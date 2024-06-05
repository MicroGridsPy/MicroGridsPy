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

class GridPage(tk.Frame):
    
    def on_confirm_and_next(self):
        all_filled = True
        for var, label, entry in self.grid_params_entries:
            try : value = str(entry.get())
            except: value = ''
            if not value.strip():  
                #entry.config(bg='red')
                label_text = label.cget("text")
                messagebox.showwarning("Warning", f"Please fill in the required field for {label_text}.")
                entry.focus_set()  # Set focus to the empty entry
                all_filled = False
                break  
    
        if not all_filled: return
        if self.Year_Grid_Connection_var.get() > self.backup_var.get():
                tk.messagebox.showerror("Error", "Year Grid Connection can not exceed the Total Project Duration")
                return False
        self.controller.show_frame("PlotPage")
    
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
        
    def get_validation_command(self, param, default):
        if isinstance(default, int):
            return (self.register(self.validate_integer), '%P')
        elif isinstance(default, float):
            return (self.register(self.validate_float), '%P')
        return None
        
    def display_extra_parameters(self):
        extra_params = [
            ("Grid_Average_Number_Outages", 43.48, "Average number of outages in the national grid in a year (0 to simulate ideal power grid)"),
            ("Grid_Average_Outage_Duration", 455.0, "Average duration of an outage [min] (0 to simulate ideal power grid)")]

        for param, value, tooltip_text in extra_params:
            row = len(self.grid_params_entries) + 4  # Calculate the next row number dynamically
            # Create and grid the label for the extra parameter
            label = ttk.Label(self.inner_frame, text=param)
            label.grid(row=row, column=0, sticky='w')
            # Create and grid the entry for the extra parameter
            var = tk.DoubleVar(value=value)
            vcmd = self.get_validation_command(param, value)
            entry = ttk.Entry(self.inner_frame, textvariable=var,validate='key', validatecommand=vcmd)
            entry.grid(row=row, column=1, sticky='w')
            create_tooltip(entry, tooltip_text)  # Assuming create_tooltip is a pre-defined function

            # Store the label and entry in the list for future reference or clearing
            self.grid_params_entries.append((var, label, entry))
        
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
        self.nav_frame = NavigationFrame(self, back_command=controller.show_previous_page_from_grid, next_command=self.on_confirm_and_next)
        self.nav_frame.grid(row=2, column=0, sticky='ew', columnspan=self.grid_size()[0])

        # Define custom font
        self.title_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.subtitle_font = tkFont.Font(family="Helvetica", size=12,underline=True)
        
        self.title_label = ttk.Label(self.inner_frame, text="On-Grid Model", font=self.title_font)
        self.title_label.grid(row=1, column=0, columnspan=1, pady=10, sticky='w')
        
        self.italic_font = tkFont.Font(family="Helvetica", size=10, slant="italic")
        
        self.intro_label = ttk.Label(self.inner_frame, text="Simulate the connection with the main grid taking into account its costs and availability:", font=self.italic_font, wraplength=850, justify="left")
        self.intro_label.grid(row=2, column=0, columnspan=2, pady=10, sticky='w')
        
        self.backup_var = tk.IntVar(value=20)

        ttk.Label(self.inner_frame, text="Year Grid Connection:", anchor='w',style='TLabel').grid(row=3, column=0, sticky='w')
        self.Year_Grid_Connection_var = tk.IntVar(value=1)
        vcmd = (self.register(self.validate_integer), '%P')
        self.Year_Grid_Connection_entry = ttk.Entry(self.inner_frame, textvariable=self.Year_Grid_Connection_var, validate='key', validatecommand=vcmd)
        self.Year_Grid_Connection_entry.grid(row=3, column=1, sticky='w')
        create_tooltip(self.Year_Grid_Connection_entry, "Year at which microgrid is connected to the national grid (starting from 1)")
        
        # Define and grid the parameters as labels and entries
        self.grid_params = {
            "Grid_Sold_El_Price": 0.0,
            "Grid_Purchased_El_Price": 0.138,
            "Grid_Distance": 0.5,
            "Grid_Connection_Cost": 14000.0,
            "Grid_Maintenance_Cost": 0.025,
            "Maximum_Grid_Power": 80.0,
            "Grid_Average_Number_Outages": 43.48,
            "Grid_Average_Outage_Duration": 455.0,
            "National_Grid_Specific_CO2_emissions": 0.1495
        }
        
        self.grid_params_tooltips = {
            "Grid_Sold_El_Price": "Price at which electricity is sold to the grid [USD/kWh]",
            "Grid_Purchased_El_Price": "Price at which electricity is purchased from the grid [USD/kWh]",
            "Grid_Distance": "Distance from grid connection point [km]",
            "Grid_Connection_Cost": "Investment cost of grid connection, i.e., extension of power line + transformer costs [USD/km]",
            "Grid_Maintenance_Cost": "O&M cost for maintenance of the power line and transformer as a fraction of investment cost [-]",
            "Maximum_Grid_Power": "Maximum active power that can be injected/withdrawn to/from the grid [kW]",
            "Grid_Average_Number_Outages": "Average number of outages in the national grid in a year (0 to simulate ideal power grid)",
            "Grid_Average_Outage_Duration": "Average duration of an outage [min] (0 to simulate ideal power grid)",
            "National_Grid_Specific_CO2_emissions": "Specific CO2 emissions by the considered national grid [kgCO2/kWh]"
            }

        self.grid_params_entries = []
        for i, (param, value) in enumerate(self.grid_params.items(), start=4):
            label = ttk.Label(self.inner_frame, text=param)
            label.grid(row=i, column=0, sticky='w')
            var = tk.DoubleVar(value=value)
            vcmd = self.get_validation_command(param, value)
            entry = ttk.Entry(self.inner_frame, textvariable=var,validate='key', validatecommand=vcmd)
            entry.grid(row=i, column=1, sticky='w')
            tooltip_text = self.grid_params_tooltips.get(param, "No description available")
            create_tooltip(entry, tooltip_text)
            self.grid_params_entries.append((var, label, entry))
            
        
        
    def get_input_data(self):
        grid_data = {}
        grid_data['Year_Grid_Connection'] = self.Year_Grid_Connection_var.get()
        for var, label, entry in self.grid_params_entries:
            param = label.cget("text")
            grid_data[param] = var.get()  # Retrieve the value from the entry widget
        return grid_data


