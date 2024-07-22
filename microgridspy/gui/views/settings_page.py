"""
This module provides the settings page for the MicroGridsPy Streamlit application. 
It allows users to configure key aspects of their project's timeline, financial settings, 
and optimization goals. Users can adjust parameters and validate them using Pydantic.
"""

import streamlit as st

from microgridspy.model.parameters import ProjectParameters


def initialize_session_state(default_values: ProjectParameters) -> None:
    """Initialize session state variables for project settings."""
    project_settings = default_values.project_settings
    session_state_defaults = {
        'time_horizon': project_settings.time_horizon,
        'start_date': project_settings.start_date,
        'discount_rate': project_settings.discount_rate,
        'currency': project_settings.currency,
        'time_resolution': project_settings.time_resolution,
        'optimization_goal': project_settings.optimization_goal,
        'investment_cost_limit': project_settings.investment_cost_limit,
        'system_configuration': project_settings.system_configuration,
        'renewable_penetration': project_settings.renewable_penetration,
        'land_availability': project_settings.land_availability,
        'battery_independence': project_settings.battery_independence,
        'lost_load_fraction': project_settings.lost_load_fraction,
        'lost_load_specific_cost': project_settings.lost_load_specific_cost,
        'solver': project_settings.solver}

    for key, value in session_state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def settings_page() -> None:
    """
    Settings (Configuration Page) view.

    This function displays the configuration settings page for the user to update various 
    parameters related to the project's timeline, financial settings, and optimization goals. 
    It captures user inputs, validates them using Pydantic, and saves the updated configuration 
    to a YAML file.
    """
    st.title("Project Settings")
    st.subheader("Configure key aspects of the project's timeline, financial settings, and optimization goals.")
    st.write("This page allows you to configure the basic settings for your project. Adjust the timeline, financial parameters, and optimization goals to suit your project's needs.")

    # Initialize session state variables
    initialize_session_state(st.session_state.default_values)

    with st.expander("📅 Project Timeline", expanded=False):
        st.write("Set the overall duration and start date for the project.")
        st.session_state.time_horizon = st.number_input(
            "Total Project Duration [Years]:", min_value=0, value=st.session_state.time_horizon,
            help="Enter the total duration of the project in years.")
        
        st.session_state.start_date = st.date_input(
            "Start Date of the Project:", value=st.session_state.start_date,
            help="Select the start date of the project.")

    with st.expander("💰 Financial Settings", expanded=False):
        st.write("Configure the discount rate to actualize costs over the project time horizon.")
        st.session_state.discount_rate = st.number_input(
            "Discount Rate [-]:", min_value=0.0, max_value=1.0, value=st.session_state.discount_rate,
            help="Enter the discount rate as a fraction (e.g. 0.1 for 10%).")
        st.session_state.currency = st.text_input(
            "Currency:", value=st.session_state.currency,
            help="Enter the currency used for the project (e.g. USD, EUR, etc.).")

    with st.expander("⚙️ Optimization Settings", expanded=False):
        st.write("Define the goals and constraints for the optimization process.")
        resolution_options = {"Hourly resolution": 8760}
        selected_resolution = st.selectbox(
            "Time Resolution [periods/year]:", options=list(resolution_options.keys()),
            help="Select the time resolution for the model.")
        st.session_state.time_resolution = resolution_options[selected_resolution]

        optimization_goal = st.radio(
            "Optimization Goal:", options=["NPC", "Operation cost"],
            index=0 if st.session_state.optimization_goal == 0 else 1,
            help="Select the optimization goal: NPC (Net Present Cost) or Operation cost.")
        st.session_state.optimization_goal = 0 if optimization_goal == "NPC" else 1

        if st.session_state.optimization_goal == 1:
            st.session_state.investment_cost_limit = st.number_input(
                f"Investment Cost Limit [{st.session_state.currency}]:", min_value=0.0, value=st.session_state.investment_cost_limit,
                help="Enter the investment cost limit in USD.")

        st.write("Select the system configuration of the mini-grid.")
        system_configuration_options = [
            "Renewables + Batteries and Generators", 
            "Renewables + Batteries Only", 
            "Renewables + Generators Only"]
        
        system_configuration_labels = [
            "Renewables + Batteries & Generators", 
            "Renewables + Batteries Only", 
            "Renewables + Generators Only"]
        
        system_configuration_tabs = st.tabs(system_configuration_labels)

        for i, tab in enumerate(system_configuration_tabs):
            with tab:
                st.session_state.system_configuration = i
                st.write(system_configuration_options[i])

        solver_options = ["HiGHS", "Gurobi"]
        solver_index = st.session_state.solver if isinstance(
            st.session_state.solver, int) else solver_options.index(st.session_state.solver)
        
        st.session_state.solver = st.selectbox(
            "Select Solver:", options=solver_options, index=solver_index,
            help="Select the solver to be used for optimization.")

    with st.expander("🔒 Optimization Constraints", expanded=False):
        st.write("Specify the contribution of renewable energy sources, allowable unmet load, and battery independence.")
        st.session_state.renewable_penetration = st.number_input(
            "Renewable Penetration [-]:", min_value=0.0, max_value=1.0,
            value=st.session_state.renewable_penetration,
            help="Enter the minimum fraction of electricity produced by renewable sources (0 to 1).")
        
        st.session_state.battery_independence = st.number_input(
            "Battery Independence [Days]:", min_value=0,
            value=st.session_state.battery_independence,
            help="Enter the number of days of battery independence.")
        
        st.session_state.lost_load_fraction = st.number_input(
            "Lost Load Fraction [-]:", min_value=0.0, max_value=1.0,
            value=st.session_state.lost_load_fraction,
            help="Enter the maximum admissible loss of load as a fraction (0 to 1).")
        
        if st.session_state.lost_load_fraction > 0:
            st.session_state.lost_load_specific_cost = st.number_input(
                f"Lost Load Specific Cost [{st.session_state.currency}/Wh]:", min_value=0.0, max_value=1.0,
                value=st.session_state.lost_load_specific_cost,
                help=f"Enter the value of the unmet load in {st.session_state.currency} per Wh.")
            
        st.session_state.land_availability = st.number_input(
            "Land Availability for Renewables [m2]:", min_value=0.0,
            value=st.session_state.land_availability,
            help="Enter the available land area for the project in m2.")

    # Navigation buttons
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "New Project"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Advanced Settings"
            st.rerun()
