# Typical-Year Tutorial

This tutorial runs a complete **typical-year** (steady-state) study from project creation to
results, using the open-source HiGHS solver. It assumes MicroGridsPy is installed with the
`highs` extra — see [Installation](../getting-started/installation.md).

## 1. Create the project

```python
import microgridspy as mgp

paths = mgp.create_project(
    "tutorial_typical",
    formulation="steady_state",
    system_type="off_grid",
    resources=["solar"],     # one renewable source labelled "solar"
    scenarios=1,             # deterministic (single scenario)
)
print(paths)                 # where the input templates were written
```

This writes `formulation.json` and input templates into the project folder. The renewable
source count follows the length of `resources`.

## 2. Populate the inputs

Edit the generated files with your case-study data (see the
[Data Reference](../data-reference/overview.md) for formats and units):

- **`load_demand.csv`** — 8760 hourly demand values (kWh/hour).
- **`resource_availability.csv`** — hourly capacity factor for `solar` (values in `[0,1]`).
- **`renewables.yaml`** — PV CAPEX, FOM, lifetime, WACC, efficiency, unit size.
- **`battery.yaml`** — energy CAPEX, efficiencies, DoD, charge/discharge times, lifetime.
- **`generator.yaml`** — diesel capacity, nominal efficiency, fuel LHV, fuel cost, emissions.

You can inspect an input series before solving:

```python
fig_hourly, fig_daily = mgp.plot_input_timeseries("tutorial_typical", "load_demand")
```

## 3. Validate

```python
mgp.validate_project("tutorial_typical")   # raises InputValidationError if incomplete
```

## 4. Solve

```python
model = mgp.solve("tutorial_typical", solver="highs")
```

## 5. Inspect capacity and cost results

```python
results = model.results()

print(results.kpis)            # LCOE, renewable share, total cost, ...
print(results.design_summary)  # installed capacity by technology
print(results.dispatch.head()) # hourly dispatch time series
```

## 6. Export

```python
mgp.export_results(results)    # CSV/Excel into the project's results/ folder
```

## What the model solved

Under the hood, the typical-year formulation minimized the expected
[equivalent annual cost (EAC)](../methodology/objective-function.md#typical-year-planning) —
annualized investment cost plus expected annual operating cost — subject to the hourly
[energy balance](../methodology/constraints.md#energy-balance-constraint), the
[renewable production limit](../methodology/renewable.md), and the
[battery](../methodology/battery.md) and [generator](../methodology/generator.md)
constraints. Because there is a single representative year, intertemporal discounting does
not affect the sizing decision.

## Next steps

- Add a second scenario (`scenarios=2`) to make it stochastic.
- Enable a weak-grid connection with `system_type="on_grid"`.
- Move to the [Multi-Year Tutorial](multi-year.md) for phased capacity expansion.
