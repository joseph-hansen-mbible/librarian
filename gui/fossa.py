import os
import tkinter as tk
from tkinter import Menu, ttk
from pathlib import Path
import sys
import threading
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui.methods import Helpers
from objects.Project import Project, Status
from whoami import Who
from methods.Populators import Populators
from methods.Creators import CreatorsMaintab as Creators
from methods.CreatorsSettings import CreatorsSettings
from objects.References import References
from db import fossadb
from workers import core

def main():
    who = Who.Who()
    ref = References()
    ref.who = who
    Helpers.FossaMain(ref)

def CheckOutBlenderFile(filepath, artist, project, ref):
    if ref.database_connected:
        core.FossaWorker(core.LFRoles.CACHING, os.path.join(ref.network_base_path_variable.get(), project), artist, ref.database).CheckOutBlenderFile(filepath)

def CheckInBlenderFile(artist, project, ref):
    # you can only checkout one at a time so the filepath doesn't matter
    # this wouldn't work for actual VC but really CICO here is just file locks anyway
    if ref.database_connected:
        core.FossaWorker(core.LFRoles.CACHING, os.path.join(ref.network_base_path_variable.get(), project), artist, ref.database).CheckInBlenderFile()
    # this needs to connect to Blender and never be called directly, only through bpy,
    # to ensure that when a file is checked back in it CANNOT be edited without checking out again

if __name__ == "__main__":
    main()
