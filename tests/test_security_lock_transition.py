from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest

from src.security.database_keys import DerivedDomainKey
from src.security.infrastructure.lock_transition_repository import (
    AppendOnlyLockTransitionRepository,
)
from src.security.lock_transition import (
    AuthenticatedLockEvidence,
    AuthenticatedLockTransitionChain,
    EMPTY_LOCK_OWNER_SHA256,
    EMPTY_LOCK_TRANSITION_SHA256,
    LOCK_TRANSITION_AUTH_PURPOSE,
    LockTransitionError,
    LockTransitionType,
    append_lock_transition,
    validate_lock_transition_chain,
)


def _id() -> str:
    return str(uuid4())


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@pytest.fixture
def binding():
    return _id(), _id(), _id(), _digest("context")


@pytest.fixture
def key() -> DerivedDomainKey:
    return DerivedDomainKey(LOCK_TRANSITION_AUTH_PURPOSE, 1, b"k" * 32)


def _evidence(binding, revision: int = 1) -> AuthenticatedLockEvidence:
    installation, database, migration, context = binding
    return AuthenticatedLockEvidence(
        installation_id=installation,
        database_context_id=database,
        migration_id=migration,
        migration_context_digest=context,
        replay_anchor_revision=revision,
        replay_anchor_digest=_digest(f"anchor-{revision}"),
        journal_digest=_digest("journal"),
        artifact_digest=_digest("artifacts"),
        anchor_authenticated=True,
        journal_authenticated=True,
        artifacts_authenticated=True,
    )


def _append(chain, kind, key, binding, *, second=0, evidence=None):
    installation, database, migration, context = binding
    owner_before = (
        EMPTY_LOCK_OWNER_SHA256
        if not chain.entries
        else chain.entries[-1].owner_after_digest
    )
    if kind is LockTransitionType.ACQUIRED:
        owner_after = _digest(f"owner-{chain.sequence + 1}")
    elif kind is LockTransitionType.RELEASED:
        owner_after = EMPTY_LOCK_OWNER_SHA256
    elif kind is LockTransitionType.TAKEOVER_PREPARED:
        owner_after = _digest(f"takeover-owner-{chain.sequence + 1}")
    else:
        owner_after = owner_before
    return append_lock_transition(
        chain,
        kind,
        installation_id=installation,
        database_context_id=database,
        migration_id=migration,
        migration_context_digest=context,
        evidence=evidence or _evidence(binding),
        owner_before_digest=owner_before,
        owner_after_digest=owner_after,
        occurred_at=datetime(2026, 7, 22, tzinfo=UTC) + timedelta(seconds=second),
        auth_key=key,
    )


def test_complete_hmac_chain_and_takeover(key, binding) -> None:
    chain = AuthenticatedLockTransitionChain()
    for index, kind in enumerate(
        (
            LockTransitionType.ACQUIRED,
            LockTransitionType.STALE_DETECTED,
            LockTransitionType.TAKEOVER_PREPARED,
            LockTransitionType.TAKEOVER_COMMITTED,
            LockTransitionType.RELEASED,
            LockTransitionType.ACQUIRED,
        )
    ):
        chain = _append(
            chain,
            kind,
            key,
            binding,
            second=index,
            evidence=_evidence(binding, index + 1),
        )
    validate_lock_transition_chain(
        chain, key, expected_head_digest=chain.head_digest, expected_sequence=6
    )


def test_tampered_removed_inserted_and_replayed_entries_block(key, binding) -> None:
    first = _append(AuthenticatedLockTransitionChain(), LockTransitionType.ACQUIRED, key, binding)
    chain = _append(first, LockTransitionType.RELEASED, key, binding, second=1)
    tampered = replace(chain.entries[1], owner_after_digest=_digest("evil"))
    with pytest.raises(LockTransitionError, match="lock_transition_auth_failed"):
        validate_lock_transition_chain(AuthenticatedLockTransitionChain((chain.entries[0], tampered)), key)
    with pytest.raises(LockTransitionError, match="lock_transition_replay_detected"):
        validate_lock_transition_chain(first, key, expected_head_digest=chain.head_digest, expected_sequence=2)
    with pytest.raises(LockTransitionError, match="lock_transition_chain_broken"):
        validate_lock_transition_chain(AuthenticatedLockTransitionChain((chain.entries[1],)), key)
    inserted = AuthenticatedLockTransitionChain((chain.entries[0], chain.entries[0], chain.entries[1]))
    with pytest.raises(LockTransitionError):
        validate_lock_transition_chain(inserted, key)


def test_foreign_migration_anchor_rollback_and_unauthenticated_evidence_block(key, binding) -> None:
    chain = _append(
        AuthenticatedLockTransitionChain(),
        LockTransitionType.ACQUIRED,
        key,
        binding,
        evidence=_evidence(binding, 2),
    )
    foreign = (binding[0], binding[1], _id(), binding[3])
    with pytest.raises(LockTransitionError, match="lock_transition_context_mismatch"):
        _append(chain, LockTransitionType.RELEASED, key, foreign)
    with pytest.raises(LockTransitionError, match="lock_transition_anchor_rollback"):
        _append(
            chain,
            LockTransitionType.RELEASED,
            key,
            binding,
            evidence=_evidence(binding, 1),
        )
    invalid = replace(_evidence(binding, 2), journal_authenticated=False)
    with pytest.raises(LockTransitionError, match="lock_transition_evidence_unauthenticated"):
        _append(chain, LockTransitionType.RELEASED, key, binding, evidence=invalid)


@pytest.mark.parametrize(
    ("field_name", "truthy_value"),
    (
        ("anchor_authenticated", "yes"),
        ("journal_authenticated", 1),
        ("artifacts_authenticated", object()),
    ),
)
def test_truthy_non_boolean_authentication_claims_block(
    key, binding, field_name, truthy_value
) -> None:
    evidence = replace(_evidence(binding), **{field_name: truthy_value})
    with pytest.raises(
        LockTransitionError, match="lock_transition_evidence_unauthenticated"
    ):
        _append(
            AuthenticatedLockTransitionChain(),
            LockTransitionType.ACQUIRED,
            key,
            binding,
            evidence=evidence,
        )


def test_evidence_context_and_same_revision_digest_substitution_block(
    key, binding
) -> None:
    foreign = replace(_evidence(binding), migration_id=_id())
    with pytest.raises(
        LockTransitionError, match="lock_transition_evidence_context_mismatch"
    ):
        _append(
            AuthenticatedLockTransitionChain(),
            LockTransitionType.ACQUIRED,
            key,
            binding,
            evidence=foreign,
        )

    chain = _append(
        AuthenticatedLockTransitionChain(),
        LockTransitionType.ACQUIRED,
        key,
        binding,
    )
    substituted = replace(
        _evidence(binding), journal_digest=_digest("substituted-journal")
    )
    with pytest.raises(
        LockTransitionError, match="lock_transition_evidence_revision_mismatch"
    ):
        _append(
            chain,
            LockTransitionType.RELEASED,
            key,
            binding,
            second=1,
            evidence=substituted,
        )

    unchanged_anchor = replace(
        _evidence(binding, 2), replay_anchor_digest=_evidence(binding).replay_anchor_digest
    )
    with pytest.raises(
        LockTransitionError, match="lock_transition_anchor_revision_mismatch"
    ):
        _append(
            chain,
            LockTransitionType.RELEASED,
            key,
            binding,
            second=1,
            evidence=unchanged_anchor,
        )


def test_owner_discontinuity_and_transition_state_substitution_block(
    key, binding
) -> None:
    chain = _append(
        AuthenticatedLockTransitionChain(),
        LockTransitionType.ACQUIRED,
        key,
        binding,
    )
    installation, database, migration, context = binding
    arguments = {
        "installation_id": installation,
        "database_context_id": database,
        "migration_id": migration,
        "migration_context_digest": context,
        "evidence": _evidence(binding),
        "occurred_at": datetime(2026, 7, 22, 0, 0, 1, tzinfo=UTC),
        "auth_key": key,
    }
    with pytest.raises(
        LockTransitionError, match="lock_transition_owner_continuity_invalid"
    ):
        append_lock_transition(
            chain,
            LockTransitionType.RELEASED,
            owner_before_digest=_digest("foreign-owner"),
            owner_after_digest=EMPTY_LOCK_OWNER_SHA256,
            **arguments,
        )
    with pytest.raises(
        LockTransitionError, match="lock_transition_owner_state_invalid"
    ):
        append_lock_transition(
            chain,
            LockTransitionType.RELEASED,
            owner_before_digest=chain.entries[-1].owner_after_digest,
            owner_after_digest=_digest("still-owned"),
            **arguments,
        )


def test_repository_is_append_only_and_detects_tamper_and_tail_replay(tmp_path: Path, key, binding) -> None:
    repository = AppendOnlyLockTransitionRepository(tmp_path)
    empty = repository.load(
        key,
        expected_head_digest=EMPTY_LOCK_TRANSITION_SHA256,
        expected_sequence=0,
    )
    first = _append(empty, LockTransitionType.ACQUIRED, key, binding)
    assert repository.append(empty, first, key) == first
    second = _append(first, LockTransitionType.RELEASED, key, binding, second=1)
    assert repository.append(first, second, key) == second
    files = sorted(repository.path.iterdir())
    payload = json.loads(files[0].read_text())
    payload["sequence"] = 9
    files[0].write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    with pytest.raises(LockTransitionError):
        repository.load(
            key,
            expected_head_digest=second.head_digest,
            expected_sequence=2,
        )

    clean = AppendOnlyLockTransitionRepository(tmp_path / "clean")
    (tmp_path / "clean").mkdir()
    assert clean.append(AuthenticatedLockTransitionChain(), first, key) == first
    with pytest.raises(LockTransitionError, match="lock_transition_replay_detected"):
        clean.load(key, expected_head_digest=second.head_digest, expected_sequence=2)


def test_repository_requires_explicit_replay_expectation(
    tmp_path: Path, key
) -> None:
    repository = AppendOnlyLockTransitionRepository(tmp_path)
    with pytest.raises(
        LockTransitionError, match="lock_transition_replay_expectation_required"
    ):
        repository.load(key)
    with pytest.raises(
        LockTransitionError, match="lock_transition_replay_expectation_required"
    ):
        repository.load(
            key, expected_head_digest=EMPTY_LOCK_TRANSITION_SHA256
        )


def test_repository_crash_before_or_after_persistence_is_deterministic(tmp_path: Path, key, binding) -> None:
    empty = AuthenticatedLockTransitionChain()
    first = _append(empty, LockTransitionType.ACQUIRED, key, binding)

    def before(point: str) -> None:
        if point == "before_persist":
            raise RuntimeError("crash")

    repository = AppendOnlyLockTransitionRepository(tmp_path, fault_injector=before)
    with pytest.raises(RuntimeError, match="crash"):
        repository.append(empty, first, key)
    assert AppendOnlyLockTransitionRepository(tmp_path).load(
        key,
        expected_head_digest=EMPTY_LOCK_TRANSITION_SHA256,
        expected_sequence=0,
    ) == empty

    def after(point: str) -> None:
        if point == "after_entry_fsync":
            raise RuntimeError("crash")

    repository = AppendOnlyLockTransitionRepository(tmp_path, fault_injector=after)
    with pytest.raises(RuntimeError, match="crash"):
        repository.append(empty, first, key)
    assert AppendOnlyLockTransitionRepository(tmp_path).load(
        key,
        expected_head_digest=first.head_digest,
        expected_sequence=1,
    ) == first


def test_parallel_takeover_publish_has_single_winner(tmp_path: Path, key, binding) -> None:
    repository = AppendOnlyLockTransitionRepository(tmp_path)
    first = _append(AuthenticatedLockTransitionChain(), LockTransitionType.ACQUIRED, key, binding)
    repository.append(AuthenticatedLockTransitionChain(), first, key)
    stale = _append(first, LockTransitionType.STALE_DETECTED, key, binding, second=1)
    repository.append(first, stale, key)
    prepared = _append(stale, LockTransitionType.TAKEOVER_PREPARED, key, binding, second=2)
    repository.append(stale, prepared, key)
    committed = _append(prepared, LockTransitionType.TAKEOVER_COMMITTED, key, binding, second=3)
    assert repository.append(prepared, committed, key) == committed
    with pytest.raises(LockTransitionError, match="lock_transition_replay_detected"):
        repository.append(prepared, committed, key)
