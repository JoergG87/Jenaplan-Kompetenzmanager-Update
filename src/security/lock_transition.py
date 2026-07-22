"""Authenticated, append-only lock-transition domain for migration recovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import hmac
import json
import re

from .data_keys import LoadedDataMasterKey
from .database_keys import DerivedDomainKey, derive_domain_separated_key
from .domain import SecurityStoreError, validate_uuid4


LOCK_TRANSITION_VERSION = 1
LOCK_TRANSITION_AUTH_PURPOSE = (
    "jenaplan-kompetenzmanager/migration-lock-transition-auth/v1"
)
LOCK_TRANSITION_AUTH_ALGORITHM = "hmac-sha256"
EMPTY_LOCK_TRANSITION_SHA256 = hashlib.sha256(b"").hexdigest()
EMPTY_LOCK_OWNER_SHA256 = hashlib.sha256(b"").hexdigest()
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_UTC = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")


class LockTransitionError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class LockTransitionType(StrEnum):
    ACQUIRED = "acquired"
    RELEASED = "released"
    STALE_DETECTED = "stale_detected"
    TAKEOVER_PREPARED = "takeover_prepared"
    TAKEOVER_COMMITTED = "takeover_committed"
    BLOCKED = "blocked"


_ALLOWED: dict[LockTransitionType, frozenset[LockTransitionType]] = {
    LockTransitionType.ACQUIRED: frozenset(
        {
            LockTransitionType.RELEASED,
            LockTransitionType.STALE_DETECTED,
            LockTransitionType.BLOCKED,
        }
    ),
    LockTransitionType.RELEASED: frozenset(
        {LockTransitionType.ACQUIRED, LockTransitionType.BLOCKED}
    ),
    LockTransitionType.STALE_DETECTED: frozenset(
        {LockTransitionType.TAKEOVER_PREPARED, LockTransitionType.BLOCKED}
    ),
    LockTransitionType.TAKEOVER_PREPARED: frozenset(
        {LockTransitionType.TAKEOVER_COMMITTED, LockTransitionType.BLOCKED}
    ),
    LockTransitionType.TAKEOVER_COMMITTED: frozenset(
        {
            LockTransitionType.RELEASED,
            LockTransitionType.STALE_DETECTED,
            LockTransitionType.BLOCKED,
        }
    ),
    LockTransitionType.BLOCKED: frozenset(),
}


@dataclass(frozen=True)
class AuthenticatedLockEvidence:
    installation_id: str
    database_context_id: str
    migration_id: str
    migration_context_digest: str
    replay_anchor_revision: int
    replay_anchor_digest: str
    journal_digest: str
    artifact_digest: str
    anchor_authenticated: bool = field(repr=False)
    journal_authenticated: bool = field(repr=False)
    artifacts_authenticated: bool = field(repr=False)


@dataclass(frozen=True)
class AuthenticatedLockTransition:
    transition_version: int
    sequence: int
    transition: LockTransitionType
    previous_digest: str
    installation_id: str
    database_context_id: str
    migration_id: str
    migration_context_digest: str
    replay_anchor_revision: int
    replay_anchor_digest: str
    journal_digest: str
    artifact_digest: str
    owner_before_digest: str
    owner_after_digest: str
    occurred_at: str
    auth_algorithm: str
    auth_kdf_version: int
    auth_tag: str = field(repr=False)

    def payload(self) -> dict[str, object]:
        return {
            "artifact_digest": self.artifact_digest,
            "auth_algorithm": self.auth_algorithm,
            "auth_kdf_version": self.auth_kdf_version,
            "database_context_id": self.database_context_id,
            "installation_id": self.installation_id,
            "journal_digest": self.journal_digest,
            "migration_context_digest": self.migration_context_digest,
            "migration_id": self.migration_id,
            "occurred_at": self.occurred_at,
            "owner_after_digest": self.owner_after_digest,
            "owner_before_digest": self.owner_before_digest,
            "previous_digest": self.previous_digest,
            "replay_anchor_digest": self.replay_anchor_digest,
            "replay_anchor_revision": self.replay_anchor_revision,
            "sequence": self.sequence,
            "transition": self.transition.value,
            "transition_version": self.transition_version,
        }

    def to_bytes(self) -> bytes:
        return _canonical({**self.payload(), "auth_tag": self.auth_tag})

    def digest(self) -> str:
        return hashlib.sha256(self.to_bytes()).hexdigest()

    @classmethod
    def from_bytes(cls, value: bytes) -> "AuthenticatedLockTransition":
        try:
            payload = json.loads(value.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise LockTransitionError("lock_transition_format_invalid") from None
        required = {
            "artifact_digest", "auth_algorithm", "auth_kdf_version",
            "auth_tag", "database_context_id", "installation_id",
            "journal_digest", "migration_context_digest", "migration_id",
            "occurred_at", "owner_after_digest", "owner_before_digest",
            "previous_digest", "replay_anchor_digest",
            "replay_anchor_revision", "sequence", "transition",
            "transition_version",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise LockTransitionError("lock_transition_fields_invalid")
        try:
            entry = cls(
                transition_version=payload["transition_version"],
                sequence=payload["sequence"],
                transition=LockTransitionType(payload["transition"]),
                previous_digest=payload["previous_digest"],
                installation_id=payload["installation_id"],
                database_context_id=payload["database_context_id"],
                migration_id=payload["migration_id"],
                migration_context_digest=payload["migration_context_digest"],
                replay_anchor_revision=payload["replay_anchor_revision"],
                replay_anchor_digest=payload["replay_anchor_digest"],
                journal_digest=payload["journal_digest"],
                artifact_digest=payload["artifact_digest"],
                owner_before_digest=payload["owner_before_digest"],
                owner_after_digest=payload["owner_after_digest"],
                occurred_at=payload["occurred_at"],
                auth_algorithm=payload["auth_algorithm"],
                auth_kdf_version=payload["auth_kdf_version"],
                auth_tag=payload["auth_tag"],
            )
        except (TypeError, ValueError):
            raise LockTransitionError("lock_transition_fields_invalid") from None
        if entry.to_bytes() != value:
            raise LockTransitionError("lock_transition_not_canonical")
        _validate_entry_shape(entry)
        return entry


@dataclass(frozen=True)
class AuthenticatedLockTransitionChain:
    entries: tuple[AuthenticatedLockTransition, ...] = ()

    @property
    def sequence(self) -> int:
        return 0 if not self.entries else self.entries[-1].sequence

    @property
    def head_digest(self) -> str:
        return EMPTY_LOCK_TRANSITION_SHA256 if not self.entries else self.entries[-1].digest()


def derive_lock_transition_auth_key(
    dmk: LoadedDataMasterKey,
    *,
    installation_id: str,
    database_context_id: str,
    migration_id: str,
) -> DerivedDomainKey:
    for value in (installation_id, database_context_id, migration_id):
        _uuid(value)
    return derive_domain_separated_key(
        dmk,
        purpose=LOCK_TRANSITION_AUTH_PURPOSE,
        derivation_version=1,
        context={
            "installation_id": installation_id,
            "database_context_id": database_context_id,
            "migration_id": migration_id,
            "dmk_generation": dmk.generation,
        },
    )


def append_lock_transition(
    chain: AuthenticatedLockTransitionChain,
    transition: LockTransitionType,
    *,
    installation_id: str,
    database_context_id: str,
    migration_id: str,
    migration_context_digest: str,
    evidence: AuthenticatedLockEvidence,
    owner_before_digest: str,
    owner_after_digest: str,
    occurred_at: datetime,
    auth_key: DerivedDomainKey,
) -> AuthenticatedLockTransitionChain:
    validate_lock_transition_chain(chain, auth_key)
    _require_evidence(
        evidence,
        installation_id=installation_id,
        database_context_id=database_context_id,
        migration_id=migration_id,
        migration_context_digest=migration_context_digest,
    )
    if not isinstance(transition, LockTransitionType):
        raise LockTransitionError("lock_transition_type_invalid")
    if chain.entries:
        previous = chain.entries[-1]
        if transition not in _ALLOWED[previous.transition]:
            raise LockTransitionError("lock_transition_illegal")
        if (
            previous.installation_id,
            previous.database_context_id,
            previous.migration_id,
            previous.migration_context_digest,
        ) != (
            installation_id,
            database_context_id,
            migration_id,
            migration_context_digest,
        ):
            raise LockTransitionError("lock_transition_context_mismatch")
        if evidence.replay_anchor_revision < previous.replay_anchor_revision:
            raise LockTransitionError("lock_transition_anchor_rollback")
        _validate_evidence_progression(previous, evidence)
    elif transition is not LockTransitionType.ACQUIRED:
        raise LockTransitionError("lock_transition_genesis_invalid")
    for value in (installation_id, database_context_id, migration_id):
        _uuid(value)
    for value in (
        migration_context_digest, owner_before_digest, owner_after_digest,
        evidence.replay_anchor_digest, evidence.journal_digest,
        evidence.artifact_digest,
    ):
        _digest(value)
    timestamp = _timestamp(occurred_at)
    unsigned = AuthenticatedLockTransition(
        LOCK_TRANSITION_VERSION,
        chain.sequence + 1,
        transition,
        chain.head_digest,
        installation_id,
        database_context_id,
        migration_id,
        migration_context_digest,
        evidence.replay_anchor_revision,
        evidence.replay_anchor_digest,
        evidence.journal_digest,
        evidence.artifact_digest,
        owner_before_digest,
        owner_after_digest,
        timestamp,
        LOCK_TRANSITION_AUTH_ALGORITHM,
        1,
        "0" * 64,
    )
    tag = hmac.new(_key(auth_key), _canonical(unsigned.payload()), hashlib.sha256).hexdigest()
    entry = AuthenticatedLockTransition(**{**unsigned.__dict__, "auth_tag": tag})
    _validate_owner_transition(entry, chain.entries[-1] if chain.entries else None)
    replacement = AuthenticatedLockTransitionChain((*chain.entries, entry))
    validate_lock_transition_chain(replacement, auth_key)
    return replacement


def validate_lock_transition_chain(
    chain: AuthenticatedLockTransitionChain,
    auth_key: DerivedDomainKey,
    *,
    expected_head_digest: str | None = None,
    expected_sequence: int | None = None,
) -> None:
    if not isinstance(chain, AuthenticatedLockTransitionChain):
        raise LockTransitionError("lock_transition_chain_invalid")
    key = _key(auth_key)
    previous_digest = EMPTY_LOCK_TRANSITION_SHA256
    previous: AuthenticatedLockTransition | None = None
    for sequence, entry in enumerate(chain.entries, start=1):
        _validate_entry_shape(entry)
        if entry.sequence != sequence or entry.previous_digest != previous_digest:
            raise LockTransitionError("lock_transition_chain_broken")
        expected = hmac.new(key, _canonical(entry.payload()), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(entry.auth_tag, expected):
            raise LockTransitionError("lock_transition_auth_failed")
        if previous is None:
            if entry.transition is not LockTransitionType.ACQUIRED:
                raise LockTransitionError("lock_transition_genesis_invalid")
        else:
            if entry.transition not in _ALLOWED[previous.transition]:
                raise LockTransitionError("lock_transition_illegal")
            if (
                entry.installation_id, entry.database_context_id,
                entry.migration_id, entry.migration_context_digest,
            ) != (
                previous.installation_id, previous.database_context_id,
                previous.migration_id, previous.migration_context_digest,
            ):
                raise LockTransitionError("lock_transition_context_mismatch")
            if entry.replay_anchor_revision < previous.replay_anchor_revision:
                raise LockTransitionError("lock_transition_anchor_rollback")
            if entry.occurred_at < previous.occurred_at:
                raise LockTransitionError("lock_transition_time_rollback")
            _validate_evidence_progression(previous, entry)
        _validate_owner_transition(entry, previous)
        previous, previous_digest = entry, entry.digest()
    if expected_head_digest is not None:
        _digest(expected_head_digest)
        if not hmac.compare_digest(chain.head_digest, expected_head_digest):
            raise LockTransitionError("lock_transition_replay_detected")
    if expected_sequence is not None and chain.sequence != expected_sequence:
        raise LockTransitionError("lock_transition_replay_detected")


def _require_evidence(
    evidence: AuthenticatedLockEvidence,
    *,
    installation_id: str,
    database_context_id: str,
    migration_id: str,
    migration_context_digest: str,
) -> None:
    if not isinstance(evidence, AuthenticatedLockEvidence):
        raise LockTransitionError("lock_transition_evidence_invalid")
    if any(
        value is not True
        for value in (
            evidence.anchor_authenticated,
            evidence.journal_authenticated,
            evidence.artifacts_authenticated,
        )
    ):
        raise LockTransitionError("lock_transition_evidence_unauthenticated")
    if (
        evidence.installation_id,
        evidence.database_context_id,
        evidence.migration_id,
        evidence.migration_context_digest,
    ) != (
        installation_id,
        database_context_id,
        migration_id,
        migration_context_digest,
    ):
        raise LockTransitionError("lock_transition_evidence_context_mismatch")
    if type(evidence.replay_anchor_revision) is not int or evidence.replay_anchor_revision < 1:
        raise LockTransitionError("lock_transition_anchor_revision_invalid")
    for value in (
        evidence.replay_anchor_digest,
        evidence.journal_digest,
        evidence.artifact_digest,
    ):
        _digest(value)


def _validate_evidence_progression(
    previous: AuthenticatedLockTransition,
    current: AuthenticatedLockTransition | AuthenticatedLockEvidence,
) -> None:
    if current.replay_anchor_revision < previous.replay_anchor_revision:
        raise LockTransitionError("lock_transition_anchor_rollback")
    previous_evidence = (
        previous.replay_anchor_digest,
        previous.journal_digest,
        previous.artifact_digest,
    )
    current_evidence = (
        current.replay_anchor_digest,
        current.journal_digest,
        current.artifact_digest,
    )
    if current.replay_anchor_revision == previous.replay_anchor_revision:
        if current_evidence != previous_evidence:
            raise LockTransitionError("lock_transition_evidence_revision_mismatch")
    elif current.replay_anchor_digest == previous.replay_anchor_digest:
        raise LockTransitionError("lock_transition_anchor_revision_mismatch")


def _validate_owner_transition(
    entry: AuthenticatedLockTransition,
    previous: AuthenticatedLockTransition | None,
) -> None:
    expected_before = (
        EMPTY_LOCK_OWNER_SHA256 if previous is None else previous.owner_after_digest
    )
    if not hmac.compare_digest(entry.owner_before_digest, expected_before):
        raise LockTransitionError("lock_transition_owner_continuity_invalid")

    owner_before_empty = entry.owner_before_digest == EMPTY_LOCK_OWNER_SHA256
    owner_after_empty = entry.owner_after_digest == EMPTY_LOCK_OWNER_SHA256
    if entry.transition is LockTransitionType.ACQUIRED:
        valid = owner_before_empty and not owner_after_empty
    elif entry.transition is LockTransitionType.RELEASED:
        valid = not owner_before_empty and owner_after_empty
    elif entry.transition is LockTransitionType.STALE_DETECTED:
        valid = (
            not owner_before_empty
            and hmac.compare_digest(
                entry.owner_before_digest, entry.owner_after_digest
            )
        )
    elif entry.transition is LockTransitionType.TAKEOVER_PREPARED:
        valid = (
            not owner_before_empty
            and not owner_after_empty
            and not hmac.compare_digest(
                entry.owner_before_digest, entry.owner_after_digest
            )
        )
    elif entry.transition is LockTransitionType.TAKEOVER_COMMITTED:
        valid = (
            not owner_before_empty
            and hmac.compare_digest(
                entry.owner_before_digest, entry.owner_after_digest
            )
        )
    else:
        valid = hmac.compare_digest(
            entry.owner_before_digest, entry.owner_after_digest
        )
    if not valid:
        raise LockTransitionError("lock_transition_owner_state_invalid")


def _validate_entry_shape(entry: AuthenticatedLockTransition) -> None:
    if entry.transition_version != LOCK_TRANSITION_VERSION:
        raise LockTransitionError("lock_transition_version_unsupported")
    if type(entry.sequence) is not int or entry.sequence < 1:
        raise LockTransitionError("lock_transition_sequence_invalid")
    if not isinstance(entry.transition, LockTransitionType):
        raise LockTransitionError("lock_transition_type_invalid")
    for value in (entry.installation_id, entry.database_context_id, entry.migration_id):
        _uuid(value)
    for value in (
        entry.previous_digest, entry.migration_context_digest,
        entry.replay_anchor_digest, entry.journal_digest, entry.artifact_digest,
        entry.owner_before_digest, entry.owner_after_digest, entry.auth_tag,
    ):
        _digest(value)
    if type(entry.replay_anchor_revision) is not int or entry.replay_anchor_revision < 1:
        raise LockTransitionError("lock_transition_anchor_revision_invalid")
    if entry.auth_algorithm != LOCK_TRANSITION_AUTH_ALGORITHM or entry.auth_kdf_version != 1:
        raise LockTransitionError("lock_transition_auth_contract_invalid")
    if not isinstance(entry.occurred_at, str) or not _UTC.fullmatch(entry.occurred_at):
        raise LockTransitionError("lock_transition_time_invalid")


def _key(auth_key: DerivedDomainKey) -> bytes:
    if (
        not isinstance(auth_key, DerivedDomainKey)
        or auth_key.purpose != LOCK_TRANSITION_AUTH_PURPOSE
        or auth_key.derivation_version != 1
        or len(auth_key.key_material) != 32
    ):
        raise LockTransitionError("lock_transition_auth_key_invalid")
    return auth_key.key_material


def _uuid(value: object) -> None:
    try:
        validate_uuid4(value)  # type: ignore[arg-type]
    except (SecurityStoreError, TypeError):
        raise LockTransitionError("lock_transition_binding_invalid") from None


def _digest(value: object) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise LockTransitionError("lock_transition_digest_invalid")


def _timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise LockTransitionError("lock_transition_time_invalid")
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
