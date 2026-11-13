from pathlib import Path
import tkinter as tk

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
    def populate_current_files_treeview(ref):
        lock_icon_path = Path(__file__).resolve().parent.parent / "assets" / "lock.png"
        ref.lock_icon = tk.PhotoImage(file=str(lock_icon_path)).subsample(16, 16)
        ref.current_files_treeview.insert("", "end", values=("File1.blend", "Joseph Hansen"), image=ref.lock_icon)
    
    @staticmethod
    def populate_recent_files_treeview(ref):
        lock_icon_path = Path(__file__).resolve().parent.parent / "assets" / "lock.png"
        unlock_icon_path = Path(__file__).resolve().parent.parent / "assets" / "unlock.png"
        ref.lock_icon = tk.PhotoImage(file=str(lock_icon_path)).subsample(16, 16)
        ref.unlock_icon = tk.PhotoImage(file=str(unlock_icon_path)).subsample(16, 16)
        ref.recent_files_treeview.insert("", "end", values=("File1.blend", "Joseph Hansen", "2023-10-01", "SSOT"), image=ref.lock_icon)
        ref.recent_files_treeview.insert("", "end", values=("File2.blend", "Joseph Hansen", "2023-10-01", "WIP"))