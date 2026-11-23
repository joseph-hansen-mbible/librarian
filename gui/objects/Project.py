from enum import Enum
import os
from copy import deepcopy

class Status(Enum):
    NOT_STARTED = "Not Started"
    ACTIVE = "Active"
    POSTPONED = "Postponed"
    COMPLETED = "Completed"
    POSTLAUNCH = "Post Launch"
    CANCELED = "Canceled"
    
class Project:
    def __init__(
        self,
        name,
        status,
        directory_path,
        scenes=None,
        characters=None,
        pending_change=None,
    ):
        self._name = name
        self._status = status if isinstance(status, Status) else Status.NOT_STARTED
        self._id = name.lower().replace(" ", "_")
        self._directory_path = directory_path
        self._scenes = deepcopy(scenes) if scenes is not None else []
        self._characters = list(characters) if characters is not None else []
        self._pending_change = deepcopy(pending_change)
        self._tag_color = self.determine_tag_color()
        
    def determine_tag_color(self):
        if self._status == Status.NOT_STARTED:
            return "gray"
        elif self._status == Status.ACTIVE:
            return "green"
        elif self._status == Status.POSTPONED:
            return "yellow"
        elif self._status == Status.COMPLETED:
            return "blue"
        elif self._status == Status.POSTLAUNCH:
            return "purple"
        elif self._status == Status.CANCELED:
            return "red"
        else:
            return "black"  # Default color for undefined statuses

    @property
    def name(self):
        return self._name

    @property
    def status(self):
        return self._status

    @property
    def id(self):
        return self._id

    @property
    def directory_path(self):
        return self._directory_path

    @property
    def scenes(self):
        return self._scenes

    @property
    def characters(self):
        return self._characters

    @property
    def pending_change(self):
        return self._pending_change

    @property
    def tag_color(self):
        return self._tag_color

    def update_status(self, new_status):
        if isinstance(new_status, Status):
            self._status = new_status
            self._tag_color = self.determine_tag_color()
        else:
            raise ValueError("new_status must be a Status")
    
    def update_directory_path(self, new_directory_path):
        if os.path.isdir(new_directory_path):
            self._directory_path = new_directory_path
        else:
            raise ValueError("new_directory_path must be a valid directory path")