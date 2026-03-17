# core/typical_year_model/model.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import xarray as xr
import linopy as lp

from core.typical_year_model.sets import initialize_sets
from core.typical_year_model.data import initialize_data
from core.typical_year_model.variables import initialize_vars
from core.typical_year_model.constraints import initialize_constraints
from core.typical_year_model.objective import initialize_objective
from core.io.utils import tee_console_output


class InputValidationError(RuntimeError):
    pass


SolverKw = Dict[str, Any]


@dataclass
class _BuildFlags:
    sets_initialized: bool = False
    data_initialized: bool = False
    model_initialized: bool = False
    vars_initialized: bool = False
    constraints_initialized: bool = False
    model_built: bool = False


class SteadyStateModel:
    def __init__(self, project_name: str) -> None:
        self.project_name = project_name

        self.sets: xr.Dataset = xr.Dataset()
        self.data: xr.Dataset = xr.Dataset()

        self.model: Optional[lp.Model] = None
        self.vars: Dict[str, lp.Variable] = {}

        self._last_log_path: Optional[Path] = None
        self._flags = _BuildFlags()

    # ---------------------------------------------------------------------
    # Build steps
    # ---------------------------------------------------------------------
    def _initialize_sets(self) -> None:
        self.sets = initialize_sets(self.project_name)
        self._flags.sets_initialized = True

    def _initialize_data(self) -> None:
        if not self._flags.sets_initialized:
            self._initialize_sets()
        self.data = initialize_data(self.project_name, self.sets)
        self._flags.data_initialized = True

    def _initialize_linopy_model(self) -> None:
        self.model = lp.Model()
        self._flags.model_initialized = True

    def _initialize_vars(self) -> None:
        if not self._flags.data_initialized:
            self._initialize_data()
        if not self._flags.model_initialized or self.model is None:
            self._initialize_linopy_model()

        self.vars = initialize_vars(self.sets, self.data, self.model)
        self._flags.vars_initialized = True

    def _initialize_constraints(self) -> None:
        if not self._flags.vars_initialized:
            self._initialize_vars()
        if self.model is None:
            raise RuntimeError("_initialize_constraints: model is not initialized.")

        initialize_constraints(self.sets, self.data, self.vars, self.model)
        self._flags.constraints_initialized = True

    def _initialize_objective(self) -> None:
        if not self._flags.constraints_initialized:
            self._initialize_constraints()
        if self.model is None:
            raise RuntimeError("_initialize_objective: model is not initialized.")

        initialize_objective(self.sets, self.data, self.vars, self.model)
        self._flags.model_built = True

    def _build_model(self) -> None:
        if not self._flags.sets_initialized:
            self._initialize_sets()
        if not self._flags.data_initialized:
            self._initialize_data()
        if not self._flags.model_initialized:
            self._initialize_linopy_model()
        if not self._flags.vars_initialized:
            self._initialize_vars()
        if not self._flags.constraints_initialized:
            self._initialize_constraints()
        if not self._flags.model_built:
            self._initialize_objective()

    # ---------------------------------------------------------------------
    # Optional exports
    # ---------------------------------------------------------------------
    def _maybe_write_problem(self, problem_fn: Optional[Path]) -> None:
        """
        Best-effort export of the optimization problem.
        Linopy supports writing LP/MPS in most versions, but API differs slightly.
        """
        if problem_fn is None or self.model is None:
            return

        problem_fn = Path(problem_fn)
        problem_fn.parent.mkdir(parents=True, exist_ok=True)

        # Try common linopy APIs defensively
        try:
            # Newer linopy: model.to_file(...)
            if hasattr(self.model, "to_file"):
                self.model.to_file(problem_fn)
                return
        except Exception:
            pass

        try:
            # Older patterns sometimes use write(...)
            if hasattr(self.model, "write"):
                self.model.write(problem_fn)
                return
        except Exception:
            pass

        # If nothing worked, at least create a placeholder so UI does not mislead
        problem_fn.write_text("[Could not export via linopy API in this environment]\n", encoding="utf-8")

    def _ensure_log_artifact(self, solver: str) -> None:
        if self._last_log_path is None:
            return
        if self._last_log_path.exists() and self._last_log_path.stat().st_size > 0:
            return
        self._last_log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_log_path.write_text(
            (
                f"Solver: {solver}\n"
                "No solver log was produced by the current linopy/solver backend.\n"
                "The solve still completed, but the backend did not emit a file-based log.\n"
            ),
            encoding="utf-8",
        )

    # ---------------------------------------------------------------------
    # Solve
    # ---------------------------------------------------------------------
    def solve_single_objective(
        self,
        solver: str = "highs",
        solver_params: SolverKw | None = None,
        problem_fn: Optional[Path] = None,
        log_file_path: Optional[Path] = None,
    ) -> xr.Dataset:
        """
        Build and solve the model. Returns an xarray Dataset with:
          - attrs: status, objective_value (if available), solver, solver_params
          - (optional) decision var snapshots (res_units, battery_units, generator_units)
        The full numeric solution is also available as self.model.solution after solve.
        """
        self._build_model()
        if self.model is None:
            raise RuntimeError("solve_single_objective: linopy model is not initialized.")

        # Record log path for UI (note: solver controls actual logging)
        if log_file_path is not None:
            self._last_log_path = Path(log_file_path)
            self._last_log_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self._last_log_path = None

        # Optional export
        self._maybe_write_problem(problem_fn)

        # Run solver
        solve_kwargs = dict(solver_params or {})
        try:
            # Many linopy versions accept log_file / logfile; be defensive
            if self._last_log_path is not None:
                if "logfile" in self.model.solve.__code__.co_varnames:
                    solve_kwargs["logfile"] = str(self._last_log_path)
                elif "log_file" in self.model.solve.__code__.co_varnames:
                    solve_kwargs["log_file"] = str(self._last_log_path)
                # otherwise: ignore; solver may still print to stdout
        except Exception:
            # If introspection fails, ignore
            pass

        # Solve call
        if self._last_log_path is not None:
            with tee_console_output(self._last_log_path):
                result = self.model.solve(solver_name=solver, **solve_kwargs) if "solver_name" in getattr(self.model.solve, "__code__", object()).co_varnames else self.model.solve(solver, **solve_kwargs)
        else:
            result = self.model.solve(solver_name=solver, **solve_kwargs) if "solver_name" in getattr(self.model.solve, "__code__", object()).co_varnames else self.model.solve(solver, **solve_kwargs)
        self._ensure_log_artifact(solver)

        # Linopy stores solution on the model
        sol = getattr(self.model, "solution", None)

        out = xr.Dataset()
        # status handling differs across versions: "result" might be a string or object
        out.attrs["solver"] = solver
        out.attrs["solver_params"] = dict(solver_params or {})
        out.attrs["status"] = str(getattr(result, "status", result))

        # objective value (best effort)
        obj_val = None
        for attr in ("objective_value", "objective", "obj_value"):
            if sol is not None and hasattr(sol, attr):
                try:
                    obj_val = float(getattr(sol, attr))
                    break
                except Exception:
                    pass
        if obj_val is None:
            # some versions store in result
            try:
                if hasattr(result, "objective_value"):
                    obj_val = float(result.objective_value)
            except Exception:
                pass
        if obj_val is not None:
            out.attrs["objective_value"] = obj_val

        # Attach minimal decision vars for Streamlit (best effort)
        # Note: solution variables are usually available under sol["var_name"] or sol[var]
        try:
            if isinstance(sol, xr.Dataset):
                # common case: sol is xr.Dataset of variables
                for k in ("res_units", "battery_units", "generator_units"):
                    if k in sol.data_vars:
                        out[k] = sol[k]
            elif sol is not None and hasattr(sol, "__getitem__"):
                # other structures that behave like dict
                for k in ("res_units", "battery_units", "generator_units"):
                    try:
                        v = sol[k]
                        if isinstance(v, xr.DataArray):
                            out[k] = v
                    except Exception:
                        pass
        except Exception:
            pass

        return out

    # ---------------------------------------------------------------------
    # Convenience for UI
    # ---------------------------------------------------------------------
    def results_summary(self) -> xr.Dataset:
        """
        Small, UI-oriented summary extracted from self.model.solution.
        Safe to call after solve.
        """
        if self.model is None:
            raise RuntimeError("results_summary: model is not initialized.")
        sol = getattr(self.model, "solution", None)
        ds = xr.Dataset()

        # objective
        obj_val = None
        if sol is not None:
            for attr in ("objective_value", "objective", "obj_value"):
                if hasattr(sol, attr):
                    try:
                        obj_val = float(getattr(sol, attr))
                        break
                    except Exception:
                        pass
        if obj_val is not None:
            ds.attrs["objective_value"] = obj_val

        # design vars
        try:
            if isinstance(sol, xr.Dataset):
                for k in ("res_units", "battery_units", "generator_units"):
                    if k in sol.data_vars:
                        ds[k] = sol[k]
        except Exception:
            pass

        return ds
