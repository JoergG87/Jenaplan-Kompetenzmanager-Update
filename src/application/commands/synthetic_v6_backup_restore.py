"""Exact synthetic V6 strategy for existing desktop backup/restore commands."""
from src.application.commands.final_v4_backup_restore import FinalV4EncryptedRestoreApplicationService
from src.core.timetable_schema import SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION
from src.security.synthetic_v6_backup_runtime import SyntheticV6EncryptedBackupService
from src.security.synthetic_v6_live_restore import prepare_synthetic_v6_live_restore


class SyntheticV6EncryptedRestoreApplicationService(FinalV4EncryptedRestoreApplicationService):
    schema_version = SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity.schema_version
    schema_fingerprint = SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity.fingerprint
    prepare_restore = staticmethod(prepare_synthetic_v6_live_restore)

    def __init__(self, service, **kwargs):
        if type(service) is not SyntheticV6EncryptedBackupService:
            raise ValueError("synthetic_v6_backup_service_required")
        service.require_synthetic()
        super().__init__(service, **kwargs)
