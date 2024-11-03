import streamlit as st
from config.path_manager import PathManager
from microgridspy.gui.utils import initialize_session_state

def ensure_list_length(key: str, length: int) -> None:
    """Ensure the list in session state has the required length."""
    if key not in st.session_state:
        st.session_state[key] = [0.0] * length
    else:
        st.session_state[key].extend([0.0] * (length - len(st.session_state[key])))

def update_parameters(i: int, res_name: str, time_horizon: int, brownfield: bool, land_availability: float, currency: str) -> None:
    """Update renewable parameters for the given index."""
    st.subheader(f"{res_name} Parameters")
    
    st.session_state.res_inverter_efficiency[i] = st.number_input(
        f"Inverter Efficiency [%]", 
        min_value=0.0, 
        max_value=100.0, 
        value=float(st.session_state.res_inverter_efficiency[i] * 100), 
        key=f"inv_eff_{i}") / 100
    
    if land_availability > 0:
        st.session_state.res_specific_area[i] = st.number_input(
            f"Specific Area [m2/kW]",
            min_value=0.0, 
            value=float(st.session_state.res_specific_area[i]), 
            key=f"spec_area_{i}")
    
    st.session_state.res_specific_investment_cost[i] = st.number_input(
        f"Specific Investment Cost [{currency}/W]", 
        min_value=0.0,
        value=float(st.session_state.res_specific_investment_cost[i]), 
        key=f"inv_cost_{i}")
    
    st.session_state.res_specific_om_cost[i] = st.number_input(
        f"Specific O&M Cost as % of investment cost [%]", 
        min_value=0.0, 
        max_value=100.0,
        value=float(st.session_state.res_specific_om_cost[i] * 100), 
        key=f"om_cost_{i}") / 100
    
    if brownfield:
        st.session_state.res_lifetime[i] = st.number_input(
            f"Lifetime [years]", 
            value=float(st.session_state.res_lifetime[i]), 
            key=f"lifetime_{i}")
    else:
        st.session_state.res_lifetime[i] = st.number_input(
            f"Lifetime [years]", 
            min_value=float(time_horizon), 
            value=max(float(time_horizon), float(st.session_state.res_lifetime[i])), 
            key=f"lifetime_{i}")
    
    st.session_state.res_unit_co2_emission[i] = st.number_input(
        f"Unit CO2 Emission [kgCO2/W]", 
        value=float(st.session_state.res_unit_co2_emission[i]), 
        key=f"co2_{i}")

    if brownfield:
        st.write("##### Brownfield project parameters:")
    
        # Get user input in kW, but store the value in W
        res_capacity = st.number_input(
            f"Existing Capacity [W]", 
            min_value=0.0,
            value=float(st.session_state.res_existing_capacity[i]),
            key=f"exist_cap_{i}")

        # Store the value in W in session_state
        st.session_state.res_existing_capacity[i] = res_capacity
        if res_capacity > 0:
            st.session_state.res_existing_years[i] = st.number_input(
                f"Existing Years [years]", 
                min_value=0.0,
                max_value=float(st.session_state.res_lifetime[i] - 1),
                value=float(st.session_state.res_existing_years[i]), 
                key=f"exist_years_{i}")

def renewables_technology() -> None:
    """Streamlit page for configuring renewable energy technology parameters."""
    st.title("Renewables Parameters")
    st.subheader("Define the parameters for each renewable source")
    image_path = PathManager.IMAGES_PATH / "technology_characterization.png"
    st.image(str(image_path), use_column_width=True, caption="Overview of the technology characterization parameters")

    # Initialize session state variables
    initialize_session_state(st.session_state.default_values, 'renewables_params')
    currency = st.session_state.get('currency', 'USD')
    res_sources = st.session_state.get('res_sources', 0)
    if res_sources == 0:
        st.warning("Renewables sources not initialized yet. Please define the number of renewable sources in the Resource Assessment page.")
        return
    res_names = st.session_state.get('res_names', [])
    time_horizon = st.session_state.get('time_horizon', 0)
    brownfield = st.session_state.get('brownfield', False)
    land_availability = st.session_state.get('land_availability', 0.0)

    # Ensure session state lists have the correct length
    keys = ['res_inverter_efficiency', 'res_specific_investment_cost','res_specific_om_cost', 'res_lifetime', 'res_unit_co2_emission']
    if land_availability > 0:
        keys.append('res_specific_area')
    if brownfield:
        keys.extend(['res_existing_capacity', 'res_existing_area', 'res_existing_years'])

    for key in keys:
        ensure_list_length(key, res_sources)

    # Display parameters for each renewable source
    for i in range(res_sources):
        update_parameters(i, res_names[i], time_horizon, brownfield, land_availability, currency)
        st.markdown("---")  # Add a separator between renewable sources

    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Demand Assessment"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Battery Characterization"
            st.rerun()