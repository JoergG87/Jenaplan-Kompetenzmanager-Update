from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from src.security.migration_journal import MigrationPhase

from test_security_migration_recovery import _fixture


@pytest.mark.parametrize(
    "phase,callback_name,error,allowed_phases",
    [
        (MigrationPhase.BACKUP_CREATED, "backup_verifier", OSError(errno.ENOSPC, "private"), {MigrationPhase.BACKUP_CREATED}),
        (MigrationPhase.EXPORT_COMPLETED, "target_validator", PermissionError("private"), {MigrationPhase.VALIDATION_STARTED}),
        (MigrationPhase.VALIDATION_COMPLETED, "target_reopener", OSError(errno.EIO, "private"), {MigrationPhase.REOPEN_STARTED}),
    ],
)
def test_callback_faults_fail_closed_without_leaking_details(
    tmp_path: Path,
    phase: MigrationPhase,
    callback_name: str,
    error: OSError,
    allowed_phases: set[MigrationPhase],
) -> None:
    def fail(_paths):
        raise error

    options = {callback_name: fail}
    paths, repository, key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, phase, **options
    )
    before = {path.name: path.read_bytes() for path in paths.root.iterdir() if path.is_file()}
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert "private" not in repr(result)
        assert repository.load(key).phase in allowed_phases
        after = {path.name: path.read_bytes() for path in paths.root.iterdir() if path.is_file()}
        for protected in (paths.source.name, paths.backup.name, paths.target.name):
            if protected in before:
                assert after[protected] == before[protected]
        if phase is MigrationPhase.BACKUP_CREATED:
            assert after == before
    finally:
        lock.release()


def test_journal_enospc_leaves_old_journal_and_prepared_anchor(tmp_path: Path) -> None:
    paths, repository, key, anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.BACKUP_CREATED
    )
    original_save = repository.save

    def fail_save(*_args, **_kwargs):
        raise OSError(errno.ENOSPC, "private")

    repository.save = fail_save
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert repository.load(key).phase is MigrationPhase.BACKUP_CREATED
        assert anchor.read().pending is not None
        assert paths.source.exists() and paths.backup.exists()
    finally:
        repository.save = original_save
        lock.release()


def test_anchor_advance_fault_leaves_new_journal_for_next_reconcile(
    tmp_path: Path,
) -> None:
    _paths, repository, key, anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.BACKUP_CREATED
    )
    original_advance = anchor.advance

    def fail_advance(*_args, **_kwargs):
        raise OSError(errno.ENOSPC, "private")

    anchor.advance = fail_advance
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert repository.load(key).phase is MigrationPhase.BACKUP_VERIFIED
        assert anchor.read().pending is not None
        anchor.advance = original_advance
        second = orchestrator.recover()
        assert second.blocked
        assert anchor.read().pending is None
    finally:
        anchor.advance = original_advance
        lock.release()


@pytest.mark.parametrize("role", ["source", "backup"])
def test_unreadable_required_file_blocks_without_mutation(
    tmp_path: Path, role: str
) -> None:
    paths, repository, key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.BACKUP_CREATED
    )
    candidate = getattr(paths, role)
    candidate.chmod(0)
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert repository.load(key).phase is MigrationPhase.BACKUP_CREATED
    finally:
        candidate.chmod(0o600)
        lock.release()


def test_unexpected_journal_temporary_file_blocks_before_operation(
    tmp_path: Path,
) -> None:
    paths, repository, key, _anchor, lock, orchestrator, calls = _fixture(
        tmp_path, MigrationPhase.BACKUP_CREATED
    )
    journal_before = repository.path.read_bytes()
    unexpected = paths.root / ".database-migration-journal-unexpected.tmp"
    unexpected.write_bytes(b"unknown")
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert calls == []
        assert unexpected.read_bytes() == b"unknown"
        assert repository.path.read_bytes() == journal_before
    finally:
        lock.release()


def test_replace_enospc_preserves_identity_bound_target(
    tmp_path: Path,
) -> None:
    def fail_replace(_source, _destination):
        raise OSError(errno.ENOSPC, "private")

    paths, repository, key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path,
        MigrationPhase.TARGET_CREATED,
        replace_file=fail_replace,
    )
    target_before = paths.target.read_bytes()
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert paths.target.read_bytes() == target_before
        assert repository.load(key).phase is MigrationPhase.ROLLBACK_STARTED
    finally:
        lock.release()


def test_fsync_fault_retains_owned_quarantine_and_never_deletes_other_files(
    tmp_path: Path,
) -> None:
    calls = 0

    def fail_first_fsync(_directory: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError(errno.EIO, "private")

    paths, _repository, _key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path,
        MigrationPhase.TARGET_CREATED,
        fsync_directory=fail_first_fsync,
    )
    source_before = paths.source.read_bytes()
    backup_before = paths.backup.read_bytes()
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert paths.source.read_bytes() == source_before
        assert paths.backup.read_bytes() == backup_before
        quarantine = list(paths.root.glob(".recovery-target-*.quarantine"))
        assert len(quarantine) == 1
        assert quarantine[0].read_bytes() == b"synthetic-encrypted-target"
    finally:
        lock.release()


def test_target_swap_is_blocked_and_foreign_file_is_preserved(tmp_path: Path) -> None:
    paths, repository, key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.TARGET_CREATED
    )
    displaced = paths.root / "displaced-owned-target.keep"
    os.replace(paths.target, displaced)
    paths.target.write_bytes(b"foreign")
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert paths.target.read_bytes() == b"foreign"
        assert displaced.read_bytes() == b"synthetic-encrypted-target"
        assert repository.load(key).phase is MigrationPhase.TARGET_CREATED
    finally:
        lock.release()


def test_quarantine_creation_race_never_clobbers_the_foreign_file(
    tmp_path: Path,
) -> None:
    holder = {}

    def create_foreign_quarantine(point: str) -> None:
        if point != "before_target_quarantine":
            return
        paths = holder["paths"]
        quarantine = paths.root / (
            ".recovery-target-33333333-3333-4333-8333-333333333333.quarantine"
        )
        quarantine.write_bytes(b"foreign-quarantine")

    paths, repository, key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path,
        MigrationPhase.TARGET_CREATED,
        fault_injector=create_foreign_quarantine,
    )
    holder["paths"] = paths
    target_before = paths.target.read_bytes()
    try:
        result = orchestrator.recover()
        assert result.blocked
        quarantine = paths.root / (
            ".recovery-target-33333333-3333-4333-8333-333333333333.quarantine"
        )
        assert quarantine.read_bytes() == b"foreign-quarantine"
        assert paths.target.read_bytes() == target_before
        assert repository.load(key).phase is MigrationPhase.ROLLBACK_STARTED
    finally:
        lock.release()


def test_quarantine_swap_at_final_identity_check_preserves_foreign_file(
    tmp_path: Path,
) -> None:
    holder = {}

    def swap_at_last_hook(point: str) -> None:
        if point != "before_quarantine_final_verification":
            return
        paths = holder["paths"]
        quarantine = next(paths.root.glob(".recovery-target-*.quarantine"))
        displaced = paths.root / "owned-quarantine.keep"
        os.replace(quarantine, displaced)
        quarantine.write_bytes(b"foreign-quarantine")

    paths, _repository, _key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path,
        MigrationPhase.TARGET_CREATED,
        fault_injector=swap_at_last_hook,
    )
    holder["paths"] = paths
    try:
        result = orchestrator.recover()
        assert result.blocked
        quarantine = next(paths.root.glob(".recovery-target-*.quarantine"))
        assert quarantine.read_bytes() == b"foreign-quarantine"
        assert (paths.root / "owned-quarantine.keep").read_bytes() == (
            b"synthetic-encrypted-target"
        )
    finally:
        lock.release()


def test_recovery_never_uses_path_unlink_for_quarantined_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths, repository, key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.TARGET_CREATED
    )

    def forbidden_unlink(*_args, **_kwargs):
        raise AssertionError("pathname unlink is unsafe after an identity check")

    monkeypatch.setattr(Path, "unlink", forbidden_unlink)
    try:
        result = orchestrator.recover()
        assert not result.blocked
        assert repository.load(key).phase is MigrationPhase.FAILED
        assert not paths.target.exists()
        quarantine = paths.root / (
            ".recovery-target-33333333-3333-4333-8333-333333333333.quarantine"
        )
        assert quarantine.read_bytes() == b"synthetic-encrypted-target"
    finally:
        lock.release()


def test_unsanitized_exception_code_is_not_returned(tmp_path: Path) -> None:
    class LeakyError(RuntimeError):
        code = "Private path: /secret/key"

    def fail(_paths):
        raise LeakyError("private payload")

    _paths, _repository, _key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path,
        MigrationPhase.BACKUP_CREATED,
        backup_verifier=fail,
    )
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert result.error_code == "migration_recovery_blocked"
        assert "secret" not in repr(result)
        assert "private" not in repr(result).lower()
    finally:
        lock.release()


def test_system_exit_from_interruption_hook_is_not_masked(tmp_path: Path) -> None:
    def interrupt(_paths):
        raise SystemExit(73)

    _paths, _repository, _key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path,
        MigrationPhase.BACKUP_CREATED,
        backup_verifier=interrupt,
    )
    try:
        with pytest.raises(SystemExit, match="73"):
            orchestrator.recover()
    finally:
        lock.release()


def test_symlink_root_escape_is_blocked_without_touching_outside_file(
    tmp_path: Path,
) -> None:
    paths, repository, key, _anchor, lock, orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.TARGET_CREATED
    )
    outside = tmp_path / "outside.keep"
    outside.write_bytes(b"outside")
    paths.target.unlink()
    paths.target.symlink_to(outside)
    try:
        result = orchestrator.recover()
        assert result.blocked
        assert outside.read_bytes() == b"outside"
        assert paths.target.is_symlink()
        assert repository.load(key).phase is MigrationPhase.TARGET_CREATED
    finally:
        lock.release()
