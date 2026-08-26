# Inputs folder

This folder contains user-editable input templates.

## load_demand.csv
- Hourly **load demand** template (8760 rows).
- Units: **kWh per hour** (energy during each hour).
- **Two-row header**:
  - Row 1: scenario labels
  - Row 2: year labels
- A meta column `meta/hour` provides the hour index (0..8759).

Scenarios: scenario_1

Years: typical_year

## resource_availability.csv
- Hourly **resource availability** template (8760 rows).
- Units: **capacity factor** (per unit of nominal capacity, typically 0..1).
- **Three-row header**:
  - Row 1: scenario labels
  - Row 2: year labels
  - Row 3: resource labels
- A meta column `meta/hour` provides the hour index (0..8759).

Scenarios: scenario_1

Years: typical_year

Resources: Solar Irradiation

## renewables.yaml
- Renewable techno-economic parameters.
- Parameters can vary by resource and, for investment-side data, by investment step.
- Renewable inverter CAPEX is modeled explicitly, with its own inverter lifetime input.


Renewables Technologies: Solar PV


## battery.yaml
- Battery techno-economic parameters.
- In the typical-year formulation, battery investment data use a single base step and technical parameters remain shared.
- Battery inverter CAPEX is modeled explicitly, and battery power-energy coupling is expressed through optional `max_charge_c_rate` / `max_discharge_c_rate` inputs.

## generator.yaml
- Generator and fuel techno-economic parameters.
- In the typical-year formulation, generator investment data use a single base step while technical parameters remain shared and fuel inputs stay scenario-based.
- `generator.technical.efficiency_curve_csv` is automatically set from the Project Setup choice:
  - `null` for constant generator efficiency in partial load
  - `generator_efficiency_curve.csv` for efficiency-curve mode
