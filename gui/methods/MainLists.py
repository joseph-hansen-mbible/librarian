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
            {
                "filepath": filepath,
                "metadata": metadata,
                "values": (
                    project_name,
                    scene,
                    _StringValue(metadata.get("shot")),
                    _StringValue(version),
                    _StringValue(metadata.get("action")),
                    _StringValue(metadata.get("status")),
                    f"{checklist_count}/{len(checklist)}",
                    _StringValue(metadata.get("unlock_approvals", 0)),
                ),
            }
        )
    all_files_rows.sort(
        key=lambda row: tuple(
            str(value).casefold()
            for value in (
                row["values"] if isinstance(row, dict) else row
            )
        )
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
        return _Helpers._CheckoutAndOpenBlenderFile(
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

