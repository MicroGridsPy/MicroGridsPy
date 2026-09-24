"""Reading a solved run back out of Streamlit session state.

The Optimization page stores what it solved in ``st.session_state``; the Results
page reads it back through these helpers. They are GUI state accessors, which is
why they live in `microgridspy.app` and not in the export layer.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import xarray as xr

from microgridspy.export.multi_year_results import MultiYearResults
from microgridspy.export.results_bundle import ResultsBundle
from microgridspy.export.typical_year_results import TypicalYearResults


def _dataset_project_name(data: Any) -> str | None:
    if not isinstance(data, xr.Dataset):
        return None
    settings = (data.attrs or {}).get("settings", {})
    if not isinstance(settings, dict):
        return None
    raw = settings.get("project_name", None)
    return str(raw) if raw is not None else None


def get_results_bundle_from_session(
    session_state: Mapping[str, Any], *, active_project: str | None = None
) -> ResultsBundle | None:
    """Return the solved-run bundle the Optimization page stored, if it is current."""
    raw = session_state.get("gp_results_bundle")
    if not isinstance(raw, ResultsBundle):
        return None
    if active_project is not None and _dataset_project_name(raw.data) not in {
        None,
        active_project,
    }:
        return None
    model_obj = session_state.get("gp_model_obj")
    model_sol = getattr(getattr(model_obj, "model", None), "solution", None)
    if isinstance(model_sol, xr.Dataset):
        raw.solution = model_sol
    return raw


def get_typical_year_results_from_session(
    session_state: Mapping[str, Any],
    *,
    active_project: str | None = None,
) -> TypicalYearResults | None:
    """Return the typical-year results the Optimization page stored, if they are current."""
    raw = session_state.get("gp_typical_year_results")
    if not isinstance(raw, TypicalYearResults):
        return None
    raw_project = str(raw.metadata.get("project_name") or raw.project_name)
    if active_project is not None and raw_project not in {None, "", active_project}:
        return None
    return raw


def get_multi_year_results_from_session(
    session_state: Mapping[str, Any],
    *,
    active_project: str | None = None,
) -> MultiYearResults | None:
    """Return the multi-year results the Optimization page stored, if they are current."""
    raw = session_state.get("gp_multi_year_results")
    if not isinstance(raw, MultiYearResults):
        return None
    raw_project = str(raw.metadata.get("project_name") or raw.project_name)
    if active_project is not None and raw_project not in {None, "", active_project}:
        return None
    return raw
