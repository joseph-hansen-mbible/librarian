import os
from pathlib import Path
import sys

class _FallbackPlatformDirs:
    def __init__(
        self,
        appname,
        appauthor=None,
        *,
        ensure_exists=False,
    ):
        self.appname = appname
        self.appauthor = appauthor
        self.ensure_exists = ensure_exists

    @property
    def user_data_path(self):
        if sys.platform == "darwin":
            path = (
                Path.home()
                / "Library"
                / "Application Support"
                / self.appname
            )
        elif os.name == "nt":
            data_root = os.environ.get("LOCALAPPDATA")
            if data_root:
                path = Path(data_root)
            else:
                path = Path.home() / "AppData" / "Local"
            if self.appauthor is not False:
                path /= self.appauthor or self.appname
            path /= self.appname
        else:
            data_root = os.environ.get("XDG_DATA_HOME")
            if data_root:
                path = Path(data_root)
            else:
                path = Path.home() / ".local" / "share"
            path /= self.appname

        if self.ensure_exists:
            path.mkdir(parents=True, exist_ok=True)
        return path


try:
    from platformdirs import PlatformDirs
except ImportError:
    PlatformDirs = _FallbackPlatformDirs
