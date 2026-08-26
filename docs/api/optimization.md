# Optimization API

The programmatic interface used to build and solve the model. `solve` is the one-line
convenience wrapper over the [model classes](models.md); `load_inputs` assembles the input
dataset without solving, for inspection.

The mathematical optimization problem — objective function and constraints — is documented
separately in the [Methodology](../methodology/objective-function.md) section.

## `solve`

::: microgridspy.solve

## `solve_example`

One-call end-to-end quick start over the [bundled examples](project.md#example-projects) —
works straight after `pip install`.

::: microgridspy.solve_example

## `load_inputs`

::: microgridspy.load_inputs
