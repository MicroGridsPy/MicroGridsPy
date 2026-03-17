# generation_planning/modeling/data.py
from __future__ import annotations

import xarray as xr

from core.data_pipeline.loader import load_project_dataset
from core.data_pipeline.typical_year_parsing import (
    InputValidationError,
    _as_float,
    _as_float_or_nan,
    _as_str,
    _broadcast_to_scenario,
    _load_battery_yaml,
    _load_generator_and_fuel_yaml,
    _load_grid_yaml,
    _load_load_demand_csv,
    _load_price_csv_typical_year,
    _load_renewables_yaml,
    _load_resource_availability_csv,
    _normalize_weights,
    _read_json,
    _read_yaml,
    _write_grid_availability_csv,
)


def initialize_data(project_name: str, sets: xr.Dataset) -> xr.Dataset:
    return load_project_dataset(project_name, sets, mode="typical_year")

