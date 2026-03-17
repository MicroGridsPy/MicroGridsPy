# generation_planning/modeling/sets.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
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


def initialize_sets(project_name: str) -> xr.Dataset:
    """
    Initialize model sets (dimensions) from formulation.json.

    Typical-year (steady_state):
      - period: 0..8759
      - scenario: scenario labels
      - res_source: renewable source ids (res_1, res_2, ...)
    """
    paths = project_paths(project_name)
    formulation = _read_json(paths.formulation_json)

    # --- formulation flags ---
    formulation_mode = str(formulation.get("core_formulation", "steady_state"))
    if formulation_mode != "steady_state":
        raise InputValidationError("This initializer is for steady_state only.")

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

    # --- renewables ---
    components = formulation.get("system_configuration", {}) or {}
    resource_labels = list(components.get("resources") or [])
    n_res = int(components.get("n_sources", len(resource_labels)))

    # --- define dimensions explicitly ---
    ds = xr.Dataset(
        coords=dict(
            period=("period", list(range(8760))),
            scenario=("scenario", scenario_labels),
            resource=("resource", resource_labels),
        )
    )

    # --- store minimal settings ---
    ds.attrs["settings"] = {
        "project_name": project_name,
        "formulation": formulation_mode,
        "n_periods": 8760,
        "n_scenarios": n_scen,
        "scenarios": scenario_labels,
        "n_res_sources": n_res,
        "resources": resource_labels,
    }

    print(f"Initialized sets for project '{project_name}': {ds.dims}")
    return ds
