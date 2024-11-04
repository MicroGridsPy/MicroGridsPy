import xarray as xr
import numpy as np
import linopy
from linopy import Model
from microgridspy.model.parameters import ProjectParameters
from typing import Dict

def add_battery_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraints for battery energy storage."""
    add_battery_state_of_charge_constraints(model, settings, sets, param, var)

    if settings.advanced_settings.milp_formulation:
        add_battery_single_flow_constraints(model, settings, sets, param, var)
    else:
        add_battery_flow_constraints(model, settings, sets, param, var)

    if settings.advanced_settings.capacity_expansion:
        add_battery_capacity_expansion_constraints(model, settings, sets, param, var)
    
    if settings.project_settings.battery_independence > 0:
        add_min_battery_independence_constraints(model, settings, sets, param, var)

    if settings.advanced_settings.multiobjective_optimization:
        add_battery_emissions_constraints(model, settings, sets, param, var)

def add_battery_state_of_charge_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    is_first_year = xr.DataArray(sets.years == sets.years[0], dims='years')
    is_first_period = xr.DataArray(sets.periods == sets.periods[0], dims='periods')
    is_brownfield = settings.advanced_settings.brownfield

    # Initial battery capacity (only battery units multiplied by nominal capacity)
    battery_capacity = var['battery_units'].sel(steps=1) * param['BATTERY_NOMINAL_CAPACITY']

    # If brownfield, add existing capacity
    if is_brownfield: battery_capacity += param['BATTERY_EXISTING_CAPACITY']

    # Contribution from battery units (without existing capacity)
    first_year_first_period = (
        (battery_capacity * param['BATTERY_INITIAL_SOC']) -
        (var['battery_outflow'] / param['BATTERY_DISCHARGE_EFFICIENCY']) +
        (var['battery_inflow'] * param['BATTERY_CHARGE_EFFICIENCY'])
    ).where(is_first_year & is_first_period, 0)

    other_years_first_period = (
        var['battery_soc'].shift(years=1, fill_value=0).sel(periods=sets.periods[-1]) -
        var['battery_outflow'] / param['BATTERY_DISCHARGE_EFFICIENCY'] +
        var['battery_inflow'] * param['BATTERY_CHARGE_EFFICIENCY']
    ).where(~is_first_year & is_first_period, 0)

    other_periods = (
        var['battery_soc'].shift(periods=1, fill_value=0) -
        var['battery_outflow'] / param['BATTERY_DISCHARGE_EFFICIENCY'] +
        var['battery_inflow'] * param['BATTERY_CHARGE_EFFICIENCY']
    ).where(~is_first_period, 0)

    battery_state_of_charge = first_year_first_period + other_years_first_period + other_periods

    model.add_constraints(
        var['battery_soc'] == battery_state_of_charge, name="Battery State of Charge Constraint")
    
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    # Create a list of tuples with years and steps
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]

    for year in sets.years.values:
        step = years_steps_tuples[year - years[0]][1]
        if is_brownfield:
            # Calculate the total age of the existing capacity at each year
            total_age = param['BATTERY_EXISTING_YEARS'] + (year - sets.years[0])
        
            # Create a boolean mask for renewable sources that have exceeded their lifetime
            lifetime_exceeded = total_age > param['BATTERY_LIFETIME']

            if lifetime_exceeded is False:
                model.add_constraints(
                    var['battery_soc'].sel(years=year) <= (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) + param['BATTERY_EXISTING_CAPACITY'],
                    name=f"Battery Maximum Charge Constraint - Year {year}")

                model.add_constraints(
                    var['battery_soc'].sel(years=year) >= (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY'] + param['BATTERY_EXISTING_CAPACITY']) * (1 - param['BATTERY_DEPTH_OF_DISCHARGE']),
                    name=f"Battery Minimum Charge Constraint - Year {year}")
            else:
                model.add_constraints(
                    var['battery_soc'].sel(years=year) <= (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']),
                    name=f"Battery Maximum Charge Constraint - Year {year}")

                model.add_constraints(
                    var['battery_soc'].sel(years=year) >= (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) * (1 - param['BATTERY_DEPTH_OF_DISCHARGE']),
                    name=f"Battery Minimum Charge Constraint - Year {year}")
        else:
            model.add_constraints(
                var['battery_soc'].sel(years=year) <= (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']),
                name=f"Battery Maximum Charge Constraint - Year {year}")

            model.add_constraints(
                var['battery_soc'].sel(years=year) >= (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) * (1 - param['BATTERY_DEPTH_OF_DISCHARGE']),
                name=f"Battery Minimum Charge Constraint - Year {year}")

def add_battery_flow_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraints for battery power (charge and discharge rates)."""
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    is_brownfield = settings.advanced_settings.brownfield
    # Create a list of tuples with years and steps
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    for year in sets.years.values:
        step = years_steps_tuples[year - years[0]][1]
        if is_brownfield:
            # Calculate the total age of the existing capacity at each year
            total_age = param['BATTERY_EXISTING_YEARS'] + (year - sets.years[0])
        
            # Create a boolean mask for renewable sources that have exceeded their lifetime
            lifetime_exceeded = total_age > param['BATTERY_LIFETIME']

            if lifetime_exceeded is False:
                model.add_constraints(
                    var['battery_max_charge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY'] + param['BATTERY_EXISTING_CAPACITY']) / param['MAXIMUM_BATTERY_CHARGE_TIME'],
                    name=f"Battery Maximum Charge Power Constraint - Year {year}")
        
                model.add_constraints(
                    var['battery_max_discharge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY'] + param['BATTERY_EXISTING_CAPACITY']) / param['MAXIMUM_BATTERY_DISCHARGE_TIME'],
                    name=f"Battery Maximum Discharge Power Constraint - Year {year}")
            else:
                model.add_constraints(
                    var['battery_max_charge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) / param['MAXIMUM_BATTERY_CHARGE_TIME'],
                    name=f"Battery Maximum Charge Power Constraint - Year {year}")
        
                model.add_constraints(
                    var['battery_max_discharge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) / param['MAXIMUM_BATTERY_DISCHARGE_TIME'],
                    name=f"Battery Maximum Discharge Power Constraint - Year {year}")
        else:
            model.add_constraints(
                var['battery_max_charge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) / param['MAXIMUM_BATTERY_CHARGE_TIME'],
                name=f"Battery Maximum Charge Power Constraint - Year {year}")
        
            model.add_constraints(
                var['battery_max_discharge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) / param['MAXIMUM_BATTERY_DISCHARGE_TIME'],
                name=f"Battery Maximum Discharge Power Constraint - Year {year}")
    
    for year in sets.years.values:
        step = years_steps_tuples[year - years[0]][1]
        model.add_constraints(
            var['battery_inflow'].sel(years=year) <= var['battery_max_charge_power'].sel(steps=step) * param['DELTA_TIME'],
            name=f"Battery Upper Inflow Constraint - Year {year}")

        model.add_constraints(
            var['battery_outflow'].sel(years=year) <= var['battery_max_discharge_power'].sel(steps=step) * param['DELTA_TIME'],
            name=f"Battery Upper Outflow Constraint - Year {year}")

    model.add_constraints(var['battery_outflow'] <= param['DEMAND'], name="Battery Maximum Outflow Constraint")

def add_battery_capacity_expansion_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraints for battery capacity expansion."""

    for step in sets.steps.values[1:]:
        model.add_constraints(
            var['battery_units'].sel(steps=step) >= var['battery_units'].sel(steps=step - 1),
            name=f"Battery Min Step Units Constraint - Step {step}")

def add_min_battery_independence_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add minimum capacity constraints for the battery."""
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    is_brownfield = settings.advanced_settings.brownfield
    # Create a list of tuples with years and steps
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]

    if is_brownfield:
        for year in sets.years.values:
            step = years_steps_tuples[year - years[0]][1]
            # Calculate the total age of the existing capacity at each year
            total_age = param['BATTERY_EXISTING_YEARS'] + (year - sets.years[0])
        
            # Create a boolean mask for renewable sources that have exceeded their lifetime
            lifetime_exceeded = total_age > param['BATTERY_LIFETIME']

            if lifetime_exceeded is False:
                model.add_constraints((var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) + param['BATTERY_EXISTING_CAPACITY']  >= param['BATTERY_MIN_CAPACITY'],
                name=f"Battery Minimum Capacity Constraint - Year {year}")
            else:
                model.add_constraints((var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) >= param['BATTERY_MIN_CAPACITY'],
                name=f"Battery Minimum Capacity Constraint - Year {year}")
    else:
        model.add_constraints((var['battery_units'] * param['BATTERY_NOMINAL_CAPACITY']) >= param['BATTERY_MIN_CAPACITY'],
        name=f"Battery Minimum Capacity Constraint")

def add_battery_single_flow_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add single flow constraints for battery charge and discharge."""
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    is_brownfield = settings.advanced_settings.brownfield
    # Create a list of tuples with years and steps
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    for year in sets.years.values:
        step = years_steps_tuples[year - years[0]][1]
        if is_brownfield:
            # Calculate the total age of the existing capacity at each year
            total_age = param['BATTERY_EXISTING_YEARS'] + (year - sets.years[0])
        
            # Create a boolean mask for renewable sources that have exceeded their lifetime
            lifetime_exceeded = total_age > param['BATTERY_LIFETIME']

            if lifetime_exceeded is False:
                model.add_constraints(
                    var['battery_max_charge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY'] + param['BATTERY_EXISTING_CAPACITY']) / param['MAXIMUM_BATTERY_CHARGE_TIME'],
                    name=f"Battery Maximum Charge Power Constraint - Year {year}")
        
                model.add_constraints(
                    var['battery_max_discharge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY'] + param['BATTERY_EXISTING_CAPACITY']) / param['MAXIMUM_BATTERY_DISCHARGE_TIME'],
                    name=f"Battery Maximum Discharge Power Constraint - Year {year}")
            else:
                model.add_constraints(
                    var['battery_max_charge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) / param['MAXIMUM_BATTERY_CHARGE_TIME'],
                    name=f"Battery Maximum Charge Power Constraint - Year {year}")
        
                model.add_constraints(
                    var['battery_max_discharge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) / param['MAXIMUM_BATTERY_DISCHARGE_TIME'],
                    name=f"Battery Maximum Discharge Power Constraint - Year {year}")
        else:
            model.add_constraints(
                var['battery_max_charge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) / param['MAXIMUM_BATTERY_CHARGE_TIME'],
                name=f"Battery Maximum Charge Power Constraint - Year {year}")
        
            model.add_constraints(
                var['battery_max_discharge_power'].sel(steps=step) == (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY']) / param['MAXIMUM_BATTERY_DISCHARGE_TIME'],
                name=f"Battery Maximum Discharge Power Constraint - Year {year}")

    for year in sets.years.values:
        step = years_steps_tuples[year - years[0]][1]
        model.add_constraints(
            var['battery_outflow'].sel(years=year) <= var['single_flow_bess'] * var['battery_max_discharge_power'].sel(steps=step) * param['DELTA_TIME'],
            name=f"Battery Single Flow Discharge Constraint - Year {year}")

        model.add_constraints(
            var['battery_inflow'].sel(years=year) <= (var['battery_max_charge_power'].sel(steps=step) * param['DELTA_TIME']) - (var['single_flow_bess'] * var['battery_max_charge_power'].sel(steps=step) * param['DELTA_TIME']),
            name=f"Battery Single Flow Charge Constraint - Year {year}")
    
    model.add_constraints(
        var['battery_outflow'] <= param['DEMAND'], name="Battery Maximum Outflow Constraint")
    
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
