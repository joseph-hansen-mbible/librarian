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
    
    