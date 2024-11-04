import xarray as xr
import linopy
from linopy import Model
from microgridspy.model.parameters import ProjectParameters
from typing import Dict

def add_generator_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraints for generator."""

    add_generator_max_energy_production_constraint(model, settings, sets, param, var)

    if settings.advanced_settings.capacity_expansion:
        add_generator_capacity_expansion_constraints(model, settings, sets, param, var)

    if settings.generator_params.partial_load:
        add_generator_partial_load_constraints(model, settings, sets, param, var)

    if settings.advanced_settings.multiobjective_optimization:
        add_generator_emissions_constraints(model, settings, sets, param, var)


def add_generator_max_energy_production_constraint(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Calculate generator energy production considering installation lifetime for each step."""
    is_brownfield = settings.advanced_settings.brownfield

    if is_brownfield:
        years = sets.years.values
        steps = sets.steps.values
        step_duration = settings.advanced_settings.step_duration
        # Create a list of tuples with years and steps
        years_steps_tuples = [((years[i] - years[0]) + 1, steps[i // step_duration]) for i in range(len(years))]

        for year in sets.years.values:
            # Retrieve the step for the current year
            step = years_steps_tuples[year - years[0]][1]

            for gen in sets.generator_types.values:

                # Calculate total_age over 'generator_types' and 'years'
                total_age = param['GENERATOR_EXISTING_YEARS'].sel(generator_types=gen) + (year - years[0])

                # Calculate lifetime_exceeded over 'generator_types' and 'years'
                lifetime_exceeded = total_age > param['GENERATOR_LIFETIME'].sel(generator_types=gen)

                # Calculate total_production considering just the new capacity
                max_production = (var['generator_units'].sel(steps=step) * param['GENERATOR_NOMINAL_CAPACITY']).sel(generator_types=gen)

                if lifetime_exceeded is False:
                    # Calculate total_production considering also the existing capacity
                    max_production += (param['GENERATOR_EXISTING_CAPACITY']).sel(generator_types=gen)

                # Add constraints for all generator types at once
                model.add_constraints(var['generator_energy_production'].sel(years=year, generator_types=gen) <= max_production, name=f"Generator Energy Production Constraint - Year {year}, Type {gen}")
    else:
        # Non-brownfield scenario
        max_production = var['generator_units'] * param['GENERATOR_NOMINAL_CAPACITY']
        model.add_constraints(var['generator_energy_production'] <= max_production, name="Generator Energy Production Constraint")
"""
    # Ensure that production does not exceed demand (assuming 'DEMAND' is over 'years' and 'generator_types')
    model.add_constraints(
        var['generator_energy_production'] <= param['DEMAND'],
        name="Maximum Energy Production Constraint for Generator")
"""

def add_generator_capacity_expansion_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraints for generator capacity expansion."""

    for step in sets.steps.values[1:]:
        model.add_constraints(
            var['generator_units'].sel(steps=step) >= var['generator_units'].sel(steps=step - 1),
            name=f"Generator Min Step Units Constraint - Step {step}")
        
def add_generator_partial_load_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    
    model.add_constraints(var['generator_energy_partial_load'] >= var['generator_partial_load'] * (param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_MIN_LOAD']), 
                          name=f"Minimum Generator Partial Load Energy Production Constraint")
    
    model.add_constraints(var['generator_energy_partial_load'] <= var['generator_partial_load'] * param['GENERATOR_NOMINAL_CAPACITY'], 
                          name=f"Maximum Generator Partial Load Energy Production Constraint")
    
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    # Create a list of tuples with years and steps
    years_steps_tuples = [((years[i] - years[0]) + 1, steps[i // step_duration]) for i in range(len(years))]

    for year in years:
        # Retrieve the step for the current year
        step = years_steps_tuples[year - years[0]][1]
        model.add_constraints(
            var['generator_energy_production'].sel(years=year) >= (var['generator_full_load'].sel(steps=step) * param['GENERATOR_NOMINAL_CAPACITY']) + var['generator_energy_partial_load'].sel(years=year), 
            name=f"Generator Partial Load Energy Production Constraint - Year {year}") 
        
    for step in steps:
        model.add_constraints(
            var['generator_units'].sel(steps=step) <= var['generator_full_load'].sel(steps=step) + 1, 
            name=f"Generator Partial Load Units Constraint - Step {step}")
        
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
    