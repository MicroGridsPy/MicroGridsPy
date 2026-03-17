from __future__ import annotations

from core.multi_year_model.model import MultiYearModel


def test_multiyear_objective_build_smoke() -> None:
    m = MultiYearModel("test_multiyear")
    m._initialize_sets()
    m._initialize_data()
    m._initialize_vars()
    m._initialize_constraints()
    m._initialize_objective()

    assert m.model is not None
    assert getattr(m.model, "objective", None) is not None

