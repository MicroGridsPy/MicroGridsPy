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

Years: 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035

## resource_availability.csv
- Hourly **resource availability** template (8760 rows).
- Units: **capacity factor** (per unit of nominal capacity, typically 0..1).
- **Three-row header**:
  - Row 1: scenario labels
  - Row 2: year labels
  - Row 3: resource labels
- A meta column `meta/hour` provides the hour index (0..8759).

Scenarios: scenario_1

Years: 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035

Resources: Solar

## renewables.yaml
- Renewable techno-economic parameters.
- Parameters can vary by resource and, for investment-side data, by investment step.

- Multi-year capacity expansion uses a shared-technology interpretation: `investment.by_step` varies across steps, while technical parameters stay shared.

Renewables Technologies: Solar_PV


## battery.yaml
- Battery techno-economic parameters.
- In the multi-year formulation, battery investment data are written by step while technical parameters remain shared.

## generator.yaml
- Generator and fuel techno-economic parameters.
- In the multi-year formulation, generator investment data are written by step while technical and fuel-physics data remain shared. Yearly fuel prices remain scenario-based.
- `generator.technical.efficiency_curve_csv` is automatically set from the Project Setup choice:
  - `null` for constant generator efficiency in partial load
  - `generator_efficiency_curve.csv` for efficiency-curve mode
