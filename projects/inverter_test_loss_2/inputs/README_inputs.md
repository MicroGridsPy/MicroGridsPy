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


Renewables Technologies: Solar PV


## battery.yaml
- Battery techno-economic parameters.
- In the typical-year formulation, battery investment data use a single base step and technical parameters remain shared.

## battery_efficiency_curve.csv
- Optional battery conversion-efficiency curve used only when `formulation.json -> battery_model.loss_model = convex_loss_epigraph`.
- Preferred semantics: the CSV stores normalized efficiency multipliers relative to the scalar efficiencies in `battery.yaml`, with the full-load row equal to `1.0`.
- Legacy absolute-efficiency curves are still accepted for backward compatibility.
- Columns:
  - `relative_power_pu`: relative DC-side battery power in (0,1]
  - `charge_efficiency`: normalized charge-efficiency multiplier (actual eta = `battery.technical.charge_efficiency * charge_efficiency`)
  - `discharge_efficiency`: normalized discharge-efficiency multiplier (actual eta = `battery.technical.discharge_efficiency * discharge_efficiency`)

## generator.yaml
- Generator and fuel techno-economic parameters.
- In the typical-year formulation, generator investment data use a single base step while technical parameters remain shared and fuel inputs stay scenario-based.
- `generator.technical.efficiency_curve_csv` is automatically set from the Project Setup choice:
  - `null` for constant generator efficiency in partial load
  - `generator_efficiency_curve.csv` for efficiency-curve mode

## generator_efficiency_curve.csv
- Optional generator partial-load efficiency curve.
- Used only when `generator.technical.efficiency_curve_csv` points to this file.
- The parser always normalizes the curve to a single zero-output anchor internally. You may include an explicit `0.0` row or provide only positive-load points.
- Preferred semantics: `Efficiency [-]` is a normalized multiplier relative to the corresponding generator nominal full-load efficiency, with the full-load row equal to `1.0`.
- Legacy absolute-efficiency curves are still accepted for backward compatibility.
- Columns:
  - `Relative Power Output [-]`
  - `Efficiency [-]`
