import tkinter as tk
from tkinter import font as tkFont
#import ttkbootstrap as ttkk
#from ttkbootstrap import Style
from tkinter import ttk
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

class AdvancedPage(tk.Frame):
    
    
    # Function to toggle the state of Generator Partial Load
    def toggle_generator_partial_load(self,*args):
        if self.MILP_Formulation_var.get() == 1:
            self.Generator_Partial_Load_label.config(state='normal')
            self.Generator_Partial_Load_checkbutton.config(state='normal')
        else:
            self.Generator_Partial_Load_var.set(0)  # Reset to 0 if MILP is not selected
            self.Generator_Partial_Load_label.config(state='disabled')
            self.Generator_Partial_Load_checkbutton.config(state='disabled')
            
            

    # Function to toggle the state of Plot Max Cost
    def toggle_MultiObjective(self, *args):
        if self.Multiobjective_Optimization_var.get() == 1:
            self.Plot_Max_Cost_label.config(state='normal')
            self.Plot_Max_Cost_radio1.config(state='normal')
            self.Plot_Max_Cost_radio0.config(state='normal')
            self.pareto_points_label.config(state='normal')
            self.pareto_points_entry.config(state='normal')
            self.pareto_solution_label.config(state='normal')
            self.pareto_solution_combobox.config(state='normal')

        else:
            self.Plot_Max_Cost_var.set(0)  # Reset to No if Multi-Objective Optimization is not selected
            self.Plot_Max_Cost_label.config(state='disabled')
            self.Plot_Max_Cost_radio1.config(state='disabled')
            self.Plot_Max_Cost_radio0.config(state='disabled')
            self.pareto_points_label.config(state='disabled')
            self.pareto_points_entry.config(state='disabled')
            self.pareto_solution_label.config(state='disabled')
            self.pareto_solution_combobox.config(state='disabled')
            
    def toggle_MultiScenario(self, *args):
        if self.Multiscenario_Optimization_var.get() == 1:
            self.num_scenarios_label.config(state='normal')
            self.num_scenarios_entry.config(state='normal')
            self.update_config_button.configure(state='normal')
        else:
            for entry in self.scenario_weights_entries:
                entry.destroy()
            for label in self.scenario_weights_labels:
                label.destroy()
            self.scenario_weights_entries.clear()
            self.scenario_weights_vars.clear()
            self.Multiscenario_Optimization_var.set(0)
            self.num_scenarios_var.set(1)
            self.num_scenarios_label.config(state='disabled')
            self.num_scenarios_entry.config(state='disabled')
            self.update_config_button.configure(state='disabled')

            
    def toggle_Capacity(self, *args):
        if self.Capacity_expansion_var.get() == 1:
            self.Step_Duration_label.config(state='normal')
            self.Step_Duration_entry.config(state='normal')
            self.Min_Step_Duration_label.config(state='normal')
            self.Min_Step_Duration_entry.config(state='normal')
        else:
            self.Step_Duration_label.config(state='disabled')
            self.Step_Duration_entry.config(state='disabled')
            self.Min_Step_Duration_label.config(state='disabled')
            self.Min_Step_Duration_label.config(state='disabled')
            self.Min_Step_Duration_entry.config(state='disabled')

    def validate_pareto_solution(self, P):
        # Validate Pareto solution ensuring it's an integer between 1 and Pareto points.
        if P.isdigit():
            pareto_solution = int(P)
            pareto_points = self.pareto_points_var.get()
            if 1 <= pareto_solution <= pareto_points:
                return True
            else:
                self.bell()  # System bell if invalid input
                return False
        elif P == "":
            return True
        else:
            self.bell()  # System bell if invalid input
            return False
        
    # Function to toggle the grid options based on the grid connection
    def toggle_grid_options(self,*args):
            if self.Grid_Connection_var.get() == 1: 
                self.Grid_Availability_Simulation_checkbutton.config(state='normal')
                self.Grid_Availability_Simulation_label.config(state='normal')
                self.Grid_Connection_Type_label.config(state='normal')
                self.Grid_Connection_Type_radio1.config(state='normal')
                self.Grid_Connection_Type_radio2.config(state='normal')
            else: 
                self.Grid_Availability_Simulation_var.set(0)
                self.Grid_Connection_Type_var.set(0)
                self.Grid_Availability_Simulation_checkbutton.config(state='disabled')
                self.Grid_Availability_Simulation_label.config(state='disabled')
                self.Grid_Connection_Type_label.config(state='disabled')
                self.Grid_Connection_Type_radio1.config(state='disabled')
                self.Grid_Connection_Type_radio2.config(state='disabled')
        
    # Function to toggle the state of WACC parameters
    def toggle_wacc_parameters(self):
        state = 'normal' if self.WACC_Calculation_var.get() == 1 else 'disabled'
        for var, label, entry in self.wacc_parameters_entries:  # Updated to unpack three elements
            label.config(state=state)
            entry.config(state=state)
            if state == 'disabled': var.set('')
            
    def toggle_investment_limit(self, *args):
        if self.Optimization_Goal_var.get() == 0:  # Assuming 0 is the value for 'Operation Cost'
            self.Investment_Cost_Limit_entry.config(state='normal')
            self.Investment_Cost_Limit_label.config(state='normal')
        else:
            self.Investment_Cost_Limit_entry.config(state='disabled')
            self.Investment_Cost_Limit_label.config(state='disabled')
                
    def on_next_button(self):
        if tk.messagebox.askyesno("Confirm Action", "Are you sure you want to proceed? You won't be able to come back and change these configuration options later."):
            # First, update the GeneratorPage parameters
            milp_formulation = self.MILP_Formulation_var.get()
            partial_load = self.Generator_Partial_Load_var.get()
            brownfield = self.Greenfield_Investment_var.get()
            fuel_cost = self.Fuel_Specific_Cost_Calculation_var.get()
            res_page = self.controller.frames.get("TechnologiesPage")
            generator_page = self.controller.frames.get("GeneratorPage")
            battery_page = self.controller.frames.get("BatteryPage")
            if milp_formulation == 1 and partial_load == 1:
                battery_page.toggle_milp_parameters()
                generator_page.toggle_milp_partial_parameters()
            elif milp_formulation == 1 and partial_load == 0:
                battery_page.toggle_milp_parameters()
                generator_page.toggle_milp_parameters()
            if brownfield == 0:
                res_page.toggle_brownfield_parameters()
                battery_page.toggle_brownfield_parameters()
                generator_page.toggle_brownfield_parameters()
            if fuel_cost == 1:
                generator_page.toggle_fuel_cost_parameters()
            
            if self.Step_Duration_var.get() > self.backup_var.get():
                tk.messagebox.showerror("Error", "Step Duration can not exceed the Total Project Duration")
                return False
            # Then, navigate to the RECalculationPage
            self.controller.show_frame("RECalculationPage")
        else: pass
        
    def update_scenario_weights(self, event=None):
        # Clear existing weight entries
        for entry in self.scenario_weights_entries:
            entry.destroy()
        for label in self.scenario_weights_labels:
            label.destroy()
        self.scenario_weights_entries.clear()
        self.scenario_weights_vars.clear()

        # Validate and get the number of scenarios
        try:
            num_scenarios = int(self.num_scenarios_var.get())
        except ValueError:
            return  # Invalid input, do nothing

        # Update the scrollable area
        self.canvas.after_idle(lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        # Create new entries for scenario weights
        if num_scenarios > 1:
            for i in range(num_scenarios):
                var = tk.DoubleVar(value=1.0 / num_scenarios)
                vcmd = (self.register(self.validate_fraction), '%P')
                label = ttk.Label(self.inner_frame, text="Scenario weight")
                entry = ttk.Entry(self.inner_frame, textvariable=var,validate='key', validatecommand=vcmd)
                label.grid(row=20 + i, column=3, sticky='w')
                entry.grid(row=20 + i, column=4, sticky='w')
                self.scenario_weights_vars.append(var)
                self.scenario_weights_entries.append(entry)
                self.scenario_weights_labels.append(label)
            
            # Check if total weight exceeds 1
            total_weight = sum(var.get() for var in self.scenario_weights_vars)
            if total_weight > 1:
                tk.messagebox.showerror("Error", "Total weights of scenarios can not exceed 1")
                return False
            # Update the scrollregion
            self.canvas.after_idle(lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
            return True

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

    def update_pareto_solution_options(self, *args):
        """ Update the options in the Pareto solution combobox based on the Pareto points. """
        points = self.pareto_points_var.get()
        options = list(range(1, points + 1))
        self.pareto_solution_combobox['values'] = options
        # Automatically select the first option if current value is out of range
        if self.pareto_solution_var.get() > points:
            self.pareto_solution_var.set(1)


                
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

        
    def __init__(self, parent, controller):
        super().__init__(parent)
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
        self.top_section.grid(row=0, column=0, columnspan=4, sticky='ew')

        # Setup the scrollable area
        self.setup_scrollable_area()
        
        # Define custom font
        self.title_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.subtitle_font = tkFont.Font(family="Helvetica", size=12,underline=True)
        self.italic_font = tkFont.Font(family="Helvetica", size=10, slant="italic")

        # Section title: MicroGridsPy - Data Input
        self.title_label = ttk.Label(self.inner_frame, text="Advanced Features", font=self.title_font,style='TLabel')
        self.title_label.grid(row=1, column=0, columnspan=1,sticky='w')

        # Section title: Model Configuration
        self.title_label = ttk.Label(self.inner_frame, text="Advanced Modeling Options", font=self.subtitle_font,style='TLabel')
        self.title_label.grid(row=2, column=0, columnspan=1, pady=10, sticky='w')
        
        #Capacity Expansion
        self.Capacity_expansion_var = tk.IntVar(value=0)
        self.Capacity_expansion_label = ttk.Label(self.inner_frame, text="Capacity Expansion:", anchor='w')
        self.Capacity_expansion_label.grid(row=3, column=0, sticky='w')
        self.Capacity_expansion_checkbutton = ttk.Checkbutton(self.inner_frame, text="Activate", variable=self.Capacity_expansion_var, onvalue=1, offvalue=0)
        self.Capacity_expansion_checkbutton.grid(row=3, column=1, sticky='w')
        self.Capacity_expansion_var.trace('w', self.toggle_Capacity)
        create_tooltip(self.Capacity_expansion_checkbutton, "Allow capacity expansion and different investment steps during the time horizon")
        
        self.backup_var = tk.IntVar(value=20)
        
        # Step Duration
        self.Step_Duration_label = ttk.Label(self.inner_frame, text="Step Duration [Years]:", anchor='w', state='disabled')
        self.Step_Duration_label.grid(row=4, column=0, sticky='w')
        self.Step_Duration_var = tk.IntVar(value=20)
        vcmd = (self.register(self.validate_integer), '%P')
        self.Step_Duration_entry = ttk.Entry(self.inner_frame, textvariable=self.Step_Duration_var,validate='key', validatecommand=vcmd,state='disabled')
        self.Step_Duration_entry.grid(row=4, column=1,sticky='w')
        create_tooltip(self.Step_Duration_entry, "Duration of each investment decision step in which the project lifetime will be split")

        
        # Min_Last_Step_Duration
        self.Min_Step_Duration_label = ttk.Label(self.inner_frame, text="Minimum Last Step Duration [Years]:", anchor='w',state='disabled')
        self.Min_Step_Duration_label.grid(row=5, column=0, sticky='w')
        self.Min_Step_Duration_var = tk.IntVar(value=1)
        vcmd = (self.register(self.validate_integer), '%P')
        self.Min_Step_Duration_entry = ttk.Entry(self.inner_frame, textvariable=self.Min_Step_Duration_var,validate='key', validatecommand=vcmd,state='disabled')
        self.Min_Step_Duration_entry.grid(row=5, column=1,sticky='w')
        create_tooltip(self.Min_Step_Duration_entry, "Minimum duration of the last investment decision step, in case of non-homogeneous divisions of the project lifetime")

        # Descriptive Text Below the Images
        descriptive_text = ("")
        self.description_label = ttk.Label(self.inner_frame, text=descriptive_text, wraplength=850, justify="left")
        self.description_label.grid(row=6, column=0, columnspan=2, sticky='w')
        
        # MILP Formulation
        self.MILP_Formulation_var = tk.IntVar(value=0)
        ttk.Label(self.inner_frame, text="Model Formulation:", anchor='w').grid(row=7, column=0, sticky='w')
        self.MILP_Formulation_radio0 = ttk.Radiobutton(self.inner_frame, text="LP", variable=self.MILP_Formulation_var, value=0)
        self.MILP_Formulation_radio0.grid(row=7, column=1, sticky='w')
        self.MILP_Formulation_radio1 = ttk.Radiobutton(self.inner_frame, text="MILP", variable=self.MILP_Formulation_var, value=1)
        self.MILP_Formulation_radio1.grid(row=7, column=1, sticky='e')
        self.MILP_Formulation_var.trace('w', self.toggle_generator_partial_load)
        create_tooltip(self.MILP_Formulation_radio0, "Linear Programming")
        create_tooltip(self.MILP_Formulation_radio1, "Multiple Integers Linear Programming")
        

        # Generator Partial Load
        self.Generator_Partial_Load_var = tk.IntVar(value=0)
        self.Generator_Partial_Load_label = ttk.Label(self.inner_frame, text="Generator Partial Load:", anchor='w')
        self.Generator_Partial_Load_label.grid(row=8, column=0, sticky='w')
        self.Generator_Partial_Load_checkbutton = ttk.Checkbutton(self.inner_frame, text="Activate", variable=self.Generator_Partial_Load_var, onvalue=1, offvalue=0)
        self.Generator_Partial_Load_checkbutton.grid(row=8, column=1, sticky='w')
        self.Generator_Partial_Load_label.config(state='disabled')
        self.Generator_Partial_Load_checkbutton.config(state='disabled')
        self.toggle_generator_partial_load()

        # Descriptive Text Below the Images
        descriptive_text = ("")
        self.description_label = ttk.Label(self.inner_frame, text=descriptive_text, wraplength=850, justify="left")
        self.description_label.grid(row=9, column=0, columnspan=2, sticky='w')

        # Greenfield
        self.Greenfield_Investment_var = tk.IntVar(value=1)
        ttk.Label(self.inner_frame, text="Type of Investment:",anchor='w').grid(row=10, column=0,sticky='w')
        self.Greenfield_radio = ttk.Radiobutton(self.inner_frame, text="Greenfield", variable=self.Greenfield_Investment_var, value=1).grid(row=10, column=1, sticky='w')
        self.Brownfield_radio = ttk.Radiobutton(self.inner_frame, text="Brownfield", variable=self.Greenfield_Investment_var, value=0).grid(row=10, column=2, sticky='w')

        # Descriptive Text Below the Images
        descriptive_text = ("")
        self.description_label = ttk.Label(self.inner_frame, text=descriptive_text, wraplength=850, justify="left")
        self.description_label.grid(row=11, column=0, columnspan=2, sticky='w')

        # Grid Connection Radiobuttons
        self.Grid_Connection_var = tk.IntVar(value=0)
        self.Grid_Connection_var.trace('w', self.toggle_grid_options)
        ttk.Label(self.inner_frame, text="Grid Connection:", anchor='w').grid(row=12, column=0, sticky='w')
        self.Grid_Connection_radio = ttk.Radiobutton(self.inner_frame, text="On-grid", variable=self.Grid_Connection_var, value=1)
        self.Grid_Connection_radio.grid(row=12, column=1, sticky='w')
        create_tooltip(self.Grid_Connection_radio, "Simulate grid connection during project lifetime")
        ttk.Radiobutton(self.inner_frame, text="Off-grid", variable=self.Grid_Connection_var, value=0).grid(row=12, column=2, sticky='w')

        # Grid Availability Simulation
        self.Grid_Availability_Simulation_var = tk.IntVar(value=0)
        self.Grid_Availability_Simulation_label = ttk.Label(self.inner_frame, text="Grid Availability:", anchor='w')
        self.Grid_Availability_Simulation_label.grid(row=13, column=0, sticky='w')
        self.Grid_Availability_Simulation_label.config(state='disabled')
        self.Grid_Availability_Simulation_checkbutton = ttk.Checkbutton(self.inner_frame, text="Activate", variable=self.Grid_Availability_Simulation_var, onvalue=1, offvalue=0)
        create_tooltip(self.Grid_Availability_Simulation_checkbutton, "Simulate grid availability matrix")
        self.Grid_Availability_Simulation_checkbutton.grid(row=13, column=1, sticky='w')
        self.Grid_Availability_Simulation_checkbutton.config(state='disabled')

        # Grid Connection Type Radiobuttons
        self.Grid_Connection_Type_var = tk.IntVar(value=0)
        self.Grid_Connection_Type_label = ttk.Label(self.inner_frame, text="Grid Connection Type:", anchor='w', state='disabled')
        self.Grid_Connection_Type_label.grid(row=14, column=0, sticky='w')
        self.Grid_Connection_Type_radio1 = ttk.Radiobutton(self.inner_frame, text="Purchase Only", variable=self.Grid_Connection_Type_var, value=0, state='disabled')
        self.Grid_Connection_Type_radio1.grid(row=14, column=1, sticky='w')
        self.Grid_Connection_Type_radio2 = ttk.Radiobutton(self.inner_frame, text="Purchase/Sell", variable=self.Grid_Connection_Type_var, value=1, state='disabled')
        self.Grid_Connection_Type_radio2.grid(row=14, column=2, sticky='w')
        self.toggle_grid_options()
        
        # Descriptive Text Below the Images
        descriptive_text = ("")
        self.description_label = ttk.Label(self.inner_frame, text=descriptive_text, wraplength=850, justify="left")
        self.description_label.grid(row=15, column=0, columnspan=2, sticky='w')
        
        # Generator Partial Load
        self.Fuel_Specific_Cost_Calculation_var = tk.IntVar(value=0)
        self.Fuel_Specific_Cost_Calculation_label = ttk.Label(self.inner_frame, text="Fuel Specific Cost Calculation:", anchor='w')
        self.Fuel_Specific_Cost_Calculation_label.grid(row=16, column=0, sticky='w')
        self.Fuel_Specific_Cost_Calculation_checkbutton = ttk.Checkbutton(self.inner_frame, text="Activate", variable=self.Fuel_Specific_Cost_Calculation_var, onvalue=1, offvalue=0)
        self.Fuel_Specific_Cost_Calculation_checkbutton.grid(row=16, column=1, sticky='w')
        create_tooltip(self.Fuel_Specific_Cost_Calculation_checkbutton, "Allow for variable fuel costs across the years")


        # WACC Calculation Checkbutton
        self.WACC_Calculation_var = tk.IntVar(value=0)
        self.WACC_Calculation_label = ttk.Label(self.inner_frame, text="WACC Calculation:", anchor='w')
        self.WACC_Calculation_label.grid(row=3, column=3, sticky='w', padx=30)
        self.WACC_Calculation_checkbutton = ttk.Checkbutton(self.inner_frame, text="Activate", variable=self.WACC_Calculation_var, onvalue=1, offvalue=0, command=self.toggle_wacc_parameters)
        self.WACC_Calculation_checkbutton.grid(row=3, column=4, sticky='w',padx=30)
        create_tooltip(self.WACC_Calculation_checkbutton, "Allow for Weighted Average Cost of Capital (WACC) in place of the standard discount rate")
        
        vcmd = (self.register(self.validate_float), '%P')

        # WACC Parameters
        wacc_parameters = {
            "cost_of_equity": 0.12,
            "cost_of_debt": 0.11,
            "tax": 0.02,
            "equity_share": 0.10,
            "debt_share": 0.90
            }

        wacc_tooltips = {
            "cost_of_equity": "Cost of equity (i.e., the return required by the equity shareholders)",
            "cost_of_debt": "Cost of debt (i.e., the interest rate)",
            "tax": "Corporate tax deduction (debt is assumed as tax deducible)",
            "equity_share": "Total level of equity",
            "debt_share": "Total level of debt"
            }
        # Create labels and entries for WACC parameters in the adjusted columns
        self.wacc_parameters_entries = []
        for i, (param, value) in enumerate(wacc_parameters.items(), start=4):  # Adjust the starting row accordingly
            label = ttk.Label(self.inner_frame, text=param)
            label.grid(row=i, column=3, sticky='w',padx=30)  # Place the labels in column 3
            var = tk.DoubleVar(value=value)
            entry = ttk.Entry(self.inner_frame, textvariable=var, state='normal', validate='key', validatecommand=vcmd)  # Initially set state to 'normal' to show the value
            entry.var = var
            entry.grid(row=i, column=4, sticky='w',padx=30)
            # Add tooltip
            tooltip_text = wacc_tooltips.get(param)
            create_tooltip(entry, tooltip_text)
            label.config(state='disabled')  
            entry.config(state='disabled')  
            self.wacc_parameters_entries.append((var, label, entry))
            
        # Section title: Model Configuration
        self.title_label = ttk.Label(self.inner_frame, text="Advanced Optimization Configuration", font=self.subtitle_font,style='TLabel')
        self.title_label.grid(row=17, column=0, columnspan=1, pady=10, sticky='w')
            
        # Multiobjective Optimization
        self.Multiobjective_Optimization_var = tk.IntVar(value=0)
        ttk.Label(self.inner_frame, text="Multi-Objective Optimization:", anchor='w').grid(row=18, column=0, sticky='w')
        self.Multiobjective_Optimization_checkbutton = ttk.Checkbutton(self.inner_frame, text="Activate", variable=self.Multiobjective_Optimization_var, onvalue=1, offvalue=0)
        self.Multiobjective_Optimization_checkbutton.grid(row=18, column=1, sticky='w')
        create_tooltip(self.Multiobjective_Optimization_checkbutton, "Optimization of NPC/operation cost and CO2 emissions")
        self.Multiobjective_Optimization_var.trace('w', self.toggle_MultiObjective)

        # Define the variable for Plot Max Cost options
        self.Plot_Max_Cost_var = tk.IntVar(value=0)
        self.Plot_Max_Cost_label = ttk.Label(self.inner_frame, text="Plot Max Cost:", anchor='w')
        self.Plot_Max_Cost_label.grid(row=19, column=0, sticky='w')
        self.Plot_Max_Cost_radio1 = ttk.Radiobutton(self.inner_frame, text="Yes", variable=self.Plot_Max_Cost_var, value=1, state='disabled')
        self.Plot_Max_Cost_radio1.grid(row=19, column=1, sticky='w')
        create_tooltip(self.Plot_Max_Cost_radio1, "Pareto curve has to include the point at maxNPC/maxOperationCost")
        self.Plot_Max_Cost_radio0 = ttk.Radiobutton(self.inner_frame, text="No", variable=self.Plot_Max_Cost_var, value=0, state='disabled')
        self.Plot_Max_Cost_radio0.grid(row=19, column=1, sticky='e')
        self.Plot_Max_Cost_label.config(state='disabled')
        
        # Number of Pareto points
        self.pareto_points_label = ttk.Label(self.inner_frame, text="Pareto points:", anchor='w', state='disabled')
        self.pareto_points_label.grid(row=20, column=0, sticky='w')
        self.pareto_points_var = tk.IntVar(value=2)
        vcmd = (self.register(self.validate_integer), '%P')
        self.pareto_points_entry = ttk.Entry(self.inner_frame, textvariable=self.pareto_points_var, state='disabled',validate='key', validatecommand=vcmd)
        self.pareto_points_entry.grid(row=20, column=1, sticky='w')
        create_tooltip(self.pareto_points_entry, "Pareto curve points to be analysed during optimization")
        
        self.pareto_points_var.trace('w', self.update_pareto_solution_options)

        # Pareto solution
        self.pareto_solution_label = ttk.Label(self.inner_frame, text="Pareto solution:", anchor='w', state='disabled')
        self.pareto_solution_label.grid(row=21, column=0, sticky='w')
        self.pareto_solution_var = tk.IntVar(value=1)
        self.pareto_solution_combobox = ttk.Combobox(self.inner_frame, textvariable=self.pareto_solution_var, state='disabled')
        self.pareto_solution_combobox.grid(row=21, column=1, sticky='w')
        create_tooltip(self.pareto_solution_combobox, "Multi-Objective optimization solution to be displayed")
        
        self.toggle_MultiObjective()
        
        # Initially update the Pareto solution options
        self.update_pareto_solution_options()

        # Multiobjective Optimization
        self.Multiscenario_Optimization_var = tk.IntVar(value=0)
        ttk.Label(self.inner_frame, text="Multi-Scenario Optimization:", anchor='w').grid(row=18, column=3, sticky='w')
        self.Multiscenario_Optimization_checkbutton = ttk.Checkbutton(self.inner_frame, text="Activate", variable=self.Multiscenario_Optimization_var, onvalue=1, offvalue=0)
        self.Multiscenario_Optimization_checkbutton.grid(row=18, column=4, sticky='w')
        create_tooltip(self.Multiscenario_Optimization_checkbutton, "Simulate different scenarios of demand and RES time series")
        self.Multiscenario_Optimization_var.trace('w', self.toggle_MultiScenario)
            
        # Number of Scenarios
        self.num_scenarios_var = tk.IntVar(value=1)
        self.num_scenarios_label = ttk.Label(self.inner_frame, text="Number of Scenarios:", anchor='w',state='disabled')
        self.num_scenarios_label.grid(row=19, column=3, sticky='w')
        vcmd = (self.register(self.validate_integer), '%P')
        self.num_scenarios_entry = ttk.Entry(self.inner_frame, textvariable=self.num_scenarios_var,validate='key', validatecommand=vcmd,state='disabled')
        self.num_scenarios_entry.grid(row=19, column=4, sticky='w')
        self.num_scenarios_entry.bind("<FocusOut>", self.update_scenario_weights)

        # Update Configuration Button
        self.update_config_button = ttk.Button(self.inner_frame, text="Update", command=self.update_scenario_weights)
        self.update_config_button.grid(row=19, column=4, sticky='e',padx=5)
        self.update_config_button.configure(state='disabled')
        
        self.scenario_weights_entries = []
        self.scenario_weights_vars = []
        self.scenario_weights_labels = []
        
        # Navigation Frame at the bottom
        self.nav_frame = NavigationFrame(self, back_command=lambda: controller.show_frame("StartPage"), next_command=self.on_next_button)
        self.nav_frame.grid(row=1000, column=0, columnspan=4, sticky='ew')

        
    def get_input_data(self):
     # Start with the predefined variables.
     input_data = {
        'Step_Duration': self.Step_Duration_var.get(),
        'Min_Last_Step_Duration': self.Min_Step_Duration_var.get(),
        'MILP_Formulation': self.MILP_Formulation_var.get(),
        'Generator_Partial_Load': self.Generator_Partial_Load_var.get(),
        'Multiobjective_Optimization': self.Multiobjective_Optimization_var.get(),
        'Plot_Max_Cost': self.Plot_Max_Cost_var.get(),
        'Pareto_points': self.pareto_points_var.get(),
        'Pareto_solution': self.pareto_solution_var.get(),
        'Greenfield_Investment': self.Greenfield_Investment_var.get(),
        'Grid_Connection': self.Grid_Connection_var.get(),
        'Fuel_Specific_Cost_Calculation': self.Fuel_Specific_Cost_Calculation_var.get(),
        'Grid_Availability_Simulation': self.Grid_Availability_Simulation_var.get(),
        'Grid_Connection_Type': self.Grid_Connection_Type_var.get(),
        'WACC_Calculation': self.WACC_Calculation_var.get(),
        'Scenarios': self.num_scenarios_var.get()
     }

     # Loop through each entry for the WACC parameters and add them to the input_data dictionary.
     for var, label, entry in self.wacc_parameters_entries:
        param = label.cget("text")
        try: input_data[param] = var.get()
        except: continue
    # Check if the number of scenarios is more than one and add scenario weights
     num_scenarios = self.num_scenarios_var.get()
     if num_scenarios > 1:
        scenario_weights = [var.get() for var in self.scenario_weights_vars]
        input_data['Scenario_Weight'] = scenario_weights

     return input_data


        



