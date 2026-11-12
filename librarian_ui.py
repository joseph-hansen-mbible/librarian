import tkinter as tk
from tkinter import ttk
from objects import Project

test_project = None

class References:
    def __init__(self):
        pass

def create_test_project():
    # Create a test project with a specific status
    global test_project
    test_project = Project.Project(name="Mary", status=Project.Status.ACTIVE, directory_path="/Volumes/KidsExperience/Mary and the Nativity")
    return test_project

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

def create_tab_container(window):
    notebook = ttk.Notebook(window)
    notebook.pack(pady=10, expand=True, fill='both')
    return notebook

def create_tab_main(notebook):
    main_tab = ttk.Frame(notebook)
    main_tab.pack(fill='both', expand=True)
    notebook.add(main_tab, text='Main')
    return main_tab

def create_tab_settings(notebook):
    settings_tab = ttk.Frame(notebook)
    settings_tab.pack(fill='both', expand=True)
    notebook.add(settings_tab, text='Settings')
    return settings_tab

def create_settings_projects_frame(settings_tab):
    projects_frame = ttk.LabelFrame(settings_tab, text="Projects")
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
    project_details_status = ttk.OptionMenu(project_details_frame, project_status_var, "Status", *[status.value for status in Project.Status])
    project_details_directory_path = ttk.Button(project_details_frame, text="Choose Directory")
    project_details_label.pack(pady=5, fill='x')
    project_details_status.pack(pady=5, fill='x')
    project_details_directory_path.pack(pady=5, fill='x')
    
    global ref
    ref.new_project_button = new_project_button
    ref.projects_frame = projects_frame
    ref.project_listbox = project_listbox
    ref.project_details_frame = project_details_frame
    ref.project_details_status = project_details_status
    ref.project_details_directory_path = project_details_directory_path
    ref.project_status_var = project_status_var

def icon_and_loop(main_window):
    # Icon
    try:
        # macos/linux
        photo = tk.PhotoImage(file='./assets/python_icon.png') #.png or .gif
        main_window.iconphoto(False, photo)
    except tk.TclError:
        # windows
        main_window.iconbitmap('./assets/pythontutorial.ico')
    finally:
        main_window.mainloop()

if __name__ == "__main__":
    
    if test_project is None:
        create_test_project()
        
    ref = References()
    
    ref.main_window = setup_main_window(tk.Tk())
    ref.tabs_container = create_tab_container(ref.main_window)
    ref.main_tab = create_tab_main(ref.tabs_container)
    ref.settings_tab = create_tab_settings(ref.tabs_container)
    ref.projects_frame = create_settings_projects_frame(ref.settings_tab)


    # last
    icon_and_loop(ref.main_window)
