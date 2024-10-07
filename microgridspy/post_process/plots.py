import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import Normalize

from microgridspy.model.model import Model
from microgridspy.post_process.cost_calculations import get_cost_details


def create_bar_of_pie_chart(model: Model, optimization_goal: str):
    cost_details = get_cost_details(model, optimization_goal)
    actualized = optimization_goal == "NPC"
    suffix = "(Actualized)" if actualized else "(Non-Actualized)"

    total_investment_cost = cost_details[f"Total Investment Cost {suffix}"]
    scenario_total_variable_cost = cost_details[f"Total Variable Cost {suffix}"]
    total_salvage_value = cost_details[f"Total Salvage Value {suffix}"]

    total_cost = total_investment_cost + scenario_total_variable_cost

    # Prepare data for pie chart
    pie_data = [
        ("Total Investment Cost", total_investment_cost, '#ff9999'),
        ("Total Variable Cost", scenario_total_variable_cost, '#66b3ff')]

    # Calculate percentages for pie chart
    labels, sizes, colors = zip(*[(label, (value / total_cost) * 100, color) for label, value, color in pie_data])

    # Prepare data for bar chart (same as before)
    variable_data = [
        ("Fixed O&M", cost_details[f"Total Fixed O&M Cost {suffix}"], '#ffcc99'),
        ("Battery Replacement", cost_details.get(f"Total Battery Replacement Cost {suffix}", 0), '#ff6666'),
        ("Fuel Cost", cost_details.get(f"Total Fuel Cost {suffix}", 0), '#c2c2f0'),
        ("Electricity Cost", cost_details.get(f"Total Electricity Purchased Cost {suffix}", 0), '#98FB98')
    ]

    variable_data = [(label, value, color) for label, value, color in variable_data if value > 0]
    variable_labels, variable_costs, variable_colors = zip(*variable_data) if variable_data else ([], [], [])
    variable_percentages = [cost / scenario_total_variable_cost * 100 for cost in variable_costs] if scenario_total_variable_cost > 0 else []

    # Create the figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={'width_ratios': [1.5, 1]})
    fig.suptitle(f"Cost Breakdown (%) - {optimization_goal}", fontsize=16)

    # Pie chart
    wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.axis('equal')

    # Add Salvage Value as text
    salvage_percentage = (total_salvage_value / total_cost) * 100
    ax1.text(0, -1.2, f"Salvage Value: {salvage_percentage:.1f}%", ha='center', va='center', fontweight='bold')

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
    For brownfield scenarios, existing capacities are included.
    Capacities are rounded to whole numbers.
    """
    num_steps = model.get_settings('num_steps', advanced=True)
    is_brownfield = model.get_settings('brownfield', advanced=True)
    
    # Get sizing data
    categories = []
    capacities = []
    existing_capacities = []
    colors = []
    capacity_units = []

    # Renewable sources and Generators (kW)
    components_kw = []
    res_units = model.get_solution_variable('Unit of Nominal Capacity for Renewables')
    if res_units is not None:
        res_nominal_capacity = model.parameters['RES_NOMINAL_CAPACITY']
        res_existing_capacity = model.parameters.get('RES_EXISTING_CAPACITY', 0)
        for source in res_units.renewable_sources.values:
            components_kw.append((source, res_units.sel(renewable_sources=source), 
                                  res_nominal_capacity.sel(renewable_sources=source),
                                  res_existing_capacity.sel(renewable_sources=source) if is_brownfield else 0))

    if model.has_generator:
        gen_units = model.get_solution_variable('Unit of Nominal Capacity for Generators')
        if gen_units is not None:
            gen_nominal_capacity = model.parameters['GENERATOR_NOMINAL_CAPACITY']
            gen_existing_capacity = model.parameters.get('GENERATOR_EXISTING_CAPACITY', 0)
            for gen_type in gen_units.generator_types.values:
                components_kw.append((gen_type, gen_units.sel(generator_types=gen_type), 
                                      gen_nominal_capacity.sel(generator_types=gen_type),
                                      gen_existing_capacity.sel(generator_types=gen_type)if is_brownfield else 0))

    for name, units, nominal_capacity, existing_capacity in components_kw:
        categories.append(name)
        capacities.append(np.round((units.values * nominal_capacity.values) / 1000))  # Rounded to whole numbers and converted to kW
        existing_capacities.append(np.round(existing_capacity))  # Rounded to whole numbers
        colors.append(color_dict.get(name))
        capacity_units.append('kW')

    # Battery (kWh)
    if model.has_battery:
        bat_units = model.get_solution_variable('Unit of Nominal Capacity for Batteries')
        if bat_units is not None:
            battery_nominal_capacity = model.parameters['BATTERY_NOMINAL_CAPACITY']
            battery_existing_capacity = model.parameters.get('BATTERY_EXISTING_CAPACITY', 0)
            categories.append("Battery Bank")
            capacities.append(np.round((bat_units.values * battery_nominal_capacity.values) / 1000))  # Rounded to whole numbers and converted to kWh
            existing_capacities.append(np.round(battery_existing_capacity))  # Rounded to whole numbers
            colors.append(color_dict.get('Battery'))
            capacity_units.append('kWh')

    # Convert capacities to numpy array for easier manipulation
    capacities = np.array(capacities)
    existing_capacities = np.array(existing_capacities)
    print("Existing Capacity to be plotted (array): ", existing_capacities)

    # Create plot with two y-axes
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()

    # Plot components in kW
    kw_mask = np.array(capacity_units) == 'kW'
    kw_categories = np.array(categories)[kw_mask]
    kw_capacities = capacities[kw_mask]
    kw_existing_capacities = existing_capacities[kw_mask]
    kw_colors = np.array(colors)[kw_mask]

    # Plot components in kWh
    kwh_mask = np.array(capacity_units) == 'kWh'
    kwh_categories = np.array(categories)[kwh_mask]
    kwh_capacities = capacities[kwh_mask]
    kwh_existing_capacities = existing_capacities[kwh_mask]
    kwh_colors = np.array(colors)[kwh_mask]

    def plot_bars(ax, categories, capacities, existing_capacities, colors, bottom=None):
        if is_brownfield:
            bars = ax.bar(categories, existing_capacities, color=colors, alpha=0.5, label='Existing')
            bottom = existing_capacities
        else:
            bottom = None
        
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

    kw_bars = plot_bars(ax1, kw_categories, kw_capacities, kw_existing_capacities, kw_colors)
    kwh_bars = plot_bars(ax2, kwh_categories, kwh_capacities, kwh_existing_capacities, kwh_colors)

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

    # Add legend if there are expansions or existing capacities
    if capacities.shape[1] > 1 or is_brownfield:
        ax1.legend(title='Capacity Breakdown')

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    return fig, categories, capacities, existing_capacities, capacity_units

def format_sizing_table(categories, capacities, existing_capacities, capacity_units):
    """Format sizing data into a presentable table with whole number capacities, including existing capacities for brownfield scenarios."""
    data = []
    for category, capacity, existing, unit in zip(categories, capacities, existing_capacities, capacity_units):
        row = [f"{category} ({unit})", f"{int(existing)}"]
        row.extend([f"{int(cap)}" for cap in capacity])  # Convert to integer
        data.append(row)
    
    columns = ['Component', 'Existing'] + [f'Step {i+1}' for i in range(capacities.shape[1])]
    df = pd.DataFrame(data, columns=columns)
    return df

def dispatch_plot(model: Model, scenario: int, year: int, day: int, color_dict: dict):
    """Plot the energy balance for a given day and year, including grid interactions and curtailment."""
    demand = model.parameters['DEMAND']
    res_production = model.get_solution_variable('Energy Production by Renewables')
    curtailment = model.get_solution_variable('Curtailment by Renewables')
    battery_inflow = model.get_solution_variable('Battery Inflow') if model.has_battery else None
    battery_outflow = model.get_solution_variable('Battery Outflow') if model.has_battery else None
    generator_production = model.get_solution_variable('Generator Energy Production') if model.has_generator else None
    energy_from_grid = model.get_solution_variable('Energy from Grid') if model.has_grid_connection else None
    energy_to_grid = model.get_solution_variable('Energy to Grid') if model.has_grid_connection and model.get_settings('grid_connection_type', advanced=True) == 1 else None
    lost_load = model.get_solution_variable('Lost Load') if model.get_settings('lost_load_fraction') > 0.0 else None

    start_idx = day * 24
    end_idx = (day + 1) * 24

    steps = model.sets['steps'].values
    years = model.sets['years'].values
    step_duration = model.settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    year_to_step = {year: step for year, step in years_steps_tuples}
    step = year_to_step[year]

    daily_demand = demand.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000
    daily_battery_inflow = battery_inflow.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if battery_inflow is not None else np.zeros_like(daily_demand)
    daily_battery_outflow = battery_outflow.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if battery_outflow is not None else np.zeros_like(daily_demand)
    daily_energy_from_grid = energy_from_grid.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if energy_from_grid is not None else np.zeros_like(daily_demand)
    daily_energy_to_grid = energy_to_grid.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if energy_to_grid is not None else np.zeros_like(daily_demand)
    daily_lost_load = lost_load.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if lost_load is not None else np.zeros_like(daily_demand)
    daily_total_curtailment = curtailment.sum('renewable_sources').isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if curtailment is not None else np.zeros_like(daily_demand)

    fig, ax = plt.subplots(figsize=(20, 12))

    x = range(24)
    cumulative_outflow = np.zeros(24)
    cumulative_inflow = np.zeros(24)

    # Plot actual renewable energy production for each source
    renewable_sources = model.sets['renewable_sources'].values
    for source in renewable_sources:
        daily_source_production = res_production.sel(renewable_sources=source, steps=step).isel(scenarios=scenario)[start_idx:end_idx] / 1000
        daily_source_curtailment = curtailment.sel(renewable_sources=source).isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if curtailment is not None else np.zeros_like(daily_demand)
        daily_actual_production = daily_source_production - daily_source_curtailment
        ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_actual_production, 
                        label=f'{source} Actual Production', color=color_dict.get(source), alpha=0.5)
        cumulative_outflow += daily_actual_production

    # Plot battery charging and discharging
    ax.fill_between(x, -cumulative_inflow, -(cumulative_inflow+daily_battery_inflow), label='Battery Charging', 
                    color=color_dict.get('Battery'), alpha=0.5)
    cumulative_inflow += daily_battery_inflow
    ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_battery_outflow, 
                    label='Battery Discharging', color=color_dict.get('Battery'), alpha=0.5)
    cumulative_outflow += daily_battery_outflow

    # Plot generator production for each type
    if generator_production is not None:
        generator_types = generator_production.coords['generator_types'].values
        for gen_type in generator_types:
            daily_gen_production = generator_production.sel(generator_types=gen_type).isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000
            ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_gen_production, 
                            label=f'{gen_type} Production', color=color_dict.get(gen_type), alpha=0.5)
            cumulative_outflow += daily_gen_production

    # Plot energy from grid
    if energy_from_grid is not None:
        ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_energy_from_grid, 
                        label='Energy from Grid', color=color_dict.get('Electricity Purchased'), alpha=0.5)
        cumulative_outflow += daily_energy_from_grid

    # Plot lost load
    if lost_load is not None:
        ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_lost_load, label='Lost Load', 
                        color=color_dict.get('Lost Load'), alpha=0.5)
        cumulative_outflow += daily_lost_load

    # Plot energy to grid (as negative values)
    if energy_to_grid is not None:
        ax.fill_between(x, -cumulative_inflow, -(cumulative_inflow+daily_energy_to_grid), label='Energy to Grid', 
                        color=color_dict.get('Electricity Sold'), alpha=0.5)
        cumulative_inflow += daily_energy_to_grid

    # Plot demand
    ax.plot(x, daily_demand, label='Demand', color=color_dict.get('Demand', 'black'), linewidth=2)

    # Plot curtailment on top of demand
    ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_total_curtailment, 
                    label='Curtailment', color=color_dict.get('Curtailment'), alpha=0.5)

    ax.set_xlabel('Hours')
    ax.set_ylabel('Energy (kWh)')
    ax.set_title(f'Energy Balance - Year {year + 1}, Day {day + 1}')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.grid(True)
    
    # Adjust y-axis to show negative values if energy is sold to the grid
    y_min = min(ax.get_ylim()[0], -daily_energy_to_grid.max() if energy_to_grid is not None else 0)
    y_max = max(ax.get_ylim()[1], (daily_demand + daily_total_curtailment).max())
    ax.set_ylim(bottom=y_min, top=y_max)

    return fig

def create_energy_usage_pie_chart(energy_usage: dict, model: Model, res_names, color_dict, gen_names=None):
    """Create a pie chart of energy usage percentages with a legend and external labels."""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Dynamically create color mapping and usage data
    color_mapping = {}
    usage_data = {}
    
    # Add renewable sources
    for res in res_names:
        color_mapping[f"{res} Usage"] = res
        usage_data[f"{res} Usage"] = energy_usage.get(f"{res} Usage", 0)

    # Add Battery
    if model.has_battery:
        color_mapping["Battery Usage"] = "Battery"
        usage_data["Battery Usage"] = energy_usage.get("Battery Usage", 0)
    
    # Add generators
    if model.has_generator:
        for gen in gen_names:
            color_mapping[f"{gen} Usage"] = gen
            usage_data[f"{gen} Usage"] = energy_usage.get(f"{gen} Usage", 0)

    if model.has_grid_connection:
        color_mapping["Grid Usage"] = "Electricity Purchased"
        usage_data["Grid Usage"] = energy_usage.get("Grid Usage", 0)

    # Remove zero values
    usage_data = {k: v for k, v in usage_data.items() if v > 0}
    
    # Get colors based on the mapping
    colors = [color_dict.get(color_mapping.get(k, k)) for k in usage_data.keys()]
    
    wedges, texts, autotexts = ax.pie(usage_data.values(), 
                                      colors=colors,
                                      autopct=lambda pct: f'{pct:.1f}%',
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
    """
    Create a heatmap visualization of time-series data for a specific year,
    showing only non-negative values.

    Parameters:
    - data: DataFrame containing time-series data
    - title: String for the chart title
    - year: Integer representing the year to visualize
    - color: String representing the color for the heatmap gradient

    Returns:
    - fig: Matplotlib figure object containing the heatmap
    """
    # Filter data for the specified year
    data_year = data[data.index.year == year]

    # Reshape data into a 2D array (366 days x 24 hours)
    data_2d = data_year.values.reshape(-1, 24)
    
    # Set negative values to 0
    data_2d = np.maximum(data_2d, 0)
    
    # Create a new figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Define a custom color gradient from white to the specified color
    colors = ["#FFFFFF", color]  # White to selected color
    cmap = LinearSegmentedColormap.from_list("custom_cmap", colors, N=100)
    
    # Find the maximum value for color scaling
    vmax = np.max(data_2d)
    
    # Create a normalization that starts from 0
    norm = Normalize(vmin=0, vmax=vmax)
    
    # Create the heatmap
    im = ax.imshow(data_2d, aspect='auto', cmap=cmap, norm=norm, extent=[0, 24, 366, 0])
    
    # Set title and axis labels
    ax.set_title(f"{title} - Year {year}")
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Day of Year')
    
    # Add a color bar to show the scale
    cbar = plt.colorbar(im)
    cbar.set_label(data.columns[0])
    
    # Set custom tick marks for x-axis (hours) and y-axis (days)
    ax.set_xticks(np.arange(0, 25, 4))
    ax.set_xticklabels(np.arange(0, 25, 4))
    ax.set_yticks(np.arange(0, 367, 30))
    ax.set_yticklabels(np.arange(0, 367, 30))
    
    plt.tight_layout()
    return fig