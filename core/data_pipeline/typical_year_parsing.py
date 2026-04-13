# generation_planning/modeling/data.py
from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import xarray as xr

from core.data_pipeline.battery_loss_model import resolve_efficiency_curve_values
from core.data_pipeline.generator_partial_load_model import build_generator_partial_load_surrogate
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


def _select_typical_year_step_block(
    *,
    path: Path,
    by_step: dict,
    context: str,
) -> tuple[str, dict]:
    if not isinstance(by_step, dict) or len(by_step) == 0:
        raise InputValidationError(f"{path.name}: {context} missing/invalid/empty.")

    if "base" in by_step:
        block = by_step.get("base")
        if not isinstance(block, dict):
            raise InputValidationError(f"{path.name}: {context}['base'] must be a dict.")
        return "base", block

    step_items = [(str(k), v) for k, v in by_step.items()]
    if len(step_items) == 1 and isinstance(step_items[0][1], dict):
        return step_items[0][0], step_items[0][1]

    raise InputValidationError(
        f"{path.name}: {context} must contain a single step block for the steady_state typical-year formulation. "
        "Use `base`, or keep exactly one step entry."
    )


def _validate_generator_partial_load_curve(
    *,
    rel: np.ndarray,
    eff: np.ndarray,
    path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Validate the implied generator fuel curve in relative units.

    We work with:
      x = relative power output in [0, 1]
      y = relative fuel use = x / eta(x)

    Here eta(x) is the absolute generator efficiency after resolving the CSV
    column either as:
    - a normalized multiplier relative to `generator_nominal_efficiency_full_load`
      with a full-load point equal to 1.0, or
    - a legacy absolute-efficiency curve in (0, 1].

    The current steady-state formulation uses segment secants as lower bounds on
    fuel use. We therefore build a conservative convex surrogate of the implied
    fuel curve and return both the raw and surrogate fuel-use samples.
    """
    return build_generator_partial_load_surrogate(
        rel=rel,
        eff=eff,
        path=path,
        error_cls=InputValidationError,
    )


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
      - resource                 (scenario-invariant params, including fixed O&M)
      - scenario, resource       (scenario-dependent params such as production subsidy)

    Expected YAML structure (NEW):
      renewables:
        - resource: <label>
          investment:
            by_step:
              "<any>": {investment-side params}   # we take the FIRST entry (typical-year ignores cohorts)
          technical:
            {shared technical params}

    Notes:
      - Typical-year uses a single investment block. `investment.by_step.base` is preferred, but a single
        non-`base` step is also accepted.
      - Fixed O&M and renewable subsidy must be provided in `investment.by_step`.
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
        "fixed_om_share_per_year",
        "production_subsidy_per_kwh",
    ]
    OPTIONAL_INVESTMENT = {"fixed_om_share_per_year": 0.0, "production_subsidy_per_kwh": 0.0}
    PARAMS_TECHNICAL = [
        "inverter_efficiency",
        "specific_area_m2_per_kw",
        "max_installable_capacity_kw",
    ]
    n_r = len(resource_labels)
    n_s = len(scenario_labels)

    inv_arr = {k: np.full((n_r,), np.nan, dtype=float) for k in PARAMS_INVESTMENT}
    tech_arr = {k: np.full((n_r,), np.nan, dtype=float) for k in PARAMS_TECHNICAL}
    fom_arr = np.full((n_r,), np.nan, dtype=float)
    subsidy_arr = np.full((n_s, n_r), np.nan, dtype=float)

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

        first_step_key, base = _select_typical_year_step_block(
            path=path,
            by_step=inv_block.get("by_step", None),
            context=f"resource '{res_label}' investment.by_step",
        )

        for k in PARAMS_INVESTMENT:
            if k not in base:
                if k in OPTIONAL_INVESTMENT:
                    inv_arr[k][j] = float(OPTIONAL_INVESTMENT[k])
                    continue
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

        fom_arr[j] = inv_arr["fixed_om_share_per_year"][j]
        for si, _ in enumerate(scenario_labels):
            subsidy_arr[si, j] = inv_arr["production_subsidy_per_kwh"][j]

        if item.get("operation", None) is not None:
            raise InputValidationError(
                f"{path.name}: resource '{res_label}' uses the legacy `operation` block, which is no longer supported "
                "in the steady_state typical-year schema. Move fixed O&M and production subsidy into "
                "`investment.by_step.<step>`."
            )

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

    data_vars["res_fixed_om_share_per_year"] = xr.DataArray(
        fom_arr,
        coords={"resource": resource_coord},
        dims=("resource",),
        name="res_fixed_om_share_per_year",
        attrs={"source_file": str(path), "component": "renewable", "original_key": "fixed_om_share_per_year", "scenario_dependent": False},
    )
    data_vars["res_production_subsidy_per_kwh"] = xr.DataArray(
        subsidy_arr,
        coords={"scenario": scenario_coord, "resource": resource_coord},
        dims=("scenario", "resource"),
        name="res_production_subsidy_per_kwh",
        attrs={"source_file": str(path), "component": "renewable", "original_key": "production_subsidy_per_kwh", "scenario_dependent": True},
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

    Notes:
      - steady_state uses a single investment block. `investment.by_step.base` is preferred, but a single
        non-`base` step is also accepted.
      - Fixed O&M must be provided in `investment.by_step`.
      - Multi-year-only degradation keys are not part of the steady_state schema.
    """
    payload = _read_yaml(path)

    bat = payload.get("battery", None)
    if not isinstance(bat, dict):
        raise InputValidationError(f"{path.name}: missing/invalid 'battery' mapping.")

    INVESTMENT = [
        "nominal_capacity_kwh",
        "specific_investment_cost_per_kwh",
        "wacc",
        "calendar_lifetime_years",
        "embedded_emissions_kgco2e_per_kwh",
        "fixed_om_share_per_year",
    ]
    OPTIONAL_INVESTMENT = {"fixed_om_share_per_year": 0.0}
    TECHNICAL = [
        "charge_efficiency",
        "discharge_efficiency",
        "initial_soc",
        "depth_of_discharge",
        "max_discharge_time_hours",
        "max_charge_time_hours",
        "max_installable_capacity_kwh",      # allow None -> NaN
    ]
    # -----------------------------
    # investment.by_step -> take a single base block
    # -----------------------------
    inv = bat.get("investment", None)
    if not isinstance(inv, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.investment mapping.")

    step_label, inv_base = _select_typical_year_step_block(
        path=path,
        by_step=inv.get("by_step", None),
        context="battery.investment.by_step",
    )

    inv_vals = {}
    for k in INVESTMENT:
        if k not in inv_base:
            if k in OPTIONAL_INVESTMENT:
                inv_vals[k] = float(OPTIONAL_INVESTMENT[k])
                continue
            raise InputValidationError(f"{path.name}: missing investment param '{k}' in battery.investment.by_step.")
        inv_vals[k] = _as_float(inv_base.get(k), name=f"battery/investment/{step_label}/{k}", default=0.0)


    # -----------------------------
    # technical (scalars)
    # -----------------------------
    tech = bat.get("technical", None)
    if not isinstance(tech, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.technical mapping.")

    raw_curve = tech.get("efficiency_curve_csv", None)
    curve_file = raw_curve.strip() if isinstance(raw_curve, str) and raw_curve.strip() else None
    raw_calendar_curve = tech.get("calendar_fade_curve_csv", None)
    calendar_curve_file = (
        raw_calendar_curve.strip() if isinstance(raw_calendar_curve, str) and raw_calendar_curve.strip() else None
    )

    tech_vals = {}
    if "initial_soh" in tech:
        raise InputValidationError(
            f"{path.name}: `battery.technical.initial_soh` is not part of the steady_state typical-year battery schema. "
            "Remove it from Typical Year projects."
        )
    for k in TECHNICAL:
        if k not in tech:
            raise InputValidationError(f"{path.name}: missing technical param '{k}' in battery.technical.")

        if k in ("max_installable_capacity_kwh",):
            tech_vals[k] = _as_float_or_nan(tech.get(k), name=f"battery/technical/{k}")
        else:
            tech_vals[k] = _as_float(tech.get(k), name=f"battery/technical/{k}", default=0.0)

    fom_value = float(inv_vals["fixed_om_share_per_year"])
    if bat.get("operation", None) is not None:
        raise InputValidationError(
            f"{path.name}: the legacy `battery.operation` block is no longer supported in the steady_state "
            "typical-year schema. Move fixed O&M into `battery.investment.by_step.<step>`."
        )

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

    data_vars["battery_fixed_om_share_per_year"] = xr.DataArray(
        fom_value,
        dims=(),
        name="battery_fixed_om_share_per_year",
        attrs={"source_file": str(path), "component": "battery", "original_key": "fixed_om_share_per_year", "scenario_dependent": False},
    )

    ds = xr.Dataset(data_vars=data_vars)
    ds.attrs["battery_label"] = str(bat.get("label", "Battery"))
    ds.attrs["efficiency_curve_file"] = curve_file
    if "cycle_fade_coefficient_per_kwh_throughput" in tech:
        ds.attrs["battery_cycle_fade_coefficient_override"] = tech.get("cycle_fade_coefficient_per_kwh_throughput")
    ds.attrs["battery_calendar_fade_curve_csv_override"] = calendar_curve_file
    if "calendar_time_increment_mode" in tech:
        ds.attrs["battery_calendar_time_increment_mode_override"] = tech.get("calendar_time_increment_mode")
    if "calendar_time_increment_per_step" in tech:
        ds.attrs["battery_calendar_time_increment_per_step_override"] = tech.get("calendar_time_increment_per_step")
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
    # generator.investment.by_step
    # -------------------------
    inv_block = gen.get("investment", None)
    if not isinstance(inv_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid generator.investment mapping.")
    step_label, base = _select_typical_year_step_block(
        path=path,
        by_step=inv_block.get("by_step", None),
        context="generator.investment.by_step",
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
        "fixed_om_share_per_year",
    ]
    GEN_INVESTMENT_ALL = GEN_INVESTMENT_REQUIRED + GEN_INVESTMENT_OPTIONAL

    # Validate presence of required keys
    missing = [k for k in GEN_INVESTMENT_REQUIRED if k not in base]
    if missing:
        raise InputValidationError(
            f"{path.name}: generator.investment.by_step['{step_label}'] missing required key(s): {missing}. "
            f"Found keys: {sorted(list(base.keys()))}"
        )

    # Coerce numeric values consistently
    inv_vals: dict[str, float] = {}
    for k in GEN_INVESTMENT_REQUIRED:
        inv_vals[k] = _as_float(
            base.get(k),
            name=f"generator/investment/by_step/{step_label}/{k}",
            default=0.0,
        )
    for k in GEN_INVESTMENT_OPTIONAL:
        # Optional: if missing or None -> default 0.0
        inv_vals[k] = _as_float(
            base.get(k, 0.0),
            name=f"generator/investment/by_step/{step_label}/{k}",
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

    shared_curve_file = None
    raw_shared_curve = tech_block.get("efficiency_curve_csv", None)
    if isinstance(raw_shared_curve, str) and raw_shared_curve.strip():
        shared_curve_file = raw_shared_curve.strip()

    fom_value = float(inv_vals["fixed_om_share_per_year"])
    if gen.get("operation", None) is not None:
        raise InputValidationError(
            f"{path.name}: the legacy `generator.operation` block is no longer supported in the steady_state "
            "typical-year schema. Use `generator.technical.efficiency_curve_csv` for the shared curve file and "
            "keep fixed O&M in `generator.investment.by_step.<step>`."
        )

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

    # operation (scenario-independent fixed O&M)
    gen_data_vars["generator_fixed_om_share_per_year"] = xr.DataArray(
        fom_value,
        dims=(),
        name="generator_fixed_om_share_per_year",
        attrs={
            "source_file": str(path),
            "scenario_dependent": False,
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
    # Efficiency curve (optional): technology-based (curve_point,)
    # -------------------------------------------------------------------------
    partial_load_enabled = bool(shared_curve_file)

    eff_curve_ds = None
    if shared_curve_file:
        curve_path = Path(shared_curve_file)
        if not curve_path.is_absolute():
            curve_path = inputs_dir / curve_path

        if not curve_path.exists():
            raise InputValidationError(
                f"{path.name}: generator technical efficiency_curve_csv not found: {curve_path}"
            )

        cdf = pd.read_csv(curve_path)
        req_cols = ["Relative Power Output [-]", "Efficiency [-]"]
        for col in req_cols:
            if col not in cdf.columns:
                raise InputValidationError(
                    f"{curve_path.name}: missing required column '{col}'. Required: {req_cols}"
                )

        rel = pd.to_numeric(cdf["Relative Power Output [-]"], errors="coerce").to_numpy(dtype=float)
        eff_raw = pd.to_numeric(cdf["Efficiency [-]"], errors="coerce").to_numpy(dtype=float)
        if np.isnan(rel).any() or np.isnan(eff_raw).any():
            raise InputValidationError(f"{curve_path.name}: contains non-numeric values in required columns.")
        if rel.size < 2:
            raise InputValidationError(f"{curve_path.name}: curve must have at least 2 points.")
        if np.any(rel < 0.0) or np.any(rel > 1.0):
            raise InputValidationError(f"{curve_path.name}: Relative Power Output [-] must be within [0,1].")
        if np.any(np.diff(rel) <= 0.0):
            raise InputValidationError(f"{curve_path.name}: Relative Power Output [-] must be strictly increasing.")
        if not np.isclose(rel[-1], 1.0, atol=1e-9):
            raise InputValidationError(f"{curve_path.name}: the last Relative Power Output [-] point must be 1.0.")

        eff, _, _ = resolve_efficiency_curve_values(
            eff_raw,
            base_efficiency=float(tech_eff),
            path=curve_path,
            column_name="Efficiency [-]",
            allow_zero=True,
        )

        rel_full, eff_full, fuel_raw_full, fuel_surrogate_full = _validate_generator_partial_load_curve(
            rel=rel,
            eff=eff,
            path=curve_path,
        )

        n_pts = int(rel_full.size)
        curve_point = xr.IndexVariable("curve_point", list(range(n_pts)))

        eff_curve_ds = xr.Dataset(
            data_vars={
                "generator_eff_curve_rel_power": xr.DataArray(
                    rel_full,
                    coords={"curve_point": curve_point},
                    dims=("curve_point",),
                    attrs={"units": "-", "source_file": str(curve_path), "scenario_dependent": False},
                ),
                "generator_eff_curve_eff": xr.DataArray(
                    eff_full,
                    coords={"curve_point": curve_point},
                    dims=("curve_point",),
                    attrs={"units": "-", "source_file": str(curve_path), "scenario_dependent": False},
                ),
                "generator_fuel_curve_rel_fuel_use": xr.DataArray(
                    fuel_surrogate_full,
                    coords={"curve_point": curve_point},
                    dims=("curve_point",),
                    attrs={
                        "units": "-",
                        "source_file": str(curve_path),
                        "scenario_dependent": False,
                        "description": "Convex surrogate of the relative fuel-use curve phi(r)=r/eta(r) used internally by the LP partial-load formulation.",
                    },
                ),
                "generator_fuel_curve_rel_fuel_use_raw": xr.DataArray(
                    fuel_raw_full,
                    coords={"curve_point": curve_point},
                    dims=("curve_point",),
                    attrs={
                        "units": "-",
                        "source_file": str(curve_path),
                        "scenario_dependent": False,
                        "description": "Raw relative fuel-use curve phi(r)=r/eta(r) derived from the user CSV before convex LP surrogate construction.",
                    },
                ),
            }
        )

    meta_flags = {
        "partial_load_modelling_enabled": partial_load_enabled,
        "efficiency_curve_file": shared_curve_file,
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


