import tkinter as tk
from tkinter import messagebox, ttk


class ProjectStructureDialogs:
    @staticmethod
    def prompt_text(parent, ref, title, prompt, initial_value=""):
        result = {"value": None}
        popup = tk.Toplevel(parent)
        popup.title(title)
        popup.transient(parent)
        popup.resizable(False, False)
        ttk.Label(popup, text=prompt).pack(
            fill="x",
            padx=10,
            pady=(10, 4),
        )
        value = tk.StringVar(value=initial_value)
        entry = ttk.Entry(popup, textvariable=value, width=48)
        entry.pack(fill="x", padx=10, pady=4)
        buttons = ttk.Frame(popup)
        buttons.pack(fill="x", padx=10, pady=10)

        def finish(accepted):
            if accepted:
                result["value"] = value.get()
            popup.destroy()

        ProjectStructureDialogs._add_cancel_button(
            buttons,
            ref,
            lambda: finish(False),
        ).pack(side="right", padx=(5, 0))
        ttk.Button(
            buttons,
            text="OK",
            command=lambda: finish(True),
        ).pack(side="right")
        popup.protocol("WM_DELETE_WINDOW", lambda: finish(False))
        popup.grab_set()
        entry.focus_set()
        popup.wait_window()
        return result["value"]

    @staticmethod
    def prompt_scene(parent, ref, title, scene=None):
        result = {"value": None}
        popup = tk.Toplevel(parent)
        popup.title(title)
        popup.transient(parent)
        popup.resizable(False, False)
        number_var = tk.StringVar(
            value=scene["name"] if scene is not None else ""
        )
        subtitle_var = tk.StringVar(
            value=scene.get("subtitle", "") if scene is not None else ""
        )
        ttk.Label(popup, text="Scene number (01-99)").grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 4)
        )
        number_entry = ttk.Entry(popup, textvariable=number_var, width=12)
        number_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 4))
        ttk.Label(popup, text="Subtitle (optional)").grid(
            row=1, column=0, sticky="w", padx=10, pady=4
        )
        ttk.Entry(popup, textvariable=subtitle_var, width=42).grid(
            row=1, column=1, sticky="ew", padx=10, pady=4
        )
        buttons = ttk.Frame(popup)
        buttons.grid(row=2, column=0, columnspan=2, sticky="e", padx=10, pady=10)

        def finish(accepted):
            if accepted:
                result["value"] = (number_var.get(), subtitle_var.get())
            popup.destroy()

        ProjectStructureDialogs._add_cancel_button(
            buttons,
            ref,
            lambda: finish(False),
        ).pack(side="right", padx=(5, 0))
        ttk.Button(
            buttons,
            text="OK",
            command=lambda: finish(True),
        ).pack(side="right")
        popup.columnconfigure(1, weight=1)
        popup.protocol("WM_DELETE_WINDOW", lambda: finish(False))
        popup.grab_set()
        number_entry.focus_set()
        popup.wait_window()
        return result["value"]

    @staticmethod
    def prompt_bulk(parent, ref, title, prompt):
        result = {"value": None}
        popup = tk.Toplevel(parent)
        popup.title(title)
        popup.transient(parent)
        popup.geometry("420x300")
        ttk.Label(popup, text=prompt).pack(
            fill="x",
            padx=10,
            pady=(10, 4),
        )
        value = tk.Text(popup, height=10, wrap="none")
        value.pack(fill="both", expand=True, padx=10, pady=4)
        buttons = ttk.Frame(popup)
        buttons.pack(fill="x", padx=10, pady=10)

        def finish(accepted):
            if accepted:
                result["value"] = value.get("1.0", "end-1c")
            popup.destroy()

        ProjectStructureDialogs._add_cancel_button(
            buttons,
            ref,
            lambda: finish(False),
        ).pack(side="right", padx=(5, 0))
        ttk.Button(
            buttons,
            text="Add",
            command=lambda: finish(True),
        ).pack(side="right")
        popup.protocol("WM_DELETE_WINDOW", lambda: finish(False))
        popup.grab_set()
        value.focus_set()
        popup.wait_window()
        return result["value"]

    @staticmethod
    def _add_cancel_button(parent, ref, command):
        return tk.Button(
            parent,
            text="Cancel",
            command=command,
            bg="#35373c",
            fg="#ffffff",
            activebackground="#45484f",
            activeforeground="#ffffff",
            font=ref.scaled_system_fonts[0],
            relief="flat",
            padx=10,
        )

    @staticmethod
    def bulk_lines(text):
        return [
            (line_number, line.strip())
            for line_number, line in enumerate(text.splitlines(), start=1)
            if line.strip()
        ]

    @staticmethod
    def validate_bulk_names(lines, existing, kind):
        known = {value.casefold() for value in existing}
        values = []
        errors = []
        for line_number, value in lines:
            folded = value.casefold()
            if not value:
                errors.append(f"Line {line_number}: name cannot be empty.")
            elif folded in known:
                errors.append(
                    f"Line {line_number}: duplicate {kind.lower()} {value!r}."
                )
            else:
                known.add(folded)
                values.append(value)
        return values, errors

    @staticmethod
    def validate_unique_name(parent, name, existing, kind):
        name = name.strip()
        if not name:
            messagebox.showerror(
                f"Invalid {kind}",
                f"Enter a {kind.lower()} name.",
                parent=parent,
            )
            return None
        if name.casefold() in {item.casefold() for item in existing}:
            messagebox.showerror(
                f"Duplicate {kind}",
                f"A {kind.lower()} named {name!r} already exists.",
                parent=parent,
            )
            return None
        return name
