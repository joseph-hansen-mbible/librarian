from enum import Enum
import datetime
import fcntl
import os
from pathlib import Path
import json
from os import path
import shutil
import sys
from threading import Lock, Timer
from platformdirs import PlatformDirs

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import fossadb

class WorkerNames(Enum):
    PROKOKIEV = 0
    RACHMANINOFF = 1
    TCHAIKOVSKY = 2
    RIMSKY_KORSAKOV = 3
    FAURE = 4
    DEBUSSY = 5
    LIZST = 6
    SCHUMANN = 7
    SHOSTAKOVICH = 8
    CHOPIN = 9
    RAVEL = 10
    BACH = 11
    SOULJA_BOY = 12
    FETTY_WAP = 13
    METRO_BOOMIN = 14
    LIL_UZI_VERT = 15
    DON_TOLLIVER = 16

class LFRoles(Enum):
    DB_ACCESS = "db_access"
    WORKER_ID = "worker_id"
    CACHING = "caching"
    CONFLICT_RESOLUTION = "conflict_resolution"
    RECORDS = "records"

class LocalCacheData():
    def __init__(self, current_file="", recent_files=[], current_file_checklist={}, unlock_ssot_request=False, ssot_unlock_count=0):
        self.current_file = current_file
        self.recent_files = recent_files
        self.current_file_checklist = current_file_checklist
        self.unlock_ssot_request = unlock_ssot_request
        self.ssot_unlock_count = ssot_unlock_count

class FossaWorker():
    def __init__(self, role, network_base_path, artist, fossa_db,
                 worker_description="worker"):
        self.role = role
        self.initial_role = role
        self.artist = artist
        self.worker_description = worker_description
        self.network_base_path = Path(network_base_path).resolve()
        self.fossa_db = fossa_db
        if not self.network_base_path.is_relative_to(self.fossa_db.network_base_path):
            raise ValueError(
                "The worker network path must be inside the FossaDB network path"
            )
        self.name = "UNASSIGNED"
        self.local_cache_data = LocalCacheData("", [], {}, False, 0)
        self._closed = False
        self._cache_role_lock_handle = None
        self._cache_copy_retry_timer = None
        self._network_cache_queued = False
        self._finishing_cache_queue = False
        self._cache_copy_guard = Lock()
        self._database_retry_timer = None
        self._database_update_guard = Lock()
        self.AssignName()
        self.EstablishLocalCachePaths()
        self.LogToRecords(
            f"assigned name and started {self.worker_description}"
        )
    
    def AssignName(self):
        worker_id_path = self.BuildLFPath(LFRoles.WORKER_ID)
        worker_id_path.parent.mkdir(parents=True, exist_ok=True)
        file_was_missing = not worker_id_path.exists()

        with worker_id_path.open(mode="a+", encoding="utf-8") as file:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            try:
                file.seek(0)
                existing = file.read()
                used_names = set()
                try:
                    parsed = json.loads(existing)
                    if isinstance(parsed, dict):
                        parsed = parsed.values()
                    if isinstance(parsed, (list, tuple, set)):
                        used_names.update(
                            str(item).strip().upper() for item in parsed
                        )
                except (json.JSONDecodeError, TypeError):
                    pass

                existing_upper = existing.upper()
                used_names.update(
                    worker_name.name
                    for worker_name in WorkerNames
                    if worker_name.name in existing_upper
                )

                for worker_name in WorkerNames:
                    if (worker_name.name not in used_names
                            and str(worker_name.value) not in used_names):
                        self.name = worker_name.name
                        file.seek(0, 2)
                        file.write(self.name + "\n")
                        file.flush()
                        break
                else:
                    raise RuntimeError("No available Fossa worker names")
            finally:
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)

        if file_was_missing:
            self.LogToRecords("created LF for " + LFRoles.WORKER_ID.value)
    
    def BuildLFPath(self, lfrole):
        return self.network_base_path / "fossa" / f"{lfrole.value}.flf"

    def BuildNetworkCachePath(self):
        return self.network_base_path / "fossa" / "cache.flf"
        
    def ReadLF(self, lfrole):
        # reading LFs is always in scope, no scope check
        p = self.BuildLFPath(lfrole)
        if path.exists(p):
            with Path(p).open(mode="r", encoding="utf-8") as file:
                content = file.read()
                return content
        else:
            # create the LF
            p.parent.mkdir(parents=True, exist_ok=True)
            with Path(p).open(mode="w", encoding="utf-8") as file:
                pass
            # store it in records!!!
            self.LogToRecords("created LF for " + lfrole.value)
            return ''
        
    def UpdateLF(self, lfrole, update):
        p = self.BuildLFPath(lfrole)
        p.parent.mkdir(parents=True, exist_ok=True)
        with Path(p).open(mode="a", encoding="utf-8") as file:
            file.write(update)
            
    def LogToRecords(self, action):
        p = self.BuildLFPath(LFRoles.RECORDS)
        log_time_format = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_string = "_".join((log_time_format, str(self.name), action)) + "\n"
        p.parent.mkdir(parents=True, exist_ok=True)

        try:
            with p.open(mode="a", encoding="utf-8") as file:
                file.write(log_string)
            return True
        except OSError:
            retry_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=10)
            self.next_record_retry_at = retry_at
            delay = max(0, (retry_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds())

            retry_timer = Timer(delay, self.LogToRecords, args=(action,))
            retry_timer.daemon = True
            retry_timer.start()
            return False
        
    def EstablishLocalCachePaths(self):
        # every worker has one local cache file that stores: 
        # what blender file is currently checked out,
        # recent blender files,
        # the current checklist for the current file OR the UAs for the current file
        
        dirs = PlatformDirs("Fossa", "Joseph Hansen", ensure_exists=True)
        appdata = dirs.user_data_path
        self.appdata_path = appdata
        self.cache_file_path = appdata / f"{self.name}_cache.flf"
        self.cache_role_lock_file_path = appdata / f"{LFRoles.CACHING.value}.flf"
        self.conflicts_file_path = appdata / "Conflicts.flf"
    
    def ScheduleLocalCacheCopyToNetwork(self):
        # A present network cache is queued for the database worker; never overwrite it.
        network_cache_path = self.BuildNetworkCachePath()
        with self._cache_copy_guard:
            if self._closed:
                return False
            if (self._cache_copy_retry_timer is not None
                    and self._cache_copy_retry_timer.is_alive()):
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
                self._ScheduleCacheCopyRetry(
                    f"network cache copy failed: {error}"
                )
                return False
            finally:
                temporary_path.unlink(missing_ok=True)

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
        retry_timer.start()

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
                self._ScheduleCacheCopyRetry(
                    f"local cache cleanup failed: {error}"
                )
                return False
            self._finishing_cache_queue = True

        worker_path = self.network_base_path
        artist = self.artist
        fossa_db = self.fossa_db
        try:
            database_worker = FossaWorker(
                LFRoles.DB_ACCESS,
                worker_path,
                artist,
                fossa_db,
                worker_description="database update worker",
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
            if (self._database_retry_timer is not None
                    and self._database_retry_timer.is_alive()):
                return False
            try:
                updated = self.fossa_db.TryUpdateFromNetworkCache(
                    self.artist, network_cache_path
                )
            except (OSError, ValueError) as error:
                self.LogToRecords(
                    f"database update failed; retrying in 60 seconds: {error}"
                )
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
        if (self._database_retry_timer is not None
                and self._database_retry_timer.is_alive()):
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
        retry_timer.start()

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
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
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
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            finally:
                lock_file.close()
                self._cache_role_lock_handle = None

    def _ReleaseWorkerName(self):
        if self.name is None:
            return
        worker_id_path = self.BuildLFPath(LFRoles.WORKER_ID)
        with worker_id_path.open(mode="a+", encoding="utf-8") as file:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            try:
                file.seek(0)
                existing = file.read().upper()
                active_names = {
                    worker_name.name
                    for worker_name in WorkerNames
                    if worker_name.name in existing
                    and worker_name.name != self.name
                }
                file.seek(0)
                file.truncate()
                file.writelines(
                    f"{worker_name.name}\n"
                    for worker_name in WorkerNames
                    if worker_name.name in active_names
                )
                file.flush()
            finally:
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)

    def Destroy(self):
        if self._closed:
            return
        for timer_name in ("_cache_copy_retry_timer", "_database_retry_timer"):
            timer = getattr(self, timer_name)
            if timer is not None:
                timer.cancel()
                setattr(self, timer_name, None)
        try:
            self._ReleaseWorkerName()
        finally:
            try:
                self._ReleaseCachingRole()
            finally:
                self._closed = True
                self.name = None
                self.role = None
    
    def CacheData(self):
        if self._network_cache_queued or self._finishing_cache_queue:
            return False
        was_caching = self.role is LFRoles.CACHING
        if not self._AcquireCachingRole():
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
        finally:
            try:
                temporary_path.unlink(missing_ok=True)
            finally:
                if not write_completed:
                    self._ReleaseCachingRole()
                    self.role = self.initial_role
        return self.ScheduleLocalCacheCopyToNetwork()
        
        
    def CheckOutBlenderFile(self, filepath):
        pass
