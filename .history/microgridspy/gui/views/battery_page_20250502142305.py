"""
This module provides the battery technology configuration page for the MicroGridsPy Streamlit application.
It allows users to define the parameters for the battery storage system.
Users can input specific parameters for the battery, ensuring the configuration aligns with project settings.
"""

import streamlit as st
from config.path_manager import PathManager
import pandas as pd
import os
import matplotlib.pyplot as plt
from microgridspy.gui.utils import initialize_session_state

def load_cost_df(currency) -> pd.DataFrame:
    """
    Load or create a DataFrame for renewable energy costs with specified columns,
    ensuring the columns are in the same order as in res_names.
    """
    battery_cost_file_path = PathManager.BATTERY_COST_FILE_PATH
    num_steps = st.session_state.num_steps
    
    # Define the correct index for num_steps
    correct_index = [f"Investment Step {i}" for i in range(1, num_steps + 1)]
    relevant_columns = [f"Battery Investment Cost [{currency}/W]"]

    if os.path.exists(battery_cost_file_path):
        # Load the CSV file
        battery_cost_df = pd.read_csv(battery_cost_file_path, index_col=0)

        # Ensure the index is consistent
        battery_cost_df.index = battery_cost_df.index.astype(str)

        # Identify rows that are missing and create them with zeros
        missing_index = [i for i in correct_index if i not in battery_cost_df.index]
        if missing_index:
            missing_rows = pd.DataFrame({col: 0.0 for col in battery_cost_df.columns}, index=missing_index)
            battery_cost_df = pd.concat([battery_cost_df, missing_rows])

        # Reindex to match the correct order and preserve existing data
        battery_cost_df = battery_cost_df.reindex(correct_index)

        # Ensure all relevant columns exist
        for col in relevant_columns:
            if col not in battery_cost_df.columns:
                battery_cost_df[col] = 0.0

        # Reorder columns to match relevant_columns order
        battery_cost_df = battery_cost_df.loc[correct_index, relevant_columns]

        return battery_cost_df

    else:
        # Create a new DataFrame with zeros if the file doesn't exist
        data = {col: [0.0] * num_steps for col in relevant_columns}
        return pd.DataFrame(data, index=correct_index)

def upload_cost_data(cost_df, currency) -> None:
    # Create dataframe that can be adjusted by the user
    st.markdown(f"Investment Cost [{currency}/Wh]")
    edited_df = st.data_editor(
        cost_df[[f'Battery Investment Cost [{currency}/Wh]']],
        hide_index=False
    )

    return edited_df

def battery_technology() -> None:
    """Streamlit page for configuring battery technology parameters."""
    st.title("Battery Parameters")
    st.subheader("Define the parameters for the battery storage system")
    st.write("""
    This page is dedicated to initializing parameters for the battery storage system within the project. 
    Here, you can configure the relevant settings and values associated with the battery type used in the model.
    Below is a brief overview of the mathematical formulation of backup system within MicroGridsPy:
    """)
    image_path = PathManager.IMAGES_PATH / "battery_math_formulation.PNG"
    st.image(str(image_path), use_column_width=True, caption="Overview of the main equations for battery")

    has_battery = st.session_state.get('system_configuration', 0) in [0, 1]
    res_names = st.session_state.get('res_names', [])

    if has_battery:
        # Initialize session state variables
        initialize_session_state(st.session_state.default_values, 'battery_params')
        currency = st.session_state.get('currency', 'USD')
        unit_committment = st.session_state.get('unit_commitment', False)
        brownfield = st.session_state.get('brownfield')

        if unit_committment:
            st.session_state.battery_nominal_capacity = st.number_input("Nominal Capacity [Wh]", min_value=0.0, value=st.session_state.battery_nominal_capacity)
        cost_df = load_cost_df(currency)
        print(cost_df.columns)
        edited_df = upload_cost_data(cost_df, currency)
        if st.button(f"Save investment cost data for Battery"):
            battery_cost_file_path = PathManager.BATTERY_COST_FILE_PATH
            cost_df[f'Battery Investment Cost [{currency}/Wh]'] = edited_df[f'Battery Investment Cost [{currency}/Wh]']
            cost_df.to_csv(battery_cost_file_path, index=True)
            st.success(f"Data saved to {battery_cost_file_path}")

        st.session_state.battery_specific_electronic_investment_cost = st.number_input(f"Specific Electronic Investment Cost as % of investment cost [%]", min_value=0.0, max_value=100.0, value=st.session_state.battery_specific_electronic_investment_cost * 100) / 100
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
            st.session_state.battery_expected_lifetime = st.number_input("Expected Lifetime [years]", min_value=1, value=st.session_state.battery_expected_lifetime)
        st.session_state.bess_unit_co2_emission = st.number_input("Unit CO2 Emission [kgCO2/kWh]", value=st.session_state.bess_unit_co2_emission)

        if st.session_state.distribution_type == "Alternating Current":
            st.write("##### Inverter parameters:")    
            st.session_state.battery_inverter_efficiency_dc_ac = st.number_input("Inverter Efficiency from DC to AC [%]", min_value=0.0, max_value=100.0, value=st.session_state.battery_inverter_efficiency_dc_ac * 100) / 100
            st.session_state.battery_inverter_efficiency_ac_dc = st.number_input("Inverter Efficiency from AC to DC [%]", min_value=0.0, max_value=100.0, value=st.session_state.battery_inverter_efficiency_ac_dc * 100) / 100
            st.session_state.battery_inverter_nominal_capacity = st.number_input("Inverter Nominal Capacity [W]", min_value=0.0, value=st.session_state.battery_inverter_nominal_capacity)
            st.session_state.battery_inverter_lifetime = st.number_input("Inverter Lifetime [years]", min_value=1, value=st.session_state.battery_inverter_lifetime)
            st.session_state.battery_inverter_cost = st.number_input(f"Inverter Cost [{currency}/W]", min_value=0.0, value=st.session_state.battery_inverter_cost)
        else:
            # Set default values for DC distribution
            st.session_state.battery_inverter_efficiency_dc_ac = 1.0
            st.session_state.battery_inverter_efficiency_ac_dc = 1.0
            st.session_state.battery_inverter_cost = 0.0

        if brownfield:
            st.write(f"### Brownfield project parameters:")
    
            # Get user input in kW, but the stored value should be in W
            battery_capacity = st.number_input(
                "Existing Capacity [Wh]", 
                min_value=0.0, 
                value=st.session_state.battery_existing_capacity)

            # Store the value in W in the session_state
            st.session_state.battery_existing_capacity = battery_capacity
            if battery_capacity > 0:
                st.session_state.battery_existing_years = st.number_input("Existing Years [years]", min_value=0, max_value=(st.session_state.battery_expected_lifetime - 1), value=st.session_state.battery_existing_years)
            if st.session_state.distribution_type == "Alternating Current":
                st.session_state.battery_existing_inverter_capacity = st.number_input("Existing Inverter Capacity [W]", 
                                                                                      min_value=0.0, 
                                                                                      value=st.session_state.battery_existing_inverter_capacity)
                if st.session_state.battery_existing_inverter_capacity > 0:
                    st.session_state.battery_inverter_existing_years = st.number_input(f"Existing Inverter Cost [{currency}/W]", 
                                                                                    min_value=0, 
                                                                                    max_value=(st.session_state.battery_inverter_lifetime - 1),
                                                                                    value=st.session_state.battery_inverter_existing_years)

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
