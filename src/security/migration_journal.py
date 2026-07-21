"""Strict migration journal state machine and read-only recovery decisions."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
import hashlib
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from typing import Mapping, Protocol

from .database_keys import DerivedDomainKey

from .domain import validate_uuid4


MIGRATION_JOURNAL_VERSION = 1
MIGRATION_JOURNAL_AUTH_ALGORITHM = "hmac-sha256"
MIGRATION_JOURNAL_MAX_EVENTS = 64
MIGRATION_FILE_ROLES = ("source", "backup", "target")
_SAFE_FILENAME = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,159}\Z")
_SAFE_CODE = re.compile(r"\A[a-z][a-z0-9_]{0,79}\Z")
_UTC_PATTERN = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")


class MigrationJournalError(RuntimeError):
    """Sanitized migration-journal failure without paths or secrets."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class MigrationPhase(str, Enum):
    NOT_STARTED = "not_started"
    PREFLIGHT_STARTED = "preflight_started"
    SOURCE_VERIFIED = "source_verified"
    BACKUP_STARTED = "backup_started"
    BACKUP_CREATED = "backup_created"
    BACKUP_VERIFIED = "backup_verified"
    TARGET_CREATION_STARTED = "target_creation_started"
    TARGET_CREATED = "target_created"
    EXPORT_STARTED = "export_started"
    EXPORT_COMPLETED = "export_completed"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    REOPEN_STARTED = "reopen_started"
    REOPEN_VERIFIED = "reopen_verified"
    SWAP_PREPARED = "swap_prepared"
    SWAP_STARTED = "swap_started"
    SWAP_COMPLETED = "swap_completed"
    POST_SWAP_VERIFIED = "post_swap_verified"
    ROLLBACK_STARTED = "rollback_started"
    ROLLBACK_COMPLETED = "rollback_completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class RecoveryDecision(str, Enum):
    NO_ACTION = "no_action"
    VERIFY_BACKUP = "verify_backup"
    ROLLBACK_TARGET = "rollback_target"
    CONTINUE_VALIDATION = "continue_validation"
    REOPEN_TARGET = "reopen_target"
    BLOCK_MANUAL_REVIEW = "block_manual_review"
    CLEANUP_COMPLETED_ARTIFACTS = "cleanup_completed_artifacts"


@dataclass(frozen=True)
class MigrationFileEvidence:
    role: str
    relative_path: str
    device_id: int
    file_id: int
    size_bytes: int
    sha256: str
    modified_ns: int


@dataclass(frozen=True)
class MigrationJournalEvent:
    revision: int
    phase: MigrationPhase
    at: str
    completed_checks: tuple[str, ...] = ()
    error_class: str | None = None


@dataclass(frozen=True)
class MigrationJournalState:
    journal_version: int
    migration_id: str
    data_context_id: str
    database_key_id: str
    database_key_generation: int
    wrapping_dmk_key_id: str
    wrapping_dmk_generation: int
    auth_algorithm: str
    auth_kdf_version: int
    created_at: str
    updated_at: str
    revision: int
    phase: MigrationPhase
    planned_paths: Mapping[str, str]
    file_evidence: Mapping[str, MigrationFileEvidence]
    completed_checks: tuple[str, ...]
    error_class: str | None
    history: tuple[MigrationJournalEvent, ...] = field(default_factory=tuple)


_NORMAL_TRANSITIONS: dict[MigrationPhase, frozenset[MigrationPhase]] = {
    MigrationPhase.NOT_STARTED: frozenset({MigrationPhase.PREFLIGHT_STARTED}),
    MigrationPhase.PREFLIGHT_STARTED: frozenset({MigrationPhase.SOURCE_VERIFIED}),
    MigrationPhase.SOURCE_VERIFIED: frozenset({MigrationPhase.BACKUP_STARTED}),
    MigrationPhase.BACKUP_STARTED: frozenset({MigrationPhase.BACKUP_CREATED}),
    MigrationPhase.BACKUP_CREATED: frozenset({MigrationPhase.BACKUP_VERIFIED}),
    MigrationPhase.BACKUP_VERIFIED: frozenset(
        {MigrationPhase.TARGET_CREATION_STARTED}
    ),
    MigrationPhase.TARGET_CREATION_STARTED: frozenset(
        {MigrationPhase.TARGET_CREATED}
    ),
    MigrationPhase.TARGET_CREATED: frozenset({MigrationPhase.EXPORT_STARTED}),
    MigrationPhase.EXPORT_STARTED: frozenset({MigrationPhase.EXPORT_COMPLETED}),
    MigrationPhase.EXPORT_COMPLETED: frozenset(
        {MigrationPhase.VALIDATION_STARTED}
    ),
    MigrationPhase.VALIDATION_STARTED: frozenset(
        {MigrationPhase.VALIDATION_COMPLETED}
    ),
    MigrationPhase.VALIDATION_COMPLETED: frozenset(
        {MigrationPhase.REOPEN_STARTED}
    ),
    MigrationPhase.REOPEN_STARTED: frozenset({MigrationPhase.REOPEN_VERIFIED}),
    MigrationPhase.REOPEN_VERIFIED: frozenset(
        {MigrationPhase.COMPLETED, MigrationPhase.SWAP_PREPARED}
    ),
    MigrationPhase.SWAP_PREPARED: frozenset({MigrationPhase.SWAP_STARTED}),
    MigrationPhase.SWAP_STARTED: frozenset({MigrationPhase.SWAP_COMPLETED}),
    MigrationPhase.SWAP_COMPLETED: frozenset(
        {MigrationPhase.POST_SWAP_VERIFIED}
    ),
    MigrationPhase.POST_SWAP_VERIFIED: frozenset({MigrationPhase.COMPLETED}),
    MigrationPhase.ROLLBACK_STARTED: frozenset(
        {MigrationPhase.ROLLBACK_COMPLETED}
    ),
    MigrationPhase.ROLLBACK_COMPLETED: frozenset({MigrationPhase.FAILED}),
    MigrationPhase.FAILED: frozenset(),
    MigrationPhase.BLOCKED: frozenset(),
    MigrationPhase.COMPLETED: frozenset(),
}
_ROLLBACK_ORIGINS = frozenset(
    {
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
    }
)
_TERMINAL = frozenset(
    {MigrationPhase.FAILED, MigrationPhase.BLOCKED, MigrationPhase.COMPLETED}
)
_RESERVED_CHECK_PHASES: dict[str, MigrationPhase] = {
    "source_identity": MigrationPhase.SOURCE_VERIFIED,
    "source_integrity": MigrationPhase.SOURCE_VERIFIED,
    "backup_integrity": MigrationPhase.BACKUP_VERIFIED,
    "export_committed": MigrationPhase.EXPORT_COMPLETED,
    "full_validation": MigrationPhase.VALIDATION_COMPLETED,
    "reopen_integrity": MigrationPhase.REOPEN_VERIFIED,
    "synthetic_prototype_completed": MigrationPhase.COMPLETED,
}


def new_migration_journal(
    *,
    migration_id: str,
    data_context_id: str,
    database_key_id: str,
    database_key_generation: int,
    wrapping_dmk_key_id: str,
    wrapping_dmk_generation: int,
    planned_paths: Mapping[str, str],
    source_evidence: MigrationFileEvidence,
    now: datetime,
) -> MigrationJournalState:
    validate_uuid4(migration_id)
    validate_uuid4(data_context_id)
    validate_uuid4(database_key_id)
    if type(database_key_generation) is not int or database_key_generation < 1:
        raise MigrationJournalError("migration_journal_database_key_generation_invalid")
    validate_uuid4(wrapping_dmk_key_id)
    if type(wrapping_dmk_generation) is not int or wrapping_dmk_generation < 1:
        raise MigrationJournalError("migration_journal_dmk_generation_invalid")
    timestamp = format_utc(now)
    event = MigrationJournalEvent(0, MigrationPhase.NOT_STARTED, timestamp)
    state = MigrationJournalState(
        journal_version=MIGRATION_JOURNAL_VERSION,
        migration_id=migration_id,
        data_context_id=data_context_id,
        database_key_id=database_key_id,
        database_key_generation=database_key_generation,
        wrapping_dmk_key_id=wrapping_dmk_key_id,
        wrapping_dmk_generation=wrapping_dmk_generation,
        auth_algorithm=MIGRATION_JOURNAL_AUTH_ALGORITHM,
        auth_kdf_version=1,
        created_at=timestamp,
        updated_at=timestamp,
        revision=0,
        phase=MigrationPhase.NOT_STARTED,
        planned_paths=MappingProxyType(dict(planned_paths)),
        file_evidence=MappingProxyType({"source": source_evidence}),
        completed_checks=(),
        error_class=None,
        history=(event,),
    )
    validate_migration_journal(state)
    return state


def transition_migration_journal(
    state: MigrationJournalState,
    phase: MigrationPhase,
    *,
    now: datetime,
    file_evidence: Mapping[str, MigrationFileEvidence] | None = None,
    completed_checks: tuple[str, ...] | None = None,
    error_class: str | None = None,
) -> MigrationJournalState:
    validate_migration_journal(state)
    if not isinstance(phase, MigrationPhase):
        raise MigrationJournalError("migration_journal_phase_unknown")
    allowed = set(_NORMAL_TRANSITIONS[state.phase])
    if state.phase in _ROLLBACK_ORIGINS:
        allowed.add(MigrationPhase.ROLLBACK_STARTED)
    if state.phase not in _TERMINAL and state.phase is not MigrationPhase.ROLLBACK_COMPLETED:
        allowed.update({MigrationPhase.FAILED, MigrationPhase.BLOCKED})
    if phase not in allowed:
        raise MigrationJournalError("migration_journal_transition_illegal")
    timestamp = format_utc(now)
    evidence = dict(state.file_evidence if file_evidence is None else file_evidence)
    _validate_evidence_update(state.file_evidence, evidence, phase)
    checks = state.completed_checks if completed_checks is None else completed_checks
    if phase in {MigrationPhase.FAILED, MigrationPhase.BLOCKED}:
        if error_class is None:
            raise MigrationJournalError("migration_journal_error_class_missing")
    elif error_class is not None:
        raise MigrationJournalError("migration_journal_error_class_invalid")
    event = MigrationJournalEvent(
        state.revision + 1,
        phase,
        timestamp,
        tuple(checks),
        error_class,
    )
    replacement = replace(
        state,
        updated_at=timestamp,
        revision=state.revision + 1,
        phase=phase,
        file_evidence=MappingProxyType(evidence),
        completed_checks=tuple(checks),
        error_class=error_class,
        history=(*state.history, event),
    )
    validate_migration_journal(replacement)
    return replacement


def validate_migration_journal(state: MigrationJournalState) -> None:
    if not isinstance(state, MigrationJournalState):
        raise MigrationJournalError("migration_journal_state_invalid")
    if type(state.journal_version) is not int:
        raise MigrationJournalError("migration_journal_version_invalid")
    if state.journal_version != MIGRATION_JOURNAL_VERSION:
        raise MigrationJournalError("migration_journal_version_unsupported")
    validate_uuid4(state.migration_id)
    validate_uuid4(state.data_context_id)
    validate_uuid4(state.database_key_id)
    if type(state.database_key_generation) is not int or state.database_key_generation < 1:
        raise MigrationJournalError("migration_journal_database_key_generation_invalid")
    validate_uuid4(state.wrapping_dmk_key_id)
    if type(state.wrapping_dmk_generation) is not int or state.wrapping_dmk_generation < 1:
        raise MigrationJournalError("migration_journal_dmk_generation_invalid")
    if state.auth_algorithm != MIGRATION_JOURNAL_AUTH_ALGORITHM:
        raise MigrationJournalError("migration_journal_auth_algorithm_unsupported")
    if type(state.auth_kdf_version) is not int or state.auth_kdf_version != 1:
        raise MigrationJournalError("migration_journal_auth_kdf_unsupported")
    parse_utc(state.created_at)
    parse_utc(state.updated_at)
    if type(state.revision) is not int or state.revision < 0:
        raise MigrationJournalError("migration_journal_revision_invalid")
    if not isinstance(state.phase, MigrationPhase):
        raise MigrationJournalError("migration_journal_phase_unknown")
    if not isinstance(state.planned_paths, Mapping) or set(state.planned_paths) != set(
        MIGRATION_FILE_ROLES
    ):
        raise MigrationJournalError("migration_journal_paths_invalid")
    if len(set(state.planned_paths.values())) != len(MIGRATION_FILE_ROLES):
        raise MigrationJournalError("migration_journal_paths_invalid")
    for role, relative in state.planned_paths.items():
        if role not in MIGRATION_FILE_ROLES or not _safe_relative_path(relative):
            raise MigrationJournalError("migration_journal_paths_invalid")
    if not isinstance(state.file_evidence, Mapping) or not set(
        state.file_evidence
    ).issubset(MIGRATION_FILE_ROLES):
        raise MigrationJournalError("migration_journal_file_evidence_invalid")
    for role, evidence in state.file_evidence.items():
        _validate_evidence(evidence)
        if evidence.role != role or evidence.relative_path != state.planned_paths[role]:
            raise MigrationJournalError("migration_journal_file_evidence_invalid")
    _validate_checks(state.completed_checks)
    _validate_error_class(state.error_class)
    if not state.history or len(state.history) > MIGRATION_JOURNAL_MAX_EVENTS:
        raise MigrationJournalError("migration_journal_history_invalid")
    if len(state.history) != state.revision + 1:
        raise MigrationJournalError("migration_journal_history_invalid")
    previous: MigrationJournalEvent | None = None
    previous_at: datetime | None = None
    seen_phases: set[MigrationPhase] = set()
    for expected_revision, event in enumerate(state.history):
        _validate_event(event)
        if event.revision != expected_revision:
            raise MigrationJournalError("migration_journal_history_invalid")
        if previous is None:
            if event.phase is not MigrationPhase.NOT_STARTED:
                raise MigrationJournalError("migration_journal_history_invalid")
        elif not _transition_is_allowed(previous.phase, event.phase):
            raise MigrationJournalError("migration_journal_history_invalid")
        event_at = parse_utc(event.at)
        if previous_at is not None and event_at < previous_at:
            raise MigrationJournalError("migration_journal_history_invalid")
        seen_phases.add(event.phase)
        if any(
            required_phase not in seen_phases
            for check in event.completed_checks
            if (required_phase := _RESERVED_CHECK_PHASES.get(check)) is not None
        ):
            raise MigrationJournalError("migration_journal_check_phase_invalid")
        previous = event
        previous_at = event_at
    last = state.history[-1]
    if (
        state.history[0].at != state.created_at
        or parse_utc(state.updated_at) < parse_utc(state.created_at)
        or last.phase is not state.phase
        or last.at != state.updated_at
        or last.completed_checks != state.completed_checks
        or last.error_class != state.error_class
    ):
        raise MigrationJournalError("migration_journal_history_invalid")
    previous_checks: frozenset[str] = frozenset()
    for event in state.history:
        event_checks = frozenset(event.completed_checks)
        if not previous_checks.issubset(event_checks):
            raise MigrationJournalError("migration_journal_checks_not_monotonic")
        previous_checks = event_checks


def capture_file_evidence(
    workspace: Path, *, role: str, relative_path: str
) -> MigrationFileEvidence:
    if role not in MIGRATION_FILE_ROLES or not _safe_relative_path(relative_path):
        raise MigrationJournalError("migration_file_role_invalid")
    root = _validated_workspace(workspace)
    path = root / relative_path
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise MigrationJournalError("migration_file_unavailable") from None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise MigrationJournalError("migration_file_not_regular")
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        path_status = path.lstat()
    except OSError:
        raise MigrationJournalError("migration_file_changed") from None
    if (
        path.is_symlink()
        or not stat.S_ISREG(path_status.st_mode)
        or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
        or (before.st_dev, before.st_ino) != (path_status.st_dev, path_status.st_ino)
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or size != after.st_size
    ):
        raise MigrationJournalError("migration_file_changed")
    if before.st_ino == 0:
        raise MigrationJournalError("migration_file_identity_unavailable")
    return MigrationFileEvidence(
        role=role,
        relative_path=relative_path,
        device_id=int(before.st_dev),
        file_id=int(before.st_ino),
        size_bytes=size,
        sha256=digest.hexdigest(),
        modified_ns=int(before.st_mtime_ns),
    )


class MigrationRecoveryEvaluator:
    """Return a deterministic technical decision without mutating any file."""

    def decide(
        self, state: MigrationJournalState, *, workspace: Path
    ) -> RecoveryDecision:
        try:
            validate_migration_journal(state)
            root = _validated_workspace(workspace)
            self._verify_observed_files(state, root)
        except (MigrationJournalError, OSError, ValueError):
            return RecoveryDecision.BLOCK_MANUAL_REVIEW
        mapping = {
            MigrationPhase.NOT_STARTED: RecoveryDecision.NO_ACTION,
            MigrationPhase.PREFLIGHT_STARTED: RecoveryDecision.NO_ACTION,
            MigrationPhase.SOURCE_VERIFIED: RecoveryDecision.NO_ACTION,
            MigrationPhase.BACKUP_STARTED: RecoveryDecision.NO_ACTION,
            MigrationPhase.BACKUP_CREATED: RecoveryDecision.VERIFY_BACKUP,
            MigrationPhase.BACKUP_VERIFIED: RecoveryDecision.NO_ACTION,
            MigrationPhase.TARGET_CREATION_STARTED: RecoveryDecision.NO_ACTION,
            MigrationPhase.TARGET_CREATED: RecoveryDecision.ROLLBACK_TARGET,
            MigrationPhase.EXPORT_STARTED: RecoveryDecision.ROLLBACK_TARGET,
            MigrationPhase.EXPORT_COMPLETED: RecoveryDecision.CONTINUE_VALIDATION,
            MigrationPhase.VALIDATION_STARTED: RecoveryDecision.CONTINUE_VALIDATION,
            MigrationPhase.VALIDATION_COMPLETED: RecoveryDecision.REOPEN_TARGET,
            MigrationPhase.REOPEN_STARTED: RecoveryDecision.REOPEN_TARGET,
            MigrationPhase.REOPEN_VERIFIED: RecoveryDecision.NO_ACTION,
            MigrationPhase.SWAP_PREPARED: RecoveryDecision.BLOCK_MANUAL_REVIEW,
            MigrationPhase.SWAP_STARTED: RecoveryDecision.BLOCK_MANUAL_REVIEW,
            MigrationPhase.SWAP_COMPLETED: RecoveryDecision.BLOCK_MANUAL_REVIEW,
            MigrationPhase.POST_SWAP_VERIFIED: RecoveryDecision.BLOCK_MANUAL_REVIEW,
            MigrationPhase.ROLLBACK_STARTED: RecoveryDecision.ROLLBACK_TARGET,
            MigrationPhase.ROLLBACK_COMPLETED: RecoveryDecision.NO_ACTION,
            MigrationPhase.FAILED: RecoveryDecision.BLOCK_MANUAL_REVIEW,
            MigrationPhase.BLOCKED: RecoveryDecision.BLOCK_MANUAL_REVIEW,
            MigrationPhase.COMPLETED: RecoveryDecision.CLEANUP_COMPLETED_ARTIFACTS,
        }
        if state.phase is MigrationPhase.ROLLBACK_STARTED:
            target = root / state.planned_paths["target"]
            if not (target.exists() or target.is_symlink()):
                return RecoveryDecision.NO_ACTION
        return mapping[state.phase]

    @staticmethod
    def _verify_observed_files(state: MigrationJournalState, root: Path) -> None:
        phase_history = {event.phase for event in state.history}
        required_checks: set[str] = set()
        for phase, checks in (
            (MigrationPhase.SOURCE_VERIFIED, {"source_identity", "source_integrity"}),
            (MigrationPhase.BACKUP_VERIFIED, {"backup_integrity"}),
            (MigrationPhase.EXPORT_COMPLETED, {"export_committed"}),
            (MigrationPhase.VALIDATION_COMPLETED, {"full_validation"}),
            (MigrationPhase.REOPEN_VERIFIED, {"reopen_integrity"}),
        ):
            if phase in phase_history:
                required_checks.update(checks)
        if not required_checks.issubset(state.completed_checks):
            raise MigrationJournalError("migration_journal_required_checks_missing")
        if "source" not in state.file_evidence:
            raise MigrationJournalError("migration_journal_file_evidence_missing")
        if (
            MigrationPhase.BACKUP_CREATED in phase_history
            and "backup" not in state.file_evidence
        ):
            raise MigrationJournalError("migration_journal_file_evidence_missing")
        if (
            MigrationPhase.TARGET_CREATED in phase_history
            and "target" not in state.file_evidence
        ):
            raise MigrationJournalError("migration_journal_file_evidence_missing")
        for role in MIGRATION_FILE_ROLES:
            relative = state.planned_paths[role]
            candidate = root / relative
            expected = state.file_evidence.get(role)
            exists = candidate.exists() or candidate.is_symlink()
            if expected is None:
                if exists:
                    raise MigrationJournalError("migration_unbound_file_present")
                continue
            if role == "target" and MigrationPhase.ROLLBACK_COMPLETED in phase_history:
                if exists:
                    raise MigrationJournalError("migration_rollback_target_present")
                continue
            missing_after_owned_rollback = (
                role == "target"
                and state.phase is MigrationPhase.ROLLBACK_STARTED
                and not exists
            )
            if missing_after_owned_rollback:
                continue
            if not exists:
                raise MigrationJournalError("migration_expected_file_missing")
            observed = capture_file_evidence(root, role=role, relative_path=relative)
            if (observed.device_id, observed.file_id) != (
                expected.device_id,
                expected.file_id,
            ):
                raise MigrationJournalError("migration_file_identity_mismatch")
            mutable_target = role == "target" and state.phase in {
                MigrationPhase.TARGET_CREATED,
                MigrationPhase.EXPORT_STARTED,
                MigrationPhase.ROLLBACK_STARTED,
            }
            if not mutable_target and (
                observed.size_bytes != expected.size_bytes
                or observed.sha256 != expected.sha256
                or observed.modified_ns != expected.modified_ns
            ):
                raise MigrationJournalError("migration_file_hash_mismatch")


class MigrationJournalReader(Protocol):
    def load(self, auth_key: DerivedDomainKey) -> MigrationJournalState: ...


def evaluate_persisted_recovery(
    repository: MigrationJournalReader,
    auth_key: DerivedDomainKey,
    *,
    workspace: Path,
) -> RecoveryDecision:
    """Fail closed for an unreadable, unauthenticated or contradictory journal."""

    try:
        state = repository.load(auth_key)
    except Exception:
        return RecoveryDecision.BLOCK_MANUAL_REVIEW
    return MigrationRecoveryEvaluator().decide(state, workspace=workspace)


def _transition_is_allowed(source: MigrationPhase, target: MigrationPhase) -> bool:
    allowed = set(_NORMAL_TRANSITIONS[source])
    if source in _ROLLBACK_ORIGINS:
        allowed.add(MigrationPhase.ROLLBACK_STARTED)
    if source not in _TERMINAL and source is not MigrationPhase.ROLLBACK_COMPLETED:
        allowed.update({MigrationPhase.FAILED, MigrationPhase.BLOCKED})
    return target in allowed


def allowed_migration_transitions(
    source: MigrationPhase,
) -> frozenset[MigrationPhase]:
    if not isinstance(source, MigrationPhase):
        raise MigrationJournalError("migration_journal_phase_unknown")
    allowed = set(_NORMAL_TRANSITIONS[source])
    if source in _ROLLBACK_ORIGINS:
        allowed.add(MigrationPhase.ROLLBACK_STARTED)
    if source not in _TERMINAL and source is not MigrationPhase.ROLLBACK_COMPLETED:
        allowed.update({MigrationPhase.FAILED, MigrationPhase.BLOCKED})
    return frozenset(allowed)


def _validate_evidence(evidence: MigrationFileEvidence) -> None:
    if not isinstance(evidence, MigrationFileEvidence):
        raise MigrationJournalError("migration_journal_file_evidence_invalid")
    if evidence.role not in MIGRATION_FILE_ROLES or not _safe_relative_path(
        evidence.relative_path
    ):
        raise MigrationJournalError("migration_journal_file_evidence_invalid")
    for value in (evidence.device_id, evidence.file_id, evidence.size_bytes, evidence.modified_ns):
        if type(value) is not int or value < 0:
            raise MigrationJournalError("migration_journal_file_evidence_invalid")
    if evidence.file_id == 0:
        raise MigrationJournalError("migration_file_identity_unavailable")
    if (
        not isinstance(evidence.sha256, str)
        or len(evidence.sha256) != 64
        or any(character not in "0123456789abcdef" for character in evidence.sha256)
    ):
        raise MigrationJournalError("migration_journal_file_evidence_invalid")


def _validate_event(event: MigrationJournalEvent) -> None:
    if not isinstance(event, MigrationJournalEvent):
        raise MigrationJournalError("migration_journal_history_invalid")
    if type(event.revision) is not int or event.revision < 0:
        raise MigrationJournalError("migration_journal_history_invalid")
    if not isinstance(event.phase, MigrationPhase):
        raise MigrationJournalError("migration_journal_history_invalid")
    if event.phase in {MigrationPhase.FAILED, MigrationPhase.BLOCKED}:
        if event.error_class is None:
            raise MigrationJournalError("migration_journal_history_invalid")
    elif event.error_class is not None:
        raise MigrationJournalError("migration_journal_history_invalid")
    parse_utc(event.at)
    _validate_checks(event.completed_checks)
    _validate_error_class(event.error_class)


def _validate_evidence_update(
    current: Mapping[str, MigrationFileEvidence],
    replacement: Mapping[str, MigrationFileEvidence],
    phase: MigrationPhase,
) -> None:
    if not set(current).issubset(replacement):
        raise MigrationJournalError("migration_journal_file_evidence_rebinding")
    for role, evidence in replacement.items():
        prior = current.get(role)
        if prior is None:
            expected_phase = {
                "backup": MigrationPhase.BACKUP_CREATED,
                "target": MigrationPhase.TARGET_CREATED,
            }.get(role)
            if role == "source" or phase is not expected_phase:
                raise MigrationJournalError(
                    "migration_journal_file_evidence_rebinding"
                )
            continue
        if evidence == prior:
            continue
        target_completion_update = (
            role == "target"
            and phase is MigrationPhase.EXPORT_COMPLETED
            and evidence.role == prior.role
            and evidence.relative_path == prior.relative_path
            and evidence.device_id == prior.device_id
            and evidence.file_id == prior.file_id
        )
        if not target_completion_update:
            raise MigrationJournalError(
                "migration_journal_file_evidence_rebinding"
            )


def _validate_checks(checks: tuple[str, ...]) -> None:
    if not isinstance(checks, tuple) or len(checks) > 32 or len(set(checks)) != len(checks):
        raise MigrationJournalError("migration_journal_checks_invalid")
    if any(not isinstance(check, str) or not _SAFE_CODE.fullmatch(check) for check in checks):
        raise MigrationJournalError("migration_journal_checks_invalid")
    if any(check not in _RESERVED_CHECK_PHASES for check in checks):
        raise MigrationJournalError("migration_journal_checks_unknown")


def _validate_error_class(value: str | None) -> None:
    if value is not None and (
        not isinstance(value, str) or not _SAFE_CODE.fullmatch(value)
    ):
        raise MigrationJournalError("migration_journal_error_class_invalid")


def _safe_relative_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(_SAFE_FILENAME.fullmatch(value))
        and value not in {".", ".."}
        and Path(value).name == value
    )


def _validated_workspace(workspace: Path) -> Path:
    root = Path(workspace)
    if root.is_symlink() or not root.is_dir():
        raise MigrationJournalError("migration_workspace_invalid")
    resolved = root.resolve()
    if resolved.is_symlink() or not resolved.is_dir():
        raise MigrationJournalError("migration_workspace_invalid")
    return resolved


def format_utc(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise MigrationJournalError("migration_journal_timestamp_invalid")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def parse_utc(value: object) -> datetime:
    if not isinstance(value, str) or not _UTC_PATTERN.fullmatch(value):
        raise MigrationJournalError("migration_journal_timestamp_invalid")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError:
        raise MigrationJournalError("migration_journal_timestamp_invalid") from None
