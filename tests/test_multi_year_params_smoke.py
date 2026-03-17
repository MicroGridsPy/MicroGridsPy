from __future__ import annotations

from core.data_pipeline.loader import load_project_dataset
from core.multi_year_model.params import get_params
from core.multi_year_model.sets import initialize_sets


def test_get_params_smoke_test_multiyear() -> None:
    sets = initialize_sets("test_multiyear")
    ds = load_project_dataset("test_multiyear", sets, mode="multi_year")
    p = get_params(ds)
    assert isinstance(p.settings, dict)
    assert p.load_demand is not None
    assert p.resource_availability is not None

