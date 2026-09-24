"""The two formulations are named typical_year and multi_year, everywhere."""

from __future__ import annotations

import json

import pytest

import microgridspy as mgp
from microgridspy.io.formulation import MULTI_YEAR, TYPICAL_YEAR, VALID_FORMULATIONS


def test_canonical_names() -> None:
    assert TYPICAL_YEAR == "typical_year"
    assert MULTI_YEAR == "multi_year"
    assert VALID_FORMULATIONS == (TYPICAL_YEAR, MULTI_YEAR)


def test_model_classes_are_named_after_the_formulations() -> None:
    assert mgp.TypicalYearModel.__name__ == "TypicalYearModel"
    assert mgp.MultiYearModel.__name__ == "MultiYearModel"
    assert "TypicalYearModel" in mgp.__all__
    # The pre-0.4 SteadyStateModel alias was removed, not deprecated.
    assert not hasattr(mgp, "SteadyStateModel")


@pytest.mark.parametrize("formulation", VALID_FORMULATIONS)
def test_create_project_writes_the_name_it_was_given(tmp_path, formulation: str) -> None:
    mgp.set_workspace(tmp_path)
    paths = mgp.create_project(
        f"case_{formulation}",
        formulation=formulation,
        horizon_years=5 if formulation == MULTI_YEAR else None,
        overwrite=True,
    )
    payload = json.loads(paths.formulation_json.read_text(encoding="utf-8"))
    assert payload["core_formulation"] == formulation


def test_unknown_formulation_is_rejected(tmp_path) -> None:
    mgp.set_workspace(tmp_path)
    with pytest.raises(mgp.InputValidationError):
        mgp.create_project("bad_case", formulation="steady_state", overwrite=True)
    with pytest.raises(mgp.InputValidationError):
        mgp.create_project("bad_case", formulation="quarterly", overwrite=True)


def test_bundled_examples_declare_canonical_names() -> None:
    from microgridspy.io.examples import EXAMPLES, _examples_root

    for name in EXAMPLES:
        payload = json.loads(
            (_examples_root() / name / "inputs" / "formulation.json").read_text(encoding="utf-8")
        )
        assert payload["core_formulation"] in VALID_FORMULATIONS, name
