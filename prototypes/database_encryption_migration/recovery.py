"""Fail-closed recovery orchestration for the isolated encryption prototype."""

from __future__ import annotations

from contextlib import closing
import ctypes
from dataclasses import dataclass, replace
import errno
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Callable

from src.security.database_keys import DerivedDomainKey
from src.security.infrastructure.migration_journal_repository import (
    AuthenticatedMigrationJournalRepository,
)
from src.security.migration_journal import (
    MigrationJournalState,
    MigrationPhase,
    MigrationRecoveryEvaluator,
    RecoveryDecision,
    capture_file_evidence,
    transition_migration_journal,
)
from src.security.monotonic_anchor import (
    MonotonicSecurityAnchorStore,
    SecurityAnchorState,
    SecurityAnchorStatus,
)

from .migration import (
    MigrationPaths,
    _open_plaintext_read_only,
    _require_guarded_synthetic_source,
)


_BLOCKED_PHASES = frozenset(
    {
        MigrationPhase.NOT_STARTED,
        MigrationPhase.PREFLIGHT_STARTED,
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_STARTED,
        MigrationPhase.BACKUP_VERIFIED,
        MigrationPhase.TARGET_CREATION_STARTED,
        MigrationPhase.SWAP_PREPARED,
        MigrationPhase.SWAP_STARTED,
        MigrationPhase.SWAP_COMPLETED,
        MigrationPhase.POST_SWAP_VERIFIED,
        MigrationPhase.ROLLBACK_COMPLETED,
        MigrationPhase.FAILED,
        MigrationPhase.BLOCKED,
    }
)


@dataclass(frozen=True)
class RecoveryExecutionResult:
    phase_before: MigrationPhase | None
    phase_after: MigrationPhase | None
    operation: str
    steps: tuple[str, ...] = ()
    blocked: bool = False
    error_code: str | None = None


class PrototypeMigrationRecoveryOrchestrator:
    """Resume only evidence-bound, explicitly safe prototype operations."""

    def __init__(
        self,
        *,
        paths: MigrationPaths,
        journal_repository: AuthenticatedMigrationJournalRepository,
        journal_auth_key: DerivedDomainKey,
        anchor_store: MonotonicSecurityAnchorStore,
        migration_lock,
        registry_observer: Callable[[], tuple[int, str]],
        migration_generation: int,
        clock,
        backup_verifier: Callable[[MigrationPaths], bool],
        target_validator: Callable[[MigrationPaths], bool],
        target_reopener: Callable[[MigrationPaths], bool],
        fault_injector: Callable[[str], None] | None = None,
        replace_file: Callable[[Path, Path], None] | None = None,
        fsync_directory: Callable[[Path], None] | None = None,
    ) -> None:
        self._paths = paths
        self._repository = journal_repository
        self._auth_key = journal_auth_key
        self._anchor = anchor_store
        self._lock = migration_lock
        self._registry_observer = registry_observer
        self._migration_generation = migration_generation
        self._clock = clock
        self._backup_verifier = backup_verifier
        self._target_validator = target_validator
        self._target_reopener = target_reopener
        self._fault = fault_injector or (lambda _point: None)
        self._replace_file = replace_file or _atomic_noreplace
        self._fsync_directory = fsync_directory or _durable_directory

    def recover(self) -> RecoveryExecutionResult:
        phase_before: MigrationPhase | None = None
        steps: list[str] = []
        try:
            state, anchor = self._preconditions()
            phase_before = state.phase
            if state.phase in _BLOCKED_PHASES:
                return self._blocked(state, "migration_recovery_phase_blocked")
            if state.phase is MigrationPhase.BACKUP_CREATED:
                if not self._backup_verifier(self._paths):
                    return self._blocked(state, "migration_recovery_backup_invalid")
                state, anchor = self._preconditions()
                state, _anchor = self._publish_transition(
                    state,
                    anchor,
                    MigrationPhase.BACKUP_VERIFIED,
                    completed_checks=(*state.completed_checks, "backup_integrity"),
                )
                steps.append("backup_verified")
            elif state.phase in {
                MigrationPhase.TARGET_CREATED,
                MigrationPhase.EXPORT_STARTED,
                MigrationPhase.ROLLBACK_STARTED,
            }:
                state = self._rollback_target(state, anchor, steps)
            elif state.phase in {
                MigrationPhase.EXPORT_COMPLETED,
                MigrationPhase.VALIDATION_STARTED,
            }:
                if state.phase is MigrationPhase.EXPORT_COMPLETED:
                    state, anchor = self._publish_transition(
                        state, anchor, MigrationPhase.VALIDATION_STARTED
                    )
                    steps.append("validation_started")
                state, anchor = self._preconditions()
                if not self._target_validator(self._paths):
                    return self._blocked(state, "migration_recovery_validation_failed")
                state, anchor = self._preconditions()
                state, _anchor = self._publish_transition(
                    state,
                    anchor,
                    MigrationPhase.VALIDATION_COMPLETED,
                    completed_checks=(*state.completed_checks, "full_validation"),
                )
                steps.append("validation_completed")
            elif state.phase in {
                MigrationPhase.VALIDATION_COMPLETED,
                MigrationPhase.REOPEN_STARTED,
            }:
                if state.phase is MigrationPhase.VALIDATION_COMPLETED:
                    state, anchor = self._publish_transition(
                        state, anchor, MigrationPhase.REOPEN_STARTED
                    )
                    steps.append("reopen_started")
                state, anchor = self._preconditions()
                if not self._target_reopener(self._paths):
                    return self._blocked(state, "migration_recovery_reopen_failed")
                state, anchor = self._preconditions()
                state, _anchor = self._publish_transition(
                    state,
                    anchor,
                    MigrationPhase.REOPEN_VERIFIED,
                    completed_checks=(*state.completed_checks, "reopen_integrity"),
                )
                steps.append("reopen_verified")
            elif state.phase is MigrationPhase.REOPEN_VERIFIED:
                state, _anchor = self._publish_transition(
                    state,
                    anchor,
                    MigrationPhase.COMPLETED,
                    completed_checks=(
                        *state.completed_checks,
                        "synthetic_prototype_completed",
                    ),
                )
                steps.append("completed")
            elif state.phase is MigrationPhase.COMPLETED:
                state = self._cleanup_completed(state, steps)
            else:
                return self._blocked(state, "migration_recovery_phase_ambiguous")
            return RecoveryExecutionResult(
                phase_before,
                state.phase,
                "recover",
                tuple(steps),
            )
        except Exception as error:
            return RecoveryExecutionResult(
                phase_before,
                phase_before,
                "blocked",
                tuple(steps),
                True,
                _sanitized_code(error),
            )

    def _preconditions(
        self, *, terminal_cleanup: bool = False
    ) -> tuple[MigrationJournalState, SecurityAnchorState]:
        # This order is intentional and is part of the recovery contract.
        if self._lock.verify_owner() is not True:
            raise RuntimeError("migration_recovery_lock_not_owned")
        state, journal_digest = self._repository.load_with_digest(self._auth_key)
        registry_high_water, registry_digest = self._registry_observer()
        anchor = self._reconcile_anchor(
            state,
            journal_digest,
            registry_high_water,
            registry_digest,
        )
        self._validate_guarded_paths(state)
        if terminal_cleanup or state.phase is MigrationPhase.COMPLETED:
            self._validate_terminal_cleanup_evidence(state)
            return state, anchor
        decision = MigrationRecoveryEvaluator().decide(
            state, workspace=self._paths.root
        )
        if decision is RecoveryDecision.BLOCK_MANUAL_REVIEW:
            raise RuntimeError("migration_recovery_evidence_ambiguous")
        return state, anchor

    def _validate_terminal_cleanup_evidence(
        self, state: MigrationJournalState
    ) -> None:
        if (
            state.phase is not MigrationPhase.COMPLETED
            or "synthetic_prototype_completed" not in state.completed_checks
        ):
            raise RuntimeError("migration_recovery_cleanup_not_authorized")
        for role in ("source", "backup", "target"):
            expected = state.file_evidence.get(role)
            if expected is None:
                raise RuntimeError("migration_recovery_cleanup_evidence_missing")
            candidate = getattr(self._paths, role)
            exists = candidate.exists() or candidate.is_symlink()
            quarantine = self._quarantine_path(state, role)
            quarantine_exists = quarantine.exists() or quarantine.is_symlink()
            if role != "source" and not exists:
                if quarantine_exists and not self._matches_evidence(
                    quarantine, role, expected
                ):
                    raise RuntimeError(
                        "migration_recovery_cleanup_identity_mismatch"
                    )
                continue
            if role != "source" and quarantine_exists:
                raise RuntimeError("migration_recovery_quarantine_ambiguous")
            if not exists:
                raise RuntimeError("migration_recovery_source_missing")
            observed = capture_file_evidence(
                self._paths.root,
                role=role,
                relative_path=state.planned_paths[role],
            )
            if observed != expected:
                raise RuntimeError("migration_recovery_cleanup_identity_mismatch")

    def _reconcile_anchor(
        self,
        state: MigrationJournalState,
        journal_digest: str,
        registry_high_water: int,
        registry_digest: str,
    ) -> SecurityAnchorState:
        stored = self._anchor.read()
        if (
            stored.status is not SecurityAnchorStatus.ACTIVE
            or stored.database_context_id != state.data_context_id
            or stored.dmk_key_id != state.wrapping_dmk_key_id
            or stored.dmk_key_generation != state.wrapping_dmk_generation
        ):
            raise RuntimeError("migration_recovery_anchor_binding_mismatch")
        actual = (
            registry_high_water,
            registry_digest,
            state.revision,
            journal_digest,
            self._migration_generation,
        )
        committed = stored.committed_state()
        if actual == _artifact_snapshot(committed):
            self._anchor.verify(committed)
            if stored.pending is not None:
                return self._anchor.abort_pending(stored, committed)
            return committed
        if stored.pending is not None and actual == _artifact_snapshot(stored.pending):
            self._anchor.verify(stored.pending)
            return self._anchor.advance(stored, stored.pending)
        try:
            self._anchor.block(stored, "migration_recovery_anchor_mismatch")
        finally:
            raise RuntimeError("migration_recovery_anchor_mismatch")

    def _validate_guarded_paths(self, state: MigrationJournalState) -> None:
        root = self._paths.root
        if root.is_symlink() or not root.is_dir() or root.resolve() != root.absolute():
            raise RuntimeError("migration_recovery_root_invalid")
        try:
            temporary_root = Path(tempfile.gettempdir()).resolve(strict=True)
        except OSError:
            raise RuntimeError("migration_recovery_test_root_unavailable") from None
        if root != temporary_root and not root.is_relative_to(temporary_root):
            raise RuntimeError("migration_recovery_test_root_required")
        expected = {
            "source": self._paths.source,
            "backup": self._paths.backup,
            "target": self._paths.target,
        }
        for role, candidate in expected.items():
            if candidate.parent != root or candidate.name != state.planned_paths[role]:
                raise RuntimeError("migration_recovery_path_mismatch")
        try:
            with closing(_open_plaintext_read_only(self._paths.source)) as source:
                _require_guarded_synthetic_source(source)
        except Exception:
            raise RuntimeError("migration_recovery_synthetic_guard_required") from None

    def _publish_transition(
        self,
        state: MigrationJournalState,
        anchor: SecurityAnchorState,
        phase: MigrationPhase,
        *,
        completed_checks: tuple[str, ...] | None = None,
        error_class: str | None = None,
    ) -> tuple[MigrationJournalState, SecurityAnchorState]:
        replacement = transition_migration_journal(
            state,
            phase,
            now=self._clock.utc_now(),
            completed_checks=completed_checks,
            error_class=error_class,
        )
        digest = self._repository.preview_digest(replacement, self._auth_key)
        planned = replace(
            anchor.committed_state(),
            anchor_revision=anchor.anchor_revision + 1,
            journal_revision=replacement.revision,
            journal_sha256=digest,
            pending=None,
            block_reason=None,
            status=SecurityAnchorStatus.ACTIVE,
        )
        prepared = self._anchor.prepare(anchor, planned)
        self._fault("after_anchor_prepare")
        self._repository.save(state, replacement, self._auth_key)
        self._fault("after_journal_publish")
        committed = self._anchor.advance(prepared, planned)
        return replacement, committed

    def _rollback_target(
        self,
        state: MigrationJournalState,
        anchor: SecurityAnchorState,
        steps: list[str],
    ) -> MigrationJournalState:
        if state.phase is not MigrationPhase.ROLLBACK_STARTED:
            state, anchor = self._publish_transition(
                state, anchor, MigrationPhase.ROLLBACK_STARTED
            )
            steps.append("rollback_started")
        state, anchor = self._preconditions()
        if self._paths.target.exists() or self._paths.target.is_symlink():
            self._quarantine_role(state, "target")
            steps.append("target_quarantined")
        state, anchor = self._preconditions()
        state, anchor = self._publish_transition(
            state, anchor, MigrationPhase.ROLLBACK_COMPLETED
        )
        state, _anchor = self._preconditions()
        state, _anchor = self._publish_transition(
            state,
            anchor,
            MigrationPhase.FAILED,
            error_class="migration_recovery_target_rolled_back",
        )
        steps.extend(("rollback_completed", "failed_safe"))
        return state

    def _cleanup_completed(
        self, state: MigrationJournalState, steps: list[str]
    ) -> MigrationJournalState:
        state, _anchor = self._preconditions(terminal_cleanup=True)
        for role in ("target", "backup"):
            state, _anchor = self._preconditions(terminal_cleanup=True)
            candidate = getattr(self._paths, role)
            if not (candidate.exists() or candidate.is_symlink()):
                quarantine = self._quarantine_path(state, role)
                if quarantine.exists() or quarantine.is_symlink():
                    if not self._matches_evidence(
                        quarantine, role, state.file_evidence[role]
                    ):
                        raise RuntimeError(
                            "migration_recovery_quarantine_identity_mismatch"
                        )
                    steps.append(f"{role}_quarantine_retained")
                    continue
                steps.append(f"{role}_already_clean")
                continue
            self._quarantine_role(state, role)
            steps.append(f"{role}_quarantined")
        self._preconditions(terminal_cleanup=True)
        return state

    def _quarantine_role(self, state: MigrationJournalState, role: str) -> None:
        if role not in {"target", "backup"}:
            raise RuntimeError("migration_recovery_cleanup_role_invalid")
        candidate = getattr(self._paths, role)
        expected = state.file_evidence.get(role)
        if expected is None:
            raise RuntimeError("migration_recovery_artifact_unbound")
        observed = candidate.lstat()
        if (
            candidate.is_symlink()
            or not stat.S_ISREG(observed.st_mode)
            or (observed.st_dev, observed.st_ino)
            != (expected.device_id, expected.file_id)
        ):
            raise RuntimeError("migration_recovery_artifact_identity_mismatch")
        quarantine = self._quarantine_path(state, role)
        if quarantine.exists() or quarantine.is_symlink():
            raise RuntimeError("migration_recovery_quarantine_present")
        self._fault("before_target_quarantine")
        self._replace_file(candidate, quarantine)
        self._fsync_directory(self._paths.root)
        self._fault("after_target_quarantine")
        quarantined = quarantine.lstat()
        if (
            quarantine.is_symlink()
            or not stat.S_ISREG(quarantined.st_mode)
            or (quarantined.st_dev, quarantined.st_ino)
            != (expected.device_id, expected.file_id)
            or candidate.exists()
            or candidate.is_symlink()
        ):
            raise RuntimeError("migration_recovery_quarantine_identity_mismatch")
        # Pathname unlink cannot atomically assert an inode identity on macOS.
        # Retaining the isolated artifact is the fail-closed choice: a same-user
        # exchange after the final identity check must never delete foreign data.
        self._fault("before_quarantine_final_verification")
        if not self._matches_evidence(quarantine, role, expected):
            raise RuntimeError("migration_recovery_quarantine_identity_mismatch")

    def _quarantine_path(
        self, state: MigrationJournalState, role: str
    ) -> Path:
        return self._paths.root / (
            f".recovery-{role}-{state.migration_id}.quarantine"
        )

    def _matches_evidence(self, path: Path, role: str, expected) -> bool:
        del role
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags)
        except OSError:
            return False
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                return False
            digest = hashlib.sha256()
            size = 0
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
            after = os.fstat(descriptor)
        except OSError:
            return False
        finally:
            os.close(descriptor)
        try:
            observed_path = path.lstat()
        except OSError:
            return False
        return bool(
            not path.is_symlink()
            and stat.S_ISREG(observed_path.st_mode)
            and (before.st_dev, before.st_ino)
            == (after.st_dev, after.st_ino)
            == (observed_path.st_dev, observed_path.st_ino)
            == (expected.device_id, expected.file_id)
            and before.st_size == after.st_size == size == expected.size_bytes
            and before.st_mtime_ns
            == after.st_mtime_ns
            == observed_path.st_mtime_ns
            == expected.modified_ns
            and digest.hexdigest() == expected.sha256
        )

    @staticmethod
    def _blocked(
        state: MigrationJournalState, code: str
    ) -> RecoveryExecutionResult:
        return RecoveryExecutionResult(
            state.phase,
            state.phase,
            "blocked",
            blocked=True,
            error_code=code,
        )


def _artifact_snapshot(state: SecurityAnchorState) -> tuple[int, str, int, str, int]:
    return (
        state.registry_high_water_mark,
        state.registry_sha256,
        state.journal_revision,
        state.journal_sha256,
        state.migration_generation,
    )


def _durable_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_noreplace(source: Path, destination: Path) -> None:
    """Atomically move one generated artifact without clobbering any name."""

    libc = ctypes.CDLL(None, use_errno=True)
    source_raw = os.fsencode(source)
    destination_raw = os.fsencode(destination)
    if hasattr(libc, "renamex_np"):
        result = libc.renamex_np(
            ctypes.c_char_p(source_raw),
            ctypes.c_char_p(destination_raw),
            ctypes.c_uint(4),  # RENAME_EXCL
        )
    elif hasattr(libc, "renameat2"):
        result = libc.renameat2(
            ctypes.c_int(-100),
            ctypes.c_char_p(source_raw),
            ctypes.c_int(-100),
            ctypes.c_char_p(destination_raw),
            ctypes.c_uint(1),  # RENAME_NOREPLACE
        )
    else:
        raise OSError(errno.ENOTSUP, "atomic no-replace rename unsupported")
    if result != 0:
        code = ctypes.get_errno()
        raise OSError(code, "atomic no-replace rename failed")


def _sanitized_code(error: BaseException) -> str:
    code = getattr(error, "code", None)
    if isinstance(code, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", code):
        return code
    if isinstance(error, PermissionError):
        return "migration_recovery_permission_denied"
    if isinstance(error, OSError):
        return "migration_recovery_io_failed"
    return "migration_recovery_blocked"
