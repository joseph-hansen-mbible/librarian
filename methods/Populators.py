import tkinter as tk

class Populators:
    @staticmethod
    def populate_who_listbox(ref, who):
        ref.who_listbox.delete(0, tk.END)
        for option in who.options:
            ref.who_listbox.insert(tk.END, option)
    
    @staticmethod
    def populate_project_listbox(ref, projects):
        ref.project_listbox.delete(0, tk.END)
        for project in projects:
            ref.project_listbox.insert(tk.END, project.name)