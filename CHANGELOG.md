# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/MicroGridsPy/MicroGridsPy/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/MicroGridsPy/MicroGridsPy/releases/tag/v0.1.0
