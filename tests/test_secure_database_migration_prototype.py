from __future__ import annotations

import hashlib
import json
from pathlib import Path
import secrets
import uuid

import pytest

from prototypes.database_encryption_migration import (
    FailurePoint,
    MigrationPaths,
    PrototypeInterruptionPoint,
    SecureMigrationPrototypeEngine,
    SimulatedProcessInterruption,
    create_synthetic_source,
)
from src.core.database_engine import SQLCipherConnectionProvider
from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import (
    DatabaseKeyEnvelopeService,
    derive_migration_journal_auth_key,
)
from src.security.infrastructure.database_key_envelope_repository import (
    FileDatabaseKeyEnvelopeRepository,
)
from src.security.infrastructure.migration_journal_repository import (
    AuthenticatedMigrationJournalRepository,
)
from src.security.infrastructure.system import (
    PlatformFilePermissionManager,
    SystemClock,
    SystemRandomSource,
)
from src.security.migration_journal import MigrationPhase, RecoveryDecision


def _dmk() -> LoadedDataMasterKey:
    return LoadedDataMasterKey(str(uuid.uuid4()), 1, secrets.token_bytes(32))


def _fixture(tmp_path: Path):
    paths = MigrationPaths.in_workspace(tmp_path)
    create_synthetic_source(paths.source)
    return paths, _dmk()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_key(report, dmk):
    repository = FileDatabaseKeyEnvelopeRepository(
        report.envelope_path, PlatformFilePermissionManager()
    )
    return DatabaseKeyEnvelopeService(
        repository=repository,
        random_source=SystemRandomSource(),
        clock=SystemClock(),
    ).load_active(dmk, expected_generation=report.database_key_generation)


def _load_journal(report, dmk):
    repository = AuthenticatedMigrationJournalRepository(
        report.journal_path, PlatformFilePermissionManager()
    )
    auth_key = derive_migration_journal_auth_key(
        dmk, migration_id=report.migration_id
    )
    return repository.load(auth_key)


def test_synthetic_sqlcipher_migration_uses_persisted_envelope_and_journal(
    tmp_path: Path,
) -> None:
    paths, dmk = _fixture(tmp_path)
    source_before = _sha256(paths.source)
    report = SecureMigrationPrototypeEngine().run(paths, dmk=dmk)

    assert report.migration.validation.successful
    assert report.migration.source_sha256_before == source_before
    assert report.migration.source_sha256_after == source_before
    assert _sha256(paths.source) == source_before
    assert _sha256(paths.backup) == report.migration.backup_sha256
    assert report.envelope_path.is_file()
    assert report.journal_path.is_file()

    database_key = _load_key(report, dmk)
    assert len(database_key.key_material) == 32
    with SQLCipherConnectionProvider().connect(
        paths.target,
        create=False,
        key_material=database_key.key_material,
    ) as connection:
        assert connection.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 48

    journal = _load_journal(report, dmk)
    assert journal.phase is MigrationPhase.COMPLETED
    assert tuple(event.phase for event in journal.history) == (
        MigrationPhase.NOT_STARTED,
        MigrationPhase.PREFLIGHT_STARTED,
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_STARTED,
        MigrationPhase.BACKUP_CREATED,
        MigrationPhase.BACKUP_VERIFIED,
        MigrationPhase.TARGET_CREATION_STARTED,
        MigrationPhase.TARGET_CREATED,
        MigrationPhase.EXPORT_STARTED,
        MigrationPhase.EXPORT_COMPLETED,
        MigrationPhase.VALIDATION_STARTED,
        MigrationPhase.VALIDATION_COMPLETED,
        MigrationPhase.REOPEN_STARTED,
        MigrationPhase.REOPEN_VERIFIED,
        MigrationPhase.COMPLETED,
    )
    assert (
        SecureMigrationPrototypeEngine().recovery_decision(paths, dmk=dmk)
        is RecoveryDecision.CLEANUP_COMPLETED_ARTIFACTS
    )

    for secret in (dmk.key_material, database_key.key_material):
        for artifact in (report.envelope_path, report.journal_path, paths.target):
            raw = artifact.read_bytes()
            assert secret not in raw
            assert secret.hex().encode("ascii") not in raw


@pytest.mark.parametrize(
    ("point", "expected_phase", "expected_decision"),
    [
        (
            PrototypeInterruptionPoint.AFTER_BACKUP,
            MigrationPhase.BACKUP_VERIFIED,
            RecoveryDecision.NO_ACTION,
        ),
        (
            PrototypeInterruptionPoint.DURING_EXPORT,
            MigrationPhase.EXPORT_STARTED,
            RecoveryDecision.ROLLBACK_TARGET,
        ),
        (
            PrototypeInterruptionPoint.AFTER_EXPORT,
            MigrationPhase.EXPORT_COMPLETED,
            RecoveryDecision.CONTINUE_VALIDATION,
        ),
        (
            PrototypeInterruptionPoint.DURING_VALIDATION,
            MigrationPhase.VALIDATION_STARTED,
            RecoveryDecision.CONTINUE_VALIDATION,
        ),
        (
            PrototypeInterruptionPoint.AFTER_REOPEN,
            MigrationPhase.REOPEN_VERIFIED,
            RecoveryDecision.NO_ACTION,
        ),
    ],
)
def test_process_interruptions_have_stable_idempotent_recovery_decisions(
    tmp_path: Path,
    point: PrototypeInterruptionPoint,
    expected_phase: MigrationPhase,
    expected_decision: RecoveryDecision,
) -> None:
    paths, dmk = _fixture(tmp_path)
    source_before = _sha256(paths.source)
    engine = SecureMigrationPrototypeEngine()
    with pytest.raises(SimulatedProcessInterruption):
        engine.run(paths, dmk=dmk, interruption_point=point)

    assert _sha256(paths.source) == source_before
    assert paths.backup.is_file()
    assert len(_sha256(paths.backup)) == 64
    envelope_path = paths.root / "database-key-envelopes-v1.json"
    journal_path = paths.root / "database-migration-journal-v1.json"
    payload = json.loads(journal_path.read_bytes())
    migration_id = payload["migration_id"]
    journal = AuthenticatedMigrationJournalRepository(
        journal_path, PlatformFilePermissionManager()
    ).load(derive_migration_journal_auth_key(dmk, migration_id=migration_id))
    assert journal.phase is expected_phase
    assert envelope_path.is_file()
    first = engine.recovery_decision(paths, dmk=dmk)
    second = engine.recovery_decision(paths, dmk=dmk)
    assert first is second is expected_decision

    source_after_interrupt = _sha256(paths.source)
    backup_after_interrupt = _sha256(paths.backup)
    with pytest.raises(Exception) as repeated:
        engine.run(paths, dmk=dmk)
    assert getattr(repeated.value, "code", "") == "secure_migration_run_already_exists"
    assert _sha256(paths.source) == source_after_interrupt
    assert _sha256(paths.backup) == backup_after_interrupt


def test_wrong_database_key_fails_and_leaves_source_and_backup_unchanged(
    tmp_path: Path,
) -> None:
    paths, dmk = _fixture(tmp_path)
    source_before = _sha256(paths.source)
    engine = SecureMigrationPrototypeEngine()
    with pytest.raises(Exception):
        engine.run(paths, dmk=dmk, failure_point=FailurePoint.WRONG_KEY)
    assert _sha256(paths.source) == source_before
    assert paths.backup.is_file()
    assert len(_sha256(paths.backup)) == 64
    assert not paths.target.exists()
    assert (
        engine.recovery_decision(paths, dmk=dmk)
        is RecoveryDecision.BLOCK_MANUAL_REVIEW
    )


def test_corrupt_envelope_or_journal_blocks_without_recreation(tmp_path: Path) -> None:
    for corrupt in ("envelope", "journal"):
        root = tmp_path / corrupt
        root.mkdir()
        paths, dmk = _fixture(root)
        engine = SecureMigrationPrototypeEngine()
        with pytest.raises(SimulatedProcessInterruption):
            engine.run(
                paths,
                dmk=dmk,
                interruption_point=PrototypeInterruptionPoint.AFTER_BACKUP,
            )
        source_before = _sha256(paths.source)
        backup_before = _sha256(paths.backup)
        path = root / (
            "database-key-envelopes-v1.json"
            if corrupt == "envelope"
            else "database-migration-journal-v1.json"
        )
        original = path.read_bytes()
        tampered = bytearray(original)
        tampered[len(tampered) // 2] ^= 1
        path.write_bytes(bytes(tampered))
        assert (
            engine.recovery_decision(paths, dmk=dmk)
            is RecoveryDecision.BLOCK_MANUAL_REVIEW
        )
        with pytest.raises(Exception):
            engine.run(paths, dmk=dmk)
        assert path.read_bytes() == bytes(tampered)
        assert _sha256(paths.source) == source_before
        assert _sha256(paths.backup) == backup_before


def test_preflight_rejects_non_synthetic_source_before_sidecar_write(
    tmp_path: Path,
) -> None:
    paths = MigrationPaths.in_workspace(tmp_path)
    paths.source.write_bytes(secrets.token_bytes(128))
    with pytest.raises(Exception):
        SecureMigrationPrototypeEngine().run(paths, dmk=_dmk())
    assert not (tmp_path / "database-key-envelopes-v1.json").exists()
    assert not (tmp_path / "database-migration-journal-v1.json").exists()
    assert not paths.backup.exists()
    assert not paths.target.exists()


def test_authenticated_journal_is_cross_bound_to_its_database_key(
    tmp_path: Path,
) -> None:
    dmk = _dmk()
    roots = (tmp_path / "first", tmp_path / "second")
    contexts = (str(uuid.uuid4()), str(uuid.uuid4()))
    engines: list[SecureMigrationPrototypeEngine] = []
    paths_list: list[MigrationPaths] = []
    for root, context in zip(roots, contexts, strict=True):
        root.mkdir()
        paths = MigrationPaths.in_workspace(root)
        create_synthetic_source(paths.source)
        engine = SecureMigrationPrototypeEngine()
        with pytest.raises(SimulatedProcessInterruption):
            engine.run(
                paths,
                dmk=dmk,
                database_context_id=context,
                interruption_point=PrototypeInterruptionPoint.AFTER_BACKUP,
            )
        engines.append(engine)
        paths_list.append(paths)

    first_envelope = roots[0] / "database-key-envelopes-v1.json"
    second_envelope = roots[1] / "database-key-envelopes-v1.json"
    second_envelope.write_bytes(first_envelope.read_bytes())
    assert (
        engines[1].recovery_decision(paths_list[1], dmk=dmk)
        is RecoveryDecision.BLOCK_MANUAL_REVIEW
    )
