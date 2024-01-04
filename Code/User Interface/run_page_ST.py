import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
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
        self.quit_button = ttk.Button(self, text="Stop", command=parent.quit)
        self.quit_button.pack(side='right', padx=10, pady=10)
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
                if self.instance.Multiobjective_Optimization.value:  # Assuming this is how you check the condition
                    self.show_pareto_curve_button = ttk.Button(self.controls_frame, text="Show Pareto Curve", command=self.show_pareto_plot, state='normal')
                    self.show_pareto_curve_button.pack(side='left', pady=5, padx=5)
        
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
        
        resized_image = plot_image.resize((500, 500))
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
        
    def run_model_thread(self):

            import time
            from pyomo.environ import AbstractModel
            from Model_Creation import Model_Creation
            from Model_Resolution import Model_Resolution
            from Results import ResultsSummary, TimeSeries, PrintResults
            
            start = time.time()      # Start time counter
            model = AbstractModel()  # Define type of optimization problem
            Model_Creation(model)    # Creation of the Sets, parameters and variables.
            # Resolve the model instance
            self.instance = Model_Resolution(model)
            self.Time_Series = TimeSeries(self.instance)
            Optimization_Goal = self.instance.Optimization_Goal.extract_values()[None]
            self.Results = ResultsSummary(self.instance, Optimization_Goal, self.Time_Series)
            PrintResults(self.instance, self.Results, self.update_output)
             
            end = time.time()
            elapsed = end - start
            elapsed_message = f'\n\nModel run complete (overall time: {round(elapsed, 0)} s, {round(elapsed / 60, 1)} m)\n'
            self.update_output(elapsed_message)
            
    def run_model(self):
        self.clear_output()
        # Running the long task in a separate thread
        thread = threading.Thread(target=self.run_model_thread)
        thread.start()


        
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        
        # Add Top Section first
        university_name = "MicroGridsPy"
        self.top_section = TopSectionFrame(self, university_name)
        self.top_section.pack(side='top', fill='x')

        # Main frame to contain all other frames except for the navigation frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(side='top', fill='both', expand=True, padx=10, pady=10)

        # Frame for the controls
        self.controls_frame = ttk.Frame(self.main_frame)
        self.controls_frame.pack(side='top', fill='x', expand=False)

        # Frame for the output
        self.output_frame = ttk.Frame(self.main_frame)
        self.output_frame.pack(side='top', fill='both', expand=True)

        # Setup the text widget for output
        self.output_text = tk.Text(self.output_frame, height=15)
        self.output_text.pack(side='left', fill='both', expand=True)

        # Scrollbar for the output text widget
        self.output_scrollbar = ttk.Scrollbar(self.output_frame, command=self.output_text.yview)
        self.output_scrollbar.pack(side='right', fill='y')
        self.output_text['yscrollcommand'] = self.output_scrollbar.set
        
        
        # Redirect output
        self.output_redirection = RedirectOutput(self.output_text)
        sys.stdout = self.output_redirection
        sys.stderr = self.output_redirection
        
        
        # Title label
        self.title_label = ttk.Label(self.controls_frame, text="Run the Model", font=("Helvetica", 16))
        self.title_label.pack(side='top', pady=10)

        # Run button
        self.run_button = ttk.Button(self.controls_frame, text="RUN", command=self.run_model)
        self.run_button.pack(side='top', pady=10)

        # Start Date Entry for Plot
        start_date_frame = ttk.Frame(self.controls_frame)
        start_date_frame.pack(fill='x', pady=5)
        ttk.Label(start_date_frame, text="Start Date for Plot:").pack(side='left')
        self.start_date_entry = ttk.Entry(start_date_frame)
        self.start_date_entry.insert(0, "01/01/2023 00:00:00")
        self.start_date_entry.pack(side='left')

        # Number of days to plot
        plot_time_frame = ttk.Frame(self.controls_frame)
        plot_time_frame.pack(fill='x', pady=5)
        ttk.Label(plot_time_frame, text="Number of days to plot:").pack(side='left')
        vcmd = (self.register(self.validate_integer), '%P')
        self.plot_time_entry = ttk.Entry(plot_time_frame, validate='key', validatecommand=vcmd)
        self.plot_time_entry.insert(0, "3")
        self.plot_time_entry.pack(side='left')

        # Frame for the Generate Plot button
        self.plot_button_frame = ttk.Frame(self.controls_frame)
        self.plot_button_frame.pack(side='top', fill='x', pady=5)

        # Generate Plot button
        self.generate_plot_button = ttk.Button(self.plot_button_frame, text="Generate Plots", command=self.generate_plot)
        self.generate_plot_button.pack(side='left', pady=5)
        self.show_plots_frame = ttk.Frame(self.controls_frame)
        self.show_plots_frame.pack(side='left', fill='x', pady=5)

        # Show Dispatch Plot button (initially disabled)
        self.show_dispatch_plot_button = ttk.Button(self.controls_frame, text="Show Dispatch Plot", command=self.show_dispatch_plot, state='disabled')
        self.show_dispatch_plot_button.pack(side='left', pady=5)
        
        # Show Size Plot button (initially disabled)
        self.size_plot_button = ttk.Button(self.show_plots_frame, text="Show Size Plot", command=self.show_size_plot, state='disabled')
        self.size_plot_button.pack(side='left', pady=5, padx=5)

        # Show Cash Flow Plot button (initially disabled)
        self.cash_plot_button = ttk.Button(self.show_plots_frame, text="Cash Flow Plot", command=self.show_cash_plot,state='disabled')
        self.cash_plot_button.pack(side='left', pady=5, padx=5)

        # Navigation frame at the very bottom of the window, outside the main_frame
        self.nav_frame = NavigationFrame(self)
        self.nav_frame.pack(side='bottom', fill='x')

        # Ensure that the main_frame does not expand vertically anymore than necessary
        self.pack_propagate(False)
        

