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
├── ambient_temperature.csv       # hourly outdoor air temp      (semi-empirical ageing only)
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
  (typical-year vs. multi-year), the number of scenarios, grid flags, and global constraints
  (minimum renewable penetration, maximum lost-load share, land availability, carbon cost).
- **Time series** (CSV) — hourly demand, renewable availability, and optional grid tariffs
  and availability. One representative year of 8760 hourly rows.
- **Technology characterization** (YAML) — techno-economic parameters for renewables,
  battery, generators, fuel, and grid.
- **Optional curves** (CSV) — battery loss and generator part-load efficiency curves that
  activate the advanced formulations described in the [Methodology](../methodology/overview.md).
- **Battery degradation inputs** (conditional) — battery ageing has two modes. The default,
  **linear capacity fade**, needs only `battery.yaml → technical.capacity_degradation_rate_per_year`
  (a flat fraction per year; `0` disables ageing) and no extra files. **Semi-empirical
  degradation** (`battery_model.degradation_model.coefficients_enabled`, multi-year projects with
  the convex-loss efficiency model only) additionally needs `ambient_temperature.csv` — an hourly
  **outdoor air** series in °C with the same scenario/year layout as `load_demand.csv` — and these
  `battery.yaml → technical` fields: `chemistry` (`LFP` or `NMC`), `cycle_lifetime_to_eol_cycles`
  and `end_of_life_soh`, plus four with defaults: `cycle_life_reference_dod` (0.8),
  `cycle_life_reference_temperature_c` (25), `enclosure_temperature_rise_c` (10) and
  `calendar_fade_scale` (1.0). Leave `calendar_lifetime_years` as `null` to have the service life
  derived from the physics. One advanced key sits in `formulation.json →
  battery_model.degradation_model`: `cycle_test_duration_years` (default `null`), the duration of
  the datasheet cycle test, which removes the calendar ageing the test itself contained from the
  cycle calibration. See
  [Battery degradation](../methodology/battery.md#battery-degradation).

## Inspecting inputs before solving

You can assemble and inspect the input dataset without solving:

```python
import microgridspy as mgp

ds = mgp.load_inputs("my_site")  # the canonical xarray.Dataset
print(mgp.list_input_timeseries("my_site"))

# plot an input series (returns hourly + average-daily matplotlib figures)
fig_hourly, fig_daily = mgp.plot_input_timeseries("my_site", "load_demand")
```

The structure of `ds` is documented in the [Internal Data Contract](../data-reference/data-contract.md).

## Validation

Before solving, validate the project:

```python
mgp.validate_project("my_site")  # raises InputValidationError on problems
```

Validation checks that required coordinates and variables exist, that dimensions are
compatible with the chosen formulation, that scenario weights normalize, and that key
settings have the expected types and value domains.
