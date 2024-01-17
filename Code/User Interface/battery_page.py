import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
from tkinter import messagebox

class TopSectionFrame(tk.Frame):
    def __init__(self, parent, university_name,  *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.configure(background='#0f2c53')

        # University Name
        self.name_label = tk.Label(self, text=university_name, font=("Arial", 10, "italic"), fg="white", background='#0f2c53')
        self.name_label.grid(row=0, column=1, pady=15, sticky='e')

        # Configure grid row and column weights
        self.grid_columnconfigure(1, weight=1) 

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

class BatteryPage(tk.Frame):
    
    def on_confirm_and_next(self):
        all_filled = True
        initial_soc = None
        depth_of_discharge = None
        for var, label, entry in self.battery_calc_params_entries:
            label_text = label.cget("text")
            if label_text == "Battery_Specific_Investment_Cost":
                specific_investment_cost = var.get()
            elif label_text == "Battery_Specific_Electronic_Investment_Cost":
                electronic_investment_cost = var.get()
            elif label_text == "Battery_Initial_SOC":
                initial_soc = float(var.get())
            elif label_text == "Battery_Depth_of_Discharge":
                depth_of_discharge = float(var.get())

            try: 
                value = str(entry.get())
            except: 
                value = ''
            if not value.strip():  
                messagebox.showwarning("Warning", f"Please fill in the required field for {label_text}.")
                entry.focus_set()  # Set focus to the empty entry
                all_filled = False
                break  

        # Additional check for specific electronic cost being less than specific investment cost
        if electronic_investment_cost is not None and specific_investment_cost is not None:
            if electronic_investment_cost >= specific_investment_cost:
                messagebox.showwarning("Warning", "Specific Electronic Cost cannot be higher than Specific Investment Cost.")
                all_filled = False

        # Check for Battery_Initial_SOC being higher than (1 - Battery_Depth_of_Discharge)
        if initial_soc is not None and depth_of_discharge is not None:
            min_initial_soc = 1 - depth_of_discharge
            if initial_soc < min_initial_soc:
                messagebox.showwarning("Warning", f"Battery Initial State of Charge must be higher than {min_initial_soc:.2f}.")
                all_filled = False

        if not all_filled: 
            return

        self.controller.show_GeneratorPage()
    
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

        
    def toggle_milp_parameters(self):
        for (var, label, entry) in self.battery_calc_params_entries:
            if label.cget('text') in self.milp_parameters:
               label.config(state='normal')  
               entry.config(state='normal')
               
    def toggle_brownfield_parameters(self):
        for (var, label, entry) in self.battery_calc_params_entries:
            if label.cget('text') in self.brownfield_parameters:
               label.config(state='normal')  
               entry.config(state='normal')
            
    def get_validation_command(self, param, default):
        fraction_params = {"Battery_Specific_OM_Cost", "Battery_Discharge_Battery_Efficiency", "Battery_Charge_Battery_Efficiency", "Battery_Depth_of_Discharge", "Battery_Initial_SOC"}  
        if param in fraction_params:
            return (self.register(self.validate_fraction), '%P')
        elif isinstance(default, int):
            return (self.register(self.validate_integer), '%P')
        elif isinstance(default, float):
            return (self.register(self.validate_float), '%P')
        return None
    
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
        self.nav_frame = NavigationFrame(self, back_command=controller.show_previous_page_from_battery, next_command=self.on_confirm_and_next)
        self.nav_frame.grid(row=2, column=0, sticky='ew', columnspan=self.grid_size()[0])

        # Define custom font
        self.title_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.subtitle_font = tkFont.Font(family="Helvetica", size=12,underline=True)
        self.italic_font = tkFont.Font(family="Helvetica", size=10, slant="italic")
        
        self.title_label = ttk.Label(self.inner_frame, text="Battery Bank Parameters", font=self.title_font)
        self.title_label.grid(row=1, column=0, columnspan=1, pady=10, sticky='w')
        
        self.intro_label = ttk.Label(self.inner_frame, text="Initialize the parameters related to the battery bank system:", font=self.italic_font, wraplength=850, justify="left")
        self.intro_label.grid(row=2, column=0, columnspan=2, pady=10, sticky='w')
        
        # Define and grid the parameters as labels and entries
        self.battery_calc_params = {
            "Battery_Specific_Investment_Cost": 0.15,
            "Battery_Specific_Electronic_Investment_Cost": 0.05,
            "Battery_Specific_OM_Cost": 0.06,
            "Battery_Discharge_Battery_Efficiency": 0.98,
            "Battery_Charge_Battery_Efficiency": 0.98,
            "Battery_Depth_of_Discharge": 0.8,
            "Maximum_Battery_Discharge_Time": 5,
            "Maximum_Battery_Charge_Time": 5,
            "Battery_Cycles": 6000,
            "Battery_Initial_SOC": 1.0,
            "BESS_unit_CO2_emission": 0.0,
            "Battery_Nominal_Capacity_milp": 1000,
            "Battery_capacity": 0.0
            }
        
        self.battery_calc_params_tooltips = {
            "Battery_Specific_Investment_Cost": "Specific investment cost of the battery bank [USD/Wh]",
            "Battery_Specific_Electronic_Investment_Cost": "Specific investment cost of non-replaceable parts (electronics) of the battery bank [USD/Wh]",
            "Battery_Specific_OM_Cost": "O&M cost of the battery bank as a fraction of specific investment cost [%]",
            "Battery_Discharge_Battery_Efficiency": "Discharge efficiency of the battery bank [%]",
            "Battery_Charge_Battery_Efficiency": "Charge efficiency of the battery bank [%]",
            "Battery_Depth_of_Discharge": "Depth of discharge of the battery bank [%]",
            "Maximum_Battery_Discharge_Time": "Maximum time to discharge the battery bank [h]",
            "Maximum_Battery_Charge_Time": "Maximum time to charge the battery bank [h]",
            "Battery_Cycles": "Maximum number of cycles before degradation of the battery [units]",
            "Battery_Initial_SOC": "Battery initial state of charge [%]",
            "BESS_unit_CO2_emission": "CO2 emissions [kgCO2/kWh]",
            "Battery_Nominal_Capacity_milp": "Battery's nominal capacity units (MILP Formulation)",
            "Battery_capacity": "Existing Battery capacity [Wh]"
        }
        self.milp_parameters = ['Battery_Nominal_Capacity_milp']
        self.brownfield_parameters = ['Battery_capacity']

        self.battery_calc_params_entries = []
        for i, (param, value) in enumerate(self.battery_calc_params.items(), start=3): 
            label_text = param
            label = ttk.Label(self.inner_frame, text=label_text)
            label.grid(row=i, column=0, sticky='w')
            var = tk.DoubleVar(value=value)
            # Initially, set the entry state to 'normal' (enabled)
            entry_state = 'normal'
            label_state = 'normal'

            # Conditionally disable entries based on specific parameters
            if  param in self.milp_parameters or param in self.brownfield_parameters:
                entry_state = 'disabled'
                label_state = 'disabled'
                
            # Create the entry
            vcmd = self.get_validation_command(param, value)
            entry = ttk.Entry(self.inner_frame, textvariable=var, validate='key', validatecommand=vcmd, state=entry_state)
            entry.grid(row=i, column=1, padx=(20,0), sticky='w')

            # Configure the label state
            label.config(state=label_state)

            # Add tooltip
            tooltip_text = self.battery_calc_params_tooltips.get(param, "No description available")
            create_tooltip(entry, tooltip_text)

            self.battery_calc_params_entries.append((var, label, entry))
        
    def get_input_data(self):
        input_data = {}
        for var, label, entry in self.battery_calc_params_entries:
            param = label.cget("text")
            input_data[param] = var.get()  # Retrieve the value from the entry widget
        return input_data


