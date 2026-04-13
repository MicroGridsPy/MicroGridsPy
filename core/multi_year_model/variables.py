# generation_planning/modeling/variables.py
from __future__ import annotations

from typing import Dict

import xarray as xr
import linopy as lp

from core.data_pipeline.battery_loss_model import CONVEX_LOSS_EPIGRAPH, normalize_battery_loss_model
from core.multi_year_model.params import get_params


class InputValidationError(RuntimeError):
    pass


def initialize_vars(sets: xr.Dataset, data: xr.Dataset, model: lp.Model) -> Dict[str, lp.Variable]:
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
            raise InputValidationError(
                f"initialize_vars: missing required coord in sets: '{c}'"
            )

    period = sets.coords["period"]
    year = sets.coords["year"]
    inv_step = sets.coords["inv_step"]
    scenario = sets.coords["scenario"]
    resource = sets.coords["resource"]

    # --- feature flags (stored in data.attrs in your initializer)
    p = get_params(data)
    on_grid = p.is_grid_on()
    allow_export = p.is_grid_export_enabled()
    partial_load_enabled = bool((p.settings.get("generator", {}) or {}).get("partial_load_modelling_enabled", False))
    battery_loss_model = normalize_battery_loss_model(
        ((p.settings.get("battery_model", {}) or {}).get("loss_model")),
        default="constant_efficiency",
    )
    battery_model_settings = (p.settings.get("battery_model", {}) or {})
    degradation_settings = (battery_model_settings.get("degradation_model", {}) or {})
    cycle_fade_enabled = bool(degradation_settings.get("cycle_fade_enabled", False))
    calendar_fade_enabled = bool(degradation_settings.get("calendar_fade_enabled", False))
    degradation_state_enabled = cycle_fade_enabled or calendar_fade_enabled
    # In the current multi-year formulation this flag controls integer sizing
    # of investment-unit variables only; it is not chronological unit commitment.
    is_integer = bool(p.settings.get("unit_commitment", False))

    vars: Dict[str, lp.Variable] = {}

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
            vars["battery_cycle_fade"] = model.add_variables(
                lower=0.0,
                dims=("period", "year", "scenario", "inv_step"),
                coords={"period": period, "year": year, "scenario": scenario, "inv_step": inv_step},
                name="battery_cycle_fade",
            )
            vars["battery_average_soc"] = model.add_variables(
                lower=0.0,
                dims=("year", "inv_step"),
                coords={"year": year, "inv_step": inv_step},
                name="battery_average_soc",
            )
            vars["battery_calendar_fade"] = model.add_variables(
                lower=0.0,
                dims=("year", "inv_step"),
                coords={"year": year, "inv_step": inv_step},
                name="battery_calendar_fade",
            )
            vars["battery_effective_energy_capacity"] = model.add_variables(
                lower=0.0,
                dims=("year", "scenario", "inv_step"),
                coords={"year": year, "scenario": scenario, "inv_step": inv_step},
                name="battery_effective_energy_capacity",
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
