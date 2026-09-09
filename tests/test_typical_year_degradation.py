"""Typical-year (steady_state) battery cycle-fade as a throughput WEAR COST (no state).

The semi-empirical cycle coefficient beta(T) is loaded from ambient_temperature.csv
and charged in the objective as a marginal wear cost per unit of throughput. There is
no capacity state and no new decision variables.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

linopy = pytest.importorskip("linopy")


def _build_project(
    root: Path, *, cycle_fade: bool, lost_load_cost: float, cyclelife: float = 2000.0
) -> None:
    import yaml

    from microgridspy.io.templates import TemplateSettings, write_templates

    inp = root / "inputs"
    inp.mkdir(parents=True, exist_ok=True)
    settings = TemplateSettings(
        formulation="steady_state",
        system_type="off_grid",
        allow_export=False,
        multi_scenario=False,
        n_scenarios=1,
        scenario_labels=["scenario_1"],
        scenario_weights=[1.0],
        start_year_label="typical_year",
        horizon_years=None,
        capacity_expansion=False,
        investment_steps_years=None,
        n_res_sources=1,
        resource_labels=["Solar"],
        conversion_labels=["Solar PV"],
        battery_label="Battery",
        battery_loss_model="constant_efficiency",
        battery_cycle_fade_enabled=cycle_fade,
        battery_efficiency_curve_csv="battery_efficiency_curve.csv",
        battery_cycle_lifetime_to_eol_cycles=cyclelife,
        battery_end_of_life_soh=0.8,
        generator_label="Generator",
        generator_efficiency_model="constant_efficiency",
        generator_efficiency_curve_csv="generator_efficiency_curve.csv",
        fuel_label="Fuel",
        battery_chemistry="LFP",
    )
    write_templates(SimpleNamespace(inputs_dir=inp), settings, overwrite=True)

    # Real battery/PV costs so the wear-cost marginal (capex/(SoH0-SoHeol)) is nonzero.
    by = yaml.safe_load((inp / "battery.yaml").read_text(encoding="utf-8"))
    bstep = by["battery"]["investment"]["by_step"]
    bkey = next(iter(bstep))
    bstep[bkey]["specific_investment_cost_per_kwh"] = 300.0
    bstep[bkey]["wacc"] = 0.05
    bstep[bkey]["inverter_specific_investment_cost_per_kw"] = 50.0
    by["battery"]["technical"]["max_charge_c_rate"] = 0.5
    by["battery"]["technical"]["max_discharge_c_rate"] = 0.5
    (inp / "battery.yaml").write_text(yaml.safe_dump(by, sort_keys=False), encoding="utf-8")

    ry = yaml.safe_load((inp / "renewables.yaml").read_text(encoding="utf-8"))
    for it in ry["renewables"]:
        rstep = it["investment"]["by_step"]
        rkey = next(iter(rstep))
        rstep[rkey]["specific_investment_cost_per_kw"] = 100.0
        rstep[rkey]["wacc"] = 0.05
    (inp / "renewables.yaml").write_text(yaml.safe_dump(ry, sort_keys=False), encoding="utf-8")

    formulation = {
        "project_name": "ty_deg",
        "core_formulation": "steady_state",
        "system_type": "off_grid",
        "on_grid": False,
        "grid_allow_export": False,
        "unit_commitment": False,
        "start_year_label": "typical_year",
        "time_horizon_years": None,
        "social_discount_rate": None,
        "capacity_expansion": False,
        "investment_steps_years": None,
        "multi_scenario": {
            "enabled": False,
            "n_scenarios": 1,
            "scenario_labels": ["scenario_1"],
            "scenario_weights": [1.0],
        },
        "optimization_constraints": {
            "enforcement": "scenario_wise",
            "min_renewable_penetration": 0.0,
            "max_lost_load_fraction": 1.0,
            "lost_load_cost_per_kwh": lost_load_cost,
            "land_availability_m2": None,
            "emission_cost_per_kgco2e": 0.0,
        },
        "system_configuration": {"n_sources": 1},
        "battery_model": {
            "loss_model": "constant_efficiency",
            "degradation_model": {
                "cycle_fade_enabled": cycle_fade,
                "calendar_fade_enabled": False,
            },
        },
        "generator_model": {"efficiency_model": "constant_efficiency"},
        "csv_format": {"delimiter": ",", "decimal": "."},
    }
    (inp / "formulation.json").write_text(json.dumps(formulation, indent=1), encoding="utf-8")

    # Constant 10 kWh/h load, PV only midday -> battery must time-shift energy.
    hod = np.arange(8760) % 24
    load = pd.read_csv(inp / "load_demand.csv", header=[0, 1])
    load[("scenario_1", "typical_year")] = 10.0
    load.to_csv(inp / "load_demand.csv", index=False)
    res = pd.read_csv(inp / "resource_availability.csv", header=[0, 1, 2])
    res[("scenario_1", "typical_year", "Solar")] = np.where((hod >= 9) & (hod <= 15), 1.0, 0.0)
    res.to_csv(inp / "resource_availability.csv", index=False)
    if cycle_fade:
        amb = pd.read_csv(inp / "ambient_temperature.csv", header=[0, 1])
        amb[("scenario_1", "typical_year")] = 35.0  # hot -> higher beta
        amb.to_csv(inp / "ambient_temperature.csv", index=False)


def _solve(root: Path, monkeypatch):
    import linopy as lp

    import microgridspy.data_pipeline.loader as loader_mod
    import microgridspy.data_pipeline.typical_year_loader as tyl
    import microgridspy.typical_year_model.sets as tysets
    from microgridspy.io.utils import ProjectPaths
    from microgridspy.typical_year_model.constraints import initialize_constraints
    from microgridspy.typical_year_model.objective import initialize_objective
    from microgridspy.typical_year_model.variables import initialize_vars

    monkeypatch.setattr(tysets, "project_paths", lambda name: ProjectPaths(root=root))
    monkeypatch.setattr(tyl, "project_paths", lambda name: ProjectPaths(root=root))

    sets = tysets.initialize_sets("ty_deg")
    ds = loader_mod.load_project_dataset("ty_deg", sets, mode="typical_year")
    model = lp.Model()
    v = initialize_vars(sets, ds, model)
    initialize_constraints(sets, ds, v, model)
    initialize_objective(sets, ds, v, model)
    try:
        model.solve(solver_name="highs")
    except Exception as exc:  # pragma: no cover - environment dependent
        if any(t in str(exc).lower() for t in ("highs", "solver", "not available", "executable")):
            pytest.skip(f"HiGHS unavailable: {exc}")
        raise
    if str(model.termination_condition) not in ("optimal", "TerminationCondition.optimal"):
        pytest.skip(f"toy model not optimal: {model.termination_condition}")
    throughput = float((v["battery_charge"] + v["battery_discharge"]).sum().solution)
    return ds, float(model.objective.value), throughput, model, v


def _crf(r: float, n: float) -> float:
    return (r * (1 + r) ** n) / ((1 + r) ** n - 1) if r > 0 else 1.0 / n


def _annuities(ds, v):
    """Return (Z, calendar_annuity, cycle_annuity) for scenario_1 at the solution."""
    z = float(v["battery_replacement_cost"].solution.sel(scenario="scenario_1"))
    cap = float((v["battery_units"] * ds["battery_nominal_capacity_kwh"]).solution)
    capex, wacc, cal = 300.0, 0.05, 10.0
    cal_ann = _crf(wacc, cal) * capex * cap
    c_repl, phi = capex / (1.0 - 0.8), _crf(wacc, cal) * cal
    fade = float(
        (ds["battery_beta_cycle"] * (v["battery_charge"] + v["battery_discharge"]).solution).sum()
    )
    return z, cal_ann, c_repl * phi * fade


def test_typical_year_replacement_cost_is_max_of_annuities(tmp_path, monkeypatch) -> None:
    # The battery energy CAPEX is amortized over the binding life via a max-of-annuities
    # epigraph. With a long rated life (gentle cycling) the CALENDAR limit binds, so the
    # charged cost equals the calendar annuity and NPC stays flat vs no degradation.
    root_off = tmp_path / "off"
    _build_project(root_off, cycle_fade=False, lost_load_cost=50.0)
    ds_off, obj_off, _, _, _ = _solve(root_off, monkeypatch)
    assert "battery_beta_cycle" not in ds_off.data_vars

    root_on = tmp_path / "on"
    _build_project(root_on, cycle_fade=True, lost_load_cost=50.0, cyclelife=6000.0)
    ds_on, obj_on, _, _, v_on = _solve(root_on, monkeypatch)

    assert "battery_beta_cycle" in ds_on.data_vars
    assert "battery_replacement_cost" in v_on
    deg = ds_on.attrs["settings"]["battery_model"]["degradation_model"]
    assert deg["coefficient_source"] == "semi_empirical"
    assert deg["cycle_fade_mode"] == "binding_life_annuity"

    z, cal_ann, cyc_ann = _annuities(ds_on, v_on)
    # epigraph identity: Z == max(calendar, cycle) annuity
    assert z == pytest.approx(max(cal_ann, cyc_ann), rel=1e-3)
    # gentle cycling -> calendar limit binds
    assert cal_ann >= cyc_ann - 1e-6
    # and NPC is essentially flat vs no degradation (only the convex-loss efficiency diff)
    assert obj_on == pytest.approx(obj_off, rel=0.05)


def test_typical_year_shorter_cycle_life_is_never_cheaper(tmp_path, monkeypatch) -> None:
    # For any fixed decision the cycle annuity is higher when the rated life is shorter,
    # so the optimal NPC is monotonic: a shorter cycle life is never cheaper. When the
    # cycle limit binds the charged cost is the (larger) cycle annuity.
    root_long = tmp_path / "long"
    _build_project(root_long, cycle_fade=True, lost_load_cost=50.0, cyclelife=6000.0)
    _, obj_long, _, _, _ = _solve(root_long, monkeypatch)

    root_short = tmp_path / "short"
    _build_project(root_short, cycle_fade=True, lost_load_cost=50.0, cyclelife=800.0)
    ds_short, obj_short, _, _, v_short = _solve(root_short, monkeypatch)

    z, cal_ann, cyc_ann = _annuities(ds_short, v_short)
    assert z == pytest.approx(max(cal_ann, cyc_ann), rel=1e-3)
    assert obj_short >= obj_long - 1e-6
