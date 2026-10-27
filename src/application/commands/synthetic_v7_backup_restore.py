"""Exact synthetic V7 strategy for existing desktop backup/restore commands."""
from src.application.commands.final_v4_backup_restore import FinalV4EncryptedRestoreApplicationService
from src.core.timetable_weeks_schema import SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION
from src.security.synthetic_v7_backup_runtime import SyntheticV7EncryptedBackupService
from src.security.synthetic_v7_live_restore import prepare_synthetic_v7_live_restore


class SyntheticV7EncryptedRestoreApplicationService(FinalV4EncryptedRestoreApplicationService):
    schema_version = SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity.schema_version
    schema_fingerprint = SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity.fingerprint
    def prepare_restore(self, **kwargs):
        return prepare_synthetic_v7_live_restore(
            **kwargs, before_handoff=self._before_handoff)

    def __init__(self, service, **kwargs):
        if type(service) is not SyntheticV7EncryptedBackupService:
            raise ValueError("synthetic_v7_backup_service_required")
        service.require_synthetic()
        super().__init__(service, **kwargs)
