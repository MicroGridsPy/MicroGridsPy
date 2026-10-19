"""Phase C acceptance tests: input assembly, cell temperature, derived service life, guards.

These exercise the multi-year loader end to end on a tiny generated project, which is the
only place the coefficient layer, the battery.yaml inputs and the temperature series meet.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import xarray as xr

from microgridspy.data_pipeline.battery_degradation_coefficients import (
    coefficient_curve_preview,
)
from microgridspy.errors import InputValidationError

AMBIENT_C = 25.0  # the template writes a flat 25 degC series


def _settings(**overrides):
    from microgridspy.io.templates import TemplateSettings

    base = dict(
        formulation="multi_year",
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
        battery_semiempirical_degradation_enabled=True,
        battery_efficiency_curve_csv="battery_efficiency_curve.csv",
        battery_cycle_lifetime_to_eol_cycles=6000.0,
        battery_end_of_life_soh=0.8,
        generator_label="Generator",
        generator_efficiency_model="constant_efficiency",
        generator_efficiency_curve_csv="generator_efficiency_curve.csv",
        fuel_label="Fuel",
        battery_chemistry="LFP",
    )
    base.update(overrides)
    return TemplateSettings(**base)


def _formulation(coefficients_enabled=True, loss_model="convex_loss_epigraph", **degradation):
    payload = {
        "project_name": "deg_integ",
        "core_formulation": "multi_year",
        "system_type": "off_grid",
        "on_grid": False,
        "grid_allow_export": False,
        "integer_sizing": False,
        "start_year_label": "2026",
        "time_horizon_years": 3,
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
            "loss_model": loss_model,
            "degradation_model": {
                "coefficients_enabled": coefficients_enabled,
                "end_of_life_soh": 0.8,
                "cycle_lifetime_to_eol_cycles": 6000,
                **degradation,
            },
        },
        "generator_model": {"efficiency_model": "constant_efficiency"},
        "csv_format": {"delimiter": ",", "decimal": "."},
    }
    return payload


def _write_profiles(inputs: Path) -> None:
    """Give the project a profile the dark-hour estimator can actually read.

    The templates ship zeros, which is a degenerate case the estimator deliberately refuses:
    with no demand outside daylight there is no battery cycling to infer. A constant load
    with midday-only PV is the off-grid shape the estimator assumes -- the battery carries
    every night.
    """
    import pandas as pd

    hour_of_day = np.arange(8760) % 24

    load = pd.read_csv(inputs / "load_demand.csv", header=[0, 1])
    for column in load.columns[1:]:
        load[column] = 10.0
    load.to_csv(inputs / "load_demand.csv", index=False)

    availability = pd.read_csv(inputs / "resource_availability.csv", header=[0, 1, 2])
    for column in availability.columns[1:]:
        availability[column] = np.where((hour_of_day >= 9) & (hour_of_day <= 15), 1.0, 0.0)
    availability.to_csv(inputs / "resource_availability.csv", index=False)


def _build(tmp_path, monkeypatch, *, settings=None, formulation=None, technical=None, life="null"):
    """Write a tiny multi-year project and return its loaded dataset."""
    import yaml

    import microgridspy.multi_year_model.data as mdata
    import microgridspy.multi_year_model.sets as msets
    from microgridspy.io.templates import write_templates
    from microgridspy.io.utils import ProjectPaths

    root = tmp_path / "projects" / "deg_integ"
    inputs = root / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)

    write_templates(SimpleNamespace(inputs_dir=inputs), settings or _settings(), overwrite=True)
    (inputs / "formulation.json").write_text(
        json.dumps(formulation or _formulation(), indent=1), encoding="utf-8"
    )

    battery = yaml.safe_load((inputs / "battery.yaml").read_text(encoding="utf-8"))
    steps = battery["battery"]["investment"]["by_step"]
    for step in steps.values():
        step["calendar_lifetime_years"] = None if life == "null" else life
    if technical:
        battery["battery"]["technical"].update(technical)
    (inputs / "battery.yaml").write_text(yaml.safe_dump(battery, sort_keys=False), encoding="utf-8")

    _write_profiles(inputs)

    monkeypatch.setattr(mdata, "project_paths", lambda name: ProjectPaths(root=root))
    monkeypatch.setattr(msets, "project_paths", lambda name: ProjectPaths(root=root))
    sets = msets.initialize_sets("deg_integ")
    return root, sets, mdata.initialize_data("deg_integ", sets)


def _degradation(ds) -> dict:
    return ds.attrs["settings"]["battery_model"]["degradation_model"]


# ===========================================================================
# What the loader attaches
# ===========================================================================


def test_loader_attaches_the_two_coefficient_fields(tmp_path, monkeypatch) -> None:
    _, _, ds = _build(tmp_path, monkeypatch)

    assert set(ds["battery_cycle_fade_coefficient"].dims) == {"year", "period", "scenario"}
    assert set(ds["battery_calendar_rate_per_year"].dims) == {"year"}
    assert float(ds["battery_cycle_fade_coefficient"].min()) > 0.0
    assert float(ds["battery_calendar_rate_per_year"].min()) > 0.0
    # The pre-audit fields must be gone, not merely unused.
    for gone in ("battery_alpha_calendar", "battery_beta_cycle", "battery_ck_bands"):
        assert gone not in ds.data_vars

    degradation = _degradation(ds)
    assert degradation["coefficient_source"] == "semi_empirical"
    assert degradation["chemistry"] == "LFP"
    assert "n_soc_bands" not in degradation


def test_cycle_coefficient_is_evaluated_at_cell_not_ambient_temperature(
    tmp_path, monkeypatch
) -> None:
    """The enclosure rise must actually reach the coefficients.

    Two projects differing only in enclosure_temperature_rise_c must get different
    coefficients, and the hotter one must be worse. This is the check that would catch the
    rise being read but never applied.
    """
    _, _, cool = _build(tmp_path / "cool", monkeypatch, technical={"enclosure_temperature_rise_c": 0.0})
    _, _, hot = _build(tmp_path / "hot", monkeypatch, technical={"enclosure_temperature_rise_c": 20.0})

    assert float(hot["battery_cycle_fade_coefficient"].mean()) > float(
        cool["battery_cycle_fade_coefficient"].mean()
    )
    assert float(hot["battery_calendar_rate_per_year"].mean()) > float(
        cool["battery_calendar_rate_per_year"].mean()
    )
    assert _degradation(cool)["mean_cell_temperature_c"] == pytest.approx(AMBIENT_C, abs=0.5)
    assert _degradation(hot)["mean_cell_temperature_c"] == pytest.approx(AMBIENT_C + 20.0, abs=0.5)
    assert _degradation(hot)["mean_ambient_temperature_c"] == pytest.approx(AMBIENT_C, abs=0.5)
    # Hotter cells die sooner.
    assert (
        _degradation(hot)["calendar_lifetime_years_derived"]
        < _degradation(cool)["calendar_lifetime_years_derived"]
    )


def test_cycle_magnitude_is_pinned_to_the_datasheet(tmp_path, monkeypatch) -> None:
    """At the reference depth and temperature the coefficient is B/(N*dod) exactly, so the
    scaling the loader reports is the one the coefficient module computed."""
    _, _, ds = _build(tmp_path, monkeypatch)
    assert _degradation(ds)["cycle_life_scaling"] == pytest.approx(1.22865, rel=1e-3)
    assert _degradation(ds)["cycle_life_reference_dod"] == pytest.approx(0.8)
    assert _degradation(ds)["cycle_life_reference_temperature_c"] == pytest.approx(25.0)


def test_calendar_mean_soc_follows_depth_of_discharge(tmp_path, monkeypatch) -> None:
    """SoC_mean = 1 - dod/2, continuous in dod -- no storage-band step."""
    _, _, ds = _build(tmp_path, monkeypatch, technical={"depth_of_discharge": 0.6})
    assert _degradation(ds)["calendar_mean_soc"] == pytest.approx(0.7)


# ===========================================================================
# Derived service life
# ===========================================================================


def test_service_life_is_derived_and_rounded_to_nearest(tmp_path, monkeypatch) -> None:
    _, _, ds = _build(tmp_path, monkeypatch, life="null")
    degradation = _degradation(ds)
    assert degradation["calendar_lifetime_mode"] == "derived"
    derived = degradation["calendar_lifetime_years_derived"]
    used = degradation["calendar_lifetime_years_used"]
    assert used == pytest.approx(max(1.0, round(derived)))
    assert abs(used - derived) <= 0.5 + 1e-9
    # The traceability fields a sweep would be sorted on.
    for key in (
        "assumed_equivalent_full_cycles_per_year",
        "assumed_cycle_fade_per_year",
        "discharge_weighted_cycle_fade_coefficient",
        "mean_cell_temperature_c",
        "calendar_fade_budget_fraction",
    ):
        assert key in degradation and np.isfinite(float(degradation[key]))
    assert degradation["assumed_equivalent_full_cycles_per_year"] > 0.0


def test_derived_life_replaces_the_input_before_masks_and_annuities(tmp_path, monkeypatch) -> None:
    """The derived life has to be written back, or the replacement schedule and the capital
    recovery factor would still be using the null/placeholder value."""
    _, _, ds = _build(tmp_path, monkeypatch, life="null")
    used = _degradation(ds)["calendar_lifetime_years_used"]
    written = np.asarray(ds["battery_calendar_lifetime_years"].values, dtype=float).reshape(-1)
    assert np.all(np.isfinite(written))
    assert written == pytest.approx(used)


def test_a_hand_set_life_is_honoured(tmp_path, monkeypatch) -> None:
    _, _, ds = _build(tmp_path, monkeypatch, life=6)
    degradation = _degradation(ds)
    assert degradation["calendar_lifetime_mode"] == "user"
    assert degradation["calendar_lifetime_years_used"] == pytest.approx(6.0)
    assert "calendar_lifetime_years_derived" not in degradation


def test_calendar_rate_tracks_the_life_it_is_linearised_over(tmp_path, monkeypatch) -> None:
    """The law is sub-linear in time, so a shorter interval implies a higher average rate.
    Getting this wrong would make cumulative fade at end of life inconsistent."""
    _, _, short = _build(tmp_path / "short", monkeypatch, life=5)
    _, _, long = _build(tmp_path / "long", monkeypatch, life=15)
    assert float(short["battery_calendar_rate_per_year"].mean()) > float(
        long["battery_calendar_rate_per_year"].mean()
    )


# ===========================================================================
# Guards
# ===========================================================================


def test_missing_temperature_series_is_refused(tmp_path, monkeypatch) -> None:
    root, _, _ = _build(tmp_path, monkeypatch)
    (root / "inputs" / "ambient_temperature.csv").unlink()

    import microgridspy.multi_year_model.data as mdata
    import microgridspy.multi_year_model.sets as msets

    sets = msets.initialize_sets("deg_integ")
    with pytest.raises(InputValidationError, match="ambient_temperature.csv"):
        mdata.initialize_data("deg_integ", sets)


def test_an_over_long_hand_set_life_is_refused_with_a_bound(tmp_path, monkeypatch) -> None:
    """Calendar fade and the end-of-life floor both scale with nameplate, so buying more
    battery cannot relax the floor: past a certain interval the model is simply infeasible.
    The guard has to say so up front, and name the longest interval that works."""
    with pytest.raises(InputValidationError) as exc:
        _build(
            tmp_path,
            monkeypatch,
            life=40,
            technical={"enclosure_temperature_rise_c": 20.0, "calendar_fade_scale": 2.72},
        )
    message = str(exc.value)
    assert "end-of-life floor" in message
    assert "calendar_lifetime_years" in message


def test_the_warning_band_fires_without_failing(tmp_path, monkeypatch) -> None:
    with pytest.warns(UserWarning, match="hypersensitive"):
        _, _, ds = _build(
            tmp_path,
            monkeypatch,
            life=7,
            technical={"enclosure_temperature_rise_c": 15.0, "calendar_fade_scale": 2.0},
        )
    degradation = _degradation(ds)
    assert degradation["calendar_fade_warning"] is True
    assert 0.70 < degradation["calendar_fade_budget_fraction"] < 1.0


def test_budget_fraction_is_recorded_on_every_run(tmp_path, monkeypatch) -> None:
    """Recorded even when it is comfortable, so a thousand-cluster sweep can be sorted on it."""
    _, _, ds = _build(tmp_path, monkeypatch)
    degradation = _degradation(ds)
    assert 0.0 < degradation["calendar_fade_budget_fraction"] < 0.70
    assert degradation["calendar_fade_warning"] is False


def test_lead_acid_project_is_refused(tmp_path, monkeypatch) -> None:
    with pytest.raises(InputValidationError, match="Li-ion only"):
        _build(tmp_path, monkeypatch, settings=_settings(battery_chemistry="lead_acid"))


def test_mixed_null_and_set_lifetimes_are_refused(tmp_path, monkeypatch) -> None:
    """Deriving the life for some cohorts and asserting it for others would amortise the
    same asset over two different horizons."""
    import yaml

    import microgridspy.multi_year_model.data as mdata
    import microgridspy.multi_year_model.sets as msets
    from microgridspy.io.templates import write_templates
    from microgridspy.io.utils import ProjectPaths

    root = tmp_path / "projects" / "deg_integ"
    inputs = root / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    settings = _settings(capacity_expansion=True, investment_steps_years=[1, 2])
    write_templates(SimpleNamespace(inputs_dir=inputs), settings, overwrite=True)
    formulation = _formulation()
    formulation["capacity_expansion"] = True
    formulation["investment_steps_years"] = [1, 2]
    (inputs / "formulation.json").write_text(json.dumps(formulation, indent=1), encoding="utf-8")

    battery = yaml.safe_load((inputs / "battery.yaml").read_text(encoding="utf-8"))
    steps = list(battery["battery"]["investment"]["by_step"].values())
    if len(steps) < 2:
        pytest.skip("template did not produce two investment steps")
    steps[0]["calendar_lifetime_years"] = None
    steps[1]["calendar_lifetime_years"] = 8
    (inputs / "battery.yaml").write_text(yaml.safe_dump(battery, sort_keys=False), encoding="utf-8")

    monkeypatch.setattr(mdata, "project_paths", lambda name: ProjectPaths(root=root))
    monkeypatch.setattr(msets, "project_paths", lambda name: ProjectPaths(root=root))
    sets = msets.initialize_sets("deg_integ")
    with pytest.raises(InputValidationError, match="null for every investment step"):
        mdata.initialize_data("deg_integ", sets)


# ===========================================================================
# Mode interaction
# ===========================================================================


def test_linear_fade_mode_attaches_no_coefficients(tmp_path, monkeypatch) -> None:
    """Mode 1 must stay exactly as cheap as it was: a flat rate and nothing else."""
    _, _, ds = _build(
        tmp_path,
        monkeypatch,
        settings=_settings(
            battery_semiempirical_degradation_enabled=False,
            battery_loss_model="constant_efficiency",
        ),
        formulation=_formulation(
            coefficients_enabled=False, loss_model="constant_efficiency"
        ),
        life=8,
    )
    for absent in (
        "battery_cycle_fade_coefficient",
        "battery_calendar_rate_per_year",
        "ambient_temperature",
    ):
        assert absent not in ds.data_vars
    assert _degradation(ds)["coefficients_enabled"] is False


def test_linear_rate_is_suppressed_and_reported_in_semiempirical_mode(
    tmp_path, monkeypatch
) -> None:
    """Both modes model background ageing, so running the flat rate alongside the explicit
    calendar channel would remove the same capacity twice."""
    with pytest.warns(UserWarning, match="capacity_degradation_rate_per_year is ignored"):
        _, _, ds = _build(
            tmp_path, monkeypatch, technical={"capacity_degradation_rate_per_year": 0.02}
        )
    rate = np.asarray(ds["battery_capacity_degradation_rate_per_year"].values, dtype=float)
    assert float(np.max(np.abs(rate))) == 0.0
    assert ds.attrs["settings"]["battery_model"]["exogenous_capacity_degradation_active"] is False


def test_a_zero_linear_rate_is_suppressed_silently(tmp_path, monkeypatch) -> None:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        _build(tmp_path, monkeypatch, technical={"capacity_degradation_rate_per_year": 0.0})


# ===========================================================================
# Ambient-temperature loader
# ===========================================================================


def test_ambient_temperature_loader_roundtrip(tmp_path) -> None:
    import pandas as pd

    import microgridspy.io.csv_format as cf
    from microgridspy.multi_year_model.data import _load_ambient_temperature_csv

    period = xr.DataArray(np.arange(3), dims="period", name="period")
    scenario = xr.DataArray(["scenario_1"], dims="scenario", name="scenario")
    year = xr.DataArray([2026, 2027], dims="year", name="year")

    cols = pd.MultiIndex.from_tuples(
        [("meta", "hour"), ("scenario_1", "2026"), ("scenario_1", "2027")],
        names=["scenario", "year"],
    )
    frame = pd.DataFrame([[0, 20.0, 30.0], [1, 21.0, 31.0], [2, 22.0, 32.0]], columns=cols)
    path = tmp_path / "ambient_temperature.csv"
    cf.write_csv_with_format(frame, path, csv_format={"sep": ",", "decimal": "."}, index=False)

    da = _load_ambient_temperature_csv(
        path, period_coord=period, scenario_coord=scenario, year_coord=year
    )
    assert set(da.dims) == {"year", "period", "scenario"}
    assert float(da.sel(year=2027, period=2, scenario="scenario_1")) == pytest.approx(32.0)


def test_ambient_temperature_loader_missing_file(tmp_path) -> None:
    from microgridspy.multi_year_model.data import _load_ambient_temperature_csv

    period = xr.DataArray(np.arange(3), dims="period", name="period")
    scenario = xr.DataArray(["scenario_1"], dims="scenario", name="scenario")
    year = xr.DataArray([2026], dims="year", name="year")
    with pytest.raises(InputValidationError):
        _load_ambient_temperature_csv(
            tmp_path / "does_not_exist.csv",
            period_coord=period,
            scenario_coord=scenario,
            year_coord=year,
        )


# ===========================================================================
# Preview
# ===========================================================================


def test_preview_returns_both_curves() -> None:
    preview = coefficient_curve_preview(chemistry="LFP", depth_of_discharge=0.8, n_points=21)
    assert preview["temperature_degc"].shape == (21,)
    assert preview["cycle_fade_coefficient"].shape == (21,)
    assert preview["calendar_rate_per_year"].shape == (21,)
    assert np.all(np.diff(preview["cycle_fade_coefficient"]) > 0.0)
    assert np.all(np.diff(preview["calendar_rate_per_year"]) > 0.0)
    assert preview["calendar_mean_soc"] == pytest.approx(0.6)
