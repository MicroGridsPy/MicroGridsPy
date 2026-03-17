from __future__ import annotations

from core.data_pipeline.loader import load_project_dataset
from core.multi_year_model.sets import initialize_sets


def test_multi_year_loader_smoke_test_multiyear() -> None:
    sets = initialize_sets("test_multiyear")
    ds = load_project_dataset("test_multiyear", sets, mode="multi_year")

    assert "load_demand" in ds.data_vars
    assert "resource_availability" in ds.data_vars

    assert ds["load_demand"].dims == ("period", "year", "scenario")
    assert ds["resource_availability"].dims == ("period", "year", "scenario", "resource")

