from pathlib import Path
import tkinter as tk
from tkinter import Menu, ttk
import tkinter.font as tkFont
import json
from platformdirs import PlatformDirs

class References:
    # basically a global manager
    def __init__(self):
        pass
    
    def load_persistence(self):
        preferences_path = self._preferences_path()
        if preferences_path.exists():
            with preferences_path.open(mode="r", encoding="utf-8") as file:
                data = json.load(file)
        else:
            data = {"fontsize": 0}
            self._write_preferences(data)

        self.blender_file_path_variable.set(data.get("blender_file_path", ""))
        self.network_base_path_variable.set(
            data.get(
                "network_base_path",
                self.network_base_path_variable.get(),
            )
        )
        self._set_selected_who(data)
        font_size_ticks = data.get("fontsize", 0)
        self._loading_persistence = True
        try:
            for _ in range(
                0,
                font_size_ticks,
                1 if font_size_ticks > 0 else -1,
            ):
                if font_size_ticks > 0:
                    self.increase_font_size()
                else:
                    self.decrease_font_size()
        finally:
            self._loading_persistence = False

    def load_selected_who(self):
        self._set_selected_who(self._read_preferences())

    def _set_selected_who(self, data):
        selected_who = data.get("who_am_i")
        self.selected_who = (
            selected_who
            if isinstance(selected_who, str)
            and selected_who in self.who.options
            else None
        )

    def _preferences_path(self):
        dirs = PlatformDirs("Fossa", "Joseph Hansen", ensure_exists=True)
        return Path(dirs.user_data_path) / "prefs.json"

    def _read_preferences(self):
        preferences_path = self._preferences_path()
        if not preferences_path.exists():
            return {"fontsize": 0}
        with preferences_path.open(mode="r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("Fossa preferences must be a JSON object")
        return data

    def _write_preferences(self, data):
        preferences_path = self._preferences_path()
        with preferences_path.open(mode="w", encoding="utf-8") as file:
            json.dump(data, file)

    def save_blender_file_path(self, blender_file_path):
        data = self._read_preferences()
        data["blender_file_path"] = blender_file_path
        self._write_preferences(data)

    def save_network_base_path(self, network_base_path):
        data = self._read_preferences()
        data["network_base_path"] = network_base_path
        self._write_preferences(data)

    def save_selected_who(self, selected_who):
        data = self._read_preferences()
        data["who_am_i"] = selected_who
        self._write_preferences(data)

    def get_project_structure_draft(self, project_id):
        drafts = self._read_preferences().get("project_structure_drafts", {})
        if not isinstance(drafts, dict):
            raise ValueError("Project structure drafts must be a JSON object")
        draft = drafts.get(project_id)
        return draft if isinstance(draft, dict) else None

    def save_project_structure_draft(self, project_id, draft):
        data = self._read_preferences()
        drafts = data.setdefault("project_structure_drafts", {})
        if not isinstance(drafts, dict):
            raise ValueError("Project structure drafts must be a JSON object")
        drafts[project_id] = draft
        self._write_preferences(data)

    def clear_project_structure_draft(self, project_id):
        data = self._read_preferences()
        drafts = data.get("project_structure_drafts", {})
        if not isinstance(drafts, dict):
            raise ValueError("Project structure drafts must be a JSON object")
        if project_id in drafts:
            del drafts[project_id]
            self._write_preferences(data)

    def get_worker_network_base_path(self, fallback=None):
        project = getattr(self, "selected_project", None)
        if project is not None:
            return Path(project.directory_path)
        return Path(
            fallback
            if fallback is not None
            else self.network_base_path_variable.get()
        )

    def save_font_size(self, ticks):
        if getattr(self, "_loading_persistence", False):
            return
        data = self._read_preferences()
        data["fontsize"] = data.get("fontsize", 0) + ticks
        self._write_preferences(data)
            
    
    def increase_font_size(self):
        ref = self
        ref.command_font.config(size=ref.command_font.actual()['size'] + 2)
        ref.treeview_heading_font.config(size=ref.treeview_heading_font.actual()['size'] + 2)
        ref.treeview_font.config(size=ref.treeview_font.actual()['size'] + 2)
        ref.label_font.config(size=ref.label_font.actual()['size'] + 2)
        ref.status_font.config(size=ref.status_font.actual()['size'] + 2)
        for font in ref.scaled_system_fonts:
            font.config(size=font.actual()["size"] + 2)

        ref.small_treeview_font.config(size=ref.small_treeview_font.actual()['size'] + 2)
        ref.treeview_heading_font_small.config(size=ref.treeview_heading_font_small.actual()['size'] + 2)
        ref.gray_font.config(size=ref.gray_font.actual()['size'] + 2)
        
        treeview_heading_adjustment = (ref.treeview_heading_font.actual()['size'] - 10) * 10
        
        ref.recent_files_treeview.column("Status", width=80 + treeview_heading_adjustment)
        ref.recent_files_treeview.column("Date", width=100 + treeview_heading_adjustment)
        ref.recent_files_treeview.column("Artist", width=110 + treeview_heading_adjustment)

        ref.locks_treeview.column("Status", width=50 + treeview_heading_adjustment, stretch=False)
        ref.locks_treeview.column("Checklist", width=100 + treeview_heading_adjustment, stretch=False)
        ref.locks_treeview.column("UA", width=50 + treeview_heading_adjustment, stretch=False)
        ref.locks_treeview.column("Scene", width=50 + treeview_heading_adjustment, stretch=False)
        ref.locks_treeview.column("Shot", width=50 + treeview_heading_adjustment, stretch=False)
        ref.locks_treeview.column("Version", width=60 + treeview_heading_adjustment, stretch=False)
        
        window_height = ref.main_window.winfo_screenheight()
        screen_height = ref.main_window.winfo_screenheight()
        center_y = int(screen_height/2 - window_height / 4)
        ref.main_window.geometry(f'{1450}x{550}+{200}+{center_y}')
        ref.main_window.minsize(1200, 550)
        
        ref.save_font_size(1)
    
    def decrease_font_size(self):
        ref = self
        ref.command_font.config(size=ref.command_font.actual()['size'] - 2)
        ref.treeview_heading_font.config(size=ref.treeview_heading_font.actual()['size'] - 2)
        ref.treeview_font.config(size=ref.treeview_font.actual()['size'] - 2)
        ref.label_font.config(size=ref.label_font.actual()['size'] - 2)
        ref.status_font.config(size=ref.status_font.actual()['size'] - 2)
        for font in ref.scaled_system_fonts:
            font.config(size=font.actual()["size"] - 2)

        ref.small_treeview_font.config(size=ref.small_treeview_font.actual()['size'] - 2)
        ref.treeview_heading_font_small.config(size=ref.treeview_heading_font_small.actual()['size'] - 2)
        ref.gray_font.config(size=ref.gray_font.actual()['size'] - 2)
        
        treeview_heading_adjustment = (ref.treeview_heading_font.actual()['size'] - 10) * 10
        
        ref.recent_files_treeview.column("Status", width=80 + treeview_heading_adjustment)
        ref.recent_files_treeview.column("Date", width=100 + treeview_heading_adjustment)
        ref.recent_files_treeview.column("Artist", width=110 + treeview_heading_adjustment)

        ref.locks_treeview.column("Status", width=50 + treeview_heading_adjustment, stretch=False)
        ref.locks_treeview.column("Checklist", width=100 + treeview_heading_adjustment, stretch=False)
        ref.locks_treeview.column("UA", width=50 + treeview_heading_adjustment, stretch=False)
        ref.locks_treeview.column("Scene", width=50 + treeview_heading_adjustment, stretch=False)
        ref.locks_treeview.column("Shot", width=50 + treeview_heading_adjustment, stretch=False)
        ref.locks_treeview.column("Version", width=60 + treeview_heading_adjustment, stretch=False)
        
        
        window_height = ref.main_window.winfo_screenheight()
        screen_height = ref.main_window.winfo_screenheight()
        center_y = int(screen_height/2 - window_height / 4)
        ref.main_window.geometry(f'{1450}x{550}+{200}+{center_y}')
        ref.main_window.minsize(1200, 550)
        
        ref.save_font_size(-1)
    
    def setup_fonts(self):
        ref = self
        style = ttk.Style(ref.main_window)
        ref.command_font = tkFont.Font(family="Helvetica", size=13, weight="bold")
        ref.scaled_system_fonts = [
            tkFont.nametofont(name)
            for name in ("TkDefaultFont", "TkMenuFont", "TkTextFont")
        ]
        style.configure("CommandBar.TLabel", font=ref.command_font)
        ref.treeview_heading_font = tkFont.Font(family="Helvetica", size=13, weight="normal")
        style.configure("Treeview.Heading", font=ref.treeview_heading_font)
        ref.treeview_heading_font_small = tkFont.Font(family="Helvetica", size=11, weight="normal")
        style.configure("Small.Treeview.Heading", font=ref.treeview_heading_font_small)
        ref.treeview_font = tkFont.Font(family="Helvetica", size=11, weight="normal")
        style.configure('Treeview', font=ref.treeview_font)
        ref.small_treeview_font = tkFont.Font(family="Helvetica", size=11, weight="normal")
        style.configure('Small.Treeview', font=ref.small_treeview_font)
        ref.gray_font = tkFont.Font(family="Helvetica", size=11, weight="normal")
        style.configure("Gray.TLabel", font=ref.gray_font, foreground="#b7b7b7")
        style.configure("CurrentFiles.TFrame", background="#2b2d32")
        style.configure("CurrentFiles.TLabel", background="#2b2d32")
        style.configure(
            "CurrentFilesValue.TLabel",
            font=ref.gray_font,
            foreground="#b7b7b7",
            background="#2b2d32",
        )
        ref.label_font = tkFont.Font(family="Helvetica", size=11, weight="normal")
        ref.status_font = tkFont.Font(family="Helvetica", size=8, weight="normal", slant="italic")
        style.configure('TLabelframe.Label', font=ref.label_font)