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
    ACTIVATION_INTENT = "activation_intent"
    TARGET_INSTALLED = "target_installed"
    RESTART_CONFIRMED = "restart_confirmed"
    WRITES_ENABLED = "writes_enabled"
    ROLLBACK_INTENT = "rollback_intent"
    ROLLBACK_INSTALLED = "rollback_installed"
    ROLLED_BACK = "rolled_back"


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
        if self.role not in {"source", "backup", "candidate", "live", "rollback", "rollback_live"}:
            raise UpgradeError("upgrade_artifact_role_invalid")
        _uuid(self.artifact_id)
        if not isinstance(self.sha256, str) or re.fullmatch(r"[0-9a-f]{64}", self.sha256) is None:
            raise UpgradeError("upgrade_artifact_hash_invalid")
        if any(type(value) is not int or value < 0 for value in (self.device_id, self.file_id, self.size_bytes)):
            raise UpgradeError("upgrade_artifact_identity_invalid")
        if self.file_id == 0 or self.size_bytes == 0 or not isinstance(self.schema, RegisteredSchemaIdentity):
            raise UpgradeError("upgrade_artifact_identity_invalid")


@dataclass(frozen=True)
class UpgradeExchangeIntent:
    """Expected before/after identities, never proof that a replacement occurred."""
    context: UpgradeContext
    intent_id: str
    direction: str
    expected_live: UpgradeArtifact
    replacement: UpgradeArtifact

    def __post_init__(self):
        _uuid(self.intent_id)
        if (not isinstance(self.context, UpgradeContext)
                or self.direction not in {"activate", "rollback"}
                or not isinstance(self.expected_live, UpgradeArtifact)
                or not isinstance(self.replacement, UpgradeArtifact)):
            raise UpgradeError("upgrade_exchange_intent_invalid")


@dataclass(frozen=True)
class UpgradeExchangeResult:
    """A later verifier's exact observed result of one bound exchange intent."""
    context: UpgradeContext
    intent_id: str
    installed: UpgradeArtifact

    def __post_init__(self):
        _uuid(self.intent_id)
        if not isinstance(self.context, UpgradeContext) or not isinstance(self.installed, UpgradeArtifact):
            raise UpgradeError("upgrade_exchange_result_invalid")


@dataclass(frozen=True)
class UpgradeRestartReceipt:
    context: UpgradeContext
    restart_id: str
    installed: UpgradeArtifact

    def __post_init__(self):
        _uuid(self.restart_id)
        if not isinstance(self.context, UpgradeContext) or not isinstance(self.installed, UpgradeArtifact):
            raise UpgradeError("upgrade_restart_receipt_invalid")


@dataclass(frozen=True)
class UpgradeTargetInspection:
    """Technical verifier evidence, not an implemented verifier or capability.

    After WRITES_ENABLED target is a fresh snapshot and need not have the
    original candidate bytes/inode. The logical artifact and context stay bound.
    """
    context: UpgradeContext
    inspection_id: str
    restart_id: str
    target: UpgradeArtifact
    integrity_verified: bool
    key_context_verified: bool
    domain_verified: bool
    documents_verified: bool

    def __post_init__(self):
        _uuid(self.inspection_id)
        _uuid(self.restart_id)
        if (not isinstance(self.context, UpgradeContext)
                or not isinstance(self.target, UpgradeArtifact)
                or self.target.role != "live" or self.target.schema != self.context.target
                or any(value is not True for value in (
                    self.integrity_verified, self.key_context_verified,
                    self.domain_verified, self.documents_verified))):
            raise UpgradeError("upgrade_target_inspection_invalid")


@dataclass(frozen=True)
class UpgradeEvidence:
    context: UpgradeContext
    phase: UpgradePhase
    artifacts: tuple[UpgradeArtifact, ...] = ()
    exchange_intent: UpgradeExchangeIntent | None = None
    exchange_result: UpgradeExchangeResult | None = None
    restart: UpgradeRestartReceipt | None = None
    inspection: UpgradeTargetInspection | None = None

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
    contract_version: int = 2

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))


def new_upgrade_state(context: UpgradeContext, registry: DatabaseSchemaRegistry) -> UpgradeState:
    registry.require_upgrade(context.source, context.target)
    return UpgradeState(context)


def _allowed_legacy(source: UpgradePhase, target: UpgradePhase) -> bool:
    if source in _TERMINAL:
        return False
    if target is UpgradePhase.RECOVERY_REQUIRED:
        return True
    if target is UpgradePhase.ABORTED:
        return source not in _ACTIVATED
    return _NEXT.get(source) is target


def _require_legacy_receipt(context: UpgradeContext, evidence: UpgradeEvidence) -> None:
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


def _validate_legacy_structure(state: UpgradeState) -> None:
    if not isinstance(state, UpgradeState) or not isinstance(state.context, UpgradeContext):
        raise UpgradeError("upgrade_state_invalid")
    if type(state.revision) is not int or state.revision != len(state.evidence) or state.revision > 32:
        raise UpgradeError("upgrade_revision_invalid")
    phase = UpgradePhase.PREFLIGHT
    recorded = {}
    for receipt in state.evidence:
        if not isinstance(receipt, UpgradeEvidence) or not _allowed_legacy(phase, receipt.phase):
            raise UpgradeError("upgrade_transition_invalid")
        if (any(value is not None for value in (receipt.exchange_intent,
                receipt.exchange_result, receipt.restart, receipt.inspection))
                or any(item.role not in {"source", "backup", "candidate", "live"}
                       for item in receipt.artifacts)):
            raise UpgradeError("upgrade_legacy_receipt_invalid")
        _require_legacy_receipt(state.context, receipt)
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
    if not isinstance(evidence, UpgradeEvidence):
        raise UpgradeError("upgrade_transition_invalid")
    if state.contract_version == 1:
        # Preserve source preparation; old activation histories are read-only.
        if (evidence.phase not in {UpgradePhase.EXCLUSIVE, UpgradePhase.SOURCE_VERIFIED,
                UpgradePhase.BACKUP_VERIFIED, UpgradePhase.STAGED,
                UpgradePhase.ABORTED, UpgradePhase.RECOVERY_REQUIRED}
                or not _allowed_legacy(state.phase, evidence.phase)):
            raise UpgradeError("upgrade_legacy_transition_denied")
    elif not _allowed_v2(state.phase, evidence.phase):
        raise UpgradeError("upgrade_transition_invalid")
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
    INSTALLED = "installed"
    RESTART_VERIFIED = "restart_verified"
    WRITES_ENABLED = "writes_enabled"
    ROLLED_BACK = "rolled_back"


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

    @property
    def writer_admission_allowed(self) -> bool:
        return False

    @property
    def automatic_source_rollback_allowed(self) -> bool:
        return False


def _classify_legacy_upgrade(state: UpgradeState | None, *, expected_context: UpgradeContext | None,
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


_V2_NEXT = {
    **{phase: next_phase for phase, next_phase in _NEXT.items()
       if phase in {UpgradePhase.PREFLIGHT, UpgradePhase.EXCLUSIVE,
                    UpgradePhase.SOURCE_VERIFIED, UpgradePhase.BACKUP_VERIFIED,
                    UpgradePhase.STAGED, UpgradePhase.MIGRATED, UpgradePhase.TARGET_VERIFIED}},
    UpgradePhase.ACTIVATION_PREPARED: UpgradePhase.ACTIVATION_INTENT,
    UpgradePhase.ACTIVATION_INTENT: UpgradePhase.TARGET_INSTALLED,
    UpgradePhase.TARGET_INSTALLED: UpgradePhase.RESTART_CONFIRMED,
    UpgradePhase.RESTART_CONFIRMED: UpgradePhase.RUNTIME_VERIFIED,
    UpgradePhase.RUNTIME_VERIFIED: UpgradePhase.WRITES_ENABLED,
    UpgradePhase.WRITES_ENABLED: UpgradePhase.COMPLETED,
    UpgradePhase.ROLLBACK_INTENT: UpgradePhase.ROLLBACK_INSTALLED,
    UpgradePhase.ROLLBACK_INSTALLED: UpgradePhase.ROLLED_BACK,
}
_V2_ROLLBACK_FROM = {UpgradePhase.ACTIVATION_INTENT, UpgradePhase.TARGET_INSTALLED,
                     UpgradePhase.RESTART_CONFIRMED, UpgradePhase.RUNTIME_VERIFIED}
_V2_PRE_ACTIVATION = {UpgradePhase.PREFLIGHT, UpgradePhase.EXCLUSIVE,
    UpgradePhase.SOURCE_VERIFIED, UpgradePhase.BACKUP_VERIFIED, UpgradePhase.STAGED,
    UpgradePhase.MIGRATED, UpgradePhase.TARGET_VERIFIED, UpgradePhase.ACTIVATION_PREPARED}


def _allowed_v2(source, target):
    if source in _TERMINAL or source is UpgradePhase.ROLLED_BACK:
        return False
    if target is UpgradePhase.RECOVERY_REQUIRED:
        return True
    if target is UpgradePhase.ABORTED:
        return source in _V2_PRE_ACTIVATION
    if target is UpgradePhase.ROLLBACK_INTENT:
        return source in _V2_ROLLBACK_FROM
    return _V2_NEXT.get(source) is target


def validate_upgrade_structure(state: UpgradeState) -> None:
    if (not isinstance(state, UpgradeState) or not isinstance(state.context, UpgradeContext)
            or type(state.contract_version) is not int or state.contract_version not in {1, 2}):
        raise UpgradeError("upgrade_contract_version_invalid")
    if state.contract_version == 1:
        _validate_legacy_structure(state)
        return
    if type(state.revision) is not int or state.revision != len(state.evidence) or state.revision > 32:
        raise UpgradeError("upgrade_revision_invalid")
    phase = UpgradePhase.PREFLIGHT
    recorded = {}
    receipts = {}
    for evidence in state.evidence:
        if not isinstance(evidence, UpgradeEvidence) or not _allowed_v2(phase, evidence.phase):
            raise UpgradeError("upgrade_transition_invalid")
        _validate_v2_receipt(state.context, evidence, recorded, receipts, phase)
        for artifact in evidence.artifacts:
            previous = recorded.get(artifact.role)
            if previous is not None and previous != artifact:
                if not (artifact.role == "candidate" and evidence.phase is UpgradePhase.MIGRATED
                        and (previous.artifact_id, previous.device_id, previous.file_id) ==
                        (artifact.artifact_id, artifact.device_id, artifact.file_id)):
                    raise UpgradeError("upgrade_artifact_changed")
            recorded[artifact.role] = artifact
        receipts[evidence.phase] = evidence
        phase = evidence.phase
    if not isinstance(state.phase, UpgradePhase) or state.phase is not phase:
        raise UpgradeError("upgrade_phase_invalid")


def _validate_v2_receipt(context, evidence, recorded, receipts, previous_phase):
    if evidence.context != context:
        raise UpgradeError("upgrade_evidence_context_mismatch")
    phase = evidence.phase
    roles = {a.role: a for a in evidence.artifacts}
    expected_fields = {
        UpgradePhase.ACTIVATION_INTENT: "exchange_intent",
        UpgradePhase.TARGET_INSTALLED: "exchange_result",
        UpgradePhase.RESTART_CONFIRMED: "restart",
        UpgradePhase.RUNTIME_VERIFIED: "inspection",
        UpgradePhase.WRITES_ENABLED: "inspection",
        UpgradePhase.COMPLETED: "inspection",
        UpgradePhase.ROLLBACK_INTENT: "exchange_intent",
        UpgradePhase.ROLLBACK_INSTALLED: "exchange_result",
    }
    types = {"exchange_intent": UpgradeExchangeIntent, "exchange_result": UpgradeExchangeResult,
             "restart": UpgradeRestartReceipt, "inspection": UpgradeTargetInspection}
    for field, kind in types.items():
        value = getattr(evidence, field)
        if expected_fields.get(phase) == field:
            if not isinstance(value, kind):
                raise UpgradeError("upgrade_required_receipt_missing")
            if value.context != context:
                raise UpgradeError("upgrade_evidence_context_mismatch")
        elif value is not None:
            raise UpgradeError("upgrade_unexpected_receipt")
    required_roles = {
        UpgradePhase.EXCLUSIVE: set(),
        UpgradePhase.SOURCE_VERIFIED: {"source"},
        UpgradePhase.BACKUP_VERIFIED: {"backup"},
        UpgradePhase.STAGED: {"candidate"},
        UpgradePhase.MIGRATED: {"candidate"},
        UpgradePhase.TARGET_VERIFIED: {"candidate"},
        UpgradePhase.ACTIVATION_PREPARED: {"source", "backup", "candidate", "rollback"},
        UpgradePhase.ACTIVATION_INTENT: set(),
        UpgradePhase.TARGET_INSTALLED: {"live"},
        UpgradePhase.RESTART_CONFIRMED: set(),
        UpgradePhase.RUNTIME_VERIFIED: {"live"},
        UpgradePhase.WRITES_ENABLED: set(),
        UpgradePhase.COMPLETED: set(),
        UpgradePhase.ROLLBACK_INTENT: set(),
        UpgradePhase.ROLLBACK_INSTALLED: {"rollback_live"},
        UpgradePhase.ROLLED_BACK: {"rollback_live"},
        UpgradePhase.ABORTED: set(),
        UpgradePhase.RECOVERY_REQUIRED: set(),
    }[phase]
    if set(roles) != required_roles:
        raise UpgradeError("upgrade_required_artifact_missing")
    for artifact in evidence.artifacts:
        schema = context.source if artifact.role in {"source", "backup", "rollback", "rollback_live"} else context.target
        if phase is UpgradePhase.STAGED:
            schema = context.source
        if artifact.schema != schema:
            raise UpgradeError("upgrade_artifact_schema_mismatch")
    if phase is UpgradePhase.ACTIVATION_PREPARED:
        for role in ("source", "backup", "candidate"):
            if roles[role] != recorded.get(role):
                raise UpgradeError("upgrade_artifact_changed")
        source, rollback = roles["source"], roles["rollback"]
        if (rollback.sha256 != source.sha256 or rollback.size_bytes != source.size_bytes
                or rollback.artifact_id == source.artifact_id
                or rollback.device_id != source.device_id
                or (rollback.device_id, rollback.file_id) in {
                    (source.device_id, source.file_id),
                    (roles["candidate"].device_id, roles["candidate"].file_id),
                    (roles["backup"].device_id, roles["backup"].file_id)}):
            raise UpgradeError("upgrade_rollback_identity_invalid")
    if phase in {UpgradePhase.ACTIVATION_INTENT, UpgradePhase.ROLLBACK_INTENT}:
        intent = evidence.exchange_intent
        activate = phase is UpgradePhase.ACTIVATION_INTENT
        expected = recorded["source"] if activate or previous_phase is UpgradePhase.ACTIVATION_INTENT else recorded["live"]
        replacement = recorded["candidate" if activate else "rollback"]
        if (intent.direction != ("activate" if activate else "rollback")
                or intent.expected_live != expected or intent.replacement != replacement
                or expected.device_id != replacement.device_id):
            raise UpgradeError("upgrade_exchange_intent_mismatch")
        if not activate and intent.intent_id == receipts[UpgradePhase.ACTIVATION_INTENT].exchange_intent.intent_id:
            raise UpgradeError("upgrade_exchange_intent_mismatch")
    if phase in {UpgradePhase.TARGET_INSTALLED, UpgradePhase.ROLLBACK_INSTALLED}:
        activate = phase is UpgradePhase.TARGET_INSTALLED
        intent_phase = UpgradePhase.ACTIVATION_INTENT if activate else UpgradePhase.ROLLBACK_INTENT
        intent = receipts[intent_phase].exchange_intent
        role = "live" if activate else "rollback_live"
        installed = replace(intent.replacement, role=role)
        if (evidence.exchange_result.intent_id != intent.intent_id
                or evidence.exchange_result.installed != installed or roles[role] != installed):
            raise UpgradeError("upgrade_exchange_result_mismatch")
    if phase is UpgradePhase.RESTART_CONFIRMED and evidence.restart.installed != recorded["live"]:
        raise UpgradeError("upgrade_restart_target_mismatch")
    if phase is UpgradePhase.RUNTIME_VERIFIED:
        if (evidence.inspection.target != recorded["live"] or roles["live"] != recorded["live"]
                or evidence.inspection.restart_id != receipts[UpgradePhase.RESTART_CONFIRMED].restart.restart_id):
            raise UpgradeError("upgrade_runtime_target_mismatch")
    if phase in {UpgradePhase.WRITES_ENABLED, UpgradePhase.COMPLETED}:
        if evidence.inspection != receipts[UpgradePhase.RUNTIME_VERIFIED].inspection:
            raise UpgradeError("upgrade_write_boundary_evidence_mismatch")
    if phase is UpgradePhase.ROLLED_BACK and roles["rollback_live"] != recorded["rollback_live"]:
        raise UpgradeError("upgrade_rollback_result_mismatch")


def source_rollback_forbidden(state: UpgradeState) -> bool:
    """Conservative pure prohibition, never authentication or execution authority.

    RECOVERY_REQUIRED retains the fence in its history. A loaded, authenticated
    journal/anchor and independent verification are still caller obligations.
    """
    try:
        validate_upgrade_structure(state)
    except (ValueError, TypeError, AttributeError):
        return True
    return state.contract_version != 2 or any(
        e.phase is UpgradePhase.WRITES_ENABLED for e in state.evidence)


def classify_upgrade(state: UpgradeState | None, *, expected_context: UpgradeContext | None,
                     observed: tuple[UpgradeArtifact, ...], registry: DatabaseSchemaRegistry,
                     inventory_complete: bool, journal_authenticated: bool,
                     target_inspection: UpgradeTargetInspection | None = None) -> UpgradeRecoveryDecision:
    """Pure classification; never a startup, writer, rollback or activation permit."""
    blocked = UpgradeRecoveryDecision(UpgradeRecoveryStatus.RECOVERY_REQUIRED, "upgrade_evidence_required")
    if (inventory_complete is not True or not isinstance(observed, tuple)
            or any(not isinstance(a, UpgradeArtifact) for a in observed)):
        return blocked
    if state is None:
        return UpgradeRecoveryDecision(UpgradeRecoveryStatus.NO_OPERATION, "upgrade_absent") if not observed and target_inspection is None else blocked
    if journal_authenticated is not True or not isinstance(state, UpgradeState) or state.context != expected_context:
        return blocked
    try:
        validate_upgrade_state(state, registry)
    except (ValueError, TypeError, AttributeError):
        return blocked
    if state.contract_version == 1:
        if target_inspection is not None:
            return blocked
        return _classify_legacy_upgrade(state, expected_context=expected_context, observed=observed,
            registry=registry, inventory_complete=True, journal_authenticated=True)
    if len({a.role for a in observed}) != len(observed):
        return blocked
    actual = {a.role: a for a in observed}
    recorded = {a.role: a for e in state.evidence for a in e.artifacts}
    fenced = source_rollback_forbidden(state)
    for role, artifact in actual.items():
        if not (fenced and role == "live") and recorded.get(role) != artifact:
            return blocked
    if state.phase is UpgradePhase.RECOVERY_REQUIRED:
        return blocked
    if fenced:
        if (not isinstance(target_inspection, UpgradeTargetInspection)
                or target_inspection.context != state.context
                or target_inspection.target != actual.get("live")
                or target_inspection.target.artifact_id != recorded["candidate"].artifact_id):
            return blocked
        status = (UpgradeRecoveryStatus.COMPLETED if state.phase is UpgradePhase.COMPLETED
                  else UpgradeRecoveryStatus.WRITES_ENABLED)
    else:
        if target_inspection is not None:
            return blocked
        if state.phase in {UpgradePhase.ROLLBACK_INSTALLED, UpgradePhase.ROLLED_BACK}:
            required = {"backup", "rollback_live"}
        elif "live" in recorded:
            required = {"backup", "rollback", "live"}
        else:
            required = {"source"} | ({"backup"} if "backup" in recorded else set())
            if "candidate" in recorded:
                required.add("candidate")
            if "rollback" in recorded:
                required.add("rollback")
        if not required.issubset(actual):
            return blocked
        if state.phase in {UpgradePhase.ACTIVATION_INTENT, UpgradePhase.ROLLBACK_INTENT}:
            return blocked  # uncertain publication outcome remains recovery-required
        status = {
            UpgradePhase.ABORTED: UpgradeRecoveryStatus.ABORTED,
            UpgradePhase.ROLLED_BACK: UpgradeRecoveryStatus.ROLLED_BACK,
            UpgradePhase.TARGET_INSTALLED: UpgradeRecoveryStatus.INSTALLED,
            UpgradePhase.RESTART_CONFIRMED: UpgradeRecoveryStatus.RESTART_VERIFIED,
            UpgradePhase.RUNTIME_VERIFIED: UpgradeRecoveryStatus.RESTART_VERIFIED,
        }.get(state.phase, UpgradeRecoveryStatus.VERIFY_CANDIDATE if "candidate" in recorded else UpgradeRecoveryStatus.NOT_ACTIVATED)
        if state.phase is UpgradePhase.ROLLBACK_INSTALLED:
            return blocked  # explicit final rollback receipt still required
    return UpgradeRecoveryDecision(status, "upgrade_classified_without_admission")
