import streamlit as st

from microgridspy.gui.utils import initialize_session_state


def settings_page():
    """Streamlit page for configuring project settings."""
    # Page title and description
    st.title("Project Settings")
    st.subheader("Configure key aspects of the project's timeline, financial settings, and optimization goals.")
    st.write("This page allows you to configure the basic settings for your project. Adjust the timeline, financial parameters, and optimization goals to suit your project's needs.")

    # Initialize session state variables
    initialize_session_state(st.session_state.default_values, 'project_settings')

    # Project settings
    with st.expander("📅 Project Timeline", expanded=False):
        st.session_state.time_horizon = st.number_input(
            "Total Project Duration [Years]:", 
            min_value=0, 
            value=st.session_state.time_horizon,
            help="Define the total lifespan of your project. This affects long-term cost calculations and technology replacements.")
        
        st.session_state.start_date = st.date_input(
            "Start Date of the Project:", 
            value=st.session_state.start_date,
            help="Select the start date of the project.")

    with st.expander("💰 Financial Settings", expanded=False):
        discount_rate_percent = st.number_input(
            "Discount Rate [%]:", 
            min_value=0.0, max_value=100.0, 
            value=st.session_state.discount_rate * 100,
            help="Enter the annual discount rate. This rate is used to calculate the present value of future cash flows, reflecting the time value of money and project risk.")
        st.session_state.discount_rate = discount_rate_percent / 100
        
        st.session_state.currency = st.text_input(
            "Currency:", 
            value=st.session_state.currency,
            help="Enter the currency used for the project (e.g. USD, EUR, etc.).")

    with st.expander("⚙️ Optimization Settings", expanded=False):
        resolution_options = {"Hourly resolution": 8760} #TODO: Add more resolution options
        selected_resolution = st.selectbox(
            "Time Resolution [periods/year]:", 
            options=list(resolution_options.keys()),
            help="Choose the time granularity of your simulation. Hourly resolution provides detailed analysis but increases computation time.")
        st.session_state.time_resolution = resolution_options[selected_resolution]

        optimization_goal = st.radio(
            "Optimization Goal:", 
            options=["NPC", "Operation cost"],
            index=0 if st.session_state.optimization_goal == 0 else 1,
            help="Select whether to optimize for lowest Net Present Cost (NPC, total lifecycle cost) or lowest Operation Cost (annual running costs).")
        st.session_state.optimization_goal = 0 if optimization_goal == "NPC" else 1

        if st.session_state.optimization_goal == 1:
            st.session_state.investment_cost_limit = st.number_input(
                f"Investment Cost Limit [{st.session_state.currency}]:", 
                min_value=0.0, 
                value=st.session_state.investment_cost_limit,
                help="Set a cap on initial investment costs. This is particularly relevant when optimizing for operation costs to ensure feasible initial outlays.")

        system_configuration_options = ["Renewables + Batteries and Generators","Renewables + Batteries Only","Renewables + Generators Only"]

        selected_system_config = st.selectbox(
            "Select System Configuration:", 
            options=system_configuration_options,
            index=st.session_state.system_configuration,
            help="Choose the components to include in the mini-grid. This determines the energy mix and affects system reliability and cost structure.")
        
        st.session_state.system_configuration = system_configuration_options.index(selected_system_config)

    with st.expander("🔒 Optimization Constraints", expanded=False):
        renewable_penetration_percent = st.number_input(
            "Minimum Renewable Penetration [%]:", 
            min_value=0.0, max_value=100.0,
            value=st.session_state.renewable_penetration * 100,
            help="Set the minimum percentage of energy that must come from renewable sources. Higher values promote cleaner energy but may increase costs.")
        st.session_state.renewable_penetration = renewable_penetration_percent / 100
        
        if st.session_state.system_configuration in [0, 1]:
            st.session_state.battery_independence = st.number_input(
                "Battery Independence [Days]:", 
                min_value=0,
                value=st.session_state.battery_independence,
                help="Specify the number of days the battery should be able to supply average load without recharging. Higher values increase energy security but also system cost.")
        
        lost_load_fraction_percent = st.number_input(
            "Maximum Lost Load Fraction [%]:", 
            min_value=0.0, max_value=100.0,
            value=st.session_state.lost_load_fraction * 100,
            help="Set the maximum acceptable percentage of unmet demand. Higher values may reduce system cost but decrease reliability.")
        st.session_state.lost_load_fraction = lost_load_fraction_percent / 100
        
        if st.session_state.lost_load_fraction > 0:
            st.session_state.lost_load_specific_cost = st.number_input(
                f"Lost Load Specific Cost [{st.session_state.currency}/Wh]:", 
                min_value=0.0,
                value=st.session_state.lost_load_specific_cost,
                help=f"Define the economic cost of unmet demand. This helps balance the trade-off between system cost and reliability.")
            
        st.session_state.land_availability = st.number_input(
            "Land Availability for Renewables [m2]:", 
            min_value=0.0,
            value=st.session_state.land_availability,
            help="Enter the total land area available for renewable energy installations. This constrains the maximum capacity of land-intensive technologies like solar PV.")

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