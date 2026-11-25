import tkinter as tk
from tkinter import ttk
from pathlib import Path

class Filters:    
    @staticmethod
    def sort_treeview(ref, treeview, column, reverse, item_ids=None, filter_callback=None):
        items = [(treeview.set(item, column), item) for item in treeview.get_children("")]
        items.sort(
            key=lambda pair: str(pair[0]).casefold(),
            reverse=reverse,
        )
        for index, (_, item) in enumerate(items):
            treeview.move(item, "", index)
        if item_ids is not None:
            item_ids[:] = [item for _, item in items]
        if filter_callback is not None:
            filter_callback(ref)
        treeview.heading(
            column,
            command=lambda _column=column: Filters.sort_treeview(
                ref,
                treeview,
                _column,
                not reverse,
                item_ids,
                filter_callback,
            ),
        )

    @staticmethod
    def filter_all_files_treeview(ref):
        treeview = ref.locks_treeview
        query = ref.all_files_filter_var.get().casefold()
        previously_detached = ref.all_files_detached_item_ids.copy()
        visible_items = set(treeview.get_children(""))
        all_items = previously_detached | visible_items
        ref.all_files_detached_item_ids.clear()

        for item in ref.all_files_item_ids:
            if item not in all_items:
                continue

            values = treeview.item(item, "values")
            matches = not query or query in " ".join(str(value) for value in values).casefold()
            if matches:
                if item in previously_detached:
                    treeview.reattach(item, "", "end")
                else:
                    treeview.move(item, "", "end")
            else:
                if item not in previously_detached:
                    treeview.detach(item)
                ref.all_files_detached_item_ids.add(item)

    @staticmethod
    def sort_all_files_treeview(ref, column, reverse):
        treeview = ref.locks_treeview

        # Restore filtered rows so sorting always applies to the complete table.
        attached_items = set(treeview.get_children(""))
        for item in ref.all_files_item_ids:
            if item not in attached_items:
                treeview.reattach(item, "", "end")
        ref.all_files_detached_item_ids.clear()

        items = [(treeview.set(item, column), item) for item in treeview.get_children("")]
        items.sort(reverse=reverse)
        for index, (_, item) in enumerate(items):
            treeview.move(item, "", index)

        ref.all_files_item_ids[:] = [item for _, item in items]
        Filters.filter_all_files_treeview(ref)
        treeview.heading(
            column,
            command=lambda _column=column: Filters.sort_all_files_treeview(
                ref, _column, not reverse
            ),
        )