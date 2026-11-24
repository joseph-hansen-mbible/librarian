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

from gui.methods import Helpers
from objects.Project import Project, Status
from objects.BlenderFile import BlenderFile
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
    StartBlenderSessionMonitor,
)

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
    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", "#25292d"),
            ("active", "#3b4045"),
        ],
        foreground=[("selected", "#eff0f1")],
    )
    
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
        command=lambda: FossaExecuteCommand(ref)
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
        command=lambda: FossaOpenSelectedRecentFile(ref),
        state="disabled",
    )
    ref.recent_files_treeview.bind(
        "<<TreeviewSelect>>",
        lambda _event: FossaUpdateRecentFileOpenButton(ref),
    )

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
    
    tools_menu.add_command(label="Fix Stranded Checkouts", command=lambda: print("TODO"))
    tools_menu.add_command(label="Open Records", command=lambda: print("TODO"))
    tools_menu.add_command(label="Free Up Stuck Workers", command=lambda: print("TODO"))
    tools_menu.add_command(label="Restart Fossa", command=lambda: print("TODO"))
    
    menubar.add_cascade(
            label="Tools",
            menu=tools_menu
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
    if schedule and not getattr(ref, "_close_application_started", False):
        ref.status_bar_timer = ref.main_window.after(
            5_000, lambda: FossaStatusBar(ref, schedule=True)
        )

def FossaUpdateMainFileLists(ref, schedule):
    rows = []
    artist = getattr(ref, "selected_who", None)
    database_snapshot = {}

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
            database_snapshot = database_checker.GetDatabaseSnapshot()
            for checkout_artist, cache_data in database_snapshot.items():
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
            database_snapshot = {}
        finally:
            if database_checker is not None:
                database_checker.Destroy()

    all_files_rows, recent_files_rows = _BuildBlenderFileListRows(
        ref,
        database_snapshot,
    )
    Populators.populate_current_files_table(ref, rows)
    Populators.populate_locks_treeview(ref, all_files_rows)
    Populators.populate_recent_files_treeview(ref, recent_files_rows)
    FossaUpdateRecentFileOpenButton(ref)
    if schedule and not getattr(ref, "_close_application_started", False):
        ref.main_file_lists_timer = ref.main_window.after(
            2_000, lambda: FossaUpdateMainFileLists(ref, schedule=True)
        )

def _BuildBlenderFileListRows(ref, database):
    file_index = database.get("__blender_files__", {})
    if not isinstance(file_index, dict):
        file_index = {}

    file_records = {}
    recent_entries = {}
    checkout_owners = {}
    for filepath, metadata in file_index.items():
        if not isinstance(filepath, str) or not filepath:
            continue
        normalized_path = _NormalizeFilePath(filepath)
        file_records[normalized_path] = metadata if isinstance(metadata, dict) else {}
        opened_by = (
            metadata.get("last_opened_by_artist", {})
            if isinstance(metadata, dict)
            else {}
        )
        if isinstance(opened_by, dict):
            for artist, opened_at in opened_by.items():
                if isinstance(artist, str) and artist:
                    recent_entries[(normalized_path, artist)] = opened_at

    for artist, artist_data in database.items():
        if artist in {"__projects__", "__blender_files__"}:
            continue
        if not isinstance(artist_data, dict):
            continue
        recent_files = artist_data.get("recent_files", [])
        if isinstance(recent_files, list):
            for filepath in recent_files:
                if isinstance(filepath, str) and filepath:
                    normalized_path = _NormalizeFilePath(filepath)
                    recent_entries.setdefault(
                        (normalized_path, str(artist)),
                        _LastOpenedByArtist(
                            file_records.get(normalized_path, {}),
                            str(artist),
                        ),
                    )

        current_file = artist_data.get("current_file")
        if isinstance(current_file, str) and current_file:
            normalized_path = _NormalizeFilePath(current_file)
            checkout_owners.setdefault(normalized_path, str(artist))
            recent_entries.setdefault(
                (normalized_path, str(artist)),
                _LastOpenedByArtist(
                    file_records.get(normalized_path, {}),
                    str(artist),
                ),
            )

    all_paths = set(file_records)
    all_paths.update(filepath for filepath, _artist in recent_entries)
    all_files_rows = []
    for filepath in sorted(all_paths, key=str.casefold):
        metadata = file_records.get(filepath, {})
        project_name = metadata.get("project_name", "")
        if not isinstance(project_name, str):
            project_name = ""
        if not project_name:
            project_name = _ProjectNameForPath(ref, filepath)

        scene = metadata.get("scene", "")
        if not isinstance(scene, str):
            scene = ""
        if not scene and Path(filepath).parent.name.startswith("Scene "):
            scene = Path(filepath).parent.name.removeprefix("Scene ")

        checklist = metadata.get("checklist", {})
        if not isinstance(checklist, dict):
            checklist = {}
        checklist_count = sum(value is True for value in checklist.values())
        version = metadata.get("version", "")
        if isinstance(version, int):
            version = f"{version:02d}"

        all_files_rows.append(
            (
                project_name,
                scene,
                _StringValue(metadata.get("shot")),
                _StringValue(version),
                _StringValue(metadata.get("action")),
                _StringValue(metadata.get("status")),
                f"{checklist_count}/{len(checklist)}",
                _StringValue(metadata.get("unlock_approvals", 0)),
            )
        )
    all_files_rows.sort(
        key=lambda row: tuple(str(value).casefold() for value in row)
    )

    recent_files_rows = []
    for (filepath, artist), opened_at in recent_entries.items():
        metadata = file_records.get(filepath, {})
        recent_files_rows.append(
            {
                "values": (
                    Path(filepath).name,
                    artist,
                    _FormatRecentFileDate(opened_at),
                    _StringValue(metadata.get("status")),
                ),
                "filepath": filepath,
                "checked_out_by": checkout_owners.get(filepath),
                "metadata": metadata,
                "opened_at": opened_at if isinstance(opened_at, str) else "",
            }
        )
    recent_files_rows.sort(
        key=lambda row: (
            bool(row["opened_at"]),
            row["opened_at"],
            row["values"][1].casefold(),
            row["values"][0].casefold(),
        ),
        reverse=True,
    )
    return all_files_rows, recent_files_rows

def _ProjectNameForPath(ref, filepath):
    project = _ProjectForPath(ref, filepath)
    return project.name if project is not None else ""

def _ProjectForPath(ref, filepath):
    path = Path(_NormalizeFilePath(filepath))
    matching_projects = []
    for project in getattr(ref, "projects", []):
        try:
            project_path = Path(project.directory_path).expanduser().resolve()
            if path.is_relative_to(project_path):
                matching_projects.append((len(str(project_path)), project))
        except (OSError, RuntimeError, TypeError, ValueError):
            continue
    return max(matching_projects, default=(0, None), key=lambda match: match[0])[1]

def _NormalizeFilePath(filepath):
    try:
        return str(Path(filepath).expanduser().resolve())
    except (OSError, RuntimeError, TypeError, ValueError):
        return str(filepath)

def _LastOpenedByArtist(metadata, artist):
    opened_by = metadata.get("last_opened_by_artist", {})
    if not isinstance(opened_by, dict):
        return ""
    opened_at = opened_by.get(artist, "")
    return opened_at if isinstance(opened_at, str) else ""

def _StringValue(value):
    if isinstance(value, str):
        return value
    return "" if value is None else str(value)

def _FormatRecentFileDate(opened_at):
    if not isinstance(opened_at, str) or not opened_at:
        return ""
    try:
        timestamp = datetime.datetime.fromisoformat(opened_at)
    except ValueError:
        return ""
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone()
    return timestamp.strftime("%Y-%m-%d %H:%M")

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
                    props=record.get("props", []),
                    pending_change=record.get("pending_change"),
                    project_code=record.get("project_code", ""),
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
    if schedule and not getattr(ref, "_close_application_started", False):
        ref.projects_timer = ref.main_window.after(
            5_000, lambda: FossaUpdateProjects(ref, schedule=True)
        )

def FossaCheckProjectApprovals(ref, schedule):
    if getattr(ref, "_close_application_started", False):
        return
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
            if (
                change["requester"] != ref.selected_who
                and ref.selected_who not in change.get("approvals", [])
            ):
                ref._approval_dialog_open = True
                CreatorsProjects.show_project_change_approval_dialog(
                    ref,
                    change,
                    lambda approved, _change=change: FossaResolveProjectApproval(
                        ref, _change, approved
                    ),
                )
                break

    if schedule and not getattr(ref, "_close_application_started", False):
        ref.approval_poll_timer = ref.main_window.after(
            20_000, lambda: FossaCheckProjectApprovals(ref, schedule=True)
        )

def FossaExecuteCommand(ref):
    try:
        action = ref.command_action_var.get()
        project_name = ref.command_project_var.get()
        if action == "Action" or project_name == "Project":
            raise ValueError("Choose an action and project before continuing.")

        project = next(
            (
                project
                for project in getattr(ref, "projects", [])
                if project.name == project_name
            ),
            None,
        )
        if project is None:
            raise ValueError("The selected project is no longer available.")

        if action not in Populators.ACTIONS:
            raise ValueError(f"Unknown Blender action {action!r}.")

        needs_scene = (
            action
            in Populators.SCENE_ONLY_ACTIONS
            | Populators.SHOT_ACTIONS
            | Populators.PROP_ACTIONS
        )
        selected_level = (
            Populators.selected_command_level(ref) if needs_scene else None
        )
        scene = selected_level["name"] if selected_level is not None else None
        shot = ref.command_shot_var.get()
        character = ref.command_character_var.get()
        prop = ref.command_prop_var.get()
        setting = ref.command_setting_var.get()

        if action in Populators.CHARACTER_ACTIONS and character == "Character":
            raise ValueError("Choose a character before continuing.")
        if action in Populators.PROP_ACTIONS and prop == "Prop":
            raise ValueError("Choose a prop before continuing.")
        if needs_scene and scene is None:
            raise ValueError("Choose a scene before continuing.")
        if action in Populators.SCENE_ONLY_ACTIONS | Populators.PROP_ACTIONS:
            if setting == "Setting":
                raise ValueError("Choose a setting before continuing.")
        if action in Populators.SHOT_ACTIONS and shot == "Shot":
            raise ValueError("Choose a shot before continuing.")

        file_to_open = BlenderFile(
            project,
            action,
            scene=scene,
            shot=shot if action in Populators.SHOT_ACTIONS else None,
            character=(
                character if action in Populators.CHARACTER_ACTIONS else None
            ),
            setting=(
                setting
                if action in Populators.SCENE_ONLY_ACTIONS | Populators.PROP_ACTIONS
                else None
            ),
            prop=prop if action in Populators.PROP_ACTIONS else None,
        )
        file_metadata = _BlenderFileMetadata(file_to_open, project)
        filepath = file_to_open.get_path(
            project.directory_path,
            project.project_code,
        )

        if not getattr(ref, "blender_ready", False):
            raise RuntimeError("The Blender executable is not configured.")
        if not getattr(ref, "database_connected", False) or ref.database is None:
            raise RuntimeError("The database is not connected.")

        artist = getattr(ref, "selected_who", None)
        if not artist:
            raise RuntimeError("Choose an artist before opening a Blender file.")

        if filepath.exists():
            return _CheckoutAndOpenBlenderFile(
                ref,
                artist,
                filepath,
                project.directory_path,
                file_metadata,
            )

        if getattr(ref, "_pending_blender_creation", None) is not None:
            raise RuntimeError(
                "A Blender file creation is already pending."
            )

        filepath.parent.mkdir(parents=True, exist_ok=True)
        ref.database.MarkBlenderFileCreationPending(artist, filepath)
        try:
            ref._blender_session_monitor = StartBlenderSessionMonitor(
                artist,
                project.directory_path,
                ref.database,
                filepath,
                failure_callback=lambda error: _ReportBlenderSessionFailure(
                    ref,
                    error,
                ),
            )
            _LaunchBlender(ref)
        except Exception as error:
            cleanup_errors = []
            try:
                ref.database.ClearBlenderFileCreationPending(artist, filepath)
            except Exception as cleanup_error:
                cleanup_errors.append(
                    f"Could not clear pending file creation: {cleanup_error}"
                )
            rollback_error = _RollbackBlenderCheckout(
                ref,
                artist,
                project.directory_path,
            )
            if rollback_error is not None:
                cleanup_errors.append(
                    f"Could not release the Blender checkout: {rollback_error}"
                )
            if cleanup_errors:
                raise RuntimeError(
                    f"{error}\n" + "\n".join(cleanup_errors)
                ) from error
            raise

        ref._pending_blender_creation = {
            "artist": artist,
            "database": ref.database,
            "filepath": filepath,
            "metadata": file_metadata,
            "project": project,
        }
        pending = ref._pending_blender_creation
        ref.command_execute_button.configure(state="disabled")
        worker = None
        try:
            worker = core.FossaWorker(
                core.LFRoles.CACHING,
                project.directory_path,
                artist,
                ref.database,
                failure_callback=lambda error: _ReportBlenderSessionFailure(
                    ref,
                    error,
                ),
            )
            scheduled = worker.ScheduleBlenderFileCheckout(
                filepath,
                lambda checked_out, error: _SchedulePendingBlenderFileCheckoutResult(
                    ref,
                    pending,
                    checked_out,
                    error,
                ),
            )
            if not scheduled:
                raise RuntimeError("Could not schedule the Blender file checkout.")
        except Exception as error:
            cleanup_errors = []
            try:
                ref.database.ClearBlenderFileCreationPending(artist, filepath)
            except Exception as cleanup_error:
                cleanup_errors.append(
                    f"Could not clear pending file creation: {cleanup_error}"
                )
            ref._pending_blender_creation = None
            ref.command_execute_button.configure(state="normal")
            rollback_error = _RollbackBlenderCheckout(
                ref,
                artist,
                project.directory_path,
            )
            if worker is not None and not worker._closed:
                worker.Destroy()
            if rollback_error is not None:
                cleanup_errors.append(
                    f"Could not release the Blender checkout: {rollback_error}"
                )
            if cleanup_errors:
                raise RuntimeError(
                    f"{error}\n" + "\n".join(cleanup_errors)
                ) from error
            raise
        return True
    except Exception as error:
        messagebox.showerror(
            "Could not open Blender file",
            str(error),
            parent=ref.main_window,
        )
        return False

def _LaunchBlender(ref):
    executable = Path(ref.blender_file_path_variable.get()).expanduser()
    if not executable.exists():
        raise RuntimeError("The configured Blender executable does not exist.")
    if sys.platform == "darwin" and executable.suffix.lower() == ".app":
        subprocess.Popen(["open", "-a", str(executable)])
    else:
        subprocess.Popen([str(executable)])

def _ReportBlenderSessionFailure(ref, message):
    if getattr(ref, "_close_application_started", False):
        return

    def show_error():
        if not getattr(ref, "_close_application_started", False):
            messagebox.showerror(
                "Blender session error",
                message,
                parent=ref.main_window,
            )

    try:
        ref.main_window.after(0, show_error)
    except (RuntimeError, tk.TclError) as error:
        print(
            f"Could not show Blender session error: {error}",
            file=sys.stderr,
        )

def _StopBlenderSessionMonitor(ref):
    monitor = getattr(ref, "_blender_session_monitor", None)
    if monitor is not None:
        monitor.Stop()
        ref._blender_session_monitor = None

def _CheckInBlenderFile(ref, artist, worker_path):
    worker = core.FossaWorker(
        core.LFRoles.CACHING,
        worker_path,
        artist,
        ref.database,
        failure_callback=lambda error: _ReportBlenderSessionFailure(
            ref,
            error,
        ),
    )
    if not worker.CheckInBlenderFile():
        raise RuntimeError(
            "The check-in could not be queued for database update."
        )

def _RollbackBlenderCheckout(ref, artist, worker_path):
    _StopBlenderSessionMonitor(ref)
    try:
        _CheckInBlenderFile(ref, artist, worker_path)
    except Exception as error:
        return error
    return None

def FossaUpdateRecentFileOpenButton(ref):
    selection = ref.recent_files_treeview.selection()
    if not selection:
        ref.open_recent_file_button.configure(state="disabled")
        return

    item_id = selection[0]
    filepath = getattr(ref, "recent_file_paths", {}).get(item_id)
    checked_out_by = getattr(
        ref, "recent_file_checkout_owners", {}
    ).get(item_id)
    is_available = (
        filepath is not None
        and Path(filepath).is_file()
        and checked_out_by is None
        and getattr(ref, "database_connected", False)
        and getattr(ref, "blender_ready", False)
        and bool(getattr(ref, "selected_who", None))
    )
    ref.open_recent_file_button.configure(
        state="normal" if is_available else "disabled"
    )

def FossaOpenSelectedRecentFile(ref):
    selection = ref.recent_files_treeview.selection()
    if not selection:
        return False

    item_id = selection[0]
    filepath = getattr(ref, "recent_file_paths", {}).get(item_id)
    if filepath is None:
        return False
    filepath = Path(filepath)

    try:
        if not ref.database_connected or ref.database is None:
            raise RuntimeError("The database is not connected.")
        if not getattr(ref, "blender_ready", False):
            raise RuntimeError("The Blender executable is not configured.")
        if not filepath.is_file():
            raise FileNotFoundError(f"Recent Blender file is unavailable: {filepath}")
        artist = getattr(ref, "selected_who", None)
        if not artist:
            raise RuntimeError("Choose an artist before opening a Blender file.")

        metadata = getattr(ref, "recent_file_metadata", {}).get(item_id, {})
        project = _ProjectForPath(ref, filepath)
        worker_path = (
            project.directory_path
            if project is not None
            else ref.get_worker_network_base_path()
        )
        return _CheckoutAndOpenBlenderFile(
            ref,
            artist,
            filepath,
            worker_path,
            metadata,
        )
    except Exception as error:
        messagebox.showerror(
            "Could not open recent Blender file",
            str(error),
            parent=ref.main_window,
        )
        FossaUpdateMainFileLists(ref, schedule=False)
        return False

def _CheckoutAndOpenBlenderFile(
    ref,
    artist,
    filepath,
    worker_path,
    metadata,
):
    worker = core.FossaWorker(
        core.LFRoles.CACHING,
        worker_path,
        artist,
        ref.database,
        failure_callback=lambda error: _ReportBlenderSessionFailure(
            ref,
            error,
        ),
    )
    if not worker.CheckOutBlenderFile(filepath):
        raise RuntimeError(
            "This Blender file is already checked out, or the "
            "database is unavailable."
        )

    metadata_error = None
    try:
        ref.database.RecordBlenderFileUse(
            artist,
            filepath,
            metadata,
        )
    except Exception as error:
        metadata_error = error
    FossaUpdateMainFileLists(ref, schedule=False)
    try:
        ref._blender_session_monitor = StartBlenderSessionMonitor(
            artist,
            worker_path,
            ref.database,
            filepath,
            failure_callback=lambda error: _ReportBlenderSessionFailure(
                ref,
                error,
            ),
        )
        _LaunchBlender(ref)
    except Exception as error:
        rollback_error = _RollbackBlenderCheckout(ref, artist, worker_path)
        if rollback_error is not None:
            raise RuntimeError(
                f"{error}\nCould not release the Blender checkout: "
                f"{rollback_error}"
            ) from error
        raise
    if metadata_error is not None:
        messagebox.showerror(
            "Could not update file lists",
            str(metadata_error),
            parent=ref.main_window,
        )
    return True

def _SchedulePendingBlenderFileCheckoutResult(
    ref,
    pending,
    checked_out,
    error,
):
    if getattr(ref, "_close_application_started", False):
        try:
            pending["database"].ClearBlenderFileCreationPending(
                pending["artist"],
                pending["filepath"],
            )
        except Exception as clear_error:
            print(
                f"Failed to clear pending Blender file creation: {clear_error}",
                file=sys.stderr,
            )
        return
    try:
        ref.main_window.after(
            0,
            lambda: _FinishPendingBlenderFileCheckout(
                ref,
                pending,
                checked_out,
                error,
            ),
        )
    except (RuntimeError, tk.TclError) as callback_error:
        print(
            f"Could not report pending Blender file checkout: {callback_error}",
            file=sys.stderr,
        )

def _FinishPendingBlenderFileCheckout(ref, pending, checked_out, error):
    reported_errors = []
    try:
        pending["database"].ClearBlenderFileCreationPending(
            pending["artist"],
            pending["filepath"],
        )
    except Exception as clear_error:
        reported_errors.append(
            f"Could not clear pending file creation: {clear_error}"
        )

    if checked_out:
        try:
            pending["database"].RecordBlenderFileUse(
                pending["artist"],
                pending["filepath"],
                pending["metadata"],
            )
        except Exception as metadata_error:
            reported_errors.append(
                f"Could not record Blender file metadata: {metadata_error}"
            )

    if not checked_out:
        rollback_error = _RollbackBlenderCheckout(
            ref,
            pending["artist"],
            pending["project"].directory_path,
        )
        if rollback_error is not None:
            reported_errors.append(
                f"Could not release the Blender checkout: {rollback_error}"
            )

    ref._pending_blender_creation = None
    ref.command_execute_button.configure(state="normal")
    FossaUpdateMainFileLists(ref, schedule=False)
    if not checked_out and error is None:
        error = RuntimeError(
            "The new Blender file could not be checked out; it may already "
            "be in use or the database may be unavailable."
        )
    if error is not None:
        reported_errors.append(str(error))
    if reported_errors:
        messagebox.showerror(
            "Could not check out Blender file",
            "\n\n".join(reported_errors),
            parent=ref.main_window,
        )

def _BlenderFileMetadata(blender_file, project):
    return {
        "project_name": project.name,
        "project_directory": str(
            Path(project.directory_path).expanduser().resolve()
        ),
        "scene": blender_file.scene or "",
        "shot": blender_file.shot or "",
        "character": blender_file.character or "",
        "prop": blender_file.prop or "",
        "setting": blender_file.setting or "",
        "version": blender_file.version,
        "action": blender_file.action,
        "status": blender_file.status.value,
        "checklist": dict(blender_file.checklist),
        "unlock_approvals": blender_file.unlock_approvals,
    }

def FossaResolveProjectApproval(ref, change, approved):
    if getattr(ref, "_close_application_started", False):
        return False
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
    ref.approval_check_idle_timer = ref.main_window.after_idle(
        lambda: FossaCheckProjectApprovals(ref, schedule=False)
    )
    return True

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