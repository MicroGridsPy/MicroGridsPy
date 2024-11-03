import os
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import seaborn as sns

from typing import Optional

from config.path_manager import PathManager
from microgridspy.gui.utils import initialize_session_state, csv_upload_interface
from microgridspy.utils.grid_availability import simulate_grid_availability

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
    
def save_grid_availability_data(grid_availability_data: pd.DataFrame, project_name: str, start_year: str) -> None:
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
    grid_availability_data.index = range(1, len(grid_availability_data) + 1)
    grid_availability_data.index.name = 'Periods'

    # Rename the columns to the correct years starting from the start date
    num_years = len(grid_availability_data.columns)
    new_column_names = [str(int(start_year) + i) for i in range(num_years)]
    grid_availability_data.columns = new_column_names

    # Save the demand data to a CSV file into the Inputs folder
    inputs_folder_path = os.path.join(PathManager.GRID_AVAILABILITY_FILE_PATH)
    grid_availability_data.to_csv(inputs_folder_path, index=True)

    # Save the demand data to a CSV file into the related project folder
    path_manager = PathManager(project_name)
    project_folder_path = os.path.join(path_manager.PROJECTS_FOLDER_PATH / project_name / "Grid Availability.csv")
    grid_availability_data.to_csv(project_folder_path, index=True)

    st.success(f"Grid Availability.csv successfully saved at {inputs_folder_path} for current use as well as at {project_folder_path} for future use.")

def heatmap_visualization(data, selected_year):
    fig, ax = plt.subplots(figsize=(15, 9))
    
    # Create a custom colormap with just red and green
    colors = ['red', 'green']
    cmap = ListedColormap(colors)
    
    # Get the data for the selected year
    year_data = data.iloc[:, selected_year]
    periods = len(year_data)

    if periods == 8760:  # Hourly data for a year
        # Reshape the data to 24 hours x 365 days
        reshaped_data = year_data.values.reshape(365, 24).T
        
        # Create the heatmap
        sns.heatmap(reshaped_data, 
                    cmap=cmap, cbar=False, ax=ax, 
                    vmin=0, vmax=1)
        
        # Set x-axis ticks to show days
        ax.set_xticks(np.arange(0, 366, 30))  # Set tick every 30 days
        ax.set_xticklabels(np.arange(0, 366, 30))
        ax.set_xlabel('Days of the year')
        
        # Set y-axis ticks to show hours
        ax.set_yticks(np.arange(0, 25, 6))  # Set tick every 6 hours
        ax.set_yticklabels(np.arange(0, 25, 6))
        ax.set_ylabel('Hours of the day')
    
    else:  # For any other number of periods
        # Create the heatmap
        sns.heatmap(year_data.to_frame().T, 
                    cmap=cmap, cbar=False, ax=ax, 
                    vmin=0, vmax=1)
        
        # Set x-axis ticks
        num_ticks = min(10, periods)  # Show at most 10 ticks
        tick_locations = np.linspace(0, periods-1, num_ticks, dtype=int)
        ax.set_xticks(tick_locations)
        ax.set_xticklabels(tick_locations)
        ax.set_xlabel('Periods')
        
        ax.set_yticks([])  # Remove y-axis ticks
        ax.set_ylabel('Grid Availability')

    ax.set_title(f'Grid Availability Heatmap for Year {selected_year}')
    
    # Custom colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, ticks=[0.25, 0.75])
    cbar.set_ticklabels(['Not Available', 'Available'])
    
    st.pyplot(fig)

def calculate_summary_stats(data, selected_year):
    year_data = data.iloc[:, selected_year-1]
    availability_percentage = year_data.mean() * 100
    longest_outage = (1 - year_data).groupby((1 - year_data).diff().ne(0).cumsum()).sum().max()
    total_outages = (1 - year_data).sum()
    return availability_percentage, longest_outage, total_outages

def grid_technology() -> None:
    """Streamlit page for configuring grid technology parameters."""
    st.title("Grid Connection Parameters")
    st.subheader("Define the parameters for the grid connection system")
    image_path = PathManager.IMAGES_PATH / "technology_characterization.png"
    st.image(str(image_path), use_column_width=True, caption="Overview of the grid connection parameters")

    has_grid_connection = st.session_state.get('grid_connection', False)
    project_name = st.session_state.get('project_name')
    grid_connection_type = st.session_state.get('grid_connection_type')

    grid_availability = None

    if has_grid_connection:
        # Initialize session state variables
        initialize_session_state(st.session_state.default_values, 'grid_params')
        currency = st.session_state.get('currency', 'USD')
        # Get start year and time horizon from session state
        start_year = st.session_state.get("start_date").year
        time_horizon = st.session_state.get("time_horizon", 20)
        periods = st.session_state.get('periods', 8760)  # Assuming hourly resolution by default
    
        st.session_state.year_grid_connection = st.slider("Year of Grid Connection", min_value=start_year, max_value=start_year + time_horizon, value=start_year)
        electricity_purchased_cost = st.number_input(f"Electricity Purchase Cost [{currency}/kWh]", min_value=0.0, value=st.session_state.electricity_purchased_cost * 1000)
        st.session_state.electricity_purchased_cost = electricity_purchased_cost / 1000
        if grid_connection_type == 1: 
            electricity_sold_price = st.number_input(f"Electricity Selling Price [{currency}/kWh]", min_value=0.0, value=st.session_state.electricity_sold_price * 1000)
            st.session_state.electricity_sold_price = electricity_sold_price / 1000
        st.session_state.grid_distance = st.number_input("Distance to Grid [km]", min_value=0.0, value=st.session_state.grid_distance)
        st.session_state.grid_connection_cost = st.number_input(f"Grid Connection Cost [{currency}]", min_value=0.0, value=st.session_state.grid_connection_cost)
        st.session_state.grid_maintenance_cost = st.number_input(f"Grid Maintenance Cost as % of connection cost [%]", min_value=0.0, value=st.session_state.grid_maintenance_cost * 100) / 100
        st.session_state.maximum_grid_power = st.number_input("Maximum Grid Power [W]", min_value=0.0, value=st.session_state.maximum_grid_power)
        st.session_state.national_grid_specific_co2_emissions = st.number_input("National Grid Specific CO2 Emissions [kgCO2/kWh]", min_value=0.0, value=st.session_state.national_grid_specific_co2_emissions)

        with st.expander("Grid Availability", expanded=True):
            st.session_state.grid_availability_simulation = st.checkbox(
                "Enable Grid Availability Simulation", 
                value=st.session_state.grid_availability_simulation,
                help="Model intermittent grid availability. This is crucial for areas with unreliable grid supply.")

            if st.session_state.grid_availability_simulation:
                st.session_state.grid_average_number_outages = st.number_input(
                    "Average Number of Outages [outages/year]",
                    value=st.session_state.grid_average_number_outages)
                
                st.session_state.grid_average_outage_duration = st.number_input(
                    "Average Outage Duration [hours]",
                    value=st.session_state.grid_average_outage_duration)

                if st.button("Simulate Grid Availability"):
                    with st.spinner("Simulating Grid Availability using Weibull distribution..."):
                        year_grid_connection = st.session_state.year_grid_connection - start_year + 1
                        grid_availability = simulate_grid_availability(
                            st.session_state.grid_average_number_outages,
                            st.session_state.grid_average_outage_duration,
                            time_horizon,
                            year_grid_connection,
                            periods)

                    st.success("Grid availability simulation completed!")
                    save_grid_availability_data(grid_availability, project_name=project_name, start_year=start_year)

            else:
                uploaded_file, delimiter_value, decimal_value = csv_upload_interface("grid_availability")

                if uploaded_file is not None:
                    grid_availability = load_csv_data(uploaded_file, delimiter_value, decimal_value, "Grid Availability")
                    if grid_availability is not None:
                        st.dataframe(grid_availability.head())
                        st.dataframe(grid_availability.shape)
                        if grid_availability.shape != (periods, time_horizon):
                            st.error(f"The uploaded file must have {time_horizon} rows and {periods} columns for the grid availability data.")
                        else:
                            if st.button("Save Grid Availability Data"):
                                save_grid_availability_data(grid_availability, project_name=project_name, start_year=start_year)

        # Visualization section
        st.write("### Grid Availability Visualization")
        file_path = PathManager.GRID_AVAILABILITY_FILE_PATH
        if os.path.exists(file_path):
            grid_availability_data = pd.read_csv(file_path, index_col='Periods')
            time_horizon = grid_availability_data.shape[1]
            selected_year = st.slider("Select Year", min_value=start_year, max_value=start_year + time_horizon, value=start_year) - start_year

            heatmap_visualization(grid_availability_data, selected_year)

            # Summary statistics
            st.write("**Summary Statistics**")
            availability, longest_outage, total_outages = calculate_summary_stats(grid_availability_data, selected_year)
    
            col1, col2, col3 = st.columns(3)
            col1.metric("Grid Availability", f"{availability:.2f}%")
            col2.metric("Longest Outage", f"{longest_outage:.0f} hours")
            col3.metric("Total Outage Time", f"{total_outages:.0f} hours")
        else:
            st.warning("Grid availability data not found. Please upload or simulate grid availability data to visualize it.")

    else:
        st.warning("Grid connection is not included in the system configuration. If you want to include grid connection, please edit the project settings page.")

    st.markdown("---")
    
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Generator Characterization"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Optimization"
            st.rerun()