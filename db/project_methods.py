import datetime

from db.project_structure import ProjectStructure
from db import file_lock


class ProjectMethods:
    PROJECTS_KEY = "__projects__"
    PROJECT_STATUS_VALUES = ProjectStructure.PROJECT_STATUS_VALUES
    REQUIRED_PROJECT_APPROVALS = ProjectStructure.REQUIRED_APPROVALS

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
            requests = project.get("structure_change_requests", {})
            if not isinstance(requests, dict):
                raise ValueError(
                    f"Change requests for project {project_id!r} must be a JSON object"
                )
            request_id = project.get("active_structure_change_request_id")
            pending_change = requests.get(request_id)
            if (
                isinstance(pending_change, dict)
                and pending_change.get("status") == "pending"
            ):
                record["pending_change"] = {
                    "id": request_id,
                    "requester": pending_change.get("requester"),
                    "proposed": pending_change.get("proposed"),
                    "approvals": ProjectStructure.GetApprovals(pending_change),
                    "rejections": list(pending_change.get("rejections", [])),
                    "approval_log": list(pending_change.get("approval_log", [])),
                    "rejection_log": list(pending_change.get("rejection_log", [])),
                    "required_approvals": self.REQUIRED_PROJECT_APPROVALS,
                }
            else:
                record["pending_change"] = None
            record.update(
                ProjectStructure.Normalize(
                    {
                        "scenes": project.get("scenes", []),
                        "characters": project.get("characters", []),
                        "props": project.get("props", []),
                        "status": project.get("status", "Not Started"),
                        "project_code": project.get("project_code", ""),
                    }
                )
            )
            records.append({"id": project_id, **record})
        return records

    def SaveProject(
        self,
        project_id,
        name,
        status,
        directory_path,
        project_code="",
    ):
        values = (project_id, name, status, directory_path)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError("Project fields must be non-empty strings")
        if status not in self.PROJECT_STATUS_VALUES:
            raise ValueError(f"Unknown project status {status!r}")
        ProjectStructure.ValidateProjectCode(project_code, allow_empty=False)

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
                    "project_code": project_code,
                    "scenes": [],
                    "characters": [],
                    "props": [],
                    "structure_change_requests": {},
                    "active_structure_change_request_id": None,
                }
                self._WriteDatabase(database)
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    @classmethod
    def _ValidateProjectStructure(cls, structure):
        return ProjectStructure.Validate(structure)

    @classmethod
    def NormalizeProjectStructure(
        cls,
        structure,
        default_status="Not Started",
        default_project_code="",
    ):
        return ProjectStructure.Normalize(
            structure,
            default_status,
            default_project_code,
        )

    @staticmethod
    def _GetProjectChangeApprovals(request):
        return ProjectStructure.GetApprovals(request)

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
        proposed_structure = ProjectStructure.Validate(proposed_structure)
        base_structure = ProjectStructure.Validate(base_structure)
        ProjectStructure.ValidateProjectCode(
            proposed_structure["project_code"],
            allow_empty=False,
        )

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
                current_structure = ProjectStructure.Normalize(
                    {
                        "scenes": project.get("scenes", []),
                        "characters": project.get("characters", []),
                        "props": project.get("props", []),
                        "status": project.get("status", "Not Started"),
                        "project_code": project.get("project_code", ""),
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
                    "approvals": [],
                    "rejections": [],
                    "approval_log": [],
                    "rejection_log": [],
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
            current_status = project.get("status", "Not Started")
            pending_changes.append(
                {
                    "project_id": project_id,
                    "project_name": project.get("name", project_id),
                    "directory_path": project.get("directory_path", ""),
                    "request_id": request_id,
                    "requester": request.get("requester"),
                    "approvals": ProjectStructure.GetApprovals(request),
                    "rejections": list(request.get("rejections", [])),
                    "approval_log": list(request.get("approval_log", [])),
                    "rejection_log": list(request.get("rejection_log", [])),
                    "required_approvals": self.REQUIRED_PROJECT_APPROVALS,
                    "proposed": ProjectStructure.Normalize(
                        request.get("proposed"),
                        default_status=current_status,
                        default_project_code=project.get("project_code", ""),
                    ),
                    "current": ProjectStructure.Normalize(
                        {
                            "scenes": project.get("scenes", []),
                            "characters": project.get("characters", []),
                            "props": project.get("props", []),
                            "status": current_status,
                            "project_code": project.get("project_code", ""),
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
                        "approvals": list(request.get("approvals", [])),
                        "reviewers": list(request.get("reviewers", [])),
                        "rejections": list(request.get("rejections", [])),
                        "approval_log": list(request.get("approval_log", [])),
                        "rejection_log": list(request.get("rejection_log", [])),
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

                approvals = ProjectStructure.GetApprovals(request)
                request["approvals"] = approvals
                if not approved:
                    request["status"] = "rejected"
                    request["approvals"] = []
                    request["reviewer"] = reviewer
                    request.setdefault("rejections", [])
                    if reviewer not in request["rejections"]:
                        request["rejections"].append(reviewer)
                    request.setdefault("rejection_log", []).append(
                        {
                            "reviewer": reviewer,
                            "decision": "rejected",
                            "timestamp": datetime.datetime.now(
                                datetime.timezone.utc
                            ).isoformat(),
                        }
                    )
                    project["active_structure_change_request_id"] = None
                    self._WriteDatabase(database)
                    return "rejected"

                if reviewer in approvals:
                    raise ValueError("You have already approved this project change")
                approvals.append(reviewer)
                request.setdefault("approval_log", []).append(
                    {
                        "reviewer": reviewer,
                        "decision": "approved",
                        "timestamp": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                    }
                )
                if len(set(approvals)) >= self.REQUIRED_PROJECT_APPROVALS:
                    proposed = ProjectStructure.Normalize(
                        request.get("proposed"),
                        default_status=project.get("status", "Not Started"),
                        default_project_code=project.get("project_code", ""),
                    )
                    project["scenes"] = proposed["scenes"]
                    project["characters"] = proposed["characters"]
                    project["props"] = proposed["props"]
                    project["status"] = proposed["status"]
                    project["project_code"] = proposed["project_code"]
                    request["status"] = "approved"
                    request["reviewers"] = list(approvals)
                    project["active_structure_change_request_id"] = None
                    status = "approved"
                else:
                    status = "pending"
                self._WriteDatabase(database)
                return status
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def WithdrawProjectStructureChange(self, project_id, request_id, requester):
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
                if request.get("requester") != requester:
                    raise ValueError("Only the requester can withdraw this project change")

                request["status"] = "withdrawn"
                request["withdrawn_by"] = requester
                project["active_structure_change_request_id"] = None
                self._WriteDatabase(database)
                return "withdrawn"
            finally:
                file_lock.flock(lock_file.fileno(), file_lock.LOCK_UN)

    def AcknowledgeProjectStructureChange(self, project_id, request_id, requester):
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
