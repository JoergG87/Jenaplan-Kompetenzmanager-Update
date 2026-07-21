from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import stat
import uuid

import pytest

from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import derive_migration_journal_auth_key
from src.security.infrastructure.migration_journal_repository import (
    AuthenticatedMigrationJournalRepository,
    MIGRATION_JOURNAL_FILENAME,
)
from src.security.infrastructure.system import PlatformFilePermissionManager
from src.security.migration_journal import (
    MIGRATION_JOURNAL_VERSION,
    MigrationJournalError,
    MigrationPhase,
    MigrationRecoveryEvaluator,
    RecoveryDecision,
    allowed_migration_transitions,
    capture_file_evidence,
    evaluate_persisted_recovery,
    new_migration_journal,
    transition_migration_journal,
    validate_migration_journal,
)


NOW = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)


def _dmk() -> LoadedDataMasterKey:
    return LoadedDataMasterKey(str(uuid.uuid4()), 1, secrets.token_bytes(32))


def _paths(tmp_path: Path) -> dict[str, str]:
    return {
        "source": "synthetic-source.sqlite",
        "backup": "run-1-verified-backup.sqlite",
        "target": "run-1-encrypted.sqlcipher",
    }


def _environment(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    planned = _paths(tmp_path)
    (tmp_path / planned["source"]).write_bytes(secrets.token_bytes(257))
    dmk = _dmk()
    migration_id = str(uuid.uuid4())
    auth_key = derive_migration_journal_auth_key(dmk, migration_id=migration_id)
    state = new_migration_journal(
        migration_id=migration_id,
        data_context_id=str(uuid.uuid4()),
        database_key_id=str(uuid.uuid4()),
        database_key_generation=1,
        wrapping_dmk_key_id=dmk.key_id,
        wrapping_dmk_generation=dmk.generation,
        planned_paths=planned,
        source_evidence=capture_file_evidence(
            tmp_path, role="source", relative_path=planned["source"]
        ),
        now=NOW,
    )
    repository = AuthenticatedMigrationJournalRepository(
        tmp_path / "journal" / MIGRATION_JOURNAL_FILENAME,
        PlatformFilePermissionManager(),
    )
    return planned, dmk, auth_key, state, repository


def _save_transition(
    repository,
    auth_key,
    state,
    phase,
    *,
    evidence=None,
    checks=None,
    error_class=None,
):
    replacement = transition_migration_journal(
        state,
        phase,
        now=NOW,
        file_evidence=evidence,
        completed_checks=checks,
        error_class=error_class,
    )
    repository.save(state, replacement, auth_key)
    return replacement


def test_complete_legal_state_run_is_persistent_and_terminal(tmp_path: Path) -> None:
    planned, _dmk_value, auth_key, state, repository = _environment(tmp_path)
    repository.create(state, auth_key)
    for phase in (
        MigrationPhase.PREFLIGHT_STARTED,
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_STARTED,
    ):
        state = _save_transition(repository, auth_key, state, phase)
    (tmp_path / planned["backup"]).write_bytes(
        (tmp_path / planned["source"]).read_bytes()
    )
    evidence = dict(state.file_evidence)
    evidence["backup"] = capture_file_evidence(
        tmp_path, role="backup", relative_path=planned["backup"]
    )
    state = _save_transition(
        repository, auth_key, state, MigrationPhase.BACKUP_CREATED, evidence=evidence
    )
    state = _save_transition(
        repository,
        auth_key,
        state,
        MigrationPhase.BACKUP_VERIFIED,
        checks=("source_integrity", "backup_integrity"),
    )
    state = _save_transition(
        repository, auth_key, state, MigrationPhase.TARGET_CREATION_STARTED
    )
    (tmp_path / planned["target"]).write_bytes(secrets.token_bytes(4096))
    evidence = dict(state.file_evidence)
    evidence["target"] = capture_file_evidence(
        tmp_path, role="target", relative_path=planned["target"]
    )
    state = _save_transition(
        repository, auth_key, state, MigrationPhase.TARGET_CREATED, evidence=evidence
    )
    for phase in (
        MigrationPhase.EXPORT_STARTED,
        MigrationPhase.EXPORT_COMPLETED,
        MigrationPhase.VALIDATION_STARTED,
        MigrationPhase.VALIDATION_COMPLETED,
        MigrationPhase.REOPEN_STARTED,
        MigrationPhase.REOPEN_VERIFIED,
        MigrationPhase.COMPLETED,
    ):
        state = _save_transition(repository, auth_key, state, phase)

    reloaded = repository.load(auth_key)
    assert reloaded == state
    assert reloaded.phase is MigrationPhase.COMPLETED
    assert len(reloaded.history) == reloaded.revision + 1
    with pytest.raises(MigrationJournalError) as terminal:
        transition_migration_journal(
            state, MigrationPhase.FAILED, now=NOW, error_class="late_failure"
        )
    assert terminal.value.code == "migration_journal_transition_illegal"
    assert repository.delete_completed(state, auth_key)
    assert not repository.delete_completed(state, auth_key)


def test_every_declared_swap_and_rollback_transition_is_legal(tmp_path: Path) -> None:
    _planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    main = (
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
        MigrationPhase.SWAP_STARTED,
        MigrationPhase.SWAP_COMPLETED,
        MigrationPhase.POST_SWAP_VERIFIED,
        MigrationPhase.COMPLETED,
    )
    for phase in main:
        state = transition_migration_journal(state, phase, now=NOW)
    assert state.phase is MigrationPhase.COMPLETED

    _planned, _dmk_value, _auth_key, rollback, _repository = _environment(tmp_path / "r")
    for phase in main[:7]:
        rollback = transition_migration_journal(rollback, phase, now=NOW)
    rollback = transition_migration_journal(
        rollback, MigrationPhase.ROLLBACK_STARTED, now=NOW
    )
    rollback = transition_migration_journal(
        rollback, MigrationPhase.ROLLBACK_COMPLETED, now=NOW
    )
    rollback = transition_migration_journal(
        rollback,
        MigrationPhase.FAILED,
        now=NOW,
        error_class="simulated_failure",
    )
    assert rollback.phase is MigrationPhase.FAILED


@pytest.mark.parametrize(
    ("source_steps", "illegal"),
    [
        ((), MigrationPhase.BACKUP_CREATED),
        ((MigrationPhase.PREFLIGHT_STARTED,), MigrationPhase.TARGET_CREATED),
        (
            (MigrationPhase.PREFLIGHT_STARTED, MigrationPhase.SOURCE_VERIFIED),
            MigrationPhase.EXPORT_STARTED,
        ),
    ],
)
def test_illegal_phase_jumps_are_rejected(
    tmp_path: Path, source_steps, illegal: MigrationPhase
) -> None:
    _planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    for phase in source_steps:
        state = transition_migration_journal(state, phase, now=NOW)
    with pytest.raises(MigrationJournalError) as caught:
        transition_migration_journal(state, illegal, now=NOW)
    assert caught.value.code == "migration_journal_transition_illegal"


@pytest.mark.parametrize(
    "check",
    [
        "source_identity",
        "source_integrity",
        "backup_integrity",
        "export_committed",
        "full_validation",
        "reopen_integrity",
        "synthetic_prototype_completed",
    ],
)
def test_reserved_checks_cannot_be_claimed_before_their_phase(
    tmp_path: Path, check: str
) -> None:
    _planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    with pytest.raises(MigrationJournalError) as caught:
        transition_migration_journal(
            state,
            MigrationPhase.PREFLIGHT_STARTED,
            now=NOW,
            completed_checks=(check,),
        )
    assert caught.value.code == "migration_journal_check_phase_invalid"


def test_unknown_check_is_rejected(tmp_path: Path) -> None:
    _planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    with pytest.raises(MigrationJournalError) as caught:
        transition_migration_journal(
            state,
            MigrationPhase.PREFLIGHT_STARTED,
            now=NOW,
            completed_checks=("unregistered_check",),
        )
    assert caught.value.code == "migration_journal_checks_unknown"


def test_journal_timestamps_must_be_monotonic(tmp_path: Path) -> None:
    _planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    earlier = NOW.replace(hour=11)
    with pytest.raises(MigrationJournalError) as caught:
        transition_migration_journal(
            state, MigrationPhase.PREFLIGHT_STARTED, now=earlier
        )
    assert caught.value.code == "migration_journal_history_invalid"


def test_every_allowed_and_forbidden_transition_is_exercised(tmp_path: Path) -> None:
    _planned, _dmk_value, _auth_key, initial, _repository = _environment(tmp_path)
    states = {MigrationPhase.NOT_STARTED: initial}
    pending = [MigrationPhase.NOT_STARTED]
    while pending:
        source = pending.pop(0)
        for target in allowed_migration_transitions(source):
            if target in states:
                continue
            kwargs = (
                {"error_class": "matrix_failure"}
                if target in {MigrationPhase.FAILED, MigrationPhase.BLOCKED}
                else {}
            )
            states[target] = transition_migration_journal(
                states[source], target, now=NOW, **kwargs
            )
            pending.append(target)
    assert set(states) == set(MigrationPhase)

    for source in MigrationPhase:
        allowed = allowed_migration_transitions(source)
        for target in MigrationPhase:
            kwargs = (
                {"error_class": "matrix_failure"}
                if target in {MigrationPhase.FAILED, MigrationPhase.BLOCKED}
                else {}
            )
            if target in allowed:
                assert (
                    transition_migration_journal(
                        states[source], target, now=NOW, **kwargs
                    ).phase
                    is target
                )
            else:
                with pytest.raises(MigrationJournalError) as caught:
                    transition_migration_journal(
                        states[source], target, now=NOW, **kwargs
                    )
                assert caught.value.code == "migration_journal_transition_illegal"


def test_authenticated_atomic_restart_and_wrong_key(tmp_path: Path) -> None:
    _planned, _dmk_value, auth_key, state, repository = _environment(tmp_path)
    repository.create(state, auth_key)
    replacement = transition_migration_journal(
        state, MigrationPhase.PREFLIGHT_STARTED, now=NOW
    )
    repository.save(state, replacement, auth_key)
    restarted = AuthenticatedMigrationJournalRepository(
        repository.path, PlatformFilePermissionManager()
    )
    assert restarted.load(auth_key) == replacement
    wrong_key = derive_migration_journal_auth_key(
        _dmk(), migration_id=state.migration_id
    )
    with pytest.raises(MigrationJournalError) as caught:
        restarted.load(wrong_key)
    assert caught.value.code == "migration_journal_authentication_failed"
    if os.name == "posix":
        assert stat.S_IMODE(repository.path.stat().st_mode) == 0o600
        assert stat.S_IMODE(repository.path.parent.stat().st_mode) == 0o700


def test_truncated_invalid_json_and_manual_manipulation_fail_closed(
    tmp_path: Path,
) -> None:
    _planned, _dmk_value, auth_key, state, repository = _environment(tmp_path)
    repository.create(state, auth_key)
    original = repository.path.read_bytes()
    for corruption in (original[: len(original) // 2], b"not-json"):
        repository.path.write_bytes(corruption)
        with pytest.raises(MigrationJournalError):
            repository.load(auth_key)
    repository.path.write_bytes(original)
    payload = json.loads(original)
    payload["phase"] = "completed"
    repository.path.write_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    )
    with pytest.raises(MigrationJournalError) as manipulated:
        repository.load(auth_key)
    assert manipulated.value.code == "migration_journal_authentication_failed"


def test_unknown_version_with_valid_hmac_is_blocked(tmp_path: Path) -> None:
    _planned, _dmk_value, auth_key, state, repository = _environment(tmp_path)
    repository.create(state, auth_key)
    payload = json.loads(repository.path.read_bytes())
    payload.pop("auth_tag")
    payload["journal_version"] = MIGRATION_JOURNAL_VERSION + 1
    authenticated = json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    tag = hmac.new(auth_key.key_material, authenticated, hashlib.sha256).digest()
    import base64

    payload["auth_tag"] = base64.urlsafe_b64encode(tag).rstrip(b"=").decode("ascii")
    repository.path.write_bytes(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    )
    assert (
        evaluate_persisted_recovery(repository, auth_key, workspace=tmp_path)
        is RecoveryDecision.BLOCK_MANUAL_REVIEW
    )


def test_leftover_temp_file_is_detected_without_discarding_last_state(
    tmp_path: Path,
) -> None:
    _planned, _dmk_value, auth_key, state, repository = _environment(tmp_path)
    repository.create(state, auth_key)
    original = repository.path.read_bytes()
    leftover = repository.path.parent / ".database-migration-journal-crash.tmp"
    leftover.write_bytes(secrets.token_bytes(31))
    with pytest.raises(MigrationJournalError) as caught:
        repository.load(auth_key)
    assert caught.value.code == "migration_journal_temporary_present"
    assert repository.path.read_bytes() == original
    assert leftover.exists()


def test_journal_file_and_parent_directory_symlinks_are_rejected(
    tmp_path: Path,
) -> None:
    _planned, _dmk_value, auth_key, state, repository = _environment(tmp_path)
    repository.create(state, auth_key)
    real = tmp_path / "real-journal.json"
    real.write_bytes(repository.path.read_bytes())
    repository.path.unlink()
    repository.path.symlink_to(real)
    with pytest.raises(MigrationJournalError):
        repository.load(auth_key)

    actual_directory = tmp_path / "actual-journal"
    actual_directory.mkdir()
    linked_directory = tmp_path / "linked-journal"
    linked_directory.symlink_to(actual_directory, target_is_directory=True)
    linked_repository = AuthenticatedMigrationJournalRepository(
        linked_directory / MIGRATION_JOURNAL_FILENAME,
        PlatformFilePermissionManager(),
    )
    with pytest.raises(MigrationJournalError) as parent:
        linked_repository.create(state, auth_key)
    assert parent.value.code == "migration_journal_directory_invalid"


def test_source_hash_identity_missing_file_and_symlink_block_recovery(
    tmp_path: Path,
) -> None:
    planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    evaluator = MigrationRecoveryEvaluator()
    assert evaluator.decide(state, workspace=tmp_path) is RecoveryDecision.NO_ACTION

    source = tmp_path / planned["source"]
    source.write_bytes(secrets.token_bytes(source.stat().st_size))
    assert (
        evaluator.decide(state, workspace=tmp_path)
        is RecoveryDecision.BLOCK_MANUAL_REVIEW
    )
    source.unlink()
    assert (
        evaluator.decide(state, workspace=tmp_path)
        is RecoveryDecision.BLOCK_MANUAL_REVIEW
    )
    outside = tmp_path.parent / f"outside-{uuid.uuid4()}.bin"
    outside.write_bytes(secrets.token_bytes(257))
    source.symlink_to(outside)
    try:
        assert (
            evaluator.decide(state, workspace=tmp_path)
            is RecoveryDecision.BLOCK_MANUAL_REVIEW
        )
    finally:
        outside.unlink(missing_ok=True)


def test_source_mtime_change_blocks_recovery_even_when_bytes_match(
    tmp_path: Path,
) -> None:
    planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    source = tmp_path / planned["source"]
    status = source.stat()
    os.utime(
        source,
        ns=(status.st_atime_ns, status.st_mtime_ns + 1_000_000_000),
    )
    assert (
        MigrationRecoveryEvaluator().decide(state, workspace=tmp_path)
        is RecoveryDecision.BLOCK_MANUAL_REVIEW
    )


def test_unbound_backup_or_target_blocks_after_write_ahead_state(tmp_path: Path) -> None:
    planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    for phase in (
        MigrationPhase.PREFLIGHT_STARTED,
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_STARTED,
    ):
        state = transition_migration_journal(state, phase, now=NOW)
    (tmp_path / planned["backup"]).write_bytes(secrets.token_bytes(19))
    assert (
        MigrationRecoveryEvaluator().decide(state, workspace=tmp_path)
        is RecoveryDecision.BLOCK_MANUAL_REVIEW
    )


def test_export_in_progress_allows_hash_change_but_never_identity_change(
    tmp_path: Path,
) -> None:
    planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    for phase in (
        MigrationPhase.PREFLIGHT_STARTED,
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_STARTED,
    ):
        state = transition_migration_journal(state, phase, now=NOW)
    (tmp_path / planned["backup"]).write_bytes(secrets.token_bytes(40))
    evidence = dict(state.file_evidence)
    evidence["backup"] = capture_file_evidence(
        tmp_path, role="backup", relative_path=planned["backup"]
    )
    state = transition_migration_journal(
        state,
        MigrationPhase.BACKUP_CREATED,
        now=NOW,
        file_evidence=evidence,
        completed_checks=("source_identity", "source_integrity"),
    )
    state = transition_migration_journal(
        state,
        MigrationPhase.BACKUP_VERIFIED,
        now=NOW,
        completed_checks=(*state.completed_checks, "backup_integrity"),
    )
    state = transition_migration_journal(
        state, MigrationPhase.TARGET_CREATION_STARTED, now=NOW
    )
    target = tmp_path / planned["target"]
    target.write_bytes(secrets.token_bytes(64))
    evidence = dict(state.file_evidence)
    evidence["target"] = capture_file_evidence(
        tmp_path, role="target", relative_path=planned["target"]
    )
    state = transition_migration_journal(
        state, MigrationPhase.TARGET_CREATED, now=NOW, file_evidence=evidence
    )
    with target.open("ab") as stream:
        stream.write(secrets.token_bytes(17))
    evaluator = MigrationRecoveryEvaluator()
    assert evaluator.decide(state, workspace=tmp_path) is RecoveryDecision.ROLLBACK_TARGET
    state = transition_migration_journal(state, MigrationPhase.EXPORT_STARTED, now=NOW)
    with target.open("ab") as stream:
        stream.write(secrets.token_bytes(33))
    assert evaluator.decide(state, workspace=tmp_path) is RecoveryDecision.ROLLBACK_TARGET

    replacement = tmp_path / "replacement.tmp"
    replacement.write_bytes(target.read_bytes())
    os.replace(replacement, target)
    assert (
        evaluator.decide(state, workspace=tmp_path)
        is RecoveryDecision.BLOCK_MANUAL_REVIEW
    )


def test_rollback_started_accepts_only_owned_target_or_its_absence(
    tmp_path: Path,
) -> None:
    planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    for phase in (
        MigrationPhase.PREFLIGHT_STARTED,
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_STARTED,
    ):
        state = transition_migration_journal(state, phase, now=NOW)
    (tmp_path / planned["backup"]).write_bytes(secrets.token_bytes(40))
    evidence = dict(state.file_evidence)
    evidence["backup"] = capture_file_evidence(
        tmp_path, role="backup", relative_path=planned["backup"]
    )
    state = transition_migration_journal(
        state,
        MigrationPhase.BACKUP_CREATED,
        now=NOW,
        file_evidence=evidence,
        completed_checks=("source_identity", "source_integrity"),
    )
    state = transition_migration_journal(
        state,
        MigrationPhase.BACKUP_VERIFIED,
        now=NOW,
        completed_checks=(*state.completed_checks, "backup_integrity"),
    )
    state = transition_migration_journal(
        state, MigrationPhase.TARGET_CREATION_STARTED, now=NOW
    )
    target = tmp_path / planned["target"]
    target.write_bytes(secrets.token_bytes(64))
    evidence = dict(state.file_evidence)
    evidence["target"] = capture_file_evidence(
        tmp_path, role="target", relative_path=planned["target"]
    )
    state = transition_migration_journal(
        state, MigrationPhase.TARGET_CREATED, now=NOW, file_evidence=evidence
    )
    state = transition_migration_journal(
        state, MigrationPhase.EXPORT_STARTED, now=NOW
    )
    with target.open("ab") as stream:
        stream.write(secrets.token_bytes(31))
    state = transition_migration_journal(
        state, MigrationPhase.ROLLBACK_STARTED, now=NOW
    )
    evaluator = MigrationRecoveryEvaluator()
    assert evaluator.decide(state, workspace=tmp_path) is RecoveryDecision.ROLLBACK_TARGET
    target.unlink()
    assert evaluator.decide(state, workspace=tmp_path) is RecoveryDecision.NO_ACTION
    completed = transition_migration_journal(
        state, MigrationPhase.ROLLBACK_COMPLETED, now=NOW
    )
    assert evaluator.decide(completed, workspace=tmp_path) is RecoveryDecision.NO_ACTION


def test_advanced_phase_without_required_evidence_blocks(tmp_path: Path) -> None:
    _planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    for phase in (
        MigrationPhase.PREFLIGHT_STARTED,
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_STARTED,
        MigrationPhase.BACKUP_CREATED,
    ):
        state = transition_migration_journal(state, phase, now=NOW)
    assert (
        MigrationRecoveryEvaluator().decide(state, workspace=tmp_path)
        is RecoveryDecision.BLOCK_MANUAL_REVIEW
    )


def test_required_phase_checks_cannot_be_omitted_from_recovery(
    tmp_path: Path,
) -> None:
    planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    for phase in (
        MigrationPhase.PREFLIGHT_STARTED,
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_STARTED,
    ):
        state = transition_migration_journal(state, phase, now=NOW)
    (tmp_path / planned["backup"]).write_bytes(secrets.token_bytes(40))
    evidence = dict(state.file_evidence)
    evidence["backup"] = capture_file_evidence(
        tmp_path, role="backup", relative_path=planned["backup"]
    )
    state = transition_migration_journal(
        state, MigrationPhase.BACKUP_CREATED, now=NOW, file_evidence=evidence
    )
    assert (
        MigrationRecoveryEvaluator().decide(state, workspace=tmp_path)
        is RecoveryDecision.BLOCK_MANUAL_REVIEW
    )


def test_file_evidence_cannot_be_removed_or_rebound(tmp_path: Path) -> None:
    _planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    source = state.file_evidence["source"]
    with pytest.raises(MigrationJournalError) as removed:
        transition_migration_journal(
            state,
            MigrationPhase.PREFLIGHT_STARTED,
            now=NOW,
            file_evidence={},
        )
    assert removed.value.code == "migration_journal_file_evidence_rebinding"
    with pytest.raises(MigrationJournalError) as rebound:
        transition_migration_journal(
            state,
            MigrationPhase.PREFLIGHT_STARTED,
            now=NOW,
            file_evidence={"source": replace(source, file_id=source.file_id + 1)},
        )
    assert rebound.value.code == "migration_journal_file_evidence_rebinding"
    with pytest.raises(TypeError):
        state.file_evidence["source"] = source  # type: ignore[index]
    with pytest.raises(TypeError):
        state.planned_paths["source"] = "replacement.sqlite"  # type: ignore[index]


def test_loaded_error_state_semantics_are_strict(tmp_path: Path) -> None:
    _planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    failed = transition_migration_journal(
        state, MigrationPhase.FAILED, now=NOW, error_class="simulated_failure"
    )
    missing_error = replace(
        failed,
        error_class=None,
        history=(*failed.history[:-1], replace(failed.history[-1], error_class=None)),
    )
    with pytest.raises(MigrationJournalError) as missing:
        validate_migration_journal(missing_error)
    assert missing.value.code == "migration_journal_history_invalid"

    unexpected_error = replace(
        state,
        error_class="unexpected_error",
        history=(replace(state.history[0], error_class="unexpected_error"),),
    )
    with pytest.raises(MigrationJournalError) as unexpected:
        validate_migration_journal(unexpected_error)
    assert unexpected.value.code == "migration_journal_history_invalid"


def test_recovery_decisions_are_idempotent_and_failed_never_continues(
    tmp_path: Path,
) -> None:
    _planned, _dmk_value, _auth_key, state, _repository = _environment(tmp_path)
    evaluator = MigrationRecoveryEvaluator()
    first = evaluator.decide(state, workspace=tmp_path)
    second = evaluator.decide(state, workspace=tmp_path)
    assert first is second is RecoveryDecision.NO_ACTION
    failed = transition_migration_journal(
        state,
        MigrationPhase.FAILED,
        now=NOW,
        error_class="preflight_failure",
    )
    assert (
        evaluator.decide(failed, workspace=tmp_path)
        is RecoveryDecision.BLOCK_MANUAL_REVIEW
    )


def test_completed_journal_cleanup_is_explicit_idempotent_and_secret_free(
    tmp_path: Path,
) -> None:
    _planned, dmk, auth_key, state, repository = _environment(tmp_path)
    repository.create(state, auth_key)
    for phase in (
        MigrationPhase.PREFLIGHT_STARTED,
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_STARTED,
        MigrationPhase.FAILED,
    ):
        if phase is MigrationPhase.FAILED:
            state = transition_migration_journal(
                state, phase, now=NOW, error_class="simulated_failure"
            )
        else:
            state = transition_migration_journal(state, phase, now=NOW)
    raw = repository.path.read_bytes()
    assert dmk.key_material not in raw
    assert auth_key.key_material not in raw
    assert dmk.key_material.hex().encode("ascii") not in raw
    assert auth_key.key_material.hex().encode("ascii") not in raw
    with pytest.raises(MigrationJournalError) as not_completed:
        repository.delete_completed(state, auth_key)
    assert not_completed.value.code == "migration_journal_delete_not_completed"
