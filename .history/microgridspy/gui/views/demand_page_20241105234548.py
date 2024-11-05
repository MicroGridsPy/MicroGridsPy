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
from microgridspy.utils.archetypes import demand_calculation
from microgridspy.gui.utils import initialize_session_state, csv_upload_interface

class User:
    def __init__(self, name, demand_data):
        self.name = name
        self.demand_data = demand_data

def load_csv_data(uploaded_file, delimiter: str, decimal: str, resource_name: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Load CSV data with given delimiter and decimal options.
    
    Args:
        uploaded_file: The uploaded CSV file.
        delimiter (str): The delimiter used in the CSV file.
        decimal (str): The decimal separator used in the CSV file.
        resource_name (Optional[str]): The name of the resource (used for column naming).
    
    Returns:
        Optional[pd.DataFrame]: The loaded DataFrame or None if an error occurred.
    """
    try:
        data = pd.read_csv(uploaded_file, delimiter=delimiter, decimal=decimal)
        data = data.apply(pd.to_numeric, errors='coerce')
        
        data.index = range(1, len(data) + 1)
        data.index.name = 'Periods'
        
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


def save_demand_data(demand_data: pd.DataFrame, filename: str, project_name: str, start_year: str) -> None:
    """
    Save demand data to a CSV file with the correct year columns starting from the start date.
    Assign the data to the demand xarray parameter of the ProjectParameters instance.

    Args:
        demand_data (pd.DataFrame): The demand data to save.
        filename (str): The filename for the CSV file.
        project_name (str): The name of the project.
        start_year (str): The start year for the demand data.

    """
    # Add the "Hours" index column ranging from 1 to len(demand_data)
    demand_data.index = range(1, len(demand_data) + 1)
    demand_data.index.name = 'Periods'

    # Rename the columns to the correct years starting from the start date
    num_years = len(demand_data.columns)
    new_column_names = [str(int(start_year) + i) for i in range(num_years)]
    demand_data.columns = new_column_names

    # Save the demand data to a CSV file into the Inputs folder
    inputs_folder_path = os.path.join(PathManager.DEMAND_FOLDER_PATH, filename)
    demand_data.to_csv(inputs_folder_path, index=True)

    # Save the demand data to a CSV file into the related project folder
    path_manager = PathManager(project_name)
    project_folder_path = os.path.join(path_manager.PROJECTS_FOLDER_PATH / project_name / "demand" , filename)
    demand_data.to_csv(project_folder_path, index=True)

    st.success(f"{filename}.csv successfully saved at {inputs_folder_path} for current use as well as at {project_folder_path} for future use.")


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

def load_demand_files():
    """Load all CSV files from the demand folder."""
    demand_files = {}
    for file in os.listdir(PathManager.DEMAND_FOLDER_PATH):
        if file.endswith('.csv'):
            file_path = os.path.join(PathManager.DEMAND_FOLDER_PATH, file)
            demand_files[file[:-4]] = pd.read_csv(file_path, index_col='Periods')
    return demand_files

def plot_daily_profile(data, selected_types, selected_year):
    """Plot daily demand profile for selected types and year."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for demand_type in selected_types:
        daily_profile = data[demand_type][selected_year].values.reshape(-1, 24).mean(axis=0)
        ax.plot(range(24), daily_profile / 1000, label=demand_type)
    
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Average Demand (kW)')
    ax.set_title(f'Average Daily Demand Profile - {selected_year}')
    ax.legend()
    ax.grid(True)
    
    return fig

def demand_visualization() -> None:
    """Streamlit application for demand visualization."""
    demand_files = load_demand_files()
    if not demand_files:
        st.warning("No demand data files found in the demand folder.")
        return

    # Select demand types to visualize
    demand_types = list(demand_files.keys())
    selected_types = st.multiselect("Select demand types to visualize", demand_types, default=demand_types[0] if demand_types else None)

    if not selected_types:
        st.warning("Please select at least one demand type to visualize.")
        return

    # Get start year and time horizon from session state
    start_year = st.session_state.get("start_date").year
    time_horizon = st.session_state.get("time_horizon")

    # Daily profile plot
    st.subheader("Daily Demand Profile")
    selected_year = st.slider("Select year for daily profile", min_value=start_year, max_value=start_year + time_horizon, value=start_year)
    daily_fig = plot_daily_profile(demand_files, selected_types, str(selected_year))
    st.pyplot(daily_fig)

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
    project_name = st.session_state.get("project_name")
    # Initialize session state variables
    initialize_session_state(st.session_state.default_values, "archetypes_params")
    # Initialize variables for demand data
    users = []
    
    st.write("Use the button below to clear all files within the demand folder before generating or uploading new demand data.")
    
    # Add a button for deleting files within the demand folder with an explanation
    if st.button(
        "Clear Demand Files", type="primary",
        help="This will delete all csv files within the demand folder. Use this if you want to start fresh with new demand data."
    ):
        clear_demand_folder(PathManager.DEMAND_FOLDER_PATH)
        path_manager = PathManager(project_name)
        project_folder_path = path_manager.PROJECTS_FOLDER_PATH / project_name / "demand"
        clear_demand_folder(project_folder_path)
        st.success("Demand folder cleared successfully.")
    
    st.write("Choose one of the following options to import or generate demand data:")
    
    with st.expander("📂 Import Demand Data", expanded=False):
        import_type = st.radio("Choose import method:", ["Individual user demand CSVs", "Aggregated demand CSV"], key="import_type")
    
        if import_type == "Individual user demand CSVs":
            num_users = st.number_input("Number of user categories:", min_value=1, step=1)
            for i in range(num_users):
                user_name = st.text_input(f"Name of user category {i + 1}:")
                uploaded_file, delimiter_value, decimal_value = csv_upload_interface(f"user_{i}")
    
                if uploaded_file is not None:
                    csv_data = load_csv_data(uploaded_file, delimiter_value, decimal_value, user_name)
                    if csv_data is not None:
                        st.dataframe(csv_data.head())
                        st.dataframe(csv_data.shape)
                        if csv_data.shape[1] < time_horizon:
                            st.error(f"The uploaded file must have at least {time_horizon} columns for the demand data.")
                        else:
                            if st.button("Save single user data", key=f"save_user_demand_button_{i}"):
                                save_demand_data(csv_data, filename=f"{user_name}.csv", project_name=project_name, start_year=start_year)
                                user = User(name=user_name, demand_data=csv_data)
                                users.append(user)
    
            if users and st.button("Aggregate and Save load demand", key="aggregate_save_button_csv"):
                aggregated_demand = np.sum([user.demand_data.to_numpy().flatten() for user in users], axis=0)
                demand_df = multi_years_demand(aggregated_demand, time_horizon)
                save_demand_data(demand_df, filename="Aggregated Demand.csv", project_name=project_name, start_year=start_year)
                st.session_state.aggregated_demand_flag = True
    
        elif import_type == "Aggregated demand CSV":
            uploaded_file, delimiter_value, decimal_value = csv_upload_interface("aggregated")
    
            if uploaded_file is not None:
                csv_data = load_csv_data(uploaded_file, delimiter_value, decimal_value)
                if csv_data is not None:
                    st.dataframe(csv_data.head())
                    st.write(csv_data.shape)
                    if csv_data.shape[1] < time_horizon:
                        st.error(f"The uploaded file must have at least {time_horizon} columns for the demand data.")
                    else:
                        if st.button("Save Aggregated Demand", key="save_aggregated_button"):
                            save_demand_data(csv_data, filename='Aggregated Demand.csv', project_name=project_name, start_year=start_year)
    
    with st.expander("🧭 Use Built-in Load Demand Archetypes for Sub-Sahara Africa", expanded=False):
        st.write("""
        MicroGridsPy provides archetypes for Sub-Saharan Africa, based on a study of typical electricity usage patterns. 
        These include 100 household types, 5 health centers, and 1 school, characterized by wealth, latitude, and climate factors.
        For details, see the [IEEE paper](https://ieeexplore.ieee.org/document/10363287).
        """)
        image_path = PathManager.IMAGES_PATH / "archetypes.png"
        st.image(str(image_path), use_column_width=True)
        demand_growth = st.number_input("Enter yearly demand growth percentage [%]:", min_value=0.0, value=st.session_state.demand_growth * 100)
        st.session_state.demand_growth = demand_growth / 100
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
                save_demand_data(user.demand_data, filename=f"{user.name}.csv", project_name=project_name, start_year=start_year)
            # Save the aggregated demand data
            save_demand_data(demand_data, filename='Aggregated Demand.csv', project_name=project_name, start_year=start_year)
    
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
                    save_demand_data(demand_df, filename="Aggregated Demand.csv", project_name=project_name, start_year=start_year)
    
                    # Save individual user category demand data over the years
                    for user in users:
                        user_hourly_demand = convert_to_hourly(user.demand_data.to_numpy().flatten())
                        user_demand_df = multi_years_demand(user_hourly_demand, time_horizon, growth_rate)
                        save_demand_data(user_demand_df, filename=f"{user.name}.csv", project_name=project_name, start_year=start_year)
    
                    st.session_state.aggregated_demand_flag = True

    # Visualization of aggregated demand data                
    st.write("### Demand Data Visualization")
    demand_visualization()

    st.write("---")  # Add a separator
    
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Resource Assessment"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Renewables Characterization"
            st.rerun()
