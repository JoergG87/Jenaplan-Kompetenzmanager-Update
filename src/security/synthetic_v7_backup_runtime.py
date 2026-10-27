"""V7 manifest/READY strategy; same encrypted backup container and lifecycle."""
from dataclasses import dataclass
from typing import ClassVar
from src.core.timetable_weeks_schema import SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION
from src.security.synthetic_v6_backup_runtime import SyntheticV6EncryptedBackupService
from src.security.final_v4_backup_runtime import FinalV4EncryptedBackupManifestV1

_TARGET = SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity
SYNTHETIC_V7_BACKUP_MANIFEST_ENTRY_ID = "00000000-0000-4000-8000-000000000007"
SYNTHETIC_V7_BACKUP_MANIFEST_FILENAME = "synthetic-v7-backup-manifest-v1.json"
SYNTHETIC_V7_RESTORE_READY_VERSION = 4


@dataclass(frozen=True, slots=True)
class SyntheticV7EncryptedBackupManifestV1(FinalV4EncryptedBackupManifestV1):
    expected_main_schema_version: ClassVar[int] = _TARGET.schema_version
    expected_main_schema_fingerprint: ClassVar[str] = _TARGET.fingerprint
    expected_manifest_entry_id: ClassVar[str] = SYNTHETIC_V7_BACKUP_MANIFEST_ENTRY_ID
    manifest_entry_id: str = SYNTHETIC_V7_BACKUP_MANIFEST_ENTRY_ID


class SyntheticV7EncryptedBackupService(SyntheticV6EncryptedBackupService):
    manifest_type = SyntheticV7EncryptedBackupManifestV1
    manifest_filename = SYNTHETIC_V7_BACKUP_MANIFEST_FILENAME
    manifest_entry_id = SYNTHETIC_V7_BACKUP_MANIFEST_ENTRY_ID
    main_schema_version = _TARGET.schema_version
    main_schema_fingerprint = _TARGET.fingerprint
    restore_ready_version = SYNTHETIC_V7_RESTORE_READY_VERSION

    def _inspect_main_connection(self, connection):
        from src.security.synthetic_v7_runtime import KeyedSyntheticV7CompatibilityInspector
        self.require_synthetic()
        return KeyedSyntheticV7CompatibilityInspector().inspect_connection(connection)
