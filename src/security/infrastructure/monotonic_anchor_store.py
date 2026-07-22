"""In-memory, unsupported, and isolated macOS monotonic-anchor stores."""

from __future__ import annotations

import ctypes
import hashlib
import threading
from typing import Callable

from ..domain import SecurityStoreError, validate_uuid4
from ..monotonic_anchor import (
    SECURITY_ANCHOR_MAX_BYTES,
    SecurityAnchorError,
    SecurityAnchorState,
    SecurityAnchorStatus,
    _blocked_state,
    _matches_observation,
    _validate_advance,
    _validate_state,
)


MACOS_MONOTONIC_SECURITY_ANCHOR_SERVICE = (
    "de.jenaplan.kompetenzmanager.monotonic-security-anchor"
)
_ERR_SEC_SUCCESS = 0
_ERR_SEC_DUPLICATE_ITEM = -25299
_ERR_SEC_ITEM_NOT_FOUND = -25300
_ERR_SEC_AUTH_FAILED = -25293
_ERR_SEC_INTERACTION_NOT_ALLOWED = -25308
_ERR_SEC_USER_CANCELED = -128
_ERR_SEC_DECODE = -26275


class InMemoryMonotonicSecurityAnchorStore:
    """Deterministic thread-safe fake with atomic expected-state transitions."""

    def __init__(self, initial_state: SecurityAnchorState | None = None) -> None:
        if initial_state is not None:
            _validate_state(initial_state)
        self._state = initial_state
        self._lock = threading.RLock()

    @property
    def supported(self) -> bool:
        return True

    def initialize(
        self,
        state: SecurityAnchorState,
        *,
        security_artifacts_exist: bool,
    ) -> SecurityAnchorState:
        _validate_initial(state)
        with self._lock:
            if self._state is not None:
                if self._state == state:
                    return self._state
                raise SecurityAnchorError("security_anchor_already_exists")
            if security_artifacts_exist:
                raise SecurityAnchorError("security_anchor_missing_with_artifacts")
            self._state = state
            return state

    def read(self) -> SecurityAnchorState:
        with self._lock:
            if self._state is None:
                raise SecurityAnchorError("security_anchor_missing")
            return self._state

    def compare(self, observed: SecurityAnchorState) -> bool:
        with self._lock:
            return self._state is not None and _matches_observation(
                self._state, observed
            )

    def verify(self, observed: SecurityAnchorState) -> SecurityAnchorState:
        with self._lock:
            state = self.read()
            if state.status is SecurityAnchorStatus.BLOCKED:
                raise SecurityAnchorError("security_anchor_blocked")
            if _matches_observation(state, observed):
                return state
            self._state = _blocked_state(
                state, "security_anchor_observation_ambiguous"
            )
            raise SecurityAnchorError("security_anchor_observation_ambiguous")

    def prepare(
        self,
        expected: SecurityAnchorState,
        planned: SecurityAnchorState,
    ) -> SecurityAnchorState:
        with self._lock:
            current = self.read()
            if current.status is SecurityAnchorStatus.BLOCKED:
                raise SecurityAnchorError("security_anchor_blocked")
            if current.pending is not None:
                if current.committed_state() == expected and current.pending == planned:
                    return current
                raise SecurityAnchorError("security_anchor_changed")
            _require_expected(current, expected)
            try:
                _validate_advance(expected.committed_state(), planned)
            except SecurityAnchorError as error:
                self._state = _blocked_state(
                    current, "security_anchor_advance_invalid"
                )
                if error.code == "security_anchor_blocked":
                    raise
                raise SecurityAnchorError("security_anchor_advance_invalid") from None
            prepared = _prepared_state(expected, planned)
            self._state = prepared
            return prepared

    def advance(
        self,
        expected: SecurityAnchorState,
        observed: SecurityAnchorState,
    ) -> SecurityAnchorState:
        with self._lock:
            current = self.read()
            _require_expected(current, expected)
            if current.status is SecurityAnchorStatus.BLOCKED:
                raise SecurityAnchorError("security_anchor_blocked")
            if current.pending is None:
                self._state = _blocked_state(
                    current, "security_anchor_pending_missing"
                )
                raise SecurityAnchorError("security_anchor_pending_missing")
            if observed != current.pending:
                self._state = _blocked_state(
                    current, "security_anchor_pending_mismatch"
                )
                raise SecurityAnchorError("security_anchor_pending_mismatch")
            self._state = current.pending
            return self._state

    def abort_pending(
        self,
        expected: SecurityAnchorState,
        observed_committed: SecurityAnchorState,
    ) -> SecurityAnchorState:
        with self._lock:
            current = self.read()
            _require_expected(current, expected)
            if current.status is SecurityAnchorStatus.BLOCKED:
                raise SecurityAnchorError("security_anchor_blocked")
            if current.pending is None:
                self._state = _blocked_state(
                    current, "security_anchor_pending_missing"
                )
                raise SecurityAnchorError("security_anchor_pending_missing")
            committed = current.committed_state()
            if observed_committed != committed:
                self._state = _blocked_state(
                    current, "security_anchor_abort_mismatch"
                )
                raise SecurityAnchorError("security_anchor_abort_mismatch")
            self._state = _aborted_state(current)
            return self._state

    def block(
        self,
        expected: SecurityAnchorState,
        reason: str,
    ) -> SecurityAnchorState:
        with self._lock:
            current = self.read()
            _require_expected(current, expected)
            self._state = _blocked_state(current, reason)
            return self._state

    def mark_failed(
        self,
        expected: SecurityAnchorState,
        reason: str,
    ) -> SecurityAnchorState:
        return self.block(expected, reason)


class UnsupportedMonotonicSecurityAnchorStore:
    """Fail-closed placeholder for platforms without an approved adapter."""

    @property
    def supported(self) -> bool:
        return False

    def _unsupported(self, *_args, **_kwargs):
        raise SecurityAnchorError("security_anchor_store_unsupported")

    initialize = _unsupported
    read = _unsupported
    compare = _unsupported
    verify = _unsupported
    prepare = _unsupported
    advance = _unsupported
    abort_pending = _unsupported
    block = _unsupported
    mark_failed = _unsupported


class MacOSMonotonicSecurityAnchorStore:
    """Structured Keychain adapter with digest CAS and no file fallback."""

    def __init__(
        self,
        *,
        installation_id: str,
        database_context_id: str,
        bridge=None,
        serialization_guard: Callable[[], bool] | None = None,
    ) -> None:
        try:
            self._installation_id = validate_uuid4(installation_id)
            self._database_context_id = validate_uuid4(database_context_id)
        except SecurityStoreError:
            raise SecurityAnchorError("security_anchor_binding_invalid") from None
        if bridge is None:
            try:
                from .platform_auth import _MacOSSecurityBridge

                bridge = _MacOSSecurityBridge()
            except Exception:
                raise SecurityAnchorError("security_anchor_store_unavailable") from None
        self._bridge = bridge
        self._serialization_guard = serialization_guard or (lambda: False)
        self._lock = threading.RLock()
        self._configure_bridge()

    @property
    def supported(self) -> bool:
        return True

    def initialize(
        self,
        state: SecurityAnchorState,
        *,
        security_artifacts_exist: bool,
    ) -> SecurityAnchorState:
        _validate_initial(state)
        self._require_binding(state)
        self._require_serialization()
        if security_artifacts_exist:
            raise SecurityAnchorError("security_anchor_missing_with_artifacts")
        with self._lock:
            encoded = state.to_bytes()
            status = self._create(encoded)
            if status == _ERR_SEC_DUPLICATE_ITEM:
                raise SecurityAnchorError("security_anchor_already_exists")
            self._raise_create_status(status)
            if self.read() != state:
                raise SecurityAnchorError("security_anchor_publish_failed")
            return state

    def read(self) -> SecurityAnchorState:
        with self._lock:
            encoded = self._read_bytes()
            state = SecurityAnchorState.from_bytes(encoded)
            self._require_binding(state)
            return state

    def compare(self, observed: SecurityAnchorState) -> bool:
        with self._lock:
            return _matches_observation(self.read(), observed)

    def verify(self, observed: SecurityAnchorState) -> SecurityAnchorState:
        self._require_serialization()
        with self._lock:
            current = self.read()
            if current.status is SecurityAnchorStatus.BLOCKED:
                raise SecurityAnchorError("security_anchor_blocked")
            if _matches_observation(current, observed):
                return current
            blocked = _blocked_state(
                current, "security_anchor_observation_ambiguous"
            )
            self._replace(current, blocked)
            raise SecurityAnchorError("security_anchor_observation_ambiguous")

    def prepare(
        self,
        expected: SecurityAnchorState,
        planned: SecurityAnchorState,
    ) -> SecurityAnchorState:
        self._require_serialization()
        with self._lock:
            current = self.read()
            if current.status is SecurityAnchorStatus.BLOCKED:
                raise SecurityAnchorError("security_anchor_blocked")
            if current.pending is not None:
                if current.committed_state() == expected and current.pending == planned:
                    return current
                raise SecurityAnchorError("security_anchor_changed")
            _require_expected(current, expected)
            try:
                _validate_advance(expected.committed_state(), planned)
            except SecurityAnchorError as error:
                blocked = _blocked_state(
                    current, "security_anchor_advance_invalid"
                )
                self._replace(current, blocked)
                if error.code == "security_anchor_blocked":
                    raise
                raise SecurityAnchorError("security_anchor_advance_invalid") from None
            prepared = _prepared_state(expected, planned)
            self._replace(current, prepared)
            return prepared

    def advance(
        self,
        expected: SecurityAnchorState,
        observed: SecurityAnchorState,
    ) -> SecurityAnchorState:
        self._require_serialization()
        with self._lock:
            current = self.read()
            _require_expected(current, expected)
            if current.status is SecurityAnchorStatus.BLOCKED:
                raise SecurityAnchorError("security_anchor_blocked")
            if current.pending is None:
                blocked = _blocked_state(
                    current, "security_anchor_pending_missing"
                )
                self._replace(current, blocked)
                raise SecurityAnchorError("security_anchor_pending_missing")
            if observed != current.pending:
                blocked = _blocked_state(
                    current, "security_anchor_pending_mismatch"
                )
                self._replace(current, blocked)
                raise SecurityAnchorError("security_anchor_pending_mismatch")
            committed = current.pending
            self._replace(current, committed)
            return committed

    def abort_pending(
        self,
        expected: SecurityAnchorState,
        observed_committed: SecurityAnchorState,
    ) -> SecurityAnchorState:
        self._require_serialization()
        with self._lock:
            current = self.read()
            _require_expected(current, expected)
            if current.status is SecurityAnchorStatus.BLOCKED:
                raise SecurityAnchorError("security_anchor_blocked")
            if current.pending is None:
                blocked = _blocked_state(
                    current, "security_anchor_pending_missing"
                )
                self._replace(current, blocked)
                raise SecurityAnchorError("security_anchor_pending_missing")
            committed = current.committed_state()
            if observed_committed != committed:
                blocked = _blocked_state(
                    current, "security_anchor_abort_mismatch"
                )
                self._replace(current, blocked)
                raise SecurityAnchorError("security_anchor_abort_mismatch")
            aborted = _aborted_state(current)
            self._replace(current, aborted)
            return aborted

    def block(
        self,
        expected: SecurityAnchorState,
        reason: str,
    ) -> SecurityAnchorState:
        self._require_serialization()
        with self._lock:
            current = self.read()
            _require_expected(current, expected)
            blocked = _blocked_state(current, reason)
            if blocked != current:
                self._replace(current, blocked)
            return blocked

    def mark_failed(
        self,
        expected: SecurityAnchorState,
        reason: str,
    ) -> SecurityAnchorState:
        return self.block(expected, reason)

    def _require_binding(self, state: SecurityAnchorState) -> None:
        if (
            state.installation_id != self._installation_id
            or state.database_context_id != self._database_context_id
        ):
            raise SecurityAnchorError("security_anchor_binding_mismatch")

    def _require_serialization(self) -> None:
        try:
            held = self._serialization_guard() is True
        except Exception:
            held = False
        if not held:
            raise SecurityAnchorError("security_anchor_serialization_lock_required")

    @property
    def _service(self) -> bytes:
        return MACOS_MONOTONIC_SECURITY_ANCHOR_SERVICE.encode("ascii")

    @property
    def _account(self) -> bytes:
        return (
            f"v1:{self._installation_id}:{self._database_context_id}".encode(
                "ascii"
            )
        )

    def _create(self, encoded: bytes) -> int:
        payload = (ctypes.c_uint8 * len(encoded)).from_buffer_copy(encoded)
        digest_value = hashlib.sha256(encoded).digest()
        digest = (ctypes.c_uint8 * len(digest_value)).from_buffer_copy(digest_value)
        return int(
            self._bridge.library.jkm_anchor_create(
                self._service,
                self._account,
                payload,
                len(encoded),
                digest,
                len(digest_value),
            )
        )

    def _read_bytes(self) -> bytes:
        pointer = ctypes.POINTER(ctypes.c_uint8)()
        length = ctypes.c_size_t()
        status = int(
            self._bridge.library.jkm_anchor_read(
                self._service,
                self._account,
                ctypes.byref(pointer),
                ctypes.byref(length),
            )
        )
        if status == _ERR_SEC_ITEM_NOT_FOUND:
            raise SecurityAnchorError("security_anchor_missing")
        if status in {
            _ERR_SEC_AUTH_FAILED,
            _ERR_SEC_INTERACTION_NOT_ALLOWED,
            _ERR_SEC_USER_CANCELED,
        }:
            raise SecurityAnchorError("security_anchor_access_denied")
        if status == _ERR_SEC_DECODE:
            raise SecurityAnchorError("security_anchor_corrupt")
        if status != _ERR_SEC_SUCCESS:
            raise SecurityAnchorError("security_anchor_store_read_failed")
        try:
            if length.value < 1 or length.value > SECURITY_ANCHOR_MAX_BYTES or not pointer:
                raise SecurityAnchorError("security_anchor_corrupt")
            return ctypes.string_at(pointer, length.value)
        finally:
            if pointer:
                self._bridge.library.jkm_secret_free(pointer, length)

    def _replace(
        self,
        expected: SecurityAnchorState,
        replacement: SecurityAnchorState,
    ) -> None:
        expected_bytes = expected.to_bytes()
        replacement_bytes = replacement.to_bytes()
        expected_digest_value = hashlib.sha256(expected_bytes).digest()
        replacement_digest_value = hashlib.sha256(replacement_bytes).digest()
        expected_digest = (
            ctypes.c_uint8 * len(expected_digest_value)
        ).from_buffer_copy(expected_digest_value)
        payload = (ctypes.c_uint8 * len(replacement_bytes)).from_buffer_copy(
            replacement_bytes
        )
        replacement_digest = (
            ctypes.c_uint8 * len(replacement_digest_value)
        ).from_buffer_copy(replacement_digest_value)
        status = int(
            self._bridge.library.jkm_anchor_update(
                self._service,
                self._account,
                expected_digest,
                len(expected_digest_value),
                payload,
                len(replacement_bytes),
                replacement_digest,
                len(replacement_digest_value),
            )
        )
        if status == _ERR_SEC_ITEM_NOT_FOUND:
            raise SecurityAnchorError("security_anchor_changed")
        if status in {
            _ERR_SEC_AUTH_FAILED,
            _ERR_SEC_INTERACTION_NOT_ALLOWED,
            _ERR_SEC_USER_CANCELED,
        }:
            raise SecurityAnchorError("security_anchor_access_denied")
        if status != _ERR_SEC_SUCCESS:
            raise SecurityAnchorError("security_anchor_store_update_failed")
        if self._read_bytes() != replacement_bytes:
            raise SecurityAnchorError("security_anchor_publish_failed")

    def _raise_create_status(self, status: int) -> None:
        if status in {
            _ERR_SEC_AUTH_FAILED,
            _ERR_SEC_INTERACTION_NOT_ALLOWED,
            _ERR_SEC_USER_CANCELED,
        }:
            raise SecurityAnchorError("security_anchor_access_denied")
        if status != _ERR_SEC_SUCCESS:
            raise SecurityAnchorError("security_anchor_store_create_failed")

    def _configure_bridge(self) -> None:
        library = self._bridge.library
        required = (
            "jkm_anchor_create",
            "jkm_anchor_read",
            "jkm_anchor_update",
            "jkm_secret_free",
        )
        if any(not hasattr(library, name) for name in required):
            raise SecurityAnchorError("security_anchor_store_unavailable")
        try:
            library.jkm_anchor_create.argtypes = [
                ctypes.c_char_p,
                ctypes.c_char_p,
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.c_size_t,
            ]
            library.jkm_anchor_create.restype = ctypes.c_int32
            library.jkm_anchor_read.argtypes = [
                ctypes.c_char_p,
                ctypes.c_char_p,
                ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8)),
                ctypes.POINTER(ctypes.c_size_t),
            ]
            library.jkm_anchor_read.restype = ctypes.c_int32
            library.jkm_anchor_update.argtypes = [
                ctypes.c_char_p,
                ctypes.c_char_p,
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.c_size_t,
            ]
            library.jkm_anchor_update.restype = ctypes.c_int32
        except AttributeError:
            pass


def _validate_initial(state: SecurityAnchorState) -> None:
    _validate_state(state, allow_pending=False)
    if (
        state.anchor_revision != 1
        or state.status is not SecurityAnchorStatus.ACTIVE
        or state.pending is not None
        or state.block_reason is not None
    ):
        raise SecurityAnchorError("security_anchor_initial_state_invalid")


def _prepared_state(
    expected: SecurityAnchorState,
    planned: SecurityAnchorState,
) -> SecurityAnchorState:
    return SecurityAnchorState(
        anchor_version=expected.anchor_version,
        installation_id=expected.installation_id,
        database_context_id=expected.database_context_id,
        dmk_key_id=expected.dmk_key_id,
        dmk_key_generation=expected.dmk_key_generation,
        anchor_revision=expected.anchor_revision,
        registry_high_water_mark=expected.registry_high_water_mark,
        registry_sha256=expected.registry_sha256,
        journal_revision=expected.journal_revision,
        journal_sha256=expected.journal_sha256,
        migration_generation=expected.migration_generation,
        status=expected.status,
        block_reason=expected.block_reason,
        pending=planned,
    )


def _require_expected(
    current: SecurityAnchorState,
    expected: SecurityAnchorState,
) -> None:
    if current != expected:
        raise SecurityAnchorError("security_anchor_changed")


def _aborted_state(prepared: SecurityAnchorState) -> SecurityAnchorState:
    if prepared.pending is None:
        raise SecurityAnchorError("security_anchor_pending_missing")
    committed = prepared.committed_state()
    return SecurityAnchorState(
        anchor_version=committed.anchor_version,
        installation_id=committed.installation_id,
        database_context_id=committed.database_context_id,
        dmk_key_id=committed.dmk_key_id,
        dmk_key_generation=committed.dmk_key_generation,
        anchor_revision=prepared.pending.anchor_revision,
        registry_high_water_mark=committed.registry_high_water_mark,
        registry_sha256=committed.registry_sha256,
        journal_revision=committed.journal_revision,
        journal_sha256=committed.journal_sha256,
        migration_generation=committed.migration_generation,
        status=SecurityAnchorStatus.ACTIVE,
    )
