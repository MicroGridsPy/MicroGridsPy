import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from tkinter import font as tkFont
import sys
import os
import threading
import webbrowser

# Modify Python path
current_directory = os.path.dirname(os.path.abspath(__file__))
model_directory = os.path.join(current_directory, '..', 'Model')
sys.path.append(model_directory)

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
        
        # Load GitHub icon
        github_icon = Image.open('Images/github_icon.png').resize((20, 20), Image.LANCZOS)
        self.github_icon_image = ImageTk.PhotoImage(github_icon)
        github_button = tk.Label(self, image=self.github_icon_image)
        github_button.bind("<Button-1>", lambda e: self.open_github())
        github_button.pack(side='right', padx=10, pady=10)
        create_tooltip(github_button, "Go to the GitHub Repository")

        # Load documentation icon
        doc_icon = Image.open('Images/doc_icon.png').resize((20, 20), Image.LANCZOS)
        self.doc_icon_image = ImageTk.PhotoImage(doc_icon)
        doc_button = tk.Label(self, image=self.doc_icon_image)
        doc_button.bind("<Button-1>", lambda e: self.open_documentation())
        doc_button.pack(side='right', padx=10, pady=10)
        create_tooltip(doc_button, "Go to the online Documentation")

        self.pack(side='bottom', fill='x')

    def open_github(self):
        webbrowser.open_new("https://github.com/MicroGridsPy/MicroGridsPy")

    def open_documentation(self):
        webbrowser.open_new("https://microgridspy-docs.readthedocs.io/en/latest/")
        
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
        if P == "" or P.isdigit():
            return True
        self.bell()
        return False

    def update_output(self, message):
        self.after(0, lambda: self.output_text.insert(tk.END, message))
        self.after(0, lambda: self.output_text.see(tk.END))

    def clear_output(self):
        self.output_text.delete('1.0', tk.END)

    def generate_plot(self):
        from Plots import DispatchPlot, SizePlot, CashFlowPlot
        try:
            plot_scenario = 1
            plot_date = self.start_date_entry.get() or '01/01/2023 00:00:00'
            plot_time = int(self.plot_time_entry.get()) if self.plot_time_entry.get() else 3
            plot_format = 'png'
            plot_resolution = 400

            DispatchPlot(self.instance, self.Time_Series, plot_scenario, plot_date, plot_time, plot_resolution, plot_format)
            SizePlot(self.instance, self.Results, plot_resolution, plot_format)
            CashFlowPlot(self.instance, self.Results, plot_resolution, plot_format)
        finally:
            self.update_output("Plots ready to show\n")
            self.show_dispatch_plot_button['state'] = 'normal'
            self.size_plot_button['state'] = 'normal'
            self.inv_plot_button['state'] = 'normal'
            self.om_plot_button['state'] = 'normal'
            if self.instance.Multiobjective_Optimization.value:
                self.show_pareto_curve_button.configure(state='normal')

    def show_plot(self, plot_name, window_title, size=(700, 400)):
        current_directory = os.path.dirname(os.path.abspath(__file__))
        results_directory = os.path.join(current_directory, '..', 'Results/Plots')
        plot_path = os.path.join(results_directory, plot_name)
        plot_image = Image.open(plot_path)
        plot_photo = ImageTk.PhotoImage(plot_image.resize(size))

        plot_window = tk.Toplevel(self)
        plot_window.title(window_title)

        plot_label = tk.Label(plot_window, image=plot_photo)
        plot_label.image = plot_photo
        plot_label.pack()

    def show_size_plot(self):
        self.show_plot('SizePlot.png', "Size Plot", (500, 500))

    def show_investment_plot(self):
        self.show_plot('Investment Costs Plot.png', "Investment Costs Plot", (700, 700))

    def show_om_plot(self):
        self.show_plot('O&M Costs Plot.png', "O&M Costs Plot", (700, 700))

    def show_dispatch_plot(self):
        self.show_plot('DispatchPlot.png', "Dispatch Plot", (700, 400))

    def show_pareto_plot(self):
        self.show_plot('ParetoCurve.png', "Pareto Curve", (700, 400))

    def run_model_thread(self):
        try:
            self.run_button.configure(state='disabled')
            self.generate_plot_button.configure(state='disabled')
            import time
            from pyomo.environ import AbstractModel
            from Model_Creation import Model_Creation
            from Model_Resolution import Model_Resolution
            from Results import ResultsSummary, TimeSeries, PrintResults

            start = time.time()
            model = AbstractModel()
            Model_Creation(model)
            self.instance = Model_Resolution(model)
            self.Time_Series = TimeSeries(self.instance)
            optimization_goal = self.instance.Optimization_Goal.extract_values()[None]
            self.Results = ResultsSummary(self.instance, optimization_goal, self.Time_Series)
            PrintResults(self.instance, self.Results)
            elapsed = time.time() - start
            self.update_output(f'\n\nModel run complete (overall time: {round(elapsed, 0)} s, {round(elapsed / 60, 1)} m)\n')
        finally:
            self.generate_plot_button.configure(state='normal')
            self.run_button.configure(state='normal')

    def run_model(self):
        self.clear_output()
        thread = threading.Thread(target=self.run_model_thread)
        thread.start()

    def setup_parameters_frame(self):
        self.title_label = ttk.Label(self.parameters_frame, text="Plot the Results:", font=("Helvetica", 16))
        self.title_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

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
        self.generate_plot_button = ttk.Button(self.plots_frame, text="Generate Plots:", command=self.generate_plot, state='disabled')
        self.generate_plot_button.grid(row=0, column=0, padx=5, pady=5)

        self.show_dispatch_plot_button = ttk.Button(self.plots_frame, text="Show Dispatch Plot", command=self.show_dispatch_plot, state='disabled')
        self.show_dispatch_plot_button.grid(row=0, column=1, padx=5, pady=5)

        self.size_plot_button = ttk.Button(self.plots_frame, text="Show Size Plot", command=self.show_size_plot, state='disabled')
        self.size_plot_button.grid(row=0, column=2, padx=5, pady=5)

        self.inv_plot_button = ttk.Button(self.plots_frame, text="Investment Costs Plot", command=self.show_investment_plot, state='disabled')
        self.inv_plot_button.grid(row=0, column=3, padx=5, pady=5)

        self.om_plot_button = ttk.Button(self.plots_frame, text="O&M Costs Plot", command=self.show_om_plot, state='disabled')
        self.om_plot_button.grid(row=0, column=4, padx=5, pady=5)

        self.show_pareto_curve_button = ttk.Button(self.plots_frame, text="Show Pareto Curve", command=self.show_pareto_plot, state='disabled')
        self.show_pareto_curve_button.grid(row=0, column=5, padx=5, pady=5)

    def setup_output_frame(self):
        self.output_text = tk.Text(self.output_frame, height=15)
        self.output_text.pack(side='left', fill='both', expand=True)
        output_scrollbar = ttk.Scrollbar(self.output_frame, command=self.output_text.yview)
        output_scrollbar.pack(side='right', fill='y')
        self.output_text['yscrollcommand'] = output_scrollbar.set

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(background='white')

        university_name = "MicroGridsPy "
        self.top_section = TopSectionFrame(self, university_name)
        self.top_section.pack(side='top', fill='x')

        self.run_button_frame = ttk.Frame(self)
        self.run_button_frame.pack(side='top', fill='x', padx=10, pady=5)

        self.title_label = ttk.Label(self.run_button_frame, text="Run the Model:", font=("Helvetica", 16))
        self.title_label.pack(side='left', padx=10)

        run_icon = Image.open('Images/run.png').resize((20, 20), Image.Resampling.LANCZOS)
        self.run_icon_image = ImageTk.PhotoImage(run_icon)
        ttk.Label(self.run_button_frame, image=self.run_icon_image).pack(side='left')

        self.run_button = ttk.Button(self.run_button_frame, text="RUN", command=self.run_model)
        self.run_button.pack(side='left', padx=20, pady=5)

        self.intro_label_frame = ttk.Frame(self)
        self.intro_label_frame.pack(side='top', fill='x', padx=10, pady=5)

        italic_font = tkFont.Font(family="Helvetica", size=10, slant="italic")
        intro_label = ttk.Label(self.intro_label_frame, text="Output panel to visualize model operation, solver log and key results:", font=italic_font)
        intro_label.pack(side='left', padx=5)

        self.output_frame = tk.Frame(self, highlightbackground="black", highlightthickness=1)
        self.output_frame.pack(side='top', fill='both', expand=True, padx=10, pady=5)
        self.setup_output_frame()
        
        self.output_redirection = RedirectOutput(self.output_text)
        sys.stdout = self.output_redirection
        sys.stderr = self.output_redirection
        
        self.parameters_frame = ttk.Frame(self)
        self.parameters_frame.pack(side='top', fill='x', padx=10, pady=5)
        self.setup_parameters_frame()

        self.plots_frame = ttk.Frame(self)
        self.plots_frame.pack(side='top', fill='x', padx=10, pady=5)
        self.setup_plots_frame()

        # Navigation Frame
        self.nav_frame = NavigationFrame(self)
        self.nav_frame.pack(side='bottom', fill='x')
        

