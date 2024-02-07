import tkinter as tk
from tkinter import font as tkFont
from tkinter import ttk
from PIL import Image, ImageTk

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
    

class ArchetypesPage(tk.Frame):
    
    def load_and_display_image(self):
        # Load the image (adjust the path to your image file)
        original_image = Image.open("Images/Archetypes.png")
        # Resize the image (change the width and height as needed)
        resized_image = original_image.resize((475, 250), Image.Resampling.LANCZOS)  # Example: (200, 200)
        # Convert the image to PhotoImage
        tk_image = ImageTk.PhotoImage(resized_image)
        # Create a label to display the image
        image_label = ttk.Label(self.inner_frame, image=tk_image)
        image_label.image = tk_image  # Keep a reference to avoid garbage collection
        image_label.grid(row=0, column=2, sticky='nsew')  # Adjust grid position as needed

        # Adjust the column configuration to make the image visible
        image_label.grid(row=4, column=1, rowspan=14, padx=(30,0), sticky='nsew')
    
    def get_input_data(self):
        input_data = {'Demand_Profile_Generation': self.demand_option_var.get()}
        for var, label, entry in self.demand_calc_params_entries:
            param = label.cget("text")
            input_data[param] = var.get()  # Retrieve the value from the entry widget
        return input_data
    
    def toggle_demand_calc_parameters(self, *args):
        if self.demand_option_var.get() == 1:
            state = 'normal'
        else:
            state = 'disabled'
        
        for var, label, entry in self.demand_calc_params_entries:
            label.config(state=state)
            entry.config(state=state)
            
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
        
    def setup_warning(self):
        # Load the warning icon image
        warning_icon = Image.open('Images/attention.png')  
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
        self.warning_label = ttk.Label(warning_frame, text="WARNING: If Import Exogenously, you must provide the Demand Time Series Data as CSV file located in 'Inputs' folder (refer to the online documentation for more details https://microgridspy-documentation.readthedocs.io/en/latest/)",  wraplength=700, justify="left")
        self.warning_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Ensure the text spans the rest of the grid
        warning_frame.grid_columnconfigure(1, weight=1)
                
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
        self.top_section.grid(row=0, column=0, sticky='ew', columnspan=self.grid_size()[0])

        # Setup the scrollable area
        self.setup_scrollable_area()
        
        self.load_and_display_image()
        
        # Add NavigationFrame at the very bottom
        self.nav_frame = NavigationFrame(self, back_command=lambda: controller.show_frame("RECalculationPage"), next_command=lambda: controller.show_frame("TechnologiesPage"))
        self.nav_frame.grid(row=2, column=0, sticky='ew', columnspan=self.grid_size()[0])

        # Define custom font
        self.title_font = tkFont.Font(family="Helvetica", size=16, weight="bold")
        self.subtitle_font = tkFont.Font(family="Helvetica", size=12,underline=True)
        self.italic_font = tkFont.Font(family="Helvetica", size=10, slant="italic")

        # Section title: Model Configuration
        self.title_label = ttk.Label(self.inner_frame, text="Demand Time Series Calculation", font=self.title_font)
        self.title_label.grid(row=1, column=0, columnspan=1, pady=10, sticky='w')
        
        self.intro_label = ttk.Label(self.inner_frame, text="Generate the load curve demand using build-in Sub-Sahara Africa village archetypes:", font=self.italic_font, wraplength=850, justify="left")
        self.intro_label.grid(row=2, column=0, columnspan=2, pady=10, sticky='w')
        
        # Radio button options for demand profile
        self.demand_option_var = tk.IntVar(value=0)
        ttk.Label(self.inner_frame, text="Demand Profile Option:", anchor='w').grid(row=3, column=0, sticky='w')

        self.demand_profile_radio = ttk.Radiobutton(self.inner_frame, text="Generate Endogenously", variable=self.demand_option_var, value=1, command=self.toggle_demand_calc_parameters)
        self.demand_profile_radio.grid(row=3, column=0, sticky='e')
        create_tooltip(self.demand_profile_radio, "Select to simulate a load demand profile with built-in demand archetypes")

        self.exogenous_demand_radio = ttk.Radiobutton(self.inner_frame, text="Import Exogenously", variable=self.demand_option_var, value=0, command=self.toggle_demand_calc_parameters)
        self.exogenous_demand_radio.grid(row=4, column=0, padx=18.5, sticky='e')
        create_tooltip(self.exogenous_demand_radio, "Select to provide demand time series data using the csv file")
        
        self.intro_label = ttk.Label(self.inner_frame, text="Endogenous Load Demand parameters:", font=self.italic_font, wraplength=850, justify="left")
        self.intro_label.grid(row=5, column=0, columnspan=2, pady=10, sticky='w')

        # Define and grid the parameters as labels and entries
        self.demand_calc_params = {
            "demand_growth": "5", 
            "cooling_period": "AY",
            "h_tier1": "252",
            "h_tier2": "160",
            "h_tier3": "50",
            "h_tier4": "36",
            "h_tier5": "5",
            "schools": "1",
            "hospital_1": "0",
            "hospital_2": "1",
            "hospital_3": "0",
            "hospital_4": "0",
            "hospital_5": "0"
            }
        
        tooltips = {
            "demand_growth": "Yearly expected average percentage variation of the demand [%]",
            "cooling_period": "Cooling period (NC = No Cooling; AY = All Year; OM = Oct-Mar; AS = Apr-Sept)",
            "h_tier1": "Number of users in tier 1",
            "h_tier2": "Number of users in tier 2",
            "h_tier3": "Number of users in tier 3",
            "h_tier4": "Number of users in tier 4",
            "h_tier5": "Number of users in tier 5",
            "schools": "Number of schools",
            "hospital_1": "Number of hospitals in tier 1",
            "hospital_2": "Number of hospitals in tier 2",
            "hospital_3": "Number of hospitals in tier 3",
            "hospital_4": "Number of hospitals in tier 4",
            "hospital_5": "Number of hospitals in tier 5"
            }

        self.demand_calc_params_entries = []
        for i, (param, value) in enumerate(self.demand_calc_params.items(), start=6):  # Adjust the starting row
            label_text = param
            label = ttk.Label(self.inner_frame, text=label_text)
            label.grid(row=i, column=0, sticky='w')
            var = tk.StringVar(value=value)
            entry = ttk.Entry(self.inner_frame, textvariable=var)
            entry.grid(row=i, column=0, sticky='e')
            # Initially disable the entries
            label.config(state='disabled')
            entry.config(state='disabled')

            # Add tooltip
            tooltip_text = tooltips.get(param, "No description available.")
            create_tooltip(entry, tooltip_text)

            self.demand_calc_params_entries.append((var, label, entry))

            

        # Create the warning label and grid it
        self.setup_warning()
        
        




