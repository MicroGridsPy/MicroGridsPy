"""MicroGridsPy: bottom-up optimization tool for planning mini-grids.

Public API::

    import microgridspy as mgp

    # one-liner: solve and get analysis-ready tables
    results = mgp.solve("Kalobeyei_1", solver="highs").results()
    results.kpis                      # pandas DataFrame
    mgp.export_results(results)       # write CSV/Excel to the project folder

    # or drive the models directly
    from microgridspy import SteadyStateModel
    model = SteadyStateModel("inverter_test_2")
    model.solve_single_objective(solver="highs")
    summary = model.results_summary()

The Streamlit GUI lives in :mod:`microgridspy.app` and is installed only with
the ``[gui]`` extra; importing this package never imports Streamlit.

Stability: ``SteadyStateModel``, ``MultiYearModel`` and ``InputValidationError``
are the stable core. The results dataclasses are provisional (their tables may
grow) until the 1.0 release.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _version

# --- Models (stable core) ---------------------------------------------------
from microgridspy.typical_year_model.model import SteadyStateModel, InputValidationError
from microgridspy.multi_year_model.model import MultiYearModel

# --- Convenience API --------------------------------------------------------
from microgridspy.api import solve, load_results, export_results

# --- Structured results (provisional) ---------------------------------------
from microgridspy.export.typical_year_results import TypicalYearResults
from microgridspy.export.multi_year_results import MultiYearResults

# --- Workspace helpers ------------------------------------------------------
from microgridspy.io.utils import set_workspace, list_projects, project_paths

__all__ = [
    "SteadyStateModel",
    "MultiYearModel",
    "solve",
    "load_results",
    "export_results",
    "TypicalYearResults",
    "MultiYearResults",
    "set_workspace",
    "list_projects",
    "project_paths",
    "InputValidationError",
    "__version__",
]

try:
    __version__ = _version("microgridspy")
except PackageNotFoundError:  # not installed (e.g. running from a source checkout)
    __version__ = "0.0.0+unknown"
