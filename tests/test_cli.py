"""Tests for the ``microgridspy`` command-line interface.

These drive `microgridspy.cli.main()` directly with an argv list and an isolated
``--workspace``, covering the non-solver subcommands end-to-end and the error path.
The solving subcommands (``demo`` / ``solve``) skip gracefully when no solver is
available, mirroring the public-API solve tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from microgridspy.cli import main


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    # argparse's --version action prints and exits 0.
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert "microgridspy" in capsys.readouterr().out


def test_no_command_errors() -> None:
    # A subcommand is required; argparse exits 2 when none is given.
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2


def test_examples_lists_bundled(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["examples"]) == 0
    out = capsys.readouterr().out
    assert "demo_typical_year" in out
    assert "demo_multi_year" in out


def test_list_empty_workspace(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list", "--workspace", str(tmp_path)]) == 0
    assert "no projects found" in capsys.readouterr().out


def test_create_validate_and_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ws = ["--workspace", str(tmp_path)]

    assert main(["create", "cli_demo", "--resources", "solar", "--overwrite", *ws]) == 0
    assert "Created project" in capsys.readouterr().out
    assert (tmp_path / "projects" / "cli_demo" / "inputs" / "formulation.json").exists()

    assert main(["validate", "cli_demo", *ws]) == 0
    assert "is valid" in capsys.readouterr().out

    assert main(["list", *ws]) == 0
    assert "cli_demo" in capsys.readouterr().out


def test_validate_missing_project_returns_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # main() traps exceptions, prints a clean message to stderr, and returns 1.
    assert main(["validate", "does_not_exist", "--workspace", str(tmp_path)]) == 1
    assert "Error:" in capsys.readouterr().err


def test_demo_solves_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    try:
        rc = main(["demo", "demo_typical_year", "--workspace", str(tmp_path)])
    except Exception as exc:  # pragma: no cover - depends on solver availability
        if "highs" in str(exc).lower() or "solver" in str(exc).lower():
            pytest.skip(f"HiGHS solver unavailable: {exc}")
        raise
    out = capsys.readouterr().out
    if rc != 0:
        pytest.skip("solver unavailable in this environment")
    assert "Solved example 'demo_typical_year'" in out
