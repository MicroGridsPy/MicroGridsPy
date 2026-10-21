"""Battery-degradation experiment campaign on the Kalobeyei case.

Implements the matrix in BATTERY_DEGRADATION_EXPERIMENT_PLAN.md. Each case is an isolated
copy of the base project with a few inputs patched, solved with Gurobi, and reduced to one
row of a tidy CSV.

    python scripts/run_degradation_sweep.py --list              # show the matrix, run nothing
    python scripts/run_degradation_sweep.py --only baseline     # a single case
    python scripts/run_degradation_sweep.py --block E0 E1       # the headline blocks
    python scripts/run_degradation_sweep.py                     # everything outstanding
    python scripts/run_degradation_sweep.py --qc                # the end-of-life QC block
    python scripts/run_degradation_sweep.py --qc --only QC_A_tau2_start_of_year_floor         --src <checkout of 39a3738>/src                         # QC case A, old floor

Resumable by design: a case already present in the results CSV is skipped, so the campaign
can be interrupted and continued. Use --force to re-run.

Results go to sweep_results_v2.csv (campaign) or qc_results.csv (--qc). The v1 file
sweep_results.csv was produced before the end-of-year floor and the test-time calendar
correction; it is never written to again.

Service-life refinement (run_with_life_refinement): the derived life is computed BEFORE the
solve from an estimated cycle fade. A case with refine_life re-derives it from the cycle fade a
solve realises while its end-of-life floor is slack -- a binding floor makes every life a fixed
point -- and solves at that life (see the function for the steps). This lives
here, outside the LP, on purpose: the life sets the calendar rate and the amortisation, so
making it a decision variable would put products of variables in the model.

Growth rates for E8/E9 are a working assumption awaiting a Kalobeyei source -- see GROWTH
below and say so in any write-up.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[1]
# --src points the campaign at another checkout of the package (QC case A runs the
# start-of-year floor from a worktree of the commit that still had it). Resolved before the
# first import of microgridspy, which happens lazily inside the run functions.
SRC = REPO / "src"
if "--src" in sys.argv:
    SRC = Path(sys.argv[sys.argv.index("--src") + 1]).resolve()
sys.path.insert(0, str(SRC))

BASE = REPO / "projects" / "Kalobeyei_3"
SWEEP = REPO / "projects" / "_sweep"
RESULTS = REPO / "projects" / "_sweep" / "sweep_results_v2.csv"
QC_RESULTS = REPO / "projects" / "_sweep" / "qc_results.csv"
LEGACY_RESULTS = REPO / "projects" / "_sweep" / "sweep_results.csv"  # v1, read-only
INHERIT = "inherit"  # keep whatever the base project says
SOLVER_PARAMS = {"Method": 2, "Crossover": 0}  # barrier, no crossover: 5x faster, same optimum

# Demand growth, sourced.
#
# PRIMARY (Baldi et al., Nature Energy 2022, "Planning sustainable electricity solutions for
# refugee settlements in sub-Saharan Africa"): hourly demand grows 10 %/yr to year 5, then is
# held constant for the project life. That paper reconstructs Kalobeyei demand from a 2020
# field campaign (325 respondents, metered and reconstructed consumption from mini-grid,
# diesel, SHS and PV), and states the assumption reproduces what Kenyan mini-grid developers
# use given long-run forecast uncertainty. Same settlement as this case study, so it is the
# defensible primary scenario.
#
# COMPOUNDING -- an interpretation, and it must be reported as one. Baldi et al. do not say
# "compound" explicitly, but neither do they describe the growth as linear, and the wording is
# consistent with the standard reading of a 10 % annual growth rate. It is therefore taken as
# compound: 1.10**5 = 1.61x by year 5 (a linear reading would give 1.50x, ~7 % lower peak).
# Any write-up should say "we interpret the stated 10 %/yr as compound" rather than attributing
# the compounding to the source. Flip GROWTH["compound"] to False to test the alternative.
#
# SHAPE SENSITIVITY: two 2025 studies of rural Kenyan mini-grids argue appliance adoption is
# logistic rather than a constant CAGR -- gradual, cumulative, heterogeneous, with early
# adopters saturating around year 6-13 and late adopters far slower (Energy Research & Social
# Science, "What happens after electrification?"; Energy for Sustainable Development,
# "Improving electricity demand growth estimation ... appliance diffusion modeling",
# doi:10.1016/j.esd.2025.101826). Since cycle fade is throughput-driven, WHEN the demand
# arrives changes the ageing, not just how much of it there is -- so the shape is tested as
# its own variable rather than assumed away.
GROWTH = {"rate": 0.10, "plateau_year": 5, "compound": True}


@dataclass
class Case:
    name: str
    block: str
    note: str = ""
    # degradation
    coefficients: bool = True
    linear_rate: float | None = None        # mode 1: capacity_degradation_rate_per_year
    enclosure: float | None = None
    calendar_scale: float | None = None
    cycle_life: float | None = None
    eol_soh: float | None = None
    dod: float | None = None
    ref_dod: float | None = None
    service_life: object = "null"           # "null" -> derived, or a number
    # system
    horizon: int | None = None
    steps: list[int] | None = None          # capacity expansion, e.g. [10, 10]
    growth_rate: float | None = None        # fraction/yr
    growth_shape: str = "ramp"              # "ramp" (Baldi) or "logistic" (diffusion studies)
    fuel_price: float | None = None         # E10: diesel price per unit of fuel
    min_renewable: float | None = None      # E11: minimum renewable penetration (1.0 = no diesel)
    # datasheet test duration tau (cycle_test_duration_years): INHERIT keeps the base
    # project's value, None removes it (no test-time calendar correction), a number sets it
    test_duration: object = INHERIT
    refine_life: bool = True                # iterate the derived life on the realised cycle fade
    floor_convention: str = "end_of_year"   # traceability only: which state the EoL floor tests
    no_battery: bool = False                # battery capacity capped at 0 (non-viable battery)
    extra: dict = field(default_factory=dict)


def matrix() -> list[Case]:
    cases = [Case("baseline", "E0", "derived life, +10 K, phi=1, N=6000, dod=0.8")]

    # E0 - the ageing ladder
    cases += [
        Case("E0_no_ageing", "E0", "no ageing at all", coefficients=False, linear_rate=0.0,
             service_life=8),
        Case("E0_linear", "E0", "flat rate matched to the same 8-year nominal life",
             coefficients=False, linear_rate=0.025, service_life=8),
    ]
    # E1 - enclosure rise (the dominant sensitivity); +10 K is the baseline
    cases += [Case(f"E1_enclosure_{t:02d}K", "E1", f"enclosure +{t} K", enclosure=float(t))
              for t in (0, 5, 15, 20)]
    # E2 - calendar magnitude band
    cases += [Case(f"E2_phi_{p}", "E2", f"calendar_fade_scale {p}", calendar_scale=p)
              for p in (1.75, 2.72)]
    # E3 - datasheet cycle life
    cases += [Case(f"E3_N_{int(n)}", "E3", f"rated cycle life {int(n)}", cycle_life=n)
              for n in (3000.0, 10000.0)]
    # E4 - end-of-life threshold
    cases += [Case("E4_eol_070", "E4", "end_of_life_soh 0.70", eol_soh=0.70)]
    # E5 - derived vs asserted life. The baseline derives 8; the estimator under-states
    # cycling by ~12 %, so a self-consistent life is nearer 7 -- this block is what decides it.
    cases += [Case(f"E5_life_{L}", "E5", f"asserted life {L} y", service_life=L)
              for L in (5, 6, 7, 10, 12, 15)]
    # E6 - depth of discharge (reference depth follows, so the datasheet anchor stays honest)
    cases += [Case(f"E6_dod_{int(100*d)}", "E6", f"depth of discharge {d}", dod=d, ref_dod=d)
              for d in (0.6, 1.0)]
    # E7 - linear-mode calibration: which flat rate reproduces the semi-empirical answer?
    cases += [Case(f"E7_linear_{r}", "E7", f"flat rate {r}/yr", coefficients=False,
                   linear_rate=r, service_life=8) for r in (0.010, 0.020, 0.030, 0.040)]
    # E8 - demand growth, Baldi et al. (2022): 10 %/yr to year 5, then constant.
    if GROWTH["rate"] is not None:
        rate = GROWTH["rate"]
        cases += [
            Case("E8_growth", "E8", "Baldi: 10 %/yr to year 5, then flat", growth_rate=rate),
            Case("E8_growth_no_ageing", "E8", "same growth, no ageing", growth_rate=rate,
                 coefficients=False, linear_rate=0.0, service_life=8),
            # Same end point, S-shaped arrival. Cycle fade is throughput-driven, so the
            # TIMING of the demand changes the ageing even when the total does not.
            Case("E8_growth_logistic", "E8", "same end point, logistic arrival",
                 growth_rate=rate, growth_shape="logistic"),
        ]
    # E9 - capacity expansion
    for n_steps, steps in ((2, [10, 10]), (4, [5, 5, 5, 5])):
        cases.append(Case(f"E9_steps{n_steps}_flat", "E9", f"{n_steps} investment steps",
                          steps=steps))
        if GROWTH["rate"] is not None:
            cases.append(Case(f"E9_steps{n_steps}_growth", "E9",
                              f"{n_steps} steps + growth", steps=steps,
                              growth_rate=GROWTH["rate"]))
    # E10 - diesel price. Every "escape to diesel" result in E1/E2/E3/E5 is conditional on
    # 1.3 per unit (0.38 /kWh at the stated LHV and efficiency). Without this block the
    # collapse threshold is a statement about one fuel price, not about storage.
    cases += [Case(f"E10_fuel_{p:g}", "E10", f"diesel {p:g}/unit", fuel_price=p)
              for p in (0.65, 1.95, 2.60)]
    # The same at the hot end, where the escape actually fires: does cheap diesel pull the
    # collapse threshold to cooler sites, and does expensive diesel remove it altogether?
    cases += [Case(f"E10_fuel_{p:g}_hot", "E10", f"diesel {p:g}/unit at +20 K",
                   fuel_price=p, enclosure=20.0) for p in (0.65, 2.60)]

    # E11 - closing the escape. Degradation costs only +5.6 % at the baseline BECAUSE the
    # model can retreat to diesel. Constraining renewable penetration shuts that valve and
    # isolates what ageing costs a system that has to carry its own storage.
    cases += [Case(f"E11_minre_{int(100*r)}", "E11", f"min renewable penetration {r:.0%}",
                   min_renewable=r) for r in (0.95, 1.0)]
    cases += [Case(f"E11_minre_{int(100*r)}_no_ageing", "E11",
                   f"min RE {r:.0%}, no ageing", min_renewable=r, coefficients=False,
                   linear_rate=0.0, service_life=8) for r in (0.95, 1.0)]
    # The no-ageing reference at the life the aged 100 % RE case refines to (10 y): a reference
    # at 8 y would mix the amortisation period into the cost of ageing.
    cases += [Case("E11_minre_100_no_ageing_L10", "E11", "min RE 100%, no ageing, life 10 y",
                   min_renewable=1.0, coefficients=False, linear_rate=0.0, service_life=10)]

    # E12 - datasheet test duration (Defect 11): the declared band around the base tau = 2.0
    cases += [Case(f"E12_tau_{t:g}", "E12", f"cycle_test_duration_years {t:g}",
                   test_duration=t) for t in (1.5, 3.0)]

    return cases


# The reduced v2 campaign (decided after the end-of-life QC): the cases the paper's claims rest
# on. Parameter uncertainty (N, the upper phi, tau beyond its band) moves to the separate
# robustness analysis; E4, E6 and E9 are cut (outside the validity domain, a flawed design, a
# functionality check). Linear-mode cases are untouched by the corrections, so after
# E0_no_ageing reproduces its v1 result the other linear rows are reused from v1, and the
# fixed lives 7/8/9 come from the QC block (QC_F7..F9). Order: the reuse check first.
REDUCED = [
    "E0_no_ageing",
    "baseline",
    "E5_life_5", "E5_life_6", "E5_life_10", "E5_life_12",
    "E1_enclosure_00K", "E1_enclosure_05K", "E1_enclosure_15K", "E1_enclosure_20K",
    "E11_minre_100",
    "E10_fuel_0.65", "E10_fuel_2.6", "E10_fuel_2.6_hot",
    "E12_tau_1.5", "E12_tau_3",
    "E8_growth",
    "E2_phi_1.75",
]


def qc_cases() -> list[Case]:
    """End-of-life QC on the Kalobeyei base (correction plan, step 6).

    A reproduces the floor on the START-of-year state and therefore needs the package of
    commit 39a3738 (--src); every other case runs the current package.
    """
    return [
        Case("QC_A_tau2_start_of_year_floor", "QC", "tau 2.0, start-of-year floor, derived L",
             test_duration=2.0, refine_life=False, floor_convention="start_of_year"),
        Case("QC_B_tau_null", "QC", "tau null, end-of-year floor, derived L",
             test_duration=None, refine_life=False),
        Case("QC_C_tau2", "QC", "tau 2.0, end-of-year floor, derived L",
             test_duration=2.0, refine_life=False),
        Case("QC_D_tau2_refined", "QC", "C + service-life refinement",
             test_duration=2.0, refine_life=True),
    ] + [
        Case(f"QC_F{L}", "QC", f"C settings, life fixed at {L} y", test_duration=2.0,
             service_life=L, refine_life=False)
        for L in (7, 8, 9)
    ]


# ---------------------------------------------------------------------------- robustness
#
# A  Morris screening of the degradation-model uncertainty: where in the plausible space does
#    each parameter matter, and does it act alone or through interactions? r trajectories of
#    k + 1 points on a 4-level grid; mu* (mean |elementary effect|) ranks importance, sigma
#    flags interaction or thresholds. Points are named by their level indices, so a point
#    two trajectories share is solved once.
# B  Economic context as a 3 x 3 factorial (diesel price x enclosure): two factors are read
#    more directly off a grid than off Morris, and the interaction is the result.
# C  Stress corners: do the paper's claims hold at the extremes?
# Every point runs with the life refinement from below, like the campaign.

ROBUST_RESULTS = SWEEP / "robustness_results.csv"
ROBUST_DESIGN = SWEEP / "robustness_design.csv"
MORRIS_LEVELS = 4
MORRIS_SEED = 20261021
# (factor, Case field, low, high). Ranges are the paper's to defend: enclosure as in E1 (the
# hot end extrapolates the cycle law outside its fitted window), calendar_fade_scale over the
# published band, N over a typical LFP datasheet spread, tau over its declared band.
MORRIS_FACTORS = [
    ("enclosure_rise_k", "enclosure", 0.0, 20.0),
    ("calendar_fade_scale", "calendar_scale", 1.0, 2.72),
    ("cycle_life_n", "cycle_life", 4000.0, 8000.0),
    ("test_duration_y", "test_duration", 1.5, 3.0),
]
BASE_FUEL_PRICE = 1.3


def morris_design(r: int = 10, levels: int = MORRIS_LEVELS, seed: int = MORRIS_SEED
                  ) -> pd.DataFrame:
    """r Morris trajectories on a ``levels``-point grid (Morris 1991, step delta = p/(2(p-1))).

    Each trajectory starts at a random grid point and moves every factor once, in random
    order and direction, by delta in unit scale. Columns: trajectory, step, moved (the factor
    changed to reach this point, '' at the start), direction, u_<factor> (unit scale),
    <factor> (physical value), case (name from the level indices).
    """
    rng = np.random.default_rng(seed)
    k = len(MORRIS_FACTORS)
    delta = levels / (2.0 * (levels - 1))
    grid = np.arange(levels) / (levels - 1)
    low_starts = grid[grid + delta <= 1.0 + 1e-12]
    rows = []
    for t in range(r):
        sign = rng.choice([-1.0, 1.0], size=k)
        x = rng.choice(low_starts, size=k)
        x = np.where(sign < 0, x + delta, x)  # a downward step starts high
        order = rng.permutation(k)
        points = [(x.copy(), "", 0.0)]
        for i in order:
            x = x.copy()
            x[i] += sign[i] * delta
            points.append((x, MORRIS_FACTORS[i][0], float(sign[i])))
        for step, (u, moved, direction) in enumerate(points):
            idx = np.rint(u * (levels - 1)).astype(int)
            row = {"trajectory": t, "step": step, "moved": moved, "direction": direction,
                   "case": "R_" + "".join(str(i) for i in idx)}
            for (name, _field, lo, hi), ui in zip(MORRIS_FACTORS, u):
                row[f"u_{name}"] = float(ui)
                row[name] = float(lo + ui * (hi - lo))
            rows.append(row)
    return pd.DataFrame(rows)


def robustness_cases(block: str, r: int = 10) -> list[Case]:
    if block == "A":
        design = morris_design(r)
        cases: dict[str, Case] = {}
        for _, row in design.iterrows():
            if row["case"] in cases:
                continue
            kwargs = {field: float(row[name]) for name, field, _lo, _hi in MORRIS_FACTORS}
            note = ", ".join(f"{name}={row[name]:g}" for name, *_ in MORRIS_FACTORS)
            cases[row["case"]] = Case(row["case"], "RA", note, **kwargs)
        return list(cases.values())
    if block == "B":
        # the six points the campaign already solved are reused by name, not re-run
        return [Case(f"RB_fuel{p:g}_encl{t:02d}K", "RB", f"diesel {p:g}, enclosure +{t} K",
                     fuel_price=p, enclosure=float(t))
                for p, t in ((0.65, 0), (0.65, 20), (2.6, 0))]
    if block == "C":
        return [
            Case("RC_worst", "RC", "+20 K, phi 2.72, N 4000, tau 1.5", enclosure=20.0,
                 calendar_scale=2.72, cycle_life=4000.0, test_duration=1.5),
            Case("RC_best", "RC", "+0 K, phi 1.0, N 8000, tau 3.0", enclosure=0.0,
                 calendar_scale=1.0, cycle_life=8000.0, test_duration=3.0),
            Case("RC_worst_dear_diesel", "RC", "worst corner, diesel 2.6", enclosure=20.0,
                 calendar_scale=2.72, cycle_life=4000.0, test_duration=1.5, fuel_price=2.6),
        ]
    raise ValueError(f"unknown robustness block {block!r}")


# the factorial's other six cells, already in the campaign results
FACTORIAL_REUSED = {
    (1.3, 10): "baseline", (0.65, 10): "E10_fuel_0.65", (2.6, 10): "E10_fuel_2.6",
    (1.3, 0): "E1_enclosure_00K", (1.3, 20): "E1_enclosure_20K",
    (2.6, 20): "E10_fuel_2.6_hot",
}


def morris_indices(design: pd.DataFrame, results: pd.DataFrame, output: str,
                   n_boot: int = 1000, seed: int = MORRIS_SEED) -> pd.DataFrame:
    """mu, mu*, sigma and a bootstrap 95 % interval on mu* for one output.

    Elementary effects are in output units per unit-scale step of the factor (the factor's
    whole range = 1), so they compare across factors with different physical units.
    """
    values = results.set_index("case")[output]
    effects: dict[str, list[tuple[int, float]]] = {name: [] for name, *_ in MORRIS_FACTORS}
    for t, traj in design.sort_values(["trajectory", "step"]).groupby("trajectory"):
        cases = list(traj["case"])
        for step in range(1, len(traj)):
            row = traj.iloc[step]
            name = row["moved"]
            du = row[f"u_{name}"] - traj.iloc[step - 1][f"u_{name}"]
            y0, y1 = values.get(cases[step - 1], np.nan), values.get(cases[step], np.nan)
            effects[name].append((int(t), float((y1 - y0) / du)))
    rng = np.random.default_rng(seed)
    out = []
    for name, pairs in effects.items():
        ee = np.array([e for _t, e in pairs if np.isfinite(e)])
        if ee.size == 0:
            out.append({"factor": name, "n": 0})
            continue
        boot = [np.mean(np.abs(rng.choice(ee, size=ee.size, replace=True)))
                for _ in range(n_boot)]
        out.append({
            "factor": name, "n": int(ee.size), "mu": float(ee.mean()),
            "mu_star": float(np.abs(ee).mean()),
            "sigma": float(ee.std(ddof=1)) if ee.size > 1 else np.nan,
            "mu_star_lo": float(np.percentile(boot, 2.5)),
            "mu_star_hi": float(np.percentile(boot, 97.5)),
        })
    return pd.DataFrame(out).sort_values("mu_star", ascending=False).reset_index(drop=True)


def analyse_robustness(r: int = 10) -> int:
    if not ROBUST_RESULTS.exists():
        print(f"no results yet: {ROBUST_RESULTS}")
        return 1
    results = pd.read_csv(ROBUST_RESULTS)
    if "error" in results.columns:
        results = results[results["error"].isna()]
    design = morris_design(r)
    pd.set_option("display.width", 200)
    for output in ("npc", "battery_kwh", "diesel_share", "life_used"):
        print(f"\nMorris -- {output}")
        print(morris_indices(design, results, output).to_string(
            index=False, float_format=lambda v: f"{v:,.4g}"))
    return 0


# ---------------------------------------------------------------------------- building


def growth_factors(n_years: int, rate: float, plateau_year: int, shape: str) -> list[float]:
    """Per-year demand multipliers.

    ``ramp``      Baldi et al.: compound growth to ``plateau_year``, then held constant.
    ``logistic``  the same end point reached along an S-curve, as the appliance-diffusion
                  studies argue: slow start, steepest around year 6, saturating by year ~13.
                  Same total demand growth, different timing -- which is what matters for a
                  throughput-driven fade channel.
    """
    if GROWTH.get("compound", True):
        final = (1.0 + rate) ** plateau_year
    else:
        final = 1.0 + rate * plateau_year

    if shape == "ramp":
        if GROWTH.get("compound", True):
            return [(1.0 + rate) ** min(i, plateau_year) for i in range(n_years)]
        return [1.0 + rate * min(i, plateau_year) for i in range(n_years)]

    if shape == "logistic":
        midpoint, steepness = 6.0, 0.6
        def sigmoid(i: float) -> float:
            return 1.0 / (1.0 + math.exp(-steepness * (i - midpoint)))
        lo, hi = sigmoid(0.0), sigmoid(float(n_years - 1))
        return [1.0 + (final - 1.0) * (sigmoid(i) - lo) / (hi - lo) for i in range(n_years)]

    raise ValueError(f"unknown growth shape {shape!r}")


def apply_growth(inputs: Path, rate: float, plateau_year: int, shape: str = "ramp") -> None:
    """Scale the load columns by the growth profile.

    Irradiance and temperature are left stationary on purpose: one thing changes at a time,
    so the enclosure and calendar results stay uncontaminated.
    """
    path = inputs / "load_demand.csv"
    frame = pd.read_csv(path, sep=";", decimal=",", header=[0, 1])
    meta, data = frame.iloc[:, :1], frame.iloc[:, 1:]
    factors = growth_factors(data.shape[1], rate, plateau_year, shape)
    scaled = data.apply(pd.to_numeric, errors="coerce") * factors
    pd.concat([meta, scaled], axis=1).to_csv(path, sep=";", decimal=",", index=False)


def _extend_steps(by_step: dict, n_steps: int) -> None:
    """Replicate investment-step 1 until there are ``n_steps`` of them.

    Capacity expansion requires every technology to declare one investment block per step,
    not just the battery. Costs are held identical across steps on purpose: the experiment
    asks what DEGRADATION does to investment timing, so introducing a cost trend would
    confound the answer with simple deferral economics.
    """
    template = next(iter(by_step.values()))
    for i in range(len(by_step) + 1, n_steps + 1):
        by_step[str(i)] = dict(template)


def build(case: Case, root: Path = SWEEP) -> Path:
    # build() replaces the whole case directory, results included; anything that only needs
    # the inputs (the dry run) must pass its own root so it never touches solved cases.
    project = root / "projects" / case.name
    if project.exists():
        shutil.rmtree(project)
    shutil.copytree(BASE / "inputs", project / "inputs")
    inputs = project / "inputs"

    formulation = json.loads((inputs / "formulation.json").read_text(encoding="utf-8"))
    degradation = formulation["battery_model"]["degradation_model"]
    degradation["coefficients_enabled"] = case.coefficients
    if not case.coefficients:
        # Linear-fade mode: drop the semi-empirical keys so the file states one mode only.
        for key in ("end_of_life_soh", "cycle_lifetime_to_eol_cycles"):
            degradation.pop(key, None)
        formulation["battery_model"]["loss_model"] = "convex_loss_epigraph"
    if case.eol_soh is not None:
        degradation["end_of_life_soh"] = case.eol_soh
    if case.cycle_life is not None:
        degradation["cycle_lifetime_to_eol_cycles"] = case.cycle_life
    if case.coefficients and case.test_duration != INHERIT:
        if case.test_duration is None:
            degradation.pop("cycle_test_duration_years", None)
        else:
            degradation["cycle_test_duration_years"] = float(case.test_duration)
    if not case.coefficients:
        degradation.pop("cycle_test_duration_years", None)
    if case.horizon is not None:
        formulation["time_horizon_years"] = case.horizon
    if case.min_renewable is not None:
        formulation["optimization_constraints"]["min_renewable_penetration"] = case.min_renewable
    if case.steps is not None:
        formulation["capacity_expansion"] = True
        formulation["investment_steps_years"] = case.steps
    formulation["project_name"] = case.name
    (inputs / "formulation.json").write_text(json.dumps(formulation, indent=2) + "\n",
                                             encoding="utf-8")

    battery = yaml.safe_load((inputs / "battery.yaml").read_text(encoding="utf-8"))
    technical = battery["battery"]["technical"]
    for key, value in (
        ("enclosure_temperature_rise_c", case.enclosure),
        ("calendar_fade_scale", case.calendar_scale),
        ("end_of_life_soh", case.eol_soh),
        ("cycle_lifetime_to_eol_cycles", case.cycle_life),
        ("depth_of_discharge", case.dod),
        ("cycle_life_reference_dod", case.ref_dod),
    ):
        if value is not None:
            technical[key] = value
    if case.no_battery:
        technical["max_installable_capacity_kwh"] = 0.0
    technical["capacity_degradation_rate_per_year"] = (
        0.0 if case.linear_rate is None else case.linear_rate
    )
    life = None if case.service_life == "null" else case.service_life
    steps_block = battery["battery"]["investment"]["by_step"]
    if case.steps is not None:
        _extend_steps(steps_block, len(case.steps))
    for step in steps_block.values():
        step["calendar_lifetime_years"] = life
    (inputs / "battery.yaml").write_text(yaml.safe_dump(battery, sort_keys=False,
                                                        allow_unicode=True), encoding="utf-8")

    if case.steps is not None:
        renewables_path = inputs / "renewables.yaml"
        renewables = yaml.safe_load(renewables_path.read_text(encoding="utf-8"))
        for item in renewables["renewables"]:
            _extend_steps(item["investment"]["by_step"], len(case.steps))
        renewables_path.write_text(
            yaml.safe_dump(renewables, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        generator_path = inputs / "generator.yaml"
        generator = yaml.safe_load(generator_path.read_text(encoding="utf-8"))
        _extend_steps(generator["generator"]["investment"]["by_step"], len(case.steps))
        generator_path.write_text(
            yaml.safe_dump(generator, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )

    if case.fuel_price is not None:
        generator_path = inputs / "generator.yaml"
        generator = yaml.safe_load(generator_path.read_text(encoding="utf-8"))
        for block in generator["fuel"]["cost"]["by_scenario"].values():
            prices = block["by_year_cost_per_unit_fuel"]
            block["by_year_cost_per_unit_fuel"] = [case.fuel_price] * len(prices)
        generator_path.write_text(
            yaml.safe_dump(generator, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )

    if case.growth_rate:
        apply_growth(inputs, case.growth_rate, GROWTH["plateau_year"], case.growth_shape)
    return project


# ---------------------------------------------------------------------------- running


def collect(case: Case, project: Path, model, solve_s: float, warned: list[str]) -> dict:
    import microgridspy as mgp

    mgp.export_results(model.results())
    out = project / "results"
    summary = pd.read_csv(out / "reporting_summary.csv")
    metrics = summary[summary.section == "summary_metrics"].set_index("row_label")["value"]
    design = pd.read_csv(out / "design_by_step.csv").groupby("technology")["installed_capacity"].sum()
    dispatch = pd.read_csv(out / "dispatch_timeseries.csv")
    kpis = pd.read_csv(out / "kpis_yearly.csv")
    settings = model.data.attrs["settings"]["battery_model"]["degradation_model"]

    nameplate = float(design.get("battery", np.nan))
    by_year = dispatch.groupby("year")
    discharge = by_year["battery_discharge_dc"].sum()
    cycle = by_year["battery_cycle_fade"].sum() if "battery_cycle_fade" in dispatch else None
    calendar = by_year["battery_calendar_fade"].sum() if "battery_calendar_fade" in dispatch else None
    soh = by_year["battery_soh"].last() if "battery_soh" in dispatch else None
    life_used = settings.get("calendar_lifetime_years_used", np.nan)

    # Annual fades are averaged PER COHORT: over the years of the cohorts that run their full
    # life inside the horizon. A cohort fades faster when new (more usable energy to cycle),
    # so the horizon mean is biased upward by a truncated last cohort -- and the refinement
    # below needs the rate a full cohort actually ages at. Multi-step cases commission
    # cohorts at different years; there the horizon mean is kept and labelled as such.
    fade_basis = "horizon"
    full_years = len(discharge)
    if case.steps is None and life_used is not None and np.isfinite(float(life_used)):
        n_life = max(1, int(round(float(life_used))))
        if len(discharge) >= n_life:
            full_years = (len(discharge) // n_life) * n_life
            fade_basis = f"{full_years // n_life} full cohort(s)"
    cycle_mean = float(cycle.iloc[:full_years].mean()) if cycle is not None else np.nan
    calendar_mean = float(calendar.iloc[:full_years].mean()) if calendar is not None else np.nan

    # State at retirement: the lowest END-of-year state (the state the floor tests). Results
    # from a package without battery_soh_by_year.csv (QC case A) are single-cohort, so it is
    # rebuilt from the start-of-year state minus that year's fades.
    soh_end = np.nan
    soh_table = out / "battery_soh_by_year.csv"
    if soh_table.exists():
        table = pd.read_csv(soh_table)
        if not table.empty:
            soh_end = float(pd.to_numeric(table["soh_end_of_year"], errors="coerce").min())
    elif soh is not None and cycle is not None and calendar is not None and nameplate > 0:
        soh_end = float((soh - (cycle + calendar) / nameplate).min())
    tau = settings.get("cycle_test_duration_years", None)
    dod = float(yaml.safe_load((project / "inputs" / "battery.yaml").read_text(
        encoding="utf-8"))["battery"]["technical"]["depth_of_discharge"])

    # Cell temperature weighted by what the battery actually did, versus by the load. The gap
    # is the thermal arbitrage the hourly coefficient invites.
    ambient = pd.read_csv(project / "inputs" / "ambient_temperature.csv", sep=";", decimal=",",
                          header=[0, 1])
    cell = pd.to_numeric(ambient.iloc[:, 1], errors="coerce").to_numpy() + float(
        settings.get("enclosure_temperature_rise_c", 0.0) or 0.0)
    first = dispatch[dispatch.year == dispatch.year.min()]
    w_dis = first["battery_discharge_dc"].to_numpy()
    t_dis = float(np.average(cell, weights=w_dis)) if w_dis.sum() > 0 else math.nan

    row = {
        "case": case.name, "block": case.block, "note": case.note,
        "npc": float(metrics.get("Net Present Cost (Expected)", np.nan)),
        "lcoe": float(metrics.get("LCOE", np.nan)),
        "pv_kw": float(design.get("renewable", np.nan)),
        "battery_kwh": nameplate,
        "generator_kw": float(design.get("generator", np.nan)),
        "lost_load_kwh": float(dispatch["lost_load"].sum()),
        "renewable_penetration": float(kpis["renewable_penetration"].mean()),
        "curtailment_share": float(kpis.get("renewable_curtailment_share", pd.Series([np.nan])).mean()),
        "generator_kwh": float(kpis["generator_generation_kwh"].sum()),
        "efc_realised": float((discharge / (nameplate * dod)).mean()) if nameplate > 0 else np.nan,
        "efc_assumed": settings.get("assumed_equivalent_full_cycles_per_year", np.nan),
        "cycle_fade_kwh_yr": cycle_mean,
        "calendar_fade_kwh_yr": calendar_mean,
        "fade_mean_basis": fade_basis,
        "calendar_share": (float(calendar.sum() / (cycle.sum() + calendar.sum()))
                           if cycle is not None and calendar is not None
                           and (cycle.sum() + calendar.sum()) > 0 else np.nan),
        "soh_min": float(soh.min()) if soh is not None else np.nan,
        "usable_at_retirement_kwh": (float(soh.min() * nameplate)
                                     if soh is not None and nameplate > 0 else np.nan),
        "life_derived": settings.get("calendar_lifetime_years_derived", np.nan),
        "life_used": life_used,
        "calendar_budget_fraction": settings.get("calendar_fade_budget_fraction", np.nan),
        "mean_cell_temp_c": settings.get("mean_cell_temperature_c", np.nan),
        "cell_temp_discharge_weighted_c": t_dis,
        "diesel_share": (float(kpis["generator_generation_kwh"].sum()
                               / kpis["served_energy_kwh"].sum())
                         if kpis["served_energy_kwh"].sum() > 0 else np.nan),
        # Defect 11 / end-of-life traceability
        "floor_convention": case.floor_convention,
        "cycle_test_duration_years": (("null" if tau is None else float(tau))
                                      if case.coefficients else np.nan),
        "lambda_cyc": settings.get("lambda_cyc", np.nan),
        "c_at_tref": settings.get("c_at_tref", np.nan),
        "test_time_calendar_fade": settings.get("test_time_calendar_fade", np.nan),
        "soh_end_of_cohort": soh_end,
        "f_cyc_realised": cycle_mean / nameplate if nameplate > 0 else np.nan,
        "f_cal_realised": calendar_mean / nameplate if nameplate > 0 else np.nan,
        # inputs of the derived-life solver, so a refinement step can be audited from the row
        "chemistry": settings.get("chemistry", ""),
        "calendar_mean_soc": settings.get("calendar_mean_soc", np.nan),
        "calendar_fade_scale": settings.get("calendar_fade_scale", np.nan),
        "end_of_life_soh": settings.get("end_of_life_soh", np.nan),
        "life_sequence": "",
        "life_iterations": 1,
        "life_note": "",
        "solve_s": round(solve_s, 1),
        "warnings": " | ".join(warned),
    }
    return row


def provenance() -> dict:
    coefficients = REPO / "src" / "microgridspy" / "data_pipeline" / "layer1_liion_coefficients.json"
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=SRC,
                                capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = ""
    try:
        import gurobipy
        gurobi = ".".join(str(v) for v in gurobipy.gurobi.version())
    except Exception:
        gurobi = ""
    return {
        "git_commit": commit,
        "package_src": str(SRC),
        "gurobi": gurobi,
        "coefficients_md5": hashlib.md5(coefficients.read_bytes()).hexdigest(),
    }


def _package_floor_convention() -> str:
    """Which state the end-of-life floor of the imported package tests."""
    text = (SRC / "microgridspy" / "multi_year_model" / "constraints.py").read_text(
        encoding="utf-8")
    return ("end_of_year" if "bat_eff_cap - bat_cycle_fade - bat_calendar_fade" in text
            else "start_of_year")


def run(case: Case, prov: dict) -> dict:
    import microgridspy as mgp

    package = _package_floor_convention()
    if package != case.floor_convention:
        raise RuntimeError(
            f"case {case.name} needs the {case.floor_convention} floor but the package at "
            f"{SRC} has the {package} one (QC case A: pass --src <checkout of 39a3738>/src)"
        )
    project = build(case)
    mgp.set_workspace(SWEEP)
    start = time.time()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = mgp.solve(case.name, solver="gurobi", solver_params=SOLVER_PARAMS)
        solve_s = time.time() - start
        warned = sorted({str(w.message).split(".")[0][:120] for w in caught})
        row = collect(case, project, model, solve_s, warned)
    return {**row, **prov}


def refinement_exclusion(case: Case) -> str | None:
    """Why a case is NOT refined, or None if it is (the battery size is checked after solving)."""
    if not case.coefficients:
        return "linear/no-ageing mode, not refined"
    if case.service_life != "null":
        return "fixed life, not refined"
    if case.steps is not None and len(case.steps) > 1:
        return "multi-step, not refined"
    if not case.refine_life:
        return "refinement off"
    return None


def derived_life_for_row(row: dict) -> float:
    """The derived-life solver of the package, fed with the cycle fade the solve realised.

    Same function, same inputs as the loader: only cycle_fade_per_year changes.
    """
    from microgridspy.data_pipeline.battery_degradation_coefficients import (
        implied_calendar_life,
    )

    return implied_calendar_life(
        row["chemistry"],
        float(row["calendar_mean_soc"]),
        float(row["mean_cell_temp_c"]),
        cycle_fade_per_year=float(row["f_cyc_realised"]),
        usable_soh_budget=1.0 - float(row["end_of_life_soh"]),
        scale=float(row["calendar_fade_scale"]),
    )


def round_life(years: float) -> int:
    """The loader's rounding rule (half-up), so a refined life lands where a derived one would."""
    from microgridspy.multi_year_model.data import _round_service_life

    return int(_round_service_life(years))


def _fmt_life(value) -> str:
    return f"{float(value):g}"


def a_priori_life(case: Case) -> float:
    """The service life the loader derives before any solve (unrounded).

    Loads the case in the scratch workspace -- no solve, nothing under SWEEP/projects touched.
    """
    import microgridspy as mgp
    import microgridspy.multi_year_model.data as mdata
    import microgridspy.multi_year_model.sets as msets

    scratch = SWEEP / "_dry_run"
    build(case, root=scratch)
    mgp.set_workspace(scratch)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = mdata.initialize_data(case.name, msets.initialize_sets(case.name))
    settings = data.attrs["settings"]["battery_model"]["degradation_model"]
    return float(settings["calendar_lifetime_years_derived"])


def floor_binds(row: dict, tol: float = 1e-4) -> bool:
    """True when a cohort retires AT the end-of-life floor rather than above it."""
    return float(row["soh_end_of_cohort"]) <= float(row["end_of_life_soh"]) + tol


def run_with_life_refinement(case: Case, max_iter: int = 5, min_battery_kwh: float = 1.0,
                             *, prov: dict | None = None) -> dict:
    """Re-derive the life from cycling the floor did NOT constrain; solve at that life.

    Why from below: when the end-of-life floor binds, the solve adjusts nameplate and diesel
    until the cumulative fade over L years is exactly B, so the realised cycle fade is
    (B - r_cal*L)/L and re-deriving the life returns L itself -- every L is a fixed point and
    the realised cycling says nothing. Only a solve whose floor is slack shows the cycling the
    system chooses on its own, and that is the cycling the life equation needs.

        1. start at the a-priori derived life minus one year, life fixed;
        2. while the floor binds, step one year shorter, until it is slack;
        3. from a slack solve, re-derive L (package solver, half-up rounding) and solve there;
        4. stop when the life reaches a binding solve (a consistent fixed point), when it
           repeats, or when the solve budget runs out (the last solved life is kept).
    """
    prov = prov or {}
    derived = a_priori_life(case)
    life = max(2, round_life(derived) - 1)
    rows: dict[int, dict] = {}
    seq: list[int] = []
    rederived = np.nan
    note = ""

    def solve(L: int) -> dict:
        if L not in rows:
            rows[L] = run(replace(case, name=f"{case.name}__L{L}", service_life=int(L)), prov)
        seq.append(L)
        return rows[L]

    while True:
        row = solve(life)
        if not (float(row["battery_kwh"]) >= min_battery_kwh):
            note = "no battery, not refined"
            break
        if floor_binds(row):
            if any(not floor_binds(r) for r in rows.values()):
                note = "converged from below (floor binding)"
                break
            # no slack solve yet: the start was already too long
            if life <= 2:
                note = "floor binds even at 2 y"
                break
            new = life - 1
        else:
            rederived = derived_life_for_row(row)
            new = max(life, round_life(rederived))  # slack => fade < B => L* > life
            if new == life:
                note = "converged from below (floor slack)"
                break
        if new not in rows and len(rows) >= max_iter:
            note = "solve budget exhausted, last kept"
            break
        life = new
    final = rows[seq[-1]]
    return {
        **final,
        "case": case.name,
        # every tried life keeps its own project directory; this one holds the chosen life
        "results_project": f"{case.name}__L{seq[-1]}",
        "life_derived": derived,
        "life_rederived": rederived,
        "life_sequence": "->".join(str(v) for v in seq),
        "life_iterations": len(rows),
        "life_note": note,
    }


NON_VIABLE = "implied service life is under"


def run_without_battery(case: Case, prov: dict, why: str) -> dict:
    """Option b for inputs the degradation model refuses (implied life under 2 years).

    A planner facing a battery that would not last two years does not install one, so the
    point is solved with battery capacity capped at zero (linear mode, no ageing: with no
    battery the degradation settings do nothing). The result is a valid point of the design
    -- the threshold beyond which storage is not viable -- rather than a hole in it.
    """
    variant = replace(case, name=f"{case.name}__nobattery", no_battery=True,
                      coefficients=False, linear_rate=0.0, service_life=8, refine_life=False)
    row = run(variant, prov)
    return {**row, "case": case.name, "results_project": variant.name,
            "life_used": np.nan, "life_sequence": "", "life_iterations": 1,
            "life_note": f"battery not viable, solved without battery ({why[:120]})"}


def run_case(case: Case, prov: dict) -> dict:
    from microgridspy.errors import InputValidationError

    reason = refinement_exclusion(case)
    try:
        if reason is None:
            return run_with_life_refinement(case, prov=prov)
        row = run(case, prov)
    except InputValidationError as exc:
        if NON_VIABLE not in str(exc):
            raise
        return run_without_battery(case, prov, str(exc))
    life = row.get("life_used", np.nan)
    return {**row, "life_sequence": _fmt_life(life) if life == life else "",
            "life_iterations": 1, "life_note": reason}


def append_row(path: Path, row: dict) -> None:
    """Rewrite the CSV with the union of columns, replacing any earlier row of the same case.

    Appending under the old header drops (or shifts) any column the earlier rows did not
    have, so the file is read, extended and written back whole.
    """
    frame = pd.DataFrame([row])
    if path.exists():
        previous = pd.read_csv(path)
        # a re-run (--force) replaces the case's earlier row instead of duplicating it
        previous = previous[previous["case"] != row.get("case")]
        columns = list(previous.columns) + [c for c in frame.columns
                                            if c not in previous.columns]
        frame = pd.concat([previous, frame], ignore_index=True).reindex(columns=columns)
    frame.to_csv(path, index=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--only", nargs="+", default=None)
    parser.add_argument("--block", nargs="+", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="build and load every case without solving")
    parser.add_argument("--robustness", choices=["A", "B", "C"], default=None,
                        help="robustness block, written to robustness_results.csv")
    parser.add_argument("--morris-r", type=int, default=10, help="Morris trajectories (A)")
    parser.add_argument("--analyse-robustness", action="store_true")
    parser.add_argument("--reduced", action="store_true",
                        help="the reduced v2 campaign (REDUCED), in that order")
    parser.add_argument("--qc", action="store_true",
                        help="the end-of-life QC block, written to qc_results.csv")
    parser.add_argument("--src", default=None,
                        help="package source to run (QC case A: a checkout of 39a3738)")
    args = parser.parse_args()

    if args.analyse_robustness:
        return analyse_robustness(args.morris_r)
    cases = qc_cases() if args.qc else matrix()
    if args.robustness:
        cases = robustness_cases(args.robustness, args.morris_r)
        if args.robustness == "A" and not args.list:
            SWEEP.mkdir(parents=True, exist_ok=True)
            morris_design(args.morris_r).to_csv(ROBUST_DESIGN, index=False)
    if args.reduced:
        by_name = {c.name: c for c in cases}
        cases = [by_name[n] for n in REDUCED]
    results = QC_RESULTS if args.qc else (ROBUST_RESULTS if args.robustness else RESULTS)
    assert results != LEGACY_RESULTS
    if args.block:
        cases = [c for c in cases if c.block in args.block]
    if args.only:
        cases = [c for c in cases if c.name in args.only]

    if args.list:
        print(f"{len(cases)} cases")
        for c in cases:
            print(f"  {c.block:<4} {c.name:<26} {c.note}")
        if GROWTH["rate"] is None:
            print("\nNOTE: E8 (and the E9 growth cases) are skipped until GROWTH['rate'] is set "
                  "from a sourced figure.")
        return 0

    SWEEP.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        # Build and load each case without solving. On a 26-case campaign a construction
        # error discovered at case 20 costs hours, and every such error is visible here in
        # seconds: the loader runs the full validation, the guards and the derived life.
        import microgridspy as mgp
        import microgridspy.multi_year_model.data as mdata
        import microgridspy.multi_year_model.sets as msets

        failures = 0
        scratch = SWEEP / "_dry_run"
        for case in cases:
            build(case, root=scratch)
            mgp.set_workspace(scratch)
            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    sets = msets.initialize_sets(case.name)
                    ds = mdata.initialize_data(case.name, sets)
                deg = ds.attrs["settings"]["battery_model"]["degradation_model"]
                note = (f"life {deg.get('calendar_lifetime_years_used', '-')}"
                        f" | budget {deg.get('calendar_fade_budget_fraction', float('nan')):.2f}"
                        if deg.get("coefficients_enabled") else "linear fade")
                flag = "  WARN: " + str(caught[0].message)[:70] if caught else ""
                print(f"  OK   {case.name:<26} {note}{flag}")
            except Exception as exc:
                failures += 1
                print(f"  FAIL {case.name:<26} {type(exc).__name__}: {str(exc)[:110]}")
        print()
        print(f"{len(cases) - failures}/{len(cases)} cases build and load")
        return 1 if failures else 0

    done: set[str] = set()
    if results.exists() and not args.force:
        previous = pd.read_csv(results)
        # A case that errored is NOT done: treating an error row as a completed case means a
        # transient failure (a locked file, a half-written directory) silently removes that
        # case from the campaign for good.
        if "error" in previous.columns:
            previous = previous[previous["error"].isna()]
        done = set(previous["case"])
    todo = [c for c in cases if c.name not in done]
    print(f"{len(todo)} to run, {len(cases) - len(todo)} already done")

    prov = provenance()
    for i, case in enumerate(todo, 1):
        print(f"\n[{i}/{len(todo)}] {case.name} -- {case.note}", flush=True)
        try:
            row = run_case(case, prov)
        except Exception as exc:  # a failed case must not sink the campaign
            print(f"  FAILED: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
            row = {"case": case.name, "block": case.block, "note": case.note,
                   "error": f"{type(exc).__name__}: {str(exc)[:300]}", **prov}
        append_row(results, row)
        if "error" not in row:
            print(f"  NPC {row['npc']:,.0f} | battery {row['battery_kwh']:.1f} kWh | "
                  f"life {row['life_sequence']} ({row['life_note']}) | "
                  f"SoH_end {row['soh_end_of_cohort']:.4f} | {row['solve_s']:.0f} s",
                  flush=True)
    print(f"\nresults -> {results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
