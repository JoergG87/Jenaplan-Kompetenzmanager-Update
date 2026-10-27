"""V7 identity strategy for the existing synthetic SQLCipher runtime."""
from dataclasses import dataclass
from src.core.timetable_weeks_schema import SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION
from src.core.timetable_weeks import verify_timetable_weeks
from src.security.synthetic_v6_runtime import SyntheticV6Runtime, OpenedSyntheticV6Runtime, KeyedSyntheticV6CompatibilityInspector
from src.security.final_v4_backup_runtime import FinalV4EncryptedBackupService
from src.security.synthetic_v6_backup_runtime import SyntheticV6EncryptedBackupService


class KeyedSyntheticV7CompatibilityInspector(KeyedSyntheticV6CompatibilityInspector):
    target_identity = SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity

    def inspect_connection(self, connection):
        report = super().inspect_connection(connection)
        verify_timetable_weeks(connection)
        return report


@dataclass(frozen=True)
class OpenedSyntheticV7Runtime(OpenedSyntheticV6Runtime):
    identity: object = SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity


class SyntheticV7Runtime(SyntheticV6Runtime):
    inspector_type = KeyedSyntheticV7CompatibilityInspector
    opened_type = OpenedSyntheticV7Runtime
    extra_historical_sources = (("schema-upgrade-source/transaction-timetable-weeks-v1/source.jkmebackup",
        (FinalV4EncryptedBackupService, SyntheticV6EncryptedBackupService)),)
    extra_historical_paths = frozenset({"schema-upgrade-source/transaction-timetable-weeks-v1",
        "schema-upgrade-source/transaction-timetable-weeks-v1/source.jkmebackup"})

    def _classify_terminal_restore(self):
        from src.security.synthetic_v7_live_restore import classify_terminal_synthetic_v7_restore_artifacts
        return classify_terminal_synthetic_v7_restore_artifacts(self.service)
