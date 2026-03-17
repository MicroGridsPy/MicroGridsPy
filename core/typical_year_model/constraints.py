# generation_planning/modeling/constraints.py
from __future__ import annotations

from typing import Dict

import numpy as np
import xarray as xr
import linopy as lp

from core.typical_year_model.params import get_params


class InputValidationError(RuntimeError):
    pass


def initialize_constraints(
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: Dict[str, lp.Variable],
    model: lp.Model,
) -> None:
    """
    Add steady_state (typical-year) constraints to the linopy model.

    Conventions (consistent with your current implementation):
      - period = 0..8759
      - scenario optional but present always (scenario_1 if disabled)
      - renewables availability in data["resource_availability"] with dims (period, scenario, resource)
      - "units" design variables scale nominal capacities from YAML templates
    """
    if not isinstance(sets, xr.Dataset):
        raise InputValidationError("initialize_constraints: `sets` must be an xarray.Dataset.")
    if not isinstance(data, xr.Dataset):
        raise InputValidationError("initialize_constraints: `data` must be an xarray.Dataset.")
    if not isinstance(vars, dict):
        raise InputValidationError("initialize_constraints: `vars` must be a dict of linopy variables.")

    # ---------------------------------------------------------------------
    # Coords
    # ---------------------------------------------------------------------
    for c in ("period", "scenario", "resource"):
        if c not in sets.coords:
            raise InputValidationError(f"initialize_constraints: missing required coord in sets: '{c}'")

    period = sets.coords["period"]
    scenario = sets.coords["scenario"]

    # ---------------------------------------------------------------------
    # Flags and enforcement mode (from attrs)
    # ---------------------------------------------------------------------
    p = get_params(data)
    on_grid = p.is_grid_on()
    allow_export = p.is_grid_export_enabled()
    enforcement = p.constraints_enforcement(default="scenario_wise")
    if enforcement not in ("expected", "scenario_wise"):
        raise InputValidationError(
            f"Invalid optimization_constraints.enforcement='{enforcement}'. "
            "Allowed: 'expected' | 'scenario_wise'."
        )

    # ---------------------------------------------------------------------
    # Parameters (data vars)
    # ---------------------------------------------------------------------
    # Time series
    load_demand = p.load_demand  # (period, scenario)
    resource_availability = p.resource_availability  # (period, scenario, resource)

    # Scenario weights (always present)
    w_s = p.scenario_weight  # (scenario,)

    # Renewables tech params
    res_nom_kw = p.res_nominal_capacity_kw  # (resource)
    res_inv_eta = p.res_inverter_efficiency  # (resource)

    # Optional land and max installable
    land_m2 = p.land_availability_m2  # scalar 
    res_area_m2_per_kw = p.res_specific_area_m2_per_kw  # (resource)
    res_max_kw = p.res_max_installable_capacity_kw  # (resource) may contain NaN

    # Generator params
    gen_nom_kw = p.generator_nominal_capacity_kw  # ()
    gen_eta_full = p.generator_nominal_efficiency_full_load  # ()
    fuel_lhv = p.fuel_lhv_kwh_per_unit_fuel  # (scenario,)

    # Battery params
    bat_nom_kwh = p.battery_nominal_capacity_kwh  # ()
    eta_c = p.battery_charge_efficiency  # (scenario,)
    eta_d = p.battery_discharge_efficiency  # (scenario,)
    soc0 = p.battery_initial_soc  # (scenario,) fraction
    dod = p.battery_depth_of_discharge  # (scenario,) fraction
    t_ch = p.battery_max_charge_time_hours  # (scenario,)
    t_dis = p.battery_max_discharge_time_hours  # (scenario,)

    # System constraints params
    min_res_pen = p.min_renewable_penetration  # scalar or (scenario,)
    max_ll_frac = p.max_lost_load_fraction  # scalar or (scenario,)

    # Grid params (if on-grid)
    if on_grid:
        line_cap_kw = p.grid_line_capacity_kw  # (scenario,)
        grid_eta = p.grid_transmission_efficiency  # (scenario,)
        grid_ren_share = p.grid_renewable_share if p.grid_renewable_share is not None else 0.0
        grid_avail = p.grid_availability  # (period, scenario)

    # ---------------------------------------------------------------------
    # Variables (aliases)
    # ---------------------------------------------------------------------
    res_units = vars["res_units"]  # (resource,)
    bat_units = vars["battery_units"]  # scalar
    gen_units = vars["generator_units"]  # scalar

    res_gen = vars["res_generation"]  # (period, scenario, resource)
    gen_gen = vars["generator_generation"]  # (period, scenario)
    fuel_cons = vars["fuel_consumption"]  # (period, scenario)
    bat_ch = vars["battery_charge"]  # (period, scenario)
    bat_dis = vars["battery_discharge"]  # (period, scenario)
    soc = vars["battery_soc"]  # (period, scenario)
    ll = vars["lost_load"]  # (period, scenario)

    grid_imp = vars.get("grid_import", None)  # (period, scenario) if on_grid. N.B: energy bought at PCC (before losses)
    grid_exp = vars.get("grid_export", None)  # (period, scenario) if allow_export. N.B: energy sold at PCC (before losses)

    # ---------------------------------------------------------------------
    # 1) Renewable generation limited by availability and installed capacity
    # Constraint:
    #   res_generation(t,s,r) <= availability(t,s,r) * res_units(r) * res_nominal_kw(r) * res_inv_eta(r)
    # ---------------------------------------------------------------------
    rhs_res = resource_availability * res_units * res_nom_kw * res_inv_eta
    model.add_constraints(res_gen <= rhs_res, name="res_generation_cap")

    # ---------------------------------------------------------------------
    # 2) Renewable max installable capacity (if provided)
    # Constraint:
    #   res_units(resource) * res_nom_kw(resource) <= res_max_kw(resource)
    #   only where res_max_kw is finite
    # ---------------------------------------------------------------------
    finite = np.isfinite(res_max_kw)
    res_max_kw_finite = res_max_kw.where(finite, drop=True)
    if res_max_kw_finite.sizes.get("resource", 0) > 0:
        model.add_constraints(
            res_units.sel(resource=res_max_kw_finite.resource) * res_nom_kw.sel(resource=res_max_kw_finite.resource)
            <= res_max_kw_finite,
            name="res_max_installable_capacity")

    # ---------------------------------------------------------------------
    # 3) Generator production capacity
    #
    # generator_generation(t,s) <= generator_units * gen_nom_kw
    # ---------------------------------------------------------------------
    rhs_gen = gen_units * gen_nom_kw
    model.add_constraints(gen_gen <= rhs_gen, name="generator_generation_cap")

    # ---------------------------------------------------------------------
    # 4) Fuel ↔ energy relationship
    #   - If no partial-load curve: equality with nominal efficiency
    #   - If partial-load enabled: convex piecewise lower bound on fuel_cons
    # ---------------------------------------------------------------------

    pl_rel = p.generator_eff_curve_rel_power
    pl_eff = p.generator_eff_curve_eff

    pl_points_ok = (
        pl_rel is not None and pl_eff is not None
        and ("curve_point" in pl_rel.dims) and ("curve_point" in pl_eff.dims)
        and (pl_rel.sizes["curve_point"] >= 2)
    )

    # Helper: if a scenario row is all-NaN, treat as no-curve for that scenario
    def _scenario_has_curve(scen: str) -> bool:
        if not pl_points_ok:
            return False
        r = pl_rel.sel(scenario=scen)
        e = pl_eff.sel(scenario=scen)
        return (np.isfinite(r.values).any() and np.isfinite(e.values).any())

    scenario_labels = [str(s) for s in sets.coords["scenario"].values.tolist()]
    scenarios_with_pl = [s for s in scenario_labels if _scenario_has_curve(s)]
    scenarios_without_pl = [s for s in scenario_labels if s not in scenarios_with_pl]

    # --- Case A) scenarios without PL curve: nominal efficiency equality
    if len(scenarios_without_pl) > 0:
        model.add_constraints(
            gen_gen.sel(scenario=scenarios_without_pl)
            == fuel_cons.sel(scenario=scenarios_without_pl) * fuel_lhv.sel(scenario=scenarios_without_pl) * gen_eta_full,
            name="fuel_to_power_nominal_eta",
        )

    # --- Case B) scenarios with PL curve: convex piecewise lower bound
    if pl_points_ok and len(scenarios_with_pl) > 0:
        # segment coordinate: 0..P-2
        P = int(pl_rel.sizes["curve_point"])
        seg = xr.IndexVariable("segment", np.arange(P - 1))

        for s in scenarios_with_pl:
            # Scalar per scenario
            lhv_s = fuel_lhv.sel(scenario=s)  # scalar DA
            cap = gen_nom_kw                  # scalar DA (kW per unit)

            # Breakpoints for this scenario
            r_full = pl_rel.sel(scenario=s)   # (curve_point,)
            e_full = pl_eff.sel(scenario=s)   # (curve_point,)

            # Basic sanity (optional but recommended)
            # - drop NaNs (if present) by requiring all finite
            if not (np.isfinite(r_full.values).all() and np.isfinite(e_full.values).all()):
                raise ValueError(f"Partial-load curve for scenario '{s}' contains NaNs; provide full curve_point series.")

            # r0,r1 and eta0,eta1
            r0 = r_full.isel(curve_point=seg)         # (segment,)
            r1 = r_full.isel(curve_point=seg + 1)     # (segment,)
            eta0 = e_full.isel(curve_point=seg)       # (segment,)
            eta1 = e_full.isel(curve_point=seg + 1)   # (segment,)

            # Convert to power at breakpoints for ONE unit (kW)
            p0 = cap * r0                              # (segment,)
            p1 = cap * r1                              # (segment,)

            # Fuel at breakpoints for ONE unit (unit_fuel/h since Δt=1h)
            # fc = P / (eta * LHV)
            fc0 = p0 / (eta0 * lhv_s)                  # (segment,)
            fc1 = p1 / (eta1 * lhv_s)                  # (segment,)

            # Segment slope in fuel per kWh (unit_fuel/kWh)
            denom = (p1 - p0)
            slope = xr.where(denom != 0.0, (fc1 - fc0) / denom, 0.0)  # (segment,)

            # Variables for this scenario
            gen_ts = gen_gen.sel(scenario=s)           # (period,)
            fuel_ts = fuel_cons.sel(scenario=s)        # (period,)

            # Broadcast to (period, segment)
            gen_b = gen_ts.expand_dims({"segment": seg})
            fuel_b = fuel_ts.expand_dims({"segment": seg})

            # RHS: slope*(gen - p0*units) + fc0*units
            rhs = slope * (gen_b - p0 * gen_units) + fc0 * gen_units

            model.add_constraints(
                fuel_b >= rhs,
                name=f"fuel_to_power_partial_load_{s}",
            )


    # ---------------------------------------------------------------------
    # 5) Battery charge/discharge power limits
    #
    # battery_charge(t,s)    <= (battery_units * bat_nom_kwh) / t_ch
    # battery_discharge(t,s) <= (battery_units * bat_nom_kwh) / t_dis
    # ---------------------------------------------------------------------
    model.add_constraints(bat_ch <= (bat_units * bat_nom_kwh) / t_ch, name="battery_charge_limit")
    model.add_constraints(bat_dis <= (bat_units * bat_nom_kwh) / t_dis, name="battery_discharge_limit")

    # ---------------------------------------------------------------------
    # 6) Battery SOC dynamics (hourly Δt=1h) with cyclic end condition
    #
    # soc[0,s] = soc0(s)*Ecap   (initial condition)
    # soc[t,s] = soc[t-1,s] + eta_c(s)*bat_ch[t-1,s] - (1/eta_d(s))*bat_dis
    # soc[T-1,s] = soc0(s)*Ecap  (cyclic condition: end returns to initial)
    # where Ecap = battery_units * bat_nom_kwh
    # ---------------------------------------------------------------------
    T = int(period.size)
    Ecap = bat_units * bat_nom_kwh

    model.add_constraints(soc.isel(period=0) == soc0 * Ecap, name="soc_initial")

    if T > 1:
        model.add_constraints(
            soc.isel(period=slice(1, None))
            == soc.isel(period=slice(0, -1))
            + eta_c * bat_ch.isel(period=slice(0, -1))
            - bat_dis.isel(period=slice(0, -1)) / eta_d,
            name="soc_balance",
        )

    # cyclic closure (do NOT also force soc[T-1]==soc0*Ecap)
    model.add_constraints(
        soc.isel(period=T-1)
        + eta_c * bat_ch.isel(period=T-1)
        - bat_dis.isel(period=T-1) / eta_d
        == soc0 * Ecap,
        name="soc_cyclic",
    )

    model.add_constraints(soc <= Ecap, name="soc_upper")
    model.add_constraints(soc >= (1.0 - dod) * Ecap, name="soc_lower")

    # ---------------------------------------------------------------------
    # 7) Grid import/export limits (if enabled)
    # Constraints:
    #   grid_import(t,s) <= grid_availability(t,s) * line_cap_kw(s)
    #   grid_export(t,s) <= grid_availability(t,s) * line_cap_kw(s)
    # ---------------------------------------------------------------------
    if on_grid:
        # Import limited by availability and line capacity and efficiency
        rhs_imp = grid_avail * line_cap_kw
        model.add_constraints(grid_imp <= rhs_imp, name="grid_import_cap")

        if allow_export:
            rhs_exp = grid_avail * line_cap_kw
            model.add_constraints(grid_exp <= rhs_exp, name="grid_export_cap")

    # ---------------------------------------------------------------------
    # 8) Energy balance per (period, scenario)
    # Energy balance:
    #   Σ_r res_generation(t,s,r)
    # + generator_generation(t,s)
    # + grid_import(t,s) [if on_grid]
    # - grid_export(t,s) [if allow_export]
    # + battery_discharge(t,s)
    # - battery_charge(t,s)
    # + lost_load(t,s)
    # == load_demand(t,s)
    # ---------------------------------------------------------------------
    res_sum = res_gen.sum("resource")  # (period, scenario)

    if on_grid and allow_export:
        model.add_constraints(
            res_sum + gen_gen + ((grid_imp * grid_eta) - (grid_exp * grid_eta)) + (bat_dis - bat_ch) + ll == load_demand,
            name="energy_balance",
        )
    elif on_grid and not allow_export:
        model.add_constraints(
            res_sum + gen_gen + (grid_imp * grid_eta) + (bat_dis - bat_ch) + ll == load_demand,
            name="energy_balance",
        )
    else:
        model.add_constraints(
            res_sum + gen_gen + (bat_dis - bat_ch) + ll == load_demand,
            name="energy_balance",
        )

    # ---------------------------------------------------------------------
    # 9) System-level constraints: min renewable penetration & max lost load
    #
    # Enforcement modes:
    #  - scenario_wise: constraints hold for each scenario separately
    #  - expected: constraints hold on scenario-weighted totals
    # ---------------------------------------------------------------------

    # Total demand energy per scenario
    E_demand_s = load_demand.sum("period")  # (scenario,)
    E_ll_s     = ll.sum("period")          # (scenario,)
    E_res_s    = res_sum.sum("period")     # (scenario,)
    E_gen_s    = gen_gen.sum("period")     # (scenario,)

    if on_grid:
        E_grid_s = (grid_imp * grid_eta).sum("period")  # (scenario,) delivered imported energy
        E_grid_ren_s = (grid_imp * grid_eta * grid_ren_share).sum("period")  # (scenario,)
    else:
        E_grid_s = xr.DataArray(
            np.zeros((int(scenario.size),), dtype=float),
            coords={"scenario": scenario},
            dims=("scenario",),
        )
        E_grid_ren_s = xr.DataArray(
            np.zeros((int(scenario.size),), dtype=float),
            coords={"scenario": scenario},
            dims=("scenario",),
        )

    # --- (A) Max lost-load share
    #     sum_t lost_load(t,s) <= max_ll_frac(s) * sum_t load(t,s)
    if enforcement == "scenario_wise":
        model.add_constraints(E_ll_s <= max_ll_frac * E_demand_s, name="max_lost_load_share")
    else:
        # expected: Σ_s w_s * LL_s <= max_ll_frac * Σ_s w_s * Demand_s
        E_ll_exp     = (E_ll_s * w_s).sum("scenario")       # scalar
        E_demand_exp = (E_demand_s * w_s).sum("scenario")   # scalar
        model.add_constraints(E_ll_exp <= max_ll_frac * E_demand_exp, name="max_lost_load_share_expected")

    # --- (B) Minimum renewable penetration
    #   E_total = E_res + E_gen + E_grid_import
    #   E_renew = E_res + renewable share of delivered grid imports
    # Only add if min_res_pen > 0.0
    if min_res_pen > 0.0:
        if enforcement == "scenario_wise":
            E_total_s = E_res_s + E_gen_s + E_grid_s
            E_renew_s = E_res_s + E_grid_ren_s
            model.add_constraints(E_renew_s >= min_res_pen * E_total_s, name="min_renewable_penetration")
        else:
            E_total_exp = ((E_res_s + E_gen_s + E_grid_s) * w_s).sum("scenario")  # scalar
            E_renew_exp = ((E_res_s + E_grid_ren_s) * w_s).sum("scenario")        # scalar
            model.add_constraints(E_renew_exp >= min_res_pen * E_total_exp, name="min_renewable_penetration_expected")

    # ---------------------------------------------------------------------
    # 10) Land availability (renewables only)
    #
    # area_used = Σ_r (res_units(r) * res_nominal_kw(r) * res_area_m2_per_kw(r))
    # ---------------------------------------------------------------------
    area_used = (res_units * res_nom_kw * res_area_m2_per_kw).sum("resource") # scalar
    model.add_constraints(area_used <= land_m2, name="land_availability") 



