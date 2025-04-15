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

# TODO: Check if this is correct
def operate_min_capacity(
    battery_independence: int,
    time_resolution: int,
    scenario_weights: List[float],
    DOD: float,
    sets: xr.Dataset,
    demand: xr.DataArray
) -> float:
    """
    Calculate the minimum battery capacity required to meet a certain number of consecutive days of energy demand.
    
    Parameters:
        battery_independence (int): Number of days the battery should be independent.
        time_resolution (int): Time resolution in hours.
        scenario_weights (List[float]): Weights for each scenario.
        DOD (float): Depth of Discharge (0 to 1 range).
        sets (xr.Dataset): Contains years, periods, scenarios.
        demand (xr.DataArray): Energy demand profile (scenarios, years, periods).

    Returns:
        float: Minimum required battery capacity.
    """

    # Compute time step duration (in hours)
    delta_time: float = operate_delta_time(time_resolution)  # Ensure this function returns time step duration correctly

    # Number of periods per day
    periods_per_day = int(24 / delta_time)

    # Number of periods for required independence
    independence_periods = battery_independence * periods_per_day

    # Reshape demand to 1D while keeping year-period structure
    demand_stacked = demand.stack(index=("years", "periods"))

    # Compute rolling sum over `independence_periods` to find worst-case demand period
    rolling_energy = demand_stacked.rolling(index=independence_periods, min_periods=independence_periods).sum()

    # Find the maximum rolling sum (worst-case battery requirement)
    max_demand = rolling_energy.max(dim="index")

    # Adjust for Depth of Discharge
    min_required_capacity = max_demand / DOD

    return min_required_capacity

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