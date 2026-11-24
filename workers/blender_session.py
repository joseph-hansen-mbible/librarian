import hashlib
import json
import os
from pathlib import Path
from threading import Lock, Timer

from platformdirs import PlatformDirs

from workers.models import LocalCacheData, LFRoles


BLENDER_CACHE_POLL_SECONDS = 20


def BlenderSessionCachePath(artist):
    artist = str(artist)
    if not artist:
        raise ValueError("Artist must not be empty")
    dirs = PlatformDirs("Fossa", "Joseph Hansen", ensure_exists=True)
    artist_hash = hashlib.sha256(artist.encode("utf-8")).hexdigest()
    return dirs.user_data_path / f"blender_{artist_hash}.flf"


def WriteInitialBlenderSessionCache(fossa_db, artist, filepath):
    filepath = Path(filepath).expanduser().resolve()
    database = fossa_db.GetDatabaseSnapshot()
    artist_data = database.get(str(artist), {})
    if not isinstance(artist_data, dict):
        artist_data = {}

    file_index = database.get("__blender_files__", {})
    file_metadata = (
        file_index.get(str(filepath), {})
        if isinstance(file_index, dict)
        else {}
    )
    if not isinstance(file_metadata, dict):
        file_metadata = {}

    recent_files = artist_data.get("recent_files", [])
    if not isinstance(recent_files, list):
        recent_files = []
    recent_files = [
        recent_file
        for recent_file in recent_files
        if isinstance(recent_file, str)
    ]
    if str(filepath) in recent_files:
        recent_files.remove(str(filepath))
    recent_files.append(str(filepath))

    checklist = file_metadata.get(
        "checklist",
        artist_data.get("current_file_checklist", {}),
    )
    if not isinstance(checklist, dict):
        checklist = {}
    unlock_count = file_metadata.get(
        "unlock_approvals",
        artist_data.get("ssot_unlock_count", 0),
    )
    if not isinstance(unlock_count, int) or isinstance(unlock_count, bool):
        unlock_count = 0

    cache_data = {
        "revision": 0,
        "blender_open": True,
        "current_file": str(filepath),
        "recent_files": recent_files,
        "current_file_checklist": checklist,
        "unlock_ssot_request": bool(
            artist_data.get("unlock_ssot_request", False)
        ),
        "ssot_unlock_count": unlock_count,
    }
    cache_path = BlenderSessionCachePath(artist)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cache_path.with_name(f".{cache_path.name}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as cache_file:
            json.dump(cache_data, cache_file)
            cache_file.flush()
            os.fsync(cache_file.fileno())
        os.replace(temporary_path, cache_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return cache_path


def StartBlenderSessionMonitor(
    artist,
    network_base_path,
    fossa_db,
    filepath,
    failure_callback=None,
):
    cache_path = WriteInitialBlenderSessionCache(
        fossa_db,
        artist,
        filepath,
    )
    return BlenderSessionMonitor(
        artist,
        network_base_path,
        fossa_db,
        cache_path,
        failure_callback=failure_callback,
    ).Start()


class BlenderSessionMonitor:
    _active_monitors = set()
    _active_monitors_lock = Lock()

    def __init__(
        self,
        artist,
        network_base_path,
        fossa_db,
        cache_path,
        poll_interval=BLENDER_CACHE_POLL_SECONDS,
        failure_callback=None,
    ):
        self.artist = artist
        self.network_base_path = Path(network_base_path).expanduser().resolve()
        self.fossa_db = fossa_db
        self.cache_path = Path(cache_path).expanduser().resolve()
        self.poll_interval = poll_interval
        self.failure_callback = failure_callback
        self._closed = False
        self._last_revision = 0
        self._last_reported_failure = None
        self._timer = None
        self._lock = Lock()

    def Start(self):
        with self._active_monitors_lock:
            self._active_monitors.add(self)
        self._Schedule(0)
        return self

    def Stop(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            timer = self._timer
            self._timer = None
        if timer is not None:
            timer.cancel()
        with self._active_monitors_lock:
            self._active_monitors.discard(self)

    @classmethod
    def StopAll(cls):
        with cls._active_monitors_lock:
            monitors = tuple(cls._active_monitors)
        for monitor in monitors:
            monitor.Stop()

    def _Schedule(self, delay):
        with self._lock:
            if self._closed:
                return
            timer = Timer(delay, self._Poll)
            timer.daemon = True
            self._timer = timer
        try:
            timer.start()
        except RuntimeError as error:
            self.Stop()
            self._ReportFailure(f"failed to schedule Blender cache polling: {error}")
            raise

    def _Poll(self):
        with self._lock:
            self._timer = None
            if self._closed:
                return

        try:
            with self.cache_path.open("r", encoding="utf-8") as cache_file:
                cache_data = json.load(cache_file)
            self._ValidateCacheData(cache_data)
        except (OSError, TypeError, ValueError) as error:
            self._ReportFailure(f"failed to read Blender cache {self.cache_path}: {error}")
            self._Schedule(self.poll_interval)
            return

        revision = cache_data["revision"]
        blender_open = cache_data["blender_open"]
        has_update = revision != self._last_revision or not blender_open
        if has_update:
            if self._ForwardCacheData(cache_data):
                self._last_revision = revision
                self._last_reported_failure = None
                if not blender_open:
                    self.Stop()
                    return
        else:
            self._last_reported_failure = None

        self._Schedule(self.poll_interval)

    def _ForwardCacheData(self, cache_data):
        current_file = cache_data["current_file"]
        if not cache_data["blender_open"]:
            current_file = ""
        local_cache_data = LocalCacheData(
            current_file=current_file,
            recent_files=cache_data["recent_files"],
            current_file_checklist=cache_data["current_file_checklist"],
            unlock_ssot_request=cache_data["unlock_ssot_request"],
            ssot_unlock_count=cache_data["ssot_unlock_count"],
        )

        from workers.core import FossaWorker

        worker = None
        try:
            worker = FossaWorker(
                LFRoles.CACHING,
                self.network_base_path,
                self.artist,
                self.fossa_db,
                failure_callback=self._NotifyFailure,
            )
            worker.local_cache_data = local_cache_data
            queued = worker.CacheData()
            retrying = (
                worker._cache_copy_retry_timer is not None
                and worker._cache_copy_retry_timer.is_alive()
            )
            accepted = queued or worker._closed or retrying
            if not accepted and not worker._closed:
                worker.Destroy()
            return accepted
        except Exception as error:
            self._ReportFailure(f"failed to forward Blender cache: {error}")
            if worker is not None and not worker._closed:
                worker.Destroy()
            return False

    @staticmethod
    def _ValidateCacheData(cache_data):
        if not isinstance(cache_data, dict):
            raise ValueError("Blender cache must be a JSON object")
        revision = cache_data.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            raise ValueError("Blender cache revision must be a non-negative integer")
        if not isinstance(cache_data.get("blender_open"), bool):
            raise ValueError("Blender cache blender_open must be a boolean")
        if not isinstance(cache_data.get("current_file", ""), str):
            raise ValueError("Blender cache current_file must be text")
        recent_files = cache_data.get("recent_files", [])
        if not isinstance(recent_files, list) or not all(
            isinstance(filepath, str) for filepath in recent_files
        ):
            raise ValueError("Blender cache recent_files must be a string array")
        checklist = cache_data.get("current_file_checklist", {})
        if not isinstance(checklist, dict):
            raise ValueError("Blender cache checklist must be a JSON object")
        if not isinstance(cache_data.get("unlock_ssot_request", False), bool):
            raise ValueError("Blender cache unlock_ssot_request must be a boolean")
        unlock_count = cache_data.get("ssot_unlock_count", 0)
        if not isinstance(unlock_count, int) or isinstance(unlock_count, bool):
            raise ValueError("Blender cache ssot_unlock_count must be an integer")

    def _ReportFailure(self, message):
        self.fossa_db._ReportFailure(
            message,
            network_base_path=self.network_base_path,
            artist=self.artist,
        )
        self._NotifyFailure(message)

    def _NotifyFailure(self, message):
        if (
            self.failure_callback is not None
            and message != self._last_reported_failure
        ):
            self._last_reported_failure = message
            self.failure_callback(message)
