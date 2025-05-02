import linopy
import xarray as xr
from typing import Dict
from linopy import Model
from microgridspy.model.parameters import ProjectParameters

def add_res_emissions_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Calculate the emissions for renewable sources."""
    
    res_emissions = linopy.LinearExpression = 0

    for step in sets.steps.values:
        # Initial emissions
        if step == 1:
            res_emissions += (var['res_units'].sel(steps=step) * 
                                    param['RES_NOMINAL_CAPACITY'] * param['RES_UNIT_CO2_EMISSION']).sum('renewable_sources')
        # Subsequent emissions
        else:
            res_emissions += ((var['res_units'].sel(steps=step) - var['res_units'].sel(steps=step - 1)) * 
                                 param['RES_NOMINAL_CAPACITY'] * param['RES_UNIT_CO2_EMISSION']).sum('renewable_sources')

    # Add the constraint
    model.add_constraints(var['res_emission'] == res_emissions,name="RES Emissions Constraint")

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

def add_project_emissions(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid_connection: bool
) -> None:
    """Add total project emissions constraint, based on technology-level emissions."""

    # Add technology-specific emissions constraints first
    add_res_emissions_constraints(model, settings, sets, param, var)

    if has_battery:
        add_battery_emissions_constraints(model, settings, sets, param, var)

    if has_generator:
        add_generator_emissions_constraints(model, settings, sets, param, var)

    if has_grid_connection:
        add_grid_emission_constraints(model, settings, sets, param, var)

    # Sum all technology emissions into a single total project emissions expression
    total_emissions = var['res_emission']

    if has_battery:
        total_emissions += var['battery_emission']
    
    if has_generator:
        total_emissions += var['gen_emission']

    if has_grid_connection:
        total_emissions += var['scenario_grid_emission']

    # Add total project emissions constraint
    try:
        model.add_constraints(var['total_project_emissions'] == total_emissions, name="Total Project Emissions Constraint")
    except Exception as e:
        raise ValueError(f"Error in calculating total project emissions: {str(e)}")
