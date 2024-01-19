import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
from tkinter import messagebox
from PIL import Image, ImageTk

class TopSectionFrame(tk.Frame):
    def __init__(self, parent, university_name, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.configure(background='#0f2c53')
        self.parent = parent  # Keep a reference to the parent

        # University Name
        self.name_label = tk.Label(self, text=university_name, font=("Arial", 10, "italic"), fg="white", background='#0f2c53')
        self.name_label.grid(row=0, column=2, pady=15, sticky='e')

        # Configure grid column weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)

    def expand_across_parent(self):
        total_columns = self.parent.grid_size()[0]
        self.grid(row=0, column=0, sticky='ew', columnspan=total_columns)

class NavigationFrame(tk.Frame):
    def __init__(self, parent, back_command, next_command, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        parent_row_index = 35

        # Span across all columns of the parent.
        self.grid(row=parent_row_index, column=0, sticky='ew', columnspan=parent.grid_size()[0])

        # Configure the background color to match the TopSectionFrame
        self.configure(background='#0f2c53', highlightbackground='#0f2c53', highlightthickness=2)

        # Grid configuration for the buttons within the NavigationFrame
        self.next_button = ttk.Button(self, text="Next", command=next_command)
        self.next_button.grid(row=0, column=2, sticky='e', padx=10, pady=10)
        
        # Grid configuration for the buttons within the NavigationFrame
        self.back_button = ttk.Button(self, text="Back", command=back_command)
        self.back_button.grid(row=0, column=0, sticky='w', padx=10, pady=10)

        # Configure the grid within NavigationFrame to align the buttons properly
        self.grid_columnconfigure(0, weight=1)  # The column for the back button, if used
        self.grid_columnconfigure(1, weight=0)  # The column for the next button
        self.grid_columnconfigure(2, weight=1)

class ToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def show_tip(self):
        "Display text in tooltip window"
        self.x, self.y, cx, cy = self.widget.bbox("insert")
        self.x += self.widget.winfo_rootx() + 25
        self.y += self.widget.winfo_rooty() + 20

        # Creates a toplevel window
        self.tipwindow = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tipwindow.wm_overrideredirect(True)
        self.tipwindow.wm_geometry("+%d+%d" % (self.x, self.y))

        label = tk.Label(self.tipwindow, text=self.text, justify=tk.LEFT,
                      background="#ffffff", relief=tk.SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self):
        if self.tipwindow:
            self.tipwindow.destroy()
        self.tipwindow = None
        
def create_tooltip(widget, text):
        tool_tip = ToolTip(widget, text)
        widget.bind('<Enter>', lambda event: tool_tip.show_tip())
        widget.bind('<Leave>', lambda event: tool_tip.hide_tip())

class GeneratorPage(tk.Frame):

        
    def setup_warning(self):
        # Load the warning icon image
        warning_icon = Image.open('Images/attention.png')  # Replace with your image's path
        warning_icon = warning_icon.resize((24, 24), Image.Resampling.LANCZOS)
        self.warning_icon_image = ImageTk.PhotoImage(warning_icon)

        # Determine the row index for the warning, which should be after all main content
        warning_row_index = self.inner_frame.grid_size()[1]  # Get the total number of rows used in inner_frame

        # Create a frame for the warning
        warning_frame = ttk.Frame(self.inner_frame, borderwidth=1, relief="solid")
        warning_frame.grid(row=warning_row_index, column=0, columnspan=4, padx=10, pady=10, sticky="ew")

        # Create the icon label and place it on the left
        icon_label = ttk.Label(warning_frame, image=self.warning_icon_image)
        icon_label.grid(row=0, column=0, padx=(10, 0), pady=10, sticky="w")

        # Create the warning label with text
        self.warning_label = ttk.Label(warning_frame, text="WARNING: If Fuel Specific Cost Import is activated, you must provide the fuel cost values in a CSV file located in 'Inputs' folder (refer to the online documentation for more details https://microgridspy-documentation.readthedocs.io/en/latest/)",  wraplength=700, justify="left")
        self.warning_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Ensure the text spans the rest of the grid
        warning_frame.grid_columnconfigure(1, weight=1)

    def validate_integer(self, P):
        if P == "": return True
        if P.isdigit():
            return True
        else:
            self.bell()  # System bell if invalid input
            return False
        
    def validate_float(self, P):
        if P == "": return True
        try: 
            value = float(P)
            if value >= 0 : return True
            else: return False
        except ValueError:
            self.bell()  # System bell if invalid input
            return False
        
    def validate_fraction(self, P):
        if P == "": return True
        try: 
            value = float(P)
            if value <= 1 : return True
            else: 
                self.bell()
                return False
        except ValueError:
            self.bell()  # System bell if invalid input
            return False

    def get_validation_command(self, param, default):
        fraction_params = {"Generator_Efficiency", "Generator_Specific_OM_Cost", "Generator_Min_output", "Generator_pgen","Fuel_Specific_Cost_Rate"}
        if param in fraction_params:
            return (self.register(self.validate_fraction), '%P')
        elif isinstance(default, int):
            return (self.register(self.validate_integer), '%P')
        elif isinstance(default, float):
            return (self.register(self.validate_float), '%P')
        return None

    def update_gen_configuration(self):
     # First, clear all existing entries.
     self.clear_gen_entries()
     self.clear_fuel_entries()

     # Get the number of generator sources to configure
     try: 
        gen_sources = int(self.Generator_Types_entry.get())
     except: gen_sources = 1

     # Reset the gen_entries list
     self.gen_entries = []
     self.fuel_entries = []

     text_parameters = ['Generator_Names', 'Fuel_Names']

     # Start adding new entries from the fourth row
     row_start_gen = 5

     for param, default in self.gen_params_defaults.items():
        for i in range(gen_sources):
            # Calculate the row for the current parameter
            row = row_start_gen + list(self.gen_params_defaults.keys()).index(param)
            vcmd = self.get_validation_command(param, default)
            
            initial_label_state = self.initial_states[param]['label']
            initial_entry_state = self.initial_states[param]['entry']

            # Check if it's a text parameter and set the appropriate variable type
            if param in text_parameters:
                temp_var = tk.StringVar(value=default)
            else:
                temp_var = tk.DoubleVar(value=default)

            # Create the label only for the first column
            if i == 0:
                label = ttk.Label(self.inner_frame, text=param)
                label.grid(row=row, column=0, sticky='w')
                label.config(state=initial_label_state)
            else:
                label = None

            # Create the entry
            entry = ttk.Entry(self.inner_frame, textvariable=temp_var, validate='key', validatecommand=vcmd)
            entry.grid(row=row, column=1 + i, sticky='w')
            entry.config(state=initial_entry_state)
            
            # Add tooltip for the entry
            tooltip_text = self.gen_params_tooltips.get(param, "Info not available")
            create_tooltip(entry, tooltip_text)

            # Append the new entry to gen_entries
            self.gen_entries.append((temp_var, label, entry))
            
     row_start_fuel = 23
            
     for param, default in self.fuel_params_defaults.items():
        for i in range(gen_sources):
            # Calculate the row for the current parameter
            row = row_start_fuel + list(self.fuel_params_defaults.keys()).index(param)
            vcmd = self.get_validation_command(param, default)
            
            initial_label_state = self.initial_states[param]['label']
            initial_entry_state = self.initial_states[param]['entry']

            # Check if it's a text parameter and set the appropriate variable type
            if param in text_parameters:
                temp_var = tk.StringVar(value=default)
            else:
                temp_var = tk.DoubleVar(value=default)
                
            label = ttk.Label(self.inner_frame, text=param)

            # Place the label only for the first column
            if i == 0:
                label.grid(row=row, column=0, sticky='w')
                label.config(state=initial_label_state)
            else:
                label = None

            # Create the entry
            entry = ttk.Entry(self.inner_frame, textvariable=temp_var, validate='key', validatecommand=vcmd)
            entry.grid(row=row, column=1 + i, sticky='w')
            entry.config(state=initial_entry_state)

            # Append the new entry to gen_entries
            self.fuel_entries.append((temp_var, label, entry))
        


    def clear_gen_entries(self):
     for var, label, entry in self.gen_entries:
        if label: 
            label.destroy()
        entry.destroy()
        
    def clear_fuel_entries(self):
     for var, label, entry in self.fuel_entries:
        if label: 
            label.destroy()
        entry.destroy()

            
    def get_input_data(self):
     gen_data = {'Generator_Types': self.Generator_Types_var.get()}
     num_gen_types = int(self.Generator_Types_var.get())

     # Initialize a dictionary to store the values for each parameter
     param_values = {param: [] for param in self.gen_params_defaults}

     # Iterate over the entries and aggregate values by parameter
     for var, label, entry in self.gen_entries:
        if label:
            param = label.cget('text')
            # Reset the current list for this parameter if we're on the first generator type
            if len(param_values[param]) >= num_gen_types:
                param_values[param] = [var.get()]
            else:
                param_values[param].append(var.get())
        else:
            # Find the parameter this value belongs to by matching the variable in param_values
            for key, values in param_values.items():
                if len(values) < num_gen_types:
                    param_values[key].append(var.get())
                    break

     for param, values in param_values.items():
         gen_data[param] = values
         
     gen_data['Fuel_Specific_Cost_Import'] = self.Fuel_Specific_Cost_Import_var.get()
     
     # Initialize a dictionary to store the values for each parameter
     param_values = {param: [] for param in self.fuel_params_defaults}

     # Iterate over the entries and aggregate values by parameter
     for var, label, entry in self.fuel_entries:
        if label:
            param = label.cget('text')
            # Reset the current list for this parameter if we're on the first generator type
            if len(param_values[param]) >= num_gen_types:
                param_values[param] = [var.get()]
            else:
                param_values[param].append(var.get())
        else:
            # Find the parameter this value belongs to by matching the variable in param_values
            for key, values in param_values.items():
                if len(values) < num_gen_types:
                    param_values[key].append(var.get())
                    break

     for param, values in param_values.items():
         gen_data[param] = values

     return gen_data
            
    def on_confirm_gen(self):
            self.controller.refresh_plot_page()
            
    def on_confirm_and_next(self):
     all_filled = True
     for var, label, entry in self.gen_entries:
         try : value = str(entry.get())
         except: value = ''
         if not str(value).strip():  
            # Use the label's text to show which field needs to be filled
            messagebox.showwarning("Warning", f"Please fill in the required field for {label.cget('text') if label else 'unknown parameter'}.")
            entry.focus_set()  # Set focus to the empty entry
            all_filled = False
            break
        
     for var, label, entry in self.fuel_entries:
         try : value = str(entry.get())
         except: value = ''
         if not str(value).strip():  
            # Use the label's text to show which field needs to be filled
            messagebox.showwarning("Warning", f"Please fill in the required field for {label.cget('text') if label else 'unknown parameter'}.")
            entry.focus_set()  # Set focus to the empty entry
            all_filled = False
            break

     if not all_filled:
        return

     # If all fields are filled, proceed to gather the input data and go to the next page
     self.get_input_data()
     self.on_confirm_gen()
     self.controller.show_GridPage()
     
    def toggle_fuel_specific_cost(self):
        # Check if the checkbutton is checked or not
        is_checked = self.Fuel_Specific_Cost_Import_var.get() == 1

        # Determine the new state based on whether the checkbox is checked
        new_state = 'disabled' if is_checked else 'normal'

        # Define the fuel parameters to be toggled
        toggle_params = ['Fuel_Specific_Start_Cost', 'Fuel_Specific_Cost_Rate']

        # Iterate over all fuel entries
        num_gen_types = int(self.Generator_Types_var.get())
        for i in range(num_gen_types):
         for var, label, entry in self.fuel_entries:
            # Check if the label's text matches one of the parameters to be toggled
            if label and label.cget('text') in toggle_params:
                label.config(state=new_state)
                entry.config(state=new_state)

                # Update the stored initial state for the parameter
                self.initial_states[label.cget('text')] = {'label': new_state, 'entry': new_state}
               
    def toggle_milp_parameters(self):
        for (var, label, entry) in self.gen_entries:
            if label.cget('text') in self.milp_parameters:
               label.config(state='normal')  
               entry.config(state='normal')
               
    def toggle_fuel_cost_parameters(self):
        self.Fuel_Specific_Cost_Import_label.config(state='normal')
        self.Fuel_Specific_Cost_Import_checkbutton.config(state='normal')
        for (var, label, entry) in self.fuel_entries:
            if label.cget('text') == 'Fuel_Specific_Cost_Rate':
               label.config(state='normal')  
               entry.config(state='normal')
               
    def toggle_brownfield_parameters(self):
        for (var, label, entry) in self.gen_entries:
            if label.cget('text') in self.brownfield_parameters:
               label.config(state='normal')  
               entry.config(state='normal')
               
    def toggle_milp_partial_parameters(self):
        for (var, label, entry) in self.gen_entries:
            if label.cget('text') in self.milp_partial_parameters:
               label.config(state='normal')  
               entry.config(state='normal')
               
    def setup_scrollable_area(self):
        # Create the main container frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create a canvas within the main container
        self.canvas = tk.Canvas(self.main_frame)
        self.canvas.grid(row=0, column=0, sticky='nsew')

        # Configure main_frame grid to expand the canvas
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Add vertical and horizontal scrollbars to the canvas
        self.v_scrollbar = ttk.Scrollbar(self.main_frame, orient='vertical', command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky='ns')
        self.h_scrollbar = ttk.Scrollbar(self.main_frame, orient='horizontal', command=self.canvas.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky='ew')

        # Configure the canvas scrolling
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Create the frame that will hold the content inside the canvas
        self.inner_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw', width=self.canvas.winfo_reqwidth(), height=self.canvas.winfo_reqheight())

        # Bind the canvas to update the inner_frame size when the canvas size changes
        self.canvas.bind('<Configure>', self.on_canvas_configure)

    def on_canvas_configure(self, event):
        # The canvas width and height come from the event
        canvas_width = event.width
        canvas_height = event.height
    
        # Get the required width and height of the inner_frame
        frame_width = self.inner_frame.winfo_reqwidth()
        frame_height = self.inner_frame.winfo_reqheight()
    
        # If the inner frame is smaller than the canvas, we need to set its width
        # to the canvas width so it fills it when not scrolling
        new_width = max(canvas_width, frame_width)
        new_height = max(canvas_height, frame_height)  # This might be needed if you have horizontal scrolling
    
        # Configure the canvas window to be the size we've determined is necessary
        self.canvas.itemconfig(self.canvas_window, width=new_width, height=new_height)
    
        # Set the scrollregion to encompass the size of the inner frame
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

                
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        
        # Configure the grid layout of the parent frame
        self.grid_rowconfigure(0, weight=0)  # Top section should not expand
        self.grid_rowconfigure(1, weight=1)  # Scrollable section should expand
        self.grid_rowconfigure(2, weight=0)  # Bottom section should not expand
        self.grid_columnconfigure(0, weight=1)

        # Add Top Section
        university_name = "MicroGridsPy"
        self.top_section = TopSectionFrame(self, university_name)
        self.top_section.grid(row=0, column=0, sticky='ew', columnspan=self.grid_size()[0])

        # Setup the scrollable area
        self.setup_scrollable_area()

        # Add NavigationFrame at the very bottom
        self.nav_frame = NavigationFrame(self, back_command=controller.show_previous_page_from_generator, next_command=self.on_confirm_and_next)
        self.nav_frame.grid(row=2, column=0, sticky='ew', columnspan=self.grid_size()[0])
        
        self.gen_params_defaults = {
            "Generator_Names": "Diesel Genset 1",
            "Generator_Efficiency": 0.3,
            "Generator_Specific_Investment_Cost": 0.4,
            "Generator_Specific_OM_Cost": 0.08,
            "Generator_Lifetime": 20,
            "GEN_unit_CO2_emission": 0.0,
            "Generator_capacity": 0.0,
            "GEN_years": 0,
            "Generator_Nominal_Capacity_milp": 5000,
            "Generator_Min_output": 0.3,
            "Generator_pgen": 0.01
            }
        
        self.fuel_params_defaults = {
            "Fuel_Names": "Diesel",
            "Fuel_LHV": 10140.0,
            "FUEL_unit_CO2_emission": 2.68,
            "Fuel_Specific_Start_Cost": 1.17,
            "Fuel_Specific_Cost_Rate": 0.0
            }
        
        self.gen_params_tooltips = {
            "Generator_Efficiency": "Average generator efficiency of each generator type [%]",
            "Generator_Specific_Investment_Cost": "Specific investment cost for each generator type [USD/W]",
            "Generator_Specific_OM_Cost": "O&M cost for each generator type as a fraction of specific investment cost [%]",
            "Generator_Lifetime": "Generator Lifetime [years]",
            "GEN_unit_CO2_emission": "Specific CO2 emissions associated to each generator type[kgCO2/kW]",
            "Generator_capacity": "Existing Generator capacity [W]",
            "GEN_years": "How many years ago the component was installed [years]",
            "Generator_Nominal_Capacity_milp": "Nominal capacity of each generator [W]",
            "Generator_Min_output":"Minimum percentage of energy output for the generator in part load [%]",
            "Generator_pgen":"Percentage of the total operation cost of the generator system at full load [%]"
        }
        
        self.fuel_params_tooltips = {
            "Fuel_Names": "Fuel names (to be specified for each generator, even if they use the same fuel)",
            "Fuel_LHV": "Fuel lower heating value (LHV) for each generator type [Wh/lt]",
            "FUEL_unit_CO2_emission": "Specific CO2 emissions associated to the fuel [kgCO2/lt]",
            "Fuel_Specific_Start_Cost": "Initial fuel specific cost [USD/Wh] at year 1",
            "Fuel_Specific_Cost_Rate": "Change rate in fuel specific cost [% per year]"
        }
        
        text_parameters = ['Generator_Names', 'Fuel_Names']
        self.fuel_parameters = ['Fuel_Specific_Start_Cost','Fuel_Specific_Cost_Rate']
        self.fuel_cost_parameters = ['Fuel_Specific_Cost_Import', 'Fuel_Specific_Start_Cost','Fuel_Specific_Cost_Rate']
        self.milp_parameters = ['Generator_Nominal_Capacity_milp']
        self.milp_partial_parameters = ['Generator_Nominal_Capacity_milp','Generator_Min_output', 'Generator_pgen']
        self.brownfield_parameters = ['Generator_capacity','GEN_years']
        self.initial_states = {}

        # Custom font definitions
        self.title_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.subtitle_font = tkFont.Font(family="Helvetica", size=12, underline=True)

        # Renewable parameters label
        self.title_label = ttk.Label(self.inner_frame, text="Generator Parameters", font=self.title_font)
        self.title_label.grid(row=1, column=0, columnspan=1, pady=10, sticky='w')
        

        # RES types entry
        ttk.Label(self.inner_frame, text="Generator Types:").grid(row=3, column=0, pady=(0,15), sticky='w')
        self.Generator_Types_var = tk.IntVar(value=1)  # Default value set to 1
        vcmd = (self.register(self.validate_integer), '%P')  # Validation command
        self.Generator_Types_entry = ttk.Entry(self.inner_frame, textvariable=self.Generator_Types_var, validate='key', validatecommand=vcmd)
        self.Generator_Types_entry.grid(row=3, column=1, pady=(0,15), sticky='w')

        # Update configuration button
        self.update_button = ttk.Button(self.inner_frame, text="Update Parameters Configuration", command=self.update_gen_configuration)
        self.update_button.grid(row=3, pady=(0,15), column=2)

        self.gen_entries = []
        for i, (param, value) in enumerate(self.gen_params_defaults.items(), start=5):  
            label_text = param
            label = ttk.Label(self.inner_frame, text=label_text)
            label.grid(row=i, column=0, sticky='w')

            # Determine the variable type
            if param in text_parameters: var = tk.StringVar(value=value)
            else: var = tk.DoubleVar(value=value)

            # Conditionally disable entries based on specific parameters
            if  (param in self.milp_partial_parameters) or (param in self.brownfield_parameters):
                entry_state = 'disabled'
                label_state = 'disabled'
            else:
                entry_state = 'normal'
                label_state = 'normal'
                
            # Create the entry
            vcmd = self.get_validation_command(param, value)
            entry = ttk.Entry(self.inner_frame, textvariable=var, validate='key', validatecommand=vcmd, state=entry_state)
            entry.grid(row=i, column=1, sticky='w')

            # Configure the label state
            label.config(state=label_state)

            # Add tooltip
            tooltip_text = self.gen_params_tooltips.get(param)
            create_tooltip(entry, tooltip_text)
            
            self.initial_states[param] = {'label': label_state, 'entry': entry_state}

            # Append to gen_entries
            self.gen_entries.append((var, label, entry))
            
        self.italic_font = tkFont.Font(family="Helvetica", size=10, slant="italic")
        self.fuel_intro_label = ttk.Label(self.inner_frame, text="Fuel parameters:", font=self.italic_font, wraplength=850, justify="left")
        self.fuel_intro_label.grid(row=22, column=0, columnspan=3, pady=10, sticky='w')

            
        self.Fuel_Specific_Cost_Import_var = tk.IntVar(value=0)
        self.Fuel_Specific_Cost_Import_label = ttk.Label(self.inner_frame, text='Fuel_Specific_Cost_Import', state='disabled')
        self.Fuel_Specific_Cost_Import_label.grid(row=29, column=0, sticky='w')
        self.Fuel_Specific_Cost_Import_checkbutton = ttk.Checkbutton(
                    self.inner_frame, text="Activate",
                    variable=self.Fuel_Specific_Cost_Import_var,
                    command=self.toggle_fuel_specific_cost,
                    state='disabled')
        self.Fuel_Specific_Cost_Import_checkbutton.grid(row=29, column=1, sticky='w')
        create_tooltip(self.Fuel_Specific_Cost_Import_checkbutton, "Check to import the fuel specific cost values from a csv file")
        
        self.fuel_entries = []
        
        for i, (param, value) in enumerate(self.fuel_params_defaults.items(), start=23):  
            label_text = param
            label = ttk.Label(self.inner_frame, text=label_text)
            label.grid(row=i, column=0, sticky='w')

            # Determine the variable type
            if param in text_parameters: var = tk.StringVar(value=value)
            else: var = tk.DoubleVar(value=value)

            # Initially, set the entry state to 'normal' (enabled)
            entry_state = 'normal'
            label_state = 'normal'
            
            # Conditionally disable entries based on specific parameters
            if  param == 'Fuel_Specific_Cost_Rate':
                entry_state = 'disabled'
                label_state = 'disabled'
                
            # Create the entry
            vcmd = self.get_validation_command(param, value)
            entry = ttk.Entry(self.inner_frame, textvariable=var, validate='key', validatecommand=vcmd, state=entry_state)
            entry.grid(row=i, column=1, sticky='w')

            # Configure the label state
            label.config(state=label_state)

            # Add tooltip
            tooltip_text = self.fuel_params_tooltips.get(param, "No description available")
            create_tooltip(entry, tooltip_text)
            
            self.initial_states[param] = {'label': label_state, 'entry': entry_state}

            # Append to gen_entries
            self.fuel_entries.append((var, label, entry))
        
            
        # Create the warning label and grid it
        self.setup_warning()


        
        
        

