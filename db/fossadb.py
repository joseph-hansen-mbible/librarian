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
        self.network_base_path.mkdir(parents=True, exist_ok=True)
        self._EnsureDatabaseFile()

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

    def TryUpdateFromNetworkCache(self, artist, network_cache_path):
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