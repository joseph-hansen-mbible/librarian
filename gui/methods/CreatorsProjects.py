from pathlib import Path
from tkinter import messagebox
import tkinter as tk
from tkinter import filedialog, ttk

from methods.CreatorsProjectApprovals import CreatorsProjectApprovals
from methods.CreatorsProjectDetails import CreatorsProjectDetails
from methods.ProjectStructureDialogs import ProjectStructureDialogs
from objects.Project import Project, Status


class CreatorsProjects:
    @staticmethod
    def create_projects_tab(ref, notebook):
        projects_tab = ttk.Frame(notebook)
        notebook.add(projects_tab, text="Projects")

        projects_frame = ttk.Frame(projects_tab)
        projects_frame.pack(fill="both", expand=True, padx=8, pady=8)

        project_list_panel = ttk.LabelFrame(projects_frame, text="Projects")
        project_list_panel.pack(side="left", fill="y", padx=(0, 8))
        project_list_panel.configure(width=240)
        project_list_panel.pack_propagate(False)
        new_project_button = ttk.Button(
            project_list_panel,
            text="New Project",
            command=lambda: CreatorsProjects.show_new_project_window(ref),
        )
        new_project_button.pack(fill="x", padx=5, pady=5)
        project_listbox = tk.Listbox(
            project_list_panel,
            height=10,
            exportselection=False,
        )
        project_listbox.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        project_details_frame = ttk.LabelFrame(
            projects_frame,
            text="Project Details",
        )
        project_details_frame.pack(side="left", fill="both", expand=True)
        project_details_label = ttk.Label(
            project_details_frame,
            text="Project Details",
        )
        project_status_var = tk.StringVar(value="Status")
        project_status_frame = ttk.Frame(project_details_frame)
        ttk.Label(project_status_frame, text="Status").pack(
            side="left",
            padx=(0, 8),
        )
        project_details_status = ttk.Combobox(
            project_status_frame,
            textvariable=project_status_var,
            values=[status.value for status in Status],
            state="disabled",
            width=18,
        )
        project_details_status.pack(side="left")
        project_details_status.bind(
            "<<ComboboxSelected>>",
            lambda _event: CreatorsProjectDetails.request_project_status_change(ref),
        )
        ttk.Label(
            project_status_frame,
            text="Selecting a status requests two approvals.",
        ).pack(side="left", padx=8)
        project_details_code = ttk.Label(project_details_frame, anchor="w")
        project_details_directory_path = ttk.Label(
            project_details_frame,
            wraplength=700,
            anchor="w",
        )
        project_details_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=5,
            pady=(5, 0),
        )
        project_status_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=5,
            pady=3,
        )
        project_details_directory_path.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=5,
            pady=3,
        )
        project_details_code.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=5,
            pady=3,
        )

        structure_frame = ttk.Frame(project_details_frame)
        structure_frame.grid(
            row=4,
            column=0,
            sticky="nsew",
            padx=5,
            pady=5,
        )
        project_details_frame.grid_columnconfigure(0, weight=1)
        project_details_frame.grid_rowconfigure(4, weight=1)
        structure_widgets = {}
        structure_titles = ("Characters", "Levels", "Shots", "Props", "Settings")
        for column in range(3):
            structure_frame.grid_columnconfigure(
                column,
                weight=1,
                uniform="project-structure",
            )
        for row in range((len(structure_titles) + 2) // 3):
            structure_frame.grid_rowconfigure(row, weight=1)
        for index, title in enumerate(structure_titles):
            row, column = divmod(index, 3)
            label_frame = ttk.LabelFrame(
                structure_frame,
                text=f"{title} (0)",
            )
            label_frame.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=3,
                pady=3,
            )
            listbox = tk.Listbox(label_frame, exportselection=False)
            listbox.pack(fill="both", expand=True, padx=4, pady=4)
            structure_widgets[title] = (label_frame, listbox)

        project_structure_status_label = ttk.Label(project_details_frame, text="")
        project_structure_status_label.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=5,
            pady=(0, 3),
        )
        project_structure_buttons = ttk.Frame(project_details_frame)
        project_structure_buttons.grid(
            row=6,
            column=0,
            sticky="ew",
            padx=5,
            pady=(3, 5),
        )
        project_structure_button = ttk.Button(
            project_structure_buttons,
            text="Edit Project",
            command=lambda: CreatorsProjectDetails.show_project_structure_editor(ref),
            state="disabled",
        )
        project_structure_button.pack(side="left", fill="x", expand=True)
        project_structure_discard_button = ttk.Button(
            project_structure_buttons,
            text="Discard Draft",
            command=lambda: CreatorsProjectDetails.discard_project_structure_draft(ref),
            state="disabled",
        )

        ref.new_project_button = new_project_button
        ref.projects_tab = projects_tab
        ref.projects_frame = projects_frame
        ref.project_listbox = project_listbox
        ref.project_details_label = project_details_label
        ref.project_details_status = project_details_status
        ref.project_details_directory_path = project_details_directory_path
        ref.project_details_code = project_details_code
        ref.project_status_var = project_status_var
        ref.project_status_menu = project_details_status
        ref.project_structure_status_label = project_structure_status_label
        ref.project_structure_button = project_structure_button
        ref.project_structure_discard_button = project_structure_discard_button
        ref.project_structure_frames = {
            structure_widgets[title][0]: title for title in structure_titles
        }
        ref.project_structure_frames_by_title = {
            title: structure_widgets[title][0] for title in structure_titles
        }
        ref.project_character_listbox = structure_widgets["Characters"][1]
        ref.project_scene_listbox = structure_widgets["Levels"][1]
        ref.project_shot_listbox = structure_widgets["Shots"][1]
        ref.project_prop_listbox = structure_widgets["Props"][1]
        ref.project_setting_listbox = structure_widgets["Settings"][1]
        project_listbox.bind(
            "<<ListboxSelect>>",
            lambda _event: CreatorsProjectDetails.show_project_details(ref),
        )
        return projects_tab

    @staticmethod
    def show_project_change_approval_dialog(ref, change, on_decision):
        CreatorsProjectApprovals.show_project_change_approval_dialog(
            ref,
            change,
            on_decision,
        )

    @staticmethod
    def show_new_project_window(ref):
        dialog = tk.Toplevel(ref.projects_tab)
        dialog.title("New Project")
        dialog.transient(ref.projects_tab)
        dialog.resizable(False, False)
        dialog.grab_set()

        name_var = tk.StringVar()
        project_code_var = tk.StringVar()
        status_var = tk.StringVar(value=Status.NOT_STARTED.value)
        directory_var = tk.StringVar()

        ttk.Label(dialog, text="Name").grid(
            row=0,
            column=0,
            sticky="w",
            padx=10,
            pady=(10, 4),
        )
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.grid(
            row=0,
            column=1,
            columnspan=2,
            sticky="ew",
            padx=10,
            pady=(10, 4),
        )
        ttk.Label(dialog, text="Project Code").grid(
            row=1,
            column=0,
            sticky="w",
            padx=10,
            pady=4,
        )
        ttk.Entry(dialog, textvariable=project_code_var, width=8).grid(
            row=1,
            column=1,
            sticky="w",
            padx=10,
            pady=4,
        )
        ttk.Label(dialog, text="2-5 letters, no spaces").grid(
            row=1,
            column=2,
            sticky="w",
            padx=10,
            pady=4,
        )
        ttk.Label(dialog, text="Status").grid(
            row=2,
            column=0,
            sticky="w",
            padx=10,
            pady=4,
        )
        status_menu = ttk.Combobox(
            dialog,
            textvariable=status_var,
            values=[status.value for status in Status],
            state="readonly",
        )
        status_menu.grid(
            row=2,
            column=1,
            columnspan=2,
            sticky="ew",
            padx=10,
            pady=4,
        )
        ttk.Label(dialog, text="Directory").grid(
            row=3,
            column=0,
            sticky="w",
            padx=10,
            pady=4,
        )
        ttk.Entry(dialog, textvariable=directory_var, width=32).grid(
            row=3,
            column=1,
            sticky="ew",
            padx=(10, 4),
            pady=4,
        )
        ttk.Button(
            dialog,
            text="Browse",
            command=lambda: CreatorsProjects.choose_project_directory(
                dialog,
                directory_var,
            ),
        ).grid(row=3, column=2, padx=(0, 10), pady=4)

        button_row = ttk.Frame(dialog)
        button_row.grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="e",
            padx=10,
            pady=10,
        )
        ProjectStructureDialogs.add_cancel_button(
            button_row,
            ref,
            dialog.destroy,
        ).pack(side="right", padx=(5, 0))
        ttk.Button(
            button_row,
            text="Create",
            command=lambda: CreatorsProjects.save_new_project(
                ref,
                dialog,
                name_var.get(),
                project_code_var.get(),
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
    def save_new_project(ref, dialog, name, project_code, status, directory_path):
        name = name.strip()
        project_code = project_code.strip()
        directory_path = directory_path.strip()
        if not name or not project_code or not directory_path:
            messagebox.showerror(
                "Invalid project",
                "Enter a project name and code, and choose a directory.",
                parent=dialog,
            )
            return
        try:
            from db.project_structure import ProjectStructure

            ProjectStructure.ValidateProjectCode(
                project_code,
                allow_empty=False,
            )
            project_status = Status(status)
            directory_path = str(Path(directory_path).expanduser().resolve())
            project = Project(
                name,
                project_status,
                directory_path,
                project_code=project_code,
            )
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
