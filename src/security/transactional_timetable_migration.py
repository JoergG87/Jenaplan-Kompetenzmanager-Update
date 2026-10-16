"""Explicit V4/old synthetic V5 -> V6 SQLCipher transaction, never product wiring."""
from contextlib import closing
import hashlib
from pathlib import Path

from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.database_content_evidence import (DatabaseContentEvidence,
    database_content_evidence, require_same_content, _frame, _typed)
from src.core.lesson_times_schema import (LESSON_TIME_TEMPLATE_STATEMENT,
    SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION)
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION
from src.core.schema_upgrade import UpgradeError
from src.core.timetable_schema import (SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION,
    SYNTHETIC_TIMETABLE_REGISTRY, TIMETABLE_TARGET_STATEMENT,
    TIMETABLE_SUBJECTS_STATEMENT, TIMETABLE_INDEX_STATEMENT)
from src.core.upgrade_validation import (verify_timetable_source_references,
    verify_timetable_target_references)
from src.core.restore_runtime import RuntimeInstanceLock
from .transactional_schema_migration import SyntheticTransactionalMigration


class SyntheticTimetableMigration(SyntheticTransactionalMigration):
    target_identity = SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity

    def __init__(self, backup_service, *, fault_hook=None):
        super().__init__(backup_service, fault_hook=fault_hook)
        self.backup = self.root / "schema-upgrade-source" / "transaction-timetable-v1" / "source.jkmebackup"
        self.source_identity = None

    def _require_inventory(self, inventory):
        if inventory.restore_evidence:
            raise UpgradeError("transaction_existing_evidence")
        if not inventory.upgrade_evidence:
            return
        allowed = {"schema-upgrade-source", "schema-upgrade-source/transaction-v1",
                   "schema-upgrade-source/transaction-v1/source.jkmebackup"}
        if any(a.relative_path not in allowed for a in inventory.artifacts
               if a.role == "upgrade_evidence"):
            raise UpgradeError("transaction_existing_evidence")
        with closing(self._connect(self.main, read_only=True)) as connection:
            if self._require_source_connection(connection) != SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION.identity:
                raise UpgradeError("transaction_existing_evidence")
        # Independently authenticate the retained old V4 source container. It
        # remains historical evidence and grants no target restore authority.
        from .final_v4_backup_runtime import FinalV4EncryptedBackupService
        service = self.service
        historical = FinalV4EncryptedBackupService(opened_runtime=None, paths=service.paths,
            loaded_keys=service.loaded, main_factory=service._main_factory,
            document_factory=service._document_factory, provider=service._provider,
            maintenance_gate=service._gate, random_source=service._random,
            clock=service._clock, installation_id=service.installation_id)
        with historical.verified_snapshot(self.root / "schema-upgrade-source" / "transaction-v1" / "source.jkmebackup"):
            pass

    def _require_source_connection(self, connection):
        result = DatabaseCompatibilityInspector().inspect_connection(connection)
        for registration in (FINAL_V4_SCHEMA_REGISTRATION, SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION):
            identity = registration.identity
            if (result.version.sqlite_user_version == identity.schema_version
                    and result.schema_identity.fingerprint == identity.fingerprint):
                self.service._provider.verify_integrity(connection)
                verify_timetable_source_references(connection)
                self.source_identity = identity
                return identity
        raise UpgradeError("transaction_source_schema_invalid")

    def _source(self, path):
        self._no_sidecars(path)
        with closing(self._connect(path, read_only=True)) as connection:
            self._require_source_connection(connection)
            return database_content_evidence(connection)

    def _require_upgrade(self):
        # Actual source is independently inspected before backup and again under BEGIN.
        for source in (FINAL_V4_SCHEMA_REGISTRATION, SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION):
            SYNTHETIC_TIMETABLE_REGISTRY.require_upgrade(source.identity, self.target_identity)

    def _apply_schema(self, connection):
        source = self._require_source_connection(connection)
        for (name,) in connection.execute("SELECT name FROM sqlite_schema WHERE type='table'"):
            quoted = '"' + name.replace('"', '""') + '"'
            if any(row[2] == "timetable_entries" for row in connection.execute(f"PRAGMA foreign_key_list({quoted})")):
                raise UpgradeError("transaction_unexpected_incoming_timetable_reference")
        links = tuple(tuple(row) for row in connection.execute(
            "SELECT timetable_entry_id, subject_id FROM timetable_entries"))
        if source == FINAL_V4_SCHEMA_REGISTRATION.identity:
            connection.execute(LESSON_TIME_TEMPLATE_STATEMENT)
        connection.execute(TIMETABLE_TARGET_STATEMENT)
        self._emit("parent_created")
        connection.execute("""INSERT INTO timetable_entries_v5_target SELECT
            timetable_entry_id, weekday, start_time, end_time, 'subject_lesson',
            target_type, target_id, room, active, sort_order, created_at, updated_at,
            deleted_at FROM timetable_entries""")
        self._emit("parent_copied")
        connection.execute("DROP TABLE timetable_entries")
        self._emit("parent_dropped")
        connection.execute("ALTER TABLE timetable_entries_v5_target RENAME TO timetable_entries")
        connection.execute(TIMETABLE_INDEX_STATEMENT)
        connection.execute(TIMETABLE_SUBJECTS_STATEMENT)
        connection.executemany("INSERT INTO timetable_entry_subjects VALUES (?, ?)", links)
        self._emit("subjects_copied")
        self._emit("schema_changed")
        connection.execute("PRAGMA user_version=6")

    def _target(self, connection, source):
        self.service._provider.verify_integrity(connection)
        result = DatabaseCompatibilityInspector().inspect_connection(connection)
        target = self.target_identity
        if (result.version.sqlite_user_version != target.schema_version
                or result.schema_identity.fingerprint != target.fingerprint):
            raise UpgradeError("transaction_target_schema_invalid")
        verify_timetable_target_references(connection)
        # Reconstruct the exact old typed table projection in memory. No row,
        # column, storage class or non-timetable historical content may change.
        cursor = connection.execute("""SELECT e.timetable_entry_id, e.weekday,
            e.start_time, e.end_time, s.subject_id, e.target_type, e.target_id,
            e.room, e.active, e.sort_order, e.created_at, e.updated_at, e.deleted_at
            FROM timetable_entries e JOIN timetable_entry_subjects s
            ON s.timetable_entry_id=e.timetable_entry_id""")
        columns = tuple(item[0] for item in cursor.description)
        rows = sorted(b"".join(_frame(_typed(value)) for value in row) for row in cursor)
        digest = hashlib.sha256(); digest.update(_frame(b"timetable_entries"))
        for column in columns:
            digest.update(_frame(column.encode("utf-8")))
        digest.update(len(rows).to_bytes(8, "big"))
        for row in rows:
            digest.update(_frame(row))
        source_names = {item[0] for item in source.tables}
        historical = []
        for table in database_content_evidence(connection).tables:
            if table[0] == "timetable_entry_subjects" or table[0] not in source_names:
                continue
            historical.append(("timetable_entries", len(rows), digest.hexdigest())
                              if table[0] == "timetable_entries" else table)
        require_same_content(source, DatabaseContentEvidence(tuple(historical)))
        # A migration creates only legacy single subject lessons.
        if connection.execute("SELECT 1 FROM timetable_entries WHERE entry_kind <> 'subject_lesson'").fetchone():
            raise UpgradeError("transaction_historical_kind_changed")
        if connection.execute("""SELECT 1 FROM timetable_entries e LEFT JOIN timetable_entry_subjects s
            ON s.timetable_entry_id=e.timetable_entry_id GROUP BY e.timetable_entry_id
            HAVING count(s.subject_id) <> 1""").fetchone():
            raise UpgradeError("transaction_historical_subject_changed")
        return target

    def inspect_restart(self):
        self._require_synthetic()
        with RuntimeInstanceLock(self.root):
            source, companion = self._verified_backup_content()
            self._no_sidecars(self.companion)
            for suffix in ("-wal", "-shm"):
                if Path(str(self.main) + suffix).exists():
                    raise UpgradeError("transaction_restart_wal_unsupported")
            with closing(self._connect(self.main)) as connection:
                result = DatabaseCompatibilityInspector().inspect_connection(connection)
                if result.version.sqlite_user_version in (4, 5):
                    identity = self._require_source_connection(connection)
                    require_same_content(source, database_content_evidence(connection))
                else:
                    identity = self._target(connection, source)
            require_same_content(companion, self._companion_content(self.companion))
            self._validate_live_documents()
            self.service._validate_crossbindings(self.main, self.companion,
                self.service.loaded.database_key.key_material)
            return identity
