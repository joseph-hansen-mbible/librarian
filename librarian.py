import tkinter as tk
from tkinter import Menu, ttk
from pathlib import Path
from objects.Project import Project, Status
from whoami import Who
from methods.Populators import Populators
from methods.Creators import Creators
import tkinter.font as tkFont

test_project = None

class References:
    def __init__(self):
        pass
    
    def increase_font_size(self):
        print("increase")
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
        ref.main_window.geometry(f'{1000+(treeview_heading_adjustment * 2)}x{700}+{200}+{center_y}')
        ref.main_window.minsize(500, 400)
    
    def decrease_font_size(self):
        ref = self
        print("decrease")
        ref.command_font.config(size=ref.command_font.actual()['size'] - 2)
        ref.treeview_heading_font.config(size=ref.treeview_heading_font.actual()['size'] - 2)
        ref.treeview_font.config(size=ref.treeview_font.actual()['size'] - 2)
        ref.label_font.config(size=ref.treeview_font.actual()['size'] - 2)
        
        treeview_heading_adjustment = (ref.treeview_heading_font.actual()['size'] - 10) * 10
        
        ref.recent_files_treeview.column("Status", width=50 + treeview_heading_adjustment)
        ref.recent_files_treeview.column("Date", width=100 + treeview_heading_adjustment)
        ref.recent_files_treeview.column("Artist", width=110 + treeview_heading_adjustment)
        ref.current_files_treeview.column("Artist", width=110 + treeview_heading_adjustment)
    
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
    
    StyleMainWindow(ref)
    SetUpMenus(ref)
    ref.setup_fonts()
    
    ref.tabs_container = Creators.create_tab_container(ref.main_window)
    ref.main_tab = Creators.create_tab_main(ref.tabs_container)
    ref.main_tab.ref = ref
    ref.settings_tab = Creators.create_tab_settings(ref.tabs_container)
    ref.command_bar_frame = Creators.create_command_entry_frame(ref.main_tab)
    Creators.fill_command_entry_frame(ref)
    ref.projects_frame = Creators.create_settings_projects_frame(ref)
    ref.current_files_frame = Creators.create_current_files_frame(ref.main_tab)
    ref.recent_files_frame = Creators.create_recent_files_frame(ref.main_tab)
    Creators.create_current_files_treeview(ref)
    Creators.create_recent_files_treeview(ref)
    Creators.create_settings_who_frame(ref)
    Creators.create_settings_other_frame(ref)
    Populators.populate_who_listbox(ref, who)
    Populators.populate_project_listbox(ref, [test_project])
    Populators.populate_current_files_treeview(ref)
    Populators.populate_recent_files_treeview(ref)

    def focus_project_listbox_on_settings(_event):
        if ref.tabs_container.select() == str(ref.settings_tab):
            ref.tabs_container.after_idle(ref.project_listbox.focus_set)

    ref.tabs_container.bind("<<NotebookTabChanged>>", focus_project_listbox_on_settings)

    # last
    icon_and_loop(ref.main_window)

def StyleMainWindow(ref):
    style = ttk.Style(ref.main_window)
    theme_script = Path(__file__).resolve().parent / "themes" / "tkbreezedark" / "breeze-dark.tcl"
    ref.main_window.tk.call("source", str(theme_script))
    style.theme_use("breeze-dark")

def SetUpMenus(ref):
    root = ref.main_window
    menubar = Menu(ref.main_window)
    root.config(menu=menubar)
    options_menu = Menu(menubar, tearoff=False)

    options_menu.add_command(
        label='Increase Font Size',
        command=ref.increase_font_size
    )
    
    options_menu.add_command(
            label='Decrease Font Size',
            command=ref.decrease_font_size
    )

    menubar.add_cascade(
        label="Appearance",
        menu=options_menu
)

if __name__ == "__main__":
    main()
