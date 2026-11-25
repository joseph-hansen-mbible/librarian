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

def _OpenRecordsPopup(ref):
    records_path = (
        ref.database.network_base_path
        / "fossa"
        / f"{core.LFRoles.RECORDS.value}.flf"
    )

    popup = tk.Toplevel(ref.main_window)
    popup.title("Fossa Records")
    popup.geometry("900x600")
    popup.transient(ref.main_window)

    text_frame = ttk.Frame(popup)
    text_frame.pack(fill="both", expand=True, padx=10, pady=10)

    text = tk.Text(
        text_frame,
        wrap="none",
        font=ref.status_font,
    )
    vertical_scrollbar = ttk.Scrollbar(
        text_frame,
        orient="vertical",
        command=text.yview,
    )
    horizontal_scrollbar = ttk.Scrollbar(
        text_frame,
        orient="horizontal",
        command=text.xview,
    )
    text.configure(
        yscrollcommand=vertical_scrollbar.set,
        xscrollcommand=horizontal_scrollbar.set,
    )

    text.grid(row=0, column=0, sticky="nsew")
    vertical_scrollbar.grid(row=0, column=1, sticky="ns")
    horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
    text_frame.rowconfigure(0, weight=1)
    text_frame.columnconfigure(0, weight=1)

    try:
        if records_path.is_file():
            records = records_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        else:
            records = "No records file exists yet."
    except OSError as error:
        records = f"Could not read records: {error}"

    text.insert("1.0", records)
    text.configure(state="disabled")

def _FreeUpStuckWorkers(ref):
    try:
        core.FossaWorker.DestroyAll()
        messagebox.showinfo(
            "Free Up Stuck Workers",
            "All active Fossa workers were destroyed.",
            parent=ref.main_window,
        )
    except Exception as error:
        messagebox.showerror(
            "Free Up Stuck Workers",
            f"Could not destroy all active workers: {error}",
            parent=ref.main_window,
        )

def _ShowApprovalLog(ref):
    popup = tk.Toplevel(ref.main_window)
    popup.title("Approval Log")
    popup.geometry("700x500")
    popup.transient(ref.main_window)

    text_frame = ttk.Frame(popup)
    text_frame.pack(fill="both", expand=True, padx=10, pady=10)
    text = tk.Text(text_frame, wrap="word", state="normal")
    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    text.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    snapshot = ref.database.GetDatabaseSnapshot()
    lines = ["APPROVAL / REJECTION LOG", ""]

    projects = snapshot.get("__projects__", {})
    if isinstance(projects, dict):
        for project_id, project in projects.items():
            if not isinstance(project, dict):
                continue
            requests = project.get("structure_change_requests", {})
            if not isinstance(requests, dict):
                continue
            for request_id, request in requests.items():
                if not isinstance(request, dict):
                    continue
                entries = list(request.get("approval_log", []))
                entries.extend(request.get("rejection_log", []))
                if not entries:
                    continue
                lines.append(
                    f"Project: {project.get('name', project_id)} "
                    f"(request {request_id})"
                )
                for entry in entries:
                    if isinstance(entry, dict):
                        lines.append(
                            f"  {entry.get('timestamp', '')} - "
                            f"{entry.get('reviewer', 'Unknown')} - "
                            f"{entry.get('decision', 'unknown')}"
                        )
                lines.append("")

    files = snapshot.get("__blender_files__", {})
    if isinstance(files, dict):
        for filepath, metadata in files.items():
            if not isinstance(metadata, dict):
                continue
            entries = list(metadata.get("unlock_approval_log", []))
            entries.extend(metadata.get("unlock_rejection_log", []))
            if not entries:
                continue
            lines.append(f"SSOT unlock: {Path(filepath).name}")
            for entry in entries:
                if isinstance(entry, dict):
                    lines.append(
                        f"  {entry.get('timestamp', '')} - "
                        f"{entry.get('reviewer', 'Unknown')} - "
                        f"{entry.get('decision', 'unknown')}"
                    )
            lines.append("")

    text.insert("1.0", "\n".join(lines) if len(lines) > 2 else "No approval activity logged.")
    text.configure(state="disabled")

def _SelectedLockFile(ref):
    selection = ref.locks_treeview.selection()
    if not selection:
        return None, None
    item_id = selection[0]
    filepath = getattr(ref, "all_files_paths", {}).get(item_id)
    if not filepath:
        return None, None
    metadata = getattr(ref, "all_files_metadata", {}).get(item_id, {})
    return filepath, metadata if isinstance(metadata, dict) else {}

def FossaUpdateSSOTButtons(ref):
    filepath, metadata = _SelectedLockFile(ref)
    if not isinstance(metadata, dict):
        metadata = {}
    has_selection = filepath is not None
    try:
        status = str(metadata.get("status", "")).casefold()
    except:
        status = "wip"
    is_ssot = has_selection and status == "ssot"
    checklist = metadata.get("checklist", {})
    checklist_complete = (
        isinstance(checklist, dict)
        and bool(checklist)
        and all(value is True for value in checklist.values())
    )
    unlock_requested = bool(metadata.get("unlock_requested", False))
    ref.view_ssot_checklist_button.configure(
        state="normal" if has_selection else "disabled"
    )
    if has_selection and not is_ssot and checklist_complete and not unlock_requested:
        ref.request_unlock_ssot_button.configure(state="normal")
        if not ref.request_unlock_ssot_button.winfo_manager():
            ref.request_unlock_ssot_button.pack(
                pady=5,
                fill="x",
                expand=True,
            )
    else:
        ref.request_unlock_ssot_button.pack_forget()

def FossaOpenSSOTChecklist(ref):
    filepath, initial_metadata = _SelectedLockFile(ref)
    if filepath is None:
        return

    snapshot = ref.database.GetDatabaseSnapshot()
    file_index = snapshot.get("__blender_files__", {})
    file_metadata = (
        file_index.get(filepath, {})
        if isinstance(file_index, dict)
        else {}
    )
    if not isinstance(file_metadata, dict):
        file_metadata = {}
    if not file_metadata:
        file_metadata = dict(initial_metadata)

    checklist = file_metadata.get("checklist", {})
    if not isinstance(checklist, dict):
        checklist = {}
    is_ssot = str(file_metadata.get("status", "")).casefold() == "ssot"
    checklist_complete = bool(checklist) and all(
        value is True for value in checklist.values()
    )
    unlock_requested = bool(file_metadata.get("unlock_requested", False))
    show_approval_controls = unlock_requested and checklist_complete

    owner = None
    for artist, artist_data in snapshot.items():
        if artist in {"__projects__", "__blender_files__"}:
            continue
        if isinstance(artist_data, dict) and (
            artist_data.get("current_file") == filepath
        ):
            owner = str(artist)
            break

    popup = tk.Toplevel(ref.main_window)
    popup.title("SSOT Checklist")
    popup.geometry("620x620")
    popup.transient(ref.main_window)

    main_frame = ttk.Frame(popup)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    canvas = tk.Canvas(main_frame)
    scrollbar = ttk.Scrollbar(
        main_frame,
        orient="vertical",
        command=canvas.yview,
    )
    checklist_frame = ttk.Frame(canvas)
    checklist_frame.bind(
        "<Configure>",
        lambda _event: canvas.configure(
            scrollregion=canvas.bbox("all")
        ),
    )
    canvas.create_window((0, 0), window=checklist_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    variables = {}
    for item, checked in checklist.items():
        variable = tk.BooleanVar(
            value=checked is True,
        )
        variables[item] = variable
        ttk.Checkbutton(
            checklist_frame,
            text=str(item),
            variable=variable,
        ).pack(anchor="w", padx=5, pady=2)

    button_frame = ttk.Frame(popup)
    button_frame.pack(fill="x", padx=10, pady=(0, 10))

    def save_checklist():
        try:
            updated = {
                item: bool(variable.get())
                for item, variable in variables.items()
            }
            ref.database.UpdateBlenderFileChecklist(
                ref.selected_who or "",
                filepath,
                updated,
            )
            _Helpers.FossaUpdateMainFileLists(ref, schedule=False)
            popup.destroy()
        except Exception as error:
            messagebox.showerror(
                "SSOT Checklist",
                str(error),
                parent=popup,
            )

    def request_unlock():
        try:
            ref.database.RequestSSOTUnlock(
                ref.selected_who or "",
                filepath,
            )
            _Helpers.FossaUpdateMainFileLists(ref, schedule=False)
            popup.destroy()
            messagebox.showinfo(
                "SSOT Unlock",
                "Unlock requested. Two approvals are required.",
                parent=ref.main_window,
            )
        except Exception as error:
            messagebox.showerror(
                "SSOT Unlock",
                str(error),
                parent=popup,
            )

    def approve_unlock():
        try:
            approval_count = ref.database.ApproveSSOTUnlock(
                owner or "",
                filepath,
                ref.selected_who or "",
            )
            _Helpers.FossaUpdateMainFileLists(ref, schedule=False)
            popup.destroy()
            messagebox.showinfo(
                "SSOT Unlock",
                f"Approval recorded ({approval_count}/"
                f"{ref.database.REQUIRED_PROJECT_APPROVALS}).",
                parent=ref.main_window,
            )
        except Exception as error:
            messagebox.showerror(
                "SSOT Unlock",
                str(error),
                parent=popup,
            )

    def reject_unlock():
        try:
            ref.database.RejectSSOTUnlock(
                owner or "",
                filepath,
                ref.selected_who or "",
            )
            _Helpers.FossaUpdateMainFileLists(ref, schedule=False)
            popup.destroy()
            messagebox.showinfo(
                "SSOT Unlock",
                "Unlock rejection recorded.",
                parent=ref.main_window,
            )
        except Exception as error:
            messagebox.showerror(
                "SSOT Unlock",
                str(error),
                parent=popup,
            )

    ttk.Button(
        button_frame,
        text="Save Checklist",
        command=save_checklist,
    ).pack(side="left")
    if show_approval_controls:
        approval_frame = ttk.LabelFrame(
            popup,
            text="SSOT Unlock Approvals",
        )
        approval_frame.pack(
            fill="x",
            padx=10,
            pady=(0, 10),
            before=button_frame,
        )

        approvals = file_metadata.get("unlock_approval_names", [])
        if not isinstance(approvals, list):
            approvals = []
        approvals = [name for name in approvals if isinstance(name, str)]
        approval_label = ttk.Label(
            approval_frame,
            text=f"{len(approvals)}/{ref.database.REQUIRED_PROJECT_APPROVALS} "
            f"approvals"
            + (f" ({', '.join(approvals)})" if approvals else ""),
        )
        approval_label.pack(anchor="w", padx=5, pady=5)
        rejections = file_metadata.get("unlock_rejection_names", [])
        if not isinstance(rejections, list):
            rejections = []
        rejections = [name for name in rejections if isinstance(name, str)]
        ttk.Label(
            approval_frame,
            text=f"Rejected by: {', '.join(rejections) if rejections else 'none yet'}",
        ).pack(anchor="w", padx=5, pady=(0, 5))
        ttk.Button(
            button_frame,
            text="Approve Unlock",
            command=approve_unlock,
        ).pack(side="left", padx=(5, 0))
        ttk.Button(
            button_frame,
            text="Reject Unlock",
            command=reject_unlock,
            style="Reject.TButton",
        ).pack(side="left", padx=(5, 0))
    elif checklist_complete and not is_ssot and not unlock_requested:
        ttk.Button(
            button_frame,
            text="Request Unlock",
            command=request_unlock,
        ).pack(side="left", padx=(5, 0))

def _RestartFossa(ref):
    if not messagebox.askyesno(
        "Restart Fossa",
        "Restart Fossa and close the current application window?",
        parent=ref.main_window,
    ):
        return

    main_window = ref.main_window
    _Helpers._cancel_scheduled_callbacks(ref, main_window)

    def restart():
        cleanup_error = None
        try:
            BlenderSessionMonitor.StopAll()
        except Exception as error:
            cleanup_error = error
        try:
            core.FossaWorker.DestroyAll()
        except Exception as error:
            if cleanup_error is None:
                cleanup_error = error

        def finish_restart():
            if cleanup_error is not None:
                messagebox.showerror(
                    "Restart Fossa",
                    f"Fossa could not be cleaned up before restarting: "
                    f"{cleanup_error}",
                    parent=main_window,
                )
                return

            try:
                if getattr(sys, "frozen", False):
                    command = [sys.executable, *sys.argv[1:]]
                else:
                    command = [sys.executable, *sys.argv]
                subprocess.Popen(
                    command,
                    cwd=str(PROJECT_ROOT),
                    close_fds=True,
                )
                main_window.destroy()
            except Exception as error:
                messagebox.showerror(
                    "Restart Fossa",
                    f"Fossa could not restart: {error}",
                    parent=main_window,
                )

        try:
            main_window.after(0, finish_restart)
        except (RuntimeError, tk.TclError):
            pass

    threading.Thread(
        target=restart,
        name="FossaRestart",
        daemon=True,
    ).start()

def _FixStrandedCheckouts(ref):
    if not messagebox.askyesno(
        "Fix Stranded Checkouts",
        "Discard every checked-out or pending Blender file? "
        "Unsaved work must be saved or lost outside Fossa.",
        parent=ref.main_window,
    ):
        return

    if getattr(ref, "_fix_stranded_checkouts_running", False):
        return
    ref._fix_stranded_checkouts_running = True
    ref.main_window.configure(cursor="watch")

    def cleanup():
        try:
            BlenderSessionMonitor.StopAll()
            core.FossaWorker.DestroyAll()
            snapshot = ref.database.GetDatabaseSnapshot()
            artists = [
                str(artist)
                for artist, artist_data in snapshot.items()
                if artist not in {"__projects__", "__blender_files__"}
                and isinstance(artist_data, dict)
            ]
            for artist in artists:
                BlenderSessionCachePath(artist).unlink(missing_ok=True)
            try:
                from workers.platform_dirs import PlatformDirs

                appdata = PlatformDirs(
                    "Fossa",
                    "Joseph Hansen",
                    ensure_exists=True,
                ).user_data_path
                (appdata / f"{core.LFRoles.CACHING.value}.flf").unlink(
                    missing_ok=True
                )
            except OSError:
                pass
            cleared_artists = ref.database.ResetStrandedCheckouts()
            result = (len(cleared_artists), None)
        except Exception as error:
            result = (None, error)

        def finish():
            ref._fix_stranded_checkouts_running = False
            ref.main_window.configure(cursor="")
            if result[1] is not None:
                messagebox.showerror(
                    "Fix Stranded Checkouts",
                    str(result[1]),
                    parent=ref.main_window,
                )
                return

            ref._pending_blender_creation = None
            ref.command_execute_button.configure(state="normal")
            _Helpers.FossaUpdateMainFileLists(ref, schedule=False)
            messagebox.showinfo(
                "Fix Stranded Checkouts",
                f"Cleared {result[0]} checked-out or pending artist state(s).",
                parent=ref.main_window,
            )

        try:
            ref.main_window.after(0, finish)
        except (RuntimeError, tk.TclError):
            ref._fix_stranded_checkouts_running = False

    try:
        threading.Thread(
            target=cleanup,
            name="Fossa-Stranded-Checkout-Cleanup",
            daemon=True,
        ).start()
    except RuntimeError as error:
        ref._fix_stranded_checkouts_running = False
        ref.main_window.configure(cursor="")
        messagebox.showerror(
            "Fix Stranded Checkouts",
            f"Could not start checkout cleanup: {error}",
            parent=ref.main_window,
        )

def FossaMenus(ref):
    root = ref.main_window
    menubar = Menu(ref.main_window)
    root.config(menu=menubar)
    options_menu = Menu(menubar, tearoff=False)
    settings_menu = Menu(menubar,tearoff=False)
    tools_menu = Menu(menubar, tearoff=False)

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
    
    tools_menu.add_command(
        label="Fix Stranded Checkouts",
        command=lambda: _FixStrandedCheckouts(ref),
    )
    tools_menu.add_command(
        label="Show Approval Log",
        command=lambda: _ShowApprovalLog(ref),
    )
    tools_menu.add_command(
        label="Open Records",
        command=lambda: _OpenRecordsPopup(ref),
    )
    tools_menu.add_command(
        label="Free Up Stuck Workers",
        command=lambda: _FreeUpStuckWorkers(ref),
    )
    tools_menu.add_command(
        label="Restart Fossa",
        command=lambda: _RestartFossa(ref),
    )
    
    menubar.add_cascade(
            label="Tools",
            menu=tools_menu
        )
