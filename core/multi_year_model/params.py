from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import xarray as xr


@dataclass(frozen=True)
class Params:
    settings: dict[str, Any]

    # Common core series
    load_demand: Optional[xr.DataArray]
    resource_availability: Optional[xr.DataArray]
    scenario_weight: Optional[xr.DataArray]

    # Policy / externalities
    min_renewable_penetration: Optional[xr.DataArray]
    max_lost_load_fraction: Optional[xr.DataArray]
    lost_load_cost_per_kwh: Optional[xr.DataArray]
    land_availability_m2: Optional[xr.DataArray]
    emission_cost_per_kgco2e: Optional[xr.DataArray]

    # Renewables
    res_nominal_capacity_kw: Optional[xr.DataArray]
    res_lifetime_years: Optional[xr.DataArray]
    res_specific_investment_cost_per_kw: Optional[xr.DataArray]
    res_wacc: Optional[xr.DataArray]
    res_grant_share_of_capex: Optional[xr.DataArray]
    res_embedded_emissions_kgco2e_per_kw: Optional[xr.DataArray]
    res_fixed_om_share_per_year: Optional[xr.DataArray]
    res_production_subsidy_per_kwh: Optional[xr.DataArray]
    res_inverter_efficiency: Optional[xr.DataArray]
    res_specific_area_m2_per_kw: Optional[xr.DataArray]
    res_max_installable_capacity_kw: Optional[xr.DataArray]
    res_capacity_degradation_rate_per_year: Optional[xr.DataArray]

    # Battery
    battery_nominal_capacity_kwh: Optional[xr.DataArray]
    battery_specific_investment_cost_per_kwh: Optional[xr.DataArray]
    battery_wacc: Optional[xr.DataArray]
    battery_calendar_lifetime_years: Optional[xr.DataArray]
    battery_fixed_om_share_per_year: Optional[xr.DataArray]
    battery_embedded_emissions_kgco2e_per_kwh: Optional[xr.DataArray]
    battery_max_installable_capacity_kwh: Optional[xr.DataArray]
    battery_charge_efficiency: Optional[xr.DataArray]
    battery_discharge_efficiency: Optional[xr.DataArray]
    battery_initial_soc: Optional[xr.DataArray]
    battery_initial_soh: Optional[xr.DataArray]
    battery_depth_of_discharge: Optional[xr.DataArray]
    battery_max_charge_time_hours: Optional[xr.DataArray]
    battery_max_discharge_time_hours: Optional[xr.DataArray]
    battery_cycle_fade_coefficient_per_kwh_throughput: Optional[xr.DataArray]
    battery_calendar_time_increment_per_year: Optional[xr.DataArray]
    battery_capacity_degradation_rate_per_year: Optional[xr.DataArray]

    # Generator / fuel
    generator_nominal_capacity_kw: Optional[xr.DataArray]
    generator_max_installable_capacity_kw: Optional[xr.DataArray]
    generator_nominal_efficiency_full_load: Optional[xr.DataArray]
    generator_capacity_degradation_rate_per_year: Optional[xr.DataArray]
    generator_specific_investment_cost_per_kw: Optional[xr.DataArray]
    generator_lifetime_years: Optional[xr.DataArray]
    generator_wacc: Optional[xr.DataArray]
    generator_fixed_om_share_per_year: Optional[xr.DataArray]
    generator_embedded_emissions_kgco2e_per_kw: Optional[xr.DataArray]
    fuel_lhv_kwh_per_unit_fuel: Optional[xr.DataArray]
    fuel_cost_per_unit_fuel: Optional[xr.DataArray]
    fuel_fuel_cost_per_unit_fuel: Optional[xr.DataArray]
    fuel_direct_emissions_kgco2e_per_unit_fuel: Optional[xr.DataArray]

    # Grid
    grid_line_capacity_kw: Optional[xr.DataArray]
    grid_transmission_efficiency: Optional[xr.DataArray]
    grid_renewable_share: Optional[xr.DataArray]
    grid_emissions_factor_kgco2e_per_kwh: Optional[xr.DataArray]
    grid_availability: Optional[xr.DataArray]
    grid_import_price: Optional[xr.DataArray]
    grid_export_price: Optional[xr.DataArray]

    # Optional curve vars + coord
    generator_eff_curve_rel_power: Optional[xr.DataArray]
    generator_eff_curve_eff: Optional[xr.DataArray]
    generator_fuel_curve_rel_fuel_use: Optional[xr.DataArray]
    curve_point: Optional[xr.DataArray]

    def is_grid_on(self) -> bool:
        return bool(((self.settings.get("grid", {}) or {}).get("on_grid", False)))

    def is_grid_export_enabled(self) -> bool:
        return bool(((self.settings.get("grid", {}) or {}).get("allow_export", False)))


def get_params(ds: xr.Dataset) -> Params:
    settings = (ds.attrs or {}).get("settings", {})
    if not isinstance(settings, dict):
        settings = {}

    def _opt(name: str) -> Optional[xr.DataArray]:
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
        res_wacc=_opt("res_wacc"),
        res_grant_share_of_capex=_opt("res_grant_share_of_capex"),
        res_embedded_emissions_kgco2e_per_kw=_opt("res_embedded_emissions_kgco2e_per_kw"),
        res_fixed_om_share_per_year=_opt("res_fixed_om_share_per_year"),
        res_production_subsidy_per_kwh=_opt("res_production_subsidy_per_kwh"),
        res_inverter_efficiency=_opt("res_inverter_efficiency"),
        res_specific_area_m2_per_kw=_opt("res_specific_area_m2_per_kw"),
        res_max_installable_capacity_kw=_opt("res_max_installable_capacity_kw"),
        res_capacity_degradation_rate_per_year=_opt("res_capacity_degradation_rate_per_year"),
        battery_nominal_capacity_kwh=_opt("battery_nominal_capacity_kwh"),
        battery_specific_investment_cost_per_kwh=_opt("battery_specific_investment_cost_per_kwh"),
        battery_wacc=_opt("battery_wacc"),
        battery_calendar_lifetime_years=_opt("battery_calendar_lifetime_years"),
        battery_fixed_om_share_per_year=_opt("battery_fixed_om_share_per_year"),
        battery_embedded_emissions_kgco2e_per_kwh=_opt("battery_embedded_emissions_kgco2e_per_kwh"),
        battery_max_installable_capacity_kwh=_opt("battery_max_installable_capacity_kwh"),
        battery_charge_efficiency=_opt("battery_charge_efficiency"),
        battery_discharge_efficiency=_opt("battery_discharge_efficiency"),
        battery_initial_soc=_opt("battery_initial_soc"),
        battery_initial_soh=_opt("battery_initial_soh"),
        battery_depth_of_discharge=_opt("battery_depth_of_discharge"),
        battery_max_charge_time_hours=_opt("battery_max_charge_time_hours"),
        battery_max_discharge_time_hours=_opt("battery_max_discharge_time_hours"),
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
