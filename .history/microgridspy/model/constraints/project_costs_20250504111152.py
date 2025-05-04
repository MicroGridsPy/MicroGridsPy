from typing import Dict, List

import xarray as xr
from xarray import where
import linopy
from linopy import Model
from xarray import where

from microgridspy.model.parameters import ProjectParameters

def add_cost_calculation_constraints(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid_connection: bool) -> None:
    """
    Add cost calculation constraints to the model.

    :param model: The optimization model
    :param settings: Project parameters
    :param sets: Dataset containing sets
    :param param: Dataset containing parameters
    :param var: Dictionary of variables
    :param has_battery: Boolean indicating whether the system has a battery
    :param has_generator: Boolean indicating whether the system has a generator
    :param has_grid_connection: Boolean indicating whether the system has a grid connection
    """
    add_investment_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection)
    # Optimization goal: NPC
    if settings.project_settings.optimization_goal == 0:
        add_fixed_om_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection, actualized=True)
        if settings.advanced_settings.milp_formulation and settings.generator_params.partial_load:
            add_scenario_variable_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection, partial_load=True, actualized=True)
        else:
            add_scenario_variable_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection, partial_load = False, actualized=True)
        add_salvage_value(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection)
        add_scenario_net_present_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection)
        add_net_present_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection)
    # Optimization goal: Variable Cost
    elif settings.project_settings.optimization_goal == 1:
        add_fixed_om_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection, actualized=False)
        if settings.advanced_settings.milp_formulation and settings.generator_params.partial_load:
            add_scenario_variable_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection, partial_load=True, actualized=False)
        else:
            add_scenario_variable_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection, partial_load=False, actualized=False)
        add_total_variable_cost(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection)
        add_investment_limit(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection)

def add_investment_cost(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid_connection: bool) -> None:
    """ Add investment cost constraint to the model."""
    step_duration: int = settings.advanced_settings.step_duration    
    # Create a list of years for each investment step
    investment_steps_years: List = [step * step_duration for step in range(len(sets.steps.values))]
    # Calculate discount factor for each year
    discount_factor = xr.DataArray([1 / ((1 + param['DISCOUNT_RATE']) ** inv_year) for inv_year in investment_steps_years],
                                    coords={'steps': sets.steps.values})
    # Initialize investment cost
    investment_cost: linopy.LinearExpression = 0

    for step in sets.steps.values:
        if step == 1:
            # Initial Investment Cost
            investment_cost += (var['res_units'].sel(steps=step) * param['RES_NOMINAL_CAPACITY'] * 
                                param['RES_SPECIFIC_INVESTMENT_COST'].sel(steps=step)).sum('renewable_sources')
            investment_cost += (var['res_inverter_units'].sel(steps=step) * param['RES_INVERTER_NOMINAL_CAPACITY'] * 
                                param['RES_INVERTER_COST']).sum('renewable_sources')
            if has_battery:
                investment_cost += (var['battery_units'].sel(steps=step) * param['BATTERY_NOMINAL_CAPACITY'] * 
                                    param['BATTERY_SPECIFIC_INVESTMENT_COST'].sel(steps=step))
                investment_cost += (var['battery_inverter_units'].sel(steps=step) * param['BATTERY_INVERTER_NOMINAL_CAPACITY'] *
                                    param['BATTERY_INVERTER_COST'])
            if has_generator:
                investment_cost += (var['generator_units'].sel(steps=step) * 
                                    param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST']).sum('generator_types')
                investment_cost += (var['generator_rectifier_units'].sel(steps=step) * param['GENERATOR_RECTIFIER_NOMINAL_CAPACITY'] *
                                    param['GENERATOR_RECTIFIER_COST']).sum('generator_types')
        else:
            # Subsequent Investment Cost
            investment_cost += ((var['res_units'].sel(steps=step) - var['res_units'].sel(steps=step - 1)) * 
                                param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST'].sel(steps=step) *
                                discount_factor.sel(steps=step)).sum('renewable_sources')
            investment_cost += ((var['res_inverter_units'].sel(steps=step) - var['res_inverter_units'].sel(steps=step - 1)) * 
                                param['RES_INVERTER_NOMINAL_CAPACITY'] * param['RES_INVERTER_COST'] *
                                discount_factor.sel(steps=step)).sum('renewable_sources')
            if has_battery:
                investment_cost += ((var['battery_units'].sel(steps=step) - var['battery_units'].sel(steps=step - 1)) * 
                                    param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'].sel(steps=step) *
                                    discount_factor.sel(steps=step))
                investment_cost += ((var['battery_inverter_units'].sel(steps=step) - var['battery_inverter_units'].sel(steps=step - 1)) * 
                                    param['BATTERY_INVERTER_NOMINAL_CAPACITY'] * param['BATTERY_INVERTER_COST'] *
                                    discount_factor.sel(steps=step))
            if has_generator:
                investment_cost += ((var['generator_units'].sel(steps=step) - var['generator_units'].sel(steps=step - 1)) * 
                                    param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] *
                                    discount_factor.sel(steps=step)).sum('generator_types')
                investment_cost += ((var['generator_rectifier_units'].sel(steps=step) - var['generator_rectifier_units'].sel(steps=step - 1)) * 
                                    param['GENERATOR_RECTIFIER_NOMINAL_CAPACITY'] * param['GENERATOR_RECTIFIER_COST'] *
                                    discount_factor.sel(steps=step)).sum('generator_types')
                
    if has_grid_connection:
        year_grid_connection: int = settings.grid_params.year_grid_connection
        years: List[int] = sets.years.values
        start_year: int = years[0]
        grid_connection_discount = 1 / ((1 + param['DISCOUNT_RATE']) ** (year_grid_connection - start_year))
        investment_cost += (param['GRID_DISTANCE'] * param['GRID_CONNECTION_COST'] * grid_connection_discount)
        investment_cost += (var['grid_transformer_units'] * param['GRID_TRASFORMER_NOMINAL_CAPACITY']* param['GRID_TRASFORMER_COST'])
    
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
    has_grid_connection: bool,
    actualized: bool) -> None:
    """Calculate fixed operation and maintenance cost and add the corresponding constraint to the model."""
    # Set useful alias for parameters
    years = sets.years.values
    steps = sets.steps.values
    renewables = sets.renewable_sources.values
    generators = sets.generator_types.values if has_generator else []
    step_duration = settings.advanced_settings.step_duration
    is_brownfield: bool = settings.advanced_settings.brownfield
    # Create a list of tuples with years and steps
    years_steps_tuples = [((years[i] - years[0]) + 1, steps[i // step_duration]) for i in range(len(years))]
    # Calculate discount factor for each year
    discount_factor = xr.DataArray([1 / ((1 + param['DISCOUNT_RATE']) ** year) for year in range(1, len(years) + 1)],
                                   coords={'years': years})
    
    om_cost: linopy.LinearExpression = 0

    if actualized:
        for year in years:
            # Retrieve the step for the current year
            step = years_steps_tuples[year - years[0]][1]

            # RES O&M cost (actualized)
            om_cost += ((var['res_units'].sel(steps=step) * 
                        param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST'].sel(steps=step) * param['RES_SPECIFIC_OM_COST']) *
                        discount_factor.sel(years=year)).sum('renewable_sources')
            
            if is_brownfield:
                # Calculate the total age of the existing capacity at each year for each renewable source
                for res in renewables:
                    # Calculate total_age
                    total_age = param['RES_EXISTING_YEARS'].sel(renewable_sources=res) + (year - years[0])

                    # Calculate lifetime_exceeded
                    lifetime_exceeded = total_age > param['RES_LIFETIME'].sel(renewable_sources=res)

                    if lifetime_exceeded is False:
                        # Existing RES O&M cost (actualized)
                        om_cost += ((param['RES_EXISTING_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST'].sel(steps=0) * param['RES_SPECIFIC_OM_COST'] *
                                    discount_factor.sel(years=year)).sel(renewable_sources=res))

            # Battery O&M cost (actualized)
            if has_battery:
                om_cost += ((var['battery_units'].sel(steps=step) * 
                            param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'].sel(steps=step) * param['BATTERY_SPECIFIC_OM_COST'] * 
                            discount_factor.sel(years=year)))
                
                if is_brownfield:
                    # Calculate the total age of the existing capacity at each year
                    total_age = param['BATTERY_EXISTING_YEARS'] + (year - sets.years[0])
        
                    # Create a boolean mask for renewable sources that have exceeded their lifetime
                    lifetime_exceeded = total_age > param['BATTERY_LIFETIME']

                    if lifetime_exceeded is False:
                        # Existing Battery O&M cost (actualized)
                        om_cost += ((param['BATTERY_EXISTING_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'].sel(steps=0) * param['BATTERY_SPECIFIC_OM_COST'] * 
                                    discount_factor.sel(years=year)))
            
            # Generator O&M cost (actualized)
            if has_generator:
                om_cost += ((var['generator_units'].sel(steps=step) * 
                            param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] * param['GENERATOR_SPECIFIC_OM_COST'] * 
                            discount_factor.sel(years=year))).sum('generator_types')
                
                if is_brownfield:
                    # Calculate the total age of the existing capacity at each year for each generator type
                    for gen in generators:
                        # Calculate the total age of the existing capacity at each year
                        total_age = param['GENERATOR_EXISTING_YEARS'].sel(generator_types=gen) + (year - sets.years[0])
        
                        # Create a boolean mask for renewable sources that have exceeded their lifetime
                        lifetime_exceeded = total_age > param['GENERATOR_LIFETIME'].sel(generator_types=gen)

                        if lifetime_exceeded is False:
                            # Existing Generator O&M cost (actualized)
                            om_cost += ((param['GENERATOR_EXISTING_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] * param['GENERATOR_SPECIFIC_OM_COST'] * 
                                        discount_factor.sel(years=year)).sel(generator_types=gen))
            
            # Grid connection cost (actualized)
            if has_grid_connection:
                if year >= settings.grid_params.year_grid_connection:
                    om_cost += (param['GRID_DISTANCE'] * param['GRID_CONNECTION_COST'] * param['GRID_MAINTENANCE_COST'] * 
                                discount_factor.sel(years=year))

    else:
        for year in sets.years.values:
            # Retrieve the step for the current year
            step = years_steps_tuples[year - years[0]][1]
            
            # RES O&M cost
            om_cost += (var['res_units'].sel(steps=step) * 
                        param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST'].sel(steps=step) * param['RES_SPECIFIC_OM_COST']).sum('renewable_sources')
            
            if is_brownfield:
                # Calculate the total age of the existing capacity at each year for each renewable source
                for res in renewables:
                    # Calculate total_age
                    total_age = param['RES_EXISTING_YEARS'].sel(renewable_sources=res) + (year - years[0])

                    # Calculate lifetime_exceeded
                    lifetime_exceeded = total_age > param['RES_LIFETIME'].sel(renewable_sources=res)

                    if lifetime_exceeded is False:
                        # Existing RES O&M cost (actualized)
                        om_cost += (param['RES_EXISTING_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST'].sel(steps=0) * param['RES_SPECIFIC_OM_COST']).sel(renewable_sources=res)

            # Battery O&M cost
            if has_battery:
                om_cost += (var['battery_units'].sel(steps=step) * 
                            param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'].sel(steps=step) * param['BATTERY_SPECIFIC_OM_COST'])
                
                if is_brownfield:
                    # Calculate the total age of the existing capacity at each year
                    total_age = param['BATTERY_EXISTING_YEARS'] + (year - sets.years[0])
        
                    # Create a boolean mask for renewable sources that have exceeded their lifetime
                    lifetime_exceeded = total_age > param['BATTERY_LIFETIME']

                    if lifetime_exceeded is False:
                        # Existing Battery O&M cost
                        om_cost += (param['BATTERY_EXISTING_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'].sel(steps=0) * param['BATTERY_SPECIFIC_OM_COST'])
            
            # Generator O&M cost
            if has_generator:
                om_cost += (var['generator_units'].sel(steps=step) * 
                            param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] * param['GENERATOR_SPECIFIC_OM_COST']).sum('generator_types') 
                
                if is_brownfield:
                    # Calculate the total age of the existing capacity at each year for each generator type
                    for gen in generators:
                        # Calculate the total age of the existing capacity at each year
                        total_age = param['GENERATOR_EXISTING_YEARS'].sel(generator_types=gen) + (year - sets.years[0])
        
                        # Create a boolean mask for renewable sources that have exceeded their lifetime
                        lifetime_exceeded = total_age > param['GENERATOR_LIFETIME'].sel(generator_types=gen)

                        if lifetime_exceeded is False:
                            # Existing Generator O&M cost
                            om_cost += (param['GENERATOR_EXISTING_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] * param['GENERATOR_SPECIFIC_OM_COST']).sel(generator_types=gen)
                
            # Grid connection cost
            if has_grid_connection:
                if year >= settings.grid_params.year_grid_connection:
                    om_cost += (param['GRID_DISTANCE'] * param['GRID_CONNECTION_COST'] * param['GRID_MAINTENANCE_COST'])

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
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    # Create a list of tuples with years and steps
    years_steps_tuples = [((years[i] - years[0]) + 1, steps[i // step_duration]) for i in range(len(years))]
    start_year = sets.years.values[0]

    battery_replacement_cost: linopy.LinearExpression = 0
    
    if actualized:
        for year in sets.years.values:
            # Calculate discounted yearly cost and sum over years
            step = years_steps_tuples[year - years[0]][1]
            battery_cost_in = (var['battery_inflow'].sel(years=year) * param['UNITARY_BATTERY_REPLACEMENT_COST'].sel(steps=step)).sum('periods')   # Energy flows include also the existing capacity in brownfield scenario
            battery_cost_out = (var['battery_outflow'].sel(years=year) * param['UNITARY_BATTERY_REPLACEMENT_COST'].sel(steps=step)).sum('periods')
            yearly_cost = battery_cost_in + battery_cost_out
            battery_replacement_cost += yearly_cost / ((1 + param['DISCOUNT_RATE'])**(year - start_year + 1))

    else:
        for year in sets.years.values:
            # Calculate discounted yearly cost and sum over years
            step = years_steps_tuples[year - years[0]][1]
            battery_cost_in = (var['battery_inflow'].sel(years=year) * param['UNITARY_BATTERY_REPLACEMENT_COST'].sel(steps=step)).sum('periods')   # Energy flows include also the existing capacity in brownfield scenario
            battery_cost_out = (var['battery_outflow'].sel(years=year) * param['UNITARY_BATTERY_REPLACEMENT_COST'].sel(steps=step)).sum('periods')
            yearly_cost = battery_cost_in + battery_cost_out
            battery_replacement_cost += yearly_cost

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

    yearly_cost: linopy.LinearExpression = 0
    generator_fuel_cost: linopy.LinearExpression = 0

    for year in years:
        yearly_cost = (var['generator_fuel_consumption'].sel(years=year) * param['FUEL_SPECIFIC_COST'].sel(years=year)).sum('periods')
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
    
def add_electricity_cost(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    actualized: bool) -> None:
    """
    Add grid connection cost constraint to the model.

    :param model: The optimization model
    :param settings: Project parameters
    :param sets: Dataset containing sets
    :param param: Dataset containing parameters
    :param var: Dictionary of variables
    :param actualized: Boolean indicating whether to use actualized costs
    """
    start_year = sets.years.values[0]
    energy_from_grid_cost = (var['energy_from_grid'] * param['ELECTRICTY_PURCHASED_COST']).sum('periods')

    # Add revenues related to purchase/sell mode
    if settings.advanced_settings.grid_connection_type == 1:
        energy_to_grid_revenue = (var['energy_to_grid'] * param['ELECTRICTY_SOLD_PRICE']).sum('periods')

    # Initialize total grid connection cost
    total_electricity_cost: linopy.LinearExpression = 0

    for year in sets.years.values:
        # Calculate yearly cost
        if settings.advanced_settings.grid_connection_type == 1:
            yearly_cost = energy_from_grid_cost.sel(years=year) - energy_to_grid_revenue.sel(years=year)
        else: 
            yearly_cost = energy_from_grid_cost.sel(years=year)

        # Calculate discounted yearly cost and sum over years
        if actualized:
            # Calculate discounted yearly cost and sum over years
            total_electricity_cost += yearly_cost / ((1 + param['DISCOUNT_RATE'])**(year - start_year + 1))
        else:
            total_electricity_cost += yearly_cost

    try:
        # Add constraint
        constraint_name = "Grid Connection Cost ({}) Constraint".format("Actualized" if actualized else "Not Actualized")
        var_name = 'scenario_grid_connection_cost_act' if actualized else 'scenario_grid_connection_cost_nonact'
        model.add_constraints(var[var_name] == total_electricity_cost, name=constraint_name)
    except Exception as e:
        raise ValueError(f"Error in calculating the Grid Connection Cost ({'Actualized' if actualized else 'Not Actualized'}): {str(e)}")
    
def add_lost_load_cost(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    actualized: bool) -> None:
    """
    Add grid connection cost constraint to the model.

    :param model: The optimization model
    :param settings: Project parameters
    :param sets: Dataset containing sets
    :param param: Dataset containing parameters
    :param var: Dictionary of variables
    :param actualized: Boolean indicating whether to use actualized costs
    """
    start_year = sets.years.values[0]
    lost_load_cost = (var['lost_load'] * param['LOST_LOAD_SPECIFIC_COST']).sum('periods')

    # Initialize total grid connection cost
    total_lost_load_cost: linopy.LinearExpression = 0
    
    for year in sets.years.values:
        if actualized:
            # Calculate discounted yearly cost and sum over years
            total_lost_load_cost += lost_load_cost.sel(years=year) / ((1 + param['DISCOUNT_RATE'])**(year - start_year + 1))
        else:
            total_lost_load_cost += lost_load_cost.sel(years=year)

    try:
        # Add constraint
        constraint_name = "Lost Load Cost ({}) Constraint".format("Actualized" if actualized else "Not Actualized")
        var_name = 'scenario_lost_load_cost_act' if actualized else 'scenario_lost_load_cost_nonact'
        model.add_constraints(var[var_name] == total_lost_load_cost, name=constraint_name)
    except Exception as e:
        raise ValueError(f"Error in calculating the Lost Load Cost ({'Actualized' if actualized else 'Not Actualized'}): {str(e)}")
    
def add_salvage_value(
    model: linopy.Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid_connection: bool
) -> None:
    # Set useful alias for parameters
    project_duration: int = settings.project_settings.time_horizon
    step_duration: int = settings.advanced_settings.step_duration
    years: xr.DataArray = sets.years.values
    renewable_sources: xr.DataArray = sets.renewable_sources.values
    generators: xr.DataArray = sets.generator_types.values if has_generator else []
    is_brownfield: bool = settings.advanced_settings.brownfield
    discount_factor: xr.DataArray = 1 / ((1 + param['DISCOUNT_RATE']) ** project_duration)
    salvage_value: linopy.LinearExpression = 0

    for step in sets.steps.values:
        # Initial investment step (including existing capacity for brownfield)
        if step == 1:
            
            # RES salvage value calculation
            salvage_value += (
                var['res_units'].sel(steps=step)
                * param['RES_NOMINAL_CAPACITY']
                * param['RES_SPECIFIC_INVESTMENT_COST'].sel(steps=sets.steps.values[-1])
                * (
                    where(
                        param['RES_LIFETIME'] - project_duration > 0,
                        param['RES_LIFETIME'] - project_duration,
                        0
                    )
                    / param['RES_LIFETIME']
                )
                * discount_factor
            ).sum('renewable_sources')

            salvage_value += (
                var['res_inverter_units'].sel(steps=step)
                * param['RES_INVERTER_NOMINAL_CAPACITY']
                * param['RES_INVERTER_COST']
                * (
                    where(
                        param['RES_INVERTER_LIFETIME'] - project_duration > 0,
                        param['RES_INVERTER_LIFETIME'] - project_duration,
                        0
                    )
                    / param['RES_INVERTER_LIFETIME']
                )
                * discount_factor
            ).sum('renewable_sources')
            
            if is_brownfield:
                for res in renewable_sources:
                    # Existing salvage value (brownfield) for each renewable source
                    salvage_value += (
                        param['RES_EXISTING_CAPACITY']
                        * param['RES_SPECIFIC_INVESTMENT_COST'].sel(steps=sets.steps.values[-1])
                        * (
                            where(
                                param['RES_LIFETIME'] - param['RES_EXISTING_YEARS'] - project_duration > 0,
                                param['RES_LIFETIME'] - param['RES_EXISTING_YEARS']- project_duration,
                                0
                            )
                            / param['RES_LIFETIME']
                        )
                        * discount_factor
                    ).sum('renewable_sources')
            
                    salvage_value += (
                        param['RES_INVERTER_EXISTING_CAPACITY']
                        * param['RES_INVERTER_NOMINAL_CAPACITY']
                        * (
                            where(
                                param['RES_INVERTER_LIFETIME'] - param['RES_INVERTER_EXISTING_YEARS'] - project_duration > 0,
                                param['RES_INVERTER_LIFETIME'] - param['RES_INVERTER_EXISTING_YEARS']- project_duration,
                                0
                            )
                            / param['RES_INVERTER_LIFETIME']
                        )
                        * discount_factor
                    ).sum('renewable_sources')

            if has_battery:
                salvage_value += (
                    var['battery_units'].sel(steps=step)
                    * param['BATTERY_NOMINAL_CAPACITY']
                    * param['BATTERY_SPECIFIC_INVESTMENT_COST'].sel(steps=sets.steps.values[-1])
                    * (
                        where(
                            param['BATTERY_LIFETIME'] - project_duration > 0,
                            param['BATTERY_LIFETIME'] - project_duration,
                            0
                        )
                        / param['BATTERY_LIFETIME']
                    )
                    * discount_factor
                )
                salvage_value += (
                    var['battery_inverter_units'].sel(steps=step)
                    * param['BATTERY_INVERTER_NOMINAL_CAPACITY']
                    * param['BATTERY_INVERTER_COST']
                    * (
                        where(
                            param['BATTERY_INVERTER_LIFETIME'] - project_duration > 0,
                            param['BATTERY_INVERTER_LIFETIME'] - project_duration,
                            0
                        )
                        / param['BATTERY_INVERTER_LIFETIME']
                    )
                    * discount_factor
                )
                if is_brownfield:
                    # Existing battery salvage (brownfield)
                    salvage_value += (param['BATTERY_EXISTING_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'].sel(steps=sets.steps.values[-1]) *
                                     (max(0, param['BATTERY_LIFETIME'] - param['BATTERY_EXISTING_YEARS'] - project_duration) / param['BATTERY_LIFETIME']) *
                                     discount_factor)
                    salvage_value += (param['BATTERY_INVERTER_EXISTING_CAPACITY'] * param['BATTERY_INVERTER_COST'] *
                                     (max(0, param['BATTERY_INVERTER_LIFETIME'] - param['BATTERY_INVERTER_EXISTING_YEARS'] - project_duration) / param['BATTERY_INVERTER_LIFETIME']) *
                                     discount_factor)

            if has_generator:
                salvage_value += (var['generator_units'].sel(steps=step) * 
                                  param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] *
                                  (max(0, param['GENERATOR_LIFETIME'] - project_duration) / param['GENERATOR_LIFETIME']) *
                                  discount_factor).sum('generator_types')
                salvage_value += (var['generator_rectifier_units'].sel(steps=step) * 
                                  param['GENERATOR_RECTIFIER_NOMINAL_CAPACITY'] * param['GENERATOR_RECTIFIER_COST'] *
                                  (max(0, param['GENERATOR_RECTIFIER_LIFETIME'] - project_duration) / param['GENERATOR_RECTIFIER_LIFETIME']) *
                                  discount_factor).sum('generator_types')
                
                if is_brownfield:
                    for gen in generators:
                        # Existing generator salvage (brownfield)
                        salvage_value += (param['GENERATOR_EXISTING_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] *
                                        (max(0, param['GENERATOR_LIFETIME'] - param['GENERATOR_EXISTING_YEARS'] - project_duration) / param['GENERATOR_LIFETIME']) *
                                        discount_factor).sel(generator_types=gen)
                        salvage_value += (param['GENERATOR_RECTIFIER_EXISTING_CAPACITY'] * param['GENERATOR_RECTIFIER_COST'] *
                                        (max(0, param['GENERATOR_RECTIFIER_LIFETIME'] - param['GENERATOR_RECTIFIER_EXISTING_YEARS'] - project_duration) / param['GENERATOR_RECTIFIER_LIFETIME']) *
                                        discount_factor).sel(generator_types=gen)
        # Subsequent investment steps
        else:
            # RES salvage
            additional_units = var['res_units'].sel(steps=step) - var['res_units'].sel(steps=step - 1)
            remaining_lifetime = where(
                param['RES_LIFETIME'] - (project_duration - (step * step_duration)) > 0,
                param['RES_LIFETIME'] - (project_duration - (step * step_duration)),
                0
            )
            salvage_value += (additional_units * 
                              param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_INVESTMENT_COST'].sel(steps=sets.steps.values[-1]) *
                              (remaining_lifetime / param['RES_LIFETIME']) *
                              discount_factor).sum('renewable_sources')
            
            additional_res_inverter_units = var['res_inverter_units'].sel(steps=step) - var['res_inverter_units'].sel(steps=step - 1)
            remaining_res_inverter_lifetime = where(
                param['RES_INVERTER_LIFETIME'] - (project_duration - (step * step_duration)) > 0,
                param['RES_INVERTER_LIFETIME'] - (project_duration - (step * step_duration)),
                0
            )
            salvage_value += (additional_res_inverter_units * 
                              param['RES_INVERTER_NOMINAL_CAPACITY'] * param['RES_INVERTER_COST'] *
                              (remaining_res_inverter_lifetime / param['RES_INVERTER_LIFETIME']) *
                              discount_factor).sum('renewable_sources')

            if has_battery:
                additional_battery_units = var['battery_units'].sel(steps=step) - var['battery_units'].sel(steps=step - 1)
                remaining_battery_lifetime = max(0, param['BATTERY_LIFETIME'] - (project_duration - (step * step_duration)))
                salvage_value += (additional_battery_units * 
                                  param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_SPECIFIC_INVESTMENT_COST'].sel(steps=sets.steps.values[-1]) *
                                  (remaining_battery_lifetime / param['BATTERY_LIFETIME']) *
                                  discount_factor)
                
                additional_battery_inverter_units = var['battery_inverter_units'].sel(steps=step) - var['battery_inverter_units'].sel(steps=step - 1)
                remaining_battery_inverter_lifetime = max(0, param['BATTERY_INVERTER_LIFETIME'] - (project_duration - (step * step_duration)))
                salvage_value += (additional_battery_inverter_units * 
                                  param['BATTERY_INVERTER_NOMINAL_CAPACITY'] * param['BATTERY_INVERTER_COST'] *
                                  (remaining_battery_inverter_lifetime / param['BATTERY_INVERTER_LIFETIME']) *
                                  discount_factor)

            if has_generator:
                additional_generator_units = var['generator_units'].sel(steps=step) - var['generator_units'].sel(steps=step - 1)
                remaining_generator_lifetime = max(0, param['GENERATOR_LIFETIME'] - (project_duration - (step * step_duration)))
                salvage_value += (additional_generator_units * 
                                  param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_SPECIFIC_INVESTMENT_COST'] *
                                  (remaining_generator_lifetime / param['GENERATOR_LIFETIME']) *
                                  discount_factor).sum('generator_types')
    
                additional_generator_rectifier_units = var['generator_rectifier_units'].sel(steps=step) - var['generator_rectifier_units'].sel(steps=step - 1)
                remaining_generator_rectifier_lifetime = max(0, param['GENERATOR_RECTIFIER_LIFETIME'] - (project_duration - (step * step_duration)))
                salvage_value += (additional_generator_rectifier_units * 
                                  param['GENERATOR_RECTIFIER_NOMINAL_CAPACITY'] * param['GENERATOR_RECTIFIER_COST'] *
                                  (remaining_generator_rectifier_lifetime / param['GENERATOR_RECTIFIER_LIFETIME']) *
                                  discount_factor).sum('generator_types')

    if has_grid_connection:
        year_grid_connection = (settings.grid_params.year_grid_connection - years[0])
        salvage_value += (param['GRID_DISTANCE'] * param['GRID_CONNECTION_COST'] /
                         ((1 + param['DISCOUNT_RATE'])**(project_duration - year_grid_connection)))

    try:
        model.add_constraints(var['salvage_value'] == salvage_value, name="Salvage Value Constraint")
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
    has_grid_connection: bool,
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

    # Add grid connection cost
    if has_grid_connection:
        add_electricity_cost(model, settings, sets, param, var, actualized)
        grid_connection_cost_var = 'scenario_grid_connection_cost_act' if actualized else 'scenario_grid_connection_cost_nonact'
        scenario_variable_cost += var[grid_connection_cost_var]

    if settings.project_settings.lost_load_specific_cost > 0.0:
        add_lost_load_cost(model, settings, sets, param, var, actualized)
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
    has_grid_connection: bool) -> None:
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
    has_grid_connection: bool) -> None:
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
    has_grid_connection: bool) -> None:
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
    has_grid_connection: bool) -> None:
    """Add net present cost constraint (objective function) to the model."""
    try:
        # Add constraint
        model.add_constraints(
            var['net_present_cost'] == (var["scenario_net_present_cost"] * param['SCENARIO_WEIGHTS']).sum('scenarios'),
            name=f"Net Present Cost Constraint")
    except Exception as e:
        raise ValueError(f"Error in calculating net present cost: {str(e)}")
