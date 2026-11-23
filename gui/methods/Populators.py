import tkinter as tk
from tkinter import ttk

class Populators:
    STATUS_SUCCESS_BACKGROUND = "#24482a"
    STATUS_ERROR_BACKGROUND = "#6d2929"
    APPROVE_BACKGROUND = "#24482a"
    REJECT_BACKGROUND = "#6d2929"

    ACTIONS = (
        "Work on a character model",
        "Work on a character rig",
        "Work on a prop",
        "Graybox",
        "Animate characters with graybox",
        "Work on a set",
        "Test character materials on set",
        "Composite a shot",
    )
    CHARACTER_ACTIONS = {
        "Work on a character model",
        "Work on a character rig",
    }
    PROP_ACTIONS = {"Work on a prop"}
    SCENE_ONLY_ACTIONS = {
        "Work on a set",
        "Test character materials on set",
    }
    SHOT_ACTIONS = {
        "Graybox",
        "Animate characters with graybox",
        "Composite a shot",
    }

    @staticmethod
    def populate_who_listbox(ref, who):
        ref.who_listbox.delete(0, tk.END)
        for option in who.options:
            ref.who_listbox.insert(tk.END, option)
    
    @staticmethod
    def populate_project_listbox(ref, projects):
        selected_project_id = None
        selection = ref.project_listbox.curselection()
        if selection and selection[0] < len(ref.projects):
            selected_project_id = ref.projects[selection[0]].id

        ref.project_listbox.delete(0, tk.END)
        ref.projects = list(projects)
        for project in ref.projects:
            ref.project_listbox.insert(tk.END, project.name)
        if ref.project_listbox.size():
            selected_index = next(
                (
                    index
                    for index, project in enumerate(ref.projects)
                    if project.id == selected_project_id
                ),
                0,
            )
            ref.project_listbox.selection_set(selected_index)
            ref.project_listbox.activate(selected_index)
            ref.project_listbox.event_generate("<<ListboxSelect>>")
        else:
            ref.selected_project = None
            ref.project_details_label.configure(text="Project Details")
            ref.project_status_var.set("Status")
            ref.project_details_directory_path.configure(text="")
            ref.project_status_menu.configure(state="disabled")
            ref.project_structure_status_label.configure(text="")
            ref.project_structure_button.configure(state="disabled")
            ref.project_structure_discard_button.configure(state="disabled")
            for listbox in (
                ref.project_character_listbox,
                ref.project_scene_listbox,
                ref.project_shot_listbox,
                ref.project_prop_listbox,
                ref.project_setting_listbox,
            ):
                listbox.delete(0, tk.END)
            for frame, title in ref.project_structure_frames.items():
                frame.configure(text=f"{title} (0)")
            ref.command_project_var.set("Project")

    @staticmethod
    def populate_command_project_optionbox(ref, projects):
        project_names = [project.name for project in projects]
        menu = ref.command_project_optionbox["menu"]
        menu.delete(0, tk.END)
        menu.add_command(
            label="Project",
            command=tk._setit(ref.command_project_var, "Project"),
        )
        for project_name in project_names:
            menu.add_command(
                label=project_name,
                command=tk._setit(ref.command_project_var, project_name),
            )

        current_project = ref.command_project_var.get()
        selected_project = getattr(ref, "selected_project", None)
        if (
            current_project == "Project"
            and selected_project is not None
            and selected_project.name in project_names
        ):
            current_project = selected_project.name
        if current_project not in project_names:
            current_project = "Project"
        ref.command_project_var.set(current_project)

    @staticmethod
    def initialize_command_bar(ref):
        menu = ref.command_action_optionbox["menu"]
        menu.delete(0, tk.END)
        menu.add_command(
            label="Action",
            command=tk._setit(ref.command_action_var, "Action"),
        )
        for action in Populators.ACTIONS:
            menu.add_command(
                label=action,
                command=tk._setit(ref.command_action_var, action),
            )
        ref.command_action_var.trace_add(
            "write",
            lambda *_: Populators.update_command_action_fields(ref),
        )
        ref.command_project_var.trace_add(
            "write",
            lambda *_: Populators.populate_command_structure_optionboxes(ref),
        )
        ref.command_scene_var.trace_add(
            "write",
            lambda *_: Populators.populate_command_level_fields(ref),
        )
        Populators.populate_command_structure_optionboxes(ref)
        Populators.update_command_action_fields(ref)

    @staticmethod
    def _populate_optionbox(ref, optionbox, variable, placeholder, options):
        menu = optionbox["menu"]
        menu.delete(0, tk.END)
        menu.add_command(
            label=placeholder,
            command=tk._setit(variable, placeholder),
        )
        for option in options:
            menu.add_command(
                label=option,
                command=tk._setit(variable, option),
            )
        current = variable.get()
        if current not in options:
            current = placeholder
        variable.set(current)

    @staticmethod
    def populate_command_structure_optionboxes(ref):
        selected_name = ref.command_project_var.get()
        project = next(
            (
                project
                for project in getattr(ref, "projects", [])
                if project.name == selected_name
            ),
            None,
        )
        Populators._populate_optionbox(
            ref,
            ref.command_character_optionbox,
            ref.command_character_var,
            "Character",
            project.characters if project is not None else [],
        )
        Populators._populate_optionbox(
            ref,
            ref.command_prop_optionbox,
            ref.command_prop_var,
            "Prop",
            project.props if project is not None else [],
        )
        Populators._populate_optionbox(
            ref,
            ref.command_scene_optionbox,
            ref.command_scene_var,
            "Level",
            [
                f'{level["name"]} - {level["subtitle"]}'
                if level.get("subtitle")
                else level["name"]
                for level in project.scenes
            ]
            if project is not None
            else [],
        )
        Populators.populate_command_level_fields(ref)

    @staticmethod
    def selected_command_level(ref):
        selected_project = ref.command_project_var.get()
        project = next(
            (
                project
                for project in getattr(ref, "projects", [])
                if project.name == selected_project
            ),
            None,
        )
        if project is None:
            return None
        selected_level_text = ref.command_scene_var.get()
        return next(
            (
                level
                for level in project.scenes
                if (
                    f'{level["name"]} - {level["subtitle"]}'
                    if level.get("subtitle")
                    else level["name"]
                )
                == selected_level_text
            ),
            None,
        )

    @staticmethod
    def populate_command_level_fields(ref):
        Populators.populate_command_shots(ref)
        Populators.populate_command_settings(ref)

    @staticmethod
    def populate_command_shots(ref):
        selected_level = Populators.selected_command_level(ref)
        Populators._populate_optionbox(
            ref,
            ref.command_shot_optionbox,
            ref.command_shot_var,
            "Shot",
            selected_level["shots"] if selected_level is not None else [],
        )

    @staticmethod
    def populate_command_settings(ref):
        selected_level = Populators.selected_command_level(ref)
        Populators._populate_optionbox(
            ref,
            ref.command_setting_optionbox,
            ref.command_setting_var,
            "Setting",
            selected_level["settings"] if selected_level is not None else [],
        )

    @staticmethod
    def update_command_action_fields(ref):
        action = ref.command_action_var.get()
        ref.command_target_label.pack_forget()
        ref.command_character_optionbox.pack_forget()
        ref.command_prop_optionbox.pack_forget()
        ref.command_scene_optionbox.pack_forget()
        ref.command_shot_optionbox.pack_forget()
        ref.command_setting_optionbox.pack_forget()

        if action in Populators.CHARACTER_ACTIONS:
            ref.command_target_label.pack(
                side="left",
                padx=5,
                before=ref.command_execute_button,
            )
            ref.command_character_optionbox.pack(
                side="left",
                padx=5,
                before=ref.command_execute_button,
            )
        elif action in Populators.PROP_ACTIONS:
            ref.command_target_label.pack(
                side="left",
                padx=5,
                before=ref.command_execute_button,
            )
            ref.command_prop_optionbox.pack(
                side="left",
                padx=5,
                before=ref.command_execute_button,
            )
            ref.command_scene_optionbox.pack(
                side="left",
                padx=5,
                before=ref.command_execute_button,
            )
            ref.command_setting_optionbox.pack(
                side="left",
                padx=5,
                before=ref.command_execute_button,
            )
        elif action in Populators.SCENE_ONLY_ACTIONS | Populators.SHOT_ACTIONS:
            ref.command_target_label.pack(
                side="left",
                padx=5,
                before=ref.command_execute_button,
            )
            ref.command_scene_optionbox.pack(
                side="left",
                padx=5,
                before=ref.command_execute_button,
            )
            if action in Populators.SCENE_ONLY_ACTIONS:
                ref.command_setting_optionbox.pack(
                    side="left",
                    padx=5,
                    before=ref.command_execute_button,
                )
            if action in Populators.SHOT_ACTIONS:
                ref.command_shot_optionbox.pack(
                    side="left",
                    padx=5,
                    before=ref.command_execute_button,
                )
    
    @staticmethod
    def populate_current_files_table(ref, rows=None):
        if rows is None:
            rows = []

        for widget in ref.current_files_table.winfo_children():
            widget.destroy()
        ref.current_files_table_next_row = 1

        for row in rows:
            for column, value in enumerate(row):
                ttk.Label(
                    ref.current_files_table,
                    text=value,
                    style="CurrentFilesValue.TLabel",
                ).grid(
                    row=ref.current_files_table_next_row,
                    column=column,
                    sticky='w',
                    padx=(5, 8),
                    pady=2,
                )
            ref.current_files_table_next_row += 1
    
    @staticmethod
    def populate_recent_files_treeview(ref):
        ref.recent_files_treeview.insert(
            "",
            "end",
            values=("File1.blend", "Joseph Hansen", "2023-10-01", "SSOT"),
        )
        ref.recent_files_treeview.insert(
            "",
            "end",
            values=("File2.blend", "Joseph Hansen", "2023-10-01", "WIP"),
        )
    
    @staticmethod
    def populate_locks_treeview(ref):
        # ("Project", "Level", "Shot", "Version", "Type", "Status", "Checklist", "UA")
        item = ref.locks_treeview.insert("", "end", values=("Noah", "1", "1", "1", "CharAnimGraybox", "WIP", "0/5", "0"))
        ref.all_files_item_ids.append(item)

    @staticmethod
    def update_status_bar(ref):
        database_text = "Database connected" if ref.database_connected else "Connection failure"
        database_background = (
            Populators.STATUS_SUCCESS_BACKGROUND
            if ref.database_connected
            else Populators.STATUS_ERROR_BACKGROUND
        )
        
        blender_text = "Fruitbat ready" if ref.blender_ready else "Set the path to Fruitbat executable in settings"
        blender_background = (
            Populators.STATUS_SUCCESS_BACKGROUND
            if ref.blender_ready
            else Populators.STATUS_ERROR_BACKGROUND
        )

        if not hasattr(ref, "status_bar_database_connection"):
            ref.status_bar_database_connection = ttk.Label(
                        ref.statusbar,
                        text=database_text,
                        font=ref.status_font,
                        anchor='center',
                        background=database_background,
                        foreground="#ffffff"
                    )
            
            ref.status_bar_database_connection.pack(side="left", fill="x", expand=True, padx="2")
            
        else:
            ref.status_bar_database_connection.configure(
                text=database_text,
                background=database_background,
                foreground="#ffffff",
            )
        
        if not hasattr(ref, "status_bar_blender_connection"):
            ref.status_bar_blender_connection = ttk.Label(
                ref.statusbar,
                text=blender_text,
                font=ref.status_font,
                anchor='center',
                background=blender_background,
                foreground="#ffffff"
            )
            ref.status_bar_blender_connection.pack(side="left", fill="x", expand=True, padx="2")
        else: 
            ref.status_bar_blender_connection.configure(
                text=blender_text,
                background=blender_background,
                foreground="#ffffff",
            )
