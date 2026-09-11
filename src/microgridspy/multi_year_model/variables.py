# generation_planning/modeling/variables.py
from __future__ import annotations

import linopy as lp
import numpy as np
import xarray as xr

from microgridspy.data_pipeline.battery_loss_model import (
    CONVEX_LOSS_EPIGRAPH,
    normalize_battery_loss_model,
)
from microgridspy.multi_year_model.params import get_params


class InputValidationError(RuntimeError):
    pass


def initialize_vars(sets: xr.Dataset, data: xr.Dataset, model: lp.Model) -> dict[str, lp.Variable]:
    """
    Define multi-year decision variables using labeled coords from `sets`.

    Design variables (scenario-invariant), interpreted as INCREMENTAL "units" of capacities:
      - res_units(inv_step,resource)
      - battery_units(inv_step)
      - generator_units(inv_step)

    Operational variables:
      - res_generation(period, year, scenario, resource)
      - generator_generation(period, year, scenario, inv_step)
      - fuel_consumption(period, year, scenario, inv_step)
      - battery_charge(period, year, scenario, inv_step)
      - battery_discharge(period, year, scenario, inv_step)
      - battery_soc(period, year, scenario, inv_step)
      - lost_load(period, year, scenario)

    Optional on-grid:
      - grid_import(period, year, scenario)
      - grid_export(period, year, scenario) (if allow_export)

    """
    if not isinstance(sets, xr.Dataset):
        raise InputValidationError("initialize_vars: sets must be an xarray.Dataset.")
    if not isinstance(data, xr.Dataset):
        raise InputValidationError("initialize_vars: data must be an xarray.Dataset.")

    # --- required coords (per your sets.py)
    for c in ("period", "year", "inv_step", "scenario", "resource"):
        if c not in sets.coords:
            raise InputValidationError(f"initialize_vars: missing required coord in sets: '{c}'")

    period = sets.coords["period"]
    year = sets.coords["year"]
    inv_step = sets.coords["inv_step"]
    scenario = sets.coords["scenario"]
    resource = sets.coords["resource"]

    # --- feature flags (stored in data.attrs in your initializer)
    p = get_params(data)
    on_grid = p.is_grid_on()
    allow_export = p.is_grid_export_enabled()
    partial_load_enabled = bool(
        (p.settings.get("generator", {}) or {}).get("partial_load_modelling_enabled", False)
    )
    battery_loss_model = normalize_battery_loss_model(
        ((p.settings.get("battery_model", {}) or {}).get("loss_model")),
        default="constant_efficiency",
    )
    battery_model_settings = p.settings.get("battery_model", {}) or {}
    degradation_settings = battery_model_settings.get("degradation_model", {}) or {}
    cycle_fade_enabled = bool(degradation_settings.get("cycle_fade_enabled", False))
    degradation_state_enabled = cycle_fade_enabled
    # In the current multi-year formulation this flag controls integer sizing
    # of investment-unit variables only; it is not chronological unit commitment.
    is_integer = bool(p.settings.get("unit_commitment", False))

    vars: dict[str, lp.Variable] = {}

    # =========================================================================
    # Design / sizing variables (scenario-invariant)
    # =========================================================================
    # Renewable installed capacity [kW] by resource
    vars["res_units"] = model.add_variables(
        lower=0.0,
        integer=is_integer,
        dims=("inv_step", "resource"),
        coords={"inv_step": inv_step, "resource": resource},
        name="res_units",
    )

    # Battery installed energy capacity [kWh] (scalar)
    vars["battery_units"] = model.add_variables(
        lower=0.0,
        dims=("inv_step",),
        coords={"inv_step": inv_step},
        integer=is_integer,
        name="battery_units",
    )
    vars["battery_inverter_power"] = model.add_variables(
        lower=0.0,
        dims=("inv_step",),
        coords={"inv_step": inv_step},
        name="battery_inverter_power",
    )

    # Generator installed power capacity [kW] (scalar)
    vars["generator_units"] = model.add_variables(
        lower=0.0,
        dims=("inv_step",),
        coords={"inv_step": inv_step},
        integer=is_integer,
        name="generator_units",
    )

    # =========================================================================
    # Operational variables
    # =========================================================================
    # Renewable generation [kWh] by resource
    vars["res_generation"] = model.add_variables(
        lower=0.0,
        dims=("period", "year", "scenario", "resource"),
        coords={"period": period, "year": year, "scenario": scenario, "resource": resource},
        name="res_generation",
    )

    # Generator generation [kWh]
    vars["generator_generation"] = model.add_variables(
        lower=0.0,
        dims=("period", "year", "scenario", "inv_step"),
        coords={"period": period, "year": year, "scenario": scenario, "inv_step": inv_step},
        name="generator_generation",
    )

    # Fuel consumption [unit_fuel] (generic fuel unit, consistent with fuel.yaml keys)
    vars["fuel_consumption"] = model.add_variables(
        lower=0.0,
        dims=("period", "year", "scenario", "inv_step"),
        coords={"period": period, "year": year, "scenario": scenario, "inv_step": inv_step},
        name="fuel_consumption",
    )

    # Generator committed (online) units [dimensionless]. Under the clustered
    # unit-commitment partial-load model, this is the integer number of cohort
    # units online each hour; the no-load fuel intercept is charged per online unit.
    commitment_mode = (
        str((p.settings.get("generator", {}) or {}).get("partial_load_commitment", "integer"))
        .strip()
        .lower()
    )
    if commitment_mode == "relaxed":  # legacy: the LP relaxation was removed
        commitment_mode = "integer"
    if partial_load_enabled and commitment_mode == "integer":
        vars["generator_online_units"] = model.add_variables(
            lower=0.0,
            integer=True,
            dims=("period", "year", "scenario", "inv_step"),
            coords={"period": period, "year": year, "scenario": scenario, "inv_step": inv_step},
            name="generator_online_units",
        )

    # Battery charge/discharge/SoC [kWh]
    vars["battery_charge"] = model.add_variables(
        lower=0.0,
        dims=("period", "year", "scenario", "inv_step"),
        coords={"period": period, "year": year, "scenario": scenario, "inv_step": inv_step},
        name="battery_charge",
    )
    vars["battery_discharge"] = model.add_variables(
        lower=0.0,
        dims=("period", "year", "scenario", "inv_step"),
        coords={"period": period, "year": year, "scenario": scenario, "inv_step": inv_step},
        name="battery_discharge",
    )
    vars["battery_soc"] = model.add_variables(
        lower=0.0,
        dims=("period", "year", "scenario", "inv_step"),
        coords={"period": period, "year": year, "scenario": scenario, "inv_step": inv_step},
        name="battery_soc",
    )
    if battery_loss_model == CONVEX_LOSS_EPIGRAPH:
        vars["battery_charge_dc"] = model.add_variables(
            lower=0.0,
            dims=("period", "year", "scenario", "inv_step"),
            coords={"period": period, "year": year, "scenario": scenario, "inv_step": inv_step},
            name="battery_charge_dc",
        )
        vars["battery_discharge_dc"] = model.add_variables(
            lower=0.0,
            dims=("period", "year", "scenario", "inv_step"),
            coords={"period": period, "year": year, "scenario": scenario, "inv_step": inv_step},
            name="battery_discharge_dc",
        )
        vars["battery_charge_loss"] = model.add_variables(
            lower=0.0,
            dims=("period", "year", "scenario", "inv_step"),
            coords={"period": period, "year": year, "scenario": scenario, "inv_step": inv_step},
            name="battery_charge_loss",
        )
        vars["battery_discharge_loss"] = model.add_variables(
            lower=0.0,
            dims=("period", "year", "scenario", "inv_step"),
            coords={"period": period, "year": year, "scenario": scenario, "inv_step": inv_step},
            name="battery_discharge_loss",
        )
        if degradation_state_enabled:
            # Annual cycle fade per cohort (kWh of capacity lost that year). Defined as
            # the per-year sum of beta(T)*(charge_dc+discharge_dc); aggregating to a
            # yearly variable (instead of one per hour) keeps the state recursion exact
            # while removing the 8760x per-period fade variables/constraints.
            vars["battery_cycle_fade"] = model.add_variables(
                lower=0.0,
                dims=("year", "scenario", "inv_step"),
                coords={"year": year, "scenario": scenario, "inv_step": inv_step},
                name="battery_cycle_fade",
            )
            vars["battery_effective_energy_capacity"] = model.add_variables(
                lower=0.0,
                dims=("year", "scenario", "inv_step"),
                coords={"year": year, "scenario": scenario, "inv_step": inv_step},
                name="battery_effective_energy_capacity",
            )
            # Epigraph for the battery energy CAPEX amortized over the BINDING life:
            # >= calendar annuity and >= cycle-limited annuity, so at the optimum it
            # equals max(the two) = CAPEX amortized over min(calendar, cycle) life. This
            # keeps degradation inside the annuity/no-salvage cash-flow convention (no
            # double-counting wear charge).
            vars["battery_replacement_cost"] = model.add_variables(
                lower=0.0,
                dims=("year", "scenario", "inv_step"),
                coords={"year": year, "scenario": scenario, "inv_step": inv_step},
                name="battery_replacement_cost",
            )

            # Depth-resolved cycle aging (marginal_bands): a stacked SOC-band reservoir.
            #   battery_soc_band[b]       usable stored energy in band b (0=top/shallow) [kWh]
            #   battery_discharge_band[b] DC discharge routed through band b             [kWh]
            #   battery_charge_band[b]    DC charge routed into band b                   [kWh]
            # Convex costs c_k (increasing with depth) make the optimiser cycle shallow
            # bands first, so cycling depth is emergent and the block stays a pure LP.
            cycle_fade_mode = (
                str(degradation_settings.get("cycle_fade_mode", "single_beta")).strip().lower()
            )
            if cycle_fade_mode == "marginal_bands":
                n_soc_bands = int(degradation_settings.get("n_soc_bands", 5))
                band_coord = np.arange(n_soc_bands)
                band_dims = ("soc_band", "period", "year", "scenario", "inv_step")
                band_coords = {
                    "soc_band": band_coord,
                    "period": period,
                    "year": year,
                    "scenario": scenario,
                    "inv_step": inv_step,
                }
                for _nm in (
                    "battery_soc_band",
                    "battery_discharge_band",
                    "battery_charge_band",
                ):
                    vars[_nm] = model.add_variables(
                        lower=0.0, dims=band_dims, coords=band_coords, name=_nm
                    )

    # Lost load [kWh]
    vars["lost_load"] = model.add_variables(
        lower=0.0,
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
        name="lost_load",
    )

    # =========================================================================
    # Grid variables (conditional)
    # =========================================================================
    if on_grid:
        vars["grid_import"] = model.add_variables(
            lower=0.0,
            dims=("period", "year", "scenario"),
            coords={"period": period, "year": year, "scenario": scenario},
            name="grid_import",
        )

        if allow_export:
            vars["grid_export"] = model.add_variables(
                lower=0.0,
                dims=("period", "year", "scenario"),
                coords={"period": period, "year": year, "scenario": scenario},
                name="grid_export",
            )

    return vars
