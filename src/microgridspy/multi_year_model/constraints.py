from __future__ import annotations

import linopy as lp
import numpy as np
import xarray as xr

from microgridspy.data_pipeline.battery_loss_model import (
    CONVEX_LOSS_EPIGRAPH,
    normalize_battery_loss_model,
)
from microgridspy.data_pipeline.generator_partial_load_model import (
    fit_generator_willans_from_curve,
)
from microgridspy.data_pipeline.utils import finite_nonnegative_scalar_limit
from microgridspy.multi_year_model.lifecycle import (
    repeating_degradation_factor,
    replacement_active_mask,
    replacement_commission_mask,
)
from microgridspy.multi_year_model.params import get_params


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


def _available_capacity_by_year_by_step(
    *,
    sets: xr.Dataset,
    units: lp.Variable,
    nominal_capacity: xr.DataArray,
    lifetime_years: xr.DataArray | float,
    degradation_rate: xr.DataArray | None = None,
) -> xr.DataArray:
    """Return cohort-specific available capacity with dims including year and inv_step."""
    inv_active = replacement_active_mask(sets)
    invest_cap = units * nominal_capacity
    factor = repeating_degradation_factor(
        sets=sets,
        lifetime_years=lifetime_years,
        degradation_rate=degradation_rate,
    )
    return invest_cap * inv_active * factor


def _is_effectively_positive(da: xr.DataArray | None) -> bool:
    if da is None:
        return False
    vals = np.asarray(da.values, dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return False
    return float(vals.max()) > 0.0


def _shared_scalar_from_da(name: str, da: xr.DataArray | None) -> float | None:
    if da is None:
        return None
    vals = np.asarray(da.values, dtype=float).reshape(-1)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return None
    baseline = float(vals[0])
    if not np.allclose(vals, baseline, atol=1e-12, rtol=0.0):
        raise InputValidationError(
            f"Parameter '{name}' must be shared across investment steps in the multi-year formulation."
        )
    return baseline


def validate_constraint_shapes(
    *,
    sets: xr.Dataset,
    p: object,
    vars: dict[str, lp.Variable],
) -> None:
    required_sets = ("period", "year", "inv_step", "scenario", "resource")
    for c in required_sets:
        if c not in sets.coords:
            raise InputValidationError(
                f"initialize_constraints: missing required coord in sets: '{c}'"
            )

    required_vars = (
        "res_units",
        "battery_units",
        "battery_inverter_power",
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
        (
            "resource_availability",
            p.resource_availability,
            {"period", "year", "scenario", "resource"},
        ),
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
    vars: dict[str, lp.Variable],
    model: lp.Model,
) -> None:
    if not isinstance(sets, xr.Dataset):
        raise InputValidationError("initialize_constraints: `sets` must be an xarray.Dataset.")
    if not isinstance(data, xr.Dataset):
        raise InputValidationError("initialize_constraints: `data` must be an xarray.Dataset.")
    if not isinstance(vars, dict):
        raise InputValidationError(
            "initialize_constraints: `vars` must be a dict of linopy variables."
        )

    period = sets.coords["period"]
    year = sets.coords["year"]

    p = get_params(data)
    validate_constraint_shapes(sets=sets, p=p, vars=vars)

    on_grid = p.is_grid_on()
    allow_export = p.is_grid_export_enabled()
    battery_loss_model = normalize_battery_loss_model(
        ((p.settings.get("battery_model", {}) or {}).get("loss_model")),
        default="constant_efficiency",
    )
    battery_model_settings = p.settings.get("battery_model", {}) or {}
    degradation_settings = battery_model_settings.get("degradation_model", {}) or {}
    cycle_fade_enabled = bool(degradation_settings.get("cycle_fade_enabled", False))
    degradation_state_enabled = cycle_fade_enabled
    # Semi-empirical coefficient fields (temperature- and DoD-aware), attached by the
    # loader when cycle fade is active. beta drives the endogenous cycle-fade recursion
    # (use-based); alpha drives the calendar rate (time-based, static within the solve).
    beta_cycle = data.get("battery_beta_cycle") if isinstance(data, xr.Dataset) else None
    calendar_rate_year = (
        data.get("battery_calendar_rate_per_year") if isinstance(data, xr.Dataset) else None
    )
    # Calendar ageing rate (time-based). When the semi-empirical calendar rate is present
    # it drives the availability factor as a year-varying r_cal,y = alpha(T_bar_y)*8760
    # (temperature-aware, static within the solve), replacing the flat user %/yr.
    if calendar_rate_year is not None:
        battery_capacity_degradation_rate = calendar_rate_year
    else:
        battery_capacity_degradation_rate = p.battery_capacity_degradation_rate_per_year
    # Whether the availability ceiling actually declines within a cohort's life. When it
    # does not (rate == 0), the effective-capacity year-link can be an exact equality
    # (no degeneracy); otherwise it stays an inequality (take the min of continuation and
    # the declining ceiling).
    _rate_vals = np.asarray(
        xr.DataArray(battery_capacity_degradation_rate).values, dtype=float
    ).reshape(-1)
    exogenous_fade_active = bool(_rate_vals.size and np.nanmax(np.abs(_rate_vals)) > 0.0)
    if degradation_state_enabled and battery_loss_model != CONVEX_LOSS_EPIGRAPH:
        raise InputValidationError(
            "Battery degradation tracking requires battery_model.loss_model='convex_loss_epigraph'."
        )
    enforcement = str(
        (p.settings.get("optimization_constraints", {}) or {}).get("enforcement", "scenario_wise")
    )
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
    res_dc_ac_ratio = _require_da("res_dc_ac_ratio", p.res_dc_ac_ratio)
    res_inv_eta = _require_da("res_inverter_efficiency", p.res_inverter_efficiency)
    res_max_kw = _require_da("res_max_installable_capacity_kw", p.res_max_installable_capacity_kw)

    bat_nom_kwh = _require_da("battery_nominal_capacity_kwh", p.battery_nominal_capacity_kwh)
    bat_max_installable_kwh = p.battery_max_installable_capacity_kwh
    eta_c = _require_da("battery_charge_efficiency", p.battery_charge_efficiency)
    eta_d = _require_da("battery_discharge_efficiency", p.battery_discharge_efficiency)
    soc0 = _require_da("battery_initial_soc", p.battery_initial_soc)
    soh0 = (
        _require_da("battery_initial_soh", p.battery_initial_soh)
        if degradation_state_enabled
        else p.battery_initial_soh
    )
    soc0_scalar = float(soc0.item()) if getattr(soc0, "dims", ()) == () else soc0
    soh0_scalar = (
        float(soh0.item())
        if (degradation_state_enabled and getattr(soh0, "dims", ()) == ())
        else soh0
    )
    dod = _require_da("battery_depth_of_discharge", p.battery_depth_of_discharge)
    bat_max_charge_c_rate = p.battery_max_charge_c_rate
    bat_max_discharge_c_rate = p.battery_max_discharge_c_rate
    gen_nom_kw = _require_da("generator_nominal_capacity_kw", p.generator_nominal_capacity_kw)
    gen_max_kw = _require_da(
        "generator_max_installable_capacity_kw", p.generator_max_installable_capacity_kw
    )
    gen_eta_full = _require_da(
        "generator_nominal_efficiency_full_load", p.generator_nominal_efficiency_full_load
    )
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
    bat_inv_power = vars["battery_inverter_power"]  # (inv_step,)
    gen_units = vars["generator_units"]  # (inv_step,)

    res_gen = vars["res_generation"]  # (period, year, scenario, resource)
    gen_gen = vars["generator_generation"]  # (period, year, scenario, inv_step)
    fuel_cons = vars["fuel_consumption"]  # (period, year, scenario, inv_step)
    bat_ch = vars["battery_charge"]  # (period, year, scenario, inv_step)
    bat_dis = vars["battery_discharge"]  # (period, year, scenario, inv_step)
    soc = vars["battery_soc"]  # (period, year, scenario, inv_step)
    bat_ch_dc = vars.get("battery_charge_dc")
    bat_dis_dc = vars.get("battery_discharge_dc")
    bat_ch_loss = vars.get("battery_charge_loss")
    bat_dis_loss = vars.get("battery_discharge_loss")
    bat_cycle_fade = vars.get("battery_cycle_fade")
    bat_eff_cap = vars.get("battery_effective_energy_capacity")
    ll = vars["lost_load"]  # (period, year, scenario)
    # Grid interchange is represented at the PCC before transmission
    # efficiency. Delivered imports/exports are obtained in the nodal balance.
    grid_imp = vars.get("grid_import")
    grid_exp = vars.get("grid_export")
    # ------------------------------------------------------------------
    # 1) Renewable generation capacity with year availability
    # ------------------------------------------------------------------
    res_cap_available_dc = _available_capacity_by_year(
        sets=sets,
        units=res_units,
        nominal_capacity=res_nom_kw,
        lifetime_years=p.res_lifetime_years,
        degradation_rate=p.res_capacity_degradation_rate_per_year,
    )
    res_cap_available_ac = res_cap_available_dc / res_dc_ac_ratio
    model.add_constraints(
        res_gen <= (resource_availability * res_cap_available_dc * res_inv_eta),
        name="res_generation_cap",
    )
    model.add_constraints(
        res_gen <= res_cap_available_ac,
        name="res_generation_inverter_cap",
    )

    finite_res_max = np.isfinite(res_max_kw)
    res_max_kw_finite = res_max_kw.where(finite_res_max, drop=True)
    if res_max_kw_finite.sizes.get("resource", 0) > 0:
        lhs_res_total = (
            (res_units * res_nom_kw).sum("inv_step").sel(resource=res_max_kw_finite.resource)
        )
        model.add_constraints(
            lhs_res_total <= res_max_kw_finite, name="res_max_installable_capacity"
        )

    # ------------------------------------------------------------------
    # 2) Generator capacity with year availability (by vintage)
    # ------------------------------------------------------------------
    gen_cap_available = _available_capacity_by_year_by_step(
        sets=sets,
        units=gen_units,
        nominal_capacity=gen_nom_kw,
        lifetime_years=p.generator_lifetime_years,
        degradation_rate=p.generator_capacity_degradation_rate_per_year,
    )
    model.add_constraints(gen_gen <= gen_cap_available, name="generator_generation_cap")

    gen_max_shared = _shared_scalar_from_da("generator_max_installable_capacity_kw", gen_max_kw)
    if gen_max_shared is not None and gen_max_shared > 0.0:
        model.add_constraints(
            (gen_units * gen_nom_kw).sum("inv_step") <= float(gen_max_shared),
            name="generator_max_capacity",
        )

    # ------------------------------------------------------------------
    # 3) Fuel-to-power relation
    # ------------------------------------------------------------------
    gen_settings = p.settings.get("generator", {}) or {}
    partial_load_enabled = (
        p.generator_eff_curve_rel_power is not None and p.generator_eff_curve_eff is not None
    )
    commitment_mode = str(gen_settings.get("partial_load_commitment", "integer")).strip().lower()
    if not partial_load_enabled:
        commitment_mode = "off"
    if commitment_mode == "relaxed":
        # Legacy: the LP relaxation was removed (it was equivalent to constant
        # efficiency). Part-load now always uses the exact integer commitment.
        commitment_mode = "integer"
    if commitment_mode not in ("off", "integer"):
        raise InputValidationError(
            f"Invalid generator.partial_load_commitment='{commitment_mode}'. "
            "Allowed: 'off' | 'integer'."
        )

    if commitment_mode == "integer":
        # Clustered unit-commitment partial-load model (Palmintier & Webster).
        # An integer count of committed cohort units carries the affine Willans
        # no-load fuel intercept, so idling committed capacity burns fuel even at
        # zero output and part-load operation is penalised.
        n_online = vars.get("generator_online_units")
        if n_online is None:
            raise InputValidationError(
                "Generator commitment mode is active but the 'generator_online_units' "
                "variable is missing."
            )
        q0, q1 = fit_generator_willans_from_curve(
            p.generator_eff_curve_rel_power.values,
            p.generator_eff_curve_eff.values,
            error_cls=InputValidationError,
        )
        min_load = float(gen_settings.get("min_load_fraction", 0.0) or 0.0)
        if not (0.0 <= min_load < 1.0):
            raise InputValidationError("generator.min_load_fraction must be within [0, 1).")

        # Committed (online) nominal capacity per period/year/scenario/cohort.
        online_cap = n_online * gen_nom_kw
        # Cannot commit more than the available (degraded) cohort capacity.
        model.add_constraints(
            online_cap <= gen_cap_available, name="generator_commitment_availability"
        )
        # Output bounded by committed capacity, with optional minimum stable load.
        model.add_constraints(gen_gen <= online_cap, name="generator_online_max")
        if min_load > 0.0:
            model.add_constraints(gen_gen >= min_load * online_cap, name="generator_online_min")
        # Affine Willans fuel: marginal per kWh output plus a no-load intercept
        # charged per unit of committed capacity. Minimising fuel makes it tight.
        model.add_constraints(
            fuel_cons >= (q1 / fuel_lhv) * gen_gen + (q0 / fuel_lhv) * online_cap,
            name="generator_fuel_willans",
        )
    else:
        model.add_constraints(
            gen_gen == fuel_cons * fuel_lhv * gen_eta_full,
            name="fuel_to_power_nominal_eta",
        )

    # ------------------------------------------------------------------
    # 4) Battery limits and SOC dynamics (by vintage)
    # ------------------------------------------------------------------
    bat_cap_available = _available_capacity_by_year_by_step(
        sets=sets,
        units=bat_units,
        nominal_capacity=bat_nom_kwh,
        lifetime_years=p.battery_calendar_lifetime_years,
        degradation_rate=battery_capacity_degradation_rate,
    )
    bat_active_year = replacement_active_mask(sets)
    bat_commission_year = replacement_commission_mask(sets, p.battery_calendar_lifetime_years)
    bat_active = bat_active_year.expand_dims(
        period=period, scenario=sets.coords["scenario"]
    ).transpose("period", "year", "scenario", "inv_step")
    bat_max_installable_shared = _shared_scalar_from_da(
        "battery_max_installable_capacity_kwh",
        bat_max_installable_kwh,
    )
    if bat_max_installable_shared is not None and float(bat_max_installable_shared) < 0.0:
        raise InputValidationError(
            "battery_max_installable_capacity_kwh must be >= 0 when provided."
        )
    if bat_max_installable_shared is not None:
        model.add_constraints(
            (bat_units * bat_nom_kwh).sum("inv_step") <= float(bat_max_installable_shared),
            name="battery_max_installable_capacity",
        )

    # Broadcast the step-level inverter design variable through the same
    # vintage activity mask already expanded to operational dimensions.
    bat_inv_active = bat_inv_power * bat_active
    model.add_constraints(bat_ch <= bat_inv_active, name="battery_charge_limit")
    model.add_constraints(bat_dis <= bat_inv_active, name="battery_discharge_limit")
    bat_nominal_energy = bat_units * bat_nom_kwh
    if isinstance(bat_max_charge_c_rate, xr.DataArray):
        finite_charge_rate = xr.where(
            np.isfinite(bat_max_charge_c_rate), bat_max_charge_c_rate, 0.0
        )
        if np.any(np.isfinite(np.asarray(bat_max_charge_c_rate.values, dtype=float))):
            model.add_constraints(
                bat_inv_power <= (bat_nominal_energy * finite_charge_rate),
                name="battery_max_charge_c_rate",
            )
    if isinstance(bat_max_discharge_c_rate, xr.DataArray):
        finite_discharge_rate = xr.where(
            np.isfinite(bat_max_discharge_c_rate), bat_max_discharge_c_rate, 0.0
        )
        if np.any(np.isfinite(np.asarray(bat_max_discharge_c_rate.values, dtype=float))):
            model.add_constraints(
                bat_inv_power <= (bat_nominal_energy * finite_discharge_rate),
                name="battery_max_discharge_c_rate",
            )

    T = int(period.size)
    year_values = year.values.tolist()
    first_year = year_values[0]
    # Dynamic formulation uses a continuous chronology across modeled years:
    # initialize SOC only once in the first year, then carry terminal SOC
    # forward through explicit inter-year link constraints.
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
        # The battery curve is normalized on DC-side power relative to the same
        # charge/discharge reference used by the public AC-side power caps.
        p_ref_ch = bat_inv_active
        p_ref_dis = bat_inv_active

        # The curve is defined on relative DC-side power in [0, 1], so keep
        # the internal DC powers within the same normalized reference range.
        model.add_constraints(
            bat_ch_dc <= p_ref_ch,
            name="battery_charge_dc_limit",
        )
        model.add_constraints(
            bat_dis_dc <= p_ref_dis,
            name="battery_discharge_dc_limit",
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
        p_ref_ch_b = p_ref_ch.expand_dims({"battery_loss_segment": seg})
        p_ref_dis_b = p_ref_dis.expand_dims({"battery_loss_segment": seg})

        model.add_constraints(
            bat_ch_loss_b >= (ch_slope * bat_ch_dc_b) + (ch_intercept * p_ref_ch_b),
            name="battery_charge_loss_epigraph",
        )
        model.add_constraints(
            bat_dis_loss_b >= (dis_slope * bat_dis_dc_b) + (dis_intercept * p_ref_dis_b),
            name="battery_discharge_loss_epigraph",
        )

        if degradation_state_enabled:
            if bat_cycle_fade is None or bat_eff_cap is None:
                raise InputValidationError(
                    "Battery degradation mode is active, but battery_cycle_fade/"
                    "battery_effective_energy_capacity variables are missing."
                )
            # Track degraded usable energy directly in kWh. This keeps the
            # dynamic battery model linear and lets degradation affect both
            # energy and power limits without tying the physics to a global
            # planning upper bound such as battery_max_installable_capacity_kwh.
            model.add_constraints(
                bat_eff_cap <= bat_cap_available,
                name="battery_effective_energy_capacity_upper_available",
            )

            # Annual cycle fade (semi-empirical, single source): the capacity lost in a
            # year is the temperature- and DoD-aware coefficient beta(T) times the DC-side
            # energy exchanged (charge + discharge summed, matching beta's calibration of
            # 2*DoD throughput per full cycle), summed over the year. beta is a
            # (period, year, scenario) field broadcast over the cohort dimension. Defining
            # the fade as one variable PER YEAR (rather than per hour) removes the
            # 8760x per-period fade constraints while keeping the state recursion exact.
            if beta_cycle is None:
                raise InputValidationError(
                    "Battery cycle fade is active but the semi-empirical beta(T) coefficient "
                    "field 'battery_beta_cycle' is missing from the dataset."
                )
            model.add_constraints(
                bat_cycle_fade == (beta_cycle * (bat_ch_dc + bat_dis_dc)).sum("period"),
                name="battery_cycle_fade_definition",
            )

            model.add_constraints(
                bat_eff_cap.sel(year=first_year)
                == soh0_scalar * bat_cap_available.sel(year=first_year),
                name="battery_effective_energy_capacity_initial",
            )
            model.add_constraints(
                soc.sel(year=first_year).isel(period=0)
                == soc0_scalar * bat_eff_cap.sel(year=first_year),
                name="soc_initial",
            )
            for idx in range(1, len(year_values)):
                prev_year = year_values[idx - 1]
                cur_year = year_values[idx]
                commission_cur = bat_commission_year.sel(year=cur_year)
                commission_cur_state = commission_cur.expand_dims(scenario=sets.coords["scenario"])
                # Annual fade (already summed over the year).
                continued_eff_cap = bat_eff_cap.sel(year=prev_year) - bat_cycle_fade.sel(
                    year=prev_year
                )
                reset_eff_cap = soh0_scalar * bat_cap_available.sel(year=cur_year)
                target_eff_cap = continued_eff_cap + commission_cur_state * (
                    reset_eff_cap - continued_eff_cap
                )
                # When the availability ceiling declines within a cohort's life (a
                # positive calendar rate), keep this as an upper bound so the LP takes
                # min(continuation, declining ceiling) and cannot be over-constrained.
                # When there is no exogenous decline, make it an exact EQUALITY: the
                # state is then fully determined by the cycle-fade recursion (no
                # degeneracy, no reliance on a tie-breaking regularizer).
                if exogenous_fade_active:
                    model.add_constraints(
                        bat_eff_cap.sel(year=cur_year) <= target_eff_cap,
                        name=f"battery_effective_energy_capacity_year_link_{cur_year}",
                    )
                else:
                    model.add_constraints(
                        bat_eff_cap.sel(year=cur_year) == target_eff_cap,
                        name=f"battery_effective_energy_capacity_year_link_{cur_year}",
                    )
                reset_soc = soc0_scalar * bat_eff_cap.sel(year=cur_year)
                continued_soc = (
                    soc.sel(year=prev_year).isel(period=T - 1)
                    + bat_ch_dc.sel(year=prev_year).isel(period=T - 1)
                    - bat_dis_dc.sel(year=prev_year).isel(period=T - 1)
                )
                target_soc = continued_soc + commission_cur_state * (reset_soc - continued_soc)
                model.add_constraints(
                    soc.sel(year=cur_year).isel(period=0) == target_soc,
                    name=f"soc_year_link_{cur_year}",
                )
            soc_upper_bound = bat_eff_cap
            soc_lower_bound = (1.0 - dod) * bat_eff_cap
            soc_upper_bound = soc_upper_bound.expand_dims(period=period)
            soc_lower_bound = soc_lower_bound.expand_dims(period=period)

        if T > 1:
            model.add_constraints(
                soc.isel(period=slice(1, None))
                == soc.isel(period=slice(0, -1))
                + bat_ch_dc.isel(period=slice(0, -1))
                - bat_dis_dc.isel(period=slice(0, -1)),
                name="soc_balance",
            )
        if not degradation_state_enabled:
            model.add_constraints(
                soc.sel(year=first_year).isel(period=0)
                == soc0_scalar * bat_cap_available.sel(year=first_year),
                name="soc_initial",
            )
            for idx in range(1, len(year_values)):
                prev_year = year_values[idx - 1]
                cur_year = year_values[idx]
                commission_cur = bat_commission_year.sel(year=cur_year)
                commission_cur_state = commission_cur.expand_dims(scenario=sets.coords["scenario"])
                reset_soc = soc0_scalar * bat_cap_available.sel(year=cur_year)
                continued_soc = (
                    soc.sel(year=prev_year).isel(period=T - 1)
                    + bat_ch_dc.sel(year=prev_year).isel(period=T - 1)
                    - bat_dis_dc.sel(year=prev_year).isel(period=T - 1)
                )
                target_soc = continued_soc + commission_cur_state * (reset_soc - continued_soc)
                model.add_constraints(
                    soc.sel(year=cur_year).isel(period=0) == target_soc,
                    name=f"soc_year_link_{cur_year}",
                )
            soc_upper_bound = bat_cap_available
            soc_lower_bound = (1.0 - dod) * bat_cap_available
    else:
        model.add_constraints(
            soc.sel(year=first_year).isel(period=0)
            == soc0_scalar * bat_cap_available.sel(year=first_year),
            name="soc_initial",
        )
        if T > 1:
            model.add_constraints(
                soc.isel(period=slice(1, None))
                == soc.isel(period=slice(0, -1))
                + eta_c * bat_ch.isel(period=slice(0, -1))
                - bat_dis.isel(period=slice(0, -1)) / eta_d,
                name="soc_balance",
            )
        for idx in range(1, len(year_values)):
            prev_year = year_values[idx - 1]
            cur_year = year_values[idx]
            commission_cur = bat_commission_year.sel(year=cur_year)
            commission_cur_state = commission_cur.expand_dims(scenario=sets.coords["scenario"])
            reset_soc = soc0_scalar * bat_cap_available.sel(year=cur_year)
            continued_soc = (
                soc.sel(year=prev_year).isel(period=T - 1)
                + eta_c * bat_ch.sel(year=prev_year).isel(period=T - 1)
                - bat_dis.sel(year=prev_year).isel(period=T - 1) / eta_d
            )
            target_soc = continued_soc + commission_cur_state * (reset_soc - continued_soc)
            model.add_constraints(
                soc.sel(year=cur_year).isel(period=0) == target_soc,
                name=f"soc_year_link_{cur_year}",
            )
        soc_upper_bound = bat_cap_available
        soc_lower_bound = (1.0 - dod) * bat_cap_available
    if battery_loss_model == CONVEX_LOSS_EPIGRAPH and not degradation_state_enabled:
        soc_upper_bound = bat_cap_available
        soc_lower_bound = (1.0 - dod) * bat_cap_available
    model.add_constraints(soc <= soc_upper_bound, name="soc_upper")
    model.add_constraints(soc >= soc_lower_bound, name="soc_lower")

    # ------------------------------------------------------------------
    # 5) Grid limits and nodal balance
    # ------------------------------------------------------------------
    if on_grid and grid_imp is not None:
        # With hourly steps, the kW line capacity is used directly as a per-step
        # kWh interchange bound (Δt = 1 h). Transmission efficiency is applied
        # in the balance and scope-2 accounting, not in these limits.
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
    gen_sum = gen_gen.sum("inv_step")
    bat_net = (bat_dis - bat_ch).sum("inv_step")
    lhs = res_sum + gen_sum + bat_net + ll

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
    e_gen = gen_gen.sum("period").sum("inv_step")  # (year, scenario)

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
            model.add_constraints(
                e_renew >= (min_res_pen * e_total), name="min_renewable_penetration"
            )
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
    land_limit = finite_nonnegative_scalar_limit(
        land_m2.values,
        name="land_availability_m2",
        error_cls=InputValidationError,
    )
    if land_limit is not None:
        model.add_constraints(area_used <= land_m2, name="land_availability")
