import tkinter as tk
from tkinter import ttk

from objects.Project import Project, Status

class Creators:
    @staticmethod
    def setup_main_window(root):
        root.title("Art Team Librarian")

        window_width = root.winfo_screenwidth()
        window_height = root.winfo_screenheight()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width / 6)
        center_y = int(screen_height/2 - window_height / 3)
        root.geometry(f'{int(window_width/3)}x{int(window_height/3)}+{center_x}+{center_y}')
        root.minsize(800, 800)
        
        return root

    @staticmethod
    def create_tab_container(window):
        notebook = ttk.Notebook(window)
        notebook.pack(pady=10, expand=True, fill='both')
        return notebook

    @staticmethod
    def create_tab_main(notebook):
        main_tab = ttk.Frame(notebook)
        main_tab.pack(fill='both', expand=True)
        notebook.add(main_tab, text='Main')
        return main_tab
    
    @staticmethod
    def create_command_entry_frame(parent):
        command_bar_frame = ttk.Frame(parent)
        command_bar_frame.pack(fill='x', expand=False, padx=10, pady=40, side='top')
        return command_bar_frame
    
    @staticmethod
    def fill_command_entry_frame(ref):
        # "I want to..." label + action optionbox + "in" + project optionbox + "for" + scene optionbox + shot optionbox
        style = ttk.Style(ref.command_bar_frame)
        command_font = ("Helvetica", 14, "bold")
        style.configure("CommandBar.TLabel", font=command_font)
        style.configure("CommandBar.TMenubutton", font=command_font)
        style.configure("Go.TButton", font=command_font, padding=(12, 6))

        action_label = ttk.Label(
            ref.command_bar_frame,
            text="I want to...",
            style="CommandBar.TLabel",
            font=command_font,
        )
        action_label.pack(side='left', padx=5)
        ref.command_action_var = tk.StringVar(value="Action")
        ref.command_action_optionbox = ttk.OptionMenu(
            ref.command_bar_frame,
            ref.command_action_var,
            "Action",
            "Action",
            style="CommandBar.TMenubutton",
        )
        ref.command_action_optionbox.pack(side='left', padx=5)
        second_command_label = ttk.Label(
            ref.command_bar_frame,
            text="in",
            style="CommandBar.TLabel",
            font=command_font,
        )
        second_command_label.pack(side='left', padx=5)
        ref.command_project_var = tk.StringVar(value="Project")
        ref.command_project_optionbox = ttk.OptionMenu(
            ref.command_bar_frame,
            ref.command_project_var,
            "Project",
            "Project",
            style="CommandBar.TMenubutton",
        )
        ref.command_project_optionbox.pack(side='left', padx=5)
        third_command_label = ttk.Label(
            ref.command_bar_frame,
            text="for",
            style="CommandBar.TLabel",
            font=command_font,
        )
        third_command_label.pack(side='left', padx=5)
        ref.command_scene_var = tk.StringVar(value="Scene")
        ref.command_scene_optionbox = ttk.OptionMenu(
            ref.command_bar_frame,
            ref.command_scene_var,
            "Scene",
            "Scene",
            style="CommandBar.TMenubutton",
        )
        ref.command_scene_optionbox.pack(side='left', padx=5)
        ref.command_shot_var = tk.StringVar(value="Shot")
        ref.command_shot_optionbox = ttk.OptionMenu(
            ref.command_bar_frame,
            ref.command_shot_var,
            "Shot",
            "Shot",
            style="CommandBar.TMenubutton",
        )
        ref.command_shot_optionbox.pack(side='left', padx=5)
        ref.command_execute_button = ttk.Button(
            ref.command_bar_frame,
            text="Go",
            style="Go.TButton",
        )
        ref.command_execute_button.pack(side='left', padx=5)

    @staticmethod
    def create_tab_settings(notebook):
        settings_tab = ttk.Frame(notebook)
        settings_tab.pack(fill='both', expand=True)
        notebook.add(settings_tab, text='Settings')
        return settings_tab

    @staticmethod
    def create_settings_projects_frame(ref):
        projects_frame = ttk.LabelFrame(ref.settings_tab, text="Projects")
        projects_frame.pack(fill='x', expand=False, padx=10, pady=10, side='top')
        
        new_project_button = ttk.Button(projects_frame, text="New Project")
        new_project_button.pack(side='left', pady=10, fill='none', anchor = "n")
        
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
        who_frame.pack(fill='x', expand=False, padx=10, pady=10, side='top')
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
        blender_file_path_entry = ttk.Entry(other_row)
        blender_file_path_entry.pack(side='left', fill='x', expand=True)
        choose_blender_file_path_button = ttk.Button(other_row, text="Blender Executable")
        choose_blender_file_path_button.pack(side='right', padx=5)
        
        status_checks_row = ttk.Frame(other_frame)
        status_checks_row.pack(fill='x', expand=False, padx=5, pady=5)
        status_checks = {
            "Blender connection": ttk.Label(status_checks_row, text="Blender connection", background="green"),
            "Network connection": ttk.Label(status_checks_row, text="Network connection", background="green"),
            "Database connection": ttk.Label(status_checks_row, text="Database connection", background="green"),
        }
        for label in status_checks.values():
            label.pack(side='left', padx=5, pady=5, fill='x', expand=True)
        