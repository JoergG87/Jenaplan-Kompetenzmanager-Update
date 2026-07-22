"""Canonical, Qt-free crossbinding values for one database migration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re

from .domain import validate_uuid4


MIGRATION_CROSSBINDING_VERSION = 1
MIGRATION_ARTIFACT_ROLES = ("source", "backup", "target")
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_SAFE_FILENAME = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,159}\Z")
_SAFE_TOKEN = re.compile(r"\A[a-z][a-z0-9_-]{0,63}\Z")
_SAFE_IDENTITY = re.compile(r"\A[!-~]{1,160}\Z")
_VERSION = re.compile(r"\A[0-9]+(?:\.[0-9]+){1,3}(?:[-+][A-Za-z0-9.-]+)?\Z")


class MigrationCrossbindingError(RuntimeError):
    """Sanitized validation failure without paths, payloads, or secrets."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class MigrationArtifactBinding:
    """Capability and platform identity for exactly one migration file role."""

    role: str
    capability_id: str
    relative_name: str
    present: bool
    identity_scheme: str | None
    identity_value: str | None
    size_bytes: int | None
    sha256: str | None

    def __post_init__(self) -> None:
        _validate_artifact(self)

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MigrationCrossbindingContext:
    """One immutable binding across every security and file migration input."""

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
    envelope_registry_revision: int
    journal_sha256: str
    journal_revision: int
    journal_phase: str
    anchor_revision: int
    replay_anchor_sha256: str
    lock_transition_sha256: str
    lock_transition_sequence: int
    lock_transition_type: str
    lock_owner_before_sha256: str
    lock_owner_after_sha256: str
    artifacts: tuple[MigrationArtifactBinding, ...]
    expected_sqlite_version: str
    expected_sqlcipher_version: str
    expected_schema_version: int

    def __post_init__(self) -> None:
        _validate_context(self)

    def to_bytes(self) -> bytes:
        return _canonical_bytes(self._payload())

    def lock_binding_digest_sha256(self) -> str:
        """Bind every non-lock input without creating a lock/context cycle."""

        payload = self._payload()
        for field_name in (
            "lock_owner_after_sha256",
            "lock_owner_before_sha256",
            "lock_transition_sequence",
            "lock_transition_sha256",
            "lock_transition_type",
        ):
            del payload[field_name]
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()

    def _payload(self) -> dict[str, object]:
        return {
            "anchor_revision": self.anchor_revision,
            "artifacts": [artifact.to_payload() for artifact in self.artifacts],
            "context_version": self.context_version,
            "database_context_id": self.database_context_id,
            "database_key_generation": self.database_key_generation,
            "database_key_id": self.database_key_id,
            "dmk_key_generation": self.dmk_key_generation,
            "dmk_key_id": self.dmk_key_id,
            "envelope_registry_revision": self.envelope_registry_revision,
            "envelope_registry_sha256": self.envelope_registry_sha256,
            "expected_schema_version": self.expected_schema_version,
            "expected_sqlcipher_version": self.expected_sqlcipher_version,
            "expected_sqlite_version": self.expected_sqlite_version,
            "installation_id": self.installation_id,
            "journal_revision": self.journal_revision,
            "journal_sha256": self.journal_sha256,
            "journal_phase": self.journal_phase,
            "lock_owner_after_sha256": self.lock_owner_after_sha256,
            "lock_owner_before_sha256": self.lock_owner_before_sha256,
            "lock_transition_sequence": self.lock_transition_sequence,
            "lock_transition_sha256": self.lock_transition_sha256,
            "lock_transition_type": self.lock_transition_type,
            "migration_generation": self.migration_generation,
            "migration_id": self.migration_id,
            "replay_anchor_sha256": self.replay_anchor_sha256,
        }
    def digest_sha256(self) -> str:
        return hashlib.sha256(self.to_bytes()).hexdigest()


def _canonical_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")


def require_matching_migration_contexts(
    expected: MigrationCrossbindingContext,
    observed: MigrationCrossbindingContext,
) -> None:
    """Fail closed unless every canonical crossbinding byte is identical."""

    if not isinstance(expected, MigrationCrossbindingContext) or not isinstance(
        observed, MigrationCrossbindingContext
    ):
        raise MigrationCrossbindingError("migration_crossbinding_context_invalid")
    if expected.to_bytes() != observed.to_bytes():
        raise MigrationCrossbindingError("migration_crossbinding_mismatch")


def _validate_context(context: MigrationCrossbindingContext) -> None:
    if (
        type(context.context_version) is not int
        or context.context_version != MIGRATION_CROSSBINDING_VERSION
    ):
        raise MigrationCrossbindingError("migration_crossbinding_version_unsupported")
    for identifier in (
        context.installation_id,
        context.database_context_id,
        context.migration_id,
        context.dmk_key_id,
        context.database_key_id,
    ):
        _require_uuid(identifier)
    for value in (
        context.migration_generation,
        context.dmk_key_generation,
        context.database_key_generation,
        context.envelope_registry_revision,
        context.anchor_revision,
        context.lock_transition_sequence,
    ):
        _require_positive_int(value)
    if type(context.journal_revision) is not int or context.journal_revision < 0:
        raise MigrationCrossbindingError("migration_crossbinding_revision_invalid")
    for digest in (
        context.envelope_registry_sha256,
        context.journal_sha256,
        context.replay_anchor_sha256,
        context.lock_transition_sha256,
        context.lock_owner_before_sha256,
        context.lock_owner_after_sha256,
    ):
        _require_sha256(digest)
    if not isinstance(context.journal_phase, str) or not _SAFE_TOKEN.fullmatch(
        context.journal_phase
    ):
        raise MigrationCrossbindingError("migration_crossbinding_journal_phase_invalid")
    if context.lock_transition_type not in {
        "ACQUIRED",
        "RELEASED",
        "STALE_DETECTED",
        "TAKEOVER_PREPARED",
        "TAKEOVER_COMMITTED",
        "BLOCKED",
    }:
        raise MigrationCrossbindingError("migration_crossbinding_lock_transition_invalid")
    if not isinstance(context.artifacts, tuple) or tuple(
        artifact.role for artifact in context.artifacts
    ) != MIGRATION_ARTIFACT_ROLES:
        raise MigrationCrossbindingError("migration_crossbinding_artifacts_invalid")
    if len({artifact.capability_id for artifact in context.artifacts}) != len(
        MIGRATION_ARTIFACT_ROLES
    ) or len({artifact.relative_name for artifact in context.artifacts}) != len(
        MIGRATION_ARTIFACT_ROLES
    ):
        raise MigrationCrossbindingError("migration_crossbinding_artifacts_invalid")
    present_identities = tuple(
        (artifact.identity_scheme, artifact.identity_value)
        for artifact in context.artifacts
        if artifact.present
    )
    if len(set(present_identities)) != len(present_identities):
        raise MigrationCrossbindingError("migration_crossbinding_artifacts_invalid")
    for artifact in context.artifacts:
        _validate_artifact(artifact)
    _require_version(context.expected_sqlite_version)
    _require_version(context.expected_sqlcipher_version)
    if (
        type(context.expected_schema_version) is not int
        or context.expected_schema_version < 1
    ):
        raise MigrationCrossbindingError("migration_crossbinding_schema_version_invalid")


def _validate_artifact(artifact: MigrationArtifactBinding) -> None:
    if not isinstance(artifact.role, str) or artifact.role not in MIGRATION_ARTIFACT_ROLES:
        raise MigrationCrossbindingError("migration_artifact_role_invalid")
    _require_uuid(artifact.capability_id)
    if not isinstance(artifact.relative_name, str) or not _SAFE_FILENAME.fullmatch(
        artifact.relative_name
    ):
        raise MigrationCrossbindingError("migration_artifact_name_invalid")
    if type(artifact.present) is not bool:
        raise MigrationCrossbindingError("migration_artifact_presence_invalid")
    identity_values = (
        artifact.identity_scheme,
        artifact.identity_value,
        artifact.size_bytes,
        artifact.sha256,
    )
    if not artifact.present:
        if any(value is not None for value in identity_values):
            raise MigrationCrossbindingError("migration_artifact_absence_invalid")
        return
    if (
        not isinstance(artifact.identity_scheme, str)
        or not _SAFE_TOKEN.fullmatch(artifact.identity_scheme)
        or not isinstance(artifact.identity_value, str)
        or not _SAFE_IDENTITY.fullmatch(artifact.identity_value)
        or type(artifact.size_bytes) is not int
        or artifact.size_bytes < 0
    ):
        raise MigrationCrossbindingError("migration_artifact_identity_invalid")
    _require_sha256(artifact.sha256)


def _require_uuid(value: object) -> None:
    try:
        validate_uuid4(value)
    except Exception:
        raise MigrationCrossbindingError("migration_crossbinding_identifier_invalid") from None


def _require_positive_int(value: object) -> None:
    if type(value) is not int or value < 1:
        raise MigrationCrossbindingError("migration_crossbinding_revision_invalid")


def _require_sha256(value: object) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise MigrationCrossbindingError("migration_crossbinding_digest_invalid")


def _require_version(value: object) -> None:
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        raise MigrationCrossbindingError("migration_crossbinding_engine_version_invalid")


__all__ = [
    "MIGRATION_ARTIFACT_ROLES",
    "MIGRATION_CROSSBINDING_VERSION",
    "MigrationArtifactBinding",
    "MigrationCrossbindingContext",
    "MigrationCrossbindingError",
    "require_matching_migration_contexts",
]
