# Data Contract for Canonical xr.Dataset

This document defines the canonical data interface between input templates/loaders and formulation-specific model algebra.

Scope:
- Shared across formulations: sets and data loading pipeline.
- Separate per formulation: variables, constraints, objective, and lightweight param aliases.

## 1. Canonical Dataset: `ds`

The loader returns one canonical `xarray.Dataset` (`ds`) for both formulations.

Rules:
- All parameter names are snake_case.
- Physical/economic parameters are data variables in `ds`.
- Runtime/model switches live in `ds.attrs["settings"]`.
- Optional components are represented by presence/absence of data vars plus explicit settings flags.

## 2. Required Coordinates

### 2.1 Base coords (always required)
- `period`: hourly index for the representative year, typically `0..8759`.
- `scenario`: scenario labels (at least one; deterministic case is `scenario_1`).
- `resource`: renewable resource labels.

### 2.2 Multi-year-only coords
- `year`: planning years labels (e.g., `2026..2045`, or `year_1..year_N` fallback).
- `inv_step`: investment step labels (e.g., `1..N` or canonical string labels).

### 2.3 Optional helper coords
- `curve_point`: generator efficiency curve points when partial-load modelling is enabled.

## 3. Required Attributes

`ds.attrs["settings"]` must exist and be a dictionary.

Minimum required keys:
- `project_name`: string
- `formulation`: `"steady_state"` or `"dynamic"`
- `unit_commitment`: bool
- `multi_scenario`:
  - `enabled`: bool
  - `n_scenarios`: int
- `optimization_constraints`:
  - `enforcement`: `"scenario_wise"` or `"expected"`
- `resources`:
  - `n_resources`: int
  - `resource_labels`: list[str]
- `grid`:
  - `on_grid`: bool
  - `allow_export`: bool

Recommended keys:
- `capacity_expansion` (dynamic): bool
- `inputs_loaded`: dict[path-like strings]
- `generator.partial_load_modelling_enabled`: bool

## 4. Time Series Storage Contract

### 4.1 Core operational series
- `load_demand`
  - Typical-year: dims `(period, scenario)`
  - Multi-year: dims `(period, year, scenario)`
- `resource_availability`
  - Typical-year: dims `(period, scenario, resource)`
  - Multi-year: dims `(period, year, scenario, resource)`

### 4.2 Scenario weights
- `scenario_weight`: dims `(scenario)`; normalized to sum to 1.

### 4.3 Grid time series (if on-grid)
- `grid_import_price`
  - Typical-year: `(period, scenario)`
  - Multi-year: `(period, year, scenario)`
- `grid_export_price` (only if export enabled; otherwise absent)
  - Same dims as import price.
- `grid_availability`
  - Typical-year: `(period, scenario)`
  - Multi-year: `(period, year, scenario)`

## 5. Technology Parameters Contract

Naming convention by component prefix:
- Renewables: `res_*`
- Battery: `battery_*`
- Generator: `generator_*`
- Fuel: `fuel_*`
- Grid: `grid_*`

### 5.1 Scalar vs indexed policy
- Use scalar (`()`) only when invariant across all indices.
- Use `(scenario)` for uncertainty/policy/economic operation terms varying by scenario (sizing decision is unique and shared across scenarios).
- Use `(resource)` for renewable technology vectors.
- Use `(inv_step)` (dynamic) for cohort/investment-step dependent investment terms.
- Use `(scenario, resource)` when scenario-dependent renewable attributes are required.

### 5.2 Optimization/policy parameters
Required canonical names:
- `min_renewable_penetration`: scalar or `(scenario)`
- `max_lost_load_fraction`: scalar or `(scenario)`
- `lost_load_cost_per_kwh`: scalar or `(scenario)`
- `land_availability_m2`: scalar
- `emission_cost_per_kgco2e`: scalar or `(scenario)`

## 6. Optional Components Representation

### 6.1 Grid
- Controlled by `ds.attrs["settings"]["grid"]` flags.
- If `on_grid = false`:
  - Grid data vars may be absent.
  - Model equations must branch by settings, not by guessing from missing vars only.
- If `on_grid = true` and `allow_export = false`:
  - `grid_export_price` may be absent.
  - Export variables/constraints should not be created.

### 6.2 Partial-load generator curve
- If enabled, `curve_point` coord and curve vars must be present.
- If disabled, curve vars absent and nominal efficiency formulation used.

## 7. Variable Naming Conventions (Model Variables)

To keep constraints/objective readable and stable across formulations:
- Design vars: `res_units`, `battery_units`, `generator_units`
- Operational vars:
  - `res_generation`
  - `generator_generation`
  - `fuel_consumption`
  - `battery_charge`, `battery_discharge`, `battery_soc`
  - `lost_load`
  - `grid_import`, `grid_export` (conditional)

Dims policy:
- Typical-year ops: `(period, scenario, ...)`
- Multi-year ops: `(period, year, scenario, ...)`

## 8. Formulation-Specific `params.py` Contract

Each formulation provides a lightweight alias module only.

Allowed responsibilities:
- `p = ds["..."]` aliases
- `settings = ds.attrs["settings"]`
- simple dim-safe selectors/reindexing helpers

Not allowed responsibilities:
- file I/O
- heavy validation
- template parsing logic

## 9. Validation Philosophy (Minimum Checks)

The shared loader/validation should enforce only:
- required coords exist
- required vars exist (depending on settings)
- dims are compatible with formulation
- scenario weights normalize
- key attrs/settings exist and have expected type/value domain

Do not over-constrain early experimentation.
Prefer warnings for soft issues, hard errors only for shape/semantic blockers.

## 10. Forward Compatibility Rules

When adding/removing parameters:
- Update schema spec first (`core/data_pipeline/schemas/*`).
- Regenerate templates from schema.
- Update shared loader mapping.
- Update formulation `params.py` aliases.
- Keep constraints/objective unchanged when possible.

This keeps equation files math-focused and minimizes refactor friction.
