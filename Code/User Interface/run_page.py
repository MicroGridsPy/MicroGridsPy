import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from tkinter import font as tkFont
import sys
import os
import threading

# Modify Python path
current_directory = os.path.dirname(os.path.abspath(__file__))
model_directory = os.path.join(current_directory, '..', 'Model')
sys.path.append(model_directory)

class TopSectionFrame(tk.Frame):
    def __init__(self, parent, university_name, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.configure(background='#0f2c53')
        self.name_label = tk.Label(self, text=university_name, font=("Arial", 10, "italic"), fg="white", background='#0f2c53')
        self.name_label.pack(pady=15, side='right')
        self.pack(side='top', fill='x')

class NavigationFrame(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.configure(background='#0f2c53', highlightbackground='#0f2c53', highlightthickness=2)
        self.exit_button = ttk.Button(self, text="Exit", command=parent.destroy)
        self.exit_button.pack(side='right', padx=10, pady=10)
        self.pack(side='bottom', fill='x')

class RedirectOutput:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def write(self, message):
        # Use 'after' method for thread-safe updates
        self.text_widget.after(0, lambda: self.text_widget.insert(tk.END, message))
        self.text_widget.after(0, lambda: self.text_widget.see(tk.END))

    def flush(self):
        self.stdout.flush()
        self.stderr.flush()
        
class RunPage(tk.Frame):
    
    def validate_integer(self, P):
        if P == "": return True
        if P.isdigit():
            return True
        else:
            self.bell()  # System bell if invalid input
            return False
    
    def update_output(self, message):
        def _update():
            self.output_text.insert(tk.END, message)
            self.output_text.see(tk.END)  # Auto-scroll to the end
        self.after(0, _update)
        
    def clear_output(self):
        self.output_text.delete('1.0', tk.END)
        
    def generate_plot(self):
        
            from Plots import DispatchPlot, SizePlot, CashFlowPlot
            try:
             PlotScenario = 1                     # Plot scenario
             PlotDate = self.start_date_entry.get() if self.start_date_entry.get() else '01/01/2023 00:00:00'
             PlotTime = int(self.plot_time_entry.get()) if self.start_date_entry.get() else 3
             PlotFormat = 'png'                   # Desired extension of the saved file (Valid formats: png, svg, pdf)
             PlotResolution = 400                 # Plot resolution in dpi (useful only for .png files, .svg and .pdf output a vector plot)

             DispatchPlot(self.instance, self.Time_Series,PlotScenario, PlotDate,PlotTime, PlotResolution, PlotFormat)  
             SizePlot(self.instance,self.Results, PlotResolution, PlotFormat)
             CashFlowPlot(self.instance, self.Results, PlotResolution, PlotFormat)
            finally: 
                self.update_output("Plots ready to show\n")
                self.show_dispatch_plot_button['state'] = 'normal'
                self.size_plot_button['state'] = 'normal'
                self.cash_plot_button['state'] = 'normal'
                if self.instance.Multiobjective_Optimization.value: self.show_pareto_curve_button.configure(state='normal')
        
    def show_size_plot(self):
        # Load the saved plot image
        current_directory = os.path.dirname(os.path.abspath(__file__))
        results_directory = os.path.join(current_directory, '..', 'Results/Plots')
        plot_path = os.path.join(results_directory, 'SizePlot.png')
        plot_image = Image.open(plot_path)
        plot_photo = ImageTk.PhotoImage(plot_image)
        
        resized_image = plot_image.resize((500, 500))
        plot_photo = ImageTk.PhotoImage(resized_image)

        # Create a new window or use an existing frame
        plot_window = tk.Toplevel(self)
        plot_window.title("Size Plot")

        # Display the image in a label widget
        plot_label = tk.Label(plot_window, image=plot_photo)
        plot_label.image = plot_photo  # Keep a reference!
        plot_label.pack()
        
    def show_cash_plot(self):
        # Load the saved plot image
        current_directory = os.path.dirname(os.path.abspath(__file__))
        results_directory = os.path.join(current_directory, '..', 'Results/Plots')
        plot_path = os.path.join(results_directory, 'CashFlowPlot.png')
        plot_image = Image.open(plot_path)
        plot_photo = ImageTk.PhotoImage(plot_image)
        
        resized_image = plot_image.resize((700, 700))
        plot_photo = ImageTk.PhotoImage(resized_image)

        # Create a new window or use an existing frame
        plot_window = tk.Toplevel(self)
        plot_window.title("Cash Flow Plot")

        # Display the image in a label widget
        plot_label = tk.Label(plot_window, image=plot_photo)
        plot_label.image = plot_photo  # Keep a reference!
        plot_label.pack()
        
    def show_dispatch_plot(self):
        # Load the saved plot image
        current_directory = os.path.dirname(os.path.abspath(__file__))
        results_directory = os.path.join(current_directory, '..', 'Results/Plots')
        plot_path = os.path.join(results_directory, 'DispatchPlot.png')
        plot_image = Image.open(plot_path)
        plot_photo = ImageTk.PhotoImage(plot_image)
        
        resized_image = plot_image.resize((700, 400))
        plot_photo = ImageTk.PhotoImage(resized_image)

        # Create a new window or use an existing frame
        plot_window = tk.Toplevel(self)
        plot_window.title("Dispatch Plot")

        # Display the image in a label widget
        plot_label = tk.Label(plot_window, image=plot_photo)
        plot_label.image = plot_photo  # Keep a reference!
        plot_label.pack()
        
    def show_pareto_plot(self):
        # Load the saved plot image
        current_directory = os.path.dirname(os.path.abspath(__file__))
        results_directory = os.path.join(current_directory, '..', 'Results/Plots')
        plot_path = os.path.join(results_directory, 'ParetoCurve.png')
        plot_image = Image.open(plot_path)
        plot_photo = ImageTk.PhotoImage(plot_image)
        
        resized_image = plot_image.resize((700, 400))
        plot_photo = ImageTk.PhotoImage(resized_image)

        # Create a new window or use an existing frame
        plot_window = tk.Toplevel(self)
        plot_window.title("Pareto Curve")

        # Display the image in a label widget
        plot_label = tk.Label(plot_window, image=plot_photo)
        plot_label.image = plot_photo  # Keep a reference!
        plot_label.pack()
        
    def stop_simulation(self):
        self.stop_simulation_flag = True
        
    def run_model_thread(self):
        try:
            self.run_button.configure(state='disabled')
            self.generate_plot_button.configure(state='disabled')
            import time
            from pyomo.environ import AbstractModel
            from Model_Creation import Model_Creation
            from Model_Resolution import Model_Resolution
            from Results import ResultsSummary, TimeSeries, PrintResults
            
            start = time.time()      # Start time counter
            if self.stop_simulation_flag == False:
                model = AbstractModel()  # Define type of optimization problem
            else: print('Model interrupted by the user\n')
            if self.stop_simulation_flag == False:
                Model_Creation(model)    # Creation of the Sets, parameters and variables
            else: print('Model interrupted by the user\n')
            # Resolve the model instance
            if self.stop_simulation_flag == False:
                self.instance = Model_Resolution(model)
            else: print('Model interrupted by the user\n')
            if self.stop_simulation_flag == False:
                self.Time_Series = TimeSeries(self.instance)
            else: print('Model interrupted by the user\n')
            if self.stop_simulation_flag == False:
                Optimization_Goal = self.instance.Optimization_Goal.extract_values()[None]
            else: print('Model interrupted by the user\n')
            if self.stop_simulation_flag == False:
                self.Results = ResultsSummary(self.instance, Optimization_Goal, self.Time_Series)
            else: print('Model interrupted by the user\n')
            if self.stop_simulation_flag == False:
                PrintResults(self.instance, self.Results)
            else: print('Model interrupted by the user\n')
            end = time.time()
            elapsed = end - start
            elapsed_message = f'\n\nModel run complete (overall time: {round(elapsed, 0)} s, {round(elapsed / 60, 1)} m)\n'
            self.update_output(elapsed_message)
        finally:
            self.generate_plot_button.configure(state='normal')
            self.run_button.configure(state='normal')
            self.stop_simulation_flag == True
            
    def run_model(self):
        self.clear_output()
        # Running the long task in a separate thread
        thread = threading.Thread(target=self.run_model_thread)
        thread.start()

    def setup_parameters_frame(self):
        
        self.title_label = ttk.Label(self.parameters_frame, text="Plot the Results:", font=("Helvetica", 16))
        self.title_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Parameters Initialization Frame setup with grid layout
        ttk.Label(self.parameters_frame, text="Start Date for Plot:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.start_date_entry = ttk.Entry(self.parameters_frame)
        self.start_date_entry.insert(0, "01/01/2023 00:00:00")
        self.start_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self.parameters_frame, text="Number of days to plot:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        vcmd = (self.register(self.validate_integer), '%P')
        self.plot_time_entry = ttk.Entry(self.parameters_frame, validate='key', validatecommand=vcmd)
        self.plot_time_entry.insert(0, "3")
        self.plot_time_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")


    def setup_plots_frame(self):
        # Generate Plot button
        self.generate_plot_button = ttk.Button(self.plots_frame, text="Generate Plots:", command=self.generate_plot,state='disabled')
        self.generate_plot_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Plots Frame setup with grid layout
        self.show_dispatch_plot_button = ttk.Button(self.plots_frame, text="Show Dispatch Plot", command=self.show_dispatch_plot, state='disabled')
        self.show_dispatch_plot_button.grid(row=0, column=1, padx=5, pady=5)

        self.size_plot_button = ttk.Button(self.plots_frame, text="Show Size Plot", command=self.show_size_plot, state='disabled')
        self.size_plot_button.grid(row=0, column=2, padx=5, pady=5)

        self.cash_plot_button = ttk.Button(self.plots_frame, text="Cash Flow Plot", command=self.show_cash_plot, state='disabled')
        self.cash_plot_button.grid(row=0, column=3, padx=5, pady=5)

        # Placeholder for Pareto Curve Button (if needed)
        self.show_pareto_curve_button = ttk.Button(self.plots_frame, text="Show Pareto Curve", command=self.show_pareto_plot, state='disabled')
        self.show_pareto_curve_button.grid(row=0, column=4, padx=5, pady=5)
        
    def setup_output_frame(self):
        self.output_text = tk.Text(self.output_frame, height=15)
        self.output_text.pack(side='left', fill='both', expand=True)
        self.output_scrollbar = ttk.Scrollbar(self.output_frame, command=self.output_text.yview)
        self.output_scrollbar.pack(side='right', fill='y')
        self.output_text['yscrollcommand'] = self.output_scrollbar.set

        
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.stop_simulation_flag = False
        
        # Add Top Section first
        university_name = "MicroGridsPy "
        self.top_section = TopSectionFrame(self, university_name)
        self.top_section.pack(side='top', fill='x')

        self.run_button_frame = ttk.Frame(self)
        self.run_button_frame.pack(side='top', fill='x', padx=10, pady=5)
        
        self.title_label = ttk.Label(self.run_button_frame, text="Run the Model:", font=("Helvetica", 16))
        self.title_label.pack(side='left', padx=10)
        
        # Add Icon to Run Button Frame
        run_icon = Image.open('Images/run.png')  # Load the image
        run_icon = run_icon.resize((20, 20), Image.Resampling.LANCZOS)  # Resize the image
        self.run_icon_image = ImageTk.PhotoImage(run_icon)  
        self.run_icon_label = ttk.Label(self.run_button_frame, image=self.run_icon_image)  
        self.run_icon_label.pack(side='left')   
        
        self.run_button = ttk.Button(self.run_button_frame, text="RUN", command=self.run_model)
        self.run_button.pack(side='left', padx=20, pady=5)
        
        # Add Icon to Run Button Frame
        pause_icon = Image.open('Images/pause.png')  # Load the image
        pause_icon = pause_icon.resize((20, 20), Image.Resampling.LANCZOS)  # Resize the image
        self.pause_icon_image = ImageTk.PhotoImage(pause_icon)  
        self.pause_icon_label = ttk.Label(self.run_button_frame, image=self.pause_icon_image)  
        self.pause_icon_label.pack(side='left') 
        
        self.quit_button = ttk.Button(self.run_button_frame, text="Stop", command=self.stop_simulation)
        self.quit_button.pack(side='left', padx=5, pady=5)
        

        self.intro_label_frame = ttk.Frame(self)
        self.intro_label_frame.pack(side='top', fill='x', padx=10, pady=5)

        self.italic_font = tkFont.Font(family="Helvetica", size=10, slant="italic")
        self.intro_label = ttk.Label(self.intro_label_frame, text="Output panel to visualize model operation, solver log and key results:", font=self.italic_font)
        self.intro_label.pack(side='left', padx=5)

        self.output_frame = tk.Frame(self, highlightbackground="black", highlightthickness=1)
        self.output_frame.pack(side='top', fill='both', expand=True, padx=10, pady=5)
        self.setup_output_frame()
        
        '''
        self.output_redirection = RedirectOutput(self.output_text)
        sys.stdout = self.output_redirection
        sys.stderr = self.output_redirection
        '''
        self.parameters_frame = ttk.Frame(self)
        self.parameters_frame.pack(side='top', fill='x', padx=10, pady=5)
        self.setup_parameters_frame()
        
        self.plots_frame = ttk.Frame(self)
        self.plots_frame.pack(side='top', fill='x', padx=10, pady=5)
        self.setup_plots_frame()

        # Navigation Frame
        self.nav_frame = NavigationFrame(self)
        self.nav_frame.pack(side='bottom', fill='x')
        

