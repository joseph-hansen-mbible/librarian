import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class CreatorsSettings:
    @staticmethod
    def create_settings_window(ref):
        settings_window = tk.Toplevel(ref.main_window)
        settings_window.title("Settings")
        settings_window.geometry("800x300")
        settings_window.minsize(400, 200)
        if ref.selected_who is not None:
            settings_window.transient(ref.main_window)
        settings_window.withdraw()
        settings_window.protocol(
            "WM_DELETE_WINDOW",
            lambda: (
                settings_window.withdraw()
                if ref.selected_who
                else settings_window.lift()
            ),
        )

        ref.settings_tab = ttk.Frame(settings_window)
        ref.settings_tab.pack(fill="both", expand=True)
        return settings_window

    @staticmethod
    def create_settings_button(ref, parent):
        settings_icon_path = (
            Path(__file__).resolve().parent.parent / "assets" / "settings.png"
        )
        ref.settings_icon = tk.PhotoImage(file=str(settings_icon_path)).subsample(2, 2)
        ref.settings_button = ttk.Button(
            parent,
            image=ref.settings_icon,
            command=lambda: CreatorsSettings.show_settings_window(ref),
        )
        ref.settings_button.pack(side="right", padx=5)

    @staticmethod
    def show_settings_window(ref):
        ref.settings_window.deiconify()
        ref.settings_window.lift()
        ref.settings_window.focus_set()

    @staticmethod
    def create_settings_who_frame(ref):
        who_frame = ttk.LabelFrame(
            ref.settings_tab,
            text="You must set who you are before proceeding",
        )
        who_frame.pack(fill="x", expand=False, padx=5, pady=5, side="top")
        who_listbox = tk.Listbox(
            who_frame,
            height=10,
            exportselection=False,
        )
        who_listbox.pack(side="left", anchor="w", fill="none", expand=True)

        ref.who_listbox = who_listbox
        ref.who_frame = who_frame
        who_listbox.bind(
            "<<ListboxSelect>>",
            lambda _event: CreatorsSettings.select_who(ref),
        )

    @staticmethod
    def select_who(ref):
        selection = ref.who_listbox.curselection()
        if not selection:
            return
        selected_who = ref.who_listbox.get(selection[0])
        try:
            ref.save_selected_who(selected_who)
        except OSError as error:
            messagebox.showerror(
                "Could not save selection",
                f"Your selection could not be saved: {error}",
                parent=ref.settings_window,
            )
            ref.who_listbox.selection_clear(0, tk.END)
            return

        ref.selected_who = selected_who
        ref.who_frame.destroy()
        ref.main_window.deiconify()
        ref.settings_window.withdraw()
        from methods.Helpers import (
            FossaCheckProjectApprovals,
            FossaUpdateMainFileLists,
        )

        FossaUpdateMainFileLists(ref, schedule=False)
        FossaCheckProjectApprovals(ref, schedule=False)

    @staticmethod
    def create_settings_other_frame(ref):
        other_frame = ttk.LabelFrame(ref.settings_tab, text="Settings")
        other_frame.pack(fill="x", expand=False, padx=10, pady=10, side="top")

        other_row = ttk.Frame(other_frame)
        other_row.pack(fill="x", expand=False, padx=5, pady=5)

        blender_file_path_entry = ttk.Entry(
            other_row,
            textvariable=ref.blender_file_path_variable,
        )
        blender_file_path_entry.pack(side="left", fill="x", expand=True)
        blender_file_path_entry.bind(
            "<Return>",
            lambda _event: CreatorsSettings.save_blender_file_path(ref),
        )
        blender_file_path_entry.bind(
            "<FocusOut>",
            lambda _event: CreatorsSettings.save_blender_file_path(ref),
        )
        choose_blender_file_path_button = ttk.Button(
            other_row,
            text="Blender Executable",
            command=lambda: CreatorsSettings.choose_blender_file_path(ref),
        )
        choose_blender_file_path_button.pack(side="right", padx=5)
        ref.blender_file_path_entry = blender_file_path_entry

        network_row = ttk.Frame(other_frame)
        network_row.pack(fill="x", expand=False, padx=5, pady=5)
        network_base_path_entry = ttk.Entry(
            network_row,
            textvariable=ref.network_base_path_variable,
        )
        network_base_path_entry.pack(side="left", fill="x", expand=True)
        network_base_path_entry.bind(
            "<Return>",
            lambda _event: CreatorsSettings.save_network_base_path(ref),
        )
        network_base_path_entry.bind(
            "<FocusOut>",
            lambda _event: CreatorsSettings.save_network_base_path(ref),
        )
        choose_network_base_path_button = ttk.Button(
            network_row,
            text="Network Folder",
            command=lambda: CreatorsSettings.choose_network_base_path(ref),
        )
        choose_network_base_path_button.pack(side="right", padx=5)
        ref.network_base_path_entry = network_base_path_entry

        ttk.Button(
            ref.settings_tab,
            text="Increase Font Size",
            command=ref.increase_font_size,
        ).pack(padx=10, pady=(0, 5), anchor="w")
        ttk.Button(
            ref.settings_tab,
            text="Decrease Font Size",
            command=ref.decrease_font_size,
        ).pack(padx=10, pady=(0, 10), anchor="w")

    @staticmethod
    def choose_blender_file_path(ref):
        blender_file_path = filedialog.askopenfilename(
            parent=ref.settings_window,
            title="Select Blender executable",
            filetypes=(("Blender executable", "*"), ("All files", "*")),
        )
        if blender_file_path:
            ref.blender_file_path_variable.set(blender_file_path)
            CreatorsSettings.save_blender_file_path(ref)

    @staticmethod
    def save_blender_file_path(ref):
        ref.save_blender_file_path(ref.blender_file_path_variable.get())
        ref.update_status_bar()

    @staticmethod
    def choose_network_base_path(ref):
        network_base_path = filedialog.askdirectory(
            parent=ref.settings_window,
            title="Select network folder",
            mustexist=True,
        )
        if network_base_path:
            ref.network_base_path_variable.set(network_base_path)
            CreatorsSettings.save_network_base_path(ref)

    @staticmethod
    def save_network_base_path(ref):
        ref.save_network_base_path(ref.network_base_path_variable.get())
        ref.update_status_bar()
