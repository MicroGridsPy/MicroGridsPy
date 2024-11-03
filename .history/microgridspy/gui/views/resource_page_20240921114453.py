"""
This module provides the resource assessment page for the MicroGridsPy Streamlit application. 
It allows users to download or upload resource availability data for their project. 
Users can configure specific resource parameters for solar and wind energy, visualize the data, 
and save the updated configuration to a CSV file.
"""
import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import folium
import openpyxl

from streamlit_folium import st_folium
from geopy.exc import GeopyError
from geopy.geocoders import Nominatim
from pathlib import Path
from typing import Tuple, Optional

from config.path_manager import PathManager
from microgridspy.utils.nasa_power import download_nasa_pv_data, download_nasa_wind_data
from microgridspy.gui.utils import csv_upload_interface, initialize_session_state

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
        
        if len(data.columns) > 1:
            selected_column = st.selectbox("Select the column representing data", data.columns)
            data = data[[selected_column]]
        
        if resource_name:
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

def delete_resource_file(file_path: Path) -> None:
    """Delete the resource file at the given path."""
    if file_path.exists():
        file_path.unlink()
        st.success(f"{file_path} deleted successfully.")
    else:
        st.info(f"{file_path} does not exist.")

def get_turbine_models():
    excel_path = PathManager.POWER_CURVE_FILE_PATH
    wb = openpyxl.load_workbook(excel_path)
    
    horizontal_models = []
    vertical_models = []
    
    for sheet_name in wb.sheetnames:
        parts = sheet_name.split(' - ')
        if len(parts) == 2:
            model, model_type = parts
            if model_type == "Horizontal Axis":
                horizontal_models.append(model)
            elif model_type == "Vertical Axis":
                vertical_models.append(model)
    
    return horizontal_models, vertical_models

def save_custom_turbine_model(custom_model_name, turbine_type, rated_power, rotor_diameter, hub_height, power_curve_data):
    excel_path = PathManager.POWER_CURVE_FILE_PATH
    sheet_name = f"{custom_model_name} - {turbine_type}"
    
    turbine_specs = [
        ["Rated Power [kW]", rated_power],
        ["Rotor Diameter [m]", rotor_diameter],
        ["Hub Height [m]", hub_height],
        ["Wind Speed [m/s]", "Power [kW]"]]
    
    custom_data = turbine_specs + power_curve_data.values.tolist()

    with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a' if excel_path.exists() else 'w') as writer:
        pd.DataFrame(custom_data).to_excel(writer, sheet_name=sheet_name, index=False, header=False)

    return sheet_name

def get_coordinates(address: str) -> Tuple[float, float]:
    """Get the latitude and longitude coordinates for the given address."""
    geolocator = Nominatim(user_agent="myGeocoder")
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
        raise ValueError(f"No location found for the given address: {address}")
    except GeopyError as e:
        raise ValueError(f"Geocoding error: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {e}")

def handle_location_input(address: str) -> None:
    """Handle the input address to get the coordinates and update the session state."""
    try:
        lat, lon = get_coordinates(address)
        st.session_state.lat = lat
        st.session_state.lon = lon
        st.session_state.location = f"{lat}, {lon}"
        st.success("Location found!")
    except ValueError as e:
        st.error(f"Could not find location: {e}")

def save_resource_data(resource_data: pd.DataFrame, resource_name: str, project_name: str) -> None:
    """Save the resource data to a CSV file."""
    # Save the resource data to a CSV file into the Inputs folder
    inputs_folder_path = PathManager.RESOURCE_FILE_PATH

    if not inputs_folder_path.exists():
        resource_data.columns = [resource_name]
        resource_data.to_csv(inputs_folder_path, index=True)
    else:
        existing_data = pd.read_csv(inputs_folder_path, index_col='Periods')
        existing_data[resource_name] = resource_data[resource_name]
        existing_data.to_csv(inputs_folder_path, index=True)
    

    # Save the resource data to a CSV file into the related project folder
    project_folder_path = PathManager.PROJECTS_FOLDER_PATH / str(project_name) / "resource" / 'Resources Availability.csv'

    if not project_folder_path.exists():
        resource_data.columns = [resource_name]
        resource_data.to_csv(project_folder_path, index=True)
    else:
        existing_data = pd.read_csv(project_folder_path, index_col='Periods')
        existing_data[resource_name] = resource_data[resource_name]
        existing_data.to_csv(project_folder_path, index=True)

    st.success(f"Resource data saved successfully for {resource_name} at {inputs_folder_path} for current use as well as at {project_folder_path} for future use.")

def plot_resource_data(resource_data: pd.DataFrame, resource_name: str, selected_month: str) -> None:
    """Plot the resource data for the selected resource and month."""
    resource_data['Hour'] = resource_data.index % 24
    resource_data['Month'] = ((resource_data.index - 1) // 24) % 12 + 1
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

def resource_assessment():
    """Streamlit page for resource assessment."""
    st.title("Resource Assessment")
    st.subheader("Download or upload resource availability data for your project.")

    initialize_session_state(st.session_state.default_values, 'resource_assessment')
    initialize_session_state(st.session_state.default_values, 'nasa_power_params')
    nasa_power_params = st.session_state.default_values.nasa_power_params
    project_name = st.session_state.get("project_name")

    # Location selection
    st.subheader("Select Project Location")
    address = st.text_input("Enter location address:", 
                            help="Input a specific address or location name to set project coordinates.")
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

    # Resource data section
    st.subheader("Renewables Time Series Data")
    if st.button("Clear Resource Availability File", type="primary",
                 help="Delete the existing resource data file. Use this to start fresh with new resource data."):
        delete_resource_file(PathManager.RESOURCE_FILE_PATH)
        project_folder_path = PathManager.PROJECTS_FOLDER_PATH / str(project_name) / "resource" / 'Resources Availability.csv'
        delete_resource_file(project_folder_path)
 

    # Initialize or update session state variables
    if 'res_sources' not in st.session_state:
        st.session_state.res_sources = 1
    if 'res_names' not in st.session_state:
        st.session_state.res_names = []
    if 'res_types' not in st.session_state:
        st.session_state.res_types = []
    if 'res_nominal_capacity' not in st.session_state:
        st.session_state.res_nominal_capacity = []

    # Number of renewable sources
    st.session_state.res_sources = st.number_input(
        "Number of Renewable Technologies", 
        min_value=1, 
        value=st.session_state.res_sources,
        help="Specify the number of different renewable energy sources in your project. Each source will be configured separately.")

    # Ensure lists have correct length
    while len(st.session_state.res_names) < st.session_state.res_sources:
        st.session_state.res_names.append(f"Renewable Source {len(st.session_state.res_names) + 1}")
    while len(st.session_state.res_types) < st.session_state.res_sources:
        st.session_state.res_types.append("☀️ Solar Energy")
    while len(st.session_state.res_nominal_capacity) < st.session_state.res_sources:
        st.session_state.res_nominal_capacity.append(0)

    # Truncate lists if necessary
    st.session_state.res_names = st.session_state.res_names[:st.session_state.res_sources]
    st.session_state.res_types = st.session_state.res_types[:st.session_state.res_sources]
    st.session_state.res_nominal_capacity = st.session_state.res_nominal_capacity[:st.session_state.res_sources]

    # Input for resource names and types
    for i in range(st.session_state.res_sources):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.res_names[i] = st.text_input(
                f"Name for Renewable Technology {i+1}", 
                value=st.session_state.res_names[i], 
                key=f"res_name_{i}",
                help="Provide a descriptive name for this renewable energy source.")
        with col2:
            st.session_state.res_types[i] = st.selectbox(
                f"Type of Renewable Resource {i+1}", 
                ["☀️ Solar Energy", "🌀 Wind Energy", "📝 Other"], 
                index=["☀️ Solar Energy", "🌀 Wind Energy", "📝 Other"].index(st.session_state.res_types[i]),
                key=f"res_type_{i}",
                help="Select the type of renewable energy source. This determines the configuration options and data processing.")

    # Configuration sections for each resource
    for i in range(st.session_state.res_sources):
        res_name = st.session_state.res_names[i]
        res_type = st.session_state.res_types[i]
        st.write(f"### {res_name} Electricity Production")

        if res_type == "☀️ Solar Energy":
            with st.expander("⬇️ Download Solar Resource Availability from NASA POWER", expanded=False):
                st.image(str(PathManager.IMAGES_PATH / "nasa_power.png"), use_column_width=True)
                st.session_state.res_nominal_capacity[i] = st.number_input(
                    f"Nominal Power for {res_name} [W]:", 
                    value=st.session_state.res_nominal_capacity[i], 
                    key=f"nom_power_{i}",
                    help="Enter the nominal power capacity of the solar installation in Watts.")
                
                solar_params = {
                    'tilt': {
                        'name': "Panel Tilt Angle",
                        'description': "The angle between the solar panel surface and the horizontal plane, in degrees. Optimal tilt is typically close to the latitude of the location. Range: 0° (horizontal) to 90° (vertical). Example: 30° for mid-latitudes."},
                    'azim': {
                        'name': "Panel Azimuth Angle",
                        'description': "The compass direction that the solar panels face, in degrees. 0° is North, 90° is East, 180° is South, 270° is West. For maximum annual energy in the Northern Hemisphere, panels typically face South (180°). Adjust based on local conditions and time-of-day demand."},
                    'ro_ground': {
                        'name': "Ground Reflectance (Albedo)",
                        'description': "The fraction of solar radiation reflected by the ground surface. Affects the amount of indirect light reaching the panels. Typical values: 0.1 (dark surfaces) to 0.4 (light surfaces). Examples: Grass ≈ 0.25, Concrete ≈ 0.30, Fresh snow ≈ 0.80."},
                    'k_T': {
                        'name': "Temperature Coefficient of Power",
                        'description': "The rate at which panel efficiency decreases as temperature increases, expressed as a percentage per degree Celsius. Typical values range from -0.2% to -0.5% per °C, with -0.4% per °C being common. A lower absolute value indicates better high-temperature performance."},
                    'NMOT': {
                        'name': "Nominal Module Operating Temperature",
                        'description': "The expected temperature of the solar panel under specific test conditions, in degrees Celsius. This value is used to estimate real-world performance. Typical range: 40°C to 50°C. Lower NMOT generally indicates better performance in hot conditions."},
                    'T_NMOT': {
                        'name': "Ambient Temperature at NMOT",
                        'description': "The ambient air temperature at which the Nominal Module Operating Temperature (NMOT) is defined, usually 20°C (68°F). This is part of the standard test conditions for determining NMOT."},
                    'G_NMOT': {
                        'name': "Solar Irradiance at NMOT",
                        'description': "The solar irradiance level at which the Nominal Module Operating Temperature (NMOT) is defined, usually 800 W/m². This represents typical sunny conditions and is part of the standard test conditions for determining NMOT."}
                }

                for param, info in solar_params.items():
                    setattr(st.session_state, param, st.number_input(
                    f"{info['name']} for {res_name}:", 
                    value=getattr(st.session_state, param), 
                    key=f"{param}_{i}",
                    help=info['description']))

                if st.button(f"Download Solar Data for {res_name}", key=f"download_solar_{i}"):
                    with st.spinner('Downloading and processing data from NASA POWER...'):
                        try:
                            solar_resource_data = download_nasa_pv_data(
                                res_name=res_name, 
                                base_URL=nasa_power_params.base_url,
                                loc_id=nasa_power_params.loc_id,
                                parameters_1=nasa_power_params.parameters_1,
                                parameters_2=nasa_power_params.parameters_2,
                                parameters_3=nasa_power_params.parameters_3,
                                date_start=nasa_power_params.date_start,
                                date_end=nasa_power_params.date_end,
                                community=nasa_power_params.community,
                                temp_res_1=nasa_power_params.temp_res_1,
                                temp_res_2=nasa_power_params.temp_res_2,
                                output_format=nasa_power_params.output_format,
                                lat=st.session_state.lat, 
                                lon=st.session_state.lon, 
                                time_zone=st.session_state.time_zone,
                                nom_power=st.session_state.res_nominal_capacity[i],
                                tilt=st.session_state.tilt, 
                                azimuth=st.session_state.azim, 
                                ro_ground=st.session_state.ro_ground,
                                k_T=st.session_state.k_T, 
                                NMOT=st.session_state.NMOT, 
                                T_NMOT=st.session_state.T_NMOT, 
                                G_NMOT=st.session_state.G_NMOT)
                            
                            save_resource_data(solar_resource_data, res_name, project_name)
                        except Exception as e:
                            st.error(f"Error downloading NASA POWER data: {e}")

            with st.expander(f"📂 Upload CSV for {res_name}", expanded=False):
                st.session_state.res_nominal_capacity[i] = st.number_input(
                    f"Nominal Capacity for {res_name} of the data (W)", 
                    value=st.session_state.res_nominal_capacity[i], 
                    key=f"nom_capacity_{i}",
                    help="Enter the nominal capacity of the solar installation represented in the uploaded data.")
                uploaded_file, delimiter, decimal = csv_upload_interface(f"solar_{i}")
                if uploaded_file:
                    solar_resource_data = load_csv_data(uploaded_file, delimiter, decimal, res_name)
                    if solar_resource_data is not None:
                        st.dataframe(solar_resource_data.head(10))
                        st.write(solar_resource_data.shape)
                        if st.button(f"Save Data for {res_name}", key=f"save_solar_csv_{i}"):
                            save_resource_data(solar_resource_data, res_name, project_name)

        elif res_type == "🌀 Wind Energy":
            with st.expander("⬇️ Download Wind Resource Availability from NASA POWER", expanded=False):
                st.image(str(PathManager.IMAGES_PATH / "nasa_power.png"), use_column_width=True)
        
                horizontal_models, vertical_models = get_turbine_models()
                custom_option = "Add custom wind turbine model"
        
                st.session_state.turbine_type = st.selectbox(
                    f"Turbine Type for {res_name}:", 
                    options=["Horizontal Axis", "Vertical Axis"], 
                    index=["Horizontal Axis", "Vertical Axis"].index(st.session_state.turbine_type), 
                    key=f"turbine_type_{i}",
                    help="Select the type of wind turbine. This affects the available turbine models and power characteristics.")
        
                models = horizontal_models if st.session_state.turbine_type == "Horizontal Axis" else vertical_models
                models.append(custom_option)
                st.session_state.turbine_model = st.selectbox(
                    f"Turbine Model for {res_name}:", 
                    options=models, 
                    index=models.index(st.session_state.turbine_model) if st.session_state.turbine_model in models else 0, 
                    key=f"turbine_model_{i}",
                    help="Choose a specific turbine model. This determines the power curve and other characteristics used in energy calculations.")
        
                if st.session_state.turbine_model == custom_option:
                    st.write("### Custom Wind Turbine Model")
                    custom_model_name = st.text_input("Model Name", key=f"custom_model_name_{i}")
                    rated_power = st.number_input("Rated Power [kW]", min_value=0.0, value=100.0, key=f"rated_power_{i}")
                    rotor_diameter = st.number_input("Rotor Diameter [m]", min_value=0.0, value=21.0, key=f"rotor_diameter_{i}")
                    hub_height = st.number_input("Hub Height [m]", min_value=0.0, value=37.0, key=f"hub_height_{i}")
    
                    wind_speeds = list(range(31))
                    power_curve_data = pd.DataFrame({"Wind Speed [m/s]": wind_speeds, "Power [kW]": [0.0] * 30})
                    edited_power_curve = st.data_editor(power_curve_data, num_rows="fixed", key=f"power_curve_{i}")
    
                    if st.button("Save Custom Turbine Model", key=f"save_custom_turbine_{i}"):
                        try:
                            new_sheet_name = save_custom_turbine_model(
                                custom_model_name, 
                                st.session_state.turbine_type, 
                                rated_power, 
                                rotor_diameter, 
                                hub_height, 
                                edited_power_curve)
                            st.success(f"Custom turbine model '{new_sheet_name}' saved successfully!")
                    
                            # Update the turbine models list and select the new model
                            if st.session_state.turbine_type == "Horizontal Axis":
                                horizontal_models.append(custom_model_name)
                            else:
                                vertical_models.append(custom_model_name)
                            st.session_state.turbine_model = custom_model_name
                        except Exception as e:
                            st.error(f"Error saving custom turbine model: {e}")
    
                    st.session_state.res_nominal_capacity[i] = rated_power * 1000  # Convert kW to W
                else:
                    # Read the nominal power from the Excel file for the selected model
                    excel_path = PathManager.POWER_CURVE_FILE_PATH
                    sheet_name = f"{st.session_state.turbine_model} - {st.session_state.turbine_type}"
                    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
                    rated_power = df.iloc[0, 1]  # Assuming rated power is always in cell B1
                    st.session_state.res_nominal_capacity[i] = rated_power * 1000  # Convert kW to W
        
                st.session_state.drivetrain_efficiency = st.number_input(
                    f"Drivetrain Efficiency for {res_name}:", 
                    min_value=0.0, 
                    max_value=1.0, 
                    value=st.session_state.drivetrain_efficiency, 
                    key=f"drivetrain_efficiency_{i}",
                    help="Enter the efficiency of the turbine's drivetrain (typically between 0.85 and 0.95).")
        
                if st.button(f"Download Wind Data for {res_name}", key=f"download_wind_{i}"):
                    with st.spinner('Downloading and processing data from NASA POWER...'):
                        try:
                            wind_resource_data = download_nasa_wind_data(
                                res_name=res_name, 
                                base_URL=nasa_power_params.base_url,
                                loc_id=nasa_power_params.loc_id,
                                parameters_1=nasa_power_params.parameters_1,
                                parameters_2=nasa_power_params.parameters_2,
                                parameters_3=nasa_power_params.parameters_3,
                                date_start=nasa_power_params.date_start,
                                date_end=nasa_power_params.date_end,
                                community=nasa_power_params.community,
                                temp_res_1=nasa_power_params.temp_res_1,
                                temp_res_2=nasa_power_params.temp_res_2,
                                output_format=nasa_power_params.output_format,
                                lat=st.session_state.lat, 
                                lon=st.session_state.lon, 
                                time_zone=st.session_state.time_zone,
                                turbine_model=st.session_state.turbine_model, 
                                turbine_type=st.session_state.turbine_type,
                                drivetrain_efficiency=st.session_state.drivetrain_efficiency)
                            
                            save_resource_data(wind_resource_data, res_name, project_name)
                        except Exception as e:
                            st.error(f"Error downloading NASA POWER data: {e}")

            with st.expander(f"📂 Upload CSV for {res_name}", expanded=False):
                st.session_state.res_nominal_capacity[i] = st.number_input(
                    f"Nominal Capacity for {res_name} of the data (W)", 
                    value=st.session_state.res_nominal_capacity[i], 
                    key=f"nom_capacity_{i}",
                    help=f"Enter the nominal capacity of the wind turbine represented in the uploaded data.")
                uploaded_file, delimiter, decimal = csv_upload_interface(f"wind_{i}")
                if uploaded_file:
                    wind_resource_data = load_csv_data(uploaded_file, delimiter, decimal, res_name)
                    if wind_resource_data is not None:
                        st.dataframe(wind_resource_data.head(10))
                        st.write(wind_resource_data.shape)
                        if st.button(f"Save Data for {res_name}", key=f"save_wind_csv_{i}"):
                            save_resource_data(wind_resource_data, res_name, project_name)

        elif res_type == "📝 Other":
            with st.expander(f"📂 Upload CSV for {res_name}", expanded=False):
                st.session_state.res_nominal_capacity[i] = st.number_input(
                    f"Nominal Capacity for {res_name} of the data (W)", 
                    value=st.session_state.res_nominal_capacity[i], 
                    key=f"nom_capacity_{i}",
                    help=f"Enter the nominal capacity of the {res_name} represented in the uploaded data.")
                uploaded_file, delimiter, decimal = csv_upload_interface(f"other_{i}")
                if uploaded_file:
                    other_resource_data = load_csv_data(uploaded_file, delimiter, decimal, res_name)
                    if other_resource_data is not None:
                        st.dataframe(other_resource_data.head(10))
                        st.write(other_resource_data.shape)
                        if st.button(f"Save Data for {res_name}", key=f"save_other_csv_{i}"):
                            save_resource_data(other_resource_data, res_name, project_name)

    # Visualization section
    st.subheader("Visualize Resource Data")
    file_path = PathManager.RESOURCE_FILE_PATH
    if os.path.exists(file_path):
        resource_data = pd.read_csv(file_path, index_col='Periods')
        resource_name = st.selectbox("Select Resource to Visualize", resource_data.columns)
        month_names = ['All Year'] + ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        selected_month = st.selectbox("Select Month to Visualize", month_names)
        plot_resource_data(resource_data, resource_name, selected_month)
    else:
        st.warning("No resource data file found. Please upload or download resource data first.")

    st.write("---")  # Add a separator

    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Project Settings"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Demand Assessment"
            st.rerun()