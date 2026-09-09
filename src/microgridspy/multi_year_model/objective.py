from __future__ import annotations

import linopy as lp
import numpy as np
import xarray as xr

from microgridspy.multi_year_model.lifecycle import (
    map_inv_step_to_year,
    replacement_active_mask,
    replacement_commission_mask,
    year_ordinal,
)
from microgridspy.multi_year_model.params import get_params


class InputValidationError(RuntimeError):
    pass


def _require_da(name: str, da: xr.DataArray | None) -> xr.DataArray:
    if da is None:
        raise InputValidationError(f"Missing required parameter/data variable: '{name}'")
    return da


def _require_finite_da(name: str, da: xr.DataArray | None) -> xr.DataArray:
    out = _require_da(name, da)
    vals = np.asarray(out.values, dtype=float)
    mask = ~np.isfinite(vals)
    if np.any(mask):
        n_bad = int(mask.sum())
        n_tot = int(vals.size)
        raise InputValidationError(
            f"Parameter '{name}' contains non-finite values ({n_bad}/{n_tot}). "
            "Please fix NaN/inf values in project inputs before solving."
        )
    return out


def _finite_or_zero(da: xr.DataArray | float | int) -> xr.DataArray:
    out = xr.DataArray(da)
    return xr.where(np.isfinite(out), out, 0.0)


def _crf(rate: xr.DataArray | float, lifetime: xr.DataArray | float) -> xr.DataArray:
    """
    Capital Recovery Factor:
      CRF = r * (1+r)^n / ((1+r)^n - 1), and if r==0 -> 1/n.
    """
    r = xr.DataArray(rate)
    n = xr.DataArray(lifetime)
    one_plus = 1.0 + r
    pow_term = one_plus**n
    crf_val = (r * pow_term) / (pow_term - 1.0)
    crf_val = xr.where(r == 0.0, 1.0 / n, crf_val)
    return xr.where(n > 0.0, crf_val, 0.0)


def _discount_factor_by_year(sets: xr.Dataset, social_rate: float) -> xr.DataArray:
    y_ord = year_ordinal(sets)
    return 1.0 / ((1.0 + float(social_rate)) ** y_ord)


def initialize_objective(
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, lp.Variable],
    model: lp.Model,
) -> None:
    if not isinstance(sets, xr.Dataset):
        raise InputValidationError("initialize_objective: sets must be an xarray.Dataset.")
    if not isinstance(data, xr.Dataset):
        raise InputValidationError("initialize_objective: data must be an xarray.Dataset.")
    if not isinstance(vars, dict):
        raise InputValidationError("initialize_objective: vars must be a dict of linopy variables.")
    if not isinstance(model, lp.Model):
        raise InputValidationError("initialize_objective: model must be a linopy.Model.")

    for c in ("period", "year", "inv_step", "scenario", "resource"):
        if c not in sets.coords:
            raise InputValidationError(f"initialize_objective: missing coord '{c}' in sets.")

    p = get_params(data)
    on_grid = p.is_grid_on()
    allow_export = p.is_grid_export_enabled()

    # Note: if missing in attrs, keep rs=0.0 to avoid blocking objective build.
    rs = float(p.settings.get("social_discount_rate", 0.0) or 0.0)
    if rs <= -1.0:
        raise InputValidationError(f"Invalid social_discount_rate={rs}. Must be > -1.")
    disc_y = _discount_factor_by_year(sets, rs)  # (year,)

    w_s = _require_finite_da("scenario_weight", p.scenario_weight)

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------
    res_units = vars["res_units"]  # (inv_step, resource)
    bat_units = vars["battery_units"]  # (inv_step,)
    bat_inv_power = vars["battery_inverter_power"]  # (inv_step,)
    gen_units = vars["generator_units"]  # (inv_step,)

    res_gen = vars["res_generation"]  # (period, year, scenario, resource)
    fuel_cons = vars["fuel_consumption"]  # (period, year, scenario, inv_step)
    lost_load = vars["lost_load"]  # (period, year, scenario)
    # Grid cost accounting uses raw PCC interchange variables; transmission
    # efficiency is applied separately in the energy balance and scope-2 terms.
    grid_imp = vars.get("grid_import", None)  # (period, year, scenario)
    grid_exp = vars.get("grid_export", None)  # (period, year, scenario)

    # ------------------------------------------------------------------
    # Required investment parameters
    # ------------------------------------------------------------------
    res_nom_kw = _require_finite_da("res_nominal_capacity_kw", p.res_nominal_capacity_kw)
    res_capex_kw = _require_finite_da(
        "res_specific_investment_cost_per_kw", p.res_specific_investment_cost_per_kw
    )
    res_inv_capex_kw_ac = _require_finite_da(
        "res_inverter_specific_investment_cost_per_kw_ac",
        p.res_inverter_specific_investment_cost_per_kw_ac,
    )
    res_life_y = _require_finite_da("res_lifetime_years", p.res_lifetime_years)
    res_inv_life_y = _require_finite_da(
        "res_inverter_lifetime_years", p.res_inverter_lifetime_years
    )
    res_wacc = _require_finite_da("res_wacc", p.res_wacc)
    res_grant = _require_finite_da("res_grant_share_of_capex", p.res_grant_share_of_capex)
    res_dc_ac_ratio = _require_finite_da("res_dc_ac_ratio", p.res_dc_ac_ratio)

    bat_nom_kwh = _require_finite_da("battery_nominal_capacity_kwh", p.battery_nominal_capacity_kwh)
    bat_capex_kwh = _require_finite_da(
        "battery_specific_investment_cost_per_kwh", p.battery_specific_investment_cost_per_kwh
    )
    bat_inv_capex_kw = _require_finite_da(
        "battery_inverter_specific_investment_cost_per_kw",
        p.battery_inverter_specific_investment_cost_per_kw,
    )
    bat_life_y = _require_finite_da(
        "battery_calendar_lifetime_years", p.battery_calendar_lifetime_years
    )
    bat_inv_life_y = _require_finite_da(
        "battery_inverter_lifetime_years", p.battery_inverter_lifetime_years
    )
    bat_wacc = _require_finite_da("battery_wacc", p.battery_wacc)

    gen_nom_kw = _require_finite_da(
        "generator_nominal_capacity_kw", p.generator_nominal_capacity_kw
    )
    gen_capex_kw = _require_finite_da(
        "generator_specific_investment_cost_per_kw", p.generator_specific_investment_cost_per_kw
    )
    gen_life_y = _require_finite_da("generator_lifetime_years", p.generator_lifetime_years)
    gen_wacc = _require_finite_da("generator_wacc", p.generator_wacc)

    # ------------------------------------------------------------------
    # Investment annuities
    # ------------------------------------------------------------------
    res_inv_present = res_units * res_nom_kw * res_capex_kw * (1.0 - res_grant)
    res_inv_ac_present = (
        (res_units * res_nom_kw / res_dc_ac_ratio) * res_inv_capex_kw_ac * (1.0 - res_grant)
    )
    bat_inv_present = bat_units * bat_nom_kwh * bat_capex_kwh
    bat_inv_power_present = bat_inv_power * bat_inv_capex_kw
    gen_inv_present = gen_units * gen_nom_kw * gen_capex_kw

    res_annuity = res_inv_present * _crf(res_wacc, res_life_y)
    res_inv_ac_annuity = res_inv_ac_present * _crf(res_wacc, res_inv_life_y)
    bat_annuity = bat_inv_present * _crf(bat_wacc, bat_life_y)
    bat_inv_power_annuity = bat_inv_power_present * _crf(bat_wacc, bat_inv_life_y)
    gen_annuity = gen_inv_present * _crf(gen_wacc, gen_life_y)

    # Automatic like-for-like replacements keep each investment cohort active
    # from its commissioning year through the end of the planning horizon.
    res_active = replacement_active_mask(sets)
    bat_active = replacement_active_mask(sets)
    gen_active = replacement_active_mask(sets)

    ann_res_y = ((res_annuity + res_inv_ac_annuity) * res_active).sum("inv_step").sum("resource")
    ann_gen_y = (gen_annuity * gen_active).sum("inv_step")

    # Battery energy (cell) CAPEX and battery inverter CAPEX are amortized separately.
    # The inverter is always calendar-amortized. The energy CAPEX is amortized over the
    # BINDING life via an epigraph (see below) when cycle-fade degradation is active;
    # otherwise it is calendar-amortized like everything else.
    bat_energy_annuity_cal = bat_annuity * bat_active  # (year, inv_step) calendar
    bat_inv_annuity_y = (bat_inv_power_annuity * bat_active).sum("inv_step")  # (year,)
    bat_cycle_fade_var = vars.get("battery_cycle_fade", None)
    bat_repl_cost = vars.get("battery_replacement_cost", None)
    degradation_on = bat_cycle_fade_var is not None and bat_repl_cost is not None

    if degradation_on:
        # Endogenous battery energy replacement cost Z_{y,s,k} = max(calendar, cycle):
        #   Z >= calendar annuity                        (CAPEX / calendar life, WACC via CRF)
        #   Z >= c_repl * phi * F_cyc                     (CAPEX amortized over cycle-limited life)
        # with c_repl = CAPEX / (SoH0 - SoH_eol) and the financing gross-up
        # phi = CRF(wacc, calendar_life) * calendar_life, chosen so the two bounds
        # coincide exactly at the crossover (cycle life == calendar life). At the optimum
        # Z = CAPEX amortized over min(calendar, cycle-limited) life -> the effective
        # (economic == technical) lifetime, fully consistent with the annuity/no-salvage
        # cash-flow convention and free of the earlier double count.
        soh0 = _require_finite_da("battery_initial_soh", p.battery_initial_soh)
        soh_eol = _require_finite_da("battery_end_of_life_soh", p.battery_end_of_life_soh)
        usable_life_fraction = soh0 - soh_eol
        c_repl = bat_capex_kwh / usable_life_fraction  # (inv_step) currency / kWh fade
        phi = _crf(bat_wacc, bat_life_y) * bat_life_y  # (inv_step) financing gross-up (>=1)
        model.add_constraints(
            bat_repl_cost >= bat_energy_annuity_cal,
            name="battery_replacement_cost_calendar",
        )
        model.add_constraints(
            bat_repl_cost >= (c_repl * phi) * bat_cycle_fade_var,
            name="battery_replacement_cost_cycle",
        )
        # scenario-independent annuities only; battery energy replacement is
        # scenario-dependent (throughput is recourse) and enters the weighted cashflow.
        annuity_y = ann_res_y + bat_inv_annuity_y + ann_gen_y  # (year,)
        bat_energy_repl_y_s = bat_repl_cost.sum("inv_step")  # (year, scenario)
    else:
        ann_bat_y = (bat_energy_annuity_cal + bat_inv_power_annuity * bat_active).sum("inv_step")
        annuity_y = ann_res_y + ann_bat_y + ann_gen_y  # (year,)
        bat_energy_repl_y_s = None

    # ------------------------------------------------------------------
    # OPEX (year, scenario) then expected value
    # ------------------------------------------------------------------
    fuel_cost = (
        p.fuel_cost_per_unit_fuel
        if p.fuel_cost_per_unit_fuel is not None
        else p.fuel_fuel_cost_per_unit_fuel
    )
    fuel_cost = _require_finite_da("fuel_cost_per_unit_fuel", fuel_cost)
    fuel_cost_y_s = (fuel_cons * fuel_cost).sum("period").sum("inv_step")

    if on_grid:
        if grid_imp is None:
            raise InputValidationError("grid is enabled but variable 'grid_import' is missing.")
        grid_import_price = _require_finite_da("grid_import_price", p.grid_import_price)
        grid_import_cost_y_s = (grid_imp * grid_import_price).sum("period")
        if allow_export:
            if grid_exp is None:
                raise InputValidationError(
                    "grid export is enabled but variable 'grid_export' is missing."
                )
            grid_export_price = _require_finite_da("grid_export_price", p.grid_export_price)
            grid_export_rev_y_s = (grid_exp * grid_export_price).sum("period")
        else:
            grid_export_rev_y_s = 0.0
    else:
        grid_import_cost_y_s = 0.0
        grid_export_rev_y_s = 0.0

    # Renewable production subsidy (optional, step-period dependent)
    if p.res_production_subsidy_per_kwh is not None:
        subsidy = map_inv_step_to_year(
            sets,
            _finite_or_zero(p.res_production_subsidy_per_kwh),
            name="res_production_subsidy_per_kwh",
        )
        res_subsidy_rev_y_s = (res_gen * subsidy).sum("period").sum("resource")
    else:
        res_subsidy_rev_y_s = 0.0

    # Fixed O&M (optional but present in current templates)
    if p.res_fixed_om_share_per_year is not None:
        res_fom_share = _finite_or_zero(p.res_fixed_om_share_per_year)
        res_capex_base = res_units * res_nom_kw * res_capex_kw
        res_fom_y_s = (res_capex_base * res_active * res_fom_share).sum("inv_step").sum("resource")
    else:
        res_fom_y_s = 0.0
    if p.res_inverter_fixed_om_share_per_year is not None:
        res_inv_fom_share = _finite_or_zero(p.res_inverter_fixed_om_share_per_year)
        res_inv_capex_base = (res_units * res_nom_kw / res_dc_ac_ratio) * res_inv_capex_kw_ac
        res_inv_fom_y_s = (
            (res_inv_capex_base * res_active * res_inv_fom_share).sum("inv_step").sum("resource")
        )
    else:
        res_inv_fom_y_s = 0.0

    if p.battery_fixed_om_share_per_year is not None:
        bat_fom_share = _finite_or_zero(p.battery_fixed_om_share_per_year)
        bat_capex_base = bat_units * bat_nom_kwh * bat_capex_kwh
        bat_fom_y_s = (bat_capex_base * bat_active * bat_fom_share).sum("inv_step")
    else:
        bat_fom_y_s = 0.0
    if p.battery_inverter_fixed_om_share_per_year is not None:
        bat_inv_fom_share = _finite_or_zero(p.battery_inverter_fixed_om_share_per_year)
        bat_inv_fom_y_s = (bat_inv_power_present * bat_active * bat_inv_fom_share).sum("inv_step")
    else:
        bat_inv_fom_y_s = 0.0

    if p.generator_fixed_om_share_per_year is not None:
        gen_fom_share = _finite_or_zero(p.generator_fixed_om_share_per_year)
        gen_capex_base = gen_units * gen_nom_kw * gen_capex_kw
        gen_fom_y_s = (gen_capex_base * gen_active * gen_fom_share).sum("inv_step")
    else:
        gen_fom_y_s = 0.0

    opex_y_s = (
        fuel_cost_y_s
        + grid_import_cost_y_s
        - grid_export_rev_y_s
        - res_subsidy_rev_y_s
        + res_fom_y_s
        + bat_fom_y_s
        + res_inv_fom_y_s
        + bat_inv_fom_y_s
        + gen_fom_y_s
    )

    # ------------------------------------------------------------------
    # Externalities (year, scenario) + embedded at commissioning
    # ------------------------------------------------------------------
    lost_load_cost = _require_finite_da("lost_load_cost_per_kwh", p.lost_load_cost_per_kwh)
    emission_cost = _require_finite_da("emission_cost_per_kgco2e", p.emission_cost_per_kgco2e)
    fuel_direct_kg = _require_finite_da(
        "fuel_direct_emissions_kgco2e_per_unit_fuel", p.fuel_direct_emissions_kgco2e_per_unit_fuel
    )

    ll_cost_y_s = lost_load.sum("period") * lost_load_cost
    direct_em_kg_y_s = (fuel_cons.sum("period") * fuel_direct_kg).sum("inv_step")
    direct_em_cost_y_s = direct_em_kg_y_s * emission_cost
    if (
        on_grid
        and grid_imp is not None
        and p.grid_transmission_efficiency is not None
        and p.grid_emissions_factor_kgco2e_per_kwh is not None
    ):
        grid_scope2_kg_y_s = (
            (grid_imp * p.grid_transmission_efficiency).sum("period")
        ) * p.grid_emissions_factor_kgco2e_per_kwh
        grid_scope2_cost_y_s = grid_scope2_kg_y_s * emission_cost
    else:
        grid_scope2_cost_y_s = 0.0

    ext_y_s = ll_cost_y_s + direct_em_cost_y_s + grid_scope2_cost_y_s
    opex_ext_y_s = opex_y_s + ext_y_s
    if bat_energy_repl_y_s is not None:
        # Battery energy CAPEX amortized over the binding (endogenous) life, scenario-weighted.
        opex_ext_y_s = opex_ext_y_s + bat_energy_repl_y_s
    expected_cashflow_y = annuity_y + (opex_ext_y_s * w_s).sum("scenario")

    # Embedded emissions at commissioning year (optional)
    commission_res = replacement_commission_mask(sets, res_life_y)
    commission_bat = replacement_commission_mask(sets, bat_life_y)
    commission_gen = replacement_commission_mask(sets, gen_life_y)
    em_cost_exp = (
        (emission_cost * w_s).sum("scenario") if "scenario" in emission_cost.dims else emission_cost
    )

    emb_y = 0.0
    if p.res_embedded_emissions_kgco2e_per_kw is not None:
        res_emb_fac = _require_finite_da(
            "res_embedded_emissions_kgco2e_per_kw", p.res_embedded_emissions_kgco2e_per_kw
        )
        res_emb_kg = res_units * res_nom_kw * res_emb_fac
        emb_y = emb_y + (res_emb_kg * commission_res).sum("inv_step").sum("resource") * em_cost_exp
    if p.battery_embedded_emissions_kgco2e_per_kwh is not None:
        bat_emb_fac = _require_finite_da(
            "battery_embedded_emissions_kgco2e_per_kwh", p.battery_embedded_emissions_kgco2e_per_kwh
        )
        bat_emb_kg = bat_units * bat_nom_kwh * bat_emb_fac
        emb_y = emb_y + (bat_emb_kg * commission_bat).sum("inv_step") * em_cost_exp
    if p.generator_embedded_emissions_kgco2e_per_kw is not None:
        gen_emb_fac = _require_finite_da(
            "generator_embedded_emissions_kgco2e_per_kw",
            p.generator_embedded_emissions_kgco2e_per_kw,
        )
        gen_emb_kg = gen_units * gen_nom_kw * gen_emb_fac
        emb_y = emb_y + (gen_emb_kg * commission_gen).sum("inv_step") * em_cost_exp

    total_cashflow_y = expected_cashflow_y + emb_y

    # ------------------------------------------------------------------
    # Battery dispatch regularization (internal tie-breaker)
    # ------------------------------------------------------------------
    # Encourage solutions without simultaneous charge/discharge and avoid
    # degenerate circulation loops. Not a degradation model.
    #
    # epsilon in currency/kWh (tiny), aligned with the typical-year model.
    epsilon = 1e-6
    bat_ch = vars["battery_charge"]
    bat_dis = vars["battery_discharge"]
    bat_eff_cap = vars.get("battery_effective_energy_capacity", None)
    bat_throughput_y_s = (bat_ch + bat_dis).sum("period").sum("inv_step")
    bat_reg_cost_y = epsilon * (bat_throughput_y_s * w_s).sum("scenario")

    # The economic cost of cycle-fade degradation is carried by the max-of-annuities
    # epigraph above (battery_replacement_cost), NOT by a separate wear charge, so there
    # is no double count with the calendar annuity. A tiny credit keeps the raw
    # effective-capacity LP state pushed to its largest feasible value for reporting
    # robustness (the physical SoH used in reports is reconstructed separately).
    eff_cap_reg_credit_y = 0.0
    if bat_eff_cap is not None:
        eff_cap_reg_credit_y = -1e-9 * (bat_eff_cap.sum("inv_step") * w_s).sum("scenario")

    # Reporting-only note: the discounted value of annuity payments that would
    # fall beyond the modeled horizon (a salvage / residual-value term) is
    # intentionally NOT subtracted from the objective. In the current multi-year
    # formulation we optimize discounted in-horizon annual cashflows only;
    # charging an out-of-horizon salvage term here would mix annuity accounting
    # with a full-CAPEX residual-value convention. (The previously computed
    # `post_horizon_annuity_tail_memo` was unused and has been removed.)

    npwc = (
        (total_cashflow_y + bat_reg_cost_y + eff_cap_reg_credit_y) * disc_y
    ).sum("year")
    model.add_objective(npwc, overwrite=True)
