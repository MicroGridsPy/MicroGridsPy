# generation_planning/pages/optimization.py
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import xarray as xr

from core.typical_year_model.model import SteadyStateModel
from core.multi_year_model.model import MultiYearModel
from core.export.results_bundle import build_results_bundle
from core.io.utils import project_paths
from core.visualization.page_helpers import get_dataset_settings, read_json_file

class InputValidationError(RuntimeError):
    pass

def _as_str(x: Any, *, name: str, default: str = "") -> str:
    """Convert x to str, with default if None. Raise InputValidationError on failure."""
    if x is None:
        return default
    try:
        return str(x)
    except Exception as e:
        raise InputValidationError(f"Invalid value for '{name}': {x!r} (error: {e})")
    
# =============================================================================
# Defaults / Session keys
# =============================================================================
KEYS = {
    "active_project": "active_project",  # set by project_setup.py
    "solver": "gp_solver",
    "use_custom_lp": "gp_use_custom_lp",
    "custom_lp": "gp_custom_lp",
    "use_custom_log": "gp_use_custom_log",
    "custom_log": "gp_custom_log",

    # solver params
    "highs_time_limit": "gp_highs_time_limit",
    "highs_mip_rel_gap": "gp_highs_mip_rel_gap",
    "highs_threads": "gp_highs_threads",
    "highs_presolve": "gp_highs_presolve",

    "gurobi_time_limit": "gp_gurobi_time_limit",
    "gurobi_mip_gap": "gp_gurobi_mip_gap",
    "gurobi_threads": "gp_gurobi_threads",
    "gurobi_presolve": "gp_gurobi_presolve",

    # outputs
    "solution": "gp_solution",
    "sets": "gp_sets",
    "data": "gp_data",
    "vars": "gp_vars",
    "solution_summary": "gp_solution_summary",
    "model_obj": "gp_model_obj",
    "log_path": "gp_log_path",
    "results_bundle": "gp_results_bundle",
}

RESULT_STATE_KEYS = (
    KEYS["solution"],
    KEYS["solution_summary"],
    KEYS["sets"],
    KEYS["data"],
    KEYS["vars"],
    KEYS["model_obj"],
    KEYS["log_path"],
    KEYS["results_bundle"],
)


def _init_defaults() -> None:
    defaults = {
        KEYS["solver"]: "highs",
        KEYS["use_custom_lp"]: False,
        KEYS["custom_lp"]: "",
        KEYS["use_custom_log"]: False,
        KEYS["custom_log"]: "",

        # HiGHS
        KEYS["highs_time_limit"]: 0,
        KEYS["highs_mip_rel_gap"]: 0.0,
        KEYS["highs_threads"]: 0,
        KEYS["highs_presolve"]: True,

        # Gurobi
        KEYS["gurobi_time_limit"]: 0,
        KEYS["gurobi_mip_gap"]: 0.0,
        KEYS["gurobi_threads"]: 0,
        KEYS["gurobi_presolve"]: -1,
    }
    for k, v in defaults.items():
        if k not in st.session_state or st.session_state[k] is None:
            st.session_state[k] = v


def _reset_result_state() -> None:
    for key in RESULT_STATE_KEYS:
        st.session_state[key] = None


# =============================================================================
# Helpers (solver + I/O)
# =============================================================================
def _solver_params(solver: str) -> Dict[str, Any]:
    """Return solver kwargs for linopy.Model.solve()."""
    if solver == "gurobi":
        p: Dict[str, Any] = {}
        tl = int(st.session_state[KEYS["gurobi_time_limit"]])
        if tl > 0:
            p["TimeLimit"] = tl
        gap = float(st.session_state[KEYS["gurobi_mip_gap"]])
        if gap > 0:
            p["MIPGap"] = gap
        th = int(st.session_state[KEYS["gurobi_threads"]])
        if th > 0:
            p["Threads"] = th
        p["Presolve"] = int(st.session_state[KEYS["gurobi_presolve"]])
        return p

    p: Dict[str, Any] = {}
    tl = int(st.session_state[KEYS["highs_time_limit"]])
    if tl > 0:
        p["time_limit"] = float(tl)
    gap = float(st.session_state[KEYS["highs_mip_rel_gap"]])
    if gap > 0:
        p["mip_rel_gap"] = gap
    th = int(st.session_state[KEYS["highs_threads"]])
    if th > 0:
        p["threads"] = th
    p["presolve"] = "on" if bool(st.session_state[KEYS["highs_presolve"]]) else "off"
    return p


def _default_log_path(project_name: str, solver: str) -> Path:
    paths = project_paths(project_name)
    return paths.logs_dir / f"{solver}_solve.log"


def _validate_optional_paths(project_name: str, solver: str) -> Tuple[Optional[Path], Path, bool]:
    lp_path = None
    log_path = _default_log_path(project_name, solver)
    ok = True

    if bool(st.session_state[KEYS["use_custom_lp"]]):
        raw = str(st.session_state[KEYS["custom_lp"]]).strip()
        if not raw:
            st.error("Custom LP path is enabled but empty.")
            ok = False
        else:
            lp_path = Path(raw)
            if lp_path.suffix.lower() not in (".lp", ".mps"):
                st.error("Custom problem file must end with .lp or .mps.")
                ok = False

    if bool(st.session_state[KEYS["use_custom_log"]]):
        raw = str(st.session_state[KEYS["custom_log"]]).strip()
        if not raw:
            st.error("Custom log path is enabled but empty.")
            ok = False
        else:
            log_path = Path(raw)
            if log_path.suffix.lower() not in (".log", ".txt"):
                st.error("Custom log file should end with .log or .txt.")
                ok = False

    return lp_path, log_path, ok


# =============================================================================
# Debug helpers (UI-only)
# =============================================================================
def _safe_preview(values, n: int = 8):
    """Return a JSON-safe preview list."""
    try:
        arr = np.asarray(values)
        flat = arr.ravel()
        return flat[:n].tolist()
    except Exception:
        try:
            return list(values)[:n]
        except Exception:
            return str(values)


def _show_xr_dataset_debug(ds: xr.Dataset, title: str, coord_preview_n: int = 8) -> None:
    st.markdown(f"### {title}")

    if ds is None:
        st.info("Not available yet.")
        return

    with st.expander("Coordinates & dimensions", expanded=False):
        if not ds.coords:
            st.info("No coordinates.")
        else:
            coord_info = {}
            for cname, c in ds.coords.items():
                try:
                    coord_info[cname] = {
                        "len": int(c.size),
                        "dims": list(c.dims),
                        "preview": _safe_preview(c.values, n=coord_preview_n),
                    }
                except Exception as e:
                    coord_info[cname] = {"error": str(e)}
            st.json(coord_info)

        st.markdown("**Dimensions (sizes)**")
        st.json({k: int(v) for k, v in ds.sizes.items()})

    with st.expander("Attributes", expanded=False):
        attrs = dict(ds.attrs or {})
        settings = attrs.pop("settings", None)
        if settings is not None:
            st.markdown("**settings**")
            st.json(settings)
        if attrs:
            st.markdown("**other attrs**")
            st.json(attrs)
        if settings is None and not attrs:
            st.info("No attributes stored.")

    with st.expander("Data variables (overview)", expanded=False):
        if len(ds.data_vars) == 0:
            st.info("No data variables.")
        else:
            rows = []
            for vname, da in ds.data_vars.items():
                rows.append(
                    {
                        "var": vname,
                        "dims": ", ".join(da.dims),
                        "shape": str(tuple(da.shape)),
                        "dtype": str(da.dtype),
                    }
                )
            st.dataframe(pd.DataFrame(rows), width="stretch")


def _render_variables_debug(data_ds: Optional[xr.Dataset], vars_dict: Any) -> None:
    """Minimal vars inspector: name, dims, expected type, coords preview."""
    st.markdown("### Variables")

    with st.expander("Variables dictionary (dims/shape)", expanded=False):
        if vars_dict is None:
            st.info("Not available yet.")
            return
        if not isinstance(vars_dict, dict) or len(vars_dict) == 0:
            st.warning("vars_dict is empty or not a dict.")
            return

        settings = get_dataset_settings(data_ds)
        uc_enabled = bool(settings.get("unit_commitment", False))
        st.caption(f"unit_commitment (from data.attrs['settings']): {uc_enabled}")

        def _expected_vartype(var_name: str) -> str:
            if not uc_enabled:
                return "Continuous"
            if var_name in {"res_units", "battery_units", "generator_units"}:
                return "Integer"
            return "Continuous"

        rows = []
        for name, var in vars_dict.items():
            try:
                da = getattr(var, "data", None)
                if da is None:
                    rows.append(
                        {
                            "var": name,
                            "dims": "(no .data)",
                            "expected_type": _expected_vartype(name),
                            "coords_preview": "",
                        }
                    )
                    continue

                dims = list(getattr(da, "dims", ()))
                coords_preview = {
                    d: _safe_preview(da.coords[d].values, n=4) if d in da.coords else "-"
                    for d in dims
                }

                rows.append(
                    {
                        "var": name,
                        "dims": ", ".join(dims) if dims else "(scalar)",
                        "expected_type": _expected_vartype(name),
                        "coords_preview": coords_preview,
                    }
                )
            except Exception as e:
                rows.append(
                    {
                        "var": name,
                        "dims": "ERROR",
                        "expected_type": "?",
                        "coords_preview": f"{e}",
                    }
                )

        st.dataframe(pd.DataFrame(rows), width="stretch")


def _render_constraints_debug(model_obj: Any) -> None:
    """
    Debug viewer for linopy constraints (works with SteadyStateModel or a raw lp.Model).
    """
    st.markdown("### Constraints")

    if model_obj is None:
        st.info("Model not available yet. Run at least the 'build' step (and store the model in session state).")
        return

    lp_model = getattr(model_obj, "model", None)
    if lp_model is None:
        lp_model = model_obj if hasattr(model_obj, "constraints") else None

    if lp_model is None or not hasattr(lp_model, "constraints"):
        st.warning("Could not find a linopy model with constraints on this object.")
        return

    cons = lp_model.constraints
    if cons is None or len(cons) == 0:
        st.info("No constraints found in the model yet.")
        return

    def _count_rows(con_obj: Any) -> Optional[int]:
        try:
            da = getattr(con_obj, "data", None)
            if da is not None:
                return int(np.prod(getattr(da, "shape", (1,)) or (1,)))
        except Exception:
            pass
        for attr in ("lhs", "rhs"):
            try:
                da = getattr(con_obj, attr, None)
                if da is not None:
                    return int(np.prod(getattr(da, "shape", (1,)) or (1,)))
            except Exception:
                continue
        return None

    def _dims_and_coords_preview(con_obj: Any, n: int = 4) -> Tuple[str, Dict[str, Any]]:
        da = getattr(con_obj, "data", None)
        if da is None:
            da = getattr(con_obj, "lhs", None) or getattr(con_obj, "rhs", None)

        if da is None or not hasattr(da, "dims"):
            return "(unknown)", {}

        dims = list(da.dims) if da.dims else []
        dims_str = ", ".join(dims) if dims else "(scalar)"

        coords_preview: Dict[str, Any] = {}
        try:
            for d in dims:
                coords_preview[d] = _safe_preview(da.coords[d].values, n=n) if d in da.coords else "-"
        except Exception as e:
            coords_preview = {"error": str(e)}

        return dims_str, coords_preview

    rows = []
    for cname, cobj in cons.items():
        try:
            dims_str, coords_preview = _dims_and_coords_preview(cobj, n=4)
            cnt = _count_rows(cobj)
            rows.append(
                {
                    "constraint": str(cname),
                    "count": cnt if cnt is not None else "",
                    "dims": dims_str,
                    "coords_preview": coords_preview,
                }
            )
        except Exception as e:
            rows.append({"constraint": str(cname), "count": "", "dims": "ERROR", "coords_preview": str(e)})

    with st.expander("Constraints overview (name / count / dims)", expanded=False):
        st.dataframe(pd.DataFrame(rows), width="stretch")

    with st.expander("Inspect a constraint (raw)", expanded=False):
        names = [r["constraint"] for r in rows]
        if not names:
            st.info("No constraints to inspect.")
            return
        pick = st.selectbox("Select constraint", options=names, index=0)
        try:
            st.write(cons[pick])
        except Exception as e:
            st.error(f"Could not render constraint '{pick}': {e}")

def _as_float(x: Any) -> Optional[float]:
    """Best-effort float conversion for numpy/xarray scalars."""
    try:
        if x is None:
            return None
        if isinstance(x, (float, int)):
            return float(x)
        if hasattr(x, "item"):  # numpy scalar, 0-d array
            return float(x.item())
        # xarray DataArray scalar
        if isinstance(x, xr.DataArray) and x.ndim == 0:
            return float(x.values.item())
        return float(x)
    except Exception:
        return None


def _status_to_str(status_obj: Any) -> Optional[str]:
    """
    Turn linopy Status/Result status into a readable string.
    Typical: ('ok','optimal') or Status(status='ok', termination_condition='optimal')
    """
    if status_obj is None:
        return None

    # If it's already string-like
    if isinstance(status_obj, str):
        return status_obj

    # tuple-like: ('ok','optimal')
    try:
        if isinstance(status_obj, tuple) and len(status_obj) >= 2:
            return f"{status_obj[0]} / {status_obj[1]}"
    except Exception:
        pass

    # Status dataclass-like: has .status and .termination_condition
    try:
        s = getattr(status_obj, "status", None)
        tc = getattr(status_obj, "termination_condition", None)
        if s is not None or tc is not None:
            return f"{s} / {tc}"
    except Exception:
        pass

    # Fallback repr
    try:
        return str(status_obj)
    except Exception:
        return None


def _extract_solution_summary(m: Any) -> Dict[str, Any]:
    """
    Extract minimal results from a solved linopy.Model or a wrapper object.

    Returns:
      - status (str|None)
      - objective_value (float|None)
    """
    out: Dict[str, Any] = {
        "status": None,
        "objective_value": None,
    }

    lp: Any = m

    # ------------------------------------------------------------------
    # 1) Status
    # ------------------------------------------------------------------
    # Prefer last solve "result" if available on wrapper
    # but in many apps you don't store it; so try common places.
    result = getattr(m, "result", None) or getattr(lp, "result", None)
    if result is not None:
        out["status"] = _status_to_str(getattr(result, "status", result))
    else:
        # Some versions store status on lp.status
        out["status"] = _status_to_str(getattr(lp, "status", None))

    # ------------------------------------------------------------------
    # 2) Objective value
    # ------------------------------------------------------------------
    # Best practice per docs: m.objective.value exists after solve.
    obj = getattr(lp, "objective", None)
    if obj is not None:
        out["objective_value"] = _as_float(getattr(obj, "value", None))

    # Fallbacks: sometimes objective is inside Result.solution
    if out["objective_value"] is None and result is not None:
        sol = getattr(result, "solution", None)
        if sol is not None:
            out["objective_value"] = _as_float(getattr(sol, "objective", None))

    # Another fallback: some linopy versions expose objective in lp.solution attrs (less common)
    if out["objective_value"] is None:
        sol_ds = getattr(lp, "solution", None)
        if isinstance(sol_ds, xr.Dataset):
            # Sometimes stored as attribute; keep it defensive
            out["objective_value"] = _as_float(sol_ds.attrs.get("objective_value"))  # optional

    return out

def _render_minimal_results(solution_summary: Optional[Dict[str, Any]]) -> None:
    st.subheader("Results (minimal)")

    if not solution_summary:
        st.info("No results yet. Build and solve the model first.")
        return

    obj = solution_summary.get("objective_value", None)
    status = solution_summary.get("status", None) or "solved (check logs)"

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Status", str(status))
    with c2:
        st.metric("Objective value", f"{obj:.4g}" if isinstance(obj, (int, float)) else "n/a")


def _render_solver_log(log_path_value: Any) -> None:
    with st.expander("Solver Log", expanded=False):
        if not log_path_value:
            st.info("No solver log available for this run.")
            return
        p = Path(str(log_path_value))
        st.write(f"Path: {p}")
        if not p.exists() or not p.is_file():
            st.warning("Log path does not exist.")
            return
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            st.error(f"Could not read solver log: {e}")
            return
        st.text_area("Log content", value=txt, height=260)


def _build_model(project_name: str, formulation_mode: str) -> SteadyStateModel | MultiYearModel:
    if formulation_mode == "steady_state":
        return SteadyStateModel(project_name=project_name)
    if formulation_mode == "dynamic":
        return MultiYearModel(project_name=project_name)
    raise InputValidationError(f"Unknown formulation '{formulation_mode}' in formulation.json")


def _store_solve_outputs(
    *,
    model: SteadyStateModel | MultiYearModel,
    solution: Any,
    solver: str,
    fallback_log_path: Path,
) -> None:
    st.session_state[KEYS["solution"]] = solution
    st.session_state[KEYS["sets"]] = model.sets
    st.session_state[KEYS["data"]] = model.data
    st.session_state[KEYS["vars"]] = model.vars
    st.session_state[KEYS["model_obj"]] = model
    st.session_state[KEYS["log_path"]] = str(model._last_log_path) if model._last_log_path else str(fallback_log_path)
    st.session_state[KEYS["solution_summary"]] = _extract_solution_summary(model)
    st.session_state[KEYS["results_bundle"]] = build_results_bundle(
        sets=model.sets,
        data=model.data,
        vars=model.vars,
        model_obj=model,
        solution=getattr(model.model, "solution", None) if model.model is not None else solution,
        solution_summary=st.session_state[KEYS["solution_summary"]],
        solver=solver,
    )


# =============================================================================
# Page
# =============================================================================
def render_generation_planning_optimization_page() -> None:
    _init_defaults()

    st.title("Model Optimization")
    st.caption("Build and solve the single-objective optimization model for the active project.")

    project_name = st.session_state.get(KEYS["active_project"])
    if not project_name:
        st.error("No active project found. Please create/select a project first in the Project Setup page.")
        return

    st.success(f"Active project: {project_name}")

    # Retrieve project-specific formulation.json settings
    paths = project_paths(project_name)
    formulation_json = read_json_file(
        paths.formulation_json,
        error_cls=InputValidationError,
        parse_prefix="Cannot parse JSON",
    )
    formulation_mode = _as_str(formulation_json.get("core_formulation", "steady_state"), name="core_formulation")

    st.subheader("Solve Run")
    st.caption("This page builds the full model and solves the single-objective formulation.")
    st.info("Multi-objective workflows are not exposed here yet. This page always runs the single-objective solve.")

    st.subheader("Solver")
    solver = st.radio(
        "Select solver",
        options=["highs", "gurobi"],
        index=0 if st.session_state[KEYS["solver"]] == "highs" else 1,
        format_func=lambda v: "HiGHS" if v == "highs" else "Gurobi",
        horizontal=True,
    )
    st.session_state[KEYS["solver"]] = solver

    with st.expander("Advanced settings", expanded=False):
        st.caption("Optional problem export, log override, and solver-specific parameters.")

        c1, c2 = st.columns(2)
        with c1:
            st.session_state[KEYS["use_custom_lp"]] = st.checkbox(
                "Write problem file (.lp/.mps)",
                value=bool(st.session_state[KEYS["use_custom_lp"]]),
            )
            st.session_state[KEYS["custom_lp"]] = st.text_input(
                "Problem file path",
                value=str(st.session_state[KEYS["custom_lp"]]),
                placeholder=".../problem.lp",
                disabled=not bool(st.session_state[KEYS["use_custom_lp"]]),
            )

        with c2:
            st.session_state[KEYS["use_custom_log"]] = st.checkbox(
                "Override solver log path",
                value=bool(st.session_state[KEYS["use_custom_log"]]),
            )
            st.session_state[KEYS["custom_log"]] = st.text_input(
                "Solver log path",
                value=str(st.session_state[KEYS["custom_log"]]),
                placeholder=".../solver.log",
                disabled=not bool(st.session_state[KEYS["use_custom_log"]]),
            )

        st.markdown("---")

        if solver == "gurobi":
            st.markdown("**Gurobi parameters**")
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                st.session_state[KEYS["gurobi_time_limit"]] = st.number_input(
                    "TimeLimit [s]", min_value=0, step=10, value=int(st.session_state[KEYS["gurobi_time_limit"]])
                )
            with g2:
                st.session_state[KEYS["gurobi_mip_gap"]] = st.number_input(
                    "MIPGap (0–1)", min_value=0.0, max_value=1.0, step=0.001,
                    value=float(st.session_state[KEYS["gurobi_mip_gap"]])
                )
            with g3:
                st.session_state[KEYS["gurobi_threads"]] = st.number_input(
                    "Threads", min_value=0, step=1, value=int(st.session_state[KEYS["gurobi_threads"]])
                )
            with g4:
                st.session_state[KEYS["gurobi_presolve"]] = st.selectbox(
                    "Presolve", options=[-1, 0, 1, 2],
                    index=[-1, 0, 1, 2].index(int(st.session_state[KEYS["gurobi_presolve"]]))
                )
        else:
            st.markdown("**HiGHS parameters**")
            h1, h2, h3, h4 = st.columns(4)
            with h1:
                st.session_state[KEYS["highs_time_limit"]] = st.number_input(
                    "time_limit [s]", min_value=0, step=10, value=int(st.session_state[KEYS["highs_time_limit"]])
                )
            with h2:
                st.session_state[KEYS["highs_mip_rel_gap"]] = st.number_input(
                    "mip_rel_gap (0–1)", min_value=0.0, max_value=1.0, step=0.001,
                    value=float(st.session_state[KEYS["highs_mip_rel_gap"]])
                )
            with h3:
                st.session_state[KEYS["highs_threads"]] = st.number_input(
                    "threads", min_value=0, step=1, value=int(st.session_state[KEYS["highs_threads"]])
                )
            with h4:
                st.session_state[KEYS["highs_presolve"]] = st.checkbox(
                    "presolve", value=bool(st.session_state[KEYS["highs_presolve"]])
                )

    st.markdown("---")

    lp_path, log_path, ok = _validate_optional_paths(project_name, solver)
    params = _solver_params(solver)

    st.caption(f"Solver log will be stored at `{log_path}`")

    run_clicked = st.button(
        "Build and solve",
        type="primary",
        help="Builds the full model and solves the single-objective problem for the active project.",
    )

    if run_clicked and ok:
        _reset_result_state()

        t0 = time.time()

        with st.spinner(f"Building and solving project '{project_name}'..."):
            model = _build_model(project_name, formulation_mode)
            solution = model.solve_single_objective(
                solver=solver,
                solver_params=params,
                problem_fn=lp_path if lp_path else None,
                log_file_path=log_path,
            )
            _store_solve_outputs(
                model=model,
                solution=solution,
                solver=solver,
                fallback_log_path=log_path,
            )

        elapsed = time.time() - t0
        st.success(f"Solve completed. Runtime: {elapsed:.2f} s")

    _render_solver_log(st.session_state.get(KEYS["log_path"]))

    # -------------------------
    # Quick inspection (debugging-friendly)
    # -------------------------
    with st.expander("Quick inspection", expanded=False):
        bundle = st.session_state.get(KEYS["results_bundle"])
        data_ds = getattr(bundle, "data", None) if bundle is not None else st.session_state.get(KEYS["data"])
        vars_dict = getattr(bundle, "vars", None) if bundle is not None else st.session_state.get(KEYS["vars"])
        model_obj = st.session_state.get(KEYS["model_obj"])

        _show_xr_dataset_debug(data_ds, "Data")
        _render_variables_debug(data_ds, vars_dict)
        _render_constraints_debug(model_obj)
        summary = st.session_state.get(KEYS["solution_summary"])
        _render_minimal_results(summary)



# Call page
render_generation_planning_optimization_page()
