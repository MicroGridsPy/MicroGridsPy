# Quickstart

This page walks through the minimum end-to-end workflow: create a project, populate and
validate its inputs, solve, and read the results.

## The workflow

```python
import microgridspy as mgp

# 1. Create a project folder and generate input templates
mgp.create_project(
    "my_site",
    formulation="steady_state",   # or "dynamic" for multi-year planning
    system_type="off_grid",       # or "on_grid"
    resources=["solar", "wind"],  # one renewable source per label
    scenarios=1,                  # number of stochastic scenarios
)

# 2. Edit the generated input files (CSV / YAML / JSON) with your case-study data,
#    then validate that the project is complete and internally consistent
mgp.validate_project("my_site")

# 3. Build and solve the optimization; returns the solved model
model = mgp.solve("my_site", solver="highs")

# 4. Retrieve analysis-ready results
results = model.results()     # a TypicalYearResults object (pandas DataFrames)
print(results.kpis)           # headline KPIs
print(results.design_summary) # installed capacity by technology

# 5. Persist results to the project's results/ folder as CSV/Excel
mgp.export_results(results)
```

## What each step does

| Step | Function | Effect |
|---|---|---|
| Create | [`create_project`](../api/project.md) | writes `formulation.json` and input templates into a project folder |
| Validate | [`validate_project`](../api/project.md) | checks required inputs exist and are consistent; raises `InputValidationError` otherwise |
| Solve | [`solve`](../api/optimization.md) | assembles the Linopy model and solves it, returning the solved model |
| Results | `model.results()` / [`load_results`](../api/results.md) | structured results object with capacity, costs, dispatch and KPIs |
| Export | [`export_results`](../api/results.md) | writes the result tables to disk |

!!! tip "Formulation auto-detection"
    `solve()`, `load_results()` and `load_inputs()` read the formulation from the project's
    `formulation.json` when you don't pass `formulation=` explicitly, so you rarely need to
    repeat it after `create_project`.

## Driving the models directly

The convenience functions above wrap the model classes. You can also use them directly:

```python
from microgridspy import SteadyStateModel

model = SteadyStateModel("my_site")
model.solve_single_objective(solver="highs")
results = model.results()
```

For the multi-year formulation, use `MultiYearModel` in the same way. See the
[API Reference](../api/index.md) for the full, source-generated signatures, and the
[Tutorials](../tutorials/typical-year.md) for complete case studies.
