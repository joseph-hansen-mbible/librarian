from copy import deepcopy
from tkinter import messagebox

from db.project_structure import ProjectStructure
from methods.ProjectStructureDialogs import ProjectStructureDialogs


class ProjectStructureActions:
    def __init__(self, editor):
        self.editor = editor

    def add_scene(self):
        e = self.editor
        values = e.prompt_scene("Add Scene")
        if values is None:
            return
        name, subtitle = values
        name = name.strip()
        if ProjectStructure.SCENE_NUMBER_PATTERN.fullmatch(name) is None:
            messagebox.showerror(
                "Invalid scene number",
                "Scene numbers must be from 01 to 99.",
                parent=e.dialog,
            )
            return
        if any(scene["name"] == name for scene in e.draft["scenes"]):
            messagebox.showerror(
                "Duplicate scene",
                f"Scene {name} already exists.",
                parent=e.dialog,
            )
            return
        updated = deepcopy(e.draft)
        updated["scenes"].append(
            {
                "name": name,
                "subtitle": subtitle.strip(),
                "shots": [],
            }
        )
        e.persist_draft(updated, name)

    def rename_scene(self):
        e = self.editor
        current = e.selected_scene()
        if current is None:
            return
        values = e.prompt_scene("Rename Scene", current)
        if values is None:
            return
        name, subtitle = values
        name = name.strip()
        if ProjectStructure.SCENE_NUMBER_PATTERN.fullmatch(name) is None:
            messagebox.showerror(
                "Invalid scene number",
                "Scene numbers must be from 01 to 99.",
                parent=e.dialog,
            )
            return
        if any(
            scene["name"] == name and scene["name"] != current["name"]
            for scene in e.draft["scenes"]
        ):
            messagebox.showerror(
                "Duplicate scene",
                f"Scene {name} already exists.",
                parent=e.dialog,
            )
            return
        updated = deepcopy(e.draft)
        scene = next(
            scene for scene in updated["scenes"]
            if scene["name"] == current["name"]
        )
        scene["name"] = name
        scene["subtitle"] = subtitle.strip()
        e.persist_draft(updated, name, e.selected_value(e.shot_listbox))

    def remove_scene(self):
        e = self.editor
        selected = e.selected_scene()
        if selected is None:
            return
        updated = deepcopy(e.draft)
        updated["scenes"] = [
            scene for scene in updated["scenes"]
            if scene["name"] != selected["name"]
        ]
        e.persist_draft(updated)

    def add_shot(self):
        e = self.editor
        scene = e.selected_scene()
        if scene is None:
            messagebox.showinfo(
                "Select a scene",
                "Select a scene before adding a shot.",
                parent=e.dialog,
            )
            return
        name = e.prompt_name("Add Shot", "Shot name (XX or XXY):")
        if name is None:
            return
        name = name.strip()
        if ProjectStructure.SHOT_NAME_PATTERN.fullmatch(name) is None:
            messagebox.showerror(
                "Invalid shot",
                "Shot names must be XX or XXY, with XX from 01 to 99 and Y uppercase.",
                parent=e.dialog,
            )
            return
        if name in scene["shots"]:
            messagebox.showerror(
                "Duplicate shot",
                f"Shot {name!r} already exists in this scene.",
                parent=e.dialog,
            )
            return
        updated = deepcopy(e.draft)
        next_scene = next(
            item for item in updated["scenes"]
            if item["name"] == scene["name"]
        )
        next_scene["shots"].append(name)
        e.persist_draft(updated, scene["name"], name)

    def rename_shot(self):
        e = self.editor
        scene = e.selected_scene()
        selected = e.selected_value(e.shot_listbox)
        if scene is None or selected is None:
            return
        name = e.prompt_name("Rename Shot", "Shot name (XX or XXY):", selected)
        if name is None:
            return
        name = name.strip()
        if ProjectStructure.SHOT_NAME_PATTERN.fullmatch(name) is None:
            messagebox.showerror(
                "Invalid shot",
                "Shot names must be XX or XXY, with XX from 01 to 99 and Y uppercase.",
                parent=e.dialog,
            )
            return
        if name in scene["shots"] and name != selected:
            messagebox.showerror(
                "Duplicate shot",
                f"Shot {name!r} already exists in this scene.",
                parent=e.dialog,
            )
            return
        updated = deepcopy(e.draft)
        next_scene = next(
            item for item in updated["scenes"]
            if item["name"] == scene["name"]
        )
        next_scene["shots"][next_scene["shots"].index(selected)] = name
        e.persist_draft(updated, scene["name"], name)

    def remove_shot(self):
        e = self.editor
        scene = e.selected_scene()
        selected = e.selected_value(e.shot_listbox)
        if scene is None or selected is None:
            return
        updated = deepcopy(e.draft)
        next_scene = next(
            item for item in updated["scenes"]
            if item["name"] == scene["name"]
        )
        next_scene["shots"].remove(selected)
        e.persist_draft(updated, scene["name"])

    def add_character(self):
        e = self.editor
        name = e.prompt_name("Add Character", "Character name:")
        if name is None:
            return
        name = ProjectStructureDialogs.validate_unique_name(
            e.dialog,
            name,
            e.draft["characters"],
            "Character",
        )
        if name is None:
            return
        updated = deepcopy(e.draft)
        updated["characters"].append(name)
        e.persist_draft(updated, selected_character=name)

    def rename_character(self):
        e = self.editor
        selected = e.selected_value(e.character_listbox)
        if selected is None:
            return
        name = e.prompt_name("Rename Character", "Character name:", selected)
        if name is None:
            return
        name = ProjectStructureDialogs.validate_unique_name(
            e.dialog,
            name,
            [
                character for character in e.draft["characters"]
                if character != selected
            ],
            "Character",
        )
        if name is None:
            return
        updated = deepcopy(e.draft)
        updated["characters"][updated["characters"].index(selected)] = name
        e.persist_draft(updated, selected_character=name)

    def remove_character(self):
        e = self.editor
        selected = e.selected_value(e.character_listbox)
        if selected is None:
            return
        updated = deepcopy(e.draft)
        updated["characters"].remove(selected)
        e.persist_draft(updated)

    def add_prop(self):
        e = self.editor
        name = e.prompt_name("Add Prop", "Prop name:")
        if name is None:
            return
        name = ProjectStructureDialogs.validate_unique_name(
            e.dialog,
            name,
            e.draft["props"],
            "Prop",
        )
        if name is None:
            return
        updated = deepcopy(e.draft)
        updated["props"].append(name)
        e.persist_draft(updated, selected_prop=name)

    def rename_prop(self):
        e = self.editor
        selected = e.selected_value(e.prop_listbox)
        if selected is None:
            return
        name = e.prompt_name("Rename Prop", "Prop name:", selected)
        if name is None:
            return
        name = ProjectStructureDialogs.validate_unique_name(
            e.dialog,
            name,
            [prop for prop in e.draft["props"] if prop != selected],
            "Prop",
        )
        if name is None:
            return
        updated = deepcopy(e.draft)
        updated["props"][updated["props"].index(selected)] = name
        e.persist_draft(updated, selected_prop=name)

    def remove_prop(self):
        e = self.editor
        selected = e.selected_value(e.prop_listbox)
        if selected is None:
            return
        updated = deepcopy(e.draft)
        updated["props"].remove(selected)
        e.persist_draft(updated)

    def add_bulk_names(self, kind, key):
        e = self.editor
        raw = e.prompt_bulk(
            f"Bulk Add {kind}",
            f"Enter one {kind.lower()} per line:",
        )
        if raw is None:
            return
        values, errors = ProjectStructureDialogs.validate_bulk_names(
            ProjectStructureDialogs.bulk_lines(raw),
            e.draft[key],
            kind,
        )
        if errors:
            self._show_bulk_errors(kind, errors)
            return
        if not values:
            messagebox.showinfo(
                "Nothing to add",
                f"Enter at least one {kind.lower()}.",
                parent=e.dialog,
            )
            return
        updated = deepcopy(e.draft)
        updated[key].extend(values)
        e.persist_draft(
            updated,
            selected_character=values[0] if key == "characters" else None,
            selected_prop=values[0] if key == "props" else None,
        )

    def add_bulk_scenes(self):
        e = self.editor
        raw = e.prompt_bulk(
            "Bulk Add Scenes",
            "Enter one scene per line: XX or XX: subtitle.",
        )
        if raw is None:
            return
        lines = ProjectStructureDialogs.bulk_lines(raw)
        known = {scene["name"] for scene in e.draft["scenes"]}
        additions = []
        errors = []
        for line_number, value in lines:
            number, separator, subtitle = value.partition(":")
            number = number.strip()
            if ProjectStructure.SCENE_NUMBER_PATTERN.fullmatch(number) is None:
                errors.append(
                    f"Line {line_number}: scene number must be from 01 to 99."
                )
            elif number in known:
                errors.append(
                    f"Line {line_number}: scene {number} already exists."
                )
            else:
                known.add(number)
                additions.append(
                    {
                        "name": number,
                        "subtitle": subtitle.strip() if separator else "",
                        "shots": [],
                    }
                )
        if errors:
            self._show_bulk_errors("scenes", errors)
            return
        if not additions:
            messagebox.showinfo(
                "Nothing to add",
                "Enter at least one scene.",
                parent=e.dialog,
            )
            return
        updated = deepcopy(e.draft)
        updated["scenes"].extend(additions)
        e.persist_draft(updated, additions[0]["name"])

    def add_bulk_shots(self):
        e = self.editor
        scene = e.selected_scene()
        if scene is None:
            messagebox.showinfo(
                "Select a scene",
                "Select a scene before bulk adding shots.",
                parent=e.dialog,
            )
            return
        raw = e.prompt_bulk(
            "Bulk Add Shots",
            "Enter one shot per line (XX or XXY):",
        )
        if raw is None:
            return
        known = set(scene["shots"])
        additions = []
        errors = []
        for line_number, name in ProjectStructureDialogs.bulk_lines(raw):
            if ProjectStructure.SHOT_NAME_PATTERN.fullmatch(name) is None:
                errors.append(
                    f"Line {line_number}: {name!r} is not XX or XXY (01-99)."
                )
            elif name in known:
                errors.append(
                    f"Line {line_number}: shot {name!r} already exists."
                )
            else:
                known.add(name)
                additions.append(name)
        if errors:
            self._show_bulk_errors("shots", errors)
            return
        if not additions:
            messagebox.showinfo(
                "Nothing to add",
                "Enter at least one shot.",
                parent=e.dialog,
            )
            return
        updated = deepcopy(e.draft)
        next_scene = next(
            item for item in updated["scenes"]
            if item["name"] == scene["name"]
        )
        next_scene["shots"].extend(additions)
        e.persist_draft(updated, scene["name"], additions[0])

    def _show_bulk_errors(self, kind, errors):
        messagebox.showerror(
            f"Could not add {kind}",
            "No items were added:\n" + "\n".join(errors),
            parent=self.editor.dialog,
        )
