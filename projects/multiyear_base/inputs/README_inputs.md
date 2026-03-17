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

Years: 2026, 2027, 2028, 2029, 2030

## resource_availability.csv
- Hourly **resource availability** template (8760 rows).
- Units: **capacity factor** (per unit of nominal capacity, typically 0..1).
- **Three-row header**:
  - Row 1: scenario labels
  - Row 2: year labels
  - Row 3: resource labels
- A meta column `meta/hour` provides the hour index (0..8759).

Scenarios: scenario_1

Years: 2026, 2027, 2028, 2029, 2030

Resources: Solar

## renewables.yaml
- Renewable techno-economic parameters.
- Parameters can vary by resources, scenario and (if enabled) by investment step.

Renewables Technologies: Solar PV


## battery.yaml
- Battery techno-economic parameters.
- Parameters can vary by scenario and (if enabled) by investment step.
