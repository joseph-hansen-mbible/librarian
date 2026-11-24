import datetime
import json
from os import path
from pathlib import Path
import sys
from threading import Lock, Timer

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import file_lock
from workers.blender_methods import BlenderWorkerMethods
from workers.cache_methods import CacheWorkerMethods
from workers.models import LFRoles, LocalCacheData, WorkerNames
from workers.project_methods import ProjectWorkerMethods


class FossaWorker(
    BlenderWorkerMethods, CacheWorkerMethods, ProjectWorkerMethods
):
    _active_workers = set()
    _active_workers_lock = Lock()

    def __init__(self, role, network_base_path, artist, fossa_db):
        self.role = role
        self.initial_role = role
        self.artist = artist
        self.network_base_path = Path(network_base_path).resolve()
        self.fossa_db = fossa_db
        self.name = "UNASSIGNED"
        self._closed = False
        self._cache_role_lock_handle = None
        self._cache_copy_retry_timer = None
        self._network_cache_queued = False
        self._finishing_cache_queue = False
        self._cache_copy_guard = Lock()
        self._database_retry_timer = None
        self._database_update_guard = Lock()
        self._blender_watch_timer = None
        self.local_cache_data = LocalCacheData("", [], {}, False, 0)

        try:
            self.AssignName()
            self.EstablishLocalCachePaths()
        except Exception as error:
            self._ReportFailure(f"worker initialization failed: {error}")
            if self.name != "UNASSIGNED":
                try:
                    self._ReleaseWorkerName()
                except Exception as cleanup_error:
                    self._ReportFailure(
                        f"failed to release worker name after initialization error: "
                        f"{cleanup_error}"
                    )
            raise

        worker_descriptions = {
            LFRoles.DB_ACCESS: "database access worker",
            LFRoles.CACHING: "caching worker",
            LFRoles.BLENDER: "Blender file listener",
            LFRoles.CONFLICT_RESOLUTION: "conflict resolution worker",
            LFRoles.RECORDS: "records worker",
            LFRoles.APPROVAL_NEEDED: "project change approval worker",
        }
        description = worker_descriptions.get(role, "worker")
        self.LogToRecords(f"assigned name and started {description}")
        with self._active_workers_lock:
            self._active_workers.add(self)

    @classmethod
    def DestroyAll(cls):
        with cls._active_workers_lock:
            workers = tuple(cls._active_workers)

        failures = []
        for worker in workers:
            try:
                worker.Destroy()
            except Exception as error:
                failures.append(error)

        if failures:
            raise ExceptionGroup(
                "Failed to close one or more Fossa workers", failures
            )

    def _ReportFailure(self, message):
        if self.role is LFRoles.RECORDS or self._closed:
            return False

        reporter = None
        try:
            reporter_path = self.network_base_path
            if not reporter_path.is_relative_to(
                self.fossa_db.network_base_path
            ):
                reporter_path = self.fossa_db.network_base_path
            reporter = FossaWorker(
                LFRoles.RECORDS,
                reporter_path,
                self.artist,
                self.fossa_db,
            )
            return reporter.LogToRecords(f"failure: {message}")
        except Exception:
            return False
        finally:
            if reporter is not None:
                try:
                    reporter.Destroy()
                except Exception:
                    pass

    def AssignName(self):
        worker_id_path = self.BuildLFPath(LFRoles.WORKER_ID)
        worker_id_path.parent.mkdir(parents=True, exist_ok=True)
        file_was_missing = not worker_id_path.exists()
        registry_issue = None

        with worker_id_path.open(mode="a+", encoding="utf-8") as file:
            file_lock.flock(file.fileno(), file_lock.LOCK_EX)
            try:
                file.seek(0)
                existing = file.read()
                existing_upper = existing.upper()
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
                    if existing.strip() and not any(
                        worker_name.name in existing_upper
                        for worker_name in WorkerNames
                    ):
                        registry_issue = (
                            "worker ID registry is malformed; using text fallback"
                        )

                used_names.update(
                    worker_name.name
                    for worker_name in WorkerNames
                    if worker_name.name in existing_upper
                )

                for worker_name in WorkerNames:
                    if (
                        worker_name.name not in used_names
                        and str(worker_name.value) not in used_names
                    ):
                        self.name = worker_name.name
                        file.seek(0, 2)
                        file.write(self.name + "\n")
                        file.flush()
                        break
                else:
                    raise RuntimeError("No available Fossa worker names")
            finally:
                file_lock.flock(file.fileno(), file_lock.LOCK_UN)

        if registry_issue is not None:
            self._ReportFailure(registry_issue)
        if file_was_missing:
            self.LogToRecords("created LF for " + LFRoles.WORKER_ID.value)

    def BuildLFPath(self, lfrole):
        return self.network_base_path / "fossa" / f"{lfrole.value}.flf"

    def BuildNetworkCachePath(self):
        return self.network_base_path / "fossa" / "cache.flf"

    def ReadLF(self, lfrole):
        p = self.BuildLFPath(lfrole)
        try:
            if path.exists(p):
                with Path(p).open(mode="r", encoding="utf-8") as file:
                    return file.read()
            p.parent.mkdir(parents=True, exist_ok=True)
            with Path(p).open(mode="w", encoding="utf-8"):
                pass
            self.LogToRecords("created LF for " + lfrole.value)
            return ""
        except OSError as error:
            self._ReportFailure(f"failed to read or create {p}: {error}")
            raise

    def UpdateLF(self, lfrole, update):
        p = self.BuildLFPath(lfrole)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with Path(p).open(mode="a", encoding="utf-8") as file:
                file.write(update)
        except OSError as error:
            self._ReportFailure(f"failed to update {p}: {error}")
            raise

    def LogToRecords(self, action):
        p = self.BuildLFPath(LFRoles.RECORDS)
        log_time_format = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y%m%d_%H%M%S")
        log_string = "_".join((log_time_format, str(self.name), action)) + "\n"

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open(mode="a", encoding="utf-8") as file:
                file.write(log_string)
            return True
        except OSError as error:
            self._ReportFailure(f"failed to write records log {p}: {error}")
            if self.role is LFRoles.RECORDS:
                return False
            retry_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                seconds=10
            )
            self.next_record_retry_at = retry_at
            delay = max(
                0,
                (
                    retry_at
                    - datetime.datetime.now(datetime.timezone.utc)
                ).total_seconds(),
            )

            retry_timer = Timer(delay, self.LogToRecords, args=(action,))
            retry_timer.daemon = True
            try:
                retry_timer.start()
            except RuntimeError as timer_error:
                self._ReportFailure(
                    f"failed to schedule records retry: {timer_error}"
                )
                return False
            return False

    def _ReleaseWorkerName(self):
        if self.name is None:
            return
        self.LogToRecords(f"releasing worker name {self.name}")
        worker_id_path = self.BuildLFPath(LFRoles.WORKER_ID)
        with worker_id_path.open(mode="a+", encoding="utf-8") as file:
            file_lock.flock(file.fileno(), file_lock.LOCK_EX)
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
                file_lock.flock(file.fileno(), file_lock.LOCK_UN)

    def Destroy(self):
        if self._closed:
            return
        for timer_name in (
            "_cache_copy_retry_timer",
            "_database_retry_timer",
            "_blender_watch_timer",
        ):
            timer = getattr(self, timer_name)
            if timer is not None:
                timer.cancel()
                setattr(self, timer_name, None)
        try:
            self._ReleaseWorkerName()
        except Exception as error:
            self._ReportFailure(f"failed to release worker name: {error}")
            raise
        finally:
            try:
                self._ReleaseCachingRole()
            except Exception as error:
                self._ReportFailure(f"failed to release caching role: {error}")
                raise
            finally:
                self._closed = True
                self.name = None
                self.role = None
                with self._active_workers_lock:
                    self._active_workers.discard(self)
