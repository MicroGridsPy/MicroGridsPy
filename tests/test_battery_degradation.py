"""Unit tests for the battery cycle-fade coefficient convention (Stage 1 consistency fixes).

Pins the documented ``/initial_soh`` convention: the cycle-fade coefficient measures
usable-capacity fade per unit of DC throughput relative to the *beginning-of-life* usable
capacity, so the initial SoH appears in the denominator and only matters when it is below 1.
"""

from __future__ import annotations

import pytest

from microgridspy.data_pipeline.battery_degradation_model import (
    InputValidationError,
    derive_cycle_fade_coefficient_from_cycle_life,
)


def test_cycle_fade_coefficient_full_initial_soh() -> None:
    gamma = derive_cycle_fade_coefficient_from_cycle_life(
        initial_soh=1.0,
        end_of_life_soh=0.8,
        cycle_lifetime_to_eol_cycles=4000.0,
        reference_depth_of_discharge=0.8,
    )
    # (1.0 - 0.8) / (4000 * 0.8 * 1.0)
    assert gamma == pytest.approx(0.2 / 3200.0, rel=1e-12)


def test_cycle_fade_coefficient_scales_with_initial_soh_denominator() -> None:
    # With initial_soh < 1 the coefficient carries the extra 1/initial_soh factor, i.e. it is
    # the initial_soh == 1 numerator divided by (N * dod) and then by initial_soh.
    initial_soh = 0.95
    gamma = derive_cycle_fade_coefficient_from_cycle_life(
        initial_soh=initial_soh,
        end_of_life_soh=0.8,
        cycle_lifetime_to_eol_cycles=4000.0,
        reference_depth_of_discharge=0.8,
    )
    expected = (initial_soh - 0.8) / (4000.0 * 0.8 * initial_soh)
    assert gamma == pytest.approx(expected, rel=1e-12)
    # The denominator normalization is genuinely present (result differs from dropping /soh0).
    without_norm = (initial_soh - 0.8) / (4000.0 * 0.8)
    assert gamma == pytest.approx(without_norm / initial_soh, rel=1e-12)


def test_cycle_fade_coefficient_rejects_invalid_inputs() -> None:
    with pytest.raises(InputValidationError):
        derive_cycle_fade_coefficient_from_cycle_life(
            initial_soh=0.8,
            end_of_life_soh=0.9,  # eol above initial -> invalid
            cycle_lifetime_to_eol_cycles=4000.0,
            reference_depth_of_discharge=0.8,
        )
    with pytest.raises(InputValidationError):
        derive_cycle_fade_coefficient_from_cycle_life(
            initial_soh=1.0,
            end_of_life_soh=0.8,
            cycle_lifetime_to_eol_cycles=0.0,  # non-positive cycle life -> invalid
            reference_depth_of_discharge=0.8,
        )


# ---------------------------------------------------------------------------
# Multi-year degradation solve fixture (2 years, 1 cohort, N scenarios) used to
# check the unified scenario-wise calendar/cycle fade convention (Stage 2) and
# the effective-capacity tightness guard (Stage 1 reporting truthfulness).
# ---------------------------------------------------------------------------
import linopy as lp  # noqa: E402
import numpy as np  # noqa: E402
import xarray as xr  # noqa: E402

from microgridspy.multi_year_model.constraints import initialize_constraints  # noqa: E402
from microgridspy.multi_year_model.objective import initialize_objective  # noqa: E402
from microgridspy.multi_year_model.variables import initialize_vars  # noqa: E402


def _deg_sets(scenarios: list[str]) -> xr.Dataset:
    years = ["2026", "2027"]
    return xr.Dataset(
        data_vars={
            "inv_step_start_year": xr.DataArray(
                ["2026"], dims=("inv_step",), coords={"inv_step": ["1"]}
            ),
            "year_inv_step": xr.DataArray(["1", "1"], dims=("year",), coords={"year": years}),
        },
        coords={
            "period": ("period", np.arange(2, dtype=int)),
            "year": ("year", years),
            "scenario": ("scenario", list(scenarios)),
            "resource": ("resource", ["Solar"]),
            "inv_step": ("inv_step", ["1"]),
        },
    )


def _deg_data(
    scenarios: list[str], period1_load: dict[str, float]
) -> tuple[xr.Dataset, xr.Dataset]:
    sets = _deg_sets(scenarios)
    yrs, pers, scs, res, inv = sets.year, sets.period, sets.scenario, sets.resource, sets.inv_step
    ns, ny = len(scenarios), 2

    # period-major dim order (period, year, scenario), matching the real pipeline.
    load = np.zeros((2, ny, ns))
    for si, s in enumerate(scenarios):
        load[1, :, si] = period1_load[s]  # demand only in period 1
    avail = np.zeros((2, ny, ns, 1))
    avail[0, :, :, 0] = 1.0  # RES only in period 0 -> must charge the battery to serve period 1

    def scal(v):
        return xr.DataArray(v)

    def inv1(v):
        return xr.DataArray([v], dims=("inv_step",), coords={"inv_step": inv})

    def invres(v):
        return xr.DataArray(
            [[v]], dims=("inv_step", "resource"), coords={"inv_step": inv, "resource": res}
        )

    def resd(v):
        return xr.DataArray([v], dims=("resource",), coords={"resource": res})

    data = xr.Dataset(
        data_vars={
            "load_demand": xr.DataArray(
                load,
                dims=("period", "year", "scenario"),
                coords={"period": pers, "year": yrs, "scenario": scs},
            ),
            "resource_availability": xr.DataArray(
                avail,
                dims=("period", "year", "scenario", "resource"),
                coords={"period": pers, "year": yrs, "scenario": scs, "resource": res},
            ),
            "scenario_weight": xr.DataArray(
                [1.0 / ns] * ns, dims=("scenario",), coords={"scenario": scs}
            ),
            "min_renewable_penetration": scal(0.0),
            "max_lost_load_fraction": scal(0.0),
            "lost_load_cost_per_kwh": scal(1.0e6),
            "land_availability_m2": scal(np.nan),
            "emission_cost_per_kgco2e": scal(0.0),
            "res_nominal_capacity_kw": invres(1.0),
            "res_lifetime_years": invres(20.0),
            "res_specific_investment_cost_per_kw": invres(10.0),
            "res_inverter_specific_investment_cost_per_kw_ac": invres(0.0),
            "res_inverter_lifetime_years": invres(20.0),
            "res_wacc": invres(0.0),
            "res_grant_share_of_capex": invres(0.0),
            "res_embedded_emissions_kgco2e_per_kw": invres(0.0),
            "res_fixed_om_share_per_year": invres(0.0),
            "res_inverter_fixed_om_share_per_year": invres(0.0),
            "res_production_subsidy_per_kwh": invres(0.0),
            "res_dc_ac_ratio": resd(1.0),
            "res_inverter_efficiency": resd(1.0),
            "res_specific_area_m2_per_kw": resd(0.0),
            "res_max_installable_capacity_kw": resd(np.nan),
            "res_capacity_degradation_rate_per_year": resd(0.0),
            "battery_nominal_capacity_kwh": inv1(1.0),
            "battery_specific_investment_cost_per_kwh": inv1(1.0),
            "battery_inverter_specific_investment_cost_per_kw": inv1(0.0),
            "battery_inverter_lifetime_years": inv1(20.0),
            "battery_wacc": inv1(0.0),
            "battery_calendar_lifetime_years": inv1(20.0),
            "battery_fixed_om_share_per_year": inv1(0.0),
            "battery_inverter_fixed_om_share_per_year": inv1(0.0),
            "battery_embedded_emissions_kgco2e_per_kwh": inv1(0.0),
            "battery_max_installable_capacity_kwh": scal(np.nan),
            "battery_charge_efficiency": scal(1.0),
            "battery_discharge_efficiency": scal(1.0),
            "battery_initial_soc": scal(1.0),
            "battery_initial_soh": scal(1.0),
            "battery_depth_of_discharge": scal(1.0),
            "battery_max_charge_c_rate": scal(1.0),
            "battery_max_discharge_c_rate": scal(1.0),
            "battery_cycle_fade_coefficient_per_kwh_throughput": scal(0.01),
            "battery_calendar_time_increment_per_year": scal(1.0),
            "battery_capacity_degradation_rate_per_year": scal(0.0),
            "generator_nominal_capacity_kw": inv1(1.0),
            "generator_max_installable_capacity_kw": scal(0.0),
            "generator_nominal_efficiency_full_load": scal(0.3),
            "generator_capacity_degradation_rate_per_year": scal(0.0),
            "generator_specific_investment_cost_per_kw": inv1(1.0e6),
            "generator_lifetime_years": inv1(20.0),
            "generator_wacc": inv1(0.0),
            "generator_fixed_om_share_per_year": inv1(0.0),
            "generator_embedded_emissions_kgco2e_per_kw": inv1(0.0),
            "fuel_lhv_kwh_per_unit_fuel": scal(1.0),
            "fuel_cost_per_unit_fuel": scal(0.0),
            "fuel_fuel_cost_per_unit_fuel": scal(0.0),
            "fuel_direct_emissions_kgco2e_per_unit_fuel": scal(0.0),
        }
    )
    # advanced convex-loss battery curve (lossless: zero slopes/intercepts)
    lseg = xr.IndexVariable("battery_loss_segment", [0])
    data = data.assign_coords({"battery_loss_segment": lseg})
    for nm in (
        "battery_charge_loss_slope",
        "battery_charge_loss_intercept",
        "battery_discharge_loss_slope",
        "battery_discharge_loss_intercept",
    ):
        data[nm] = xr.DataArray(
            [0.0], dims=("battery_loss_segment",), coords={"battery_loss_segment": lseg}
        )
    # calendar-fade curve: linear in average SOC (slope 0.02 per unit soc, zero intercept)
    cseg = xr.IndexVariable("battery_calendar_segment", [0])
    data = data.assign_coords({"battery_calendar_segment": cseg})
    data["battery_calendar_fade_slope"] = xr.DataArray(
        [0.02], dims=("battery_calendar_segment",), coords={"battery_calendar_segment": cseg}
    )
    data["battery_calendar_fade_intercept"] = xr.DataArray(
        [0.0], dims=("battery_calendar_segment",), coords={"battery_calendar_segment": cseg}
    )

    data.attrs["settings"] = {
        "project_name": "deg_test",
        "social_discount_rate": 0.0,
        "grid": {"on_grid": False, "allow_export": False},
        "optimization_constraints": {"enforcement": "scenario_wise"},
        "battery_model": {
            "loss_model": "convex_loss_epigraph",
            "degradation_model": {"cycle_fade_enabled": True, "calendar_fade_enabled": True},
        },
    }
    data.attrs["conversion_technology_by_resource"] = {"Solar": "Solar PV"}
    return sets, data


def _solve_deg(sets: xr.Dataset, data: xr.Dataset):
    model = lp.Model()
    vars_dict = initialize_vars(sets, data, model)
    initialize_constraints(sets, data, vars_dict, model)
    initialize_objective(sets, data, vars_dict, model)
    try:
        try:
            model.solve(solver_name="highs")
        except TypeError:
            model.solve("highs")
    except Exception as exc:  # pragma: no cover - environment dependent
        if any(t in str(exc).lower() for t in ("highs", "solver", "not available", "executable")):
            pytest.skip(f"HiGHS unavailable: {exc}")
        raise
    return model, vars_dict, model.solution


def test_degradation_vars_are_scenario_wise() -> None:
    sets, data = _deg_data(["scenario_1"], {"scenario_1": 0.4})
    model = lp.Model()
    vars_dict = initialize_vars(sets, data, model)
    for name in (
        "battery_average_soc",
        "battery_calendar_fade",
        "battery_effective_energy_capacity",
    ):
        assert "scenario" in set(vars_dict[name].dims), f"{name} must be scenario-indexed"


def test_calendar_fade_diverges_across_scenarios() -> None:
    # Two scenarios with different period-1 loads -> different SOC trajectories ->
    # (now) different per-scenario calendar fade and effective capacity.
    sets, data = _deg_data(["s_low", "s_high"], {"s_low": 0.2, "s_high": 0.8})
    _, _, sol = _solve_deg(sets, data)
    cal_y0 = sol["battery_calendar_fade"].sel(year="2026").sum("inv_step")
    assert "scenario" in cal_y0.dims
    v_low = float(cal_y0.sel(scenario="s_low"))
    v_high = float(cal_y0.sel(scenario="s_high"))
    assert abs(v_high - v_low) > 1e-6  # genuinely different calendar fade per scenario


def test_reported_effective_capacity_uses_physical_recursion() -> None:
    # Reporting truthfulness: the raw LP effective-capacity state can stay slack-low
    # (its year-link is an inequality nudged tight only by a 1e-9 regularizer), but the
    # reported capacity must follow the physical fade recursion from the initial SoH.
    from microgridspy.export.multi_year_results import (
        build_dispatch_timeseries_table_multi_year,
    )

    sets, data = _deg_data(["scenario_1"], {"scenario_1": 0.5})
    _, vd, sol = _solve_deg(sets, data)

    cyc = float(sol["battery_cycle_fade"].sel(year="2026").sum().item())
    cal = float(sol["battery_calendar_fade"].sel(year="2026").sum().item())
    # year 2026: soh0 * nominal = 1.0 * 0.5; year 2027: previous minus one year of fade
    expected_y1 = 0.5 - cyc - cal

    df = build_dispatch_timeseries_table_multi_year(sets=sets, data=data, vars=vd, solution=sol)
    reported_y1 = float(
        df.loc[df["year"].astype(str) == "2027", "battery_effective_energy_capacity"].iloc[0]
    )
    assert reported_y1 == pytest.approx(expected_y1, abs=1e-6)


# ---------------------------------------------------------------------------
# Template surface (Stage 2): calendar/time ageing is one control with two
# mutually exclusive flavors. The simple flat %/yr is a first-class, controllable
# field; the SOC-dependent curve suppresses it (never both in the written YAML).
# ---------------------------------------------------------------------------
def _battery_template_settings(**overrides):
    from microgridspy.io.templates import TemplateSettings

    base = dict(
        formulation="dynamic",
        system_type="off_grid",
        allow_export=False,
        multi_scenario=False,
        n_scenarios=1,
        scenario_labels=["scenario_1"],
        scenario_weights=[1.0],
        start_year_label="2026",
        horizon_years=10,
        capacity_expansion=False,
        investment_steps_years=None,
        n_res_sources=1,
        resource_labels=["Solar"],
        conversion_labels=["Solar PV"],
        battery_label="Battery",
        battery_loss_model="constant_efficiency",
        battery_cycle_fade_enabled=False,
        battery_calendar_fade_enabled=False,
        battery_efficiency_curve_csv="battery_efficiency_curve.csv",
        battery_cycle_lifetime_to_eol_cycles=6000.0,
        battery_calendar_fade_curve_csv="battery_calendar_fade_curve.csv",
        battery_calendar_time_increment_per_step=1.0,
        battery_end_of_life_soh=0.8,
        generator_label="Generator",
        generator_efficiency_model="constant_efficiency",
        generator_efficiency_curve_csv="generator_efficiency_curve.csv",
        fuel_label="Fuel",
    )
    base.update(overrides)
    return TemplateSettings(**base)


def _written_battery_technical(tmp_path, name, settings):
    import yaml

    import microgridspy as mgp

    mgp.set_workspace(tmp_path)
    mgp.create_project(
        name, formulation="dynamic", horizon_years=10, settings=settings, overwrite=True
    )
    text = next(tmp_path.rglob("battery.yaml")).read_text(encoding="utf-8")
    return yaml.safe_load(text)["battery"]["technical"]


def test_battery_simple_flat_ageing_is_written(tmp_path) -> None:
    tech = _written_battery_technical(
        tmp_path,
        "bat_flat",
        _battery_template_settings(battery_capacity_degradation_rate_per_year=0.02),
    )
    assert tech.get("capacity_degradation_rate_per_year") == pytest.approx(0.02)


def test_battery_calendar_curve_suppresses_flat_rate(tmp_path) -> None:
    tech = _written_battery_technical(
        tmp_path,
        "bat_cal",
        _battery_template_settings(
            battery_loss_model="convex_loss_epigraph",
            battery_calendar_fade_enabled=True,
            battery_capacity_degradation_rate_per_year=0.02,
        ),
    )
    # Mutually exclusive: with SOC-dependent calendar fade, the flat rate is not written.
    assert "capacity_degradation_rate_per_year" not in tech
    assert tech.get("calendar_fade_curve_csv")


def test_physical_effective_capacity_handles_integer_year_coord() -> None:
    # Regression: the real pipeline uses an integer 'year' coordinate; the reporting
    # recursion must not assume string years (it did, causing a sel KeyError).
    from microgridspy.export.multi_year_results import _physical_effective_capacity

    years = [2026, 2027]
    scen, inv = ["s1"], ["1"]

    def _da(vals):
        return xr.DataArray(
            np.array(vals, dtype=float).reshape(2, 1, 1),
            dims=("year", "scenario", "inv_step"),
            coords={"year": years, "scenario": scen, "inv_step": inv},
        )

    nominal = _da([1.0, 1.0])
    cycle = _da([0.1, 0.0])
    calendar = _da([0.05, 0.0])
    commission = xr.DataArray(
        np.array([1.0, 0.0]).reshape(2, 1),
        dims=("year", "inv_step"),
        coords={"year": years, "inv_step": inv},
    )
    out = _physical_effective_capacity(
        nominal_available=nominal,
        cycle_fade_year=cycle,
        calendar_fade=calendar,
        commission=commission,
        soh0=1.0,
    )
    assert float(out.sel(year=2026).values.reshape(-1)[0]) == pytest.approx(1.0)
    # year 2 = prev(1.0) - cycle(0.1) - calendar(0.05) = 0.85
    assert float(out.sel(year=2027).values.reshape(-1)[0]) == pytest.approx(0.85)
