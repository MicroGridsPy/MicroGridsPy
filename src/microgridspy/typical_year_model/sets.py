from __future__ import annotations

import xarray as xr

from microgridspy.errors import InputValidationError
from microgridspy.io.formulation import TYPICAL_YEAR
from microgridspy.io.input_labels import renewable_labels_from_yaml
from microgridspy.io.jsonio import read_json
from microgridspy.io.utils import project_paths


def initialize_sets(project_name: str) -> xr.Dataset:
    """
    Initialize model sets (dimensions) from formulation.json.

    Typical-year:
      - period: 0..8759
      - scenario: scenario labels
      - res_source: renewable source ids (res_1, res_2, ...)
    """
    paths = project_paths(project_name)
    formulation = read_json(paths.formulation_json)

    # --- formulation flags ---
    formulation_mode = str(formulation.get("core_formulation", TYPICAL_YEAR))
    if formulation_mode != TYPICAL_YEAR:
        raise InputValidationError(f"This initializer is for {TYPICAL_YEAR} projects only.")

    # --- scenarios ---
    ms = formulation.get("multi_scenario", {}) or {}
    ms_enabled = bool(ms.get("enabled", False))

    if ms_enabled:
        scenario_labels = list(ms.get("scenario_labels") or [])
        n_scen = int(ms.get("n_scenarios", len(scenario_labels)))
        if not scenario_labels:
            scenario_labels = [f"scenario_{i + 1}" for i in range(n_scen)]
    else:
        scenario_labels = ["scenario_1"]
        n_scen = 1

    # --- renewables ---
    components = formulation.get("system_configuration", {}) or {}
    renewables_yaml = renewable_labels_from_yaml(paths.inputs_dir / "renewables.yaml")
    resource_labels = list(renewables_yaml.get("resources") or components.get("resources") or [])
    n_res = int(components.get("n_sources", len(resource_labels) or 1))
    if not resource_labels:
        resource_labels = [f"Resource_{i + 1}" for i in range(n_res)]
    elif len(resource_labels) < n_res:
        resource_labels = resource_labels + [
            f"Resource_{i + 1}" for i in range(len(resource_labels), n_res)
        ]
    elif len(resource_labels) > n_res:
        resource_labels = resource_labels[:n_res]

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
