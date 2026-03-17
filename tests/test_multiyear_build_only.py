from __future__ import annotations

from core.multi_year_model.model import MultiYearModel


def test_multiyear_build_only_smoke() -> None:
    m = MultiYearModel("test_multiyear")

    m._initialize_sets()
    m._initialize_data()
    m._initialize_vars()
    m._initialize_constraints()

    assert {"period", "year", "scenario", "inv_step"}.issubset(set(m.data.dims))
    assert isinstance(m.vars, dict)
    assert len(m.vars) > 0
    assert m.model is not None
    assert hasattr(m.model, "constraints")
    assert len(m.model.constraints) > 0

