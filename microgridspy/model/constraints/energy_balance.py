from typing import Dict

import xarray as xr
import linopy
from linopy import Model

from microgridspy.model.parameters import ProjectParameters


def add_energy_balance_constraints(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid: bool) -> None:
    """Add energy balance constraint."""
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    # Calculate total renewable energy production
    total_res_energy_production = var['res_energy_production'].sum('renewable_sources')
    total_curtailment = var['curtailment'].sum('renewable_sources')

    for year in sets.years.values:
        step = years_steps_tuples[year - years[0]][1]
        
        # Initialize total_energy_production for each year
        yearly_energy_production: linopy.LinearExpression = total_res_energy_production.sel(steps=step) - total_curtailment.sel(years=year)
            
        if has_battery:
            yearly_energy_production += var['battery_outflow'].sel(years=year) - var['battery_inflow'].sel(years=year)

        if has_generator:
            total_generator_energy_production = var['generator_energy_production'].sum('generator_types')
            yearly_energy_production += total_generator_energy_production.sel(years=year)

        if settings.project_settings.lost_load_fraction > 0:
            yearly_energy_production += var['lost_load'].sel(years=year)

        # Add the energy balance constraint for each year
        model.add_constraints(yearly_energy_production == param['DEMAND'].sel(years=year), name=f"Energy Balance Constraint - Year {year}")


