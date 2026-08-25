# Multi-Year Tutorial

This tutorial runs a **multi-year** (dynamic) planning study with an explicit horizon,
phased investment steps, and capacity expansion. It builds on the concepts from the
[Typical-Year Tutorial](typical-year.md).

## 1. Create the project

```python
import microgridspy as mgp

mgp.create_project(
    "tutorial_multiyear",
    formulation="dynamic",
    system_type="off_grid",
    resources=["solar", "wind"],
    horizon_years=20,                  # planning horizon H = 20 years
    capacity_expansion=True,           # allow staged expansion
    investment_steps_years=[5, 5, 5, 5],  # four 5-year investment steps
    start_year_label="2026",
    scenarios=2,                       # two stochastic scenarios
)
```

Compared with the typical-year case, the dynamic formulation adds a **year** axis and
**investment steps** ($\tau$), each defining an investment cohort with its own installation
time, lifetime, and financial parameters.

## 2. Populate the multi-year inputs

The time-series files now carry an extra year dimension:

- **`load_demand.csv`** — `scenario × year`, 8760 hourly rows each. This is where you encode
  **demand growth** across the horizon.
- **`resource_availability.csv`** — `scenario × year × resource`.
- **`renewables.yaml`**, **`battery.yaml`**, **`generator.yaml`** — techno-economic inputs
  indexed by investment step where relevant (CAPEX trajectories, WACC, lifetimes).

See the multi-year tab of the [Data Reference](../data-reference/overview.md) for the exact
axes, units, and mandatory conditions.

## 3. Validate and solve

```python
mgp.validate_project("tutorial_multiyear")
model = mgp.solve("tutorial_multiyear", solver="highs")
results = model.results()   # a MultiYearResults object
```

## 4. Inspect the horizon results

```python
print(results.kpis)            # present-value cost, renewable share, ...
# per-year installed capacity, dispatch, and cost breakdowns resolved over the horizon
```

## What the model solved

The dynamic formulation minimized the expected
[Net Present Welfare Cost (NPWC)](../methodology/objective-function.md#multi-year-planning):
each investment cohort's capital cost is converted to a WACC-based
[annuity](../methodology/objective-function.md#annuities-and-the-capital-recovery-factor),
system-level cash flows are discounted with the social discount rate, installed capacity is
**non-decreasing** across steps, and a
[salvage value](../methodology/objective-function.md#salvage-value) credits assets whose
technical lifetime extends beyond the horizon. Sizing is shared across scenarios while
dispatch is scenario-specific.

## Example projects

The repository ships example projects (e.g. the `Kalobeyei_*` cases under `projects/`) that
exercise the dynamic formulation with real-world data. They are a useful reference for how a
complete multi-year input set is structured.
