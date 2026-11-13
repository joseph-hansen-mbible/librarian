from pathlib import Path
import tkinter as tk
from tkinter import Menu, ttk
import tkinter.font as tkFont
import json
from os import path
from platformdirs import PlatformDirs

class References:
    # basically a global manager
    def __init__(self):
        pass
    
    def load_persistence(self):
        dirs = PlatformDirs("Fossa", "Joseph Hansen", ensure_exists=True)
        appdata = dirs.user_data_path
        if path.exists(appdata / "prefs.json"):
            with (Path(appdata / "prefs.json").open(mode="r", encoding="utf-8")) as file:
                data = json.load(file)
                for i in range(0, data['fontsize'], 1 if data['fontsize'] > 0 else -1):
                    if data['fontsize'] > 0:
                        self.increase_font_size()
                    else:
                        self.decrease_font_size()
        else:
            with (Path(appdata / "prefs.json").open(mode="w", encoding="utf-8")) as file:
                json.dump({'fontsize': 0}, file)
                    
    def save_font_size(self, ticks):
        dirs = PlatformDirs("Fossa", "Joseph Hansen", ensure_exists=True)
        appdata = dirs.user_data_path
        with (Path(appdata / "prefs.json").open(mode="r", encoding="utf-8")) as file:
                data = json.load(file)
                current_ticks = data["fontsize"]
                current_ticks += ticks
        with (Path(appdata / "prefs.json").open(mode="w", encoding="utf-8")) as file:
                json.dump({'fontsize': ticks}, file)
            
    
    def increase_font_size(self):
        ref = self
        ref.command_font.config(size=ref.command_font.actual()['size'] + 2)
        ref.treeview_heading_font.config(size=ref.treeview_heading_font.actual()['size'] + 2)
        ref.treeview_font.config(size=ref.treeview_font.actual()['size'] + 2)
        ref.label_font.config(size=ref.treeview_font.actual()['size'] + 2)
        
        treeview_heading_adjustment = (ref.treeview_heading_font.actual()['size'] - 10) * 10
        
        ref.recent_files_treeview.column("Status", width=50 + treeview_heading_adjustment)
        ref.recent_files_treeview.column("Date", width=100 + treeview_heading_adjustment)
        ref.recent_files_treeview.column("Artist", width=110 + treeview_heading_adjustment)
        ref.current_files_treeview.column("Artist", width=110 + treeview_heading_adjustment)
        
        window_height = ref.main_window.winfo_screenheight()
        screen_height = ref.main_window.winfo_screenheight()
        center_y = int(screen_height/2 - window_height / 4)
        ref.main_window.geometry(f'{int(1000+(treeview_heading_adjustment * 2.2))}x{700}+{200}+{center_y}')
        ref.main_window.minsize(500, 400)
        
        ref.save_font_size(1)
    
    def decrease_font_size(self):
        ref = self
        ref.command_font.config(size=ref.command_font.actual()['size'] - 2)
        ref.treeview_heading_font.config(size=ref.treeview_heading_font.actual()['size'] - 2)
        ref.treeview_font.config(size=ref.treeview_font.actual()['size'] - 2)
        ref.label_font.config(size=ref.treeview_font.actual()['size'] - 2)
        
        treeview_heading_adjustment = (ref.treeview_heading_font.actual()['size'] - 10) * 10
        
        ref.recent_files_treeview.column("Status", width=50 + treeview_heading_adjustment)
        ref.recent_files_treeview.column("Date", width=100 + treeview_heading_adjustment)
        ref.recent_files_treeview.column("Artist", width=110 + treeview_heading_adjustment)
        ref.current_files_treeview.column("Artist", width=110 + treeview_heading_adjustment)
        
        window_height = ref.main_window.winfo_screenheight()
        screen_height = ref.main_window.winfo_screenheight()
        center_y = int(screen_height/2 - window_height / 4)
        ref.main_window.geometry(f'{int(1000+(treeview_heading_adjustment * 2.2))}x{700}+{200}+{center_y}')
        ref.main_window.minsize(500, 400)
        
        ref.save_font_size(-1)
    
    def setup_fonts(self):
        ref = self
        style = ttk.Style(ref.main_window)
        ref.command_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        style.configure("CommandBar.TLabel", font=ref.command_font)
        ref.treeview_heading_font = tkFont.Font(family="Helvetica", size=13, weight="normal")
        style.configure("Treeview.Heading", font=ref.treeview_heading_font)
        ref.treeview_font = tkFont.Font(family="Helvetica", size=11, weight="normal")
        style.configure('Treeview', font=ref.treeview_font)
        ref.label_font = tkFont.Font(family="Helvetica", size=11, weight="normal")
        style.configure('TLabelframe.Label', font=ref.label_font)