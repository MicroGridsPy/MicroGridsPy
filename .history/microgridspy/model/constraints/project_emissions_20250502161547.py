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

def add_battery_emissions_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Calculate the emissions for battery."""
    
    battery_emissions = linopy.LinearExpression = 0

    for step in sets.steps.values:
        # Initial emissions
        if step == 1:
            battery_emissions += (var['battery_units'].sel(steps=step) * 
                                 param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_UNIT_CO2_EMISSION'])
        # Subsequent emissions
        else:
            battery_emissions += ((var['battery_units'].sel(steps=step) - var['battery_units'].sel(steps=step - 1)) * 
                                 param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_UNIT_CO2_EMISSION'])

    # Add the constraint
    model.add_constraints(var['battery_emission'] == battery_emissions, name="Battery Emissions Constraint")

def add_generator_emissions_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Calculate the emissions for generator types."""
    
    generator_emissions = linopy.LinearExpression = 0

    for step in sets.steps.values:
        # Initial emissions
        if step == 1:
            generator_emissions += (var['generator_units'].sel(steps=step) * 
                                    param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_UNIT_CO2_EMISSION']).sum('generator_types')
        # Subsequent emissions
        else:
            generator_emissions += ((var['generator_units'].sel(steps=step) - var['generator_units'].sel(steps=step - 1)) * 
                                    param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_UNIT_CO2_EMISSION']).sum('generator_types')

    # Add the constraint
    model.add_constraints(var['gen_emission'] == generator_emissions, name="Generator Emissions Constraint")
    # Add fuel emissions constraint
    model.add_constraints(var['fuel_emission'] == var['generator_fuel_consumption'] * param['FUEL_CO2_EMISSION'], name="Fuel Emissions Constraint")

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
    total_emissions = 0

    if has_battery:
        total_emissions += var['battery_emission'].sum()

    if has_generator:
        total_emissions += var['gen_emission'].sum()
        total_emissions += var['fuel_emission'].sum(dim=['years', 'generator_types', 'periods'])

    if has_grid_connection:
        total_emissions += var['scenario_grid_emission']

    # RES is optional too
    total_emissions += var['res_emission'].sum()

    # Add total project emissions constraint
    try:
        model.add_constraints(var['scenario_co2_emission'] == total_emissions, name="Total Scenario Emissions Constraint")

        model.add_constraints(
            var['total_emission'] == (var["scenario_co2_emission"] * param['SCENARIO_WEIGHTS']).sum('scenarios'),
            name="Total Emissions Weighted Constraint"
        )

    except Exception as e:
        raise ValueError(f"Error in calculating total project emissions: {str(e)}")
