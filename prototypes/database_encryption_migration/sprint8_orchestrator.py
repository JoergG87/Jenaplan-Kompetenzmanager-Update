"""VFS-free synthetic migration and restart-recovery orchestrator.

This module has no product RuntimePaths, startup, UI, backup/restore, or
Identity-VFS imports.  Every path and dependency is injected by tests.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
from typing import Callable

from src.core.database_engine import SQLCipherConnectionProvider
from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import (
    DatabaseKey,
    DerivedDomainKey,
    derive_domain_separated_key,
)
from src.security.infrastructure.simplified_migration_state import (
    AuthenticatedMigrationJournalV2Repository,
    AuthenticatedMigrationJournalV2State,
    ExternalReplayAnchorV2Repository,
    ExternalReplayAnchorV2State,
    MIGRATION_JOURNAL_V2_FILENAME,
)
from src.security.migration_lock import (
    MIGRATION_LOCK_FILENAME,
    MigrationLockPort,
    MigrationLockStatus,
)
from src.security.simplified_migration import (
    EMPTY_SHA256,
    SIMPLIFIED_MIGRATION_CROSSBINDING_VERSION,
    SimplifiedMigrationArtifactV2,
    SimplifiedMigrationCrossbindingV2,
    SimplifiedMigrationError,
    SimplifiedMigrationPreflightEvidenceV2,
    SimplifiedMigrationPreflightMode,
    SimplifiedMigrationRecoveryDecision,
    absent_simplified_artifact,
    capture_simplified_artifact,
    derive_simplified_migration_preflight_v2,
    derive_simplified_recovery_decision,
    private_root_digest,
)

from .migration import (
    DatabaseSnapshot,
    ValidationResult,
    _compare_snapshots,
    _open_plaintext_read_only,
    _require_guarded_synthetic_source,
    _snapshot,
    _verify_plaintext_integrity,
)


SPRINT8_JOURNAL_AUTH_PURPOSE = (
    "jenaplan-kompetenzmanager/migration-journal-auth/v2"
)
SPRINT8_ANCHOR_AUTH_PURPOSE = (
    "jenaplan-kompetenzmanager/migration-replay-anchor-auth/v2"
)
SPRINT8_EXCHANGE_FILENAME = "migration-exchange-v2.json"
SPRINT8_EXCHANGE_DIRECTORY = "swap-simulation"
_SOURCE_NAME = "synthetic-source.sqlite"
_BACKUP_NAME = "migration-safety-copy.sqlite"
_TARGET_NAME = "migration-target.sqlcipher"
_ALLOWED_TRANSITIONS = {
    "not_started": {"preflight_started"},
    "preflight_started": {"source_verified"},
    "source_verified": {"backup_started"},
    "backup_started": {"backup_created"},
    "backup_created": {"backup_verified"},
    "backup_verified": {"target_creation_started"},
    "target_creation_started": {"target_created"},
    "target_created": {"export_started"},
    "export_started": {"export_completed"},
    "export_completed": {"validation_started"},
    "validation_started": {"validation_completed"},
    "validation_completed": {"reopen_started"},
    "reopen_started": {"reopen_verified"},
    "reopen_verified": {"swap_started"},
    "swap_started": {"swap_simulated"},
    "swap_simulated": {"completed"},
    "completed": set(),
}


@dataclass(frozen=True)
class Sprint8MigrationPaths:
    root: Path
    source: Path
    backup: Path
    target: Path
    journal: Path
    exchange_journal: Path
    exchange_directory: Path

    @classmethod
    def in_test_root(cls, root: Path) -> Sprint8MigrationPaths:
        base = Path(root)
        return cls(
            root=base,
            source=base / _SOURCE_NAME,
            backup=base / _BACKUP_NAME,
            target=base / _TARGET_NAME,
            journal=base / MIGRATION_JOURNAL_V2_FILENAME,
            exchange_journal=base / SPRINT8_EXCHANGE_FILENAME,
            exchange_directory=base / SPRINT8_EXCHANGE_DIRECTORY,
        )


@dataclass(frozen=True)
class Sprint8PreflightResult:
    mode: SimplifiedMigrationPreflightMode
    decision: SimplifiedMigrationRecoveryDecision
    context: SimplifiedMigrationCrossbindingV2
    error_code: str | None = None


@dataclass(frozen=True)
class SimulatedAtomicExchangePlanV2:
    performed_on_copies: bool
    same_volume: bool
    predecessor_retained: bool
    pre_swap_source_sha256: str
    candidate_sha256: str
    post_swap_live_sha256: str
    steps: tuple[str, ...]


@dataclass(frozen=True)
class Sprint8MigrationReport:
    preflight_mode: SimplifiedMigrationPreflightMode
    final_phase: str
    source_sha256_before: str
    source_sha256_after: str
    backup_sha256: str
    target_sha256: str
    validation: ValidationResult
    reopened: bool
    exchange: SimulatedAtomicExchangePlanV2


class SyntheticMigrationOrchestratorV2:
    """Smallest complete synthetic source-to-cipher migration path."""

    def __init__(
        self,
        *,
        paths: Sprint8MigrationPaths,
        allowed_private_root: Path,
        installation_id: str,
        database_context_id: str,
        migration_id: str,
        migration_generation: int,
        dmk_loader: Callable[[], LoadedDataMasterKey],
        database_key_loader: Callable[[LoadedDataMasterKey], tuple[DatabaseKey, str]],
        migration_lock: MigrationLockPort,
        journal_repository: AuthenticatedMigrationJournalV2Repository,
        anchor_repository: ExternalReplayAnchorV2Repository,
        sqlcipher_provider: SQLCipherConnectionProvider,
        sqlcipher_version_probe: Callable[[], str],
        app_instance_available: Callable[[], bool],
        source_closed_probe: Callable[[Path], bool],
        lock_chain_head_loader: Callable[[], str],
        disk_free_probe: Callable[[Path], int] | None = None,
        permissions_probe: Callable[[Path], bool] | None = None,
        expected_sqlite_version: str = sqlite3.sqlite_version,
        expected_sqlcipher_version: str = "4.12.0 community",
        expected_schema_version: int = 1,
        safety_reserve_bytes: int = 16 * 1024 * 1024,
        fsync: Callable[[int], None] = os.fsync,
        replace_file: Callable[[Path, Path], None] = os.replace,
        fault_injector: Callable[[str], None] | None = None,
    ) -> None:
        self.paths = paths
        self.allowed_private_root = Path(allowed_private_root)
        self.installation_id = installation_id
        self.database_context_id = database_context_id
        self.migration_id = migration_id
        self.migration_generation = migration_generation
        self._dmk_loader = dmk_loader
        self._database_key_loader = database_key_loader
        self._lock = migration_lock
        self._journal = journal_repository
        self._anchor = anchor_repository
        self._provider = sqlcipher_provider
        self._sqlcipher_version_probe = sqlcipher_version_probe
        self._app_instance_available = app_instance_available
        self._source_closed_probe = source_closed_probe
        self._lock_chain_head_loader = lock_chain_head_loader
        self._disk_free_probe = disk_free_probe or (
            lambda root: shutil.disk_usage(root).free
        )
        self._permissions_probe = permissions_probe or _private_permissions
        self._expected_sqlite_version = expected_sqlite_version
        self._expected_sqlcipher_version = expected_sqlcipher_version
        self._expected_schema_version = expected_schema_version
        self._safety_reserve_bytes = safety_reserve_bytes
        self._fsync = fsync
        self._replace_file = replace_file
        self._fault = fault_injector or (lambda _point: None)
        self._dmk: LoadedDataMasterKey | None = None
        self._database_key: DatabaseKey | None = None
        self._registry_digest: str | None = None
        self._journal_key: DerivedDomainKey | None = None
        self._anchor_key: DerivedDomainKey | None = None
        self._state: AuthenticatedMigrationJournalV2State | None = None
        self._journal_digest: str = EMPTY_SHA256
        self._anchor_state: ExternalReplayAnchorV2State | None = None
        self._validation: ValidationResult | None = None
        self._exchange: SimulatedAtomicExchangePlanV2 | None = None
        self._initial_mode = SimplifiedMigrationPreflightMode.NEW

    def preflight(self) -> Sprint8PreflightResult:
        """Read-only inspection.  It never creates a lock or state file."""

        try:
            self._require_root_and_fixed_paths()
            dmk, database_key, registry_digest = self._load_and_verify_keys()
            journal_key, anchor_key = self._derive_auth_keys(dmk)
            artifacts = self._capture_artifacts()
            unexpected = self._unexpected_artifacts()
            state, journal_digest, journal_authenticated = self._read_journal(
                journal_key
            )
            anchor, anchor_authenticated = self._read_anchor(
                anchor_key,
                state=state,
                journal_digest=journal_digest,
                registry_digest=registry_digest,
            )
            phase = "not_started" if state is None else state.phase
            journal_revision = 0 if state is None else state.revision
            anchor_revision = 0 if anchor is None else _matching_anchor(
                anchor, journal_digest, state
            ).anchor_revision
            lock_head = self._lock_chain_head_loader()
            crossbinding_authenticated = self._bindings_match(
                state,
                artifacts,
                dmk,
                database_key,
                registry_digest,
            )
            context = self._context(
                artifacts=artifacts,
                dmk=dmk,
                database_key=database_key,
                registry_digest=registry_digest,
                journal_digest=journal_digest,
                journal_revision=journal_revision,
                phase=phase,
                anchor_revision=anchor_revision,
                lock_head=lock_head,
            )
            evidence = SimplifiedMigrationPreflightEvidenceV2(
                context=context,
                root_approved=True,
                fixed_paths_match=True,
                single_instance=self._single_instance_ok(),
                source_closed=bool(self._source_closed_probe(self.paths.source)),
                wal_shm_quiet=self._wal_shm_quiet(),
                source_integrity_ok=self._source_integrity_ok(),
                roles_match_phase=_roles_match_phase(phase, artifacts),
                disk_space_ok=self._disk_space_ok(),
                permissions_ok=bool(self._permissions_probe(self.paths.root)),
                sqlcipher_available=self._sqlcipher_available(),
                sqlcipher_version_matches=(
                    self._sqlcipher_version_probe()
                    == self._expected_sqlcipher_version
                ),
                envelope_authenticated=True,
                journal_authenticated=journal_authenticated,
                anchor_authenticated=anchor_authenticated,
                lock_authenticated=self._lock_authentic(),
                crossbinding_authenticated=crossbinding_authenticated,
                unexpected_artifacts=unexpected,
            )
            mode = derive_simplified_migration_preflight_v2(evidence)
            return Sprint8PreflightResult(
                mode=mode,
                decision=derive_simplified_recovery_decision(evidence),
                context=context,
                error_code=None if mode is not SimplifiedMigrationPreflightMode.BLOCKED else "migration_preflight_blocked",
            )
        except Exception as error:
            return Sprint8PreflightResult(
                mode=SimplifiedMigrationPreflightMode.BLOCKED,
                decision=SimplifiedMigrationRecoveryDecision.BLOCKED,
                context=self._blocked_context(),
                error_code=_error_code(error, "migration_preflight_failed"),
            )

    def run(self) -> Sprint8MigrationReport:
        initial = self.preflight()
        if initial.mode is SimplifiedMigrationPreflightMode.BLOCKED:
            raise SimplifiedMigrationError(
                initial.error_code or "migration_preflight_blocked"
            )
        if initial.mode is SimplifiedMigrationPreflightMode.COMPLETED:
            self._initial_mode = initial.mode
        else:
            self._initial_mode = initial.mode
        self._acquire_or_take_over_lock(initial)
        try:
            locked = self.preflight()
            if locked.mode is SimplifiedMigrationPreflightMode.BLOCKED:
                raise SimplifiedMigrationError(
                    locked.error_code or "migration_locked_preflight_blocked"
                )
            self._load_runtime_state()
            self._resolve_pending_anchor()
            if self._state is None:
                self._initialize_state()
            self._drive_to_completion()
            return self._report()
        finally:
            try:
                if self._lock.verify_owner():
                    self._lock.release()
            except Exception:
                pass

    def recover(self) -> Sprint8MigrationReport:
        """A new process performs a full preflight and then resumes safely."""

        result = self.preflight()
        if result.mode is SimplifiedMigrationPreflightMode.BLOCKED:
            raise SimplifiedMigrationError(
                result.error_code or "migration_recovery_blocked"
            )
        return self.run()

    def _drive_to_completion(self) -> None:
        assert self._state is not None
        while self._state.phase != "completed":
            phase = self._state.phase
            if phase == "not_started":
                self._transition("preflight_started")
            elif phase == "preflight_started":
                self._verify_source()
                self._transition("source_verified", checks=("source_identity", "source_integrity"))
                self._fault("crash_before_backup")
            elif phase == "source_verified":
                self._transition("backup_started")
            elif phase == "backup_started":
                if self.paths.backup.exists() or self.paths.backup.is_symlink():
                    if not self._backup_is_byte_identical():
                        raise SimplifiedMigrationError("migration_partial_backup_requires_manual_review")
                else:
                    self._copy_byte_identical_backup()
                self._transition("backup_created", artifacts=self._capture_artifacts())
                self._fault("crash_after_backup_before_verification")
            elif phase == "backup_created":
                self._verify_backup()
                self._transition(
                    "backup_verified",
                    checks=(*self._state.completed_checks, "backup_byte_identical", "backup_integrity"),
                )
            elif phase == "backup_verified":
                self._transition("target_creation_started")
            elif phase == "target_creation_started":
                if self.paths.target.exists() or self.paths.target.is_symlink():
                    self._quarantine_incomplete_target()
                self._create_target()
                self._transition("target_created", artifacts=self._capture_artifacts())
            elif phase == "target_created":
                self._transition("export_started")
            elif phase == "export_started":
                if self._target_has_user_schema():
                    self._quarantine_incomplete_target()
                    self._create_target()
                self._export_without_attach()
                self._transition(
                    "export_completed",
                    artifacts=self._capture_artifacts(),
                    checks=(*self._state.completed_checks, "transfer_without_attach"),
                )
            elif phase == "export_completed":
                self._transition("validation_started")
            elif phase == "validation_started":
                self._validation = self._validate_all()
                self._transition(
                    "validation_completed",
                    artifacts=self._capture_artifacts(),
                    checks=(*self._state.completed_checks, "full_validation", "persistent_pragmas"),
                )
            elif phase == "validation_completed":
                self._fault("crash_before_reopen")
                self._transition("reopen_started")
            elif phase == "reopen_started":
                self._validation = self._reopen_and_validate()
                self._transition(
                    "reopen_verified",
                    artifacts=self._capture_artifacts(),
                    checks=(*self._state.completed_checks, "reopen_integrity"),
                )
                self._fault("crash_after_reopen")
            elif phase == "reopen_verified":
                self._fault("crash_before_simulated_swap")
                self._transition("swap_started")
            elif phase == "swap_started":
                self._exchange = self._simulate_atomic_exchange_on_copies()
                self._transition(
                    "swap_simulated",
                    checks=(*self._state.completed_checks, "simulated_exchange", "source_retained"),
                )
            elif phase == "swap_simulated":
                self._validation = self._reopen_and_validate()
                self._transition(
                    "completed",
                    artifacts=self._capture_artifacts(),
                    checks=(*self._state.completed_checks, "post_simulation_validation"),
                )
            else:
                raise SimplifiedMigrationError("migration_phase_unsupported")

    def _initialize_state(self) -> None:
        dmk, database_key, registry_digest = self._load_and_verify_keys()
        artifacts = self._capture_artifacts()
        state = AuthenticatedMigrationJournalV2State(
            journal_version=2,
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
            migration_id=self.migration_id,
            migration_generation=self.migration_generation,
            dmk_key_id=dmk.key_id,
            dmk_key_generation=dmk.generation,
            database_key_id=database_key.key_id,
            database_key_generation=database_key.generation,
            envelope_registry_sha256=registry_digest,
            revision=0,
            phase="not_started",
            artifacts=artifacts,
            completed_checks=(),
        )
        journal_key, anchor_key = self._derive_auth_keys(dmk)
        planned_digest = self._journal.preview_digest(state, journal_key)
        lock_head = self._lock_chain_head_loader()
        committed = ExternalReplayAnchorV2State(
            anchor_version=2,
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
            migration_id=self.migration_id,
            migration_generation=self.migration_generation,
            anchor_revision=1,
            envelope_registry_sha256=registry_digest,
            journal_revision=0,
            journal_sha256=EMPTY_SHA256,
            lock_chain_head_sha256=lock_head,
        )
        planned = replace(
            committed,
            anchor_revision=2,
            journal_sha256=planned_digest,
        )
        prepared = replace(committed, pending=planned)
        self._anchor.initialize(prepared, anchor_key)
        self._fault("crash_after_anchor_genesis_prepare")
        digest = self._journal.create(state, journal_key)
        self._fault("crash_after_journal_genesis_publish")
        if digest != planned_digest:
            raise SimplifiedMigrationError("migration_genesis_digest_mismatch")
        self._anchor.commit(prepared, planned, anchor_key)
        self._state = state
        self._journal_digest = digest
        self._anchor_state = planned

    def _transition(
        self,
        phase: str,
        *,
        artifacts: tuple[SimplifiedMigrationArtifactV2, ...] | None = None,
        checks: tuple[str, ...] | None = None,
    ) -> None:
        assert self._state is not None
        if phase not in _ALLOWED_TRANSITIONS.get(self._state.phase, set()):
            raise SimplifiedMigrationError("migration_phase_transition_invalid")
        replacement_state = replace(
            self._state,
            revision=self._state.revision + 1,
            phase=phase,
            artifacts=self._state.artifacts if artifacts is None else artifacts,
            completed_checks=self._state.completed_checks if checks is None else checks,
        )
        journal_key = self._require_journal_key()
        anchor_key = self._require_anchor_key()
        if self._anchor_state is None:
            self._anchor_state = self._anchor.read(anchor_key)
        planned_digest = self._journal.preview_digest(replacement_state, journal_key)
        planned_anchor = replace(
            self._anchor_state.committed(),
            anchor_revision=self._anchor_state.anchor_revision + 1,
            journal_revision=replacement_state.revision,
            journal_sha256=planned_digest,
            lock_chain_head_sha256=self._lock_chain_head_loader(),
        )
        prepared = self._anchor.prepare(
            self._anchor_state, planned_anchor, anchor_key
        )
        self._fault(f"crash_after_anchor_prepare_{phase}")
        digest = self._journal.replace(
            self._journal_digest, replacement_state, journal_key
        )
        self._fault(f"crash_after_journal_publish_{phase}")
        if digest != planned_digest:
            raise SimplifiedMigrationError("migration_transition_digest_mismatch")
        self._anchor_state = self._anchor.commit(
            prepared, planned_anchor, anchor_key
        )
        self._state = replacement_state
        self._journal_digest = digest

    def _resolve_pending_anchor(self) -> None:
        anchor_key = self._require_anchor_key()
        if not self._anchor.exists():
            return
        anchor = self._anchor.read(anchor_key)
        if anchor.pending is None:
            self._anchor_state = anchor
            return
        if self._state is None:
            if anchor.journal_sha256 != EMPTY_SHA256:
                raise SimplifiedMigrationError("migration_anchor_journal_mismatch")
            self._anchor_state = self._anchor.abort_pending(anchor, anchor_key)
            return
        if self._journal_digest == anchor.pending.journal_sha256:
            self._anchor_state = self._anchor.commit(
                anchor, anchor.pending, anchor_key
            )
        elif self._journal_digest == anchor.journal_sha256:
            self._anchor_state = self._anchor.abort_pending(anchor, anchor_key)
        else:
            raise SimplifiedMigrationError("migration_anchor_journal_mismatch")

    def _copy_byte_identical_backup(self) -> None:
        if not self._wal_shm_quiet() or not self._source_closed_probe(self.paths.source):
            raise SimplifiedMigrationError("migration_source_not_quiet")
        source_before = capture_simplified_artifact(
            self.paths.root, role="source", relative_path=self.paths.source.name
        )
        source_descriptor = destination_descriptor = None
        try:
            source_flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                source_flags |= os.O_NOFOLLOW
            source_descriptor = os.open(self.paths.source, source_flags)
            destination_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                destination_flags |= os.O_NOFOLLOW
            destination_descriptor = os.open(
                self.paths.backup, destination_flags, 0o600
            )
            copied = 0
            while True:
                chunk = os.read(source_descriptor, 1024 * 1024)
                if not chunk:
                    break
                view = memoryview(chunk)
                while view:
                    written = os.write(destination_descriptor, view)
                    view = view[written:]
                copied += len(chunk)
                self._fault("crash_during_backup")
            if copied != source_before.size_bytes:
                raise SimplifiedMigrationError("migration_backup_size_mismatch")
            self._fsync(destination_descriptor)
            os.fchmod(destination_descriptor, 0o600)
        except FileExistsError:
            raise SimplifiedMigrationError("migration_backup_exists") from None
        except SimplifiedMigrationError:
            raise
        except OSError as error:
            if getattr(error, "errno", None) == 28:
                raise SimplifiedMigrationError("migration_enospc") from None
            raise SimplifiedMigrationError("migration_backup_copy_failed") from None
        finally:
            if destination_descriptor is not None:
                os.close(destination_descriptor)
            if source_descriptor is not None:
                os.close(source_descriptor)
        _fsync_directory(self.paths.root, self._fsync)
        source_after = capture_simplified_artifact(
            self.paths.root, role="source", relative_path=self.paths.source.name
        )
        if source_before != source_after or not self._backup_is_byte_identical():
            raise SimplifiedMigrationError("migration_backup_not_byte_identical")

    def _verify_source(self) -> DatabaseSnapshot:
        if not self._source_closed_probe(self.paths.source) or not self._wal_shm_quiet():
            raise SimplifiedMigrationError("migration_source_not_quiet")
        before = capture_simplified_artifact(
            self.paths.root, role="source", relative_path=self.paths.source.name
        )
        with closing(_open_plaintext_read_only(self.paths.source)) as source:
            _require_guarded_synthetic_source(source)
            _verify_plaintext_integrity(source)
            snapshot = _snapshot(source)
        after = capture_simplified_artifact(
            self.paths.root, role="source", relative_path=self.paths.source.name
        )
        if before != after:
            raise SimplifiedMigrationError("migration_source_changed")
        return snapshot

    def _verify_backup(self) -> None:
        if not self._backup_is_byte_identical():
            raise SimplifiedMigrationError("migration_backup_not_byte_identical")
        with closing(_open_plaintext_read_only(self.paths.source)) as source:
            _require_guarded_synthetic_source(source)
            _verify_plaintext_integrity(source)
            source_snapshot = _snapshot(source)
        with closing(_open_plaintext_read_only(self.paths.backup)) as backup:
            _require_guarded_synthetic_source(backup)
            _verify_plaintext_integrity(backup)
            backup_snapshot = _snapshot(backup)
        if not _compare_snapshots(source_snapshot, backup_snapshot).successful:
            raise SimplifiedMigrationError("migration_backup_integrity_failed")

    def _create_target(self) -> None:
        with closing(
            self._provider.connect(
                self.paths.target,
                create=True,
                key_material=self._require_database_key().key_material,
            )
        ) as target:
            target.execute("PRAGMA auto_vacuum = FULL")
            target.commit()
            self._fault("crash_during_target_creation")
        _fsync_file(self.paths.target, self._fsync)
        _fsync_directory(self.paths.root, self._fsync)

    def _export_without_attach(self) -> None:
        key = self._require_database_key().key_material
        with closing(_open_plaintext_read_only(self.paths.backup)) as source:
            _require_guarded_synthetic_source(source)
            _verify_plaintext_integrity(source)
            dump = "\n".join(source.iterdump())
        self._fault("crash_during_export")
        with closing(
            self._provider.connect(self.paths.target, create=False, key_material=key)
        ) as target:
            target.execute("PRAGMA foreign_keys = OFF")
            target.executescript(dump)
            target.execute(
                "PRAGMA application_id = "
                + str(_pragma_value(self.paths.backup, "application_id"))
            )
            target.execute(
                "PRAGMA user_version = "
                + str(_pragma_value(self.paths.backup, "user_version"))
            )
            target.commit()
            target.execute("PRAGMA foreign_keys = ON")
            self._provider.verify_integrity(target)
        _fsync_file(self.paths.target, self._fsync)
        _fsync_directory(self.paths.root, self._fsync)

    def _validate_all(self) -> ValidationResult:
        self._fault("crash_during_validation")
        self._verify_backup()
        with closing(_open_plaintext_read_only(self.paths.source)) as source:
            source_snapshot = _snapshot(source)
        with closing(
            self._provider.connect(
                self.paths.target,
                create=False,
                key_material=self._require_database_key().key_material,
            )
        ) as target:
            self._provider.verify_integrity(target)
            target_snapshot = _snapshot(target)
        result = _compare_snapshots(source_snapshot, target_snapshot)
        if not result.successful:
            raise SimplifiedMigrationError("migration_validation_failed")
        return result

    def _reopen_and_validate(self) -> ValidationResult:
        result = self._validate_all()
        with closing(
            self._provider.connect(
                self.paths.target,
                create=False,
                key_material=self._require_database_key().key_material,
            )
        ) as reopened:
            self._provider.verify_integrity(reopened)
        return result

    def _simulate_atomic_exchange_on_copies(self) -> SimulatedAtomicExchangePlanV2:
        simulation = self.paths.exchange_directory
        if simulation.exists() or simulation.is_symlink():
            if self.paths.exchange_journal.exists():
                return self._read_exchange_plan()
            self._recover_incomplete_swap_simulation(simulation)
        else:
            simulation.mkdir(mode=0o700)
        live = simulation / "live.sqlite"
        candidate = simulation / "candidate.sqlcipher"
        predecessor = simulation / "plaintext-predecessor.sqlite"
        if not live.exists():
            _exclusive_copy(self.paths.source, live, self._fsync)
        if not candidate.exists():
            _exclusive_copy(self.paths.target, candidate, self._fsync)
        _fsync_directory(simulation, self._fsync)
        source_sha = _sha256_file(live)
        candidate_sha = _sha256_file(candidate)
        same_volume = live.stat().st_dev == candidate.stat().st_dev == simulation.stat().st_dev
        if not same_volume:
            raise SimplifiedMigrationError("migration_swap_volume_mismatch")
        try:
            self._replace_file(live, predecessor)
            self._fsync_directory_for_swap(simulation)
            self._fault("crash_during_simulated_swap")
            self._replace_file(candidate, live)
            self._fsync_directory_for_swap(simulation)
        except Exception:
            if not live.exists() and predecessor.exists():
                self._replace_file(predecessor, live)
                self._fsync_directory_for_swap(simulation)
            raise
        if not predecessor.exists() or _sha256_file(live) != candidate_sha:
            raise SimplifiedMigrationError("migration_swap_postcheck_failed")
        plan = SimulatedAtomicExchangePlanV2(
            performed_on_copies=True,
            same_volume=True,
            predecessor_retained=True,
            pre_swap_source_sha256=source_sha,
            candidate_sha256=candidate_sha,
            post_swap_live_sha256=_sha256_file(live),
            steps=(
                "pre_swap_hash_and_volume_check",
                "fsync_source_candidate_and_directory",
                "os_replace_live_to_retained_predecessor",
                "os_replace_candidate_to_live",
                "fsync_directory",
                "restart_reopen_and_post_swap_validation",
                "retain_plaintext_predecessor_for_rollback",
            ),
        )
        _write_json_exclusive(self.paths.exchange_journal, plan.__dict__, self._fsync)
        return plan

    def _recover_incomplete_swap_simulation(self, simulation: Path) -> None:
        if simulation.is_symlink() or not simulation.is_dir():
            raise SimplifiedMigrationError("migration_swap_simulation_ambiguous")
        live = simulation / "live.sqlite"
        candidate = simulation / "candidate.sqlcipher"
        predecessor = simulation / "plaintext-predecessor.sqlite"
        names = {item.name for item in simulation.iterdir()}
        if names == {predecessor.name, candidate.name}:
            if _sha256_file(predecessor) != _sha256_file(self.paths.source):
                raise SimplifiedMigrationError("migration_swap_simulation_ambiguous")
            if _sha256_file(candidate) != _sha256_file(self.paths.target):
                raise SimplifiedMigrationError("migration_swap_simulation_ambiguous")
            self._replace_file(predecessor, live)
            self._fsync_directory_for_swap(simulation)
            return
        if names == {live.name, predecessor.name}:
            if _sha256_file(live) != _sha256_file(self.paths.target):
                raise SimplifiedMigrationError("migration_swap_simulation_ambiguous")
            if _sha256_file(predecessor) != _sha256_file(self.paths.source):
                raise SimplifiedMigrationError("migration_swap_simulation_ambiguous")
            plan = SimulatedAtomicExchangePlanV2(
                performed_on_copies=True,
                same_volume=True,
                predecessor_retained=True,
                pre_swap_source_sha256=_sha256_file(predecessor),
                candidate_sha256=_sha256_file(live),
                post_swap_live_sha256=_sha256_file(live),
                steps=(
                    "recovered_post_replace_state",
                    "fsync_directory",
                    "restart_reopen_and_post_swap_validation",
                    "retain_plaintext_predecessor_for_rollback",
                ),
            )
            _write_json_exclusive(
                self.paths.exchange_journal, plan.__dict__, self._fsync
            )
            return
        if names == {live.name, candidate.name}:
            if _sha256_file(live) != _sha256_file(self.paths.source):
                raise SimplifiedMigrationError("migration_swap_simulation_ambiguous")
            if _sha256_file(candidate) != _sha256_file(self.paths.target):
                raise SimplifiedMigrationError("migration_swap_simulation_ambiguous")
            return
        raise SimplifiedMigrationError("migration_swap_simulation_ambiguous")

    def _fsync_directory_for_swap(self, directory: Path) -> None:
        try:
            _fsync_directory(directory, self._fsync)
        except OSError:
            raise SimplifiedMigrationError("migration_swap_fsync_failed") from None

    def _read_exchange_plan(self) -> SimulatedAtomicExchangePlanV2:
        try:
            payload = json.loads(self.paths.exchange_journal.read_text("ascii"))
            payload["steps"] = tuple(payload["steps"])
            result = SimulatedAtomicExchangePlanV2(**payload)
        except Exception:
            raise SimplifiedMigrationError("migration_exchange_journal_invalid") from None
        if not result.predecessor_retained or result.candidate_sha256 != result.post_swap_live_sha256:
            raise SimplifiedMigrationError("migration_exchange_journal_invalid")
        return result

    def _quarantine_incomplete_target(self) -> None:
        if not self.paths.target.exists() or self.paths.target.is_symlink():
            if self.paths.target.is_symlink():
                raise SimplifiedMigrationError("migration_target_symlink_blocked")
            return
        quarantine = self.paths.root / f".recovery-target-{self.migration_id}.quarantine"
        if quarantine.exists() or quarantine.is_symlink():
            raise SimplifiedMigrationError("migration_target_quarantine_exists")
        source_before = capture_simplified_artifact(
            self.paths.root, role="source", relative_path=self.paths.source.name
        )
        backup_before = capture_simplified_artifact(
            self.paths.root, role="backup", relative_path=self.paths.backup.name
        )
        self._replace_file(self.paths.target, quarantine)
        _fsync_directory(self.paths.root, self._fsync)
        source_after = capture_simplified_artifact(
            self.paths.root, role="source", relative_path=self.paths.source.name
        )
        backup_after = capture_simplified_artifact(
            self.paths.root, role="backup", relative_path=self.paths.backup.name
        )
        if source_before != source_after or backup_before != backup_after:
            raise SimplifiedMigrationError("migration_quarantine_foreign_mutation")

    def _report(self) -> Sprint8MigrationReport:
        assert self._state is not None
        validation = self._validation or self._reopen_and_validate()
        exchange = self._exchange or self._read_exchange_plan()
        artifacts = self._capture_artifacts()
        return Sprint8MigrationReport(
            preflight_mode=self._initial_mode,
            final_phase=self._state.phase,
            source_sha256_before=self._state.artifacts[0].sha256 or artifacts[0].sha256 or "",
            source_sha256_after=artifacts[0].sha256 or "",
            backup_sha256=artifacts[1].sha256 or "",
            target_sha256=artifacts[2].sha256 or "",
            validation=validation,
            reopened=True,
            exchange=exchange,
        )

    def _load_runtime_state(self) -> None:
        dmk, database_key, registry_digest = self._load_and_verify_keys()
        self._dmk, self._database_key, self._registry_digest = dmk, database_key, registry_digest
        journal_key, anchor_key = self._derive_auth_keys(dmk)
        self._journal_key, self._anchor_key = journal_key, anchor_key
        if self._journal.exists():
            self._state, self._journal_digest = self._journal.load_with_digest(journal_key)
        if self._anchor.exists():
            self._anchor_state = self._anchor.read(anchor_key)

    def _load_and_verify_keys(self) -> tuple[LoadedDataMasterKey, DatabaseKey, str]:
        dmk = self._dmk_loader()
        database_key, digest = self._database_key_loader(dmk)
        if len(dmk.key_material) != 32 or len(database_key.key_material) != 32:
            raise SimplifiedMigrationError("migration_key_material_invalid")
        if not isinstance(digest, str) or len(digest) != 64:
            raise SimplifiedMigrationError("migration_registry_digest_invalid")
        return dmk, database_key, digest

    def _derive_auth_keys(
        self, dmk: LoadedDataMasterKey
    ) -> tuple[DerivedDomainKey, DerivedDomainKey]:
        context = {
            "database_context_id": self.database_context_id,
            "migration_id": self.migration_id,
            "migration_generation": self.migration_generation,
        }
        return (
            derive_domain_separated_key(
                dmk,
                purpose=SPRINT8_JOURNAL_AUTH_PURPOSE,
                derivation_version=2,
                context=context,
            ),
            derive_domain_separated_key(
                dmk,
                purpose=SPRINT8_ANCHOR_AUTH_PURPOSE,
                derivation_version=2,
                context=context,
            ),
        )

    def _require_database_key(self) -> DatabaseKey:
        if self._database_key is None:
            self._dmk, self._database_key, self._registry_digest = self._load_and_verify_keys()
        return self._database_key

    def _require_journal_key(self) -> DerivedDomainKey:
        if self._journal_key is None:
            dmk = self._dmk or self._dmk_loader()
            self._journal_key, self._anchor_key = self._derive_auth_keys(dmk)
        return self._journal_key

    def _require_anchor_key(self) -> DerivedDomainKey:
        self._require_journal_key()
        assert self._anchor_key is not None
        return self._anchor_key

    def _read_journal(self, key: DerivedDomainKey):
        if not self._journal.exists():
            return None, EMPTY_SHA256, True
        state, digest = self._journal.load_with_digest(key)
        return state, digest, True

    def _read_anchor(self, key, *, state, journal_digest, registry_digest):
        if not self._anchor.exists():
            return None, state is None
        anchor = self._anchor.read(key)
        matching = _matching_anchor(anchor, journal_digest, state)
        valid = (
            matching.installation_id == self.installation_id
            and matching.database_context_id == self.database_context_id
            and matching.migration_id == self.migration_id
            and matching.migration_generation == self.migration_generation
            and matching.envelope_registry_sha256 == registry_digest
        )
        return anchor, valid

    def _bindings_match(self, state, artifacts, dmk, database_key, registry_digest):
        if state is None:
            return not self._journal.exists() and not self._anchor.exists()
        scalar_match = (
            state.installation_id == self.installation_id
            and state.database_context_id == self.database_context_id
            and state.migration_id == self.migration_id
            and state.migration_generation == self.migration_generation
            and state.dmk_key_id == dmk.key_id
            and state.dmk_key_generation == dmk.generation
            and state.database_key_id == database_key.key_id
            and state.database_key_generation == database_key.generation
            and state.envelope_registry_sha256 == registry_digest
        )
        if not scalar_match:
            return False
        for expected, observed in zip(state.artifacts, artifacts):
            if expected.role != observed.role or expected.relative_path != observed.relative_path:
                return False
            if expected.role in {"source", "backup"} and expected.present and expected != observed:
                return False
            if expected.role == "target" and expected.present:
                if not observed.present:
                    return False
                if (expected.device_id, expected.file_id) != (observed.device_id, observed.file_id):
                    return False
                if state.phase not in {"export_started", "target_creation_started"} and expected != observed:
                    return False
        return True

    def _context(self, **values) -> SimplifiedMigrationCrossbindingV2:
        return SimplifiedMigrationCrossbindingV2(
            context_version=SIMPLIFIED_MIGRATION_CROSSBINDING_VERSION,
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
            migration_id=self.migration_id,
            migration_generation=self.migration_generation,
            dmk_key_id=values["dmk"].key_id,
            dmk_key_generation=values["dmk"].generation,
            database_key_id=values["database_key"].key_id,
            database_key_generation=values["database_key"].generation,
            envelope_registry_sha256=values["registry_digest"],
            journal_sha256=values["journal_digest"],
            journal_revision=values["journal_revision"],
            journal_phase=values["phase"],
            replay_anchor_revision=values["anchor_revision"],
            lock_chain_head_sha256=values["lock_head"],
            private_root_sha256=private_root_digest(self.paths.root),
            artifacts=values["artifacts"],
            expected_sqlite_version=self._expected_sqlite_version,
            expected_sqlcipher_version=self._expected_sqlcipher_version,
            expected_schema_version=self._expected_schema_version,
        )

    def _blocked_context(self) -> SimplifiedMigrationCrossbindingV2:
        zero_id = "00000000-0000-4000-8000-000000000000"
        root_digest = EMPTY_SHA256
        try:
            root_digest = private_root_digest(self.paths.root)
        except Exception:
            pass
        return SimplifiedMigrationCrossbindingV2(
            2,
            self.installation_id if _uuidish(self.installation_id) else zero_id,
            self.database_context_id if _uuidish(self.database_context_id) else zero_id,
            self.migration_id if _uuidish(self.migration_id) else zero_id,
            max(1, self.migration_generation),
            zero_id,
            1,
            zero_id,
            1,
            EMPTY_SHA256,
            EMPTY_SHA256,
            0,
            "blocked",
            0,
            EMPTY_SHA256,
            root_digest,
            (
                absent_simplified_artifact(role="source", relative_path=_SOURCE_NAME),
                absent_simplified_artifact(role="backup", relative_path=_BACKUP_NAME),
                absent_simplified_artifact(role="target", relative_path=_TARGET_NAME),
            ),
            self._expected_sqlite_version,
            self._expected_sqlcipher_version,
            self._expected_schema_version,
        )

    def _capture_artifacts(self) -> tuple[SimplifiedMigrationArtifactV2, ...]:
        return tuple(
            capture_simplified_artifact(
                self.paths.root, role=role, relative_path=path.name
            )
            for role, path in (
                ("source", self.paths.source),
                ("backup", self.paths.backup),
                ("target", self.paths.target),
            )
        )

    def _require_root_and_fixed_paths(self) -> None:
        root = self.paths.root.resolve(strict=True)
        allowed = self.allowed_private_root.resolve(strict=True)
        if self.paths.root.is_symlink() or root != allowed or not root.is_dir():
            raise SimplifiedMigrationError("migration_root_not_approved")
        expected = Sprint8MigrationPaths.in_test_root(root)
        if any(getattr(self.paths, field).resolve(strict=False) != getattr(expected, field).resolve(strict=False) for field in (
            "source", "backup", "target", "journal", "exchange_journal", "exchange_directory"
        )):
            raise SimplifiedMigrationError("migration_fixed_paths_mismatch")

    def _unexpected_artifacts(self) -> tuple[str, ...]:
        allowed = {
            self.paths.source.name,
            self.paths.backup.name,
            self.paths.target.name,
            self.paths.journal.name,
            self.paths.exchange_journal.name,
            self.paths.exchange_directory.name,
            MIGRATION_LOCK_FILENAME,
            "database-key-envelopes-v1.json",
            f".recovery-target-{self.migration_id}.quarantine",
        }
        return tuple(
            sorted(
                path.name
                for path in self.paths.root.iterdir()
                if path.name not in allowed
                and not (
                    path.name.startswith(
                        ".database-key-envelope-registry-retained-"
                    )
                    and path.name.endswith(".tmp.artifact")
                    and path.is_file()
                    and not path.is_symlink()
                )
            )
        )

    def _single_instance_ok(self) -> bool:
        return bool(self._app_instance_available())

    def _lock_authentic(self) -> bool:
        inspection = self._lock.inspect()
        if inspection.status is MigrationLockStatus.HELD:
            try:
                return self._lock.verify_owner()
            except Exception:
                return False
        return inspection.status in {
            MigrationLockStatus.MISSING,
            MigrationLockStatus.RELEASED,
            MigrationLockStatus.STALE,
        }

    def _acquire_or_take_over_lock(self, preflight: Sprint8PreflightResult) -> None:
        inspection = self._lock.inspect()
        if inspection.status is MigrationLockStatus.STALE:
            take_over = getattr(self._lock, "take_over_stale", None)
            if not callable(take_over) or inspection.owner is None or inspection.device_id is None or inspection.file_id is None:
                raise SimplifiedMigrationError("migration_stale_lock_takeover_unsupported")
            take_over(
                expected_owner=inspection.owner,
                expected_device_id=inspection.device_id,
                expected_file_id=inspection.file_id,
                recovery_evidence_validator=lambda _owner, _identity: preflight.mode
                in {SimplifiedMigrationPreflightMode.RESUME, SimplifiedMigrationPreflightMode.RECOVERY, SimplifiedMigrationPreflightMode.COMPLETED},
            )
        else:
            self._lock.acquire()
        self._lock.verify_owner()

    def _wal_shm_quiet(self) -> bool:
        return not any(
            Path(str(self.paths.source) + suffix).exists()
            or Path(str(self.paths.source) + suffix).is_symlink()
            for suffix in ("-wal", "-shm", "-journal")
        )

    def _source_integrity_ok(self) -> bool:
        try:
            if (
                sqlite3.sqlite_version != self._expected_sqlite_version
                or self._expected_schema_version != 1
            ):
                return False
            with closing(_open_plaintext_read_only(self.paths.source)) as source:
                _require_guarded_synthetic_source(source)
                _verify_plaintext_integrity(source)
            return True
        except Exception:
            return False

    def _disk_space_ok(self) -> bool:
        try:
            required = self.paths.source.stat().st_size * 4 + self._safety_reserve_bytes
            return self._disk_free_probe(self.paths.root) >= required
        except OSError:
            return False

    def _sqlcipher_available(self) -> bool:
        try:
            return bool(self._sqlcipher_version_probe())
        except Exception:
            return False

    def _backup_is_byte_identical(self) -> bool:
        try:
            source = capture_simplified_artifact(self.paths.root, role="source", relative_path=self.paths.source.name)
            backup = capture_simplified_artifact(self.paths.root, role="backup", relative_path=self.paths.backup.name)
            return (
                source.present
                and backup.present
                and source.size_bytes == backup.size_bytes
                and source.sha256 == backup.sha256
            )
        except Exception:
            return False

    def _target_has_user_schema(self) -> bool:
        if not self.paths.target.exists():
            return False
        try:
            with closing(
                self._provider.connect(
                    self.paths.target,
                    create=False,
                    key_material=self._require_database_key().key_material,
                )
            ) as target:
                count = target.execute(
                    "SELECT count(*) FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%'"
                ).fetchone()[0]
            return bool(count)
        except Exception:
            return True


def _roles_match_phase(
    phase: str, artifacts: tuple[SimplifiedMigrationArtifactV2, ...]
) -> bool:
    present = {item.role for item in artifacts if item.present}
    if phase == "not_started":
        return present == {"source"}
    if phase in {"preflight_started", "source_verified"}:
        return present == {"source"}
    if phase == "backup_started":
        return present in ({"source"}, {"source", "backup"})
    if phase in {"backup_created", "backup_verified", "target_creation_started"}:
        return present in ({"source", "backup"}, {"source", "backup", "target"})
    if phase in _ALLOWED_TRANSITIONS:
        return present == {"source", "backup", "target"}
    return False


def _matching_anchor(anchor, journal_digest, state):
    candidates = (anchor.committed(), anchor.pending)
    journal_revision = 0 if state is None else state.revision
    for candidate in candidates:
        if candidate is None:
            continue
        if candidate.journal_sha256 == journal_digest and candidate.journal_revision == journal_revision:
            return candidate
    if state is None and anchor.journal_sha256 == EMPTY_SHA256:
        return anchor.committed()
    raise SimplifiedMigrationError("migration_anchor_journal_mismatch")


def _private_permissions(root: Path) -> bool:
    try:
        mode = stat.S_IMODE(Path(root).stat().st_mode)
        if mode & 0o077 != 0 or not os.access(root, os.R_OK | os.W_OK | os.X_OK):
            return False
        for item in Path(root).iterdir():
            if item.is_symlink():
                return False
            item_mode = stat.S_IMODE(item.stat().st_mode)
            if item_mode & 0o077 != 0:
                return False
        return True
    except OSError:
        return False


def _exclusive_copy(source: Path, destination: Path, fsync) -> None:
    source_descriptor = destination_descriptor = None
    try:
        source_descriptor = os.open(source, os.O_RDONLY)
        destination_descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        while True:
            chunk = os.read(source_descriptor, 1024 * 1024)
            if not chunk:
                break
            view = memoryview(chunk)
            while view:
                view = view[os.write(destination_descriptor, view):]
        fsync(destination_descriptor)
    finally:
        if destination_descriptor is not None:
            os.close(destination_descriptor)
        if source_descriptor is not None:
            os.close(source_descriptor)


def _write_json_exclusive(path: Path, payload: object, fsync) -> None:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, encoded)
        fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent, fsync)


def _fsync_file(path: Path, fsync) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path, fsync) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        fsync(descriptor)
    finally:
        os.close(descriptor)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pragma_value(path: Path, pragma: str) -> int:
    with closing(_open_plaintext_read_only(path)) as connection:
        return int(connection.execute(f"PRAGMA {pragma}").fetchone()[0])


def _error_code(error: BaseException, fallback: str) -> str:
    code = getattr(error, "code", None)
    if isinstance(code, str) and code:
        return code
    if isinstance(error, PermissionError):
        return "migration_permission_denied"
    return fallback


def _uuidish(value: object) -> bool:
    return isinstance(value, str) and len(value) == 36


__all__ = [
    "SimulatedAtomicExchangePlanV2",
    "Sprint8MigrationPaths",
    "Sprint8MigrationReport",
    "Sprint8PreflightResult",
    "SyntheticMigrationOrchestratorV2",
]
