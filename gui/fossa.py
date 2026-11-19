import tkinter as tk
from tkinter import Menu, ttk
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from objects.Project import Project, Status
from whoami import Who
from methods.Populators import Populators
from methods.Creators import CreatorsMaintab as Creators
from methods.CreatorsSettings import CreatorsSettings
from objects.References import References
from db import fossadb

test_project = None

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
    ref.update_status_bar = lambda: UpdateStatusBar(ref, schedule=False)

    ref.main_window = Creators.setup_main_window(tk.Tk())
    
    StyleMainWindow(ref)
    SetUpMenus(ref)
    ref.setup_fonts()
    
    ref.blender_file_path_variable = tk.StringVar()
    ref.network_base_path_variable = tk.StringVar(
        value="/Volumes/KidsExperience"
    )
    
    ref.settings_window = CreatorsSettings.create_settings_window(ref)
    ref.main_toolbar_frame = Creators.create_main_toolbar(ref.main_window)
    ref.statusbar = Creators.create_main_statusbar(ref.main_window)

    CreatorsSettings.create_settings_button(ref, ref.main_toolbar_frame)
    ref.tabs_container = Creators.create_tab_container(ref.main_window)
    
    ref.main_tab = Creators.create_tab_main(ref.tabs_container)
    
    ref.main_tab.ref = ref
    ref.main_window.ref = ref
    
    ref.all_files_tab = Creators.create_tab_all_files(ref.tabs_container)
    ref.all_files_tab.ref = ref
    
    ref.projects_frame = CreatorsSettings.create_settings_projects_frame(ref)
    
    ref.file_lists_frame = Creators.create_file_lists_frame(ref.main_tab)
    ref.recent_files_frame = Creators.create_recent_files_frame(ref.file_lists_frame)
    ref.main_content_left_frame = Creators.create_main_content_left_frame(ref.file_lists_frame)
    ref.command_bar_frame = Creators.create_command_entry_frame(ref.main_content_left_frame)
    Creators.fill_command_entry_frame(ref)
    ref.current_files_frame = Creators.create_current_files_frame(ref.main_content_left_frame)
    Creators.create_current_files_header(ref)
    
    Creators.create_current_files_table(ref)
    Creators.create_recent_files_header(ref)
    ref.recent_files_tree_frame = Creators.create_recent_files_tree_frame(ref)
    Creators.create_recent_files_treeview(ref)
    Creators.create_recent_files_note_frame(ref)
    Creators.create_recent_files_open_button(ref)

    ref.locks_frame = Creators.create_locks_frame(ref.all_files_tab)
    ref.locks_details_frame = Creators.create_locks_details_frame(ref.all_files_tab)
    Creators.create_locks_treeview(ref)
    Creators.create_locks_details_buttons(ref)
    
    CreatorsSettings.create_settings_who_frame(ref)
    CreatorsSettings.create_settings_other_frame(ref)
    
    Populators.populate_who_listbox(ref, who)
    Populators.populate_project_listbox(ref, [test_project])
    Populators.populate_recent_files_treeview(ref)
    Populators.populate_current_files_table(ref)
    Populators.populate_locks_treeview(ref)
    
    # last
    ref.load_persistence()
    UpdateStatusBar(ref)
    UpdateStatusBar(ref)

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
    settings_menu = Menu(menubar,tearoff=False)

    options_menu.add_command(
        label='Increase Font Size',
        command=ref.increase_font_size
    )
    
    settings_menu.add_command(label="Settings", command=lambda: CreatorsSettings.show_settings_window(ref))
    
    options_menu.add_command(
            label='Decrease Font Size',
            command=ref.decrease_font_size
    )

    menubar.add_cascade(
        label="Appearance",
        menu=options_menu)
    
    menubar.add_cascade(
        label="Settings",
        menu=settings_menu
    )

def UpdateStatusBar(ref, schedule=True):
    network_base_path = ref.network_base_path_variable.get().strip()
    if not network_base_path:
        ref.database = None
        ref.database_connected = False
    else:
        network_base_path = Path(network_base_path).expanduser().resolve()
        database = getattr(ref, "database", None)
        if database is None or database.network_base_path != network_base_path:
            ref.database = None
            if network_base_path.is_dir():
                try:
                    ref.database = fossadb.FossaDB(network_base_path)
                except (OSError, ValueError):
                    ref.database = None
        ref.database_connected = (
            ref.database.IsConnected() if ref.database is not None else False
        )

    blender_file_path = ref.blender_file_path_variable.get()
    ref.blender_ready = (
        bool(blender_file_path)
        and (".app" in blender_file_path or ".exe" in blender_file_path)
        and Path(blender_file_path).exists()
    )

    Populators.update_status_bar(ref)
    if schedule:
        ref.status_bar_timer = ref.main_window.after(
            5_000, lambda: UpdateStatusBar(ref)
        )

if __name__ == "__main__":
    main()
