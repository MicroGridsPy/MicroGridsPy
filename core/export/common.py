from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import pandas as pd
import xarray as xr

from core.export.results_bundle import ResultsBundle
from core.io.utils import project_paths


class InputValidationError(RuntimeError):
    pass


def safe_float(value: Any) -> float:
    """Best-effort float conversion for Python, numpy, and xarray scalar-like values."""
    try:
        if value is None:
            return float("nan")
        if hasattr(value, "item"):
            return float(value.item())
        return float(value)
    except Exception:
        return float("nan")


def get_var_solution(
    *,
    vars_dict: Optional[Dict[str, Any]],
    solution: Optional[xr.Dataset],
    name: str,
    prefer_solution_dataset: bool = True,
) -> Optional[xr.DataArray]:
    """Resolve a solved variable from the solution dataset or the linopy variable dict."""
    if prefer_solution_dataset and isinstance(solution, xr.Dataset) and name in solution:
        da = solution[name]
        if isinstance(da, xr.DataArray):
            return da

    if isinstance(vars_dict, dict):
        var = vars_dict.get(name, None)
        try:
            if var is not None and hasattr(var, "solution") and isinstance(var.solution, xr.DataArray):
                return var.solution
        except Exception:
            pass

    if not prefer_solution_dataset and isinstance(solution, xr.Dataset) and name in solution:
        da = solution[name]
        if isinstance(da, xr.DataArray):
            return da

    return None


def require_data_array(name: str, da: Optional[xr.DataArray]) -> xr.DataArray:
    """Require that a solved variable resolves to an xarray.DataArray."""
    if not isinstance(da, xr.DataArray):
        raise InputValidationError(f"Missing solved variable '{name}' in vars/solution.")
    return da


def get_bundle_formulation(bundle: ResultsBundle) -> str:
    """Return formulation mode from bundle data settings."""
    data = bundle.data
    if not isinstance(data, xr.Dataset):
        return "steady_state"
    settings = (data.attrs or {}).get("settings", {})
    return str(settings.get("formulation", "steady_state"))


def ensure_results_dir(project_name: str, *, suffix: str | None = None) -> Path:
    """Return and create the export output directory for a project."""
    out_dir = project_paths(project_name).results_dir
    if suffix:
        out_dir = out_dir / suffix
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_csv_outputs(out_dir: Path, outputs: Mapping[str, pd.DataFrame]) -> Dict[str, str]:
    """Write multiple DataFrames to CSV in a directory and return path metadata."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: Dict[str, str] = {"out_dir": str(out_dir)}
    for filename, df in outputs.items():
        path = out_dir / filename
        df.to_csv(path, index=False)
        key = filename.replace(".csv", "").replace("-", "_") + "_csv"
        written[key] = str(path)
    return written
