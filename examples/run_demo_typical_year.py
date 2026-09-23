"""Example: use MicroGridsPy as a Python library.

Loads the bundled ``demo_typical_year`` example into an isolated workspace, then
validates, solves (HiGHS), reads the structured results, and exports them. This is
the intended public quick-start path — it works straight after ``pip install`` with
no repository clone and no manual input files.

Run from anywhere:  python examples/run_demo_typical_year.py
"""

import tempfile
from pathlib import Path

import microgridspy as mgp

# Use a throwaway workspace so the example never touches an existing projects/ folder.
workspace = Path(tempfile.mkdtemp(prefix="microgridspy_example_"))
mgp.set_workspace(workspace)
print("workspace:", workspace)

# 1) copy the packaged example project into the workspace.
project = mgp.load_example("demo_typical_year", overwrite=True)
print("loaded example:", project)

# 2) validate -> solve -> results.
mgp.validate_project(project)
model = mgp.solve(project, solver="highs")
r = model.results()
print("status   :", r.metadata["status"])
print("objective:", round(r.metadata["objective_value"], 2))  # -> 226704.91
print("kpis:\n", r.kpis)

# 3) persist the result tables (CSV/Excel) to the project's results/ folder.
written = mgp.export_results(r)
print(f"wrote {len(written)} result files under {workspace / 'projects' / project / 'results'}")
