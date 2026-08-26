"""MicroGridsPy: bottom-up optimization tool for planning mini-grids.

Public API:

```python
import microgridspy as mgp

# one-liner: solve and get analysis-ready tables
results = mgp.solve("Kalobeyei_1", solver="highs").results()
results.kpis                      # pandas DataFrame
mgp.export_results(results)       # write CSV/Excel to the project folder

# or drive the models directly
from microgridspy import SteadyStateModel
model = SteadyStateModel("demo_typical_year")
model.solve_single_objective(solver="highs")
summary = model.results_summary()
```

The Streamlit GUI lives in `microgridspy.app` and is installed only with
the ``[gui]`` extra; importing this package never imports Streamlit.

Stability: ``SteadyStateModel``, ``MultiYearModel`` and ``InputValidationError``
are the stable core. The results dataclasses are provisional (their tables may
grow) until the 1.0 release.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

# --- Convenience API --------------------------------------------------------
from microgridspy.api import (
    export_results,
    list_input_timeseries,
    load_inputs,
    load_results,
    plot_input_timeseries,
    solve,
    solve_example,
)
from microgridspy.export.multi_year_results import MultiYearResults

# --- Structured results (provisional) ---------------------------------------
from microgridspy.export.typical_year_results import TypicalYearResults
from microgridspy.io.examples import list_examples, load_example

# --- Project scaffolding & management ---------------------------------------
from microgridspy.io.project_setup import (
    copy_project,
    create_project,
    delete_project,
    rename_project,
    validate_project,
)
from microgridspy.io.templates import TemplateSettings

# --- Workspace helpers ------------------------------------------------------
from microgridspy.io.utils import list_projects, project_exists, project_paths, set_workspace
from microgridspy.multi_year_model.model import MultiYearModel

# --- Models (stable core) ---------------------------------------------------
from microgridspy.typical_year_model.model import InputValidationError, SteadyStateModel

__all__ = [
    "SteadyStateModel",
    "MultiYearModel",
    "solve",
    "solve_example",
    "list_examples",
    "load_example",
    "load_results",
    "export_results",
    "load_inputs",
    "list_input_timeseries",
    "plot_input_timeseries",
    "create_project",
    "validate_project",
    "delete_project",
    "copy_project",
    "rename_project",
    "TemplateSettings",
    "TypicalYearResults",
    "MultiYearResults",
    "set_workspace",
    "list_projects",
    "project_paths",
    "project_exists",
    "InputValidationError",
    "__version__",
]

try:
    __version__ = _version("microgridspy")
except PackageNotFoundError:  # not installed (e.g. running from a source checkout)
    __version__ = "0.0.0+unknown"
