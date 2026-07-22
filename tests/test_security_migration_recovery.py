from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
import os
import shutil
import sqlite3
import uuid

import pytest

from prototypes.database_encryption_migration import MigrationPaths
from prototypes.database_encryption_migration.recovery import (
    PrototypeMigrationRecoveryOrchestrator,
)
from prototypes.database_encryption_migration.synthetic_data import (
    SyntheticScale,
    create_synthetic_source,
)
from src.security.database_keys import (
    DerivedDomainKey,
    MIGRATION_JOURNAL_AUTH_PURPOSE,
)
from src.security.infrastructure.migration_journal_repository import (
    AuthenticatedMigrationJournalRepository,
)
from src.security.infrastructure.monotonic_anchor_store import (
    InMemoryMonotonicSecurityAnchorStore,
)
from src.security.infrastructure.system import PlatformFilePermissionManager
from src.security.migration_journal import (
    MigrationPhase,
    capture_file_evidence,
    new_migration_journal,
    transition_migration_journal,
)
from src.security.migration_lock import ExclusiveMigrationLock
from src.security.monotonic_anchor import (
    SECURITY_ANCHOR_VERSION,
    SecurityAnchorState,
    SecurityAnchorStatus,
)


INSTALLATION_ID = "11111111-1111-4111-8111-111111111111"
DATABASE_CONTEXT_ID = "22222222-2222-4222-8222-222222222222"
MIGRATION_ID = "33333333-3333-4333-8333-333333333333"
DATABASE_KEY_ID = "44444444-4444-4444-8444-444444444444"
DMK_KEY_ID = "55555555-5555-4555-8555-555555555555"
REGISTRY_DIGEST = "a" * 64


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 22, 0, 0, tzinfo=UTC)

    def utc_now(self) -> datetime:
        self.value += timedelta(seconds=1)
        return self.value


def _fixture(
    tmp_path: Path,
    phase: MigrationPhase,
    *,
    backup_verifier=None,
    target_validator=None,
    target_reopener=None,
    fault_injector=None,
    replace_file=None,
    fsync_directory=None,
    guarded_synthetic_source: bool = True,
):
    root = tmp_path / f"root-{uuid.uuid4()}"
    root.mkdir(mode=0o700)
    paths = MigrationPaths.in_workspace(root)
    if guarded_synthetic_source:
        create_synthetic_source(
            paths.source,
            SyntheticScale(1, 1, 5, 1, 1, 1, 1),
        )
    else:
        with sqlite3.connect(paths.source) as connection:
            connection.execute("CREATE TABLE ordinary_data(value TEXT NOT NULL)")
            connection.execute("INSERT INTO ordinary_data VALUES ('foreign')")
    clock = Clock()
    state = new_migration_journal(
        migration_id=MIGRATION_ID,
        data_context_id=DATABASE_CONTEXT_ID,
        database_key_id=DATABASE_KEY_ID,
        database_key_generation=1,
        wrapping_dmk_key_id=DMK_KEY_ID,
        wrapping_dmk_generation=1,
        planned_paths={
            "source": paths.source.name,
            "backup": paths.backup.name,
            "target": paths.target.name,
        },
        source_evidence=capture_file_evidence(
            root, role="source", relative_path=paths.source.name
        ),
        now=clock.utc_now(),
    )
    evidence = dict(state.file_evidence)
    checks: tuple[str, ...] = ()
    phases = (
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
        MigrationPhase.SWAP_PREPARED,
        MigrationPhase.COMPLETED,
    )
    for next_phase in phases:
        if next_phase is MigrationPhase.SWAP_PREPARED and phase is not next_phase:
            continue
        if next_phase is MigrationPhase.COMPLETED and phase is not next_phase:
            continue
        if next_phase is MigrationPhase.SOURCE_VERIFIED:
            checks = ("source_identity", "source_integrity")
        elif next_phase is MigrationPhase.BACKUP_CREATED:
            shutil.copy2(paths.source, paths.backup)
            evidence["backup"] = capture_file_evidence(
                root, role="backup", relative_path=paths.backup.name
            )
        elif next_phase is MigrationPhase.BACKUP_VERIFIED:
            checks = (*checks, "backup_integrity")
        elif next_phase is MigrationPhase.TARGET_CREATED:
            paths.target.write_bytes(b"synthetic-encrypted-target")
            evidence["target"] = capture_file_evidence(
                root, role="target", relative_path=paths.target.name
            )
        elif next_phase is MigrationPhase.EXPORT_COMPLETED:
            evidence["target"] = capture_file_evidence(
                root, role="target", relative_path=paths.target.name
            )
            checks = (*checks, "export_committed")
        elif next_phase is MigrationPhase.VALIDATION_COMPLETED:
            checks = (*checks, "full_validation")
        elif next_phase is MigrationPhase.REOPEN_VERIFIED:
            checks = (*checks, "reopen_integrity")
        elif next_phase is MigrationPhase.COMPLETED:
            checks = (*checks, "synthetic_prototype_completed")
        state = transition_migration_journal(
            state,
            next_phase,
            now=clock.utc_now(),
            file_evidence=evidence,
            completed_checks=checks,
        )
        if next_phase is phase:
            break
    if phase in {MigrationPhase.FAILED, MigrationPhase.BLOCKED}:
        state = transition_migration_journal(
            state,
            phase,
            now=clock.utc_now(),
            error_class=f"synthetic_{phase.value}",
        )

    auth_key = DerivedDomainKey(
        MIGRATION_JOURNAL_AUTH_PURPOSE,
        1,
        b"j" * 32,
    )
    repository = AuthenticatedMigrationJournalRepository(
        root / "database-migration-journal-v1.json",
        PlatformFilePermissionManager(),
    )
    repository.create(state, auth_key)
    state, journal_digest = repository.load_with_digest(auth_key)
    anchor_state = SecurityAnchorState(
        anchor_version=SECURITY_ANCHOR_VERSION,
        installation_id=INSTALLATION_ID,
        database_context_id=DATABASE_CONTEXT_ID,
        dmk_key_id=DMK_KEY_ID,
        dmk_key_generation=1,
        anchor_revision=1,
        registry_high_water_mark=1,
        registry_sha256=REGISTRY_DIGEST,
        journal_revision=state.revision,
        journal_sha256=journal_digest,
        migration_generation=1,
        status=SecurityAnchorStatus.ACTIVE,
    )
    anchor = InMemoryMonotonicSecurityAnchorStore(anchor_state)
    lock = ExclusiveMigrationLock(
        root,
        installation_id=INSTALLATION_ID,
        database_context_id=DATABASE_CONTEXT_ID,
        migration_id=MIGRATION_ID,
        allowed_root=root,
    ).acquire()
    calls: list[str] = []
    orchestrator = PrototypeMigrationRecoveryOrchestrator(
        paths=paths,
        journal_repository=repository,
        journal_auth_key=auth_key,
        anchor_store=anchor,
        migration_lock=lock,
        registry_observer=lambda: (1, REGISTRY_DIGEST),
        migration_generation=1,
        clock=clock,
        backup_verifier=backup_verifier
        or (lambda _paths: calls.append("backup") or True),
        target_validator=target_validator
        or (lambda _paths: calls.append("validate") or True),
        target_reopener=target_reopener
        or (lambda _paths: calls.append("reopen") or True),
        fault_injector=fault_injector,
        replace_file=replace_file,
        fsync_directory=fsync_directory,
    )
    return paths, repository, auth_key, anchor, lock, orchestrator, calls


@pytest.mark.parametrize(
    "phase,expected_phase,expected_call",
    [
        (MigrationPhase.BACKUP_CREATED, MigrationPhase.BACKUP_VERIFIED, "backup"),
        (
            MigrationPhase.EXPORT_COMPLETED,
            MigrationPhase.VALIDATION_COMPLETED,
            "validate",
        ),
        (
            MigrationPhase.VALIDATION_STARTED,
            MigrationPhase.VALIDATION_COMPLETED,
            "validate",
        ),
        (
            MigrationPhase.VALIDATION_COMPLETED,
            MigrationPhase.REOPEN_VERIFIED,
            "reopen",
        ),
        (
            MigrationPhase.REOPEN_STARTED,
            MigrationPhase.REOPEN_VERIFIED,
            "reopen",
        ),
        (MigrationPhase.REOPEN_VERIFIED, MigrationPhase.COMPLETED, None),
    ],
)
def test_supported_recovery_phases_execute_one_idempotent_operation(
    tmp_path: Path,
    phase: MigrationPhase,
    expected_phase: MigrationPhase,
    expected_call: str | None,
) -> None:
    paths, repository, key, _anchor, lock, orchestrator, calls = _fixture(
        tmp_path, phase
    )
    source_before = paths.source.read_bytes()
    backup_before = paths.backup.read_bytes() if paths.backup.exists() else None
    try:
        result = orchestrator.recover()
        assert not result.blocked
        assert result.phase_after is expected_phase
        if expected_call is not None:
            assert calls == [expected_call]
        assert paths.source.read_bytes() == source_before
        if backup_before is not None:
            assert paths.backup.read_bytes() == backup_before
        assert repository.load(key).phase is expected_phase
    finally:
        lock.release()


@pytest.mark.parametrize(
    "phase",
    [
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_VERIFIED,
        MigrationPhase.TARGET_CREATION_STARTED,
        MigrationPhase.SWAP_PREPARED,
        MigrationPhase.FAILED,
        MigrationPhase.BLOCKED,
    ],
)
def test_ambiguous_or_disallowed_phases_block_without_file_operation(
    tmp_path: Path, phase: MigrationPhase
) -> None:
    paths, _repository, _key, _anchor, lock, orchestrator, calls = _fixture(
        tmp_path, phase
    )
    before = {path.name: path.read_bytes() for path in paths.root.iterdir() if path.is_file()}
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert calls == []
        after = {path.name: path.read_bytes() for path in paths.root.iterdir() if path.is_file()}
        assert after == before
    finally:
        lock.release()


def test_recovery_rejects_a_nonsynthetic_database_even_in_a_temporary_root(
    tmp_path: Path,
) -> None:
    paths, repository, key, _anchor, lock, orchestrator, calls = _fixture(
        tmp_path,
        MigrationPhase.BACKUP_CREATED,
        guarded_synthetic_source=False,
    )
    before = {
        path.name: path.read_bytes()
        for path in paths.root.iterdir()
        if path.is_file()
    }
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert result.error_code == "migration_recovery_blocked"
        assert calls == []
        assert repository.load(key).phase is MigrationPhase.BACKUP_CREATED
        assert before == {
            path.name: path.read_bytes()
            for path in paths.root.iterdir()
            if path.is_file()
        }
    finally:
        lock.release()


@pytest.mark.parametrize(
    "phase", [MigrationPhase.TARGET_CREATED, MigrationPhase.EXPORT_STARTED]
)
def test_identity_bound_target_rollback_never_deletes_source_backup_or_unknown(
    tmp_path: Path, phase: MigrationPhase
) -> None:
    paths, repository, key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, phase
    )
    unknown = paths.root / "unknown.keep"
    unknown.write_bytes(b"unknown")
    source_before = paths.source.read_bytes()
    backup_before = paths.backup.read_bytes()
    try:
        result = orchestrator.recover()
        assert not result.blocked
        assert result.phase_after is MigrationPhase.FAILED
        assert not paths.target.exists()
        quarantine = paths.root / (
            f".recovery-target-{MIGRATION_ID}.quarantine"
        )
        assert quarantine.read_bytes() == b"synthetic-encrypted-target"
        assert paths.source.read_bytes() == source_before
        assert paths.backup.read_bytes() == backup_before
        assert unknown.read_bytes() == b"unknown"
        assert repository.load(key).phase is MigrationPhase.FAILED
    finally:
        lock.release()


def _planned_anchor(anchor_state, replacement, key):
    return replace(
        anchor_state.committed_state(),
        anchor_revision=anchor_state.anchor_revision + 1,
        journal_revision=replacement.revision,
        journal_sha256=AuthenticatedMigrationJournalRepository.preview_digest(
            replacement, key
        ),
    )


def test_prepared_old_artifacts_are_monotonically_aborted_before_recovery(
    tmp_path: Path,
) -> None:
    paths, repository, key, anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.BACKUP_CREATED
    )
    state = repository.load(key)
    replacement = transition_migration_journal(
        state,
        MigrationPhase.BACKUP_VERIFIED,
        now=datetime(2026, 7, 22, 2, 0, tzinfo=UTC),
        completed_checks=(*state.completed_checks, "backup_integrity"),
    )
    prepared = anchor.prepare(anchor.read(), _planned_anchor(anchor.read(), replacement, key))
    try:
        result = orchestrator.recover()
        assert not result.blocked
        assert result.phase_after is MigrationPhase.BACKUP_VERIFIED
        assert anchor.read().pending is None
        assert anchor.read().anchor_revision > prepared.anchor_revision
        assert paths.source.exists() and paths.backup.exists()
    finally:
        lock.release()


def test_prepared_new_artifacts_are_committed_before_phase_is_blocked(
    tmp_path: Path,
) -> None:
    _paths, repository, key, anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.BACKUP_CREATED
    )
    state = repository.load(key)
    replacement = transition_migration_journal(
        state,
        MigrationPhase.BACKUP_VERIFIED,
        now=datetime(2026, 7, 22, 2, 0, tzinfo=UTC),
        completed_checks=(*state.completed_checks, "backup_integrity"),
    )
    planned = _planned_anchor(anchor.read(), replacement, key)
    anchor.prepare(anchor.read(), planned)
    repository.save(state, replacement, key)
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert anchor.read() == planned
        assert anchor.read().pending is None
    finally:
        lock.release()


def test_mixed_prepared_and_published_artifacts_block_anchor(tmp_path: Path) -> None:
    paths, repository, key, anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.BACKUP_CREATED
    )
    state = repository.load(key)
    planned_journal = transition_migration_journal(
        state,
        MigrationPhase.BACKUP_VERIFIED,
        now=datetime(2026, 7, 22, 2, 0, tzinfo=UTC),
        completed_checks=(*state.completed_checks, "backup_integrity"),
    )
    anchor.prepare(anchor.read(), _planned_anchor(anchor.read(), planned_journal, key))
    conflicting = transition_migration_journal(
        state,
        MigrationPhase.BLOCKED,
        now=datetime(2026, 7, 22, 2, 0, tzinfo=UTC),
        error_class="synthetic_conflict",
    )
    repository.save(state, conflicting, key)
    source_before = paths.source.read_bytes()
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert anchor.read().status is SecurityAnchorStatus.BLOCKED
        assert paths.source.read_bytes() == source_before
    finally:
        lock.release()


def test_repeated_recovery_is_stable_after_one_safe_operation(tmp_path: Path) -> None:
    paths, repository, key, _anchor, lock, orchestrator, calls = _fixture(
        tmp_path, MigrationPhase.BACKUP_CREATED
    )
    try:
        first = orchestrator.recover()
        snapshot = {path.name: path.read_bytes() for path in paths.root.iterdir() if path.is_file()}
        second = orchestrator.recover()
        assert not first.blocked
        assert second.blocked
        assert calls == ["backup"]
        assert repository.load(key).phase is MigrationPhase.BACKUP_VERIFIED
        assert snapshot == {
            path.name: path.read_bytes() for path in paths.root.iterdir() if path.is_file()
        }
    finally:
        lock.release()


def test_completed_cleanup_removes_only_generated_backup_and_target(
    tmp_path: Path,
) -> None:
    paths, repository, key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.COMPLETED
    )
    unknown = paths.root / "unknown.keep"
    unknown.write_bytes(b"unknown")
    source_before = paths.source.read_bytes()
    sidecars_before = {
        repository.path.name: repository.path.read_bytes(),
        lock.path.name: lock.path.read_bytes(),
    }
    try:
        result = orchestrator.recover()
        assert not result.blocked
        assert result.phase_after is MigrationPhase.COMPLETED
        assert paths.source.read_bytes() == source_before
        assert not paths.backup.exists()
        assert not paths.target.exists()
        assert (
            paths.root / f".recovery-backup-{MIGRATION_ID}.quarantine"
        ).exists()
        assert (
            paths.root / f".recovery-target-{MIGRATION_ID}.quarantine"
        ).exists()
        assert unknown.read_bytes() == b"unknown"
        assert repository.load(key).phase is MigrationPhase.COMPLETED
        assert repository.path.read_bytes() == sidecars_before[repository.path.name]
        assert lock.path.read_bytes() == sidecars_before[lock.path.name]
    finally:
        lock.release()


def test_completed_cleanup_resumes_missing_artifact_and_is_idempotent(
    tmp_path: Path,
) -> None:
    paths, _repository, _key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.COMPLETED
    )
    paths.target.unlink()
    source_before = paths.source.read_bytes()
    try:
        first = orchestrator.recover()
        second = orchestrator.recover()
        assert not first.blocked and not second.blocked
        assert paths.source.read_bytes() == source_before
        assert not paths.backup.exists() and not paths.target.exists()
    finally:
        lock.release()


def test_completed_cleanup_retains_owned_quarantine_after_process_abort(
    tmp_path: Path,
) -> None:
    paths, _repository, _key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.COMPLETED
    )
    quarantine = paths.root / (
        f".recovery-target-{MIGRATION_ID}.quarantine"
    )
    os.replace(paths.target, quarantine)
    try:
        result = orchestrator.recover()
        assert not result.blocked
        assert quarantine.read_bytes() == b"synthetic-encrypted-target"
        assert not paths.target.exists()
        assert not paths.backup.exists()
        assert (
            paths.root / f".recovery-backup-{MIGRATION_ID}.quarantine"
        ).exists()
        assert paths.source.exists()
    finally:
        lock.release()


def test_completed_cleanup_blocks_swapped_backup_and_preserves_foreign(
    tmp_path: Path,
) -> None:
    paths, _repository, _key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.COMPLETED
    )
    owned = paths.root / "owned-backup.keep"
    os.replace(paths.backup, owned)
    paths.backup.write_bytes(b"foreign-backup")
    source_before = paths.source.read_bytes()
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert paths.backup.read_bytes() == b"foreign-backup"
        assert owned.exists()
        assert paths.target.exists()
        assert paths.source.read_bytes() == source_before
    finally:
        lock.release()
