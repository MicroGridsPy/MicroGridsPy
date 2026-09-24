# Planning Modes

MicroGridsPy supports two planning formulations. The choice is recorded in
`formulation.json` at project creation and drives which model class is used.

| Mode | `create_project(formulation=...)` | Main use | Time representation |
|---|---|---|---|
| **Typical-year** | `"typical_year"` | screening / steady-state studies | one representative year |
| **Multi-year** |  `"multi_year"` | long-term planning | explicit horizon and investment steps |

!!! warning "Renamed in 0.4 — breaking change"
    These two formulations were previously called `steady_state` and `dynamic`, and the
    typical-year model class was `SteadyStateModel`. The names above are now the only
    ones accepted, in `formulation.json`, in the API and in the CLI.

    **Projects created before 0.4 must be updated.** Change `core_formulation` in the
    project's `formulation.json` from `steady_state` to `typical_year`, or from `dynamic`
    to `multi_year`. Passing an old name now raises `InputValidationError` rather than
    being silently translated. In code, replace `SteadyStateModel` with `TypicalYearModel`.

## Practical differences

**Typical-year** minimizes an equivalent annual cost for a single representative year that
is assumed to repeat. It is the fastest option and is ideal for feasibility screening,
technology comparisons, and multi-scenario studies where tractability matters. Intertemporal
discounting does **not** affect sizing in this mode.

**Multi-year** represents an explicit horizon $y = 1,\dots,H$ with year- and
scenario-dependent inputs. It supports **capacity expansion** across predefined investment
steps (with non-decreasing installed capacity), technology-specific WACC-based annuities,
a social discount rate, and cohort-based annuity persistence (implicit like-for-like
replacement) over the modelled horizon.

## Selecting a mode in code

```python
import microgridspy as mgp

# typical-year
mgp.create_project("screening", formulation="typical_year", resources=["solar"])

# multi-year with a 20-year horizon and four 5-year investment steps
mgp.create_project(
    "expansion",
    formulation="multi_year",
    horizon_years=20,
    capacity_expansion=True,
    investment_steps_years=[5, 5, 5, 5],
    resources=["solar", "wind"],
)
```

`solve()`, `load_results()` and `load_inputs()` auto-detect the formulation from
`formulation.json`, so you don't need to repeat it. For the mathematical distinction, see
[Methodology → Planning Modes](../methodology/planning-modes.md).
