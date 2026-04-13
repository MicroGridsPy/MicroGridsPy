# generation_planning/modeling/objective.py
from __future__ import annotations

from typing import Dict

import numpy as np
import xarray as xr
import linopy as lp

from core.typical_year_model.params import get_params


class InputValidationError(RuntimeError):
    pass


BATTERY_REGULARIZATION_EPSILON = 1e-4
GRID_REGULARIZATION_EPSILON = 1e-4


def _crf(r: xr.DataArray | float, n: xr.DataArray | float) -> xr.DataArray:
    """
    Capital Recovery Factor:
        CRF = r * (1+r)^n / ((1+r)^n - 1)
    with r = WACC, n = lifetime (years); if r=0 -> 1/n.
        """
    r = xr.DataArray(r)
    n = xr.DataArray(n)
    one_plus = 1.0 + r
    pow_term = one_plus ** n
    crf_val = (r * pow_term) / (pow_term - 1.0)
    return xr.where(r == 0.0, 1.0 / n, crf_val)


def initialize_objective(
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: Dict[str, lp.Variable],
    model: lp.Model,
) -> None:
    """
    Objective: minimize total expected annual system cost:

      total = annualized_investment_cost
            + annual_fixed_om_cost
            + sum_s w_s * annual_operating_cost(s)

    Annualized investment cost uses CRF and includes CAPEX annualization
    (after grants).

    Fixed O&M is computed once from installed capacity and is independent of
    scenarios and dispatch.

    Annual operating cost includes:
      - fuel cost
      - grid import cost (if on-grid)
      - grid export revenue (if allow_export)
      - renewable production subsidy (revenue)
      - lost load penalty (if any)
      - emissions cost for scope 1, scope 2 (if on-grid), and scope 3
        (if emission_cost_per_kgco2e > 0)
    """
    if not isinstance(sets, xr.Dataset):
        raise InputValidationError("initialize_objective: sets must be an xarray.Dataset.")
    if not isinstance(data, xr.Dataset):
        raise InputValidationError("initialize_objective: data must be an xarray.Dataset.")
    if not isinstance(vars, dict):
        raise InputValidationError("initialize_objective: vars must be a dict of linopy variables.")
    if not isinstance(model, lp.Model):
        raise InputValidationError("initialize_objective: model must be a linopy.Model.")

    # ------------------------------------------------------------------
    # Coords / weights
    # ------------------------------------------------------------------
    for c in ("scenario", "resource", "period"):
        if c not in sets.coords:
            raise InputValidationError(f"initialize_objective: missing coord '{c}' in sets.")

    scenario = sets.coords["scenario"]
    resource = sets.coords["resource"]
    period = sets.coords["period"]

    p = get_params(data)
    w_s = p.scenario_weight  # (scenario,)

    # Flags
    on_grid = p.is_grid_on()
    allow_export = p.is_grid_export_enabled()

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------
    res_units = vars["res_units"]                # (resource,)
    bat_units = vars["battery_units"]            # scalar
    gen_units = vars["generator_units"]          # scalar

    res_gen = vars["res_generation"]             # (period, scenario, resource)
    bat_ch = vars["battery_charge"]              # (period, scenario)
    bat_dis = vars["battery_discharge"]          # (period, scenario)
    fuel_cons = vars["fuel_consumption"]         # (period, scenario)
    lost_load = vars["lost_load"]                # (period, scenario)

    # Grid cost accounting uses raw PCC interchange variables; transmission
    # efficiency is applied separately in the energy balance and scope-2 terms.
    grid_imp = vars.get("grid_import", None)     # (period, scenario) if on_grid
    grid_exp = vars.get("grid_export", None)     # (period, scenario) if allow_export

    # ------------------------------------------------------------------
    # Tech parameters (from your current data.py naming)
    # ------------------------------------------------------------------
    # Renewables
    res_nom_kw = p.res_nominal_capacity_kw                         # (resource,)
    res_capex_kw = p.res_specific_investment_cost_per_kw           # (resource,)
    res_life_y = p.res_lifetime_years                              # (resource,)
    res_wacc = p.res_wacc                                           # (resource,)
    res_grant = p.res_grant_share_of_capex                         # (resource,)
    # scenario-dependent subsidy, but scenario-independent fixed O&M
    res_fom_share = p.res_fixed_om_share_per_year                  # (resource,)
    res_subsidy_kwh = p.res_production_subsidy_per_kwh             # (scenario, resource)
    res_emb_kg_per_kw = p.res_embedded_emissions_kgco2e_per_kw      # (scenario, resource)

    # Battery
    bat_nom_kwh = p.battery_nominal_capacity_kwh                   # scalar
    bat_capex_kwh = p.battery_specific_investment_cost_per_kwh     # scalar
    bat_life_y = p.battery_calendar_lifetime_years                 # scalar
    bat_wacc = p.battery_wacc                                       # scalar
    bat_fom_share = p.battery_fixed_om_share_per_year              # scalar
    bat_emb_kg_per_kwh = p.battery_embedded_emissions_kgco2e_per_kwh  # (scenario,)

    # Generator
    gen_nom_kw = p.generator_nominal_capacity_kw                  # scalar
    gen_capex_kw = p.generator_specific_investment_cost_per_kw    # scalar
    gen_life_y = p.generator_lifetime_years                       # scalar
    gen_wacc = p.generator_wacc                                   # scalar
    gen_fom_share = p.generator_fixed_om_share_per_year           # scalar
    gen_emb_kg_per_kw = p.generator_embedded_emissions_kgco2e_per_kw  # (scenario,)

    # Fuel (scenario-dependent)
    fuel_cost = p.fuel_fuel_cost_per_unit_fuel                           # (scenario,)
    fuel_dir_kg_per_unit = p.fuel_direct_emissions_kgco2e_per_unit_fuel  # (scenario,)

    # Grid prices (if on-grid)
    if on_grid:
        grid_import_price = p.grid_import_price                    # (period, scenario)
        grid_eta = p.grid_transmission_efficiency if p.grid_transmission_efficiency is not None else 1.0
        grid_em_factor = (
            p.grid_emissions_factor_kgco2e_per_kwh
            if p.grid_emissions_factor_kgco2e_per_kwh is not None
            else 0.0
        )
        if allow_export:
            grid_export_price = p.grid_export_price                # (period, scenario)

    # Policy / externalities
    lost_load_cost = p.lost_load_cost_per_kwh                      # scalar or (scenario,)
    emission_cost = p.emission_cost_per_kgco2e                     # scalar or (scenario,)

    # ------------------------------------------------------------------
    # 1) Annualized investment cost + scenario-independent fixed O&M
    # ------------------------------------------------------------------
    # Installed capacities
    cap_res_kw = res_units * res_nom_kw                               # (resource,)
    cap_bat_kwh = bat_units * bat_nom_kwh                             # scalar
    cap_gen_kw = gen_units * gen_nom_kw                               # scalar

    # CRFs
    res_crf = _crf(res_wacc, res_life_y)                              # (resource,)
    bat_crf = _crf(bat_wacc, bat_life_y)                              # scalar
    gen_crf = _crf(gen_wacc, gen_life_y)                              # scalar

    # Effective CAPEX after grant
    res_capex_eff_kw = (1.0 - res_grant) * res_capex_kw               # (resource,)

    # Annualized CAPEX via CRF
    annual_res_capex = (res_crf * res_capex_eff_kw * cap_res_kw).sum("resource")         # scalar
    annual_bat_capex = bat_crf * bat_capex_kwh * cap_bat_kwh                             # scalar
    annual_gen_capex = gen_crf * gen_capex_kw * cap_gen_kw                               # scalar
    annualized_investment_cost = annual_res_capex + annual_bat_capex + annual_gen_capex  # scalar

    # Fixed O&M
    annual_res_fom = (res_capex_kw * res_fom_share * cap_res_kw).sum("resource")  # scalar
    annual_bat_fom = bat_capex_kwh * bat_fom_share * cap_bat_kwh                   # scalar
    annual_gen_fom = gen_capex_kw * gen_fom_share * cap_gen_kw                     # scalar
    annual_fixed_om_cost = annual_res_fom + annual_bat_fom + annual_gen_fom        # scalar

    # ------------------------------------------------------------------
    # 2) Annual operating cost per scenario (then expected value)
    # ------------------------------------------------------------------
    # Fuel cost: sum_t fuel_cons[t,s] * fuel_cost[s]
    fuel_cost_s = (fuel_cons.sum("period") * fuel_cost)  # (scenario,)

    # Grid import/export
    if on_grid:
        grid_import_cost_s = (grid_imp * grid_import_price).sum("period")  # (scenario,)
        if allow_export:
            grid_export_revenue_s = (grid_exp * grid_export_price).sum("period")  # (scenario,)
        else:
            # If not allowing export, set revenue to zero
            grid_export_revenue_s = xr.DataArray(
                np.zeros((int(scenario.size),), dtype=float),
                coords={"scenario": scenario},
                dims=("scenario",),
            )
    else:
        # If not on-grid, set import cost and export revenue to zero
        grid_import_cost_s = xr.DataArray(
            np.zeros((int(scenario.size),), dtype=float),
            coords={"scenario": scenario},
            dims=("scenario",),
        )
        grid_export_revenue_s = xr.DataArray(
            np.zeros((int(scenario.size),), dtype=float),
            coords={"scenario": scenario},
            dims=("scenario",),
        )

    # Renewable production subsidy (revenue): sum_t,r res_gen[t,s,r] * subsidy[s,r]
    res_subsidy_rev_s = (res_gen.sum("period") * res_subsidy_kwh).sum("resource")  # (scenario,)

    # Lost-load penalty
    ll_cost_s = lost_load.sum("period") * lost_load_cost  # (scenario,)

    # ------------------------------------------------------------------
    # 3) Emissions cost (optional)
    # ------------------------------------------------------------------
    # Direct operational emissions from fuel
    direct_ops_kg_s = fuel_cons.sum("period") * fuel_dir_kg_per_unit  # (scenario,)
    scope2_grid_kg_s = (
        (grid_imp * grid_eta).sum("period") * grid_em_factor
        if on_grid and grid_imp is not None
        else xr.DataArray(
            np.zeros((int(scenario.size),), dtype=float),
            coords={"scenario": scenario},
            dims=("scenario",),
        )
    )

    # Embodied emissions (annualized by lifetime)
    # Renewables: (cap_res_kw[resource] * emb_kg_per_kw[scenario,resource] / life_y[resource]) -> (scenario,)
    embodied_kg_res_s = ((cap_res_kw * res_emb_kg_per_kw) / res_life_y).sum("resource")    # (scenario,)
    embodied_kg_gen_s = (cap_gen_kw * gen_emb_kg_per_kw) / gen_life_y                      # (scenario,)
    embodied_kg_bat_s = (cap_bat_kwh * bat_emb_kg_per_kwh) / bat_life_y                    # (scenario,)
    embodied_kg_s = embodied_kg_res_s + embodied_kg_gen_s + embodied_kg_bat_s              # (scenario,)
    emissions_cost_s = emission_cost * (direct_ops_kg_s + scope2_grid_kg_s + embodied_kg_s)  # (scenario,)

    # Total externalities cost
    externalities_cost_s = ll_cost_s + emissions_cost_s  # (scenario,)

    # ------------------------------------------------------------------
    # Total annual operating cost per scenario
    # ------------------------------------------------------------------
    annual_operating_cost_s = (
        fuel_cost_s
        + grid_import_cost_s
        - grid_export_revenue_s
        - res_subsidy_rev_s
        + externalities_cost_s
    )  # (scenario,)

    expected_annual_operating_cost = (w_s * annual_operating_cost_s).sum("scenario")  # scalar

    # ------------------------------------------------------------------
    # Battery dispatch regularization (internal tie-breaker)
    # ------------------------------------------------------------------
    # Encourage solutions without simultaneous charge/discharge and avoid
    # degenerate circulation loops. Not a degradation model.
    #
    # Small penalties in currency per kWh discourage counter-flows without changing the model class.
    # scenario-weighted throughput (kWh)
    bat_throughput_s = (bat_ch + bat_dis).sum("period")   # (scenario,)
    bat_reg_cost = BATTERY_REGULARIZATION_EPSILON * (w_s * bat_throughput_s).sum("scenario")  # scalar

    # Small anti-circulation penalty for grid import/export loops.
    if on_grid and grid_imp is not None:
        grid_throughput_s = grid_imp.sum("period")
        if allow_export and grid_exp is not None:
            grid_throughput_s = grid_throughput_s + grid_exp.sum("period")
        grid_reg_cost = GRID_REGULARIZATION_EPSILON * (w_s * grid_throughput_s).sum("scenario")
    else:
        grid_reg_cost = xr.DataArray(0.0)

    # ------------------------------------------------------------------
    # Objective
    # ------------------------------------------------------------------
    total_annual_cost = (
        annualized_investment_cost
        + annual_fixed_om_cost
        + expected_annual_operating_cost
        + bat_reg_cost
        + grid_reg_cost
    )
    model.add_objective(total_annual_cost, overwrite=True)

