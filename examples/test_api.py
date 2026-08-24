"""Example: use MicroGridsPy as a Python library.

Creates a NEW project from scratch with create_project(), reuses the input data
from the bundled ``inverter_test_2`` example, then validates, solves (HiGHS), and
reads the structured results.

Run from anywhere:  python examples/test_api.py
Creates <repo>/projects/smoke_test/ (a throwaway you can delete afterwards).
"""
import shutil
from pathlib import Path

import microgridspy as mgp

# Resolve the repo root from this file, so the example works from any directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
mgp.set_workspace(REPO_ROOT)                       # projects/ lives under the repo root
src_inputs = REPO_ROOT / "projects" / "inverter_test_2" / "inputs"

# 1) create a NEW project from scratch, matching inverter_test_2's config.
#    NB: inverter_test_2 uses European CSV format -> delimiter ';', decimal ','.
paths = mgp.create_project(
    "smoke_test",
    formulation="steady_state",
    system_type="off_grid",
    resources=["solar"],          # 1 source -> matches n_sources
    csv_delimiter=";",
    csv_decimal=",",
    overwrite=True,
)
print("created:", paths.root)

# 2) reuse inverter_test_2's REAL data, keeping create_project's formulation.json.
for f in ["load_demand.csv", "resource_availability.csv",
          "renewables.yaml", "battery.yaml", "generator.yaml"]:
    shutil.copy(src_inputs / f, paths.inputs_dir / f)
print("copied real inputs from inverter_test_2")

# 3) validate -> solve -> results.
mgp.validate_project("smoke_test")
model = mgp.solve("smoke_test", solver="highs")
r = model.results()
print("status   :", r.metadata["status"])
print("objective:", round(r.metadata["objective_value"], 2))   # -> 226704.91
print("kpis:\n", r.kpis)
