# Input Data

A MicroGridsPy case study is defined entirely by files inside a **project folder**. Running
[`create_project(...)`](../api/project.md#create_project) writes these files as templates; you
then fill them with your data and validate the project before solving.

## Project folder layout

```text
my_site/
├── formulation.json              # mode, scenarios, grid flags, global constraints
├── load_demand.csv               # hourly demand time series
├── resource_availability.csv     # hourly renewable availability by resource
├── renewables.yaml               # renewable techno-economic inputs
├── battery.yaml                  # battery techno-economic inputs
├── generator.yaml                # generator + fuel inputs
├── grid.yaml                     # grid line/outage inputs        (on-grid only)
├── grid_import_price.csv         # hourly import tariff           (on-grid only)
├── grid_export_price.csv         # hourly export tariff           (export only)
├── grid_availability.csv         # derived availability matrix    (generated)
├── battery_efficiency_curve.csv  # advanced battery loss curve    (optional)
├── generator_efficiency_curve.csv# part-load generator curve      (optional)
└── README_inputs.md              # human-readable summary
```

Which files are needed depends on the formulation and on flags such as `on_grid` and
`allow_export`. The full field-by-field breakdown — formats, units, dimensions, and when
each file is mandatory — is in the [Data Reference](../data-reference/overview.md).

## Categories of input

- **Formulation & settings** (`formulation.json`) — selects the planning mode
  (steady-state vs. dynamic), the number of scenarios, grid flags, and global constraints
  (minimum renewable penetration, maximum lost-load share, land availability, carbon cost).
- **Time series** (CSV) — hourly demand, renewable availability, and optional grid tariffs
  and availability. One representative year of 8760 hourly rows.
- **Technology characterization** (YAML) — techno-economic parameters for renewables,
  battery, generators, fuel, and grid.
- **Optional curves** (CSV) — battery loss and generator part-load efficiency curves that
  activate the advanced formulations described in the [Methodology](../methodology/overview.md).

## Inspecting inputs before solving

You can assemble and inspect the input dataset without solving:

```python
import microgridspy as mgp

ds = mgp.load_inputs("my_site")          # the canonical xarray.Dataset
print(mgp.list_input_timeseries("my_site"))

# plot an input series (returns hourly + average-daily matplotlib figures)
fig_hourly, fig_daily = mgp.plot_input_timeseries("my_site", "load_demand")
```

The structure of `ds` is documented in the [Internal Data Contract](../data-reference/data-contract.md).

## Validation

Before solving, validate the project:

```python
mgp.validate_project("my_site")   # raises InputValidationError on problems
```

Validation checks that required coordinates and variables exist, that dimensions are
compatible with the chosen formulation, that scenario weights normalize, and that key
settings have the expected types and value domains.
