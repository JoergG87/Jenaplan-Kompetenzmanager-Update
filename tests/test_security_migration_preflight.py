from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from src.security.database_keys import DerivedDomainKey
from src.security.lock_transition import (
    AuthenticatedLockEvidence,
    AuthenticatedLockTransition,
    AuthenticatedLockTransitionChain,
    EMPTY_LOCK_OWNER_SHA256,
    LOCK_TRANSITION_AUTH_PURPOSE,
    LockTransitionType,
    append_lock_transition,
    validate_lock_transition_chain,
)
from src.security.migration_context import (
    MIGRATION_CROSSBINDING_VERSION,
    MigrationArtifactBinding,
    MigrationCrossbindingContext,
)
from src.security.migration_journal import MigrationPhase
from src.security.migration_preflight import (
    AuthenticatedArtifactProjection,
    AuthenticatedEnvelopeRegistryProjection,
    AuthenticatedJournalProjection,
    AuthenticatedLockHeadProjection,
    AuthenticatedMigrationPreflightProjection,
    AuthenticatedReplayAnchorProjection,
    AuthenticatedSourceAbsence,
    MigrationPreflightMode,
    derive_migration_preflight,
)


def _artifact(role: str, index: int, *, present: bool) -> MigrationArtifactBinding:
    return MigrationArtifactBinding(
        role=role,
        capability_id=f"{index:08d}-0000-4000-8000-{index:012d}",
        relative_name=f"{role}.sqlite",
        present=present,
        identity_scheme="posix-inode" if present else None,
        identity_value=f"1:{index}" if present else None,
        size_bytes=index * 100 if present else None,
        sha256=f"{index:x}" * 64 if present else None,
    )


def _artifacts(
    source: bool = True, backup: bool = True, target: bool = True
) -> tuple[MigrationArtifactBinding, ...]:
    return (
        _artifact("source", 1, present=source),
        _artifact("backup", 2, present=backup),
        _artifact("target", 3, present=target),
    )


def _context(
    artifacts: tuple[MigrationArtifactBinding, ...],
    *,
    phase: MigrationPhase,
    lock_transition_type: str,
) -> tuple[MigrationCrossbindingContext, AuthenticatedLockTransition]:
    installation_id = "11111111-1111-4111-8111-111111111111"
    database_context_id = "22222222-2222-4222-8222-222222222222"
    migration_id = "33333333-3333-4333-8333-333333333333"
    journal = AuthenticatedJournalProjection.create(
        installation_id=installation_id,
        database_context_id=database_context_id,
        migration_id=migration_id,
        dmk_key_id="44444444-4444-4444-8444-444444444444",
        dmk_key_generation=1,
        database_key_id="55555555-5555-4555-8555-555555555555",
        database_key_generation=1,
        revision=2,
        source_sha256="b" * 64,
        phase=phase,
    )
    context = MigrationCrossbindingContext(
        context_version=MIGRATION_CROSSBINDING_VERSION,
        installation_id=installation_id,
        database_context_id=database_context_id,
        migration_id=migration_id,
        migration_generation=1,
        dmk_key_id="44444444-4444-4444-8444-444444444444",
        dmk_key_generation=1,
        database_key_id="55555555-5555-4555-8555-555555555555",
        database_key_generation=1,
        envelope_registry_sha256="a" * 64,
        envelope_registry_revision=1,
        journal_sha256=journal.source_sha256,
        journal_revision=2,
        journal_phase=phase.value,
        anchor_revision=3,
        replay_anchor_sha256="6" * 64,
        lock_transition_sha256="0" * 64,
        lock_transition_sequence=1,
        lock_transition_type=lock_transition_type,
        lock_owner_before_sha256="7" * 64,
        lock_owner_after_sha256="8" * 64,
        artifacts=artifacts,
        expected_sqlite_version="3.50.4",
        expected_sqlcipher_version="4.17.0",
        expected_schema_version=7,
    )
    evidence = AuthenticatedLockEvidence(
        installation_id=installation_id,
        database_context_id=database_context_id,
        migration_id=migration_id,
        migration_context_digest=context.lock_binding_digest_sha256(),
        replay_anchor_revision=context.anchor_revision,
        replay_anchor_digest=context.replay_anchor_sha256,
        journal_digest=context.journal_sha256,
        artifact_digest="9" * 64,
        anchor_authenticated=True,
        journal_authenticated=True,
        artifacts_authenticated=True,
    )
    chain = AuthenticatedLockTransitionChain()
    key = DerivedDomainKey(LOCK_TRANSITION_AUTH_PURPOSE, 1, b"k" * 32)
    path = {
        "ACQUIRED": (LockTransitionType.ACQUIRED,),
        "RELEASED": (LockTransitionType.ACQUIRED, LockTransitionType.RELEASED),
        "STALE_DETECTED": (
            LockTransitionType.ACQUIRED,
            LockTransitionType.STALE_DETECTED,
        ),
        "TAKEOVER_PREPARED": (
            LockTransitionType.ACQUIRED,
            LockTransitionType.STALE_DETECTED,
            LockTransitionType.TAKEOVER_PREPARED,
        ),
        "TAKEOVER_COMMITTED": (
            LockTransitionType.ACQUIRED,
            LockTransitionType.STALE_DETECTED,
            LockTransitionType.TAKEOVER_PREPARED,
            LockTransitionType.TAKEOVER_COMMITTED,
        ),
        "BLOCKED": (LockTransitionType.ACQUIRED, LockTransitionType.BLOCKED),
    }[lock_transition_type]
    for index, transition_type in enumerate(path):
        owner_before = (
            EMPTY_LOCK_OWNER_SHA256
            if not chain.entries
            else chain.entries[-1].owner_after_digest
        )
        if transition_type is LockTransitionType.ACQUIRED:
            owner_after = "7" * 64
        elif transition_type is LockTransitionType.RELEASED:
            owner_after = EMPTY_LOCK_OWNER_SHA256
        elif transition_type is LockTransitionType.TAKEOVER_PREPARED:
            owner_after = "8" * 64
        else:
            owner_after = owner_before
        chain = append_lock_transition(
            chain,
            transition_type,
            installation_id=installation_id,
            database_context_id=database_context_id,
            migration_id=migration_id,
            migration_context_digest=context.lock_binding_digest_sha256(),
            evidence=evidence,
            owner_before_digest=owner_before,
            owner_after_digest=owner_after,
            occurred_at=datetime(2026, 7, 22, 12, 0, index, tzinfo=UTC),
            auth_key=key,
        )
    head = chain.entries[-1]
    validate_lock_transition_chain(
        chain,
        key,
        expected_head_digest=head.digest(),
        expected_sequence=head.sequence,
    )
    return (
        replace(
            context,
            lock_transition_sha256=head.digest(),
            lock_transition_sequence=head.sequence,
            lock_owner_before_sha256=head.owner_before_digest,
            lock_owner_after_sha256=head.owner_after_digest,
        ),
        head,
    )


def _projection(
    phase: MigrationPhase | None,
    *,
    artifacts: tuple[MigrationArtifactBinding, ...] | None = None,
    new: bool = False,
    lock_transition_type: str | None = "RELEASED",
) -> AuthenticatedMigrationPreflightProjection:
    bound = artifacts or _artifacts()
    if new:
        context = None
        lock_transition = None
    else:
        context, lock_transition = _context(
            bound,
            phase=phase or MigrationPhase.NOT_STARTED,
            lock_transition_type=lock_transition_type or "RELEASED",
        )
    installation_id = "11111111-1111-4111-8111-111111111111"
    database_context_id = "22222222-2222-4222-8222-222222222222"
    if new:
        sources = tuple(
            AuthenticatedSourceAbsence.create(
                source=source,
                installation_id=installation_id,
                database_context_id=database_context_id,
            )
            for source in ("anchor", "envelope_registry", "journal", "lock_chain")
        )
    else:
        assert context is not None and phase is not None and lock_transition_type is not None
        sources = (
            AuthenticatedReplayAnchorProjection(
                installation_id=installation_id,
                database_context_id=database_context_id,
                dmk_key_id=context.dmk_key_id,
                dmk_key_generation=context.dmk_key_generation,
                migration_generation=context.migration_generation,
                revision=context.anchor_revision,
                canonical_sha256=context.replay_anchor_sha256,
            ),
            AuthenticatedEnvelopeRegistryProjection(
                installation_id=installation_id,
                database_context_id=database_context_id,
                dmk_key_id=context.dmk_key_id,
                dmk_key_generation=context.dmk_key_generation,
                database_key_id=context.database_key_id,
                database_key_generation=context.database_key_generation,
                revision=context.envelope_registry_revision,
                canonical_sha256=context.envelope_registry_sha256,
            ),
            AuthenticatedJournalProjection.create(
                installation_id=installation_id,
                database_context_id=database_context_id,
                migration_id=context.migration_id,
                dmk_key_id=context.dmk_key_id,
                dmk_key_generation=context.dmk_key_generation,
                database_key_id=context.database_key_id,
                database_key_generation=context.database_key_generation,
                revision=context.journal_revision,
                source_sha256=context.journal_sha256,
                phase=phase,
            ),
            AuthenticatedLockHeadProjection.from_authenticated_transition(
                lock_transition
            ),
        )
    return AuthenticatedMigrationPreflightProjection(
        expected_context=context,
        authenticated_context=context,
        replay_anchor=sources[0],
        envelope_registry=sources[1],
        journal=sources[2],
        lock_head=sources[3],
        artifacts=AuthenticatedArtifactProjection.create(
            installation_id=installation_id,
            database_context_id=database_context_id,
            migration_id=None if new else context.migration_id,
            expected_artifacts=bound,
            observed_artifacts=bound,
            unexpected_artifacts=(),
        ),
        expected_sqlite_version="3.50.4",
        observed_sqlite_version="3.50.4",
        expected_sqlcipher_version="4.17.0",
        observed_sqlcipher_version="4.17.0",
        expected_schema_version=7,
        observed_schema_version=7,
    )


def test_all_five_modes_are_derived_without_mutation() -> None:
    cases = (
        (
            _projection(None, artifacts=_artifacts(True, False, False), new=True),
            MigrationPreflightMode.NEW,
        ),
        (
            _projection(
                MigrationPhase.BACKUP_VERIFIED,
                artifacts=_artifacts(True, True, False),
            ),
            MigrationPreflightMode.RESUME,
        ),
        (_projection(MigrationPhase.EXPORT_STARTED), MigrationPreflightMode.RECOVERY),
        (_projection(MigrationPhase.COMPLETED), MigrationPreflightMode.COMPLETED),
        (_projection(MigrationPhase.BLOCKED), MigrationPreflightMode.BLOCKED),
    )

    for projection, expected in cases:
        before = repr(projection)
        assert derive_migration_preflight(projection).mode is expected
        assert repr(projection) == before


def test_source_digests_remain_distinct_from_projection_seals() -> None:
    projection = _projection(MigrationPhase.EXPORT_STARTED)
    assert projection.expected_context is not None
    assert isinstance(projection.journal, AuthenticatedJournalProjection)
    assert isinstance(projection.lock_head, AuthenticatedLockHeadProjection)

    assert (
        projection.journal.source_sha256
        == projection.expected_context.journal_sha256
    )
    assert projection.journal.projection_sha256 != projection.journal.source_sha256
    assert (
        projection.lock_head.source_sha256
        == projection.lock_head.transition.digest()
        == projection.expected_context.lock_transition_sha256
    )


@pytest.mark.parametrize(
    ("phase", "presence"),
    [
        (MigrationPhase.NOT_STARTED, (True, False, False)),
        (MigrationPhase.PREFLIGHT_STARTED, (True, False, False)),
        (MigrationPhase.SOURCE_VERIFIED, (True, False, False)),
        (MigrationPhase.BACKUP_VERIFIED, (True, True, False)),
        (MigrationPhase.EXPORT_COMPLETED, (True, True, True)),
        (MigrationPhase.VALIDATION_COMPLETED, (True, True, True)),
        (MigrationPhase.REOPEN_VERIFIED, (True, True, True)),
    ],
)
def test_stable_phase_artifact_matrix_resumes(
    phase: MigrationPhase, presence: tuple[bool, bool, bool]
) -> None:
    decision = derive_migration_preflight(
        _projection(phase, artifacts=_artifacts(*presence))
    )
    assert decision.mode is MigrationPreflightMode.RESUME


@pytest.mark.parametrize(
    ("phase", "presence"),
    [
        (MigrationPhase.BACKUP_STARTED, (True, False, False)),
        (MigrationPhase.BACKUP_CREATED, (True, True, False)),
        (MigrationPhase.TARGET_CREATION_STARTED, (True, True, False)),
        (MigrationPhase.TARGET_CREATED, (True, True, True)),
        (MigrationPhase.EXPORT_STARTED, (True, True, True)),
        (MigrationPhase.VALIDATION_STARTED, (True, True, True)),
        (MigrationPhase.REOPEN_STARTED, (True, True, True)),
        (MigrationPhase.ROLLBACK_STARTED, (True, True, True)),
        (MigrationPhase.ROLLBACK_STARTED, (True, True, False)),
        (MigrationPhase.ROLLBACK_COMPLETED, (True, True, False)),
    ],
)
def test_interrupted_phase_artifact_matrix_enters_recovery(
    phase: MigrationPhase, presence: tuple[bool, bool, bool]
) -> None:
    decision = derive_migration_preflight(
        _projection(phase, artifacts=_artifacts(*presence))
    )
    assert decision.mode is MigrationPreflightMode.RECOVERY


@pytest.mark.parametrize("lock_head", ["STALE_DETECTED", "TAKEOVER_PREPARED"])
def test_incomplete_lock_transition_forces_recovery(lock_head: str) -> None:
    decision = derive_migration_preflight(
        _projection(
            MigrationPhase.BACKUP_VERIFIED,
            artifacts=_artifacts(True, True, False),
            lock_transition_type=lock_head,
        )
    )
    assert decision.mode is MigrationPreflightMode.RECOVERY


def test_phase_cannot_change_without_matching_authenticated_journal() -> None:
    valid = _projection(MigrationPhase.EXPORT_COMPLETED)
    assert isinstance(valid.journal, AuthenticatedJournalProjection)
    forged = replace(valid.journal, phase=MigrationPhase.COMPLETED)

    decision = derive_migration_preflight(replace(valid, journal=forged))

    assert decision.mode is MigrationPreflightMode.BLOCKED
    assert decision.error_code == "migration_preflight_projection_invalid"

    resealed = AuthenticatedJournalProjection.create(
        installation_id=valid.journal.installation_id,
        database_context_id=valid.journal.database_context_id,
        migration_id=valid.journal.migration_id,
        dmk_key_id=valid.journal.dmk_key_id,
        dmk_key_generation=valid.journal.dmk_key_generation,
        database_key_id=valid.journal.database_key_id,
        database_key_generation=valid.journal.database_key_generation,
        revision=valid.journal.revision,
        source_sha256=valid.journal.source_sha256,
        phase=MigrationPhase.COMPLETED,
    )
    jointly_changed = replace(
        valid,
        expected_context=replace(valid.expected_context, journal_phase="completed"),
        authenticated_context=replace(
            valid.authenticated_context, journal_phase="completed"
        ),
        journal=resealed,
    )
    assert jointly_changed.expected_context.journal_sha256 == valid.expected_context.journal_sha256
    assert derive_migration_preflight(jointly_changed).mode is MigrationPreflightMode.BLOCKED


def test_lock_type_cannot_change_without_matching_authenticated_head() -> None:
    valid = _projection(MigrationPhase.BACKUP_VERIFIED, artifacts=_artifacts(True, True, False))
    assert isinstance(valid.lock_head, AuthenticatedLockHeadProjection)
    forged_transition = replace(
        valid.lock_head.transition,
        transition=LockTransitionType.STALE_DETECTED,
    )
    forged = AuthenticatedLockHeadProjection.from_authenticated_transition(
        forged_transition
    )

    decision = derive_migration_preflight(replace(valid, lock_head=forged))

    assert decision.mode is MigrationPreflightMode.BLOCKED
    assert decision.error_code == "migration_preflight_authenticated_state_missing"

    jointly_changed = replace(
        valid,
        expected_context=replace(
            valid.expected_context, lock_transition_type="STALE_DETECTED"
        ),
        authenticated_context=replace(
            valid.authenticated_context, lock_transition_type="STALE_DETECTED"
        ),
        lock_head=forged,
    )
    assert (
        jointly_changed.expected_context.lock_transition_sha256
        == valid.expected_context.lock_transition_sha256
    )
    assert derive_migration_preflight(jointly_changed).mode is MigrationPreflightMode.BLOCKED


def test_lock_binding_rejects_non_lock_context_change_and_foreign_valid_head() -> None:
    valid = _projection(MigrationPhase.EXPORT_STARTED)
    changed_context = replace(valid.expected_context, expected_schema_version=8)
    changed_non_lock = replace(
        valid,
        expected_context=changed_context,
        authenticated_context=changed_context,
        expected_schema_version=8,
        observed_schema_version=8,
    )
    assert derive_migration_preflight(changed_non_lock).mode is MigrationPreflightMode.BLOCKED

    assert isinstance(valid.lock_head, AuthenticatedLockHeadProjection)
    _, foreign_transition = _context(
        valid.artifacts.expected_artifacts,
        phase=MigrationPhase.EXPORT_STARTED,
        lock_transition_type="BLOCKED",
    )
    foreign_head = AuthenticatedLockHeadProjection.from_authenticated_transition(
        foreign_transition
    )
    assert derive_migration_preflight(
        replace(valid, lock_head=foreign_head)
    ).mode is MigrationPreflightMode.BLOCKED


@pytest.mark.parametrize(
    "phase",
    [
        MigrationPhase.SWAP_PREPARED,
        MigrationPhase.SWAP_STARTED,
        MigrationPhase.SWAP_COMPLETED,
        MigrationPhase.POST_SWAP_VERIFIED,
        MigrationPhase.FAILED,
        MigrationPhase.BLOCKED,
    ],
)
def test_reserved_or_terminal_error_phase_blocks(phase: MigrationPhase) -> None:
    decision = derive_migration_preflight(_projection(phase))
    assert decision.mode is MigrationPreflightMode.BLOCKED
    assert decision.error_code == "migration_preflight_phase_blocked"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("installation_id", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        ("database_context_id", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        ("migration_id", "cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        ("migration_generation", 2),
        ("dmk_key_id", "dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
        ("dmk_key_generation", 2),
        ("database_key_id", "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"),
        ("database_key_generation", 2),
        ("envelope_registry_sha256", "d" * 64),
        ("envelope_registry_revision", 2),
        ("journal_sha256", "e" * 64),
        ("journal_revision", 3),
        ("journal_phase", "export_completed"),
        ("anchor_revision", 4),
        ("replay_anchor_sha256", "d" * 64),
        ("lock_transition_sha256", "f" * 64),
        ("lock_transition_sequence", 5),
        ("lock_transition_type", "STALE_DETECTED"),
        ("lock_owner_before_sha256", "d" * 64),
        ("lock_owner_after_sha256", "e" * 64),
        ("expected_sqlite_version", "3.51.0"),
        ("expected_sqlcipher_version", "4.18.0"),
        ("expected_schema_version", 8),
    ],
)
def test_any_foreign_crossbinding_component_blocks(field: str, value: object) -> None:
    projection = _projection(MigrationPhase.EXPORT_STARTED)
    assert projection.authenticated_context is not None
    foreign = replace(projection.authenticated_context, **{field: value})

    decision = derive_migration_preflight(
        replace(projection, authenticated_context=foreign)
    )
    assert decision.mode is MigrationPreflightMode.BLOCKED
    assert decision.error_code == "migration_crossbinding_mismatch"


def test_missing_extra_and_swapped_artifacts_block() -> None:
    valid = _projection(MigrationPhase.EXPORT_STARTED)
    missing_target = replace(
        valid,
        artifacts=replace(
            valid.artifacts,
            observed_artifacts=_artifacts(True, True, False),
        ),
    )
    extra = replace(
        valid,
        artifacts=replace(
            valid.artifacts, unexpected_artifacts=("unexpected.sqlite",)
        ),
    )
    swapped_source = replace(
        valid,
        artifacts=replace(
            valid.artifacts,
            observed_artifacts=(
                replace(valid.artifacts.observed_artifacts[0], identity_value="1:999"),
                *valid.artifacts.observed_artifacts[1:],
            ),
        ),
    )

    for projection in (missing_target, extra, swapped_source):
        assert derive_migration_preflight(projection).mode is MigrationPreflightMode.BLOCKED


def test_missing_or_invalid_authenticated_state_blocks() -> None:
    valid = _projection(MigrationPhase.EXPORT_STARTED)
    absence = AuthenticatedSourceAbsence(
        source="anchor",
        installation_id=valid.artifacts.installation_id,
        database_context_id=valid.artifacts.database_context_id,
        proof_sha256="a" * 64,
    )
    assert derive_migration_preflight(
        replace(valid, replay_anchor=absence)
    ).mode is MigrationPreflightMode.BLOCKED
    assert derive_migration_preflight(
        replace(valid, authenticated_context=None)
    ).mode is MigrationPreflightMode.BLOCKED


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("observed_sqlite_version", "3.51.0"),
        ("observed_sqlcipher_version", "4.18.0"),
        ("observed_schema_version", 8),
    ],
)
def test_engine_or_schema_version_mismatch_blocks(field: str, value: object) -> None:
    decision = derive_migration_preflight(
        replace(_projection(MigrationPhase.EXPORT_STARTED), **{field: value})
    )
    assert decision.mode is MigrationPreflightMode.BLOCKED
    assert decision.error_code == "migration_preflight_version_mismatch"


def test_new_requires_all_security_state_and_backup_target_roles_free() -> None:
    new = _projection(None, artifacts=_artifacts(True, False, False), new=True)
    occupied = replace(
        new,
        artifacts=AuthenticatedArtifactProjection.create(
            installation_id=new.artifacts.installation_id,
            database_context_id=new.artifacts.database_context_id,
            migration_id=None,
            expected_artifacts=_artifacts(True, True, False),
            observed_artifacts=_artifacts(True, True, False),
            unexpected_artifacts=(),
        ),
    )
    old_anchor = replace(
        new,
        replay_anchor=_projection(MigrationPhase.EXPORT_STARTED).replay_anchor,
    )

    assert derive_migration_preflight(new).mode is MigrationPreflightMode.NEW
    assert (
        derive_migration_preflight(occupied).error_code
        == "migration_preflight_new_roles_not_free"
    )
    assert (
        derive_migration_preflight(old_anchor).error_code
        == "migration_preflight_new_state_invalid"
    )


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("installation_id", "not-an-installation-uuid"),
        ("database_context_id", "not-a-database-context-uuid"),
    ),
)
def test_new_rejects_malformed_binding_identifiers(
    field: str, invalid: str
) -> None:
    valid = _projection(None, artifacts=_artifacts(True, False, False), new=True)
    identity = {
        "installation_id": valid.artifacts.installation_id,
        "database_context_id": valid.artifacts.database_context_id,
    }
    identity[field] = invalid
    sources = tuple(
        AuthenticatedSourceAbsence.create(source=source, **identity)
        for source in ("anchor", "envelope_registry", "journal", "lock_chain")
    )
    malformed = replace(
        valid,
        replay_anchor=sources[0],
        envelope_registry=sources[1],
        journal=sources[2],
        lock_head=sources[3],
        artifacts=AuthenticatedArtifactProjection.create(
            migration_id=None,
            expected_artifacts=valid.artifacts.expected_artifacts,
            observed_artifacts=valid.artifacts.observed_artifacts,
            unexpected_artifacts=(),
            **identity,
        ),
    )

    decision = derive_migration_preflight(malformed)

    assert decision.mode is MigrationPreflightMode.BLOCKED
    assert decision.error_code == "migration_preflight_projection_invalid"


def test_new_rejects_equal_but_malformed_engine_versions() -> None:
    new = _projection(None, artifacts=_artifacts(True, False, False), new=True)
    malformed = replace(
        new,
        expected_sqlcipher_version="current",
        observed_sqlcipher_version="current",
    )
    decision = derive_migration_preflight(malformed)
    assert decision.mode is MigrationPreflightMode.BLOCKED
    assert decision.error_code == "migration_preflight_projection_invalid"


def test_derivation_is_repeatable_and_malformed_input_blocks_instead_of_raising() -> None:
    projection = _projection(MigrationPhase.EXPORT_STARTED)
    decisions = tuple(derive_migration_preflight(projection) for _ in range(10))
    assert len(set(decisions)) == 1
    assert derive_migration_preflight(object()).mode is MigrationPreflightMode.BLOCKED
