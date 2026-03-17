
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import math
import xarray as xr

from core.io.utils import project_paths


class InputValidationError(RuntimeError):
    pass


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise InputValidationError(f"Missing required file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise InputValidationError(f"Cannot parse JSON: {path}\nerror: {e}")


def _safe_int(v: Any, *, name: str) -> int:
    try:
        iv = int(v)
    except Exception:
        raise InputValidationError(f"Invalid int for '{name}': {v!r}")
    if iv <= 0:
        raise InputValidationError(f"'{name}' must be > 0, got {iv}")
    return iv


def initialize_sets(project_name: str) -> xr.Dataset:
    """
    Initialize model sets (dimensions) from formulation.json for dynamic multi-year formulation.

    Dynamic formulation:
      - period: 0..8759 (typical-year hours)
      - year: 1..n_years
      - inv_step: 1..n_steps (or [1] if capacity_expansion disabled)
      - scenario: scenario labels
      - resource: resource labels

    Also returns step metadata and mappings:
      - inv_step_start_year[inv_step]
      - inv_step_end_year[inv_step]
      - inv_step_len_years[inv_step]
      - year_inv_step[year]  (maps year -> inv_step)
      - inv_active_in_year[inv_step, year]  (availability mask)
    """
    paths = project_paths(project_name)
    formulation = _read_json(paths.formulation_json)

    # --- formulation flags ---
    formulation_mode = str(formulation.get("core_formulation", "steady_state"))
    if formulation_mode != "dynamic":
        raise InputValidationError("This initializer is for dynamic formulation only.")

    # --- scenarios ---
    ms = formulation.get("multi_scenario", {}) or {}
    ms_enabled = bool(ms.get("enabled", False))

    if ms_enabled:
        scenario_labels = list(ms.get("scenario_labels") or [])
        n_scen = int(ms.get("n_scenarios", len(scenario_labels)))
        if not scenario_labels:
            scenario_labels = [f"scenario_{i+1}" for i in range(n_scen)]
    else:
        scenario_labels = ["scenario_1"]
        n_scen = 1

    # --- renewables/resources ---
    components = formulation.get("system_configuration", {}) or {}
    resource_labels = list(components.get("resources") or [])
    n_res = int(components.get("n_sources", len(resource_labels)))
    if not resource_labels:
        resource_labels = [f"res_{i+1}" for i in range(n_res)]

    # --- dynamic horizon / investment steps ---
    # Recommended keys (choose one convention and keep it stable)
    #  - time_horizon_years: int
    #  - capacity_expansion: {"enabled": bool, "step_years": int}

    # horizon
    n_years = _safe_int(formulation.get("time_horizon_years", 1), name="time_horizon_years")

    # year labels (use the label as a START YEAR if possible; otherwise fall back to 1..n_years)
    start_year_label = str(formulation.get("start_year_label", "")).strip()
    start_year_int = int(start_year_label)
    year_labels = list(range(start_year_int, start_year_int + n_years))  # e.g. 2026..2029

    # capacity expansion and investment steps
    capexp_enabled = bool(formulation.get("capacity_expansion", False))

    if capexp_enabled:
        step_years_list = formulation.get("investment_steps_years") or []
        step_years_list = [int(v) for v in step_years_list]
        n_steps = len(step_years_list)
        inv_steps = list(range(1, n_steps + 1))  # 1-based

        # step start/end in *year labels* (same type as year_labels)
        step_start, step_end = [], []
        cursor_idx = 0
        for dur in step_years_list:
            s = year_labels[cursor_idx]
            e = year_labels[cursor_idx + dur - 1]
            step_start.append(s)
            step_end.append(e)
            cursor_idx += dur

        step_len = step_years_list[:]  # already durations in years

        # year -> inv_step mapping (same length as year_labels)
        year_to_step = []
        for s_idx, dur in enumerate(step_years_list, start=1):
            year_to_step.extend([s_idx] * dur)

    else:
        n_steps = 1
        inv_steps = [1]
        step_start = [year_labels[0]]
        step_end = [year_labels[-1]]
        step_len = [n_years]
        year_to_step = [1] * n_years

    # availability mask: capacity built in step s is available in year y if y >= step_start[s]
    inv_active = []
    for s_idx in range(n_steps):
        s_start = step_start[s_idx]
        inv_active.append([1 if y >= s_start else 0 for y in year_labels])

    # --- define dimensions explicitly ---------------------------------------------
    ds = xr.Dataset(
        coords=dict(
            period=("period", list(range(8760))),  # typical-year hours
            year=("year", year_labels),            # labelled years (e.g. 2026..)
            inv_step=("inv_step", inv_steps),
            scenario=("scenario", scenario_labels),
            resource=("resource", resource_labels),
        )
    )

    # --- store mappings / step metadata -------------------------------------------
    ds["inv_step_start_year"] = xr.DataArray(step_start, dims=("inv_step",))
    ds["inv_step_end_year"] = xr.DataArray(step_end, dims=("inv_step",))
    ds["inv_step_len_years"] = xr.DataArray(step_len, dims=("inv_step",))

    ds["year_inv_step"] = xr.DataArray(year_to_step, dims=("year",))

    ds["inv_active_in_year"] = xr.DataArray(
        inv_active,
        dims=("inv_step", "year"),
        coords={"inv_step": ds.coords["inv_step"], "year": ds.coords["year"]},
    )

    # --- store settings -----------------------------------------------------------
    ds.attrs["settings"] = {
        "project_name": project_name,
        "formulation": formulation_mode,
        "n_periods": 8760,
        "n_years": n_years,
        "year_labels": year_labels,
        "n_inv_steps": n_steps,
        "investment_steps_years": step_len,  # list[int]
        "capacity_expansion": {"enabled": capexp_enabled, "investment_steps_years": step_len},
        "n_scenarios": n_scen,
        "scenarios": scenario_labels,
        "n_res_sources": n_res,
        "resources": resource_labels,
    }

    print(f"Initialized dynamic sets for project '{project_name}': {ds.dims}")
    return ds
