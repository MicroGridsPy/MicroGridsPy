# Model API

The public model classes representing the two optimization formulations. Both are
constructed from a project name and expose `solve_single_objective(...)`, `results()`, and
`results_summary()`.

The detailed mathematical description of each formulation belongs in the
[Methodology](../methodology/overview.md) section rather than in the generated API.

## `TypicalYearModel`

The typical-year formulation.

::: microgridspy.TypicalYearModel

## `MultiYearModel`

The multi-year (dynamic) capacity-expansion formulation.

::: microgridspy.MultiYearModel

## `InputValidationError`

Raised when a project's inputs are missing or inconsistent.

::: microgridspy.InputValidationError
