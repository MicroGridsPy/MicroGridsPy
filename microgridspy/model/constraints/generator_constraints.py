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


def add_generator_max_energy_production_constraint(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Calculate generator energy production considering installation lifetime for each step."""
            
    model.add_constraints(var['generator_energy_production'] <= var['generator_units'] * param['GENERATOR_NOMINAL_CAPACITY'], 
                          name=f"Generator Energy Production Constraint")
    
    model.add_constraints(var['generator_energy_production'] <= param['DEMAND'], name=f"Maximum Energy Production Constraint for generator")

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