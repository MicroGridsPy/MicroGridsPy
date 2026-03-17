# generation_planning/modeling/data.py
from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple

import numpy as np
import pandas as pd
import xarray as xr

from core.data_pipeline.utils import (
    as_float,
    as_float_or_nan,
    as_str,
    broadcast_to_scenario,
    normalize_weights,
    read_json_or_raise,
    read_yaml_or_raise,
)
from core.data_pipeline.loader import load_project_dataset
from core.io.utils import project_paths, simulate_grid_availability_dynamic


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

def _normalize_step_key(k: object) -> str:
    """
    Normalize YAML step keys to match inv_step_coord labels.

    Accepts:
      - "1", "2"
      - 1, 2
      - "step_1", "step_2"
      - "base" (alias/default block)
      - "Step 1" (best effort)
    Returns:
      - "1" or "2" ... (string)
    """
    s = str(k).strip()
    s_low = s.lower().replace(" ", "")
    if s_low == "base":
        return "base"
    if s_low.startswith("step_"):
        return s_low.split("step_", 1)[1]
    if s_low.startswith("step"):
        # e.g. "step1"
        tail = s_low.split("step", 1)[1]
        return tail
    return s  # already like "1" (or something else)

def _remap_by_step_dict(path: Path, by_step: dict, *, expected_steps: List[str], context: str) -> Dict[str, dict]:
    """
    Remap a YAML by_step mapping that may be keyed by:
      - step labels ('1', '2', ...)
      - aliases ('step_1', 'step_2', ...)
      - 'base' (default block)

    Behavior for 'base':
      - if only one step is expected, 'base' maps to that step
      - if multiple steps are expected, 'base' is broadcast as default for any missing step

    Raises a clear error if after remapping required steps are still missing.
    """
    if not isinstance(by_step, dict):
        raise InputValidationError(f"{path.name}: {context} missing/invalid by_step mapping.")

    # Normalize keys
    remapped: Dict[str, dict] = {}
    for k, v in by_step.items():
        nk = _normalize_step_key(k)
        remapped[str(nk)] = v

    # Support human-friendly single/default block in templates:
    # by_step: {base: {...}}
    if "base" in remapped:
        base_block = remapped["base"]
        for st in expected_steps:
            remapped.setdefault(st, base_block)

    missing = [st for st in expected_steps if st not in remapped]
    if missing:
        raise InputValidationError(
            f"{path.name}: {context} missing steps {missing}. "
            f"Expected steps: {expected_steps}. "
            f"Found keys: {list(by_step.keys())}"
        )
    return remapped

# -----------------------------------------------------------------------------
# load data from CSV templates
# -----------------------------------------------------------------------------
def _load_load_demand_csv(
    path: Path,
    *,
    period_coord: xr.DataArray,
    scenario_coord: xr.DataArray,
    year_coord: xr.DataArray,
) -> xr.DataArray:
    """
    Parse multi-year (dynamic) load_demand.csv template with 2-row header:

      meta,hour
      scenario_1,year_1
      0,0.0
      1,0.0
      ...

    Actually stored as a MultiIndex header (scenario, year):
      - ("meta","hour") column must exist and match sets.period exactly (0..8759)
      - demand columns must include (scenario_label, year_label) for all combos
      - returns xr.DataArray with dims (year, period, scenario) in kWh

    Notes:
      - year labels are strings in the CSV (e.g., "typical_year", "year_1", "2025")
      - scenario labels are strings ("scenario_1", ...)
    """
    if not path.exists():
        raise InputValidationError(f"Missing required file: {path}")

    df = pd.read_csv(path, header=[0, 1])

    # ------------------------------------------------------------
    # 1) hour column validation
    # ------------------------------------------------------------
    if ("meta", "hour") not in df.columns:
        raise InputValidationError(
            f"{path.name}: missing required column ('meta','hour'). "
            "Your time series templates must include meta/hour as the first column."
        )

    hour = pd.to_numeric(df[("meta", "hour")], errors="coerce")
    if hour.isna().any():
        raise InputValidationError(f"{path.name}: meta/hour contains non-numeric values.")

    hour = hour.astype(int).to_numpy()
    expected = np.asarray(period_coord.values, dtype=int)

    if hour.shape[0] != expected.shape[0]:
        raise InputValidationError(
            f"{path.name}: expected {expected.shape[0]} hours, got {hour.shape[0]}."
        )
    if not np.array_equal(hour, expected):
        mismatch_idx = int(np.where(hour != expected)[0][0])
        raise InputValidationError(
            f"{path.name}: meta/hour does not match sets.period. "
            f"First mismatch at row {mismatch_idx}: file={hour[mismatch_idx]} vs sets={expected[mismatch_idx]}."
        )

    # ------------------------------------------------------------
    # 2) required scenario/year columns
    # ------------------------------------------------------------
    scenario_labels: List[str] = [str(s) for s in scenario_coord.values.tolist()]
    year_labels: List[str] = [str(y) for y in year_coord.values.tolist()]

    required = [(s, y) for s in scenario_labels for y in year_labels]
    missing = [c for c in required if c not in df.columns]
    if missing:
        missing_names = ", ".join([f"({a},{b})" for a, b in missing[:12]])
        more = "" if len(missing) <= 12 else f" ... (+{len(missing)-12} more)"
        raise InputValidationError(
            f"{path.name}: missing scenario/year columns: {missing_names}{more}. "
            f"Expected all combinations of scenarios={scenario_labels} and years={year_labels}."
        )

    # ------------------------------------------------------------
    # 3) extract matrix and validate numeric
    # ------------------------------------------------------------
    # shape = (period, scenario*year)
    mat = df.loc[:, required].to_numpy()
    mat = pd.DataFrame(mat).apply(pd.to_numeric, errors="coerce").to_numpy()

    if np.isnan(mat).any():
        r, c = np.argwhere(np.isnan(mat))[0]
        s, y = required[int(c)]
        raise InputValidationError(
            f"{path.name}: found missing/non-numeric load value at hour={hour[int(r)]}, "
            f"scenario='{s}', year='{y}'."
        )

    # ------------------------------------------------------------
    # 4) reshape to (period, scenario, year) then transpose to (year, period, scenario)
    # ------------------------------------------------------------
    n_p = int(period_coord.size)
    n_s = int(scenario_coord.size)
    n_y = int(year_coord.size)

    # required ordered as [(s1,y1),(s1,y2)...,(s2,y1)...]
    # reshape accordingly: period x scenario x year
    mat3 = mat.reshape(n_p, n_s, n_y)

    da = xr.DataArray(
        mat3,
        coords={"period": period_coord, "scenario": scenario_coord, "year": year_coord},
        dims=("period", "scenario", "year"),
        name="load_demand_kwh",
        attrs={"units": "kWh", "source_file": str(path)},
    ).transpose("year", "period", "scenario")

    return da

# -----------------------------------------------------------------------------
# load resource availability from CSV template
# -----------------------------------------------------------------------------
def _load_resource_availability_csv(
    path: Path,
    *,
    period_coord: xr.DataArray,
    scenario_coord: xr.DataArray,
    year_coord: xr.DataArray,
    resource_coord: xr.DataArray,
) -> xr.DataArray:
    """
    Parse multi-year (dynamic) resource_availability.csv template with 3 header rows:

      meta,scenario_1,scenario_1,...
      hour,year_1,year_1,...
      ,Solar PV,Wind Turbine,...

    Required:
      - header=[0,1,2]
      - meta/hour column must be ("meta","hour","")
      - for each (scenario, year, resource) there is a column (s,y,r)
      - hour must match sets.period exactly (0..8759)

    Returns:
      xr.DataArray renewable_availability_cf(year, period, scenario, resource)
      units: "-"
    """
    if not path.exists():
        raise InputValidationError(f"Missing required file: {path}")

    df = pd.read_csv(path, header=[0, 1, 2])

    # ------------------------------------------------------------
    # Normalize MultiIndex headers produced by pandas for blank cells
    # (e.g. "Unnamed: 0_level_2" -> "")
    # ------------------------------------------------------------
    if isinstance(df.columns, pd.MultiIndex) and df.columns.nlevels == 3:
        cols = []
        for a, b, c in df.columns:
            c = "" if (c is None or (isinstance(c, float) and pd.isna(c)) or str(c).startswith("Unnamed:")) else str(c)
            cols.append((str(a), str(b), c))
        df.columns = pd.MultiIndex.from_tuples(cols)

    # ------------------------------------------------------------
    # 1) hour column validation
    # ------------------------------------------------------------
    req_hour_col = ("meta", "hour", "")
    if req_hour_col not in df.columns:
        # Provide a helpful error (show first column as hint)
        first_col = df.columns[0] if len(df.columns) > 0 else None
        raise InputValidationError(
            f"{path.name}: missing required meta/hour column {req_hour_col}. "
            f"Expected first column to be {req_hour_col}, got {first_col!r}."
        )

    hour = pd.to_numeric(df[req_hour_col], errors="coerce")
    if hour.isna().any():
        raise InputValidationError(f"{path.name}: meta/hour contains non-numeric values.")

    hour = hour.astype(int).to_numpy()
    expected = np.asarray(period_coord.values, dtype=int)

    if hour.shape[0] != expected.shape[0]:
        raise InputValidationError(
            f"{path.name}: expected {expected.shape[0]} hours, got {hour.shape[0]}."
        )
    if not np.array_equal(hour, expected):
        mismatch_idx = int(np.where(hour != expected)[0][0])
        raise InputValidationError(
            f"{path.name}: meta/hour does not match sets.period. "
            f"First mismatch at row {mismatch_idx}: file={hour[mismatch_idx]} vs sets={expected[mismatch_idx]}."
        )

    # ------------------------------------------------------------
    # 2) required columns for all (scenario, year, resource)
    # ------------------------------------------------------------
    scenario_labels: List[str] = [str(s) for s in scenario_coord.values.tolist()]
    year_labels: List[str] = [str(y) for y in year_coord.values.tolist()]
    resource_labels: List[str] = [str(r) for r in resource_coord.values.tolist()]

    required: List[Tuple[str, str, str]] = [(s, y, r) for s in scenario_labels for y in year_labels for r in resource_labels]
    missing = [c for c in required if c not in df.columns]
    if missing:
        sample = ", ".join([f"({a},{b},{c})" for a, b, c in missing[:12]])
        more = "" if len(missing) <= 12 else f" ... (+{len(missing)-12} more)"
        raise InputValidationError(
            f"{path.name}: missing required availability columns for the current sets. "
            f"Examples: {sample}{more}"
        )

    # ------------------------------------------------------------
    # 3) extract -> reshape to (period, scenario, year, resource) then transpose
    # ------------------------------------------------------------
    # Extract in the exact order of `required` so reshaping is deterministic.
    # shape raw = (period, scenario*year*resource)
    raw = df.loc[:, required].to_numpy()

    # numeric validation (fast + informative)
    raw_num = pd.DataFrame(raw).apply(pd.to_numeric, errors="coerce").to_numpy()
    if np.isnan(raw_num).any():
        r_idx, c_idx = np.argwhere(np.isnan(raw_num))[0]
        s, y, res = required[int(c_idx)]
        raise InputValidationError(
            f"{path.name}: found missing/non-numeric availability at "
            f"hour={int(expected[int(r_idx)])}, scenario='{s}', year='{y}', resource='{res}'."
        )

    n_p = int(period_coord.size)
    n_s = int(scenario_coord.size)
    n_y = int(year_coord.size)
    n_r = int(resource_coord.size)

    # required ordered as: for s in scenarios, for y in years, for r in resources
    # -> reshape into (period, scenario, year, resource)
    arr = raw_num.reshape(n_p, n_s, n_y, n_r)

    da = xr.DataArray(
        arr,
        coords={
            "period": period_coord,
            "scenario": scenario_coord,
            "year": year_coord,
            "resource": resource_coord,
        },
        dims=("period", "scenario", "year", "resource"),
        name="renewable_availability_cf",
        attrs={"units": "-", "source_file": str(path)},
    ).transpose("year", "period", "scenario", "resource")

    # Optional sanity checks for CF bounds (keep as warning-level in UI if you prefer)
    # Here we enforce hard validation because bad CFs silently poison results.
    if (da < 0.0).any() or (da > 1.5).any():
        # allow >1 only if user uses normalization tricks; tighten to 1.0 if you want strict CF
        mn = float(da.min().item())
        mx = float(da.max().item())
        raise InputValidationError(
            f"{path.name}: renewable_availability_cf has values outside expected bounds. "
            f"min={mn:.3g}, max={mx:.3g}. Expected ~[0,1]."
        )

    return da

# -----------------------------------------------------------------------------
# Load dynamic renewable techno-economic parameters from renewables.yaml
# -----------------------------------------------------------------------------
def _load_renewables_yaml(
    path: Path,
    *,
    scenario_coord: xr.DataArray,
    resource_coord: xr.DataArray,
    inv_step_coord: xr.DataArray,
) -> xr.Dataset:
    """
    Load dynamic renewable techno-economic parameters from inputs/renewables.yaml.

    Output dims:
      - inv_step, resource                  (investment-side + any invariant-by-step params)
      - resource                            (technical params, step-invariant)
      - scenario, inv_step, resource        (scenario-dependent operation params, broadcast across steps)

    Expected YAML structure:
      renewables:
        - resource: <label>
          investment:
            by_step:
              "<inv_step_label>": {investment-side params}
          technical:
            {step-invariant technical params}
          operation:
            by_scenario:
              "<scenario>": {scenario operation params}

    Notes:
      - inv_step labels MUST match sets.inv_step, e.g. ["1","2"].
      - max_installable_capacity_kw may be None -> NaN.
      - degradation keys are optional -> default to 0.0.
    """
    if not path.exists():
        raise InputValidationError(f"Missing required file: {path}")

    payload = _read_yaml(path)

    ren_list = payload.get("renewables", None)
    if not isinstance(ren_list, list) or len(ren_list) == 0:
        raise InputValidationError(f"{path.name}: expected a non-empty list under key 'renewables'.")

    scenario_labels = [str(s) for s in scenario_coord.values.tolist()]
    resource_labels = [str(r) for r in resource_coord.values.tolist()]
    step_labels = [str(st) for st in inv_step_coord.values.tolist()]

    res_to_idx = {lab: i for i, lab in enumerate(resource_labels)}
    step_to_idx = {lab: i for i, lab in enumerate(step_labels)}

    # -----------------------------
    # Parameters (NEW)
    # -----------------------------
    # investment-side, cohort-enabled (by_step)
    PARAMS_INVESTMENT_BY_STEP = [
        "nominal_capacity_kw",
        "lifetime_years",
        "specific_investment_cost_per_kw",
        "wacc",
        "grant_share_of_capex",
        "embedded_emissions_kgco2e_per_kw",   # embodied per kW installed (investment-side)
    ]

    # technical, step-invariant (single technology physics)
    PARAMS_TECHNICAL_INVARIANT = [
        "inverter_efficiency",
        "specific_area_m2_per_kw",            # physical land-use coefficient (resource-level)
        "max_installable_capacity_kw",        # allow None -> NaN
    ]

    # operation, scenario-dependent (NOT step-dependent in YAML)
    # We broadcast across inv_step so downstream still sees (scenario, inv_step, resource)
    PARAMS_OPERATION_BY_SCENARIO = [
        "fixed_om_share_per_year",
        "production_subsidy_per_kwh",
        "capacity_degradation_rate_per_year",
    ]
    OPTIONAL_OPERATION = {
        "capacity_degradation_rate_per_year",
    }

    n_k = len(step_labels)
    n_r = len(resource_labels)
    n_s = len(scenario_labels)

    # allocate arrays
    inv_arr = {k: np.full((n_k, n_r), np.nan, dtype=float) for k in PARAMS_INVESTMENT_BY_STEP}
    tech_arr = {k: np.full((n_r,), np.nan, dtype=float) for k in PARAMS_TECHNICAL_INVARIANT}
    op_arr = {k: np.full((n_s, n_k, n_r), np.nan, dtype=float) for k in PARAMS_OPERATION_BY_SCENARIO}

    # -----------------------------
    # Load each renewable entry
    # -----------------------------
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

        # ---- investment.by_step
        inv_block = item.get("investment", None)
        if not isinstance(inv_block, dict):
            raise InputValidationError(f"{path.name}: resource '{res_label}' missing/invalid 'investment' mapping.")

        inv_by_step_raw = inv_block.get("by_step", None)
        inv_by_step = _remap_by_step_dict(
            path,
            inv_by_step_raw,
            expected_steps=step_labels,
            context=f"resource '{res_label}' investment.by_step",
        )

        legacy_specific_area_by_step: Dict[str, float] = {}
        for st in step_labels:
            blk = inv_by_step[st]
            if not isinstance(blk, dict):
                raise InputValidationError(
                    f"{path.name}: resource '{res_label}' investment.by_step['{st}'] must be a mapping/dict."
                )
            si = step_to_idx[st]
            if "specific_area_m2_per_kw" in blk:
                legacy_specific_area_by_step[st] = _as_float(
                    blk.get("specific_area_m2_per_kw"),
                    name=f"{res_label}/investment/{st}/specific_area_m2_per_kw",
                    default=0.0,
                )
            for k in PARAMS_INVESTMENT_BY_STEP:
                if k not in blk:
                    raise InputValidationError(
                        f"{path.name}: missing investment param '{k}' in resource '{res_label}', step '{st}'."
                    )
                if k == "max_installable_capacity_kw":
                    inv_arr[k][si, j] = _as_float_or_nan(blk.get(k), name=f"{res_label}/investment/{st}/{k}")
                else:
                    inv_arr[k][si, j] = _as_float(blk.get(k), name=f"{res_label}/investment/{st}/{k}", default=0.0)

        # ---- technical (step-invariant)
        tech_block = item.get("technical", None)
        if not isinstance(tech_block, dict):
            raise InputValidationError(f"{path.name}: resource '{res_label}' missing/invalid 'technical' mapping.")

        for k in PARAMS_TECHNICAL_INVARIANT:
            if k in tech_block:
                if k == "max_installable_capacity_kw":
                    tech_arr[k][j] = _as_float_or_nan(tech_block.get(k), name=f"{res_label}/technical/{k}")
                else:
                    tech_arr[k][j] = _as_float(tech_block.get(k), name=f"{res_label}/technical/{k}", default=0.0)
                continue

            # Backward compatibility:
            # allow specific_area_m2_per_kw under investment.by_step, but store as resource-level technical param.
            if k == "specific_area_m2_per_kw" and len(legacy_specific_area_by_step) > 0:
                vals = list(legacy_specific_area_by_step.values())
                v0 = vals[0]
                if not all(np.isclose(v, v0, rtol=0.0, atol=1e-12) for v in vals):
                    raise InputValidationError(
                        f"{path.name}: resource '{res_label}' has step-varying specific_area_m2_per_kw in investment.by_step. "
                        "This parameter must be step-invariant; move it to technical.specific_area_m2_per_kw "
                        "or use the same value across all steps."
                    )
                tech_arr[k][j] = v0
                continue

            raise InputValidationError(
                f"{path.name}: missing technical param '{k}' in resource '{res_label}' (technical.{k})."
            )

        # ---- operation.by_scenario (NOT step-dependent)
        op_block = item.get("operation", None)
        if not isinstance(op_block, dict):
            raise InputValidationError(f"{path.name}: resource '{res_label}' missing/invalid 'operation' mapping.")

        by_scenario = op_block.get("by_scenario", None)
        if not isinstance(by_scenario, dict):
            raise InputValidationError(
                f"{path.name}: resource '{res_label}' operation.by_scenario missing/invalid."
            )

        for s_idx, s_lab in enumerate(scenario_labels):
            if s_lab not in by_scenario:
                raise InputValidationError(
                    f"{path.name}: resource '{res_label}' missing scenario '{s_lab}' in operation.by_scenario."
                )

            sb = by_scenario[s_lab]
            if not isinstance(sb, dict):
                raise InputValidationError(
                    f"{path.name}: operation.by_scenario['{s_lab}'] for resource '{res_label}' must be a dict."
                )

            # broadcast across inv_step
            for st in step_labels:
                si = step_to_idx[st]
                for k in PARAMS_OPERATION_BY_SCENARIO:
                    if k not in sb:
                        if k in OPTIONAL_OPERATION:
                            op_arr[k][s_idx, si, j] = 0.0
                            continue
                        raise InputValidationError(
                            f"{path.name}: missing operation param '{k}' in resource '{res_label}', scenario '{s_lab}'."
                        )
                    op_arr[k][s_idx, si, j] = _as_float(sb.get(k), name=f"{res_label}/operation/{s_lab}/{k}", default=0.0)

    # -----------------------------
    # Build xr.Dataset
    # -----------------------------
    data_vars: Dict[str, xr.DataArray] = {}

    # investment by step: (inv_step, resource)
    for k in PARAMS_INVESTMENT_BY_STEP:
        var_name = f"res_{k}"
        data_vars[var_name] = xr.DataArray(
            inv_arr[k],
            coords={"inv_step": inv_step_coord, "resource": resource_coord},
            dims=("inv_step", "resource"),
            name=var_name,
            attrs={"source_file": str(path), "component": "renewable", "original_key": k, "scenario_dependent": False},
        )

    # technical invariant: (resource,)
    for k in PARAMS_TECHNICAL_INVARIANT:
        var_name = f"res_{k}"
        data_vars[var_name] = xr.DataArray(
            tech_arr[k],
            coords={"resource": resource_coord},
            dims=("resource",),
            name=var_name,
            attrs={"source_file": str(path), "component": "renewable", "original_key": k, "scenario_dependent": False},
        )

    # operation by scenario (broadcast to inv_step): (scenario, inv_step, resource)
    for k in PARAMS_OPERATION_BY_SCENARIO:
        var_name = f"res_{k}"
        data_vars[var_name] = xr.DataArray(
            op_arr[k],
            coords={"scenario": scenario_coord, "inv_step": inv_step_coord, "resource": resource_coord},
            dims=("scenario", "inv_step", "resource"),
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
    inv_step_coord: xr.DataArray,
) -> xr.Dataset:
    """
    Load dynamic battery parameters from inputs/battery.yaml (NEW SCHEMA).

    expected YAML structure:
      battery:
        label: ...
        investment:
          by_step:
            "<inv_step>":
              {investment-side params, step-dependent}
        technical:
          {technical params, step-INVARIANT}
        operation:
          by_scenario:
            "<scenario>":
              {operation params, scenario-dependent (NOT step-dependent)}

    Output dims (recommended for downstream convenience):
      - inv_step                        investment-side params
      - scenario, inv_step              technical + operation params (broadcasted)

    Notes:
      - embedded_emissions_kgco2e_per_kwh is treated as investment-side (cohort-dependent) here.
      - Degradation keys are OPTIONAL (dynamic-only); if missing default to 0.0.
    """
    payload = _read_yaml(path)

    bat = payload.get("battery", None)
    if not isinstance(bat, dict):
        raise InputValidationError(f"{path.name}: missing/invalid 'battery' mapping.")

    scenario_labels = [str(s) for s in scenario_coord.values.tolist()]
    step_labels = [str(st) for st in inv_step_coord.values.tolist()]
    n_s = len(scenario_labels)
    n_k = len(step_labels)

    step_to_idx = {lab: i for i, lab in enumerate(step_labels)}
    scen_to_idx = {lab: i for i, lab in enumerate(scenario_labels)}

    # -----------------------------
    # Parameter lists (NEW)
    # -----------------------------
    INVESTMENT_BY_STEP = [
        "nominal_capacity_kwh",
        "specific_investment_cost_per_kwh",
        "wacc",
        "calendar_lifetime_years",
        "embedded_emissions_kgco2e_per_kwh", # cohort-side
    ]

    TECHNICAL_INVARIANT = [
        "charge_efficiency",
        "discharge_efficiency",
        "initial_soc",
        "depth_of_discharge",
        "max_discharge_time_hours",
        "max_charge_time_hours",
        "max_installable_capacity_kwh",      # allow None -> NaN
    ]

    OPERATION_BY_SCENARIO = [
        "fixed_om_share_per_year",
        "capacity_degradation_rate_per_year",  # optional -> default 0.0
    ]
    OPTIONAL_OPERATION = {
        "capacity_degradation_rate_per_year",
    }

    # -----------------------------
    # 1) Investment block: battery.investment.by_step
    # -----------------------------
    inv_block = bat.get("investment", None)
    if not isinstance(inv_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.investment mapping.")

    inv_by_step_raw = inv_block.get("by_step", None)
    inv_by_step = _remap_by_step_dict(
        path,
        inv_by_step_raw,
        expected_steps=step_labels,
        context="battery.investment.by_step",
    )

    inv_arr = {k: np.full((n_k,), np.nan, dtype=float) for k in INVESTMENT_BY_STEP}

    for st in step_labels:
        blk = inv_by_step[st]
        if not isinstance(blk, dict):
            raise InputValidationError(f"{path.name}: battery.investment.by_step['{st}'] must be a dict.")
        si = step_to_idx[st]

        for k in INVESTMENT_BY_STEP:
            if k not in blk:
                raise InputValidationError(
                    f"{path.name}: missing investment param '{k}' in battery.investment.by_step['{st}']."
                )
            # Persist parsed investment values into (inv_step,) arrays.
            if k in ("max_installable_capacity_kwh",):
                inv_arr[k][si] = _as_float_or_nan(blk.get(k), name=f"battery/investment/{st}/{k}")
            else:
                inv_arr[k][si] = _as_float(blk.get(k), name=f"battery/investment/{st}/{k}", default=0.0)

    # -----------------------------
    # 2) Technical block: battery.technical (step-invariant)
    # -----------------------------
    tech = bat.get("technical", None)
    if not isinstance(tech, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.technical mapping.")

    tech_vals = {}
    for k in TECHNICAL_INVARIANT:
        if k not in tech:
            raise InputValidationError(f"{path.name}: missing technical param '{k}' in battery.technical.")
        if k in ("max_installable_capacity_kwh",):
            tech_vals[k] = _as_float_or_nan(tech.get(k), name=f"battery/technical/{k}")
        else:
            tech_vals[k] = _as_float(tech.get(k), name=f"battery/technical/{k}", default=0.0)

    # -----------------------------
    # 3) Operation block: battery.operation.by_scenario (scenario-dependent, not step-dependent)
    # -----------------------------
    op = bat.get("operation", None)
    if not isinstance(op, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.operation mapping.")

    op_by_scen = op.get("by_scenario", None)
    if not isinstance(op_by_scen, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.operation.by_scenario mapping.")

    op_arr = {k: np.full((n_s,), np.nan, dtype=float) for k in OPERATION_BY_SCENARIO}

    for s in scenario_labels:
        if s not in op_by_scen:
            raise InputValidationError(
                f"{path.name}: battery.operation.by_scenario missing scenario '{s}'. Expected: {scenario_labels}"
            )
        sb = op_by_scen[s]
        if not isinstance(sb, dict):
            raise InputValidationError(f"{path.name}: battery.operation.by_scenario['{s}'] must be a dict.")

        sj = scen_to_idx[s]
        for k in OPERATION_BY_SCENARIO:
            if k not in sb:
                if k in OPTIONAL_OPERATION:
                    op_arr[k][sj] = 0.0
                    continue
                raise InputValidationError(
                    f"{path.name}: missing operation param '{k}' in battery.operation.by_scenario['{s}']."
                )
            op_arr[k][sj] = _as_float(sb.get(k), name=f"battery/operation/{s}/{k}", default=0.0)

    # -----------------------------
    # Build xr.Dataset
    # -----------------------------
    PREFIX = "battery_"
    data_vars = {}

    # investment: (inv_step,)
    for k in INVESTMENT_BY_STEP:
        var_name = f"{PREFIX}{k}"
        data_vars[var_name] = xr.DataArray(
            inv_arr[k],
            coords={"inv_step": inv_step_coord},
            dims=("inv_step",),
            name=var_name,
            attrs={"source_file": str(path), "component": "battery", "original_key": k, "scenario_dependent": False},
        )

    # technical: broadcast to (scenario, inv_step) for downstream convenience
    for k in TECHNICAL_INVARIANT:
        var_name = f"{PREFIX}{k}"
        full = np.full((n_s, n_k), float(tech_vals[k]), dtype=float)
        data_vars[var_name] = xr.DataArray(
            full,
            coords={"scenario": scenario_coord, "inv_step": inv_step_coord},
            dims=("scenario", "inv_step"),
            name=var_name,
            attrs={"source_file": str(path), "component": "battery", "original_key": k, "scenario_dependent": False},
        )

    # operation: broadcast (scenario,) -> (scenario, inv_step)
    for k in OPERATION_BY_SCENARIO:
        var_name = f"{PREFIX}{k}"
        full = np.repeat(op_arr[k].reshape(n_s, 1), n_k, axis=1)
        data_vars[var_name] = xr.DataArray(
            full,
            coords={"scenario": scenario_coord, "inv_step": inv_step_coord},
            dims=("scenario", "inv_step"),
            name=var_name,
            attrs={"source_file": str(path), "component": "battery", "original_key": k, "scenario_dependent": True},
        )

    ds = xr.Dataset(data_vars=data_vars)
    ds.attrs["battery_label"] = str(bat.get("label", "Battery"))
    ds.attrs["settings"] = {"inputs_loaded": {"battery_yaml": str(path)}, "formulation": "dynamic"}
    return ds

def _load_generator_and_fuel_yaml(
    path: Path,
    *,
    inputs_dir: Path,
    scenario_coord: xr.DataArray,
    inv_step_coord: xr.DataArray,
    year_coord: xr.DataArray,
) -> Tuple[xr.Dataset, xr.Dataset, Optional[xr.Dataset], dict]:
    """
    Load dynamic generator + fuel blocks from inputs/generator.yaml.

    generator schema:
      generator:
        label: ...
        investment:
          by_step:
            base OR step_i:
              {step-dependent investment-side parameters}
        technical:
          {step-invariant technical parameters}
        operation:
          by_scenario:
            <scenario>:
              {scenario-dependent operation parameters (+ optional degradation in dynamic)}

    Fuel:
      fuel:
        label: ...
        by_scenario:
          <scenario>:
            lhv_kwh_per_unit_fuel
            direct_emissions_kgco2e_per_unit_fuel
            by_year_cost_per_unit_fuel  # list aligned with year labels

    Returns:
      (gen_ds, fuel_ds, eff_curve_ds_or_none, meta_flags)
    """
    payload = _read_yaml(path)

    gen = payload.get("generator", None)
    fuel = payload.get("fuel", None)
    if not isinstance(gen, dict):
        raise InputValidationError(f"{path.name}: missing/invalid 'generator' mapping.")
    if not isinstance(fuel, dict):
        raise InputValidationError(f"{path.name}: missing/invalid 'fuel' mapping.")

    scenario_labels = [str(s) for s in scenario_coord.values.tolist()]
    step_labels = [str(st) for st in inv_step_coord.values.tolist()]
    year_labels = [str(y) for y in year_coord.values.tolist()]

    n_s = len(scenario_labels)
    n_k = len(step_labels)
    n_y = len(year_labels)

    step_to_idx = {lab: i for i, lab in enumerate(step_labels)}

    # ============================================================
    # Generator parameters (NEW)
    # ============================================================
    # investment-side params (step-dependent, scenario-invariant)
    GEN_INVESTMENT_STEP = [
        "nominal_capacity_kw",
        "lifetime_years",
        "specific_investment_cost_per_kw",
        "wacc",
        "embedded_emissions_kgco2e_per_kw",   # investment-side attribute
    ]
    OPTIONAL_GEN_INVESTMENT_STEP = {"max_installable_capacity_kw"}

    # technical params (step-invariant scalars)
    GEN_TECHNICAL = [
        "nominal_efficiency_full_load",
        "max_installable_capacity_kw",        # optional
    ]

    # operation params (scenario-dependent, NOT step-dependent)
    GEN_OPERATION_SCENARIO = [
        "fixed_om_share_per_year",
        "efficiency_curve_csv",              # optional, scenario-level
        # dynamic-only optional degradation
        "capacity_degradation_rate_per_year",
    ]
    OPTIONAL_GEN_OPERATION_SCENARIO = {
        "efficiency_curve_csv",
        "capacity_degradation_rate_per_year",
    }

    # ---- investment.by_step
    inv_block = gen.get("investment", None)
    if not isinstance(inv_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid generator.investment mapping.")
    inv_by_step_raw = inv_block.get("by_step", None)
    inv_by_step = _remap_by_step_dict(
        path,
        inv_by_step_raw,
        expected_steps=step_labels,
        context="generator.investment.by_step",
    )

    inv_arr = {k: np.full((n_k,), np.nan, dtype=float) for k in GEN_INVESTMENT_STEP}

    for st in step_labels:
        blk = inv_by_step.get(st, None)
        if not isinstance(blk, dict):
            raise InputValidationError(f"{path.name}: generator.investment.by_step['{st}'] must be a dict.")

        si = step_to_idx[st]
        for k in GEN_INVESTMENT_STEP:
            if k not in blk:
                if k in OPTIONAL_GEN_INVESTMENT_STEP:
                    inv_arr[k][si] = float("nan")
                    continue
                raise InputValidationError(
                    f"{path.name}: missing generator investment param '{k}' in investment.by_step['{st}']."
                )

            if k in OPTIONAL_GEN_INVESTMENT_STEP:
                inv_arr[k][si] = _as_float_or_nan(blk.get(k), name=f"generator/investment/{st}/{k}")
            else:
                inv_arr[k][si] = _as_float(blk.get(k), name=f"generator/investment/{st}/{k}", default=0.0)

    # ---- technical (scalars)
    tech_block = gen.get("technical", None)
    if not isinstance(tech_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid generator.technical mapping.")

    tech_vals: dict[str, float] = {}
    for k in GEN_TECHNICAL:
        if k not in tech_block:
            raise InputValidationError(f"{path.name}: missing generator technical param '{k}' in generator.technical.")
        if k == "max_installable_capacity_kw":
            tech_vals[k] = _as_float_or_nan(tech_block.get(k), name=f"generator/technical/{k}")
        else:
            tech_vals[k] = _as_float(tech_block.get(k), name=f"generator/technical/{k}", default=0.0)

    # ---- operation.by_scenario (scenario-dependent, no steps)
    op_block = gen.get("operation", None)
    if not isinstance(op_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid generator.operation mapping.")
    op_by_scenario = op_block.get("by_scenario", None)
    if not isinstance(op_by_scenario, dict):
        raise InputValidationError(f"{path.name}: generator.operation.by_scenario missing/invalid.")

    op_arr = {k: np.full((n_s,), np.nan, dtype=float) for k in GEN_OPERATION_SCENARIO if k != "efficiency_curve_csv"}
    curve_files: dict[str, Optional[str]] = {s: None for s in scenario_labels}

    for s_idx, s in enumerate(scenario_labels):
        if s not in op_by_scenario:
            raise InputValidationError(f"{path.name}: generator.operation.by_scenario missing scenario '{s}'.")
        sb = op_by_scenario[s]
        if not isinstance(sb, dict):
            raise InputValidationError(f"{path.name}: generator.operation.by_scenario['{s}'] must be a dict.")

        # curve pointer (scenario-dependent)
        raw_curve = sb.get("efficiency_curve_csv", None)
        curve_files[s] = raw_curve.strip() if isinstance(raw_curve, str) and raw_curve.strip() else None

        # fixed om is required
        if "fixed_om_share_per_year" not in sb:
            raise InputValidationError(
                f"{path.name}: missing generator operation param 'fixed_om_share_per_year' in scenario '{s}'."
            )
        op_arr["fixed_om_share_per_year"][s_idx] = _as_float(
            sb.get("fixed_om_share_per_year"), name=f"generator/operation/{s}/fixed_om_share_per_year", default=0.0
        )

        # degradation optional (dynamic)
        for k in ("capacity_degradation_rate_per_year"):
            if k in op_arr:
                if k not in sb:
                    op_arr[k][s_idx] = 0.0
                else:
                    op_arr[k][s_idx] = _as_float(sb.get(k), name=f"generator/operation/{s}/{k}", default=0.0)

    # ------------------------------------------------------------
    # Build generator dataset
    # ------------------------------------------------------------
    gen_data_vars: dict[str, xr.DataArray] = {}

    # investment by step: (inv_step,)
    for k in GEN_INVESTMENT_STEP:
        var_name = f"generator_{k}"
        gen_data_vars[var_name] = xr.DataArray(
            inv_arr[k],
            coords={"inv_step": inv_step_coord},
            dims=("inv_step",),
            name=var_name,
            attrs={"source_file": str(path), "scenario_dependent": False, "original_key": k, "block": "investment"},
        )

    # technical scalars: dims=()
    for k in GEN_TECHNICAL:
        var_name = f"generator_{k}"
        gen_data_vars[var_name] = xr.DataArray(
            tech_vals[k],
            dims=(),
            name=var_name,
            attrs={"source_file": str(path), "scenario_dependent": False, "original_key": k, "block": "technical"},
        )

    # operation: (scenario,)
    # fixed_om always exists; degradation arrays exist only if you kept them in GEN_OPERATION_SCENARIO
    gen_data_vars["generator_fixed_om_share_per_year"] = xr.DataArray(
        op_arr["fixed_om_share_per_year"],
        coords={"scenario": scenario_coord},
        dims=("scenario",),
        name="generator_fixed_om_share_per_year",
        attrs={"source_file": str(path), "scenario_dependent": True, "original_key": "fixed_om_share_per_year", "block": "operation"},
    )
    for k in ("capacity_degradation_rate_per_year"):
        if k in op_arr:
            var_name = f"generator_{k}"
            gen_data_vars[var_name] = xr.DataArray(
                op_arr[k],
                coords={"scenario": scenario_coord},
                dims=("scenario",),
                name=var_name,
                attrs={"source_file": str(path), "scenario_dependent": True, "original_key": k, "block": "operation"},
            )

    gen_ds = xr.Dataset(data_vars=gen_data_vars)
    gen_ds.attrs["generator_label"] = str(gen.get("label", "Generator"))

    # ============================================================
    # Fuel parameters (dynamic)
    # ============================================================
    fuel_by_scenario = fuel.get("by_scenario", None)
    if not isinstance(fuel_by_scenario, dict):
        raise InputValidationError(f"{path.name}: fuel.by_scenario missing/invalid.")

    FUEL_SCALAR = [
        "lhv_kwh_per_unit_fuel",
        "direct_emissions_kgco2e_per_unit_fuel",
    ]
    FUEL_YEARLY = "by_year_cost_per_unit_fuel"

    fuel_scalar_arr = {k: np.full((n_s,), np.nan, dtype=float) for k in FUEL_SCALAR}
    fuel_cost_year_arr = np.full((n_s, n_y), np.nan, dtype=float)

    for s_idx, s in enumerate(scenario_labels):
        if s not in fuel_by_scenario:
            raise InputValidationError(f"{path.name}: fuel.by_scenario missing scenario '{s}'.")
        fb = fuel_by_scenario[s]
        if not isinstance(fb, dict):
            raise InputValidationError(f"{path.name}: fuel.by_scenario['{s}'] must be a dict.")

        for k in FUEL_SCALAR:
            if k not in fb:
                raise InputValidationError(f"{path.name}: fuel.by_scenario['{s}'] missing '{k}'.")
            fuel_scalar_arr[k][s_idx] = _as_float(fb.get(k), name=f"fuel/{s}/{k}", default=0.0)

        if FUEL_YEARLY not in fb:
            raise InputValidationError(
                f"{path.name}: fuel.by_scenario['{s}'] missing '{FUEL_YEARLY}' (dynamic expects yearly list)."
            )
        series = fb.get(FUEL_YEARLY)
        if not isinstance(series, list):
            raise InputValidationError(
                f"{path.name}: fuel.by_scenario['{s}'].{FUEL_YEARLY} must be a list aligned with year labels."
            )
        if len(series) != n_y:
            raise InputValidationError(
                f"{path.name}: fuel.by_scenario['{s}'].{FUEL_YEARLY} length mismatch: "
                f"expected {n_y} (years={year_labels}), got {len(series)}."
            )

        vals = []
        for i, v in enumerate(series):
            vals.append(_as_float(v, name=f"fuel/{s}/{FUEL_YEARLY}[{i}]", default=0.0))
        fuel_cost_year_arr[s_idx, :] = np.asarray(vals, dtype=float)

    fuel_ds = xr.Dataset(
        data_vars={
            "fuel_lhv_kwh_per_unit_fuel": xr.DataArray(
                fuel_scalar_arr["lhv_kwh_per_unit_fuel"],
                coords={"scenario": scenario_coord},
                dims=("scenario",),
                attrs={"source_file": str(path), "scenario_dependent": True, "original_key": "lhv_kwh_per_unit_fuel"},
            ),
            "fuel_direct_emissions_kgco2e_per_unit_fuel": xr.DataArray(
                fuel_scalar_arr["direct_emissions_kgco2e_per_unit_fuel"],
                coords={"scenario": scenario_coord},
                dims=("scenario",),
                attrs={"source_file": str(path), "scenario_dependent": True, "original_key": "direct_emissions_kgco2e_per_unit_fuel"},
            ),
            "fuel_cost_per_unit_fuel": xr.DataArray(
                fuel_cost_year_arr,
                coords={"scenario": scenario_coord, "year": year_coord},
                dims=("scenario", "year"),
                attrs={"source_file": str(path), "scenario_dependent": True, "original_key": "by_year_cost_per_unit_fuel"},
            ),
        }
    )
    fuel_ds.attrs["fuel_label"] = str(fuel.get("label", "Fuel"))

    # ============================================================
    # Efficiency curve (optional) (scenario, curve_point) -- same behavior
    # ============================================================
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

            if rel.size < 2:
                raise InputValidationError(f"{curve_path.name}: curve must have at least 2 points.")
            if np.any(rel < 0.0) or np.any(rel > 1.0):
                raise InputValidationError(f"{curve_path.name}: Relative Power Output [-] must be within [0,1].")

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
        "efficiency_curve_files": curve_files,  # scenario -> filename or None
        "generator_label": gen_ds.attrs.get("generator_label", "Generator"),
        "fuel_label": fuel_ds.attrs.get("fuel_label", "Fuel"),
        "fuel_cost_is_yearly": True,
        "fuel_cost_dims": ("scenario", "year"),
    }

    return gen_ds, fuel_ds, eff_curve_ds, meta_flags


def _load_price_csv_dynamic(
    path: Path,
    *,
    period_coord: xr.DataArray,
    scenario_coord: xr.DataArray,
    year_coord: xr.DataArray,
    var_name: str,
    units: str = "currency_per_kWh",
) -> xr.DataArray:
    """
    Parse dynamic price CSV template with header=[0,1] (scenario, year):

      meta,scenario_1,scenario_1,scenario_2,scenario_2
      hour,year_1,year_2,year_1,year_2
      0,0.0,0.0,0.0,0.0
      1, ...
      ...

    Requirements:
      - CSV uses header=[0,1]
      - hour column exists as ('meta','hour')
      - scenario columns cover all combinations (scenario_label, year_label)
      - hour must match sets.period exactly (typically 0..8759)
    Returns:
      xr.DataArray(period, scenario, year)
    """
    if not path.exists():
        raise InputValidationError(f"Missing required file: {path}")

    df = pd.read_csv(path, header=[0, 1])

    # --------------------------------------------------
    # 1) hour column validation
    # --------------------------------------------------
    if ("meta", "hour") not in df.columns:
        raise InputValidationError(
            f"{path.name}: missing required column ('meta','hour'). "
            "Your time series templates must include meta/hour as the first column."
        )

    hour = pd.to_numeric(df[("meta", "hour")], errors="coerce")
    if hour.isna().any():
        raise InputValidationError(f"{path.name}: meta/hour contains non-numeric values.")
    hour = hour.astype(int).to_numpy()

    expected = np.asarray(period_coord.values, dtype=int)
    if hour.shape[0] != expected.shape[0]:
        raise InputValidationError(
            f"{path.name}: expected {expected.shape[0]} hours, got {hour.shape[0]}."
        )
    if not np.array_equal(hour, expected):
        mismatch_idx = int(np.where(hour != expected)[0][0])
        raise InputValidationError(
            f"{path.name}: meta/hour does not match sets.period. "
            f"First mismatch at row {mismatch_idx}: file={hour[mismatch_idx]} vs sets={expected[mismatch_idx]}."
        )

    # --------------------------------------------------
    # 2) required scenario × year columns exist
    # --------------------------------------------------
    scenario_labels = [str(s) for s in scenario_coord.values.tolist()]
    year_labels = [str(y) for y in year_coord.values.tolist()]

    missing = []
    for s in scenario_labels:
        for y in year_labels:
            if (s, y) not in df.columns:
                missing.append((s, y))

    if missing:
        sample = ", ".join([f"({a},{b})" for a, b in missing[:10]])
        raise InputValidationError(
            f"{path.name}: missing required price columns for current sets. "
            f"Examples: {sample}"
            + (f" ... (+{len(missing)-10} more)" if len(missing) > 10 else "")
        )

    # --------------------------------------------------
    # 3) extract into (period, scenario, year)
    # --------------------------------------------------
    # We want a stable ordering: scenario major, year minor, to reshape reliably
    cols = [(s, y) for s in scenario_labels for y in year_labels]
    mat = df.loc[:, cols].to_numpy()  # (period, scenario*year)

    # numeric validation
    mat = pd.DataFrame(mat).apply(pd.to_numeric, errors="coerce").to_numpy()
    if np.isnan(mat).any():
        r, c = np.argwhere(np.isnan(mat))[0]
        s_idx = int(c // len(year_labels))
        y_idx = int(c % len(year_labels))
        raise InputValidationError(
            f"{path.name}: found missing/non-numeric value at "
            f"hour={hour[r]}, scenario='{scenario_labels[s_idx]}', year='{year_labels[y_idx]}'."
        )

    # reshape -> (period, scenario, year)
    arr = mat.reshape((len(expected), len(scenario_labels), len(year_labels)))

    da = xr.DataArray(
        arr,
        coords={"period": period_coord, "scenario": scenario_coord, "year": year_coord},
        dims=("period", "scenario", "year"),
        name=var_name,
        attrs={"units": units, "source_file": str(path)},
    )
    return da

def _load_grid_yaml_dynamic(
    path: Path,
    *,
    scenario_coord: xr.DataArray,
    year_coord: xr.DataArray,
) -> xr.Dataset:
    """
    Load dynamic grid parameters from inputs/grid.yaml.

    Output dims:
      - scenario

    Expected YAML structure (dynamic):
      grid:
        by_scenario:
          <scenario>:
            line:
              capacity_kw: ...
              transmission_efficiency: ...
            first_year_connection: <int year label or null>
            outages:
              average_outages_per_year: ...
              average_outage_duration_minutes: ...
              outage_scale_od_hours: ...
              outage_shape_od: ...

    Notes:
      - first_year_connection is scenario-dependent.
      - If first_year_connection is null:
          recommended interpretation is "grid available from the start of horizon"
          (i.e., connected for all years). Your downstream model should define the convention.
    """
    payload = _read_yaml(path)

    grid = payload.get("grid", None)
    if not isinstance(grid, dict):
        raise InputValidationError(f"{path.name}: missing/invalid 'grid' mapping.")

    by_scenario = grid.get("by_scenario", None)
    if not isinstance(by_scenario, dict):
        raise InputValidationError(f"{path.name}: missing/invalid grid.by_scenario mapping.")

    scenario_labels = [str(s) for s in scenario_coord.values.tolist()]
    year_labels = [str(y) for y in year_coord.values.tolist()]

    # (section, key, output_name)
    PARAMS = [
        ("line", "capacity_kw", "grid_line_capacity_kw"),
        ("line", "transmission_efficiency", "grid_transmission_efficiency"),
        ("line", "renewable_share", "grid_renewable_share"),

        ("outages", "average_outages_per_year", "grid_avg_outages_per_year"),
        ("outages", "average_outage_duration_minutes", "grid_avg_outage_duration_minutes"),
        ("outages", "outage_scale_od_hours", "grid_outage_scale_od_hours"),
        ("outages", "outage_shape_od", "grid_outage_shape_od"),
        ("outages", "outage_seed", "grid_outage_seed"),
    ]

    arr = {out: np.full((len(scenario_labels),), np.nan, dtype=float) for _, _, out in PARAMS}
    first_year = np.full((len(scenario_labels),), np.nan, dtype=float)  # store as float; keep NaN for null

    for i, s_lab in enumerate(scenario_labels):
        if s_lab not in by_scenario:
            raise InputValidationError(
                f"{path.name}: grid.by_scenario missing scenario '{s_lab}'. "
                f"Expected scenarios: {scenario_labels}"
            )

        block = by_scenario[s_lab]
        if not isinstance(block, dict):
            raise InputValidationError(f"{path.name}: grid.by_scenario['{s_lab}'] must be a mapping/dict.")

        # ---- first_year_connection (dynamic-only) ----
        # Allow missing -> treat as NaN (but your template includes it; we still guard)
        raw_fy = block.get("first_year_connection", None)
        if raw_fy is None or (isinstance(raw_fy, str) and raw_fy.strip() == ""):
            first_year[i] = float("nan")
        else:
            # keep strict: must be int-like
            try:
                fy_int = int(raw_fy)
            except Exception:
                raise InputValidationError(
                    f"{path.name}: grid.by_scenario['{s_lab}'].first_year_connection must be an int year label or null."
                )
            first_year[i] = float(fy_int)

            # Optional strict consistency check with provided year labels (if those are int-like)
            # If year labels are not int-like (e.g., 'year_1'), we skip this check.
            try:
                year_ints = [int(str(y)) for y in year_labels]
                if fy_int not in year_ints:
                    raise InputValidationError(
                        f"{path.name}: first_year_connection={fy_int} for scenario '{s_lab}' "
                        f"not found in sets.year labels={year_labels}."
                    )
            except ValueError:
                # year labels are not integer-coded; skip membership check
                pass

        # ---- line + outages ----
        for section, key, out in PARAMS:
            sec = block.get(section, None)
            if not isinstance(sec, dict):
                raise InputValidationError(
                    f"{path.name}: grid.by_scenario['{s_lab}'] missing/invalid '{section}' mapping."
                )
            if key not in sec:
                raise InputValidationError(
                    f"{path.name}: grid.by_scenario['{s_lab}'].{section} missing key '{key}'."
                )

            # sensible defaults if user leaves them empty (but present)
            default = 0.0
            if out == "grid_transmission_efficiency":
                default = 1.0
            elif out == "grid_renewable_share":
                default = 0.0
            elif out == "grid_outage_scale_od_hours":
                default = 36 / 60  # 0.6h default
            elif out == "grid_outage_shape_od":
                default = 0.56
            elif out == "grid_outage_seed":
                default = 0.0

            arr[out][i] = _as_float(sec.get(key), name=f"grid/{s_lab}/{section}/{key}", default=default)

    # ---- validity checks ----
    if np.any(arr["grid_transmission_efficiency"] < 0.0) or np.any(arr["grid_transmission_efficiency"] > 1.0):
        raise InputValidationError(f"{path.name}: line.transmission_efficiency must be in [0,1].")
    if np.any(arr["grid_renewable_share"] < 0.0) or np.any(arr["grid_renewable_share"] > 1.0):
        raise InputValidationError(f"{path.name}: line.renewable_share must be in [0,1].")
    if np.any(arr["grid_outage_scale_od_hours"] <= 0.0):
        raise InputValidationError(f"{path.name}: outages.outage_scale_od_hours must be > 0.")
    if np.any(arr["grid_outage_shape_od"] <= 0.0):
        raise InputValidationError(f"{path.name}: outages.outage_shape_od must be > 0.")
    if np.any(arr["grid_line_capacity_kw"] < 0.0):
        raise InputValidationError(f"{path.name}: line.capacity_kw must be >= 0.")

    # ---- build dataset ----
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

    data_vars["grid_first_year_connection"] = xr.DataArray(
        first_year,
        coords={"scenario": scenario_coord},
        dims=("scenario",),
        name="grid_first_year_connection",
        attrs={
            "source_file": str(path),
            "component": "grid",
            "dynamic_only": True,
            "notes": "NaN means null/unspecified; downstream should apply the chosen convention.",
        },
    )

    ds = xr.Dataset(data_vars=data_vars)
    ds.attrs["settings"] = {"inputs_loaded": {"grid_yaml": str(path)}, "formulation": "dynamic"}
    return ds


def _write_grid_availability_csv_dynamic(path: Path, *, availability: xr.DataArray) -> None:
    if set(availability.dims) != {"period", "scenario", "year"}:
        raise InputValidationError("grid_availability must have dims ('period','scenario','year').")

    period = availability.coords["period"].values.astype(int)
    scenario_labels = [str(v) for v in availability.coords["scenario"].values.tolist()]
    year_values = availability.coords["year"].values.tolist()
    year_labels = [str(v) for v in year_values]

    cols = [("meta", "hour")] + [(scenario, year) for scenario in scenario_labels for year in year_labels]
    df = pd.DataFrame(columns=pd.MultiIndex.from_tuples(cols))
    df[("meta", "hour")] = period

    for scenario in scenario_labels:
        for year_value, year_label in zip(year_values, year_labels):
            df[(scenario, year_label)] = availability.sel(scenario=scenario, year=year_value).values.astype(float)

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _first_connection_year_to_ordinal(first_year_value: Any, year_values: list[Any]) -> int | None:
    try:
        if first_year_value is None or np.isnan(float(first_year_value)):
            return None
    except Exception:
        pass

    if not year_values:
        return None

    year_labels = [str(v) for v in year_values]
    fy_str = str(first_year_value)
    if fy_str in year_labels:
        return year_labels.index(fy_str) + 1

    try:
        fy_int = int(first_year_value)
        year_ints = [int(v) for v in year_values]
        if fy_int <= year_ints[0]:
            return 1
        for idx, year_int in enumerate(year_ints, start=1):
            if fy_int == year_int:
                return idx
        if fy_int > year_ints[-1]:
            return int(len(year_values) + 1)
    except Exception:
        pass

    return None


def regenerate_grid_availability_dynamic(*, project_name: str, sets: xr.Dataset) -> xr.DataArray:
    paths = project_paths(project_name)
    scenario_coord = sets.coords["scenario"]
    year_coord = sets.coords["year"]
    period_coord = sets.coords["period"]

    grid_ds = _load_grid_yaml_dynamic(
        paths.inputs_dir / "grid.yaml",
        scenario_coord=scenario_coord,
        year_coord=year_coord,
    )

    n_p = int(period_coord.size)
    n_s = int(scenario_coord.size)
    n_y = int(year_coord.size)
    avail = np.zeros((n_p, n_s, n_y), dtype=float)

    scenario_labels = [str(s) for s in scenario_coord.values.tolist()]
    year_values = year_coord.values.tolist()
    year_labels = [str(y) for y in year_values]

    for j, s_lab in enumerate(scenario_labels):
        ao = float(grid_ds["grid_avg_outages_per_year"].sel(scenario=s_lab).values)
        ad = float(grid_ds["grid_avg_outage_duration_minutes"].sel(scenario=s_lab).values)
        scale_od = float(grid_ds["grid_outage_scale_od_hours"].sel(scenario=s_lab).values)
        shape_od = float(grid_ds["grid_outage_shape_od"].sel(scenario=s_lab).values)
        seed = int(float(grid_ds["grid_outage_seed"].sel(scenario=s_lab).values))
        fy = grid_ds["grid_first_year_connection"].sel(scenario=s_lab).values
        connection_ordinal = _first_connection_year_to_ordinal(fy, year_values)

        avail_ty = simulate_grid_availability_dynamic(
            ao,
            ad,
            years=int(year_coord.size),
            periods_per_year=int(period_coord.size),
            first_year_connection=connection_ordinal,
            scale_od=scale_od,
            shape_od=shape_od,
            rng=np.random.default_rng(seed),
        )

        for k, y_lab in enumerate(year_labels):
            connected = True
            if connection_ordinal is not None:
                connected = (k + 1) >= int(connection_ordinal)
            avail[:, j, k] = avail_ty[:, k] if connected else 0.0

    grid_availability = xr.DataArray(
        avail,
        coords={"period": period_coord, "scenario": scenario_coord, "year": year_coord},
        dims=("period", "scenario", "year"),
        name="grid_availability",
        attrs={"units": "binary", "component": "grid", "dynamic_only": True},
    )

    _write_grid_availability_csv_dynamic(paths.inputs_dir / "grid_availability.csv", availability=grid_availability)
    return grid_availability

# -----------------------------------------------------------------------------
# main entrypoint (DYNAMIC)
# -----------------------------------------------------------------------------
def _initialize_data_legacy(project_name: str, sets: xr.Dataset) -> xr.Dataset:
    """
    Legacy dynamic loader implementation kept for shared pipeline delegation.
    """
    if not isinstance(sets, xr.Dataset):
        raise InputValidationError("initialize_data_dynamic expects `sets` as an xarray.Dataset.")
    for c in ("scenario", "period", "year", "inv_step", "resource"):
        if c not in sets.coords:
            raise InputValidationError(f"Sets missing required coord: '{c}'")

    scenario_coord = sets.coords["scenario"]
    period_coord = sets.coords["period"]
    year_coord = sets.coords["year"]
    inv_step_coord = sets.coords["inv_step"]
    resource_coord = sets.coords["resource"]

    n_scen = int(scenario_coord.size)

    paths = project_paths(project_name)
    formulation = _read_json(paths.formulation_json)

    formulation_mode = _as_str(formulation.get("core_formulation", "steady_state"), name="core_formulation")
    if formulation_mode != "dynamic":
        raise InputValidationError("This data initializer is for dynamic only.")

    uc_enabled = bool(formulation.get("unit_commitment", False))
    capexp_enabled = bool(formulation.get("capacity_expansion", False))

    ms = formulation.get("multi_scenario", {}) or {}
    ms_enabled = bool(ms.get("enabled", False))

    if ms_enabled:
        raw_w = ms.get("scenario_weights") or []
        weights = _normalize_weights(raw_w, n_scen)
    else:
        weights = [1.0] * n_scen

    scenario_weights = xr.DataArray(
        weights,
        coords={"scenario": scenario_coord},
        dims=("scenario",),
        name="scenario_weight",
    )

    optc = formulation.get("optimization_constraints", {}) or {}
    enforcement = _as_str(optc.get("enforcement", None), name="optimization_constraints.enforcement")
    if not enforcement:
        enforcement = "expected" if ms_enabled else "scenario_wise"
    if enforcement not in ("expected", "scenario_wise"):
        raise InputValidationError(
            f"Invalid optimization_constraints.enforcement: {enforcement!r}. "
            "Allowed: 'expected' | 'scenario_wise'."
        )

    min_res_pen = _as_float(optc.get("min_renewable_penetration", 0.0), name="min_renewable_penetration", default=0.0)
    max_ll_frac = _as_float(optc.get("max_lost_load_fraction", 0.0), name="max_lost_load_fraction", default=0.0)
    lolc = _as_float(optc.get("lost_load_cost_per_kwh", 0.0), name="lost_load_cost_per_kwh", default=0.0)
    land_m2 = _as_float(optc.get("land_availability_m2", 0.0), name="land_availability_m2", default=0.0)
    em_cost = _as_float(optc.get("emission_cost_per_kgco2e", 0.0), name="emission_cost_per_kgco2e", default=0.0)

    da_min_res_pen = xr.DataArray(min_res_pen, name="min_renewable_penetration")
    da_max_ll_frac = xr.DataArray(max_ll_frac, name="max_lost_load_fraction")
    da_land = xr.DataArray(land_m2, name="land_availability_m2")
    da_lolc = xr.DataArray(lolc, name="lost_load_cost_per_kwh")
    da_em_cost = xr.DataArray(em_cost, name="emission_cost_per_kgco2e")
    if enforcement == "scenario_wise":
        da_lolc = _broadcast_to_scenario(da_lolc, scenario_coord)
        da_em_cost = _broadcast_to_scenario(da_em_cost, scenario_coord)

    load_path = paths.inputs_dir / "load_demand.csv"
    load_demand = _load_load_demand_csv(
        load_path,
        period_coord=period_coord,
        scenario_coord=scenario_coord,
        year_coord=year_coord,
    )
    resource_path = paths.inputs_dir / "resource_availability.csv"
    resource_avail = _load_resource_availability_csv(
        resource_path,
        period_coord=period_coord,
        scenario_coord=scenario_coord,
        year_coord=year_coord,
        resource_coord=resource_coord,
    )

    data = xr.Dataset(
        data_vars={
            "scenario_weight": scenario_weights,
            "min_renewable_penetration": da_min_res_pen,
            "max_lost_load_fraction": da_max_ll_frac,
            "lost_load_cost_per_kwh": da_lolc,
            "land_availability_m2": da_land,
            "emission_cost_per_kgco2e": da_em_cost,
            "load_demand": load_demand,
            "resource_availability": resource_avail,
        }
    )

    renewables_path = paths.inputs_dir / "renewables.yaml"
    ren_params_ds = _load_renewables_yaml(
        renewables_path,
        scenario_coord=scenario_coord,
        resource_coord=resource_coord,
        inv_step_coord=inv_step_coord,
    )
    battery_path = paths.inputs_dir / "battery.yaml"
    bat_params_ds = _load_battery_yaml(
        battery_path,
        scenario_coord=scenario_coord,
        inv_step_coord=inv_step_coord,
    )
    genfuel_path = paths.inputs_dir / "generator.yaml"
    gen_ds, fuel_ds, curve_ds, genfuel_meta = _load_generator_and_fuel_yaml(
        genfuel_path,
        inputs_dir=paths.inputs_dir,
        scenario_coord=scenario_coord,
        year_coord=year_coord,
        inv_step_coord=inv_step_coord,
    )

    data = xr.merge([data, ren_params_ds, bat_params_ds, gen_ds, fuel_ds], compat="override")
    if curve_ds is not None:
        data = xr.merge([data, curve_ds], compat="override")

    on_grid = bool(formulation.get("on_grid", False))
    allow_export = bool(formulation.get("grid_allow_export", False))

    if on_grid:
        grid_yaml_path = paths.inputs_dir / "grid.yaml"
        grid_ds = _load_grid_yaml_dynamic(
            grid_yaml_path,
            scenario_coord=scenario_coord,
            year_coord=year_coord,
        )

        imp_path = paths.inputs_dir / "grid_import_price.csv"
        grid_import_price = _load_price_csv_dynamic(
            imp_path,
            period_coord=period_coord,
            scenario_coord=scenario_coord,
            year_coord=year_coord,
            var_name="grid_import_price",
        )

        if allow_export:
            exp_path = paths.inputs_dir / "grid_export_price.csv"
            grid_export_price = _load_price_csv_dynamic(
                exp_path,
                period_coord=period_coord,
                scenario_coord=scenario_coord,
                year_coord=year_coord,
                var_name="grid_export_price",
            )
        else:
            grid_export_price = None
            exp_path = None

        grid_availability = regenerate_grid_availability_dynamic(project_name=project_name, sets=sets)
        grid_avail_csv_path = paths.inputs_dir / "grid_availability.csv"

        to_merge = [
            grid_ds,
            xr.Dataset({"grid_import_price": grid_import_price}),
            xr.Dataset({"grid_availability": grid_availability}),
        ]
        if grid_export_price is not None:
            to_merge.append(xr.Dataset({"grid_export_price": grid_export_price}))

        data = xr.merge([data] + to_merge, compat="override", join="exact")

        data.attrs.setdefault("settings", {})
        data.attrs["settings"]["grid"] = {
            "on_grid": True,
            "allow_export": allow_export,
            "inputs_loaded": {
                "grid_yaml": str(grid_yaml_path),
                "grid_import_price_csv": str(imp_path),
                "grid_export_price_csv": str(exp_path) if allow_export else None,
                "grid_availability_csv": str(grid_avail_csv_path),
            },
        }
    else:
        data.attrs.setdefault("settings", {})
        data.attrs["settings"]["grid"] = {"on_grid": False, "allow_export": False}

    data.attrs["settings"].update(
        {
            "project_name": project_name,
            "formulation": formulation_mode,
            "unit_commitment": uc_enabled,
            "start_year_label": formulation.get("start_year_label"),
            "time_horizon_years": int(year_coord.size),
            "social_discount_rate": _as_float(
                formulation.get("social_discount_rate", 0.0),
                name="social_discount_rate",
                default=0.0,
            ),
            "capacity_expansion": capexp_enabled,
            "investment_steps_years": formulation.get("investment_steps_years"),
            "multi_scenario": {"enabled": ms_enabled, "n_scenarios": n_scen},
            "resources": {
                "n_resources": int(sets.sizes.get("resource", 0)),
                "resource_labels": sets.coords["resource"].values.tolist(),
            },
            "optimization_constraints": {"enforcement": enforcement},
            "inputs_loaded": {
                "load_demand_csv": str(load_path),
                "resource_availability_csv": str(resource_path),
                "renewables_yaml": str(renewables_path),
                "battery_yaml": str(battery_path),
                "generator_yaml": str(genfuel_path),
            },
        }
    )

    data.attrs["settings"].setdefault("generator", {})
    data.attrs["settings"]["generator"]["partial_load_modelling_enabled"] = bool(
        genfuel_meta.get("partial_load_modelling_enabled", False)
    )
    data.attrs["settings"]["generator"]["efficiency_curve_files"] = genfuel_meta.get("efficiency_curve_files", {})
    data.attrs["settings"]["generator"]["label"] = genfuel_meta.get("generator_label", "Generator")
    data.attrs["settings"]["fuel"] = {"label": genfuel_meta.get("fuel_label", "Fuel")}
    data.attrs["settings"]["battery_label"] = bat_params_ds.attrs.get("battery_label", "Battery")

    return data


def initialize_data(project_name: str, sets: xr.Dataset) -> xr.Dataset:
    return load_project_dataset(project_name, sets, mode="multi_year")
