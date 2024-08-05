from typing import Dict, List

import xarray as xr
import linopy
from linopy import Model

from microgridspy.model.parameters import ProjectParameters

def add_cost_calculation_constraints(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid: bool) -> None:
    """
    Add cost calculation constraints to the model.

    :param model: The optimization model
    :param settings: Project parameters
    :param sets: Dataset containing sets
    :param param: Dataset containing parameters
    :param var: Dictionary of variables
    :param has_battery: Boolean indicating whether the system has a battery
    :param has_generator: Boolean indicating whether the system has a generator
    :param has_grid: Boolean indicating whether the system has a grid connection
    """
    try:
        add_investment_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid)
        # Optimization goal: NPC
        if settings.project_settings.optimization_goal == 0:
            add_fixed_om_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid, actualized=True)
            if settings.advanced_settings.milp_formulation and settings.generator_params.partial_load:
                add_scenario_variable_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid, partial_load=True, actualized=True)
            else:
                add_scenario_variable_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid, partial_load = False, actualized=True)
            add_salvage_value(model, settings, sets, param, var, has_battery, has_generator, has_grid)
            add_scenario_net_present_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid)
            add_net_present_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid)
        # Optimization goal: Variable Cost
        elif settings.project_settings.optimization_goal == 1:
            add_fixed_om_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid, actualized=False)
            if settings.advanced_settings.milp_formulation and settings.generator_params.partial_load:
                add_scenario_variable_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid, partial_load=True, actualized=False)
            else:
                add_scenario_variable_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid, partial_load=False, actualized=False)
            add_total_variable_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid)
            add_investment_limit(model, settings, sets, param, var, has_battery, has_generator, has_grid)
    except Exception as e:
        raise ValueError(f"Error in adding cost calculation constraints: {str(e)}")

def add_investment_cost(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid: bool) -> None:
    """ Add investment cost constraint to the model."""
    step_duration: int = settings.advanced_settings.step_duration    
    # Create a list of years for each investment step
    investment_steps_years: List = [step * step_duration for step in range(len(sets.steps.values))]
    # Calculate discount factor for each year
    discount_factor = xr.DataArray([1 / ((1 + param['DISCOUNT_RATE']) ** inv_year) for inv_year in investment_steps_years],
                                    coords={'steps': sets.steps.values})

    investment_cost: linopy.LinearExpression = 0

    for step in sets.steps.values:
        if step == 1:
            # Initial Investment Cost
            investment_cost += (var['res_units'].sel(steps=step) * 
                                param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST']).sum('renewable_sources')
            if has_battery:
                investment_cost += (var['battery_units'].sel(steps=step) * 
                                    param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'])
            if has_generator:
                investment_cost += (var['generator_units'].sel(steps=step) * 
                                    param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'])
        else:
            # Subsequent Investment Cost
            investment_cost += ((var['res_units'].sel(steps=step) - var['res_units'].sel(steps=step - 1)) * 
                                param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST'] *
                                discount_factor.sel(steps=step)).sum('renewable_sources')
            if has_battery:
                investment_cost += ((var['battery_units'].sel(steps=step) - var['battery_units'].sel(steps=step - 1)) * 
                                    param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'] *
                                    discount_factor.sel(steps=step))
            if has_generator:
                investment_cost += ((var['generator_units'].sel(steps=step) - var['generator_units'].sel(steps=step - 1)) * 
                                    param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] *
                                    discount_factor.sel(steps=step))
    try:
        # Add constraint
        model.add_constraints(var['total_investment_cost'] == investment_cost, name="Total Investment Cost Constraint")
    except Exception as e:
        raise ValueError(f"Error in calculating investment cost: {str(e)}")

def add_fixed_om_cost(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid: bool,
    actualized: bool) -> None:
    """Calculate fixed operation and maintenance cost and add the corresponding constraint to the model."""
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    # Create a list of tuples with years and steps
    years_steps_tuples = [((years[i] - years[0]) + 1, steps[i // step_duration]) for i in range(len(years))]
    # Calculate discount factor for each year
    discount_factor = xr.DataArray([1 / ((1 + param['DISCOUNT_RATE']) ** year) for year in range(1, len(years) + 1)],
                                   coords={'years': years})
    
    om_cost: linopy.LinearExpression = 0

    if actualized:
        for year in sets.years.values:
            # Retrieve the step for the current year
            step = years_steps_tuples[year - years[0]][1]
            
            # RES O&M cost (actualized)
            om_cost += ((var['res_units'].sel(steps=step) * 
                        param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST'] * param['RES_SPECIFIC_OM_COST']) *
                        discount_factor.sel(years=year)).sum('renewable_sources')

            # Battery O&M cost (actualized)
            if has_battery:
                om_cost += ((var['battery_units'].sel(steps=step) * 
                            param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'] * param['BATTERY_SPECIFIC_OM_COST'] * 
                            discount_factor.sel(years=year)))
            
            # Generator O&M cost (actualized)
            if has_generator:
                om_cost += ((var['generator_units'].sel(steps=step) * 
                            param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] * param['GENERATOR_SPECIFIC_OM_COST'] * 
                            discount_factor.sel(years=year)))

    else:
        for step in sets.steps.values:
            # RES O&M cost
            om_cost += (var['res_units'].sel(steps=step) * 
                        param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST'] * param['RES_SPECIFIC_OM_COST']).sum('renewable_sources')

            # Battery O&M cost
            if has_battery:
                om_cost += (var['battery_units'].sel(steps=step) * 
                            param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'] * param['BATTERY_SPECIFIC_OM_COST'])
            
            # Generator O&M cost
            if has_generator:
                om_cost += (var['generator_units'].sel(steps=step) * 
                            param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] * param['GENERATOR_SPECIFIC_OM_COST']) 


    try:
        # Add constraint
        constraint_name = "Fixed O&M costs ({}) Constraint".format("Actualized" if actualized else "Not Actualized")
        var_name = 'operation_maintenance_cost_act' if actualized else 'operation_maintenance_cost_nonact'
        model.add_constraints(var[var_name] == om_cost, name=constraint_name)
    except Exception as e:
        raise ValueError(f"Error in calculating total Fixed O&M costs ({'Actualized' if actualized else 'Not Actualized'}): {str(e)}")


def add_battery_replacement_cost(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    actualized: bool) -> None:
    """
    Add battery replacement cost constraint to the model.

    :param model: The optimization model
    :param settings: Project parameters
    :param sets: Dataset containing sets
    :param param: Dataset containing parameters
    :param var: Dictionary of variables
    :param actualized: Boolean indicating whether to use actualized costs
    """
    battery_cost_in = (var['battery_inflow'] * param['UNITARY_BATTERY_REPLACEMENT_COST']).sum('periods')
    battery_cost_out = (var['battery_outflow'] * param['UNITARY_BATTERY_REPLACEMENT_COST']).sum('periods')
    yearly_cost = battery_cost_in + battery_cost_out
    start_year = sets.years.values[0]
    
    battery_replacement_cost: linopy.LinearExpression = 0
    
    if actualized:
        for year in sets.years.values:
            # Calculate discounted yearly cost and sum over years
            battery_replacement_cost += yearly_cost.sel(years=year) / ((1 + param['DISCOUNT_RATE'])**(year - start_year + 1))
    else:
        battery_replacement_cost = yearly_cost.sum('years')

    try:
        # Add constraint
        constraint_name = "Battery Replacement Cost ({}) Constraint".format("Actualized" if actualized else "Not Actualized")
        var_name = 'battery_replacement_cost_act' if actualized else 'battery_replacement_cost_nonact'
        model.add_constraints(var[var_name] == battery_replacement_cost, name=constraint_name)
    except Exception as e:
        raise ValueError(f"Error in calculating the Battery Replacement Cost ({'Actualized' if actualized else 'Not Actualized'}): {str(e)}")
    
def add_generator_fuel_cost(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    partial_load: bool,
    actualized: bool) -> None:
    """
    Add generator fuel cost constraint to the model.
    """
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    # Create a list of tuples with years and steps
    years_steps_tuples = [((years[i] - years[0]) + 1, steps[i // step_duration]) for i in range(len(years))]

    yearly_cost: linopy.LinearExpression = 0
    generator_fuel_cost: linopy.LinearExpression = 0

    print("ECCOLO")
    print(param['GENERATOR_MARGINAL_COST'])

    if partial_load == False:
        for year in years:
            yearly_cost = (var['generator_energy_production'].sel(years=year) * param['GENERATOR_MARGINAL_COST'].sel(years=year)).sum('periods')
            if actualized:
                generator_fuel_cost += yearly_cost / ((1 + param['DISCOUNT_RATE'])**(year - years[0] + 1))
            else:
                generator_fuel_cost += yearly_cost
    else:
        for year in years:
            # Retrieve the step for the current year
            step = years_steps_tuples[year - years[0]][1]
            yearly_cost = (var['generator_full_load'].sel(steps=step) * param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_MARGINAL_COST'].sel(years=year) +
                            var['generator_energy_partial_load'].sel(years=year) * param['GENERATOR_MARGINAL_COST_MILP'].sel(years=year) +
                            var['generator_partial_load'].sel(years=year) * param['GENERATOR_START_COST'].sel(years=year))
            if actualized:
                generator_fuel_cost += yearly_cost / ((1 + param['DISCOUNT_RATE'])**(year - years[0] + 1))
            else:
                generator_fuel_cost += yearly_cost

    try:
        # Add constraint
        constraint_name = "Total Fuel Cost ({}) Constraint".format("Actualized" if actualized else "Not Actualized")
        var_name = 'total_fuel_cost_act' if actualized else 'total_fuel_cost_nonact'
        model.add_constraints(var[var_name] == generator_fuel_cost, name=constraint_name)
    except Exception as e:
        raise ValueError(f"Error in calculating the Total Fuel Cost ({'Actualized' if actualized else 'Not Actualized'}): {str(e)}")

def add_salvage_value(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid: bool) -> None:
    """Add salvage value constraint to the model."""
    project_duration = settings.project_settings.time_horizon
    step_duration = settings.advanced_settings.step_duration
    discount_factor = 1 / ((1 + param['DISCOUNT_RATE']) ** project_duration)
    salvage_value: linopy.LinearExpression = 0


    for step in sets.steps.values:
        if step == 1:
            # Initial investment step
            salvage_value += (var['res_units'].sel(steps=step) * 
                              param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST'] *
                              ((param['RES_LIFETIME'] - project_duration) / param['RES_LIFETIME']) *
                              discount_factor).sum('renewable_sources')
            if has_battery:
                salvage_value += (var['battery_units'].sel(steps=step) * 
                                  param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'] *
                                  ((param['BATTERY_LIFETIME'] - project_duration) / param['BATTERY_LIFETIME']) *
                                  discount_factor)
            if has_generator:
                salvage_value += (var['generator_units'].sel(steps=step) * 
                                  param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] *
                                  ((param['GENERATOR_LIFETIME'] - project_duration) / param['GENERATOR_LIFETIME']) *
                                  discount_factor)
        else:
            # Subsequent investment steps
            additional_units = var['res_units'].sel(steps=step) - var['res_units'].sel(steps=step - 1)
            remaining_lifetime = param['RES_LIFETIME'] - (project_duration - (step * step_duration))
            salvage_value += (additional_units * 
                              param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST'] *
                              (remaining_lifetime / param['RES_LIFETIME']) *
                              discount_factor).sum('renewable_sources')
            if has_battery:
                additional_battery_units = var['battery_units'].sel(steps=step) - var['battery_units'].sel(steps=step - 1)
                remaining_battery_lifetime = param['BATTERY_LIFETIME'] - (project_duration - (step * step_duration))
                salvage_value += (additional_battery_units * 
                                  param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'] *
                                  (remaining_battery_lifetime / param['BATTERY_LIFETIME']) *
                                  discount_factor)
            if has_generator:
                additional_generator_units = var['generator_units'].sel(steps=step) - var['generator_units'].sel(steps=step - 1)
                remaining_generator_lifetime = param['GENERATOR_LIFETIME'] - (project_duration - (step * step_duration))
                salvage_value += (additional_generator_units * 
                                  param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] *
                                  (remaining_generator_lifetime / param['GENERATOR_LIFETIME']) *
                                  discount_factor)
    try:
        # Add constraint
        model.add_constraints(var['salvage_value'] == salvage_value.sum(), name="Salvage Value Constraint")
    except Exception as e:
        raise ValueError(f"Error in calculating salvage value: {str(e)}")

def add_scenario_variable_cost(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid: bool,
    partial_load: bool,
    actualized: bool) -> None:
    """Add scenario variable cost constraint to the model."""
    scenario_variable_cost: linopy.LinearExpression = 0
    
    # Add fixed O&M cost
    om_cost_var = 'operation_maintenance_cost_act' if actualized else 'operation_maintenance_cost_nonact'
    scenario_variable_cost += var[om_cost_var]
    
    # Add battery replacement cost
    if has_battery:
        add_battery_replacement_cost(model, settings, sets, param, var, actualized)
        battery_replacement_cost_var = 'battery_replacement_cost_act' if actualized else 'battery_replacement_cost_nonact'
        scenario_variable_cost += var[battery_replacement_cost_var]

    # Add generator fuel cost
    if has_generator:
        add_generator_fuel_cost(model, settings, sets, param, var, partial_load, actualized)
        generator_fuel_cost_var = 'total_fuel_cost_act' if actualized else 'total_fuel_cost_nonact'
        scenario_variable_cost += var[generator_fuel_cost_var]

    if settings.project_settings.lost_load_specific_cost > 0.0:
        lost_load_cost_var = 'scenario_lost_load_cost_act' if actualized else 'scenario_lost_load_cost_nonact'
        scenario_variable_cost += var[lost_load_cost_var]
    
    try:
        # Add constraint
        var_name = 'total_scenario_variable_cost_act' if actualized else 'total_scenario_variable_cost_nonact'
        model.add_constraints(var[var_name] == scenario_variable_cost,
                name=f"Total Scenario Variable Cost {'(Actualized)' if actualized else '(Not Actualized)'} Constraint")
    except Exception as e:
        raise ValueError(f"Error in calculating scenario variable cost ({'actualized' if actualized else 'non actualized'}): {str(e)}")

def add_total_variable_cost(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid: bool) -> None:
    """
    Add total variable cost (objective) constraint to the model.

    :param model: The optimization model
    :param settings: Project parameters
    :param sets: Dataset containing sets
    :param param: Dataset containing parameters
    :param var: Dictionary of variables
    """
    try:
        # Add constraint
        model.add_constraints(
            var['total_variable_cost'] == (var["total_scenario_variable_cost_nonact"] * param['SCENARIO_WEIGHTS']).sum('scenarios'),
            name=f"Total Variable Cost Constraint")
    except Exception as e:
        raise ValueError(f"Error in calculating total variable cost: {str(e)}")

def add_investment_limit(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid: bool) -> None:
    """
    Add investment limit constraint to the model.

    :param model: The optimization model
    :param settings: Project parameters
    :param sets: Dataset containing sets
    :param param: Dataset containing parameters
    :param var: Dictionary of variables
    """
    try:
        # Add constraint
        model.add_constraints(var['total_investment_cost'] <= param['INVESTMENT_COST_LIMIT'], name="Investment Limit Constraint")
    except Exception as e:
        raise ValueError(f"Error in adding investment limit constraint: {str(e)}")

def add_scenario_net_present_cost(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid: bool) -> None:
    """Add scenario net present cost constraint to the model."""
    try:
        # Add constraint
        model.add_constraints(
            var['scenario_net_present_cost'] == (
                var['total_investment_cost'] + var['total_scenario_variable_cost_act'] - var['salvage_value']),
                name=f"Scenario Net Present Cost Constraint")
    except Exception as e:
        raise ValueError(f"Error in calculating scenario net present cost: {str(e)}")
    
def add_net_present_cost(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid: bool) -> None:
    """Add net present cost constraint (objective function) to the model."""
    try:
        # Add constraint
        model.add_constraints(
            var['net_present_cost'] == (var["scenario_net_present_cost"] * param['SCENARIO_WEIGHTS']).sum('scenarios'),
            name=f"Net Present Cost Constraint")
    except Exception as e:
        raise ValueError(f"Error in calculating net present cost: {str(e)}")