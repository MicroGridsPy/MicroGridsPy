# generation_planning/modeling/constraints.py
from __future__ import annotations

from typing import Dict

import numpy as np
import xarray as xr
import linopy as lp

from core.data_pipeline.battery_loss_model import CONVEX_LOSS_EPIGRAPH, normalize_battery_loss_model
from core.data_pipeline.utils import finite_nonnegative_scalar_limit
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
    battery_loss_model = normalize_battery_loss_model(
        ((data.attrs or {}).get("settings", {}).get("battery_model", {}) or {}).get("loss_model"),
        default="constant_efficiency",
    )
    battery_model_settings = ((data.attrs or {}).get("settings", {}).get("battery_model", {}) or {})
    degradation_settings = (battery_model_settings.get("degradation_model", {}) or {})
    degradation_state_enabled = bool(degradation_settings.get("cycle_fade_enabled", False)) or bool(
        degradation_settings.get("calendar_fade_enabled", False)
    )
    if degradation_state_enabled:
        raise InputValidationError(
            "Battery degradation constraints are not supported in the steady_state typical-year formulation. "
            "Use the dynamic multi-year formulation for cycle fade, calendar fade, SoH update, and SoH-driven capacity restriction."
        )
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
    gen_max_installable_kw = p.generator_max_installable_capacity_kw  # scalar, may be NaN
    fuel_lhv = p.fuel_lhv_kwh_per_unit_fuel  # (scenario,)

    # Battery params
    bat_nom_kwh = p.battery_nominal_capacity_kwh  # ()
    bat_max_installable_kwh = p.battery_max_installable_capacity_kwh  # scalar or None
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
    bat_ch_dc = vars.get("battery_charge_dc", None)
    bat_dis_dc = vars.get("battery_discharge_dc", None)
    bat_ch_loss = vars.get("battery_charge_loss", None)
    bat_dis_loss = vars.get("battery_discharge_loss", None)
    ll = vars["lost_load"]  # (period, scenario)

    # Grid interchange variables are modeled at the point of common coupling
    # (PCC), before applying transmission efficiency in the internal balance.
    grid_imp = vars.get("grid_import", None)  # (period, scenario) if on_grid
    grid_exp = vars.get("grid_export", None)  # (period, scenario) if allow_export

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
    if bool(np.any((res_max_kw.where(finite, other=0.0) < 0.0).values)):
        raise InputValidationError("res_max_installable_capacity_kw must be non-negative when provided.")
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

    gen_cap_limit = finite_nonnegative_scalar_limit(
        gen_max_installable_kw.values,
        name="generator_max_installable_capacity_kw",
        error_cls=InputValidationError,
    )
    if gen_cap_limit is not None:
        model.add_constraints(
            gen_units * gen_nom_kw <= gen_cap_limit,
            name="generator_max_installable_capacity",
        )

    # ---------------------------------------------------------------------
    # 4) Fuel ↔ energy relationship
    #   - If no partial-load curve: equality with nominal efficiency
    #   - If partial-load enabled: convex piecewise lower bound on fuel_cons
    # ---------------------------------------------------------------------

    pl_rel = p.generator_eff_curve_rel_power
    pl_fuel_rel = p.generator_fuel_curve_rel_fuel_use

    pl_points_ok = (
        pl_rel is not None and pl_fuel_rel is not None
        and ("curve_point" in pl_rel.dims) and ("curve_point" in pl_fuel_rel.dims)
        and (pl_rel.sizes["curve_point"] >= 2)
    )

    if pl_points_ok:
        # segment coordinate: 0..P-2
        P = int(pl_rel.sizes["curve_point"])
        seg = xr.IndexVariable("segment", np.arange(P - 1))
        scenario_labels = [str(s) for s in sets.coords["scenario"].values.tolist()]

        for s in scenario_labels:
            # Scalar per scenario
            lhv_s = fuel_lhv.sel(scenario=s)  # scalar DA
            cap = gen_nom_kw                  # scalar DA (kW per unit)

            # Shared technology curve
            r_full = pl_rel   # (curve_point,)
            phi_full = pl_fuel_rel   # (curve_point,)

            # Basic sanity (optional but recommended)
            # - drop NaNs (if present) by requiring all finite
            if not (np.isfinite(r_full.values).all() and np.isfinite(phi_full.values).all()):
                raise ValueError("Generator partial-load fuel-use curve contains NaNs; provide full curve_point series.")

            # r0,r1 and phi0,phi1
            r0 = r_full.isel(curve_point=seg)         # (segment,)
            r1 = r_full.isel(curve_point=seg + 1)     # (segment,)
            phi0 = phi_full.isel(curve_point=seg)     # (segment,)
            phi1 = phi_full.isel(curve_point=seg + 1) # (segment,)

            # Convert to power at breakpoints for ONE unit (kW)
            p0 = cap * r0                              # (segment,)
            p1 = cap * r1                              # (segment,)

            # Fuel at breakpoints for ONE unit (unit_fuel/h since Δt=1h)
            # fc = P / (eta * LHV)
            fc0 = cap * phi0 / lhv_s                   # (segment,)
            fc1 = cap * phi1 / lhv_s                   # (segment,)

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
    else:
        model.add_constraints(
            gen_gen == fuel_cons * fuel_lhv * gen_eta_full,
            name="fuel_to_power_nominal_eta",
        )
    # ---------------------------------------------------------------------
    # 5) Battery charge/discharge power limits
    #
    # battery_charge(t,s)    <= (battery_units * bat_nom_kwh) / t_ch
    # battery_discharge(t,s) <= (battery_units * bat_nom_kwh) / t_dis
    # ---------------------------------------------------------------------
    if battery_loss_model != CONVEX_LOSS_EPIGRAPH:
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
    if bat_max_installable_kwh is not None:
        battery_cap_limit = finite_nonnegative_scalar_limit(
            bat_max_installable_kwh.values,
            name="battery_max_installable_capacity_kwh",
            error_cls=InputValidationError,
        )
        if battery_cap_limit is not None:
            model.add_constraints(
                Ecap <= battery_cap_limit,
                name="battery_max_installable_capacity",
            )

    if battery_loss_model == CONVEX_LOSS_EPIGRAPH:
        if not all(v is not None for v in (bat_ch_dc, bat_dis_dc, bat_ch_loss, bat_dis_loss)):
            raise InputValidationError(
                "Advanced battery loss mode is active, but internal battery DC/loss variables are missing."
            )
        required_curve_vars = (
            "battery_charge_loss_slope",
            "battery_charge_loss_intercept",
            "battery_discharge_loss_slope",
            "battery_discharge_loss_intercept",
        )
        missing_curve_vars = [name for name in required_curve_vars if name not in data.data_vars]
        if missing_curve_vars:
            raise InputValidationError(
                f"Advanced battery loss mode is active, but required battery curve variables are missing: {missing_curve_vars}"
            )

        seg = data.coords["battery_loss_segment"]
        ch_slope = data["battery_charge_loss_slope"]
        ch_intercept = data["battery_charge_loss_intercept"]
        dis_slope = data["battery_discharge_loss_slope"]
        dis_intercept = data["battery_discharge_loss_intercept"]

        # In advanced mode the internal battery power reference is the DC-side
        # power derived from energy capacity and max charge/discharge time.
        # Public AC powers are then coupled through explicit loss variables.
        p_ref_ch = (Ecap / t_ch)
        p_ref_dis = (Ecap / t_dis)

        model.add_constraints(
            bat_ch_dc <= p_ref_ch,
            name="battery_charge_dc_limit",
        )
        model.add_constraints(
            bat_dis_dc <= p_ref_dis,
            name="battery_discharge_dc_limit",
        )
        model.add_constraints(
            bat_ch <= p_ref_ch + bat_ch_loss,
            name="battery_charge_limit",
        )
        model.add_constraints(
            bat_dis <= p_ref_dis,
            name="battery_discharge_limit",
        )
        model.add_constraints(
            bat_ch == bat_ch_dc + bat_ch_loss,
            name="battery_charge_ac_dc_coupling",
        )
        model.add_constraints(
            bat_dis == bat_dis_dc - bat_dis_loss,
            name="battery_discharge_ac_dc_coupling",
        )

        bat_ch_dc_b = bat_ch_dc.expand_dims({"battery_loss_segment": seg})
        bat_ch_loss_b = bat_ch_loss.expand_dims({"battery_loss_segment": seg})
        bat_dis_dc_b = bat_dis_dc.expand_dims({"battery_loss_segment": seg})
        bat_dis_loss_b = bat_dis_loss.expand_dims({"battery_loss_segment": seg})

        model.add_constraints(
            bat_ch_loss_b >= (ch_slope * bat_ch_dc_b) + (ch_intercept * p_ref_ch),
            name="battery_charge_loss_epigraph",
        )
        model.add_constraints(
            bat_dis_loss_b >= (dis_slope * bat_dis_dc_b) + (dis_intercept * p_ref_dis),
            name="battery_discharge_loss_epigraph",
        )

        if T > 1:
            model.add_constraints(
                soc.isel(period=slice(1, None))
                == soc.isel(period=slice(0, -1))
                + bat_ch_dc.isel(period=slice(0, -1))
                - bat_dis_dc.isel(period=slice(0, -1)),
                name="soc_balance",
            )

        model.add_constraints(
            soc.isel(period=T-1)
            + bat_ch_dc.isel(period=T-1)
            - bat_dis_dc.isel(period=T-1)
            == soc0 * Ecap,
            name="soc_cyclic",
        )
        model.add_constraints(soc.isel(period=0) == soc0 * Ecap, name="soc_initial")
        soc_upper_bound = Ecap
        soc_lower_bound = (1.0 - dod) * Ecap
    else:
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
        soc_upper_bound = Ecap
        soc_lower_bound = (1.0 - dod) * Ecap

    model.add_constraints(soc <= soc_upper_bound, name="soc_upper")
    model.add_constraints(soc >= soc_lower_bound, name="soc_lower")

    # ---------------------------------------------------------------------
    # 7) Grid import/export limits (if enabled)
    # Constraints:
    #   grid_import(t,s) <= grid_availability(t,s) * line_cap_kw(s)
    #   grid_export(t,s) <= grid_availability(t,s) * line_cap_kw(s)
    # With hourly steps, the kW line capacity is used directly as a per-step
    # kWh interchange bound (Δt = 1 h).
    # ---------------------------------------------------------------------
    if on_grid:
        # Line limits apply to raw PCC interchange. Transmission efficiency is
        # applied later in the energy balance, not in the capacity bound.
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
    # + grid_import(t,s) * grid_eta(s) [if on_grid]
    # - grid_export(t,s) * grid_eta(s) [if allow_export]
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
    # 10) Land availability (renewables only, only if user provides a finite
    #     non-negative limit)
    #
    # area_used = Σ_r (res_units(r) * res_nominal_kw(r) * res_area_m2_per_kw(r))
    # ---------------------------------------------------------------------
    land_limit = finite_nonnegative_scalar_limit(
        land_m2.values,
        name="land_availability_m2",
        error_cls=InputValidationError,
    )
    if land_limit is not None:
        area_used = (res_units * res_nom_kw * res_area_m2_per_kw).sum("resource") # scalar
        model.add_constraints(area_used <= land_limit, name="land_availability")



