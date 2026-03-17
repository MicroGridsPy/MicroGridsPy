from __future__ import annotations

from typing import Dict

import numpy as np
import xarray as xr
import linopy as lp

from core.multi_year_model.lifecycle import replacement_active_mask, repeating_degradation_factor
from core.multi_year_model.params import get_params


class InputValidationError(RuntimeError):
    pass


def _require_da(name: str, da: xr.DataArray | None) -> xr.DataArray:
    if da is None:
        raise InputValidationError(f"Missing required parameter/data variable: '{name}'")
    return da


def _available_capacity_by_year(
    *,
    sets: xr.Dataset,
    units: lp.Variable,
    nominal_capacity: xr.DataArray,
    lifetime_years: xr.DataArray | float,
    degradation_rate: xr.DataArray | None = None,
) -> xr.DataArray:
    """
    Generic linear capacity availability from incremental investments.

    Returns capacity with dims that include `year` and any non-investment dims
    from `units/nominal_capacity/degradation_rate` (e.g. scenario, resource).
    """
    inv_active = replacement_active_mask(sets)
    invest_cap = units * nominal_capacity
    factor = repeating_degradation_factor(
        sets=sets,
        lifetime_years=lifetime_years,
        degradation_rate=degradation_rate,
    )
    available = (invest_cap * inv_active * factor).sum("inv_step")
    return available


def _is_effectively_positive(da: xr.DataArray | None) -> bool:
    if da is None:
        return False
    vals = np.asarray(da.values, dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return False
    return float(vals.max()) > 0.0


def validate_constraint_shapes(
    *,
    sets: xr.Dataset,
    p: object,
    vars: Dict[str, lp.Variable],
) -> None:
    required_sets = ("period", "year", "inv_step", "scenario", "resource")
    for c in required_sets:
        if c not in sets.coords:
            raise InputValidationError(f"initialize_constraints: missing required coord in sets: '{c}'")

    required_vars = (
        "res_units",
        "battery_units",
        "generator_units",
        "res_generation",
        "generator_generation",
        "fuel_consumption",
        "battery_charge",
        "battery_discharge",
        "battery_soc",
        "lost_load",
    )
    for v in required_vars:
        if v not in vars:
            raise InputValidationError(f"initialize_constraints: missing required variable '{v}'")

    required_data = (
        ("load_demand", p.load_demand, {"period", "year", "scenario"}),
        ("resource_availability", p.resource_availability, {"period", "year", "scenario", "resource"}),
        ("scenario_weight", p.scenario_weight, {"scenario"}),
        ("min_renewable_penetration", p.min_renewable_penetration, set()),
        ("max_lost_load_fraction", p.max_lost_load_fraction, set()),
    )
    for name, da, expected_any in required_data:
        da_req = _require_da(name, da)
        if expected_any and not expected_any.issubset(set(da_req.dims)):
            raise InputValidationError(
                f"Parameter '{name}' has dims {da_req.dims}, expected at least {sorted(expected_any)}"
            )


def initialize_constraints(
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: Dict[str, lp.Variable],
    model: lp.Model,
) -> None:
    if not isinstance(sets, xr.Dataset):
        raise InputValidationError("initialize_constraints: `sets` must be an xarray.Dataset.")
    if not isinstance(data, xr.Dataset):
        raise InputValidationError("initialize_constraints: `data` must be an xarray.Dataset.")
    if not isinstance(vars, dict):
        raise InputValidationError("initialize_constraints: `vars` must be a dict of linopy variables.")

    period = sets.coords["period"]

    p = get_params(data)
    validate_constraint_shapes(sets=sets, p=p, vars=vars)

    on_grid = p.is_grid_on()
    allow_export = p.is_grid_export_enabled()
    enforcement = str((p.settings.get("optimization_constraints", {}) or {}).get("enforcement", "scenario_wise"))
    if enforcement not in ("expected", "scenario_wise"):
        raise InputValidationError(
            f"Invalid optimization_constraints.enforcement='{enforcement}'. "
            "Allowed: 'expected' | 'scenario_wise'."
        )

    load_demand = _require_da("load_demand", p.load_demand)
    resource_availability = _require_da("resource_availability", p.resource_availability)
    scenario_weight = _require_da("scenario_weight", p.scenario_weight)

    min_res_pen = _require_da("min_renewable_penetration", p.min_renewable_penetration)
    max_ll_frac = _require_da("max_lost_load_fraction", p.max_lost_load_fraction)

    res_nom_kw = _require_da("res_nominal_capacity_kw", p.res_nominal_capacity_kw)
    res_inv_eta = _require_da("res_inverter_efficiency", p.res_inverter_efficiency)
    res_max_kw = _require_da("res_max_installable_capacity_kw", p.res_max_installable_capacity_kw)

    bat_nom_kwh = _require_da("battery_nominal_capacity_kwh", p.battery_nominal_capacity_kwh)
    eta_c = _require_da("battery_charge_efficiency", p.battery_charge_efficiency)
    eta_d = _require_da("battery_discharge_efficiency", p.battery_discharge_efficiency)
    soc0 = _require_da("battery_initial_soc", p.battery_initial_soc)
    dod = _require_da("battery_depth_of_discharge", p.battery_depth_of_discharge)
    t_ch = _require_da("battery_max_charge_time_hours", p.battery_max_charge_time_hours)
    t_dis = _require_da("battery_max_discharge_time_hours", p.battery_max_discharge_time_hours)

    gen_nom_kw = _require_da("generator_nominal_capacity_kw", p.generator_nominal_capacity_kw)
    gen_max_kw = _require_da("generator_max_installable_capacity_kw", p.generator_max_installable_capacity_kw)
    gen_eta_full = _require_da("generator_nominal_efficiency_full_load", p.generator_nominal_efficiency_full_load)
    fuel_lhv = _require_da("fuel_lhv_kwh_per_unit_fuel", p.fuel_lhv_kwh_per_unit_fuel)

    land_m2 = _require_da("land_availability_m2", p.land_availability_m2)
    res_area_m2_per_kw = _require_da("res_specific_area_m2_per_kw", p.res_specific_area_m2_per_kw)

    if on_grid:
        grid_line_cap = _require_da("grid_line_capacity_kw", p.grid_line_capacity_kw)
        grid_eta = _require_da("grid_transmission_efficiency", p.grid_transmission_efficiency)
        grid_ren_share = _require_da("grid_renewable_share", p.grid_renewable_share)
        grid_availability = _require_da("grid_availability", p.grid_availability)

    res_units = vars["res_units"]  # (inv_step, resource)
    bat_units = vars["battery_units"]  # (inv_step,)
    gen_units = vars["generator_units"]  # (inv_step,)

    res_gen = vars["res_generation"]  # (period, year, scenario, resource)
    gen_gen = vars["generator_generation"]  # (period, year, scenario)
    fuel_cons = vars["fuel_consumption"]  # (period, year, scenario)
    bat_ch = vars["battery_charge"]  # (period, year, scenario)
    bat_dis = vars["battery_discharge"]  # (period, year, scenario)
    soc = vars["battery_soc"]  # (period, year, scenario)
    ll = vars["lost_load"]  # (period, year, scenario)
    grid_imp = vars.get("grid_import")
    grid_exp = vars.get("grid_export")
    # ------------------------------------------------------------------
    # 1) Renewable generation capacity with year availability
    # ------------------------------------------------------------------
    res_cap_available = _available_capacity_by_year(
        sets=sets,
        units=res_units,
        nominal_capacity=res_nom_kw,
        lifetime_years=p.res_lifetime_years,
        degradation_rate=p.res_capacity_degradation_rate_per_year,
    ) * res_inv_eta
    model.add_constraints(
        res_gen <= (resource_availability * res_cap_available),
        name="res_generation_cap",
    )

    finite_res_max = np.isfinite(res_max_kw)
    res_max_kw_finite = res_max_kw.where(finite_res_max, drop=True)
    if res_max_kw_finite.sizes.get("resource", 0) > 0:
        lhs_res_total = (res_units * res_nom_kw).sum("inv_step").sel(resource=res_max_kw_finite.resource)
        model.add_constraints(lhs_res_total <= res_max_kw_finite, name="res_max_installable_capacity")

    # ------------------------------------------------------------------
    # 2) Generator capacity with year availability
    # ------------------------------------------------------------------
    gen_cap_available = _available_capacity_by_year(
        sets=sets,
        units=gen_units,
        nominal_capacity=gen_nom_kw,
        lifetime_years=p.generator_lifetime_years,
        degradation_rate=p.generator_capacity_degradation_rate_per_year,
    )
    model.add_constraints(gen_gen <= gen_cap_available, name="generator_generation_cap")

    gen_max_vals = np.asarray(gen_max_kw.values, dtype=float)
    if np.isfinite(gen_max_vals).any():
        model.add_constraints(
            (gen_units * gen_nom_kw).sum("inv_step") <= float(np.nanmax(gen_max_vals)),
            name="generator_max_capacity",
        )

    # ------------------------------------------------------------------
    # 3) Fuel-to-power relation
    # ------------------------------------------------------------------
    if p.generator_eff_curve_eff is not None and p.generator_eff_curve_rel_power is not None:
        pl_rel = p.generator_eff_curve_rel_power
        pl_eff = p.generator_eff_curve_eff
        scenario_labels = [str(s) for s in sets.coords["scenario"].values.tolist()]

        def _scenario_has_curve(scen: str) -> bool:
            rel = pl_rel.sel(scenario=scen)
            eff = pl_eff.sel(scenario=scen)
            return bool(np.isfinite(rel.values).any() and np.isfinite(eff.values).any())

        scenarios_with_pl = [s for s in scenario_labels if _scenario_has_curve(s)]
        scenarios_without_pl = [s for s in scenario_labels if s not in scenarios_with_pl]

        if len(scenarios_without_pl) > 0:
            model.add_constraints(
                gen_gen.sel(scenario=scenarios_without_pl)
                == fuel_cons.sel(scenario=scenarios_without_pl) * fuel_lhv.sel(scenario=scenarios_without_pl) * gen_eta_full,
                name="fuel_to_power_nominal_eta",
            )

        if len(scenarios_with_pl) > 0:
            P = int(pl_rel.sizes["curve_point"])
            seg = xr.IndexVariable("segment", np.arange(P - 1))

            for s in scenarios_with_pl:
                lhv_s = fuel_lhv.sel(scenario=s)
                cap_sy = gen_cap_available.sel(scenario=s) if "scenario" in gen_cap_available.dims else gen_cap_available
                r_full = pl_rel.sel(scenario=s)
                e_full = pl_eff.sel(scenario=s)

                if not (np.isfinite(r_full.values).all() and np.isfinite(e_full.values).all()):
                    raise InputValidationError(
                        f"Partial-load curve for scenario '{s}' contains NaNs; provide a full curve_point series."
                    )
                if np.any(np.diff(r_full.values) < 0.0):
                    raise InputValidationError(
                        f"Partial-load curve for scenario '{s}' must be sorted by increasing relative power output."
                    )
                positive_power_mask = np.asarray(r_full.values, dtype=float) > 0.0
                if np.any(np.asarray(e_full.values, dtype=float)[positive_power_mask] <= 0.0):
                    raise InputValidationError(
                        f"Partial-load curve for scenario '{s}' contains non-positive efficiencies at positive output."
                    )

                r0 = r_full.isel(curve_point=seg)
                r1 = r_full.isel(curve_point=seg + 1)
                eta0 = e_full.isel(curve_point=seg)
                eta1 = e_full.isel(curve_point=seg + 1)

                rel0 = xr.DataArray(
                    np.asarray(r0.values, dtype=float),
                    coords={"segment": seg},
                    dims=("segment",),
                )
                rel1 = xr.DataArray(
                    np.asarray(r1.values, dtype=float),
                    coords={"segment": seg},
                    dims=("segment",),
                )
                eff0 = xr.DataArray(
                    np.asarray(eta0.values, dtype=float),
                    coords={"segment": seg},
                    dims=("segment",),
                )
                eff1 = xr.DataArray(
                    np.asarray(eta1.values, dtype=float),
                    coords={"segment": seg},
                    dims=("segment",),
                )

                lhv_value = float(lhv_s)
                alpha0 = xr.where(np.isclose(rel0, 0.0), 0.0, rel0 / (eff0 * lhv_value))
                alpha1 = xr.where(np.isclose(rel1, 0.0), 0.0, rel1 / (eff1 * lhv_value))

                rel_span = rel1 - rel0
                if np.any(np.isclose(rel_span.values.astype(float), 0.0)):
                    raise InputValidationError(
                        f"Partial-load curve for scenario '{s}' contains repeated relative-power points."
                    )

                slope = (alpha1 - alpha0) / rel_span
                intercept = alpha0 - slope * rel0

                gen_sy = gen_gen.sel(scenario=s).expand_dims(segment=seg)
                fuel_sy = fuel_cons.sel(scenario=s).expand_dims(segment=seg)
                cap_seg = cap_sy.expand_dims(segment=seg)
                rhs = slope * gen_sy + intercept * cap_seg

                model.add_constraints(
                    fuel_sy >= rhs,
                    name=f"fuel_to_power_partial_load_{s}",
                )
    else:
        model.add_constraints(
            gen_gen == fuel_cons * fuel_lhv * gen_eta_full,
            name="fuel_to_power_nominal_eta",
        )

    # ------------------------------------------------------------------
    # 4) Battery limits and SOC dynamics
    # ------------------------------------------------------------------
    bat_cap_available = _available_capacity_by_year(
        sets=sets,
        units=bat_units,
        nominal_capacity=bat_nom_kwh,
        lifetime_years=p.battery_calendar_lifetime_years,
        degradation_rate=p.battery_capacity_degradation_rate_per_year,
    )

    model.add_constraints(bat_ch <= (bat_cap_available / t_ch), name="battery_charge_limit")
    model.add_constraints(bat_dis <= (bat_cap_available / t_dis), name="battery_discharge_limit")

    T = int(period.size)
    model.add_constraints(soc.isel(period=0) == soc0 * bat_cap_available, name="soc_initial")

    if T > 1:
        model.add_constraints(
            soc.isel(period=slice(1, None))
            == soc.isel(period=slice(0, -1))
            + eta_c * bat_ch.isel(period=slice(0, -1))
            - bat_dis.isel(period=slice(0, -1)) / eta_d,
            name="soc_balance",
        )

    model.add_constraints(
        soc.isel(period=T - 1)
        + eta_c * bat_ch.isel(period=T - 1)
        - bat_dis.isel(period=T - 1) / eta_d
        == soc0 * bat_cap_available,
        name="soc_cyclic",
    )
    model.add_constraints(soc <= bat_cap_available, name="soc_upper")
    model.add_constraints(soc >= (1.0 - dod) * bat_cap_available, name="soc_lower")

    # ------------------------------------------------------------------
    # 5) Grid limits and nodal balance
    # ------------------------------------------------------------------
    if on_grid and grid_imp is not None:
        model.add_constraints(
            grid_imp <= (grid_availability * grid_line_cap),
            name="grid_import_cap",
        )
        if allow_export and grid_exp is not None:
            model.add_constraints(
                grid_exp <= (grid_availability * grid_line_cap),
                name="grid_export_cap",
            )

    res_sum = res_gen.sum("resource")
    lhs = res_sum + gen_gen + (bat_dis - bat_ch) + ll

    if on_grid and grid_imp is not None:
        lhs = lhs + (grid_imp * grid_eta)
        if allow_export and grid_exp is not None:
            lhs = lhs - (grid_exp * grid_eta)

    model.add_constraints(lhs == load_demand, name="energy_balance")

    # ------------------------------------------------------------------
    # 6) Policy constraints (year/scenario or expected-by-year)
    # ------------------------------------------------------------------
    e_demand = load_demand.sum("period")  # (year, scenario)
    e_ll = ll.sum("period")  # (year, scenario)
    e_res = res_sum.sum("period")  # (year, scenario)
    e_gen = gen_gen.sum("period")  # (year, scenario)

    if on_grid and grid_imp is not None:
        e_grid = (grid_imp * grid_eta).sum("period")
        e_grid_ren = (grid_imp * grid_eta * grid_ren_share).sum("period")
    else:
        # e_res is a linopy expression, not an xarray object; keep zero as scalar.
        e_grid = 0.0
        e_grid_ren = 0.0

    if enforcement == "scenario_wise":
        model.add_constraints(e_ll <= (max_ll_frac * e_demand), name="max_lost_load_share")
    else:
        lhs_ll = (e_ll * scenario_weight).sum("scenario")
        if "scenario" in max_ll_frac.dims:
            rhs_ll = (max_ll_frac * e_demand * scenario_weight).sum("scenario")
        else:
            rhs_ll = max_ll_frac * (e_demand * scenario_weight).sum("scenario")
        model.add_constraints(lhs_ll <= rhs_ll, name="max_lost_load_share_expected")

    if _is_effectively_positive(min_res_pen):
        e_total = e_res + e_gen + e_grid
        e_renew = e_res + e_grid_ren
        if enforcement == "scenario_wise":
            model.add_constraints(e_renew >= (min_res_pen * e_total), name="min_renewable_penetration")
        else:
            lhs_res = (e_renew * scenario_weight).sum("scenario")
            if "scenario" in min_res_pen.dims:
                rhs_res = (min_res_pen * e_total * scenario_weight).sum("scenario")
            else:
                rhs_res = min_res_pen * (e_total * scenario_weight).sum("scenario")
            model.add_constraints(lhs_res >= rhs_res, name="min_renewable_penetration_expected")

    # ------------------------------------------------------------------
    # 7) Land use (design-side, scenario-independent investments)
    # ------------------------------------------------------------------
    area_used = res_units * res_nom_kw * res_area_m2_per_kw
    if "inv_step" in area_used.dims:
        area_used = area_used.sum("inv_step")
    if "resource" in area_used.dims:
        area_used = area_used.sum("resource")
    model.add_constraints(area_used <= land_m2, name="land_availability")
