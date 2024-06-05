import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
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
    def __init__(self, parent, next_command, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        parent_row_index = 35

        # Span across all columns of the parent.
        self.grid(row=parent_row_index, column=0, sticky='ew', columnspan=parent.grid_size()[0])

        # Configure the background color to match the TopSectionFrame
        self.configure(background='#0f2c53', highlightbackground='#0f2c53', highlightthickness=2)

        # Grid configuration for the buttons within the NavigationFrame
        self.next_button = ttk.Button(self, text="Let's start!", command=next_command)
        self.next_button.grid(row=0, column=2, sticky='e', padx=10, pady=10)
    

        # Configure the grid within NavigationFrame to align the buttons properly
        self.grid_columnconfigure(0, weight=1)  # The column for the back button, if used
        self.grid_columnconfigure(1, weight=0)  # The column for the next button
        self.grid_columnconfigure(2, weight=1)

class InitialPage(tk.Frame):
    
    def load_and_display_image(self):
        # Load the image (adjust the path to your image file)
        original_image = Image.open("Images/Mgpy_Scheme.png")
        # Resize the image (change the width and height as needed)
        resized_image = original_image.resize((350, 200), Image.Resampling.LANCZOS)  # Example: (200, 200)
        # Convert the image to PhotoImage
        tk_image = ImageTk.PhotoImage(resized_image)
        # Create a label to display the image
        image_label = ttk.Label(self.inner_frame, image=tk_image)
        image_label.image = tk_image  # Keep a reference to avoid garbage collection
        image_label.grid(row=3, column=0, padx=10, sticky='n')  # Adjust grid position as needed


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
        self.load_and_display_image()

        # Add NavigationFrame at the very bottom
        self.nav_frame = NavigationFrame(self, next_command=lambda: controller.show_frame("StartPage"))
        self.nav_frame.grid(row=2, column=0, sticky='ew', columnspan=self.grid_size()[0])

        # Define custom font
        self.title_font = tkFont.Font(family="Helvetica", size=18, weight="bold")
        self.subtitle_font = tkFont.Font(family="Helvetica", size=12,underline=True)
        
        self.title_label = ttk.Label(self.inner_frame, text="Welcome to MicroGridsPy!", font=self.title_font)
        self.subtitle_label = ttk.Label(self.inner_frame, text="Bottom-up, open-source optimization model for energy scaling and dispatch in mini-grids", font=self.subtitle_font)
        
        # Centering the Title and Subtitle
        self.title_label.grid(row=1, column=0, columnspan=2, pady=10, sticky='n')
        self.subtitle_label.grid(row=2, column=0, columnspan=2, pady=10, sticky='n')

        # Load and Display Image
        self.load_and_display_image()
        # Caption for the Image Beside the Carousel
        self.model_scheme_caption = ttk.Label(self.inner_frame, text="Model exemplative scheme", font=("Arial", 10, "italic"))
        self.model_scheme_caption.grid(row=4, column=0, pady=0, sticky='n')

        # Image Carousel (to the right of the main image)
        self.setup_image_carousel(['Images/Carousel/1.png', 'Images/Carousel/2.png', 'Images/Carousel/3.png','Images/Carousel/4.png','Images/Carousel/5.png'])  # Example image paths        # Add Horizontal Separator
        
        separator = ttk.Separator(self.inner_frame, orient='horizontal')
        separator.grid(row=5, column=0, columnspan=2, sticky='ew', padx=5, pady=10)

        # Descriptive Text Below the Images
        descriptive_text = ("The model optimizes micro-grid size and dispatch strategy at 1-hour temporal resolution. It outputs fixed and variable costs, "
                    "technology-associated LCOE, and enables selection of capacities for batteries, generators, and renewable sources. "
                    "The goal is achieving the lowest Net Present Cost (NPC) or minimal Operation and Maintenance (O&M) expenses, "
                    "within the system's limitations, over the project's lifespan.")
        self.description_label = ttk.Label(self.inner_frame, text=descriptive_text, wraplength=850, justify="left")
        self.description_label.grid(row=6, column=0, columnspan=2, sticky='w')

        # Load and Display Preview Image
        preview_image_path = "Images/Application.png"  # Replace with the actual path
        preview_image = Image.open(preview_image_path)
        resized_preview_image = preview_image.resize((250, 150), Image.Resampling.LANCZOS)  # Adjust size as needed
        tk_preview_image = ImageTk.PhotoImage(resized_preview_image)
        self.preview_image_label = ttk.Label(self.inner_frame, image=tk_preview_image)
        self.preview_image_label.image = tk_preview_image  # Keep a reference to avoid garbage collection
        self.preview_image_label.grid(row=7, column=1, padx=10, pady=10, sticky='e')
        
        # Advanced Features Text
        advanced_features_text = ("In the latest version of MicroGridsPy:\n\n"
                          "- Interactive User Interface for Data Input and Validation;\n"
                          "- Modeling of the Generator Partial Load Effect;\n"
                          "- Endogenous Load Curve Estimation and RES production times series;\n"
                          "- Brownfield and Grid Connection features;\n\n"
                          "MicroGridsPy is developed in the open on GitHub and contributions are very welcome!\n"
                          "Check out the online documentation (https://mgpy-docs.readthedocs.io/en/latest/).")
        self.advanced_features_label = ttk.Label(self.inner_frame, text=advanced_features_text, justify="left", wraplength=600)
        self.advanced_features_label.grid(row=7, column=0, pady=10, sticky='w')
    
    def setup_image_carousel(self, image_paths):
        # Enlarged Carousel Images
        self.carousel_images = [ImageTk.PhotoImage(Image.open(path).resize((350, 175), Image.Resampling.LANCZOS)) for path in image_paths]
        self.carousel_label = ttk.Label(self.inner_frame, image=self.carousel_images[0])
        self.carousel_label.image = self.carousel_images[0]  # Reference to avoid garbage collection
        self.carousel_label.grid(row=3, column=1, pady=10, sticky='w')
        self.current_image_index = 0
        self.update_carousel()

        # Carousel Caption
        self.carousel_caption = ttk.Label(self.inner_frame, text="Example Result Plots", font=("Arial", 10, "italic"))
        self.carousel_caption.grid(row=4, column=1, padx=10, pady=0, sticky='n')

    def update_carousel(self):
        self.current_image_index = (self.current_image_index + 1) % len(self.carousel_images)
        self.carousel_label.configure(image=self.carousel_images[self.current_image_index])
        self.carousel_label.image = self.carousel_images[self.current_image_index]
        self.after(3000, self.update_carousel)
        



