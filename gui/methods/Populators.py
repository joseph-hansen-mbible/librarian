import tkinter as tk
from tkinter import ttk

class Populators:
    @staticmethod
    def populate_who_listbox(ref, who):
        ref.who_listbox.delete(0, tk.END)
        for option in who.options:
            ref.who_listbox.insert(tk.END, option)
        if ref.who_listbox.size():
            ref.who_listbox.selection_set(0)
            ref.who_listbox.activate(0)
    
    @staticmethod
    def populate_project_listbox(ref, projects):
        ref.project_listbox.delete(0, tk.END)
        for project in projects:
            ref.project_listbox.insert(tk.END, project.name)
        if ref.project_listbox.size():
            ref.project_listbox.selection_set(0)
            ref.project_listbox.activate(0)
    
    @staticmethod
    def populate_current_files_table(ref):
        row = ("File1.blend", "Joseph Hansen")
        rows = [row, row, row, row, row, row]
        for r in rows:
            for column, value in enumerate(r):
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
        # ("Project", "Scene", "Shot", "Version", "Type", "Status", "Checklist", "UA")
        item = ref.locks_treeview.insert("", "end", values=("Noah", "1", "1", "1", "CharAnimGraybox", "WIP", "0/5", "0"))
        ref.all_files_item_ids.append(item)

    @staticmethod
    def update_status_bar(ref):
        text = "Database connected" if ref.database_connected else "Connection failure"
        background = "green" if ref.database_connected else "red"

        if not hasattr(ref, "status_bar_database_connection"):
            ref.status_bar_database_connection = ttk.Label(
                        ref.statusbar,
                        text=text,
                        font=ref.status_font,
                        anchor='center',
                        background=background,
                    )
            ref.status_bar_database_connection.pack(side="left", fill="x", expand=True)
        else:
            ref.status_bar_database_connection.configure(text=text, background=background)