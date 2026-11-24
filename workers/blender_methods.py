import json
from pathlib import Path
from threading import Timer

from workers.models import LFRoles


class BlenderWorkerMethods:
    BLENDER_CACHE_POLL_INTERVAL = 2

    def WatchBlenderFile(self, filepath):
        if self._closed:
            return False
        if self.role is not LFRoles.BLENDER:
            raise RuntimeError("Blender file watching requires a Blender worker")

        self._blender_file_path = str(
            Path(filepath).expanduser().resolve()
        )
        self._blender_checkin_pending = False
        self._blender_cache_signature = self._GetBlenderCacheSignature()
        self._ScheduleBlenderCacheCheck()
        return True

    def _GetBlenderCacheSignature(self):
        try:
            cache_stat = self.blender_cache_file_path.stat()
        except FileNotFoundError:
            return None
        return (
            cache_stat.st_mtime_ns,
            cache_stat.st_size,
            cache_stat.st_ino,
        )

    def _ScheduleBlenderCacheCheck(self):
        if self._closed:
            return
        if (
            self._blender_watch_timer is not None
            and self._blender_watch_timer.is_alive()
        ):
            return

        timer = Timer(
            self.BLENDER_CACHE_POLL_INTERVAL,
            self._CheckBlenderCache,
        )
        timer.daemon = True
        self._blender_watch_timer = timer
        try:
            timer.start()
        except RuntimeError as error:
            self._ReportFailure(
                f"failed to schedule Blender cache check: {error}"
            )
            raise

    def _CheckBlenderCache(self):
        self._blender_watch_timer = None
        if self._closed:
            return

        if self._blender_checkin_pending:
            retry_timer = self._cache_copy_retry_timer
            if retry_timer is not None and retry_timer.is_alive():
                self._ScheduleBlenderCacheCheck()
            else:
                self._ScheduleBlenderCheckIn()
            return

        try:
            signature = self._GetBlenderCacheSignature()
        except OSError as error:
            self._ReportFailure(f"failed to inspect Blender cache: {error}")
            self._ScheduleBlenderCacheCheck()
            return

        if signature == self._blender_cache_signature:
            self._ScheduleBlenderCacheCheck()
            return
        self._blender_cache_signature = signature
        if signature is None:
            self._ScheduleBlenderCacheCheck()
            return

        try:
            with self.blender_cache_file_path.open(
                mode="r", encoding="utf-8"
            ) as cache_file:
                cache_data = json.load(cache_file)
            if not isinstance(cache_data, dict):
                raise ValueError("Blender cache must be a JSON object")
        except (OSError, ValueError) as error:
            self._ReportFailure(f"failed to read Blender cache: {error}")
            self._ScheduleBlenderCacheCheck()
            return

        checkin_path = cache_data.get("checking-in")
        if (
            cache_data.get("hey-fossa") == "all done"
            and isinstance(checkin_path, str)
            and checkin_path
            and str(Path(checkin_path).expanduser().resolve())
            == self._blender_file_path
        ):
            self._blender_checkin_pending = True
            self._ScheduleBlenderCheckIn()
            return

        self._ScheduleBlenderCacheCheck()

    def _ScheduleBlenderCheckIn(self):
        if self._closed:
            return
        if self._network_cache_queued or self._finishing_cache_queue:
            return
        retry_timer = self._cache_copy_retry_timer
        if retry_timer is not None and retry_timer.is_alive():
            self._ScheduleBlenderCacheCheck()
            return

        self.local_cache_data.current_file = ""
        try:
            if self.CacheData():
                self.Destroy()
                return
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            self._ReportFailure(
                f"failed to schedule Blender check-in: {error}"
            )

        self._ScheduleBlenderCacheCheck()
