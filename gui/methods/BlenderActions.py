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
    _Helpers.FossaUpdateMainFileLists(ref, schedule=False)
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
    _Helpers.FossaUpdateMainFileLists(ref, schedule=False)
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

