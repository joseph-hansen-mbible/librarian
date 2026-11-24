import datetime
import json
import os
from pathlib import Path
import shutil
from threading import Timer

from platformdirs import PlatformDirs

from db import file_lock
from workers.models import LFRoles


class CacheWorkerMethods:
    def EstablishLocalCachePaths(self):
        dirs = PlatformDirs("Fossa", "Joseph Hansen", ensure_exists=True)
        appdata = dirs.user_data_path
        self.appdata_path = appdata
        self.cache_file_path = appdata / f"{self.name}_cache.flf"
        self.blender_cache_file_path = appdata / "blender_cache.flf"
        self.cache_role_lock_file_path = appdata / f"{LFRoles.CACHING.value}.flf"
        self.conflicts_file_path = appdata / "Conflicts.flf"

    def ScheduleLocalCacheCopyToNetwork(self):
        network_cache_path = self.BuildNetworkCachePath()
        with self._cache_copy_guard:
            if self._closed:
                return False
            if (
                self._cache_copy_retry_timer is not None
                and self._cache_copy_retry_timer.is_alive()
            ):
                return False

            temporary_path = network_cache_path.with_name(
                f".{network_cache_path.name}.{self.name}.tmp"
            )
            try:
                network_cache_path.parent.mkdir(parents=True, exist_ok=True)
                if network_cache_path.exists():
                    self._ScheduleCacheCopyRetry(
                        f"network cache is pending database update: {network_cache_path}"
                    )
                    return False

                shutil.copyfile(self.cache_file_path, temporary_path)
                if network_cache_path.exists():
                    self._ScheduleCacheCopyRetry(
                        f"network cache became pending during copy: {network_cache_path}"
                    )
                    return False
                os.replace(temporary_path, network_cache_path)
                self._network_cache_queued = True
            except OSError as error:
                self._ReportFailure(f"network cache copy failed: {error}")
                self._ScheduleCacheCopyRetry(
                    "network cache copy failed; retrying"
                )
                return False
            finally:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError as error:
                    self._ReportFailure(
                        f"temporary network cache cleanup failed: {error}"
                    )
                    raise

        return self._CompleteQueuedCache()

    def _ScheduleCacheCopyRetry(self, reason):
        self.LogToRecords(f"{reason}; retrying in 60 seconds")
        retry_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            seconds=60
        )
        self.next_cache_copy_retry_at = retry_at
        delay = max(
            0,
            (retry_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds(),
        )
        retry_timer = Timer(delay, self._RetryScheduledCacheCopy)
        retry_timer.daemon = True
        self._cache_copy_retry_timer = retry_timer
        try:
            retry_timer.start()
        except RuntimeError as error:
            self._ReportFailure(f"failed to schedule cache retry: {error}")
            raise

    def _RetryScheduledCacheCopy(self):
        with self._cache_copy_guard:
            self._cache_copy_retry_timer = None
            cache_is_queued = self._network_cache_queued
        if cache_is_queued:
            self._CompleteQueuedCache()
        else:
            self.ScheduleLocalCacheCopyToNetwork()

    def _CompleteQueuedCache(self):
        with self._cache_copy_guard:
            if self._closed or not self._network_cache_queued:
                return False
            if self._finishing_cache_queue:
                return False
            try:
                self.cache_file_path.unlink(missing_ok=True)
            except OSError as error:
                self._ReportFailure(f"local cache cleanup failed: {error}")
                self._ScheduleCacheCopyRetry(
                    "local cache cleanup failed; retrying"
                )
                return False
            self._finishing_cache_queue = True

        worker_path = self.network_base_path
        artist = self.artist
        fossa_db = self.fossa_db
        try:
            database_worker = self.__class__(
                LFRoles.DB_ACCESS,
                worker_path,
                artist,
                fossa_db,
            )
        finally:
            self.Destroy()

        database_worker.UpdateDatabaseFromNetworkCache()
        return True

    def UpdateDatabaseFromNetworkCache(self):
        network_cache_path = self.BuildNetworkCachePath()
        with self._database_update_guard:
            if self._closed:
                return False
            if (
                self._database_retry_timer is not None
                and self._database_retry_timer.is_alive()
            ):
                return False
            try:
                updated = self.fossa_db.TryUpdateFromNetworkCache(
                    self.artist,
                    network_cache_path,
                    failure_reporter=self._ReportFailure,
                )
            except (OSError, ValueError):
                self._ScheduleDatabaseUpdateRetry()
                return False

            if not updated:
                self.LogToRecords(
                    "database is busy; retrying update in 60 seconds"
                )
                self._ScheduleDatabaseUpdateRetry()
                return False

        self.Destroy()
        return True

    def _ScheduleDatabaseUpdateRetry(self):
        if (
            self._database_retry_timer is not None
            and self._database_retry_timer.is_alive()
        ):
            return
        retry_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            seconds=60
        )
        self.next_database_retry_at = retry_at
        delay = max(
            0,
            (retry_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds(),
        )
        retry_timer = Timer(delay, self._RetryDatabaseUpdate)
        retry_timer.daemon = True
        self._database_retry_timer = retry_timer
        try:
            retry_timer.start()
        except RuntimeError as error:
            self._ReportFailure(f"failed to schedule database retry: {error}")
            raise

    def _RetryDatabaseUpdate(self):
        with self._database_update_guard:
            self._database_retry_timer = None
        self.UpdateDatabaseFromNetworkCache()

    def _AcquireCachingRole(self):
        if self._closed:
            return False
        if self._cache_role_lock_handle is not None:
            return True

        lock_file = self.cache_role_lock_file_path.open(mode="a+", encoding="utf-8")
        try:
            file_lock.flock(
                lock_file.fileno(), file_lock.LOCK_EX | file_lock.LOCK_NB
            )
        except BlockingIOError:
            lock_file.seek(0)
            current_worker = lock_file.read().strip() or "unknown worker"
            lock_file.close()
            self.role = LFRoles.CONFLICT_RESOLUTION
            conflict = (
                f"cache role held by {current_worker}; "
                f"{self.name} switched to conflict resolution"
            )
            self.LogToRecords(conflict)
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y%m%d_%H%M%S"
            )
            with self.conflicts_file_path.open(mode="a", encoding="utf-8") as file:
                file.write(f"{timestamp}_{conflict}\n")
            return False

        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(self.name)
        lock_file.flush()
        self._cache_role_lock_handle = lock_file
        self.role = LFRoles.CACHING
        return True

    def _ReleaseCachingRole(self):
        lock_file = self._cache_role_lock_handle
        if lock_file is None:
            return
        try:
            lock_file.seek(0)
            lock_file.truncate()
            lock_file.flush()
        finally:
            try:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)
            finally:
                lock_file.close()
                self._cache_role_lock_handle = None

    def CacheData(self):
        if self._network_cache_queued or self._finishing_cache_queue:
            return False
        was_caching = self.role is LFRoles.CACHING
        try:
            acquired = self._AcquireCachingRole()
        except Exception as error:
            self._ReportFailure(f"failed to acquire caching role: {error}")
            raise
        if not acquired:
            return False
        if not was_caching:
            self.LogToRecords("entered caching role")

        temporary_path = self.cache_file_path.with_name(
            f"{self.cache_file_path.name}.tmp"
        )
        write_completed = False
        try:
            with temporary_path.open(mode="w", encoding="utf-8") as file:
                json.dump(vars(self.local_cache_data), file)
            os.replace(temporary_path, self.cache_file_path)
            write_completed = True
        except Exception as error:
            self._ReportFailure(f"failed to write local cache: {error}")
            raise
        finally:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError as error:
                self._ReportFailure(
                    f"temporary local cache cleanup failed: {error}"
                )
                raise
            finally:
                if not write_completed:
                    try:
                        self._ReleaseCachingRole()
                    except Exception as error:
                        self._ReportFailure(
                            f"failed to release caching role after cache write: "
                            f"{error}"
                        )
                        raise
                    self.role = self.initial_role
        return self.ScheduleLocalCacheCopyToNetwork()

    def CanCheckOutBlenderFile(self, filepath):
        if self._closed:
            return False
        return self.fossa_db.CanCheckOutBlenderFile(
            self.artist,
            filepath,
            failure_reporter=self._ReportFailure,
            network_base_path=self.network_base_path,
        )

    def CheckOutBlenderFile(self, filepath):
        if self._closed:
            return False
        try:
            if not self.CanCheckOutBlenderFile(filepath):
                return False
            requested_path = str(Path(filepath).expanduser().resolve())
            self.local_cache_data.current_file = requested_path
            if requested_path not in self.local_cache_data.recent_files:
                self.local_cache_data.recent_files.append(requested_path)
            else:
                self.local_cache_data.recent_files.remove(requested_path)
                self.local_cache_data.recent_files.append(requested_path)

            self.CacheData()
            return True
        finally:
            self.Destroy()

    def CheckInBlenderFile(self):
        self.local_cache_data.current_file = ""
        self.CacheData()
        self.Destroy()
