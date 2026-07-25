"""VFS-free Security Sprint 8 migration domain contracts.

The types in this module contain no product paths, file descriptors,
capabilities, VFS bindings, or super-journal state.  Infrastructure must
authenticate every projection before the pure preflight function is called.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from .domain import validate_uuid4


SIMPLIFIED_MIGRATION_CROSSBINDING_VERSION = 2
SIMPLIFIED_MIGRATION_ARTIFACT_ROLES = ("source", "backup", "target")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_SAFE_COMPONENT = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,159}\Z")
_SAFE_PHASE = re.compile(r"\A[a-z][a-z0-9_]{0,63}\Z")
_VERSION = re.compile(r"\A[0-9]+(?:\.[0-9]+){1,3}(?:[-+ ][A-Za-z0-9.-]+)*\Z")


class SimplifiedMigrationError(RuntimeError):
    """Sanitized migration-contract failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SimplifiedMigrationPreflightMode(StrEnum):
    NEW = "NEW"
    RESUME = "RESUME"
    RECOVERY = "RECOVERY"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class SimplifiedMigrationRecoveryDecision(StrEnum):
    SAFE_RESTART = "SAFE_RESTART"
    REPEAT_VALIDATION = "REPEAT_VALIDATION"
    QUARANTINE_TARGET = "QUARANTINE_TARGET"
    CONFIRM_BACKUP_AUTHORITATIVE = "CONFIRM_BACKUP_AUTHORITATIVE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class SimplifiedMigrationArtifactV2:
    """One fixed file role below an injected private root."""

    role: str
    relative_path: str
    present: bool
    device_id: int | None
    file_id: int | None
    size_bytes: int | None
    sha256: str | None

    def __post_init__(self) -> None:
        _validate_artifact(self)

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SimplifiedMigrationCrossbindingV2:
    """Canonical VFS-free binding for one migration generation."""

    context_version: int
    installation_id: str
    database_context_id: str
    migration_id: str
    migration_generation: int
    dmk_key_id: str
    dmk_key_generation: int
    database_key_id: str
    database_key_generation: int
    envelope_registry_sha256: str
    journal_sha256: str
    journal_revision: int
    journal_phase: str
    replay_anchor_revision: int
    lock_chain_head_sha256: str
    private_root_sha256: str
    artifacts: tuple[SimplifiedMigrationArtifactV2, ...]
    expected_sqlite_version: str
    expected_sqlcipher_version: str
    expected_schema_version: int

    def __post_init__(self) -> None:
        _validate_context(self)

    def to_bytes(self) -> bytes:
        return _canonical_bytes(
            {
                "artifacts": [item.to_payload() for item in self.artifacts],
                "context_version": self.context_version,
                "database_context_id": self.database_context_id,
                "database_key_generation": self.database_key_generation,
                "database_key_id": self.database_key_id,
                "dmk_key_generation": self.dmk_key_generation,
                "dmk_key_id": self.dmk_key_id,
                "envelope_registry_sha256": self.envelope_registry_sha256,
                "expected_schema_version": self.expected_schema_version,
                "expected_sqlcipher_version": self.expected_sqlcipher_version,
                "expected_sqlite_version": self.expected_sqlite_version,
                "installation_id": self.installation_id,
                "journal_phase": self.journal_phase,
                "journal_revision": self.journal_revision,
                "journal_sha256": self.journal_sha256,
                "lock_chain_head_sha256": self.lock_chain_head_sha256,
                "migration_generation": self.migration_generation,
                "migration_id": self.migration_id,
                "private_root_sha256": self.private_root_sha256,
                "replay_anchor_revision": self.replay_anchor_revision,
            }
        )

    def digest_sha256(self) -> str:
        return hashlib.sha256(self.to_bytes()).hexdigest()


@dataclass(frozen=True)
class SimplifiedMigrationPreflightEvidenceV2:
    """Authenticated, read-only inputs to the pure mode derivation."""

    context: SimplifiedMigrationCrossbindingV2
    root_approved: bool
    fixed_paths_match: bool
    single_instance: bool
    source_closed: bool
    wal_shm_quiet: bool
    source_integrity_ok: bool
    roles_match_phase: bool
    disk_space_ok: bool
    permissions_ok: bool
    sqlcipher_available: bool
    sqlcipher_version_matches: bool
    envelope_authenticated: bool
    journal_authenticated: bool
    anchor_authenticated: bool
    lock_authenticated: bool
    crossbinding_authenticated: bool
    unexpected_artifacts: tuple[str, ...] = ()


_RESUME_PHASES = frozenset(
    {
        "source_verified",
        "backup_verified",
        "export_completed",
        "validation_completed",
        "reopen_verified",
        "swap_simulated",
    }
)
_RECOVERY_PHASES = frozenset(
    {
        "preflight_started",
        "backup_started",
        "backup_created",
        "target_creation_started",
        "target_created",
        "export_started",
        "validation_started",
        "reopen_started",
        "swap_started",
    }
)


def derive_simplified_migration_preflight_v2(
    evidence: SimplifiedMigrationPreflightEvidenceV2,
) -> SimplifiedMigrationPreflightMode:
    """Derive a mode without mutating or opening any artifact."""

    if not isinstance(evidence, SimplifiedMigrationPreflightEvidenceV2):
        return SimplifiedMigrationPreflightMode.BLOCKED
    checks = (
        evidence.root_approved,
        evidence.fixed_paths_match,
        evidence.single_instance,
        evidence.source_closed,
        evidence.wal_shm_quiet,
        evidence.source_integrity_ok,
        evidence.roles_match_phase,
        evidence.disk_space_ok,
        evidence.permissions_ok,
        evidence.sqlcipher_available,
        evidence.sqlcipher_version_matches,
        evidence.envelope_authenticated,
        evidence.journal_authenticated,
        evidence.anchor_authenticated,
        evidence.lock_authenticated,
        evidence.crossbinding_authenticated,
    )
    if not all(checks) or evidence.unexpected_artifacts:
        return SimplifiedMigrationPreflightMode.BLOCKED
    phase = evidence.context.journal_phase
    present = {item.role for item in evidence.context.artifacts if item.present}
    if phase == "not_started":
        if present == {"source"}:
            return SimplifiedMigrationPreflightMode.NEW
        return SimplifiedMigrationPreflightMode.BLOCKED
    if phase == "completed":
        if present == set(SIMPLIFIED_MIGRATION_ARTIFACT_ROLES):
            return SimplifiedMigrationPreflightMode.COMPLETED
        return SimplifiedMigrationPreflightMode.BLOCKED
    if phase in _RESUME_PHASES:
        return SimplifiedMigrationPreflightMode.RESUME
    if phase in _RECOVERY_PHASES:
        return SimplifiedMigrationPreflightMode.RECOVERY
    return SimplifiedMigrationPreflightMode.BLOCKED


def derive_simplified_recovery_decision(
    evidence: SimplifiedMigrationPreflightEvidenceV2,
) -> SimplifiedMigrationRecoveryDecision:
    mode = derive_simplified_migration_preflight_v2(evidence)
    phase = evidence.context.journal_phase
    if mode is SimplifiedMigrationPreflightMode.BLOCKED:
        return SimplifiedMigrationRecoveryDecision.BLOCKED
    if mode is SimplifiedMigrationPreflightMode.NEW:
        return SimplifiedMigrationRecoveryDecision.SAFE_RESTART
    if mode is SimplifiedMigrationPreflightMode.COMPLETED:
        return SimplifiedMigrationRecoveryDecision.CONFIRM_BACKUP_AUTHORITATIVE
    if phase in {"validation_started", "validation_completed", "reopen_started", "reopen_verified", "swap_simulated"}:
        return SimplifiedMigrationRecoveryDecision.REPEAT_VALIDATION
    if phase in {"target_creation_started", "target_created", "export_started"}:
        return SimplifiedMigrationRecoveryDecision.QUARANTINE_TARGET
    if phase in {"backup_verified", "export_completed"}:
        return SimplifiedMigrationRecoveryDecision.CONFIRM_BACKUP_AUTHORITATIVE
    if phase in {"preflight_started", "source_verified", "backup_started"}:
        return SimplifiedMigrationRecoveryDecision.SAFE_RESTART
    return SimplifiedMigrationRecoveryDecision.MANUAL_REVIEW_REQUIRED


def absent_simplified_artifact(
    *, role: str, relative_path: str
) -> SimplifiedMigrationArtifactV2:
    return SimplifiedMigrationArtifactV2(
        role, relative_path, False, None, None, None, None
    )


def capture_simplified_artifact(
    root: Path, *, role: str, relative_path: str
) -> SimplifiedMigrationArtifactV2:
    """Capture a regular no-follow file below exactly one resolved root."""

    relative = _validated_relative_path(relative_path)
    base = Path(root)
    try:
        resolved_root = base.resolve(strict=True)
    except OSError:
        raise SimplifiedMigrationError("migration_root_invalid") from None
    if base.is_symlink() or not resolved_root.is_dir():
        raise SimplifiedMigrationError("migration_root_invalid")
    path = resolved_root.joinpath(*PurePosixPath(relative).parts)
    try:
        status = path.lstat()
    except FileNotFoundError:
        return absent_simplified_artifact(role=role, relative_path=relative)
    except OSError:
        raise SimplifiedMigrationError("migration_artifact_unreadable") from None
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
        raise SimplifiedMigrationError("migration_artifact_invalid")
    digest = hashlib.sha256()
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
        try:
            descriptor_status = os.fstat(descriptor)
            if (descriptor_status.st_dev, descriptor_status.st_ino) != (
                status.st_dev,
                status.st_ino,
            ):
                raise SimplifiedMigrationError("migration_artifact_changed")
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
            final_status = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    except SimplifiedMigrationError:
        raise
    except OSError:
        raise SimplifiedMigrationError("migration_artifact_unreadable") from None
    if (
        final_status.st_dev != status.st_dev
        or final_status.st_ino != status.st_ino
        or final_status.st_size != status.st_size
    ):
        raise SimplifiedMigrationError("migration_artifact_changed")
    return SimplifiedMigrationArtifactV2(
        role=role,
        relative_path=relative,
        present=True,
        device_id=status.st_dev,
        file_id=status.st_ino,
        size_bytes=status.st_size,
        sha256=digest.hexdigest(),
    )


def private_root_digest(root: Path) -> str:
    try:
        resolved = Path(root).resolve(strict=True)
    except OSError:
        raise SimplifiedMigrationError("migration_root_invalid") from None
    return hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()


def _validate_context(context: SimplifiedMigrationCrossbindingV2) -> None:
    if context.context_version != SIMPLIFIED_MIGRATION_CROSSBINDING_VERSION:
        raise SimplifiedMigrationError("migration_crossbinding_version_unsupported")
    for value in (
        context.installation_id,
        context.database_context_id,
        context.migration_id,
        context.dmk_key_id,
        context.database_key_id,
    ):
        try:
            validate_uuid4(value)
        except Exception:
            raise SimplifiedMigrationError("migration_crossbinding_identifier_invalid") from None
    for value in (
        context.migration_generation,
        context.dmk_key_generation,
        context.database_key_generation,
    ):
        if type(value) is not int or value < 1:
            raise SimplifiedMigrationError("migration_crossbinding_generation_invalid")
    for value in (context.journal_revision, context.replay_anchor_revision):
        if type(value) is not int or value < 0:
            raise SimplifiedMigrationError("migration_crossbinding_revision_invalid")
    for value in (
        context.envelope_registry_sha256,
        context.journal_sha256,
        context.lock_chain_head_sha256,
        context.private_root_sha256,
    ):
        _require_sha256(value)
    if not isinstance(context.journal_phase, str) or not _SAFE_PHASE.fullmatch(
        context.journal_phase
    ):
        raise SimplifiedMigrationError("migration_crossbinding_phase_invalid")
    if tuple(item.role for item in context.artifacts) != SIMPLIFIED_MIGRATION_ARTIFACT_ROLES:
        raise SimplifiedMigrationError("migration_crossbinding_artifacts_invalid")
    if len({item.relative_path for item in context.artifacts}) != 3:
        raise SimplifiedMigrationError("migration_crossbinding_artifacts_invalid")
    for item in context.artifacts:
        _validate_artifact(item)
    for value in (context.expected_sqlite_version, context.expected_sqlcipher_version):
        if not isinstance(value, str) or not _VERSION.fullmatch(value):
            raise SimplifiedMigrationError("migration_crossbinding_engine_version_invalid")
    if type(context.expected_schema_version) is not int or context.expected_schema_version < 1:
        raise SimplifiedMigrationError("migration_crossbinding_schema_version_invalid")


def _validate_artifact(artifact: SimplifiedMigrationArtifactV2) -> None:
    if artifact.role not in SIMPLIFIED_MIGRATION_ARTIFACT_ROLES:
        raise SimplifiedMigrationError("migration_artifact_role_invalid")
    _validated_relative_path(artifact.relative_path)
    if type(artifact.present) is not bool:
        raise SimplifiedMigrationError("migration_artifact_presence_invalid")
    values = (artifact.device_id, artifact.file_id, artifact.size_bytes, artifact.sha256)
    if not artifact.present:
        if any(value is not None for value in values):
            raise SimplifiedMigrationError("migration_artifact_absence_invalid")
        return
    if any(type(value) is not int or value < 0 for value in values[:3]):
        raise SimplifiedMigrationError("migration_artifact_identity_invalid")
    _require_sha256(artifact.sha256)


def _validated_relative_path(value: str) -> str:
    if not isinstance(value, str) or "\\" in value:
        raise SimplifiedMigrationError("migration_artifact_path_invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or len(path.parts) > 3:
        raise SimplifiedMigrationError("migration_artifact_path_invalid")
    if any(part in {"", ".", ".."} or not _SAFE_COMPONENT.fullmatch(part) for part in path.parts):
        raise SimplifiedMigrationError("migration_artifact_path_invalid")
    normalized = path.as_posix()
    if normalized != value:
        raise SimplifiedMigrationError("migration_artifact_path_invalid")
    return normalized


def _require_sha256(value: object) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise SimplifiedMigrationError("migration_crossbinding_digest_invalid")


def _canonical_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


__all__ = [
    "EMPTY_SHA256",
    "SIMPLIFIED_MIGRATION_ARTIFACT_ROLES",
    "SIMPLIFIED_MIGRATION_CROSSBINDING_VERSION",
    "SimplifiedMigrationArtifactV2",
    "SimplifiedMigrationCrossbindingV2",
    "SimplifiedMigrationError",
    "SimplifiedMigrationPreflightEvidenceV2",
    "SimplifiedMigrationPreflightMode",
    "SimplifiedMigrationRecoveryDecision",
    "absent_simplified_artifact",
    "capture_simplified_artifact",
    "derive_simplified_migration_preflight_v2",
    "derive_simplified_recovery_decision",
    "private_root_digest",
]
