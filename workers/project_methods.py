from workers.models import LFRoles


class ProjectWorkerMethods:
    def GetDatabaseSnapshot(self):
        if self._closed:
            return {}
        return self.fossa_db.GetDatabaseSnapshot()

    def GetProjects(self):
        if self._closed:
            raise RuntimeError("Cannot read projects from a closed worker")
        return self.fossa_db.GetProjects()

    def SyncProject(self, project):
        if self._closed:
            raise RuntimeError("Cannot sync a project with a closed worker")
        if self.role is not LFRoles.DB_ACCESS:
            raise RuntimeError("Project sync requires a database access worker")
        self.fossa_db.SaveProject(
            project.id,
            project.name,
            project.status.value,
            project.directory_path,
            project.project_code,
        )

    def SubmitProjectStructureChange(
        self,
        project_id,
        requester,
        request_id,
        proposed_structure,
        base_structure,
    ):
        self._RequireApprovalRole()
        return self.fossa_db.SubmitProjectStructureChange(
            project_id,
            requester,
            request_id,
            proposed_structure,
            base_structure,
        )

    def GetPendingProjectStructureChanges(self):
        self._RequireApprovalRole()
        return self.fossa_db.GetPendingProjectStructureChanges()

    def GetProjectStructureChangeResults(self, requester):
        self._RequireApprovalRole()
        return self.fossa_db.GetProjectStructureChangeResults(requester)

    def ResolveProjectStructureChange(
        self, project_id, request_id, reviewer, approved
    ):
        self._RequireApprovalRole()
        return self.fossa_db.ResolveProjectStructureChange(
            project_id,
            request_id,
            reviewer,
            approved,
        )

    def WithdrawProjectStructureChange(self, project_id, request_id, requester):
        self._RequireApprovalRole()
        return self.fossa_db.WithdrawProjectStructureChange(
            project_id,
            request_id,
            requester,
        )

    def AcknowledgeProjectStructureChange(
        self, project_id, request_id, requester
    ):
        self._RequireApprovalRole()
        return self.fossa_db.AcknowledgeProjectStructureChange(
            project_id,
            request_id,
            requester,
        )

    def _RequireApprovalRole(self):
        if self._closed:
            raise RuntimeError("Project change approval worker is closed")
        if self.role is not LFRoles.APPROVAL_NEEDED:
            raise RuntimeError(
                "Project change operation requires an approval worker"
            )
