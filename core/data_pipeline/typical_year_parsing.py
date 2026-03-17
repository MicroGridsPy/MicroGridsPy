# generation_planning/modeling/data.py
from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import xarray as xr

from core.data_pipeline.utils import (
    as_float,
    as_float_or_nan,
    as_str,
    broadcast_to_scenario,
    coord_labels,
    coerce_numeric_array,
    normalize_weights,
    read_csv_or_raise,
    read_json_or_raise,
    read_yaml_or_raise,
    validate_hour_column,
)


class InputValidationError(RuntimeError):
    pass


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------
_read_json = partial(read_json_or_raise, error_cls=InputValidationError)
_read_yaml = partial(read_yaml_or_raise, error_cls=InputValidationError)
_as_float = partial(as_float, error_cls=InputValidationError)
_as_float_or_nan = partial(as_float_or_nan, error_cls=InputValidationError)
_as_str = partial(as_str, error_cls=InputValidationError)
_normalize_weights = normalize_weights
_broadcast_to_scenario = broadcast_to_scenario


def _load_csv(path: Path, *, header: int | list[int]) -> pd.DataFrame:
    return read_csv_or_raise(path, header=header, error_cls=InputValidationError)


def _scenario_labels(coord: xr.DataArray) -> list[str]:
    return coord_labels(coord)


def _resource_labels(coord: xr.DataArray) -> list[str]:
    return coord_labels(coord)


def _validate_meta_hour_2level(
    df: pd.DataFrame,
    *,
    path: Path,
    period_coord: xr.DataArray,
    missing_col_suffix: str = "",
) -> tuple[np.ndarray, np.ndarray]:
    if ("meta", "hour") not in df.columns:
        suffix = f" {missing_col_suffix}".rstrip()
        raise InputValidationError(f"{path.name}: missing required column ('meta','hour').{suffix}")
    return validate_hour_column(
        df[("meta", "hour")],
        path=path,
        period_coord=period_coord,
        error_cls=InputValidationError,
    )


def _validate_meta_hour_3level(
    df: pd.DataFrame,
    *,
    path: Path,
    period_coord: xr.DataArray,
) -> tuple[np.ndarray, np.ndarray]:
    first_col = df.columns[0]
    if not (len(first_col) == 3 and str(first_col[0]) == "meta" and str(first_col[1]) == "hour"):
        raise InputValidationError(
            f"{path.name}: first column must be meta/hour with 3 header rows. "
            f"Got first column={first_col!r}."
        )
    return validate_hour_column(
        df[first_col],
        path=path,
        period_coord=period_coord,
        error_cls=InputValidationError,
    )

# -----------------------------------------------------------------------------
# load data from CSV templates
def _load_load_demand_csv(
    path: Path,
    *,
    period_coord: xr.DataArray,
    scenario_coord: xr.DataArray,
) -> xr.DataArray:
    """
    Parse typical-year load demand template:

      meta,low_demand,high_demand
      hour,typical_year,typical_year
      0,,
      1,,

    Requirements:
      - CSV uses header=[0,1]
      - hour column is exactly ('meta','hour') (or first column at least)
      - scenario columns are (scenario_label,'typical_year')
      - hour must match sets.period exactly (0..8759)
    """
    df = _load_csv(path, header=[0, 1])

    hour, _ = _validate_meta_hour_2level(
        df,
        path=path,
        period_coord=period_coord,
        missing_col_suffix="Your time series templates must include meta/hour as the first column.",
    )

    # --- scenario columns: (scenario_label, typical_year) ---
    scenario_labels = _scenario_labels(scenario_coord)

    missing_cols = [(s, "typical_year") for s in scenario_labels if (s, "typical_year") not in df.columns]
    if missing_cols:
        missing_names = ", ".join([f"({a},{b})" for a, b in missing_cols])
        raise InputValidationError(
            f"{path.name}: missing scenario columns: {missing_names}. "
            f"Expected scenarios: {scenario_labels} (each with 'typical_year')."
        )

    # extract in scenario order
    mat = df.loc[:, [(s, "typical_year") for s in scenario_labels]].to_numpy()

    # validate numeric
    mat = coerce_numeric_array(mat)
    if np.isnan(mat).any():
        # identify first bad location (row, col)
        r, c = np.argwhere(np.isnan(mat))[0]
        raise InputValidationError(
            f"{path.name}: found missing/non-numeric load value at hour={hour[r]}, scenario='{scenario_labels[int(c)]}'."
        )

    da = xr.DataArray(
        mat,
        coords={"period": period_coord, "scenario": scenario_coord},
        dims=("period", "scenario"),
        name="load_demand_kwh",
        attrs={"units": "kWh", "source_file": str(path)},
    )
    return da

# -----------------------------------------------------------------------------
# load resource availability from CSV template
# -----------------------------------------------------------------------------
def _load_resource_availability_csv(
    path: Path,
    *,
    period_coord: xr.DataArray,
    scenario_coord: xr.DataArray,
    resource_coord: xr.DataArray,
    year_label: str = "typical_year",
) -> xr.DataArray:
    """
    Parse typical-year resource availability template with 3 header rows:

    meta,low_demand,low_demand,high_demand,high_demand
    hour,typical_year,typical_year,typical_year,typical_year
    ,Solar,Wind,Solar,Wind
    0,0.0,0.0,0.0,0.0
    ...

    Returns:
      xr.DataArray availability_cf(period, scenario, resource)
    """
    df = _load_csv(path, header=[0, 1, 2])
    hour, expected = _validate_meta_hour_3level(df, path=path, period_coord=period_coord)

    scenario_labels = _scenario_labels(scenario_coord)
    resource_labels = _resource_labels(resource_coord)

    # --- validate required columns exist for every (scenario, year_label, resource) ---
    missing = []
    for s in scenario_labels:
        for r in resource_labels:
            col = (s, year_label, r)
            if col not in df.columns:
                missing.append(col)

    if missing:
        sample = ", ".join([f"({a},{b},{c})" for a, b, c in missing[:10]])
        raise InputValidationError(
            f"{path.name}: missing required availability columns for the current sets. "
            f"Examples: {sample}"
            + (f" ... (+{len(missing)-10} more)" if len(missing) > 10 else "")
        )

    # --- extract into (period, scenario, resource) ---
    blocks = []
    for s in scenario_labels:
        cols_sr = [(s, year_label, r) for r in resource_labels]
        mat_sr = df.loc[:, cols_sr].to_numpy()   # (period, resource)
        blocks.append(mat_sr)

    # blocks: list of (period, resource) for each scenario -> stack to (scenario, period, resource)
    arr = np.stack(blocks, axis=0)

    # reorder -> (period, scenario, resource)
    arr = np.transpose(arr, (1, 0, 2))

    # numeric validation
    arr = coerce_numeric_array(arr.reshape(arr.shape[0], -1)).reshape(arr.shape)
    if np.isnan(arr).any():
        p, s, r = np.argwhere(np.isnan(arr))[0]
        raise InputValidationError(
            f"{path.name}: found missing/non-numeric availability at "
            f"hour={int(expected[p])}, scenario='{scenario_labels[int(s)]}', resource='{resource_labels[int(r)]}'."
        )

    da = xr.DataArray(
        arr,
        coords={"period": period_coord, "scenario": scenario_coord, "resource": resource_coord},
        dims=("period", "scenario", "resource"),
        name="renewable_availability_cf",
        attrs={"units": "-", "source_file": str(path), "year_label": year_label},
    )
    return da

def _load_renewables_yaml(
    path: Path,
    *,
    scenario_coord: xr.DataArray,
    resource_coord: xr.DataArray,
) -> xr.Dataset:
    """
    Load steady_state renewable techno-economic parameters from inputs/renewables.yaml.

    Output dims:
      - resource                 (scenario-invariant params)
      - scenario, resource       (scenario-dependent params)

    Expected YAML structure (NEW):
      renewables:
        - resource: <label>
          investment:
            by_step:
              "<any>": {investment-side params}   # we take the FIRST entry (typical-year ignores cohorts)
          technical:
            {step-invariant technical params}
          operation:
            by_scenario:
              "<scenario>": {scenario operation params}

    Notes:
      - Typical-year ignores investment steps; it will read the first available by_step entry.
      - Dynamic-only degradation is ignored here (not applicable).
      - max_installable_capacity_kw may be NaN if None in YAML.
    """
    if not path.exists():
        raise InputValidationError(f"Missing required file: {path}")

    payload = _read_yaml(path)

    ren_list = payload.get("renewables", None)
    if not isinstance(ren_list, list) or len(ren_list) == 0:
        raise InputValidationError(f"{path.name}: expected a non-empty list under key 'renewables'.")

    scenario_labels = _scenario_labels(scenario_coord)
    resource_labels = _resource_labels(resource_coord)
    res_to_idx = {lab: i for i, lab in enumerate(resource_labels)}

    # For typical-year we keep the same variable names, but no inv_step dimension.
    PARAMS_INVESTMENT = [
        "nominal_capacity_kw",
        "lifetime_years",
        "specific_investment_cost_per_kw",
        "wacc",
        "grant_share_of_capex",
        "embedded_emissions_kgco2e_per_kw",
    ]
    PARAMS_TECHNICAL = [
        "inverter_efficiency",
        "specific_area_m2_per_kw",
        "max_installable_capacity_kw",
    ]
    PARAMS_OPERATION = [
        "fixed_om_share_per_year",
        "production_subsidy_per_kwh",
    ]

    n_r = len(resource_labels)
    n_s = len(scenario_labels)

    inv_arr = {k: np.full((n_r,), np.nan, dtype=float) for k in PARAMS_INVESTMENT}
    tech_arr = {k: np.full((n_r,), np.nan, dtype=float) for k in PARAMS_TECHNICAL}
    op_arr = {k: np.full((n_s, n_r), np.nan, dtype=float) for k in PARAMS_OPERATION}

    for item in ren_list:
        if not isinstance(item, dict):
            raise InputValidationError(f"{path.name}: each element in 'renewables' must be a mapping/dict.")

        res_label = item.get("resource", None)
        if res_label is None:
            raise InputValidationError(f"{path.name}: a renewable entry is missing required key 'resource'.")
        res_label = str(res_label)

        if res_label not in res_to_idx:
            raise InputValidationError(
                f"{path.name}: renewable.resource='{res_label}' not found in sets.resource={resource_labels}."
            )
        j = res_to_idx[res_label]

        # ---- investment.by_step (take first step entry)
        inv_block = item.get("investment", None)
        if not isinstance(inv_block, dict):
            raise InputValidationError(f"{path.name}: resource '{res_label}' missing/invalid 'investment' mapping.")

        inv_by_step = inv_block.get("by_step", None)
        if not isinstance(inv_by_step, dict) or len(inv_by_step) == 0:
            raise InputValidationError(f"{path.name}: resource '{res_label}' investment.by_step missing/invalid/empty.")

        # take first available step (typical-year ignores cohorts)
        first_step_key = next(iter(inv_by_step.keys()))
        base = inv_by_step.get(first_step_key)
        if not isinstance(base, dict):
            raise InputValidationError(
                f"{path.name}: resource '{res_label}' investment.by_step['{first_step_key}'] must be a dict."
            )

        for k in PARAMS_INVESTMENT:
            if k not in base:
                raise InputValidationError(
                    f"{path.name}: missing investment param '{k}' in resource '{res_label}' (investment.by_step['{first_step_key}'])."
                )

            inv_arr[k][j] = _as_float(base.get(k), name=f"{res_label}/investment/{first_step_key}/{k}", default=0.0)

        # ---- technical (step-invariant)
        tech_block = item.get("technical", None)
        if not isinstance(tech_block, dict):
            raise InputValidationError(f"{path.name}: resource '{res_label}' missing/invalid 'technical' mapping.")

        for k in PARAMS_TECHNICAL:
            if k not in tech_block:
                raise InputValidationError(
                    f"{path.name}: missing technical param '{k}' in resource '{res_label}' (technical.{k})."
                )
            if k in ("max_installable_capacity_kw", "specific_area_m2_per_kw"):
                tech_arr[k][j] = _as_float_or_nan(tech_block.get(k), name=f"{res_label}/technical/{k}")
            else:
                tech_arr[k][j] = _as_float(tech_block.get(k), name=f"{res_label}/technical/{k}", default=0.0)

        # ---- operation.by_scenario
        op_block = item.get("operation", None)
        if not isinstance(op_block, dict):
            raise InputValidationError(f"{path.name}: resource '{res_label}' missing/invalid 'operation' mapping.")

        by_scenario = op_block.get("by_scenario", None)
        if not isinstance(by_scenario, dict):
            raise InputValidationError(f"{path.name}: resource '{res_label}' operation.by_scenario missing/invalid.")

        for si, s_lab in enumerate(scenario_labels):
            if s_lab not in by_scenario:
                raise InputValidationError(
                    f"{path.name}: resource '{res_label}' missing scenario '{s_lab}' in operation.by_scenario."
                )
            sb = by_scenario[s_lab]
            if not isinstance(sb, dict):
                raise InputValidationError(
                    f"{path.name}: operation.by_scenario['{s_lab}'] for resource '{res_label}' must be a dict."
                )

            for k in PARAMS_OPERATION:
                if k not in sb:
                    raise InputValidationError(
                        f"{path.name}: missing operation param '{k}' in resource '{res_label}', scenario '{s_lab}'."
                    )
                op_arr[k][si, j] = _as_float(sb.get(k), name=f"{res_label}/operation/{s_lab}/{k}", default=0.0)

    # -----------------------------
    # Build xr.Dataset
    # -----------------------------
    data_vars: Dict[str, xr.DataArray] = {}

    for k in PARAMS_INVESTMENT:
        var_name = f"res_{k}"
        data_vars[var_name] = xr.DataArray(
            inv_arr[k],
            coords={"resource": resource_coord},
            dims=("resource",),
            name=var_name,
            attrs={"source_file": str(path), "component": "renewable", "original_key": k, "scenario_dependent": False},
        )

    for k in PARAMS_TECHNICAL:
        var_name = f"res_{k}"
        data_vars[var_name] = xr.DataArray(
            tech_arr[k],
            coords={"resource": resource_coord},
            dims=("resource",),
            name=var_name,
            attrs={"source_file": str(path), "component": "renewable", "original_key": k, "scenario_dependent": False},
        )

    for k in PARAMS_OPERATION:
        var_name = f"res_{k}"
        data_vars[var_name] = xr.DataArray(
            op_arr[k],
            coords={"scenario": scenario_coord, "resource": resource_coord},
            dims=("scenario", "resource"),
            name=var_name,
            attrs={"source_file": str(path), "component": "renewable", "original_key": k, "scenario_dependent": True},
        )

    ds = xr.Dataset(data_vars=data_vars)
    ds.attrs["settings"] = {"inputs_loaded": {"renewables_yaml": str(path)}, "schema": "new_cohort_investment_only"}
    return ds


def _load_battery_yaml(
    path: Path,
    *,
    scenario_coord: xr.DataArray,
) -> xr.Dataset:
    """
    Load steady_state battery parameters from inputs/battery.yaml (NEW SCHEMA).

    Expected YAML structure:
      battery:
        label: ...
        investment:
          by_step:
            "base" OR "1" OR "<inv_step>":
              {investment-side params}
        technical:
          {technical params}
        operation:
          by_scenario:
            "<scenario>":
              {operation params}

    Notes:
      - steady_state ignores investment steps beyond the first entry we find.
      - Degradation keys are ignored in steady_state even if present.
    """
    payload = _read_yaml(path)

    bat = payload.get("battery", None)
    if not isinstance(bat, dict):
        raise InputValidationError(f"{path.name}: missing/invalid 'battery' mapping.")

    scenario_labels = _scenario_labels(scenario_coord)
    n_s = len(scenario_labels)

    INVESTMENT = [
        "nominal_capacity_kwh",
        "specific_investment_cost_per_kwh",
        "wacc",
        "calendar_lifetime_years",
        "embedded_emissions_kgco2e_per_kwh",
    ]
    TECHNICAL = [
        "charge_efficiency",
        "discharge_efficiency",
        "initial_soc",
        "depth_of_discharge",
        "max_discharge_time_hours",
        "max_charge_time_hours",
        "max_installable_capacity_kwh",      # allow None -> NaN
    ]
    OPERATION = [
        "fixed_om_share_per_year",
    ]

    # -----------------------------
    # investment.by_step -> take a single base block
    # -----------------------------
    inv = bat.get("investment", None)
    if not isinstance(inv, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.investment mapping.")

    inv_by_step = inv.get("by_step", None)
    if not isinstance(inv_by_step, dict) or len(inv_by_step) == 0:
        raise InputValidationError(f"{path.name}: missing/invalid battery.investment.by_step mapping.")

    # Prefer 'base' if present, else take first key deterministically
    if "base" in inv_by_step and isinstance(inv_by_step["base"], dict):
        inv_base = inv_by_step["base"]
    else:
        first_key = sorted(inv_by_step.keys(), key=lambda x: str(x))[0]
        inv_base = inv_by_step.get(first_key)
        if not isinstance(inv_base, dict):
            raise InputValidationError(f"{path.name}: battery.investment.by_step['{first_key}'] must be a dict.")

    inv_vals = {}
    for k in INVESTMENT:
        if k not in inv_base:
            raise InputValidationError(f"{path.name}: missing investment param '{k}' in battery.investment.by_step.")
        inv_vals[k] = _as_float(inv_base.get(k), name=f"battery/investment/base/{k}", default=0.0)


    # -----------------------------
    # technical (scalars)
    # -----------------------------
    tech = bat.get("technical", None)
    if not isinstance(tech, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.technical mapping.")

    tech_vals = {}
    for k in TECHNICAL:
        if k not in tech:
            raise InputValidationError(f"{path.name}: missing technical param '{k}' in battery.technical.")

        if k in ("max_installable_capacity_kwh",):
            tech_vals[k] = _as_float_or_nan(tech.get(k), name=f"battery/technical/{k}")
        else:
            tech_vals[k] = _as_float(tech.get(k), name=f"battery/technical/{k}", default=0.0)

    # -----------------------------
    # operation.by_scenario (scenario-dependent)
    # -----------------------------
    op = bat.get("operation", None)
    if not isinstance(op, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.operation mapping.")

    op_by_scen = op.get("by_scenario", None)
    if not isinstance(op_by_scen, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.operation.by_scenario mapping.")

    op_arr = {k: np.full((n_s,), np.nan, dtype=float) for k in OPERATION}

    for i, s in enumerate(scenario_labels):
        if s not in op_by_scen:
            raise InputValidationError(
                f"{path.name}: battery.operation.by_scenario missing scenario '{s}'. Expected: {scenario_labels}"
            )
        sb = op_by_scen[s]
        if not isinstance(sb, dict):
            raise InputValidationError(f"{path.name}: battery.operation.by_scenario['{s}'] must be a dict.")

        for k in OPERATION:
            if k not in sb:
                raise InputValidationError(f"{path.name}: missing operation param '{k}' in scenario '{s}'.")
            op_arr[k][i] = _as_float(sb.get(k), name=f"battery/operation/{s}/{k}", default=0.0)

    # -----------------------------
    # Build xr.Dataset
    # -----------------------------
    PREFIX = "battery_"
    data_vars = {}

    for k in INVESTMENT:
        var_name = f"{PREFIX}{k}"
        data_vars[var_name] = xr.DataArray(
            inv_vals[k],
            dims=(),
            name=var_name,
            attrs={"source_file": str(path), "component": "battery", "original_key": k, "scenario_dependent": False},
        )

    for k in TECHNICAL:
        var_name = f"{PREFIX}{k}"
        data_vars[var_name] = xr.DataArray(
            tech_vals[k],
            dims=(),
            name=var_name,
            attrs={"source_file": str(path), "component": "battery", "original_key": k, "scenario_dependent": False},
        )

    for k in OPERATION:
        var_name = f"{PREFIX}{k}"
        data_vars[var_name] = xr.DataArray(
            op_arr[k],
            coords={"scenario": scenario_coord},
            dims=("scenario",),
            name=var_name,
            attrs={"source_file": str(path), "component": "battery", "original_key": k, "scenario_dependent": True},
        )

    ds = xr.Dataset(data_vars=data_vars)
    ds.attrs["battery_label"] = str(bat.get("label", "Battery"))
    ds.attrs["settings"] = {"inputs_loaded": {"battery_yaml": str(path)}, "formulation": "steady_state"}
    return ds


def _load_generator_and_fuel_yaml(
    path: Path,
    *,
    inputs_dir: Path,
    scenario_coord: xr.DataArray,
) -> tuple[xr.Dataset, xr.Dataset, Optional[xr.Dataset], dict]:
    payload = _read_yaml(path)

    gen = payload.get("generator", None)
    fuel = payload.get("fuel", None)
    if not isinstance(gen, dict):
        raise InputValidationError(f"{path.name}: missing/invalid 'generator' mapping.")
    if not isinstance(fuel, dict):
        raise InputValidationError(f"{path.name}: missing/invalid 'fuel' mapping.")

    scenario_labels = _scenario_labels(scenario_coord)
    n_s = len(scenario_labels)

    # -------------------------
    # generator.investment.by_step.base
    # -------------------------
    inv_block = gen.get("investment", None)
    if not isinstance(inv_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid generator.investment mapping.")
    inv_by_step = inv_block.get("by_step", None)
    if not isinstance(inv_by_step, dict):
        raise InputValidationError(f"{path.name}: missing/invalid generator.investment.by_step mapping.")

    base = inv_by_step.get("base", None)
    if not isinstance(base, dict):
        raise InputValidationError(
            f"{path.name}: generator.investment.by_step.base missing/invalid "
            "(steady_state expects 'base')."
        )

    # Keep the keys in ONE place and decide what is required
    GEN_INVESTMENT_REQUIRED = [
        "nominal_capacity_kw",
        "lifetime_years",
        "specific_investment_cost_per_kw",
        "wacc",
    ]
    GEN_INVESTMENT_OPTIONAL = [
        "embedded_emissions_kgco2e_per_kw",
    ]
    GEN_INVESTMENT_ALL = GEN_INVESTMENT_REQUIRED + GEN_INVESTMENT_OPTIONAL

    # Validate presence of required keys
    missing = [k for k in GEN_INVESTMENT_REQUIRED if k not in base]
    if missing:
        raise InputValidationError(
            f"{path.name}: generator.investment.by_step.base missing required key(s): {missing}. "
            f"Found keys: {sorted(list(base.keys()))}"
        )

    # Coerce numeric values consistently
    inv_vals: dict[str, float] = {}
    for k in GEN_INVESTMENT_REQUIRED:
        inv_vals[k] = _as_float(
            base.get(k),
            name=f"generator/investment/by_step/base/{k}",
            default=0.0,
        )
    for k in GEN_INVESTMENT_OPTIONAL:
        # Optional: if missing or None -> default 0.0
        inv_vals[k] = _as_float(
            base.get(k, 0.0),
            name=f"generator/investment/by_step/base/{k}",
            default=0.0,
        )

    # -------------------------
    # generator.technical (scalars)
    # -------------------------
    tech_block = gen.get("technical", None)
    if not isinstance(tech_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid generator.technical mapping.")

    if "nominal_efficiency_full_load" not in tech_block:
        raise InputValidationError(f"{path.name}: missing generator technical param 'nominal_efficiency_full_load'.")

    tech_eff = _as_float(
        tech_block.get("nominal_efficiency_full_load"),
        name="generator/technical/nominal_efficiency_full_load",
        default=0.0,
    )

    max_cap_kw = _as_float_or_nan(
        tech_block.get("max_installable_capacity_kw"),
        name="generator/technical/max_installable_capacity_kw",
    )

    # -------------------------
    # generator.operation.by_scenario (scenario-dependent)
    # -------------------------
    op_block = gen.get("operation", None)
    if not isinstance(op_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid generator.operation mapping.")
    op_by_scenario = op_block.get("by_scenario", None)
    if not isinstance(op_by_scenario, dict):
        raise InputValidationError(f"{path.name}: generator.operation.by_scenario missing/invalid.")

    GEN_OPERATION_REQUIRED = ["fixed_om_share_per_year"]
    op_arr = {k: np.full((n_s,), np.nan, dtype=float) for k in GEN_OPERATION_REQUIRED}
    curve_files: dict[str, Optional[str]] = {s: None for s in scenario_labels}

    for i, s in enumerate(scenario_labels):
        if s not in op_by_scenario:
            raise InputValidationError(f"{path.name}: generator.operation.by_scenario missing scenario '{s}'.")
        sb = op_by_scenario[s]
        if not isinstance(sb, dict):
            raise InputValidationError(f"{path.name}: generator.operation.by_scenario['{s}'] must be a dict.")

        raw_curve = sb.get("efficiency_curve_csv", None)
        curve_files[s] = raw_curve.strip() if isinstance(raw_curve, str) and raw_curve.strip() else None

        for k in GEN_OPERATION_REQUIRED:
            if k not in sb:
                raise InputValidationError(
                    f"{path.name}: missing generator operation param '{k}' in scenario '{s}'."
                )
            op_arr[k][i] = _as_float(sb.get(k), name=f"generator/operation/{s}/{k}", default=0.0)

    # -------------------------
    # fuel.by_scenario (steady_state)
    # -------------------------
    fuel_by_scenario = fuel.get("by_scenario", None)
    if not isinstance(fuel_by_scenario, dict):
        raise InputValidationError(f"{path.name}: fuel.by_scenario missing/invalid.")

    FUEL_NUMERIC_REQUIRED = [
        "lhv_kwh_per_unit_fuel",
        "direct_emissions_kgco2e_per_unit_fuel",
        "fuel_cost_per_unit_fuel",
    ]
    fuel_arr = {k: np.full((n_s,), np.nan, dtype=float) for k in FUEL_NUMERIC_REQUIRED}

    for i, s in enumerate(scenario_labels):
        if s not in fuel_by_scenario:
            raise InputValidationError(f"{path.name}: fuel.by_scenario missing scenario '{s}'.")
        fb = fuel_by_scenario[s]
        if not isinstance(fb, dict):
            raise InputValidationError(f"{path.name}: fuel.by_scenario['{s}'] must be a dict.")

        missing_fuel = [k for k in FUEL_NUMERIC_REQUIRED if k not in fb]
        if missing_fuel:
            raise InputValidationError(
                f"{path.name}: fuel.by_scenario['{s}'] missing key(s): {missing_fuel}. "
                f"Found keys: {sorted(list(fb.keys()))}"
            )

        for k in FUEL_NUMERIC_REQUIRED:
            fuel_arr[k][i] = _as_float(fb.get(k), name=f"fuel/{s}/{k}", default=0.0)

    # -------------------------------------------------------------------------
    # Build generator dataset
    # -------------------------------------------------------------------------
    gen_data_vars: dict[str, xr.DataArray] = {}

    # investment scalars (dims=())
    for k in GEN_INVESTMENT_ALL:
        var_name = f"generator_{k}"
        gen_data_vars[var_name] = xr.DataArray(
            inv_vals[k],
            dims=(),
            name=var_name,
            attrs={
                "source_file": str(path),
                "scenario_dependent": False,
                "original_key": k,
                "block": "investment",
            },
        )

    # technical scalar (dims=())
    gen_data_vars["generator_nominal_efficiency_full_load"] = xr.DataArray(
        tech_eff,
        dims=(),
        name="generator_nominal_efficiency_full_load",
        attrs={
            "source_file": str(path),
            "scenario_dependent": False,
            "original_key": "nominal_efficiency_full_load",
            "block": "technical",
        },
    )

    gen_data_vars["generator_max_installable_capacity_kw"] = xr.DataArray(
        max_cap_kw,
        dims=(),
        name="generator_max_installable_capacity_kw",
        attrs={
            "source_file": str(path),
            "scenario_dependent": False,
            "original_key": "max_installable_capacity_kw",
            "block": "technical",
        },
    )

    # operation (scenario,)
    gen_data_vars["generator_fixed_om_share_per_year"] = xr.DataArray(
        op_arr["fixed_om_share_per_year"],
        coords={"scenario": scenario_coord},
        dims=("scenario",),
        name="generator_fixed_om_share_per_year",
        attrs={
            "source_file": str(path),
            "scenario_dependent": True,
            "original_key": "fixed_om_share_per_year",
            "block": "operation",
        },
    )

    gen_ds = xr.Dataset(data_vars=gen_data_vars)
    gen_ds.attrs["generator_label"] = str(gen.get("label", "Generator"))

    # -------------------------------------------------------------------------
    # Build fuel dataset (scenario,)
    # -------------------------------------------------------------------------
    fuel_ds = xr.Dataset(
        data_vars={
            f"fuel_{k}": xr.DataArray(
                fuel_arr[k],
                coords={"scenario": scenario_coord},
                dims=("scenario",),
                name=f"fuel_{k}",
                attrs={"source_file": str(path), "scenario_dependent": True, "original_key": k},
            )
            for k in FUEL_NUMERIC_REQUIRED
        }
    )
    fuel_ds.attrs["fuel_label"] = str(fuel.get("label", "Fuel"))

    # -------------------------------------------------------------------------
    # Efficiency curve (optional): scenario-dependent (scenario, curve_point)
    # -------------------------------------------------------------------------
    any_curve = any(v is not None for v in curve_files.values())
    partial_load_enabled = bool(any_curve)

    eff_curve_ds = None
    if any_curve:
        rel_list = []
        eff_list = []
        valid_scenarios = []

        for s in scenario_labels:
            fn = curve_files[s]
            if fn is None:
                continue

            curve_path = Path(fn)
            if not curve_path.is_absolute():
                curve_path = inputs_dir / curve_path

            if not curve_path.exists():
                raise InputValidationError(
                    f"{path.name}: efficiency_curve_csv for scenario '{s}' not found: {curve_path}"
                )

            cdf = pd.read_csv(curve_path)

            req_cols = ["Relative Power Output [-]", "Efficiency [-]"]
            for col in req_cols:
                if col not in cdf.columns:
                    raise InputValidationError(
                        f"{curve_path.name}: missing required column '{col}'. Required: {req_cols}"
                    )

            rel = pd.to_numeric(cdf["Relative Power Output [-]"], errors="coerce").to_numpy(dtype=float)
            eff = pd.to_numeric(cdf["Efficiency [-]"], errors="coerce").to_numpy(dtype=float)
            if np.isnan(rel).any() or np.isnan(eff).any():
                raise InputValidationError(f"{curve_path.name}: contains non-numeric values in required columns.")

            rel_list.append(rel)
            eff_list.append(eff)
            valid_scenarios.append(s)

        lengths = {len(x) for x in rel_list}
        if len(lengths) > 1:
            raise InputValidationError(
                f"{path.name}: efficiency curves have different lengths across scenarios: {sorted(lengths)}. "
                "For now, use the same number of points in each curve."
            )

        n_pts = int(next(iter(lengths))) if lengths else 0
        curve_point = xr.IndexVariable("curve_point", list(range(n_pts)))

        rel_full = np.full((n_s, n_pts), np.nan, dtype=float)
        eff_full = np.full((n_s, n_pts), np.nan, dtype=float)

        for s, rel, eff in zip(valid_scenarios, rel_list, eff_list):
            i = scenario_labels.index(s)
            rel_full[i, :] = rel
            eff_full[i, :] = eff

        eff_curve_ds = xr.Dataset(
            data_vars={
                "generator_eff_curve_rel_power": xr.DataArray(
                    rel_full,
                    coords={"scenario": scenario_coord, "curve_point": curve_point},
                    dims=("scenario", "curve_point"),
                    attrs={"units": "-", "source_file": str(path), "scenario_dependent": True},
                ),
                "generator_eff_curve_eff": xr.DataArray(
                    eff_full,
                    coords={"scenario": scenario_coord, "curve_point": curve_point},
                    dims=("scenario", "curve_point"),
                    attrs={"units": "-", "source_file": str(path), "scenario_dependent": True},
                ),
            }
        )

    meta_flags = {
        "partial_load_modelling_enabled": partial_load_enabled,
        "efficiency_curve_files": curve_files,
        "generator_label": gen_ds.attrs.get("generator_label", "Generator"),
        "fuel_label": fuel_ds.attrs.get("fuel_label", "Fuel"),
    }

    return gen_ds, fuel_ds, eff_curve_ds, meta_flags


def _load_price_csv_typical_year(
    path: Path,
    *,
    period_coord: xr.DataArray,
    scenario_coord: xr.DataArray,
    var_name: str,
    year_label: str = "typical_year",
) -> xr.DataArray:
    """
    Parse price CSV template with header=[0,1]:
      meta,low_demand,high_demand
      hour,typical_year,typical_year
      0,0.0,0.0
      ...

    Returns DataArray(period, scenario).
    """
    df = _load_csv(path, header=[0, 1])

    hour, _ = _validate_meta_hour_2level(df, path=path, period_coord=period_coord)

    scenario_labels = _scenario_labels(scenario_coord)
    missing_cols = [(s, year_label) for s in scenario_labels if (s, year_label) not in df.columns]
    if missing_cols:
        missing_names = ", ".join([f"({a},{b})" for a, b in missing_cols])
        raise InputValidationError(
            f"{path.name}: missing scenario columns: {missing_names}. "
            f"Expected scenarios: {scenario_labels} (each with '{year_label}')."
        )

    mat = df.loc[:, [(s, year_label) for s in scenario_labels]].to_numpy()
    mat = coerce_numeric_array(mat)
    if np.isnan(mat).any():
        r, c = np.argwhere(np.isnan(mat))[0]
        raise InputValidationError(
            f"{path.name}: found missing/non-numeric value at hour={hour[r]}, scenario='{scenario_labels[int(c)]}'."
        )

    da = xr.DataArray(
        mat,
        coords={"period": period_coord, "scenario": scenario_coord},
        dims=("period", "scenario"),
        name=var_name,
        attrs={"units": "currency_per_kWh", "source_file": str(path)},
    )
    return da

def _load_grid_yaml(
    path: Path,
    *,
    scenario_coord: xr.DataArray,
) -> xr.Dataset:
    """
    Load steady_state grid parameters from inputs/grid.yaml.

    Output dims:
      - scenario

    Expected YAML structure:
      grid:
        by_scenario:
          <scenario>:
            line:
              capacity_kw: ...
              transmission_efficiency: ...
            outages:
              average_outages_per_year: ...
              average_outage_duration_minutes: ...
              outage_scale_od_hours: ...   
              outage_shape_od: ...         
    """
    payload = _read_yaml(path)

    grid = payload.get("grid", None)
    if not isinstance(grid, dict):
        raise InputValidationError(f"{path.name}: missing/invalid 'grid' mapping.")

    by_scenario = grid.get("by_scenario", None)
    if not isinstance(by_scenario, dict):
        raise InputValidationError(f"{path.name}: missing/invalid grid.by_scenario mapping.")

    scenario_labels = _scenario_labels(scenario_coord)

    # keys (steady_state only)
    PARAMS = [
        ("line", "capacity_kw", "grid_line_capacity_kw"),
        ("line", "transmission_efficiency", "grid_transmission_efficiency"),
        ("line", "renewable_share", "grid_renewable_share"),
        ("line", "emissions_factor_kgco2e_per_kwh", "grid_emissions_factor_kgco2e_per_kwh"),

        ("outages", "average_outages_per_year", "grid_avg_outages_per_year"),
        ("outages", "average_outage_duration_minutes", "grid_avg_outage_duration_minutes"),

        # outage duration Weibull parameters (hours / -)
        ("outages", "outage_scale_od_hours", "grid_outage_scale_od_hours"),
        ("outages", "outage_shape_od", "grid_outage_shape_od"),
        ("outages", "outage_seed", "grid_outage_seed"),
    ]
    OPTIONAL_KEYS = {"renewable_share", "emissions_factor_kgco2e_per_kwh", "outage_seed"}

    arr = {out: np.full((len(scenario_labels),), np.nan, dtype=float) for _, _, out in PARAMS}

    for i, s_lab in enumerate(scenario_labels):
        if s_lab not in by_scenario:
            raise InputValidationError(
                f"{path.name}: grid.by_scenario missing scenario '{s_lab}'. "
                f"Expected scenarios: {scenario_labels}"
            )

        block = by_scenario[s_lab]
        if not isinstance(block, dict):
            raise InputValidationError(f"{path.name}: grid.by_scenario['{s_lab}'] must be a mapping/dict.")

        for section, key, out in PARAMS:
            sec = block.get(section, None)
            if not isinstance(sec, dict):
                raise InputValidationError(
                    f"{path.name}: grid.by_scenario['{s_lab}'] missing/invalid '{section}' mapping."
                )
            if key not in sec and key not in OPTIONAL_KEYS:
                raise InputValidationError(
                    f"{path.name}: grid.by_scenario['{s_lab}'].{section} missing key '{key}'."
                )

            # sensible defaults if user leaves them empty (but present)
            default = 0.0
            if out == "grid_transmission_efficiency":
                default = 1.0
            elif out == "grid_renewable_share":
                default = 0.0
            elif out == "grid_emissions_factor_kgco2e_per_kwh":
                default = 0.0
            elif out == "grid_outage_scale_od_hours":
                default = 36 / 60  # 0.6h default
            elif out == "grid_outage_shape_od":
                default = 0.56
            elif out == "grid_outage_seed":
                default = 0.0

            arr[out][i] = _as_float(sec.get(key), name=f"grid/{s_lab}/{section}/{key}", default=default)

    # Optional: basic validity checks
    if np.any(arr["grid_transmission_efficiency"] < 0.0) or np.any(arr["grid_transmission_efficiency"] > 1.0):
        raise InputValidationError(f"{path.name}: line.transmission_efficiency must be in [0,1].")
    if np.any(arr["grid_renewable_share"] < 0.0) or np.any(arr["grid_renewable_share"] > 1.0):
        raise InputValidationError(f"{path.name}: line.renewable_share must be in [0,1].")
    if np.any(arr["grid_emissions_factor_kgco2e_per_kwh"] < 0.0):
        raise InputValidationError(f"{path.name}: line.emissions_factor_kgco2e_per_kwh must be >= 0.")
    if np.any(arr["grid_outage_scale_od_hours"] <= 0.0):
        raise InputValidationError(f"{path.name}: outages.outage_scale_od_hours must be > 0.")
    if np.any(arr["grid_outage_shape_od"] <= 0.0):
        raise InputValidationError(f"{path.name}: outages.outage_shape_od must be > 0.")

    data_vars = {
        out: xr.DataArray(
            arr[out],
            coords={"scenario": scenario_coord},
            dims=("scenario",),
            name=out,
            attrs={"source_file": str(path), "component": "grid"},
        )
        for out in arr
    }

    ds = xr.Dataset(data_vars=data_vars)
    ds.attrs["settings"] = {"inputs_loaded": {"grid_yaml": str(path)}}
    return ds

def _write_grid_availability_csv(
    path: Path,
    *,
    availability: xr.DataArray,  # dims (period, scenario)
    year_label: str = "typical_year",
) -> None:
    """
    Save availability as CSV with 2-level header like other time series:
      (meta,hour) plus (scenario, typical_year) columns.
    """
    if set(availability.dims) != {"period", "scenario"}:
        raise InputValidationError("grid_availability must have dims ('period','scenario').")

    period = availability.coords["period"].values.astype(int)
    scenario_labels = _scenario_labels(availability.coords["scenario"])

    cols = [("meta", "hour")] + [(s, year_label) for s in scenario_labels]
    df = pd.DataFrame(columns=pd.MultiIndex.from_tuples(cols))

    df[("meta", "hour")] = period
    mat = availability.transpose("period", "scenario").values
    for j, s in enumerate(scenario_labels):
        df[(s, year_label)] = mat[:, j]

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


