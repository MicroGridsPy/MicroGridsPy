import streamlit as st
import pandas as pd

from typing import Dict, Any, List

from microgridspy.model.model import Model
from config.path_manager import PathManager
from microgridspy.post_process.cost_calculations import calculate_actualized_investment_cost, calculate_actualized_salvage_value, calculate_lcoe, calculate_grid_costs
from microgridspy.post_process.energy_calculations import calculate_energy_usage, calculate_renewable_penetration
from microgridspy.post_process.data_retrieval import get_sizing_results, get_generator_usage, get_battery_soc, get_renewables_usage, get_grid_usage
from microgridspy.post_process.plots import(
    create_bar_of_pie_chart, 
    create_energy_usage_pie_chart, 
    create_heatmap, dispatch_plot, 
    create_sizing_plot, 
)
from microgridspy.post_process.export_results import save_results_to_excel, save_plots

def display_cost_breakdown(model: Model, optimization_goal: str):
    currency = st.session_state.get('currency', 'USD')
    actualized = optimization_goal == "NPC"
    
    cost_data: List[Dict[str, Any]] = []
    
    def add_cost_item(label: str, value: float, condition: bool = True):
        if condition:
            cost_data.append({
                "Cost Item": label,
                f"Value (k{currency})": f"{value / 1000:.2f}"
            })
    
    # Main cost (NPC or Total Variable Cost)
    if actualized:
        main_cost = model.get_solution_variable('Net Present Cost').values.item()
    else:
        main_cost = model.get_solution_variable('Total Variable Cost').values.item()
    
    # Display main metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric(optimization_goal, f"{main_cost / 1000:.2f} k{currency}")
    
    with col2:
        lcoe = calculate_lcoe(model, optimization_goal)
        lcoe_label = "Levelized Cost of Energy (LCOE)" if actualized else "Levelized Variable Cost (LVC)"
        st.metric(lcoe_label, f"{lcoe:.4f} {currency}/kWh")
    
    # Calculate and add cost items
    if actualized:
        add_cost_item("Total Investment Cost (Actualized)", 
                      model.get_solution_variable("Total Investment Cost").values.item())
    else:
        add_cost_item("Total Investment Cost (Actualized)", 
                      calculate_actualized_investment_cost(model) * 1000)
    
    add_cost_item(f"Total Variable Cost ({'Actualized' if actualized else 'Not Actualized'})", 
                  model.get_solution_variable(f"Scenario Total Variable Cost {'(Actualized)' if actualized else '(Not Actualized)'}").values.item())
    
    add_cost_item(f" - Total Fixed O&M Cost ({'Actualized' if actualized else 'Not Actualized'})", 
                  model.get_solution_variable(f"Operation and Maintenance Cost {'(Actualized)' if actualized else '(Not Actualized)'}").values.item())
    
    if model.has_battery:
        add_cost_item(f" - Total Battery Replacement Cost ({'Actualized' if actualized else 'Not Actualized'})", 
                    model.get_solution_variable(f"Battery Replacement Cost {'(Actualized)' if actualized else '(Not Actualized)'}").values.item(),
                    model.has_battery)
    
    if model.has_generator:
        add_cost_item(f" - Total Fuel Cost ({'Actualized' if actualized else 'Not Actualized'})", 
                    model.get_solution_variable(f"Total Fuel Cost {'(Actualized)' if actualized else '(Not Actualized)'}").values.item(),
                    model.has_generator)
    
    if actualized:
        add_cost_item("Total Salvage Value (Actualized)", 
                      model.get_solution_variable("Salvage Value").values.item())
    else:
        add_cost_item("Total Salvage Value (Actualized)", 
                      calculate_actualized_salvage_value(model) * 1000)
    
    if model.has_grid_connection:
        grid_investment_cost, grid_fixed_om_cost, cost_electricity_purchased, cost_electricity_sold = calculate_grid_costs(model, actualized)
        
        add_cost_item("Grid Investment Cost (Actualized)", grid_investment_cost)
        
        add_cost_item(f"Grid Fixed O&M Cost ({'Actualized' if actualized else 'Not Actualized'})", 
                      grid_fixed_om_cost)
        
        add_cost_item(f"Total Electricity Purchased Cost ({'Actualized' if actualized else 'Not Actualized'})", 
                      cost_electricity_purchased)
        
        if model.get_settings('grid_connection_type', advanced=True) == 1:
            add_cost_item(f"Total Electricity Sold Revenue ({'Actualized' if actualized else 'Not Actualized'})", 
                          cost_electricity_sold)
    
    # Display cost details
    st.subheader("Cost Details")
    cost_df = pd.DataFrame(cost_data)
    st.table(cost_df)

def plots_dashboard():
    """Create the results dashboard with cost breakdown, sizing results, and additional visualizations."""
    # Initialize dict to store plot figures
    fig: dict = {}

    st.title("Results Dashboard")

    if 'model' not in st.session_state:
        st.warning("Please run the optimization model first.")
        return
    else:
        # Get the results from the model
        model: Model = st.session_state.model

    # Define default colors
    DEFAULT_COLORS = {
        'Demand': '#000000',  # Black
        'Curtailment': '#FFA500',  # Orange
        'Battery': '#4CC9F0',  # Light Blue
        'Electricity Purchased': '#800080',  # Purple
        'Electricity Sold': '#008000',  # Green
        'Lost Load': '#F21B3F'  # Red
}

    # Add RES names to DEFAULT_COLORS
    for i, res_name in enumerate(model.sets['renewable_sources'].values):
        DEFAULT_COLORS[res_name] = ['#FFFF00', '#FFFFE0', '#FFFACD', '#FAFAD2'][i % 4]  # Shades of yellow

    if model.has_generator:
        # Add Generator names to DEFAULT_COLORS
        for i, gen_name in enumerate(model.sets['generator_types'].values):
            DEFAULT_COLORS[gen_name] = ['#00509D', '#0066CC', '#0077B6', '#0088A3'][i % 4]  # Shades of blue

    # Initialize color dictionary in session state if not present
    if 'color_dict' not in st.session_state:
        st.session_state.color_dict = DEFAULT_COLORS.copy()

    # Cost breakdown
    st.header("Cost Breakdown")
    # Optimization goal: NPC
    if model.get_settings('optimization_goal') == 0:
        display_cost_breakdown(model, 'NPC')
        # Create and display the bar of pie chart
        cost_breakdown_fig = create_bar_of_pie_chart(model, 'NPC')
        fig['Cost Breakdown Bar of Pie Chart'] = cost_breakdown_fig
        st.pyplot(cost_breakdown_fig)
    # Optimization goal: Total Variable Cost
    else:
        display_cost_breakdown(model, 'Total Variable Cost')
        # Create and display the bar of pie chart
        cost_breakdown_fig = create_bar_of_pie_chart(model, 'Total Variable Cost')
        fig['Cost Breakdown Bar of Pie Chart'] = cost_breakdown_fig
        st.pyplot(cost_breakdown_fig)

    st.write("---")  # Add a separator

    # Sizing and Dispatch
    st.header("Sizing and Dispatch")

    # Color customization section
    st.write("Customize colors for each technology: click on the color picker to change the color.")

    # Define all possible elements
    all_elements = ["Demand", "Curtailment"] + list(model.sets['renewable_sources'].values)

    # Add elements based on system configuration
    if model.has_battery:
        all_elements.append("Battery")
    if model.has_generator:
        all_elements.extend(list(model.sets['generator_types'].values))
    if model.has_grid_connection:
        all_elements.append("Electricity Purchased")
        if model.get_settings('grid_connection_type', advanced=True) == 1:
            all_elements.append("Electricity Sold")
    if model.get_settings('lost_load_fraction') > 0.0:
        all_elements.append("Lost Load")

    # Create color pickers
    cols = st.columns(len(all_elements))
    for element, col in zip(all_elements, cols):
        with col:
            default_color = st.session_state.color_dict.get(element, DEFAULT_COLORS.get(element))
            st.session_state.color_dict[element] = st.color_picker(
                element,
                key=f"color_{element}",
                value=default_color)


    # Sizing results
    st.header("Mini-Grid Sizing")
    
    # Create and display the sizing plot
    sizing_fig = create_sizing_plot(model, st.session_state.color_dict)
    fig['System Sizing'] = sizing_fig
    st.pyplot(sizing_fig)

    # Display sizing results in a formatted table
    sizing_df = get_sizing_results(model)
    st.table(sizing_df)

    # Create a dictionary of installed capacities
    installed_capacities = {cat: cap.sum() for cat, cap in zip(sizing_df['Component'], sizing_df.iloc[:, 2:].values)}

    st.write("---")  # Add a separator

    # Energy Balance Visualization
    st.header("Energy Usage Visualization")

    # Convert years to integers if they're not already
    years = [int(year) for year in model.sets['years']]
    min_year = min(years)
    max_year = max(years)

    # Energy Balance Visualization
    st.subheader("Dispatch Plot")

    selected_year = st.slider("Select Year for Dispatch Plot", 
                        min_value=min_year,
                        max_value=max_year,
                        value=min_year)
    selected_year_index = years.index(selected_year)
    selected_day = st.slider("Select Day", 0, 364, 0, key="day_slider")

    dispatch_fig = dispatch_plot(model, scenario=0, year=selected_year_index, day=selected_day, color_dict=st.session_state.color_dict)
    fig['Dispatch Plot'] = dispatch_fig
    st.pyplot(dispatch_fig)

    # Energy Usage and Curtailment
    st.subheader("Average Energy Usage")
    
    energy_usage = calculate_energy_usage(model)
    renewable_penetration = calculate_renewable_penetration(model)
    
    # Display Curtailment and Renewable Penetration as metrics side by side
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Curtailment", f"{energy_usage['Curtailment']:.2f}%")
    with col2:
        st.metric("Renewable Penetration", f"{renewable_penetration:.2f}%")
    
    # Create and display pie chart
    if model.has_generator:
        energy_usage_fig = create_energy_usage_pie_chart(energy_usage, model, st.session_state.res_names, st.session_state.color_dict, st.session_state.gen_names)
    else:
        energy_usage_fig = create_energy_usage_pie_chart(energy_usage, model, st.session_state.res_names, st.session_state.color_dict)
    fig['Energy Usage Pie Chart'] = energy_usage_fig
    st.pyplot(energy_usage_fig)

    if model.get_settings('lost_load_fraction') > 0.0:
        lost_load_percentage = energy_usage["Lost Load"]
        st.metric("Lost Load Fraction", f"{lost_load_percentage:.2f}%")

    st.write("---")  # Add a separator

    # Export results
    st.header("Export Results")
    st.write("Save results and plots within the results folder.")
    excel_filepath = PathManager.RESULTS_FOLDER_PATH
    plots_filepath = PathManager.RESULTS_FOLDER_PATH / "Plots"
    plots_filepath.mkdir(exist_ok=True)
    
    if st.button("Export Results"):
        with st.spinner("Exporting results..."):
            save_results_to_excel(model, excel_filepath)
        st.success(f"Results exported successfully to {excel_filepath}")

    if st.button("Save Plots"):
        with st.spinner("Saving current plots..."):
            save_plots(plots_filepath, fig)
        st.success(f"Plots saved successfully to {plots_filepath}")

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
