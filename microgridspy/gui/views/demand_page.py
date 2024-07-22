"""
This module provides the demand assessment page for the MicroGridsPy Streamlit application. 
It allows users to simulate or upload load demand data for their project. 
Users can configure specific demand parameters and visualize dynamically the data.
"""

import os
import shutil
import datetime
from io import BytesIO
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from ramp import UseCase
from ramp.post_process.post_process import Profile_formatting

from config.path_manager import PathManager
from microgridspy.model.parameters import ProjectParameters
from microgridspy.utils.archetypes import demand_calculation

class User:
    def __init__(self, name, demand_data):
        self.name = name
        self.demand_data = demand_data

def initialize_session_state(default_values: ProjectParameters) -> None:
    """Initialize session state with default values for archetypes if not already set."""
    archetypes_params = default_values.archetypes_params
    session_vars = {
        'demand_growth': archetypes_params.demand_growth,
        'cooling_period': archetypes_params.cooling_period,
        'h_tier1': archetypes_params.h_tier1,
        'h_tier2': archetypes_params.h_tier2,
        'h_tier3': archetypes_params.h_tier3,
        'h_tier4': archetypes_params.h_tier4,
        'h_tier5': archetypes_params.h_tier5,
        'schools': archetypes_params.schools,
        'hospital_1': archetypes_params.hospital_1,
        'hospital_2': archetypes_params.hospital_2,
        'hospital_3': archetypes_params.hospital_3,
        'hospital_4': archetypes_params.hospital_4,
        'hospital_5': archetypes_params.hospital_5,
        'aggregated_demand_flag': False,
    }
    for key, value in session_vars.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_demand_folder(demand_path: str) -> None:
    """
    Delete all files within the demand folder.

    Args:
        demand_path (str): Path to the demand folder.
    """
    for filename in os.listdir(demand_path):
        file_path = os.path.join(demand_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')


def save_demand_data(demand_data: pd.DataFrame, filename: str, start_year: str) -> str:
    """
    Save demand data to a CSV file with the correct year columns starting from the start date.
    Assign the data to the demand xarray parameter of the ProjectParameters instance.

    Args:
        demand_data (pd.DataFrame): The demand data to save.
        filename (str): The filename for the CSV file.
        project_params (ProjectParameters): The project parameters instance to assign the data.

    Returns:
        str: The file path of the saved CSV file.
    """
    # Add the "Hours" index column ranging from 1 to len(demand_data)
    demand_data.index = range(1, len(demand_data) + 1)
    demand_data.index.name = 'Periods'

    # Rename the columns to the correct years starting from the start date
    num_years = len(demand_data.columns)
    new_column_names = [str(int(start_year) + i) for i in range(num_years)]
    demand_data.columns = new_column_names

    file_path = os.path.join(PathManager.DEMAND_FOLDER_PATH, filename)
    demand_data.to_csv(file_path, index=True)

    return file_path


def load_ramp_data(file_content: BytesIO, num_days: int, force_reinitialize: bool) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Load and process data from RAMP software.

    Args:
        file_content (BytesIO): The content of the RAMP input file.
        num_days (int): The number of days to simulate.
        force_reinitialize (bool): Whether to force reinitialization.

    Returns:
        Tuple[Optional[np.ndarray], Optional[np.ndarray]]: The full year profiles series and daily average profile.
    """
    try:
        usecase = UseCase(name="Use Case")
        usecase.initialize(num_days=num_days, force=force_reinitialize)
        usecase.load(file_content)
        load_profile = usecase.generate_daily_load_profiles()

        _, _, profiles_series = Profile_formatting(load_profile)

        minutes_per_day = 1440
        num_days_generated = len(profiles_series) // minutes_per_day

        profiles_reshaped = profiles_series.reshape((num_days_generated, minutes_per_day))
        profiles_daily_avg = profiles_reshaped.mean(axis=0)

        if num_days < 365:
            repeat_factor = 365 // num_days_generated + 1
            profiles_series_full_year = np.tile(profiles_series, repeat_factor)[:365 * minutes_per_day]
            profiles_daily_avg_full_year = np.mean(profiles_series_full_year.reshape((365, minutes_per_day)), axis=0)
        else:
            profiles_series_full_year = profiles_series
            profiles_daily_avg_full_year = profiles_daily_avg

        return profiles_series_full_year, profiles_daily_avg_full_year
    except Exception as e:
        st.error(f"Error loading RAMP data: {e}")
        return None, None


def load_csv_data(uploaded_file, delimiter: str, decimal: str) -> Optional[pd.DataFrame]:
    """
    Load CSV data with given delimiter and decimal options.

    Args:
        uploaded_file: The uploaded CSV file.
        delimiter (str): The delimiter used in the CSV file.
        decimal (str): The decimal separator used in the CSV file.

    Returns:
        Optional[pd.DataFrame]: The loaded CSV data as a DataFrame, or None if an error occurs.
    """
    try:
        data = pd.read_csv(uploaded_file, delimiter=delimiter, decimal=decimal, index_col=0)
        data = data.apply(pd.to_numeric, errors='coerce')
        if data.empty:
            st.warning("No data found in the CSV file. Please check delimiter and decimal settings.")
        elif data.isnull().values.any():
            st.warning("Some values could not be converted to numeric. Please check the data.")
        else:
            st.success(f"Data loaded successfully using delimiter '{delimiter}' and decimal '{decimal}'")
        return data
    except Exception as e:
        st.error(f"Error during import of CSV data: {e}")
        return None


def plot_cloud_plot_with_avg(profiles_series: np.ndarray, profiles_daily_avg: np.ndarray, title: str) -> None:
    """
    Plot the daily average load curve with variability range.

    Args:
        profiles_series (np.ndarray): The full series of profiles.
        profiles_daily_avg (np.ndarray): The daily average profile.
        title (str): The title for the plot.
    """
    minutes_per_day = 1440
    num_days = len(profiles_series) // minutes_per_day
    profiles_reshaped = profiles_series.reshape((num_days, minutes_per_day))

    profiles_min = profiles_reshaped.min(axis=0)
    profiles_max = profiles_reshaped.max(axis=0)

    fig, ax = plt.subplots(figsize=(15, 10))

    for day in profiles_reshaped:
        ax.plot(day / 1000, color='lightgrey', linewidth=0.5, alpha=0.3)

    ax.fill_between(range(minutes_per_day), profiles_min / 1000, profiles_max / 1000, color='grey', alpha=0.3, label='Variability Range')
    ax.plot(profiles_daily_avg / 1000, color='red', linewidth=2, label='Average Daily Profile')

    ax.set_title(title)
    ax.set_xlabel('Time of Day')
    ax.set_ylabel('Power [kW]')
    ax.set_xticks(np.linspace(0, minutes_per_day, 24))
    ax.set_xticklabels([f'{hour}:00' for hour in range(24)], rotation=45)
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)


def multi_years_demand(demand_data: np.ndarray, time_horizon: int, growth_rate: Optional[float] = None) -> pd.DataFrame:
    """
    Create and save a CSV file for the demand data.

    Args:
        demand_data (np.ndarray): The demand data.
        time_horizon (int): The time horizon for the demand data.
        growth_rate (Optional[float]): The growth rate for the demand data.

    Returns:
        pd.DataFrame: The DataFrame of the created demand data.
    """
    demand_profile = np.array(demand_data)
    if growth_rate is not None:
        demand_profiles = [demand_profile * (1 + growth_rate) ** year for year in range(time_horizon)]
    else:
        demand_profiles = [demand_profile for _ in range(time_horizon)]

    hours_in_year = len(demand_profile)
    hourly_index = np.arange(1, hours_in_year + 1)

    demand_df = pd.DataFrame(index=hourly_index)
    for year in range(time_horizon):
        demand_df[f'Year_{year + 1}'] = demand_profiles[year]

    return demand_df


def demand_generation_with_user_input(latitude: float, time_horizon: int) -> Tuple[pd.DataFrame, List[User]]:
    """
    Generate demand data using user input.

    Returns:
        pd.DataFrame: The generated demand data.
        List[User]: List of User objects with individual demand profiles.

    TODO: Implement different time resolutions for demand data.
    """
    load_tot, users_demand = demand_calculation(
        lat=latitude,
        cooling_period=st.session_state.cooling_period,
        num_h_tier1=st.session_state.h_tier1,
        num_h_tier2=st.session_state.h_tier2,
        num_h_tier3=st.session_state.h_tier3,
        num_h_tier4=st.session_state.h_tier4,
        num_h_tier5=st.session_state.h_tier5,
        num_schools=st.session_state.schools,
        num_hospitals1=st.session_state.hospital_1,
        num_hospitals2=st.session_state.hospital_2,
        num_hospitals3=st.session_state.hospital_3,
        num_hospitals4=st.session_state.hospital_4,
        num_hospitals5=st.session_state.hospital_5,
        demand_growth=st.session_state.demand_growth,
        years=time_horizon,
        periods=365 * 24
    )
    return load_tot, users_demand


def plot_demand_data(time_horizon: int, start_year: str) -> None:
    """
    Plot the aggregated demand data from the Aggregated Demand.csv file in the inputs/demand folder.

    Args:
        time_horizon (int): The time horizon for the demand data.

    TODO: Implement different time resolution handling.
    """

    if not os.path.exists(PathManager.AGGREGATED_DEMAND_FILE_PATH):
        st.warning("Aggregated Demand.csv file not found. Please upload or generate demand data to visualize.")
        return

    # Read the aggregated demand data with "Hours" as the index
    demand_data = pd.read_csv(PathManager.AGGREGATED_DEMAND_FILE_PATH, index_col='Periods')

    # Convert start_year to a datetime object
    start_year_datetime = datetime.datetime.strptime(start_year, "%Y")
    start_year_int = start_year_datetime.year

    # Allow the user to select the year within the time horizon
    year_to_plot = st.slider(
        "Select Year to Plot",
        min_value=datetime.datetime(start_year_int, 1, 1),
        max_value=datetime.datetime(start_year_int + time_horizon - 1, 1, 1),
        value=datetime.datetime(start_year_int, 1, 1),
        format="YYYY"
    )

    # Extract data for the selected year
    year_to_plot_str = year_to_plot.year
    selected_year_data = demand_data[f'{year_to_plot_str}']

    # Reshape data to (365, 24) for daily hourly profiles
    hourly_data = selected_year_data.values.reshape(-1, 24)

    # Calculate the average daily profile
    average_daily_profile = hourly_data.mean(axis=0) / 1000  # Convert to kW

    # Calculate the min and max values for variability range
    variability_range_min = hourly_data.min(axis=0) / 1000  # Convert to kW
    variability_range_max = hourly_data.max(axis=0) / 1000  # Convert to kW

    # Calculate the average daily energy consumption and peak power
    avg_daily_energy_consumption = (hourly_data.sum(axis=1).mean()) / 1000  # Convert to kWh
    avg_daily_peak_power = average_daily_profile.max()  # Already in kW

    # Create x-axis labels for hours
    x_labels = [f"{hour:02d}:00" for hour in range(24)]

    # Plotting
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(average_daily_profile, color='red', linewidth=2, label='Average Daily Profile (kW)')
    ax.fill_between(range(24), variability_range_min, variability_range_max, color='gray', alpha=0.3, label='Variability Range')
    ax.set_xticks(range(24))
    ax.set_xticklabels(x_labels, rotation=45)
    ax.set_ylabel('Average Demand (kW)')
    ax.set_title(f'Average Daily Profile at Year {year_to_plot} - Aggregated Demand')
    ax.legend()

    # Adding a box with average daily energy consumption and peak power
    textstr = f'Avg. Daily Energy: {avg_daily_energy_consumption:.2f} kWh\nAvg. Daily Peak Power: {avg_daily_peak_power:.2f} kW'
    props = dict(boxstyle='round', facecolor='white', alpha=0.5)
    ax.text(0.95, 0.05, textstr, transform=ax.transAxes, fontsize=12, verticalalignment='bottom', horizontalalignment='right', bbox=props)

    st.pyplot(fig)


def convert_to_hourly(demand_data: np.ndarray) -> np.ndarray:
    """
    Convert minute-resolution demand data to hourly resolution.

    Args:
        demand_data (np.ndarray): Minute-resolution demand data.

    Returns:
        np.ndarray: Hourly-resolution demand data.
    """
    hourly_data = demand_data.reshape(-1, 60).sum(axis=1)
    return hourly_data


def load_and_simulate_ramp_data(uploaded_file: BytesIO, num_days: int, force_reinitialize: bool) -> List[User]:
    """
    Load and simulate RAMP data from an uploaded file.

    Args:
        uploaded_file (BytesIO): The uploaded RAMP input file in .xlsx format.
        num_days (int): The number of days to simulate.
        force_reinitialize (bool): Whether to force reinitialization of the simulation.

    Returns:
        List[User]: A list of User objects with simulated demand data.
    """
    users = []
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0)
        categories = df.iloc[:, 0].unique()

        for category in categories:
            with st.spinner(f'Generating load profiles for {category}, please wait...'):
                category_data = df[df.iloc[:, 0] == category]
                file_content = BytesIO()
                category_data.to_excel(file_content, index=False)
                file_content.seek(0)

                ramp_data, ramp_avg = load_ramp_data(file_content, num_days, force_reinitialize=True)
                # Reshape 1D array to 2D array
                ramp_data = ramp_data.reshape(-1, 1)
                # Convert to pd.DataFrame
                num_years = ramp_data.shape[1]
                ramp_data = pd.DataFrame(ramp_data, columns=[f'Year_{i+1}' for i in range(num_years)])
                if ramp_data is not None:
                    user = User(name=category, demand_data=ramp_data)
                    users.append(user)
                    st.success(f"Load profiles for {category} generated successfully using RAMP")
                else:
                    st.error(f"Error processing data for {category}.")
    except Exception as e:
        st.error(f"Error processing the uploaded file: {e}")
    return users


def demand_assessment() -> None:
    """
    Streamlit application for demand assessment.
    """
    st.title("Demand Assessment")
    st.subheader("Simulate or upload load demand data for your project.")
    
    # Retrieve session state variables
    time_horizon = st.session_state.get("time_horizon")
    lat = st.session_state.get("lat")
    start_year = str(st.session_state.get("start_date").year)
    # Initialize session state variables
    initialize_session_state(st.session_state.default_values)
    # Initialize variables for demand data
    users = []
    
    st.write("Use the button below to clear all files within the demand folder before generating or uploading new demand data.")
    
    # Add a button for deleting files within the demand folder with an explanation
    if st.button(
        "Clear Demand Files", type="primary",
        help="This will delete all csv files within the demand folder. Use this if you want to start fresh with new demand data."
    ):
        clear_demand_folder(PathManager.DEMAND_FOLDER_PATH)
        st.success("Demand folder cleared successfully.")
    
    st.write("Choose one of the following options to import or generate demand data:")
    
    with st.expander("📂 Import Demand Data", expanded=False):
        import_type = st.radio("Choose import method:", ["Individual user demand CSVs", "Aggregated demand CSV"], key="import_type")
    
        if import_type == "Individual user demand CSVs":
            num_users = st.number_input("Number of users:", min_value=1, step=1)
            for i in range(num_users):
                user_name = st.text_input(f"Name of user category {i + 1}:")
                delimiter_options = {"Comma (,)": ",", "Semicolon (;)": ";", "Tab (\\t)": "\t"}
                decimal_options = {"Dot (.)": ".", "Comma (,)": ","}
    
                delimiter = st.selectbox("Select delimiter", list(delimiter_options.keys()), key=f"delimiter_{i}")
                decimal = st.selectbox("Select decimal separator", list(decimal_options.keys()), key=f"decimal_{i}")
    
                delimiter_value = delimiter_options[delimiter]
                decimal_value = decimal_options[decimal]
    
                uploaded_file = st.file_uploader(f"Choose CSV file for {user_name}", type=["csv"], key=f"user_{i}_csv")
    
                if uploaded_file is not None:
                    csv_data = load_csv_data(uploaded_file, delimiter_value, decimal_value)
                    if csv_data is not None:
                        st.dataframe(csv_data.head())
                        st.dataframe(csv_data.shape)
                        if csv_data.shape[1] < time_horizon:
                            st.error(f"The uploaded file must have at least {time_horizon} columns for the demand data.")
                        else:
                            if st.button("Save single user data", key=f"save_user_demand_button_{i}"):
                                demand_csv_path = save_demand_data(csv_data, filename=f"{user_name}.csv", start_year=start_year)
                                st.success(f"{user_name}.csv uploaded successfully and saved at {demand_csv_path}")
                                user = User(name=user_name, demand_data=csv_data)
                                users.append(user)
    
            if users and st.button("Aggregate and Save load demand", key="aggregate_save_button_csv"):
                aggregated_demand = np.sum([user.demand_data.to_numpy().flatten() for user in users], axis=0)
                demand_df = multi_years_demand(aggregated_demand, time_horizon)
                demand_csv_path = save_demand_data(demand_df, filename="Aggregated Demand.csv", start_year=start_year)
                st.success(f"Aggregated Demand.csv created successfully at {demand_csv_path}")
                st.session_state.aggregated_demand_flag = True
    
        elif import_type == "Aggregated demand CSV":
            delimiter_options = {"Comma (,)": ",", "Semicolon (;)": ";", "Tab (\\t)": "\t"}
            decimal_options = {"Dot (.)": ".", "Comma (,)": ","}
    
            delimiter = st.selectbox("Select delimiter", list(delimiter_options.keys()), key="agg_delimiter")
            decimal = st.selectbox("Select decimal separator", list(decimal_options.keys()), key="agg_decimal")
    
            delimiter_value = delimiter_options[delimiter]
            decimal_value = decimal_options[decimal]
    
            uploaded_file = st.file_uploader("Choose an aggregated demand CSV file", type=["csv"], key="aggregated_csv")
    
            if uploaded_file is not None:
                csv_data = load_csv_data(uploaded_file, delimiter_value, decimal_value)
                if csv_data is not None:
                    st.dataframe(csv_data.head())
                    st.write(csv_data.shape)
                    if csv_data.shape[1] < time_horizon:
                        st.error(f"The uploaded file must have at least {time_horizon} columns for the demand data.")
                    else:
                        if st.button("Save Aggregated Demand", key="save_aggregated_button"):
                            demand_csv_path = save_demand_data(csv_data, filename='Aggregated Demand.csv', start_year=start_year)
                            st.success(f"Aggregated Demand.csv uploaded successfully and saved at {demand_csv_path}")
                            st.session_state.aggregated_demand_flag = True
    
    with st.expander("🧭 Use Built-in Load Demand Archetypes for Sub-Sahara Africa", expanded=False):
        st.write("""
        MicroGridsPy provides archetypes for Sub-Saharan Africa, based on a study of typical electricity usage patterns. 
        These include 100 household types, 5 health centers, and 1 school, characterized by wealth, latitude, and climate factors.
        For details, see the [IEEE paper](https://ieeexplore.ieee.org/document/10363287).
        """)
        image_path = PathManager.IMAGES_PATH / "archetypes.png"
        st.image(str(image_path), use_column_width=True)
        st.session_state.demand_growth = st.number_input("Enter yearly demand growth percentage:", value=st.session_state.demand_growth)
        st.session_state.cooling_period = st.selectbox("Select cooling period:", ["NC", "AY", "OM", "AS"])
        st.session_state.h_tier1 = st.number_input("Enter number of households for tier 1:", value=st.session_state.h_tier1)
        st.session_state.h_tier2 = st.number_input("Enter number of households for tier 2:", value=st.session_state.h_tier2)
        st.session_state.h_tier3 = st.number_input("Enter number of households for tier 3:", value=st.session_state.h_tier3)
        st.session_state.h_tier4 = st.number_input("Enter number of households for tier 4:", value=st.session_state.h_tier4)
        st.session_state.h_tier5 = st.number_input("Enter number of households for tier 5:", value=st.session_state.h_tier5)
        st.session_state.schools = st.number_input("Enter number of schools:", value=st.session_state.schools)
        st.session_state.hospital_1 = st.number_input("Enter number of hospitals for type 1:", value=st.session_state.hospital_1)
        st.session_state.hospital_2 = st.number_input("Enter number of hospitals for type 2:", value=st.session_state.hospital_2)
        st.session_state.hospital_3 = st.number_input("Enter number of hospitals for type 3:", value=st.session_state.hospital_3)
        st.session_state.hospital_4 = st.number_input("Enter number of hospitals for type 4:", value=st.session_state.hospital_4)
        st.session_state.hospital_5 = st.number_input("Enter number of hospitals for type 5:", value=st.session_state.hospital_5)
    
        if st.button("Generate Demand Data using archetypes"):
            with st.spinner("Generating load demand data..."):
                demand_data, users = demand_generation_with_user_input(lat, time_horizon)
            # Save individual user demand data
            for user in users:
                user_csv_path = save_demand_data(user.demand_data, filename=f"{user.name}.csv", start_year=start_year)
                st.success(f"{user.name}.csv saved successfully at {user_csv_path}")
            # Save the aggregated demand data
            demand_csv_path = save_demand_data(demand_data, filename='Aggregated Demand.csv', start_year=start_year)
            st.success(f"Aggregated Demand.csv uploaded successfully and saved at {demand_csv_path}")
            st.session_state.aggregated_demand_flag = True
    
    with st.expander("⏯️ Simulate High-Resolution Load Profiles using RAMP Software", expanded=False):
        st.write("RAMP is an open-source software suite for the stochastic simulation of any user-driven energy demand time series based on few simple inputs. Learn more.")
        image_path = PathManager.IMAGES_PATH / "ramp.png"
        st.image(str(image_path), use_column_width=True)
    
        num_days = st.number_input("Enter the number of days to simulate:", value=365)
        if num_days < 365:
            st.warning(f"If the number of days to simulate is less than 365, the software will automatically repeat the data to complete the year. Please note that repeating data may reduce variability in the final load profile.")
    
        uploaded_file = st.file_uploader("Choose a RAMP Input file (.xlsx)", key="ramp")
    
        if uploaded_file is not None:
            file_content = BytesIO(uploaded_file.read())
            users = load_and_simulate_ramp_data(file_content, num_days, force_reinitialize=True)
    
            if users:
                # Select user category to visualize
                selected_user_name = st.selectbox("Select user category to visualize", [user.name for user in users])
                selected_user = next((user for user in users if user.name == selected_user_name), None)
                if selected_user:
                    st.write(f"Visualizing load profile for **{selected_user.name}** (minute-resolution)")
                    profiles_daily_avg = selected_user.demand_data.to_numpy().reshape(-1, 1440).mean(axis=0)
                    plot_cloud_plot_with_avg(selected_user.demand_data.to_numpy(), profiles_daily_avg, title=f"Load Profile for **{selected_user.name}**")
    
                # Option for Constant multi-years demand or evolving demand
                demand_type = st.radio("Select demand type:", ["Constant demand", "Evolving demand"])
                growth_rate = st.number_input("Enter annual growth rate (%):", value=2.0) if demand_type == "Evolving demand" else None
                growth_rate = growth_rate / 100 if growth_rate is not None else None
    
                if st.button("Aggregate and Save Demand Data", key="aggregate_save_button_ramp"):
                    # Aggregate and save data
                    aggregated_demand = np.sum([user.demand_data.to_numpy() for user in users], axis=0)
                    hourly_aggregated_demand = convert_to_hourly(aggregated_demand)
                    demand_df = multi_years_demand(hourly_aggregated_demand, time_horizon, growth_rate)
    
                    # Save aggregated demand data
                    demand_csv_path = save_demand_data(demand_df, filename="Aggregated Demand.csv", start_year=start_year)
                    st.success(f"Aggregated Demand.csv created successfully at {demand_csv_path}")
    
                    # Save individual user category demand data over the years
                    for user in users:
                        user_hourly_demand = convert_to_hourly(user.demand_data.to_numpy().flatten())
                        user_demand_df = multi_years_demand(user_hourly_demand, time_horizon, growth_rate)
                        user_csv_path = save_demand_data(user_demand_df, filename=f"{user.name}.csv", start_year=start_year)
                        st.success(f"{user.name}.csv saved successfully at {user_csv_path}")
    
                    st.session_state.aggregated_demand_flag = True

    # Visualization of aggregated demand data                
    st.write("### Demand Data Visualization")
    if st.session_state.aggregated_demand_flag:
        plot_demand_data(time_horizon, start_year)
    else:
        st.warning("No aggregated demand data available for visualization.")
    
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Resource Assessment"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Renewables Characterization"
            st.rerun()
