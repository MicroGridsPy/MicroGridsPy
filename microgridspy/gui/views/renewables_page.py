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
        key=f"res_inv_cost_{i}")
    
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
       
    if 'res_connection_types' not in st.session_state:
        st.session_state.res_connection_types = [''] * len(st.session_state.res_current_types)
    else:
        st.session_state.res_connection_types.extend([''] * (len(st.session_state.res_current_types) - len(st.session_state.res_connection_types)))

    if st.session_state.grid_type == "Alternating Current":
        if st.session_state.res_current_types[i] == "Direct Current":
            st.write("##### Inverter parameters:")    
            options = ["Connected with a seperate Inverter to the Microgrid", "Connected with the same Inverter as the Battery to the Microgrid"]
            if st.session_state.res_connection_types[i] not in options:
                st.session_state.res_connection_types[i] = options[1]
            if st.session_state.milp_formulation:
                st.session_state.res_connection_types[i] = st.selectbox(
                        f"Connection to the Microgrid for Resource {i+1}", 
                        options, 
                        index=options.index(st.session_state.res_connection_types[i]),
                        key=f"res_connenction_types_{i}",
                        help="Select the connection type of renewable energy source. This determines the configuration options and data processing.")
            else:
                st.session_state.res_connection_types[i] = options[0]
            if st.session_state.res_connection_types[i] == options[0]:
                st.session_state.res_inverter_efficiency[i] = st.number_input(
                    f"Inverter Efficiency [%]", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=float(st.session_state.res_inverter_efficiency[i] * 100), 
                    key=f"inv_eff_{i}") / 100
                st.session_state.res_inverter_nominal_capacity[i] = st.number_input(
                    f"Inverter Nominal Capacity [W]", 
                    min_value=0.0, 
                    value=float(st.session_state.res_inverter_nominal_capacity[i]), 
                    key=f"inv_nom_{i}")
                st.session_state.res_inverter_lifetime[i] = st.number_input(
                    f"Inverter Lifetime [years]", 
                    min_value=0.0, 
                    value=float(st.session_state.res_inverter_lifetime[i]), 
                    key=f"inv_lifetime_{i}")
                st.session_state.res_inverter_cost[i] = st.number_input(
                    f"Inverter Cost [{currency}/W]", 
                    min_value=0.0, 
                    value=float(st.session_state.res_inverter_cost[i]), 
                    key=f"res_inverter_cost_{i}")
            else:
                st.session_state.res_inverter_efficiency[i] = 1.0
                st.session_state.res_inverter_nominal_capacity[i] = 1.0 # Does not matter as it is not used in the model
                st.session_state.res_inverter_cost[i] = 0.0

        else:
            st.write("##### Converter parameters:")
            options = ["Connected directly to the Microgrid", "Connected with a AC-AC Converter to the Microgrid"]
            if st.session_state.res_connection_types[i] not in options:
                st.session_state.res_connection_types[i] = options[1]
            st.session_state.res_connection_types[i] = st.selectbox(
                    f"Connection to the Microgrid for Resource {i+1}", 
                    options, 
                    index=options.index(st.session_state.res_connection_types[i]),
                    key=f"res_connenction_type_{i}",
                    help="Select the connection type of renewable energy source. This determines the configuration options and data processing.")
            if st.session_state.res_connection_types[i] == options[1]:
                st.session_state.res_inverter_efficiency[i] = st.number_input(
                    f"AC-AC Converter Efficiency [%]", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=float(st.session_state.res_inverter_efficiency[i] * 100), 
                    key=f"inv_eff_{i}") / 100
                st.session_state.res_inverter_nominal_capacity[i] = st.number_input(
                    f"AC-AC Converter Nominal Capacity [W]", 
                    min_value=0.0, 
                    value=float(st.session_state.res_inverter_nominal_capacity[i]), 
                    key=f"inv_nom_{i}")
                st.session_state.res_inverter_lifetime[i] = st.number_input(
                    f"AC-AC Converter Lifetime [years]", 
                    min_value=0.0, 
                    value=float(st.session_state.res_inverter_lifetime[i]), 
                    key=f"inv_lifetime_{i}")
                st.session_state.res_inverter_cost[i] = st.number_input(
                    f"AC-AC Converter Cost [{currency}/W]", 
                    min_value=0.0, 
                    value=float(st.session_state.res_inverter_cost[i]), 
                    key=f"res_inverter_cost_{i}")
            else:
                st.session_state.res_inverter_efficiency[i] = 1.0
                
                st.session_state.res_inverter_cost[i] = 0.0

    else:
        if st.session_state.res_current_types[i] == "Direct Current":
            st.session_state.res_inverter_efficiency[i] = 1.0
            st.session_state.res_inverter_nominal_capacity[i] = 1.0 # Does not matter as it is not used in the model
            st.session_state.res_inverter_cost[i] = 0.0

        else:
            st.write("##### Rectifier parameters:")
            st.session_state.res_inverter_efficiency[i] = st.number_input(
                f"Rectifier Efficiency [%]",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.res_inverter_efficiency[i] * 100),
                key=f"inv_eff_{i}") / 100
            st.session_state.res_inverter_nominal_capacity[i] = st.number_input(
                f"Rectifier Nominal Capacity [W]",
                min_value=0.0,
                value=float(st.session_state.res_inverter_nominal_capacity[i]),
                key=f"inv_nom_{i}")
            st.session_state.res_inverter_cost[i] = st.number_input(
                f"Rectifier Cost [{currency}/W]",
                min_value=0.0,
                value=float(st.session_state.res_inverter_cost[i]),
                key=f"res_inverter_cost_{i}")

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

        if st.session_state.res_connection_types[i] == "Connected with a seperate Inverter to the Microgrid":
            # Get user input in kW, but store the value in W
            inverter_capacity = st.number_input(
                f"Existing Inverter Capacity [W]", 
                min_value=0.0,
                value=float(st.session_state.res_inverter_existing_capacity[i]),
                key=f"exist_inverter_cap_{i}")

            # Store the value in W in session_state
            st.session_state.res_inverter_existing_capacity[i] = res_capacity
            if inverter_capacity > 0:
                st.session_state.res_inverter_existing_years[i] = st.number_input(
                    f"Existing Years Inverter [years]", 
                    min_value=0.0,
                    max_value=float(st.session_state.res_inverter_lifetime[i] - 1),
                    value=float(st.session_state.res_inverter_existing_years[i]), 
                    key=f"inverter_exist_years_{i}")
                
        elif st.session_state.grid_type == "Alternating Current" and st.session_state.res_connection_types[i] == "Connected with a AC-AC Converter to the Microgrid":
            # Get user input in kW, but store the value in W
            inverter_capacity = st.number_input(
                f"Existing Converter Capacity [W]", 
                min_value=0.0,
                value=float(st.session_state.res_inverter_existing_capacity[i]),
                key=f"exist_inverter_cap_{i}")

            # Store the value in W in session_state
            st.session_state.res_inverter_existing_capacity[i] = res_capacity
            if inverter_capacity > 0:
                st.session_state.res_inverter_existing_years[i] = st.number_input(
                    f"Existing Years Converter [years]", 
                    min_value=0.0,
                    max_value=float(st.session_state.res_inverter_lifetime[i] - 1),
                    value=float(st.session_state.res_inverter_existing_years[i]), 
                    key=f"inverter_exist_years_{i}")
                
        elif st.session_state.grid_type == "Direct Current" and st.session_state.res_current_types[i] == "Alternating Current":
            # Get user input in kW, but store the value in W
            inverter_capacity = st.number_input(
                f"Existing Rectifier Capacity [W]", 
                min_value=0.0,
                value=float(st.session_state.res_inverter_existing_capacity[i]),
                key=f"exist_inverter_cap_{i}")

            # Store the value in W in session_state
            st.session_state.res_inverter_existing_capacity[i] = res_capacity
            if inverter_capacity > 0:
                st.session_state.res_inverter_existing_years[i] = st.number_input(
                    f"Existing Years Rectifier [years]", 
                    min_value=0.0,
                    max_value=float(st.session_state.res_inverter_lifetime[i] - 1),
                    value=float(st.session_state.res_inverter_existing_years[i]), 
                    key=f"inverter_exist_years_{i}")

def renewables_technology() -> None:
    """Streamlit page for configuring renewable energy technology parameters."""
    st.title("Renewables Parameters")
    st.subheader("Define the parameters for each renewable source")
    st.write("""
    This page is dedicated to initializing parameters for renewable energy technologies within the project. 
    Here, you can configure the relevant settings and values associated with each renewable source used in the model.
    Below is a brief overview of the mathematical formulation of renewables within MicroGridsPy:
    """)
    image_path = PathManager.IMAGES_PATH / "renewables_math_formulation.PNG"
    st.image(str(image_path), use_column_width=True, caption="Overview of the main equations for renewables")

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
    keys = ['res_specific_investment_cost','res_specific_om_cost', 'res_lifetime', 'res_unit_co2_emission',
            'res_inverter_efficiency', 'res_inverter_nominal_capacity', 'res_inverter_lifetime', 'res_inverter_cost', 'res_inverter_existing_capacity', 'res_inverter_existing_years']
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