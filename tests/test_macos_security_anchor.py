from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import ctypes
from dataclasses import replace
import hashlib
import threading
import uuid

import pytest

from src.security.monotonic_anchor import (
    SECURITY_ANCHOR_VERSION,
    SecurityAnchorError,
    SecurityAnchorState,
    SecurityAnchorStatus,
)
from src.security.infrastructure.monotonic_anchor_store import (
    MACOS_MONOTONIC_SECURITY_ANCHOR_SERVICE,
    MacOSMonotonicSecurityAnchorStore,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _state(*, revision: int = 1, binding: tuple[str, str, str] | None = None) -> SecurityAnchorState:
    installation_id, database_context_id, dmk_key_id = binding or (_uuid(), _uuid(), _uuid())
    return SecurityAnchorState(
        anchor_version=SECURITY_ANCHOR_VERSION,
        installation_id=installation_id,
        database_context_id=database_context_id,
        dmk_key_id=dmk_key_id,
        dmk_key_generation=1,
        anchor_revision=revision,
        registry_high_water_mark=revision,
        registry_sha256=f"{revision:x}" * 64,
        journal_revision=revision,
        journal_sha256=f"{revision + 1:x}" * 64,
        migration_generation=revision,
        status=SecurityAnchorStatus.ACTIVE,
    )


class FakeAnchorLibrary:
    def __init__(self) -> None:
        self.values: dict[tuple[bytes, bytes], tuple[bytes, bytes]] = {}
        self.buffers: list[object] = []
        self.create_status: int | None = None
        self.read_status: int | None = None
        self.update_status: int | None = None
        self.calls: list[tuple[str, bytes, bytes]] = []
        self._lock = threading.Lock()

    @staticmethod
    def _bytes(buffer, length) -> bytes:
        return bytes(buffer[: int(length)])

    def jkm_anchor_create(
        self, service, account, payload, payload_length, payload_digest, digest_length
    ):
        with self._lock:
            if self.create_status is not None:
                return self.create_status
            key = (service, account)
            if key in self.values:
                return -25299
            value = self._bytes(payload, payload_length)
            digest = self._bytes(payload_digest, digest_length)
            self.values[key] = (value, digest)
            self.calls.append(("create", service, account))
            return 0

    def jkm_anchor_read(self, service, account, pointer_out, length_out):
        with self._lock:
            if self.read_status is not None:
                return self.read_status
            value = self.values.get((service, account))
            if value is None:
                return -25300
            payload = value[0]
            buffer = (ctypes.c_uint8 * len(payload)).from_buffer_copy(payload)
            self.buffers.append(buffer)
            ctypes.cast(
                pointer_out, ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8))
            )[0] = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_uint8))
            ctypes.cast(length_out, ctypes.POINTER(ctypes.c_size_t))[0] = len(payload)
            self.calls.append(("read", service, account))
            return 0

    def jkm_anchor_update(
        self,
        service,
        account,
        expected_digest,
        expected_digest_length,
        payload,
        payload_length,
        payload_digest,
        digest_length,
    ):
        with self._lock:
            if self.update_status is not None:
                return self.update_status
            key = (service, account)
            current = self.values.get(key)
            expected = self._bytes(expected_digest, expected_digest_length)
            if current is None or current[1] != expected:
                return -25300
            replacement = self._bytes(payload, payload_length)
            replacement_digest = self._bytes(payload_digest, digest_length)
            self.values[key] = (replacement, replacement_digest)
            self.calls.append(("update", service, account))
            return 0

    def jkm_secret_free(self, _pointer, _length):
        return None


class Bridge:
    def __init__(self, library: FakeAnchorLibrary | None = None) -> None:
        self.library = library or FakeAnchorLibrary()


def _adapter(
    initial: SecurityAnchorState,
    *,
    bridge: Bridge | None = None,
    guard=lambda: True,
) -> MacOSMonotonicSecurityAnchorStore:
    return MacOSMonotonicSecurityAnchorStore(
        installation_id=initial.installation_id,
        database_context_id=initial.database_context_id,
        bridge=bridge or Bridge(),
        serialization_guard=guard,
    )


def test_macos_adapter_uses_separate_namespace_structured_payload_and_no_file_fallback() -> None:
    initial = _state()
    bridge = Bridge()
    adapter = _adapter(initial, bridge=bridge)
    assert adapter.initialize(initial, security_artifacts_exist=False) == initial
    assert adapter.read() == initial
    assert not hasattr(adapter, "path")
    assert {service for _name, service, _account in bridge.library.calls} == {
        MACOS_MONOTONIC_SECURITY_ANCHOR_SERVICE.encode("ascii")
    }
    ((service, account), (payload, digest)), = bridge.library.values.items()
    assert service == MACOS_MONOTONIC_SECURITY_ANCHOR_SERVICE.encode("ascii")
    assert account == (
        f"v1:{initial.installation_id}:{initial.database_context_id}".encode("ascii")
    )
    assert digest == hashlib.sha256(payload).digest()
    assert b"registry_sha256" in payload and b"journal_sha256" in payload


def test_macos_prepare_and_advance_use_digest_bound_compare_and_update() -> None:
    initial = _state()
    planned = _state(
        revision=2,
        binding=(initial.installation_id, initial.database_context_id, initial.dmk_key_id),
    )
    bridge = Bridge()
    adapter = _adapter(initial, bridge=bridge)
    adapter.initialize(initial, security_artifacts_exist=False)
    prepared = adapter.prepare(initial, planned)
    assert prepared.pending == planned
    assert adapter.verify(initial) == prepared
    assert adapter.verify(planned) == prepared
    assert adapter.advance(prepared, planned) == planned
    assert adapter.read() == planned
    assert [name for name, _service, _account in bridge.library.calls].count("update") == 2


def test_macos_restart_on_old_artifacts_can_abort_pending_monotonically() -> None:
    initial = _state()
    planned = _state(
        revision=2,
        binding=(initial.installation_id, initial.database_context_id, initial.dmk_key_id),
    )
    bridge = Bridge()
    first = _adapter(initial, bridge=bridge)
    first.initialize(initial, security_artifacts_exist=False)
    prepared = first.prepare(initial, planned)

    restarted = _adapter(initial, bridge=bridge)
    aborted = restarted.abort_pending(prepared, initial)

    assert aborted.pending is None
    assert aborted.status is SecurityAnchorStatus.ACTIVE
    assert aborted.anchor_revision == planned.anchor_revision
    assert aborted.registry_sha256 == initial.registry_sha256
    assert aborted.journal_sha256 == initial.journal_sha256
    assert restarted.read() == aborted


def test_macos_abort_mismatch_blocks_and_stale_parallel_call_is_changed() -> None:
    initial = _state()
    planned = _state(
        revision=2,
        binding=(initial.installation_id, initial.database_context_id, initial.dmk_key_id),
    )
    bridge = Bridge()
    adapter = _adapter(initial, bridge=bridge)
    adapter.initialize(initial, security_artifacts_exist=False)
    prepared = adapter.prepare(initial, planned)
    wrong = replace(initial, journal_sha256="e" * 64)
    with pytest.raises(SecurityAnchorError) as mismatch:
        adapter.abort_pending(prepared, wrong)
    assert mismatch.value.code == "security_anchor_abort_mismatch"
    assert adapter.read().status is SecurityAnchorStatus.BLOCKED

    other_bridge = Bridge()
    first = _adapter(initial, bridge=other_bridge)
    second = _adapter(initial, bridge=other_bridge)
    first.initialize(initial, security_artifacts_exist=False)
    other_prepared = first.prepare(initial, planned)
    first.abort_pending(other_prepared, initial)
    with pytest.raises(SecurityAnchorError) as stale:
        second.abort_pending(other_prepared, initial)
    assert stale.value.code == "security_anchor_changed"


def test_macos_missing_anchor_with_artifacts_and_duplicate_create_fail_closed() -> None:
    initial = _state()
    adapter = _adapter(initial)
    with pytest.raises(SecurityAnchorError, match="security_anchor_missing_with_artifacts"):
        adapter.initialize(initial, security_artifacts_exist=True)
    adapter.initialize(initial, security_artifacts_exist=False)
    with pytest.raises(SecurityAnchorError, match="security_anchor_already_exists"):
        adapter.initialize(_state(binding=(initial.installation_id, initial.database_context_id, initial.dmk_key_id)), security_artifacts_exist=False)


@pytest.mark.parametrize(
    "status,code",
    [
        (-25300, "security_anchor_missing"),
        (-25293, "security_anchor_access_denied"),
        (-25308, "security_anchor_access_denied"),
        (-128, "security_anchor_access_denied"),
        (-26275, "security_anchor_corrupt"),
        (-1, "security_anchor_store_read_failed"),
    ],
)
def test_macos_read_statuses_are_sanitized(status: int, code: str) -> None:
    initial = _state()
    bridge = Bridge()
    adapter = _adapter(initial, bridge=bridge)
    bridge.library.read_status = status
    with pytest.raises(SecurityAnchorError) as caught:
        adapter.read()
    assert caught.value.code == code


def test_macos_corrupt_keychain_payload_is_detected_without_recreation() -> None:
    initial = _state()
    bridge = Bridge()
    adapter = _adapter(initial, bridge=bridge)
    adapter.initialize(initial, security_artifacts_exist=False)
    key = next(iter(bridge.library.values))
    bridge.library.values[key] = (b"{broken", hashlib.sha256(b"{broken").digest())
    with pytest.raises(SecurityAnchorError, match="security_anchor_format_invalid"):
        adapter.read()
    assert bridge.library.values[key][0] == b"{broken"


def test_macos_mutation_requires_external_cross_process_serialization_guard() -> None:
    initial = _state()
    adapter = _adapter(initial, guard=lambda: False)
    with pytest.raises(SecurityAnchorError, match="security_anchor_serialization_lock_required"):
        adapter.initialize(initial, security_artifacts_exist=False)


def test_macos_cross_adapter_compare_and_update_rejects_parallel_stale_writer() -> None:
    initial = _state()
    first_planned = _state(
        revision=2,
        binding=(initial.installation_id, initial.database_context_id, initial.dmk_key_id),
    )
    second_planned = replace(first_planned, journal_sha256="f" * 64)
    library = FakeAnchorLibrary()
    first = _adapter(initial, bridge=Bridge(library))
    second = _adapter(initial, bridge=Bridge(library))
    first.initialize(initial, security_artifacts_exist=False)

    def prepare(adapter, planned):
        try:
            adapter.prepare(initial, planned)
            return "prepared"
        except SecurityAnchorError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(
            executor.map(
                lambda pair: prepare(*pair),
                ((first, first_planned), (second, second_planned)),
            )
        )
    assert sorted(results) == ["prepared", "security_anchor_changed"]
    persisted = first.read()
    assert persisted.pending in {first_planned, second_planned}


def test_macos_stale_prepare_cannot_block_a_newer_anchor() -> None:
    initial = _state()
    planned = _state(
        revision=2,
        binding=(initial.installation_id, initial.database_context_id, initial.dmk_key_id),
    )
    bridge = Bridge()
    current_writer = _adapter(initial, bridge=bridge)
    stale_writer = _adapter(initial, bridge=bridge)
    current_writer.initialize(initial, security_artifacts_exist=False)
    prepared = current_writer.prepare(initial, planned)
    committed = current_writer.advance(prepared, planned)
    invalid_stale = replace(planned, anchor_revision=9)

    with pytest.raises(SecurityAnchorError) as stale:
        stale_writer.prepare(initial, invalid_stale)
    assert stale.value.code == "security_anchor_changed"
    assert current_writer.read() == committed


@pytest.mark.parametrize(
    "operation,status,code",
    [
        ("create", -25299, "security_anchor_already_exists"),
        ("create", -25293, "security_anchor_access_denied"),
        ("create", -1, "security_anchor_store_create_failed"),
        ("update", -25300, "security_anchor_changed"),
        ("update", -25308, "security_anchor_access_denied"),
        ("update", -1, "security_anchor_store_update_failed"),
    ],
)
def test_macos_write_statuses_are_sanitized(operation: str, status: int, code: str) -> None:
    initial = _state()
    bridge = Bridge()
    adapter = _adapter(initial, bridge=bridge)
    if operation == "create":
        bridge.library.create_status = status
        call = lambda: adapter.initialize(initial, security_artifacts_exist=False)
    else:
        adapter.initialize(initial, security_artifacts_exist=False)
        bridge.library.update_status = status
        planned = _state(
            revision=2,
            binding=(initial.installation_id, initial.database_context_id, initial.dmk_key_id),
        )
        call = lambda: adapter.prepare(initial, planned)
    with pytest.raises(SecurityAnchorError) as caught:
        call()
    assert caught.value.code == code
