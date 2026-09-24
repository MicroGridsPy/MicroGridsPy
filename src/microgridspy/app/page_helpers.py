from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import xarray as xr


def resolve_active_project_from_session() -> tuple[str, Path]:
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


def get_dataset_settings(data_ds: xr.Dataset | None) -> dict[str, Any]:
    """Safely return dataset settings from attrs."""
    if not isinstance(data_ds, xr.Dataset):
        return {}
    settings = (data_ds.attrs or {}).get("settings", {})
    return settings if isinstance(settings, dict) else {}


def get_nested_flag(settings: dict[str, Any], path: tuple[str, ...], default: bool = False) -> bool:
    """Safely read a nested boolean-ish flag from a dict."""
    current: Any = settings
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return bool(current)
