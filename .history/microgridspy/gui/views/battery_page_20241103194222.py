"""
This module provides the battery technology configuration page for the MicroGridsPy Streamlit application.
It allows users to define the parameters for the battery storage system.
Users can input specific parameters for the battery, ensuring the configuration aligns with project settings.
"""

import streamlit as st
from config.path_manager import PathManager
from microgridspy.gui.utils import initialize_session_state


def battery_technology() -> None:
    """Streamlit page for configuring battery technology parameters."""
    st.title("Battery Parameters")
    st.subheader("Define the parameters for the battery storage system")
    image_path = PathManager.IMAGES_PATH / "technology_characterization.png"
    st.image(str(image_path), use_column_width=True, caption="Overview of the technology characterization parameters")

    has_battery = st.session_state.get('system_configuration', 0) in [0, 1]

    if has_battery:
        # Initialize session state variables
        initialize_session_state(st.session_state.default_values, 'battery_params')
        currency = st.session_state.get('currency', 'USD')
        unit_committment = st.session_state.get('unit_commitment', False)
        time_horizon = st.session_state.get('time_horizon', 0)
        brownfield = st.session_state.get('brownfield')
    
        st.session_state.battery_chemistry = st.text_input("Battery Chemistry", value=st.session_state.battery_chemistry)
        if unit_committment:
            st.session_state.battery_nominal_capacity = st.number_input("Nominal Capacity [Wh]", min_value=0.0, value=st.session_state.battery_nominal_capacity)
        st.session_state.battery_specific_investment_cost = st.number_input(f"Specific Investment Cost [{currency}/Wh]", min_value=0.0, value=st.session_state.battery_specific_investment_cost,)
        st.session_state.battery_specific_electronic_investment_cost = st.number_input(f"Specific Electronic Investment Cost [{currency}/Wh]", min_value=0.0, value=st.session_state.battery_specific_electronic_investment_cost)
        st.session_state.battery_specific_om_cost = st.number_input(f"Specific O&M Cost as % of investment cost [%]", min_value=0.0, value=st.session_state.battery_specific_om_cost * 100) / 100
        st.session_state.battery_discharge_battery_efficiency = st.number_input("Discharge Efficiency [%]", min_value=0.0, max_value=100.0, value=st.session_state.battery_discharge_battery_efficiency * 100) / 100
        st.session_state.battery_charge_battery_efficiency = st.number_input("Charge Efficiency [%]", min_value=0.0, max_value=100.0, value=st.session_state.battery_charge_battery_efficiency * 100) / 100
        st.session_state.battery_initial_soc = st.number_input("Initial State of Charge [%]", min_value=0.0, max_value=100.0, value=st.session_state.battery_initial_soc * 100) / 100
        st.session_state.battery_depth_of_discharge = st.number_input("Depth of Discharge [%]", min_value=0.0, max_value=100.0, value=st.session_state.battery_depth_of_discharge * 100) / 100
        st.session_state.maximum_battery_discharge_time = st.number_input("Maximum Discharge Time [hours]", value=st.session_state.maximum_battery_discharge_time)
        st.session_state.maximum_battery_charge_time = st.number_input("Maximum Charge Time [hours]", value=st.session_state.maximum_battery_charge_time)
        st.session_state.battery_cycles = st.number_input("Battery Cycles [cycles]", value=st.session_state.battery_cycles)
        if brownfield: 
            st.session_state.battery_expected_lifetime = st.number_input("Expected Lifetime [years]", value=st.session_state.battery_expected_lifetime)
        else: 
            st.session_state.battery_expected_lifetime = st.number_input("Expected Lifetime [years]", min_value=time_horizon, value=st.session_state.battery_expected_lifetime)
        st.session_state.bess_unit_co2_emission = st.number_input("Unit CO2 Emission [kgCO2/kWh]", value=st.session_state.bess_unit_co2_emission)
    
        if brownfield:
            st.write(f"### Brownfield project:")
    
            # Get user input in kW, but the stored value should be in W
            battery_capacity = st.number_input(
                "Existing Capacity [Wh]", 
                min_value=0.0, 
                value=st.session_state.battery_existing_capacity)

            # Store the value in W in the session_state
            st.session_state.battery_existing_capacity = battery_capacity
            if battery_capacity > 0:
                st.session_state.battery_existing_years = st.number_input("Existing Years [years]", min_value=0, max_value=(st.session_state.battery_expected_lifetime - 1), value=st.session_state.battery_existing_years)
    else:
        st.warning("Battery technology is not included in the system configuration. If you want to include a battery, please edit the project settings page.")

    st.markdown("---")
    
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Renewables Characterization"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Generator Characterization"
            st.rerun()
