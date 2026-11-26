import datetime
import os
import subprocess
import tkinter as tk
from tkinter import Menu, messagebox, ttk
from pathlib import Path
import sys
import threading
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui.methods import Helpers as _Helpers
from objects.Project import Project, Status
from objects.BlenderFile import BlenderFile, BlenderFileStatus
from whoami import Who
from methods.Populators import Populators
from methods.Creators import CreatorsMaintab as Creators
from methods.CreatorsSettings import CreatorsSettings
from methods.CreatorsProjects import CreatorsProjects
from objects.References import References
from db import fossadb
from workers import core
from workers.blender_session import (
    BlenderSessionMonitor,
    BlenderSessionCachePath,
    StartBlenderSessionMonitor,
)

CLOSE_APPLICATION_TIMEOUT_MS = 1_000
CLOSE_APPLICATION_POLL_MS = 50

def FossaMain(ref, on_ready=None):
    ref.load_selected_who()
    ref.update_status_bar = lambda: _Helpers.FossaStatusBar(ref, schedule=False)

    ref.main_window = Creators.setup_main_window(tk.Tk())
    ref.main_window.protocol(
        "WM_DELETE_WINDOW", lambda: FossaCloseApplication(ref)
    )
    
    style = ttk.Style(ref.main_window)
    theme_script = PROJECT_ROOT / "themes" / "tkbreezedark" / "breeze-dark.tcl"
    ref.main_window.tk.call("source", str(theme_script))
    style.theme_use("breeze-dark")
    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", "#25292d"),
            ("active", "#3b4045"),
        ],
        foreground=[("selected", "#eff0f1")],
    )
    
    _Helpers.FossaMenus(ref)
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
    ref.projects_tab = CreatorsProjects.create_projects_tab(
        ref,
        ref.tabs_container,
    )
    ref.projects_tab.ref = ref
    
    ref.all_files_tab = Creators.create_tab_all_files(ref.tabs_container)
    ref.all_files_tab.ref = ref
    
    ref.file_lists_frame = Creators.create_file_lists_frame(ref.main_tab)
    ref.recent_files_frame = Creators.create_recent_files_frame(ref.file_lists_frame)
    ref.main_content_left_frame = Creators.create_main_content_left_frame(ref.file_lists_frame)
    ref.command_bar_frame = Creators.create_command_entry_frame(ref.main_content_left_frame)
    Creators.fill_command_entry_frame(ref)
    ref.command_execute_button.configure(
        command=lambda: _Helpers.FossaExecuteCommand(ref)
    )
    ref.current_files_frame = Creators.create_current_files_frame(ref.main_content_left_frame)
    Creators.create_current_files_header(ref)
    
    Creators.create_current_files_table(ref)
    Creators.create_recent_files_header(ref)
    ref.recent_files_tree_frame = Creators.create_recent_files_tree_frame(ref)
    Creators.create_recent_files_treeview(ref)
    Creators.create_recent_files_note_frame(ref)
    Creators.create_recent_files_open_button(ref)
    ref.open_recent_file_button.configure(
        command=lambda: _Helpers.FossaOpenSelectedRecentFile(ref),
        state="disabled",
    )
    ref.recent_files_treeview.bind(
        "<<TreeviewSelect>>",
        lambda _event: _Helpers.FossaUpdateRecentFileOpenButton(ref),
    )

    ref.locks_frame = Creators.create_locks_frame(ref.all_files_tab)
    ref.locks_details_frame = Creators.create_locks_details_frame(ref.all_files_tab)
    Creators.create_locks_treeview(ref)
    Creators.create_locks_details_buttons(ref)
    ref.locks_treeview.bind(
        "<<TreeviewSelect>>",
        lambda _event: _Helpers.FossaUpdateSSOTButtons(ref),
    )
    ref.open_file_button.configure(
        command=lambda: _Helpers.FossaOpenSelectedLockFile(ref),
        state="disabled",
    )
    ref.view_ssot_checklist_button.configure(
        command=lambda: _Helpers.FossaOpenSSOTChecklist(ref),
        state="disabled",
    )
    ref.request_unlock_ssot_button.configure(
        command=lambda: _Helpers.FossaOpenSSOTChecklist(ref),
        state="disabled",
    )
    
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
    _Helpers.FossaStatusBar(ref, True)
    _Helpers.FossaUpdateMainFileLists(ref, schedule=True)
    _Helpers.FossaUpdateProjects(ref, schedule=True)
    _Helpers.FossaCheckProjectApprovals(ref, schedule=True)

    if on_ready is not None:
        ref.main_ready_timer = ref.main_window.after_idle(on_ready)

    try:
        FossaIcon(ref.main_window)
    except Exception as e:
        print(f"Failed to set application icon: {e}", file=sys.stderr)
        ref.main_window.mainloop()

def FossaIcon(main_window):
    icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
    photo = tk.PhotoImage(file=str(icon_path))
    main_window.iconphoto(False, photo)
    main_window.mainloop()

def _cancel_scheduled_callbacks(ref, main_window):
    for timer_name in (
        "main_ready_timer",
        "status_bar_timer",
        "main_file_lists_timer",
        "projects_timer",
        "approval_poll_timer",
        "approval_check_idle_timer",
        "close_poll_timer",
    ):
        timer_id = getattr(ref, timer_name, None)
        if timer_id is None:
            continue
        try:
            main_window.after_cancel(timer_id)
        except tk.TclError:
            pass
        setattr(ref, timer_name, None)

def FossaCloseApplication(ref):
    if getattr(ref, "_close_application_started", False):
        return
    ref._close_application_started = True

    main_window = ref.main_window
    _cancel_scheduled_callbacks(ref, main_window)
    cleanup_error = [None]
    started_at = time.monotonic()
    destroy_started = [False]

    def destroy_window():
        if destroy_started[0]:
            return
        destroy_started[0] = True
        _cancel_scheduled_callbacks(ref, main_window)
        try:
            main_window.destroy()
        except tk.TclError:
            pass

    def clean_up_workers():
        try:
            artist = getattr(ref, "selected_who", None)
            if artist:
                worker_path = ref.get_worker_network_base_path()
                try:
                    from gui.methods.BlenderActions import _CheckInBlenderFile
                    _CheckInBlenderFile(ref, artist, worker_path)
                except Exception as checkin_error:
                    print(
                        f"Failed to check in Blender session during shutdown: "
                        f"{checkin_error}",
                        file=sys.stderr,
                    )
            BlenderSessionMonitor.StopAll()
            core.FossaWorker.DestroyAll()
        except Exception as error:
            cleanup_error[0] = error

    def poll_close():
        ref.close_poll_timer = None
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
        ref.close_poll_timer = main_window.after(
            CLOSE_APPLICATION_POLL_MS,
            poll_close,
        )

    cleanup_worker = threading.Thread(
        target=clean_up_workers,
        name="FossaWorker-Cleanup",
        daemon=True,
    )
    ref._close_application_cleanup = cleanup_worker
    cleanup_worker.start()
    ref.close_poll_timer = main_window.after(
        CLOSE_APPLICATION_POLL_MS,
        poll_close,
    )
