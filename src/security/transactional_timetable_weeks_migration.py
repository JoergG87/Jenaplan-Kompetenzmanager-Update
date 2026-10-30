"""Direct exact V4/V6 -> V7 using the existing synthetic SQLCipher transaction."""
from contextlib import closing
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION
from src.core.timetable_schema import SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION
from src.core.timetable_weeks_schema import SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION, SYNTHETIC_TIMETABLE_WEEKS_REGISTRY, TIMETABLE_WEEKS_STATEMENTS
from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.database_content_evidence import database_content_evidence, require_same_content
from src.core.schema_upgrade import UpgradeError
from src.core.timetable_weeks import verify_timetable_weeks
from src.core.upgrade_validation import verify_timetable_source_references, verify_timetable_target_references
from src.security.transactional_timetable_migration import SyntheticTimetableMigration


class SyntheticTimetableWeeksMigration(SyntheticTimetableMigration):
    target_identity = SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity

    def __init__(self, backup_service, *, fault_hook=None):
        super().__init__(backup_service, fault_hook=fault_hook)
        self.backup = self.root / "schema-upgrade-source/transaction-timetable-weeks-v1/source.jkmebackup"

    def _require_source_connection(self, connection):
        result = DatabaseCompatibilityInspector().inspect_connection(connection)
        for registration, verifier in ((FINAL_V4_SCHEMA_REGISTRATION, verify_timetable_source_references),
                (SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION, verify_timetable_target_references)):
            identity = registration.identity
            if result.version.sqlite_user_version == identity.schema_version and result.schema_identity.fingerprint == identity.fingerprint:
                self.service._provider.verify_integrity(connection)
                verifier(connection)
                self.source_identity = identity
                return identity
        raise UpgradeError("transaction_source_schema_invalid")

    def _require_upgrade(self):
        for source in (FINAL_V4_SCHEMA_REGISTRATION, SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION):
            SYNTHETIC_TIMETABLE_WEEKS_REGISTRY.require_upgrade(source.identity, self.target_identity)

    def _require_inventory(self, inventory):
        if inventory.restore_evidence:
            raise UpgradeError("transaction_existing_evidence")
        allowed = {"schema-upgrade-source", "schema-upgrade-source/transaction-v1",
            "schema-upgrade-source/transaction-v1/source.jkmebackup",
            "schema-upgrade-source/transaction-timetable-v1",
            "schema-upgrade-source/transaction-timetable-v1/source.jkmebackup"}
        if any(a.relative_path not in allowed for a in inventory.artifacts if a.role == "upgrade_evidence"):
            raise UpgradeError("transaction_existing_evidence")
        from src.security.synthetic_v6_runtime import SyntheticV6Runtime
        SyntheticV6Runtime(self.service)._verify_historical_sources()

    def _apply_schema(self, connection):
        source = self._require_source_connection(connection)
        if source == FINAL_V4_SCHEMA_REGISTRATION.identity:
            # Existing normalization in the SAME transaction, no intermediate
            # installed version or backup/restore authority.
            SyntheticTimetableMigration._apply_schema(self, connection)
        for statement in TIMETABLE_WEEKS_STATEMENTS:
            connection.execute(statement)
        self._emit("schema_changed")
        connection.execute("PRAGMA user_version=7")

    def _target(self, connection, source):
        self.service._provider.verify_integrity(connection)
        result = DatabaseCompatibilityInspector().inspect_connection(connection)
        if (result.version.sqlite_user_version != self.target_identity.schema_version
                or result.schema_identity.fingerprint != self.target_identity.fingerprint):
            raise UpgradeError("transaction_target_schema_invalid")
        verify_timetable_target_references(connection)
        verify_timetable_weeks(connection)
        if connection.execute("SELECT 1 FROM timetable_entries WHERE week_pattern <> 'all'").fetchone():
            raise UpgradeError("transaction_historical_week_changed")
        if connection.execute("SELECT 1 FROM timetable_week_cycle").fetchone() or connection.execute("SELECT 1 FROM timetable_week_overrides").fetchone():
            raise UpgradeError("transaction_unexpected_week_configuration")
        # Project the original columns through an in-memory read-only proxy.
        # Typed full-content evidence still compares every historical row.
        class HistoricalConnection:
            def execute(self, sql):
                if sql.startswith('SELECT * FROM "timetable_entries"'):
                    columns = [row[1] for row in connection.execute("PRAGMA table_info(timetable_entries)") if row[1] != "week_pattern"]
                    sql = 'SELECT ' + ','.join('"' + c + '"' for c in columns) + ' FROM "timetable_entries"'
                if sql.startswith("SELECT name FROM sqlite_schema"):
                    from types import SimpleNamespace
                    return SimpleNamespace(fetchall=lambda: [row for row in connection.execute(sql) if row[0] not in ("timetable_week_cycle", "timetable_week_overrides")])
                return connection.execute(sql)
        if self.source_identity == FINAL_V4_SCHEMA_REGISTRATION.identity:
            # Reconstruct original V4 values for typed full-content evidence.
            self._verify_v4_content(connection, source)
        else:
            require_same_content(source, database_content_evidence(HistoricalConnection()))
        return self.target_identity

    @staticmethod
    def _verify_v4_content(connection, source):
        from src.core.database_content_evidence import DatabaseContentEvidence, _frame, _typed
        import hashlib
        cursor = connection.execute("""SELECT e.timetable_entry_id,e.weekday,e.start_time,e.end_time,s.subject_id,e.target_type,e.target_id,e.room,e.active,e.sort_order,e.created_at,e.updated_at,e.deleted_at
            FROM timetable_entries e JOIN timetable_entry_subjects s ON s.timetable_entry_id=e.timetable_entry_id""")
        columns = tuple(item[0] for item in cursor.description)
        rows = sorted(b"".join(_frame(_typed(value)) for value in row) for row in cursor)
        digest=hashlib.sha256();digest.update(_frame(b"timetable_entries"))
        for column in columns: digest.update(_frame(column.encode()))
        digest.update(len(rows).to_bytes(8,"big"))
        for row in rows: digest.update(_frame(row))
        names={table[0] for table in source.tables}
        historical=tuple(("timetable_entries",len(rows),digest.hexdigest()) if table[0]=="timetable_entries" else table
            for table in database_content_evidence(connection).tables if table[0] in names)
        require_same_content(source, DatabaseContentEvidence(historical))
        if connection.execute("SELECT 1 FROM timetable_entries WHERE entry_kind <> 'subject_lesson'").fetchone():
            raise UpgradeError("transaction_historical_kind_changed")
        if connection.execute("SELECT 1 FROM timetable_entries e LEFT JOIN timetable_entry_subjects s ON s.timetable_entry_id=e.timetable_entry_id GROUP BY e.timetable_entry_id HAVING count(s.subject_id) <> 1").fetchone():
            raise UpgradeError("transaction_historical_subject_changed")

    def inspect_restart(self, *, lock=None):
        from src.core.restore_runtime import RuntimeInstanceLock
        from pathlib import Path
        self._require_synthetic()
        from contextlib import nullcontext
        if lock is not None:
            from src.security.upgrade_startup import ProductUpgradeStartupGuard
            if lock.runtime_root != self.root:
                raise UpgradeError("transaction_lock_root_invalid")
            ProductUpgradeStartupGuard(lock)._require_lock()
        with (RuntimeInstanceLock(self.root) if lock is None else nullcontext(lock)):
            source, companion = self._verified_backup_content()
            self._no_sidecars(self.companion)
            for suffix in ("-wal", "-shm"):
                if Path(str(self.main) + suffix).exists():
                    raise UpgradeError("transaction_restart_wal_unsupported")
            with closing(self._connect(self.main)) as connection:
                result = DatabaseCompatibilityInspector().inspect_connection(connection)
                if result.version.sqlite_user_version in (4,6):
                    identity = self._require_source_connection(connection)
                    require_same_content(source, database_content_evidence(connection))
                else:
                    identity = self._target(connection, source)
            require_same_content(companion, self._companion_content(self.companion))
            self._validate_live_documents()
            self.service._validate_crossbindings(self.main, self.companion, self.service.loaded.database_key.key_material)
            return identity
