# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
