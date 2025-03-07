from typing import Optional, List

import xarray as xr
import numpy as np
import pandas as pd

from microgridspy.model.parameters import ProjectParameters
from config.path_manager import PathManager


def read_csv_data(file_path: str, index_col: Optional[int] = 0) -> pd.DataFrame:
    """
    Safely read a CSV file and return a pandas DataFrame.
    
    Args:
        file_path (str): Path to the CSV file.
        index_col (Optional[int]): Index column to use. Defaults to 0.
    
    Returns:
        pd.DataFrame: The loaded data.
    
    Raises:
        FileNotFoundError: If the file doesn't exist.
        pd.errors.EmptyDataError: If the file is empty.
        pd.errors.ParserError: If the file is not a valid CSV.
    """
    try:
        df = pd.read_csv(file_path, index_col=index_col)
        if df.empty:
            raise pd.errors.EmptyDataError(f"The file {file_path} is empty.")
        return df
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {file_path} was not found. Please check the file path.")
    except pd.errors.EmptyDataError as e:
        raise pd.errors.EmptyDataError(f"Error reading {file_path}: {str(e)}")
    except pd.errors.ParserError as e:
        raise pd.errors.ParserError(f"Error parsing {file_path}: {str(e)}. Please ensure it's a valid CSV file.")  

def operate_discount_rate(data: ProjectParameters) -> float:
    """
    Calculates the discount rate considering the Weighted Average Cost of Capital (WACC).

    Parameters:
    data (ProjectParameters): The project parameters containing necessary financial data.

    Returns:
    float: The calculated discount rate.
    """
    wacc_calculation = data.advanced_settings.wacc_calculation
    equity_share = data.advanced_settings.equity_share
    debt_share = data.advanced_settings.debt_share
    cost_of_debt = data.advanced_settings.cost_of_debt
    tax = data.advanced_settings.tax
    cost_of_equity = data.advanced_settings.cost_of_equity

    discount_rate: float = 0.0

    if wacc_calculation == 1:
        if equity_share == 0:
            discount_rate = cost_of_debt * (1 - tax)
        else:
            leverage = debt_share / equity_share
            discount_rate = (cost_of_debt * (1 - tax) * leverage / (1 + leverage) + 
                             cost_of_equity / (1 + leverage))
    else:
        discount_rate = data.project_settings.discount_rate

    return discount_rate


def operate_unitary_battery_replacement_cost(data: ProjectParameters, investment_steps: int) -> float:
    """
    Initializes the unit replacement cost of the battery based on the model parameters.

    Parameters:
    data (ProjectParameters): The object containing parameters related to battery cost and performance.

    Returns:
    float: The calculated unit replacement cost of the battery.
    """
    try:
        battery_cost_df: pd.DataFrame = read_csv_data(PathManager.BATTERY_COST_FILE_PATH)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise RuntimeError(f"Failed to initialize Battery cost data: {str(e)}")

    # Reshape the data to match other variables' dimension order
    battery_cost_data: np.ndarray = battery_cost_df.values.flatten(order='F').reshape(investment_steps)
    # Extract battery parameters
    Battery_Specific_Electronic_Investment_Cost = data.battery_params.battery_specific_electronic_investment_cost
    Battery_Cycles = data.battery_params.battery_cycles
    Battery_Depth_of_Discharge = data.battery_params.battery_depth_of_discharge

    # Calculate the unitary battery replacement cost
    Unitary_Battery_Cost = battery_cost_data * (1 - Battery_Specific_Electronic_Investment_Cost)
    Unitary_Battery_Replacement_Cost = Unitary_Battery_Cost / (Battery_Cycles * 2 * Battery_Depth_of_Discharge)
    return Unitary_Battery_Replacement_Cost

def operate_delta_time(time_resolution: int) -> float:
    """
    Calculate the duration of each time step in hours based on the number of periods in a year.
    
    Parameters:
    time_resolution (int): Number of periods in a year
    
    Returns:
    float: Duration of each time step in hours
    """
    hours_in_year = 8760  # Number of hours in a non-leap year
    
    delta_time = hours_in_year / time_resolution

    return round(delta_time, 6)

def operate_min_capacity(battery_independence: int, time_resolution: int, scenario_weights: List[float], DOD: float, sets: xr.Dataset, demand: xr.DataArray) -> float:
    """
    Calculate the minimum capacity required for the battery bank based on the model's demand profile and battery independence criteria.
    
    Parameters:
    battery_independence (int): The desired level of battery independence (days)
    sets (xr.Dataset): The model sets
    param (xr.Dataset): The model parameters
    demand (xr.DataArray): The demand profile
    
    Returns:
    float: The minimum required battery capacity to ensure the desired level of battery independence
    """
    delta_time: float = operate_delta_time(time_resolution)
    periods_per_day = int(24 / delta_time)
    independence_periods = battery_independence * periods_per_day
    total_periods = len(sets.periods) * len(sets.years)
    group_count = int(total_periods / independence_periods)
    
    # Flatten the demand data
    demand_data = demand.values.reshape(-1)
    demand_df = pd.DataFrame({'demand': demand_data})
    demand_df['grouper'] = np.repeat(np.arange(1, group_count + 1), independence_periods)[:total_periods]
    
    # Calculate period energy
    period_energy = demand_df.groupby('grouper')['demand'].sum()
    period_average_energy = period_energy.mean()
    
    # Calculate available energy considering scenario weights
    available_energy = period_average_energy * scenario_weights.sum()
    
    # Calculate minimum capacity
    min_capacity = available_energy / DOD.item()
    
    return min_capacity

def initialize_res_investment_cost(res_names: List[str], investment_steps: int) -> np.ndarray:
    """Initialize the RES investment cost array based on the user input."""
    try:
        res_cost_df: pd.DataFrame = read_csv_data(PathManager.RES_COST_FILE_PATH)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise RuntimeError(f"Failed to initialize RES cost data: {str(e)}")
    
    num_res_types: int = len(res_names)

    # Reshape the data to match other variables' dimension order
    res_cost_data: np.ndarray = res_cost_df.values.flatten(order='F').reshape(num_res_types, investment_steps)

    return res_cost_data

def initialize_battery_investment_cost(investment_steps: int) -> np.ndarray:
    """Initialize the RES investment cost array based on the user input."""
    try:
        battery_cost_df: pd.DataFrame = read_csv_data(PathManager.BATTERY_COST_FILE_PATH)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise RuntimeError(f"Failed to initialize Battery cost data: {str(e)}")

    # Reshape the data to match other variables' dimension order
    battery_cost_data: np.ndarray = battery_cost_df.values.flatten(order='F').reshape(investment_steps)

    return battery_cost_data

def initialize_fuel_specific_cost(gen_names: List[str], time_horizon: int) -> np.ndarray:
    """Initialize the fuel-specific cost array based on the user input."""
    try:
        fuel_specific_cost_df: pd.DataFrame = read_csv_data(PathManager.FUEL_SPECIFIC_COST_FILE_PATH)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise RuntimeError(f"Failed to initialize fuel cost data: {str(e)}")
    
    num_gen_types: int = len(gen_names)

    # Reshape the data to match other variables' dimension order
    fuel_specific_cost_data: np.ndarray = fuel_specific_cost_df.values.reshape(num_gen_types, time_horizon)

    return fuel_specific_cost_data

def operate_marginal_cost(
    gen_names: List[str],
    time_horizon: int,
    gen_nominal_efficiency: List[float],
    fuel_lhv: List[float],
    gen_nominal_capacity: List[float],
    gen_cost_increase: List[float],
    partial_load: bool = False
) -> np.ndarray:
    """
    Calculates the marginal cost of operation for a generator type based on the fuel-specific cost and efficiency.
    """
    num_gen_types: int = len(gen_names)
    fuel_specific_cost: np.ndarray = initialize_fuel_specific_cost(gen_names, time_horizon)
    
    # Initialize the marginal cost array
    marginal_cost: np.ndarray = np.zeros((num_gen_types, time_horizon))
    
    # Calculate full load marginal cost for each generator type and year
    for g in range(num_gen_types):
        for y in range(time_horizon):
            marginal_cost[g, y] = (fuel_specific_cost[g, y] / (fuel_lhv[g] * gen_nominal_efficiency[g]))
    
    if partial_load:
        start_cost: np.ndarray = np.zeros((num_gen_types, time_horizon))
        # Calculate start cost for each generator type and year
        for g in range(num_gen_types):
            for y in range(time_horizon):
                start_cost[g, y] = (marginal_cost[g, y] * gen_nominal_capacity[g] * gen_cost_increase[g])

        # Calculate partial load marginal cost
        partial_load_marginal_cost: np.ndarray = np.zeros((num_gen_types, time_horizon))
        for g in range(num_gen_types):
            for y in range(time_horizon):
                partial_load_marginal_cost[g, y] = (
                    (marginal_cost[g, y] * gen_nominal_capacity[g] - start_cost[g, y]) / gen_nominal_capacity[g])
        return partial_load_marginal_cost
    else:
        return marginal_cost

def operate_start_cost(gen_names: List[str], time_horizon: int, gen_nominal_efficiency: List[float], fuel_lhv: List[float], gen_nominal_capacity: List[float], gen_cost_increase: List[float]) -> np.ndarray:
    """
    Initializes the start-up cost of a generator for a given year. This cost is based on the generator's marginal cost,
    nominal capacity, and a part-load operation parameter.
    """

    marginal_cost: np.ndarray = operate_marginal_cost(gen_names, time_horizon, gen_nominal_efficiency, fuel_lhv, gen_nominal_capacity, gen_cost_increase , partial_load=False)
    # Initialize the start cost array
    num_gen_types: int = len(gen_names)
    start_cost: np.ndarray = np.zeros((num_gen_types, time_horizon))

    # Calculate start cost for each generator type and year
    for g in range(num_gen_types):
        for y in range(time_horizon):
            start_cost[g, y] = (marginal_cost[g, y] * gen_nominal_capacity[g] * gen_cost_increase[g])

    return start_cost