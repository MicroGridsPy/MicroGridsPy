"""
This module provides the resource assessment page for the MicroGridsPy Streamlit application. 
It allows users to download or upload resource availability data for their project. 
Users can configure specific resource parameters for solar and wind energy, visualize the data, 
and save the updated configuration to a CSV file.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

import folium
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from geopy.exc import GeopyError
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium

from config.path_manager import PathManager
from microgridspy.model.parameters import ProjectParameters
from microgridspy.utils.nasa_power import download_nasa_pv_data, download_nasa_wind_data


def delete_resource_file(file_path: Path) -> None:
    """Delete the resource availability file."""
    if os.path.exists(file_path):
        os.remove(file_path)
        st.success(f"{file_path} deleted successfully.")
    else:
        st.info(f"{file_path} does not exist.")


def initialize_session_state(default_values: ProjectParameters) -> None:
    """Initialize session state with default values if not already set."""
    resource_assessment = default_values.resource_assessment
    renewables_params = default_values.renewables_params
    session_vars = {
        'res_sources': renewables_params.res_sources,
        'res_names': renewables_params.res_names,
        'res_nominal_capacity': renewables_params.res_nominal_capacity,
        'location': resource_assessment.location,
        'lat': resource_assessment.lat,
        'lon': resource_assessment.lon,
        'time_zone': resource_assessment.time_zone,
        'turbine_type': resource_assessment.turbine_type,
        'turbine_model': resource_assessment.turbine_model,
        'drivetrain_efficiency': resource_assessment.drivetrain_efficiency,
        'nom_power': resource_assessment.nom_power,
        'tilt': resource_assessment.tilt,
        'azim': resource_assessment.azim,
        'ro_ground': resource_assessment.ro_ground,
        'k_T': resource_assessment.k_T,
        'NMOT': resource_assessment.NMOT,
        'T_NMOT': resource_assessment.T_NMOT,
        'G_NMOT': resource_assessment.G_NMOT,
        'resource_data_saved': False  # Add this flag to track if data has been saved
    }

    for key, value in session_vars.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_nasa_power_params() -> dict:
    """Get NASA POWER parameters from session state."""
    params = {
        'lat': st.session_state.lat,
        'lon': st.session_state.lon,
        'time_zone': st.session_state.time_zone,
        'turbine_model': st.session_state.turbine_model,
        'turbine_type': st.session_state.turbine_type,
        'drivetrain_efficiency': st.session_state.drivetrain_efficiency,
        'nom_power': st.session_state.nom_power,
        'tilt': st.session_state.tilt,
        'azimuth': st.session_state.azim,
        'ro_ground': st.session_state.ro_ground,
        'k_T': st.session_state.k_T,
        'NMOT': st.session_state.NMOT,
        'T_NMOT': st.session_state.T_NMOT,
        'G_NMOT': st.session_state.G_NMOT
    }
    return params


def get_coordinates(address: str) -> Tuple[float, float]:
    """Get the latitude and longitude of a given address using Nominatim."""
    geolocator = Nominatim(user_agent="myGeocoder")
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
        else:
            raise ValueError(f"No location found for the given address: {address}")
    except GeopyError as e:
        raise ValueError(f"Geocoding error: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {e}")


def handle_location_input(address: str) -> None:
    """Handle user input for project location and update session state."""
    try:
        st.session_state.lat, st.session_state.lon = get_coordinates(address)
        st.session_state.location = f"{st.session_state.lat}, {st.session_state.lon}"
        st.success("Location found!")
    except ValueError as e:
        st.error(f"Could not find location: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")


def load_csv_data(uploaded_file, resource_name: str, delimiter: str, decimal: str) -> Optional[pd.DataFrame]:
    """Load CSV data with given delimiter and decimal options."""
    try:
        data = pd.read_csv(uploaded_file, delimiter=delimiter, decimal=decimal)
        data = data.apply(pd.to_numeric, errors='coerce')

        if len(data.columns) > 1:
            selected_column = st.selectbox("Select the column representing electricity data", data.columns)
            data = data[[selected_column]]

        data.columns = [resource_name]
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


def save_resource_data(resource_data: pd.DataFrame, resource_name: str) -> None:
    """Save resource data to a CSV file. Overwrite if the file already exists."""
    file_path = PathManager.RESOURCE_FILE_PATH

    if not file_path.exists():
        combined_df = resource_data
        combined_df.columns = [resource_name]
        combined_df.to_csv(file_path, index=True)
    else:
        existing_data = pd.read_csv(file_path, index_col='Periods')
        existing_data[resource_name] = resource_data[resource_name]
        existing_data.to_csv(file_path, index=True)

    st.session_state.resource_data_saved = True
    st.success(f"Resource data saved successfully for {resource_name} at {file_path}")


def plot_resource_data(resource_data: pd.DataFrame, resource_name: str, selected_month: str) -> None:
    """Plot the average daily profile of the resource availability (hourly resolution) and show variability range."""
    resource_data['Hour'] = resource_data.index % 24
    resource_data['Month'] = ((resource_data.index) // 24) % 12 + 1

    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    if selected_month == 'All Year':
        st.write(f"Displaying average daily profile for **{resource_name}**")
        filtered_data = resource_data
    else:
        month_number = month_names.index(selected_month) + 1
        st.write(f"Displaying average daily profile for **{resource_name}** in **{selected_month}**")
        filtered_data = resource_data[resource_data['Month'] == month_number]

    hourly_data = filtered_data.groupby('Hour')[resource_name]
    average_daily_profile = hourly_data.mean() / 1000  # Convert to kW
    variability_range_min = hourly_data.min() / 1000
    variability_range_max = hourly_data.max() / 1000

    x_labels = [f"{hour:02d}:00" for hour in range(24)]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(average_daily_profile.index, average_daily_profile.values, label='Average Profile')
    ax.fill_between(average_daily_profile.index, variability_range_min, variability_range_max, color='gray', alpha=0.3, label='Variability Range')
    ax.set_xticks(range(24))
    ax.set_xticklabels(x_labels, rotation=45)
    ax.set_ylabel(f"Resource: {resource_name} [kW]")
    ax.set_title(f"Average Daily Profile of Resource: {resource_name} - Unit of electricity production")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)


def resource_assessment() -> None:
    """Resource Assessment Page for configuring resource parameters."""
    st.title("Resource Assessment")
    st.subheader("Download or upload resource availability data for your project.")
    
    initialize_session_state(st.session_state.default_values)
    nasa_power_params = st.session_state.default_values.nasa_power_params

    # Initialize resource data variables
    solar_resource_data = None
    wind_resource_data = None
    other_resource_data = None

    st.subheader("Select Project Location")
    st.write("Select the location for your project using the map below or enter an address to find the location.")
    
    address = st.text_input("Enter location address:")
    if address:
        handle_location_input(address)

    initial_coords = [st.session_state.lat, st.session_state.lon]
    m = folium.Map(location=initial_coords, zoom_start=5)
    folium.Marker(initial_coords, tooltip="Project Location").add_to(m)
    output = st_folium(m, width=700, height=500)

    if output and output.get('last_clicked'):
        st.session_state.lat = output['last_clicked']['lat']
        st.session_state.lon = output['last_clicked']['lng']
        st.session_state.location = f"{st.session_state.lat}, {st.session_state.lon}"

    st.write(f"Selected Coordinates: {st.session_state.lat}, {st.session_state.lon}")

    st.subheader("Renewables Time Series Data")
    st.write("Configure specific resource parameters for solar and wind or import your own data.")

    if st.button(
        "Clear Resource Availability File", type="primary",
        help="This will delete the csv file within the inputs folder. Use this if you want to start fresh with new resource data."):
        delete_resource_file(PathManager.RESOURCE_FILE_PATH)

    st.session_state.res_sources = st.number_input(
        "Number of Renewable Technologies", min_value=1, value=st.session_state.res_sources,
        help="Type the number of renewable sources and press enter.")
    
    if len(st.session_state.res_names) < st.session_state.res_sources:
        st.session_state.res_names.extend([f"Renewable Source {i+1}" for i in range(len(st.session_state.res_names), st.session_state.res_sources)])
    res_types = []

    for i in range(st.session_state.res_sources):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.res_names[i] = st.text_input(f"Name for Renewable Technology {i+1}", value=st.session_state.res_names[i], key=f"res_name_{i}")
        with col2:
            if i == 2:
                index_default = 2
            elif i == 0:
                index_default = 0
            else:
                index_default = 1
            res_type = st.selectbox(f"Type of Renewable Resource {i+1}", ["☀️ Solar Energy", "🌀 Wind Energy", "📝 Other"], index=index_default, key=f"res_type_{i}")
        res_types.append(res_type)

    for i in range(st.session_state.res_sources):
        res_name = st.session_state.res_names[i]
        res_type = res_types[i]

        st.write(f"### {res_name} Electricity Production")

        if res_type == "☀️ Solar Energy":
            with st.expander("⬇️ Download Solar Resource Availability from NASA POWER", expanded=False):
                st.write("""
                The NASA POWER project provides comprehensive solar and meteorological data beneficial for renewable energy applications. 
                It offers up-to-date and historical data from Earth observation satellites and models, supporting diverse applications. 
                MicroGridsPy leverages this data for endogenous solar and wind time series estimation.
                For more details, visit the [NASA POWER Project](https://power.larc.nasa.gov/).
                """)
                image_path = PathManager.IMAGES_PATH / "nasa_power.png"
                st.image(str(image_path), use_column_width=True)
                st.session_state.nom_power = st.number_input(f"Nominal Power for {res_name} [W]:", value=st.session_state.nom_power, key=f"nom_power_{i}")
                st.session_state.res_nominal_capacity[i] = st.session_state.nom_power
                st.session_state.tilt = st.number_input(f"Tilt Angle for {res_name} [degrees]:", value=st.session_state.tilt, key=f"tilt_{i}")
                st.session_state.azim = st.number_input(f"Azimuth Angle for {res_name} [degrees]:", value=st.session_state.azim, key=f"azim_{i}")
                st.session_state.ro_ground = st.number_input(f"Ground Reflectance for {res_name}:", min_value=0.0, max_value=1.0, value=st.session_state.ro_ground, key=f"ro_ground_{i}")
                st.session_state.k_T = st.number_input(f"Temperature Coefficient for {res_name}:", value=st.session_state.k_T, key=f"k_T_{i}")
                st.session_state.NMOT = st.number_input(f"Nominal Module Operating Temperature (NMOT) for {res_name} [°C]:", value=st.session_state.NMOT, key=f"NMOT_{i}")
                st.session_state.T_NMOT = st.number_input(f"Ambient Temperature at which NMOT is measured for {res_name} [°C]:", value=st.session_state.T_NMOT, key=f"T_NMOT_{i}")
                st.session_state.G_NMOT = st.number_input(f"Solar Irradiance at which NMOT is measured for {res_name} [W/m²]:", value=st.session_state.G_NMOT, key=f"G_NMOT_{i}")

                if st.button(f"Download Solar Data for {res_name}", key=f"download_solar_{i}"):
                    with st.spinner('Downloading and processing data from NASA POWER...'):
                        try:
                            solar_resource_data = download_nasa_pv_data(
                                res_name,
                                nasa_power_params.base_url,
                                nasa_power_params.loc_id,
                                nasa_power_params.parameters_1,
                                nasa_power_params.parameters_2,
                                nasa_power_params.parameters_3,
                                nasa_power_params.date_start,
                                nasa_power_params.date_end,
                                nasa_power_params.community,
                                nasa_power_params.temp_res_1,
                                nasa_power_params.temp_res_2,
                                nasa_power_params.output_format,
                                st.session_state.lat,
                                st.session_state.lon,
                                st.session_state.time_zone,
                                st.session_state.nom_power,
                                st.session_state.tilt,
                                st.session_state.azim,
                                st.session_state.ro_ground,
                                st.session_state.k_T,
                                st.session_state.NMOT,
                                st.session_state.T_NMOT,
                                st.session_state.G_NMOT
                            )
                            save_resource_data(solar_resource_data, res_name)
                        except Exception as e:
                            st.error(f"Error downloading NASA POWER data: {e}")

            with st.expander(f"📂 Upload CSV for {res_name}", expanded=False):
                st.session_state.res_nominal_capacity[i] = st.number_input(f"Nominal Capacity for {res_name} of the data (W)", value=st.session_state.res_nominal_capacity[i], key=f"nom_capacity_{i}")
                delimiter_options = {
                    "Comma (,)": ",",
                    "Semicolon (;)": ";",
                    "Tab (\\t)": "\t"}
                
                decimal_options = {
                    "Dot (.)": ".",
                    "Comma (,)": ","}
                
                delimiter = st.selectbox("Select delimiter", list(delimiter_options.keys()), key=f"delimiter_solar_{i}")
                decimal = st.selectbox("Select decimal separator", list(decimal_options.keys()), key=f"decimal_solar_{i}")
        
                delimiter_value = delimiter_options[delimiter]
                decimal_value = decimal_options[decimal]

                uploaded_file = st.file_uploader(f"Choose a file for {st.session_state.res_names[i]}", type=["csv"])

                if uploaded_file is not None:
                    solar_resource_data = load_csv_data(uploaded_file, res_name, delimiter_value, decimal_value)
                    if solar_resource_data is not None:
                        st.dataframe(solar_resource_data.head(10))
                        st.write(solar_resource_data.shape)

                if solar_resource_data is not None:
                    if st.button(f"Save Data for {res_name}", key=f"save_solar_csv_{i}"):
                        save_resource_data(solar_resource_data, res_name)

        elif res_type == "🌀 Wind Energy":
            with st.expander("⬇️ Download Wind Resource Availability from NASA POWER", expanded=False):
                st.write("""
                The NASA POWER project provides comprehensive solar and meteorological data beneficial for renewable energy applications. 
                It offers up-to-date and historical data from Earth observation satellites and models, supporting diverse applications. 
                MicroGridsPy leverages this data for endogenous solar and wind time series estimation.
                For more details, visit the [NASA POWER Project](https://power.larc.nasa.gov/).
                """)
                image_path = PathManager.IMAGES_PATH / "nasa_power.png"
                st.image(str(image_path), use_column_width=True)
                horizontal_models = ["Alstom.Eco.80", "NPS100c-21"]
                vertical_models = ["Hi-VAWT.DS1500", "Hi-VAWT.DS700"]
                
                st.session_state.turbine_type = st.selectbox(
                    f"Turbine Type for {res_name}:", options=["Horizontal Axis", "Vertical Axis"],
                    index=["Horizontal Axis", "Vertical Axis"].index(st.session_state.turbine_type), key=f"turbine_type_{i}")
                
                if st.session_state.turbine_type == "Horizontal Axis":
                    models = horizontal_models
                else:
                    models = vertical_models
                
                st.session_state.turbine_model = st.selectbox(
                    f"Turbine Model for {res_name}:", options=models,
                    index=models.index(st.session_state.turbine_model) if st.session_state.turbine_model in models else 0,
                    key=f"turbine_model_{i}")
                
                turbine_nom_power = {'Alstom.Eco.80': 1670000,'NPS100c-21': 100000,'Hi-VAWT.DS1500': 300,'Hi-VAWT.DS700': 700}
                st.session_state.res_nominal_capacity[i] = turbine_nom_power.get(st.session_state[f'turbine_model_{i}'], 0)
                
                st.session_state.drivetrain_efficiency = st.number_input(
                    f"Drivetrain Efficiency for {res_name}:", min_value=0.0, max_value=1.0,
                    value=st.session_state.drivetrain_efficiency, key=f"drivetrain_efficiency_{i}")
                
                if st.button(f"Download Wind Data for {res_name}", key=f"download_wind_{i}"):
                    with st.spinner('Downloading and processing data from NASA POWER...'):
                        try:
                            wind_resource_data = download_nasa_wind_data(
                                res_name,
                                nasa_power_params.base_url,
                                nasa_power_params.loc_id,
                                nasa_power_params.parameters_1,
                                nasa_power_params.parameters_2,
                                nasa_power_params.parameters_3,
                                nasa_power_params.date_start,
                                nasa_power_params.date_end,
                                nasa_power_params.community,
                                nasa_power_params.temp_res_1,
                                nasa_power_params.temp_res_2,
                                nasa_power_params.output_format,
                                st.session_state.lat,
                                st.session_state.lon,
                                st.session_state.time_zone,
                                st.session_state.turbine_model,
                                st.session_state.turbine_type,
                                st.session_state.drivetrain_efficiency
                            )
                            save_resource_data(wind_resource_data, res_name)
                        except Exception as e:
                            st.error(f"Error downloading NASA POWER data: {e}")

            with st.expander(f"📂 Upload CSV for {res_name}", expanded=False):
                st.session_state.res_nominal_capacity[i] = st.number_input(f"Nominal Capacity for {res_name} of the data (W)", value=st.session_state.res_nominal_capacity[i], key=f"nom_capacity_{i}")
                delimiter_options = {
                    "Comma (,)": ",",
                    "Semicolon (;)": ";",
                    "Tab (\\t)": "\t"}
                
                decimal_options = {
                    "Dot (.)": ".",
                    "Comma (,)": ","}
                
                delimiter = st.selectbox("Select delimiter", list(delimiter_options.keys()), key=f"delimiter_wind_{i}")
                decimal = st.selectbox("Select decimal separator", list(decimal_options.keys()), key=f"decimal_wind_{i}")
        
                delimiter_value = delimiter_options[delimiter]
                decimal_value = decimal_options[decimal]

                uploaded_file = st.file_uploader(f"Choose a file for {st.session_state.res_names[i]}", type=["csv"])

                if uploaded_file is not None:
                    wind_resource_data = load_csv_data(uploaded_file, res_name, delimiter_value, decimal_value)
                    if wind_resource_data is not None:
                        st.dataframe(wind_resource_data.head(10))
                        st.write(wind_resource_data.shape)

                if wind_resource_data is not None:
                    if st.button(f"Save Data for {res_name}", key=f"save_wind_csv_{i}"):
                        save_resource_data(wind_resource_data, res_name)

        elif res_type == "📝 Other":
            with st.expander(f"📂 Upload CSV for {res_name}", expanded=False):
                st.session_state.res_nominal_capacity[i] = st.number_input(f"Nominal Capacity for {res_name} of the data (W)", value=st.session_state.res_nominal_capacity[i], key=f"nom_capacity_{i}")
                delimiter_options = {
                    "Comma (,)": ",",
                    "Semicolon (;)": ";",
                    "Tab (\\t)": "\t"}
                
                decimal_options = {
                    "Dot (.)": ".",
                    "Comma (,)": ","}
                
                delimiter = st.selectbox("Select delimiter", list(delimiter_options.keys()), key=f"delimiter_other_{i}")
                decimal = st.selectbox("Select decimal separator", list(decimal_options.keys()), key=f"decimal_other_{i}")
        
                delimiter_value = delimiter_options[delimiter]
                decimal_value = decimal_options[decimal]

                uploaded_file = st.file_uploader(f"Choose a file for {st.session_state.res_names[i]}", type=["csv"])

                if uploaded_file is not None:
                    other_resource_data = load_csv_data(uploaded_file, res_name, delimiter_value, decimal_value)
                    if other_resource_data is not None:
                        st.dataframe(other_resource_data.head(10))
                        st.write(other_resource_data.shape)

                if other_resource_data is not None:
                    if st.button(f"Save Data for {res_name}", key=f"save_other_csv_{i}"):
                        save_resource_data(other_resource_data, res_name)

    # Visualization section at the end
    st.subheader("Visualize Resource Data")
    if st.session_state.resource_data_saved:
        file_path = PathManager.RESOURCE_FILE_PATH
        if os.path.exists(file_path):
            resource_data = pd.read_csv(file_path, index_col='Periods')
            resource_name = st.selectbox("Select Resource to Visualize", resource_data.columns)
            month_names = ['All Year'] + ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            selected_month = st.selectbox("Select Month to Visualize", month_names)
            plot_resource_data(resource_data, resource_name, selected_month)
        else:
            st.warning("No resource data file found. Please upload or download resource data first.")
    else:
        st.warning("No resource data saved. Please upload or download resource data first.")

    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Project Settings"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Demand Assessment"
            st.rerun()
