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
    def __init__(self, parent, next_command, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        parent_row_index = 35

        # Span across all columns of the parent.
        self.grid(row=parent_row_index, column=0, sticky='ew', columnspan=parent.grid_size()[0])

        # Configure the background color to match the TopSectionFrame
        self.configure(background='#0f2c53', highlightbackground='#0f2c53', highlightthickness=2)

        # Grid configuration for the buttons within the NavigationFrame
        self.next_button = ttk.Button(self, text="Next", command=next_command)
        self.next_button.grid(row=0, column=2, sticky='e', padx=10, pady=10)

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

class StartPage(tk.Frame):
    
    def check_battery_independence(self, *args):
        # Get the value of "Time Resolution (periods)"
        time_resolution = self.Periods_var.get()
        
        # Disable "Battery Independence" if "Time Resolution" is not 8760
        if time_resolution != 8760:
            self.Battery_Independence_var.set(0)
            self.Battery_Independence_entry.config(state='disabled')
        else:
            self.Battery_Independence_entry.config(state='normal')
    def check_lost_load_fraction(self,*args):
        # Get the value of Lost Load Fraction
        fraction = self.Lost_Load_Fraction_var.get()
        # If the fraction is greater than 0, enable the Cost Entry and Label, else disable them
        if fraction > 0.0:
            self.Lost_Load_Specific_Cost_entry.config(state='normal')
            self.Lost_Load_Specific_Cost_label.config(state='normal')
        else:
            self.Lost_Load_Specific_Cost_entry.config(state='disabled')
            self.Lost_Load_Specific_Cost_label.config(state='disabled')
    
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
    def toggle_Plot_Max_Cost(self,*args):
            if self.Multiobjective_Optimization_var.get() == 1:
                self.Plot_Max_Cost_label.config(state='normal')
                self.Plot_Max_Cost_radio1.config(state='normal')
                self.Plot_Max_Cost_radio0.config(state='normal')
            else:
                self.Plot_Max_Cost_var.set(0)  # Reset to No if Multi-Objective Optimization is not selected
                self.Plot_Max_Cost_label.config(state='disabled')
                self.Plot_Max_Cost_radio1.config(state='disabled')
                self.Plot_Max_Cost_radio0.config(state='disabled')
        
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
        # First, update the GeneratorPage parameters
        milp_formulation = self.MILP_Formulation_var.get()
        partial_load = self.Generator_Partial_Load_var.get()
        brownfield = self.Greenfield_Investment_var.get()
        res_page = self.controller.frames.get("TechnologiesPage")
        generator_page = self.controller.frames.get("GeneratorPage")
        battery_page = self.controller.frames.get("BatteryPage")
        if milp_formulation == 1 and partial_load == 1:
            battery_page.toggle_milp_parameters()
            generator_page.toggle_milp_partial_parameters()
        if milp_formulation == 1 and partial_load == 0:
            battery_page.toggle_milp_parameters()
            generator_page.toggle_milp_parameters()
        if brownfield == 0:
            res_page.toggle_brownfield_parameters()
            battery_page.toggle_brownfield_parameters()
            generator_page.toggle_brownfield_parameters() 
        # Then, navigate to the RECalculationPage
        self.controller.show_frame("RECalculationPage")
        
    def update_scenario_weights(self, event=None):
        # Clear existing weight entries
        for entry in self.scenario_weights_entries:
            entry.destroy()
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
                entry = ttk.Entry(self.inner_frame, textvariable=var,validate='key', validatecommand=vcmd)
                entry.grid(row=21 + i, column=3, sticky='w')
                self.scenario_weights_vars.append(var)
                self.scenario_weights_entries.append(entry)
            self.scenario_weights_label.config(state='normal')
        else:
            # If only one scenario, add one entry with default value 1
            self.scenario_weight_var = tk.DoubleVar(value=1.0)
            self.scenario_weight_entry = ttk.Entry(self.inner_frame, textvariable=self.scenario_weight_var)
            self.scenario_weight_entry.grid(row=21, column=3, sticky='w')
            self.scenario_weight_entry.config(state='disabled')
            self.scenario_weights_label.config(state='disabled')
            
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
        # Resize the canvas_window to match the canvas size
        self.canvas.itemconfig(self.canvas_window, width=event.width, height=event.height)
        # Update the scrollable area to encompass the inner_frame after all content is placed
        self.canvas.after_idle(lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))


                
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

        # Section title: MicroGridsPy - Data Input
        self.title_label = ttk.Label(self.inner_frame, text="MicroGridsPy - Data Input", font=self.title_font,style='TLabel')
        self.title_label.grid(row=1, column=0, columnspan=1,sticky='w')

        # Section title: Model Configuration
        self.title_label = ttk.Label(self.inner_frame, text="Model Configuration", font=self.subtitle_font,style='TLabel')
        self.title_label.grid(row=2, column=0, columnspan=1, sticky='w')


        # Model Configuration Parameters
        #-------------------------------

        # Total Project Duration 
        ttk.Label(self.inner_frame, text="Total Project Duration [Years]:", anchor='w',style='TLabel').grid(row=3, column=0, sticky='w')
        self.Years_var = tk.IntVar(value=10)
        vcmd = (self.register(self.validate_integer), '%P')
        self.Years_entry = ttk.Entry(self.inner_frame, textvariable=self.Years_var, validate='key', validatecommand=vcmd)
        self.Years_entry.grid(row=3, column=1, sticky='w')
        create_tooltip(self.Years_entry, "Enter the duration of the project in years")

        # Step Duration
        ttk.Label(self.inner_frame, text="Step Duration [Years]:", anchor='w').grid(row=4, column=0, sticky='w')
        self.Step_Duration_var = tk.IntVar(value=1)
        vcmd = (self.register(self.validate_integer), '%P')
        self.Step_Duration_entry = ttk.Entry(self.inner_frame, textvariable=self.Step_Duration_var,validate='key', validatecommand=vcmd)
        self.Step_Duration_entry.grid(row=4, column=1,sticky='w')
        create_tooltip(self.Step_Duration_entry, "Duration of each investment decision step in which the project lifetime will be split")

        # Min_Last_Step_Duration
        ttk.Label(self.inner_frame, text="Minimum Last Step Duration [Years]:", anchor='w').grid(row=5, column=0, sticky='w')
        self.Min_Step_Duration_var = tk.IntVar(value=1)
        vcmd = (self.register(self.validate_integer), '%P')
        self.Min_Step_Duration_entry = ttk.Entry(self.inner_frame, textvariable=self.Min_Step_Duration_var,validate='key', validatecommand=vcmd)
        self.Min_Step_Duration_entry.grid(row=5, column=1,sticky='w')
        create_tooltip(self.Min_Step_Duration_entry, "Minimum duration of the last investment decision step, in case of non-homogeneous divisions of the project lifetime")

        # Real_Discount_Rate
        ttk.Label(self.inner_frame, text="Discount Rate [-]:", anchor='w').grid(row=6, column=0, sticky='w')
        self.Real_Discount_Rate_var = tk.DoubleVar(value=0.1)
        vcmd = (self.register(self.validate_float), '%P')
        self.Real_Discount_Rate_entry = ttk.Entry(self.inner_frame, textvariable=self.Real_Discount_Rate_var,validate='key', validatecommand=vcmd)
        self.Real_Discount_Rate_entry.grid(row=6, column=1,sticky='w')
        create_tooltip(self.Real_Discount_Rate_entry, "Real discount rate accounting also for inflation")

        # Start Date Entry
        ttk.Label(self.inner_frame, text="Start Date of the Project:",anchor='w').grid(row=7, column=0, sticky='w')
        self.StartDate_var = tk.StringVar(value="01/01/2023 00:00:00")
        self.StartDate_entry = ttk.Entry(self.inner_frame, textvariable=self.StartDate_var)
        self.StartDate_entry.grid(row=7, column=1,sticky='w')
        create_tooltip(self.StartDate_entry, "MM/DD/YYYY HH:MM:SS format")



        # Optimization Setup Parameters
        #-------------------------------

        # Section title: Optimization setup
        self.title_label = ttk.Label(self.inner_frame, text="Optimization setup", font=self.subtitle_font)
        self.title_label.grid(row=2, column=2, columnspan=1, pady=5, sticky='w', padx=(30, 0))  # Align to west (left), start from column 2

        # Renewable Penetration
        ttk.Label(self.inner_frame, text="Renewable Penetration [-]", anchor='w').grid(row=3, column=2, sticky='w',padx=(30, 0))
        self.Renewable_Penetration_var = tk.DoubleVar(value=0.0)
        vcmd = (self.register(self.validate_fraction), '%P')
        self.Renewable_Penetration_entry = ttk.Entry(self.inner_frame, textvariable=self.Renewable_Penetration_var,validate='key', validatecommand=vcmd)
        self.Renewable_Penetration_entry.grid(row=3, column=3,padx=(30, 0))
        create_tooltip(self.Renewable_Penetration_entry, "Minimum fraction of electricity produced by renewable sources")

        # Battery Independence
        ttk.Label(self.inner_frame, text="Battery Independence [Days]", anchor='w').grid(row=4, column=2, sticky='w',padx=(30, 0))
        self.Battery_Independence_var = tk.IntVar(value=0)
        vcmd = (self.register(self.validate_integer), '%P')
        self.Battery_Independence_entry = ttk.Entry(self.inner_frame, textvariable=self.Battery_Independence_var,validate='key', validatecommand=vcmd)
        self.Battery_Independence_entry.grid(row=4, column=3,padx=(30, 0))
        create_tooltip(self.Battery_Independence_entry, "Number of days of battery independence")

        # Lost Load Fraction
        ttk.Label(self.inner_frame, text="Lost Load Fraction [-]", anchor='w').grid(row=5, column=2, sticky='w',padx=(30, 0))
        self.Lost_Load_Fraction_var = tk.DoubleVar(value=0.0)
        vcmd = (self.register(self.validate_float), '%P')
        self.Lost_Load_Fraction_entry = ttk.Entry(self.inner_frame, textvariable=self.Lost_Load_Fraction_var,validate='key', validatecommand=vcmd)
        self.Lost_Load_Fraction_entry.grid(row=5, column=3,padx=(30, 0))
        create_tooltip(self.Lost_Load_Fraction_entry, "Maximum admissible loss of load as a fraction")
        self.Lost_Load_Fraction_var.trace('w', self.check_lost_load_fraction)

        # Lost Load Specific Cost
        self.Lost_Load_Specific_Cost_var = tk.DoubleVar(value=0.0)
        vcmd = (self.register(self.validate_float), '%P')
        self.Lost_Load_Specific_Cost_label = ttk.Label(self.inner_frame, text="Lost Load Specific Cost [USD/Wh]", anchor='w')
        self.Lost_Load_Specific_Cost_label.grid(row=6, column=2, sticky='w',padx=(30, 0))
        self.Lost_Load_Specific_Cost_entry = ttk.Entry(self.inner_frame, textvariable=self.Lost_Load_Specific_Cost_var,validate='key', validatecommand=vcmd)
        self.Lost_Load_Specific_Cost_entry.grid(row=6, column=3,padx=(30, 0))
        create_tooltip(self.Lost_Load_Specific_Cost_entry, "Value of the unmet load in USD per Wh.")
        self.Lost_Load_Specific_Cost_label.config(state='disabled')
        self.Lost_Load_Specific_Cost_entry.config(state='disabled')
        
        # Periods
        ttk.Label(self.inner_frame, text="Time Resolution [periods/year]:",anchor='w').grid(row=7, column=2, sticky='w',padx=(30, 0))
        self.Periods_var = tk.IntVar(value=8760)
        vcmd = (self.register(self.validate_integer), '%P')
        self.Periods_entry = ttk.Entry(self.inner_frame, textvariable=self.Periods_var,validate='key', validatecommand=vcmd)
        self.Periods_entry.grid(row=7, column=3,padx=(30, 0))
        create_tooltip(self.Periods_entry, "Units of time for which the model performs calculations")
        # Bind the callback function to the change in "Time Resolution (periods)"
        self.Periods_var.trace('w', self.check_battery_independence)


        #----------------------------------------------------------------------------------------------------------------------------

        # Optimization Goal
        self.Optimization_Goal_var = tk.IntVar(value=1)
        ttk.Label(self.inner_frame, text="Optimization Goal:",anchor='w').grid(row=9, column=0,sticky='w',ipady=20)
        self.Optimization_Goal_radio1 = ttk.Radiobutton(self.inner_frame, text="NPC", variable=self.Optimization_Goal_var, value=1)
        self.Optimization_Goal_radio1.grid(row=9, column=1, sticky='w')
        self.Optimization_Goal_radio0 = ttk.Radiobutton(self.inner_frame, text="Operation cost", variable=self.Optimization_Goal_var, value=0)
        self.Optimization_Goal_radio0.grid(row=9, column=1, sticky='e')
        create_tooltip(self.Optimization_Goal_radio1, "Net Present Cost oriented optimization")
        create_tooltip(self.Optimization_Goal_radio0, "Non-Actualized Operation Cost-oriented optimization")
        self.Optimization_Goal_var.trace('w', self.toggle_investment_limit)
        
        # Investment_Cost_Limit
        self.Investment_Cost_Limit_label = ttk.Label(self.inner_frame, text="Investment Cost Limit [USD]",anchor='w')
        self.Investment_Cost_Limit_label.grid(row=9, column=2,sticky='w',padx=(30, 0))
        self.Investment_Cost_Limit_var = tk.DoubleVar(value=500000)
        vcmd = (self.register(self.validate_float), '%P')
        self.Investment_Cost_Limit_entry = ttk.Entry(self.inner_frame, textvariable=self.Investment_Cost_Limit_var,validate='key', validatecommand=vcmd)
        self.Investment_Cost_Limit_entry.grid(row=9, column=3,padx=(30, 0))
        create_tooltip(self.Investment_Cost_Limit_entry, "Upper limit to investment cost (considered only in case Optimization_Goal='Operation cost')")
        self.toggle_investment_limit()

        # Model Components
        self.Model_Components_var = tk.IntVar(value=0)
        ttk.Label(self.inner_frame, text="Backup Systems:", anchor='w').grid(row=10, column=0, sticky='w')
        self.Model_Components_radio0 = ttk.Radiobutton(self.inner_frame, text="Batteries and Generators", variable=self.Model_Components_var, value=0)
        self.Model_Components_radio0.grid(row=10, column=1, sticky='w')
        self.Model_Components_radio1 = ttk.Radiobutton(self.inner_frame, text="Batteries Only", variable=self.Model_Components_var, value=1)
        self.Model_Components_radio1.grid(row=11, column=1, sticky='w')
        self.Model_Components_radio2 = ttk.Radiobutton(self.inner_frame, text="Generators Only", variable=self.Model_Components_var, value=2)
        self.Model_Components_radio2.grid(row=12, column=1, sticky='w')
        

        
        # Model Advanced Features
        #-------------------------------

        self.title_label = ttk.Label(self.inner_frame, text="Advanced Features", font=self.subtitle_font)
        self.title_label.grid(row=13, column=0, columnspan=1, pady=10, sticky='w')


        # MILP Formulation
        self.MILP_Formulation_var = tk.IntVar(value=0)
        ttk.Label(self.inner_frame, text="Model Formulation:", anchor='w').grid(row=14, column=0, sticky='w')
        self.MILP_Formulation_radio0 = ttk.Radiobutton(self.inner_frame, text="LP", variable=self.MILP_Formulation_var, value=0)
        self.MILP_Formulation_radio0.grid(row=14, column=1, sticky='w')
        self.MILP_Formulation_radio1 = ttk.Radiobutton(self.inner_frame, text="MILP", variable=self.MILP_Formulation_var, value=1)
        self.MILP_Formulation_radio1.grid(row=14, column=1, sticky='e')
        self.MILP_Formulation_var.trace('w', self.toggle_generator_partial_load)
        create_tooltip(self.MILP_Formulation_radio0, "Linear Programming")
        create_tooltip(self.MILP_Formulation_radio1, "Multiple Integers Linear Programming")

        # Generator Partial Load
        self.Generator_Partial_Load_var = tk.IntVar(value=0)
        self.Generator_Partial_Load_label = ttk.Label(self.inner_frame, text="Generator Partial Load:", anchor='w')
        self.Generator_Partial_Load_label.grid(row=15, column=0, sticky='w')
        self.Generator_Partial_Load_checkbutton = ttk.Checkbutton(self.inner_frame, text="Activate", variable=self.Generator_Partial_Load_var, onvalue=1, offvalue=0)
        self.Generator_Partial_Load_checkbutton.grid(row=15, column=1, sticky='w')
        self.Generator_Partial_Load_label.config(state='disabled')
        self.Generator_Partial_Load_checkbutton.config(state='disabled')
        self.toggle_generator_partial_load()


        # Multiobjective Optimization
        self.Multiobjective_Optimization_var = tk.IntVar(value=0)
        ttk.Label(self.inner_frame, text="Multi-Objective Optimization:", anchor='w').grid(row=16, column=0, sticky='w')
        self.Multiobjective_Optimization_checkbutton = ttk.Checkbutton(self.inner_frame, text="Activate", variable=self.Multiobjective_Optimization_var, onvalue=1, offvalue=0)
        self.Multiobjective_Optimization_checkbutton.grid(row=16, column=1, sticky='w')
        create_tooltip(self.Multiobjective_Optimization_checkbutton, "Optimization of NPC/operation cost and CO2 emissions")
        self.Multiobjective_Optimization_var.trace('w', self.toggle_Plot_Max_Cost)

        # Define the variable for Plot Max Cost options
        self.Plot_Max_Cost_var = tk.IntVar(value=0)
        self.Plot_Max_Cost_label = ttk.Label(self.inner_frame, text="Plot Max Cost:", anchor='w')
        self.Plot_Max_Cost_label.grid(row=17, column=0, sticky='w')
        self.Plot_Max_Cost_radio1 = ttk.Radiobutton(self.inner_frame, text="Yes", variable=self.Plot_Max_Cost_var, value=1, state='disabled')
        self.Plot_Max_Cost_radio1.grid(row=17, column=1, sticky='w')
        create_tooltip(self.Plot_Max_Cost_radio1, "Pareto curve has to include the point at maxNPC/maxOperationCost")
        self.Plot_Max_Cost_radio0 = ttk.Radiobutton(self.inner_frame, text="No", variable=self.Plot_Max_Cost_var, value=0, state='disabled')
        self.Plot_Max_Cost_radio0.grid(row=17, column=1, sticky='e')
        self.Plot_Max_Cost_label.config(state='disabled')
        self.toggle_Plot_Max_Cost()


        # Greenfield
        self.Greenfield_Investment_var = tk.IntVar(value=1)
        ttk.Label(self.inner_frame, text="Type of Investment:",anchor='w').grid(row=18, column=0,sticky='w')
        self.Greenfield_radio = ttk.Radiobutton(self.inner_frame, text="Greenfield", variable=self.Greenfield_Investment_var, value=1).grid(row=18, column=1, sticky='w')
        self.Brownfield_radio = ttk.Radiobutton(self.inner_frame, text="Brownfield", variable=self.Greenfield_Investment_var, value=0).grid(row=18, column=1, sticky='e')


        # Grid Connection Radiobuttons
        self.Grid_Connection_var = tk.IntVar(value=0)
        self.Grid_Connection_var.trace('w', self.toggle_grid_options)
        ttk.Label(self.inner_frame, text="Grid Connection:", anchor='w').grid(row=19, column=0, sticky='w')
        self.Grid_Connection_radio = ttk.Radiobutton(self.inner_frame, text="On-grid", variable=self.Grid_Connection_var, value=1)
        self.Grid_Connection_radio.grid(row=19, column=1, sticky='w')
        create_tooltip(self.Grid_Connection_radio, "Simulate grid connection during project lifetime")
        ttk.Radiobutton(self.inner_frame, text="Off-grid", variable=self.Grid_Connection_var, value=0).grid(row=19, column=1, sticky='e')

        # Grid Availability Simulation
        self.Grid_Availability_Simulation_var = tk.IntVar(value=0)
        self.Grid_Availability_Simulation_label = ttk.Label(self.inner_frame, text="Grid Availability:", anchor='w')
        self.Grid_Availability_Simulation_label.grid(row=20, column=0, sticky='w')
        self.Grid_Availability_Simulation_label.config(state='disabled')
        self.Grid_Availability_Simulation_checkbutton = ttk.Checkbutton(self.inner_frame, text="Activate", variable=self.Grid_Availability_Simulation_var, onvalue=1, offvalue=0)
        create_tooltip(self.Grid_Availability_Simulation_checkbutton, "Simulate grid availability matrix")
        self.Grid_Availability_Simulation_checkbutton.grid(row=20, column=1, sticky='w')
        self.Grid_Availability_Simulation_checkbutton.config(state='disabled')

        # Grid Connection Type Radiobuttons
        self.Grid_Connection_Type_var = tk.IntVar(value=0)
        self.Grid_Connection_Type_label = ttk.Label(self.inner_frame, text="Grid Connection Type:", anchor='w', state='disabled')
        self.Grid_Connection_Type_label.grid(row=21, column=0, sticky='w')
        self.Grid_Connection_Type_radio1 = ttk.Radiobutton(self.inner_frame, text="Buy Only", variable=self.Grid_Connection_Type_var, value=0, state='disabled')
        self.Grid_Connection_Type_radio1.grid(row=21, column=1, sticky='w')
        self.Grid_Connection_Type_radio2 = ttk.Radiobutton(self.inner_frame, text="Buy/Sell", variable=self.Grid_Connection_Type_var, value=1, state='disabled')
        self.Grid_Connection_Type_radio2.grid(row=21, column=1, sticky='e')
        self.toggle_grid_options()


        # WACC Calculation Checkbutton
        self.WACC_Calculation_var = tk.IntVar(value=0)
        self.WACC_Calculation_label = ttk.Label(self.inner_frame, text="WACC Calculation:", anchor='w')
        self.WACC_Calculation_label.grid(row=14, column=2, sticky='w',padx=(30, 0))
        self.WACC_Calculation_checkbutton = ttk.Checkbutton(self.inner_frame, text="Activate", variable=self.WACC_Calculation_var, onvalue=1, offvalue=0, command=self.toggle_wacc_parameters)
        self.WACC_Calculation_checkbutton.grid(row=14, column=3, sticky='w')
        
        vcmd = (self.register(self.validate_float), '%P')

        # WACC Parameters
        wacc_parameters = {
            "cost_of_equity": 0.12,
            "cost_of_debt": 0.11,
            "tax": 0.02,
            "equity_share": 0.10,
            "debt_share": 0.90
            }

        # Create labels and entries for WACC parameters in the adjusted columns
        self.wacc_parameters_entries = []
        for i, (param, value) in enumerate(wacc_parameters.items(), start=15):  # Adjust the starting row accordingly
            label = ttk.Label(self.inner_frame, text=param)
            label.grid(row=i, column=2, sticky='w',padx=(40, 0))  # Place the labels in column 3
            var = tk.DoubleVar(value=value)
            entry = ttk.Entry(self.inner_frame, textvariable=var, state='normal', validate='key', validatecommand=vcmd)  # Initially set state to 'normal' to show the value
            entry.var = var
            entry.grid(row=i, column=3, sticky='w')  # Place the entry fields in column 4
            label.config(state='disabled')  # Then disable the entry
            entry.config(state='disabled')  # Then disable the entry
            self.wacc_parameters_entries.append((var, label, entry))
            
        # Number of Scenarios
        self.num_scenarios_var = tk.IntVar(value=1)
        self.num_scenarios_label = ttk.Label(self.inner_frame, text="Number of Scenarios:", anchor='w')
        self.num_scenarios_label.grid(row=20, column=2, sticky='w', padx=(30, 0))
        vcmd = (self.register(self.validate_integer), '%P')
        self.num_scenarios_entry = ttk.Entry(self.inner_frame, textvariable=self.num_scenarios_var,validate='key', validatecommand=vcmd)
        self.num_scenarios_entry.grid(row=20, column=3, sticky='w')
        self.num_scenarios_entry.bind("<FocusOut>", self.update_scenario_weights)
        
        # Initialize Scenario Weights with one entry and disabled
        self.scenario_weights_label = ttk.Label(self.inner_frame, text="Scenario Weights:", anchor='w', state='disabled')
        self.scenario_weights_label.grid(row=21, column=2, sticky='w', padx=(30, 0))
        self.scenario_weight_var = tk.DoubleVar(value=1.0)
        self.scenario_weight_entry = ttk.Entry(self.inner_frame, textvariable=self.scenario_weight_var, state='disabled')
        self.scenario_weight_entry.grid(row=21, column=3, sticky='w')

        # Update Configuration Button
        self.update_config_button = ttk.Button(self.inner_frame, text="Update", command=self.update_scenario_weights)
        self.update_config_button.grid(row=20, column=4, sticky='w')

        # Scenario Weights
        self.scenario_weights_vars = []
        self.scenario_weights_entries = []
        
        # Navigation Frame at the bottom
        self.nav_frame = NavigationFrame(self, self.on_next_button)
        self.nav_frame.grid(row=1000, column=0, columnspan=4, sticky='ew')

        
    def get_input_data(self):
     # Start with the predefined variables.
     input_data = {
        'Years': self.Years_var.get(),
        'Step_Duration': self.Step_Duration_var.get(),
        'Min_Last_Step_Duration': self.Min_Step_Duration_var.get(),
        'Discount_Rate': self.Real_Discount_Rate_var.get(),
        'Start_Date': self.StartDate_var.get(),
        'Periods': self.Periods_var.get(),
        'Renewable_Penetration': self.Renewable_Penetration_var.get(),
        'Battery_Independence': self.Battery_Independence_var.get(),
        'Lost_Load_Fraction': self.Lost_Load_Fraction_var.get(),
        'Lost_Load_Specific_Cost': self.Lost_Load_Specific_Cost_var.get(),
        'Investment_Cost_Limit': self.Investment_Cost_Limit_var.get(),
        'Optimization_Goal': self.Optimization_Goal_var.get(),
        'Model_Components': self.Model_Components_var.get(),
        'MILP_Formulation': self.MILP_Formulation_var.get(),
        'Generator_Partial_Load': self.Generator_Partial_Load_var.get(),
        'Multiobjective_Optimization': self.Multiobjective_Optimization_var.get(),
        'Plot_Max_Cost': self.Plot_Max_Cost_var.get(),
        'Greenfield_Investment': self.Greenfield_Investment_var.get(),
        'Grid_Connection': self.Grid_Connection_var.get(),
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


        



