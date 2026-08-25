# Quickstart

This page shows the fastest way to see MicroGridsPy run — solving the **bundled example
project** — and then the full workflow for building your own case study.

## Run the bundled example

The repository ships one ready-to-run project, **`demo_typical_year`**: a small off-grid,
typical-year case with real hourly demand and solar data. With the package installed (including
the `highs` extra) and working from a clone of the repository, you can solve it in one call:

```python
import microgridspy as mgp

# Projects are resolved from <workspace>/projects/. Running from the repo root
# finds projects/demo_typical_year automatically; otherwise point the workspace at
# the folder that contains projects/:
# mgp.set_workspace("/path/to/MicroGridsPy")

model = mgp.solve("demo_typical_year", solver="highs")
results = model.results()

print(results.kpis)            # headline KPIs (LCOE, renewable share, total cost, …)
print(results.design_summary)  # installed capacity by technology
```

The active **workspace** is the directory containing a `projects/` folder — by default the
current working directory, or the path in the `MICROGRIDSPY_WORKSPACE` environment variable, or
whatever you pass to [`set_workspace`](../api/index.md#workspace-helpers). The
[Examples](../examples/index.md) section walks through the larger `Kalobeyei_*` projects the same
way.

## Build your own project

To start a new case study, `create_project` writes a project folder with a `formulation.json`
and input templates.

!!! note "Templates are scaffolding to fill in"
    The generated **time-series CSVs are empty (all cells `0.0`)** and the **YAML economic
    parameters default to `0.0`** (only a few technical defaults — efficiencies, depth of
    discharge, lifetimes — are pre-filled). A freshly created project therefore does not solve
    to a meaningful result until you populate demand, resource availability, and costs. Use
    `demo_typical_year` above (or an example project) as a reference for a complete input set.

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
