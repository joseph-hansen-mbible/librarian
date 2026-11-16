import tkinter as tk
from tkinter import ttk
from pathlib import Path

from methods.Filters import Filters
from objects.Project import Project, Status

class CreatorsMaintab:
    @staticmethod
    def setup_main_window(root):
        root.title("Fossa - MOTB Art Team")
        return root

    @staticmethod
    def create_tab_container(window):
        notebook = ttk.Notebook(window)
        notebook.pack(pady=5, expand=True, fill='both')
        return notebook

    @staticmethod
    def create_tab_main(notebook):
        main_tab = ttk.Frame(notebook)
        main_tab.pack(fill='both', expand=True)
        notebook.add(main_tab, text='Main')
        return main_tab

    @staticmethod
    def create_tab_all_files(notebook):
        all_files_tab = ttk.Frame(notebook)
        all_files_tab.pack(fill='both', expand=True)
        notebook.add(all_files_tab, text='All Files')
        return all_files_tab
    
    @staticmethod
    def create_command_entry_frame(parent):
        command_bar_frame = ttk.Frame(parent)
        command_bar_frame.pack(fill='none', expand=False, padx=5, pady=40, side='top', anchor='center')
        return command_bar_frame
    
    @staticmethod
    def fill_command_entry_frame(ref):
        # "I want to..." label + action optionbox + "in" + project optionbox + "for" + scene optionbox + shot optionbox
        style = ttk.Style(ref.command_bar_frame)
        command_font = ref.command_font
        style.configure("CommandBar.TLabel", font=command_font)
        style.configure("CommandBar.TMenubutton", font=command_font)
        style.configure("Go.TButton", font=command_font, padding=(12, 6))

        action_label = ttk.Label(
            ref.command_bar_frame,
            text="I want to...",
            style="CommandBar.TLabel",
            font=command_font,
        )
        action_label.pack(side='left', padx=5)
        ref.command_action_var = tk.StringVar(value="Action")
        ref.command_action_optionbox = ttk.OptionMenu(
            ref.command_bar_frame,
            ref.command_action_var,
            "Action",
            "Action",
            style="CommandBar.TMenubutton",
        )
        ref.command_action_optionbox.pack(side='left', padx=5)
        second_command_label = ttk.Label(
            ref.command_bar_frame,
            text="in",
            style="CommandBar.TLabel",
            font=command_font,
        )
        second_command_label.pack(side='left', padx=5)
        ref.command_project_var = tk.StringVar(value="Project")
        ref.command_project_optionbox = ttk.OptionMenu(
            ref.command_bar_frame,
            ref.command_project_var,
            "Project",
            "Project",
            style="CommandBar.TMenubutton",
        )
        ref.command_project_optionbox.pack(side='left', padx=5)
        third_command_label = ttk.Label(
            ref.command_bar_frame,
            text="for",
            style="CommandBar.TLabel",
            font=command_font,
        )
        third_command_label.pack(side='left', padx=5)
        ref.command_scene_var = tk.StringVar(value="Scene")
        ref.command_scene_optionbox = ttk.OptionMenu(
            ref.command_bar_frame,
            ref.command_scene_var,
            "Scene",
            "Scene",
            style="CommandBar.TMenubutton",
        )
        ref.command_scene_optionbox.pack(side='left', padx=5)
        ref.command_shot_var = tk.StringVar(value="Shot")
        ref.command_shot_optionbox = ttk.OptionMenu(
            ref.command_bar_frame,
            ref.command_shot_var,
            "Shot",
            "Shot",
            style="CommandBar.TMenubutton",
        )
        ref.command_shot_optionbox.pack(side='left', padx=5)
        ref.command_execute_button = ttk.Button(
            ref.command_bar_frame,
            text="Go",
            style="Go.TButton",
        )
        ref.command_execute_button.pack(side='left', padx=5)
        
    @staticmethod
    def create_current_files_frame(parent):
        current_files_frame = ttk.Frame(parent)
        current_files_frame.pack(fill='both', expand=True, side='left', padx=5, pady=5)
        return current_files_frame

    @staticmethod
    def create_current_files_header(ref):
        ttk.Label(
            ref.current_files_frame,
            text="Currently Checked Out",
            font=ref.command_font,
            anchor='w',
        ).pack(side='top', fill='x', anchor='w', pady=5)
    
    @staticmethod
    def create_recent_files_frame(parent):
        recent_files_frame = ttk.Frame(parent)
        recent_files_frame.grid(row=0, column=1, sticky='nsew', padx=(2, 5), pady=5)
        return recent_files_frame

    @staticmethod
    def create_recent_files_header(ref):
        ttk.Label(
            ref.recent_files_frame,
            text="Recent Files",
            font=ref.command_font,
            anchor='w',
        ).pack(side='top', fill='x', pady=5)

    @staticmethod
    def create_recent_files_tree_frame(ref):
        tree_frame = ttk.Frame(ref.recent_files_frame)
        tree_frame.pack(side='top', fill='x')
        return tree_frame

    @staticmethod
    def create_recent_files_note_frame(ref):
        notes_frame = ttk.Frame(ref.recent_files_frame)
        notes_frame.pack(side='top', fill='both', expand=True, pady=(5, 0))

        ttk.Label(
            notes_frame,
            text="Notes",
            font=ref.treeview_heading_font_small,
            anchor='w',
        ).pack(side='top', fill='x', pady=(0, 2))

        notes_text = tk.Text(
            notes_frame,
            height=4,
            wrap='word',
            font=ref.treeview_font,
            state='disabled',
            exportselection=False,
            takefocus=False,
            bg="#2B2D32",
            
        )
        notes_scrollbar = ttk.Scrollbar(
            notes_frame,
            orient=tk.VERTICAL,
            command=notes_text.yview,
        )
        notes_text.configure(yscrollcommand=notes_scrollbar.set)
        notes_text.pack(side='left', fill='both', expand=True)
        notes_scrollbar.pack(side='right', fill='y')

        ref.recent_files_notes_text = notes_text

    @staticmethod
    def create_recent_files_open_button(ref):
        ref.open_recent_file_button = ttk.Button(
            ref.recent_files_frame,
            text="Open",
            style="Go.TButton",
        )
        ref.open_recent_file_button.pack(side='bottom', fill='x', pady=(5, 0))

    @staticmethod
    def create_file_lists_frame(parent):
        file_lists_frame = ttk.Frame(parent)
        file_lists_frame.pack(fill='both', expand=True, side='top')
        file_lists_frame.grid_columnconfigure(0, weight=2, uniform="file_lists")
        file_lists_frame.grid_columnconfigure(1, weight=1, uniform="file_lists")
        file_lists_frame.grid_rowconfigure(0, weight=1)
        file_lists_frame.ref = parent.ref
        return file_lists_frame

    @staticmethod
    def create_main_content_left_frame(parent):
        left_frame = ttk.Frame(parent)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(5, 2), pady=5)
        left_frame.ref = parent.ref
        return left_frame

    @staticmethod
    def create_locks_frame(parent):
        locks_frame = ttk.Frame(parent)
        locks_frame.pack(fill='both', expand=True, side='left', padx=5, pady=5)
        locks_frame_label = ttk.Label(locks_frame, text="SSOT/WIP", font=parent.ref.command_font, anchor='n')
        locks_frame_label.pack(side='top', pady=5)
        return locks_frame

    @staticmethod
    def create_locks_details_frame(parent):
        locks_details_frame = ttk.Frame(parent)
        locks_details_frame.pack(fill='x', expand=True, side='right', padx=5, pady=5, anchor='n')
        return locks_details_frame
    
    @staticmethod
    def create_locks_details_buttons(ref):
        ref.open_file_button = ttk.Button(
            ref.locks_details_frame,
            text="Open File",
            style="Go.TButton",
        )
        ref.request_unlock_ssot_button = ttk.Button(
            ref.locks_details_frame,
            text="Request Unlock",
        )
        ref.view_ssot_checklist_button = ttk.Button(
            ref.locks_details_frame,
            text="Open SSOT Checklist",
        )
        ref.open_file_button.pack(pady=10, fill='x', expand=True)
        ref.view_ssot_checklist_button.pack(pady=5, fill='x', expand=True)
        ref.request_unlock_ssot_button.pack(pady=5, fill='x', expand=True)
    
    @staticmethod
    def create_locks_treeview(ref):
        columns = ("Project", "Scene", "Shot", "Version", "Type", "Status", "Checklist", "UA")
        filter_frame = ttk.Frame(ref.locks_frame)
        filter_frame.pack(fill='x', side='top', padx=5, pady=(0, 5))
        ttk.Label(filter_frame, text="Filter:").pack(side='left', padx=(0, 5))
        ref.all_files_filter_var = tk.StringVar()
        ref.all_files_filter_entry = ttk.Entry(filter_frame, textvariable=ref.all_files_filter_var)
        ref.all_files_filter_entry.pack(side='left', fill='x', expand=True)

        treeview = ttk.Treeview(
            ref.locks_frame,
            columns=columns,
            show="headings",
        )
        
        treeview.config(style="Small.Treeview.Heading")
        treeview.config(style="Small.Treeview")
        
        treeview.column("Status", width=100, stretch=False)
        treeview.column("Scene", width=50, stretch=False)
        treeview.column("Shot", width=50, stretch=False)
        treeview.column("Checklist", width=100, stretch=False)
        treeview.column("UA", width=50, stretch=False)
        treeview.column("Version", width=60, stretch=False)
        for column in columns:
            treeview.heading(
                column,
                text=column,
                command=lambda _column=column: Filters.sort_all_files_treeview(
                    ref, _column, False
                ),
            )
            treeview.column(column, anchor="w")

        v_scrollbar = ttk.Scrollbar(ref.locks_frame, orient=tk.VERTICAL, command=treeview.yview)
        
        treeview.configure(yscrollcommand=v_scrollbar.set)
        treeview.pack(side='left', fill='both', expand=True, anchor='w')
        v_scrollbar.pack(side='right', fill='y')
        
        ref.locks_treeview = treeview
        ref.all_files_item_ids = []
        ref.all_files_detached_item_ids = set()
        ref.all_files_filter_var.trace_add(
            "write",
            lambda *_: Filters.filter_all_files_treeview(ref),
        )
    
    @staticmethod
    def create_file_text_table(parent, ref, columns, column_weights):
        table = ttk.Frame(parent)
        table.pack(fill='both', expand=True, padx=5, pady=5)
        for index, column in enumerate(columns):
            table.grid_columnconfigure(index, weight=column_weights[index])
            ttk.Label(
                table,
                text=column,
                font=ref.treeview_heading_font_small,
            ).grid(row=0, column=index, sticky='w', padx=(12, 8), pady=(8, 2))
        return table

    @staticmethod
    def create_current_files_table(ref):
        columns = ("File", "Artist")
        ref.current_files_table = CreatorsMaintab.create_file_text_table(
            ref.current_files_frame,
            ref,
            columns,
            (1, 1),
        )
        ref.current_files_table_next_row = 1
    
    @staticmethod
    def create_recent_files_treeview(ref):
        columns = ("File", "Artist", "Date", "Status")
        treeview = ttk.Treeview(
            ref.recent_files_tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=8,
        )
        treeview.column("Status", width=60, minwidth=60, stretch=False)
        treeview.column("Date", width=90, minwidth=90, stretch=False)
        treeview.column("Artist", width=105, minwidth=85, stretch=True)
        treeview.column("File", width=130, minwidth=100, stretch=True)
        for column in columns:
            treeview.heading(column, text=column)
            treeview.column(column, anchor="w")

        v_scrollbar = ttk.Scrollbar(
            ref.recent_files_tree_frame,
            orient=tk.VERTICAL,
            command=treeview.yview,
        )
        treeview.configure(yscrollcommand=v_scrollbar.set)
        treeview.pack(side='left', fill='x', expand=True, anchor='w')
        v_scrollbar.pack(side='right', fill='y')

        ref.recent_files_treeview = treeview
        