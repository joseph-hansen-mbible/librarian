import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from copy import deepcopy
from pathlib import Path
import re
import sys
import uuid

from methods.Filters import Filters
from methods.Populators import Populators
from objects.Project import Project, Status

class CreatorsSettings:    
    SHOT_NAME_PATTERN = re.compile(r"(?:0[1-9]|[1-9][0-9])[A-Z]")

    @staticmethod
    def create_settings_window(ref):
        settings_window = tk.Toplevel(ref.main_window)
        settings_window.title("Settings")
        settings_window.geometry("700x700")
        settings_window.minsize(500, 400)
        settings_window.transient(ref.main_window)
        settings_window.withdraw()
        settings_window.protocol(
            "WM_DELETE_WINDOW",
            lambda: (
                settings_window.withdraw()
                if ref.selected_who
                else settings_window.lift()
            ),
        )

        ref.settings_tab = ttk.Frame(settings_window)
        ref.settings_tab.pack(fill='both', expand=True)
        return settings_window

    @staticmethod
    def create_settings_button(ref, parent):
        settings_icon_path = Path(__file__).resolve().parent.parent / "assets" / "settings.png"
        ref.settings_icon = tk.PhotoImage(file=str(settings_icon_path)).subsample(2, 2)
        ref.settings_button = ttk.Button(
            parent,
            image=ref.settings_icon,
            command=lambda: CreatorsSettings.show_settings_window(ref),
        )
        ref.settings_button.pack(side='right', padx=5)

    @staticmethod
    def show_settings_window(ref):
        ref.settings_window.deiconify()
        ref.settings_window.lift()
        ref.settings_window.focus_set()

    @staticmethod
    def create_settings_projects_frame(ref):
        projects_frame = ttk.LabelFrame(ref.settings_tab, text="Projects")
        projects_frame.pack(fill='x', expand=False, padx=5, pady=5, side='top')
        
        new_project_button = ttk.Button(
            projects_frame,
            text="New Project",
            command=lambda: CreatorsSettings.show_new_project_window(ref),
        )
        new_project_button.pack(side='left', pady=5, fill='none', anchor = "n")
        
        # left column project list
        project_list_frame = ttk.Frame(projects_frame)
        project_list_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        project_listbox = tk.Listbox(
            project_list_frame,
            height=10,
            exportselection=False,
        )
        project_listbox.pack(side='left', fill='both', expand=True)
        
        # right column project details
        project_details_frame = ttk.Frame(projects_frame)
        project_details_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        project_details_label = ttk.Label(project_details_frame, text="Project Details")
        project_status_var = tk.StringVar(value="Status")
        project_details_status = ttk.Label(
            project_details_frame,
            textvariable=project_status_var,
        )
        project_details_directory_path = ttk.Label(
            project_details_frame,
            wraplength=280,
            anchor="w",
        )
        project_details_label.pack(pady=5, fill='x')
        project_details_status.pack(pady=5, fill='x')
        project_details_directory_path.pack(pady=5, fill='x')
        project_structure_status_label = ttk.Label(project_details_frame, text="")
        project_structure_status_label.pack(pady=5, fill='x')
        project_structure_button = ttk.Button(
            project_details_frame,
            text="Edit Characters, Scenes, and Shots",
            command=lambda: CreatorsSettings.show_project_structure_editor(ref),
        )
        project_structure_button.pack(pady=5, fill='x')
        project_structure_discard_button = ttk.Button(
            project_details_frame,
            text="Discard Local Draft",
            command=lambda: CreatorsSettings.discard_project_structure_draft(ref),
            state="disabled",
        )
        project_structure_discard_button.pack(pady=5, fill='x')
        
        ref.new_project_button = new_project_button
        ref.project_listbox = project_listbox
        ref.project_details_label = project_details_label
        ref.project_details_status = project_details_status
        ref.project_details_directory_path = project_details_directory_path
        ref.project_status_var = project_status_var
        ref.project_structure_status_label = project_structure_status_label
        ref.project_structure_button = project_structure_button
        ref.project_structure_discard_button = project_structure_discard_button
        project_listbox.bind(
            "<<ListboxSelect>>",
            lambda _event: CreatorsSettings.show_project_details(ref),
        )
        
        
    @staticmethod
    def create_settings_who_frame(ref):
        who_frame = ttk.LabelFrame(ref.settings_tab, text="You must set who you are before proceeding")
        who_frame.pack(fill='x', expand=False, padx=5, pady=5, side='top')
        who_listbox = tk.Listbox(
            who_frame,
            height=10,
            exportselection=False,
        )
        who_listbox.pack(side='left', anchor='w', fill='none', expand=True)
        
        ref.who_listbox = who_listbox
        ref.who_frame = who_frame
        who_listbox.bind(
            "<<ListboxSelect>>",
            lambda _event: CreatorsSettings.select_who(ref),
        )

    @staticmethod
    def select_who(ref):
        selection = ref.who_listbox.curselection()
        if not selection:
            return
        selected_who = ref.who_listbox.get(selection[0])
        try:
            ref.save_selected_who(selected_who)
        except OSError as error:
            messagebox.showerror(
                "Could not save selection",
                f"Your selection could not be saved: {error}",
                parent=ref.settings_window,
            )
            ref.who_listbox.selection_clear(0, tk.END)
            return

        ref.selected_who = selected_who
        ref.who_frame.destroy()
        ref.main_window.deiconify()
        ref.settings_window.withdraw()
        from methods.Helpers import (
            FossaCheckProjectApprovals,
            FossaUpdateMainFileLists,
        )

        FossaUpdateMainFileLists(ref, schedule=False)
        FossaCheckProjectApprovals(ref, schedule=False)

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
        try:
            draft = ref.get_project_structure_draft(project.id)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Could not load project draft",
                str(error),
                parent=ref.settings_window,
            )
            draft = None
        canonical_structure = {
            "scenes": project.scenes,
            "characters": project.characters,
        }
        stale_draft = (
            draft is not None
            and draft.get("base_structure", canonical_structure)
            != canonical_structure
        )
        if project.pending_change is not None:
            requester = project.pending_change.get("requester", "another user")
            status = (
                "Your structure changes are awaiting approval"
                if requester == ref.selected_who
                else f"Structure changes pending approval from {requester}"
            )
            ref.project_structure_status_label.configure(
                text=status
            )
            ref.project_structure_button.configure(state="disabled")
            ref.project_structure_discard_button.configure(state="disabled")
        elif draft is not None and draft.get("state") == "pending":
            ref.project_structure_status_label.configure(
                text="Your structure changes are awaiting approval"
            )
            ref.project_structure_button.configure(state="disabled")
            ref.project_structure_discard_button.configure(state="disabled")
        elif stale_draft:
            ref.project_structure_status_label.configure(
                text="Draft is out of date; discard it before editing"
            )
            ref.project_structure_button.configure(state="disabled")
            ref.project_structure_discard_button.configure(state="normal")
        else:
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
                parent=ref.settings_window,
            )
            return
        ref.project_structure_status_label.configure(text="")
        ref.project_structure_button.configure(state="normal")
        ref.project_structure_discard_button.configure(state="disabled")

    @staticmethod
    def show_project_structure_editor(ref):
        project = getattr(ref, "selected_project", None)
        if project is None:
            return
        if project.pending_change is not None:
            messagebox.showinfo(
                "Approval pending",
                "This project already has a structure change awaiting approval.",
                parent=ref.settings_window,
            )
            return

        try:
            cached_draft = ref.get_project_structure_draft(project.id)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Could not load project draft",
                str(error),
                parent=ref.settings_window,
            )
            return

        canonical_structure = {
            "scenes": deepcopy(project.scenes),
            "characters": list(project.characters),
        }
        if (
            cached_draft is not None
            and cached_draft.get("base_structure", canonical_structure)
            != canonical_structure
        ):
            messagebox.showerror(
                "Draft is out of date",
                "The project changed after this draft was started. Discard the draft and reopen the editor.",
                parent=ref.settings_window,
            )
            return
        draft = {
            "scenes": deepcopy(
                cached_draft.get("scenes", project.scenes)
                if cached_draft is not None
                else project.scenes
            ),
            "characters": list(
                cached_draft.get("characters", project.characters)
                if cached_draft is not None
                else project.characters
            ),
        }
        base_structure = deepcopy(canonical_structure)

        dialog = tk.Toplevel(ref.settings_window)
        dialog.title(f"Project Structure - {project.name}")
        dialog.transient(ref.settings_window)
        dialog.geometry("900x420")
        dialog.minsize(700, 350)
        dialog.grab_set()

        columns = ttk.Frame(dialog)
        columns.pack(fill="both", expand=True, padx=8, pady=8)
        for column in range(3):
            columns.columnconfigure(column, weight=1, uniform="structure")

        character_frame = ttk.LabelFrame(columns, text="Characters")
        scene_frame = ttk.LabelFrame(columns, text="Scenes")
        shot_frame = ttk.LabelFrame(columns, text="Shots")
        character_frame.grid(row=0, column=0, sticky="nsew", padx=4)
        scene_frame.grid(row=0, column=1, sticky="nsew", padx=4)
        shot_frame.grid(row=0, column=2, sticky="nsew", padx=4)

        character_listbox = tk.Listbox(character_frame, exportselection=False)
        scene_listbox = tk.Listbox(scene_frame, exportselection=False)
        shot_listbox = tk.Listbox(shot_frame, exportselection=False)
        for parent, listbox in (
            (character_frame, character_listbox),
            (scene_frame, scene_listbox),
            (shot_frame, shot_listbox),
        ):
            listbox.pack(fill="both", expand=True, padx=5, pady=5)

        def persist_draft(
            updated,
            selected_scene=None,
            selected_shot=None,
            selected_character=None,
        ):
            nonlocal draft
            try:
                ref.save_project_structure_draft(
                    project.id,
                    {
                        "scenes": updated["scenes"],
                        "characters": updated["characters"],
                        "base_structure": base_structure,
                        "state": "draft",
                        "request_id": None,
                    },
                )
            except (OSError, TypeError, ValueError) as error:
                messagebox.showerror(
                    "Could not save project draft",
                    str(error),
                    parent=dialog,
                )
                return False

            draft = updated
            refresh_lists(selected_scene, selected_shot, selected_character)
            ref.project_structure_status_label.configure(
                text="Unsubmitted draft saved locally"
            )
            ref.project_structure_discard_button.configure(state="normal")
            return True

        def selected_value(listbox):
            selection = listbox.curselection()
            return listbox.get(selection[0]) if selection else None

        def refresh_shots(scene_name=None, shot_name=None):
            shot_listbox.delete(0, tk.END)
            scene = next(
                (item for item in draft["scenes"] if item["name"] == scene_name),
                None,
            )
            if scene is None:
                return
            for shot in scene["shots"]:
                shot_listbox.insert(tk.END, shot)
            if shot_name in scene["shots"]:
                index = scene["shots"].index(shot_name)
                shot_listbox.selection_set(index)
                shot_listbox.activate(index)

        def refresh_lists(scene_name=None, shot_name=None, character_name=None):
            scene_listbox.delete(0, tk.END)
            for scene in draft["scenes"]:
                scene_listbox.insert(tk.END, scene["name"])
            if scene_name in [scene["name"] for scene in draft["scenes"]]:
                index = next(
                    index
                    for index, scene in enumerate(draft["scenes"])
                    if scene["name"] == scene_name
                )
                scene_listbox.selection_set(index)
                scene_listbox.activate(index)
                refresh_shots(scene_name, shot_name)
            else:
                refresh_shots()

            character_listbox.delete(0, tk.END)
            for character in draft["characters"]:
                character_listbox.insert(tk.END, character)
            if character_name in draft["characters"]:
                index = draft["characters"].index(character_name)
                character_listbox.selection_set(index)
                character_listbox.activate(index)

        def prompt_name(title, prompt, initial_value=None):
            return simpledialog.askstring(
                title,
                prompt,
                initialvalue=initial_value,
                parent=dialog,
            )

        def validate_unique_name(name, existing, kind):
            name = name.strip()
            if not name:
                messagebox.showerror(
                    f"Invalid {kind}",
                    f"Enter a {kind.lower()} name.",
                    parent=dialog,
                )
                return None
            if name.casefold() in {item.casefold() for item in existing}:
                messagebox.showerror(
                    f"Duplicate {kind}",
                    f"A {kind.lower()} named {name!r} already exists.",
                    parent=dialog,
                )
                return None
            return name

        def add_scene():
            name = prompt_name("Add Scene", "Scene name:")
            if name is None:
                return
            name = validate_unique_name(
                name,
                [scene["name"] for scene in draft["scenes"]],
                "Scene",
            )
            if name is None:
                return
            updated = deepcopy(draft)
            updated["scenes"].append({"name": name, "shots": []})
            persist_draft(updated, name)

        def rename_scene():
            selected = selected_value(scene_listbox)
            if selected is None:
                return
            name = prompt_name("Rename Scene", "Scene name:", selected)
            if name is None:
                return
            name = validate_unique_name(
                name,
                [
                    scene["name"]
                    for scene in draft["scenes"]
                    if scene["name"] != selected
                ],
                "Scene",
            )
            if name is None:
                return
            updated = deepcopy(draft)
            scene = next(
                scene for scene in updated["scenes"] if scene["name"] == selected
            )
            scene["name"] = name
            persist_draft(updated, name, selected_value(shot_listbox))

        def remove_scene():
            selected = selected_value(scene_listbox)
            if selected is None:
                return
            updated = deepcopy(draft)
            updated["scenes"] = [
                scene for scene in updated["scenes"] if scene["name"] != selected
            ]
            persist_draft(updated)

        def add_shot():
            scene_name = selected_value(scene_listbox)
            if scene_name is None:
                messagebox.showinfo(
                    "Select a scene",
                    "Select a scene before adding a shot.",
                    parent=dialog,
                )
                return
            name = prompt_name("Add Shot", "Shot name (XXY):")
            if name is None:
                return
            name = name.strip()
            scene = next(
                scene for scene in draft["scenes"] if scene["name"] == scene_name
            )
            if not CreatorsSettings.is_valid_shot_name(name):
                messagebox.showerror(
                    "Invalid shot",
                    "Shot names must be XXY, where XX is 01-99 and Y is one uppercase letter.",
                    parent=dialog,
                )
                return
            if name in scene["shots"]:
                messagebox.showerror(
                    "Duplicate shot",
                    f"Shot {name!r} already exists in this scene.",
                    parent=dialog,
                )
                return
            updated = deepcopy(draft)
            next_scene = next(
                scene for scene in updated["scenes"] if scene["name"] == scene_name
            )
            next_scene["shots"].append(name)
            persist_draft(updated, scene_name, name)

        def rename_shot():
            scene_name = selected_value(scene_listbox)
            selected = selected_value(shot_listbox)
            if scene_name is None or selected is None:
                return
            name = prompt_name("Rename Shot", "Shot name (XXY):", selected)
            if name is None:
                return
            name = name.strip()
            if not CreatorsSettings.is_valid_shot_name(name):
                messagebox.showerror(
                    "Invalid shot",
                    "Shot names must be XXY, where XX is 01-99 and Y is one uppercase letter.",
                    parent=dialog,
                )
                return
            scene = next(
                scene for scene in draft["scenes"] if scene["name"] == scene_name
            )
            if name in scene["shots"] and name != selected:
                messagebox.showerror(
                    "Duplicate shot",
                    f"Shot {name!r} already exists in this scene.",
                    parent=dialog,
                )
                return
            updated = deepcopy(draft)
            next_scene = next(
                scene for scene in updated["scenes"] if scene["name"] == scene_name
            )
            next_scene["shots"][next_scene["shots"].index(selected)] = name
            persist_draft(updated, scene_name, name)

        def remove_shot():
            scene_name = selected_value(scene_listbox)
            selected = selected_value(shot_listbox)
            if scene_name is None or selected is None:
                return
            updated = deepcopy(draft)
            scene = next(
                scene for scene in updated["scenes"] if scene["name"] == scene_name
            )
            scene["shots"].remove(selected)
            persist_draft(updated, scene_name)

        def add_character():
            name = prompt_name("Add Character", "Character name:")
            if name is None:
                return
            name = validate_unique_name(name, draft["characters"], "Character")
            if name is None:
                return
            updated = deepcopy(draft)
            updated["characters"].append(name)
            persist_draft(updated, selected_character=name)

        def rename_character():
            selected = selected_value(character_listbox)
            if selected is None:
                return
            name = prompt_name("Rename Character", "Character name:", selected)
            if name is None:
                return
            name = validate_unique_name(
                name,
                [character for character in draft["characters"] if character != selected],
                "Character",
            )
            if name is None:
                return
            updated = deepcopy(draft)
            updated["characters"][updated["characters"].index(selected)] = name
            persist_draft(updated, selected_character=name)

        def remove_character():
            selected = selected_value(character_listbox)
            if selected is None:
                return
            updated = deepcopy(draft)
            updated["characters"].remove(selected)
            persist_draft(updated)

        def add_controls(parent, add_command, rename_command, remove_command):
            controls = ttk.Frame(parent)
            controls.pack(fill="x", padx=5, pady=(0, 5))
            ttk.Button(controls, text="Add", command=add_command).pack(
                side="top", fill="x", pady=2
            )
            ttk.Button(controls, text="Rename", command=rename_command).pack(
                side="top", fill="x", pady=2
            )
            ttk.Button(controls, text="Remove", command=remove_command).pack(
                side="top", fill="x", pady=2
            )

        add_controls(
            character_frame, add_character, rename_character, remove_character
        )
        add_controls(scene_frame, add_scene, rename_scene, remove_scene)
        add_controls(shot_frame, add_shot, rename_shot, remove_shot)
        scene_listbox.bind(
            "<<ListboxSelect>>",
            lambda _event: refresh_shots(selected_value(scene_listbox)),
        )
        refresh_lists(
            scene_name=draft["scenes"][0]["name"] if draft["scenes"] else None
        )

        footer = ttk.Frame(dialog)
        footer.pack(fill="x", padx=8, pady=(0, 8))

        def submit_for_approval():
            canonical = {
                "scenes": project.scenes,
                "characters": project.characters,
            }
            if base_structure != canonical:
                messagebox.showerror(
                    "Draft is out of date",
                    "The project changed after this draft was started. Discard the draft and reopen the editor.",
                    parent=dialog,
                )
                return
            if draft == canonical:
                messagebox.showinfo(
                    "No changes",
                    "There are no project structure changes to submit.",
                    parent=dialog,
                )
                return
            if not ref.selected_who or not ref.database_connected or ref.database is None:
                messagebox.showerror(
                    "Database unavailable",
                    "A selected Who Am I and a database connection are required.",
                    parent=dialog,
                )
                return

            request_id = str(uuid.uuid4())
            pending_draft = {
                **deepcopy(draft),
                "base_structure": base_structure,
                "state": "pending",
                "request_id": request_id,
            }
            try:
                ref.save_project_structure_draft(project.id, pending_draft)
                from workers import core

                worker = core.FossaWorker(
                    core.LFRoles.APPROVAL_NEEDED,
                    project.directory_path,
                    ref.selected_who,
                    ref.database,
                )
                try:
                    worker.SubmitProjectStructureChange(
                        project.id,
                        ref.selected_who,
                        request_id,
                        draft,
                        base_structure,
                    )
                finally:
                    worker.Destroy()
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                try:
                    ref.save_project_structure_draft(
                        project.id,
                        {
                            **deepcopy(draft),
                            "base_structure": base_structure,
                            "state": "draft",
                            "request_id": None,
                        },
                    )
                except (OSError, TypeError, ValueError) as cache_error:
                    print(
                        f"Failed to restore local project draft: {cache_error}",
                        file=sys.stderr,
                    )
                messagebox.showerror(
                    "Could not request approval",
                    str(error),
                    parent=dialog,
                )
                return

            ref.project_structure_status_label.configure(
                text="Your structure changes are awaiting approval"
            )
            ref.project_structure_button.configure(state="disabled")
            dialog.destroy()
            from methods.Helpers import FossaUpdateProjects

            FossaUpdateProjects(ref, schedule=False)

        ttk.Button(
            footer,
            text="Request Approval",
            command=submit_for_approval,
        ).pack(side="right")
        ttk.Button(
            footer,
            text="Close",
            command=dialog.destroy,
        ).pack(side="right", padx=(0, 5))

    @staticmethod
    def is_valid_shot_name(name):
        return CreatorsSettings.SHOT_NAME_PATTERN.fullmatch(name) is not None

    @staticmethod
    def show_project_change_approval_dialog(ref, change, on_decision):
        dialog = tk.Toplevel(ref.main_window)
        dialog.title("Project Changes Need Approval")
        dialog.transient(ref.main_window)
        dialog.geometry("600x420")
        dialog.minsize(500, 300)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text=(
                f"{change['requester']} requested changes to "
                f"{change['project_name']}:"
            ),
            wraplength=560,
            justify="left",
        ).pack(fill="x", padx=10, pady=10)

        summary = CreatorsSettings.describe_project_structure_change(change)
        details_frame = ttk.Frame(dialog)
        details_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        details = tk.Text(details_frame, wrap="word", height=14, state="normal")
        details_scrollbar = ttk.Scrollbar(
            details_frame,
            orient=tk.VERTICAL,
            command=details.yview,
        )
        details.configure(yscrollcommand=details_scrollbar.set)
        details.insert("1.0", summary)
        details.configure(state="disabled")
        details.pack(side="left", fill="both", expand=True)
        details_scrollbar.pack(side="right", fill="y")

        def close_without_decision():
            ref._approval_dialog_open = False
            dialog.destroy()

        def decide(approved):
            if on_decision(approved):
                dialog.destroy()

        footer = ttk.Frame(dialog)
        footer.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(
            footer,
            text="Reject",
            command=lambda: decide(False),
        ).pack(side="right", padx=(5, 0))
        ttk.Button(
            footer,
            text="Approve",
            command=lambda: decide(True),
        ).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", close_without_decision)

    @staticmethod
    def describe_project_structure_change(change):
        current = change["current"]
        proposed = change["proposed"]
        lines = []

        current_characters = set(current["characters"])
        proposed_characters = set(proposed["characters"])
        for character in sorted(proposed_characters - current_characters):
            lines.append(f"+ Character: {character}")
        for character in sorted(current_characters - proposed_characters):
            lines.append(f"- Character: {character}")

        current_scenes = {scene["name"]: scene for scene in current["scenes"]}
        proposed_scenes = {scene["name"]: scene for scene in proposed["scenes"]}
        for scene_name in sorted(proposed_scenes.keys() - current_scenes.keys()):
            shots = ", ".join(proposed_scenes[scene_name]["shots"]) or "none"
            lines.append(f"+ Scene: {scene_name} (shots: {shots})")
        for scene_name in sorted(current_scenes.keys() - proposed_scenes.keys()):
            lines.append(f"- Scene: {scene_name}")
        for scene_name in sorted(current_scenes.keys() & proposed_scenes.keys()):
            old_shots = set(current_scenes[scene_name]["shots"])
            new_shots = set(proposed_scenes[scene_name]["shots"])
            for shot in sorted(new_shots - old_shots):
                lines.append(f"+ Shot {shot} in {scene_name}")
            for shot in sorted(old_shots - new_shots):
                lines.append(f"- Shot {shot} in {scene_name}")

        return "\n".join(lines) if lines else "No differences."

    @staticmethod
    def show_new_project_window(ref):
        dialog = tk.Toplevel(ref.settings_window)
        dialog.title("New Project")
        dialog.transient(ref.settings_window)
        dialog.resizable(False, False)
        dialog.grab_set()

        name_var = tk.StringVar()
        status_var = tk.StringVar(value=Status.NOT_STARTED.value)
        directory_var = tk.StringVar()

        ttk.Label(dialog, text="Name").grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 4)
        )
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=10, pady=(10, 4))

        ttk.Label(dialog, text="Status").grid(
            row=1, column=0, sticky="w", padx=10, pady=4
        )
        status_menu = ttk.Combobox(
            dialog,
            textvariable=status_var,
            values=[status.value for status in Status],
            state="readonly",
        )
        status_menu.grid(row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=4)

        ttk.Label(dialog, text="Directory").grid(
            row=2, column=0, sticky="w", padx=10, pady=4
        )
        ttk.Entry(dialog, textvariable=directory_var, width=32).grid(
            row=2, column=1, sticky="ew", padx=(10, 4), pady=4
        )
        ttk.Button(
            dialog,
            text="Browse",
            command=lambda: CreatorsSettings.choose_project_directory(
                dialog, directory_var
            ),
        ).grid(row=2, column=2, padx=(0, 10), pady=4)

        button_row = ttk.Frame(dialog)
        button_row.grid(row=3, column=0, columnspan=3, sticky="e", padx=10, pady=10)
        ttk.Button(
            button_row,
            text="Cancel",
            command=dialog.destroy,
        ).pack(side="right", padx=(5, 0))
        ttk.Button(
            button_row,
            text="Create",
            command=lambda: CreatorsSettings.save_new_project(
                ref,
                dialog,
                name_var.get(),
                status_var.get(),
                directory_var.get(),
            ),
        ).pack(side="right")
        dialog.columnconfigure(1, weight=1)
        name_entry.focus_set()

    @staticmethod
    def choose_project_directory(parent, directory_var):
        directory = filedialog.askdirectory(
            parent=parent,
            title="Select project directory",
            mustexist=True,
        )
        if directory:
            directory_var.set(directory)

    @staticmethod
    def save_new_project(ref, dialog, name, status, directory_path):
        name = name.strip()
        directory_path = directory_path.strip()
        if not name or not directory_path:
            messagebox.showerror(
                "Invalid project",
                "Enter a project name and choose a directory.",
                parent=dialog,
            )
            return
        try:
            project_status = Status(status)
            directory_path = str(Path(directory_path).expanduser().resolve())
            project = Project(name, project_status, directory_path)
            if not Path(directory_path).is_dir():
                raise ValueError("Choose an existing project directory.")
            if not ref.selected_who:
                raise ValueError("Select Who Am I before creating a project.")
            if not ref.database_connected or ref.database is None:
                raise ConnectionError("The database is not connected.")

            from workers import core

            worker = core.FossaWorker(
                core.LFRoles.DB_ACCESS,
                ref.get_worker_network_base_path(),
                ref.selected_who,
                ref.database,
            )
            try:
                worker.SyncProject(project)
            finally:
                worker.Destroy()
        except (OSError, ValueError, RuntimeError, ConnectionError) as error:
            messagebox.showerror(
                "Could not create project",
                str(error),
                parent=dialog,
            )
            return

        dialog.destroy()
        from methods.Helpers import FossaUpdateProjects

        FossaUpdateProjects(ref, schedule=False)

    @staticmethod
    def create_settings_other_frame(ref):
        other_frame = ttk.LabelFrame(ref.settings_tab, text="Other Settings")
        other_frame.pack(fill='x', expand=False, padx=10, pady=10, side='top')
        
        other_row = ttk.Frame(other_frame)
        other_row.pack(fill='x', expand=False, padx=5, pady=5)

        blender_file_path_entry = ttk.Entry(other_row, textvariable=ref.blender_file_path_variable)
        blender_file_path_entry.pack(side='left', fill='x', expand=True)
        blender_file_path_entry.bind(
            "<Return>",
            lambda _event: CreatorsSettings.save_blender_file_path(ref),
        )
        blender_file_path_entry.bind(
            "<FocusOut>",
            lambda _event: CreatorsSettings.save_blender_file_path(ref),
        )
        choose_blender_file_path_button = ttk.Button(
            other_row,
            text="Blender Executable",
            command=lambda: CreatorsSettings.choose_blender_file_path(ref),
        )
        choose_blender_file_path_button.pack(side='right', padx=5)

        ref.blender_file_path_entry = blender_file_path_entry

        network_row = ttk.Frame(other_frame)
        network_row.pack(fill='x', expand=False, padx=5, pady=5)

        network_base_path_entry = ttk.Entry(
            network_row,
            textvariable=ref.network_base_path_variable,
        )
        network_base_path_entry.pack(side='left', fill='x', expand=True)
        network_base_path_entry.bind(
            "<Return>",
            lambda _event: CreatorsSettings.save_network_base_path(ref),
        )
        network_base_path_entry.bind(
            "<FocusOut>",
            lambda _event: CreatorsSettings.save_network_base_path(ref),
        )
        choose_network_base_path_button = ttk.Button(
            network_row,
            text="Network Folder",
            command=lambda: CreatorsSettings.choose_network_base_path(ref),
        )
        choose_network_base_path_button.pack(side='right', padx=5)
        ref.network_base_path_entry = network_base_path_entry
        
        increase_button = tk.Button(ref.settings_tab, text="Increase Font Size", command=ref.increase_font_size)
        increase_button.pack()

        decrease_button = tk.Button(ref.settings_tab, text="Decrease Font Size", command=ref.decrease_font_size)
        decrease_button.pack()

    @staticmethod
    def choose_blender_file_path(ref):
        blender_file_path = filedialog.askopenfilename(
            parent=ref.settings_window,
            title="Select Blender executable",
            filetypes=(("Blender executable", "*"), ("All files", "*")),
        )
        if blender_file_path:
            ref.blender_file_path_variable.set(blender_file_path)
            CreatorsSettings.save_blender_file_path(ref)

    @staticmethod
    def save_blender_file_path(ref):
        ref.save_blender_file_path(ref.blender_file_path_variable.get())
        ref.update_status_bar()

    @staticmethod
    def choose_network_base_path(ref):
        network_base_path = filedialog.askdirectory(
            parent=ref.settings_window,
            title="Select network folder",
            mustexist=True,
        )
        if network_base_path:
            ref.network_base_path_variable.set(network_base_path)
            CreatorsSettings.save_network_base_path(ref)

    @staticmethod
    def save_network_base_path(ref):
        ref.save_network_base_path(ref.network_base_path_variable.get())
        ref.update_status_bar()