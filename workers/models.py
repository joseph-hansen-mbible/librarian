from enum import Enum


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
    HAYDN = 12
    SCHUBERT = 13
    STRAVINKSY = 14
    GRIEG = 15
    SOULJA_BOY = 16
    FETTY_WAP = 17
    METRO_BOOMIN = 18
    LIL_UZI_VERT = 19
    DON_TOLLIVER = 20
    SNOOP_DOGG = 21
    JUICE_WRLD = 22
    KENDRICK_LAMAR = 23


class LFRoles(Enum):
    DB_ACCESS = "db_access"
    WORKER_ID = "worker_id"
    CACHING = "caching"
    CONFLICT_RESOLUTION = "conflict_resolution"
    RECORDS = "records"
    APPROVAL_NEEDED = "approval_needed"


class LocalCacheData:
    def __init__(
        self,
        current_file="",
        recent_files=None,
        current_file_checklist=None,
        unlock_ssot_request=False,
        ssot_unlock_count=0,
        current_file_notes="",
        increment_from="",
        increment_to="",
    ):
        self.current_file = current_file
        self.recent_files = recent_files if recent_files is not None else []
        self.current_file_checklist = (
            current_file_checklist
            if current_file_checklist is not None
            else {}
        )
        self.unlock_ssot_request = unlock_ssot_request
        self.ssot_unlock_count = ssot_unlock_count
        self.current_file_notes = current_file_notes
        self.increment_from = increment_from
        self.increment_to = increment_to
