"""High-level convenience API for MicroGridsPy.

These are thin wrappers over the model, export, and IO layers that give library
users a short path from a project name to solved, analysis-ready results::

    import microgridspy as mgp

    results = mgp.solve("Kalobeyei_1", solver="highs").results()
    results.kpis                      # pandas DataFrame
    mgp.export_results(results)       # write CSV/Excel to the project folder
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Union

import xarray as xr

from microgridspy.typical_year_model.model import SteadyStateModel, InputValidationError
from microgridspy.multi_year_model.model import MultiYearModel
from microgridspy.export.typical_year_results import TypicalYearResults
from microgridspy.export.multi_year_results import MultiYearResults

AnyModel = Union[SteadyStateModel, MultiYearModel]
AnyResults = Union[TypicalYearResults, MultiYearResults]

_STEADY = {"steady_state", "typical_year"}
_DYNAMIC = {"dynamic", "multi_year"}


def _detect_formulation(project_name: str) -> str:
    """Read ``core_formulation`` from a project's ``formulation.json``."""
    from microgridspy.io.utils import project_paths

    fpath = project_paths(project_name).formulation_json
    if not fpath.exists():
        raise InputValidationError(
            f"Cannot detect formulation: {fpath} not found. "
            "Pass formulation='steady_state' or 'dynamic' explicitly."
        )
    try:
        raw = json.loads(fpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputValidationError(f"Cannot parse {fpath}: {exc}") from exc
    return str(raw.get("core_formulation", "steady_state"))


def _model_for(project_name: str, formulation: str) -> AnyModel:
    if formulation in _STEADY:
        return SteadyStateModel(project_name)
    if formulation in _DYNAMIC:
        return MultiYearModel(project_name)
    raise InputValidationError(
        f"Unknown formulation '{formulation}' (expected one of "
        f"{sorted(_STEADY | _DYNAMIC)})."
    )


def solve(
    project_name: str,
    *,
    formulation: Optional[str] = None,
    solver: str = "highs",
    **solver_kwargs: Any,
) -> AnyModel:
    """Build and solve a project, returning the solved model.

    Args:
        project_name: the project folder in the active workspace.
        formulation: ``"steady_state"`` or ``"dynamic"``; if ``None`` it is read
            from the project's ``formulation.json``.
        solver: ``"highs"`` (open source) or ``"gurobi"`` (licensed).
        **solver_kwargs: forwarded to
            :meth:`SteadyStateModel.solve_single_objective` (e.g. ``solver_params``,
            ``problem_fn``, ``log_file_path``).

    Returns:
        The solved model instance, ready for :meth:`results` /
        :meth:`results_summary`.
    """
    if formulation is None:
        formulation = _detect_formulation(project_name)
    model = _model_for(project_name, formulation)
    model.solve_single_objective(solver=solver, **solver_kwargs)
    return model


def load_results(
    project_name: str,
    *,
    formulation: Optional[str] = None,
) -> Optional[AnyResults]:
    """Load a previously saved run's results from the project's ``results/`` folder.

    Args:
        project_name: the project to read.
        formulation: ``"steady_state"`` or ``"dynamic"``; auto-detected from
            ``formulation.json`` when ``None``.

    Returns:
        The structured results object, or ``None`` if no saved run exists.
    """
    from microgridspy.export.results_page_helpers import (
        load_multi_year_results_from_files,
        load_typical_year_results_from_files,
    )

    if formulation is None:
        formulation = _detect_formulation(project_name)
    if formulation in _DYNAMIC:
        return load_multi_year_results_from_files(project_name)
    return load_typical_year_results_from_files(project_name)


def export_results(results: AnyResults, out_dir: Optional[Path] = None) -> dict[str, str]:
    """Write a results object to CSV/Excel files.

    Args:
        results: a :class:`TypicalYearResults` or :class:`MultiYearResults`.
        out_dir: destination directory; when ``None``, writes to the project's
            ``results/`` folder.

    Returns:
        Mapping of output name to the written file path.
    """
    if isinstance(results, MultiYearResults):
        from microgridspy.export.multi_year_results import export_multi_year_results_package

        return export_multi_year_results_package(results=results, out_dir=out_dir)
    if isinstance(results, TypicalYearResults):
        from microgridspy.export.typical_year_results import export_typical_year_results_package

        return export_typical_year_results_package(results=results, out_dir=out_dir)
    raise TypeError(
        f"export_results expects TypicalYearResults or MultiYearResults, got {type(results).__name__}"
    )


def load_inputs(project_name: str, *, formulation: Optional[str] = None) -> xr.Dataset:
    """Assemble and return a project's input dataset, without solving.

    Builds the sets and data layers (the same inputs a model would use), so you
    can inspect the assembled xarray Dataset directly.

    Args:
        project_name: the project to read.
        formulation: ``"steady_state"`` or ``"dynamic"``; auto-detected when None.

    Returns:
        xr.Dataset: the assembled input dataset.
    """
    if formulation is None:
        formulation = _detect_formulation(project_name)
    model = _model_for(project_name, formulation)
    model._initialize_data()  # builds sets + data, no optimization model
    return model.data


def list_input_timeseries(project_name: str, *, formulation: Optional[str] = None) -> list[str]:
    """List the time-series input variables available to plot for a project."""
    from microgridspy.visualization.input_plots import list_timeseries_options

    ds = load_inputs(project_name, formulation=formulation)
    return [opt.variable for opt in list_timeseries_options(ds)]


def plot_input_timeseries(
    project_name: str,
    variable: Optional[str] = None,
    *,
    formulation: Optional[str] = None,
    scenario: Optional[str] = None,
    year: Optional[Union[str, int]] = None,
    **selectors: Any,
):
    """Plot an input time series as ``(hourly, daily)`` matplotlib figures.

    Args:
        project_name: the project to read.
        variable: the time-series variable to plot; defaults to the first
            available (see :func:`list_input_timeseries`).
        formulation: auto-detected when None.
        scenario, year: optional selectors when the variable has those dimensions.
        **selectors: further dimension selectors (e.g. ``resource="solar"``).

    Returns:
        tuple[matplotlib.figure.Figure, matplotlib.figure.Figure]: hourly and
        average-daily figures.
    """
    from microgridspy.visualization.input_plots import (
        build_timeseries_figures,
        list_timeseries_options,
        slice_timeseries,
    )

    ds = load_inputs(project_name, formulation=formulation)
    names = [opt.variable for opt in list_timeseries_options(ds)]
    if not names:
        raise InputValidationError(f"No plottable time-series inputs found for '{project_name}'.")
    if variable is None:
        variable = names[0]
    elif variable not in names:
        raise InputValidationError(
            f"'{variable}' is not a plottable time series for '{project_name}'. Available: {names}"
        )
    da = slice_timeseries(
        ds, variable=variable, scenario=scenario, year=year, selectors=selectors or None
    )
    label = variable.replace("_", " ")
    return build_timeseries_figures(da, title_prefix=label, y_label=label)
