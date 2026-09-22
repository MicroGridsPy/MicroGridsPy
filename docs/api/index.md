# API Reference

The API Reference is generated automatically from the **MicroGridsPy Python package** using
**[mkdocstrings](https://mkdocstrings.github.io/)**. It reads the package statically from
`src/` via [Griffe](https://mkdocstrings.github.io/griffe/), so signatures, parameters and
return values stay synchronized with the source:

```text
Python source + docstrings
          ↓
      mkdocstrings (Griffe)
          ↓
      API Reference
```

When signatures or behavior change, update the **Python docstrings** and rebuild the
documentation — details should not be duplicated by hand in Markdown.

## Import convention

```python
import microgridspy as mgp
```

Everything documented here is re-exported at the top level of the `microgridspy` package.

## API organization

The reference is split into logical groups:

| Page | Public objects |
|---|---|
| [Project Management](project.md) | `create_project`, `validate_project`, `copy_project`, `rename_project`, `delete_project`, `TemplateSettings` |
| [Models](models.md) | `SteadyStateModel`, `MultiYearModel`, `InputValidationError` |
| [Optimization](optimization.md) | `solve`, `load_inputs` |
| [Results](results.md) | `load_results`, `export_results`, `TypicalYearResults`, `MultiYearResults`, input time-series helpers |

## Stability

`SteadyStateModel`, `MultiYearModel` and `InputValidationError` form the **stable core**.
The results dataclasses (`TypicalYearResults`, `MultiYearResults`) are **provisional** —
their tables may grow — until the 1.0 release.

## Workspace helpers

Projects live in a workspace directory. These helpers manage it:

::: microgridspy.set_workspace

::: microgridspy.list_projects

::: microgridspy.project_paths

::: microgridspy.project_exists

## Cross-links with methodology

The API Reference and the [Methodology](../methodology/overview.md) complement each other:
the Methodology explains *what* is modelled mathematically, while the API Reference explains
*how* the Python package exposes it. For example, the battery
[formulation](../methodology/battery.md) corresponds to the battery inputs and results
surfaced through the model classes.
