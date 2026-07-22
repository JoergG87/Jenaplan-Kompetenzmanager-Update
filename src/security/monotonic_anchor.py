"""Qt-free monotonic replay-anchor domain and platform-port contract."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import re
from typing import Protocol, runtime_checkable

from .domain import SecurityStoreError, validate_uuid4


SECURITY_ANCHOR_VERSION = 1
SECURITY_ANCHOR_MAX_BYTES = 8 * 1024
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_SAFE_CODE = re.compile(r"\A[a-z][a-z0-9_]{0,79}\Z")


class SecurityAnchorStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class SecurityAnchorError(RuntimeError):
    """Sanitized fail-closed error without paths, payloads, or secrets."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, repr=False)
class SecurityAnchorState:
    anchor_version: int
    installation_id: str
    database_context_id: str
    dmk_key_id: str
    dmk_key_generation: int
    anchor_revision: int
    registry_high_water_mark: int
    registry_sha256: str
    journal_revision: int
    journal_sha256: str
    migration_generation: int
    status: SecurityAnchorStatus
    block_reason: str | None = None
    pending: SecurityAnchorState | None = None

    def __post_init__(self) -> None:
        _validate_state(self)

    def __repr__(self) -> str:
        pending_revision = None if self.pending is None else self.pending.anchor_revision
        return (
            "SecurityAnchorState("
            f"anchor_version={self.anchor_version}, "
            f"anchor_revision={self.anchor_revision}, "
            f"registry_high_water_mark={self.registry_high_water_mark}, "
            f"journal_revision={self.journal_revision}, "
            f"migration_generation={self.migration_generation}, "
            f"status={self.status.value!r}, "
            f"pending_revision={pending_revision!r})"
        )

    def committed_state(self) -> SecurityAnchorState:
        """Return the committed state without its optional prepared successor."""

        return replace(self, pending=None)

    def to_bytes(self) -> bytes:
        return _encode_state(self)

    @classmethod
    def from_bytes(cls, value: bytes) -> SecurityAnchorState:
        if not isinstance(value, bytes) or not value or len(value) > SECURITY_ANCHOR_MAX_BYTES:
            raise SecurityAnchorError("security_anchor_size_invalid")
        try:
            payload = json.loads(value.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SecurityAnchorError("security_anchor_format_invalid") from None
        state = _state_from_payload(payload, allow_pending=True)
        if _encode_state(state) != value:
            raise SecurityAnchorError("security_anchor_not_canonical")
        return state


@runtime_checkable
class MonotonicSecurityAnchorStore(Protocol):
    @property
    def supported(self) -> bool: ...

    def initialize(
        self,
        state: SecurityAnchorState,
        *,
        security_artifacts_exist: bool,
    ) -> SecurityAnchorState: ...

    def read(self) -> SecurityAnchorState: ...
    def compare(self, observed: SecurityAnchorState) -> bool: ...
    def verify(self, observed: SecurityAnchorState) -> SecurityAnchorState: ...
    def prepare(
        self,
        expected: SecurityAnchorState,
        planned: SecurityAnchorState,
    ) -> SecurityAnchorState: ...
    def advance(
        self,
        expected: SecurityAnchorState,
        observed: SecurityAnchorState,
    ) -> SecurityAnchorState: ...
    def abort_pending(
        self,
        expected: SecurityAnchorState,
        observed_committed: SecurityAnchorState,
    ) -> SecurityAnchorState: ...
    def block(
        self,
        expected: SecurityAnchorState,
        reason: str,
    ) -> SecurityAnchorState: ...
    def mark_failed(
        self,
        expected: SecurityAnchorState,
        reason: str,
    ) -> SecurityAnchorState: ...


def _validate_state(state: SecurityAnchorState, *, allow_pending: bool = True) -> None:
    if not isinstance(state, SecurityAnchorState):
        raise SecurityAnchorError("security_anchor_state_invalid")
    if type(state.anchor_version) is not int or state.anchor_version != SECURITY_ANCHOR_VERSION:
        raise SecurityAnchorError("security_anchor_version_unsupported")
    for identifier in (
        state.installation_id,
        state.database_context_id,
        state.dmk_key_id,
    ):
        try:
            validate_uuid4(identifier)
        except SecurityStoreError:
            raise SecurityAnchorError("security_anchor_binding_invalid") from None
    _positive_int(state.dmk_key_generation, "security_anchor_dmk_generation_invalid")
    _positive_int(state.anchor_revision, "security_anchor_revision_invalid")
    _nonnegative_int(
        state.registry_high_water_mark,
        "security_anchor_registry_high_water_invalid",
    )
    _nonnegative_int(state.journal_revision, "security_anchor_journal_revision_invalid")
    _nonnegative_int(
        state.migration_generation,
        "security_anchor_migration_generation_invalid",
    )
    if not isinstance(state.registry_sha256, str) or not _SHA256.fullmatch(
        state.registry_sha256
    ):
        raise SecurityAnchorError("security_anchor_registry_digest_invalid")
    if not isinstance(state.journal_sha256, str) or not _SHA256.fullmatch(
        state.journal_sha256
    ):
        raise SecurityAnchorError("security_anchor_journal_digest_invalid")
    if not isinstance(state.status, SecurityAnchorStatus):
        raise SecurityAnchorError("security_anchor_status_invalid")
    if state.status is SecurityAnchorStatus.ACTIVE:
        if state.block_reason is not None:
            raise SecurityAnchorError("security_anchor_block_reason_invalid")
    elif not _safe_reason(state.block_reason):
        raise SecurityAnchorError("security_anchor_block_reason_invalid")
    if state.pending is not None:
        if not allow_pending:
            raise SecurityAnchorError("security_anchor_pending_nested")
        _validate_state(state.pending, allow_pending=False)
        if (
            state.pending.pending is not None
            or state.pending.status is not SecurityAnchorStatus.ACTIVE
            or state.pending.block_reason is not None
        ):
            raise SecurityAnchorError("security_anchor_pending_invalid")
        committed_for_transition = replace(
            state,
            status=SecurityAnchorStatus.ACTIVE,
            block_reason=None,
            pending=None,
        )
        _validate_advance(committed_for_transition, state.pending)


def _validate_advance(
    committed: SecurityAnchorState,
    planned: SecurityAnchorState,
) -> None:
    _validate_state(committed, allow_pending=False)
    _validate_state(planned, allow_pending=False)
    if committed.status is not SecurityAnchorStatus.ACTIVE:
        raise SecurityAnchorError("security_anchor_blocked")
    if planned.status is not SecurityAnchorStatus.ACTIVE or planned.block_reason is not None:
        raise SecurityAnchorError("security_anchor_advance_invalid")
    if _binding(committed) != _binding(planned):
        raise SecurityAnchorError("security_anchor_advance_invalid")
    if planned.anchor_revision != committed.anchor_revision + 1:
        raise SecurityAnchorError("security_anchor_advance_invalid")
    for old, new in (
        (committed.registry_high_water_mark, planned.registry_high_water_mark),
        (committed.journal_revision, planned.journal_revision),
        (committed.migration_generation, planned.migration_generation),
    ):
        if new < old or new > old + 1:
            raise SecurityAnchorError("security_anchor_advance_invalid")
    journal_changed = planned.journal_sha256 != committed.journal_sha256
    if journal_changed != (
        planned.journal_revision == committed.journal_revision + 1
    ):
        raise SecurityAnchorError("security_anchor_advance_invalid")
    if (
        planned.registry_high_water_mark == committed.registry_high_water_mark + 1
        and planned.registry_sha256 == committed.registry_sha256
    ):
        raise SecurityAnchorError("security_anchor_advance_invalid")
    if _artifact_snapshot(committed) == _artifact_snapshot(planned):
        raise SecurityAnchorError("security_anchor_advance_invalid")


def _matches_observation(
    stored: SecurityAnchorState,
    observed: SecurityAnchorState,
) -> bool:
    if stored.status is SecurityAnchorStatus.BLOCKED:
        return False
    try:
        _validate_state(observed, allow_pending=False)
    except SecurityAnchorError:
        return False
    if observed.status is not SecurityAnchorStatus.ACTIVE:
        return False
    if _same_bound_snapshot(stored.committed_state(), observed):
        return True
    return stored.pending is not None and _same_bound_snapshot(stored.pending, observed)


def _same_bound_snapshot(first: SecurityAnchorState, second: SecurityAnchorState) -> bool:
    return (
        _binding(first) == _binding(second)
        and first.anchor_revision == second.anchor_revision
        and _artifact_snapshot(first) == _artifact_snapshot(second)
    )


def _blocked_state(state: SecurityAnchorState, reason: str) -> SecurityAnchorState:
    if not _safe_reason(reason):
        raise SecurityAnchorError("security_anchor_block_reason_invalid")
    if state.status is SecurityAnchorStatus.BLOCKED:
        if state.block_reason == reason:
            return state
        raise SecurityAnchorError("security_anchor_blocked")
    return replace(state, status=SecurityAnchorStatus.BLOCKED, block_reason=reason)


def _binding(state: SecurityAnchorState) -> tuple[object, ...]:
    return (
        state.anchor_version,
        state.installation_id,
        state.database_context_id,
        state.dmk_key_id,
        state.dmk_key_generation,
    )


def _artifact_snapshot(state: SecurityAnchorState) -> tuple[object, ...]:
    return (
        state.registry_high_water_mark,
        state.registry_sha256,
        state.journal_revision,
        state.journal_sha256,
        state.migration_generation,
    )


def _state_payload(state: SecurityAnchorState) -> dict[str, object]:
    return {
        "anchor_revision": state.anchor_revision,
        "anchor_version": state.anchor_version,
        "block_reason": state.block_reason,
        "database_context_id": state.database_context_id,
        "dmk_key_generation": state.dmk_key_generation,
        "dmk_key_id": state.dmk_key_id,
        "installation_id": state.installation_id,
        "journal_revision": state.journal_revision,
        "journal_sha256": state.journal_sha256,
        "migration_generation": state.migration_generation,
        "pending": None if state.pending is None else _state_payload(state.pending),
        "registry_high_water_mark": state.registry_high_water_mark,
        "registry_sha256": state.registry_sha256,
        "status": state.status.value,
    }


def _state_from_payload(payload: object, *, allow_pending: bool) -> SecurityAnchorState:
    required = {
        "anchor_revision",
        "anchor_version",
        "block_reason",
        "database_context_id",
        "dmk_key_generation",
        "dmk_key_id",
        "installation_id",
        "journal_revision",
        "journal_sha256",
        "migration_generation",
        "pending",
        "registry_high_water_mark",
        "registry_sha256",
        "status",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise SecurityAnchorError("security_anchor_fields_invalid")
    try:
        pending_payload = payload["pending"]
        if pending_payload is not None and not allow_pending:
            raise SecurityAnchorError("security_anchor_pending_nested")
        pending = (
            None
            if pending_payload is None
            else _state_from_payload(pending_payload, allow_pending=False)
        )
        return SecurityAnchorState(
            anchor_version=payload["anchor_version"],
            installation_id=payload["installation_id"],
            database_context_id=payload["database_context_id"],
            dmk_key_id=payload["dmk_key_id"],
            dmk_key_generation=payload["dmk_key_generation"],
            anchor_revision=payload["anchor_revision"],
            registry_high_water_mark=payload["registry_high_water_mark"],
            registry_sha256=payload["registry_sha256"],
            journal_revision=payload["journal_revision"],
            journal_sha256=payload["journal_sha256"],
            migration_generation=payload["migration_generation"],
            status=SecurityAnchorStatus(payload["status"]),
            block_reason=payload["block_reason"],
            pending=pending,
        )
    except SecurityAnchorError:
        raise
    except (KeyError, TypeError, ValueError):
        raise SecurityAnchorError("security_anchor_fields_invalid") from None


def _encode_state(state: SecurityAnchorState) -> bytes:
    _validate_state(state)
    try:
        encoded = json.dumps(
            _state_payload(state),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError):
        raise SecurityAnchorError("security_anchor_fields_invalid") from None
    if len(encoded) > SECURITY_ANCHOR_MAX_BYTES:
        raise SecurityAnchorError("security_anchor_size_invalid")
    return encoded


def _positive_int(value: object, code: str) -> None:
    if type(value) is not int or value < 1:
        raise SecurityAnchorError(code)


def _nonnegative_int(value: object, code: str) -> None:
    if type(value) is not int or value < 0:
        raise SecurityAnchorError(code)


def _safe_reason(value: object) -> bool:
    return isinstance(value, str) and _SAFE_CODE.fullmatch(value) is not None
