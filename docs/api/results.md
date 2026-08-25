# Results API

How optimization outputs are loaded, exported, and inspected. The structured results
objects hold analysis-ready `pandas` DataFrames (capacity, costs, dispatch, KPIs). For
guidance on **interpreting** these outputs, see the User Guide [Results](../user-guide/results.md)
page.

## `load_results`

::: microgridspy.load_results

## `export_results`

::: microgridspy.export_results

## `TypicalYearResults`

The structured results object returned by the typical-year formulation
(`SteadyStateModel.results()`).

::: microgridspy.TypicalYearResults
    options:
      show_root_heading: true
      members: false

## `MultiYearResults`

The structured results object returned by the multi-year formulation.

::: microgridspy.MultiYearResults
    options:
      show_root_heading: true
      members: false

## Input time-series inspection

Helpers to list and plot a project's input time series without solving.

::: microgridspy.list_input_timeseries

::: microgridspy.plot_input_timeseries
