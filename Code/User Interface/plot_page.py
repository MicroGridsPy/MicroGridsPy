import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont

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

class PlotPage(tk.Frame):
    
    def update_legend_color(self, combobox, legend_label):
        color_name = combobox.get()
        color_hex = self.color_options.get(color_name, "")  # Default to empty if color not found
        legend_label.config(background=color_hex)
        
    def refresh_page(self):
        res_sources = int(self.controller.get_res_sources_value())
        gen_types = int(self.controller.get_generator_types_value())
        self.setup_page(res_sources, gen_types)

    def setup_page(self, res_sources, gen_types):
        self.res_color_entries.clear()
        self.gen_color_entries.clear()
        self.single_color_entries.clear()

        row_start = 7
        row_start = self.create_multiple_color_inputs_res("RES_Colors", "Orange", row_start, res_sources)
        row_start = self.create_multiple_color_inputs_gen("Generator_Colors", "Blue", row_start, gen_types)
        self.create_single_color_inputs(row_start)

    def create_multiple_color_inputs_res(self, label_text, default_color_text, row_start, num_sources):
        # Remove existing widgets if the number of sources has changed
        if len(self.res_color_entries) != num_sources:
            for widget in self.inner_frame.grid_slaves():
                if int(widget.grid_info()["row"]) == row_start:
                    widget.destroy()
            self.res_color_entries.clear()

        ttk.Label(self.inner_frame, text=label_text).grid(row=row_start, column=0, pady=5, sticky='w')

        for i in range(num_sources):
            # Configure the column position for combobox and color label
            combobox_column = 2 * i + 1  # Offset by 2*i for each combobox
            label_column = combobox_column + 1  # Place label right next to the combobox

            # Create and grid the color combobox
            color_combobox = ttk.Combobox(self.inner_frame, values=list(self.color_options.keys()), width=15)
            if label_text == "RES_Colors" and i == 1:
                color_combobox.set("Teal")
            else:
                color_combobox.set(default_color_text)
            color_combobox.grid(row=row_start, column=combobox_column, padx=5, pady=2)

            # Create and grid the legend label
            default_color_hex = self.color_options[default_color_text]
            if label_text == "RES_Colors" and i == 1:
                default_color_hex = self.color_options["Teal"]
            legend_label = ttk.Label(self.inner_frame, background=default_color_hex, width=2)
            legend_label.grid(row=row_start, column=label_column, padx=2, pady=2)
            self.res_color_entries.append(default_color_hex)

            # Function to update the color entry when selection changes
            def update_color_entry(event, index=i, combobox=color_combobox, legend=legend_label):
                selected_color_name = combobox.get()
                hex_color = self.color_options.get(selected_color_name, "")
                if index < len(self.res_color_entries):
                    self.res_color_entries[index] = hex_color  # Update the entry at the specific index
                else:
                    self.res_color_entries.append(hex_color)  # Append new color if index exceeds the list
                self.update_legend_color(combobox, legend)

            color_combobox.bind("<<ComboboxSelected>>", update_color_entry)

        return row_start + 1
    
    def create_multiple_color_inputs_gen(self, label_text, default_color_text, row_start, num_sources):
        # Remove existing widgets if the number of sources has changed
        if len(self.gen_color_entries) != num_sources:
            for widget in self.inner_frame.grid_slaves():
                if int(widget.grid_info()["row"]) == row_start:
                    widget.destroy()
            self.gen_color_entries.clear()

        ttk.Label(self.inner_frame, text=label_text).grid(row=row_start, column=0, pady=5, sticky='w')

        for i in range(num_sources):
            # Configure the column position for combobox and color label
            combobox_column = 2 * i + 1  # Offset by 2*i for each combobox
            label_column = combobox_column + 1  # Place label right next to the combobox

            # Create and grid the color combobox
            color_combobox = ttk.Combobox(self.inner_frame, values=list(self.color_options.keys()), width=15)
            if label_text == "RES_Colors" and i == 1:
                color_combobox.set("Teal")
            else:
                color_combobox.set(default_color_text)
            color_combobox.grid(row=row_start, column=combobox_column, padx=5, pady=2)

            # Create and grid the legend label
            default_color_hex = self.color_options[default_color_text]
            if label_text == "RES_Colors" and i == 1:
                default_color_hex = self.color_options["Teal"]
            legend_label = ttk.Label(self.inner_frame, background=default_color_hex, width=2)
            legend_label.grid(row=row_start, column=label_column, padx=2, pady=2)
            self.gen_color_entries.append(default_color_hex)

            # Function to update the color entry when selection changes
            def update_color_entry(event, index=i, combobox=color_combobox, legend=legend_label):
                selected_color_name = combobox.get()
                hex_color = self.color_options.get(selected_color_name, "")
                if index < len(self.gen_color_entries):
                    self.gen_color_entries[index] = hex_color  # Update the entry at the specific index
                else:
                    self.gen_color_entries.append(hex_color)  # Append new color if index exceeds the list
                self.update_legend_color(combobox, legend)

            color_combobox.bind("<<ComboboxSelected>>", update_color_entry)

        return row_start + 1


    def create_single_color_inputs(self, row_start):
     for param, default_color_text in self.plot_params_defaults.items():
        ttk.Label(self.inner_frame, text=param).grid(row=row_start, column=0, pady=5, sticky='w')
            
        color_combobox = ttk.Combobox(self.inner_frame, values=list(self.color_options.keys()), width=15)
        color_combobox.set(default_color_text)
        color_combobox.grid(row=row_start, column=1, padx=5, pady=2)
        
        # Create a legend label
        default_color_hex = self.color_options[default_color_text]
        legend_label = ttk.Label(self.inner_frame, background=default_color_hex, width=2)
        legend_label.grid(row=row_start, column=2, padx=2, pady=2)

        self.single_color_entries[param] = default_color_hex

        # Function to update the color entry when selection changes
        def update_color_entry(event, param=param, combobox=color_combobox,legend=legend_label):
            selected_color_name = combobox.get()
            self.single_color_entries[param] = self.color_options.get(selected_color_name)
            self.update_legend_color(combobox, legend)

        # Bind combobox selection change to update the color entry
        color_combobox.bind("<<ComboboxSelected>>", update_color_entry)

        row_start += 1

     return row_start
 
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
        self.nav_frame = NavigationFrame(self, back_command=controller.show_previous_page_from_plot, next_command=controller.save_all_data)
        self.nav_frame.grid(row=2, column=0, sticky='ew', columnspan=self.grid_size()[0])
        
        # Define custom font
        self.title_font = tkFont.Font(family="Helvetica", size=16, weight="bold")
        self.subtitle_font = tkFont.Font(family="Helvetica", size=12,underline=True)

        # Section title: Model Configuration
        self.title_label = ttk.Label(self.inner_frame, text="Plot Colors", font=self.title_font)
        self.title_label.grid(row=1, column=0,pady=10, sticky='w')
        
        self.italic_font = tkFont.Font(family="Helvetica", size=10, slant="italic")
        
        self.intro_label = ttk.Label(self.inner_frame, text="Select the plot colors from the drop-down menu:", font=self.italic_font, wraplength=850, justify="left")
        self.intro_label.grid(row=2, column=0, columnspan=2, pady=10, sticky='w')
        
        self.color_options = {
            'Orange': '#FF8800', 
            'Blue': '#00509D', 
            'Turquoise': '#4CC9F0',
            'Red': '#F21B3F', 
            'Yellow': '#FFD500', 
            'Green': '#008000', 
            'Purple': '#800080',
            'Pink': '#FFC0CB',        
            'Teal': '#008080',        
            'Magenta': '#FF00FF',
            'Lime': '#00FF00',
            'Sapphire': '#0F52BA',    
            'Amber': '#FFBF00',
            'Cyan': '#00FFFF',
            'Violet': '#7F00FF',
            'Indigo': '#4B0082',
            'Mint': '#3EB489',
            'Coral': '#FF7F50',
            'Maroon': '#800000',                   
        }
        
        # Define default color parameters and their initial values
        self.plot_params_defaults = {
            "Battery_Color": 'Turquoise',
            "Lost_Load_Color": 'Red',
            "Curtailment_Color": 'Yellow',
            "Energy_To_Grid_Color": 'Green',
            "Energy_From_Grid_Color": 'Purple'
        }

        # Initialize the data structures to hold the entry widgets
        self.res_color_entries = []
        self.gen_color_entries = []
        self.single_color_entries = {}
        

    def get_input_data(self):
     plot_data = {}
     plot_data['RES_Colors'] = [color.lstrip('#') for color in self.res_color_entries]
     plot_data['Generator_Colors'] = [color.lstrip('#') for color in self.gen_color_entries]
     for param, entry in self.single_color_entries.items():
        plot_data[param] = entry.lstrip('#')
     return plot_data


