from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import xarray as xr


@dataclass(frozen=True)
class Params:
    settings: dict[str, Any]

    # Core time series
    load_demand: xr.DataArray
    resource_availability: xr.DataArray
    grid_import_price: Optional[xr.DataArray]
    grid_export_price: Optional[xr.DataArray]
    grid_availability: Optional[xr.DataArray]

    # Weights / policy / externalities
    scenario_weight: xr.DataArray
    min_renewable_penetration: xr.DataArray
    max_lost_load_fraction: xr.DataArray
    lost_load_cost_per_kwh: xr.DataArray
    land_availability_m2: xr.DataArray
    emission_cost_per_kgco2e: xr.DataArray

    # Renewables
    res_nominal_capacity_kw: xr.DataArray
    res_specific_investment_cost_per_kw: xr.DataArray
    res_lifetime_years: xr.DataArray
    res_wacc: xr.DataArray
    res_grant_share_of_capex: xr.DataArray
    res_fixed_om_share_per_year: xr.DataArray
    res_production_subsidy_per_kwh: xr.DataArray
    res_embedded_emissions_kgco2e_per_kw: xr.DataArray
    res_inverter_efficiency: xr.DataArray
    res_specific_area_m2_per_kw: xr.DataArray
    res_max_installable_capacity_kw: xr.DataArray

    # Battery
    battery_nominal_capacity_kwh: xr.DataArray
    battery_specific_investment_cost_per_kwh: xr.DataArray
    battery_calendar_lifetime_years: xr.DataArray
    battery_wacc: xr.DataArray
    battery_fixed_om_share_per_year: xr.DataArray
    battery_embedded_emissions_kgco2e_per_kwh: xr.DataArray
    battery_charge_efficiency: xr.DataArray
    battery_discharge_efficiency: xr.DataArray
    battery_initial_soc: xr.DataArray
    battery_depth_of_discharge: xr.DataArray
    battery_max_charge_time_hours: xr.DataArray
    battery_max_discharge_time_hours: xr.DataArray

    # Generator / fuel
    generator_nominal_capacity_kw: xr.DataArray
    generator_specific_investment_cost_per_kw: xr.DataArray
    generator_lifetime_years: xr.DataArray
    generator_wacc: xr.DataArray
    generator_fixed_om_share_per_year: xr.DataArray
    generator_embedded_emissions_kgco2e_per_kw: xr.DataArray
    generator_nominal_efficiency_full_load: xr.DataArray
    fuel_lhv_kwh_per_unit_fuel: xr.DataArray
    fuel_fuel_cost_per_unit_fuel: xr.DataArray
    fuel_direct_emissions_kgco2e_per_unit_fuel: xr.DataArray

    # Grid
    grid_line_capacity_kw: Optional[xr.DataArray]
    grid_transmission_efficiency: Optional[xr.DataArray]
    grid_renewable_share: Optional[xr.DataArray]
    grid_emissions_factor_kgco2e_per_kwh: Optional[xr.DataArray]

    # Optional curve vars
    generator_eff_curve_rel_power: Optional[xr.DataArray]
    generator_eff_curve_eff: Optional[xr.DataArray]

    def is_grid_on(self) -> bool:
        return bool(((self.settings.get("grid", {}) or {}).get("on_grid", False)))

    def is_grid_export_enabled(self) -> bool:
        return bool(((self.settings.get("grid", {}) or {}).get("allow_export", False)))

    def constraints_enforcement(self, default: str = "scenario_wise") -> str:
        return str(
            ((self.settings.get("optimization_constraints", {}) or {}).get("enforcement", default))
        )


def get_params(ds: xr.Dataset) -> Params:
    settings = (ds.attrs or {}).get("settings", {})
    if not isinstance(settings, dict):
        settings = {}

    def _opt(name: str) -> Optional[xr.DataArray]:
        return ds[name] if name in ds.data_vars else None

    return Params(
        settings=settings,
        load_demand=ds["load_demand"],
        resource_availability=ds["resource_availability"],
        grid_import_price=_opt("grid_import_price"),
        grid_export_price=_opt("grid_export_price"),
        grid_availability=_opt("grid_availability"),
        scenario_weight=ds["scenario_weight"],
        min_renewable_penetration=ds["min_renewable_penetration"],
        max_lost_load_fraction=ds["max_lost_load_fraction"],
        lost_load_cost_per_kwh=ds["lost_load_cost_per_kwh"],
        land_availability_m2=ds["land_availability_m2"],
        emission_cost_per_kgco2e=ds["emission_cost_per_kgco2e"],
        res_nominal_capacity_kw=ds["res_nominal_capacity_kw"],
        res_specific_investment_cost_per_kw=ds["res_specific_investment_cost_per_kw"],
        res_lifetime_years=ds["res_lifetime_years"],
        res_wacc=ds["res_wacc"],
        res_grant_share_of_capex=ds["res_grant_share_of_capex"],
        res_fixed_om_share_per_year=ds["res_fixed_om_share_per_year"],
        res_production_subsidy_per_kwh=ds["res_production_subsidy_per_kwh"],
        res_embedded_emissions_kgco2e_per_kw=ds["res_embedded_emissions_kgco2e_per_kw"],
        res_inverter_efficiency=ds["res_inverter_efficiency"],
        res_specific_area_m2_per_kw=ds["res_specific_area_m2_per_kw"],
        res_max_installable_capacity_kw=ds["res_max_installable_capacity_kw"],
        battery_nominal_capacity_kwh=ds["battery_nominal_capacity_kwh"],
        battery_specific_investment_cost_per_kwh=ds["battery_specific_investment_cost_per_kwh"],
        battery_calendar_lifetime_years=ds["battery_calendar_lifetime_years"],
        battery_wacc=ds["battery_wacc"],
        battery_fixed_om_share_per_year=ds["battery_fixed_om_share_per_year"],
        battery_embedded_emissions_kgco2e_per_kwh=ds["battery_embedded_emissions_kgco2e_per_kwh"],
        battery_charge_efficiency=ds["battery_charge_efficiency"],
        battery_discharge_efficiency=ds["battery_discharge_efficiency"],
        battery_initial_soc=ds["battery_initial_soc"],
        battery_depth_of_discharge=ds["battery_depth_of_discharge"],
        battery_max_charge_time_hours=ds["battery_max_charge_time_hours"],
        battery_max_discharge_time_hours=ds["battery_max_discharge_time_hours"],
        generator_nominal_capacity_kw=ds["generator_nominal_capacity_kw"],
        generator_specific_investment_cost_per_kw=ds["generator_specific_investment_cost_per_kw"],
        generator_lifetime_years=ds["generator_lifetime_years"],
        generator_wacc=ds["generator_wacc"],
        generator_fixed_om_share_per_year=ds["generator_fixed_om_share_per_year"],
        generator_embedded_emissions_kgco2e_per_kw=ds["generator_embedded_emissions_kgco2e_per_kw"],
        generator_nominal_efficiency_full_load=ds["generator_nominal_efficiency_full_load"],
        fuel_lhv_kwh_per_unit_fuel=ds["fuel_lhv_kwh_per_unit_fuel"],
        fuel_fuel_cost_per_unit_fuel=ds["fuel_fuel_cost_per_unit_fuel"],
        fuel_direct_emissions_kgco2e_per_unit_fuel=ds["fuel_direct_emissions_kgco2e_per_unit_fuel"],
        grid_line_capacity_kw=_opt("grid_line_capacity_kw"),
        grid_transmission_efficiency=_opt("grid_transmission_efficiency"),
        grid_renewable_share=_opt("grid_renewable_share"),
        grid_emissions_factor_kgco2e_per_kwh=_opt("grid_emissions_factor_kgco2e_per_kwh"),
        generator_eff_curve_rel_power=_opt("generator_eff_curve_rel_power"),
        generator_eff_curve_eff=_opt("generator_eff_curve_eff"),
    )

