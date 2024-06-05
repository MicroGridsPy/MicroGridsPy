import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont

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


