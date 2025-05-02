import streamlit as st
import pandas as pd

from typing import Dict, Any, List
from pathlib import Path
from microgridspy.model.model import Model
from config.path_manager import PathManager
from microgridspy.post_process.cost_calculations import (
    calculate_actualized_investment_cost,
    calculate_actualized_salvage_value,
    calculate_lcoe,
    calculate_grid_costs)
from microgridspy.post_process.energy_calculations import (
    calculate_energy_usage,
    calculate_renewable_penetration,
    calculate_partial_load_indicators)
from microgridspy.post_process.data_retrieval import get_sizing_results, get_conversion_sizing_results
from microgridspy.post_process.plots import (
    costs_pie_chart,
    create_energy_usage_pie_chart,
    dispatch_plot,
    create_sizing_plot
)
from microgridspy.post_process.export_results import save_energy_balance_to_excel, save_plots

# Constants
DEFAULT_COLORS = {
    'Demand': '#000000',  # Black
    'Curtailment': '#FFA500',  # Orange
    'Battery': '#4CC9F0',  # Light Blue
    'Electricity Purchased': '#800080',  # Purple
    'Electricity Sold': '#008000',  # Green
    'Lost Load': '#F21B3F'  # Red
}

# Helper functions
def initialize_colors(model: Model) -> Dict[str, str]:
    """Initialize or retrieve the color dictionary from the session state."""
    colors = DEFAULT_COLORS.copy()

    # Add renewable sources colors
    for i, res_name in enumerate(model.sets['renewable_sources'].values):
        colors[res_name] = ['#FFFF00', '#FFFFE0', '#FFFACD', '#FAFAD2'][i % 4]  # Shades of yellow

    # Add generator types colors if they exist
    if model.has_generator:
        for i, gen_name in enumerate(model.sets['generator_types'].values):
            colors[gen_name] = ['#00509D', '#0066CC', '#0077B6', '#0088A3'][i % 4]  # Shades of blue

    if 'color_dict' not in st.session_state:
        st.session_state.color_dict = colors

    return st.session_state.color_dict

def create_color_customization_section(all_elements: List[str], color_dict: Dict[str, str]) -> None:
    """Create a color customization section in the Streamlit app."""
    st.write("Customize colors for each technology: click on the color picker to change the color.")
    cols = st.columns(len(all_elements))
    for element, col in zip(all_elements, cols):
        with col:
            default_color = color_dict.get(element, DEFAULT_COLORS.get(element))
            color_dict[element] = st.color_picker(
                element,
                key=f"color_{element}",
                value=default_color)

def costs_breakdown(model: Model, optimization_goal: str):
    """Display the cost breakdown of the model."""
    currency = st.session_state.get('currency', 'USD')
    actualized = optimization_goal == "NPC"

    cost_data: List[Dict[str, Any]] = []

    def add_cost_item(label: str, value: float, condition: bool = True):
        if condition:
            cost_data.append({
                "Cost Item": label,
                f"Value (k{currency})": f"{value / 1000:.2f}"})

    # Function to check if a variable exists in the solution
    def get_variable_value(var_name: str, default=0):
        try:
            return model.get_solution_variable(var_name).values.item()
        except ValueError:
            return default

    # Investment Cost
    investment_cost = (get_variable_value("Total Investment Cost") if actualized else calculate_actualized_investment_cost(model))
    add_cost_item("Total Investment Cost (Actualized)", investment_cost)

    # Variable Cost
    variable_cost_label = f"Total Variable Cost ({'Actualized' if actualized else 'Not Actualized'})"
    variable_cost = get_variable_value(f"Scenario Total Variable Cost {'(Actualized)' if actualized else '(Not Actualized)'}")
    add_cost_item(variable_cost_label, variable_cost)

    # Fixed O&M Cost
    om_cost_label = f" - Total Fixed O&M Cost ({'Actualized' if actualized else 'Not Actualized'})"
    om_cost = get_variable_value(f"Operation and Maintenance Cost {'(Actualized)' if actualized else '(Not Actualized)'}")
    add_cost_item(om_cost_label, om_cost)

    # Battery Cost
    if model.has_battery:
        battery_cost_label = f" - Total Battery Replacement Cost ({'Actualized' if actualized else 'Not Actualized'})"
        battery_cost = get_variable_value(f"Battery Replacement Cost {'(Actualized)' if actualized else '(Not Actualized)'}")
        add_cost_item(battery_cost_label, battery_cost)

    # Generator Cost (only if the variable exists)
    if model.has_generator:
        fuel_cost_label = f" - Total Fuel Cost ({'Actualized' if actualized else 'Not Actualized'})"
        fuel_cost = get_variable_value(f"Total Fuel Cost {'(Actualized)' if actualized else '(Not Actualized)'}")
        add_cost_item(fuel_cost_label, fuel_cost, fuel_cost > 0)  # Avoid adding if it's zero

    # Salvage Value
    salvage_value = (get_variable_value("Salvage Value") if actualized else calculate_actualized_salvage_value(model))
    add_cost_item("Total Salvage Value (Actualized)", salvage_value)

    # Grid Costs
    if model.has_grid_connection:
        grid_costs = calculate_grid_costs(model, actualized)
        add_cost_item("Grid Investment Cost (Actualized)", grid_costs[0])
        add_cost_item(f"Grid Fixed O&M Cost ({'Actualized' if actualized else 'Not Actualized'})", grid_costs[1])
        add_cost_item(f"Total Electricity Purchased Cost ({'Actualized' if actualized else 'Not Actualized'})", grid_costs[2])

        if model.get_settings('grid_connection_type', advanced=True) == 1:
            add_cost_item(f"Total Electricity Sold Revenue ({'Actualized' if actualized else 'Not Actualized'})", grid_costs[3])

    # Create DataFrame
    cost_df = pd.DataFrame(cost_data)

    return cost_df


def define_all_elements(model: Model) -> List[str]:
    """Define all possible elements for the energy system."""
    elements = ["Demand", "Curtailment"] + list(model.sets['renewable_sources'].values)
    if model.has_battery:
        elements.append("Battery")
    if model.has_generator:
        elements.extend(list(model.sets['generator_types'].values))
    if model.has_grid_connection:
        elements.append("Electricity Purchased")
        if model.get_settings('grid_connection_type', advanced=True) == 1:
            elements.append("Electricity Sold")
    if model.get_settings('lost_load_fraction') > 0.0:
        elements.append("Lost Load")
    return elements

def export_results(project_name: str, model: Model, costs_df: pd.DataFrame, sizing_df: pd.DataFrame, conversion_sizing_df: pd.DataFrame, fig: dict) -> None:
    """Setup the export results section."""

    # Retrieve results folder path
    results_folder = Path(PathManager.RESULTS_FOLDER_PATH)
    plots_folder = results_folder / "Plots"
    plots_folder.mkdir(exist_ok=True)

    # Retrieve the related project folder path
    path_manager = PathManager(project_name)
    project_folder = Path(path_manager.PROJECTS_FOLDER_PATH) / project_name / "results"
    project_folder_plots = project_folder / "Plots"
    project_folder_plots.mkdir(exist_ok=True, parents=True)

    if st.button("📁 Export Results to Excel"):
        with st.spinner("Exporting results..."):
            # Cost breakdown
            costs_df.to_excel(results_folder / "Costs Breakdown.xlsx", index=False)
            costs_df.to_excel(project_folder / "Costs Breakdown.xlsx", index=False)
            
            # Sizing results
            sizing_df.to_excel(results_folder / "Sizing Results.xlsx", index=False)
            sizing_df.to_excel(project_folder / "Sizing Results.xlsx", index=False)
            if conversion_sizing_df is not None:
                conversion_sizing_df.to_excel(results_folder / "Conversion Sizing Results.xlsx", index=False)
                conversion_sizing_df.to_excel(project_folder / "Conversion Sizing Results.xlsx", index=False)
            
            # Energy balance
            save_energy_balance_to_excel(model, results_folder)
            save_energy_balance_to_excel(model, project_folder)
        
        st.success(f"Results exported successfully to {results_folder} and {project_folder}")

    if st.button("📊 Save Current Plots"):
        with st.spinner("Saving current plots..."):
            save_plots(plots_folder, fig)
            save_plots(project_folder_plots, fig)
        
        st.success(f"Plots saved successfully to {plots_folder} and {project_folder_plots}")


def plots_dashboard():
    """Create the results dashboard with cost breakdown, sizing results, and additional visualizations."""
    fig: dict = {}
    st.title("Results Dashboard")

    if 'model' not in st.session_state:
        st.warning("Please run the optimization model first.")
        return

    # Retrieve model and settings
    model: Model = st.session_state.model
    currency = st.session_state.get('currency', 'USD')
    project_name = st.session_state.get('project_name')
    partial_load = st.session_state.get('partial_load')

    # Initialize colors
    color_dict = initialize_colors(model)

    # -------------------------
    # Cost Breakdown
    # -------------------------
    st.header("Cost Breakdown")

    # Determine the optimization goal
    optimization_goal = 'NPC' if model.get_settings('optimization_goal') == 0 else 'Total Variable Cost'
    actualized = optimization_goal == "NPC"

    # Display main metrics
    main_cost = (
        model.get_solution_variable('Net Present Cost').values.item()
        if actualized else
        model.get_solution_variable('Total Variable Cost').values.item())

    col1, col2 = st.columns(2)
    with col1:
        st.metric(optimization_goal, f"{main_cost / 1000:.2f} k{currency}")

    with col2:
        lcoe = calculate_lcoe(model, optimization_goal)
        lcoe_label = "Levelized Cost of Energy (LCOE)" if actualized else "Levelized Variable Cost (LVC)"
        st.metric(lcoe_label, f"{lcoe:.4f} {currency}/kWh")
    
    # Display cost breakdown
    st.subheader("Cost Details")
    costs_df = costs_breakdown(model, optimization_goal)
    st.table(costs_df)

    # Cost Breakdown Pie Chart
    cost_breakdown_fig = costs_pie_chart(model, optimization_goal, color_dict)
    fig['Cost Breakdown Bar of Pie Chart'] = cost_breakdown_fig
    st.pyplot(cost_breakdown_fig)

    st.write("---")  # Add a separator

    # -------------------------
    # Sizing and Dispatch
    # -------------------------
    st.header("Sizing and Dispatch")
    # Color customization
    all_elements = define_all_elements(model)
    create_color_customization_section(all_elements, color_dict)

    # Sizing results
    # -------------------------
    st.header("Mini-Grid Sizing")
    sizing_df = get_sizing_results(model)
    sizing_fig = create_sizing_plot(model, color_dict, sizing_df)
    fig['System Sizing'] = sizing_fig
    st.pyplot(sizing_fig)
    st.table(sizing_df)

    try:
        conversion_sizing_df = get_conversion_sizing_results(model)
        st.write("Conversion Sizing Results")
        st.table(conversion_sizing_df)
    except:
        conversion_sizing_df = None
        st.write("No conversion sizing results available.")
    
    # Energy Balance Visualization
    # --------------------------------
    st.header("Energy Usage Visualization")

    years = [int(year) for year in model.sets['years']]
    min_year, max_year = min(years), max(years)

    # Dispatch Plot
    st.subheader("Dispatch Plot")
    st.info("**Note:** The dispatch plot presented here shows an optimal use of energy based on perfect foresight. It represents an idealized scenario and does not reflect a realistic dispatch strategy with real-time constraints.")
    if len(years) > 1:
        selected_year = st.slider("Select Year for Dispatch Plot", min_value=min_year, max_value=max_year, value=min_year)
        selected_year_index = years.index(selected_year)
        selected_day = st.slider("Select Day", 0, 364, 0, key="day_slider")
    else:
        selected_year_index = 0
        selected_day = st.slider("Select Day", 0, 364, 0, key="day_slider")

    dispatch_fig = dispatch_plot(model, scenario=0, year=selected_year_index, day=selected_day, color_dict=color_dict)
    fig['Dispatch Plot'] = dispatch_fig
    st.pyplot(dispatch_fig)

    # Energy Usage Pie Chart
    energy_usage = calculate_energy_usage(model)
    renewable_penetration = calculate_renewable_penetration(model)
    st.subheader("Average Energy Usage")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Yearly Curtailment", f"{energy_usage['Curtailment']:.2f}%")
    with col2:
        st.metric("Average Yearly Renewable Penetration", f"{renewable_penetration:.2f}%")

    if model.has_generator:
        energy_usage_fig = create_energy_usage_pie_chart(energy_usage, model, st.session_state.res_names, color_dict, st.session_state.gen_names)
    else:
        energy_usage_fig = create_energy_usage_pie_chart(energy_usage, model, st.session_state.res_names, color_dict)
    fig['Energy Usage Pie Chart'] = energy_usage_fig
    st.pyplot(energy_usage_fig)

    if model.has_generator:
        col1, col2 = st.columns(2)
        with col1:
            fuel_consumption_da = model.get_solution_variable('Generator Fuel Consumption')
            fuel_consumption = fuel_consumption_da.sum().item()
            st.metric("Fuel Total Consumption", f"{fuel_consumption:.2f} liters")
        with col2:
            fuel_emission_da = model.get_solution_variable('Fuel Emissions')
            fuel_emission = fuel_emission_da.sum().item()
            st.metric("Fuel Total Emission", f"{fuel_emission:.2f} kgCO₂")
        if partial_load: 
            # Compute and display the Partial Load Indicators
            avg_load_factor, avg_efficiency = calculate_partial_load_indicators(model)

            st.markdown("**Generator Partial Load Indicators**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Average Generator Load Factor", f"{avg_load_factor:.2f} %")
            with col2:
                st.metric("Average Generator Efficiency", f"{avg_efficiency:.2f} kWh/liter")


    # Export results
    st.header("Export Results")
    st.write("Click the buttons below to export the full results to Excel or save the current plots.")
    export_results(project_name, model, costs_df, sizing_df, conversion_sizing_df, fig)

    st.write("---")  # Add a separator

    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Optimization"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Project Profitability"
            st.rerun()
