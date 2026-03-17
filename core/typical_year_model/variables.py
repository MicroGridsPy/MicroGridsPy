# generation_planning/modeling/variables.py
from __future__ import annotations

from typing import Dict

import xarray as xr
import linopy as lp


class InputValidationError(RuntimeError):
    pass


def _bool_from_attrs(obj: xr.Dataset, path: list[str], default: bool = False) -> bool:
    """
    Read a nested boolean from obj.attrs, e.g. path=["settings","grid","on_grid"].

    Returns:
        bool: The value found at the nested path, cast to bool.
              If the path does not exist (or attrs is not a dict chain), returns `default`.
    """
    cur = obj.attrs
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return bool(cur)


def initialize_vars(sets: xr.Dataset, data: xr.Dataset, model: lp.Model) -> Dict[str, lp.Variable]:
    """
    Define steady_state (typical-year) decision variables using labeled coords from `sets`.

    Design variables (scenario-invariant):
      - res_units(resource)
      - battery_units()
      - generator_units()

    Operational variables:
      - res_generation(period, scenario, resource)
      - generator_generation(period, scenario)
      - fuel_consumption(period, scenario)  # unit = "unit_fuel" consistent with fuel YAML keys
      - battery_charge(period, scenario)
      - battery_discharge(period, scenario)
      - battery_soc(period, scenario)
      - lost_load(period, scenario)

    Optional on-grid:
      - grid_import(period, scenario)
      - grid_export(period, scenario) (if allow_export)

    Optional partial-load curve scaffolding:
      - gen_segment_energy(period, scenario, curve_point) (only if curve exists)
    """
    if not isinstance(sets, xr.Dataset):
        raise InputValidationError("initialize_vars: sets must be an xarray.Dataset.")
    if not isinstance(data, xr.Dataset):
        raise InputValidationError("initialize_vars: data must be an xarray.Dataset.")

    # --- required coords (per your sets.py)
    for c in ("period", "scenario", "resource"):
        if c not in sets.coords:
            raise InputValidationError(
                f"initialize_vars: missing required coord in sets: '{c}'"
            )

    period = sets.coords["period"]
    scenario = sets.coords["scenario"]
    resource = sets.coords["resource"]

    # --- feature flags (stored in data.attrs in your initializer)
    on_grid = _bool_from_attrs(data, ["settings", "grid", "on_grid"], default=False)
    allow_export = _bool_from_attrs(data, ["settings", "grid", "allow_export"], default=False)
    partial_load_enabled = _bool_from_attrs(
        data, ["settings", "generator", "partial_load_modelling_enabled"], default=False
    )
    is_integer = _bool_from_attrs(data, ["settings", "unit_commitment"], default=False)

    # curve coord exists only if you merged curve_ds
    has_curve_coord = "curve_point" in data.coords

    vars: Dict[str, lp.Variable] = {}

    # =========================================================================
    # Design / sizing variables (scenario-invariant)
    # =========================================================================
    # Renewable installed capacity [kW] by resource
    vars["res_units"] = model.add_variables(
        lower=0.0,
        integer=is_integer,
        dims=("resource",),
        coords={"resource": resource},
        name="res_units",
    )

    # Battery installed energy capacity [kWh] (scalar)
    vars["battery_units"] = model.add_variables(
        lower=0.0,
        integer=is_integer,
        name="battery_units",
    )

    # Generator installed power capacity [kW] (scalar)
    vars["generator_units"] = model.add_variables(
        lower=0.0,
        integer=is_integer,
        name="generator_units",
    )

    # =========================================================================
    # Operational variables
    # =========================================================================
    # Renewable generation [kWh] by resource
    vars["res_generation"] = model.add_variables(
        lower=0.0,
        dims=("period", "scenario", "resource"),
        coords={"period": period, "scenario": scenario, "resource": resource},
        name="res_generation",
    )

    # Generator generation [kWh]
    vars["generator_generation"] = model.add_variables(
        lower=0.0,
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
        name="generator_generation",
    )

    # Fuel consumption [unit_fuel] (generic fuel unit, consistent with fuel.yaml keys)
    vars["fuel_consumption"] = model.add_variables(
        lower=0.0,
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
        name="fuel_consumption",
    )

    # Battery charge/discharge/SoC [kWh]
    vars["battery_charge"] = model.add_variables(
        lower=0.0,
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
        name="battery_charge",
    )
    vars["battery_discharge"] = model.add_variables(
        lower=0.0,
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
        name="battery_discharge",
    )
    vars["battery_soc"] = model.add_variables(
        lower=0.0,
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
        name="battery_soc",
    )

    # Lost load [kWh]
    vars["lost_load"] = model.add_variables(
        lower=0.0,
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
        name="lost_load",
    )

    # =========================================================================
    # Grid variables (conditional)
    # =========================================================================
    if on_grid:
        vars["grid_import"] = model.add_variables(
            lower=0.0,
            dims=("period", "scenario"),
            coords={"period": period, "scenario": scenario},
            name="grid_import",
        )

        if allow_export:
            vars["grid_export"] = model.add_variables(
                lower=0.0,
                dims=("period", "scenario"),
                coords={"period": period, "scenario": scenario},
                name="grid_export",
            )

    # =========================================================================
    # Optional: partial-load curve scaffolding
    # =========================================================================
    # Keep this minimal: create segment energy variables only if curve exists.
    # Later you can enforce convex combination / SOS2 / piecewise constraints.
    if partial_load_enabled and has_curve_coord:
        curve_point = data.coords["curve_point"]
        vars["gen_segment_energy"] = model.add_variables(
            lower=0.0,
            dims=("period", "scenario", "curve_point"),
            coords={"period": period, "scenario": scenario, "curve_point": curve_point},
            name="gen_segment_energy",
        )

    return vars
