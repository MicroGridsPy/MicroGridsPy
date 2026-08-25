# Running a Model

The practical workflow is:

1. **create** a project and generate templates;
2. **populate and validate** the inputs;
3. **select** the formulation and solver;
4. **run** the optimization;
5. **inspect** KPIs and detailed results.

## From project to solved model

```python
import microgridspy as mgp

mgp.validate_project("my_site")               # step 2
model = mgp.solve("my_site", solver="highs")  # steps 3–4
results = model.results()                      # step 5
```

`solve()` reads the formulation from `formulation.json`, builds the appropriate model
(`SteadyStateModel` or `MultiYearModel`), and solves it with the requested solver. It
returns the **solved model**, from which you obtain a structured results object with
`model.results()` or an `xarray` summary with `model.results_summary()`.

## Solver options

```python
model = mgp.solve(
    "my_site",
    solver="highs",          # "highs" (open source) or "gurobi" (licensed)
    formulation=None,        # None → auto-detect; or "steady_state" / "dynamic"
)
```

Extra keyword arguments are forwarded to the model's `solve_single_objective(...)` (e.g.
`solver_params`, `problem_fn`, `log_file_path`). At least one solver extra must be installed
— see [Installation](../getting-started/installation.md).

## Driving the model class directly

```python
from microgridspy import SteadyStateModel

model = SteadyStateModel("my_site")
model.solve_single_objective(solver="highs")
results = model.results()
```

Use `MultiYearModel` the same way for dynamic studies.

## Command line

The package also installs a `microgridspy` console command and a `microgridspy-gui`
Streamlit workspace (with the `[gui]` extra). The CLI mirrors the create → validate → solve
workflow; run `microgridspy --help` for the available subcommands.

Once solved, see [Results](results.md) for what the outputs mean.
