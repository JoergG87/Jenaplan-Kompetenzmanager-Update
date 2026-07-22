from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import uuid

import pytest

from src.security.monotonic_anchor import (
    SECURITY_ANCHOR_VERSION,
    MonotonicSecurityAnchorStore,
    SecurityAnchorError,
    SecurityAnchorState,
    SecurityAnchorStatus,
)
from src.security.infrastructure.monotonic_anchor_store import (
    InMemoryMonotonicSecurityAnchorStore,
    UnsupportedMonotonicSecurityAnchorStore,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _state(
    *,
    anchor_revision: int = 1,
    registry_high_water_mark: int = 1,
    registry_hash: str = "1" * 64,
    journal_revision: int = 1,
    journal_hash: str = "2" * 64,
    migration_generation: int = 1,
    installation_id: str | None = None,
    database_context_id: str | None = None,
    dmk_key_id: str | None = None,
    dmk_key_generation: int = 1,
) -> SecurityAnchorState:
    return SecurityAnchorState(
        anchor_version=SECURITY_ANCHOR_VERSION,
        installation_id=installation_id or _uuid(),
        database_context_id=database_context_id or _uuid(),
        dmk_key_id=dmk_key_id or _uuid(),
        dmk_key_generation=dmk_key_generation,
        anchor_revision=anchor_revision,
        registry_high_water_mark=registry_high_water_mark,
        registry_sha256=registry_hash,
        journal_revision=journal_revision,
        journal_sha256=journal_hash,
        migration_generation=migration_generation,
        status=SecurityAnchorStatus.ACTIVE,
    )


def _next(current: SecurityAnchorState, **changes: object) -> SecurityAnchorState:
    return replace(
        current.committed_state(),
        anchor_revision=current.anchor_revision + 1,
        journal_revision=current.journal_revision + 1,
        journal_sha256="3" * 64,
        **changes,
    )


def test_port_contract_is_runtime_checkable() -> None:
    assert isinstance(InMemoryMonotonicSecurityAnchorStore(), MonotonicSecurityAnchorStore)


def test_initialize_is_allowed_only_without_existing_security_artifacts() -> None:
    initial = _state()
    store = InMemoryMonotonicSecurityAnchorStore()
    assert store.initialize(initial, security_artifacts_exist=False) == initial
    assert store.initialize(initial, security_artifacts_exist=False) == initial
    assert store.read() == initial

    blocked = InMemoryMonotonicSecurityAnchorStore()
    with pytest.raises(SecurityAnchorError) as caught:
        blocked.initialize(initial, security_artifacts_exist=True)
    assert caught.value.code == "security_anchor_missing_with_artifacts"
    with pytest.raises(SecurityAnchorError, match="security_anchor_missing"):
        blocked.read()

    with pytest.raises(SecurityAnchorError, match="security_anchor_initial_state_invalid"):
        InMemoryMonotonicSecurityAnchorStore().initialize(
            replace(initial, anchor_revision=2), security_artifacts_exist=False
        )


def test_committed_and_exact_pending_are_the_only_restart_valid_states() -> None:
    committed = _state()
    planned = _next(committed)
    store = InMemoryMonotonicSecurityAnchorStore(committed)
    prepared = store.prepare(committed, planned)

    assert prepared.committed_state() == committed
    assert prepared.pending == planned
    assert store.compare(committed) is True
    assert store.compare(planned) is True
    assert store.verify(committed) == prepared
    assert store.verify(planned) == prepared

    restarted_old = InMemoryMonotonicSecurityAnchorStore(prepared)
    assert restarted_old.verify(committed) == prepared
    restarted_new = InMemoryMonotonicSecurityAnchorStore(prepared)
    assert restarted_new.advance(prepared, planned) == planned
    assert restarted_new.read() == planned


def test_advance_commits_only_the_exact_pending_snapshot() -> None:
    committed = _state()
    planned = _next(committed)
    store = InMemoryMonotonicSecurityAnchorStore(committed)
    prepared = store.prepare(committed, planned)

    wrong = replace(planned, journal_sha256="4" * 64)
    with pytest.raises(SecurityAnchorError) as caught:
        store.advance(prepared, wrong)
    assert caught.value.code == "security_anchor_pending_mismatch"
    assert store.read().status is SecurityAnchorStatus.BLOCKED


def test_restart_on_exact_old_state_can_abort_pending_without_revision_reset() -> None:
    committed = _state(anchor_revision=4, journal_revision=7)
    planned = _next(committed)
    prepared = InMemoryMonotonicSecurityAnchorStore(committed).prepare(
        committed, planned
    )
    restarted = InMemoryMonotonicSecurityAnchorStore(prepared)

    aborted = restarted.abort_pending(prepared, committed)

    assert aborted.pending is None
    assert aborted.status is SecurityAnchorStatus.ACTIVE
    assert aborted.anchor_revision == planned.anchor_revision == 5
    assert aborted.registry_high_water_mark == committed.registry_high_water_mark
    assert aborted.registry_sha256 == committed.registry_sha256
    assert aborted.journal_revision == committed.journal_revision
    assert aborted.journal_sha256 == committed.journal_sha256
    assert aborted.migration_generation == committed.migration_generation
    assert restarted.read() == aborted


def test_abort_pending_mismatch_blocks_and_parallel_stale_caller_is_changed() -> None:
    committed = _state()
    planned = _next(committed)
    store = InMemoryMonotonicSecurityAnchorStore(committed)
    prepared = store.prepare(committed, planned)
    wrong = replace(committed, registry_sha256="e" * 64)
    with pytest.raises(SecurityAnchorError) as mismatch:
        store.abort_pending(prepared, wrong)
    assert mismatch.value.code == "security_anchor_abort_mismatch"
    assert store.read().status is SecurityAnchorStatus.BLOCKED

    concurrent = InMemoryMonotonicSecurityAnchorStore(committed)
    concurrent_prepared = concurrent.prepare(committed, planned)
    concurrent.abort_pending(concurrent_prepared, committed)
    with pytest.raises(SecurityAnchorError) as stale:
        concurrent.abort_pending(concurrent_prepared, committed)
    assert stale.value.code == "security_anchor_changed"


@pytest.mark.parametrize(
    "replayed",
    [
        lambda current: replace(current, registry_high_water_mark=0, registry_sha256="0" * 64),
        lambda current: replace(current, journal_revision=0, journal_sha256="0" * 64),
        lambda current: replace(
            current,
            registry_high_water_mark=0,
            registry_sha256="0" * 64,
            journal_revision=0,
            journal_sha256="0" * 64,
        ),
    ],
)
def test_registry_journal_and_joint_replay_block(replayed) -> None:
    current = _state(anchor_revision=3, registry_high_water_mark=3, journal_revision=8)
    store = InMemoryMonotonicSecurityAnchorStore(current)
    with pytest.raises(SecurityAnchorError) as caught:
        store.verify(replayed(current))
    assert caught.value.code == "security_anchor_observation_ambiguous"
    assert store.read().status is SecurityAnchorStatus.BLOCKED


def test_equal_counters_with_an_older_or_alternate_digest_block() -> None:
    current = _state()
    store = InMemoryMonotonicSecurityAnchorStore(current)
    alternate = replace(current, registry_sha256="a" * 64)
    assert store.compare(alternate) is False
    with pytest.raises(SecurityAnchorError, match="security_anchor_observation_ambiguous"):
        store.verify(alternate)
    assert store.read().status is SecurityAnchorStatus.BLOCKED


@pytest.mark.parametrize(
    "field,value",
    [
        ("installation_id", _uuid()),
        ("database_context_id", _uuid()),
        ("dmk_key_id", _uuid()),
        ("dmk_key_generation", 2),
    ],
)
def test_wrong_installation_database_or_keyset_binding_blocks(field: str, value: object) -> None:
    current = _state()
    store = InMemoryMonotonicSecurityAnchorStore(current)
    with pytest.raises(SecurityAnchorError, match="security_anchor_observation_ambiguous"):
        store.verify(replace(current, **{field: value}))
    assert store.read().status is SecurityAnchorStatus.BLOCKED


@pytest.mark.parametrize(
    "planned",
    [
        lambda current: replace(_next(current), anchor_revision=current.anchor_revision + 2),
        lambda current: replace(_next(current), journal_revision=current.journal_revision + 2),
        lambda current: replace(
            _next(current),
            registry_high_water_mark=current.registry_high_water_mark + 2,
        ),
        lambda current: replace(
            _next(current), migration_generation=current.migration_generation + 2
        ),
        lambda current: replace(_next(current), journal_revision=current.journal_revision - 1),
        lambda current: replace(
            _next(current), journal_revision=current.journal_revision
        ),
        lambda current: replace(
            _next(current), journal_sha256=current.journal_sha256
        ),
        lambda current: replace(
            _next(current),
            registry_high_water_mark=current.registry_high_water_mark + 1,
            registry_sha256=current.registry_sha256,
        ),
    ],
)
def test_rollback_and_illegal_large_jumps_block_during_prepare(planned) -> None:
    current = _state()
    store = InMemoryMonotonicSecurityAnchorStore(current)
    with pytest.raises(SecurityAnchorError) as caught:
        store.prepare(current, planned(current))
    assert caught.value.code == "security_anchor_advance_invalid"
    assert store.read().status is SecurityAnchorStatus.BLOCKED


def test_revision_cannot_be_reused_without_a_pending_state() -> None:
    current = _state()
    store = InMemoryMonotonicSecurityAnchorStore(current)
    with pytest.raises(SecurityAnchorError) as caught:
        store.advance(current, current)
    assert caught.value.code == "security_anchor_pending_missing"
    assert store.read().status is SecurityAnchorStatus.BLOCKED


def test_parallel_advance_has_one_winner_and_does_not_corrupt_the_commit() -> None:
    committed = _state()
    planned = _next(committed)
    store = InMemoryMonotonicSecurityAnchorStore(committed)
    prepared = store.prepare(committed, planned)

    def commit() -> str:
        try:
            store.advance(prepared, planned)
            return "advanced"
        except SecurityAnchorError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _index: commit(), range(2)))
    assert sorted(results) == ["advanced", "security_anchor_changed"]
    assert store.read() == planned


def test_stale_prepare_cannot_block_a_newer_anchor_with_an_invalid_plan() -> None:
    initial = _state()
    first_plan = _next(initial)
    store = InMemoryMonotonicSecurityAnchorStore(initial)
    prepared = store.prepare(initial, first_plan)
    committed = store.advance(prepared, first_plan)
    invalid_stale_plan = replace(
        first_plan,
        anchor_revision=initial.anchor_revision + 9,
    )

    with pytest.raises(SecurityAnchorError) as stale:
        store.prepare(initial, invalid_stale_plan)
    assert stale.value.code == "security_anchor_changed"
    assert store.read() == committed


def test_block_and_mark_failed_are_irreversible_and_sanitized() -> None:
    current = _state()
    store = InMemoryMonotonicSecurityAnchorStore(current)
    blocked = store.block(current, "keychain_read_failed")
    assert blocked.status is SecurityAnchorStatus.BLOCKED
    assert blocked.block_reason == "keychain_read_failed"
    assert store.mark_failed(blocked, "keychain_read_failed") == blocked
    with pytest.raises(SecurityAnchorError, match="security_anchor_blocked"):
        store.verify(current)
    with pytest.raises(SecurityAnchorError, match="security_anchor_block_reason_invalid"):
        InMemoryMonotonicSecurityAnchorStore(current).block(current, "/secret/path")


def test_state_encoding_is_canonical_bounded_strict_and_contains_no_content() -> None:
    initial = _state()
    prepared = replace(initial, pending=_next(initial))
    encoded = prepared.to_bytes()
    assert len(encoded) < 8192
    assert SecurityAnchorState.from_bytes(encoded) == prepared
    assert SecurityAnchorState.from_bytes(encoded).to_bytes() == encoded
    assert b"password" not in encoded.lower()
    assert b"student" not in encoded.lower()
    assert b"database-key-material" not in encoded
    assert "pending=" not in repr(prepared)

    noncanonical = json.dumps(json.loads(encoded), indent=2).encode("ascii")
    with pytest.raises(SecurityAnchorError, match="security_anchor_not_canonical"):
        SecurityAnchorState.from_bytes(noncanonical)
    payload = json.loads(encoded)
    payload["unknown"] = True
    with pytest.raises(SecurityAnchorError, match="security_anchor_fields_invalid"):
        SecurityAnchorState.from_bytes(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
        )


def test_unsupported_platform_store_fails_closed_without_fallback() -> None:
    store = UnsupportedMonotonicSecurityAnchorStore()
    assert store.supported is False
    with pytest.raises(SecurityAnchorError, match="security_anchor_store_unsupported"):
        store.initialize(_state(), security_artifacts_exist=False)
    with pytest.raises(SecurityAnchorError, match="security_anchor_store_unsupported"):
        store.read()
