"""
This module provides the renewables technology configuration page for the MicroGridsPy Streamlit application.
It allows users to define the number and type of renewable sources to be considered in their project.
Users can input specific parameters for each renewable source, ensuring the configuration aligns with project settings.
"""

import streamlit as st
from microgridspy.model.parameters import ProjectParameters
from config.path_manager import PathManager

def initialize_session_state(default_values: ProjectParameters) -> None:
    """Initialize session state variables for renewables parameters."""
    renewables_params = default_values.renewables_params
    session_state_defaults = {
        'res_inverter_efficiency': renewables_params.res_inverter_efficiency,
        'res_specific_area': renewables_params.res_specific_area,
        'res_specific_investment_cost': renewables_params.res_specific_investment_cost,
        'res_specific_om_cost': renewables_params.res_specific_om_cost,
        'res_lifetime': renewables_params.res_lifetime,
        'res_unit_co2_emission': renewables_params.res_unit_co2_emission,
        'res_existing_capacity': renewables_params.res_existing_capacity,
        'res_existing_area': renewables_params.res_existing_area,
        'res_existing_years': renewables_params.res_existing_years,
    }
    for key, value in session_state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def ensure_list_length(key: str, length: int) -> None:
    """Ensure the list in session state has the required length."""
    if key not in st.session_state:
        st.session_state[key] = [0] * length
    else:
        st.session_state[key].extend([0] * (length - len(st.session_state[key])))

def update_parameters(i: int, res_name: str, time_horizon: int, brownfield: bool, land_availability: float, currency: str) -> None:
    """Update renewable parameters for the given index."""
    st.session_state.res_inverter_efficiency[i] = st.number_input(f"Inverter Efficiency of {res_name} [-]", min_value=0.0, max_value=1.0, value=st.session_state.res_inverter_efficiency[i])
    if land_availability > 0: st.session_state.res_specific_area[i] = st.number_input(f"Specific Area of {res_name} [m2/W]", value=st.session_state.res_specific_area[i])
    st.session_state.res_specific_investment_cost[i] = st.number_input(f"Specific Investment Cost of {res_name} [{currency}/W]", value=st.session_state.res_specific_investment_cost[i])
    st.session_state.res_specific_om_cost[i] = st.number_input(f"Specific O&M Cost of {res_name} as % of investment cost [-]", value=st.session_state.res_specific_om_cost[i])
    if brownfield: st.session_state.res_lifetime[i] = st.number_input(f"Lifetime of {res_name} [years]", value=st.session_state.res_lifetime[i])
    else: st.session_state.res_lifetime[i] = st.number_input(f"Lifetime of {res_name} [years]", min_value=time_horizon, value=st.session_state.res_lifetime[i])
    st.session_state.res_unit_co2_emission[i] = st.number_input(f"Unit CO2 Emission of {res_name} [kgCO2/W]", value=st.session_state.res_unit_co2_emission[i])

    if brownfield:
        st.write(f"### Brownfield project:")
        st.session_state.res_existing_capacity[i] = st.number_input(
            f"Existing Capacity of {res_name} [W]", value=st.session_state.res_existing_capacity[i])
        if land_availability > 0:
            st.session_state.res_existing_area[i] = st.number_input(
                f"Existing Area of {res_name} [m2]", value=st.session_state.res_existing_area[i])
        st.session_state.res_existing_years[i] = st.number_input(
            f"Existing Years of {res_name} [years]", value=st.session_state.res_existing_years[i])

def renewables_technology() -> None:
    """Streamlit page for configuring renewable energy technology parameters."""
    st.title("Renewables Parameters")
    st.subheader("Define the number and type of renewable sources to be considered")
    image_path = PathManager.IMAGES_PATH / "technology_characterization.png"
    st.image(str(image_path), use_column_width=True, caption="Overview of the technology characterization parameters")

    # Initialize session state variables
    initialize_session_state(st.session_state.default_values)
    currency = st.session_state.get('currency', 'USD')
    res_sources = st.session_state.get('res_sources', 0)
    if res_sources == 0:
        st.warning("Renewables sources not initialized yet. Please define the number of renewable sources in the Resource Assessment page.")
    res_names = st.session_state.get('res_names', [])
    time_horizon = st.session_state.get('time_horizon', 0)
    brownfield = st.session_state.get('brownfield')
    land_availability = st.session_state.get('land_availability')

    # Ensure session state lists have the correct length
    keys = [
        'res_inverter_efficiency', 'res_specific_investment_cost',
        'res_specific_om_cost', 'res_lifetime', 'res_unit_co2_emission'
    ]
    if land_availability:
        keys += ['res_specific_area']
    if brownfield:
        keys += ['res_existing_capacity', 'res_existing_area', 'res_existing_years']

    for key in keys:
        ensure_list_length(key, res_sources)

    # Input fields for each RES parameter
    for i in range(res_sources):
        st.write(f"### {res_names[i]}")
        update_parameters(i, res_names[i], time_horizon, brownfield, land_availability, currency)

    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Demand Assessment"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "TODO: Add next page"
            st.rerun()
