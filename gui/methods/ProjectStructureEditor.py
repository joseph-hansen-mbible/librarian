from copy import deepcopy
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import uuid

from db.fossadb import FossaDB
from methods.ProjectStructureActions import ProjectStructureActions
from methods.ProjectStructureDialogs import ProjectStructureDialogs
from objects.Project import Status


class ProjectStructureEditor:
    def __init__(self, ref, project):
        self.ref = ref
        self.project = project
        self.dialog = None
        self.base_structure = None
        self.draft = None
        self.actions = ProjectStructureActions(self)

    def show(self):
        try:
            if not self._load_draft():
                return
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Could not load project draft",
                str(error),
                parent=self.ref.projects_tab,
            )
            return
        self._build_dialog()

    def _canonical_structure(self):
        return {
            "scenes": deepcopy(self.project.scenes),
            "characters": list(self.project.characters),
            "props": list(self.project.props),
            "status": self.project.status.value,
        }

    def _load_draft(self):
        canonical = self._canonical_structure()
        cached = self.ref.get_project_structure_draft(self.project.id)
        if cached is not None:
            cached.update(
                FossaDB.NormalizeProjectStructure(
                    cached,
                    default_status=self.project.status.value,
                )
            )
            cached["base_structure"] = FossaDB.NormalizeProjectStructure(
                cached.get("base_structure", canonical),
                default_status=self.project.status.value,
            )
        if (
            cached is not None
            and cached.get("base_structure", canonical) != canonical
        ):
            messagebox.showerror(
                "Draft is out of date",
                "The project changed after this draft was started. Discard the draft and reopen the editor.",
                parent=self.ref.projects_tab,
            )
            return False
        self.base_structure = deepcopy(canonical)
        self.draft = {
            "scenes": deepcopy(
                cached.get("scenes", self.project.scenes)
                if cached is not None
                else self.project.scenes
            ),
            "characters": list(
                cached.get("characters", self.project.characters)
                if cached is not None
                else self.project.characters
            ),
            "props": list(
                cached.get("props", self.project.props)
                if cached is not None
                else self.project.props
            ),
            "status": (
                cached.get("status", self.project.status.value)
                if cached is not None
                else self.project.status.value
            ),
        }
        return True

    def _build_dialog(self):
        ref = self.ref
        self.dialog = tk.Toplevel(ref.projects_tab)
        self.dialog.title(f"Project Structure - {self.project.name}")
        self.dialog.transient(ref.projects_tab)
        self.dialog.geometry("1100x560")
        self.dialog.minsize(850, 420)
        self.dialog.grab_set()

        status_frame = ttk.Frame(self.dialog)
        status_frame.pack(fill="x", padx=12, pady=(10, 0))
        ttk.Label(status_frame, text="Project Status").pack(
            side="left",
            padx=(0, 8),
        )
        self.status_var = tk.StringVar(value=self.draft["status"])
        self.status_menu = ttk.Combobox(
            status_frame,
            textvariable=self.status_var,
            values=[status.value for status in Status],
            state="readonly",
            width=18,
        )
        self.status_menu.pack(side="left")
        self.status_menu.bind(
            "<<ComboboxSelected>>",
            self._update_status_draft,
        )

        columns = ttk.Frame(self.dialog)
        columns.pack(fill="both", expand=True, padx=8, pady=8)
        for column in range(4):
            columns.columnconfigure(column, weight=1, uniform="structure")
        columns.rowconfigure(0, weight=1)

        frames = {
            "characters": ttk.LabelFrame(columns, text="Characters"),
            "props": ttk.LabelFrame(columns, text="Props"),
            "scenes": ttk.LabelFrame(columns, text="Scenes"),
            "shots": ttk.LabelFrame(columns, text="Shots"),
        }
        for column, key in enumerate(("characters", "props", "scenes", "shots")):
            frames[key].grid(row=0, column=column, sticky="nsew", padx=4)
        self.character_listbox = tk.Listbox(
            frames["characters"],
            exportselection=False,
        )
        self.prop_listbox = tk.Listbox(frames["props"], exportselection=False)
        self.scene_listbox = tk.Listbox(frames["scenes"], exportselection=False)
        self.shot_listbox = tk.Listbox(frames["shots"], exportselection=False)
        for listbox in (
            self.character_listbox,
            self.prop_listbox,
            self.scene_listbox,
            self.shot_listbox,
        ):
            listbox.pack(fill="both", expand=True, padx=5, pady=5)

        self._add_controls(
            frames["characters"],
            self.actions.add_character,
            lambda: self.actions.add_bulk_names("Characters", "characters"),
            self.actions.rename_character,
            self.actions.remove_character,
        )
        self._add_controls(
            frames["props"],
            self.actions.add_prop,
            lambda: self.actions.add_bulk_names("Props", "props"),
            self.actions.rename_prop,
            self.actions.remove_prop,
        )
        self._add_controls(
            frames["scenes"],
            self.actions.add_scene,
            self.actions.add_bulk_scenes,
            self.actions.rename_scene,
            self.actions.remove_scene,
        )
        self._add_controls(
            frames["shots"],
            self.actions.add_shot,
            self.actions.add_bulk_shots,
            self.actions.rename_shot,
            self.actions.remove_shot,
        )
        self.scene_listbox.bind(
            "<<ListboxSelect>>",
            lambda _event: self._refresh_shots(
                self.selected_scene()["name"]
                if self.selected_scene() is not None
                else None
            ),
        )
        self._refresh_lists(
            scene_name=self.draft["scenes"][0]["name"]
            if self.draft["scenes"]
            else None
        )

        footer = ttk.Frame(self.dialog)
        footer.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(
            footer,
            text="Request Approval",
            command=self._submit_for_approval,
        ).pack(side="right")
        ttk.Button(
            footer,
            text="Close",
            command=self.dialog.destroy,
        ).pack(side="right", padx=(0, 5))

    @staticmethod
    def _add_controls(parent, add_command, bulk_command, rename_command, remove_command):
        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=5, pady=(0, 5))
        for label, command in (
            ("Add", add_command),
            ("Bulk Add", bulk_command),
            ("Rename", rename_command),
            ("Remove", remove_command),
        ):
            ttk.Button(
                controls,
                text=label,
                command=command,
            ).pack(side="top", fill="x", pady=2)

    def persist_draft(
        self,
        updated,
        selected_scene=None,
        selected_shot=None,
        selected_character=None,
        selected_prop=None,
    ):
        try:
            self.ref.save_project_structure_draft(
                self.project.id,
                {
                    "scenes": updated["scenes"],
                    "characters": updated["characters"],
                    "props": updated["props"],
                    "status": updated["status"],
                    "base_structure": self.base_structure,
                    "state": "draft",
                    "request_id": None,
                },
            )
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror(
                "Could not save project draft",
                str(error),
                parent=self.dialog,
            )
            return False

        self.draft = updated
        self._refresh_lists(
            selected_scene,
            selected_shot,
            selected_character,
            selected_prop,
        )
        self.ref.project_structure_status_label.configure(
            text="Unsubmitted draft saved locally"
        )
        self.ref.project_structure_discard_button.configure(state="normal")
        return True

    def selected_value(self, listbox):
        selection = listbox.curselection()
        return listbox.get(selection[0]) if selection else None

    @staticmethod
    def display_scene(scene):
        return (
            f'{scene["name"]} - {scene["subtitle"]}'
            if scene.get("subtitle")
            else scene["name"]
        )

    def selected_scene(self):
        selected = self.selected_value(self.scene_listbox)
        return next(
            (
                scene
                for scene in self.draft["scenes"]
                if self.display_scene(scene) == selected
            ),
            None,
        )

    def _refresh_shots(self, scene_name=None, shot_name=None):
        self.shot_listbox.delete(0, tk.END)
        scene = next(
            (item for item in self.draft["scenes"] if item["name"] == scene_name),
            None,
        )
        if scene is None:
            return
        for shot in scene["shots"]:
            self.shot_listbox.insert(tk.END, shot)
        if shot_name in scene["shots"]:
            index = scene["shots"].index(shot_name)
            self.shot_listbox.selection_set(index)
            self.shot_listbox.activate(index)

    def _refresh_lists(
        self,
        scene_name=None,
        shot_name=None,
        character_name=None,
        prop_name=None,
    ):
        self.scene_listbox.delete(0, tk.END)
        for scene in self.draft["scenes"]:
            self.scene_listbox.insert(tk.END, self.display_scene(scene))
        if scene_name in [scene["name"] for scene in self.draft["scenes"]]:
            index = next(
                index
                for index, scene in enumerate(self.draft["scenes"])
                if scene["name"] == scene_name
            )
            self.scene_listbox.selection_set(index)
            self.scene_listbox.activate(index)
            self._refresh_shots(scene_name, shot_name)
        else:
            self._refresh_shots()

        self.character_listbox.delete(0, tk.END)
        for character in self.draft["characters"]:
            self.character_listbox.insert(tk.END, character)
        if character_name in self.draft["characters"]:
            index = self.draft["characters"].index(character_name)
            self.character_listbox.selection_set(index)
            self.character_listbox.activate(index)

        self.prop_listbox.delete(0, tk.END)
        for prop in self.draft["props"]:
            self.prop_listbox.insert(tk.END, prop)
        if prop_name in self.draft["props"]:
            index = self.draft["props"].index(prop_name)
            self.prop_listbox.selection_set(index)
            self.prop_listbox.activate(index)

    def prompt_name(self, title, prompt, initial_value=""):
        return ProjectStructureDialogs.prompt_text(
            self.dialog,
            self.ref,
            title,
            prompt,
            initial_value,
        )

    def prompt_scene(self, title, scene=None):
        return ProjectStructureDialogs.prompt_scene(
            self.dialog,
            self.ref,
            title,
            scene,
        )

    def prompt_bulk(self, title, prompt):
        return ProjectStructureDialogs.prompt_bulk(
            self.dialog,
            self.ref,
            title,
            prompt,
        )

    def _update_status_draft(self, _event):
        new_status = self.status_var.get()
        if new_status == self.draft["status"]:
            return
        updated = deepcopy(self.draft)
        updated["status"] = new_status
        scene = self.selected_scene()
        self.persist_draft(
            updated,
            scene["name"] if scene is not None else None,
            self.selected_value(self.shot_listbox),
            self.selected_value(self.character_listbox),
            self.selected_value(self.prop_listbox),
        )

    @staticmethod
    def request_approval(ref, project, proposed, base_structure, parent):
        if not ref.selected_who or not ref.database_connected or ref.database is None:
            messagebox.showerror(
                "Database unavailable",
                "A selected Who Am I and a database connection are required.",
                parent=parent,
            )
            return False

        request_id = str(uuid.uuid4())
        pending_draft = {
            **deepcopy(proposed),
            "base_structure": deepcopy(base_structure),
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
                    proposed,
                    base_structure,
                )
            finally:
                worker.Destroy()
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            try:
                ref.save_project_structure_draft(
                    project.id,
                    {
                        **deepcopy(proposed),
                        "base_structure": deepcopy(base_structure),
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
                parent=parent,
            )
            return False

        ref.project_structure_status_label.configure(
            text="Your project changes are awaiting approval (0/2 approvals)"
        )
        ref.project_structure_button.configure(state="disabled")
        from methods.Helpers import FossaUpdateProjects

        FossaUpdateProjects(ref, schedule=False)
        return True

    def _submit_for_approval(self):
        canonical = self._canonical_structure()
        if self.base_structure != canonical:
            messagebox.showerror(
                "Draft is out of date",
                "The project changed after this draft was started. Discard the draft and reopen the editor.",
                parent=self.dialog,
            )
            return
        if self.draft == canonical:
            messagebox.showinfo(
                "No changes",
                "There are no project structure changes to submit.",
                parent=self.dialog,
            )
            return
        if self.request_approval(
            self.ref,
            self.project,
            self.draft,
            self.base_structure,
            self.dialog,
        ):
            self.dialog.destroy()
