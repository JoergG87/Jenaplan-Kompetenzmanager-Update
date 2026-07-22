from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from src.security.migration_context import (
    MIGRATION_CROSSBINDING_VERSION,
    MigrationArtifactBinding,
    MigrationCrossbindingContext,
    MigrationCrossbindingError,
    require_matching_migration_contexts,
)


INSTALLATION_ID = "11111111-1111-4111-8111-111111111111"
DATABASE_CONTEXT_ID = "22222222-2222-4222-8222-222222222222"
MIGRATION_ID = "33333333-3333-4333-8333-333333333333"
DMK_ID = "44444444-4444-4444-8444-444444444444"
DATABASE_KEY_ID = "55555555-5555-4555-8555-555555555555"


def _artifact(role: str, index: int, *, present: bool = True) -> MigrationArtifactBinding:
    return MigrationArtifactBinding(
        role=role,
        capability_id=f"{index:08d}-0000-4000-8000-{index:012d}",
        relative_name=f"{role}.sqlite",
        present=present,
        identity_scheme="posix-inode" if present else None,
        identity_value=f"17:{100 + index}" if present else None,
        size_bytes=1024 * index if present else None,
        sha256=f"{index:x}" * 64 if present else None,
    )


def _context(
    *, artifacts: tuple[MigrationArtifactBinding, ...] | None = None
) -> MigrationCrossbindingContext:
    return MigrationCrossbindingContext(
        context_version=MIGRATION_CROSSBINDING_VERSION,
        installation_id=INSTALLATION_ID,
        database_context_id=DATABASE_CONTEXT_ID,
        migration_id=MIGRATION_ID,
        migration_generation=1,
        dmk_key_id=DMK_ID,
        dmk_key_generation=2,
        database_key_id=DATABASE_KEY_ID,
        database_key_generation=3,
        envelope_registry_sha256="a" * 64,
        envelope_registry_revision=4,
        journal_sha256="b" * 64,
        journal_revision=5,
        journal_phase="export_started",
        anchor_revision=6,
        replay_anchor_sha256="6" * 64,
        lock_transition_sha256="c" * 64,
        lock_transition_sequence=7,
        lock_transition_type="RELEASED",
        lock_owner_before_sha256="7" * 64,
        lock_owner_after_sha256="8" * 64,
        artifacts=artifacts
        or (
            _artifact("source", 1),
            _artifact("backup", 2),
            _artifact("target", 3),
        ),
        expected_sqlite_version="3.50.4",
        expected_sqlcipher_version="4.17.0",
        expected_schema_version=7,
    )


def test_context_is_canonical_immutable_and_deterministic() -> None:
    first = _context()
    second = _context()

    assert first == second
    assert first.to_bytes() == second.to_bytes()
    assert first.digest_sha256() == hashlib.sha256(first.to_bytes()).hexdigest()
    assert first.to_bytes().startswith(b'{"anchor_revision":6,"artifacts":[')
    with pytest.raises(Exception):
        first.anchor_revision = 8


def test_lock_binding_digest_is_non_circular_but_full_digest_binds_lock_head() -> None:
    context = _context()
    changed_lock = replace(
        context,
        lock_transition_sha256="d" * 64,
        lock_transition_sequence=8,
        lock_transition_type="STALE_DETECTED",
        lock_owner_after_sha256="9" * 64,
    )
    changed_non_lock = replace(context, database_key_generation=4)

    assert (
        changed_lock.lock_binding_digest_sha256()
        == context.lock_binding_digest_sha256()
    )
    assert changed_lock.digest_sha256() != context.digest_sha256()
    assert (
        changed_non_lock.lock_binding_digest_sha256()
        != context.lock_binding_digest_sha256()
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("installation_id", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        ("database_context_id", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        ("migration_id", "cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        ("migration_generation", 2),
        ("dmk_key_id", "dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
        ("dmk_key_generation", 3),
        ("database_key_id", "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"),
        ("database_key_generation", 4),
        ("envelope_registry_sha256", "d" * 64),
        ("envelope_registry_revision", 5),
        ("journal_sha256", "e" * 64),
        ("journal_revision", 6),
        ("journal_phase", "export_completed"),
        ("anchor_revision", 7),
        ("replay_anchor_sha256", "9" * 64),
        ("lock_transition_sha256", "f" * 64),
        ("lock_transition_sequence", 8),
        ("lock_transition_type", "STALE_DETECTED"),
        ("lock_owner_before_sha256", "9" * 64),
        ("lock_owner_after_sha256", "9" * 64),
        ("expected_sqlite_version", "3.51.0"),
        ("expected_sqlcipher_version", "4.18.0"),
        ("expected_schema_version", 8),
    ],
)
def test_each_scalar_crossbinding_change_is_rejected(
    field: str, replacement: object
) -> None:
    expected = _context()
    observed = replace(expected, **{field: replacement})

    with pytest.raises(MigrationCrossbindingError) as caught:
        require_matching_migration_contexts(expected, observed)
    assert caught.value.code == "migration_crossbinding_mismatch"


def test_each_artifact_identity_capability_presence_and_path_is_bound() -> None:
    expected = _context()
    source = expected.artifacts[0]
    mutations = (
        replace(
            source,
            capability_id="99999999-9999-4999-8999-999999999999",
        ),
        replace(source, relative_name="alternate.sqlite"),
        replace(source, identity_value="17:999"),
        replace(source, size_bytes=source.size_bytes + 1),
        replace(source, sha256="f" * 64),
        _artifact("source", 1, present=False),
    )

    for replacement_source in mutations:
        observed = replace(
            expected,
            artifacts=(replacement_source, *expected.artifacts[1:]),
        )
        with pytest.raises(MigrationCrossbindingError, match="mismatch"):
            require_matching_migration_contexts(expected, observed)


@pytest.mark.parametrize(
    "artifacts",
    [
        (_artifact("source", 1), _artifact("backup", 2)),
        (
            _artifact("backup", 2),
            _artifact("source", 1),
            _artifact("target", 3),
        ),
        (
            _artifact("source", 1),
            _artifact("backup", 1),
            _artifact("target", 3),
        ),
        (
            _artifact("source", 1),
            replace(_artifact("backup", 2), relative_name="source.sqlite"),
            _artifact("target", 3),
        ),
    ],
)
def test_missing_reordered_or_duplicate_artifact_bindings_are_rejected(
    artifacts: tuple[MigrationArtifactBinding, ...]
) -> None:
    with pytest.raises(MigrationCrossbindingError, match="artifacts_invalid"):
        _context(artifacts=artifacts)


def test_absent_artifact_cannot_carry_stale_identity_evidence() -> None:
    with pytest.raises(MigrationCrossbindingError) as caught:
        replace(_artifact("target", 3, present=False), sha256="a" * 64)
    assert caught.value.code == "migration_artifact_absence_invalid"


def test_duplicate_present_platform_identity_is_rejected() -> None:
    source = _artifact("source", 1)
    backup = replace(
        _artifact("backup", 2),
        identity_scheme=source.identity_scheme,
        identity_value=source.identity_value,
    )
    with pytest.raises(MigrationCrossbindingError, match="artifacts_invalid"):
        _context(artifacts=(source, backup, _artifact("target", 3)))


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("context_version", 2, "migration_crossbinding_version_unsupported"),
        ("migration_id", "not-a-uuid", "migration_crossbinding_identifier_invalid"),
        ("journal_sha256", "A" * 64, "migration_crossbinding_digest_invalid"),
        ("anchor_revision", 0, "migration_crossbinding_revision_invalid"),
        (
            "expected_sqlcipher_version",
            "SQLCipher current",
            "migration_crossbinding_engine_version_invalid",
        ),
        (
            "expected_schema_version",
            0,
            "migration_crossbinding_schema_version_invalid",
        ),
    ],
)
def test_malformed_context_fields_fail_closed(
    field: str, value: object, code: str
) -> None:
    with pytest.raises(MigrationCrossbindingError) as caught:
        replace(_context(), **{field: value})
    assert caught.value.code == code
