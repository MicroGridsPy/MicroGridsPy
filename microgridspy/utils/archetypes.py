import os
import streamlit as st
import pandas as pd
from typing import List, Tuple
from config.path_manager import PathManager

class User:
    def __init__(self, name, demand_data):
        self.name = name
        self.demand_data = demand_data

class Household:
    def __init__(self, zone: str, wealth: int, cooling: str, number: float):
        self.zone = zone
        self.wealth = wealth
        self.cooling = cooling
        self.number = number

    def load_demand(self, h_load: pd.DataFrame) -> pd.DataFrame:
        return self.number / 100 * h_load

class Hospital:
    def __init__(self, type: int, number: float):
        self.type = type
        self.number = number

    def load_demand(self, h_load: pd.DataFrame) -> pd.DataFrame:
        return self.number * h_load

class School:
    def __init__(self, number: float):
        self.number = number

    def load_demand(self, s_load: pd.DataFrame) -> pd.DataFrame:
        return self.number * s_load

def determine_zone(lat: float) -> str:
    """
    Determine the zone based on latitude.

    Args:
        lat (float): Latitude of the location.

    Returns:
        str: Zone identifier.

    Raises:
        ValueError: If the latitude is outside the valid range for archetypes.
    """
    if 10 <= lat <= 20:
        return 'F1'
    elif -10 <= lat < 10:
        return 'F2'
    elif -20 <= lat < -10:
        return 'F3'
    elif -30 <= lat < -20:
        return 'F4'
    elif lat < -30:
        return 'F5'
    else:
        raise ValueError("Latitude out of range. Archetypes are valid only for Sub-Sahara Africa, within the latitudes -30 to 20 degrees.")

def aggregate_load(load_data: pd.DataFrame, periods: int) -> pd.DataFrame:
    """
    Aggregates the load data to match the number of periods.

    Args:
        load_data (pd.DataFrame): DataFrame containing the load data.
        periods (int): Number of periods to aggregate the data into.

    Returns:
        pd.DataFrame: Aggregated load data.
    """
    total_hours = len(load_data)
    agg_factor = total_hours // periods
    aggregated_load = load_data.groupby(load_data.index // agg_factor).sum()
    return aggregated_load

def load_household_data(household: Household, tier: int, periods: int) -> pd.DataFrame:
    h_load_name = f"{household.cooling}_{household.zone}_Tier-{tier}"
    file_path = os.path.join(PathManager.ARCHETYPES_FOLDER_PATH, f"{h_load_name}.xlsx")
    h_load = pd.read_excel(file_path, skiprows=0, usecols="B")
    return aggregate_load(h_load, periods)

def load_hospital_data(hospital: Hospital, tier: int, periods: int) -> pd.DataFrame:
    hospital_load_name = f"HOSPITAL_Tier-{tier}"
    file_path = os.path.join(PathManager.ARCHETYPES_FOLDER_PATH, f"{hospital_load_name}.xlsx")
    hospital_load = pd.read_excel(file_path, skiprows=0, usecols="B")
    return aggregate_load(hospital_load, periods)

def load_school_data(school: School, periods: int) -> pd.DataFrame:
    school_load_name = "SCHOOL"
    file_path = os.path.join(PathManager.ARCHETYPES_FOLDER_PATH, f"{school_load_name}.xlsx")
    school_load = pd.read_excel(file_path, skiprows=0, usecols="B")
    return aggregate_load(school_load, periods)

def apply_demand_growth(load_total: pd.DataFrame, demand_growth: float) -> None:
    for column in range(1, load_total.shape[1]):
        load_total.iloc[:, column] = load_total.iloc[:, column - 1] * (1 + demand_growth / 100)


def demand_calculation(
    lat: float, cooling_period: str, num_h_tier1: float, num_h_tier2: float, num_h_tier3: float,
    num_h_tier4: float, num_h_tier5: float, num_schools: float, num_hospitals1: float,
    num_hospitals2: float, num_hospitals3: float, num_hospitals4: float, num_hospitals5: float, 
    demand_growth: float, years: int, periods: int
) -> Tuple[pd.DataFrame, List[User]]:
    """
    Calculates the load demand for households, hospitals, and schools.

    Args:
        lat (float): Latitude to determine the zone.
        cooling_period (str): Cooling period identifier.
        num_h_tier1 (float): Number of households for tier 1.
        num_h_tier2 (float): Number of households for tier 2.
        num_h_tier3 (float): Number of households for tier 3.
        num_h_tier4 (float): Number of households for tier 4.
        num_h_tier5 (float): Number of households for tier 5.
        num_schools (float): Number of schools.
        num_hospitals1 (float): Number of hospitals for type 1.
        num_hospitals2 (float): Number of hospitals for type 2.
        num_hospitals3 (float): Number of hospitals for type 3.
        num_hospitals4 (float): Number of hospitals for type 4.
        num_hospitals5 (float): Number of hospitals for type 5.
        demand_growth (float): Annual demand growth rate.
        years (int): Number of years for the demand projection.
        periods (int): Number of periods in a year.

    Returns:
        Tuple[pd.DataFrame, List[User]]: Total load demand and user profiles.
    """
    if lat is None: raise ValueError("Latitude is not initialized. Please initialize it in the Resource Assessment page.")
    
    zone = determine_zone(lat)
    users = []

    # Households
    households = [
        Household(zone, 1, cooling_period, num_h_tier1),
        Household(zone, 2, cooling_period, num_h_tier2),
        Household(zone, 3, cooling_period, num_h_tier3),
        Household(zone, 4, cooling_period, num_h_tier4),
        Household(zone, 5, cooling_period, num_h_tier5)
    ]
    
    load_households = pd.DataFrame(0, index=range(periods), columns=['Load'])
    for ii, household in enumerate(households, start=1):
        if household.number > 0:
            household_load = household.load_demand(load_household_data(household, ii, periods))
            load_households['Load'] += household_load.iloc[:, 0]

    # Hospitals
    hospitals = [
        Hospital(1, num_hospitals1),
        Hospital(2, num_hospitals2),
        Hospital(3, num_hospitals3),
        Hospital(4, num_hospitals4),
        Hospital(5, num_hospitals5)
    ]
    
    load_tot_hospitals = pd.DataFrame(0, index=range(periods), columns=['Load'])
    for ii, hospital in enumerate(hospitals, start=1):
        if hospital.number > 0:
            hospital_load = hospital.load_demand(load_hospital_data(hospital, ii, periods))
            load_tot_hospitals['Load'] += hospital_load.iloc[:, 0]

    # School
    load_school = pd.DataFrame(0, index=range(periods), columns=['Load'])
    if num_schools > 0:
        school = School(num_schools)
        school_load = school.load_demand(load_school_data(school, periods))
        load_school['Load'] += school_load.iloc[:, 0]

    # Combine all loads
    load_total = load_households + load_tot_hospitals + load_school
    
    if load_total['Load'].sum() == 0:
        raise ValueError("Error: Total load is zero. Please input at least one non-zero load (household, hospital, or school).")

    load_total = pd.concat([load_total] * years, axis=1)
    apply_demand_growth(load_total, demand_growth)

    # Update column names
    load_total.columns = [f'Year_{i+1}' for i in range(load_total.shape[1])]

    # Save individual load profiles to User class
    for ii, household in enumerate(households, start=1):
        if household.number > 0:
            user_name = f"Household_Tier_{ii}"
            h_load = household.load_demand(load_household_data(household, ii, periods))
            h_load = pd.concat([h_load] * years, axis=1)
            apply_demand_growth(h_load, demand_growth)
            h_load.columns = [f'Year_{i+1}' for i in range(h_load.shape[1])]
            users.append(User(name=user_name, demand_data=h_load))
    
    for ii, hospital in enumerate(hospitals, start=1):
        if hospital.number > 0:
            user_name = f"Hospital_Tier_{ii}"
            h_load = hospital.load_demand(load_hospital_data(hospital, ii, periods))
            h_load = pd.concat([h_load] * years, axis=1)
            apply_demand_growth(h_load, demand_growth)
            h_load.columns = [f'Year_{i+1}' for i in range(h_load.shape[1])]
            users.append(User(name=user_name, demand_data=h_load))

    if num_schools > 0:
        user_name = "School"
        s_load = school.load_demand(load_school_data(school, periods))
        s_load = pd.concat([s_load] * years, axis=1)
        apply_demand_growth(s_load, demand_growth)
        s_load.columns = [f'Year_{i+1}' for i in range(s_load.shape[1])]
        users.append(User(name=user_name, demand_data=s_load))

    return load_total, users
