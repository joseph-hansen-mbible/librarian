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
        project_listbox = tk.Listbox(project_list_frame, height=10)
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
        who_listbox = tk.Listbox(who_frame, height=10)
        who_listbox.pack(side='left', anchor='w', fill='none', expand=True)
        
        who_lock_button = ttk.Button(who_frame, text="Unlock")
        who_lock_button.pack(side='right', expand=True,padx=5, pady=5)
        
        ref.who_listbox = who_listbox
        ref.who_lock_button = who_lock_button