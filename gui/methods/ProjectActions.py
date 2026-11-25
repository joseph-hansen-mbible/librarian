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

