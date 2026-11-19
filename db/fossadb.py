import fcntl
import json
import os
from pathlib import Path
import uuid


class FossaDB:
    def __init__(self, network_base_path):
        self.network_base_path = Path(network_base_path).resolve()
        self.database_file_path = self.network_base_path / "fossa.db"
        self.lock_file_path = self.network_base_path / ".fossa.db.lock"
        try:
            self.network_base_path.mkdir(parents=True, exist_ok=True)
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
        with self.lock_file_path.open(mode="a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                if self.database_file_path.exists():
                    self._ReadDatabase()
                else:
                    self._WriteDatabase({})
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _ReadDatabase(self):
        if not self.database_file_path.exists():
            return {}

        with self.database_file_path.open(mode="r", encoding="utf-8") as file:
            database = json.load(file)
        if not isinstance(database, dict):
            raise ValueError("Fossa database must be a JSON object")
        return database

    def _WriteDatabase(self, database):
        temporary_path = self.database_file_path.with_name(
            f".fossa.db.{uuid.uuid4().hex}.tmp"
        )
        try:
            with temporary_path.open(mode="x", encoding="utf-8") as file:
                json.dump(database, file)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.database_file_path)
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
        self, artist, filepath, failure_reporter=None, network_base_path=None
    ):
        """Return whether the file is free, reserving it for this artist on success."""
        try:
            return self._TryReserveBlenderFile(artist, filepath)
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

    def _TryReserveBlenderFile(self, artist, filepath):
        artist = str(artist)
        if not artist:
            raise ValueError("Artist must not be empty")
        requested_path = Path(filepath).expanduser().resolve()
        if not str(filepath):
            raise ValueError("Filepath must not be empty")

        with self.lock_file_path.open(mode="a+", encoding="utf-8") as lock_file:
            try:
                fcntl.flock(
                    lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                )
            except BlockingIOError:
                return False

            try:
                database = self._ReadDatabase()
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

                artist_data = database.get(artist, {})
                if not isinstance(artist_data, dict):
                    raise ValueError(
                        f"Cache data for {artist!r} must be a JSON object"
                    )
                artist_data["current_file"] = str(requested_path)
                database[artist] = artist_data
                self._WriteDatabase(database)
                return True
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _TryUpdateFromNetworkCache(self, artist, network_cache_path):
        network_cache_path = Path(network_cache_path)
        with self.lock_file_path.open(mode="a+", encoding="utf-8") as lock_file:
            try:
                fcntl.flock(
                    lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
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
                database[str(artist)] = cache_data
                self._WriteDatabase(database)
                network_cache_path.unlink()
                return True
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)