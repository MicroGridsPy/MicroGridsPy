"""
MicroGridsPy - Multi-year capacity-expansion (MYCE)

Linear Programming framework for microgrids least-cost sizing,
able to account for time-variable load demand evolution and capacity expansion.

Authors: 
    Alessandro Onori   - Department of Energy, Politecnico di Milano
    Giulia Guidicini   - Department of Energy, Politecnico di Milano 
    Lorenzo Rinaldi    - Department of Energy, Politecnico di Milano
    Nicolò Stevanato   - Department of Energy, Politecnico di Milano / Fondazione Eni Enrico Mattei
    Francesco Lombardi - Department of Energy, Politecnico di Milano
    Emanuela Colombo   - Department of Energy, Politecnico di Milano
    
Based on the original model by:
    Sergio Balderrama  - Department of Mechanical and Aerospace Engineering, University of Liège / San Simon University, Centro Universitario de Investigacion en Energia
    Sylvain Quoilin    - Department of Mechanical Engineering Technology, KU Leuven
"""


import re
import os
import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk
# from initial_page import InitialPage
from start_page import StartPage
from advanced_page import AdvancedPage
from recalculation_page import RECalculationPage
from archetypes_page import ArchetypesPage
from technologies_page import TechnologiesPage
from battery_page import BatteryPage
from generator_page import GeneratorPage
from grid_page import GridPage
from plot_page import PlotPage
from run_page import RunPage

class Application(ThemedTk):
        
    def __init__(self):
        ThemedTk.__init__(self, theme="plastick")
        style = ttk.Style()
        # Define the background color
        background_color = '#ffffff'
        # Configure styles for each widget type
        style.configure('TLabel', background=background_color)
        style.configure('TEntry', fieldbackground=background_color)
        style.configure('TButton', background=background_color)
        style.configure('TRadiobutton', background=background_color)
        style.configure('TCheckbutton', background=background_color)
        style.configure('TFrame', background=background_color)
        self.title("MicroGridsPy User Interface")  # Set the application title
        self.geometry("900x700")      # Set the default size of the application
        self.iconbitmap('Images/python_logo.ico')
        # Set the background color for the main window
        self.configure(background=background_color)

        # Container frame setup
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        # Set the background color for the container frame
        container.configure(background=background_color)
        
        # Initialize frames
        self.frames = {}
        for F in (StartPage, AdvancedPage, RECalculationPage, ArchetypesPage, TechnologiesPage, BatteryPage, GeneratorPage, GridPage, PlotPage, RunPage):
            frame = F(parent=container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("StartPage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        
    def show_RECalculationPage(self):
        self.show_frame("RECalculationPage")
        
    def show_ArchetypesPage(self):
        self.show_frame("ArchetypesPage")
        
    def show_TechnologiesPage(self):
        self.show_frame("TechnologiesPage")
        
    def get_model_components_value(self):
        # Return the value of Model_Components from StartPage
        return self.frames["StartPage"].Model_Components_var.get()

    def get_res_sources_value(self):
        return self.frames["TechnologiesPage"].RES_Sources_var.get()

    def get_generator_types_value(self):
        return self.frames["GeneratorPage"].Generator_Types_var.get()
    
    def get_grid_connection_value(self):
        return self.frames["AdvancedPage"].Grid_Connection_var.get()

    def get_grid_availability_value(self):
        return self.frames["AdvancedPage"].Grid_Availability_Simulation_var.get()
    
    def get_archetypes_value(self):
        return self.frames["ArchetypesPage"].demand_option_var.get()
    
    def get_res_calculation_value(self):
        return self.frames["RECalculationPage"].RE_Supply_Calculation_var.get()
    
    def get_milp_formulation_value(self):
        return self.frames["AdvancedPage"].MILP_Formulation_var.get()
    
    def get_brownfield_value(self):
        return self.frames["AdvancedPage"].Greenfield_Investment_var.get()
    
    def get_partial_load_value(self):
        return self.frames["AdvancedPage"].Generator_Partial_Load_var.get()
    
        
    def show_next_page(self):
        model_components = self.get_model_components_value()
        if model_components == 0:  # Both Battery and Generator
            self.show_frame("BatteryPage")
        elif model_components == 1:  # Only Battery
            self.show_frame("BatteryPage")
        elif model_components == 2:  # Only Generator
            self.show_frame("GeneratorPage")


    def show_GeneratorPage(self):
        model_components = self.get_model_components_value()
        grid_connection = self.get_grid_connection_value()
        if model_components == 0:  
            self.show_frame("GeneratorPage")
        elif grid_connection == 1:
            self.show_frame("GridPage")
        else: self.show_frame("PlotPage")
        
            
    def show_previous_page_from_battery(self):
        self.show_frame("TechnologiesPage")

    def show_previous_page_from_generator(self):
        model_components = self.get_model_components_value()
        if model_components == 0:  
            self.show_frame("BatteryPage")
        else:
            self.show_frame("TechnologiesPage")
            
    def show_previous_page_from_grid(self):
        model_components = self.get_model_components_value()
        if model_components == 0 or model_components == 2:  
            self.show_frame("GeneratorPage")
        else:
            self.show_frame("BatteryPage")
            
    def show_previous_page_from_plot(self):
        grid_connection = self.get_grid_connection_value()
        model_components = self.get_model_components_value()
        if grid_connection == 1:
            self.show_frame("GridPage")
        elif model_components == 0 or model_components == 2:
            self.show_frame("GeneratorPage")
        elif model_components == 1:
            self.show_frame("BatteryPage")
            
    def show_GridPage(self):
        grid_connection = self.get_grid_connection_value()
        grid_availability = self.get_grid_availability_value()
        if grid_connection == 1 and grid_availability == 1: 
           grid_page = self.frames.get("GridPage")
           grid_page.display_extra_parameters()
           self.show_frame("GridPage")
        elif grid_connection == 1 and grid_availability == 0: self.show_frame("GridPage")
        else: self.show_frame("PlotPage")
        
    def show_PlotPage(self):
        self.show_frame("PlotPage")
        
    def refresh_plot_page(self):
        # Retrieve the PlotPage instance and refresh it
        plot_page = self.frames["PlotPage"]
        plot_page.refresh_page()
        
    def save_all_data(self):
        grid_connection = int(self.get_grid_connection_value())
        model_components = int(self.get_model_components_value())
        demand_generation = int(self.get_archetypes_value())
        res_calculation = int(self.get_res_calculation_value())
        # Initialize the data dictionary
        startpage_data = {'StartPage': self.frames['StartPage'].get_input_data()}
        data = startpage_data
        advancedpage_data = {'AdvancedPage': self.frames['AdvancedPage'].get_input_data()}
        data.update(advancedpage_data)
        if model_components == 1:
            battery_data = {'BatteryPage' : self.frames['BatteryPage'].get_input_data()}
            data.update(battery_data)
        if grid_connection == 1: 
            grid_data = {'GridPage' : self.frames['GridPage'].get_input_data()}
            data.update(grid_data)
        if demand_generation == 1: 
            demand_data = {'ArchetypesPage' : self.frames['ArchetypesPage'].get_input_data()}
            data.update(demand_data)
        if res_calculation == 1:
            res_calculation_data = {'RECalculationPage' : self.frames['RECalculationPage'].get_input_data()}
            data.update(res_calculation_data)
            
        technologies_data = {'TechnologiesPage': self.frames['TechnologiesPage'].get_input_data()}
        data.update(technologies_data)

        if model_components == 0:
            generator_data = {'GeneratorPage' : self.frames['GeneratorPage'].get_input_data()}
            data.update(generator_data)
            battery_data = {'BatteryPage' : self.frames['BatteryPage'].get_input_data()}
            data.update(battery_data)
            
        if model_components == 2: 
            generator_data = {'GeneratorPage' : self.frames['GeneratorPage'].get_input_data()}
            data.update(generator_data)
            
        plot_data = {'PlotPage': self.frames['PlotPage'].get_input_data()}
        data.update(plot_data)
        self.write_to_dat_file(data)
        self.show_frame("RunPage")
                
    def write_to_dat_file(self, data):
     # Extract the inner dictionary of actual parameters to update
     parameters_to_update = {}
     
     current_directory = os.path.dirname(os.path.abspath(__file__))
     inputs_directory = os.path.join(current_directory, '..', 'Inputs')
     data_file_path = os.path.join(inputs_directory, 'Parameters.dat')
     
     for page_data in data.values():
        parameters_to_update.update(page_data)

     # Read the .dat file content
     with open('Parameters_prova.dat', 'r') as file:
        content = file.readlines()

     # Open the file in write mode to update the content
     with open(data_file_path, 'w') as file:
        in_multi_line_block = False
        for i, line in enumerate(content):
            if in_multi_line_block:
                # Check if we've reached the end of the multi-entry parameter block
                if line.strip() == ';':
                    in_multi_line_block = False
                    continue

            # Check if the line is the beginning of a multi-entry parameter block
            if re.match(r'\d+\s+.*;', line.strip()):
                in_multi_line_block = True
                continue

            match_single = re.match(r'(param: \S+ :=)([^;]*);', line)
            match_multi = re.match(r'(param:\s+)(\S+)(\s+:=)', line)

            if match_single:
                param_name = match_single.group(1).split()[1]
                if param_name in parameters_to_update:
                    new_value = parameters_to_update[param_name]
                    if param_name == 'time_zone':
                        updated_line = f"{match_single.group(1)} {new_value};\n"
                    else:
                        new_value_formatted = f"'{new_value}'" if isinstance(new_value, str) else new_value
                        updated_line = f"{match_single.group(1)} {new_value_formatted};\n"
                    file.write(updated_line)
                else:
                    file.write(line)

            elif match_multi:
                param_name = match_multi.group(2)
                if param_name in parameters_to_update:
                    new_values = parameters_to_update[param_name]
                    file.write(f"{match_multi.group(1)}{param_name}{match_multi.group(3)}\n")
                    for idx, val in enumerate(new_values, start=1):
                        val_formatted = f"'{val}'" if isinstance(val, str) else val
                        file.write(f"{idx}\t{val_formatted}\n")
                    file.write(";\n")
                    in_multi_line_block = True
                else:
                    file.write(line)
                    file.write(content[i + 1])

            else:
                file.write(line)  


if __name__ == "__main__":
    app = Application()
    app.mainloop()