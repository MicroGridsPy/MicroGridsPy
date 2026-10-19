"""Battery degradation is refused in the typical-year formulation.

A typical year has no year axis, so capacity fade cannot accumulate: the state cannot
decline, the end-of-life floor has nothing to bind in, and no replacement schedule can be
expressed. What used to live here was a binding-life CAPEX amortisation -- a max-of-annuities
epigraph over min(calendar, cycle-limited) life -- which priced ageing without modelling it
and inherited the pre-audit coefficient defects. Its calendar branch bound in every case
tested, which made the cycle branch, and so the whole mechanism, inert.

Rather than maintain a second degradation scheme whose numbers cannot be reconciled with the
multi-year one, a typical-year project asking for degradation is now refused. Sizing without
ageing is unaffected, which is what the last test here checks.
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
        formulation="typical_year",
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
        battery_semiempirical_degradation_enabled=cycle_fade,
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
        "core_formulation": "typical_year",
        "system_type": "off_grid",
        "on_grid": False,
        "grid_allow_export": False,
        "integer_sizing": False,
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
                "coefficients_enabled": cycle_fade,
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
    # The templates no longer write a temperature series for typical-year projects, because
    # the mode that would consume it is refused there.
    if (inp / "ambient_temperature.csv").exists():
        amb = pd.read_csv(inp / "ambient_temperature.csv", header=[0, 1])
        amb[("scenario_1", "typical_year")] = 35.0
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


def test_typical_year_degradation_is_refused(tmp_path, monkeypatch) -> None:
    """Semi-empirical degradation in a typical-year project is refused at load time, and the
    message names the flag that was set and the formulation that supports it."""
    from microgridspy.errors import InputValidationError

    root = tmp_path / "degradation_on"
    _build_project(root, cycle_fade=True, lost_load_cost=50.0, cyclelife=6000.0)
    with pytest.raises(InputValidationError) as exc:
        _solve(root, monkeypatch)
    message = str(exc.value)
    assert "multi-year" in message
    assert "coefficients_enabled" in message


def test_typical_year_without_degradation_still_solves(tmp_path, monkeypatch) -> None:
    """The refusal must not cost the typical-year formulation its ordinary sizing path.

    With the flags off the model solves, the battery is used to time-shift midday PV into the
    night, and no degradation artefacts are left in the dataset or the variable set.
    """
    root = tmp_path / "off"
    _build_project(root, cycle_fade=False, lost_load_cost=50.0)
    ds, objective, throughput, _, v = _solve(root, monkeypatch)

    assert objective > 0.0
    assert throughput > 0.0  # the battery is actually cycling
    assert "battery_beta_cycle" not in ds.data_vars
    assert "ambient_temperature" not in ds.data_vars
    assert "battery_replacement_cost" not in v
    degradation = ds.attrs["settings"]["battery_model"]["degradation_model"]
    assert degradation["cycle_fade_enabled"] is False
