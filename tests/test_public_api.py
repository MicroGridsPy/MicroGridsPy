"""Package-level smoke tests for the public MicroGridsPy API.

These exercise the library the way a user would - create/validate projects,
inspect inputs, manage and solve them - using an isolated per-test workspace and
the bundled ``demo_typical_year`` example as realistic input data. They guard the
public surface (`__init__.__all__`) against packaging and API regressions.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

import microgridspy as mgp

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_PROJECT = REPO_ROOT / "projects" / "demo_typical_year"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """An isolated workspace with the demo_typical_year example copied in."""
    mgp.set_workspace(tmp_path)
    if EXAMPLE_PROJECT.exists():
        shutil.copytree(EXAMPLE_PROJECT, tmp_path / "projects" / "demo_typical_year")
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


@pytest.mark.skipif(not EXAMPLE_PROJECT.exists(), reason="demo_typical_year example not present")
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
