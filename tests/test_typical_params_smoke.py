from __future__ import annotations

from core.data_pipeline.loader import load_project_dataset
from core.typical_year_model.params import get_params
from core.typical_year_model.sets import initialize_sets


def test_get_params_smoke_test_typical() -> None:
    sets = initialize_sets("test_typical")
    ds = load_project_dataset("test_typical", sets, mode="typical_year")
    p = get_params(ds)
    assert p.load_demand is not None
    assert p.resource_availability is not None
    assert isinstance(p.settings, dict)

