import linopy
import xarray as xr
from microgridspy.model.parameters import ProjectParameters

from typing import Dict
from linopy import Model

def add_project_emissions(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid_connection: bool) -> None:
    """Add project emissions constraints."""

    