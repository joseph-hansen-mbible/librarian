from pathlib import Path
import json

class Who:
    def __init__(self):
        with (Path(__file__).parent / ".whoami").open(encoding="utf-8") as file:
            data = json.load(file)
        self.options = data.get("options", [])