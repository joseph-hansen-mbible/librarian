import os
import tkinter as tk
from tkinter import Menu, ttk
from pathlib import Path
import sys
import threading
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui.methods import Helpers
from objects.Project import Project, Status
from whoami import Who
from methods.Populators import Populators
from methods.Creators import CreatorsMaintab as Creators
from methods.CreatorsSettings import CreatorsSettings
from objects.References import References
from db import fossadb
from workers import core

CLOSE_APPLICATION_TIMEOUT_MS = 1_000
CLOSE_APPLICATION_POLL_MS = 50

def FossaMain(ref, on_ready=None):
    ref.load_selected_who()
    ref.update_status_bar = lambda: FossaStatusBar(ref, schedule=False)

    ref.main_window = Creators.setup_main_window(tk.Tk())
    ref.main_window.protocol(
        "WM_DELETE_WINDOW", lambda: FossaCloseApplication(ref)
    )
    
    style = ttk.Style(ref.main_window)
    theme_script = PROJECT_ROOT / "themes" / "tkbreezedark" / "breeze-dark.tcl"
    ref.main_window.tk.call("source", str(theme_script))
    style.theme_use("breeze-dark")
    
    FossaMenus(ref)
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
    
    CreatorsSettings.create_settings_other_frame(ref)
    
    Populators.populate_project_listbox(ref, [])
    Populators.initialize_command_bar(ref)
    Populators.populate_recent_files_treeview(ref)
    Populators.populate_current_files_table(ref)
    Populators.populate_locks_treeview(ref)
    
    # last
    ref.load_persistence()
    if ref.selected_who is None:
        CreatorsSettings.create_settings_who_frame(ref)
        Populators.populate_who_listbox(ref, ref.who)
        ref.main_window.withdraw()
        CreatorsSettings.show_settings_window(ref)
    FossaStatusBar(ref, True)
    FossaUpdateMainFileLists(ref, schedule=True)
    FossaUpdateProjects(ref, schedule=True)
    FossaCheckProjectApprovals(ref, schedule=True)

    if on_ready is not None:
        ref.main_window.after_idle(on_ready)

    FossaIcon(ref.main_window)

def FossaIcon(main_window):
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

def FossaMenus(ref):
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
    
def FossaStatusBar(ref, schedule):
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
    FossaUpdateMainFileLists(ref, schedule=False)
    if schedule:
        ref.status_bar_timer = ref.main_window.after(
            5_000, lambda: FossaStatusBar(ref, schedule=True)
        )

def FossaUpdateMainFileLists(ref, schedule):
    rows = []
    artist = getattr(ref, "selected_who", None)

    if (
        artist
        and getattr(ref, "database_connected", False)
        and ref.database is not None
    ):
        database_checker = None
        try:
            database_checker = core.FossaWorker(
                core.LFRoles.DB_ACCESS,
                ref.get_worker_network_base_path(),
                artist,
                ref.database,
            )
            database = database_checker.GetDatabaseSnapshot()
            for checkout_artist, cache_data in database.items():
                if not isinstance(cache_data, dict):
                    continue
                current_file = cache_data.get("current_file")
                if not isinstance(current_file, str) or not current_file:
                    continue
                rows.append(
                    (
                        Path(current_file).name,
                        str(checkout_artist),
                    )
                )
            rows.sort(key=lambda row: (row[1].lower(), row[0].lower()))
        except (OSError, ValueError):
            rows = []
        finally:
            if database_checker is not None:
                database_checker.Destroy()

    Populators.populate_current_files_table(ref, rows)
    if schedule:
        ref.main_file_lists_timer = ref.main_window.after(
            2_000, lambda: FossaUpdateMainFileLists(ref, schedule=True)
        )

def FossaUpdateProjects(ref, schedule):
    projects = None
    worker = None
    if getattr(ref, "database_connected", False) and ref.database is not None:
        try:
            worker = core.FossaWorker(
                core.LFRoles.DB_ACCESS,
                ref.get_worker_network_base_path(),
                ref.selected_who or "Settings",
                ref.database,
            )
            project_records = worker.GetProjects()
            projects = [
                Project(
                    record["name"],
                    Status(record["status"]),
                    record["directory_path"],
                    scenes=record.get("scenes", []),
                    characters=record.get("characters", []),
                    pending_change=record.get("pending_change"),
                )
                for record in project_records
            ]
            projects.sort(key=lambda project: project.name.casefold())
        except (KeyError, OSError, TypeError, ValueError) as error:
            print(f"Failed to load projects from the database: {error}", file=sys.stderr)
        finally:
            if worker is not None:
                worker.Destroy()

    if projects is not None:
        Populators.populate_project_listbox(ref, projects)
        Populators.populate_command_project_optionbox(ref, projects)
    if schedule:
        ref.projects_timer = ref.main_window.after(
            5_000, lambda: FossaUpdateProjects(ref, schedule=True)
        )

def FossaCheckProjectApprovals(ref, schedule):
    results_found = False
    pending_changes = []
    worker = None
    if (
        getattr(ref, "selected_who", None)
        and getattr(ref, "database_connected", False)
        and ref.database is not None
    ):
        try:
            worker = core.FossaWorker(
                core.LFRoles.APPROVAL_NEEDED,
                ref.get_worker_network_base_path(),
                ref.selected_who,
                ref.database,
            )
            for result in worker.GetProjectStructureChangeResults(ref.selected_who):
                draft = ref.get_project_structure_draft(result["project_id"])
                if draft is not None and draft.get("request_id") == result["request_id"]:
                    ref.clear_project_structure_draft(result["project_id"])
                worker.AcknowledgeProjectStructureChange(
                    result["project_id"],
                    result["request_id"],
                    ref.selected_who,
                )
                results_found = True

            pending_changes = worker.GetPendingProjectStructureChanges()
        except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
            print(f"Failed to check project change approvals: {error}", file=sys.stderr)
        finally:
            if worker is not None:
                worker.Destroy()

    if results_found:
        FossaUpdateProjects(ref, schedule=False)

    if not getattr(ref, "_approval_dialog_open", False):
        for change in pending_changes:
            if change["requester"] != ref.selected_who:
                ref._approval_dialog_open = True
                CreatorsSettings.show_project_change_approval_dialog(
                    ref,
                    change,
                    lambda approved, _change=change: FossaResolveProjectApproval(
                        ref, _change, approved
                    ),
                )
                break

    if schedule:
        ref.approval_poll_timer = ref.main_window.after(
            60_000, lambda: FossaCheckProjectApprovals(ref, schedule=True)
        )

def FossaResolveProjectApproval(ref, change, approved):
    worker = None
    try:
        worker = core.FossaWorker(
            core.LFRoles.APPROVAL_NEEDED,
            change["directory_path"],
            ref.selected_who,
            ref.database,
        )
        worker.ResolveProjectStructureChange(
            change["project_id"],
            change["request_id"],
            ref.selected_who,
            approved,
        )
    except (OSError, RuntimeError, ValueError) as error:
        from tkinter import messagebox

        messagebox.showerror(
            "Could not resolve project change",
            str(error),
            parent=ref.main_window,
        )
        return False
    finally:
        if worker is not None:
            worker.Destroy()

    ref._approval_dialog_open = False
    FossaUpdateProjects(ref, schedule=False)
    ref.main_window.after_idle(
        lambda: FossaCheckProjectApprovals(ref, schedule=False)
    )
    return True

def FossaCloseApplication(ref):
    if getattr(ref, "_close_application_started", False):
        return
    ref._close_application_started = True

    main_window = ref.main_window
    cleanup_error = [None]
    started_at = time.monotonic()
    destroy_started = [False]

    def destroy_window():
        if destroy_started[0]:
            return
        destroy_started[0] = True
        try:
            main_window.destroy()
        except tk.TclError:
            pass

    def clean_up_workers():
        try:
            core.FossaWorker.DestroyAll()
        except Exception as error:
            cleanup_error[0] = error

    def poll_close():
        elapsed_ms = (time.monotonic() - started_at) * 1000
        worker = getattr(ref, "_close_application_cleanup", None)
        if worker is not None and not worker.is_alive():
            if cleanup_error[0] is not None:
                print(
                    f"Failed to close Fossa workers: {cleanup_error[0]}",
                    file=sys.stderr,
                )
            destroy_window()
            return
        if elapsed_ms >= CLOSE_APPLICATION_TIMEOUT_MS:
            destroy_window()
            return
        main_window.after(CLOSE_APPLICATION_POLL_MS, poll_close)

    cleanup_worker = threading.Thread(
        target=clean_up_workers,
        name="FossaWorker-Cleanup",
        daemon=True,
    )
    ref._close_application_cleanup = cleanup_worker
    cleanup_worker.start()
    main_window.after(CLOSE_APPLICATION_POLL_MS, poll_close)