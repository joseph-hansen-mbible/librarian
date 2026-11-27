from pathlib import Path
import json

from gui.resource_paths import gui_resource


class Who:
    def __init__(self):
        try:
            with gui_resource("whoami", ".whoami").open(encoding="utf-8") as file:
                data = json.load(file)
            self.options = data.get("options", [])
        except:
            with gui_resource("whoami", "whoami").open(encoding="utf-8") as file:
                data = json.load(file)
            self.options = data.get("options", [])
