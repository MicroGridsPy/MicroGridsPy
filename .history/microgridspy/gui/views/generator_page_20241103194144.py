"""
This module provides the generator technology configuration page for the MicroGridsPy Streamlit application.
It allows users to define the parameters for different types of generators in their project.
Users can input specific parameters for each generator type, ensuring the configuration aligns with project settings.
"""
import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from config.path_manager import PathManager
from microgridspy.gui.utils import initialize_session_state


def ensure_list_length(key: str, length: int) -> None:
    """Ensure the list in session state has the required length."""
    if key not in st.session_state:
        st.session_state[key] = [0] * length
    else:
        st.session_state[key].extend([0] * (length - len(st.session_state[key])))

def manual_fuel_cost_input(time_horizon: int, gen_names: list, currency: str):
    """Create a data editor for manual input of fuel specific costs."""
    initial_data = {
        'Year': list(range(1, time_horizon + 1)),
        **{gen: [0.0] * time_horizon for gen in gen_names}
    }
    df = pd.DataFrame(initial_data)

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        column_config={
            "Year": st.column_config.NumberColumn(
                "Year",
                min_value=1,
                max_value=time_horizon,
                step=1,
                disabled=True),
            **{
                gen: st.column_config.NumberColumn(
                    f"{gen} [{currency}/l]",
                    min_value=0.0,
                    format="%.2f"
                ) for gen in gen_names
            }
        },
        hide_index=True)

    return edited_df

def load_fuel_cost_data(file_path):
    """Load existing fuel cost data from CSV file."""
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None
    

def generator_technology() -> None:
    """Streamlit page for configuring generator technology parameters."""
    st.title("Generator Parameters")
    st.subheader("Define the parameters for the generator types in your project")
    image_path = PathManager.IMAGES_PATH / "technology_characterization.png"
    st.image(str(image_path), use_column_width=True, caption="Overview of the technology characterization parameters")

    has_generator = st.session_state.get('system_configuration', 0) in [0, 2]
    
    if has_generator:
        # Initialize session state variables
        initialize_session_state(st.session_state.default_values, "generator_params")
        currency = st.session_state.get('currency', 'USD')
        time_horizon = st.session_state.get('time_horizon', 0)
        brownfield = st.session_state.get('brownfield', False)
        unit_commitment = st.session_state.get('unit_commitment', False)
        milp_formulation = st.session_state.get('advanced_settings', {}).get('milp_formulation', False)
        fuel_cost_df = None

        # Number of generator types
        st.session_state.gen_types = st.number_input("Number of Generator Types", min_value=1, value=st.session_state.gen_types)

        # Ensure session state lists have the correct length
        keys = [
        'gen_names', 'gen_nominal_capacity', 'gen_nominal_efficiency',
        'gen_specific_investment_cost', 'gen_specific_om_cost', 'gen_lifetime',
        'gen_unit_co2_emission', 'gen_existing_capacity', 'gen_existing_years',
        'fuel_names', 'fuel_lhv', 'fuel_co2_emission', 'gen_min_output', 'gen_cost_increase']
        for key in keys:
            ensure_list_length(key, st.session_state.gen_types)

        # Generator and Fuel Parameters
        st.header("Generator and Fuel Parameters")
        st.write("Please input the technical, economic, and fuel-related parameters for each generator type:")
        for i in range(st.session_state.gen_types):
            st.subheader(f"Generator Type {i+1}")
            st.session_state.gen_names[i] = st.text_input(f"Name for Generator Type {i+1}", value=st.session_state.gen_names[i])
            gen_name = st.session_state.gen_names[i]

            if unit_commitment:
                st.session_state.gen_nominal_capacity[i] = st.number_input(
                    f"Nominal Capacity of {gen_name} [W]", 
                    value=st.session_state.gen_nominal_capacity[i],
                    help="The rated power output of the generator.")

            st.session_state.gen_nominal_efficiency[i] = st.number_input(
                f"Nominal Efficiency of {gen_name} [%]", 
                min_value=0.0, 
                max_value=100.0, 
                value=float(st.session_state.gen_nominal_efficiency[i] * 100),
                step=0.1,
                format="%.1f",
                help="The efficiency of the generator at its nominal capacity. Input as a percentage.") / 100  # Convert percentage to fraction

            st.session_state.gen_specific_investment_cost[i] = st.number_input(
                f"Specific Investment Cost of {gen_name} [{currency}/W]", 
                value=st.session_state.gen_specific_investment_cost[i],
                help="The initial investment cost per watt of installed capacity.")

            st.session_state.gen_specific_om_cost[i] = st.number_input(
                f"Specific O&M Cost of {gen_name} [% of investment cost]", 
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.gen_specific_om_cost[i] * 100),
                step=0.1,
                format="%.1f",
                help="Annual operation and maintenance cost as a percentage of the initial investment cost.") / 100  # Convert percentage to fraction

            if brownfield:
                st.session_state.gen_lifetime[i] = st.number_input(
                    f"Lifetime of {gen_name} [years]", 
                    value=st.session_state.gen_lifetime[i],
                    help="Expected operational lifetime of the generator.")
            else:
                st.session_state.gen_lifetime[i] = st.number_input(
                    f"Lifetime of {gen_name} [years]", 
                    min_value=time_horizon, 
                    value=max(st.session_state.gen_lifetime[i], time_horizon),
                    help="Expected operational lifetime of the generator. Must be at least as long as the project time horizon for greenfield projects.")

            st.session_state.gen_unit_co2_emission[i] = st.number_input(
                f"Unit CO2 Emission of {gen_name} [kgCO2/kWh]", 
                value=st.session_state.gen_unit_co2_emission[i],
                help="The amount of CO2 emitted per kWh of electricity generated.")

            st.session_state.fuel_names[i] = st.text_input(
                f"Fuel Name for {gen_name}", 
                value=st.session_state.fuel_names[i],
                help="The name of the fuel used by this generator type.")

            st.session_state.fuel_lhv[i] = st.number_input(
                f"Fuel LHV for {gen_name} [Wh/l]", 
                value=st.session_state.fuel_lhv[i],
                help="Lower Heating Value of the fuel in Watt-hours per liter.")

            st.session_state.fuel_co2_emission[i] = st.number_input(
                f"Fuel CO2 Emission for {gen_name} [kgCO2/l]", 
                value=st.session_state.fuel_co2_emission[i],
                help="The amount of CO2 emitted per liter of fuel consumed.")

            if brownfield:
                st.write("### Brownfield project parameters:")
                
                # Get user input in kW, but store the value in W
                gen_capacity = st.number_input(
                    f"Existing Capacity of {gen_name} [W]", 
                    min_value=0.0,
                    value=float(st.session_state.gen_existing_capacity[i]),
                    help="The capacity of existing generators of this type.")
                
                # Store the value in W in session_state
                st.session_state.gen_existing_capacity[i] = gen_capacity
                if gen_capacity > 0:
                    st.session_state.gen_existing_years[i] = st.number_input(
                        f"Existing Years of {gen_name} [years]", 
                        min_value=0,
                        max_value=(st.session_state.gen_lifetime[i] - 1),
                        value=st.session_state.gen_existing_years[i],
                        help="The number of years the existing generators have been in operation.")

            # Variable Fuel Cost
            st.subheader(f"Variable Fuel Cost for {gen_name}")
        
            fuel_cost_option = st.radio(
                f"Select fuel cost type for {gen_name}:",
                ["Fixed price", "Variable prices"],
                key=f"fuel_cost_option_{i}")

            fuel_cost_file_path = PathManager.FUEL_SPECIFIC_COST_FILE_PATH.parent / "Fuel Specific Cost.csv"
            existing_fuel_cost_data = load_fuel_cost_data(fuel_cost_file_path)

            if fuel_cost_option == "Fixed price":
                fixed_price = st.number_input(
                    f"Fixed fuel price for {gen_name} [{currency}/l]",
                    min_value=0.0,
                    value=existing_fuel_cost_data[gen_name].mean() if existing_fuel_cost_data is not None else 0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"fixed_price_{i}")
            
                fuel_cost_df = pd.DataFrame({
                    'Year': list(range(1, time_horizon + 1)),
                    gen_name: [fixed_price] * time_horizon})
                
                # Save the data to CSV file
                fuel_cost_df.to_csv(fuel_cost_file_path, index=False)
        
            else:  # Variable prices
                st.write(f"Please input the fuel specific cost for {gen_name} over the project timeline:")
            
                if existing_fuel_cost_data is not None:
                    fuel_cost_df = st.data_editor(
                        existing_fuel_cost_data,
                        num_rows="dynamic",
                        column_config={
                            "Year": st.column_config.NumberColumn(
                                "Year",
                                min_value=1,
                                max_value=time_horizon,
                                step=1,
                                disabled=True),
                            gen_name: st.column_config.NumberColumn(
                                f"{gen_name} [{currency}/l]",
                                min_value=0.0,
                                format="%.2f")},
                        hide_index=True)
                else:
                    fuel_cost_df = manual_fuel_cost_input(time_horizon, [gen_name], currency)

                if st.button(f"Save and Export Fuel Cost Data for {gen_name}"):
                    # Save the data to CSV file
                    fuel_cost_df.to_csv(fuel_cost_file_path, index=False)
                    st.success(f"Fuel Specific Cost data saved and exported successfully to {fuel_cost_file_path}")

                # Create line plot
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(fuel_cost_df['Year'], fuel_cost_df[gen_name], marker='o', label=gen_name)
                ax.set_xlabel('Year')
                ax.set_ylabel(f'Fuel Cost [{currency}/l]')
                ax.set_title(f'Fuel Cost Variation Over Time for {gen_name}')
                ax.legend()
                ax.grid(True)
                st.pyplot(fig)

            st.markdown("---")  # Add a horizontal line for visual separation between generator types


        # Partial Load Parameters
        if milp_formulation and unit_commitment:
            st.header("Partial Load Parameters")
            st.session_state.partial_load = st.checkbox("Enable Partial Load", value=st.session_state.partial_load)
            if st.session_state.partial_load:
                for i, gen_name in enumerate(st.session_state.gen_names):
                    st.session_state.gen_min_output[i] = st.number_input(
                        f"Minimum Output for {gen_name} [%]", 
                        min_value=0.0, 
                        max_value=100.0, 
                        value=float(st.session_state.gen_min_output[i] * 100),
                        step=0.1,
                        format="%.1f",
                        help="The minimum output of the generator as a percentage of its nominal capacity.") / 100  # Convert percentage to fraction
                    st.session_state.gen_cost_increase[i] = st.number_input(
                        f"Cost Increase for {gen_name} [%]", 
                        min_value=0.0, 
                        max_value=100.0,
                        value=float(st.session_state.gen_cost_increase[i] * 100),
                        step=0.1,
                        format="%.1f",
                        help="The percentage increase in operating cost when the generator is running at minimum output.") / 100  # Convert percentage to fraction

    else:
        st.warning("Generator technology is not included in the system configuration. If you want to include a generator, please edit the project settings page.")
        
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Battery Characterization"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Grid Connection"
            st.rerun()