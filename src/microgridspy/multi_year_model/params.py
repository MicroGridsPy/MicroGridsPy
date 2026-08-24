from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import xarray as xr


@dataclass(frozen=True)
class Params:
    settings: dict[str, Any]

    # Common core series
    load_demand: xr.DataArray | None
    resource_availability: xr.DataArray | None
    scenario_weight: xr.DataArray | None

    # Policy / externalities
    min_renewable_penetration: xr.DataArray | None
    max_lost_load_fraction: xr.DataArray | None
    lost_load_cost_per_kwh: xr.DataArray | None
    land_availability_m2: xr.DataArray | None
    emission_cost_per_kgco2e: xr.DataArray | None

    # Renewables
    res_nominal_capacity_kw: xr.DataArray | None
    res_lifetime_years: xr.DataArray | None
    res_specific_investment_cost_per_kw: xr.DataArray | None
    res_inverter_specific_investment_cost_per_kw_ac: xr.DataArray | None
    res_inverter_lifetime_years: xr.DataArray | None
    res_wacc: xr.DataArray | None
    res_grant_share_of_capex: xr.DataArray | None
    res_embedded_emissions_kgco2e_per_kw: xr.DataArray | None
    res_fixed_om_share_per_year: xr.DataArray | None
    res_inverter_fixed_om_share_per_year: xr.DataArray | None
    res_production_subsidy_per_kwh: xr.DataArray | None
    res_dc_ac_ratio: xr.DataArray | None
    res_inverter_efficiency: xr.DataArray | None
    res_specific_area_m2_per_kw: xr.DataArray | None
    res_max_installable_capacity_kw: xr.DataArray | None
    res_capacity_degradation_rate_per_year: xr.DataArray | None

    # Battery
    battery_nominal_capacity_kwh: xr.DataArray | None
    battery_specific_investment_cost_per_kwh: xr.DataArray | None
    battery_inverter_specific_investment_cost_per_kw: xr.DataArray | None
    battery_inverter_lifetime_years: xr.DataArray | None
    battery_wacc: xr.DataArray | None
    battery_calendar_lifetime_years: xr.DataArray | None
    battery_fixed_om_share_per_year: xr.DataArray | None
    battery_inverter_fixed_om_share_per_year: xr.DataArray | None
    battery_embedded_emissions_kgco2e_per_kwh: xr.DataArray | None
    battery_max_installable_capacity_kwh: xr.DataArray | None
    battery_charge_efficiency: xr.DataArray | None
    battery_discharge_efficiency: xr.DataArray | None
    battery_initial_soc: xr.DataArray | None
    battery_initial_soh: xr.DataArray | None
    battery_depth_of_discharge: xr.DataArray | None
    battery_max_charge_c_rate: xr.DataArray | None
    battery_max_discharge_c_rate: xr.DataArray | None
    battery_cycle_fade_coefficient_per_kwh_throughput: xr.DataArray | None
    battery_calendar_time_increment_per_year: xr.DataArray | None
    battery_capacity_degradation_rate_per_year: xr.DataArray | None

    # Generator / fuel
    generator_nominal_capacity_kw: xr.DataArray | None
    generator_max_installable_capacity_kw: xr.DataArray | None
    generator_nominal_efficiency_full_load: xr.DataArray | None
    generator_capacity_degradation_rate_per_year: xr.DataArray | None
    generator_specific_investment_cost_per_kw: xr.DataArray | None
    generator_lifetime_years: xr.DataArray | None
    generator_wacc: xr.DataArray | None
    generator_fixed_om_share_per_year: xr.DataArray | None
    generator_embedded_emissions_kgco2e_per_kw: xr.DataArray | None
    fuel_lhv_kwh_per_unit_fuel: xr.DataArray | None
    fuel_cost_per_unit_fuel: xr.DataArray | None
    fuel_fuel_cost_per_unit_fuel: xr.DataArray | None
    fuel_direct_emissions_kgco2e_per_unit_fuel: xr.DataArray | None

    # Grid
    grid_line_capacity_kw: xr.DataArray | None
    grid_transmission_efficiency: xr.DataArray | None
    grid_renewable_share: xr.DataArray | None
    grid_emissions_factor_kgco2e_per_kwh: xr.DataArray | None
    grid_availability: xr.DataArray | None
    grid_import_price: xr.DataArray | None
    grid_export_price: xr.DataArray | None

    # Optional curve vars + coord
    generator_eff_curve_rel_power: xr.DataArray | None
    generator_eff_curve_eff: xr.DataArray | None
    generator_fuel_curve_rel_fuel_use: xr.DataArray | None
    curve_point: xr.DataArray | None

    def is_grid_on(self) -> bool:
        return bool((self.settings.get("grid", {}) or {}).get("on_grid", False))

    def is_grid_export_enabled(self) -> bool:
        return bool((self.settings.get("grid", {}) or {}).get("allow_export", False))


def get_params(ds: xr.Dataset) -> Params:
    settings = (ds.attrs or {}).get("settings", {})
    if not isinstance(settings, dict):
        settings = {}

    def _opt(name: str) -> xr.DataArray | None:
        return ds[name] if name in ds.data_vars else None

    curve_point = ds.coords["curve_point"] if "curve_point" in ds.coords else None

    return Params(
        settings=settings,
        load_demand=_opt("load_demand"),
        resource_availability=_opt("resource_availability"),
        scenario_weight=_opt("scenario_weight"),
        min_renewable_penetration=_opt("min_renewable_penetration"),
        max_lost_load_fraction=_opt("max_lost_load_fraction"),
        lost_load_cost_per_kwh=_opt("lost_load_cost_per_kwh"),
        land_availability_m2=_opt("land_availability_m2"),
        emission_cost_per_kgco2e=_opt("emission_cost_per_kgco2e"),
        res_nominal_capacity_kw=_opt("res_nominal_capacity_kw"),
        res_lifetime_years=_opt("res_lifetime_years"),
        res_specific_investment_cost_per_kw=_opt("res_specific_investment_cost_per_kw"),
        res_inverter_specific_investment_cost_per_kw_ac=_opt("res_inverter_specific_investment_cost_per_kw_ac"),
        res_inverter_lifetime_years=_opt("res_inverter_lifetime_years"),
        res_wacc=_opt("res_wacc"),
        res_grant_share_of_capex=_opt("res_grant_share_of_capex"),
        res_embedded_emissions_kgco2e_per_kw=_opt("res_embedded_emissions_kgco2e_per_kw"),
        res_fixed_om_share_per_year=_opt("res_fixed_om_share_per_year"),
        res_inverter_fixed_om_share_per_year=_opt("res_inverter_fixed_om_share_per_year"),
        res_production_subsidy_per_kwh=_opt("res_production_subsidy_per_kwh"),
        res_dc_ac_ratio=_opt("res_dc_ac_ratio"),
        res_inverter_efficiency=_opt("res_inverter_efficiency"),
        res_specific_area_m2_per_kw=_opt("res_specific_area_m2_per_kw"),
        res_max_installable_capacity_kw=_opt("res_max_installable_capacity_kw"),
        res_capacity_degradation_rate_per_year=_opt("res_capacity_degradation_rate_per_year"),
        battery_nominal_capacity_kwh=_opt("battery_nominal_capacity_kwh"),
        battery_specific_investment_cost_per_kwh=_opt("battery_specific_investment_cost_per_kwh"),
        battery_inverter_specific_investment_cost_per_kw=_opt("battery_inverter_specific_investment_cost_per_kw"),
        battery_inverter_lifetime_years=_opt("battery_inverter_lifetime_years"),
        battery_wacc=_opt("battery_wacc"),
        battery_calendar_lifetime_years=_opt("battery_calendar_lifetime_years"),
        battery_fixed_om_share_per_year=_opt("battery_fixed_om_share_per_year"),
        battery_inverter_fixed_om_share_per_year=_opt("battery_inverter_fixed_om_share_per_year"),
        battery_embedded_emissions_kgco2e_per_kwh=_opt("battery_embedded_emissions_kgco2e_per_kwh"),
        battery_max_installable_capacity_kwh=_opt("battery_max_installable_capacity_kwh"),
        battery_charge_efficiency=_opt("battery_charge_efficiency"),
        battery_discharge_efficiency=_opt("battery_discharge_efficiency"),
        battery_initial_soc=_opt("battery_initial_soc"),
        battery_initial_soh=_opt("battery_initial_soh"),
        battery_depth_of_discharge=_opt("battery_depth_of_discharge"),
        battery_max_charge_c_rate=_opt("battery_max_charge_c_rate"),
        battery_max_discharge_c_rate=_opt("battery_max_discharge_c_rate"),
        battery_cycle_fade_coefficient_per_kwh_throughput=_opt("battery_cycle_fade_coefficient_per_kwh_throughput"),
        battery_calendar_time_increment_per_year=_opt("battery_calendar_time_increment_per_year"),
        battery_capacity_degradation_rate_per_year=_opt("battery_capacity_degradation_rate_per_year"),
        generator_nominal_capacity_kw=_opt("generator_nominal_capacity_kw"),
        generator_max_installable_capacity_kw=_opt("generator_max_installable_capacity_kw"),
        generator_nominal_efficiency_full_load=_opt("generator_nominal_efficiency_full_load"),
        generator_capacity_degradation_rate_per_year=_opt("generator_capacity_degradation_rate_per_year"),
        generator_specific_investment_cost_per_kw=_opt("generator_specific_investment_cost_per_kw"),
        generator_lifetime_years=_opt("generator_lifetime_years"),
        generator_wacc=_opt("generator_wacc"),
        generator_fixed_om_share_per_year=_opt("generator_fixed_om_share_per_year"),
        generator_embedded_emissions_kgco2e_per_kw=_opt("generator_embedded_emissions_kgco2e_per_kw"),
        fuel_lhv_kwh_per_unit_fuel=_opt("fuel_lhv_kwh_per_unit_fuel"),
        fuel_cost_per_unit_fuel=_opt("fuel_cost_per_unit_fuel"),
        fuel_fuel_cost_per_unit_fuel=_opt("fuel_fuel_cost_per_unit_fuel"),
        fuel_direct_emissions_kgco2e_per_unit_fuel=_opt("fuel_direct_emissions_kgco2e_per_unit_fuel"),
        grid_line_capacity_kw=_opt("grid_line_capacity_kw"),
        grid_transmission_efficiency=_opt("grid_transmission_efficiency"),
        grid_renewable_share=_opt("grid_renewable_share"),
        grid_emissions_factor_kgco2e_per_kwh=_opt("grid_emissions_factor_kgco2e_per_kwh"),
        grid_availability=_opt("grid_availability"),
        grid_import_price=_opt("grid_import_price"),
        grid_export_price=_opt("grid_export_price"),
        generator_eff_curve_rel_power=_opt("generator_eff_curve_rel_power"),
        generator_eff_curve_eff=_opt("generator_eff_curve_eff"),
        generator_fuel_curve_rel_fuel_use=_opt("generator_fuel_curve_rel_fuel_use"),
        curve_point=curve_point,
    )
