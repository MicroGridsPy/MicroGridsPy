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
        investment_cost += (var['grid_transformer_units'] * param['GRID_TRANSFORMER_NOMINAL_CAPACITY']* param['GRID_TRANSFORMER_COST'])
    
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
    """
    Compute economically consistent salvage value (NPC level), in a way that:
    - Is consistent with CRF / discounting logic of the NPC objective.
    - Uses the last-step CAPEX for salvage (as in the previous implementation).
    - Treats RES, batteries, generators, and their inverters/rectifiers consistently.
    - Avoids comparisons on linopy.Variable (no > 0 on variables).

    For a component with lifetime L and discount rate r, used for H years
    after its investment, the salvage PV at the investment time is:

        S_at_invest = I * f(L, H)

    with CRF-consistent salvage fraction:
        f(L, H) = ((1+r)^(L-H) - 1) / ((1+r)^L - 1)      for 0 <= H < L
                  0                                      otherwise

    Then we discount S_at_invest from investment year t_inv to year 0.
    """

    # Aliases
    project_duration: int = settings.project_settings.time_horizon      # [years]
    step_duration: int = settings.advanced_settings.step_duration       # [years]
    years: xr.DataArray = sets.years.values
    is_brownfield: bool = settings.advanced_settings.brownfield
    r = param["DISCOUNT_RATE"]
    one_plus_r = 1 + r

    # ------------------------------------------------------------------
    # Helper: CRF-consistent salvage fraction (PV at investment time)
    # ------------------------------------------------------------------
    def salvage_fraction_crf(lifetime: xr.DataArray, years_in_use: float) -> xr.DataArray:
        """
        Compute CRF-consistent salvage fraction f(L, H) at the time of investment.

        lifetime:    DataArray with technical lifetime L (yrs).
        years_in_use: scalar H (yrs of use in the project horizon, from
                      the investment date to project end).

        Returned fraction f(L, H) is zero if:
          - lifetime <= 0, or
          - H <= 0, or
          - H >= lifetime (fully used within the project).
        """

        # Broadcast scalar years_in_use to lifetime shape
        if not isinstance(years_in_use, xr.DataArray):
            H = xr.full_like(lifetime, float(years_in_use), dtype=float)
        else:
            H = xr.broadcast(years_in_use, lifetime)[0]

        L = lifetime

        # Clamp H into [0, L]
        H = xr.where(H < 0, 0, H)
        H = xr.where(H > L, L, H)

        # Valid region: 0 < H < L and L > 0
        valid = (L > 0) & (H > 0) & (H < L)

        # Numerator and denominator of f(L,H)
        num = one_plus_r ** (L - H) - 1
        den = one_plus_r ** L - 1

        frac = xr.where(valid, num / den, 0)

        return frac

    # ------------------------------------------------------------------
    # Accumulate salvage NPV at year 0
    # ------------------------------------------------------------------
    salvage_npv: linopy.LinearExpression = 0

    # -----------------------------
    # NEW / ADDITIONAL CAPACITY
    # -----------------------------
    for step in sets.steps.values:
        # Investment year (in years from project start)
        # Convention: step 1 -> invest at year 0
        if step == 1:
            invest_year = 0
        else:
            invest_year = step * step_duration

        # Years of use of this asset segment within the project
        years_in_use = project_duration - invest_year

        # Discount factor from investment year to year 0
        df_invest = 1 / (one_plus_r ** invest_year)

        # --- RES modules ---
        res_units_step = var["res_units"].sel(steps=step)
        if step == 1:
            additional_res_units = res_units_step
        else:
            additional_res_units = res_units_step - var["res_units"].sel(steps=step - 1)
        # Note: we rely on monotonic capacity constraints; no clipping with xr.where on variables.

        if "renewable_sources" in res_units_step.dims:
            res_frac = salvage_fraction_crf(param["RES_LIFETIME"], years_in_use)
            salvage_npv += (
                additional_res_units
                * param["RES_NOMINAL_CAPACITY"]
                * param["RES_SPECIFIC_INVESTMENT_COST"].sel(steps=sets.steps.values[-1])
                * res_frac
                * df_invest
            ).sum("renewable_sources")

        # --- RES inverters ---
        res_inv_units_step = var["res_inverter_units"].sel(steps=step)
        if step == 1:
            additional_res_inv_units = res_inv_units_step
        else:
            additional_res_inv_units = res_inv_units_step - var["res_inverter_units"].sel(steps=step - 1)

        if "renewable_sources" in res_inv_units_step.dims:
            res_inv_frac = salvage_fraction_crf(param["RES_INVERTER_LIFETIME"], years_in_use)
            salvage_npv += (
                additional_res_inv_units
                * param["RES_INVERTER_NOMINAL_CAPACITY"]
                * param["RES_INVERTER_COST"]
                * res_inv_frac
                * df_invest
            ).sum("renewable_sources")

        # --- Batteries (bank + inverter) ---
        if has_battery:
            # Battery bank
            bat_units_step = var["battery_units"].sel(steps=step)
            if step == 1:
                additional_bat_units = bat_units_step
            else:
                additional_bat_units = bat_units_step - var["battery_units"].sel(steps=step - 1)

            bat_frac = salvage_fraction_crf(param["BATTERY_LIFETIME"], years_in_use)
            salvage_npv += (
                additional_bat_units
                * param["BATTERY_NOMINAL_CAPACITY"]
                * param["BATTERY_SPECIFIC_INVESTMENT_COST"].sel(steps=sets.steps.values[-1])
                * bat_frac
                * df_invest
            )

            # Battery inverter
            bat_inv_units_step = var["battery_inverter_units"].sel(steps=step)
            if step == 1:
                additional_bat_inv_units = bat_inv_units_step
            else:
                additional_bat_inv_units = bat_inv_units_step - var["battery_inverter_units"].sel(steps=step - 1)

            bat_inv_frac = salvage_fraction_crf(param["BATTERY_INVERTER_LIFETIME"], years_in_use)
            salvage_npv += (
                additional_bat_inv_units
                * param["BATTERY_INVERTER_NOMINAL_CAPACITY"]
                * param["BATTERY_INVERTER_COST"]
                * bat_inv_frac
                * df_invest
            )

        # --- Generators (prime mover + rectifier) ---
        if has_generator:
            # Prime movers
            gen_units_step = var["generator_units"].sel(steps=step)
            if step == 1:
                additional_gen_units = gen_units_step
            else:
                additional_gen_units = gen_units_step - var["generator_units"].sel(steps=step - 1)

            gen_frac = salvage_fraction_crf(param["GENERATOR_LIFETIME"], years_in_use)
            salvage_npv += (
                additional_gen_units
                * param["GENERATOR_NOMINAL_CAPACITY"]
                * param["GENERATOR_SPECIFIC_INVESTMENT_COST"]
                * gen_frac
                * df_invest
            ).sum("generator_types")

            # Rectifiers
            gen_rect_units_step = var["generator_rectifier_units"].sel(steps=step)
            if step == 1:
                additional_gen_rect_units = gen_rect_units_step
            else:
                additional_gen_rect_units = gen_rect_units_step - var["generator_rectifier_units"].sel(steps=step - 1)

            gen_rect_frac = salvage_fraction_crf(param["GENERATOR_RECTIFIER_LIFETIME"], years_in_use)
            salvage_npv += (
                additional_gen_rect_units
                * param["GENERATOR_RECTIFIER_NOMINAL_CAPACITY"]
                * param["GENERATOR_RECTIFIER_COST"]
                * gen_rect_frac
                * df_invest
            ).sum("generator_types")

    # -----------------------------
    # EXISTING (BROWNFIELD) ASSETS
    # -----------------------------
    if is_brownfield:
        # We treat existing assets as if a "virtual" investment of cost I_existing
        # happens at year 0, with an effective remaining lifetime L_rem = L - age.
        # Then we apply the same CRF-consistent salvage logic with H = min(project_duration, L_rem).

        # --- Existing RES modules ---
        L_res_eff = param["RES_LIFETIME"] - param["RES_EXISTING_YEARS"]
        H_res = project_duration  # use for up to project_duration years, limited by L_res_eff inside salvage_fraction_crf
        res_existing_frac = salvage_fraction_crf(L_res_eff, H_res)
        salvage_npv += (
            param["RES_EXISTING_CAPACITY"]
            * param["RES_SPECIFIC_INVESTMENT_COST"].sel(steps=sets.steps.values[-1])
            * res_existing_frac
        ).sum("renewable_sources")

        # --- Existing RES inverters (if present) ---
        if "RES_INVERTER_EXISTING_CAPACITY" in param:
            L_res_inv_eff = param["RES_INVERTER_LIFETIME"] - param["RES_INVERTER_EXISTING_YEARS"]
            H_res_inv = project_duration
            res_inv_existing_frac = salvage_fraction_crf(L_res_inv_eff, H_res_inv)
            salvage_npv += (
                param["RES_INVERTER_EXISTING_CAPACITY"]
                * param["RES_INVERTER_COST"]
                * res_inv_existing_frac
            ).sum("renewable_sources")

        # --- Existing batteries ---
        if has_battery:
            L_bat_eff = param["BATTERY_LIFETIME"] - param["BATTERY_EXISTING_YEARS"]
            H_bat = project_duration
            bat_existing_frac = salvage_fraction_crf(L_bat_eff, H_bat)
            salvage_npv += (
                param["BATTERY_EXISTING_CAPACITY"]
                * param["BATTERY_SPECIFIC_INVESTMENT_COST"].sel(steps=sets.steps.values[-1])
                * bat_existing_frac
            )

            if "BATTERY_INVERTER_EXISTING_CAPACITY" in param:
                L_bat_inv_eff = param["BATTERY_INVERTER_LIFETIME"] - param["BATTERY_INVERTER_EXISTING_YEARS"]
                H_bat_inv = project_duration
                bat_inv_existing_frac = salvage_fraction_crf(L_bat_inv_eff, H_bat_inv)
                salvage_npv += (
                    param["BATTERY_INVERTER_EXISTING_CAPACITY"]
                    * param["BATTERY_INVERTER_COST"]
                    * bat_inv_existing_frac
                )

        # --- Existing generators ---
        if has_generator:
            L_gen_eff = param["GENERATOR_LIFETIME"] - param["GENERATOR_EXISTING_YEARS"]
            H_gen = project_duration
            gen_existing_frac = salvage_fraction_crf(L_gen_eff, H_gen)
            salvage_npv += (
                param["GENERATOR_EXISTING_CAPACITY"]
                * param["GENERATOR_SPECIFIC_INVESTMENT_COST"]
                * gen_existing_frac
            ).sum("generator_types")

            L_gen_rect_eff = param["GENERATOR_RECTIFIER_LIFETIME"] - param["GENERATOR_RECTIFIER_EXISTING_YEARS"]
            H_gen_rect = project_duration
            gen_rect_existing_frac = salvage_fraction_crf(L_gen_rect_eff, H_gen_rect)
            salvage_npv += (
                param["GENERATOR_RECTIFIER_EXISTING_CAPACITY"]
                * param["GENERATOR_RECTIFIER_COST"]
                * gen_rect_existing_frac
            ).sum("generator_types")

    # -----------------------------
    # GRID CONNECTION SALVAGE
    # -----------------------------
    salvage_grid_npv: linopy.LinearExpression = 0
    if has_grid_connection:
        # Keep the existing simplified logic for the line asset;
        # it does not have an explicit technical lifetime parameter here.
        year_grid_connection = settings.grid_params.year_grid_connection - years[0]
        salvage_grid_npv += (
            param["GRID_DISTANCE"]
            * param["GRID_CONNECTION_COST"]
            / (one_plus_r ** (project_duration - year_grid_connection))
        )

    total_salvage_npv = salvage_npv + salvage_grid_npv

    try:
        model.add_constraints(var["salvage_value"] == total_salvage_npv, name="Salvage Value Constraint")
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
