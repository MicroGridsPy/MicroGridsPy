# generation_planning/modeling/data.py
from __future__ import annotations

import xarray as xr

from microgridspy.data_pipeline.loader import load_project_dataset


def initialize_data(project_name: str, sets: xr.Dataset) -> xr.Dataset:
    return load_project_dataset(project_name, sets, mode="typical_year")
