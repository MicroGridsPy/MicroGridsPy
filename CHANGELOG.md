# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-09-25

### Fixed
- **Multi-year battery energy balance closes at the end of the horizon.** `soc_balance`
  linked `soc[t] -> soc[t+1]` only up to the second-to-last period, and `soc_year_link_*`
  only carried state *between* years, so the state implied after the final period of the
  final year was unbounded: the battery could discharge energy it had never stored in that
  last step. New `soc_terminal_upper` / `soc_terminal_lower` constraints apply the same
  bounds to that state. The typical-year formulation was never affected — its `soc_cyclic`
  constraint already closed the loop.
  The leak only bound when the battery would otherwise be empty at the horizon end, so
  long hourly runs are unlikely to change: on `demo_multi_year` the final-hour discharge
  (18.9 kWh) was already covered by stored energy (664.2 kWh). Short or reduced-resolution
  horizons could be affected materially.

### Changed
- **BREAKING — the two formulations are now named `typical_year` and `multi_year`
  everywhere**: in `formulation.json`, in `create_project(formulation=...)`, in the CLI
  `--formulation` choices and in the model class names. Previously the same two concepts
  were spelled three ways (`steady_state`/`dynamic` in data and the API, `typical_year`/
  `multi_year` in module names and docs, `SteadyStateModel`/`MultiYearModel` in code).
  Projects created by earlier releases must set `core_formulation` to the new name; the
  old spellings now raise `InputValidationError` instead of being translated.
- **BREAKING — `SteadyStateModel` was removed.** Use `TypicalYearModel`.
- **One exception type.** `InputValidationError` was defined separately in 20 modules, so
  `except microgridspy.InputValidationError` did not catch errors raised by most of the
  package. It now lives in `microgridspy.errors` and every layer raises that one class.
- **One capital-recovery factor.** `_crf` was implemented five times, with three different
  zero-rate tolerances and three different answers for a non-positive lifetime, so the
  annuity used in the objective could differ from the annuity shown in the results. It now
  lives in `microgridspy.finance.crf`. For a non-positive lifetime it returns `nan`
  (previously `0.0`, `nan` or `inf` depending on which copy ran).

### Removed
- Dead code: `export/csv_reader.py`, `export/manifest.py`, `export/yaml_reader.py`,
  `app/typical_year_file_results_page.py` and 17 unreferenced functions.
- The `error_cls` parameter threaded through the IO and coercion helpers, which existed
  only to select between the duplicate exception classes.
- The duplicated session state on the Optimization page: a solved run was stored four ways
  (`gp_sets`/`gp_data`/`gp_vars`, the results bundle and the two typed results objects).
  Only the bundle and the typed results remain.
- `pre-commit` from the `dev` extra — the project has no pre-commit configuration.

## [0.2.0] - 2026-08-24

### Added
- Project management: `delete_project`, `copy_project`, `rename_project`.
- `load_inputs()` — assemble a project's input dataset without solving.
- `list_input_timeseries()` and `plot_input_timeseries()` — input time-series
  plots returned as matplotlib figures.
- `to_excel()` method on `TypicalYearResults` / `MultiYearResults`.
- `microgridspy` command-line interface (`list` / `create` / `validate` / `solve`).

### Changed
- Removed outdated files (broken `requirements.txt`, `environment_nobuilds.yml`,
  documentation PDFs); README rewritten for `pip install` and the Python API.
- Home page: the PDF previews were replaced with a documentation-link placeholder.
- The `formulation.json` builder is shared between the GUI and the library.
- Whole codebase formatted and linted with ruff.
- Added a package-level test suite (`tests/test_public_api.py`); `ruff check`,
  `ruff format --check`, and `pytest` all pass.

### Fixed
- `results_summary()` now reads the objective from `model.objective.value`, so the
  headline objective value is populated instead of `None`.
- Restored 3 multi-year inverter tests whose fixture was missing the
  `year_inv_step` mapping.

## [0.1.0] - 2026-08-24

First pip-installable release.

### Added
- `pyproject.toml` (Hatchling + hatch-vcs): git-tag-driven versioning, the
  `microgridspy-gui` console entry point, and optional extras `gui`, `highs`,
  `gurobi`, `dev`.
- `src/` layout; the package is importable as `microgridspy`.
- Public API:
  - `SteadyStateModel`, `MultiYearModel` with `solve_single_objective()`,
    `results()` and `results_summary()`.
  - `solve()`, `load_results()`, `export_results()` convenience functions.
  - `create_project()`, `validate_project()` for headless project scaffolding.
  - `set_workspace()`, `list_projects()`, `project_paths()`, `project_exists()`.
  - `TypicalYearResults`, `MultiYearResults`, `InputValidationError`.
- `MICROGRIDSPY_WORKSPACE` environment variable to locate the projects folder.

### Changed
- Renamed the importable package from `core` to `microgridspy`.
- Moved the Streamlit GUI into the `microgridspy.app` subpackage; installing the
  core no longer requires Streamlit (it is gated behind the `gui` extra).
- The GUI's project-creation writes `formulation.json` via the shared
  `microgridspy.io.project_setup.build_formulation_payload`, so the app and the
  library stay in lock-step.

### Fixed
- Optimal HiGHS solves were reported as "no feasible solution" because the
  result gate grepped the solver log for a Gurobi-specific marker. Detection now
  uses the in-memory linopy solution, so HiGHS and Gurobi both work.

[Unreleased]: https://github.com/MicroGridsPy/MicroGridsPy/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/MicroGridsPy/MicroGridsPy/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/MicroGridsPy/MicroGridsPy/releases/tag/v0.1.0
