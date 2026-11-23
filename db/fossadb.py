import json
import os
from pathlib import Path
import re
import uuid

from db import file_lock


class FossaDB:
    PROJECTS_KEY = "__projects__"
    SHOT_NAME_PATTERN = re.compile(r"(?:0[1-9]|[1-9][0-9])[A-Z]")

    def __init__(self, network_base_path):
        self.network_base_path = Path(network_base_path).resolve()
        self.database_file_path = self.network_base_path / "fossa.db"
        self.lock_file_path = self.network_base_path / ".fossa.db.lock"
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
        with self.lock_file_path.open(mode="a+", encoding="utf-8") as lock_file:
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

        with self.database_file_path.open(mode="r", encoding="utf-8") as file:
            database = json.load(file)
        if not isinstance(database, dict):
            raise ValueError("Fossa database must be a JSON object")
        return database

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
        with self.lock_file_path.open(mode="a+", encoding="utf-8") as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                return self._ReadDatabase()
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def GetProjects(self):
        database = self.GetDatabaseSnapshot()
        projects = database.get(self.PROJECTS_KEY, {})
        if not isinstance(projects, dict):
            raise ValueError("Fossa projects must be a JSON object")
        records = []
        for project_id, project in projects.items():
            if not isinstance(project, dict):
                raise ValueError(f"Project {project_id!r} must be a JSON object")
            record = {
                key: value
                for key, value in project.items()
                if key not in {
                    "structure_change_requests",
                    "active_structure_change_request_id",
                }
            }
            active_request_id = project.get("active_structure_change_request_id")
            requests = project.get("structure_change_requests", {})
            if not isinstance(requests, dict):
                raise ValueError(
                    f"Change requests for project {project_id!r} must be a JSON object"
                )
            pending_change = requests.get(active_request_id)
            if (
                isinstance(pending_change, dict)
                and pending_change.get("status") == "pending"
            ):
                record["pending_change"] = {
                    "id": active_request_id,
                    "requester": pending_change.get("requester"),
                    "proposed": pending_change.get("proposed"),
                }
            else:
                record["pending_change"] = None
            record.setdefault("scenes", [])
            record.setdefault("characters", [])
            records.append({"id": project_id, **record})
        return records

    def SaveProject(self, project_id, name, status, directory_path):
        values = (project_id, name, status, directory_path)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError("Project fields must be non-empty strings")

        with self.lock_file_path.open(mode="a+", encoding="utf-8") as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                projects = database.setdefault(self.PROJECTS_KEY, {})
                if not isinstance(projects, dict):
                    raise ValueError("Fossa projects must be a JSON object")
                if project_id in projects:
                    raise ValueError(f"A project named {name!r} already exists")
                projects[project_id] = {
                    "name": name,
                    "status": status,
                    "directory_path": directory_path,
                    "scenes": [],
                    "characters": [],
                    "structure_change_requests": {},
                    "active_structure_change_request_id": None,
                }
                self._WriteDatabase(database)
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    @classmethod
    def _ValidateProjectStructure(cls, structure):
        if not isinstance(structure, dict):
            raise ValueError("Project structure must be a JSON object")
        scenes = structure.get("scenes")
        characters = structure.get("characters")
        if not isinstance(scenes, list) or not isinstance(characters, list):
            raise ValueError("Project scenes and characters must be JSON arrays")

        normalized_scenes = []
        seen_scenes = set()
        for scene in scenes:
            if not isinstance(scene, dict):
                raise ValueError("Each project scene must be a JSON object")
            name = scene.get("name")
            shots = scene.get("shots")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Scene names must be non-empty strings")
            if not isinstance(shots, list):
                raise ValueError(f"Shots for scene {name!r} must be a JSON array")
            name = name.strip()
            normalized_name = name.casefold()
            if normalized_name in seen_scenes:
                raise ValueError(f"Scene {name!r} is duplicated")
            seen_scenes.add(normalized_name)

            normalized_shots = []
            seen_shots = set()
            for shot in shots:
                if (
                    not isinstance(shot, str)
                    or cls.SHOT_NAME_PATTERN.fullmatch(shot) is None
                ):
                    raise ValueError(
                        f"Shot names must be XXY with XX from 01 to 99 and uppercase Y: {shot!r}"
                    )
                if shot in seen_shots:
                    raise ValueError(f"Shot {shot!r} is duplicated in scene {name!r}")
                seen_shots.add(shot)
                normalized_shots.append(shot)
            normalized_scenes.append(
                {"name": name, "shots": normalized_shots}
            )

        normalized_characters = []
        seen_characters = set()
        for character in characters:
            if not isinstance(character, str) or not character.strip():
                raise ValueError("Character names must be non-empty strings")
            character = character.strip()
            normalized_name = character.casefold()
            if normalized_name in seen_characters:
                raise ValueError(f"Character {character!r} is duplicated")
            seen_characters.add(normalized_name)
            normalized_characters.append(character)

        return {
            "scenes": normalized_scenes,
            "characters": normalized_characters,
        }

    def SubmitProjectStructureChange(
        self,
        project_id,
        requester,
        request_id,
        proposed_structure,
        base_structure,
    ):
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (project_id, requester, request_id)
        ):
            raise ValueError("Project, requester, and request IDs must be non-empty")
        proposed_structure = self._ValidateProjectStructure(proposed_structure)
        base_structure = self._ValidateProjectStructure(base_structure)

        with self.lock_file_path.open(mode="a+", encoding="utf-8") as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                projects = database.get(self.PROJECTS_KEY, {})
                if not isinstance(projects, dict):
                    raise ValueError("Fossa projects must be a JSON object")
                project = projects.get(project_id)
                if not isinstance(project, dict):
                    raise ValueError(f"Project {project_id!r} does not exist")
                current_structure = self._ValidateProjectStructure(
                    {
                        "scenes": project.get("scenes", []),
                        "characters": project.get("characters", []),
                    }
                )
                if current_structure != base_structure:
                    raise ValueError(
                        "Project structure changed after this draft was started"
                    )

                requests = project.setdefault("structure_change_requests", {})
                if not isinstance(requests, dict):
                    raise ValueError(
                        f"Change requests for project {project_id!r} must be a JSON object"
                    )
                for completed_id, request in list(requests.items()):
                    if (
                        isinstance(request, dict)
                        and request.get("acknowledged") is True
                    ):
                        del requests[completed_id]

                active_request_id = project.get(
                    "active_structure_change_request_id"
                )
                active_request = requests.get(active_request_id)
                if (
                    isinstance(active_request, dict)
                    and active_request.get("status") == "pending"
                ):
                    raise ValueError(
                        "A project structure change is already awaiting approval"
                    )
                if request_id in requests:
                    raise ValueError(f"Change request {request_id!r} already exists")

                requests[request_id] = {
                    "requester": requester,
                    "status": "pending",
                    "proposed": proposed_structure,
                    "acknowledged": False,
                }
                project["active_structure_change_request_id"] = request_id
                self._WriteDatabase(database)
                return request_id
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def GetPendingProjectStructureChanges(self):
        database = self.GetDatabaseSnapshot()
        projects = database.get(self.PROJECTS_KEY, {})
        if not isinstance(projects, dict):
            raise ValueError("Fossa projects must be a JSON object")
        pending_changes = []
        for project_id, project in projects.items():
            if not isinstance(project, dict):
                raise ValueError(f"Project {project_id!r} must be a JSON object")
            request_id = project.get("active_structure_change_request_id")
            requests = project.get("structure_change_requests", {})
            if not isinstance(requests, dict):
                raise ValueError(
                    f"Change requests for project {project_id!r} must be a JSON object"
                )
            request = requests.get(request_id)
            if not isinstance(request, dict) or request.get("status") != "pending":
                continue
            pending_changes.append(
                {
                    "project_id": project_id,
                    "project_name": project.get("name", project_id),
                    "directory_path": project.get("directory_path", ""),
                    "request_id": request_id,
                    "requester": request.get("requester"),
                    "proposed": self._ValidateProjectStructure(
                        request.get("proposed")
                    ),
                    "current": self._ValidateProjectStructure(
                        {
                            "scenes": project.get("scenes", []),
                            "characters": project.get("characters", []),
                        }
                    ),
                }
            )
        return pending_changes

    def GetProjectStructureChangeResults(self, requester):
        if not isinstance(requester, str) or not requester.strip():
            raise ValueError("Requester must be a non-empty string")
        database = self.GetDatabaseSnapshot()
        projects = database.get(self.PROJECTS_KEY, {})
        if not isinstance(projects, dict):
            raise ValueError("Fossa projects must be a JSON object")
        results = []
        for project_id, project in projects.items():
            if not isinstance(project, dict):
                raise ValueError(f"Project {project_id!r} must be a JSON object")
            requests = project.get("structure_change_requests", {})
            if not isinstance(requests, dict):
                raise ValueError(
                    f"Change requests for project {project_id!r} must be a JSON object"
                )
            for request_id, request in requests.items():
                if (
                    not isinstance(request, dict)
                    or request.get("requester") != requester
                    or request.get("status") not in {"approved", "rejected"}
                    or request.get("acknowledged") is True
                ):
                    continue
                results.append(
                    {
                        "project_id": project_id,
                        "project_name": project.get("name", project_id),
                        "request_id": request_id,
                        "requester": requester,
                        "status": request["status"],
                    }
                )
        return results

    def ResolveProjectStructureChange(
        self, project_id, request_id, reviewer, approved
    ):
        if (
            not isinstance(project_id, str)
            or not project_id.strip()
            or not isinstance(request_id, str)
            or not request_id.strip()
            or not isinstance(reviewer, str)
            or not reviewer.strip()
            or not isinstance(approved, bool)
        ):
            raise ValueError("Invalid project change resolution")

        with self.lock_file_path.open(mode="a+", encoding="utf-8") as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                projects = database.get(self.PROJECTS_KEY, {})
                if not isinstance(projects, dict):
                    raise ValueError("Fossa projects must be a JSON object")
                project = projects.get(project_id)
                if not isinstance(project, dict):
                    raise ValueError(f"Project {project_id!r} does not exist")
                requests = project.get("structure_change_requests", {})
                if not isinstance(requests, dict):
                    raise ValueError(
                        f"Change requests for project {project_id!r} must be a JSON object"
                    )
                request = requests.get(request_id)
                if (
                    not isinstance(request, dict)
                    or project.get("active_structure_change_request_id") != request_id
                    or request.get("status") != "pending"
                ):
                    raise ValueError("This project change is no longer pending")
                if request.get("requester") == reviewer:
                    raise ValueError("The requester cannot approve their own changes")

                status = "approved" if approved else "rejected"
                if approved:
                    proposed = self._ValidateProjectStructure(
                        request.get("proposed")
                    )
                    project["scenes"] = proposed["scenes"]
                    project["characters"] = proposed["characters"]
                request["status"] = status
                request["reviewer"] = reviewer
                project["active_structure_change_request_id"] = None
                self._WriteDatabase(database)
                return status
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def AcknowledgeProjectStructureChange(
        self, project_id, request_id, requester
    ):
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (project_id, request_id, requester)
        ):
            raise ValueError("Project, request, and requester IDs must be non-empty")

        with self.lock_file_path.open(mode="a+", encoding="utf-8") as lock_file:
            file_lock.flock(lock_file.fileno(), file_lock.LOCK_EX)
            try:
                database = self._ReadDatabase()
                projects = database.get(self.PROJECTS_KEY, {})
                if not isinstance(projects, dict):
                    raise ValueError("Fossa projects must be a JSON object")
                project = projects.get(project_id)
                if not isinstance(project, dict):
                    raise ValueError(f"Project {project_id!r} does not exist")
                requests = project.get("structure_change_requests", {})
                request = requests.get(request_id) if isinstance(requests, dict) else None
                if (
                    not isinstance(request, dict)
                    or request.get("requester") != requester
                    or request.get("status") not in {"approved", "rejected"}
                ):
                    raise ValueError("No resolved change request was found")
                request["acknowledged"] = True
                self._WriteDatabase(database)
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

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
                file_lock.flock(
                    lock_file.fileno(), file_lock.LOCK_EX | file_lock.LOCK_NB
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
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def _TryUpdateFromNetworkCache(self, artist, network_cache_path):
        network_cache_path = Path(network_cache_path)
        with self.lock_file_path.open(mode="a+", encoding="utf-8") as lock_file:
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
                database[artist] = cache_data
                self._WriteDatabase(database)
                network_cache_path.unlink()
                return True
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)