from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from src.security.database_keys import DerivedDomainKey
from src.security.infrastructure.simplified_migration_state import (
    AuthenticatedMigrationJournalV2Repository,
    AuthenticatedMigrationJournalV2State,
    ExternalReplayAnchorV2Repository,
    ExternalReplayAnchorV2State,
)
from src.security.simplified_migration import (
    EMPTY_SHA256,
    SimplifiedMigrationArtifactV2,
    SimplifiedMigrationError,
    absent_simplified_artifact,
)


def _key(value: int = 1) -> DerivedDomainKey:
    return DerivedDomainKey(
        "jenaplan-kompetenzmanager/migration-state-test/v2", 2, bytes([value]) * 32
    )


def _state() -> AuthenticatedMigrationJournalV2State:
    source = SimplifiedMigrationArtifactV2(
        "source", "synthetic-source.sqlite", True, 1, 2, 6, hashlib.sha256(b"source").hexdigest()
    )
    return AuthenticatedMigrationJournalV2State(
        journal_version=2,
        installation_id=str(uuid4()),
        database_context_id=str(uuid4()),
        migration_id=str(uuid4()),
        migration_generation=1,
        dmk_key_id=str(uuid4()),
        dmk_key_generation=1,
        database_key_id=str(uuid4()),
        database_key_generation=1,
        envelope_registry_sha256=hashlib.sha256(b"registry").hexdigest(),
        revision=0,
        phase="not_started",
        artifacts=(
            source,
            absent_simplified_artifact(
                role="backup", relative_path="migration-safety-copy.sqlite"
            ),
            absent_simplified_artifact(
                role="target", relative_path="migration-target.sqlcipher"
            ),
        ),
        completed_checks=(),
    )


def _anchor(state, digest: str) -> ExternalReplayAnchorV2State:
    return ExternalReplayAnchorV2State(
        anchor_version=2,
        installation_id=state.installation_id,
        database_context_id=state.database_context_id,
        migration_id=state.migration_id,
        migration_generation=state.migration_generation,
        anchor_revision=1,
        envelope_registry_sha256=state.envelope_registry_sha256,
        journal_revision=state.revision,
        journal_sha256=digest,
        lock_chain_head_sha256=hashlib.sha256(b"lock").hexdigest(),
    )


def test_journal_v2_authenticates_canonical_state_and_compare_replace(tmp_path: Path):
    repository = AuthenticatedMigrationJournalV2Repository(tmp_path / "journal.json")
    state = _state()
    digest = repository.create(state, _key())
    observed, observed_digest = repository.load_with_digest(_key())
    assert observed == state
    assert observed_digest == digest

    replacement = replace(
        state, revision=1, phase="preflight_started", completed_checks=("source_identity",)
    )
    replacement_digest = repository.replace(digest, replacement, _key())
    assert repository.load(_key()) == replacement
    assert replacement_digest != digest

    with pytest.raises(SimplifiedMigrationError) as caught:
        repository.replace(digest, state, _key())
    assert caught.value.code == "migration_journal_changed"


def test_journal_v2_rejects_wrong_key_tampering_and_unknown_version(tmp_path: Path):
    path = tmp_path / "journal.json"
    repository = AuthenticatedMigrationJournalV2Repository(path)
    state = _state()
    repository.create(state, _key())
    original = path.read_bytes()

    with pytest.raises(SimplifiedMigrationError):
        repository.load(_key(2))
    path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(SimplifiedMigrationError):
        repository.load(_key())

    path.unlink()
    with pytest.raises(SimplifiedMigrationError) as caught:
        repository.create(replace(state, journal_version=3), _key())
    assert caught.value.code == "migration_journal_version_unsupported"


def test_anchor_v2_prepare_commit_and_abort_resolve_only_old_or_planned(tmp_path: Path):
    state = _state()
    repository = ExternalReplayAnchorV2Repository(tmp_path / "anchor.json")
    committed = _anchor(state, EMPTY_SHA256)
    repository.initialize(committed, _key())
    planned = replace(
        committed,
        anchor_revision=2,
        journal_revision=1,
        journal_sha256=hashlib.sha256(b"journal-v2").hexdigest(),
    )
    prepared = repository.prepare(committed, planned, _key())
    assert repository.read(_key()).pending == planned
    assert repository.abort_pending(prepared, _key()) == committed

    prepared_again = repository.prepare(committed, planned, _key())
    assert repository.commit(prepared_again, planned, _key()) == planned
    assert repository.read(_key()) == planned


def test_failed_atomic_replace_does_not_overwrite_authenticated_journal(tmp_path: Path):
    path = tmp_path / "journal.json"
    baseline = AuthenticatedMigrationJournalV2Repository(path)
    state = _state()
    digest = baseline.create(state, _key())
    before = path.read_bytes()

    def fail_replace(_source, _target):
        raise OSError("simulated")

    failing = AuthenticatedMigrationJournalV2Repository(
        path, replace_file=fail_replace
    )
    with pytest.raises(SimplifiedMigrationError):
        failing.replace(
            digest, replace(state, revision=1, phase="preflight_started"), _key()
        )
    assert path.read_bytes() == before
