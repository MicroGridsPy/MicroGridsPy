import tkinter as tk
from tkinter import font as tkFont
from tkinter import ttk
from PIL import Image, ImageTk
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
        
            
    def toggle_investment_limit(self, *args):
        if self.Optimization_Goal_var.get() == 0:  # Assuming 0 is the value for 'Operation Cost'
            self.Investment_Cost_Limit_entry.config(state='normal')
            self.Investment_Cost_Limit_label.config(state='normal')
        else:
            self.Investment_Cost_Limit_entry.config(state='disabled')
            self.Investment_Cost_Limit_label.config(state='disabled')
        

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
        
    def on_next_button(self):
        advanced_page = self.controller.frames.get("AdvancedPage")
        grid_page = self.controller.frames.get("GridPage")
        advanced_page.Step_Duration_var.set(value=self.Years_var.get())
        advanced_page.backup_var.set(value=self.Years_var.get())
        grid_page.backup_var.set(value=self.Years_var.get())
        self.controller.show_frame("AdvancedPage")
        
    def confirm_and_advance(self):
        if messagebox.askyesno("Confirm Action", "Are you sure you want to proceed? You won't be able to come back and change these configuration options later."):
            self.controller.show_frame('RECalculationPage')
        else: pass


                
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
        self.title_label = ttk.Label(self.inner_frame, text="MicroGridsPy - Data Input", font=self.title_font,style='TLabel')
        self.title_label.grid(row=1, column=0, columnspan=1,sticky='w')

        # Section title: Model Configuration
        self.title_label = ttk.Label(self.inner_frame, text="Model Configuration", font=self.subtitle_font,style='TLabel')
        self.title_label.grid(row=2, column=0, columnspan=1, pady=10, sticky='w')
        

        # Descriptive Text Below the Images
        descriptive_text = ("Configure key aspects of the project's timeline and financial settings:\n")
        self.description_label = ttk.Label(self.inner_frame, text=descriptive_text, font=self.italic_font, wraplength=850, justify="left")
        self.description_label.grid(row=3, column=0, columnspan=2, sticky='w')


        # Model Configuration Parameters
        #-------------------------------

        # Total Project Duration 
        ttk.Label(self.inner_frame, text="Total Project Duration [Years]:", anchor='w',style='TLabel').grid(row=4, column=0, sticky='w')
        self.Years_var = tk.IntVar(value=20)
        vcmd = (self.register(self.validate_integer), '%P')
        self.Years_entry = ttk.Entry(self.inner_frame, textvariable=self.Years_var, validate='key', validatecommand=vcmd)
        self.Years_entry.grid(row=4, column=1, sticky='w')
        create_tooltip(self.Years_entry, "Enter the duration of the project in years")

        # Real_Discount_Rate
        ttk.Label(self.inner_frame, text="Discount Rate [-]:", anchor='w').grid(row=5, column=0, sticky='w')
        self.Real_Discount_Rate_var = tk.DoubleVar(value=0.1)
        vcmd = (self.register(self.validate_float), '%P')
        self.Real_Discount_Rate_entry = ttk.Entry(self.inner_frame, textvariable=self.Real_Discount_Rate_var,validate='key', validatecommand=vcmd)
        self.Real_Discount_Rate_entry.grid(row=5, column=1,sticky='w')
        create_tooltip(self.Real_Discount_Rate_entry, "Real discount rate accounting also for inflation")

        # Start Date Entry
        ttk.Label(self.inner_frame, text="Start Date of the Project:",anchor='w').grid(row=6, column=0, sticky='w')
        self.StartDate_var = tk.StringVar(value="01/01/2023 00:00:00")
        self.StartDate_entry = ttk.Entry(self.inner_frame, textvariable=self.StartDate_var)
        self.StartDate_entry.grid(row=6, column=1,sticky='w')
        create_tooltip(self.StartDate_entry, "MM/DD/YYYY HH:MM:SS format")
        
        separator = ttk.Separator(self.inner_frame, orient='horizontal')
        separator.grid(row=7, column=0, columnspan=4, sticky='ew', padx=5, pady=10)



        # Optimization Setup Parameters
        #-------------------------------

        # Section title: Optimization setup
        self.title_label = ttk.Label(self.inner_frame, text="Optimization setup", font=self.subtitle_font)
        self.title_label.grid(row=8, column=0, columnspan=1, pady=10, sticky='w')
        
        # Descriptive Text Below the Images
        descriptive_text = ("Configure essential optimization parameters to tailor the project's analytical model:\n")
        self.description_label = ttk.Label(self.inner_frame, text=descriptive_text, font=self.italic_font, wraplength=850, justify="left")
        self.description_label.grid(row=9, column=0, columnspan=2, sticky='w')
        
        # Periods
        ttk.Label(self.inner_frame, text="Time Resolution [periods/year]:",anchor='w').grid(row=10, column=0, sticky='w')
        self.Periods_var = tk.IntVar(value=8760)
        vcmd = (self.register(self.validate_integer), '%P')
        self.Periods_entry = ttk.Entry(self.inner_frame, textvariable=self.Periods_var,validate='key', validatecommand=vcmd)
        self.Periods_entry.grid(row=10, column=1,sticky='w')
        create_tooltip(self.Periods_entry, "Units of time for which the model performs calculations")
        # Bind the callback function to the change in "Time Resolution (periods)"
        self.Periods_var.trace('w', self.check_battery_independence)
        
        # Mapping of solver names to numeric values
        solver_mapping = {'Gurobi': 0, 'GLPK': 1}

        # Solver selection
        ttk.Label(self.inner_frame, text="Select Solver:", anchor='w').grid(row=10, column=2, sticky='w', padx=(30, 0))
        self.Solver_var = tk.StringVar()
        self.Solver_numeric_var = tk.IntVar()  # Variable to store the numeric value

        self.Solver_combobox = ttk.Combobox(self.inner_frame, textvariable=self.Solver_var, state='readonly')
        self.Solver_combobox['values'] = list(solver_mapping.keys())
        self.Solver_combobox.grid(row=10, column=3, sticky='w', padx=(30, 0))
        self.Solver_combobox.current(0)  # Default to first solver
        # Bind the callback function to the selection event
        # Callback function to update numeric variable
        def update_solver_numeric_var(event):
            solver_name = self.Solver_var.get()
            self.Solver_numeric_var.set(solver_mapping[solver_name])
        self.Solver_combobox.bind('<<ComboboxSelected>>', update_solver_numeric_var)



        # Optimization Goal
        self.Optimization_Goal_var = tk.IntVar(value=1)
        ttk.Label(self.inner_frame, text="Optimization Goal:",anchor='w').grid(row=11, column=0,sticky='w',ipady=10)
        self.Optimization_Goal_radio1 = ttk.Radiobutton(self.inner_frame, text="NPC", variable=self.Optimization_Goal_var, value=1)
        self.Optimization_Goal_radio1.grid(row=11, column=1, sticky='w')
        self.Optimization_Goal_radio0 = ttk.Radiobutton(self.inner_frame, text="Operation cost", variable=self.Optimization_Goal_var, value=0)
        self.Optimization_Goal_radio0.grid(row=11, column=1, sticky='e')
        create_tooltip(self.Optimization_Goal_radio1, "Net Present Cost oriented optimization")
        create_tooltip(self.Optimization_Goal_radio0, "Non-Actualized Operation Cost-oriented optimization")
        self.Optimization_Goal_var.trace('w', self.toggle_investment_limit)
        
        # Investment_Cost_Limit
        self.Investment_Cost_Limit_label = ttk.Label(self.inner_frame, text="Investment Cost Limit [USD]:",anchor='w')
        self.Investment_Cost_Limit_label.grid(row=11, column=2,sticky='w',padx=(30, 0))
        self.Investment_Cost_Limit_var = tk.DoubleVar(value=500000)
        vcmd = (self.register(self.validate_float), '%P')
        self.Investment_Cost_Limit_entry = ttk.Entry(self.inner_frame, textvariable=self.Investment_Cost_Limit_var,validate='key', validatecommand=vcmd)
        self.Investment_Cost_Limit_entry.grid(row=11, column=3,padx=(30, 0))
        create_tooltip(self.Investment_Cost_Limit_entry, "Upper limit to investment cost (considered only in case Optimization_Goal='Operation cost')")
        self.toggle_investment_limit()

        # Model Components
        self.Model_Components_var = tk.IntVar(value=0)
        ttk.Label(self.inner_frame, text="Backup Systems:", anchor='w').grid(row=13, column=0, sticky='w')
        self.Model_Components_radio0 = ttk.Radiobutton(self.inner_frame, text="Batteries and Generators", variable=self.Model_Components_var, value=0)
        self.Model_Components_radio0.grid(row=12, column=1, sticky='w')
        self.Model_Components_radio1 = ttk.Radiobutton(self.inner_frame, text="Batteries Only", variable=self.Model_Components_var, value=1)
        self.Model_Components_radio1.grid(row=13, column=1, sticky='w')
        self.Model_Components_radio2 = ttk.Radiobutton(self.inner_frame, text="Generators Only", variable=self.Model_Components_var, value=2)
        self.Model_Components_radio2.grid(row=14, column=1, sticky='w')
    
        
        # Descriptive Text Below the Images
        descriptive_text = ("")
        self.description_label = ttk.Label(self.inner_frame, text=descriptive_text, font=self.italic_font, wraplength=850, justify="left")
        self.description_label.grid(row=15, column=0, columnspan=2, sticky='w')
        
        # Renewable Penetration
        ttk.Label(self.inner_frame, text="Renewable Penetration [-]", anchor='w').grid(row=16, column=0, sticky='w')
        self.Renewable_Penetration_var = tk.DoubleVar(value=0.0)
        vcmd = (self.register(self.validate_fraction), '%P')
        self.Renewable_Penetration_entry = ttk.Entry(self.inner_frame, textvariable=self.Renewable_Penetration_var,validate='key', validatecommand=vcmd)
        self.Renewable_Penetration_entry.grid(row=16, column=1,sticky='w')
        create_tooltip(self.Renewable_Penetration_entry, "Minimum fraction of electricity produced by renewable sources")

        # Battery Independence
        ttk.Label(self.inner_frame, text="Battery Independence [Days]", anchor='w').grid(row=17, column=0, sticky='w')
        self.Battery_Independence_var = tk.IntVar(value=0)
        vcmd = (self.register(self.validate_integer), '%P')
        self.Battery_Independence_entry = ttk.Entry(self.inner_frame, textvariable=self.Battery_Independence_var,validate='key', validatecommand=vcmd)
        self.Battery_Independence_entry.grid(row=17, column=1,sticky='w')
        create_tooltip(self.Battery_Independence_entry, "Number of days of battery independence")

        # Lost Load Fraction
        ttk.Label(self.inner_frame, text="Lost Load Fraction [-]", anchor='w').grid(row=18, column=0, sticky='w')
        self.Lost_Load_Fraction_var = tk.DoubleVar(value=0.0)
        vcmd = (self.register(self.validate_float), '%P')
        self.Lost_Load_Fraction_entry = ttk.Entry(self.inner_frame, textvariable=self.Lost_Load_Fraction_var,validate='key', validatecommand=vcmd)
        self.Lost_Load_Fraction_entry.grid(row=18, column=1,sticky='w')
        create_tooltip(self.Lost_Load_Fraction_entry, "Maximum admissible loss of load as a fraction")
        self.Lost_Load_Fraction_var.trace('w', self.check_lost_load_fraction)

        # Lost Load Specific Cost
        self.Lost_Load_Specific_Cost_var = tk.DoubleVar(value=0.0)
        vcmd = (self.register(self.validate_float), '%P')
        self.Lost_Load_Specific_Cost_label = ttk.Label(self.inner_frame, text="Lost Load Specific Cost [USD/Wh]", anchor='w')
        self.Lost_Load_Specific_Cost_label.grid(row=19, column=0, sticky='w')
        self.Lost_Load_Specific_Cost_entry = ttk.Entry(self.inner_frame, textvariable=self.Lost_Load_Specific_Cost_var,validate='key', validatecommand=vcmd)
        self.Lost_Load_Specific_Cost_entry.grid(row=19, column=1,sticky='w')
        create_tooltip(self.Lost_Load_Specific_Cost_entry, "Value of the unmet load in USD per Wh.")
        self.Lost_Load_Specific_Cost_label.config(state='disabled')
        self.Lost_Load_Specific_Cost_entry.config(state='disabled')
        
      
        # Advanced Features Frame
        self.advanced_frame = tk.Frame(self.inner_frame, background='#FFFFFF')
        self.advanced_frame.grid(row=21, column=0, padx=10, pady=10, sticky='ew')

        # Advanced Features Icon
        advanced_icon = Image.open('Images/advanced_icon.png')  # Load the image
        resized_icon = advanced_icon.resize((30, 30), Image.Resampling.LANCZOS)  # Resize the image
        self.advanced_icon_image = ImageTk.PhotoImage(resized_icon)  
        self.advanced_icon_label = ttk.Label(self.advanced_frame, image=self.advanced_icon_image)  
        self.advanced_icon_label.grid(row=0, column=0, padx=5, pady=5)

        # Advanced Features Button
        self.advanced_button = ttk.Button(self.advanced_frame, text="Advanced Features", command=self.on_next_button)
        self.advanced_button.grid(row=0, column=1, padx=5, pady=5)

        # Keep a reference to the image to avoid garbage collection
        self.advanced_icon_label.image = self.advanced_icon_image

        
        # Navigation Frame at the bottom
        self.nav_frame = NavigationFrame(self, next_command=self.confirm_and_advance)
        self.nav_frame.grid(row=30, column=0, columnspan=4, sticky='ew')

        
    def get_input_data(self):
     # Start with the predefined variables.
     input_data = {
        'Years': self.Years_var.get(),
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
        'Solver': self.Solver_numeric_var.get()
     }

     return input_data


        



