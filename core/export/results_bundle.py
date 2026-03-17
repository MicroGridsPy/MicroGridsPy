from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import xarray as xr


@dataclass
class ResultsBundle:
    formulation_mode: Optional[str] = None
    sets: Optional[xr.Dataset] = None
    data: Optional[xr.Dataset] = None
    vars: Optional[Dict[str, Any]] = None
    solution: Optional[xr.Dataset] = None
    objective_value: Optional[float] = None
    status: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_results_bundle(
    *,
    sets: Optional[xr.Dataset],
    data: Optional[xr.Dataset],
    vars: Optional[Dict[str, Any]],
    model_obj: Any = None,
    solution: Optional[xr.Dataset] = None,
    solution_summary: Optional[Dict[str, Any]] = None,
    solver: Optional[str] = None,
) -> ResultsBundle:
    sol = solution
    if not isinstance(sol, xr.Dataset) and model_obj is not None:
        m = getattr(model_obj, "model", None)
        if m is not None and isinstance(getattr(m, "solution", None), xr.Dataset):
            sol = m.solution

    obj = None
    status = None
    if isinstance(solution_summary, dict):
        obj = solution_summary.get("objective_value", None)
        status = solution_summary.get("status", None)

    if obj is None and isinstance(sol, xr.Dataset):
        raw = sol.attrs.get("objective_value", None)
        try:
            if raw is not None:
                obj = float(raw)
        except Exception:
            pass

    meta: Dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if solver is not None:
        meta["solver"] = solver

    formulation_mode = None
    if isinstance(data, xr.Dataset):
        s = (data.attrs or {}).get("settings", {})
        if isinstance(s, dict):
            formulation_mode = str(s.get("formulation", "")) or None

    return ResultsBundle(
        formulation_mode=formulation_mode,
        sets=sets if isinstance(sets, xr.Dataset) else None,
        data=data if isinstance(data, xr.Dataset) else None,
        vars=vars if isinstance(vars, dict) else None,
        solution=sol if isinstance(sol, xr.Dataset) else None,
        objective_value=obj,
        status=status,
        metadata=meta,
    )
