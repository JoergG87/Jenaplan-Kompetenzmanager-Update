"""Pure recovery-aware preflight derivation from authenticated projections.

Infrastructure adapters must authenticate every source before creating these
projections. The journal projection keeps the repository byte digest separate
from its recomputed field seal. A lock projection is created from the actual
HMAC-bearing transition, whose full-entry digest is compared with the context.
The domain layer crosschecks both against an independently authenticated
migration context; no projection factory authenticates storage or an HMAC.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import re

from .migration_context import (
    MIGRATION_ARTIFACT_ROLES,
    MigrationArtifactBinding,
    MigrationCrossbindingContext,
    MigrationCrossbindingError,
    require_matching_migration_contexts,
)
from .domain import validate_uuid4
from .lock_transition import AuthenticatedLockTransition
from .migration_journal import MigrationJournalState, MigrationPhase


_SAFE_NAME = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,159}\Z")
_VERSION = re.compile(r"\A[0-9]+(?:\.[0-9]+){1,3}(?:[-+][A-Za-z0-9.-]+)?\Z")
_LOCK_TRANSITIONS = frozenset(
    {
        "ACQUIRED",
        "RELEASED",
        "STALE_DETECTED",
        "TAKEOVER_PREPARED",
        "TAKEOVER_COMMITTED",
        "BLOCKED",
    }
)
_AUTHENTICATED_SOURCES = ("anchor", "envelope_registry", "journal", "lock_chain")


class MigrationPreflightMode(StrEnum):
    NEW = "NEW"
    RESUME = "RESUME"
    RECOVERY = "RECOVERY"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AuthenticatedSourceAbsence:
    """Adapter-authenticated proof that one source does not exist."""

    source: str
    installation_id: str
    database_context_id: str
    proof_sha256: str

    @classmethod
    def create(
        cls, *, source: str, installation_id: str, database_context_id: str
    ) -> AuthenticatedSourceAbsence:
        """Seal values obtained from an adapter-authenticated absence check."""
        values = (source, installation_id, database_context_id)
        return cls(*values, proof_sha256=_canonical_digest(values))


@dataclass(frozen=True)
class AuthenticatedReplayAnchorProjection:
    installation_id: str
    database_context_id: str
    dmk_key_id: str
    dmk_key_generation: int
    migration_generation: int
    revision: int
    canonical_sha256: str


@dataclass(frozen=True)
class AuthenticatedEnvelopeRegistryProjection:
    installation_id: str
    database_context_id: str
    dmk_key_id: str
    dmk_key_generation: int
    database_key_id: str
    database_key_generation: int
    revision: int
    canonical_sha256: str


@dataclass(frozen=True)
class AuthenticatedJournalProjection:
    installation_id: str
    database_context_id: str
    migration_id: str
    dmk_key_id: str
    dmk_key_generation: int
    database_key_id: str
    database_key_generation: int
    revision: int
    source_sha256: str
    projection_sha256: str
    phase: MigrationPhase

    @classmethod
    def create(
        cls,
        *,
        installation_id: str,
        database_context_id: str,
        migration_id: str,
        dmk_key_id: str,
        dmk_key_generation: int,
        database_key_id: str,
        database_key_generation: int,
        revision: int,
        source_sha256: str,
        phase: MigrationPhase,
    ) -> AuthenticatedJournalProjection:
        """Seal fields extracted from an HMAC-authenticated journal."""
        values = (
            installation_id,
            database_context_id,
            migration_id,
            dmk_key_id,
            dmk_key_generation,
            database_key_id,
            database_key_generation,
            revision,
            source_sha256,
            phase,
        )
        return cls(
            installation_id,
            database_context_id,
            migration_id,
            dmk_key_id,
            dmk_key_generation,
            database_key_id,
            database_key_generation,
            revision,
            source_sha256,
            _journal_projection_digest(values),
            phase,
        )

    @classmethod
    def from_authenticated_state(
        cls,
        *,
        installation_id: str,
        state: MigrationJournalState,
        source_sha256: str,
    ) -> AuthenticatedJournalProjection:
        """Project a journal returned by an authenticating repository adapter."""

        return cls.create(
            installation_id=installation_id,
            database_context_id=state.data_context_id,
            migration_id=state.migration_id,
            dmk_key_id=state.wrapping_dmk_key_id,
            dmk_key_generation=state.wrapping_dmk_generation,
            database_key_id=state.database_key_id,
            database_key_generation=state.database_key_generation,
            revision=state.revision,
            source_sha256=source_sha256,
            phase=state.phase,
        )


@dataclass(frozen=True)
class AuthenticatedLockHeadProjection:
    transition: AuthenticatedLockTransition

    @classmethod
    def from_authenticated_transition(
        cls, transition: AuthenticatedLockTransition
    ) -> AuthenticatedLockHeadProjection:
        """Project a transition after its HMAC chain has been verified."""

        return cls(transition)

    @property
    def installation_id(self) -> str:
        return self.transition.installation_id

    @property
    def database_context_id(self) -> str:
        return self.transition.database_context_id

    @property
    def migration_id(self) -> str:
        return self.transition.migration_id

    @property
    def migration_context_digest(self) -> str:
        return self.transition.migration_context_digest

    @property
    def sequence(self) -> int:
        return self.transition.sequence

    @property
    def source_sha256(self) -> str:
        return self.transition.digest()

    @property
    def transition_type(self) -> str:
        return self.transition.transition.name

    @property
    def owner_before_sha256(self) -> str:
        return self.transition.owner_before_digest

    @property
    def owner_after_sha256(self) -> str:
        return self.transition.owner_after_digest

    @property
    def replay_anchor_revision(self) -> int:
        return self.transition.replay_anchor_revision

    @property
    def replay_anchor_sha256(self) -> str:
        return self.transition.replay_anchor_digest

    @property
    def journal_sha256(self) -> str:
        return self.transition.journal_digest


@dataclass(frozen=True)
class AuthenticatedArtifactProjection:
    installation_id: str
    database_context_id: str
    migration_id: str | None
    expected_artifacts: tuple[MigrationArtifactBinding, ...]
    observed_artifacts: tuple[MigrationArtifactBinding, ...]
    unexpected_artifacts: tuple[str, ...]
    proof_sha256: str

    @classmethod
    def create(
        cls,
        *,
        installation_id: str,
        database_context_id: str,
        migration_id: str | None,
        expected_artifacts: tuple[MigrationArtifactBinding, ...],
        observed_artifacts: tuple[MigrationArtifactBinding, ...],
        unexpected_artifacts: tuple[str, ...],
    ) -> AuthenticatedArtifactProjection:
        """Seal results from a capability-authenticated artifact observer."""
        values = (
            installation_id,
            database_context_id,
            migration_id,
            expected_artifacts,
            observed_artifacts,
            unexpected_artifacts,
        )
        return cls(*values, proof_sha256=_artifact_projection_digest(*values))


@dataclass(frozen=True)
class AuthenticatedMigrationPreflightProjection:
    """Read-only, source-specific projections authenticated by their adapters."""

    expected_context: MigrationCrossbindingContext | None
    authenticated_context: MigrationCrossbindingContext | None
    replay_anchor: AuthenticatedReplayAnchorProjection | AuthenticatedSourceAbsence
    envelope_registry: (
        AuthenticatedEnvelopeRegistryProjection | AuthenticatedSourceAbsence
    )
    journal: AuthenticatedJournalProjection | AuthenticatedSourceAbsence
    lock_head: AuthenticatedLockHeadProjection | AuthenticatedSourceAbsence
    artifacts: AuthenticatedArtifactProjection
    expected_sqlite_version: str
    observed_sqlite_version: str
    expected_sqlcipher_version: str
    observed_sqlcipher_version: str
    expected_schema_version: int
    observed_schema_version: int


@dataclass(frozen=True)
class MigrationPreflightDecision:
    mode: MigrationPreflightMode
    error_code: str | None = None


_RESUME_PHASES = frozenset(
    {
        MigrationPhase.NOT_STARTED,
        MigrationPhase.PREFLIGHT_STARTED,
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_VERIFIED,
        MigrationPhase.EXPORT_COMPLETED,
        MigrationPhase.VALIDATION_COMPLETED,
        MigrationPhase.REOPEN_VERIFIED,
    }
)
_RECOVERY_PHASES = frozenset(
    {
        MigrationPhase.BACKUP_STARTED,
        MigrationPhase.BACKUP_CREATED,
        MigrationPhase.TARGET_CREATION_STARTED,
        MigrationPhase.TARGET_CREATED,
        MigrationPhase.EXPORT_STARTED,
        MigrationPhase.VALIDATION_STARTED,
        MigrationPhase.REOPEN_STARTED,
        MigrationPhase.ROLLBACK_STARTED,
        MigrationPhase.ROLLBACK_COMPLETED,
    }
)
_BLOCKED_PHASES = frozenset(
    {
        MigrationPhase.SWAP_PREPARED,
        MigrationPhase.SWAP_STARTED,
        MigrationPhase.SWAP_COMPLETED,
        MigrationPhase.POST_SWAP_VERIFIED,
        MigrationPhase.FAILED,
        MigrationPhase.BLOCKED,
    }
)


def derive_migration_preflight(
    projection: AuthenticatedMigrationPreflightProjection,
) -> MigrationPreflightDecision:
    """Derive one mode without I/O, mutation, clocks, or environment reads."""

    try:
        _validate_projection_shape(projection)
        if projection.artifacts.unexpected_artifacts:
            return _blocked("migration_preflight_additional_artifact")
        if (
            projection.artifacts.expected_artifacts
            != projection.artifacts.observed_artifacts
        ):
            return _blocked("migration_preflight_artifact_mismatch")
        if not _versions_match(projection):
            return _blocked("migration_preflight_version_mismatch")

        contexts = (projection.expected_context, projection.authenticated_context)
        if contexts == (None, None):
            return _derive_new(projection)
        if None in contexts:
            return _blocked("migration_preflight_context_missing")

        assert projection.expected_context is not None
        assert projection.authenticated_context is not None
        require_matching_migration_contexts(
            projection.expected_context, projection.authenticated_context
        )
        context = projection.expected_context
        if projection.artifacts.expected_artifacts != context.artifacts:
            return _blocked("migration_preflight_artifact_mismatch")
        if (
            projection.expected_sqlite_version != context.expected_sqlite_version
            or projection.expected_sqlcipher_version
            != context.expected_sqlcipher_version
            or projection.expected_schema_version != context.expected_schema_version
        ):
            return _blocked("migration_preflight_version_mismatch")
        if not _authenticated_sources_match(projection, context):
            return _blocked("migration_preflight_authenticated_state_missing")
        assert isinstance(projection.journal, AuthenticatedJournalProjection)
        assert isinstance(projection.lock_head, AuthenticatedLockHeadProjection)
        phase = projection.journal.phase
        lock_transition_type = projection.lock_head.transition_type
        if lock_transition_type == "BLOCKED":
            return _blocked("migration_preflight_lock_blocked")
        if not _phase_artifacts_match(phase, context.artifacts):
            return _blocked("migration_preflight_phase_artifact_mismatch")
        if phase in _BLOCKED_PHASES:
            return _blocked("migration_preflight_phase_blocked")
        if phase is MigrationPhase.COMPLETED:
            if lock_transition_type in {
                "STALE_DETECTED",
                "TAKEOVER_PREPARED",
            }:
                return MigrationPreflightDecision(MigrationPreflightMode.RECOVERY)
            return MigrationPreflightDecision(MigrationPreflightMode.COMPLETED)
        if phase in _RECOVERY_PHASES or lock_transition_type in {
            "STALE_DETECTED",
            "TAKEOVER_PREPARED",
        }:
            return MigrationPreflightDecision(MigrationPreflightMode.RECOVERY)
        if phase in _RESUME_PHASES:
            return MigrationPreflightDecision(MigrationPreflightMode.RESUME)
        return _blocked("migration_preflight_phase_unknown")
    except MigrationCrossbindingError as error:
        return _blocked(error.code)
    except Exception:
        return _blocked("migration_preflight_projection_invalid")


def _derive_new(
    projection: AuthenticatedMigrationPreflightProjection,
) -> MigrationPreflightDecision:
    absences = (
        projection.replay_anchor,
        projection.envelope_registry,
        projection.journal,
        projection.lock_head,
    )
    if not all(isinstance(item, AuthenticatedSourceAbsence) for item in absences):
        return _blocked("migration_preflight_new_state_invalid")
    if tuple(item.source for item in absences) != _AUTHENTICATED_SOURCES:
        return _blocked("migration_preflight_new_state_invalid")
    identity = (
        projection.artifacts.installation_id,
        projection.artifacts.database_context_id,
    )
    if projection.artifacts.migration_id is not None or any(
        (item.installation_id, item.database_context_id) != identity for item in absences
    ):
        return _blocked("migration_preflight_new_state_invalid")
    presence = tuple(
        artifact.present for artifact in projection.artifacts.observed_artifacts
    )
    if presence != (True, False, False):
        return _blocked("migration_preflight_new_roles_not_free")
    return MigrationPreflightDecision(MigrationPreflightMode.NEW)


def _validate_projection_shape(
    projection: AuthenticatedMigrationPreflightProjection,
) -> None:
    if not isinstance(projection, AuthenticatedMigrationPreflightProjection):
        raise TypeError
    if not isinstance(projection.artifacts, AuthenticatedArtifactProjection):
        raise TypeError
    for identifier in (
        projection.artifacts.installation_id,
        projection.artifacts.database_context_id,
    ):
        try:
            validate_uuid4(identifier)
        except Exception:
            raise TypeError from None
    if projection.artifacts.proof_sha256 != _artifact_projection_digest(
        projection.artifacts.installation_id,
        projection.artifacts.database_context_id,
        projection.artifacts.migration_id,
        projection.artifacts.expected_artifacts,
        projection.artifacts.observed_artifacts,
        projection.artifacts.unexpected_artifacts,
    ):
        raise TypeError
    _require_canonical_artifacts(projection.artifacts.expected_artifacts)
    _require_canonical_artifacts(projection.artifacts.observed_artifacts)
    if (
        not isinstance(projection.artifacts.unexpected_artifacts, tuple)
        or tuple(sorted(set(projection.artifacts.unexpected_artifacts)))
        != projection.artifacts.unexpected_artifacts
        or any(
            not isinstance(name, str) or not _SAFE_NAME.fullmatch(name)
            for name in projection.artifacts.unexpected_artifacts
        )
    ):
        raise TypeError
    absence_proofs = tuple(
        source.proof_sha256
        for source in (
            projection.replay_anchor,
            projection.envelope_registry,
            projection.journal,
            projection.lock_head,
        )
        if isinstance(source, AuthenticatedSourceAbsence)
    )
    for digest in (projection.artifacts.proof_sha256, *absence_proofs):
        _require_sha256(digest)
    for source in (
        projection.replay_anchor,
        projection.envelope_registry,
        projection.journal,
        projection.lock_head,
    ):
        if isinstance(source, AuthenticatedSourceAbsence) and source.proof_sha256 != (
            _canonical_digest(
                (source.source, source.installation_id, source.database_context_id)
            )
        ):
            raise TypeError
    if isinstance(projection.journal, AuthenticatedJournalProjection):
        journal_values = (
            projection.journal.installation_id,
            projection.journal.database_context_id,
            projection.journal.migration_id,
            projection.journal.dmk_key_id,
            projection.journal.dmk_key_generation,
            projection.journal.database_key_id,
            projection.journal.database_key_generation,
            projection.journal.revision,
            projection.journal.source_sha256,
            projection.journal.phase,
        )
        if projection.journal.projection_sha256 != _journal_projection_digest(
            journal_values
        ):
            raise TypeError
    if isinstance(projection.lock_head, AuthenticatedLockHeadProjection):
        lock = projection.lock_head
        if not isinstance(lock.transition, AuthenticatedLockTransition) or (
            AuthenticatedLockTransition.from_bytes(lock.transition.to_bytes())
            != lock.transition
        ):
            raise TypeError
    for value in (
        projection.expected_sqlite_version,
        projection.observed_sqlite_version,
        projection.expected_sqlcipher_version,
        projection.observed_sqlcipher_version,
    ):
        if not isinstance(value, str) or not _VERSION.fullmatch(value):
            raise TypeError
    for value in (
        projection.expected_schema_version,
        projection.observed_schema_version,
    ):
        if type(value) is not int or value < 1:
            raise TypeError


def _authenticated_sources_match(
    projection: AuthenticatedMigrationPreflightProjection,
    context: MigrationCrossbindingContext,
) -> bool:
    anchor = projection.replay_anchor
    registry = projection.envelope_registry
    journal = projection.journal
    lock = projection.lock_head
    artifacts = projection.artifacts
    if not (
        isinstance(anchor, AuthenticatedReplayAnchorProjection)
        and isinstance(registry, AuthenticatedEnvelopeRegistryProjection)
        and isinstance(journal, AuthenticatedJournalProjection)
        and isinstance(lock, AuthenticatedLockHeadProjection)
    ):
        return False
    identity = (context.installation_id, context.database_context_id)
    if any(
        (source.installation_id, source.database_context_id) != identity
        for source in (anchor, registry, journal, lock, artifacts)
    ):
        return False
    if artifacts.migration_id != context.migration_id:
        return False
    if (
        anchor.dmk_key_id,
        anchor.dmk_key_generation,
        anchor.migration_generation,
        anchor.revision,
        anchor.canonical_sha256,
    ) != (
        context.dmk_key_id,
        context.dmk_key_generation,
        context.migration_generation,
        context.anchor_revision,
        context.replay_anchor_sha256,
    ):
        return False
    if (
        registry.dmk_key_id,
        registry.dmk_key_generation,
        registry.database_key_id,
        registry.database_key_generation,
        registry.revision,
        registry.canonical_sha256,
    ) != (
        context.dmk_key_id,
        context.dmk_key_generation,
        context.database_key_id,
        context.database_key_generation,
        context.envelope_registry_revision,
        context.envelope_registry_sha256,
    ):
        return False
    if (
        journal.migration_id,
        journal.dmk_key_id,
        journal.dmk_key_generation,
        journal.database_key_id,
        journal.database_key_generation,
        journal.revision,
        journal.source_sha256,
        journal.phase.value,
    ) != (
        context.migration_id,
        context.dmk_key_id,
        context.dmk_key_generation,
        context.database_key_id,
        context.database_key_generation,
        context.journal_revision,
        context.journal_sha256,
        context.journal_phase,
    ):
        return False
    if (
        lock.migration_id,
        lock.migration_context_digest,
        lock.sequence,
        lock.source_sha256,
        lock.transition_type,
        lock.owner_before_sha256,
        lock.owner_after_sha256,
        lock.replay_anchor_revision,
        lock.replay_anchor_sha256,
        lock.journal_sha256,
    ) != (
        context.migration_id,
        context.lock_binding_digest_sha256(),
        context.lock_transition_sequence,
        context.lock_transition_sha256,
        context.lock_transition_type,
        context.lock_owner_before_sha256,
        context.lock_owner_after_sha256,
        context.anchor_revision,
        context.replay_anchor_sha256,
        context.journal_sha256,
    ):
        return False
    return lock.transition_type in _LOCK_TRANSITIONS


def _require_sha256(value: object) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise TypeError


def _journal_projection_digest(values: tuple[object, ...]) -> str:
    serializable = tuple(
        value.value if isinstance(value, MigrationPhase) else value for value in values
    )
    return _canonical_digest(serializable)


def _artifact_projection_digest(
    installation_id: str,
    database_context_id: str,
    migration_id: str | None,
    expected_artifacts: tuple[MigrationArtifactBinding, ...],
    observed_artifacts: tuple[MigrationArtifactBinding, ...],
    unexpected_artifacts: tuple[str, ...],
) -> str:
    return _canonical_digest(
        (
            installation_id,
            database_context_id,
            migration_id,
            tuple(artifact.to_payload() for artifact in expected_artifacts),
            tuple(artifact.to_payload() for artifact in observed_artifacts),
            unexpected_artifacts,
        )
    )


def _canonical_digest(values: tuple[object, ...]) -> str:
    encoded = json.dumps(
        values,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _require_canonical_artifacts(
    artifacts: tuple[MigrationArtifactBinding, ...],
) -> None:
    if not isinstance(artifacts, tuple) or tuple(
        artifact.role for artifact in artifacts
    ) != MIGRATION_ARTIFACT_ROLES:
        raise TypeError


def _versions_match(projection: AuthenticatedMigrationPreflightProjection) -> bool:
    return (
        projection.expected_sqlite_version == projection.observed_sqlite_version
        and projection.expected_sqlcipher_version
        == projection.observed_sqlcipher_version
        and projection.expected_schema_version == projection.observed_schema_version
    )


def _phase_artifacts_match(
    phase: MigrationPhase, artifacts: tuple[MigrationArtifactBinding, ...]
) -> bool:
    presence = tuple(artifact.present for artifact in artifacts)
    if phase in {
        MigrationPhase.NOT_STARTED,
        MigrationPhase.PREFLIGHT_STARTED,
        MigrationPhase.SOURCE_VERIFIED,
        MigrationPhase.BACKUP_STARTED,
    }:
        return presence == (True, False, False)
    if phase in {
        MigrationPhase.BACKUP_CREATED,
        MigrationPhase.BACKUP_VERIFIED,
        MigrationPhase.TARGET_CREATION_STARTED,
        MigrationPhase.ROLLBACK_COMPLETED,
    }:
        return presence == (True, True, False)
    if phase is MigrationPhase.ROLLBACK_STARTED:
        return presence in {(True, True, True), (True, True, False)}
    return presence == (True, True, True)


def _blocked(code: str) -> MigrationPreflightDecision:
    return MigrationPreflightDecision(MigrationPreflightMode.BLOCKED, code)


__all__ = [
    "AuthenticatedArtifactProjection",
    "AuthenticatedEnvelopeRegistryProjection",
    "AuthenticatedJournalProjection",
    "AuthenticatedLockHeadProjection",
    "AuthenticatedMigrationPreflightProjection",
    "AuthenticatedReplayAnchorProjection",
    "AuthenticatedSourceAbsence",
    "MigrationPreflightDecision",
    "MigrationPreflightMode",
    "derive_migration_preflight",
]
