from copy import deepcopy
import tkinter as tk
from tkinter import messagebox

from db.fossadb import FossaDB
from methods.ProjectStructureEditor import ProjectStructureEditor
from objects.Project import Status


class CreatorsProjectDetails:
    @staticmethod
    def show_project_details(ref):
        selection = ref.project_listbox.curselection()
        if not selection:
            return
        project = ref.projects[selection[0]]
        previous_project = getattr(ref, "selected_project", None)
        preserve_structure_selection = (
            previous_project is not None and previous_project.id == project.id
        )
        structure_listboxes = (
            ref.project_character_listbox,
            ref.project_scene_listbox,
            ref.project_shot_listbox,
            ref.project_prop_listbox,
            ref.project_setting_listbox,
        )
        selected_structure_items = (
            {
                listbox: [
                    listbox.get(index) for index in listbox.curselection()
                ]
                for listbox in structure_listboxes
            }
            if preserve_structure_selection
            else {}
        )
        ref.selected_project = project
        ref.command_project_var.set(project.name)
        ref.project_details_label.configure(text=project.name)
        ref.project_status_var.set(project.status.value)
        ref.project_details_code.configure(
            text=f"Project Code: {project.project_code or 'Not set'}"
        )
        ref.project_details_directory_path.configure(text=project.directory_path)
        ref.project_status_menu.configure(state="readonly")
        for listbox in structure_listboxes:
            listbox.delete(0, tk.END)
        for character in project.characters:
            ref.project_character_listbox.insert(tk.END, character)
        for level in project.scenes:
            display_name = (
                f'{level["name"]} - {level["subtitle"]}'
                if level.get("subtitle")
                else level["name"]
            )
            ref.project_scene_listbox.insert(tk.END, display_name)
            for shot in level["shots"]:
                ref.project_shot_listbox.insert(
                    tk.END,
                    f'{level["name"]} / {shot}',
                )
            for setting in level["settings"]:
                ref.project_setting_listbox.insert(
                    tk.END,
                    f'{level["name"]} / {setting}',
                )
        for prop in project.props:
            ref.project_prop_listbox.insert(tk.END, prop)
        for listbox, selected_items in selected_structure_items.items():
            for selected_item in selected_items:
                for index in range(listbox.size()):
                    if listbox.get(index) == selected_item:
                        listbox.selection_set(index)
                        break
        structure_counts = (
            ("Characters", len(project.characters)),
            ("Levels", len(project.scenes)),
            ("Shots", sum(len(level["shots"]) for level in project.scenes)),
            ("Props", len(project.props)),
            ("Settings", sum(len(level["settings"]) for level in project.scenes)),
        )
        for title, count in structure_counts:
            ref.project_structure_frames_by_title[title].configure(
                text=f"{title} ({count})"
            )

        canonical_structure = {
            "scenes": project.scenes,
            "characters": project.characters,
            "props": project.props,
            "status": project.status.value,
            "project_code": project.project_code,
        }
        try:
            draft = ref.get_project_structure_draft(project.id)
            if draft is not None:
                draft.update(
                    FossaDB.NormalizeProjectStructure(
                        draft,
                        default_status=project.status.value,
                        default_project_code=project.project_code,
                    )
                )
                draft["base_structure"] = FossaDB.NormalizeProjectStructure(
                    draft.get("base_structure", canonical_structure),
                    default_status=project.status.value,
                    default_project_code=project.project_code,
                )
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Could not load project draft",
                str(error),
                parent=ref.projects_tab,
            )
            draft = None

        stale_draft = (
            draft is not None
            and draft.get("base_structure", canonical_structure)
            != canonical_structure
        )
        ref.project_structure_button.pack_forget()
        ref.project_structure_discard_button.pack_forget()
        if project.pending_change is not None:
            ref.project_status_menu.configure(state="disabled")
            requester = project.pending_change.get("requester", "another user")
            proposed_status = project.pending_change.get(
                "proposed",
                {},
            ).get("status", project.status.value)
            approval_count = len(project.pending_change.get("approvals", []))
            required_approvals = project.pending_change.get(
                "required_approvals",
                2,
            )
            if proposed_status != project.status.value:
                status = (
                    f"Your status change to {proposed_status} has "
                    f"{approval_count}/{required_approvals} approvals"
                    if requester == ref.selected_who
                    else (
                        f"Status change to {proposed_status} from {requester}: "
                        f"{approval_count}/{required_approvals} approvals"
                    )
                )
            else:
                status = (
                    f"Your project changes have "
                    f"{approval_count}/{required_approvals} approvals"
                    if requester == ref.selected_who
                    else (
                        f"Project changes from {requester}: "
                        f"{approval_count}/{required_approvals} approvals"
                    )
                )
            ref.project_structure_status_label.configure(text=status)
            if requester == ref.selected_who:
                CreatorsProjectDetails._show_project_structure_action(
                    ref,
                    ref.project_structure_discard_button,
                )
            else:
                CreatorsProjectDetails._show_project_structure_action(
                    ref,
                    ref.project_structure_button,
                )
        elif draft is not None and draft.get("state") == "pending":
            ref.project_status_menu.configure(state="disabled")
            ref.project_structure_status_label.configure(
                text="Your project changes are awaiting approval"
            )
            CreatorsProjectDetails._show_project_structure_action(
                ref,
                ref.project_structure_discard_button,
            )
        elif stale_draft:
            ref.project_status_menu.configure(state="disabled")
            ref.project_structure_status_label.configure(
                text="Draft is out of date; discard it before editing"
            )
            CreatorsProjectDetails._show_project_structure_action(
                ref,
                ref.project_structure_discard_button,
            )
        else:
            ref.project_status_menu.configure(
                state="disabled" if draft is not None else "readonly"
            )
            ref.project_structure_status_label.configure(
                text=(
                    "Unsubmitted draft saved locally"
                    if draft is not None
                    else ""
                )
            )
            CreatorsProjectDetails._show_project_structure_action(
                ref,
                ref.project_structure_button,
            )

    @staticmethod
    def _show_project_structure_action(ref, button):
        button.configure(state="normal")
        button.pack(side="left", fill="x", expand=True)

    @staticmethod
    def discard_project_structure_draft(ref):
        project = getattr(ref, "selected_project", None)
        if project is None:
            return
        pending_change = project.pending_change
        if pending_change is not None:
            requester = pending_change.get("requester")
            if not ref.selected_who or requester != ref.selected_who:
                messagebox.showerror(
                    "Could not withdraw project changes",
                    "Only the requester can withdraw a pending project change.",
                    parent=ref.projects_tab,
                )
                return
            if not ref.database_connected or ref.database is None:
                messagebox.showerror(
                    "Could not withdraw project changes",
                    "A database connection is required to withdraw a pending project change.",
                    parent=ref.projects_tab,
                )
                return
            worker = None
            try:
                from workers import core

                worker = core.FossaWorker(
                    core.LFRoles.APPROVAL_NEEDED,
                    project.directory_path,
                    ref.selected_who,
                    ref.database,
                )
                worker.WithdrawProjectStructureChange(
                    project.id,
                    pending_change["id"],
                    ref.selected_who,
                )
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                messagebox.showerror(
                    "Could not withdraw project changes",
                    str(error),
                    parent=ref.projects_tab,
                )
                return
            finally:
                if worker is not None:
                    worker.Destroy()
        try:
            ref.clear_project_structure_draft(project.id)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Could not discard project draft",
                str(error),
                parent=ref.projects_tab,
            )
            if pending_change is not None:
                from methods.Helpers import FossaUpdateProjects

                FossaUpdateProjects(ref, schedule=False)
            return
        if pending_change is not None:
            from methods.Helpers import FossaUpdateProjects

            FossaUpdateProjects(ref, schedule=False)
        else:
            CreatorsProjectDetails.show_project_details(ref)

    @staticmethod
    def request_project_status_change(ref):
        project = getattr(ref, "selected_project", None)
        if project is None:
            return
        current_status = project.status.value
        selected_status = ref.project_status_var.get()
        if selected_status == current_status:
            return
        try:
            selected_status = Status(selected_status).value
        except ValueError:
            ref.project_status_var.set(current_status)
            ref.project_status_menu.configure(state="readonly")
            return

        if project.pending_change is not None:
            ref.project_status_var.set(current_status)
            ref.project_status_menu.configure(state="disabled")
            return

        base_structure = {
            "scenes": deepcopy(project.scenes),
            "characters": list(project.characters),
            "props": list(project.props),
            "status": current_status,
        }
        proposed = {
            **base_structure,
            "status": selected_status,
            "project_code": project.project_code,
        }
        ref.project_status_var.set(current_status)
        ref.project_status_menu.configure(state="disabled")
        if not ProjectStructureEditor.request_approval(
            ref,
            project,
            proposed,
            base_structure,
            ref.projects_tab,
        ):
            ref.project_status_menu.configure(state="readonly")

    @staticmethod
    def show_project_structure_editor(ref):
        project = getattr(ref, "selected_project", None)
        if project is None:
            return
        if project.pending_change is not None:
            messagebox.showinfo(
                "Approval pending",
                "This project already has a structure change awaiting approval.",
                parent=ref.projects_tab,
            )
            return
        ProjectStructureEditor(ref, project).show()
