import tkinter as tk
from tkinter import ttk

from methods.Populators import Populators


class CreatorsProjectApprovals:
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

        approvals = change.get("approvals", [])
        required_approvals = change.get("required_approvals", 2)
        approval_names = ", ".join(approvals) if approvals else "none yet"
        ttk.Label(
            dialog,
            text=f"Approvals: {len(approvals)}/{required_approvals} ({approval_names})",
        ).pack(fill="x", padx=10, pady=(0, 8))

        summary = CreatorsProjectApprovals.describe_project_structure_change(change)
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
        tk.Button(
            footer,
            text="Reject",
            command=lambda: decide(False),
            bg=Populators.REJECT_BACKGROUND,
            fg="#ffffff",
            activebackground="#853636",
            activeforeground="#ffffff",
            font=ref.scaled_system_fonts[0],
            relief="flat",
            padx=14,
            pady=6,
        ).pack(side="right", padx=(5, 0))
        tk.Button(
            footer,
            text="Approve",
            command=lambda: decide(True),
            bg=Populators.APPROVE_BACKGROUND,
            fg="#ffffff",
            activebackground="#315f38",
            activeforeground="#ffffff",
            font=ref.scaled_system_fonts[0],
            relief="flat",
            padx=14,
            pady=6,
        ).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", close_without_decision)

    @staticmethod
    def describe_project_structure_change(change):
        current = change["current"]
        proposed = change["proposed"]
        lines = []

        if current.get("status") != proposed.get("status"):
            lines.append(
                f"~ Project status: {current.get('status', 'Not Started')} -> "
                f"{proposed.get('status', 'Not Started')}"
            )

        current_characters = set(current["characters"])
        proposed_characters = set(proposed["characters"])
        for character in sorted(proposed_characters - current_characters):
            lines.append(f"+ Character: {character}")
        for character in sorted(current_characters - proposed_characters):
            lines.append(f"- Character: {character}")

        current_props = set(current.get("props", []))
        proposed_props = set(proposed.get("props", []))
        for prop in sorted(proposed_props - current_props):
            lines.append(f"+ Prop: {prop}")
        for prop in sorted(current_props - proposed_props):
            lines.append(f"- Prop: {prop}")

        current_scenes = {scene["name"]: scene for scene in current["scenes"]}
        proposed_scenes = {scene["name"]: scene for scene in proposed["scenes"]}

        def display_scene(scene):
            return (
                f'{scene["name"]} - {scene["subtitle"]}'
                if scene.get("subtitle")
                else scene["name"]
            )

        for scene_name in sorted(proposed_scenes.keys() - current_scenes.keys()):
            shots = ", ".join(proposed_scenes[scene_name]["shots"]) or "none"
            lines.append(
                f"+ Scene: {display_scene(proposed_scenes[scene_name])} "
                f"(shots: {shots})"
            )
        for scene_name in sorted(current_scenes.keys() - proposed_scenes.keys()):
            lines.append(f"- Scene: {display_scene(current_scenes[scene_name])}")
        for scene_name in sorted(current_scenes.keys() & proposed_scenes.keys()):
            old_scene = current_scenes[scene_name]
            new_scene = proposed_scenes[scene_name]
            if old_scene.get("subtitle", "") != new_scene.get("subtitle", ""):
                lines.append(
                    f"~ Scene {scene_name} subtitle: "
                    f"{old_scene.get('subtitle', '')!r} -> "
                    f"{new_scene.get('subtitle', '')!r}"
                )
            old_shots = set(old_scene["shots"])
            new_shots = set(new_scene["shots"])
            for shot in sorted(new_shots - old_shots):
                lines.append(f"+ Shot {shot} in Scene {scene_name}")
            for shot in sorted(old_shots - new_shots):
                lines.append(f"- Shot {shot} in Scene {scene_name}")

        return "\n".join(lines) if lines else "No differences."
