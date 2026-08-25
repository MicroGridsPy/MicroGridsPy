# Results

Solving a project yields a **structured results object** — `TypicalYearResults` for the
steady-state formulation, `MultiYearResults` for the dynamic one. Each is a collection of
analysis-ready `pandas` DataFrames.

## Obtaining results

```python
import microgridspy as mgp

model = mgp.solve("my_site", solver="highs")
results = model.results()          # structured results (DataFrames)

# or reload a previously saved run without re-solving:
results = mgp.load_results("my_site")
```

## What the tables contain

Typical-year results expose, among others:

| Table | Content |
|---|---|
| `kpis` | headline indicators (e.g. LCOE, renewable share, total cost) |
| `design_summary` | installed capacity by technology |
| `dispatch` | hourly dispatch time series |
| `energy_balance` | supply/demand balance components |
| `upfront` | upfront (investment) costs |
| `annuities`, `expected_fixed_om`, `expected_cost_components` | annualized cost breakdown |
| `embodied`, `scenario_emissions` | emissions accounting |
| `renewable_design`, `battery_design`, `generator_design` | per-technology sizing |
| `renewable_inverter_design`, `battery_inverter_design`, `inverter_metrics` | inverter sizing/metrics |

The multi-year results object provides analogous tables resolved over the planning horizon.

## Interpreting outputs

Results span several levels — installed capacity, investment cost, operating cost, total or
present-value cost, energy production by technology, battery operation, generator use, grid
interaction, lost load and curtailment, and hourly time series. The
[Methodology](../methodology/overview.md) section explains which quantities are optimization
**variables**, which are **constraints**, and which are derived **accounting** outputs — for
example, the [objective](../methodology/objective-function.md) defines the cost tables, while
the [energy balance](../methodology/constraints.md#energy-balance-constraint) underlies the
dispatch and balance tables.

## Exporting

```python
paths = mgp.export_results(results)   # writes CSV/Excel to the project's results/ folder
```

`export_results` returns a mapping of output name → written file path. Pass `out_dir=` to
write elsewhere. Because everything is `pandas`, you can also work with the DataFrames
directly (`results.kpis.to_csv(...)`, plotting, further analysis).
