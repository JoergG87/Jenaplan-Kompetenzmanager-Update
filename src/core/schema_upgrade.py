"""Pure future upgrade contracts. No I/O, migration or runtime admission."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
from uuid import UUID

from .schema_registry import DatabaseSchemaRegistry, RegisteredSchemaIdentity


class UpgradeError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class UpgradePhase(str, Enum):
    PREFLIGHT = "preflight"
    EXCLUSIVE = "exclusive"
    SOURCE_VERIFIED = "source_verified"
    BACKUP_VERIFIED = "backup_verified"
    STAGED = "staged"
    MIGRATED = "migrated"
    TARGET_VERIFIED = "target_verified"
    ACTIVATION_PREPARED = "activation_prepared"
    ACTIVATING = "activating"
    RUNTIME_VERIFIED = "runtime_verified"
    COMPLETED = "completed"
    ABORTED = "aborted"
    RECOVERY_REQUIRED = "recovery_required"


_NEXT = {
    UpgradePhase.PREFLIGHT: UpgradePhase.EXCLUSIVE,
    UpgradePhase.EXCLUSIVE: UpgradePhase.SOURCE_VERIFIED,
    UpgradePhase.SOURCE_VERIFIED: UpgradePhase.BACKUP_VERIFIED,
    UpgradePhase.BACKUP_VERIFIED: UpgradePhase.STAGED,
    UpgradePhase.STAGED: UpgradePhase.MIGRATED,
    UpgradePhase.MIGRATED: UpgradePhase.TARGET_VERIFIED,
    UpgradePhase.TARGET_VERIFIED: UpgradePhase.ACTIVATION_PREPARED,
    UpgradePhase.ACTIVATION_PREPARED: UpgradePhase.ACTIVATING,
    UpgradePhase.ACTIVATING: UpgradePhase.RUNTIME_VERIFIED,
    UpgradePhase.RUNTIME_VERIFIED: UpgradePhase.COMPLETED,
}
_TERMINAL = {UpgradePhase.COMPLETED, UpgradePhase.ABORTED, UpgradePhase.RECOVERY_REQUIRED}
_ACTIVATED = {UpgradePhase.ACTIVATING, UpgradePhase.RUNTIME_VERIFIED, UpgradePhase.COMPLETED}


def _uuid(value: str) -> None:
    try:
        valid = isinstance(value, str) and str(UUID(value)) == value and UUID(value).version == 4
    except (ValueError, TypeError, AttributeError):
        valid = False
    if not valid:
        raise UpgradeError("upgrade_identity_invalid")


@dataclass(frozen=True)
class UpgradeContext:
    operation_id: str
    installation_id: str
    database_context_id: str
    database_key_id: str
    database_key_generation: int
    dmk_key_id: str
    dmk_generation: int
    source: RegisteredSchemaIdentity
    target: RegisteredSchemaIdentity
    transformation_id: str

    def __post_init__(self) -> None:
        for value in (self.operation_id, self.installation_id, self.database_context_id,
                      self.database_key_id, self.dmk_key_id):
            _uuid(value)
        for value in (self.database_key_generation, self.dmk_generation):
            if type(value) is not int or value < 1:
                raise UpgradeError("upgrade_key_generation_invalid")
        if not all(isinstance(value, RegisteredSchemaIdentity) for value in (self.source, self.target)):
            raise UpgradeError("upgrade_schema_identity_invalid")
        if not isinstance(self.transformation_id, str) or re.fullmatch(
            r"[a-z][a-z0-9_-]{0,79}", self.transformation_id
        ) is None:
            raise UpgradeError("upgrade_transformation_invalid")


@dataclass(frozen=True)
class UpgradeArtifact:
    """Technical receipt; actual file/key/schema verification is a separate port."""
    role: str
    artifact_id: str
    sha256: str
    device_id: int
    file_id: int
    size_bytes: int
    schema: RegisteredSchemaIdentity

    def __post_init__(self) -> None:
        if self.role not in {"source", "backup", "candidate", "live"}:
            raise UpgradeError("upgrade_artifact_role_invalid")
        _uuid(self.artifact_id)
        if not isinstance(self.sha256, str) or re.fullmatch(r"[0-9a-f]{64}", self.sha256) is None:
            raise UpgradeError("upgrade_artifact_hash_invalid")
        if any(type(value) is not int or value < 0 for value in (self.device_id, self.file_id, self.size_bytes)):
            raise UpgradeError("upgrade_artifact_identity_invalid")
        if self.file_id == 0 or self.size_bytes == 0 or not isinstance(self.schema, RegisteredSchemaIdentity):
            raise UpgradeError("upgrade_artifact_identity_invalid")


@dataclass(frozen=True)
class UpgradeEvidence:
    context: UpgradeContext
    phase: UpgradePhase
    artifacts: tuple[UpgradeArtifact, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.context, UpgradeContext) or not isinstance(self.phase, UpgradePhase):
            raise UpgradeError("upgrade_evidence_invalid")
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        if any(not isinstance(item, UpgradeArtifact) for item in self.artifacts):
            raise UpgradeError("upgrade_evidence_invalid")
        if len({item.role for item in self.artifacts}) != len(self.artifacts):
            raise UpgradeError("upgrade_evidence_duplicate")


@dataclass(frozen=True)
class UpgradeState:
    context: UpgradeContext
    phase: UpgradePhase = UpgradePhase.PREFLIGHT
    revision: int = 0
    evidence: tuple[UpgradeEvidence, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))


def new_upgrade_state(context: UpgradeContext, registry: DatabaseSchemaRegistry) -> UpgradeState:
    registry.require_upgrade(context.source, context.target)
    return UpgradeState(context)


def _allowed(source: UpgradePhase, target: UpgradePhase) -> bool:
    if source in _TERMINAL:
        return False
    if target is UpgradePhase.RECOVERY_REQUIRED:
        return True
    if target is UpgradePhase.ABORTED:
        return source not in _ACTIVATED
    return _NEXT.get(source) is target


def _require_receipt(context: UpgradeContext, evidence: UpgradeEvidence) -> None:
    if evidence.context != context:
        raise UpgradeError("upgrade_evidence_context_mismatch")
    roles = {item.role: item for item in evidence.artifacts}
    required = {
        UpgradePhase.SOURCE_VERIFIED: ("source", context.source),
        UpgradePhase.BACKUP_VERIFIED: ("backup", context.source),
        UpgradePhase.STAGED: ("candidate", context.source),
        UpgradePhase.MIGRATED: ("candidate", context.target),
        UpgradePhase.TARGET_VERIFIED: ("candidate", context.target),
        UpgradePhase.ACTIVATION_PREPARED: ("candidate", context.target),
        UpgradePhase.ACTIVATING: ("candidate", context.target),
        UpgradePhase.RUNTIME_VERIFIED: ("live", context.target),
        UpgradePhase.COMPLETED: ("live", context.target),
    }.get(evidence.phase)
    if required is not None:
        role, schema = required
        if role not in roles or roles[role].schema != schema:
            raise UpgradeError("upgrade_required_artifact_missing")
    for item in evidence.artifacts:
        expected = context.source if item.role in {"source", "backup"} else context.target
        if evidence.phase is UpgradePhase.STAGED and item.role == "candidate":
            expected = context.source
        if item.schema != expected:
            raise UpgradeError("upgrade_artifact_schema_mismatch")


def validate_upgrade_state(state: UpgradeState, registry: DatabaseSchemaRegistry) -> None:
    if not isinstance(state, UpgradeState) or not isinstance(state.context, UpgradeContext):
        raise UpgradeError("upgrade_state_invalid")
    registry.require_upgrade(state.context.source, state.context.target)
    validate_upgrade_structure(state)


def validate_upgrade_structure(state: UpgradeState) -> None:
    if not isinstance(state, UpgradeState) or not isinstance(state.context, UpgradeContext):
        raise UpgradeError("upgrade_state_invalid")
    if type(state.revision) is not int or state.revision != len(state.evidence) or state.revision > 32:
        raise UpgradeError("upgrade_revision_invalid")
    phase = UpgradePhase.PREFLIGHT
    recorded = {}
    for receipt in state.evidence:
        if not isinstance(receipt, UpgradeEvidence) or not _allowed(phase, receipt.phase):
            raise UpgradeError("upgrade_transition_invalid")
        _require_receipt(state.context, receipt)
        for artifact in receipt.artifacts:
            if artifact.role == "live":
                candidate = recorded.get("candidate")
                if candidate is None or replace(candidate, role="live") != artifact:
                    raise UpgradeError("upgrade_live_candidate_mismatch")
            previous = recorded.get(artifact.role)
            if previous is not None and previous != artifact:
                if not (artifact.role == "candidate" and receipt.phase is UpgradePhase.MIGRATED
                        and (previous.artifact_id, previous.device_id, previous.file_id) ==
                        (artifact.artifact_id, artifact.device_id, artifact.file_id)):
                    raise UpgradeError("upgrade_artifact_changed")
            recorded[artifact.role] = artifact
        phase = receipt.phase
    if not isinstance(state.phase, UpgradePhase) or phase is not state.phase:
        raise UpgradeError("upgrade_phase_invalid")


def advance_upgrade(state: UpgradeState, evidence: UpgradeEvidence,
                    registry: DatabaseSchemaRegistry) -> UpgradeState:
    validate_upgrade_state(state, registry)
    if state.evidence and evidence == state.evidence[-1]:
        return state  # exact retry only, no new revision
    if not isinstance(evidence, UpgradeEvidence) or not _allowed(state.phase, evidence.phase):
        raise UpgradeError("upgrade_transition_invalid")
    _require_receipt(state.context, evidence)
    replacement = replace(state, phase=evidence.phase, revision=state.revision + 1,
                          evidence=(*state.evidence, evidence))
    validate_upgrade_state(replacement, registry)
    return replacement


class UpgradeRecoveryStatus(str, Enum):
    NO_OPERATION = "no_operation"
    ABORTED = "aborted"
    NOT_ACTIVATED = "not_activated"
    VERIFY_CANDIDATE = "verify_candidate"
    RECOVERY_REQUIRED = "recovery_required"
    COMPLETED = "completed"


@dataclass(frozen=True)
class UpgradeRecoveryDecision:
    status: UpgradeRecoveryStatus
    reason: str

    @property
    def activation_allowed(self) -> bool:
        return False

    @property
    def normal_runtime_allowed(self) -> bool:
        return False


def classify_upgrade(state: UpgradeState | None, *, expected_context: UpgradeContext | None,
                     observed: tuple[UpgradeArtifact, ...], registry: DatabaseSchemaRegistry,
                     inventory_complete: bool, journal_authenticated: bool) -> UpgradeRecoveryDecision:
    """Classification only. Authentication/fresh observations are caller obligations.

    No result is a startup, restore or activation capability. Replay freshness
    is enforced separately by the upgrade journal repository high-water mark;
    authentication alone is insufficient. Full local rollback remains undetectable.
    """
    blocked = UpgradeRecoveryDecision(UpgradeRecoveryStatus.RECOVERY_REQUIRED, "upgrade_evidence_required")
    if inventory_complete is not True:
        return blocked
    if state is None:
        return UpgradeRecoveryDecision(UpgradeRecoveryStatus.NO_OPERATION, "upgrade_absent") if not observed else blocked
    if not isinstance(state, UpgradeState) or journal_authenticated is not True or state.context != expected_context:
        return blocked
    try:
        validate_upgrade_state(state, registry)
    except ValueError:
        return blocked
    if any(not isinstance(item, UpgradeArtifact) for item in observed):
        return blocked
    if len({item.role for item in observed}) != len(observed):
        return blocked
    actual = {item.role: item for item in observed}
    recorded = {item.role: item for receipt in state.evidence for item in receipt.artifacts}
    if any(recorded.get(role) != item for role, item in actual.items()):
        return blocked
    required = "live" if state.phase is UpgradePhase.COMPLETED else "source"
    if required not in actual or recorded.get(required) != actual[required]:
        return blocked
    if "source" not in actual or recorded.get("source") != actual["source"]:
        return blocked
    if "backup" in recorded and actual.get("backup") != recorded["backup"]:
        return blocked
    if state.phase is UpgradePhase.COMPLETED:
        status = UpgradeRecoveryStatus.COMPLETED
    elif state.phase is UpgradePhase.ABORTED:
        status = UpgradeRecoveryStatus.ABORTED
    elif state.phase in _ACTIVATED or state.phase is UpgradePhase.RECOVERY_REQUIRED:
        return blocked
    elif "candidate" in recorded:
        if actual.get("candidate") != recorded["candidate"]:
            return blocked
        status = UpgradeRecoveryStatus.VERIFY_CANDIDATE
    else:
        status = UpgradeRecoveryStatus.NOT_ACTIVATED
    return UpgradeRecoveryDecision(status, "upgrade_classified_without_admission")
