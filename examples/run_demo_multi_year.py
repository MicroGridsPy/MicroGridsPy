"""Example: multi-year capacity planning with MicroGridsPy.

Loads the bundled ``demo_multi_year`` example into an isolated workspace, then
validates, solves (HiGHS), reads the structured results, and exports them.

This is the multi-year counterpart of ``run_demo_typical_year.py``. Instead of one
representative year it optimises an explicit 10-year horizon, so the results carry
a ``year`` dimension: capacity evolves, assets are replaced, and cash flows are
discounted to a net present cost.

Be patient: this builds a model with roughly 876,000 rows (8,760 hours x 10 years)
and takes on the order of 20 minutes to solve, against seconds for the typical-year
demo. That difference is the whole point of having both formulations.

Run from anywhere:  python examples/run_demo_multi_year.py
"""

import tempfile
from pathlib import Path

import microgridspy as mgp

# Use a throwaway workspace so the example never touches an existing projects/ folder.
workspace = Path(tempfile.mkdtemp(prefix="microgridspy_example_"))
mgp.set_workspace(workspace)
print("workspace:", workspace)

# 1) copy the packaged example project into the workspace.
project = mgp.load_example("demo_multi_year", overwrite=True)
print("loaded example:", project)

# 2) validate -> solve -> results.
mgp.validate_project(project)
model = mgp.solve(project, solver="highs")
r = model.results()
print("status   :", r.metadata["status"])
print("objective:", round(r.metadata["objective_value"], 2))  # net present cost

# 3) what multi-year adds over typical-year: results resolved by year.
print("\ncapacity by year:\n", r.capacity_by_year)
print("\nyearly KPIs:\n", r.kpis_yearly)

# 4) persist the result tables (CSV/Excel) to the project's results/ folder.
written = mgp.export_results(r)
print(f"\nwrote {len(written)} result files under {workspace / 'projects' / project / 'results'}")
