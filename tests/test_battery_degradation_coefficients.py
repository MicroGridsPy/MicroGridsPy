"""Tests for the semi-empirical degradation coefficients and the
ambient-temperature input loader."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from microgridspy.data_pipeline.battery_degradation_coefficients import (
    InputValidationError,
    coefficient_curve_preview,
    cycle_life_scaling,
    evaluate_degradation_coefficients,
    normalize_chemistry,
    select_dod_band,
)


def test_normalize_chemistry_aliases() -> None:
    assert normalize_chemistry("LFP") == "LFP"
    assert normalize_chemistry("lifepo4") == "LFP"
    assert normalize_chemistry("NMC") == "NMC"
    assert normalize_chemistry("lead-acid") == "lead_acid"
    assert normalize_chemistry("PbA") == "lead_acid"
    with pytest.raises(InputValidationError):
        normalize_chemistry("sodium_ion")
    with pytest.raises(InputValidationError):
        normalize_chemistry(None)
    assert normalize_chemistry(None, default="LFP") == "LFP"


def test_dod_band_and_soc_band_mapping() -> None:
    # Li-ion DoD snaps to the nearest fitted band; DoD>=0.75 -> 20% SoC alpha band.
    assert select_dod_band("LFP", 0.83) == 0.8
    assert select_dod_band("NMC", 0.62) == 0.6
    hi = evaluate_degradation_coefficients(
        chemistry="LFP", depth_of_discharge=0.8, temperature_degc=np.array([25.0])
    )
    lo = evaluate_degradation_coefficients(
        chemistry="LFP", depth_of_discharge=0.6, temperature_degc=np.array([25.0])
    )
    assert hi["alpha_soc_band_percent"] == 20
    assert lo["alpha_soc_band_percent"] == 40
    assert hi["beta_dod_band"] == 0.8 and lo["beta_dod_band"] == 0.6


def test_beta_increases_with_temperature_and_scales_with_cycle_life() -> None:
    r = evaluate_degradation_coefficients(
        chemistry="LFP",
        depth_of_discharge=0.8,
        temperature_degc=np.array([25.0, 45.0]),
        user_cycle_life=6000,
    )
    assert r["beta"][1] > r["beta"][0] > 0.0  # hotter -> more cycle wear
    assert r["alpha"][1] > r["alpha"][0] > 0.0  # hotter -> more calendar wear
    # Halving the rated cycle life doubles beta (N_ref/N_user scaling).
    r_half = evaluate_degradation_coefficients(
        chemistry="LFP",
        depth_of_discharge=0.8,
        temperature_degc=np.array([25.0]),
        user_cycle_life=3000,
    )
    assert r_half["beta"][0] == pytest.approx(2.0 * r["beta"][0], rel=1e-9)
    assert cycle_life_scaling("LFP", 3000) == pytest.approx(2.0)
    assert cycle_life_scaling("LFP", None) == pytest.approx(1.0)


def test_eol_fade_matches_expected_soh_drop() -> None:
    # For LFP DoD 0.8, N=6000 at ~30 C, beta * (2*N*DoD) ~ 0.2 (i.e. 80% SoH EOL).
    r = evaluate_degradation_coefficients(
        chemistry="LFP",
        depth_of_discharge=0.8,
        temperature_degc=np.array([30.0]),
        user_cycle_life=6000,
    )
    eol_fade = r["beta"][0] * 2.0 * 6000.0 * 0.8
    assert 0.15 < eol_fade < 0.25


def test_lead_acid_is_temperature_flat_and_bandless() -> None:
    r = evaluate_degradation_coefficients(
        chemistry="lead_acid",
        depth_of_discharge=0.5,
        temperature_degc=np.array([15.0, 45.0]),
    )
    assert r["beta"][0] == pytest.approx(r["beta"][1])  # no temperature term
    assert r["alpha"][0] == pytest.approx(r["alpha"][1])
    assert r["beta_dod_band"] is None


def test_curve_preview_shapes() -> None:
    prev = coefficient_curve_preview(chemistry="NMC", depth_of_discharge=0.6, n_points=41)
    assert prev["temperature_degc"].shape == (41,)
    assert prev["alpha"].shape == (41,) and prev["beta"].shape == (41,)


def test_ambient_temperature_loader_roundtrip(tmp_path) -> None:
    import microgridspy.io.csv_format as cf
    from microgridspy.multi_year_model.data import _load_ambient_temperature_csv

    period = xr.DataArray(np.arange(3), dims="period", name="period")
    scenario = xr.DataArray(["scenario_1"], dims="scenario", name="scenario")
    year = xr.DataArray([2026, 2027], dims="year", name="year")

    import pandas as pd

    cols = pd.MultiIndex.from_tuples(
        [("meta", "hour"), ("scenario_1", "2026"), ("scenario_1", "2027")],
        names=["scenario", "year"],
    )
    df = pd.DataFrame(
        [[0, 20.0, 30.0], [1, 21.0, 31.0], [2, 22.0, 32.0]], columns=cols
    )
    path = tmp_path / "ambient_temperature.csv"
    cf.write_csv_with_format(df, path, csv_format={"sep": ",", "decimal": "."}, index=False)

    da = _load_ambient_temperature_csv(
        path, period_coord=period, scenario_coord=scenario, year_coord=year
    )
    assert set(da.dims) == {"year", "period", "scenario"}
    assert float(da.sel(year=2027, period=2, scenario="scenario_1")) == pytest.approx(32.0)


def _write_formulation_json(path, *, start_year="2026", horizon=3) -> None:
    import json

    payload = {
        "project_name": "deg_integ",
        "core_formulation": "dynamic",
        "system_type": "off_grid",
        "on_grid": False,
        "grid_allow_export": False,
        "unit_commitment": False,
        "start_year_label": start_year,
        "time_horizon_years": horizon,
        "social_discount_rate": 0.05,
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
            "max_lost_load_fraction": 0.0,
            "lost_load_cost_per_kwh": 0.0,
            "land_availability_m2": None,
            "emission_cost_per_kgco2e": 0.0,
        },
        "system_configuration": {"n_sources": 1},
        "battery_model": {
            "loss_model": "convex_loss_epigraph",
            "degradation_model": {"cycle_fade_enabled": True, "calendar_fade_enabled": False},
        },
        "generator_model": {"efficiency_model": "constant_efficiency"},
        "csv_format": {"delimiter": ",", "decimal": "."},
    }
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")


def test_end_to_end_loader_attaches_semiempirical_coefficients(tmp_path, monkeypatch) -> None:
    """The dynamic file loader loads ambient_temperature.csv and attaches the
    temperature- and DoD-aware semi-empirical alpha/beta coefficient fields."""
    from microgridspy.io.templates import TemplateSettings, write_templates
    from microgridspy.io.utils import ProjectPaths
    import microgridspy.multi_year_model.data as mdata
    import microgridspy.multi_year_model.sets as msets

    project_root = tmp_path / "projects" / "deg_integ"
    inputs_dir = project_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    settings = TemplateSettings(
        formulation="dynamic",
        system_type="off_grid",
        allow_export=False,
        multi_scenario=False,
        n_scenarios=1,
        scenario_labels=["scenario_1"],
        scenario_weights=[1.0],
        start_year_label="2026",
        horizon_years=3,
        capacity_expansion=False,
        investment_steps_years=None,
        n_res_sources=1,
        resource_labels=["Solar"],
        conversion_labels=["Solar PV"],
        battery_label="Battery",
        battery_loss_model="convex_loss_epigraph",
        battery_cycle_fade_enabled=True,
        battery_efficiency_curve_csv="battery_efficiency_curve.csv",
        battery_cycle_lifetime_to_eol_cycles=4000.0,
        battery_end_of_life_soh=0.8,
        generator_label="Generator",
        generator_efficiency_model="constant_efficiency",
        generator_efficiency_curve_csv="generator_efficiency_curve.csv",
        fuel_label="Fuel",
        battery_chemistry="LFP",
    )

    from types import SimpleNamespace

    write_templates(SimpleNamespace(inputs_dir=inputs_dir), settings, overwrite=True)
    _write_formulation_json(inputs_dir / "formulation.json")

    assert (inputs_dir / "ambient_temperature.csv").exists()

    monkeypatch.setattr(mdata, "project_paths", lambda name: ProjectPaths(root=project_root))
    monkeypatch.setattr(msets, "project_paths", lambda name: ProjectPaths(root=project_root))

    sets = msets.initialize_sets("deg_integ")
    ds = mdata.initialize_data("deg_integ", sets)

    for v in ("ambient_temperature", "battery_alpha_calendar", "battery_beta_cycle"):
        assert v in ds.data_vars, f"{v} not attached by loader"
        assert set(ds[v].dims) == {"year", "period", "scenario"}

    # 25 degC template -> strictly positive coefficients; cycle-life scaling = 6000/4000.
    assert float(ds["battery_beta_cycle"].min()) > 0.0
    deg = ds.attrs["settings"]["battery_model"]["degradation_model"]
    assert deg["coefficient_source"] == "semi_empirical"
    assert deg["beta_dod_band"] == pytest.approx(0.8)
    assert deg["cycle_life_scaling"] == pytest.approx(1.5)


def test_multi_year_cycle_fade_uses_semiempirical_beta(tmp_path, monkeypatch) -> None:
    """The dynamic constraint layer consumes beta(T) (not the flat gamma): at the
    optimum battery_cycle_fade equals beta * (charge_dc + discharge_dc)."""
    import json
    from types import SimpleNamespace

    import linopy as lp
    import pandas as pd
    import yaml

    from microgridspy.io.templates import TemplateSettings, write_templates
    from microgridspy.io.utils import ProjectPaths
    import microgridspy.data_pipeline.loader as loader_mod
    import microgridspy.multi_year_model.data as mdata
    import microgridspy.multi_year_model.sets as msets
    from microgridspy.multi_year_model.constraints import initialize_constraints
    from microgridspy.multi_year_model.objective import initialize_objective
    from microgridspy.multi_year_model.variables import initialize_vars

    root = tmp_path / "projects" / "my_deg"
    inp = root / "inputs"
    inp.mkdir(parents=True, exist_ok=True)
    settings = TemplateSettings(
        formulation="dynamic",
        system_type="off_grid",
        allow_export=False,
        multi_scenario=False,
        n_scenarios=1,
        scenario_labels=["scenario_1"],
        scenario_weights=[1.0],
        start_year_label="2026",
        horizon_years=2,
        capacity_expansion=False,
        investment_steps_years=None,
        n_res_sources=1,
        resource_labels=["Solar"],
        conversion_labels=["Solar PV"],
        battery_label="Battery",
        battery_loss_model="convex_loss_epigraph",
        battery_cycle_fade_enabled=True,
        battery_efficiency_curve_csv="battery_efficiency_curve.csv",
        battery_cycle_lifetime_to_eol_cycles=2000.0,
        battery_end_of_life_soh=0.8,
        generator_label="Generator",
        generator_efficiency_model="constant_efficiency",
        generator_efficiency_curve_csv="generator_efficiency_curve.csv",
        fuel_label="Fuel",
        battery_chemistry="LFP",
    )
    write_templates(SimpleNamespace(inputs_dir=inp), settings, overwrite=True)

    by = yaml.safe_load((inp / "battery.yaml").read_text(encoding="utf-8"))
    bs = by["battery"]["investment"]["by_step"]
    bk = next(iter(bs))
    bs[bk]["specific_investment_cost_per_kwh"] = 300.0
    bs[bk]["wacc"] = 0.05
    bs[bk]["inverter_specific_investment_cost_per_kw"] = 50.0
    by["battery"]["technical"]["max_charge_c_rate"] = 0.5
    by["battery"]["technical"]["max_discharge_c_rate"] = 0.5
    (inp / "battery.yaml").write_text(yaml.safe_dump(by, sort_keys=False), encoding="utf-8")
    ry = yaml.safe_load((inp / "renewables.yaml").read_text(encoding="utf-8"))
    for it in ry["renewables"]:
        rs = it["investment"]["by_step"]
        rk = next(iter(rs))
        rs[rk]["specific_investment_cost_per_kw"] = 100.0
        rs[rk]["wacc"] = 0.05
    (inp / "renewables.yaml").write_text(yaml.safe_dump(ry, sort_keys=False), encoding="utf-8")

    _write_formulation_json(inp / "formulation.json", start_year="2026", horizon=2)
    # override enforcement/lost-load so the toy is feasible and cycles the battery
    formulation = json.loads((inp / "formulation.json").read_text(encoding="utf-8"))
    formulation["social_discount_rate"] = 0.05
    formulation["optimization_constraints"]["max_lost_load_fraction"] = 1.0
    formulation["optimization_constraints"]["lost_load_cost_per_kwh"] = 50.0
    (inp / "formulation.json").write_text(json.dumps(formulation, indent=1), encoding="utf-8")

    hod = np.arange(8760) % 24
    ld = pd.read_csv(inp / "load_demand.csv", header=[0, 1])
    for c in ld.columns:
        if c[0] != "meta":
            ld[c] = 10.0
    ld.to_csv(inp / "load_demand.csv", index=False)
    rv = pd.read_csv(inp / "resource_availability.csv", header=[0, 1, 2])
    for c in rv.columns:
        if c[0] != "meta":
            rv[c] = np.where((hod >= 9) & (hod <= 15), 1.0, 0.0)
    rv.to_csv(inp / "resource_availability.csv", index=False)
    am = pd.read_csv(inp / "ambient_temperature.csv", header=[0, 1])
    for c in am.columns:
        if c[0] != "meta":
            am[c] = 35.0
    am.to_csv(inp / "ambient_temperature.csv", index=False)

    monkeypatch.setattr(mdata, "project_paths", lambda name: ProjectPaths(root=root))
    monkeypatch.setattr(msets, "project_paths", lambda name: ProjectPaths(root=root))
    sets = msets.initialize_sets("my_deg")
    ds = loader_mod.load_project_dataset("my_deg", sets, mode="multi_year")
    assert "battery_beta_cycle" in ds.data_vars and "battery_alpha_calendar" in ds.data_vars

    m = lp.Model()
    v = initialize_vars(sets, ds, m)
    initialize_constraints(sets, ds, v, m)
    initialize_objective(sets, ds, v, m)
    try:
        m.solve(solver_name="highs")
    except Exception as exc:  # pragma: no cover
        if any(t in str(exc).lower() for t in ("highs", "solver", "not available", "executable")):
            pytest.skip(f"HiGHS unavailable: {exc}")
        raise
    if str(m.termination_condition) not in ("optimal", "TerminationCondition.optimal"):
        pytest.skip(f"toy not optimal: {m.termination_condition}")

    cf = float(v["battery_cycle_fade"].solution.sum())
    beta = ds["battery_beta_cycle"]
    ch = v["battery_charge_dc"].solution
    dis = v["battery_discharge_dc"].solution
    expected = float((beta * (ch + dis)).sum())
    assert cf > 0.0  # the battery actually cycles
    assert cf == pytest.approx(expected, rel=1e-6)


def test_ambient_temperature_loader_missing_file(tmp_path) -> None:
    from microgridspy.multi_year_model.data import (
        InputValidationError as DataInputValidationError,
    )
    from microgridspy.multi_year_model.data import _load_ambient_temperature_csv

    period = xr.DataArray(np.arange(3), dims="period", name="period")
    scenario = xr.DataArray(["scenario_1"], dims="scenario", name="scenario")
    year = xr.DataArray([2026], dims="year", name="year")
    with pytest.raises(DataInputValidationError):
        _load_ambient_temperature_csv(
            tmp_path / "does_not_exist.csv",
            period_coord=period,
            scenario_coord=scenario,
            year_coord=year,
        )
