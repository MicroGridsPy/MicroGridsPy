import xarray as xr
import pandas as pd

from config.path_manager import PathManager
from microgridspy.model.parameters import ProjectParameters
from microgridspy.model.utils import (
    read_csv_data, 
    operate_discount_rate,
    operate_unitary_battery_replacement_cost,
    operate_delta_time,
    operate_min_capacity,
    initialize_fuel_specific_cost,
    operate_marginal_cost,
    operate_start_cost
)

def initialize_sets(data: ProjectParameters, has_generator: bool) -> xr.Dataset:
    """Definition of sets (or dimensions) and return as xr.Dataset."""

    # Extract parameters from data
    num_periods = data.project_settings.time_resolution
    start_year = data.project_settings.start_date.year
    num_years = data.project_settings.time_horizon
    num_scenarios = data.advanced_settings.num_scenarios
    num_steps = data.advanced_settings.num_steps
    renewable_sources = data.resource_assessment.res_names

    # Initialize the dictionary for Dataset creation
    dataset_dict = {
        'periods': xr.DataArray(range(1, num_periods + 1), dims='periods', name='periods'),
        'years': xr.DataArray(range(start_year, start_year + num_years), dims='years', name='years'),
        'scenarios': xr.DataArray(range(1, num_scenarios + 1), dims='scenarios', name='scenarios'),
        'steps': xr.DataArray(range(1, num_steps + 1), dims='steps', name='steps'),
        'renewable_sources': xr.DataArray(renewable_sources, dims='renewable_sources', name='renewable_sources')
    }

    # Conditionally add generator types
    if has_generator:
        generator_types = data.generator_params.gen_names
        dataset_dict['generator_types'] = xr.DataArray(generator_types, dims='generator_types', name='generator_types')

    # Create and return the Dataset
    return xr.Dataset(dataset_dict)

def initialize_demand(sets: xr.Dataset) -> xr.DataArray:
    """
    Load the demand time series data into an xarray DataArray.
    """
    try:
        demand_df = read_csv_data(PathManager.AGGREGATED_DEMAND_FILE_PATH)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise RuntimeError(f"Failed to initialize demand data: {str(e)}")

    num_scenarios = len(sets.scenarios)
    num_years = len(sets.years)
    num_periods = len(sets.periods)

    # Reshape the data to match other variables' dimension order
    demand_data = demand_df.values.reshape(num_scenarios, num_periods, num_years)

    # Create xarray DataArray with consistent dimension order
    demand_array = xr.DataArray(
        data=demand_data,
        dims=["scenarios", "periods", "years"],
        coords={
            "scenarios": sets.scenarios.values,
            "periods": sets.periods.values,
            "years": sets.years.values
        },
        name="Aggregated Load Demand")

    return demand_array

def initialize_resource(sets: xr.Dataset) -> xr.DataArray:
    """
    Load the resource time series data into an xarray DataArray.
    """
    try:
        resource_df = read_csv_data(PathManager.RESOURCE_FILE_PATH)
        # Rest of the function remains the same
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise RuntimeError(f"Failed to initialize resource data: {str(e)}")

    num_scenarios = len(sets.scenarios)
    num_res_sources = len(sets.renewable_sources)
    num_periods = len(sets.periods)

    # Reshape the data to match other variables' dimension order
    resource_data = resource_df.values.reshape(num_scenarios, num_res_sources, num_periods)

    # Create xarray DataArray with consistent dimension order
    return xr.DataArray(
        data=resource_data,
        dims=["scenarios", "renewable_sources", "periods"],
        coords={
            "scenarios": sets.scenarios.values,
            "renewable_sources": sets.renewable_sources.values,
            "periods": sets.periods.values
        },
        name="Resource Availability - Unit of electricity production")

def initialize_temperature(sets: xr.Dataset) -> xr.DataArray:
    """
    Load the temperature time series data into an xarray DataArray.
    """
    try:
        temperature_df = read_csv_data(PathManager.TEMPERATURE_FILE_PATH)
        # Rest of the function remains the same
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise RuntimeError(f"Failed to initialize temperature data: {str(e)}")

    num_scenarios = len(sets.scenarios)
    num_periods = len(sets.periods)

    # Reshape the data to match other variables' dimension order
    temperature_data = temperature_df.values.reshape(num_scenarios, num_periods)

    # Create xarray DataArray with consistent dimension order
    return xr.DataArray(
        data=temperature_data,
        dims=["scenarios", "periods"],
        coords={
            "scenarios": sets.scenarios.values,
            "periods": sets.periods.values
        },
        name="Temperature")

def initialize_grid_availability(sets: xr.Dataset) -> xr.DataArray:
    """
    Load the grid availability time series data into an xarray DataArray.
    """
    try:
        grid_availability_df = read_csv_data(PathManager.GRID_AVAILABILITY_FILE_PATH)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise RuntimeError(f"Failed to initialize demand data: {str(e)}")

    num_scenarios = len(sets.scenarios)
    num_years = len(sets.years)
    num_periods = len(sets.periods)

    # Reshape the data to match other variables' dimension order
    grid_availability_data = grid_availability_df.values.reshape(num_scenarios, num_periods, num_years)

    # Create xarray DataArray with consistent dimension order
    grid_availability_array = xr.DataArray(
        data=grid_availability_data,
        dims=["scenarios", "periods", "years"],
        coords={
            "scenarios": sets.scenarios.values,
            "periods": sets.periods.values,
            "years": sets.years.values
        },
        name="Aggregated Load Demand")

    return grid_availability_array

def initialize_project_parameters(data: ProjectParameters, sets: xr.Dataset) -> xr.Dataset:
    """
    Initialize the project parameters as xr.Dataset.
    """
    project_parameters = {}

    # Time Horizon (years)
    project_parameters['TIME_HORIZON'] = xr.DataArray(
        data.project_settings.time_horizon,
        dims=[],
        name='Time Horizon (years)')

    # Delta Time 
    project_parameters['DELTA_TIME'] = xr.DataArray(
        operate_delta_time(data.project_settings.time_resolution),
        dims=[],
        name='Duration of each time step (hourly-based)')

    # Discount Rate
    project_parameters['DISCOUNT_RATE'] = xr.DataArray(
        operate_discount_rate(data),
        dims=[],
        name='Yearly Discount Rate (fraction)')

    # Investment Cost Limit if optimization goal is total variable costs minimization
    if data.project_settings.optimization_goal == 1:
        project_parameters['INVESTMENT_COST_LIMIT'] = xr.DataArray(
            data.project_settings.investment_cost_limit,
            dims=[],
            name='Investment Cost Limit')
        
    # Lost load specific cost
    if data.project_settings.lost_load_fraction > 0.0:
        project_parameters['LOST_LOAD_FRACTION'] = xr.DataArray(
            data.project_settings.lost_load_fraction,
            dims=[],
            name='Yearly allowed Lost Load Fraction of the Demand')
        
        project_parameters['LOST_LOAD_SPECIFIC_COST'] = xr.DataArray(
            data.project_settings.lost_load_specific_cost,
            dims=[],
            name='Lost Load Specific Cost')
        
    # Renewable Penetration Limit
    if data.project_settings.renewable_penetration > 0:
        project_parameters['MINIMUM_RENEWABLE_PENETRATION'] = xr.DataArray(
            data.project_settings.renewable_penetration,
            dims=[],
            name='Minimum Renewable Penetration')
        
    # Land Availability (m^2) 
    if data.project_settings.land_availability > 0:
        project_parameters['LAND_AVAILABILITY'] = xr.DataArray(
            data.project_settings.land_availability,
            dims=['renewable_sources'],
            coords={'renewable_sources': sets.renewable_sources.values},
            name='Land Availability')

    # Scenario Weights for multi-scenario optimization
    project_parameters['SCENARIO_WEIGHTS'] = xr.DataArray(
        data.advanced_settings.scenario_weights,
        dims=['scenarios'],
        coords={'scenarios': sets.scenarios.values},
        name='Scenario Weights')

    return xr.Dataset(project_parameters)

def initialize_res_parameters(data: ProjectParameters, sets: xr.Dataset) -> xr.Dataset:
    """
    Initialize the renewable energy source parameters as xr.Dataset.
    """
    renewable_sources = sets.renewable_sources.values

    res_parameters = {
        # Nominal Capacity (W)
        'RES_NOMINAL_CAPACITY': xr.DataArray(
            data.resource_assessment.res_nominal_capacity,
            dims=['renewable_sources'],
            coords={'renewable_sources': renewable_sources},
            name='Renewables Nominal Capacity'),

        # Inverter Efficiency (fraction)
        'RES_INVERTER_EFFICIENCY': xr.DataArray(
            data.renewables_params.res_inverter_efficiency,
            dims=['renewable_sources'],
            coords={'renewable_sources': renewable_sources},
            name='Renewables Inverter Efficiency (%)'),

        # Investment cost per unit of capacity installed (USD/W)
        'RES_SPECIFIC_INVESTMENT_COST': xr.DataArray(
            data.renewables_params.res_specific_investment_cost,
            dims=['renewable_sources'],
            coords={'renewable_sources': renewable_sources},
            name='Renewables Specific Investment Cost (USD/W)'),

        # O&M cost as % of investment cost (fraction)
        'RES_SPECIFIC_OM_COST': xr.DataArray(
            data.renewables_params.res_specific_om_cost,
            dims=['renewable_sources'],
            coords={'renewable_sources': renewable_sources},
            name='Renewables Specific O&M Cost (fraction)'),

        # Lifetime (years)
        'RES_LIFETIME': xr.DataArray(
            data.renewables_params.res_lifetime,
            dims=['renewable_sources'],
            coords={'renewable_sources': renewable_sources},
            name='Renewables Lifetime (years)'),
    }

    if data.advanced_settings.multiobjective_optimization:
        # CO2 emission per unit of capacity installed (kgCO2/W)
        res_parameters['RES_UNIT_CO2_EMISSION'] = xr.DataArray(
            data.renewables_params.res_unit_co2_emission,
            dims=['renewable_sources'],
            coords={'renewable_sources': renewable_sources},
            name='Unit CO2 Emission (kgCO2/W)')

    # Brownfield Investment scenario
    if data.advanced_settings.brownfield:
        res_parameters['RES_EXISTING_CAPACITY'] = xr.DataArray(
            data.renewables_params.res_existing_capacity,
            dims=['renewable_sources'],
            coords={'renewable_sources': renewable_sources},
            name='Renewable Existing Capacity (W)')
        
        res_parameters['RES_EXISTING_YEARS'] = xr.DataArray(
            data.renewables_params.res_existing_years,
            dims=['renewable_sources'],
            coords={'renewable_sources': renewable_sources},
            name='Renewable Existing Years')

    # Specific Area (m^2)
    if data.project_settings.land_availability > 0:
        res_parameters['RES_SPECIFIC_AREA'] = xr.DataArray(
            data.renewables_params.res_specific_area,
            dims=['renewable_sources'],
            coords={'renewable_sources': renewable_sources},
            name='Specific Area (m^2)')

    return xr.Dataset(res_parameters)

def initialize_battery_parameters(data: ProjectParameters, time_series: xr.Dataset, sets: xr.Dataset) -> xr.Dataset:
    """
    Initialize the battery parameters as xr.Dataset.
    """
    battery_parameters = {
        'BATTERY_NOMINAL_CAPACITY': xr.DataArray(
            data.battery_params.battery_nominal_capacity,
            dims=[],
            name='Battery Nominal Capacity'),

        'BATTERY_SPECIFIC_INVESTMENT_COST': xr.DataArray(
            data.battery_params.battery_specific_investment_cost,
            dims=[],
            name='Specific Investment Cost of the Battery Bank (USD/Wh)'),

        'BATTERY_SPECIFIC_ELECTRONIC_INVESTMENT_COST': xr.DataArray(
            data.battery_params.battery_specific_electronic_investment_cost,
            dims=[],
            name='Specific Investment Cost of Electronics of the Battery Bank (USD/Wh)'),

        'BATTERY_SPECIFIC_OM_COST': xr.DataArray(
            data.battery_params.battery_specific_om_cost,
            dims=[],
            name='Specific O&M Cost of the Battery Bank (%)'),

        'BATTERY_DISCHARGE_EFFICIENCY': xr.DataArray(
            data.battery_params.battery_discharge_battery_efficiency,
            dims=[],
            name='Discharge Efficiency of the Battery (%)'),

        'BATTERY_CHARGE_EFFICIENCY': xr.DataArray(
            data.battery_params.battery_charge_battery_efficiency,
            dims=[],
            name='Charge Efficiency of the Battery (%)'),

        'BATTERY_DEPTH_OF_DISCHARGE': xr.DataArray(
            data.battery_params.battery_depth_of_discharge,
            dims=[],
            name='Depth of Discharge of the Battery (%)'),

        'MAXIMUM_BATTERY_DISCHARGE_TIME': xr.DataArray(
            data.battery_params.maximum_battery_discharge_time,
            dims=[],
            name='Maximum Discharge Time of the Battery (hours)'),

        'MAXIMUM_BATTERY_CHARGE_TIME': xr.DataArray(
            data.battery_params.maximum_battery_charge_time,
            dims=[],
            name='Maximum Charge Time of the Battery (hours)'),

        'BATTERY_CYCLES': xr.DataArray(
            data.battery_params.battery_cycles,
            dims=[],
            name='Battery Cycles'),

        'BATTERY_LIFETIME': xr.DataArray(
            data.battery_params.battery_expected_lifetime,
            dims=[],
            name='Average Battery Lifetime Expectancy (years)'),

        'UNITARY_BATTERY_REPLACEMENT_COST': xr.DataArray(
            operate_unitary_battery_replacement_cost(data),
            dims=[],
            name='Unitary Battery Replacement Cost'),

        'BATTERY_INITIAL_SOC': xr.DataArray(
            data.battery_params.battery_initial_soc,
            dims=[],
            name='Battery Initial State of Charge'),}

    if data.advanced_settings.multiobjective_optimization:
        battery_parameters['BATTERY_UNIT_CO2_EMISSION'] = xr.DataArray(
            data.battery_params.bess_unit_co2_emission,
            dims=[],
            name='Battery Unit CO2 Emission (LCA)')

    # Brownfield Investment scenario
    if data.advanced_settings.brownfield:
        battery_parameters['BATTERY_EXISTING_CAPACITY'] = xr.DataArray(
            data.battery_params.battery_existing_capacity,
            dims=[],
            name='Battery Existing Capacity (Wh)')
        battery_parameters['BATTERY_EXISTING_YEARS'] = xr.DataArray(
            data.battery_params.battery_existing_years,
            dims=[],
            name='Battery Existing Years (years)')
    
    # Battery Independence
    if data.project_settings.battery_independence > 0:
        battery_parameters['BATTERY_MIN_CAPACITY'] = xr.DataArray(
            operate_min_capacity(data.project_settings.battery_independence, 
                                 data.project_settings.time_resolution, 
                                 data.advanced_settings.scenario_weights, 
                                 data.battery_params.battery_depth_of_discharge, 
                                 sets, time_series['DEMAND']),
            dims=[],
            name='Battery Minimum Capacity (W*period)')

    return xr.Dataset(battery_parameters)

def initialize_generator_parameters(data: ProjectParameters, sets: xr.Dataset) -> xr.Dataset:
    """
    Initialize the generator parameters as xr.Dataset.
    """
    generator_types = sets.generator_types.values

    generator_parameters = {
        'GENERATOR_NOMINAL_CAPACITY': xr.DataArray(
            data.generator_params.gen_nominal_capacity,
            dims=['generator_types'],
            coords={'generator_types': generator_types},
            name='Generators Nominal Capacity'),

        'GENERATOR_SPECIFIC_INVESTMENT_COST': xr.DataArray(
            data.generator_params.gen_specific_investment_cost,
            dims=['generator_types'],
            coords={'generator_types': generator_types},
            name='Specific Investment Cost of the Generators'),

        'GENERATOR_SPECIFIC_OM_COST': xr.DataArray(
            data.generator_params.gen_specific_om_cost,
            dims=['generator_types'],
            coords={'generator_types': generator_types},
            name='Specific O&M Cost of the Generators'),

        'GENERATOR_LIFETIME': xr.DataArray(
            data.generator_params.gen_lifetime,
            dims=['generator_types'],
            coords={'generator_types': generator_types},
            name='Generators Lifetime'),

        'FUEL_SPECIFIC_COST': xr.DataArray(
            initialize_fuel_specific_cost(data.generator_params.gen_names, data.project_settings.time_horizon),
            dims=['generator_types', 'years'],
            coords={'generator_types': generator_types, 'years': sets.years.values},
            name='Fuel Specific Cost'),

        'GENERATOR_MARGINAL_COST': xr.DataArray(
            operate_marginal_cost(data.generator_params.gen_names, 
                                  data.project_settings.time_horizon,
                                  data.generator_params.gen_nominal_efficiency,
                                  data.generator_params.fuel_lhv,
                                  data.generator_params.gen_nominal_capacity,
                                  data.generator_params.gen_cost_increase,
                                  partial_load=False),
            dims=['generator_types', 'years'],
            coords={'generator_types': generator_types, 'years': sets.years.values},
            name='Marginal Cost of operation at nominal efficiency')}
    
    # Brownfield Investment scenario
    if data.advanced_settings.brownfield:
        generator_parameters['GENERATOR_EXISTING_CAPACITY'] = xr.DataArray(
            data.generator_params.gen_existing_capacity,
            dims=['generator_types'],
            coords={'generator_types': generator_types},
            name='Generator Existing Capacity (Wh)')
        generator_parameters['GENERATOR_EXISTING_YEARS'] = xr.DataArray(
            data.generator_params.gen_existing_years,
            dims=['generator_types'],
            coords={'generator_types': generator_types},
            name='Generator Existing Years (years)')

    if data.advanced_settings.multiobjective_optimization:
        generator_parameters['GENERATOR_UNIT_CO2_EMISSION'] = xr.DataArray(
            data.generator_params.gen_unit_co2_emission,
            dims=['generator_types'],
            coords={'generator_types': generator_types},
            name='Unit CO2 Emission of the Generators')
        
    if data.advanced_settings.unit_commitment and data.generator_params.partial_load:
        generator_parameters['GENERATOR_MIN_LOAD'] = xr.DataArray(
            data.generator_params.gen_min_output,
            dims=['generator_types'],
            coords={'generator_types': generator_types},
            name='Minimum Output of the generators in partial load')
        
        generator_parameters['GENERATOR_START_COST'] = xr.DataArray(
            operate_start_cost(data.generator_params.gen_names, 
                                  data.project_settings.time_horizon,
                                  data.generator_params.gen_nominal_efficiency,
                                  data.generator_params.fuel_lhv,
                                  data.generator_params.gen_nominal_capacity,
                                  data.generator_params.gen_cost_increase),
            dims=['generator_types', 'years'],
            coords={'generator_types': generator_types, 'years': sets.years.values},
            name='Start-up cost of a generator in partial load')
        
        generator_parameters['GENERATOR_MARGINAL_COST_MILP'] = xr.DataArray(
            operate_marginal_cost(data.generator_params.gen_names, 
                                  data.project_settings.time_horizon,
                                  data.generator_params.gen_nominal_efficiency,
                                  data.generator_params.fuel_lhv,
                                  data.generator_params.gen_nominal_capacity,
                                  data.generator_params.gen_cost_increase,
                                  partial_load=True),
            dims=['generator_types', 'years'],
            coords={'generator_types': generator_types, 'years': sets.years.values},
            name='Marginal Cost of operation in partial load')
        
    return xr.Dataset(generator_parameters)

def initialize_grid_parameters(data: ProjectParameters, sets: xr.Dataset) -> xr.Dataset:
    """
    Initialize the grid parameters as xr.Dataset.
    """

    grid_parameters = {
        'ELECTRICTY_PURCHASED_COST': xr.DataArray(
            data.grid_params.electricity_purchased_cost,
            dims=[],
            name='Electricity Purchased Cost'),

        'ELECTRICTY_SOLD_PRICE': xr.DataArray(
            data.grid_params.electricity_sold_price,
            dims=[],
            name='Electricity Sold Price'),

        'GRID_CONNECTION_COST': xr.DataArray(
            data.grid_params.grid_connection_cost,
            dims=[],
            name='Cost of Grid Connection'),

        'GRID_DISTANCE': xr.DataArray(
            data.grid_params.grid_distance,
            dims=[],
            name='Distance to the Grid Connection'),

        'GRID_MAINTENANCE_COST': xr.DataArray(
            data.grid_params.grid_maintenance_cost,
            dims=[],
            name='Grid Maintenance Cost'),
    }

    return xr.Dataset(grid_parameters)