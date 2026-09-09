"""Multi-year battery cycle-fade degradation tests.

The endogenous cycle-fade layer uses the semi-empirical coefficient beta(T) as its
single source: annual capacity fade = sum_t beta(T)_t * (charge_dc + discharge_dc),
propagated through the yearly effective-capacity state with cohort resets.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Multi-year degradation solve fixture (2 years, 1 cohort, N scenarios) used to
# check the scenario-wise cycle-fade convention and the effective-capacity
# tightness guard (reporting truthfulness).
# ---------------------------------------------------------------------------
import linopy as lp  # noqa: E402
import numpy as np  # noqa: E402
import xarray as xr  # noqa: E402

from microgridspy.multi_year_model.constraints import initialize_constraints  # noqa: E402
from microgridspy.multi_year_model.objective import initialize_objective  # noqa: E402
from microgridspy.multi_year_model.variables import initialize_vars  # noqa: E402


def _deg_sets(scenarios: list[str], years: tuple[str, ...] = ("2026", "2027")) -> xr.Dataset:
    years = list(years)
    return xr.Dataset(
        data_vars={
            "inv_step_start_year": xr.DataArray(
                [years[0]], dims=("inv_step",), coords={"inv_step": ["1"]}
            ),
            "year_inv_step": xr.DataArray(
                ["1"] * len(years), dims=("year",), coords={"year": years}
            ),
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
    scenarios: list[str],
    period1_load: dict[str, float],
    *,
    years: tuple[str, ...] = ("2026", "2027"),
    calendar_lifetime: float = 20.0,
) -> tuple[xr.Dataset, xr.Dataset]:
    sets = _deg_sets(scenarios, years=years)
    yrs, pers, scs, res, inv = sets.year, sets.period, sets.scenario, sets.resource, sets.inv_step
    ns, ny = len(scenarios), len(years)

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
            "battery_calendar_lifetime_years": inv1(calendar_lifetime),
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
            "battery_beta_cycle": xr.DataArray(
                np.full((2, ny, ns), 0.01),
                dims=("period", "year", "scenario"),
                coords={"period": pers, "year": yrs, "scenario": scs},
            ),
            "battery_end_of_life_soh": scal(0.8),
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
    data.attrs["settings"] = {
        "project_name": "deg_test",
        "social_discount_rate": 0.0,
        "grid": {"on_grid": False, "allow_export": False},
        "optimization_constraints": {"enforcement": "scenario_wise"},
        "battery_model": {
            "loss_model": "convex_loss_epigraph",
            "degradation_model": {"cycle_fade_enabled": True},
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
        "battery_cycle_fade",
        "battery_effective_energy_capacity",
    ):
        assert "scenario" in set(vars_dict[name].dims), f"{name} must be scenario-indexed"


def test_cycle_fade_diverges_across_scenarios() -> None:
    # Two scenarios with different period-1 loads -> different throughput ->
    # different per-scenario cycle fade and effective capacity. Start empty so each
    # scenario must charge-then-discharge its own load (throughput is load-proportional).
    sets, data = _deg_data(["s_low", "s_high"], {"s_low": 0.2, "s_high": 0.8})
    data["battery_initial_soc"] = xr.DataArray(0.0)
    _, _, sol = _solve_deg(sets, data)
    cyc_y0 = sol["battery_cycle_fade"].sel(year="2026").sum("inv_step")
    assert "scenario" in cyc_y0.dims
    v_low = float(cyc_y0.sel(scenario="s_low"))
    v_high = float(cyc_y0.sel(scenario="s_high"))
    assert abs(v_high - v_low) > 1e-6  # genuinely different cycle fade per scenario


def test_reported_effective_capacity_uses_physical_recursion() -> None:
    # Reporting truthfulness: the raw LP effective-capacity state can stay slack-low
    # (its year-link is an inequality nudged tight only by a 1e-9 regularizer), but the
    # reported capacity must follow the physical cycle-fade recursion from the initial SoH.
    from microgridspy.export.multi_year_results import (
        build_dispatch_timeseries_table_multi_year,
    )

    sets, data = _deg_data(["scenario_1"], {"scenario_1": 0.5})
    _, vd, sol = _solve_deg(sets, data)

    cyc = float(sol["battery_cycle_fade"].sel(year="2026").sum().item())
    # year 2026: soh0 * nominal = 1.0 * 0.5; year 2027: previous minus one year of cycle fade
    expected_y1 = 0.5 - cyc

    df = build_dispatch_timeseries_table_multi_year(sets=sets, data=data, vars=vd, solution=sol)
    reported_y1 = float(
        df.loc[df["year"].astype(str) == "2027", "battery_effective_energy_capacity"].iloc[0]
    )
    assert reported_y1 == pytest.approx(expected_y1, abs=1e-6)


# ---------------------------------------------------------------------------
# Replacement / capacity-expansion consistency: when a battery cohort is
# replaced (calendar lifetime reached), degradation must restart from a fresh
# battery. Both channels reset: the endogenous cycle-fade state (via the
# commission mask) and the exogenous flat calendar rate (via the repeating
# degradation factor, whose per-cycle age resets).
# ---------------------------------------------------------------------------
def test_battery_replacement_resets_cycle_fade_state() -> None:
    # 4 years, one cohort, calendar lifetime 2 -> the battery is replaced and a new
    # cohort commissions at the 3rd year (2028). Cycle fade accumulates within each
    # 2-year life and must reset to full at the replacement year.
    years = ("2026", "2027", "2028", "2029")
    sets, data = _deg_data(["s1"], {"s1": 0.6}, years=years, calendar_lifetime=2.0)
    data["battery_initial_soc"] = xr.DataArray(0.0)  # force charge-then-discharge each year
    _, _, sol = _solve_deg(sets, data)

    eff = sol["battery_effective_energy_capacity"].sum("inv_step").sel(scenario="s1")
    e = {y: float(eff.sel(year=y)) for y in years}

    # Degradation accumulates within the first life...
    assert e["2027"] < e["2026"] - 1e-9
    # ...then RESETS to full at the replacement commissioning year...
    assert e["2028"] > e["2027"] + 1e-9
    assert e["2028"] == pytest.approx(e["2026"], abs=1e-6)  # fresh cohort == as-installed
    # ...and degrades again within the second life.
    assert e["2029"] < e["2028"] - 1e-9


def test_flat_calendar_rate_resets_each_replacement_cycle() -> None:
    # The exogenous flat-rate factor must restart at 1.0 for each new cohort, so a
    # replaced battery is not carried in pre-degraded. lifetime 2, rate 0.1, 4 years
    # -> per-cycle age = [1, 2, 1, 2] -> factor (1-rate)^(age-1) = [1, 0.9, 1, 0.9].
    from microgridspy.multi_year_model.lifecycle import repeating_degradation_factor

    years = ("2026", "2027", "2028", "2029")
    sets = _deg_sets(["s1"], years=years)
    rate = xr.DataArray([0.1], dims=("inv_step",), coords={"inv_step": ["1"]})
    factor = repeating_degradation_factor(sets, xr.DataArray(2.0), rate)
    vals = factor.sel(inv_step="1").sel(year=list(years)).values.astype(float)
    assert vals == pytest.approx([1.0, 0.9, 1.0, 0.9], abs=1e-9)


def test_physical_effective_capacity_resets_at_replacement_commission() -> None:
    # The reporting recursion must mirror the model: reset to soh0*nominal in a
    # commissioning year, decline by cycle fade otherwise.
    from microgridspy.export.multi_year_results import _physical_effective_capacity

    years = [2026, 2027, 2028, 2029]
    inv = ["1"]

    def _da(vals):
        return xr.DataArray(
            np.array(vals, dtype=float).reshape(len(years), 1, 1),
            dims=("year", "scenario", "inv_step"),
            coords={"year": years, "scenario": ["s1"], "inv_step": inv},
        )

    nominal = _da([1.0, 1.0, 1.0, 1.0])
    cycle = _da([0.1, 0.1, 0.1, 0.1])  # per-year cycle fade
    # Replacement commissions at 2026 (install) and 2028 (lifetime 2).
    commission = xr.DataArray(
        np.array([1.0, 0.0, 1.0, 0.0]).reshape(len(years), 1),
        dims=("year", "inv_step"),
        coords={"year": years, "inv_step": inv},
    )
    out = _physical_effective_capacity(
        nominal_available=nominal, cycle_fade_year=cycle, commission=commission, soh0=1.0
    )
    v = {y: float(out.sel(year=y).values.reshape(-1)[0]) for y in years}
    assert v[2026] == pytest.approx(1.0)  # install
    assert v[2027] == pytest.approx(0.9)  # 1.0 - cycle(0.1)
    assert v[2028] == pytest.approx(1.0)  # RESET at replacement
    assert v[2029] == pytest.approx(0.9)  # 1.0 - cycle(0.1) after reset


def test_capacity_expansion_new_cohort_commissions_fresh() -> None:
    # Capacity expansion: a second cohort is invested at a later step. Each cohort's
    # degradation is tracked independently and the new cohort commissions fresh at its
    # own start year, while the first keeps ageing.
    from microgridspy.multi_year_model.lifecycle import (
        repeating_degradation_factor,
        replacement_active_mask,
        replacement_commission_mask,
    )

    years = ["2026", "2027", "2028", "2029"]
    sets = xr.Dataset(
        data_vars={
            "inv_step_start_year": xr.DataArray(
                ["2026", "2028"], dims=("inv_step",), coords={"inv_step": ["1", "2"]}
            ),
            "year_inv_step": xr.DataArray(
                ["1", "1", "2", "2"], dims=("year",), coords={"year": years}
            ),
        },
        coords={"year": ("year", years), "inv_step": ("inv_step", ["1", "2"])},
    )

    active = replacement_active_mask(sets)
    # Cohort 1 active for the whole horizon; cohort 2 only from its 2028 start.
    assert list(active.sel(inv_step="1").sel(year=years).values.astype(float)) == [1, 1, 1, 1]
    assert list(active.sel(inv_step="2").sel(year=years).values.astype(float)) == [0, 0, 1, 1]

    commission = replacement_commission_mask(sets, xr.DataArray(20.0))
    # Cohort 1 commissions at install (2026); cohort 2 commissions fresh at 2028.
    assert list(commission.sel(inv_step="1").sel(year=years).values.astype(float)) == [1, 0, 0, 0]
    assert list(commission.sel(inv_step="2").sel(year=years).values.astype(float)) == [0, 0, 1, 0]

    # The flat calendar rate is fresh (factor 1.0) in each cohort's commissioning year.
    rate = xr.DataArray([0.1, 0.1], dims=("inv_step",), coords={"inv_step": ["1", "2"]})
    factor = repeating_degradation_factor(sets, xr.DataArray(20.0), rate)
    assert float(factor.sel(inv_step="1").sel(year="2026")) == pytest.approx(1.0)
    assert float(factor.sel(inv_step="1").sel(year="2028")) == pytest.approx(0.9**2)  # aged 2 yrs
    assert float(factor.sel(inv_step="2").sel(year="2028")) == pytest.approx(1.0)  # fresh cohort
    assert float(factor.sel(inv_step="2").sel(year="2029")) == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# Template surface: calendar ageing is a single flat %/yr field (0 = off). It is
# always written in the dynamic formulation and coexists with cycle fade.
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
        battery_efficiency_curve_csv="battery_efficiency_curve.csv",
        battery_cycle_lifetime_to_eol_cycles=6000.0,
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


def test_battery_flat_ageing_defaults_to_zero_and_coexists_with_cycle_fade(tmp_path) -> None:
    # Flat calendar ageing defaults to 0 (off), is still written, and is independent of
    # cycle fade (both can be active at once -- no mutual suppression).
    tech = _written_battery_technical(
        tmp_path,
        "bat_default",
        _battery_template_settings(
            battery_loss_model="convex_loss_epigraph",
            battery_cycle_fade_enabled=True,
        ),
    )
    assert tech.get("capacity_degradation_rate_per_year") == pytest.approx(0.0)
    assert tech.get("cycle_lifetime_to_eol_cycles") == pytest.approx(6000.0)
    # The SOC-dependent calendar curve was removed entirely.
    assert "calendar_fade_curve_csv" not in tech
    assert "calendar_time_increment_per_year" not in tech


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
    commission = xr.DataArray(
        np.array([1.0, 0.0]).reshape(2, 1),
        dims=("year", "inv_step"),
        coords={"year": years, "inv_step": inv},
    )
    out = _physical_effective_capacity(
        nominal_available=nominal,
        cycle_fade_year=cycle,
        commission=commission,
        soh0=1.0,
    )
    assert float(out.sel(year=2026).values.reshape(-1)[0]) == pytest.approx(1.0)
    # year 2 = prev(1.0) - cycle(0.1) = 0.9
    assert float(out.sel(year=2027).values.reshape(-1)[0]) == pytest.approx(0.9)
