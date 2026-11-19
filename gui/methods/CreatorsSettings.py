import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path

from methods.Filters import Filters
from objects.Project import Project, Status

class CreatorsSettings:    
    @staticmethod
    def create_settings_window(ref):
        settings_window = tk.Toplevel(ref.main_window)
        settings_window.title("Settings")
        settings_window.geometry("700x700")
        settings_window.minsize(500, 400)
        settings_window.transient(ref.main_window)
        settings_window.withdraw()
        settings_window.protocol("WM_DELETE_WINDOW", settings_window.withdraw)

        ref.settings_tab = ttk.Frame(settings_window)
        ref.settings_tab.pack(fill='both', expand=True)
        return settings_window

    @staticmethod
    def create_settings_button(ref, parent):
        settings_icon_path = Path(__file__).resolve().parent.parent / "assets" / "settings.png"
        ref.settings_icon = tk.PhotoImage(file=str(settings_icon_path)).subsample(2, 2)
        ref.settings_button = ttk.Button(
            parent,
            image=ref.settings_icon,
            command=lambda: CreatorsSettings.show_settings_window(ref),
        )
        ref.settings_button.pack(side='right', padx=5)

    @staticmethod
    def show_settings_window(ref):
        ref.settings_window.deiconify()
        ref.settings_window.lift()
        ref.settings_window.focus_set()

    @staticmethod
    def create_settings_projects_frame(ref):
        projects_frame = ttk.LabelFrame(ref.settings_tab, text="Projects")
        projects_frame.pack(fill='x', expand=False, padx=5, pady=5, side='top')
        
        new_project_button = ttk.Button(projects_frame, text="New Project")
        new_project_button.pack(side='left', pady=5, fill='none', anchor = "n")
        
        # left column project list
        project_list_frame = ttk.Frame(projects_frame)
        project_list_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        project_listbox = tk.Listbox(
            project_list_frame,
            height=10,
            exportselection=False,
        )
        project_listbox.pack(side='left', fill='both', expand=True)
        
        # right column project details
        project_details_frame = ttk.Frame(projects_frame)
        project_details_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        project_details_label = ttk.Label(project_details_frame, text="Project Details")
        project_status_var = tk.StringVar(value="Status")
        project_details_status = ttk.OptionMenu(project_details_frame, project_status_var, "Status", *[status.value for status in Status])
        project_details_directory_path = ttk.Button(project_details_frame, text="Choose Directory")
        project_details_label.pack(pady=5, fill='x')
        project_details_status.pack(pady=5, fill='x')
        project_details_directory_path.pack(pady=5, fill='x')
        
        ref.new_project_button = new_project_button
        ref.project_listbox = project_listbox
        ref.project_details_status = project_details_status
        ref.project_details_directory_path = project_details_directory_path
        ref.project_status_var = project_status_var
        
        
    @staticmethod
    def create_settings_who_frame(ref):
        who_frame = ttk.LabelFrame(ref.settings_tab, text="Who am I?")
        who_frame.pack(fill='x', expand=False, padx=5, pady=5, side='top')
        who_listbox = tk.Listbox(
            who_frame,
            height=10,
            exportselection=False,
        )
        who_listbox.pack(side='left', anchor='w', fill='none', expand=True)
        
        who_lock_button = ttk.Button(who_frame, text="Unlock")
        who_lock_button.pack(side='right', expand=True,padx=5, pady=5)
        
        ref.who_listbox = who_listbox
        ref.who_lock_button = who_lock_button

    @staticmethod
    def create_settings_other_frame(ref):
        other_frame = ttk.LabelFrame(ref.settings_tab, text="Other Settings")
        other_frame.pack(fill='x', expand=False, padx=10, pady=10, side='top')
        
        other_row = ttk.Frame(other_frame)
        other_row.pack(fill='x', expand=False, padx=5, pady=5)

        blender_file_path_entry = ttk.Entry(other_row, textvariable=ref.blender_file_path_variable)
        blender_file_path_entry.pack(side='left', fill='x', expand=True)
        blender_file_path_entry.bind(
            "<Return>",
            lambda _event: CreatorsSettings.save_blender_file_path(ref),
        )
        blender_file_path_entry.bind(
            "<FocusOut>",
            lambda _event: CreatorsSettings.save_blender_file_path(ref),
        )
        choose_blender_file_path_button = ttk.Button(
            other_row,
            text="Blender Executable",
            command=lambda: CreatorsSettings.choose_blender_file_path(ref),
        )
        choose_blender_file_path_button.pack(side='right', padx=5)

        ref.blender_file_path_entry = blender_file_path_entry

        network_row = ttk.Frame(other_frame)
        network_row.pack(fill='x', expand=False, padx=5, pady=5)

        network_base_path_entry = ttk.Entry(
            network_row,
            textvariable=ref.network_base_path_variable,
        )
        network_base_path_entry.pack(side='left', fill='x', expand=True)
        network_base_path_entry.bind(
            "<Return>",
            lambda _event: CreatorsSettings.save_network_base_path(ref),
        )
        network_base_path_entry.bind(
            "<FocusOut>",
            lambda _event: CreatorsSettings.save_network_base_path(ref),
        )
        choose_network_base_path_button = ttk.Button(
            network_row,
            text="Network Folder",
            command=lambda: CreatorsSettings.choose_network_base_path(ref),
        )
        choose_network_base_path_button.pack(side='right', padx=5)
        ref.network_base_path_entry = network_base_path_entry
        
        increase_button = tk.Button(ref.settings_tab, text="Increase Font Size", command=ref.increase_font_size)
        increase_button.pack()

        decrease_button = tk.Button(ref.settings_tab, text="Decrease Font Size", command=ref.decrease_font_size)
        decrease_button.pack()

    @staticmethod
    def choose_blender_file_path(ref):
        blender_file_path = filedialog.askopenfilename(
            parent=ref.settings_window,
            title="Select Blender executable",
            filetypes=(("Blender executable", "*"), ("All files", "*")),
        )
        if blender_file_path:
            ref.blender_file_path_variable.set(blender_file_path)
            CreatorsSettings.save_blender_file_path(ref)

    @staticmethod
    def save_blender_file_path(ref):
        ref.save_blender_file_path(ref.blender_file_path_variable.get())
        ref.update_status_bar()

    @staticmethod
    def choose_network_base_path(ref):
        network_base_path = filedialog.askdirectory(
            parent=ref.settings_window,
            title="Select network folder",
            mustexist=True,
        )
        if network_base_path:
            ref.network_base_path_variable.set(network_base_path)
            CreatorsSettings.save_network_base_path(ref)

    @staticmethod
    def save_network_base_path(ref):
        ref.save_network_base_path(ref.network_base_path_variable.get())
        ref.update_status_bar()