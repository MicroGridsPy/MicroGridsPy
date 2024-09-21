import xarray as xr
import linopy
from linopy import Model
from microgridspy.model.parameters import ProjectParameters
from typing import Dict

def add_res_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraints for renewable energy sources."""
    # Calculate the renewable energy production
    add_renewable_energy_production_constraints(model, settings, sets, param, var)
    
    if settings.advanced_settings.capacity_expansion:
        # Add minimum step units constraint for renewables
        add_renewables_capacity_expansion_constraints(model, settings, sets, param, var)
    
    if settings.project_settings.land_availability > 0:
        # Add land availability constraint
        add_land_availability_constraints(model, settings, sets, param, var)

    if settings.advanced_settings.multiobjective_optimization:
        # Calculate the emissions for renewable sources
        add_res_emissions_constraints(model, settings, sets, param, var)

def add_renewable_energy_production_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Calculate renewable energy production considering installation lifetime for each step."""

    if settings.advanced_settings.brownfield:
        years = sets.years.values
        steps = sets.steps.values
        step_duration = settings.advanced_settings.step_duration
        # Create a list of tuples with years and steps
        years_steps_tuples = [((years[i] - years[0]) + 1, steps[i // step_duration]) for i in range(len(years))]
        # Initialize the energy production
        res_energy_production = 0

        # Calculate total_age over 'res_types' and 'years'
        total_age = param['RES_EXISTING_YEARS'] + (years - years[0])

        # Expand 'param['RES_LIFETIME']' to align with 'total_age'
        res_lifetime = param['RES_LIFETIME']

        # Ensure 'res_lifetime' has dimensions over 'res_types' and 'years'
        res_lifetime = res_lifetime.broadcast_like(total_age)

        # Calculate lifetime_exceeded over 'res_types' and 'years'
        lifetime_exceeded = total_age > res_lifetime

        print("res_lifetime dimensions:", res_lifetime.dims)
        print("res_lifetime shape:", res_lifetime.shape)
        print("total_age dimensions:", total_age.dims)
        print("total_age shape:", total_age.shape)

        for year in sets.years.values:
            # Retrieve the step for the current year
            step = years_steps_tuples[year - years[0]][1]

            # Select data for the current year
            lifetime_exceeded_year = lifetime_exceeded.sel(years=year)

            # Existing capacity production over 'res_types'
            existing_capacity_production = ((param['RES_EXISTING_CAPACITY'] / param['RES_NOMINAL_CAPACITY']) * param['RESOURCE'] * param['RES_INVERTER_EFFICIENCY'])

            # New capacity production over 'res_types'
            new_capacity_production = (var['res_units'].sel(steps=step) * param['RESOURCE'] * param['RES_INVERTER_EFFICIENCY'])

            # Total energy production variable over 'res_types'
            res_energy_production = var['res_energy_production'].sel(steps=step)

            # Use xr.where to handle the conditional logic over arrays
            total_production = xr.where(
                lifetime_exceeded_year,
                new_capacity_production,
                new_capacity_production + existing_capacity_production)

            # Add constraints over 'res_types'
            model.add_constraints(res_energy_production == total_production, name=f"Renewable Energy Production Constraint - Year {year}")
    else:
        # Non-brownfield scenario
        res_energy_production = (var['res_units'] * param['RESOURCE'] * param['RES_INVERTER_EFFICIENCY'])

        model.add_constraints(var['res_energy_production'] == res_energy_production, name="Renewable Energy Production Constraint")

def add_renewables_capacity_expansion_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add minimum step units constraint for renewables."""

    for step in sets.steps.values[1:]:
        # Add the constraint
        model.add_constraints(
            var['res_units'].sel(steps=step) >= var['res_units'].sel(steps=step - 1),
            name=f"Renewables Min Step Units Constraint - Step {step}")


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

def add_land_availability_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add land availability constraint."""

    res_land_use: linopy.LinearExpression = 0

    for step in sets.steps.values:
        # Initial land use
        if step == 1:
            res_land_use += (var['res_units'].sel(steps=step) * 
                                param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_AREA']).sum('renewable_sources')
        # Subsequent land use
        else:
            res_land_use += ((var['res_units'].sel(steps=step) - var['res_units'].sel(steps=step - 1)) * 
                                param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_AREA']).sum('renewable_sources')
            
    # Add the constraint
    model.add_constraints(res_land_use <= param['LAND_AVAILABILITY'], name="Land Availability Constraint")

