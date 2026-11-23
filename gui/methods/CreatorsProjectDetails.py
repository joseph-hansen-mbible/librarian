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
        ref.selected_project = project
        ref.command_project_var.set(project.name)
        ref.project_details_label.configure(text=project.name)
        ref.project_status_var.set(project.status.value)
        ref.project_details_directory_path.configure(text=project.directory_path)
        ref.project_status_menu.configure(state="readonly")
        for listbox in (
            ref.project_character_listbox,
            ref.project_scene_listbox,
            ref.project_shot_listbox,
            ref.project_prop_listbox,
        ):
            listbox.delete(0, tk.END)
        for character in project.characters:
            ref.project_character_listbox.insert(tk.END, character)
        for scene in project.scenes:
            display_name = (
                f'{scene["name"]} - {scene["subtitle"]}'
                if scene.get("subtitle")
                else scene["name"]
            )
            ref.project_scene_listbox.insert(tk.END, display_name)
            for shot in scene["shots"]:
                ref.project_shot_listbox.insert(
                    tk.END,
                    f'{scene["name"]} / {shot}',
                )
        for prop in project.props:
            ref.project_prop_listbox.insert(tk.END, prop)
        structure_counts = (
            ("Characters", len(project.characters)),
            ("Scenes", len(project.scenes)),
            ("Shots", sum(len(scene["shots"]) for scene in project.scenes)),
            ("Props", len(project.props)),
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
        }
        try:
            draft = ref.get_project_structure_draft(project.id)
            if draft is not None:
                draft.update(
                    FossaDB.NormalizeProjectStructure(
                        draft,
                        default_status=project.status.value,
                    )
                )
                draft["base_structure"] = FossaDB.NormalizeProjectStructure(
                    draft.get("base_structure", canonical_structure),
                    default_status=project.status.value,
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
            ref.project_structure_button.configure(state="disabled")
            ref.project_structure_discard_button.configure(state="disabled")
        elif draft is not None and draft.get("state") == "pending":
            ref.project_status_menu.configure(state="disabled")
            ref.project_structure_status_label.configure(
                text="Your project changes are awaiting approval"
            )
            ref.project_structure_button.configure(state="disabled")
            ref.project_structure_discard_button.configure(state="disabled")
        elif stale_draft:
            ref.project_status_menu.configure(state="disabled")
            ref.project_structure_status_label.configure(
                text="Draft is out of date; discard it before editing"
            )
            ref.project_structure_button.configure(state="disabled")
            ref.project_structure_discard_button.configure(state="normal")
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
            ref.project_structure_button.configure(state="normal")
            ref.project_structure_discard_button.configure(
                state="normal" if draft is not None else "disabled"
            )

    @staticmethod
    def discard_project_structure_draft(ref):
        project = getattr(ref, "selected_project", None)
        if project is None:
            return
        try:
            ref.clear_project_structure_draft(project.id)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Could not discard project draft",
                str(error),
                parent=ref.projects_tab,
            )
            return
        ref.project_structure_status_label.configure(text="")
        ref.project_structure_button.configure(state="normal")
        ref.project_structure_discard_button.configure(state="disabled")
        ref.project_status_menu.configure(state="readonly")

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
