# Architecture

MicroGridsPy is organized around a clean separation between data loading, a canonical
internal dataset, formulation-specific model algebra, and results export:

```text
Project / input data (CSV / YAML / JSON)
        ↓
Validation and loading        (data_pipeline, io)
        ↓
Canonical internal dataset    (the DATA_CONTRACT: one xarray.Dataset)
        ↓
Formulation-specific model    (typical_year_model / multi_year_model)
        ↓
Linopy optimization model
        ↓
Results                       (export, visualization)
```

## Package layout

The package lives under `src/microgridspy/`:

| Module | Responsibility |
|---|---|
| `api.py` | high-level convenience API (`solve`, `load_results`, `export_results`, `load_inputs`, …) re-exported at the top level |
| `io/` | project scaffolding, templates, paths, workspace helpers, JSON/CSV formats |
| `data_pipeline/` | input loaders and surrogate models (battery loss/fade, generator part-load) that assemble the canonical dataset |
| `typical_year_model/` | steady-state sets, params, variables, constraints, objective, and `SteadyStateModel` |
| `multi_year_model/` | dynamic formulation with investment-step lifecycle logic and `MultiYearModel` |
| `export/` | structured results objects and CSV/Excel export |
| `visualization/` | input and result plotting |
| `app/` | optional Streamlit GUI (installed only with the `[gui]` extra) |
| `cli.py` | the `microgridspy` command-line interface |

## The data contract as the central interface

The [Internal Data Contract](../data-reference/data-contract.md) is the pivot of the whole
design. Both formulations consume the **same** canonical `xarray.Dataset`; they differ only
in their `variables`, `constraints`, `objective`, and lightweight `params.py` aliases. This
is what keeps the equation files math-focused and lets the loading and formulation layers
evolve independently.

The same separation is what makes future integration with other energy-access tools (GIS
planning, demand and resource modules) tractable: each stage can share well-defined data
interfaces rather than bespoke coupling.

## Two formulations, one economic core

The typical-year and multi-year models share the bottom-up
[cost-accounting](../methodology/cost-accounting.md) structure. The typical-year model is,
economically, the steady-state limit of the dynamic one — a property that guides how new
features should be added to both consistently.
