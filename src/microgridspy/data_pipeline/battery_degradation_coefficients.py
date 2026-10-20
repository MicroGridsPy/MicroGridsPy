"""
Pre-fitted Li-ion battery-degradation coefficients (inputs side only).

Everything in this module is exogenous to the optimisation: static coefficients evaluated
once per run against the cluster's own temperature series, so the model stays linear.

Two channels
------------
**Cycle fade.** A marginal cost ``c(T)``: capacity lost (fraction of nameplate) per unit of
discharge throughput, at cell temperature ``T``. ``c(T) = Psi(DoD, T) / DoD`` is the mean
slope of the depth-resolved per-cycle fade curve ``Psi(D, T)`` over the usable window, so one
full-DoD discharge costs exactly ``Psi(DoD, T)``. ``Psi`` ships as
``layer1_liion_coefficients.json`` (distilled from the offline Layer-I electro-thermal model):
fine 10 % depth slices, each a cubic in ``y = T[degC] / 10``.

``Psi`` is all but linear in ``D`` -- 1.7 % from the shallowest to the deepest slice for LFP,
flat past ``D = 0.5`` -- so resolving depth does not repay a per-band LP state. Temperature,
which moves ``c`` by 4.3x over 10-45 degC, is where the signal is.

**Calendar fade.** The empirical storage-ageing fit of Ali et al. (2023), Front. Energy Res.
11:1108269, Table 3: Arrhenius in temperature, exponential in mean SoC, ``t**0.48`` in time.
It is linearised to one rate per year over the battery's service life so the LP stays linear.
This REPLACES the per-hour cubic inherited from the pre-audit implementation, which gave
0.052 %/yr at 25 degC -- a 386-year calendar life, one to two orders of magnitude below every
measured LFP storage dataset. See ``CALENDAR_FADE_SOURCES`` for the calibration evidence.

Shape and magnitude
-------------------
Shape is predefined (identical for every cluster; only the temperature series changes).
Magnitude is pinned to the user's datasheet cycle life, so that ``N_user`` cycles at the rated
DoD and rated temperature consume exactly ``initial_soh - end_of_life_soh``.

Scope
-----
Li-ion only (LFP, NMC). Lead-acid is deliberately out of scope: the calendar fit has no
lead-acid row and no long-duration measurement to anchor one, and lead-acid depth banding needs
the Schiffer model rather than this distillation.

Known residual errors, carried knowingly
----------------------------------------
* The cubic temperature surrogate misfits the steep NMC law by up to 14 % inside its own fitted
  window and turns negative below it, where the implementation would clip it to zero and assign
  an NMC battery at a cool site *zero* cycle fade. ``_check_temperature_domain`` refuses that
  instead of clipping silently. An Arrhenius-form fit in ``1/T`` would remove the problem.
* The LFP-datasheet temperature correction used in the distillation was applied to NMC as well,
  giving NMC an implied activation energy of 70 kJ/mol against a published ~50. NMC therefore
  warns and should be read as the pessimistic end of the band.
* A datasheet cycle life is measured on cells that also age by calendar while the test runs, so
  pinning the cycle channel to consume the whole budget attributes that calendar ageing to
  cycling and counts it twice. ``cycle_test_duration_years`` opts out of the double count; it
  defaults to ``None`` because the test duration is not on datasheets.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np

from microgridspy.errors import InputValidationError

LFP = "LFP"
NMC = "NMC"
VALID_CHEMISTRIES = (LFP, NMC)

# Retained only so the pre-audit call sites still import; carries no coefficients and matches
# no chemistry. Removed together with the legacy block at the bottom of this module.
LEAD_ACID = "lead_acid"

_LEAD_ACID_ALIASES = frozenset({"lead_acid", "leadacid", "pba", "lead", "pb_acid"})

# ---------------------------------------------------------------------------
# Calendar ageing
# ---------------------------------------------------------------------------
# Ali et al. (2023), Front. Energy Res. 11:1108269, Table 3:
#     Q_cal(SoC, T, t) = a1 * exp(a2*SoC) * b1 * exp(b2/T) * t**c1
# t in days, T in kelvin, Q as a fraction of nominal capacity lost. Coefficients are
# (a1, a2, b1, b2, c1) per chemistry. b2 = -Ea/R, so LFP implies Ea = 29.0 kJ/mol and one fade
# doubling per 17.6 degC at 25 degC; c1 = 0.48 is the diffusion-limited (roughly square-root)
# SEI growth law.
_CALENDAR_FIT: dict[str, tuple[float, float, float, float, float]] = {
    LFP: (0.00157, 1.317, 142300.0, -3492.0, 0.48),
    NMC: (0.03304, 0.5036, 385.3, -2708.0, 0.51),
}

# Calibration evidence for the LFP fit, and why `calendar_fade_scale` exists.
#   * Ali et al. (2023) Table 3 is a cross-study fit to published LFP storage datasets
#     (Naumann 2018, Keil 2016, Eddahech 2015, Geisbauer 2021). Reproducing the paper's own
#     Figure 5 point -- 0 degC, SoC 0, 50 y -- gives 6.99 % against 7 % published, which is how
#     the functional form above was confirmed.
#   * Independent long-duration check: Sony/Murata LFP/C cells stored 10 years at 6 degC and
#     50 % SoC retained 96-98 % of capacity (J. Power Sources, 2025, S0378775325016155). The
#     fit predicts 8.2 % loss there, i.e. it is 2-3x pessimistic at low temperature.
#   * Extrapolating that measurement to 25 degC / SoC 0.6 with the same Arrhenius slope gives
#     0.76 %/yr, against 2.07 %/yr from the unscaled fit. The literature therefore brackets
#     roughly 0.8-2.1 %/yr at 25 degC, a spread of 2.7x.
# So the fit is trustworthy in SHAPE (Arrhenius in T, exponential in SoC, t^0.48 in time) but
# biased high in MAGNITUDE, because it is fitted to short tests (120-885 days) and extrapolated.
# It is therefore renormalised onto the one direct long-duration measurement -- the same
# shape-from-fit / magnitude-from-measurement split the cycle coefficients use with the rated
# cycle life. `calendar_fade_scale` then moves along the literature band: 1.0 is the anchored
# model, ~2.7 recovers the unscaled Ali envelope (the pessimistic end).
_CALENDAR_ANCHOR: dict[str, dict[str, float]] = {
    LFP: {"mean_soc": 0.5, "temperature_degc": 6.0, "years": 10.0, "fade_fraction": 0.03},
}
CALENDAR_FADE_SOURCES = (
    "shape: Ali et al. (2023) Front. Energy Res. 11:1108269 Table 3 (LFP cross-study storage "
    "fit); magnitude anchored to the 10-year LFP/C shelf-ageing measurement (96-98 % retention "
    "at 6 degC / 50 % SoC), J. Power Sources (2025) S0378775325016155"
)

# ---------------------------------------------------------------------------
# Cycle ageing
# ---------------------------------------------------------------------------
# Datasheet cycle life is quoted at a stated depth of discharge and temperature, so the
# calibration needs both. Defaults follow the usual datasheet convention (80 % DoD, 25 degC).
# The shipped Psi shape was fitted at FULL DoD and 25 degC (layer1 meta: test_DOD 1.0,
# test_T_C 25, N_cycles 6000 to 80 % SoH), which is why the pre-audit N_ref/N_user scaling
# silently delivered 7372 cycles when a user asked for 6000 at 80 % DoD -- a 23 % error in the
# fade budget.
DEFAULT_CYCLE_LIFE_REFERENCE_DOD = 0.8
DEFAULT_CYCLE_LIFE_REFERENCE_TEMPERATURE_C = 25.0

# The distillation grid runs 10-45 degC. The cubic surrogate degrades gracefully for LFP
# (-11 % at 5 degC, -12 % at 55 degC) but turns negative for NMC below the window, and the
# underlying linear temperature correction has a hard singularity at 78.3 degC.
CYCLE_TEMPERATURE_WINDOW_C = (10.0, 50.0)

_BAND_COEFF_PATH = Path(__file__).with_name("layer1_liion_coefficients.json")
_BAND_COEFF_CACHE: dict[str, Any] | None = None


def normalize_chemistry(raw: Any, *, default: str | None = None) -> str:
    """Resolve a user-supplied chemistry string to LFP or NMC."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        if default is not None:
            return default
        raise InputValidationError(
            "battery.technical.chemistry is required when battery degradation is active. "
            f"Allowed values (Li-ion only): {list(VALID_CHEMISTRIES)}."
        )
    value = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    if value in _LEAD_ACID_ALIASES:
        raise InputValidationError(
            f"battery.technical.chemistry {raw!r} is no longer supported: the battery "
            "degradation model is Li-ion only. The calendar-ageing fit has no lead-acid "
            "parameterisation and no long-duration measurement to anchor one, and lead-acid "
            "depth banding needs the Schiffer model rather than this distillation. "
            f"Allowed values: {list(VALID_CHEMISTRIES)}."
        )
    aliases = {
        "lfp": LFP,
        "lifepo4": LFP,
        "lithium_lfp": LFP,
        "nmc": NMC,
        "nca": NMC,
        "lithium_nmc": NMC,
    }
    if value not in aliases:
        raise InputValidationError(
            f"Invalid battery.technical.chemistry {raw!r}. "
            f"Allowed values (Li-ion only): {list(VALID_CHEMISTRIES)}."
        )
    return aliases[value]


def _cubic(coeffs: tuple[float, float, float, float], x: np.ndarray) -> np.ndarray:
    c1, c2, c3, c4 = coeffs
    return c1 * x**3 + c2 * x**2 + c3 * x + c4


# ===========================================================================
# Calendar fade
# ===========================================================================


def raw_calendar_fade_fraction(
    chemistry: str,
    mean_soc: float,
    mean_temperature_degc: np.ndarray,
    years: float,
) -> np.ndarray:
    """The Ali et al. fit as published, before the long-duration anchor is applied.

    Exposed so the published Figure 5 point can be checked directly, and so the anchor factor
    is observable rather than buried.
    """
    a1, a2, b1, b2, c1 = _CALENDAR_FIT[normalize_chemistry(chemistry)]
    soc = float(mean_soc)
    if not (0.0 <= soc <= 1.0):
        raise InputValidationError("battery calendar mean SoC must be within [0, 1].")
    if float(years) <= 0.0:
        raise InputValidationError("battery calendar reference years must be > 0.")
    kelvin = np.asarray(mean_temperature_degc, dtype=float) + 273.15
    if np.any(kelvin <= 0.0):
        raise InputValidationError("battery calendar temperature must be above absolute zero.")
    days = 365.0 * float(years)
    return a1 * np.exp(a2 * soc) * b1 * np.exp(b2 / kelvin) * days**c1


def _calendar_anchor_scale(chemistry: str) -> float:
    """Renormalisation factor putting the fit onto the measured long-duration anchor."""
    chem = normalize_chemistry(chemistry)
    anchor = _CALENDAR_ANCHOR.get(chem)
    if anchor is None:
        return 1.0  # no long-duration measurement available for this chemistry
    raw = float(
        raw_calendar_fade_fraction(
            chem, anchor["mean_soc"], np.array([anchor["temperature_degc"]]), anchor["years"]
        )[0]
    )
    return anchor["fade_fraction"] / raw if raw > 0.0 else 1.0


def calendar_fade_fraction(
    chemistry: str,
    mean_soc: float,
    mean_temperature_degc: np.ndarray,
    years: float,
) -> np.ndarray:
    """Cumulative calendar fade [fraction of nameplate] after ``years`` at (T, mean SoC)."""
    chem = normalize_chemistry(chemistry)
    return _calendar_anchor_scale(chem) * raw_calendar_fade_fraction(
        chem, mean_soc, mean_temperature_degc, years
    )


def calendar_rate_per_year(
    chemistry: str,
    mean_soc: float,
    mean_temperature_degc: np.ndarray,
    *,
    reference_years: float,
    scale: float = 1.0,
) -> np.ndarray:
    """Linear-equivalent calendar fade [fraction of nameplate per year].

    The empirical law is sub-linear in time (t^0.48), while the LP carries one rate per year.
    The rate returned is ``Q_cal(reference_years) / reference_years``, so the CUMULATIVE loss is
    correct at the reference horizon -- which is what the end-of-life floor and the capacity
    state depend on -- at the cost of straightening the trajectory within a cohort's life.
    Set ``reference_years`` to the battery's service life.
    """
    if float(scale) < 0.0:
        raise InputValidationError("battery calendar_fade_scale must be >= 0.")
    total = calendar_fade_fraction(chemistry, mean_soc, mean_temperature_degc, reference_years)
    return np.clip(float(scale) * total / float(reference_years), 0.0, None)


def implied_calendar_life(
    chemistry: str,
    mean_soc: float,
    mean_temperature_degc: float,
    *,
    cycle_fade_per_year: float,
    usable_soh_budget: float,
    scale: float = 1.0,
    min_years: float = 2.0,
    max_years: float = 40.0,
) -> float:
    """Years until calendar and cycle ageing together consume the usable SoH budget.

    Solves ``scale * Q_cal(T, SoC, L) + L * cycle_fade_per_year = budget`` for L. ``Q_cal``
    grows as ``L**c1`` with ``c1 < 1`` and the cycle term grows linearly, so the left-hand side
    is strictly increasing and the root is unique. Bisection, clamped to
    ``[min_years, max_years]``.

    This is the physical service life: the point at which the cohort reaches end-of-life SoH.
    It is what makes ``calendar_lifetime_years`` consistent with ``end_of_life_soh`` instead of
    an independent guess. ``cycle_fade_per_year`` has to be assumed, because the real value is a
    dispatch decision -- see the caller for how it is estimated from the load profile.
    """
    budget = float(usable_soh_budget)
    if not (0.0 < budget <= 1.0):
        raise InputValidationError(
            "battery initial_soh - end_of_life_soh must be within (0, 1] to derive a service life."
        )
    cyc = max(0.0, float(cycle_fade_per_year))
    temp = np.array([float(mean_temperature_degc)], dtype=float)

    def _fade(years: float) -> float:
        cal = float(scale) * float(calendar_fade_fraction(chemistry, mean_soc, temp, years)[0])
        return cal + years * cyc

    # Clamping a sub-year or sub-two-year result would be worse than failing. At L = 1 every
    # year becomes a commissioning year, so SoH resets annually, fade never accumulates, the
    # end-of-life floor is trivially satisfied and the degradation model silently switches
    # itself off -- while CAPEX amortises over a single year. The run would look plausible and
    # be wrong, so these are hard errors instead.
    first_year_fade = _fade(1.0)
    if first_year_fade >= budget:
        raise InputValidationError(
            f"Battery degradation consumes the entire usable SoH budget within one year: "
            f"{100.0 * first_year_fade:.1f} % against a budget of {100.0 * budget:.1f} % "
            f"(initial_soh - end_of_life_soh), at a mean cell temperature of "
            f"{float(mean_temperature_degc):.1f} degC with calendar_fade_scale={float(scale):.2f}. "
            "No replacement interval can represent that. Check "
            "battery.technical.enclosure_temperature_rise_c and calendar_fade_scale, and whether "
            "this site needs active cooling to be viable at all."
        )
    lo, hi = float(min_years), float(max_years)
    if _fade(lo) >= budget:
        raise InputValidationError(
            f"Battery implied service life is under {lo:.0f} years at a mean cell temperature of "
            f"{float(mean_temperature_degc):.1f} degC (fade over {lo:.0f} y would be "
            f"{100.0 * _fade(lo):.1f} % against a budget of {100.0 * budget:.1f} %). The annual "
            "replacement model cannot represent a life that short: a one-year interval resets SoH "
            "every year and disables the degradation state entirely. Reduce "
            "battery.technical.enclosure_temperature_rise_c or calendar_fade_scale, or treat this "
            "site as requiring a cooled enclosure."
        )
    if _fade(hi) <= budget:
        return hi
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _fade(mid) < budget:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ===========================================================================
# Cycle fade
# ===========================================================================


def _load_band_coefficients() -> dict[str, Any]:
    global _BAND_COEFF_CACHE
    if _BAND_COEFF_CACHE is None:
        if not _BAND_COEFF_PATH.exists():
            raise InputValidationError(
                f"Missing depth-band coefficient file: {_BAND_COEFF_PATH}. It is produced by the "
                "offline Layer-I model and shipped with the package."
            )
        _BAND_COEFF_CACHE = json.loads(_BAND_COEFF_PATH.read_text(encoding="utf-8"))
    return _BAND_COEFF_CACHE


def _psi_at(edges: np.ndarray, psi_edges: np.ndarray, d: float) -> np.ndarray:
    """Linear interpolation of the depth curve Psi at depth ``d`` (edges monotonic in [0,1])."""
    i1 = int(np.clip(np.searchsorted(edges, d, side="right"), 1, len(edges) - 1))
    i0 = i1 - 1
    frac = (d - edges[i0]) / (edges[i1] - edges[i0])
    return psi_edges[i0] + frac * (psi_edges[i1] - psi_edges[i0])


def _check_temperature_domain(chemistry: str, temperature_degc: np.ndarray) -> None:
    """Refuse (NMC) or warn (LFP) when the cubic surrogate is read outside its fitted window.

    The surrogate is a cubic in T fitted over 10-45 degC. Extrapolated below the window the NMC
    cubic turns negative -- -2.0e-5 at 5 degC against a physical +1.6e-5 -- and the
    non-negativity clip in ``_psi_raw`` would then assign *zero* cycle fade to an NMC battery at
    a cool site. That is a wrong answer made silent, so it is refused. LFP degrades gracefully
    (about -11 % at 5 degC, -12 % at 55 degC) and only warns.
    """
    temp = np.asarray(temperature_degc, dtype=float)
    if temp.size == 0:
        return
    lo, hi = CYCLE_TEMPERATURE_WINDOW_C
    outside = (temp < lo) | (temp > hi)
    if not bool(outside.any()):
        return
    share = 100.0 * float(outside.mean())
    detail = (
        f"cell temperature reaches {float(temp.min()):.1f}-{float(temp.max()):.1f} degC and "
        f"{share:.1f} % of hours fall outside the {lo:.0f}-{hi:.0f} degC window in which the "
        "cycle-fade surrogate was fitted"
    )
    if normalize_chemistry(chemistry) == NMC:
        raise InputValidationError(
            f"Battery cycle-fade coefficients are not usable for NMC here: {detail}. The NMC "
            "cubic surrogate turns negative below the window (known defect: Defect 6 of the "
            "degradation audit) and the non-negativity clip would silently assign zero cycle "
            "fade. Lower battery.technical.enclosure_temperature_rise_c, use chemistry LFP, or "
            "restrict the project to sites inside the fitted window."
        )
    warnings.warn(
        f"Battery cycle-fade coefficients extrapolated outside their fitted window: {detail}. "
        "The LFP surrogate is accurate to about 1 % inside 10-45 degC and drifts by roughly "
        "-12 % at the edges; treat lifetimes from this run as indicative.",
        UserWarning,
        stacklevel=3,
    )


def _psi_raw(chemistry: str, dod: float, temperature_degc: np.ndarray) -> np.ndarray:
    """Fitted per-cycle fade Psi(DoD, T), fraction of nameplate, before any calibration."""
    chem = normalize_chemistry(chemistry)
    temp = np.asarray(temperature_degc, dtype=float)
    if temp.size and not np.isfinite(temp).all():
        raise InputValidationError("ambient temperature series contains non-finite values.")
    entry = _load_band_coefficients()["ck_bands"][chem]
    edges = np.asarray(entry["edges"], dtype=float)
    c_fine = np.clip(
        np.stack([_cubic(tuple(p), temp / 10.0) for p in entry["poly"]], axis=0), 0.0, None
    )
    dwidth = np.diff(edges).reshape((-1,) + (1,) * temp.ndim)
    psi_edges = np.concatenate([np.zeros((1,) + temp.shape), np.cumsum(c_fine * dwidth, axis=0)], axis=0)
    return np.clip(_psi_at(edges, psi_edges, float(dod)), 0.0, None)


def cycle_life_scaling(
    chemistry: str,
    user_cycle_life: float | None,
    *,
    usable_soh_budget: float,
    reference_dod: float = DEFAULT_CYCLE_LIFE_REFERENCE_DOD,
    reference_temperature_degc: float = DEFAULT_CYCLE_LIFE_REFERENCE_TEMPERATURE_C,
    cycle_test_duration_years: float | None = None,
    calendar_fade_scale: float = 1.0,
    calendar_mean_soc: float = 0.6,
) -> float:
    """Magnitude factor pinning the fitted Psi shape to the user's rated cycle life.

    Solves ``N_user * Psi_scaled(ref_dod, ref_T) = budget``, i.e. the datasheet promise
    "N_user cycles at ref_dod and ref_T take the cell from SoH0 to SoH_eol" holds exactly.
    Returns 1.0 (raw fitted shape) when no rated cycle life is given.

    ``cycle_test_duration_years`` corrects the double count the datasheet anchor hides: the
    cells in the rating test also age by calendar while the test runs, so pinning the cycle
    channel to the whole budget attributes that calendar ageing to cycling, and the model's own
    calendar channel then counts it again. Supplying the test duration re-pins against
    ``budget - Q_cal(tau_test)`` instead, which makes the coefficient smaller. Left as ``None``
    the behaviour is unchanged, and the cycle channel is knowingly 18-23 % pessimistic for a
    continuous test (about 2x for one cycle per day). Datasheets do not state the duration,
    which is why this is an input and not a constant.
    """
    chem = normalize_chemistry(chemistry)
    if (
        user_cycle_life in (None, "")
        or not np.isfinite(float(user_cycle_life))
        or float(user_cycle_life) <= 0.0
    ):
        return 1.0
    budget = float(usable_soh_budget)
    if not (0.0 < budget <= 1.0):
        raise InputValidationError(
            "battery initial_soh - end_of_life_soh must be within (0, 1] to calibrate cycle fade."
        )
    ref_dod = float(reference_dod)
    if not (0.0 < ref_dod <= 1.0):
        raise InputValidationError("battery cycle_life_reference_dod must be within (0, 1].")

    if cycle_test_duration_years is not None:
        tau = float(cycle_test_duration_years)
        if tau <= 0.0:
            raise InputValidationError(
                "battery cycle_test_duration_years must be > 0 when provided."
            )
        calendar_during_test = float(calendar_fade_scale) * float(
            calendar_fade_fraction(
                chem, calendar_mean_soc, np.array([float(reference_temperature_degc)]), tau
            )[0]
        )
        if calendar_during_test >= budget:
            raise InputValidationError(
                f"battery cycle_test_duration_years: with tau={tau:g} y the rating test's own "
                f"calendar ageing is Q_cal(tau)={calendar_during_test:.4f} of nameplate "
                f"(calendar_fade_scale={float(calendar_fade_scale):g}), which already reaches the "
                f"usable SoH budget B={budget:.4f}. Nothing is left to attribute to cycling, so "
                "the cycle channel cannot be calibrated; check the test duration, "
                "end_of_life_soh and calendar_fade_scale."
            )
        budget = budget - calendar_during_test

    fade_per_reference_cycle = float(
        _psi_raw(chem, ref_dod, np.array([float(reference_temperature_degc)]))[0]
    )
    if fade_per_reference_cycle <= 0.0:
        return 1.0
    return budget / (float(user_cycle_life) * fade_per_reference_cycle)


def cycle_calibration_summary(
    chemistry: str,
    user_cycle_life: float | None,
    *,
    usable_soh_budget: float,
    reference_dod: float = DEFAULT_CYCLE_LIFE_REFERENCE_DOD,
    reference_temperature_degc: float = DEFAULT_CYCLE_LIFE_REFERENCE_TEMPERATURE_C,
    cycle_test_duration_years: float | None = None,
    calendar_fade_scale: float = 1.0,
    calendar_mean_soc: float = 0.6,
) -> dict[str, float]:
    """The datasheet calibration in three numbers, for traceability.

    ``lambda_cyc``               magnitude factor applied to the fitted Psi shape
    ``c_at_tref``                c at the datasheet point (reference depth and temperature)
    ``test_time_calendar_fade``  calendar ageing inside the rating test, phi * Q_cal(tau);
                                 0 when the test duration is not given

    By construction N_rated * reference_dod * c_at_tref + test_time_calendar_fade equals the
    usable SoH budget: replaying the datasheet test consumes exactly B.
    """
    chem = normalize_chemistry(chemistry)
    lambda_cyc = cycle_life_scaling(
        chem,
        user_cycle_life,
        usable_soh_budget=usable_soh_budget,
        reference_dod=reference_dod,
        reference_temperature_degc=reference_temperature_degc,
        cycle_test_duration_years=cycle_test_duration_years,
        calendar_fade_scale=calendar_fade_scale,
        calendar_mean_soc=calendar_mean_soc,
    )
    t_ref = np.array([float(reference_temperature_degc)])
    c_at_tref = float(_psi_raw(chem, float(reference_dod), t_ref)[0]) / float(reference_dod) * lambda_cyc
    test_calendar = (
        0.0
        if cycle_test_duration_years is None
        else float(calendar_fade_scale)
        * float(calendar_fade_fraction(chem, calendar_mean_soc, t_ref, float(cycle_test_duration_years))[0])
    )
    return {
        "lambda_cyc": float(lambda_cyc),
        "c_at_tref": c_at_tref,
        "test_time_calendar_fade": test_calendar,
    }


def cycle_fade_coefficient(
    *,
    chemistry: str,
    depth_of_discharge: float,
    temperature_degc: np.ndarray,
    user_cycle_life: float | None = None,
    usable_soh_budget: float = 0.2,
    reference_dod: float = DEFAULT_CYCLE_LIFE_REFERENCE_DOD,
    reference_temperature_degc: float = DEFAULT_CYCLE_LIFE_REFERENCE_TEMPERATURE_C,
    cycle_test_duration_years: float | None = None,
    calendar_fade_scale: float = 1.0,
    calendar_mean_soc: float | None = None,
) -> dict[str, Any]:
    """Marginal cycle-fade cost ``c(T)``, shaped like ``temperature_degc``.

    Units: fraction of nameplate capacity lost per unit of depth-fraction traversed, i.e. ``c``
    times kWh of DC discharge gives kWh of capacity lost -- independent of nameplate, which is
    what keeps the fade definition linear.

    ``temperature_degc`` is CELL temperature (outdoor air plus the enclosure rise), not ambient:
    the distillation already contains cell self-heating and the pack-to-air offset, so the
    correct input is the air temperature around the pack.
    """
    chem = normalize_chemistry(chemistry)
    dod = float(depth_of_discharge)
    if not (0.0 < dod <= 1.0):
        raise InputValidationError("battery depth_of_discharge must be within (0, 1].")
    temp = np.asarray(temperature_degc, dtype=float)
    if temp.size and not np.isfinite(temp).all():
        raise InputValidationError("ambient temperature series contains non-finite values.")
    if chem == NMC:
        warnings.warn(
            "Battery chemistry NMC inherits two known defects of the distilled cycle-fade "
            "coefficients: the LFP-datasheet temperature correction was applied to NMC as well, "
            "giving an implied activation energy of about 70 kJ/mol against a published ~50 "
            "(23x against 10.5x over 10-45 degC), and the cubic surrogate misfits the steep NMC "
            "law by up to 14 % inside its own fitted window. Read NMC results as the pessimistic "
            "end of the band; LFP is the calibrated chemistry.",
            UserWarning,
            stacklevel=2,
        )
    _check_temperature_domain(chem, temp)
    scaling = cycle_life_scaling(
        chem,
        user_cycle_life,
        usable_soh_budget=usable_soh_budget,
        reference_dod=reference_dod,
        reference_temperature_degc=reference_temperature_degc,
        cycle_test_duration_years=cycle_test_duration_years,
        calendar_fade_scale=calendar_fade_scale,
        calendar_mean_soc=(1.0 - dod / 2.0) if calendar_mean_soc is None else float(calendar_mean_soc),
    )
    return {
        "c": _psi_raw(chem, dod, temp) / dod * scaling,
        "chemistry": chem,
        "cycle_life_scaling": scaling,
    }


# ===========================================================================
# Input-visualisation preview
# ===========================================================================


def coefficient_curve_preview(
    *,
    chemistry: str,
    depth_of_discharge: float,
    user_cycle_life: float | None = None,
    usable_soh_budget: float = 0.2,
    reference_dod: float = DEFAULT_CYCLE_LIFE_REFERENCE_DOD,
    reference_temperature_degc: float = DEFAULT_CYCLE_LIFE_REFERENCE_TEMPERATURE_C,
    calendar_reference_years: float = 10.0,
    calendar_fade_scale: float = 1.0,
    temp_min: float = 10.0,
    temp_max: float = 50.0,
    n_points: int = 41,
) -> dict[str, np.ndarray]:
    """Both coefficient curves on a dense CELL-temperature grid, for the input preview.

    ``cycle_fade_coefficient`` is per kWh discharged; ``calendar_rate_per_year`` is per kWh
    of nameplate per year and depends on the horizon it is linearised over, so the preview
    states its own ``calendar_reference_years``.
    """
    grid = np.linspace(float(temp_min), float(temp_max), int(n_points))
    soc_mean = 1.0 - float(depth_of_discharge) / 2.0
    with warnings.catch_warnings():
        # A preview deliberately spans the edges of the fitted window; the warning belongs
        # on a real run, not on a plot the user asked for.
        warnings.simplefilter("ignore")
        cycle = cycle_fade_coefficient(
            chemistry=chemistry,
            depth_of_discharge=depth_of_discharge,
            temperature_degc=grid,
            user_cycle_life=user_cycle_life,
            usable_soh_budget=usable_soh_budget,
            reference_dod=reference_dod,
            reference_temperature_degc=reference_temperature_degc,
        )["c"]
    calendar = calendar_rate_per_year(
        chemistry,
        soc_mean,
        grid,
        reference_years=calendar_reference_years,
        scale=calendar_fade_scale,
    )
    return {
        "temperature_degc": grid,
        "cycle_fade_coefficient": cycle,
        "calendar_rate_per_year": calendar,
        "calendar_reference_years": float(calendar_reference_years),
        "calendar_mean_soc": float(soc_mean),
    }
