# generation_planning/modeling/variables.py
from __future__ import annotations

from typing import Dict

import xarray as xr
import linopy as lp

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
      - generator_generation(period, year, scenario)
      - fuel_consumption(period, year, scenario)  
      - battery_charge(period, year, scenario)
      - battery_discharge(period, year, scenario)
      - battery_soc(period, year, scenario)
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
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
        name="generator_generation",
    )

    # Fuel consumption [unit_fuel] (generic fuel unit, consistent with fuel.yaml keys)
    vars["fuel_consumption"] = model.add_variables(
        lower=0.0,
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
        name="fuel_consumption",
    )

    # Battery charge/discharge/SoC [kWh]
    vars["battery_charge"] = model.add_variables(
        lower=0.0,
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
        name="battery_charge",
    )
    vars["battery_discharge"] = model.add_variables(
        lower=0.0,
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
        name="battery_discharge",
    )
    vars["battery_soc"] = model.add_variables(
        lower=0.0,
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
        name="battery_soc",
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
