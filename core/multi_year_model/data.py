# generation_planning/modeling/data.py
from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple

import numpy as np
import pandas as pd
import xarray as xr

from core.data_pipeline.battery_loss_model import (
    CONVEX_LOSS_EPIGRAPH,
    InputValidationError as BatteryLossInputValidationError,
    get_battery_loss_model_from_formulation,
    load_battery_loss_curve_dataset,
    resolve_efficiency_curve_values,
)
from core.data_pipeline.generator_partial_load_model import build_generator_partial_load_surrogate
from core.data_pipeline.battery_degradation_model import (
    InputValidationError as BatteryDegradationInputValidationError,
    derive_cycle_fade_coefficient_from_cycle_life,
    get_battery_degradation_settings,
    suppress_exogenous_battery_capacity_degradation_when_endogenous,
)
from core.data_pipeline.battery_calendar_fade_model import (
    InputValidationError as BatteryCalendarFadeInputValidationError,
    load_battery_calendar_fade_curve_dataset,
)
from core.data_pipeline.utils import (
    as_float,
    as_float_or_nan,
    as_str,
    broadcast_to_scenario,
    merge_optional_datasets,
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
      - "step_1", "step_2" (legacy aliases)
      - "base" (single-step legacy alias)
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
      - canonical step labels ('1', '2', ...)
      - legacy aliases ('step_1', 'step_2', ...)
      - 'base' (single-step legacy alias)

    Behavior for 'base':
      - if only one step is expected, 'base' maps to that step
      - if multiple steps are expected, it is rejected to avoid hidden broadcasting

    Raises a clear error if after remapping required steps are still missing.
    """
    if not isinstance(by_step, dict):
        raise InputValidationError(f"{path.name}: {context} missing/invalid by_step mapping.")

    # Normalize keys
    remapped: Dict[str, dict] = {}
    for k, v in by_step.items():
        nk = _normalize_step_key(k)
        remapped[str(nk)] = v

    if "base" in remapped:
        if len(expected_steps) != 1:
            raise InputValidationError(
                f"{path.name}: {context} uses legacy key 'base' for a multi-step project. "
                f"Use explicit step labels {expected_steps}."
            )
        remapped.setdefault(expected_steps[0], remapped["base"])

    missing = [st for st in expected_steps if st not in remapped]
    if missing:
        raise InputValidationError(
            f"{path.name}: {context} missing steps {missing}. "
            f"Expected steps: {expected_steps}. "
            f"Found keys: {list(by_step.keys())}"
        )
    return remapped


def _component_top_level_by_step(
    path: Path,
    component_block: dict,
    *,
    expected_steps: List[str],
    context: str,
) -> Dict[str, dict] | None:
    by_step = component_block.get("by_step", None)
    if by_step is None:
        return None
    remapped = _remap_by_step_dict(
        path,
        by_step,
        expected_steps=expected_steps,
        context=f"{context}.by_step",
    )
    for st in expected_steps:
        blk = remapped.get(st, None)
        if not isinstance(blk, dict):
            raise InputValidationError(f"{path.name}: {context}.by_step['{st}'] must be a dict.")
    return remapped


def _normalize_optional_path(raw: object) -> str | None:
    if isinstance(raw, str):
        value = raw.strip()
        return value or None
    return None


def _shared_technology_error(component: str) -> str:
    return (
        "Multi-year formulation assumes shared technology across investment steps; "
        f"step-specific technical parameters are not supported for {component}."
    )


def _collapse_shared_by_step_numeric(
    path: Path,
    *,
    by_step: Dict[str, dict],
    step_labels: List[str],
    keys: List[str],
    optional_defaults: Dict[str, float],
    context: str,
) -> Dict[str, float]:
    shared: Dict[str, float] = {}
    for key in keys:
        baseline: float | None = None
        for step in step_labels:
            block = by_step[step]
            if key not in block:
                if key in optional_defaults:
                    value = float(optional_defaults[key])
                else:
                    raise InputValidationError(f"{path.name}: missing technical param '{key}' in {context}['{step}'].")
            elif key.endswith("max_installable_capacity_kw") or key.endswith("max_installable_capacity_kwh"):
                value = float(_as_float_or_nan(block.get(key), name=f"{context}/{step}/{key}"))
            else:
                value = float(_as_float(block.get(key), name=f"{context}/{step}/{key}", default=0.0))

            if baseline is None:
                baseline = value
            else:
                same = (
                    (not np.isfinite(baseline) and not np.isfinite(value))
                    or np.isclose(value, baseline, atol=1e-12, rtol=0.0)
                )
                if not same:
                    raise InputValidationError(f"{path.name}: {_shared_technology_error(context.split('.')[0])}")
        shared[key] = float("nan") if baseline is None else float(baseline)
    return shared


def _collapse_shared_by_step_paths(
    path: Path,
    *,
    by_step: Dict[str, dict],
    step_labels: List[str],
    keys: List[str],
    context: str,
) -> Dict[str, str | None]:
    shared: Dict[str, str | None] = {}
    for key in keys:
        baseline: str | None = None
        for step in step_labels:
            value = _normalize_optional_path(by_step[step].get(key, None))
            if baseline is None:
                baseline = value
            elif value != baseline:
                raise InputValidationError(f"{path.name}: {_shared_technology_error(context.split('.')[0])}")
        shared[key] = baseline
    return shared


def _apply_shared_override_numeric(
    *,
    current: Dict[str, float],
    key: str,
    value: float,
    component: str,
) -> None:
    baseline = current.get(key, None)
    if baseline is not None:
        same = (
            (not np.isfinite(baseline) and not np.isfinite(value))
            or np.isclose(float(value), float(baseline), atol=1e-12, rtol=0.0)
        )
        if not same:
            raise InputValidationError(_shared_technology_error(component))
    current[key] = float(value)


def _require_shared_legacy_scenario_value(
    path: Path,
    *,
    by_scenario: dict,
    scenario_labels: List[str],
    key: str,
    context: str,
    numeric: bool = True,
    optional: bool = False,
    default: float | str | None = None,
) -> float | str | None:
    values: list[float | str | None] = []
    for scenario in scenario_labels:
        block = by_scenario.get(scenario, None)
        if not isinstance(block, dict):
            raise InputValidationError(f"{path.name}: {context} missing scenario '{scenario}'.")
        if key not in block:
            if optional:
                values.append(default)
                continue
            raise InputValidationError(f"{path.name}: {context}['{scenario}'] missing '{key}'.")
        raw = block.get(key)
        if raw is None and optional:
            values.append(default)
            continue
        if numeric:
            values.append(_as_float(raw, name=f"{context}/{scenario}/{key}", default=0.0))
        else:
            values.append(_normalize_optional_path(raw))

    first = values[0]
    for other in values[1:]:
        if numeric:
            if not np.isclose(float(other), float(first), atol=1e-12, rtol=0.0):
                raise InputValidationError(
                    f"{path.name}: legacy scenario-specific '{key}' values differ across scenarios in {context}. "
                    "In the shared-technology multi-year model this parameter must be technology-based. "
                    "Move it to a shared/by_step block or make the scenario values identical."
                )
        else:
            if other != first:
                raise InputValidationError(
                    f"{path.name}: legacy scenario-specific '{key}' values differ across scenarios in {context}. "
                    "In the shared-technology multi-year model this parameter must be technology-based."
                )
    return first


def _validate_generator_partial_load_curve(
    *,
    rel: np.ndarray,
    eff: np.ndarray,
    path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Validate the implied generator fuel curve in relative units and return a
    zero-anchored raw curve together with the convex surrogate used by the LP
    secant-envelope formulation.

    The generator CSV column is resolved upstream either as a normalized
    multiplier relative to `generator_nominal_efficiency_full_load` or as a
    backward-compatible absolute-efficiency curve. This validator works on the
    resulting absolute efficiencies.
    """
    return build_generator_partial_load_surrogate(
        rel=rel,
        eff=eff,
        path=path,
        error_cls=InputValidationError,
    )

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
    Parse multi-year (dynamic) load_demand.csv template with 2-row header.

    Conceptual layout:
      row 1: meta, scenario_1, scenario_1, ...
      row 2: hour, 2026, 2027, ...
      row 3+: 0, value, value, ...

    Actually stored as a MultiIndex header (scenario, year):
      - ("meta","hour") column must exist and match sets.period exactly (0..8759)
      - demand columns must include (scenario_label, year_label) for all combos
      - returns xr.DataArray with dims (year, period, scenario) in kWh

    Notes:
      - year labels are read as strings from the CSV header but must match the
        explicit Multi-Year set labels (typically calendar years such as "2026")
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
    Parse multi-year (dynamic) resource_availability.csv template with 3 header rows.

    Conceptual layout:
      row 1: meta, scenario_1, scenario_1, ...
      row 2: hour, 2026, 2026, ...
      row 3: , Solar PV, Wind Turbine, ...

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
      - inv_step, resource                  (investment-side params)
      - resource                            (technical params, step-invariant)

    Supported YAML structures:
      - Current shared-technology schema:
          investment.by_step + shared technical
      - Legacy schemas:
          investment.by_step + shared technical + operation.by_scenario
          by_step.<step>.investment / technical / operation.by_scenario

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
        "fixed_om_share_per_year",
        "production_subsidy_per_kwh",
    ]
    OPTIONAL_INVESTMENT_BY_STEP = {
        "fixed_om_share_per_year": 0.0,
        "production_subsidy_per_kwh": 0.0,
    }

    # technical, step-invariant (single technology physics)
    PARAMS_TECHNICAL_INVARIANT = [
        "inverter_efficiency",
        "specific_area_m2_per_kw",            # physical land-use coefficient (resource-level)
        "max_installable_capacity_kw",        # allow None -> NaN
        "capacity_degradation_rate_per_year",
    ]
    OPTIONAL_TECHNICAL = {"capacity_degradation_rate_per_year": 0.0}

    n_k = len(step_labels)
    n_r = len(resource_labels)
    # allocate arrays
    inv_arr = {k: np.full((n_k, n_r), np.nan, dtype=float) for k in PARAMS_INVESTMENT_BY_STEP}
    tech_arr = {k: np.full((n_r,), np.nan, dtype=float) for k in PARAMS_TECHNICAL_INVARIANT}
    op_arr = {
        "fixed_om_share_per_year": np.full((n_k, n_r), np.nan, dtype=float),
        "production_subsidy_per_kwh": np.full((n_k, n_r), np.nan, dtype=float),
    }

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

        if "by_step" in item:
            raise InputValidationError(
                f"{path.name}: resource '{res_label}' uses legacy top-level `by_step`. "
                "Use `investment.by_step` plus a shared `technical` block."
            )

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
                    if k in OPTIONAL_INVESTMENT_BY_STEP:
                        inv_arr[k][si, j] = float(OPTIONAL_INVESTMENT_BY_STEP[k])
                        continue
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
        if "by_step" in tech_block:
            raise InputValidationError(
                f"{path.name}: resource '{res_label}' uses legacy `technical.by_step`. "
                "Multi-year renewables require one shared `technical` block."
            )

        for k in PARAMS_TECHNICAL_INVARIANT:
            if k in tech_block:
                if k == "max_installable_capacity_kw":
                    tech_arr[k][j] = _as_float_or_nan(tech_block.get(k), name=f"{res_label}/technical/{k}")
                else:
                    tech_arr[k][j] = _as_float(tech_block.get(k), name=f"{res_label}/technical/{k}", default=0.0)
                continue

            if k in OPTIONAL_TECHNICAL:
                tech_arr[k][j] = float(OPTIONAL_TECHNICAL[k])
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

        for st in step_labels:
            si = step_to_idx[st]
            op_arr["fixed_om_share_per_year"][si, j] = inv_arr["fixed_om_share_per_year"][si, j]
            op_arr["production_subsidy_per_kwh"][si, j] = inv_arr["production_subsidy_per_kwh"][si, j]

        if "operation" in item:
            raise InputValidationError(
                f"{path.name}: resource '{res_label}' uses legacy `operation` blocks. "
                "Store fixed O&M and production subsidy in `investment.by_step`, and store capacity degradation once in `technical`."
            )

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

    # investment-side shared economic terms by cohort/resource
    for k in ("fixed_om_share_per_year", "production_subsidy_per_kwh"):
        var_name = f"res_{k}"
        data_vars[var_name] = xr.DataArray(
            op_arr[k],
            coords={"inv_step": inv_step_coord, "resource": resource_coord},
            dims=("inv_step", "resource"),
            name=var_name,
            attrs={"source_file": str(path), "component": "renewable", "original_key": k, "scenario_dependent": False},
        )

    ds = xr.Dataset(data_vars=data_vars)
    ds.attrs["settings"] = {
        "inputs_loaded": {"renewables_yaml": str(path)},
        "schema": "shared_technology_capacity_expansion",
    }
    return ds

def _load_battery_yaml(
    path: Path,
    *,
    scenario_coord: xr.DataArray,
    inv_step_coord: xr.DataArray,
    require_initial_soh: bool = False,
    require_cycle_fade_coefficient: bool = False,
    require_calendar_time_increment: bool = False,
) -> xr.Dataset:
    """Load dynamic battery parameters from the current shared-technology schema.

    Required schema:
    - battery.investment.by_step
    - battery.technical

    Technical battery parameters are treated as shared across investment steps
    in the multi-year formulation.
    """
    payload = _read_yaml(path)

    bat = payload.get("battery", None)
    if not isinstance(bat, dict):
        raise InputValidationError(f"{path.name}: missing/invalid 'battery' mapping.")

    step_labels = [str(st) for st in inv_step_coord.values.tolist()]
    n_k = len(step_labels)

    step_to_idx = {lab: i for i, lab in enumerate(step_labels)}

    INVESTMENT_BY_STEP = [
        "nominal_capacity_kwh",
        "specific_investment_cost_per_kwh",
        "wacc",
        "calendar_lifetime_years",
        "embedded_emissions_kgco2e_per_kwh",
        "fixed_om_share_per_year",
    ]
    OPTIONAL_INVESTMENT_BY_STEP = {"fixed_om_share_per_year": 0.0}
    SHARED_TECHNICAL_KEYS = [
        "charge_efficiency",
        "discharge_efficiency",
        "initial_soc",
        "depth_of_discharge",
        "max_discharge_time_hours",
        "max_charge_time_hours",
        "max_installable_capacity_kwh",
        "capacity_degradation_rate_per_year",
    ]
    OPTIONAL_SHARED_TECHNICAL = {
        "capacity_degradation_rate_per_year": 0.0,
    }
    CONDITIONAL_TECHNICAL_DEFAULTS = {
        "initial_soh": 1.0,
        "end_of_life_soh": np.nan,
        "cycle_lifetime_to_eol_cycles": np.nan,
        "cycle_fade_coefficient_per_kwh_throughput": np.nan,
        "calendar_time_increment_per_year": 1.0,
    }
    REQUIRED_CONDITIONAL_TECHNICAL = {
        key
        for key, required in {
            "initial_soh": require_initial_soh,
            "cycle_fade_coefficient_per_kwh_throughput": require_cycle_fade_coefficient,
            "calendar_time_increment_per_year": require_calendar_time_increment,
        }.items()
        if required
    }
    SHARED_TECHNICAL_PATH_KEYS = [
        "efficiency_curve_csv",
        "calendar_fade_curve_csv",
    ]
    if "by_step" in bat:
        raise InputValidationError(
            f"{path.name}: battery uses legacy top-level `by_step`. "
            "Use `battery.investment.by_step` plus a shared `battery.technical` block."
        )

    inv_block = bat.get("investment", None)
    if not isinstance(inv_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.investment mapping.")
    inv_by_step = _remap_by_step_dict(
        path,
        inv_block.get("by_step", None),
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
                if k in OPTIONAL_INVESTMENT_BY_STEP:
                    inv_arr[k][si] = float(OPTIONAL_INVESTMENT_BY_STEP[k])
                    continue
                raise InputValidationError(
                    f"{path.name}: missing investment param '{k}' in battery.investment.by_step['{st}']."
                )
            inv_arr[k][si] = _as_float(blk.get(k), name=f"battery/investment/{st}/{k}", default=0.0)

    tech_block = bat.get("technical", None)
    if not isinstance(tech_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid battery.technical mapping.")
    tech_by_step_raw = tech_block.get("by_step", None)
    shared_tech: dict[str, float] = {}
    shared_paths: dict[str, str | None] = {}
    legacy_tech = None if tech_by_step_raw is not None else tech_block

    if tech_by_step_raw is not None:
        raise InputValidationError(
            f"{path.name}: battery uses legacy `technical.by_step`. "
            "Multi-year battery technical parameters must be provided once in the shared `battery.technical` block."
        )
    else:
        if not isinstance(legacy_tech, dict):
            raise InputValidationError(f"{path.name}: missing/invalid battery.technical mapping.")
        if (
            "calendar_time_increment_per_year" not in legacy_tech
            and "calendar_time_increment_per_step" in legacy_tech
        ):
            legacy_tech["calendar_time_increment_per_year"] = legacy_tech["calendar_time_increment_per_step"]
        for k in SHARED_TECHNICAL_KEYS:
            if k not in legacy_tech:
                if k in OPTIONAL_SHARED_TECHNICAL:
                    shared_tech[k] = float(OPTIONAL_SHARED_TECHNICAL[k])
                    continue
                raise InputValidationError(f"{path.name}: missing technical param '{k}' in battery.technical.")
            if k == "max_installable_capacity_kwh":
                shared_tech[k] = _as_float_or_nan(legacy_tech.get(k), name=f"battery/technical/{k}")
            else:
                shared_tech[k] = _as_float(legacy_tech.get(k), name=f"battery/technical/{k}", default=0.0)
        for key, default_value in CONDITIONAL_TECHNICAL_DEFAULTS.items():
            if key not in legacy_tech:
                if key in REQUIRED_CONDITIONAL_TECHNICAL:
                    raise InputValidationError(f"{path.name}: missing technical param '{key}' in battery.technical.")
                shared_tech[key] = float(default_value)
                continue
            shared_tech[key] = _as_float(legacy_tech.get(key), name=f"battery/technical/{key}", default=0.0)
        for k in SHARED_TECHNICAL_PATH_KEYS:
            shared_paths[k] = _normalize_optional_path(legacy_tech.get(k, None))

    legacy_op = bat.get("operation", None)
    if isinstance(legacy_op, dict):
        raise InputValidationError(
            f"{path.name}: battery uses legacy `operation` blocks. "
            "Store fixed O&M in `battery.investment.by_step` and degradation inputs in the shared `battery.technical` block."
        )

    PREFIX = "battery_"
    data_vars = {}
    for k in INVESTMENT_BY_STEP:
        var_name = f"{PREFIX}{k}"
        data_vars[var_name] = xr.DataArray(
            inv_arr[k],
            coords={"inv_step": inv_step_coord},
            dims=("inv_step",),
            name=var_name,
            attrs={"source_file": str(path), "component": "battery", "original_key": k, "scenario_dependent": False},
        )

    for k in SHARED_TECHNICAL_KEYS + list(CONDITIONAL_TECHNICAL_DEFAULTS.keys()):
        var_name = f"{PREFIX}{k}"
        data_vars[var_name] = xr.DataArray(
            shared_tech[k],
            name=var_name,
            attrs={"source_file": str(path), "component": "battery", "original_key": k, "scenario_dependent": False},
        )
    ds = xr.Dataset(data_vars=data_vars)
    ds.attrs["battery_label"] = str(bat.get("label", "Battery"))
    ds.attrs["efficiency_curve_file"] = shared_paths.get("efficiency_curve_csv", None)
    ds.attrs["battery_calendar_fade_curve_file"] = shared_paths.get("calendar_fade_curve_csv", None)
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
    """Load dynamic generator + fuel parameters from the current shared-technology schema."""
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

    n_k = len(step_labels)
    n_y = len(year_labels)

    step_to_idx = {lab: i for i, lab in enumerate(step_labels)}

    GEN_INVESTMENT_STEP = [
        "nominal_capacity_kw",
        "lifetime_years",
        "specific_investment_cost_per_kw",
        "wacc",
        "embedded_emissions_kgco2e_per_kw",
        "fixed_om_share_per_year",
    ]
    OPTIONAL_GEN_INVESTMENT_STEP = {"fixed_om_share_per_year"}
    SHARED_GEN_TECHNICAL_KEYS = [
        "nominal_efficiency_full_load",
        "max_installable_capacity_kw",
        "capacity_degradation_rate_per_year",
    ]
    OPTIONAL_SHARED_GEN_TECHNICAL = {"capacity_degradation_rate_per_year": 0.0}
    SHARED_GEN_PATH_KEYS = ["efficiency_curve_csv"]

    if "by_step" in gen:
        raise InputValidationError(
            f"{path.name}: generator uses legacy top-level `by_step`. "
            "Use `generator.investment.by_step` plus a shared `generator.technical` block."
        )

    inv_block = gen.get("investment", None)
    if not isinstance(inv_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid generator.investment mapping.")
    inv_by_step = _remap_by_step_dict(
        path,
        inv_block.get("by_step", None),
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
                    inv_arr[k][si] = 0.0
                    continue
                raise InputValidationError(
                    f"{path.name}: missing generator investment param '{k}' in investment.by_step['{st}']."
                )

            if k in OPTIONAL_GEN_INVESTMENT_STEP:
                inv_arr[k][si] = _as_float(blk.get(k), name=f"generator/investment/{st}/{k}", default=0.0)
            else:
                inv_arr[k][si] = _as_float(blk.get(k), name=f"generator/investment/{st}/{k}", default=0.0)

    tech_block = gen.get("technical", None)
    shared_gen_tech: dict[str, float] = {}
    shared_gen_paths: dict[str, str | None] = {}
    if not isinstance(tech_block, dict):
        raise InputValidationError(f"{path.name}: missing/invalid generator.technical mapping.")
    tech_by_step_raw = tech_block.get("by_step", None)
    legacy_tech = None if tech_by_step_raw is not None else tech_block
    if tech_by_step_raw is not None:
        raise InputValidationError(
            f"{path.name}: generator uses legacy `technical.by_step`. "
            "Multi-year generator technical parameters must be provided once in the shared `generator.technical` block."
        )
    else:
        if not isinstance(legacy_tech, dict):
            raise InputValidationError(f"{path.name}: missing/invalid generator.technical mapping.")
        for k in SHARED_GEN_TECHNICAL_KEYS:
            if k not in legacy_tech:
                if k in OPTIONAL_SHARED_GEN_TECHNICAL:
                    shared_gen_tech[k] = float(OPTIONAL_SHARED_GEN_TECHNICAL[k])
                    continue
                raise InputValidationError(f"{path.name}: missing generator technical param '{k}' in generator.technical.")
            if k == "max_installable_capacity_kw":
                shared_gen_tech[k] = _as_float_or_nan(legacy_tech.get(k), name=f"generator/technical/{k}")
            else:
                shared_gen_tech[k] = _as_float(legacy_tech.get(k), name=f"generator/technical/{k}", default=0.0)
        for k in SHARED_GEN_PATH_KEYS:
            shared_gen_paths[k] = _normalize_optional_path(legacy_tech.get(k, None))

    legacy_op_block = gen.get("operation", None)
    if isinstance(legacy_op_block, dict):
        raise InputValidationError(
            f"{path.name}: generator uses legacy `operation` blocks. "
            "Store fixed O&M in `generator.investment.by_step` and degradation once in `generator.technical`."
        )

    gen_data_vars: dict[str, xr.DataArray] = {}
    for k in GEN_INVESTMENT_STEP:
        var_name = f"generator_{k}"
        gen_data_vars[var_name] = xr.DataArray(
            inv_arr[k],
            coords={"inv_step": inv_step_coord},
            dims=("inv_step",),
            name=var_name,
            attrs={"source_file": str(path), "scenario_dependent": False, "original_key": k, "block": "investment"},
        )

    for k in SHARED_GEN_TECHNICAL_KEYS:
        var_name = f"generator_{k}"
        gen_data_vars[var_name] = xr.DataArray(
            shared_gen_tech[k],
            name=var_name,
            attrs={"source_file": str(path), "scenario_dependent": False, "original_key": k, "block": "technical"},
        )
    gen_ds = xr.Dataset(data_vars=gen_data_vars)
    gen_ds.attrs["generator_label"] = str(gen.get("label", "Generator"))
    gen_ds.attrs["generator_efficiency_curve_file"] = shared_gen_paths.get("efficiency_curve_csv", None)

    fuel_shared_vals = {
        "lhv_kwh_per_unit_fuel": float("nan"),
        "direct_emissions_kgco2e_per_unit_fuel": float("nan"),
    }
    fuel_cost_year_arr = np.full((len(scenario_labels), n_y), np.nan, dtype=float)
    fuel_technical_block = fuel.get("technical", None)
    fuel_cost_block = fuel.get("cost", None)
    if "by_step" in fuel:
        raise InputValidationError(
            f"{path.name}: fuel uses legacy `by_step`. "
            "Multi-year fuel inputs require one shared `fuel.technical` block plus `fuel.cost.by_scenario` yearly prices."
        )
    if isinstance(fuel_technical_block, dict):
        for key in fuel_shared_vals:
            if key not in fuel_technical_block:
                raise InputValidationError(f"{path.name}: fuel.technical missing '{key}'.")
            fuel_shared_vals[key] = _as_float(fuel_technical_block.get(key), name=f"fuel/technical/{key}", default=0.0)
        fuel_cost_by_scenario = fuel_cost_block.get("by_scenario", None) if isinstance(fuel_cost_block, dict) else None
        if not isinstance(fuel_cost_by_scenario, dict):
            raise InputValidationError(
                f"{path.name}: shared-technology dynamic fuel inputs require fuel.cost.by_scenario for yearly fuel prices."
            )
        for s_idx, s in enumerate(scenario_labels):
            block = fuel_cost_by_scenario.get(s, None)
            if not isinstance(block, dict):
                raise InputValidationError(f"{path.name}: fuel.cost.by_scenario missing scenario '{s}'.")
            series = block.get("by_year_cost_per_unit_fuel", None)
            if not isinstance(series, list) or len(series) != n_y:
                raise InputValidationError(
                    f"{path.name}: fuel.cost.by_scenario['{s}'].by_year_cost_per_unit_fuel must be a list with {n_y} entries."
                )
            fuel_cost_year_arr[s_idx, :] = np.asarray(
                [_as_float(v, name=f"fuel/cost/{s}/by_year_cost_per_unit_fuel[{i}]", default=0.0) for i, v in enumerate(series)],
                dtype=float,
            )
    elif isinstance(fuel.get("by_scenario", None), dict):
        raise InputValidationError(
            f"{path.name}: fuel uses legacy `by_scenario`. "
            "Multi-year fuel inputs now require `fuel.technical` plus `fuel.cost.by_scenario`."
        )
    else:
        raise InputValidationError(
            f"{path.name}: fuel must provide shared `technical` data plus `cost.by_scenario` yearly prices."
        )

    fuel_ds = xr.Dataset(
        data_vars={
            "fuel_lhv_kwh_per_unit_fuel": xr.DataArray(
                fuel_shared_vals["lhv_kwh_per_unit_fuel"],
                attrs={"source_file": str(path), "scenario_dependent": False, "original_key": "lhv_kwh_per_unit_fuel"},
            ),
            "fuel_direct_emissions_kgco2e_per_unit_fuel": xr.DataArray(
                fuel_shared_vals["direct_emissions_kgco2e_per_unit_fuel"],
                attrs={"source_file": str(path), "scenario_dependent": False, "original_key": "direct_emissions_kgco2e_per_unit_fuel"},
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
    shared_curve_file = shared_gen_paths.get("efficiency_curve_csv", None)
    unique_curve_files = sorted({v for v in [shared_curve_file] if v})
    partial_load_enabled = bool(unique_curve_files)
    eff_curve_ds = None
    if unique_curve_files:
        curve_path = Path(shared_curve_file)
        if not curve_path.is_absolute():
            curve_path = inputs_dir / curve_path
        if not curve_path.exists():
            raise InputValidationError(f"{path.name}: generator efficiency curve not found: {curve_path}")
        cdf = pd.read_csv(curve_path)
        req_cols = ["Relative Power Output [-]", "Efficiency [-]"]
        for col in req_cols:
            if col not in cdf.columns:
                raise InputValidationError(f"{curve_path.name}: missing required column '{col}'.")
        rel = pd.to_numeric(cdf["Relative Power Output [-]"], errors="coerce").to_numpy(dtype=float)
        eff_raw = pd.to_numeric(cdf["Efficiency [-]"], errors="coerce").to_numpy(dtype=float)
        if np.isnan(rel).any() or np.isnan(eff_raw).any():
            raise InputValidationError(f"{curve_path.name}: contains non-numeric values in required columns.")
        if rel.size < 1 or np.any(rel < 0.0) or np.any(rel > 1.0) or np.any(np.diff(rel) <= 0.0) or not np.isclose(rel[-1], 1.0, atol=1e-9):
            raise InputValidationError(f"{curve_path.name}: invalid relative-power grid for the generator efficiency curve.")
        eff, _, _ = resolve_efficiency_curve_values(
            eff_raw,
            base_efficiency=float(shared_gen_tech["nominal_efficiency_full_load"]),
            path=curve_path,
            column_name="Efficiency [-]",
            allow_zero=True,
        )
        rel, eff, fuel_raw_rel, fuel_surrogate_rel = _validate_generator_partial_load_curve(
            rel=rel,
            eff=eff,
            path=curve_path,
        )
        curve_point = xr.IndexVariable("curve_point", list(range(rel.size)))
        eff_curve_ds = xr.Dataset(
            data_vars={
                "generator_eff_curve_rel_power": xr.DataArray(
                    rel,
                    coords={"curve_point": curve_point},
                    dims=("curve_point",),
                    attrs={"units": "-", "scenario_dependent": False},
                ),
                "generator_eff_curve_eff": xr.DataArray(
                    eff,
                    coords={"curve_point": curve_point},
                    dims=("curve_point",),
                    attrs={"units": "-", "scenario_dependent": False},
                ),
                "generator_fuel_curve_rel_fuel_use": xr.DataArray(
                    fuel_surrogate_rel,
                    coords={"curve_point": curve_point},
                    dims=("curve_point",),
                    attrs={
                        "units": "-",
                        "scenario_dependent": False,
                        "description": "Convex surrogate of the relative fuel-use curve phi(r)=r/eta(r) used internally by the LP partial-load formulation.",
                    },
                ),
                "generator_fuel_curve_rel_fuel_use_raw": xr.DataArray(
                    fuel_raw_rel,
                    coords={"curve_point": curve_point},
                    dims=("curve_point",),
                    attrs={
                        "units": "-",
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
    Parse dynamic price CSV template with header=[0,1] (scenario, year).

    Conceptual layout:
      row 1: meta, scenario_1, scenario_1, scenario_2, scenario_2
      row 2: hour, 2026, 2027, 2026, 2027
      row 3+: 0, value, value, value, value

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
            first_year_connection: <year label or null>
            outages:
              average_outages_per_year: ...
              average_outage_duration_minutes: ...
              outage_scale_od_hours: ...
              outage_shape_od: ...

    Notes:
      - first_year_connection is scenario-dependent.
      - It may be provided either as an exact year label (preferred), or as an
        integer calendar year when sets.year labels are also integer-like.
      - If first_year_connection is null, grid is available from the start of
        the modeled horizon.
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
        ("line", "emissions_factor_kgco2e_per_kwh", "grid_emissions_factor_kgco2e_per_kwh"),

        ("outages", "average_outages_per_year", "grid_avg_outages_per_year"),
        ("outages", "average_outage_duration_minutes", "grid_avg_outage_duration_minutes"),
        ("outages", "outage_scale_od_hours", "grid_outage_scale_od_hours"),
        ("outages", "outage_shape_od", "grid_outage_shape_od"),
        ("outages", "outage_seed", "grid_outage_seed"),
    ]

    arr = {out: np.full((len(scenario_labels),), np.nan, dtype=float) for _, _, out in PARAMS}
    first_year = np.full((len(scenario_labels),), None, dtype=object)

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
        # Allow missing/blank -> treat as connected from the start of the horizon.
        raw_fy = block.get("first_year_connection", None)
        if raw_fy is None or (isinstance(raw_fy, str) and raw_fy.strip() == ""):
            first_year[i] = None
        else:
            if isinstance(raw_fy, str):
                fy_value: object = raw_fy.strip()
            else:
                try:
                    fy_value = int(raw_fy)
                except Exception:
                    raise InputValidationError(
                        f"{path.name}: grid.by_scenario['{s_lab}'].first_year_connection must be either "
                        "an exact year label from sets.year or an integer calendar year."
                    )
            if fy_value == "":
                raise InputValidationError(
                    f"{path.name}: grid.by_scenario['{s_lab}'].first_year_connection cannot be an empty string."
                )
            _first_connection_year_to_ordinal(
                fy_value,
                year_coord.values.tolist(),
                context=f"{path.name}: grid.by_scenario['{s_lab}'].first_year_connection",
            )
            first_year[i] = fy_value

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
            elif out == "grid_emissions_factor_kgco2e_per_kwh":
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
    if np.any(arr["grid_emissions_factor_kgco2e_per_kwh"] < 0.0):
        raise InputValidationError(f"{path.name}: line.emissions_factor_kgco2e_per_kwh must be >= 0.")
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
            "notes": (
                "Null means connected from the start of the horizon. "
                "Non-null values are validated against sets.year using exact label matching first; "
                "integer calendar-year mapping is allowed only when sets.year labels are integer-like."
            ),
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


def _first_connection_year_to_ordinal(
    first_year_value: Any,
    year_values: list[Any],
    *,
    context: str = "first_year_connection",
) -> int | None:
    if first_year_value is None:
        return None
    if not year_values:
        return None

    year_labels = [str(v) for v in year_values]
    fy_str = str(first_year_value)
    if fy_str in year_labels:
        return year_labels.index(fy_str) + 1

    try:
        fy_int = int(first_year_value)
    except Exception as exc:
        raise InputValidationError(
            f"{context}={first_year_value!r} does not match any sets.year label {year_labels}."
        ) from exc

    try:
        year_ints = [int(v) for v in year_values]
    except Exception as exc:
        raise InputValidationError(
            f"{context}={first_year_value!r} does not match any sets.year label {year_labels}. "
            "Because sets.year labels are not integer-like, numeric ordinal fallback is not supported."
        ) from exc

    if fy_int <= year_ints[0]:
        # Calendar-year semantics: anything before or equal to the first modeled
        # calendar year means the grid is connected from the horizon start.
        return 1
    for idx, year_int in enumerate(year_ints, start=1):
        if fy_int == year_int:
            return idx
    if fy_int > year_ints[-1]:
        # Connection happens after the modeled horizon, so availability is zero
        # for all modeled years.
        return int(len(year_values) + 1)

    raise InputValidationError(
        f"{context}={first_year_value!r} is not an exact sets.year label and does not match any modeled "
        f"calendar year in {year_labels}. Provide an exact year label instead."
    )


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
        connection_ordinal = _first_connection_year_to_ordinal(
            fy.item() if hasattr(fy, "item") else fy,
            year_values,
            context=f"grid.by_scenario['{s_lab}'].first_year_connection",
        )

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
        attrs={
            "units": "binary",
            "component": "grid",
            "dynamic_only": True,
            "generated_artifact": True,
            "notes": "Derived from grid.yaml outage statistics and first_year_connection; not a primary user-maintained input.",
        },
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
    land_m2 = _as_float_or_nan(optc.get("land_availability_m2", None), name="land_availability_m2")
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
    battery_loss_model = get_battery_loss_model_from_formulation(formulation)
    try:
        battery_degradation_settings = get_battery_degradation_settings(
            formulation,
            battery_loss_model=battery_loss_model,
        )
    except BatteryDegradationInputValidationError as exc:
        raise InputValidationError(str(exc)) from exc
    battery_path = paths.inputs_dir / "battery.yaml"
    bat_params_ds = _load_battery_yaml(
        battery_path,
        scenario_coord=scenario_coord,
        inv_step_coord=inv_step_coord,
        require_initial_soh=bool(battery_degradation_settings.get("endogenous_degradation_enabled", False)),
        require_cycle_fade_coefficient=False,
        require_calendar_time_increment=bool(battery_degradation_settings.get("calendar_fade_enabled", False)),
    )
    active_battery_capacity_degradation_rate, ignored_exogenous_battery_degradation = (
        suppress_exogenous_battery_capacity_degradation_when_endogenous(
            bat_params_ds.get("battery_capacity_degradation_rate_per_year", None),
            calendar_fade_enabled=bool(battery_degradation_settings.get("calendar_fade_enabled", False)),
        )
    )
    if active_battery_capacity_degradation_rate is not None:
        bat_params_ds = bat_params_ds.copy()
        bat_params_ds["battery_capacity_degradation_rate_per_year"] = active_battery_capacity_degradation_rate
    active_battery_exogenous_degradation = False
    if active_battery_capacity_degradation_rate is not None:
        vals = np.asarray(active_battery_capacity_degradation_rate.values, dtype=float)
        vals = vals[np.isfinite(vals)]
        active_battery_exogenous_degradation = bool(vals.size > 0 and float(np.max(np.abs(vals))) > 0.0)
    battery_calendar_curve_ds = None
    battery_calendar_curve_path = bat_params_ds.attrs.get("battery_calendar_fade_curve_file", None)
    if battery_degradation_settings.get("calendar_fade_enabled", False):
        raw_curve_path = battery_calendar_curve_path or battery_degradation_settings.get("battery_calendar_fade_curve_csv")
        if not raw_curve_path:
            raise InputValidationError(
                "battery.yaml: battery.technical.calendar_fade_curve_csv is required when calendar fade is enabled."
            )
        curve_path = Path(str(raw_curve_path))
        if not curve_path.is_absolute():
            curve_path = paths.inputs_dir / curve_path
        try:
            curve_ds = load_battery_calendar_fade_curve_dataset(curve_path)
        except BatteryCalendarFadeInputValidationError as exc:
            raise InputValidationError(str(exc)) from exc
        calendar_curve_point = xr.IndexVariable("battery_calendar_curve_point", curve_ds.coords["battery_calendar_curve_point"].values)
        calendar_segment = xr.IndexVariable("battery_calendar_segment", curve_ds.coords["battery_calendar_segment"].values)
        battery_calendar_curve_ds = xr.Dataset(
            data_vars={
                "battery_calendar_soc_curve_pu": xr.DataArray(
                    np.asarray(curve_ds["battery_calendar_soc_curve_pu"].values, dtype=float),
                    coords={"battery_calendar_curve_point": calendar_curve_point},
                    dims=("battery_calendar_curve_point",),
                ),
                "battery_calendar_fade_curve_coefficient_per_year": xr.DataArray(
                    np.asarray(curve_ds["battery_calendar_fade_curve_coefficient_per_year"].values, dtype=float),
                    coords={"battery_calendar_curve_point": calendar_curve_point},
                    dims=("battery_calendar_curve_point",),
                ),
                "battery_calendar_fade_slope": xr.DataArray(
                    np.asarray(curve_ds["battery_calendar_fade_slope"].values, dtype=float),
                    coords={"battery_calendar_segment": calendar_segment},
                    dims=("battery_calendar_segment",),
                ),
                "battery_calendar_fade_intercept": xr.DataArray(
                    np.asarray(curve_ds["battery_calendar_fade_intercept"].values, dtype=float),
                    coords={"battery_calendar_segment": calendar_segment},
                    dims=("battery_calendar_segment",),
                ),
            }
        )
        battery_degradation_settings["battery_calendar_fade_curve_csv"] = str(curve_path)
    battery_degradation_settings["initial_soh"] = float(
        bat_params_ds["battery_initial_soh"].item()
        if "battery_initial_soh" in bat_params_ds.data_vars
        else battery_degradation_settings.get("initial_soh", 1.0)
    )
    battery_degradation_settings["end_of_life_soh"] = (
        float(bat_params_ds["battery_end_of_life_soh"].item())
        if "battery_end_of_life_soh" in bat_params_ds.data_vars and np.isfinite(float(bat_params_ds["battery_end_of_life_soh"].item()))
        else battery_degradation_settings.get("end_of_life_soh", None)
    )
    battery_degradation_settings["cycle_lifetime_to_eol_cycles"] = (
        float(bat_params_ds["battery_cycle_lifetime_to_eol_cycles"].item())
        if "battery_cycle_lifetime_to_eol_cycles" in bat_params_ds.data_vars
        and np.isfinite(float(bat_params_ds["battery_cycle_lifetime_to_eol_cycles"].item()))
        else battery_degradation_settings.get("cycle_lifetime_to_eol_cycles", None)
    )
    legacy_cycle_fade_coefficient = (
        float(bat_params_ds["battery_cycle_fade_coefficient_per_kwh_throughput"].item())
        if "battery_cycle_fade_coefficient_per_kwh_throughput" in bat_params_ds.data_vars
        and np.isfinite(float(bat_params_ds["battery_cycle_fade_coefficient_per_kwh_throughput"].item()))
        else battery_degradation_settings.get("cycle_fade_coefficient_per_kwh_throughput", None)
    )
    if battery_degradation_settings.get("cycle_fade_enabled", False):
        cycle_lifetime_to_eol_cycles = battery_degradation_settings.get("cycle_lifetime_to_eol_cycles", None)
        end_of_life_soh = battery_degradation_settings.get("end_of_life_soh", None)
        if cycle_lifetime_to_eol_cycles is not None and end_of_life_soh is not None:
            battery_degradation_settings["cycle_fade_coefficient_per_kwh_throughput"] = float(
                derive_cycle_fade_coefficient_from_cycle_life(
                    initial_soh=float(battery_degradation_settings["initial_soh"]),
                    end_of_life_soh=float(end_of_life_soh),
                    cycle_lifetime_to_eol_cycles=float(cycle_lifetime_to_eol_cycles),
                    reference_depth_of_discharge=float(bat_params_ds["battery_depth_of_discharge"].item()),
                )
            )
            battery_degradation_settings["cycle_fade_input_mode"] = "derived_from_cycle_lifetime"
        elif legacy_cycle_fade_coefficient is not None:
            battery_degradation_settings["cycle_fade_coefficient_per_kwh_throughput"] = float(legacy_cycle_fade_coefficient)
            battery_degradation_settings["cycle_fade_input_mode"] = "direct_coefficient"
        else:
            raise InputValidationError(
                "battery.yaml: enable cycle fade only when either battery.technical.cycle_lifetime_to_eol_cycles "
                "and battery.technical.end_of_life_soh are provided, or the legacy "
                "battery.technical.cycle_fade_coefficient_per_kwh_throughput is provided."
            )
    else:
        battery_degradation_settings["cycle_fade_coefficient_per_kwh_throughput"] = float(
            legacy_cycle_fade_coefficient if legacy_cycle_fade_coefficient is not None else 0.0
        )
        battery_degradation_settings["cycle_fade_input_mode"] = (
            "direct_coefficient" if legacy_cycle_fade_coefficient is not None else "disabled"
        )
    battery_degradation_settings["battery_calendar_time_increment_per_year"] = float(
        bat_params_ds["battery_calendar_time_increment_per_year"].item()
        if "battery_calendar_time_increment_per_year" in bat_params_ds.data_vars
        else battery_degradation_settings.get("battery_calendar_time_increment_per_year", 1.0)
    )
    battery_curve_path = bat_params_ds.attrs.get("efficiency_curve_file", None)
    battery_curve_ds = None
    if battery_loss_model == CONVEX_LOSS_EPIGRAPH:
        raw_curve_path = battery_curve_path
        if not raw_curve_path:
            raise InputValidationError(
                "battery_model.loss_model='convex_loss_epigraph' requires battery.technical.efficiency_curve_csv."
            )
        curve_path = Path(raw_curve_path)
        if not curve_path.is_absolute():
            curve_path = paths.inputs_dir / curve_path
        charge_efficiency_base = float(bat_params_ds["battery_charge_efficiency"].item())
        discharge_efficiency_base = float(bat_params_ds["battery_discharge_efficiency"].item())
        try:
            curve_ds = load_battery_loss_curve_dataset(
                curve_path,
                charge_efficiency_base=charge_efficiency_base,
                discharge_efficiency_base=discharge_efficiency_base,
            )
        except BatteryLossInputValidationError as exc:
            raise InputValidationError(str(exc)) from exc
        battery_curve_point = xr.IndexVariable("battery_curve_point", curve_ds.coords["battery_curve_point"].values)
        battery_loss_segment = xr.IndexVariable("battery_loss_segment", curve_ds.coords["battery_loss_segment"].values)
        battery_curve_ds = xr.Dataset(
            data_vars={
                "battery_efficiency_curve_rel_power": xr.DataArray(
                    np.asarray(curve_ds["battery_efficiency_curve_rel_power"].values, dtype=float),
                    coords={"battery_curve_point": battery_curve_point},
                    dims=("battery_curve_point",),
                ),
                "battery_efficiency_curve_charge_efficiency": xr.DataArray(
                    np.asarray(curve_ds["battery_efficiency_curve_charge_efficiency"].values, dtype=float),
                    coords={"battery_curve_point": battery_curve_point},
                    dims=("battery_curve_point",),
                ),
                "battery_efficiency_curve_discharge_efficiency": xr.DataArray(
                    np.asarray(curve_ds["battery_efficiency_curve_discharge_efficiency"].values, dtype=float),
                    coords={"battery_curve_point": battery_curve_point},
                    dims=("battery_curve_point",),
                ),
                "battery_charge_loss_slope": xr.DataArray(
                    np.asarray(curve_ds["battery_charge_loss_slope"].values, dtype=float),
                    coords={"battery_loss_segment": battery_loss_segment},
                    dims=("battery_loss_segment",),
                ),
                "battery_charge_loss_intercept": xr.DataArray(
                    np.asarray(curve_ds["battery_charge_loss_intercept"].values, dtype=float),
                    coords={"battery_loss_segment": battery_loss_segment},
                    dims=("battery_loss_segment",),
                ),
                "battery_discharge_loss_slope": xr.DataArray(
                    np.asarray(curve_ds["battery_discharge_loss_slope"].values, dtype=float),
                    coords={"battery_loss_segment": battery_loss_segment},
                    dims=("battery_loss_segment",),
                ),
                "battery_discharge_loss_intercept": xr.DataArray(
                    np.asarray(curve_ds["battery_discharge_loss_intercept"].values, dtype=float),
                    coords={"battery_loss_segment": battery_loss_segment},
                    dims=("battery_loss_segment",),
                ),
            }
        )
        battery_curve_path = str(curve_path)
    genfuel_path = paths.inputs_dir / "generator.yaml"
    gen_ds, fuel_ds, curve_ds, genfuel_meta = _load_generator_and_fuel_yaml(
        genfuel_path,
        inputs_dir=paths.inputs_dir,
        scenario_coord=scenario_coord,
        year_coord=year_coord,
        inv_step_coord=inv_step_coord,
    )

    data = merge_optional_datasets(
        data,
        ren_params_ds,
        bat_params_ds,
        gen_ds,
        fuel_ds,
        curve_ds,
        battery_curve_ds,
        battery_calendar_curve_ds,
        compat="override",
    )

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

        data = merge_optional_datasets(data, *to_merge, compat="override", join="exact")

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
            "integer_sizing_enabled": uc_enabled,
            "unit_commitment_semantics": "integer_sizing_only",
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
                "battery_efficiency_curve_csv": battery_curve_path,
                "battery_calendar_fade_curve_csv": battery_calendar_curve_path,
                "generator_yaml": str(genfuel_path),
            },
        }
    )

    data.attrs["settings"].setdefault("generator", {})
    data.attrs["settings"]["generator"]["partial_load_modelling_enabled"] = bool(
        genfuel_meta.get("partial_load_modelling_enabled", False)
    )
    data.attrs["settings"]["generator"]["efficiency_curve_file"] = genfuel_meta.get("efficiency_curve_file")
    data.attrs["settings"]["generator"]["label"] = genfuel_meta.get("generator_label", "Generator")
    data.attrs["settings"]["fuel"] = {"label": genfuel_meta.get("fuel_label", "Fuel")}
    data.attrs["settings"]["battery_label"] = bat_params_ds.attrs.get("battery_label", "Battery")
    data.attrs["settings"]["battery_model"] = {
        "loss_model": battery_loss_model,
        "efficiency_curve_csv": battery_curve_path,
        "degradation_model": battery_degradation_settings,
    }
    data.attrs["settings"]["battery_model"]["exogenous_capacity_degradation_active"] = bool(
        active_battery_exogenous_degradation
    )
    data.attrs["settings"]["battery_model"]["exogenous_capacity_degradation_ignored"] = bool(
        ignored_exogenous_battery_degradation
    )

    return data


def initialize_data(project_name: str, sets: xr.Dataset) -> xr.Dataset:
    return load_project_dataset(project_name, sets, mode="multi_year")
