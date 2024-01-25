import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import font as tkFont
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
        


class TechnologiesPage(tk.Frame):
    
    def update_section_span(self):
        total_columns = self.grid_size()[0]
        self.top_section.grid_configure(columnspan=total_columns)
        self.nav_frame.grid_configure(columnspan=total_columns)

    def add_column(self):
        current_columns = self.grid_size()[0]
        self.grid_columnconfigure(current_columns, weight=1)  # Configure the new column
        self.update_section_span() 
    
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
    
    def clear_res_entries(self):
     for var, label, entry in self.res_entries:
        if label: 
            label.destroy()
        entry.destroy()
        
    def get_validation_command(self, param, default):
        fraction_params = {"RES_Inverter_Efficiency", "RES_Specific_OM_Cost"}  
        if param in fraction_params:
            return (self.register(self.validate_fraction), '%P')
        elif isinstance(default, int):
            return (self.register(self.validate_integer), '%P')
        elif isinstance(default, float):
            return (self.register(self.validate_float), '%P')
        return None
        
    def update_res_configuration(self):
        # Clear all existing entries before updating
        self.clear_res_entries()

        # Retrieve the number of RES sources from the entry widget or default to 1
        try:
            res_sources = int(self.RES_Sources_entry.get())
        except ValueError:
            res_sources = 1

        # Ensure the backup variables are updated
        self.res_params_defaults['RES_Nominal_Capacity'] = self.solar_backup_var.get()
        self.res_params_defaults_second['RES_Nominal_Capacity'] = self.wind_backup_var.get()


        # Initialize the res_entries list
        self.res_entries = []

        # Starting row for the new entries in the grid
        row_start = 5

        # Loop over each parameter to create labels and entries
        for param_index, (param, default) in enumerate(self.res_params_defaults.items()):
            for i in range(res_sources):
                row = row_start + param_index

                # Use different values for the second set of entries (wind turbines)
                value = default if i == 0 else self.res_params_defaults_second.get(param, default)

                # Create a variable to hold the entry's value
                var = tk.DoubleVar(value=value) if param != 'RES_Names' else tk.StringVar(value=value)

                # Create the label for the first column only
                label = ttk.Label(self.inner_frame, text=param) if i == 0 else None
                if label:
                    label.grid(row=row, column=0, sticky='w')
                    
                # Retrieve initial state for the label and entry
                initial_label_state = self.initial_states.get(param, {}).get('label', 'normal')
                initial_entry_state = self.initial_states.get(param, {}).get('entry', 'normal')

                # Create the entry widget
                if param == 'RES_Nominal_Capacity' and self.res_backup_var.get() == 1:
                    entry = ttk.Entry(self.inner_frame, textvariable=var, state='disabled')
                else: 
                    entry = ttk.Entry(self.inner_frame, textvariable=var, state=initial_entry_state)
                entry.grid(row=row, column=1 + i, sticky='w')
                
                # Set the state of the label according to its initial state
                if label:label.config(state=initial_label_state)

                # Add the variable, label, and entry to the res_entries list
                self.res_entries.append((var, label, entry))

                # Add tooltip to the entry
                tooltip_text = self.res_params_tooltips.get(param, "Info not available")
                create_tooltip(entry, tooltip_text)
        
            
    def toggle_brownfield_parameters(self):
        for (var, label, entry) in self.res_entries:
            if label and label.cget('text') in self.brownfield_parameters:
               label.config(state='normal')  
               entry.config(state='normal')
               self.initial_states[label.cget('text')] = {'label': 'normal', 'entry': 'normal'}
        
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
        self.warning_label = ttk.Label(warning_frame, text="IMPORTANT: When Endogenous RES Calculation is activated, 'RES_Nominal_Capacity' entries are disabled as they must correspond to the nominal capacity parameters used for simulating electricity production. In case of Exogenous RES Time Series Data, ensure that 'RES_Nominal_Capacity' accurately reflects the capacity per unit of production used in your data.", wraplength=700, justify="left")
        self.warning_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        # Ensure the text spans the rest of the grid
        warning_frame.grid_columnconfigure(1, weight=1)
            
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
        

        
    def get_input_data(self):
     res_data = {'RES_Sources': self.RES_Sources_var.get()}
     num_res_types = int(self.RES_Sources_var.get())

     # Initialize a dictionary to store the values for each parameter
     param_values = {param: [] for param in self.res_params_defaults}

     # Iterate over the entries and aggregate values by parameter
     for var, label, entry in self.res_entries:
        if label:
            param = label.cget('text')
            # Reset the current list for this parameter if we're on the first res type
            if len(param_values[param]) >= num_res_types:
                param_values[param] = [var.get()]
            else:
                param_values[param].append(var.get())
        else:
            # Find the parameter this value belongs to by matching the variable in param_values
            for key, values in param_values.items():
                if len(values) < num_res_types:
                    param_values[key].append(var.get())
                    break

     for param, values in param_values.items():
         res_data[param] = values
         
     return res_data
            
    def on_confirm_res(self):
            self.controller.refresh_plot_page()
            
    def on_confirm_and_next(self):
     all_filled = True
     for var, label, entry in self.res_entries:
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
    
     self.get_input_data()
     self.controller.refresh_plot_page()  # Update the plot page with the new data
     self.controller.show_next_page()  # Go to the next page

                
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        
        # Configure the grid layout of the parent frame
        self.grid_rowconfigure(0, weight=0)  # Top section should not expand
        self.grid_rowconfigure(1, weight=1)  # Scrollable section should expand
        self.grid_rowconfigure(2, weight=0)  # Bottom section should not expand
        self.grid_columnconfigure(0, weight=1)

        # Add Top Section
        university_name = "MicroGridsPy "
        self.top_section = TopSectionFrame(self, university_name)
        self.top_section.grid(row=0, column=0, sticky='ew')

        # Setup the scrollable area
        self.setup_scrollable_area()
        
        # Add NavigationFrame at the very bottom
        self.nav_frame = NavigationFrame(self, back_command=lambda: controller.show_frame("ArchetypesPage"), next_command=self.on_confirm_and_next)
        self.nav_frame.grid(row=2, column=0, sticky='ew')
        
        self.update_section_span()
        
        # Define the default parameters and their initial values
        self.res_params_defaults = {
            "RES_Names": "Solar PV",
            "RES_Nominal_Capacity": 1000,
            "RES_Inverter_Efficiency": 0.98,
            "RES_Specific_Investment_Cost": 0.95,
            "RES_Specific_OM_Cost": 0.018,
            "RES_Lifetime": 25,
            "RES_unit_CO2_emission": 0,
            "RES_capacity": 0,
            "RES_years": 0
        }
        # Additional default values for the second set of entries
        self.res_params_defaults_second = {
            "RES_Names": "Wind Turbine",
            "RES_Nominal_Capacity": 1670000,
            "RES_Inverter_Efficiency": 0.95,
            "RES_Specific_Investment_Cost": 1.9,
            "RES_Specific_OM_Cost": 0.05,
            "RES_Lifetime": 20,
            "RES_unit_CO2_emission": 0,
            "RES_capacity": 0,
            "RES_years": 0
            }
        
        self.res_params_tooltips = {
            "RES_Names":"Renewable technology name",
            "RES_Nominal_Capacity":"Capacity in W per unit of electricity production (read below for further info)",
            "RES_Inverter_Efficiency": "Average efficiency the inverter [%]",
            "RES_Specific_Investment_Cost": "Specific investment cost for each renewable technology [USD/W]",
            "RES_Specific_OM_Cost": "O&M cost for each renewable technology as a fraction of specific investment cost [%]",
            "RES_Lifetime": "Renewables Lifetime [years]",
            "RES_unit_CO2_emission": "Specific CO2 emissions associated to each renewable technology [kgCO2/kW]",
            "RES_capacity": "Existing capacity [-] in brownfield scenario",
            "RES_years": "How many years ago the component was installed [years]"
        }
        
        self.solar_backup_var = tk.DoubleVar(value=1000)
        self.wind_backup_var = tk.DoubleVar(value=1670000)
        self.res_backup_var = tk.IntVar(value=1)
        
        text_parameters = ['RES_Names']
        self.brownfield_parameters = ['RES_capacity','RES_years']
        self.initial_states = {}
        # Initialize the dictionary to hold the StringVars for each parameter
        self.res_entries = {param: [] for param in self.res_params_defaults}
        self.res_entries_widgets = []  # List to hold entry widgets for clearing

        # Custom font definitions
        self.title_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.subtitle_font = tkFont.Font(family="Helvetica", size=12, underline=True)
        self.italic_font = tkFont.Font(family="Helvetica", size=10, slant="italic")

        # Title label
        self.title_label = ttk.Label(self.inner_frame, text="Renewables Parameters", font=self.title_font)
        self.title_label.grid(row=1, column=0, columnspan=1, pady=10, sticky='w')

        # Renewable parameters label
        self.intro_label = ttk.Label(self.inner_frame, text="Define the number and type of renewable sources to be considered:", font=self.italic_font, wraplength=850, justify="left")
        self.intro_label.grid(row=2, column=0, columnspan=2, pady=10, sticky='w')

        # RES types entry
        ttk.Label(self.inner_frame, text="RES_Sources").grid(row=3, column=0, pady=(0,15), sticky='w')
        self.RES_Sources_var = tk.IntVar(value=2)  
        vcmd = (self.register(self.validate_integer), '%P')  # Validation command
        self.RES_Sources_entry = ttk.Entry(self.inner_frame, textvariable=self.RES_Sources_var, validate='key', validatecommand=vcmd)
        self.RES_Sources_entry.grid(row=3, column=1, pady=(0,15), sticky='w')
        create_tooltip(self.RES_Sources_entry, "Type the number of renewable sources and press the update button to visualize the additional parameters")

        # Update configuration button
        self.update_button = ttk.Button(self.inner_frame, text="Update Parameters Configuration", command=self.update_res_configuration)
        self.update_button.grid(row=3, column=2, pady=(0,15),sticky='w')

        self.res_entries = []
        for i, (param, value) in enumerate(self.res_params_defaults.items(), start=5):  
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
            if  param in self.brownfield_parameters:
                entry_state = 'disabled'
                label_state = 'disabled'
                
            # Create the entry
            vcmd = self.get_validation_command(param, value)
            entry = ttk.Entry(self.inner_frame, textvariable=var, validate='key', validatecommand=vcmd, state=entry_state)
            entry.grid(row=i, column=1, sticky='w')

            # Configure the label state
            label.config(state=label_state)

            # Add tooltip
            tooltip_text = self.res_params_tooltips.get(param)
            create_tooltip(entry, tooltip_text)
            
            self.initial_states[param] = {'label': label_state, 'entry': entry_state}

            # Append to gen_entries
            self.res_entries.append((var, label, entry))
            
        self.update_res_configuration()
        self.setup_warning()
     




        
        


