from __future__ import annotations

from contextlib import closing
import hashlib
from importlib.util import find_spec
from pathlib import Path
import os
import secrets
import sqlite3

import pytest

from prototypes.database_encryption_migration import (
    FailurePoint,
    MigrationPaths,
    MigrationPrototypeEngine,
    MigrationPrototypeError,
    SyntheticScale,
    create_synthetic_source,
    simulate_atomic_exchange,
)
from prototypes.database_encryption_migration.synthetic_data import (
    SYNTHETIC_GUARD_TABLE,
)
from src.core.database_engine import (
    DatabaseKeyRejectedError,
    SQLCipherConnectionProvider,
    SQLCipherVersionError,
)


pytestmark = pytest.mark.skipif(
    find_spec("sqlcipher3") is None,
    reason="isolated real-engine test requires requirements-sqlcipher-spike.txt",
)


def _fixture(tmp_path: Path, *, scale: SyntheticScale | None = None):
    paths = MigrationPaths.in_workspace(tmp_path)
    create_synthetic_source(paths.source, scale)
    return paths, bytearray(secrets.token_bytes(32))


def _erase(*materials: bytearray) -> None:
    for material in materials:
        for index in range(len(material)):
            material[index] = 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_successful_migration_validates_every_required_dimension(tmp_path: Path) -> None:
    paths, key = _fixture(tmp_path)
    try:
        report = MigrationPrototypeEngine().migrate(paths, key_material=key)
        validation = report.validation
        assert validation.successful
        assert validation.table_count == 12
        assert validation.total_rows > 3_000
        assert all(
            (
                validation.tables_match,
                validation.row_counts_match,
                validation.primary_keys_match,
                validation.foreign_keys_match,
                validation.triggers_match,
                validation.views_match,
                validation.indexes_match,
                validation.pragmas_match,
                validation.schema_hash_match,
                validation.data_hash_match,
            )
        )
        assert report.source_sha256_before == report.source_sha256_after
        assert report.successful_reopen
        assert not report.rollback_required
    finally:
        _erase(key)


def test_validation_detects_autoincrement_sequence_drift(tmp_path: Path) -> None:
    paths, key = _fixture(tmp_path)
    try:
        engine = MigrationPrototypeEngine()
        engine.migrate(paths, key_material=key)
        with closing(
            SQLCipherConnectionProvider().connect(
                paths.target, create=False, key_material=key
            )
        ) as target:
            target.execute(
                "UPDATE sqlite_sequence SET seq = seq + 100000 "
                "WHERE name = 'observation_audit'"
            )
            target.commit()
        validation = engine.validate(paths, key_material=key)
        assert not validation.successful
        assert not validation.data_hash_match
    finally:
        _erase(key)


def test_backup_verification_detects_autoincrement_sequence_drift(
    tmp_path: Path,
) -> None:
    paths, key = _fixture(tmp_path)

    def tamper_backup(event: str, observed: MigrationPaths) -> None:
        if event != "backup_created":
            return
        with sqlite3.connect(observed.backup) as backup:
            backup.execute(
                "UPDATE sqlite_sequence SET seq = seq + 100000 "
                "WHERE name = 'observation_audit'"
            )

    try:
        with pytest.raises(MigrationPrototypeError) as caught:
            MigrationPrototypeEngine().migrate(
                paths,
                key_material=key,
                phase_observer=tamper_backup,
            )
        assert caught.value.code == "migration_backup_verification_failed"
        assert not paths.backup.exists()
    finally:
        _erase(key)


def test_migration_is_repeatable_from_the_same_unchanged_source(tmp_path: Path) -> None:
    first, key = _fixture(tmp_path)
    second = MigrationPaths.in_workspace(tmp_path, run_name="run-2")
    source_before = _sha256(first.source)
    try:
        first_report = MigrationPrototypeEngine().migrate(first, key_material=key)
        second_report = MigrationPrototypeEngine().migrate(second, key_material=key)
        assert first_report.validation.schema_hash == second_report.validation.schema_hash
        assert first_report.validation.data_hash == second_report.validation.data_hash
        assert _sha256(first.source) == source_before
    finally:
        _erase(key)


@pytest.mark.parametrize(
    "failure_point",
    [
        FailurePoint.BACKUP,
        FailurePoint.EXPORT,
        FailurePoint.COMMIT,
        FailurePoint.CORRUPT_TARGET,
        FailurePoint.WRONG_KEY,
        FailurePoint.INTERRUPT_EXPORT,
    ],
)
def test_each_simulated_failure_rolls_back_and_preserves_source(
    tmp_path: Path, failure_point: FailurePoint
) -> None:
    paths, key = _fixture(tmp_path)
    source_before = _sha256(paths.source)
    try:
        with pytest.raises(MigrationPrototypeError):
            MigrationPrototypeEngine().migrate(
                paths,
                key_material=key,
                failure_point=failure_point,
            )
        assert _sha256(paths.source) == source_before
        assert not paths.target.exists()
        assert paths.backup.exists() is (failure_point is not FailurePoint.BACKUP)
        with closing(sqlite3.connect(paths.source)) as source:
            assert source.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert source.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        _erase(key)


def test_error_cleanup_never_deletes_a_foreign_replacement_target(
    tmp_path: Path,
) -> None:
    paths, key = _fixture(tmp_path)
    foreign_bytes = secrets.token_bytes(73)

    def observer(phase: str, _paths: MigrationPaths) -> None:
        if phase == "export_in_progress":
            replacement = tmp_path / "foreign-replacement.bin"
            replacement.write_bytes(foreign_bytes)
            os.replace(replacement, paths.target)
            raise MigrationPrototypeError("simulated_foreign_target_swap")

    try:
        with pytest.raises(MigrationPrototypeError):
            MigrationPrototypeEngine().migrate(
                paths,
                key_material=key,
                phase_observer=observer,
            )
        assert paths.target.read_bytes() == foreign_bytes
    finally:
        _erase(key)


def test_backup_is_complete_and_independently_readable(tmp_path: Path) -> None:
    paths, key = _fixture(tmp_path)
    try:
        report = MigrationPrototypeEngine().migrate(paths, key_material=key)
        with closing(sqlite3.connect(paths.backup)) as backup:
            assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert backup.execute("PRAGMA foreign_key_check").fetchall() == []
            assert backup.execute(
                f"SELECT count(*) FROM {SYNTHETIC_GUARD_TABLE}"
            ).fetchone()[0] == 1
        assert report.performance.backup_size_bytes == paths.backup.stat().st_size
    finally:
        _erase(key)


def test_correct_key_reopens_and_plain_sqlite_rejects_target(tmp_path: Path) -> None:
    paths, key = _fixture(tmp_path)
    try:
        MigrationPrototypeEngine().migrate(paths, key_material=key)
        with closing(
            SQLCipherConnectionProvider().connect(
                paths.target, create=False, key_material=key
            )
        ) as encrypted:
            assert encrypted.execute("SELECT count(*) FROM students").fetchone()[0] == 48
        with pytest.raises(sqlite3.DatabaseError):
            with closing(sqlite3.connect(paths.target)) as plaintext:
                plaintext.execute("SELECT count(*) FROM sqlite_schema").fetchone()
    finally:
        _erase(key)


def test_wrong_key_is_rejected_after_successful_migration(tmp_path: Path) -> None:
    paths, key = _fixture(tmp_path)
    wrong = bytearray(secrets.token_bytes(32))
    try:
        MigrationPrototypeEngine().migrate(paths, key_material=key)
        with pytest.raises(DatabaseKeyRejectedError):
            SQLCipherConnectionProvider().connect(
                paths.target,
                create=False,
                key_material=wrong,
            )
    finally:
        _erase(key, wrong)


def test_comparison_component_detects_changed_values(tmp_path: Path) -> None:
    paths, key = _fixture(tmp_path)
    provider = SQLCipherConnectionProvider()
    engine = MigrationPrototypeEngine(provider)
    try:
        engine.migrate(paths, key_material=key)
        with closing(
            provider.connect(paths.target, create=False, key_material=key)
        ) as target:
            target.execute(
                "UPDATE students SET display_name = ? WHERE student_id = ?",
                ("Manipulierter synthetischer Wert", "SYN-STU-000001"),
            )
            target.commit()
        validation = engine.validate(paths, key_material=key)
        assert not validation.successful
        assert not validation.data_hash_match
        assert validation.row_counts_match
    finally:
        _erase(key)


def test_comparison_component_detects_schema_and_index_drift(tmp_path: Path) -> None:
    paths, key = _fixture(tmp_path)
    provider = SQLCipherConnectionProvider()
    engine = MigrationPrototypeEngine(provider)
    try:
        engine.migrate(paths, key_material=key)
        with closing(
            provider.connect(paths.target, create=False, key_material=key)
        ) as target:
            target.execute("DROP INDEX idx_documents_student")
            target.commit()
        validation = engine.validate(paths, key_material=key)
        assert not validation.successful
        assert not validation.indexes_match
        assert not validation.schema_hash_match
    finally:
        _erase(key)


def test_unguarded_database_is_rejected_before_backup_or_target(tmp_path: Path) -> None:
    paths = MigrationPaths.in_workspace(tmp_path)
    with closing(sqlite3.connect(paths.source)) as source:
        source.execute("CREATE TABLE ordinary(value TEXT)")
        source.commit()
    key = bytearray(secrets.token_bytes(32))
    try:
        with pytest.raises(MigrationPrototypeError) as caught:
            MigrationPrototypeEngine().migrate(paths, key_material=key)
        assert caught.value.code == "migration_source_not_synthetic"
        assert not paths.backup.exists()
        assert not paths.target.exists()
    finally:
        _erase(key)


def test_corrupt_source_is_rejected_without_creating_target(tmp_path: Path) -> None:
    paths, key = _fixture(tmp_path)
    with paths.source.open("r+b") as source:
        source.seek(0, 2)
        source.truncate(source.tell() - 100)
    corrupted_hash = _sha256(paths.source)
    try:
        with pytest.raises(MigrationPrototypeError):
            MigrationPrototypeEngine().migrate(paths, key_material=key)
        assert _sha256(paths.source) == corrupted_hash
        assert not paths.backup.exists()
        assert not paths.target.exists()
    finally:
        _erase(key)


def test_incompatible_sqlcipher_version_fails_closed(tmp_path: Path) -> None:
    paths, key = _fixture(tmp_path)
    provider = SQLCipherConnectionProvider(expected_engine_version="0.0.0-test")
    try:
        with pytest.raises(MigrationPrototypeError) as caught:
            MigrationPrototypeEngine(provider).migrate(paths, key_material=key)
        assert caught.value.code == "sqlcipher_engine_version_incompatible"
        assert not paths.target.exists()
    finally:
        _erase(key)


def test_large_synthetic_database_records_performance_and_integrity(tmp_path: Path) -> None:
    paths, key = _fixture(tmp_path, scale=SyntheticScale.large())
    try:
        report = MigrationPrototypeEngine().migrate(paths, key_material=key)
        metrics = report.performance
        assert report.validation.successful
        assert report.validation.total_rows > 50_000
        assert metrics.source_size_bytes > 1_000_000
        assert metrics.encrypted_size_bytes > 1_000_000
        assert metrics.total_seconds > 0
        assert metrics.export_seconds > 0
        assert metrics.validation_seconds > 0
        assert metrics.reopen_seconds > 0
    finally:
        _erase(key)


def test_atomic_exchange_is_only_a_non_mutating_simulation() -> None:
    simulation = simulate_atomic_exchange()
    assert not simulation.performed
    assert len(simulation.steps) == 6
    assert "performs no exchange" in simulation.recovery_rule
