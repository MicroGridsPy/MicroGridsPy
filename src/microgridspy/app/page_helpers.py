from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type

import streamlit as st
import xarray as xr


def read_json_file(
    path: Path,
    *,
    error_cls: Type[Exception] = RuntimeError,
    missing_prefix: str = "Missing required file",
    parse_prefix: str = "Cannot parse JSON file",
) -> Dict[str, Any]:
    """Read a JSON file and raise a caller-selected exception on failure."""
    if not path.exists():
        raise error_cls(f"{missing_prefix}: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise error_cls(f"{parse_prefix}: {path}\nerror: {exc}") from exc


def resolve_active_project_from_session() -> Tuple[str, Path]:
    """Resolve the active project root from Streamlit session state or stop the page."""
    if "project_path" not in st.session_state:
        st.warning("Please create or load a project first.")
        st.stop()

    project_root = Path(str(st.session_state["project_path"]))
    if not project_root.exists():
        st.error(f"Configured project path does not exist: {project_root}")
        st.stop()

    project_name = project_root.name
    st.session_state["active_project"] = project_name
    return project_name, project_root


def get_dataset_settings(data_ds: Optional[xr.Dataset]) -> Dict[str, Any]:
    """Safely return dataset settings from attrs."""
    if not isinstance(data_ds, xr.Dataset):
        return {}
    settings = (data_ds.attrs or {}).get("settings", {})
    return settings if isinstance(settings, dict) else {}


def get_nested_flag(settings: Dict[str, Any], path: Tuple[str, ...], default: bool = False) -> bool:
    """Safely read a nested boolean-ish flag from a dict."""
    current: Any = settings
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return bool(current)


def safe_float(value: Any) -> float:
    """Best-effort float conversion that tolerates numpy/xarray scalars."""
    try:
        if value is None:
            return float("nan")
        if hasattr(value, "item"):
            return float(value.item())
        return float(value)
    except Exception:
        return float("nan")
