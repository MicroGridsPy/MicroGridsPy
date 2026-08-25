# Planning Modes

MicroGridsPy supports two planning formulations. The choice is recorded in
`formulation.json` at project creation and drives which model class is used.

| Mode | `create_project(formulation=...)` | Main use | Time representation |
|---|---|---|---|
| **Typical-year** | `"steady_state"` | screening / steady-state studies | one representative year |
| **Multi-year** | `"dynamic"` | long-term planning | explicit horizon and investment steps |

## Practical differences

**Typical-year** minimizes an equivalent annual cost for a single representative year that
is assumed to repeat. It is the fastest option and is ideal for feasibility screening,
technology comparisons, and multi-scenario studies where tractability matters. Intertemporal
discounting does **not** affect sizing in this mode.

**Multi-year** represents an explicit horizon $y = 1,\dots,H$ with year- and
scenario-dependent inputs. It supports **capacity expansion** across predefined investment
steps (with non-decreasing installed capacity), technology-specific WACC-based annuities,
a social discount rate, replacement cycles, and salvage value for long-lived assets.

## Selecting a mode in code

```python
import microgridspy as mgp

# typical-year
mgp.create_project("screening", formulation="steady_state", resources=["solar"])

# multi-year with a 20-year horizon and four 5-year investment steps
mgp.create_project(
    "expansion",
    formulation="dynamic",
    horizon_years=20,
    capacity_expansion=True,
    investment_steps_years=[5, 5, 5, 5],
    resources=["solar", "wind"],
)
```

`solve()`, `load_results()` and `load_inputs()` auto-detect the formulation from
`formulation.json`, so you don't need to repeat it. For the mathematical distinction, see
[Methodology → Planning Modes](../methodology/planning-modes.md).
