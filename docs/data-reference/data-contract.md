# Internal Data Contract

This page is **developer-facing** documentation. It defines the canonical internal data
interface — a single `xarray.Dataset` — passed between the input loaders and the
formulation-specific model algebra. It is *not* the primary user input guide; for that, see
the [Data Reference](overview.md).

```text
User input files (CSV / YAML / JSON)
      ↓
Data loading / validation
      ↓
Canonical internal data contract  ← this page
      ↓
Formulation-specific model
      ↓
Linopy optimization model
```

The contract makes the interface between modules explicit and stable, which is what allows
the loading and formulation layers to evolve independently — and what makes future
interoperability with other Python energy-access tools tractable.

!!! note "Source of truth"
    This page mirrors [`docs/DATA_CONTRACT.md`](https://github.com/MicroGridsPy/MicroGridsPy/blob/microgridspy-packaging/docs/DATA_CONTRACT.md)
    in the repository. When the internal dataset changes, update the contract first, then the
    loaders and the formulation `params.py` aliases.

## 1. Canonical dataset `ds`

The loader returns one canonical `xarray.Dataset` (`ds`) for both formulations.

- All parameter names are `snake_case`.
- Physical/economic parameters are **data variables** in `ds`.
- Runtime/model switches live in `ds.attrs["settings"]`.
- Optional components are represented by presence/absence of data variables **plus** explicit
  settings flags.

## 2. Required coordinates

**Base coords (always required)**

- `period` — hourly index for the representative year, typically `0..8759`.
- `scenario` — scenario labels (at least one; deterministic case is `scenario_1`).
- `resource` — renewable resource labels.

**Multi-year-only coords**

- `year` — planning-year labels (e.g. `2026..2045`, or `year_1..year_N` fallback).
- `inv_step` — investment-step labels (e.g. `1..N` or canonical string labels).

**Optional helper coords**

- `curve_point` — generator efficiency-curve points when partial-load modelling is enabled.

## 3. Required attributes

`ds.attrs["settings"]` must exist and be a dictionary. Minimum required keys:

- `project_name`: `str`
- `formulation`: `"steady_state"` or `"dynamic"`
- `unit_commitment`: `bool`
- `multi_scenario`: `{ enabled: bool, n_scenarios: int }`
- `optimization_constraints`: `{ enforcement: "scenario_wise" | "expected" }`
- `resources`: `{ n_resources: int, resource_labels: list[str] }`
- `grid`: `{ on_grid: bool, allow_export: bool }`

Recommended keys: `capacity_expansion` (dynamic, `bool`), `inputs_loaded`
(`dict[path-like]`), `generator.partial_load_modelling_enabled` (`bool`).

## 4. Time-series storage contract

**Core operational series**

| Variable | Typical-year dims | Multi-year dims |
|---|---|---|
| `load_demand` | `(period, scenario)` | `(period, year, scenario)` |
| `resource_availability` | `(period, scenario, resource)` | `(period, year, scenario, resource)` |

**Scenario weights** — `scenario_weight`: dims `(scenario)`, normalized to sum to 1.

**Grid time series (if on-grid)**

| Variable | Typical-year dims | Multi-year dims |
|---|---|---|
| `grid_import_price` | `(period, scenario)` | `(period, year, scenario)` |
| `grid_export_price` *(export only)* | `(period, scenario)` | `(period, year, scenario)` |
| `grid_availability` | `(period, scenario)` | `(period, year, scenario)` |

## 5. Technology parameters contract

Naming by component prefix: renewables `res_*`, battery `battery_*`, generator
`generator_*`, fuel `fuel_*`, grid `grid_*`.

**Scalar vs. indexed policy**

- Scalar `()` only when invariant across all indices.
- `(scenario)` for uncertainty/policy/economic operation terms varying by scenario (the
  sizing decision itself is unique and shared across scenarios).
- `(resource)` for renewable technology vectors.
- `(inv_step)` (dynamic) for cohort/investment-step-dependent investment terms.
- `(scenario, resource)` when scenario-dependent renewable attributes are required.

**Required canonical optimization/policy names**

- `min_renewable_penetration`: scalar or `(scenario)`
- `max_lost_load_fraction`: scalar or `(scenario)`
- `lost_load_cost_per_kwh`: scalar or `(scenario)`
- `land_availability_m2`: scalar
- `emission_cost_per_kgco2e`: scalar or `(scenario)`

## 6. Optional components

**Grid** — controlled by `settings["grid"]` flags. If `on_grid = false`, grid data vars may
be absent and equations must branch by settings, not by guessing from missing vars. If
`on_grid = true` and `allow_export = false`, `grid_export_price` may be absent and export
variables/constraints must not be created.

**Partial-load generator curve** — if enabled, the `curve_point` coord and curve vars must be
present; if disabled, curve vars are absent and the nominal-efficiency formulation is used.

## 7. Model variable naming

- Design vars: `res_units`, `battery_units`, `generator_units`.
- Operational vars: `res_generation`, `generator_generation`, `fuel_consumption`,
  `battery_charge`, `battery_discharge`, `battery_soc`, `lost_load`, `grid_import`,
  `grid_export` (conditional).

Dims policy: typical-year ops `(period, scenario, ...)`; multi-year ops
`(period, year, scenario, ...)`.

## 8. Formulation-specific `params.py`

Each formulation provides a lightweight **alias module** only.

- **Allowed:** `p = ds["..."]` aliases, `settings = ds.attrs["settings"]`, simple dim-safe
  selectors/reindexing helpers.
- **Not allowed:** file I/O, heavy validation, template-parsing logic.

## 9. Validation philosophy

The shared loader/validation enforces only: required coords exist; required vars exist
(depending on settings); dims are compatible with the formulation; scenario weights
normalize; key attrs/settings exist with expected type/value domain. Prefer **warnings** for
soft issues and hard errors only for shape/semantic blockers — do not over-constrain early
experimentation.

## 10. Forward-compatibility rules

When adding/removing parameters: update the schema spec first (`core/data_pipeline/schemas/*`),
regenerate templates from the schema, update the shared loader mapping, update the
formulation `params.py` aliases, and keep constraints/objective unchanged when possible. This
keeps equation files math-focused and minimizes refactor friction.
