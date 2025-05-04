"""
This module provides the generator technology configuration page for the MicroGridsPy Streamlit application.
It allows users to define the parameters for different types of generators in their project.
Users can input specific parameters for each generator type, ensuring the configuration aligns with project settings.
"""
import os
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

from typing import Optional, Dict
from pathlib import Path

from config.path_manager import PathManager
from microgridspy.gui.utils import initialize_session_state,csv_upload_interface

def load_csv_data(uploaded_file, delimiter: str, decimal: str) -> Optional[pd.DataFrame]:
    """
    Load CSV data with given delimiter and decimal options.
    
    Args:
        uploaded_file: The uploaded CSV file.
        delimiter (str): The delimiter used in the CSV file.
        decimal (str): The decimal separator used in the CSV file.
    
    Returns:
        Optional[pd.DataFrame]: The loaded DataFrame or None if an error occurred.
    """
    try:
        data = pd.read_csv(uploaded_file, delimiter=delimiter, decimal=decimal)
        data = data.apply(pd.to_numeric, errors='coerce')
        
        if data.empty:
            st.warning("No data found in the CSV file. Please check delimiter and decimal settings.")
        elif data.isnull().values.any():
            st.warning("Some values could not be converted to numeric. Please check the data.")
        else:
            st.success(f"Data loaded successfully using delimiter '{delimiter}' and decimal '{decimal}'")
        
        return data
    except Exception as e:
        st.error(f"Error during import of CSV data: {e}")
        return None

    st.success(f"Resource data saved successfully for {resource_name} at {inputs_folder_path}.")


def ensure_list_length(key: str, length: int) -> None:
    """Ensure the list in session state has exactly the required length."""
    if key not in st.session_state:
        st.session_state[key] = [0.0] * length
    else:
        # Adjust list to match exactly the required length
        current = st.session_state[key]
        if len(current) < length:
            st.session_state[key].extend([0.0] * (length - len(current)))
        elif len(current) > length:
            st.session_state[key] = current[:length]  # Truncate to the required length

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

def load_fuel_cost_data(file_path, gen_name) -> pd.DataFrame:
    """Load existing fuel cost data from CSV file, creating missing columns if needed."""
    if os.path.exists(file_path):
        fuel_cost_file = pd.read_csv(file_path)

        # If the generator name is missing, create a new empty column
        if gen_name not in fuel_cost_file.columns:
            st.warning(f"Fuel cost data for '{gen_name}' not found. A new column will be created.")
            fuel_cost_file[gen_name] = 0.0  # Initialize with zeros

        return fuel_cost_file[["Year", gen_name]]
    
    else:
        st.warning(f"Fuel cost file not found at {file_path}. A new file will be created.")
        return pd.DataFrame(columns=["Year", gen_name])
    
def save_fuel_cost_data(file_path: Path, generator_fuel_costs: Dict[str, pd.Series], time_horizon: int) -> None:
    """
    Save or update the fuel cost data for multiple generators in a single CSV file.

    Args:
        file_path (Path): Path to the fuel cost CSV file.
        generator_fuel_costs (Dict[str, pd.Series]): Dictionary mapping generator names to their fuel cost Series.
        time_horizon (int): Number of years in the project.
    """
    if file_path.exists():
        fuel_cost_df = pd.read_csv(file_path)
        
        # If 'Year' column is missing or wrong, rebuild it
        if 'Year' not in fuel_cost_df.columns or len(fuel_cost_df['Year']) != time_horizon:
            st.warning(f"'Year' column missing or mismatched. Resetting it.")
            fuel_cost_df['Year'] = list(range(1, time_horizon + 1))
    else:
        # If file doesn't exist, create a new DataFrame
        st.info(f"Fuel cost file not found at {file_path}. A new one will be created.")
        fuel_cost_df = pd.DataFrame({'Year': list(range(1, time_horizon + 1))})

    # Update or add generator fuel cost columns
    for gen_name, cost_series in generator_fuel_costs.items():
        if gen_name in fuel_cost_df.columns:
            st.info(f"Updating fuel cost data for generator: {gen_name}")
        else:
            st.info(f"Adding new fuel cost data for generator: {gen_name}")
        
        # Assign the new or updated fuel cost series
        fuel_cost_df[gen_name] = cost_series.values

    # Save back to CSV
    fuel_cost_df.to_csv(file_path, index=False)
    st.success(f"Fuel cost data successfully saved to {file_path}")
    

def generator_technology() -> None:
    """Streamlit page for configuring generator technology parameters."""
    st.title("Generator Parameters")
    st.subheader("Define the parameters for the generator types in your project")
    st.write("""
    This page is dedicated to initializing parameters for backup systems within the project. 
    Here, you can configure the relevant settings and values associated with each technology (generators) used in the model.
    Below is a brief overview of the mathematical formulation of backup systems within MicroGridsPy:
    """)
    image_path = PathManager.IMAGES_PATH / "generator_math_formulation.PNG"
    st.image(str(image_path), use_container_width=True, caption="Overview of the main equations for generator")

    has_generator = st.session_state.get('system_configuration', 0) in [0, 2]

    if has_generator:
        initialize_session_state(st.session_state.default_values, "generator_params")
        currency = st.session_state.get('currency', 'USD')
        time_horizon = st.session_state.get('time_horizon', 0)
        brownfield = st.session_state.get('brownfield', False)
        unit_commitment = st.session_state.get('unit_commitment', False)

        st.session_state.gen_types = st.number_input(
            "Number of Generator Types", min_value=1, value=st.session_state.gen_types
        )

        keys = [
            'gen_names', 'gen_nominal_capacity', 'gen_nominal_efficiency',
            'gen_specific_investment_cost', 'gen_specific_om_cost', 'gen_lifetime',
            'gen_unit_co2_emission', 'gen_existing_capacity', 'gen_existing_years', 
            'fuel_names', 'fuel_lhv', 'fuel_co2_emission', 'max_fuel_consumption',
            'gen_rectifier_efficiency', 'gen_rectifier_nominal_capacity', 'gen_rectifier_cost',
            'gen_rectifier_lifetime', 'gen_existing_rectifier_capacity', 'gen_existing_rectifier_years'
        ]
        for key in keys:
            ensure_list_length(key, st.session_state.gen_types)

        fuel_cost_file_path = PathManager.FUEL_SPECIFIC_COST_FILE_PATH.parent / "Fuel Specific Cost.csv"

        st.header("Generator and Fuel Parameters")
        for i in range(st.session_state.gen_types):
            st.subheader(f"Generator Type {i+1}")
            st.session_state.gen_names[i] = st.text_input(
                f"Name for Generator Type {i+1}", value=st.session_state.gen_names[i]
            )
            gen_name = st.session_state.gen_names[i]

            if unit_commitment:
                st.session_state.gen_nominal_capacity[i] = st.number_input(
                    f"Nominal Capacity of {gen_name} [W]", value=st.session_state.gen_nominal_capacity[i]
                )

            if not st.session_state.partial_load:
                st.session_state.gen_nominal_efficiency[i] = st.number_input(
                    f"Nominal Efficiency of {gen_name} [%]",
                    min_value=0.0, max_value=100.0,
                    value=float(st.session_state.gen_nominal_efficiency[i] * 100),
                    step=0.1, format="%.1f"
                ) / 100

            if st.session_state.distribution_type == "Direct Current":
                st.session_state.gen_rectifier_efficiency[i] = st.number_input(
                    f"Rectifier Efficiency of {gen_name} [%]",
                    min_value=0.0, max_value=100.0,
                    value=float(st.session_state.gen_rectifier_efficiency[i] * 100),
                    format="%.1f"
                ) / 100
                st.session_state.gen_rectifier_nominal_capacity[i] = st.number_input(
                    f"Rectifier Nominal Capacity of {gen_name} [W]",
                    value=st.session_state.gen_rectifier_nominal_capacity[i]
                )
                st.session_state.gen_rectifier_lifetime[i] = st.number_input(
                    f"Rectifier Lifetime of {gen_name} [years]",
                    value=st.session_state.gen_rectifier_lifetime[i]
                )
                st.session_state.gen_rectifier_cost[i] = st.number_input(
                    f"Rectifier Cost of {gen_name} [{currency}/W]",
                    value=st.session_state.gen_rectifier_cost[i],
                    step=0.01
                )
            else:
                st.session_state.gen_rectifier_efficiency[i] = 1.0
                st.session_state.gen_rectifier_nominal_capacity[i] = 1.0
                st.session_state.gen_rectifier_cost[i] = 0.0

            st.session_state.gen_specific_investment_cost[i] = st.number_input(
                f"Specific Investment Cost of {gen_name} [{currency}/W]",
                value=st.session_state.gen_specific_investment_cost[i],
                step=0.01
            )

            st.session_state.gen_specific_om_cost[i] = st.number_input(
                f"Specific O&M Cost of {gen_name} [% of investment cost]",
                min_value=0.0, max_value=100.0,
                value=float(st.session_state.gen_specific_om_cost[i] * 100),
                step=0.1, format="%.1f"
            ) / 100

            if brownfield:
                st.session_state.gen_lifetime[i] = st.number_input(
                    f"Lifetime of {gen_name} [years]",
                    value=st.session_state.gen_lifetime[i]
                )
            else:
                st.session_state.gen_lifetime[i] = st.number_input(
                    f"Lifetime of {gen_name} [years]",
                    min_value=time_horizon,
                    value=max(st.session_state.gen_lifetime[i], time_horizon)
                )

            st.session_state.gen_unit_co2_emission[i] = st.number_input(
                f"Unit CO2 Emission of {gen_name} [kgCO2/kW]",
                value=st.session_state.gen_unit_co2_emission[i]
            )

            st.session_state.fuel_names[i] = st.text_input(
                f"Fuel Name for {gen_name}",
                value=st.session_state.fuel_names[i]
            )

            st.session_state.fuel_lhv[i] = st.number_input(
                f"Fuel LHV for {gen_name} [Wh/l]",
                value=st.session_state.fuel_lhv[i]
            )

            st.session_state.fuel_co2_emission[i] = st.number_input(
                f"Fuel CO2 Emission for {gen_name} [kgCO2/l]",
                value=st.session_state.fuel_co2_emission[i]
            )
            # Add a checkbox for maximum yearly fuel consumption
            st.session_state.fuel_cap[i] = st.checkbox(
                f"Limit the Yearly Fuel Consumption for {gen_name}",
                value=st.session_state.fuel_cap[i],
                help="Check this box if you want to set a maximum yearly fuel consumption for this generator.")
            
            if st.session_state.fuel_cap:
                st.session_state.max_fuel_consumption[i] = st.number_input(
                    f"Maximum Yearly Fuel Consumption for {gen_name} [l/year]",
                    value=st.session_state.max_fuel_consumption[i])

            if brownfield:
                st.write("##### Brownfield project parameters:")

                st.session_state.gen_existing_capacity[i] = st.number_input(
                    f"Existing Capacity of {gen_name} [W]",
                    value=st.session_state.gen_existing_capacity[i]
                )
                st.session_state.gen_existing_years[i] = st.number_input(
                    f"Existing Years of {gen_name} [years]",
                    value=st.session_state.gen_existing_years[i]
                )
                if st.session_state.distribution_type == "Direct Current":
                    st.session_state.gen_existing_rectifier_capacity[i] = st.number_input(
                        f"Existing Rectifier Capacity of {gen_name} [W]",
                        value=st.session_state.gen_existing_rectifier_capacity[i]
                    )
                    st.session_state.gen_existing_rectifier_years[i] = st.number_input(
                        f"Existing Rectifier Years of {gen_name} [years]",
                        value=st.session_state.gen_existing_rectifier_years[i]
                    )

            # --- Variable Fuel Cost Input ---
            st.subheader(f"Variable Fuel Cost for {gen_name}")
            fuel_cost_option = st.radio(
                f"Select fuel cost type for {gen_name}:",
                ["Fixed price", "Variable prices"],
                key=f"fuel_cost_option_{i}"
            )

            # Load existing file or create new
            existing_fuel_cost_data = load_fuel_cost_data(fuel_cost_file_path, gen_name)

            if fuel_cost_option == "Fixed price":
                fixed_price = st.number_input(
                    f"Fixed fuel price for {gen_name} [{currency}/l]",
                    min_value=0.0,
                    value=existing_fuel_cost_data[gen_name].iloc[0] if not existing_fuel_cost_data.empty else 0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"fixed_price_{i}"
                )

                fuel_cost_df = pd.DataFrame({
                    'Year': list(range(1, time_horizon + 1)),
                    gen_name: [fixed_price] * time_horizon
                })

            else:
                st.write(f"Please input the fuel specific cost for {gen_name} over the project timeline:")
                if existing_fuel_cost_data is not None:
                    fuel_cost_df = st.data_editor(
                        existing_fuel_cost_data,
                        num_rows="dynamic",
                        column_config={
                            "Year": st.column_config.NumberColumn("Year", min_value=1, max_value=time_horizon, step=1, disabled=True),
                            gen_name: st.column_config.NumberColumn(f"{gen_name} [{currency}/l]", min_value=0.0, format="%.2f")
                        },
                        hide_index=True
                    )
                else:
                    fuel_cost_df = manual_fuel_cost_input(time_horizon, [gen_name], currency)

                # --- Plot Fuel Cost Variation ---
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.plot(fuel_cost_df['Year'], fuel_cost_df[gen_name], marker='o', label=gen_name)
                ax.set_xlabel('Year')
                ax.set_ylabel(f'Fuel Cost [{currency}/l]')
                ax.set_title(f'Fuel Cost Variation Over Time for {gen_name}')
                ax.legend()
                ax.grid(True)
                st.pyplot(fig)

            # Save the edited fuel cost DataFrame temporarily
            st.session_state[f"fuel_cost_df_{gen_name}"] = fuel_cost_df

            if st.button(f"Save Fuel Cost Data for {gen_name}"):
                # Save just the current generator data
                generator_fuel_costs = {gen_name: fuel_cost_df[gen_name]}
                save_fuel_cost_data(
                    file_path=fuel_cost_file_path,
                    generator_fuel_costs=generator_fuel_costs,
                    time_horizon=time_horizon
                )

            st.markdown("---")
        
        # Partial Load Modeling
        st.subheader(f"Partial Load Modeling")
        st.session_state.partial_load = st.checkbox(
            "Enable Partial Load effect for generators", 
            value=st.session_state.partial_load,
            help="Enable a more realistic modeling of generator operation by considering partial load effects due to decreasing efficiency at lower loads.")
        
        if st.session_state.partial_load:
            st.markdown("**Generators Efficiency Curve**")

            st.markdown("""
            **Instructions:**
            - Upload a CSV file:
            - First column = Relative Power Output [%] (common for all gens).
            - Next columns = Efficiency curves [%] for each generator type.
            - Number of columns = 1 + number of generator types.
            - Define the number of sampling points.
            - Select which generator efficiency curve to visualize.
            """)

            # Upload CSV
            uploaded_file, delimiter, decimal = csv_upload_interface("gen_efficiency_curves_all")
            if uploaded_file:
                gen_efficiency_data = load_csv_data(uploaded_file, delimiter, decimal)
                if gen_efficiency_data is not None:
                    expected_cols = 1 + st.session_state.gen_types
                    if gen_efficiency_data.shape[1] != expected_cols:
                        st.error(f"Uploaded CSV should have {expected_cols} columns (1 for Relative Output + {st.session_state.gen_types} generator types).")
                    else:
                        st.success(f"Generator efficiency curves loaded correctly with {expected_cols} columns.")
                        st.dataframe(gen_efficiency_data.head(10))

                        # Set column names
                        gen_efficiency_data.columns = ["Relative_Output_Percent"] + [f"{name}" for name in st.session_state.gen_names]

                        # Number of Sampling Points (Shared for all)
                        n_samples = st.number_input(
                            "Number of Sampling Points (shared for all generators)", 
                            min_value=2, max_value=50, value=10
                        )

                        # Normalize Relative Output (common x-axis)
                        relative_output = gen_efficiency_data["Relative_Output_Percent"].values / 100

                        # Initialize lists to hold sampled data for all generators
                        sampled_relative_output_list = []
                        sampled_efficiency_list = []

                        # --- Sample ALL Generators ---
                        for gen_name in st.session_state.gen_names:
                            # Efficiency for this generator
                            efficiency = gen_efficiency_data[gen_name].values / 100
                            st.session_state.gen_nominal_efficiency[i] = float(efficiency[-1]) # Update nominal efficiency

                            # Interpolate
                            interpolation = interp1d(relative_output, efficiency, kind='linear', fill_value="extrapolate")

                            # Generate Sampling Points
                            sampled_relative_output = np.linspace(0, 1, n_samples)
                            sampled_efficiency = interpolation(sampled_relative_output)

                            # Remove Points where Efficiency == 0 (to avoid division issues)
                            valid_indices = sampled_efficiency > 0
                            sampled_relative_output = sampled_relative_output[valid_indices]
                            sampled_efficiency = sampled_efficiency[valid_indices]

                            # Save for this generator
                            sampled_relative_output_list.append(sampled_relative_output.tolist())
                            sampled_efficiency_list.append(sampled_efficiency.tolist())

                        # --- Save sampled data to session_state ---
                        st.session_state['gen_sampled_relative_output'] = sampled_relative_output_list
                        st.session_state['gen_sampled_efficiency'] = sampled_efficiency_list

                        # --- Visualization ---
                        selected_gen_name = st.selectbox(
                            "Select Generator Type to Visualize", 
                            options=st.session_state.gen_names
                        )

                        # Index of the selected generator
                        selected_gen_idx = st.session_state.gen_names.index(selected_gen_name)

                        # Get sampled points for selected generator
                        plot_sampled_relative_output = np.array(sampled_relative_output_list[selected_gen_idx])
                        plot_sampled_efficiency = np.array(sampled_efficiency_list[selected_gen_idx])

                        # Get original curve for selected generator
                        original_efficiency = gen_efficiency_data[selected_gen_name].values / 100

                        # --- Plotting ---
                        fig, ax = plt.subplots(figsize=(8, 5))

                        # Plot original curve
                        ax.plot(relative_output * 100, original_efficiency * 100, label="Original Efficiency Curve", linestyle='dashed')

                        # Plot sampled points
                        ax.scatter(plot_sampled_relative_output * 100, plot_sampled_efficiency * 100, color='red', label="Sampled Points")

                        # Plot piecewise linear segments
                        for i in range(len(plot_sampled_relative_output) - 1):
                            x_seg = [plot_sampled_relative_output[i] * 100, plot_sampled_relative_output[i+1] * 100]
                            y_seg = [plot_sampled_efficiency[i] * 100, plot_sampled_efficiency[i+1] * 100]
                            ax.plot(x_seg, y_seg, color='green')

                        ax.set_xlabel("Relative Power Output (%)")
                        ax.set_ylabel("Efficiency (%)")
                        ax.set_title(f"Efficiency Curve and Piecewise Approximation for {selected_gen_name}")
                        ax.grid(True)
                        ax.legend()

                        st.pyplot(fig)
                        st.write("Nominal Efficiency in Full Load:", st.session_state.gen_nominal_efficiency[selected_gen_idx] * 100, "%")
                        st.markdown("---") 

    else:
        st.warning("Generator technology is not included in the system configuration.")

    # Navigation Buttons
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Battery Characterization"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Grid Connection"
            st.rerun()
