"""Package-level smoke tests for the public MicroGridsPy API.

These exercise the library the way a user would - create/validate projects,
inspect inputs, manage and solve them - using an isolated per-test workspace and
the bundled ``demo_typical_year`` example as realistic input data. They guard the
public surface (`__init__.__all__`) against packaging and API regressions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import microgridspy as mgp


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """An isolated workspace with the bundled demo_typical_year example loaded in."""
    mgp.set_workspace(tmp_path)
    mgp.load_example("demo_typical_year")  # copies the packaged example into the workspace
    return tmp_path


def test_import_is_streamlit_free() -> None:
    # Importing the library must never pull in the optional GUI dependency.
    assert "streamlit" not in sys.modules
    # Every advertised public name must resolve.
    for name in mgp.__all__:
        assert hasattr(mgp, name), f"missing public name: {name}"


def test_create_validate_and_inspect(tmp_path: Path) -> None:
    mgp.set_workspace(tmp_path)
    paths = mgp.create_project(
        "unit_demo", formulation="steady_state", resources=["solar"], overwrite=True
    )
    assert paths.formulation_json.exists()
    assert "unit_demo" in mgp.list_projects()
    assert mgp.project_exists("unit_demo")

    mgp.validate_project("unit_demo")  # a fresh scaffold is valid

    ds = mgp.load_inputs("unit_demo")
    assert len(ds.data_vars) > 0
    assert "load_demand" in mgp.list_input_timeseries("unit_demo")


def test_project_management(tmp_path: Path) -> None:
    mgp.set_workspace(tmp_path)
    mgp.create_project("p_src", resources=["solar"], overwrite=True)

    mgp.copy_project("p_src", "p_copy")
    assert "p_copy" in mgp.list_projects()

    mgp.rename_project("p_copy", "p_renamed")
    assert "p_copy" not in mgp.list_projects()
    assert "p_renamed" in mgp.list_projects()

    mgp.delete_project("p_renamed")
    assert "p_renamed" not in mgp.list_projects()

    with pytest.raises(FileNotFoundError):
        mgp.delete_project("does_not_exist")


def test_validate_rejects_incomplete_project(tmp_path: Path) -> None:
    mgp.set_workspace(tmp_path)
    (tmp_path / "projects" / "empty").mkdir(parents=True)
    with pytest.raises(mgp.InputValidationError):
        mgp.validate_project("empty")


def test_bundled_examples_load_and_validate(tmp_path: Path) -> None:
    mgp.set_workspace(tmp_path)
    assert mgp.list_examples() == ["demo_multi_year", "demo_typical_year"]
    for name in mgp.list_examples():
        project = mgp.load_example(name, overwrite=True)
        assert project == name
        mgp.validate_project(name)  # the bundled example inputs are complete/valid


def test_solve_end_to_end(workspace: Path) -> None:
    try:
        model = mgp.solve("demo_typical_year", solver="highs")
    except Exception as exc:  # solver may be unavailable in some CI environments
        if "highs" in str(exc).lower() or "solver" in str(exc).lower():
            pytest.skip(f"HiGHS solver unavailable: {exc}")
        raise

    results = model.results()
    assert results.metadata["objective_value"] == pytest.approx(226704.9, rel=1e-3)
    assert len(results.dispatch) == 8760

    written = mgp.export_results(results, workspace / "out")
    assert len(written) > 0


def test_solve_example_one_liner(tmp_path: Path) -> None:
    mgp.set_workspace(tmp_path)
    try:
        model = mgp.solve_example("demo_typical_year", solver="highs")
    except Exception as exc:  # solver may be unavailable in some CI environments
        if "highs" in str(exc).lower() or "solver" in str(exc).lower():
            pytest.skip(f"HiGHS solver unavailable: {exc}")
        raise
    assert not model.results().kpis.empty
