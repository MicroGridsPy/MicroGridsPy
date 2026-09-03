from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import linopy as lp
import numpy as np
import pytest
import xarray as xr

from microgridspy.data_pipeline.battery_loss_model import CONVEX_LOSS_EPIGRAPH
from microgridspy.data_pipeline.typical_year_parsing import (
    _load_battery_yaml,
    _load_renewables_yaml,
)
from microgridspy.export.typical_year_reporting import build_reporting_tables
from microgridspy.export.typical_year_results import (
    build_design_summary_table,
    build_dispatch_timeseries_table,
    build_typical_year_results,
    export_typical_year_results_package,
)
from microgridspy.typical_year_model.constraints import initialize_constraints
from microgridspy.typical_year_model.objective import _crf, initialize_objective
from microgridspy.typical_year_model.variables import initialize_vars


def _scalar_value(obj) -> float:
    if hasattr(obj, "solution") and obj.solution is not None:
        obj = obj.solution
    if hasattr(obj, "values"):
        arr = np.asarray(obj.values, dtype=float)
    else:
        arr = np.asarray(obj, dtype=float)
    return float(arr.reshape(-1)[0])


def _solve_with_highs_or_skip(model: lp.Model) -> xr.Dataset:
    try:
        try:
            model.solve(solver_name="highs")
        except TypeError:
            model.solve("highs")
    except Exception as exc:  # pragma: no cover - environment dependent
        msg = str(exc).lower()
        if any(
            token in msg
            for token in ("highs", "solver", "not installed", "not available", "executable")
        ):
            pytest.skip(f"HiGHS solver unavailable in this environment: {exc}")
        raise
    assert isinstance(model.solution, xr.Dataset)
    return model.solution


def _base_sets(periods: int) -> xr.Dataset:
    return xr.Dataset(
        coords={
            "period": ("period", np.arange(periods, dtype=int)),
            "scenario": ("scenario", ["scenario_1"]),
            "resource": ("resource", ["Solar"]),
        }
    )


def _base_data(
    *,
    periods: int,
    load: list[float],
    availability: list[float],
    loss_model: str = "constant_efficiency",
    battery_capex_kwh: float = 0.0,
    battery_inverter_capex_kw: float = 0.0,
    battery_inverter_nominal_power_kw: float = 1.0,
    renewable_capex_kw: float = 0.0,
    renewable_inverter_capex_kw_ac: float = 0.0,
    renewable_inverter_lifetime_years: float = 10.0,
    renewable_dc_ac_ratio: float = 1.0,
    renewable_fom_share: float = 0.0,
    renewable_inverter_fom_share: float = 0.0,
    battery_fom_share: float = 0.0,
    battery_inverter_fom_share: float = 0.0,
    battery_inverter_lifetime_years: float = 10.0,
    max_charge_c_rate: float | None = None,
    max_discharge_c_rate: float | None = None,
    discrete_unit_sizing: bool = False,
) -> xr.Dataset:
    scenario = ["scenario_1"]
    resource = ["Solar"]
    data = xr.Dataset(
        data_vars={
            "load_demand": xr.DataArray(
                np.asarray(load, dtype=float).reshape(periods, 1),
                dims=("period", "scenario"),
                coords={"period": np.arange(periods), "scenario": scenario},
            ),
            "resource_availability": xr.DataArray(
                np.asarray(availability, dtype=float).reshape(periods, 1, 1),
                dims=("period", "scenario", "resource"),
                coords={"period": np.arange(periods), "scenario": scenario, "resource": resource},
            ),
            "scenario_weight": xr.DataArray(
                [1.0], dims=("scenario",), coords={"scenario": scenario}
            ),
            "min_renewable_penetration": xr.DataArray(0.0),
            "max_lost_load_fraction": xr.DataArray(0.0),
            "lost_load_cost_per_kwh": xr.DataArray(
                [1.0e6], dims=("scenario",), coords={"scenario": scenario}
            ),
            "land_availability_m2": xr.DataArray(np.nan),
            "emission_cost_per_kgco2e": xr.DataArray(
                [0.0], dims=("scenario",), coords={"scenario": scenario}
            ),
            "res_nominal_capacity_kw": xr.DataArray(
                [1.0], dims=("resource",), coords={"resource": resource}
            ),
            "res_specific_investment_cost_per_kw": xr.DataArray(
                [renewable_capex_kw], dims=("resource",), coords={"resource": resource}
            ),
            "res_inverter_specific_investment_cost_per_kw_ac": xr.DataArray(
                [renewable_inverter_capex_kw_ac], dims=("resource",), coords={"resource": resource}
            ),
            "res_lifetime_years": xr.DataArray(
                [10.0], dims=("resource",), coords={"resource": resource}
            ),
            "res_inverter_lifetime_years": xr.DataArray(
                [renewable_inverter_lifetime_years],
                dims=("resource",),
                coords={"resource": resource},
            ),
            "res_wacc": xr.DataArray([0.05], dims=("resource",), coords={"resource": resource}),
            "res_grant_share_of_capex": xr.DataArray(
                [0.0], dims=("resource",), coords={"resource": resource}
            ),
            "res_fixed_om_share_per_year": xr.DataArray(
                [renewable_fom_share], dims=("resource",), coords={"resource": resource}
            ),
            "res_inverter_fixed_om_share_per_year": xr.DataArray(
                [renewable_inverter_fom_share], dims=("resource",), coords={"resource": resource}
            ),
            "res_production_subsidy_per_kwh": xr.DataArray(
                [[0.0]],
                dims=("scenario", "resource"),
                coords={"scenario": scenario, "resource": resource},
            ),
            "res_embedded_emissions_kgco2e_per_kw": xr.DataArray(
                [[0.0]],
                dims=("scenario", "resource"),
                coords={"scenario": scenario, "resource": resource},
            ),
            "res_dc_ac_ratio": xr.DataArray(
                [renewable_dc_ac_ratio], dims=("resource",), coords={"resource": resource}
            ),
            "res_inverter_efficiency": xr.DataArray(
                [1.0], dims=("resource",), coords={"resource": resource}
            ),
            "res_specific_area_m2_per_kw": xr.DataArray(
                [0.0], dims=("resource",), coords={"resource": resource}
            ),
            "res_max_installable_capacity_kw": xr.DataArray(
                [np.nan], dims=("resource",), coords={"resource": resource}
            ),
            "battery_nominal_capacity_kwh": xr.DataArray(1.0),
            "battery_specific_investment_cost_per_kwh": xr.DataArray(battery_capex_kwh),
            "battery_inverter_specific_investment_cost_per_kw": xr.DataArray(
                battery_inverter_capex_kw
            ),
            "battery_calendar_lifetime_years": xr.DataArray(10.0),
            "battery_inverter_lifetime_years": xr.DataArray(battery_inverter_lifetime_years),
            "battery_wacc": xr.DataArray(0.05),
            "battery_fixed_om_share_per_year": xr.DataArray(battery_fom_share),
            "battery_inverter_fixed_om_share_per_year": xr.DataArray(battery_inverter_fom_share),
            "battery_embedded_emissions_kgco2e_per_kwh": xr.DataArray(
                [0.0], dims=("scenario",), coords={"scenario": scenario}
            ),
            "battery_max_installable_capacity_kwh": xr.DataArray(np.nan),
            "battery_charge_efficiency": xr.DataArray(
                [1.0], dims=("scenario",), coords={"scenario": scenario}
            ),
            "battery_discharge_efficiency": xr.DataArray(
                [1.0], dims=("scenario",), coords={"scenario": scenario}
            ),
            "battery_initial_soc": xr.DataArray(
                [0.0], dims=("scenario",), coords={"scenario": scenario}
            ),
            "battery_depth_of_discharge": xr.DataArray(
                [1.0], dims=("scenario",), coords={"scenario": scenario}
            ),
            "battery_inverter_nominal_power_kw": xr.DataArray(battery_inverter_nominal_power_kw),
            "battery_max_charge_c_rate": xr.DataArray(
                np.nan if max_charge_c_rate is None else max_charge_c_rate
            ),
            "battery_max_discharge_c_rate": xr.DataArray(
                np.nan if max_discharge_c_rate is None else max_discharge_c_rate
            ),
            "generator_nominal_capacity_kw": xr.DataArray(1.0),
            "generator_max_installable_capacity_kw": xr.DataArray(np.nan),
            "generator_specific_investment_cost_per_kw": xr.DataArray(1.0e6),
            "generator_lifetime_years": xr.DataArray(10.0),
            "generator_wacc": xr.DataArray(0.05),
            "generator_fixed_om_share_per_year": xr.DataArray(0.0),
            "generator_embedded_emissions_kgco2e_per_kw": xr.DataArray(
                [0.0], dims=("scenario",), coords={"scenario": scenario}
            ),
            "generator_nominal_efficiency_full_load": xr.DataArray(1.0),
            "fuel_lhv_kwh_per_unit_fuel": xr.DataArray(
                [1.0], dims=("scenario",), coords={"scenario": scenario}
            ),
            "fuel_fuel_cost_per_unit_fuel": xr.DataArray(
                [1.0e6], dims=("scenario",), coords={"scenario": scenario}
            ),
            "fuel_direct_emissions_kgco2e_per_unit_fuel": xr.DataArray(
                [0.0], dims=("scenario",), coords={"scenario": scenario}
            ),
        },
        coords={
            "period": ("period", np.arange(periods, dtype=int)),
            "scenario": ("scenario", scenario),
            "resource": ("resource", resource),
        },
        attrs={
            "settings": {
                "grid": {"on_grid": False, "allow_export": False},
                "optimization_constraints": {"enforcement": "scenario_wise"},
                "battery_model": {"loss_model": loss_model},
                "unit_commitment": discrete_unit_sizing,
            },
            "conversion_technology_by_resource": {"Solar": "Solar PV"},
        },
    )
    if loss_model == CONVEX_LOSS_EPIGRAPH:
        seg = xr.IndexVariable("battery_loss_segment", [0])
        data = data.assign_coords({"battery_loss_segment": seg})
        data["battery_charge_loss_slope"] = xr.DataArray(
            [0.0], dims=("battery_loss_segment",), coords={"battery_loss_segment": seg}
        )
        data["battery_charge_loss_intercept"] = xr.DataArray(
            [0.0], dims=("battery_loss_segment",), coords={"battery_loss_segment": seg}
        )
        data["battery_discharge_loss_slope"] = xr.DataArray(
            [0.0], dims=("battery_loss_segment",), coords={"battery_loss_segment": seg}
        )
        data["battery_discharge_loss_intercept"] = xr.DataArray(
            [0.0], dims=("battery_loss_segment",), coords={"battery_loss_segment": seg}
        )
    return data


def _build_and_solve_case(
    data: xr.Dataset,
) -> tuple[lp.Model, dict[str, lp.Variable], xr.Dataset, xr.Dataset]:
    sets = _base_sets(data.sizes["period"])
    model = lp.Model()
    vars_dict = initialize_vars(sets, data, model)
    initialize_constraints(sets, data, vars_dict, model)
    initialize_objective(sets, data, vars_dict, model)
    solution = _solve_with_highs_or_skip(model)
    return model, vars_dict, solution, sets


def test_backward_compatibility_defaults_for_missing_inverter_fields(tmp_path: Path) -> None:
    scenario_coord = xr.DataArray(
        ["scenario_1"], dims=("scenario",), coords={"scenario": ["scenario_1"]}
    )
    resource_coord = xr.DataArray(["Solar"], dims=("resource",), coords={"resource": ["Solar"]})

    renewables_yaml = tmp_path / "renewables.yaml"
    renewables_yaml.write_text(
        dedent(
            """
            renewables:
              - resource: Solar
                investment:
                  by_step:
                    base:
                      nominal_capacity_kw: 1.0
                      specific_investment_cost_per_kw: 800
                      wacc: 0.05
                      grant_share_of_capex: 0.0
                      lifetime_years: 25
                      embedded_emissions_kgco2e_per_kw: 0.0
                technical:
                  inverter_efficiency: 1.0
                  specific_area_m2_per_kw: null
                  max_installable_capacity_kw: null
            """
        ),
        encoding="utf-8",
    )
    battery_yaml = tmp_path / "battery.yaml"
    battery_yaml.write_text(
        dedent(
            """
            battery:
              label: Battery
              investment:
                by_step:
                  base:
                    nominal_capacity_kwh: 1.0
                    specific_investment_cost_per_kwh: 350
                    wacc: 0.05
                    calendar_lifetime_years: 10
                    embedded_emissions_kgco2e_per_kwh: 0.0
                    fixed_om_share_per_year: 0.02
              technical:
                charge_efficiency: 0.95
                discharge_efficiency: 0.96
                initial_soc: 0.5
                depth_of_discharge: 0.8
                max_installable_capacity_kwh: null
            """
        ),
        encoding="utf-8",
    )

    res_ds = _load_renewables_yaml(
        renewables_yaml, scenario_coord=scenario_coord, resource_coord=resource_coord
    )
    bat_ds = _load_battery_yaml(battery_yaml, scenario_coord=scenario_coord)

    assert float(res_ds["res_dc_ac_ratio"].sel(resource="Solar")) == pytest.approx(1.0)
    assert float(
        res_ds["res_inverter_specific_investment_cost_per_kw_ac"].sel(resource="Solar")
    ) == pytest.approx(0.0)
    assert float(res_ds["res_inverter_lifetime_years"].sel(resource="Solar")) == pytest.approx(25.0)
    assert float(
        res_ds["res_inverter_fixed_om_share_per_year"].sel(resource="Solar")
    ) == pytest.approx(0.0)
    assert float(bat_ds["battery_inverter_specific_investment_cost_per_kw"]) == pytest.approx(0.0)
    assert float(bat_ds["battery_inverter_lifetime_years"]) == pytest.approx(10.0)
    assert float(bat_ds["battery_inverter_fixed_om_share_per_year"]) == pytest.approx(0.0)
    assert float(bat_ds["battery_inverter_nominal_power_kw"]) == pytest.approx(1.0)
    assert np.isnan(float(bat_ds["battery_max_charge_c_rate"]))
    assert np.isnan(float(bat_ds["battery_max_discharge_c_rate"]))


def test_battery_legacy_time_inputs_are_ignored_for_typical_year(tmp_path: Path) -> None:
    scenario_coord = xr.DataArray(
        ["scenario_1"], dims=("scenario",), coords={"scenario": ["scenario_1"]}
    )
    battery_yaml = tmp_path / "battery.yaml"
    battery_yaml.write_text(
        dedent(
            """
            battery:
              label: Battery
              investment:
                by_step:
                  base:
                    nominal_capacity_kwh: 1.0
                    specific_investment_cost_per_kwh: 350
                    wacc: 0.05
                    calendar_lifetime_years: 10
                    embedded_emissions_kgco2e_per_kwh: 0.0
                    fixed_om_share_per_year: 0.02
              technical:
                charge_efficiency: 0.95
                discharge_efficiency: 0.96
                initial_soc: 0.5
                depth_of_discharge: 0.8
                inverter_nominal_power_kw: 1.0
                max_discharge_time_hours: 0.0
                max_charge_time_hours: 5.0
                max_installable_capacity_kwh: null
            """
        ),
        encoding="utf-8",
    )

    bat_ds = _load_battery_yaml(battery_yaml, scenario_coord=scenario_coord)

    assert bat_ds.attrs["ignored_legacy_technical_keys"] == [
        "max_charge_time_hours",
        "max_discharge_time_hours",
    ]


def test_constant_efficiency_battery_inverter_limits_and_soc_recursion() -> None:
    data = _base_data(
        periods=4,
        load=[0.0, 0.0, 0.5, 0.5],
        availability=[1.0, 1.0, 0.0, 0.0],
        loss_model="constant_efficiency",
        battery_capex_kwh=0.0,
        battery_inverter_capex_kw=100.0,
        max_charge_c_rate=0.2,
        max_discharge_c_rate=0.2,
    )
    model, vars_dict, solution, _ = _build_and_solve_case(data)

    bat_inv_units = _scalar_value(solution["battery_inverter_units"])
    bat_ch = np.asarray(solution["battery_charge"].values, dtype=float).reshape(-1)
    bat_dis = np.asarray(solution["battery_discharge"].values, dtype=float).reshape(-1)
    soc = np.asarray(solution["battery_soc"].values, dtype=float).reshape(-1)
    e_cap = _scalar_value(solution["battery_units"]) * float(data["battery_nominal_capacity_kwh"])
    bat_inv = bat_inv_units * float(data["battery_inverter_nominal_power_kw"])

    assert np.all(bat_ch <= bat_inv + 1e-7)
    assert np.all(bat_dis <= bat_inv + 1e-7)
    assert e_cap >= 4.99 * bat_inv
    assert soc[0] == pytest.approx(0.0, abs=1e-7)
    for t in range(1, len(soc)):
        expected = soc[t - 1] + bat_ch[t - 1] - bat_dis[t - 1]
        assert soc[t] == pytest.approx(expected, abs=1e-7)
    assert soc[-1] + bat_ch[-1] - bat_dis[-1] == pytest.approx(0.0, abs=1e-7)
    assert float(model.objective.value) >= 0.0


def test_convex_loss_mode_respects_explicit_battery_inverter_reference() -> None:
    data = _base_data(
        periods=4,
        load=[0.0, 0.0, 0.5, 0.5],
        availability=[1.0, 1.0, 0.0, 0.0],
        loss_model=CONVEX_LOSS_EPIGRAPH,
        battery_capex_kwh=0.0,
        battery_inverter_capex_kw=100.0,
        max_charge_c_rate=0.2,
        max_discharge_c_rate=0.2,
    )
    model, _, solution, _ = _build_and_solve_case(data)

    bat_inv_units = _scalar_value(solution["battery_inverter_units"])
    bat_inv = bat_inv_units * float(data["battery_inverter_nominal_power_kw"])
    bat_ch_dc = np.asarray(solution["battery_charge_dc"].values, dtype=float).reshape(-1)
    bat_dis_dc = np.asarray(solution["battery_discharge_dc"].values, dtype=float).reshape(-1)
    bat_ch_loss = np.asarray(solution["battery_charge_loss"].values, dtype=float).reshape(-1)
    bat_dis_loss = np.asarray(solution["battery_discharge_loss"].values, dtype=float).reshape(-1)

    assert np.all(bat_ch_dc <= bat_inv + 1e-7)
    assert np.all(bat_dis_dc <= bat_inv + 1e-7)
    assert np.all(bat_ch_loss >= -1e-9)
    assert np.all(bat_dis_loss >= -1e-9)
    assert float(model.objective.value) >= 0.0


def test_battery_energy_and_inverter_power_can_diverge_economically() -> None:
    data = _base_data(
        periods=4,
        load=[0.0, 0.0, 0.5, 0.5],
        availability=[1.0, 1.0, 0.0, 0.0],
        loss_model="constant_efficiency",
        battery_capex_kwh=0.0,
        battery_inverter_capex_kw=250.0,
        max_charge_c_rate=0.2,
        max_discharge_c_rate=0.2,
    )
    _, vars_dict, solution, _ = _build_and_solve_case(data)
    design_df = build_design_summary_table(data=data, vars=vars_dict, solution=solution)

    battery_energy = float(design_df.loc[0, "battery_installed_kwh"])
    battery_inverter_units = float(design_df.loc[0, "battery_inverter_units"])
    battery_inverter = float(design_df.loc[0, "battery_inverter_power_kw"])

    assert battery_inverter_units > 0.0
    assert battery_inverter > 0.0
    assert battery_energy > battery_inverter
    assert battery_energy >= (5.0 * battery_inverter) - 1e-4


def test_discrete_sizing_makes_battery_inverter_unit_count_integral() -> None:
    data = _base_data(
        periods=4,
        load=[0.0, 0.0, 0.5, 0.5],
        availability=[1.0, 1.0, 0.0, 0.0],
        loss_model="constant_efficiency",
        battery_capex_kwh=0.0,
        battery_inverter_capex_kw=100.0,
        battery_inverter_nominal_power_kw=2.0,
        max_charge_c_rate=0.2,
        max_discharge_c_rate=0.2,
        discrete_unit_sizing=True,
    )
    _, vars_dict, solution, _ = _build_and_solve_case(data)
    design_df = build_design_summary_table(data=data, vars=vars_dict, solution=solution)

    battery_inverter_units = float(design_df.loc[0, "battery_inverter_units"])
    battery_inverter_power_kw = float(design_df.loc[0, "battery_inverter_power_kw"])

    assert battery_inverter_units == pytest.approx(round(battery_inverter_units), abs=1e-7)
    assert battery_inverter_power_kw == pytest.approx(
        battery_inverter_units * float(data["battery_inverter_nominal_power_kw"]),
        abs=1e-7,
    )


def test_renewable_inverter_accounting_and_outputs_are_reported() -> None:
    data = _base_data(
        periods=1,
        load=[1.0],
        availability=[1.0],
        loss_model="constant_efficiency",
        renewable_capex_kw=100.0,
        renewable_inverter_capex_kw_ac=40.0,
        renewable_dc_ac_ratio=2.0,
    )
    model, vars_dict, solution, _ = _build_and_solve_case(data)
    design_df = build_design_summary_table(data=data, vars=vars_dict, solution=solution)
    dispatch_df = build_dispatch_timeseries_table(data=data, vars=vars_dict, solution=solution)
    reporting = build_reporting_tables(
        data=data,
        dispatch_df=dispatch_df,
        design_df=design_df,
        solver_objective_value=float(model.objective.value),
    )

    res_capacity_kw = float(design_df.loc[0, "res_installed_kw__Solar"])
    derived_inverter_kw = float(design_df.loc[0, "res_inverter_installed_kw_ac__Solar"])
    peak_res_dispatch_kw = float(dispatch_df["res_generation__Solar"].max())
    assert derived_inverter_kw == pytest.approx(res_capacity_kw / 2.0, abs=1e-7)
    assert peak_res_dispatch_kw <= derived_inverter_kw + 1e-7

    expected_annuity = float(_crf(0.05, 10.0)) * (
        100.0 * res_capacity_kw + 40.0 * derived_inverter_kw
    )
    assert float(model.objective.value) == pytest.approx(expected_annuity, rel=1e-6, abs=1e-6)
    assert "Solar PV inverter" in reporting.upfront["Technology"].tolist()
    assert "Battery inverter" in reporting.upfront["Technology"].tolist()
    assert (
        "Annualized renewable inverter CAPEX"
        in reporting.expected_cost_components["Component"].tolist()
    )


def test_inverter_capex_uses_explicit_inverter_lifetime() -> None:
    data = _base_data(
        periods=1,
        load=[1.0],
        availability=[1.0],
        loss_model="constant_efficiency",
        renewable_capex_kw=100.0,
        renewable_inverter_capex_kw_ac=40.0,
        renewable_inverter_lifetime_years=20.0,
        renewable_dc_ac_ratio=2.0,
        battery_capex_kwh=200.0,
        battery_inverter_capex_kw=100.0,
        battery_inverter_lifetime_years=15.0,
    )
    model, vars_dict, solution, _ = _build_and_solve_case(data)
    design_df = build_design_summary_table(data=data, vars=vars_dict, solution=solution)
    dispatch_df = build_dispatch_timeseries_table(data=data, vars=vars_dict, solution=solution)
    reporting = build_reporting_tables(
        data=data,
        dispatch_df=dispatch_df,
        design_df=design_df,
        solver_objective_value=float(model.objective.value),
    )

    res_inverter_kw = float(design_df.loc[0, "res_inverter_installed_kw_ac__Solar"])
    battery_inverter_kw = float(design_df.loc[0, "battery_inverter_power_kw"])

    expected_res_inv_annuity = float(_crf(0.05, 20.0)) * 40.0 * res_inverter_kw
    expected_bat_inv_annuity = float(_crf(0.05, 15.0)) * 100.0 * battery_inverter_kw

    res_inv_row = reporting.annuities[
        reporting.annuities["Technology (lifetime)"] == "Solar PV inverter (20y)"
    ]
    bat_inv_row = reporting.annuities[
        reporting.annuities["Technology (lifetime)"] == "Battery inverter (15y)"
    ]

    assert not res_inv_row.empty
    assert not bat_inv_row.empty
    assert float(res_inv_row.iloc[0]["Annuity [/yr]"]) == pytest.approx(
        expected_res_inv_annuity, rel=1e-6, abs=1e-6
    )
    assert float(bat_inv_row.iloc[0]["Annuity [/yr]"]) == pytest.approx(
        expected_bat_inv_annuity, rel=1e-6, abs=1e-6
    )


def test_canonical_typical_year_results_are_self_sufficient_and_exportable(tmp_path: Path) -> None:
    data = _base_data(
        periods=2,
        load=[1.0, 1.0],
        availability=[1.0, 1.0],
        loss_model="constant_efficiency",
        renewable_capex_kw=100.0,
        renewable_inverter_capex_kw_ac=40.0,
        renewable_dc_ac_ratio=2.0,
        battery_inverter_capex_kw=25.0,
    )
    model, vars_dict, solution, _ = _build_and_solve_case(data)

    results = build_typical_year_results(
        project_name="unit_test_typical_year",
        data=data,
        vars=vars_dict,
        solution=solution,
        objective_value=float(model.objective.value),
        status="ok / optimal",
        solver="highs",
        results_dir=None,
        source="session",
    )

    assert results.metadata["project_name"] == "unit_test_typical_year"
    assert not results.dispatch.empty
    assert not results.design_summary.empty
    assert not results.renewable_inverter_design.empty
    assert not results.battery_inverter_design.empty
    assert not results.inverter_metrics.empty
    assert "Installed inverter AC capacity [kW_ac]" in results.renewable_inverter_design.columns
    assert "Peak utilization [%]" in results.inverter_metrics.columns
    assert "Installed inverter units" in results.battery_inverter_design.columns

    renewable_inverter_kw = float(
        results.renewable_inverter_design.loc[0, "Installed inverter AC capacity [kW_ac]"]
    )
    peak_dispatch_kw = float(results.dispatch["res_generation__Solar"].max())
    assert peak_dispatch_kw <= renewable_inverter_kw + 1e-7
    assert float(results.battery_inverter_design.loc[0, "Installed inverter units"]) >= 0.0

    written = export_typical_year_results_package(results=results, out_dir=tmp_path)
    assert (tmp_path / "renewable_inverter_design.csv").exists()
    assert (tmp_path / "battery_inverter_design.csv").exists()
    assert (tmp_path / "inverter_metrics.csv").exists()
    assert written["out_dir"] == str(tmp_path)


def _add_generator_curve(data: xr.Dataset, *, eta_full: float) -> xr.Dataset:
    """Attach a shipped-style efficiency curve (absolute efficiency) to test data."""
    rel = np.array([0.0, 0.20, 0.40, 0.60, 0.80, 1.00])
    multiplier = np.array([0.0, 0.75, 0.82, 0.89, 0.95, 1.00])
    eff = eta_full * multiplier
    cp = xr.IndexVariable("curve_point", np.arange(rel.size))
    data = data.assign_coords({"curve_point": cp})
    data["generator_eff_curve_rel_power"] = xr.DataArray(
        rel, dims=("curve_point",), coords={"curve_point": cp}
    )
    data["generator_eff_curve_eff"] = xr.DataArray(
        eff, dims=("curve_point",), coords={"curve_point": cp}
    )
    return data


def test_typical_year_integer_commitment_full_load_efficiency() -> None:
    # At full load the committed unit runs at 100%, so the effective efficiency equals
    # the datasheet full-load value (no fuel inflation, no flattening to the low-load value).
    eta_full = 0.34
    lhv = 10.0
    data = _base_data(
        periods=2,
        load=[0.0, 1.0],
        availability=[0.0, 0.0],  # renewables cannot serve -> generator must run
    )
    # Block battery so the generator is the only supply for the period-1 load.
    data["battery_max_installable_capacity_kwh"] = xr.DataArray(0.0)
    # Make the generator usable and cheap to run, with a realistic curve.
    data["generator_max_installable_capacity_kw"] = xr.DataArray(np.nan)
    data["generator_specific_investment_cost_per_kw"] = xr.DataArray(1.0)
    data["generator_nominal_efficiency_full_load"] = xr.DataArray(eta_full)
    data["fuel_lhv_kwh_per_unit_fuel"] = xr.DataArray(
        [lhv], dims=("scenario",), coords={"scenario": ["scenario_1"]}
    )
    data["fuel_fuel_cost_per_unit_fuel"] = xr.DataArray(
        [1.0], dims=("scenario",), coords={"scenario": ["scenario_1"]}
    )
    data = _add_generator_curve(data, eta_full=eta_full)
    data.attrs["settings"]["generator"] = {
        "partial_load_modelling_enabled": True,
        "partial_load_commitment": "integer",
    }

    _, vars_dict, solution, _ = _build_and_solve_case(data)

    assert "generator_online_units" in vars_dict
    assert "generator_online_units" in solution.data_vars

    gen_total = float(np.asarray(solution["generator_generation"].values).sum())
    fuel_total = float(np.asarray(solution["fuel_consumption"].values).sum())
    assert gen_total == pytest.approx(1.0, abs=1e-6)
    assert fuel_total > 0.0

    effective_eff = gen_total / (fuel_total * lhv)
    assert effective_eff == pytest.approx(eta_full, rel=1e-4)
    assert effective_eff > 0.30  # strictly above the flattened 0.255 the old surrogate gave


def _willans_q(eta_full: float) -> tuple[float, float]:
    from microgridspy.data_pipeline.generator_partial_load_model import (
        fit_generator_willans_from_curve,
    )

    rel = np.array([0.0, 0.20, 0.40, 0.60, 0.80, 1.00])
    multiplier = np.array([0.0, 0.75, 0.82, 0.89, 0.95, 1.00])
    return fit_generator_willans_from_curve(rel, eta_full * multiplier, error_cls=ValueError)


def _integer_commitment_generator_data(*, load: list[float], min_load: float) -> xr.Dataset:
    eta_full = 0.34
    lhv = 10.0
    data = _base_data(periods=len(load), load=load, availability=[0.0] * len(load))
    data["battery_max_installable_capacity_kwh"] = xr.DataArray(0.0)
    data["generator_max_installable_capacity_kw"] = xr.DataArray(np.nan)
    data["generator_specific_investment_cost_per_kw"] = xr.DataArray(1.0)
    data["generator_nominal_efficiency_full_load"] = xr.DataArray(eta_full)
    data["fuel_lhv_kwh_per_unit_fuel"] = xr.DataArray(
        [lhv], dims=("scenario",), coords={"scenario": ["scenario_1"]}
    )
    data["fuel_fuel_cost_per_unit_fuel"] = xr.DataArray(
        [1.0], dims=("scenario",), coords={"scenario": ["scenario_1"]}
    )
    data = _add_generator_curve(data, eta_full=eta_full)
    data.attrs["settings"]["generator"] = {
        "partial_load_modelling_enabled": True,
        "partial_load_commitment": "integer",
        "min_load_fraction": min_load,
    }
    return data


def test_typical_year_integer_commitment_penalizes_part_load() -> None:
    eta_full = 0.34
    lhv = 10.0
    data = _integer_commitment_generator_data(load=[0.0, 0.7], min_load=0.5)
    _, _, solution, _ = _build_and_solve_case(data)

    n = np.asarray(solution["generator_online_units"].values, dtype=float).reshape(-1)
    gen = float(np.asarray(solution["generator_generation"].values).sum())
    fuel = float(np.asarray(solution["fuel_consumption"].values).sum())

    assert max(n) == pytest.approx(1.0, abs=1e-6)  # one whole unit committed
    assert all(abs(v - round(v)) < 1e-6 for v in n)  # integer-valued commitment
    assert gen == pytest.approx(0.7, abs=1e-6)

    # No-load fuel is charged on the full committed unit even at 70% output, so the
    # effective efficiency is strictly below the datasheet full-load value.
    effective_eff = gen / (fuel * lhv)
    assert effective_eff < eta_full - 0.005
    q0, q1 = _willans_q(eta_full)
    assert fuel == pytest.approx((q1 * 0.7 + q0 * 1.0) / lhv, rel=1e-4)


def test_typical_year_integer_min_load_refuses_sub_minimum_load() -> None:
    data = _integer_commitment_generator_data(load=[0.0, 0.3], min_load=0.5)
    data["max_lost_load_fraction"] = xr.DataArray(1.0)  # allow the sub-min load to go unserved
    _, _, solution, _ = _build_and_solve_case(data)

    gen = float(np.asarray(solution["generator_generation"].values).sum())
    lost_load = float(np.asarray(solution["lost_load"].values).sum())
    # A 0.3 kW load is below the 0.5 kW minimum stable load, so the genset stays off.
    assert gen == pytest.approx(0.0, abs=1e-6)
    assert lost_load == pytest.approx(0.3, abs=1e-6)
