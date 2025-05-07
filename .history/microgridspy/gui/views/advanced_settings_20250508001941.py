import streamlit as st
import pandas as pd

from config.path_manager import PathManager
from microgridspy.gui.utils import initialize_session_state

def display_timeline(time_horizon, step_duration):
    """Display project timeline as a table."""
    num_steps = time_horizon // step_duration
    min_step_duration = time_horizon - step_duration * num_steps
    
    step_durations = [step_duration] * num_steps
    if min_step_duration > 0:
        step_durations.append(min_step_duration)
        num_steps += 1

    st.session_state.num_steps = num_steps

    timeline_data = {
        "Step": [f"Investment Step {i + 1}" for i in range(num_steps)],
        "Duration [Years]": step_durations} 
    
    df_timeline = pd.DataFrame(timeline_data)
    st.table(df_timeline)

def advanced_settings():
    """Streamlit page for configuring advanced settings."""
    # Page title and description
    st.title("Advanced Settings")
    st.write("Configure detailed model parameters and optimization options for your project.")

    initialize_session_state(st.session_state.default_values, 'advanced_settings')

    with st.expander("🧮 Model Formulation", expanded=False):
        st.markdown("""
        - **Linear Programming (LP):** This formulation uses continuous variables for optimization, allowing fractional sizing of components without considering nominal capacity constraints. It provides computational efficiency but may overlook realistic unit-based sizing.
        - **Mixed-Integer Linear Programming (MILP):** This approach introduces binary variables to capture more realistic technology behavior, like discrete flows for charging/discharging and minimum unit sizes for components. When enabled, the model also supports **Unit Commitment**, optimizing the number of units (n_units) for each technology, reflecting true nominal capacity steps.
        """)
        milp_options = ["Linear Programming (LP)", "Mixed-Integer Linear Programming (MILP)"]
        milp_index = 1 if st.session_state.milp_formulation else 0
        milp_choice = st.selectbox(
            "Optimization Formulation:",
            options=milp_options,
            index=milp_index,
            help="Choose between LP and MILP formulation. MILP allows for more realistic technology representation but may increase computational effort.")
        
        st.session_state.milp_formulation = milp_choice == "Mixed-Integer Linear Programming (MILP)"
        
        if st.session_state.milp_formulation:
            st.session_state.unit_commitment = st.checkbox(
                "Enable Unit Commitment Approach", 
                value=st.session_state.unit_commitment,
                help="Restrict sizing variables to units of nominal capacity for each technology. It allows for more realistic technology representation but may increase computational effort.")
        
        st.divider()

        st.markdown("""
        - **Greenfield:** Represents entirely new systems with no existing infrastructure, optimizing all components from scratch.
        - **Brownfield:** Accounts for existing installed capacities and years of operation, making it suitable for hybridization projects where new installations build upon existing infrastructure.
        """)
        project_type_options = ["Greenfield", "Brownfield"]
        project_type_index = 1 if st.session_state.brownfield else 0
        project_type_choice = st.selectbox(
            "Project Type:",
            options=project_type_options,
            index=project_type_index,
            help="Choose Greenfield for entirely new projects or Brownfield if considering existing capacity installed for the case study.")
        
        st.session_state.brownfield = project_type_choice == "Brownfield"

        st.divider()

        st.markdown("""
        - **Single Investment Step:** The system is optimized for the entire project horizon in one step.
        - **Capacity Expansion over Time:** Enables incremental upgrades across multiple investment steps, reflecting real-world project phasing. This setting also supports **Learning Curves**, modeling cost reductions in technology investments over time.
        """)
        capacity_expansion_options = ["Single Investment Step", "Capacity Expansion over Time"]
        capacity_expansion_index = 1 if st.session_state.capacity_expansion else 0
        capacity_expansion_choice = st.selectbox(
            "Investment Strategy:",
            options=capacity_expansion_options,
            index=capacity_expansion_index,
            help="Enable to allow system capacity to increase over time through discrete investment steps.")
        
        st.session_state.capacity_expansion = capacity_expansion_choice == "Capacity Expansion over Time"

        # Display timeline if capacity expansion is enabled
        if st.session_state.capacity_expansion:
            st.session_state.step_duration = st.slider(
                "Duration of each Investment Step [Years]:", 
                min_value=1, max_value=st.session_state.time_horizon,
                value=st.session_state.step_duration,
                help="Set the interval between potential capacity expansions. Shorter intervals allow more frequent upgrades but increase computational load.")
            
            display_timeline(st.session_state.time_horizon, st.session_state.step_duration)
        # Set step duration to time horizon if single investment step
        else:
            st.session_state.step_duration = st.session_state.time_horizon
            st.session_state.num_steps = 1


    with st.expander("⚡ Grid Connection", expanded=False):
        st.markdown("""
        The model allows for the system to **buy or sell electricity to the main grid** after a specified year of connection. This introduces several important parameters:
        - **Grid Electricity Prices:** Different rates for purchasing and selling electricity.
        - **Grid Distance and Connection Costs:** Includes the cost of extending the power line and installing transformers.
        - **Maximum Connection Capacity:** Sets the limit for energy exchange with the grid.
        - **CO₂ Emissions:** Accounts for emissions associated with national grid power consumption.
        - **Grid Availability:** Models the reliability of the grid connection, including outages and downtime. 
        Availability is simulated using **Weibull distributions** to sample outage frequency and duration, creating a realistic grid availability profile.
        """)
        st.session_state.grid_connection = st.checkbox(
            "Simulate Grid Connection", 
            value=st.session_state.grid_connection,
            help="Include national grid connection in the model. This affects energy balance and can impact system economics significantly.")
        
        if st.session_state.grid_connection:
            
            grid_connection_type = st.radio(
                "Grid Connection Type:", 
                options=["Purchase Only", "Purchase/Sell"],
                index=st.session_state.grid_connection_type,
                help="Choose whether the system can only buy from the grid or both buy and sell. Selling capability can significantly affect system economics.")
            
            st.session_state.grid_connection_type = 0 if grid_connection_type == "Purchase Only" else 1

    with st.expander("📈 Weighted Average Cost of Capital Calculation", expanded=False):
        st.markdown("""
        WACC represents the **average cost of financing** a project, weighted by its capital structure (debt and equity). It replaces the standard discount rate in financial modeling, providing a more realistic measure of the **minimum return needed** to make the investment profitable.
        The calculation accounts for the **cost of equity**, **cost of debt**, and the **corporate tax rate**, reflecting the true cost of capital for mini-grid projects.
        """)
        image_path = PathManager.IMAGES_PATH / "wacc.PNG"
        st.image(str(image_path), use_container_width=True, caption="Trends in debt and equity for SSA mini-grids")
        st.session_state.wacc_calculation = st.checkbox(
            "Enable WACC Calculation", 
            value=st.session_state.wacc_calculation,
            help="Activate to calculate the Weighted Average Cost of Capital. This provides a more accurate discount rate for financial calculations.")
        
        if st.session_state.wacc_calculation:
            cost_of_equity = st.number_input(
                "Cost of Equity [%]:", 
                min_value=0.0, max_value=100.0,
                value=st.session_state.cost_of_equity * 100,
                help="Expected return on equity investment. Higher values indicate higher risk or expected returns.")
            st.session_state.cost_of_equity = cost_of_equity / 100 
            
            cost_of_debt = st.number_input(
                "Cost of Debt [%]:", 
                min_value=0.0, max_value=100.0,
                value=st.session_state.cost_of_debt * 100,
                help="Interest rate on project debt. This is typically lower than the cost of equity.")
            st.session_state.cost_of_debt = cost_of_debt / 100  
            
            tax = st.number_input(
                "Corporate Tax Rate [%]:", 
                min_value=0.0, max_value=100.0,
                value=st.session_state.tax * 100,
                help="Applicable corporate tax rate. This affects the after-tax cost of debt.")
            st.session_state.tax = tax / 100  
            
            equity_share = st.number_input(
                "Equity Share [%]:", 
                min_value=0.0, max_value=100.0,
                value=st.session_state.equity_share * 100,
                help="Percentage of project financed through equity. Must sum to 100% with debt share.")
            st.session_state.equity_share = equity_share / 100  
            
            debt_share = st.number_input(
                "Debt Share [%]:", 
                min_value=0.0, max_value=100.0,
                value=st.session_state.debt_share * 100,
                help="Percentage of project financed through debt. Must sum to 100% with equity share.")
            st.session_state.debt_share = debt_share / 100  

            # Calculate and display WACC
            if st.session_state.equity_share + st.session_state.debt_share != 1.0:
                st.warning("Equity Share and Debt Share must sum to 100%.")
            else:
                if st.session_state.equity_share == 0:
                    wacc = st.session_state.cost_of_debt * (1 - st.session_state.tax)
                else:
                    leverage = st.session_state.debt_share / st.session_state.equity_share
                    wacc = (st.session_state.cost_of_debt * (1 - st.session_state.tax) * leverage / (1 + leverage) + 
                            st.session_state.cost_of_equity / (1 + leverage))
                
                st.metric("Calculated WACC", f"{wacc:.2%}")
                st.session_state.calculated_wacc = wacc

    with st.expander("🎯 Multi-Objective Optimization", expanded=False):
        st.markdown("""
            In rural electrification, minimizing **Net Present Cost (NPC)** and **CO₂ emissions** are often both critical and conflicting objectives. Multi-objective optimization addresses the limitations of single-objective approaches by evaluating trade-offs between costs and emissions.

            **Methodology**

            - First, the model computes optimal solutions for NPC and CO₂ emissions independently to determine the feasible range.
            - Then, it iteratively constrains one objective (e.g., emissions) while minimizing the other (NPC), generating **Pareto optimal solutions**.
            - The result is a **Pareto front**, a set of solutions offering diverse trade-offs between cost and emissions.

            The Pareto front gives stakeholders a broader view of possible system configurations. Each point on the curve is an optimal balance between NPC and CO₂ emissions: no solution is strictly better than another without compromising one of the two objectives.

        """)
        image_path = PathManager.IMAGES_PATH / "pareto_front.jpg"
        st.image(str(image_path), use_container_width=True, caption="A graphical example of the Pareto optimal front")
        st.session_state.multiobjective_optimization = st.checkbox(
            "Enable Multi-Objective Optimization", 
            value=st.session_state.multiobjective_optimization,
            help="Optimize for both cost and CO2 emissions. This provides a range of solutions with different trade-offs.")
        
        if st.session_state.multiobjective_optimization:
            st.session_state.pareto_points = st.number_input(
                "Number of Pareto Curve Points:", 
                min_value=2, 
                value=st.session_state.pareto_points,
                help="Specify the number of solutions to generate along the Pareto front. More points provide a more detailed trade-off curve but increase computation time.")

    with st.expander("🔀 Multi-Scenario Optimization", expanded=False):
        # TODO: Implement multi-scenario optimization
        st.warning("⚠️ This functionality is a work in progress and not properly implemented yet.")
        st.session_state.multi_scenario_optimization = st.checkbox(
            "Enable Multi-Scenario Optimization", 
            value=st.session_state.multi_scenario_optimization,
            help="Optimize across multiple scenarios of demand and renewable resource availability. This accounts for uncertainty in long-term projections.")
        
        if st.session_state.multi_scenario_optimization:
            st.session_state.num_scenarios = st.number_input(
                "Number of Scenarios:", 
                min_value=1, 
                value=st.session_state.num_scenarios,
                help="Set the number of scenarios to consider. More scenarios capture more uncertainty but increase computational requirements.")
            
            scenario_weights = []
            for i in range(st.session_state.num_scenarios):
                weight = st.number_input(
                    f"Scenario {i+1} Weight [%]:", 
                    min_value=0.0, max_value=100.0,
                    value=st.session_state.scenario_weights[i] * 100 if i < len(st.session_state.scenario_weights) else 100.0 / st.session_state.num_scenarios,
                    key=f"scenario_weight_{i}",
                    help=f"Assign probability or importance to Scenario {i+1}. Weights should sum to 100% across all scenarios.")
                scenario_weights.append(weight / 100)  
            st.session_state.scenario_weights = scenario_weights

    # Navigation buttons
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Project Settings"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Resource Assessment"
            st.rerun()