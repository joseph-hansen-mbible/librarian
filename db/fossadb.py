import datetime
import json
import os
import stat
import sys
import time
from pathlib import Path
import uuid

from db import file_lock
from db.project_methods import ProjectMethods
from db.project_structure import ProjectStructure


class FossaDB(ProjectMethods):
    PROJECTS_KEY = ProjectMethods.PROJECTS_KEY
    PROJECT_STATUS_VALUES = ProjectStructure.PROJECT_STATUS_VALUES
    SCENE_NUMBER_PATTERN = ProjectStructure.SCENE_NUMBER_PATTERN
    SHOT_NAME_PATTERN = ProjectStructure.SHOT_NAME_PATTERN
    REQUIRED_PROJECT_APPROVALS = ProjectStructure.REQUIRED_APPROVALS
    
    def ResetStrandedCheckouts(self):
        """Discard every artist's current and pending Blender checkout."""
        with self._OpenDatabaseLock() as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                cleared_artists = []

                for artist, artist_data in database.items():
                    if artist == "__blender_files__":
                        continue
                    if not isinstance(artist_data, dict):
                        continue

                    had_current_file = bool(artist_data.get("current_file"))
                    had_pending_file = bool(
                        artist_data.get("pending_create_file")
                    )
                    artist_data.pop("current_file", None)
                    artist_data.pop("pending_create_file", None)
                    artist_data.pop("unlock_ssot_request", None)
                    artist_data.pop("ssot_unlock_count", None)
                    artist_data.pop("current_file_checklist", None)

                    if had_current_file or had_pending_file:
                        cleared_artists.append(str(artist))

                files = database.get("__blender_files__", {})
                if isinstance(files, dict):
                    for file_record in files.values():
                        if not isinstance(file_record, dict):
                            continue
                        file_record.pop("unlock_requested", None)
                        file_record.pop("unlock_approval_names", None)
                        file_record.pop("unlock_approvals", None)
                        file_record.pop("unlock_ssot_ready", None)

                self._WriteDatabase(database)

                (self.network_base_path / "fossa" / "cache.flf").unlink(
                    missing_ok=True
                )

                return cleared_artists
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def __init__(self, network_base_path):
        self.network_base_path = Path(network_base_path).resolve()
        self.database_file_path = self.network_base_path / "fossa.db"
        self.lock_file_path = self.network_base_path / ".fossa.db.lock"
        self._storage_diagnostic_reported = False
        try:
            if not self.network_base_path.is_dir():
                raise FileNotFoundError(
                    f"FossaDB network path is unavailable: {self.network_base_path}"
                )
            self._EnsureDatabaseFile()
        except Exception as error:
            self._ReportFailure(f"FossaDB initialization failed: {error}")
            raise

    def _ReportFailure(self, message, network_base_path=None, artist="FossaDB"):
        reporter = None
        try:
            from workers.core import FossaWorker, LFRoles

            reporter_path = Path(
                network_base_path or self.network_base_path
            ).resolve()
            db_root = self.network_base_path.resolve()
            if not reporter_path.is_relative_to(db_root):
                reporter_path = db_root
            reporter = FossaWorker(
                LFRoles.RECORDS,
                reporter_path,
                artist,
                self,
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

    def _EnsureDatabaseFile(self):
        with self._OpenDatabaseLock() as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                if self.database_file_path.exists():
                    self._ReadDatabase()
                else:
                    self._WriteDatabase({})
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def _ReadDatabase(self):
        if not self.database_file_path.exists():
            return {}

        last_error = OSError("Fossa database read retry exhausted")
        for attempt in range(5):
            try:
                with self.database_file_path.open(mode="r", encoding="utf-8") as file:
                    database = json.load(file)
                if not isinstance(database, dict):
                    raise ValueError("Fossa database must be a JSON object")
                return database
            except (OSError, json.JSONDecodeError) as error:
                last_error = error
                if isinstance(error, OSError):
                    if not self._storage_diagnostic_reported:
                        print(
                            "Fossa database storage diagnostic:",
                            self.DiagnoseDatabaseStorage(),
                            file=sys.stderr,
                        )
                        self._storage_diagnostic_reported = True
                if attempt < 4:
                    time.sleep((attempt + 1) * 0.05)
        if isinstance(last_error, json.JSONDecodeError):
            raise last_error
        raise last_error

    def IsConnected(self):
        if not self.network_base_path.is_dir() or not self.database_file_path.is_file():
            return False

        try:
            self._ReadDatabase()
        except (OSError, ValueError):
            return False
        return True

    def GetDatabaseSnapshot(self):
        """Return a consistent snapshot of the database JSON."""
        last_error = OSError("Fossa database lock retry exhausted")
        for attempt in range(5):
            try:
                with self._OpenDatabaseLock() as lock_file:
                    file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
                    try:
                        return self._ReadDatabase()
                    finally:
                        file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)
            except OSError as error:
                last_error = error
                if attempt < 4:
                    time.sleep((attempt + 1) * 0.05)
        raise last_error

    def _OpenDatabaseLock(self):
        last_error = OSError("Fossa database lock open retry exhausted")
        for attempt in range(5):
            try:
                return self.lock_file_path.open(mode="a+", encoding="utf-8")
            except OSError as error:
                last_error = error
                if attempt < 4:
                    time.sleep((attempt + 1) * 0.05)
        raise last_error

    def DiagnoseDatabaseStorage(self):
        """Return a bounded diagnostic snapshot for network-volume failures."""
        diagnostic = {
            "network_path": str(self.network_base_path),
            "database_path": str(self.database_file_path),
            "lock_path": str(self.lock_file_path),
            "network_path_is_dir": self.network_base_path.is_dir(),
            "database_exists": self.database_file_path.exists(),
            "database_is_file": self.database_file_path.is_file(),
        }
        try:
            database_stat = self.database_file_path.stat()
            diagnostic.update({
                "database_size": database_stat.st_size,
                "database_mode": oct(stat.S_IMODE(database_stat.st_mode)),
                "database_uid": database_stat.st_uid,
                "database_gid": database_stat.st_gid,
            })
        except OSError as error:
            diagnostic["database_stat_error"] = (
                f"{type(error).__name__}: errno={error.errno} {error}"
            )

        try:
            with self.database_file_path.open("rb") as file:
                diagnostic["database_read_bytes"] = len(file.read(4096))
        except OSError as error:
            diagnostic["database_read_error"] = (
                f"{type(error).__name__}: errno={error.errno} {error}"
            )

        try:
            with self._OpenDatabaseLock() as lock_file:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
                try:
                    diagnostic["lock_test"] = "ok"
                finally:
                    file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)
        except OSError as error:
            diagnostic["lock_test_error"] = (
                f"{type(error).__name__}: errno={error.errno} {error}"
            )

        temporary_path = self.database_file_path.with_name(
            f".fossa.db.{uuid.uuid4().hex}.diagnostic.tmp"
        )
        try:
            with temporary_path.open("x", encoding="utf-8") as file:
                file.write("{}")
                file.flush()
                os.fsync(file.fileno())
            diagnostic["temporary_write_test"] = "ok"
        except OSError as error:
            diagnostic["temporary_write_error"] = (
                f"{type(error).__name__}: errno={error.errno} {error}"
            )
        finally:
            temporary_path.unlink(missing_ok=True)
        return diagnostic

    def _WriteDatabase(self, database):
        temporary_path = self.database_file_path.with_name(
            f".fossa.db.{uuid.uuid4().hex}.tmp"
        )
        last_error = OSError("Fossa database write retry exhausted")
        try:
            for attempt in range(5):
                try:
                    with temporary_path.open(mode="x", encoding="utf-8") as file:
                        json.dump(database, file)
                        file.flush()
                        os.fsync(file.fileno())
                    os.replace(temporary_path, self.database_file_path)
                    return
                except OSError as error:
                    last_error = error
                    if attempt < 4:
                        time.sleep((attempt + 1) * 0.05)
                    else:
                        break
            raise last_error
        finally:
            temporary_path.unlink(missing_ok=True)

    def TryUpdateFromNetworkCache(
        self, artist, network_cache_path, failure_reporter=None
    ):
        try:
            return self._TryUpdateFromNetworkCache(artist, network_cache_path)
        except Exception as error:
            message = (
                f"FossaDB cache update failed: "
                f"{type(error).__name__}: {error}"
            )
            if failure_reporter is None:
                self._ReportFailure(
                    message,
                    network_base_path=Path(network_cache_path).parent.parent,
                    artist=artist,
                )
            else:
                try:
                    failure_reporter(message)
                except Exception:
                    pass
            raise

    def CanCheckOutBlenderFile(
        self,
        artist,
        filepath,
        failure_reporter=None,
        network_base_path=None,
        allow_pending_create=False,
    ):
        """Return whether the file is free, reserving it for this artist on success."""
        try:
            return self._TryReserveBlenderFile(
                artist,
                filepath,
                allow_pending_create=allow_pending_create,
            )
        except Exception as error:
            message = (
                f"Blender file checkout check failed: "
                f"{type(error).__name__}: {error}"
            )
            if failure_reporter is None:
                self._ReportFailure(
                    message,
                    network_base_path=network_base_path,
                    artist=artist,
                )
            else:
                try:
                    failure_reporter(message)
                except Exception:
                    pass
            raise

    def MarkBlenderFileCreationPending(self, artist, filepath):
        artist = str(artist)
        if not artist:
            raise ValueError("Artist must not be empty")
        if not str(filepath):
            raise ValueError("Filepath must not be empty")
        requested_path = str(Path(filepath).expanduser().resolve())

        with self._OpenDatabaseLock() as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                artist_data = database.get(artist, {})
                if not isinstance(artist_data, dict):
                    raise ValueError(
                        f"Cache data for {artist!r} must be a JSON object"
                    )

                current_file = artist_data.get("current_file")
                if current_file not in (None, ""):
                    if not isinstance(current_file, str):
                        raise ValueError(
                            f"Current file for {artist!r} must be a string"
                        )
                    # A crashed or interrupted Blender session can leave this state
                    # behind. Release the stale checkout so the requested file can
                    # proceed through the normal pending-creation/checkout flow.
                    artist_data["current_file"] = ""

                pending_file = artist_data.get("pending_create_file")
                if pending_file not in (None, "", requested_path):
                    raise RuntimeError(
                        f"{artist!r} already has a pending Blender file creation"
                    )
                artist_data["pending_create_file"] = requested_path
                database[artist] = artist_data
                self._WriteDatabase(database)
                return requested_path
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def ClearBlenderFileCreationPending(self, artist, filepath):
        artist = str(artist)
        requested_path = str(Path(filepath).expanduser().resolve())

        with self._OpenDatabaseLock() as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                artist_data = database.get(artist)
                if not isinstance(artist_data, dict):
                    return False
                if artist_data.get("pending_create_file") != requested_path:
                    return False
                del artist_data["pending_create_file"]
                self._WriteDatabase(database)
                return True
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def UpdateBlenderFileChecklist(self, artist, filepath, checklist):
        artist = str(artist)
        if not artist:
            raise ValueError("Artist must not be empty")
        requested_path = str(Path(filepath).expanduser().resolve())
        if not isinstance(checklist, dict):
            raise ValueError("Blender file checklist must be a JSON object")
        if any(
            not isinstance(key, str) or not isinstance(value, bool)
            for key, value in checklist.items()
        ):
            raise ValueError(
                "Blender file checklist keys must be text and values must be booleans"
            )

        with self._OpenDatabaseLock() as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                files = database.setdefault("__blender_files__", {})
                if not isinstance(files, dict):
                    raise ValueError("Blender file index must be a JSON object")
                file_record = files.get(requested_path, {})
                if not isinstance(file_record, dict):
                    raise ValueError(
                        f"Blender file metadata for {requested_path!r} "
                        "must be a JSON object"
                    )
                file_record["checklist"] = dict(checklist)
                files[requested_path] = file_record

                artist_data = database.get(artist)
                if isinstance(artist_data, dict):
                    artist_data["current_file_checklist"] = dict(checklist)
                self._WriteDatabase(database)
                return True
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def UpdateBlenderFileNotes(self, artist, filepath, notes):
        artist = str(artist)
        requested_path = str(Path(filepath).expanduser().resolve())
        if not artist:
            raise ValueError("Artist must not be empty")
        if not isinstance(notes, str):
            raise ValueError("Blender file notes must be text")

        with self._OpenDatabaseLock() as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                files = database.setdefault("__blender_files__", {})
                if not isinstance(files, dict):
                    raise ValueError("Blender file index must be a JSON object")
                file_record = files.get(requested_path)
                if not isinstance(file_record, dict):
                    raise ValueError(
                        f"Blender file metadata for {requested_path!r} "
                        "must be a JSON object"
                    )
                file_record["notes"] = notes
                files[requested_path] = file_record

                artist_data = database.get(artist)
                if isinstance(artist_data, dict):
                    artist_data["current_file_notes"] = notes
                self._WriteDatabase(database)
                return True
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def RequestSSOTUnlock(self, artist, filepath):
        artist = str(artist)
        requested_path = str(Path(filepath).expanduser().resolve())
        if not artist:
            raise ValueError("Artist must not be empty")

        with self._OpenDatabaseLock() as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                artist_data = database.get(artist)
                if not isinstance(artist_data, dict):
                    raise ValueError(f"Unknown artist {artist!r}")
                if artist_data.get("current_file") != requested_path:
                    raise ValueError("Only the checked-out artist can request unlock")

                files = database.setdefault("__blender_files__", {})
                if not isinstance(files, dict):
                    raise ValueError("Blender file index must be a JSON object")
                file_record = files.get(requested_path, {})
                if not isinstance(file_record, dict):
                    file_record = {}
                checklist = file_record.get("checklist", {})
                if not isinstance(checklist, dict) or not checklist:
                    raise ValueError("This Blender file has no SSOT checklist")
                if any(value is not True for value in checklist.values()):
                    raise ValueError("The SSOT checklist must be complete")

                file_record["unlock_approval_names"] = []
                file_record["unlock_approvals"] = 0
                file_record["unlock_requested"] = True
                file_record["unlock_rejection_names"] = []
                file_record["unlock_approval_log"] = []
                file_record["unlock_rejection_log"] = []
                files[requested_path] = file_record
                artist_data["unlock_ssot_request"] = True
                artist_data["ssot_unlock_count"] = 0
                database[artist] = artist_data
                self._WriteDatabase(database)
                return True
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def RejectSSOTUnlock(self, artist, filepath, reviewer):
        artist = str(artist)
        reviewer = str(reviewer)
        requested_path = str(Path(filepath).expanduser().resolve())
        if not reviewer:
            raise ValueError("Reviewer must not be empty")
        if reviewer == artist:
            raise ValueError("The checked-out artist cannot reject their own unlock")

        with self._OpenDatabaseLock() as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                files = database.setdefault("__blender_files__", {})
                if not isinstance(files, dict):
                    raise ValueError("Blender file index must be a JSON object")
                file_record = files.get(requested_path, {})
                if not isinstance(file_record, dict):
                    raise ValueError("Unknown Blender file")
                if not file_record.get("unlock_requested", False):
                    raise ValueError("No SSOT unlock has been requested")

                rejections = file_record.get("unlock_rejection_names", [])
                if not isinstance(rejections, list):
                    rejections = []
                rejections = [name for name in rejections if isinstance(name, str)]
                if reviewer not in rejections:
                    rejections.append(reviewer)
                rejection_log = file_record.get("unlock_rejection_log", [])
                if not isinstance(rejection_log, list):
                    rejection_log = []
                rejection_log.append(
                    {
                        "reviewer": reviewer,
                        "decision": "rejected",
                        "timestamp": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                    }
                )
                file_record["unlock_rejection_names"] = rejections
                file_record["unlock_rejection_log"] = rejection_log
                file_record["unlock_requested"] = False
                file_record["unlock_approval_names"] = []
                file_record["unlock_approvals"] = 0
                files[requested_path] = file_record

                owner_data = database.get(artist)
                if isinstance(owner_data, dict):
                    owner_data["unlock_ssot_request"] = False
                    owner_data["ssot_unlock_count"] = 0
                    database[artist] = owner_data
                self._WriteDatabase(database)
                return True
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def ApproveSSOTUnlock(self, artist, filepath, reviewer):
        artist = str(artist)
        reviewer = str(reviewer)
        requested_path = str(Path(filepath).expanduser().resolve())
        if not reviewer:
            raise ValueError("Reviewer must not be empty")
        if reviewer == artist:
            raise ValueError("The checked-out artist cannot approve their own unlock")

        with self._OpenDatabaseLock() as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                files = database.setdefault("__blender_files__", {})
                if not isinstance(files, dict):
                    raise ValueError("Blender file index must be a JSON object")
                file_record = files.get(requested_path, {})
                if not isinstance(file_record, dict):
                    raise ValueError("Unknown Blender file")
                if not file_record.get("unlock_requested", False):
                    raise ValueError("No SSOT unlock has been requested")

                approvals = file_record.get("unlock_approval_names", [])
                if not isinstance(approvals, list):
                    approvals = []
                approvals = [name for name in approvals if isinstance(name, str)]
                if len(approvals) >= self.REQUIRED_PROJECT_APPROVALS:
                    raise ValueError("This SSOT unlock already has two approvals")
                if reviewer in approvals:
                    raise ValueError(f"{reviewer} has already approved this unlock")

                approvals.append(reviewer)
                approvals = approvals[:self.REQUIRED_PROJECT_APPROVALS]
                approval_log = file_record.get("unlock_approval_log", [])
                if not isinstance(approval_log, list):
                    approval_log = []
                approval_log.append(
                    {
                        "reviewer": reviewer,
                        "decision": "approved",
                        "timestamp": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                    }
                )
                file_record["unlock_approval_log"] = approval_log
                approval_count = len(approvals)
                file_record["unlock_approval_names"] = approvals
                file_record["unlock_approvals"] = approval_count
                if approval_count >= self.REQUIRED_PROJECT_APPROVALS:
                    file_record["unlock_ssot_ready"] = True
                    file_record["status"] = "ssot"
                files[requested_path] = file_record

                owner_data = database.get(artist)
                if isinstance(owner_data, dict):
                    owner_data["ssot_unlock_count"] = approval_count
                    database[artist] = owner_data
                self._WriteDatabase(database)
                return approval_count
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def RecordBlenderFileUse(self, artist, filepath, metadata):
        artist = str(artist)
        if not artist:
            raise ValueError("Artist must not be empty")
        if not str(filepath):
            raise ValueError("Filepath must not be empty")
        if not isinstance(metadata, dict):
            raise ValueError("Blender file metadata must be a JSON object")
        requested_path = str(Path(filepath).expanduser().resolve())
        opened_at = datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds"
        )

        with self._OpenDatabaseLock() as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                files = database.setdefault("__blender_files__", {})
                if not isinstance(files, dict):
                    raise ValueError("Blender file index must be a JSON object")
                file_record = files.get(requested_path, {})
                if not isinstance(file_record, dict):
                    raise ValueError(
                        f"Blender file metadata for {requested_path!r} "
                        "must be a JSON object"
                    )

                opened_by = file_record.get("last_opened_by_artist", {})
                if not isinstance(opened_by, dict):
                    raise ValueError(
                        f"Open history for {requested_path!r} must be a JSON object"
                    )
                file_record.update(metadata)
                opened_by[artist] = opened_at
                file_record["last_opened_by_artist"] = opened_by
                files[requested_path] = file_record
                self._WriteDatabase(database)
                return opened_at
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def _TryReserveBlenderFile(
        self,
        artist,
        filepath,
        allow_pending_create=False,
    ):
        artist = str(artist)
        if not artist:
            raise ValueError("Artist must not be empty")
        requested_path = Path(filepath).expanduser().resolve()
        if not str(filepath):
            raise ValueError("Filepath must not be empty")

        with self._OpenDatabaseLock() as lock_file:
            try:
                file_lock.flock(
                    lock_file.fileno(), file_lock.LOCK_EX | file_lock.LOCK_NB
                )
            except BlockingIOError:
                return False

            try:
                database = self._ReadDatabase()
                artist_data = database.get(artist, {})
                if not isinstance(artist_data, dict):
                    raise ValueError(
                        f"Cache data for {artist!r} must be a JSON object"
                    )
                current_file = artist_data.get("current_file")
                if current_file not in (None, ""):
                    if not isinstance(current_file, str):
                        raise ValueError(
                            f"Current file for {artist!r} must be a string"
                        )
                    return False
                pending_file = artist_data.get("pending_create_file")
                if pending_file not in (None, ""):
                    if not isinstance(pending_file, str):
                        raise ValueError(
                            f"Pending file for {artist!r} must be a string"
                        )
                    if (
                        Path(pending_file).expanduser().resolve()
                        != requested_path
                    ):
                        return False
                    if not allow_pending_create:
                        return False
                elif allow_pending_create:
                    return False

                for owner, cache_data in database.items():
                    if not isinstance(cache_data, dict):
                        raise ValueError(
                            f"Cache data for {owner!r} must be a JSON object"
                        )
                    if owner == artist:
                        continue

                    current_file = cache_data.get("current_file")
                    if current_file in (None, ""):
                        continue
                    if not isinstance(current_file, str):
                        raise ValueError(
                            f"Current file for {owner!r} must be a string"
                        )
                    if Path(current_file).expanduser().resolve() == requested_path:
                        return False

                artist_data["current_file"] = str(requested_path)
                if artist_data.get("pending_create_file") == str(requested_path):
                    artist_data.pop("pending_create_file", None)
                database[artist] = artist_data
                self._WriteDatabase(database)
                return True
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def _TryUpdateFromNetworkCache(self, artist, network_cache_path):
        network_cache_path = Path(network_cache_path)
        with self._OpenDatabaseLock() as lock_file:
            try:
                file_lock.flock(
                    lock_file.fileno(), file_lock.LOCK_EX | file_lock.LOCK_NB
                )
            except BlockingIOError:
                return False

            try:
                if not network_cache_path.exists():
                    return True

                with network_cache_path.open(mode="r", encoding="utf-8") as file:
                    cache_data = json.load(file)
                if not isinstance(cache_data, dict):
                    raise ValueError("Network cache must be a JSON object")

                database = self._ReadDatabase()
                artist = str(artist)
                artist_data = database.get(artist, {})
                if not isinstance(artist_data, dict):
                    raise ValueError(
                        f"Cache data for {artist!r} must be a JSON object"
                    )

                if cache_data.get("blender_open") is False:
                    existing_checklist = artist_data.get(
                        "current_file_checklist",
                        {},
                    )
                    incoming_checklist = cache_data.get(
                        "current_file_checklist",
                        {},
                    )
                    if not isinstance(incoming_checklist, dict):
                        incoming_checklist = {}
                    if not incoming_checklist and isinstance(existing_checklist, dict):
                        incoming_checklist = existing_checklist
                    cache_data["current_file_checklist"] = dict(
                        incoming_checklist
                    )

                    incoming_notes = cache_data.get(
                        "current_file_notes",
                        "",
                    )
                    if not isinstance(incoming_notes, str):
                        incoming_notes = ""
                    if not incoming_notes:
                        incoming_notes = artist_data.get(
                            "current_file_notes",
                            "",
                        )
                    if not isinstance(incoming_notes, str):
                        incoming_notes = ""
                    cache_data["current_file_notes"] = incoming_notes

                    closing_file = artist_data.get("current_file", "")
                    if isinstance(closing_file, str) and closing_file:
                        files = database.setdefault("__blender_files__", {})
                        if isinstance(files, dict):
                            closing_record = files.get(closing_file)
                            if isinstance(closing_record, dict):
                                closing_record["checklist"] = dict(
                                    incoming_checklist
                                )
                                closing_record["notes"] = incoming_notes

                    cache_data["unlock_ssot_request"] = bool(
                        artist_data.get("unlock_ssot_request", False)
                    )
                    unlock_count = artist_data.get("ssot_unlock_count", 0)
                    if not isinstance(unlock_count, int):
                        unlock_count = 0
                    cache_data["ssot_unlock_count"] = unlock_count

                increment_from = str(cache_data.get("increment_from", "") or "")
                increment_to = str(cache_data.get("increment_to", "") or "")
                if increment_from or increment_to:
                    increment_from = str(
                        Path(increment_from).expanduser().resolve()
                    ) if increment_from else ""
                    increment_to = str(
                        Path(increment_to).expanduser().resolve()
                    ) if increment_to else ""
                    if (
                        not increment_from
                        or not increment_to
                        or increment_from == increment_to
                        or not Path(increment_to).is_file()
                    ):
                        raise ValueError(
                            "Invalid incremental Blender save cache"
                        )
                    if artist_data.get("current_file") != increment_from:
                        raise ValueError(
                            "Incremental save no longer matches the active checkout"
                        )

                    files = database.setdefault("__blender_files__", {})
                    if not isinstance(files, dict):
                        raise ValueError(
                            "Blender file index must be a JSON object"
                        )
                    old_record = files.get(increment_from, {})
                    if not isinstance(old_record, dict):
                        old_record = {}
                    new_record = dict(old_record)
                    checklist = cache_data.get("current_file_checklist", {})
                    if not isinstance(checklist, dict):
                        checklist = {}
                    notes = cache_data.get("current_file_notes", "")
                    if not isinstance(notes, str):
                        notes = ""
                    new_record["checklist"] = dict(checklist)
                    new_record["notes"] = notes
                    new_record["version"] = int(
                        Path(increment_to).stem.rsplit("_", 1)[-1]
                    ) if Path(increment_to).stem.rsplit("_", 1)[-1].isdigit() else old_record.get("version", 1)
                    new_record["filepath"] = increment_to
                    opened_by = new_record.get("last_opened_by_artist", {})
                    if not isinstance(opened_by, dict):
                        opened_by = {}
                    opened_by[artist] = datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(timespec="seconds")
                    new_record["last_opened_by_artist"] = opened_by
                    files[increment_to] = new_record
                    artist_data["current_file"] = increment_to
                    artist_data["current_file_checklist"] = dict(checklist)
                    artist_data["current_file_notes"] = notes

                existing_recent_files = artist_data.get("recent_files", [])
                if not isinstance(existing_recent_files, list):
                    raise ValueError(
                        f"Recent files for {artist!r} must be a JSON array"
                    )
                incoming_recent_files = cache_data.get("recent_files", [])
                if not isinstance(incoming_recent_files, list):
                    raise ValueError(
                        f"Recent files for {artist!r} must be a JSON array"
                    )

                recent_files = []
                for filepath in (
                    existing_recent_files + incoming_recent_files
                ):
                    if filepath in recent_files:
                        recent_files.remove(filepath)
                    recent_files.append(filepath)
                cache_data["recent_files"] = recent_files
                if "pending_create_file" in artist_data:
                    cache_data["pending_create_file"] = artist_data[
                        "pending_create_file"
                    ]
                checklist = cache_data.get("current_file_checklist", {})
                if not isinstance(checklist, dict):
                    checklist = {}
                notes = cache_data.get("current_file_notes", "")
                if not isinstance(notes, str):
                    notes = ""
                current_file = cache_data.get("current_file", "")
                if isinstance(current_file, str) and current_file:
                    files = database.setdefault("__blender_files__", {})
                    if isinstance(files, dict):
                        file_record = files.get(
                            str(Path(current_file).expanduser().resolve())
                        )
                        if isinstance(file_record, dict):
                            file_record["checklist"] = dict(checklist)
                            file_record["notes"] = notes
                    artist_data["current_file_checklist"] = dict(checklist)
                    artist_data["current_file_notes"] = notes
                elif current_file == "":
                    artist_data["current_file"] = ""
                    artist_data.pop("pending_create_file", None)
                    artist_data["current_file_notes"] = ""

                cache_data.pop("increment_from", None)
                cache_data.pop("increment_to", None)
                if "pending_create_file" in artist_data:
                    cache_data["pending_create_file"] = artist_data[
                        "pending_create_file"
                    ]
                database[artist] = cache_data
                self._WriteDatabase(database)
                network_cache_path.unlink()
                return True
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)
