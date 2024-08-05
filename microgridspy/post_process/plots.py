import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from microgridspy.model.model import Model
from microgridspy.post_process.cost_calculations import calculate_actualized_investment_cost, calculate_actualized_salvage_value


def create_bar_of_pie_chart(model: Model, optimization_goal: str):
    """Create a 'bar of pie' chart showing cost breakdown percentages with variable costs exploded into a bar chart."""
    def get_cost(var_name: str):
        value = model.get_solution_variable(var_name)
        return value.values.item() / 1000 if value is not None else 0

    if optimization_goal == "NPC":
        total_investment_cost = get_cost("Total Investment Cost")
        scenario_total_variable_cost = get_cost("Scenario Total Variable Cost (Actualized)")
        total_fixed_operation_cost = get_cost("Operation and Maintenance Cost (Actualized)")
        total_battery_replacement_cost = get_cost("Battery Replacement Cost (Actualized)") if model.has_battery else 0
        total_fuel_cost = get_cost("Total Fuel Cost (Actualized)") if model.has_generator else 0
        total_salvage_value = get_cost("Salvage Value")
        
    elif optimization_goal == "Total Variable Cost":
        total_investment_cost = calculate_actualized_investment_cost(model)
        scenario_total_variable_cost = get_cost("Scenario Total Variable Cost (Non-Actualized)")
        total_fixed_operation_cost = get_cost("Operation and Maintenance Cost (Non-Actualized)")
        total_battery_replacement_cost = get_cost("Battery Replacement Cost (Not Actualized)") if model.has_battery else 0
        total_fuel_cost = get_cost("Total Fuel Cost (Non-Actualized)") if model.has_generator else 0
        total_salvage_value = calculate_actualized_salvage_value(model)

    # Calculate total cost and prepare data for pie chart
    total_cost = total_investment_cost + scenario_total_variable_cost - total_salvage_value
    pie_data = [
        ("Total Investment Cost", total_investment_cost, '#ff9999'),
        ("Total Variable Cost", scenario_total_variable_cost, '#66b3ff'),
        ("Salvage Value", -total_salvage_value, '#99ff99')]

    # Filter out zero or null values for pie chart
    pie_data = [(label, value, color) for label, value, color in pie_data if value != 0]
    
    # Calculate percentages for pie chart
    labels, sizes, colors = zip(*[(label, (value / total_cost) * 100, color) for label, value, color in pie_data])
    
    # Prepare data for bar chart
    variable_data = [
        ("Fixed O&M", total_fixed_operation_cost, '#ffcc99'),
        ("Battery Replacement", total_battery_replacement_cost, '#ff6666'),
        ("Fuel Cost", total_fuel_cost, '#c2c2f0')]
    
    # Filter out zero or null values for bar chart
    variable_data = [(label, value, color) for label, value, color in variable_data if value > 0]
    
    # Calculate percentages for bar chart
    variable_labels, variable_costs, variable_colors = zip(*variable_data) if variable_data else ([], [], [])
    variable_percentages = [cost / scenario_total_variable_cost * 100 for cost in variable_costs] if scenario_total_variable_cost > 0 else []

    # Create the figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={'width_ratios': [1.5, 1]})
    fig.suptitle(f"Cost Breakdown (%) - {optimization_goal}", fontsize=16)

    # Pie chart
    explode = [0.1 if label == "Total Variable Cost" else 0 for label in labels]
    wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', 
                                       startangle=90, explode=explode)
    ax1.axis('equal')

    # Bar chart for variable costs breakdown
    if variable_costs:
        y_pos = range(len(variable_labels))
        ax2.barh(y_pos, variable_percentages, align='center', color=variable_colors)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(variable_labels)
        ax2.invert_yaxis()  # Labels read top-to-bottom
        ax2.set_xlabel('Percentage (%)')
        ax2.set_title('Breakdown of Variable Costs')

        # Add percentage values to the end of each bar
        for i, v in enumerate(variable_percentages):
            ax2.text(v, i, f' {v:.1f}%', va='center')
    else:
        ax2.text(0.5, 0.5, "No variable costs", ha='center', va='center')
        ax2.axis('off')

    # Adjust layout
    plt.tight_layout()

    return fig

def create_sizing_plot(model: Model, color_dict: dict):
    """
    Create a plot to visualize the sizing of renewable sources, generators, and battery bank.
    Uses two y-axes for kW and kWh. If there's capacity expansion, it will show the additional capacity for each investment step.
    Capacities are rounded to whole numbers.
    """
    num_steps = model.get_settings('num_steps', advanced=True)
    
    # Get sizing data
    categories = []
    capacities = []
    colors = []
    capacity_units = []

    # Renewable sources and Generators (kW)
    components_kw = []
    if res_units := model.get_solution_variable('Unit of Nominal Capacity for Renewables'):
        res_nominal_capacity = model.parameters['RES_NOMINAL_CAPACITY']
        for source in res_units.renewable_sources.values:
            components_kw.append((source, res_units.sel(renewable_sources=source), 
                                  res_nominal_capacity.sel(renewable_sources=source)))

    if model.has_generator:
        if gen_units := model.get_solution_variable('Unit of Nominal Capacity for Generators'):
            gen_nominal_capacity = model.parameters['GENERATOR_NOMINAL_CAPACITY']
            for gen_type in gen_units.generator_types.values:
                components_kw.append((gen_type, gen_units.sel(generator_types=gen_type), 
                                      gen_nominal_capacity.sel(generator_types=gen_type)))

    for name, units, nominal_capacity in components_kw:
        categories.append(name)
        capacities.append(np.round((units.values * nominal_capacity.values) / 1000))  # Rounded to whole numbers
        colors.append(color_dict.get(name, '#CCCCCC'))
        capacity_units.append('kW')

    # Battery (kWh)
    if model.has_battery:
        if bat_units := model.get_solution_variable('Unit of Nominal Capacity for Batteries'):
            battery_nominal_capacity = model.parameters['BATTERY_NOMINAL_CAPACITY']
            categories.append("Battery Bank")
            capacities.append(np.round((bat_units.values * battery_nominal_capacity.values) / 1000))  # Rounded to whole numbers
            colors.append(color_dict.get('Battery', '#CCCCCC'))
            capacity_units.append('kWh')

    # Convert capacities to numpy array for easier manipulation
    capacities = np.array(capacities)

    # Create plot with two y-axes
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()

    # Plot components in kW
    kw_mask = np.array(capacity_units) == 'kW'
    kw_categories = np.array(categories)[kw_mask]
    kw_capacities = capacities[kw_mask]
    kw_colors = np.array(colors)[kw_mask]

    # Plot components in kWh
    kwh_mask = np.array(capacity_units) == 'kWh'
    kwh_categories = np.array(categories)[kwh_mask]
    kwh_capacities = capacities[kwh_mask]
    kwh_colors = np.array(colors)[kwh_mask]

    def plot_bars(ax, categories, capacities, colors, bottom=None):
        bars = ax.bar(categories, capacities[:, 0], color=colors, bottom=bottom)
        if capacities.shape[1] > 1:
            bottom = capacities[:, 0] if bottom is None else bottom + capacities[:, 0]
            for step in range(1, num_steps):
                if step < capacities.shape[1]:
                    expansion = capacities[:, step] - capacities[:, step-1]
                    ax.bar(categories, expansion, bottom=bottom, color=colors, alpha=0.5, 
                           label=f'Step {step+1}')
                    bottom += expansion
        return bars

    kw_bars = plot_bars(ax1, kw_categories, kw_capacities, kw_colors)
    kwh_bars = plot_bars(ax2, kwh_categories, kwh_capacities, kwh_colors)

    # Customize the plot
    ax1.set_ylabel('Capacity (kW)')
    ax2.set_ylabel('Capacity (kWh)')
    plt.title('System Sizing')

    # Add value labels on the bars
    def add_labels(ax, bars):
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',  # Display as integer
                    ha='center', va='bottom')

    add_labels(ax1, kw_bars)
    add_labels(ax2, kwh_bars)

    # Add legend if there are expansions
    if capacities.shape[1] > 1:
        ax1.legend(title='Expansion Steps')

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    return fig, categories, capacities, capacity_units

def format_sizing_table(categories, capacities, capacity_units):
    """Format sizing data into a presentable table with whole number capacities."""
    data = []
    for category, capacity, unit in zip(categories, capacities, capacity_units):
        row = [f"{category} ({unit})"]
        row.extend([f"{int(cap)}" for cap in capacity])  # Convert to integer
        data.append(row)
    
    columns = ['Component'] + [f'Step {i+1}' for i in range(capacities.shape[1])]
    df = pd.DataFrame(data, columns=columns)
    return df

def dispatch_plot(model: Model, scenario: int, year: int, day: int, color_dict: dict):
    """Plot the energy balance for a given day and year."""
    demand = model.parameters['DEMAND']
    res_production = model.get_solution_variable('Energy Production by Renewables')
    battery_inflow = model.get_solution_variable('Battery Inflow')
    battery_outflow = model.get_solution_variable('Battery Outflow')
    generator_production = model.get_solution_variable('Generator Energy Production')
    curtailment = model.get_solution_variable('Curtailment by Renewables')

    start_idx = day * 24
    end_idx = (day + 1) * 24

    steps = res_production.coords['steps'].values
    years = demand.coords['years'].values
    step_duration = model.settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    year_to_step = {year: step for year, step in years_steps_tuples}
    step = year_to_step[year]

    daily_demand = demand.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000
    daily_battery_inflow = battery_inflow.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if battery_inflow is not None else np.zeros_like(daily_demand)
    daily_battery_outflow = battery_outflow.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if battery_outflow is not None else np.zeros_like(daily_demand)
    daily_curtailment = curtailment.sum('renewable_sources').isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if curtailment is not None else np.zeros_like(daily_demand)

    fig, ax = plt.subplots(figsize=(20, 12))

    x = range(24)
    cumulative_production = np.zeros(24)

    # Plot renewable energy production for each source
    renewable_sources = res_production.coords['renewable_sources'].values
    for source in renewable_sources:
        daily_source_production = res_production.sel(renewable_sources=source, steps=step).isel(scenarios=scenario)[start_idx:end_idx] / 1000
        ax.fill_between(x, cumulative_production, cumulative_production + daily_source_production, 
                        label=f'{source} Production', color=color_dict.get(source, '#808080'), alpha=0.5)
        cumulative_production += daily_source_production

    # Plot curtailment
    ax.fill_between(x, cumulative_production, cumulative_production + daily_curtailment, 
                    label='Curtailment', color=color_dict.get('Curtailment', 'red'), alpha=0.5)

    # Plot battery charging and discharging
    ax.fill_between(x, 0, -daily_battery_inflow, label='Battery Charging', 
                    color=color_dict.get('Battery', 'lightblue'), alpha=0.5)
    ax.fill_between(x, cumulative_production, cumulative_production + daily_battery_outflow, 
                    label='Battery Discharging', color=color_dict.get('Battery', 'lightblue'), alpha=0.5)

    # Plot generator production for each type
    if generator_production is not None:
        generator_types = generator_production.coords['generator_types'].values
        for gen_type in generator_types:
            daily_gen_production = generator_production.sel(generator_types=gen_type).isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000
            ax.fill_between(x, cumulative_production + daily_battery_outflow, cumulative_production + daily_gen_production + daily_battery_outflow, 
                            label=f'{gen_type} Production', color=color_dict.get(gen_type, '#808080'), alpha=0.5)
            cumulative_production += daily_gen_production

    # Plot demand
    ax.plot(x, daily_demand, label='Demand', color=color_dict.get('Demand', 'black'), linewidth=2)

    ax.set_xlabel('Hours')
    ax.set_ylabel('Energy (kWh)')
    ax.set_title(f'Energy Balance - Year {year + 1}, Day {day + 1}')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.grid(True)
    
    return fig

def create_energy_usage_pie_chart(energy_usage, model, res_names, gen_names, color_dict):
    """Create a pie chart of energy usage percentages with a legend and external labels."""
    fig, ax = plt.subplots(figsize=(8, 6))  # Increased size slightly to accommodate external labels
    
    # Dynamically create color mapping and usage data
    color_mapping = {}
    usage_data = {}
    
    # Add renewable sources
    for res in res_names:
        color_mapping[f"{res} Usage"] = res
        usage_data[f"{res} Usage"] = energy_usage.get(f"{res} Usage", 0)
    
    # Add generators
    for gen in gen_names:
        color_mapping[f"{gen} Usage"] = gen
        usage_data[f"{gen} Usage"] = energy_usage.get(f"{gen} Usage", 0)
    
    # Add Battery
    if model.has_battery:
        color_mapping["Battery Usage"] = "Battery"
        usage_data["Battery Usage"] = energy_usage.get("Battery Usage", 0)
    
    # Remove zero values
    usage_data = {k: v for k, v in usage_data.items() if v > 0}
    
    # Get colors based on the mapping
    colors = [color_dict.get(color_mapping.get(k, k), '#808080') for k in usage_data.keys()]
    
    wedges, texts, autotexts = ax.pie(usage_data.values(), 
                                      colors=colors,
                                      autopct=lambda pct: f'{pct:.1f}%' if pct > 2 else '',
                                      pctdistance=0.8,
                                      wedgeprops=dict(width=0.5))
    
    # Add labels outside the pie chart
    ax.legend(wedges, usage_data.keys(),
              title="Energy Usage",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))
    
    ax.set_title('Average Energy Usage by Technology')
    
    # Remove bold formatting from percentage labels
    plt.setp(autotexts, weight="normal", size=8)
    
    plt.tight_layout()
    
    return fig

def create_heatmap(data, title, year, color):
    data_year = data[data.index.year == year]
    data_2d = data_year.values.reshape(-1, 24)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    colors = ["#FFFFFF", color]  # White to selected color
    cmap = LinearSegmentedColormap.from_list("custom_cmap", colors, N=100)
    
    im = ax.imshow(data_2d, aspect='auto', cmap=cmap, extent=[0, 24, 366, 0])
    ax.set_title(f"{title} - Year {year}")
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Day of Year')
    
    cbar = plt.colorbar(im)
    cbar.set_label(data.columns[0])
    
    ax.set_xticks(np.arange(0, 25, 4))
    ax.set_xticklabels(np.arange(0, 25, 4))
    ax.set_yticks(np.arange(0, 367, 30))
    ax.set_yticklabels(np.arange(0, 367, 30))
    
    plt.tight_layout()
    return fig