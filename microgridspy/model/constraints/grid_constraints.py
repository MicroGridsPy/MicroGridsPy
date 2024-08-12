import xarray as xr
import linopy
from linopy import Model
from microgridspy.model.parameters import ProjectParameters
from typing import Dict

def add_grid_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add grid-related constraints to the Linopy model."""
    
    add_maximum_power_from_grid_constraint(model, settings, sets, param, var)
    
    if settings.advanced_settings.grid_connection_type == 1:
        add_maximum_power_to_grid_constraint(model, settings, sets, param, var)
    
    if settings.advanced_settings.multiobjective_optimization:
        add_grid_emission_constraints(model, settings, sets, param, var)

def add_maximum_power_from_grid_constraint(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraint for maximum power that can be drawn from the grid."""
    
    year_grid_connection = settings.grid_params.year_grid_connection
    max_grid_power = settings.grid_params.maximum_grid_power

    for year in sets.years.values:
        if year >= year_grid_connection:
            if settings.advanced_settings.milp_formulation:
                model.add_constraints(
                    var['energy_from_grid'].sel(years=year) <= var['single_flow_grid'].sel(years=year) * param['GRID_AVAILABILITY'].sel(years=year) * max_grid_power,
                    name=f"Maximum Power From Grid - Year {year}")
            else:
                model.add_constraints(
                    var['energy_from_grid'].sel(years=year) <= param['GRID_AVAILABILITY'].sel(years=year) * max_grid_power,
                    name=f"Maximum Power From Grid - Year {year}")
        else:
            model.add_constraints(
                var['energy_from_grid'].sel(years=year) == 0,
                name=f"No Power From Grid - Year {year}")

def add_maximum_power_to_grid_constraint(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraint for maximum power that can be fed to the grid."""
    
    year_grid_connection = settings.grid_params.year_grid_connection
    max_grid_power = settings.grid_params.maximum_grid_power

    for year in sets.years.values:
        if year >= year_grid_connection:
            if settings.advanced_settings.milp_formulation:
                model.add_constraints(
                    var['energy_to_grid'].sel(years=year) <= (1 - var['single_flow_grid'].sel(years=year)) * param['GRID_AVAILABILITY'].sel(years=year) * max_grid_power,
                    name=f"Maximum Power To Grid - Year {year}")
            else:
                model.add_constraints(
                    var['energy_to_grid'].sel(years=year) <= param['GRID_AVAILABILITY'].sel(years=year) * max_grid_power,
                    name=f"Maximum Power To Grid - Year {year}")
        else:
            model.add_constraints(
                var['energy_to_grid'].sel(years=year) == 0,
                name=f"No Power To Grid - Year {year}")

def add_grid_emission_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraints for grid emissions calculation."""
    
    grid_emission_factor = settings.grid_params.national_grid_specific_co2_emissions
    
    # Calculate emissions for each scenario, year, and period
    model.add_constraints(
        var['grid_emission'] == var['energy_from_grid'] * grid_emission_factor / 1000,  # Convert to kg CO2
        name="Grid Emission Calculation")
    
    # Sum up emissions for each scenario
    model.add_constraints(
        var['scenario_grid_emission'] == var['grid_emission'].sum(dim=['years', 'periods']),
        name="Scenario Grid Emission Calculation")