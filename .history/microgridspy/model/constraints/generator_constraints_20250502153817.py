import xarray as xr
import linopy
from linopy import Model
from microgridspy.model.parameters import ProjectParameters
from typing import Dict

def add_generator_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraints for generator."""

    add_generator_max_energy_production_constraint(model, settings, sets, param, var)
    add_generator_fuel_consumption_constraints(model, settings, sets, param, var)

    if settings.advanced_settings.capacity_expansion:
        add_generator_capacity_expansion_constraints(model, settings, sets, param, var)


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
                lifetime_exceeded = bool(total_age > param['GENERATOR_LIFETIME'].sel(generator_types=gen))

                # Calculate total_production considering just the new capacity
                max_production = (var['generator_units'].sel(steps=step) * param['GENERATOR_NOMINAL_CAPACITY']).sel(generator_types=gen)

                if not lifetime_exceeded:
                    # Calculate total_production considering also the existing capacity
                    max_production += (param['GENERATOR_EXISTING_CAPACITY']).sel(generator_types=gen)

                # Add constraints for all generator types
                model.add_constraints(var['generator_energy_production'].sel(years=year, generator_types=gen) <= max_production, name=f"Generator Energy Production Constraint - Year {year}, Type {gen}")
    else:
        # Non-brownfield scenario
        max_production = var['generator_units'] * param['GENERATOR_NOMINAL_CAPACITY']
        model.add_constraints(var['generator_energy_production'] <= max_production, name="Generator Energy Production Constraint")

def add_generator_fuel_consumption_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """
    Add constraints linking generator fuel consumption and energy production using nominal efficiency and fuel LHV.
    """
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    # Create a list of tuples with years and steps
    years_steps_tuples = [((years[i] - years[0]) + 1, steps[i // step_duration]) for i in range(len(years))]

    for year in years:
        # Retrieve the step for the current year
        step = years_steps_tuples[year - years[0]][1]
        for gen in sets.generator_types.values:
            # Define variables
            gen_energy = var['generator_energy_production'].sel(years=year, generator_types=gen)
            gen_fuel_consumption = var['generator_fuel_consumption'].sel(years=year, generator_types=gen)

            if settings.generator_params.partial_load == False:
                # Define parameters
                nominal_efficiency = param['GENERATOR_NOMINAL_EFFICIENCY'].sel(generator_types=gen)
                fuel_lhv = param['FUEL_LHV'].sel(generator_types=gen)

                model.add_constraints(
                    gen_fuel_consumption == gen_energy / (nominal_efficiency * fuel_lhv),
                    name=f"Fuel Consumption Constraint - Year {year}, Type {gen}")
            else:
                # Loop over all segments (piecewise parts)
                n_segments = param['GENERATOR_SAMPLED_RELATIVE_OUTPUT'].shape[1] - 1  # number of segments = number of points - 1

                for seg in range(n_segments):
                    # Fuel power points at current and next sampling point
                    p0 = param['GENERATOR_SAMPLED_RELATIVE_OUTPUT'].sel(sample_points=seg) * param['GENERATOR_NOMINAL_CAPACITY'].sel(generator_types=gen)
                    p1 = param['GENERATOR_SAMPLED_RELATIVE_OUTPUT'].sel(sample_points=seg+1) * param['GENERATOR_NOMINAL_CAPACITY'].sel(generator_types=gen)

                    # Fuel consumption samples at current and next sampling point
                    fc0 = p0 / (param['GENERATOR_SAMPLED_EFFICIENCY'].sel(sample_points=seg, generator_types=gen) * param['FUEL_LHV'].sel(generator_types=gen))
                    fc1 = p1 / (param['GENERATOR_SAMPLED_EFFICIENCY'].sel(sample_points=seg+1, generator_types=gen) * param['FUEL_LHV'].sel(generator_types=gen))

                    # Slope between the two sampled points
                    if (p1 - p0) != 0:
                        slope = (fc1 - fc0) / (p1 - p0)
                    else:
                        slope = 0.0  # flat segment

                    # Add constraints vectorized
                    model.add_constraints(var['generator_fuel_consumption'].sel(years=year, generator_types=gen) >= 
                                          slope * (var['generator_energy_production'].sel(years=year, generator_types=gen) - p0 * var['generator_units'].sel(steps=step, generator_types=gen)) + fc0 * var['generator_units'].sel(steps=step, generator_types=gen), 
                                          name=f"Partial Load Constraint - Segment {seg}, Year {year}, Type {gen}")

def add_generator_capacity_expansion_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraints for generator capacity expansion."""

    for step in sets.steps.values[1:]:
        model.add_constraints(
            var['generator_units'].sel(steps=step) >= var['generator_units'].sel(steps=step - 1),
            name=f"Generator Min Step Units Constraint - Step {step}")



    