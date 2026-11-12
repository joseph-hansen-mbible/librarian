import tkinter as tk
from tkinter import ttk
from objects.Project import Project, Status
from whoami import Who
from methods.Populators import Populators
from methods.Creators import Creators

test_project = None

class References:
    def __init__(self):
        pass

def create_test_project():
    # Create a test project with a specific status
    global test_project
    test_project = Project(name="Mary", status=Status.ACTIVE, directory_path="/Volumes/KidsExperience/Mary and the Nativity")
    return test_project

def icon_and_loop(main_window):
    # Icon
    try:
        # macos/linux
        photo = tk.PhotoImage(file='./assets/icon.png') #.png or .gif
        main_window.iconphoto(False, photo)
    except tk.TclError:
        # windows
        main_window.iconbitmap('./assets/icon.ico')
    finally:
        main_window.mainloop()


def main():
    who = Who.Who()
        
    if test_project is None:
        create_test_project()
        
    ref = References()
    
    ref.main_window = Creators.setup_main_window(tk.Tk())
    ref.tabs_container = Creators.create_tab_container(ref.main_window)
    ref.main_tab = Creators.create_tab_main(ref.tabs_container)
    ref.settings_tab = Creators.create_tab_settings(ref.tabs_container)
    ref.projects_frame = Creators.create_settings_projects_frame(ref)
    Creators.create_settings_who_frame(ref)
    Populators.populate_who_listbox(ref, who)
    Populators.populate_project_listbox(ref, [test_project])

    # last
    icon_and_loop(ref.main_window)

if __name__ == "__main__":
    main()
