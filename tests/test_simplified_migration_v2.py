from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from src.security.simplified_migration import (
    EMPTY_SHA256,
    SIMPLIFIED_MIGRATION_CROSSBINDING_VERSION,
    SimplifiedMigrationArtifactV2,
    SimplifiedMigrationCrossbindingV2,
    SimplifiedMigrationError,
    SimplifiedMigrationPreflightEvidenceV2,
    SimplifiedMigrationPreflightMode,
    SimplifiedMigrationRecoveryDecision,
    absent_simplified_artifact,
    capture_simplified_artifact,
    derive_simplified_migration_preflight_v2,
    derive_simplified_recovery_decision,
    private_root_digest,
)


def _id() -> str:
    return str(uuid4())


def _context(tmp_path: Path, *, phase: str = "not_started", backup=False, target=False):
    source_path = tmp_path / "synthetic-source.sqlite"
    source_path.write_bytes(b"source")
    if backup:
        (tmp_path / "migration-safety-copy.sqlite").write_bytes(b"backup")
    if target:
        (tmp_path / "migration-target.sqlcipher").write_bytes(b"target")
    return SimplifiedMigrationCrossbindingV2(
        context_version=SIMPLIFIED_MIGRATION_CROSSBINDING_VERSION,
        installation_id=_id(),
        database_context_id=_id(),
        migration_id=_id(),
        migration_generation=1,
        dmk_key_id=_id(),
        dmk_key_generation=1,
        database_key_id=_id(),
        database_key_generation=1,
        envelope_registry_sha256=hashlib.sha256(b"registry").hexdigest(),
        journal_sha256=EMPTY_SHA256,
        journal_revision=0,
        journal_phase=phase,
        replay_anchor_revision=0,
        lock_chain_head_sha256=hashlib.sha256(b"lock").hexdigest(),
        private_root_sha256=private_root_digest(tmp_path),
        artifacts=(
            capture_simplified_artifact(
                tmp_path, role="source", relative_path=source_path.name
            ),
            (
                capture_simplified_artifact(
                    tmp_path,
                    role="backup",
                    relative_path="migration-safety-copy.sqlite",
                )
                if backup
                else absent_simplified_artifact(
                    role="backup", relative_path="migration-safety-copy.sqlite"
                )
            ),
            (
                capture_simplified_artifact(
                    tmp_path,
                    role="target",
                    relative_path="migration-target.sqlcipher",
                )
                if target
                else absent_simplified_artifact(
                    role="target", relative_path="migration-target.sqlcipher"
                )
            ),
        ),
        expected_sqlite_version="3.53.0",
        expected_sqlcipher_version="4.12.0 community",
        expected_schema_version=1,
    )


def _evidence(context: SimplifiedMigrationCrossbindingV2, **changes):
    values = dict(
        context=context,
        root_approved=True,
        fixed_paths_match=True,
        single_instance=True,
        source_closed=True,
        wal_shm_quiet=True,
        source_integrity_ok=True,
        roles_match_phase=True,
        disk_space_ok=True,
        permissions_ok=True,
        sqlcipher_available=True,
        sqlcipher_version_matches=True,
        envelope_authenticated=True,
        journal_authenticated=True,
        anchor_authenticated=True,
        lock_authenticated=True,
        crossbinding_authenticated=True,
        unexpected_artifacts=(),
    )
    values.update(changes)
    return SimplifiedMigrationPreflightEvidenceV2(**values)


def test_crossbinding_v2_is_canonical_and_contains_no_vfs_fields(tmp_path: Path):
    context = _context(tmp_path)
    encoded = context.to_bytes()
    assert context.digest_sha256() == hashlib.sha256(encoded).hexdigest()
    assert b"capability" not in encoded.lower()
    assert b"descriptor" not in encoded.lower()
    assert b"vfs" not in encoded.lower()
    assert b"super_journal" not in encoded.lower()
    assert b"synthetic-source.sqlite" in encoded


@pytest.mark.parametrize("invalid", ["../source.sqlite", "/tmp/source.sqlite", "a//b"])
def test_crossbinding_rejects_non_normalized_or_escaping_paths(invalid: str):
    with pytest.raises(SimplifiedMigrationError):
        SimplifiedMigrationArtifactV2(
            "source", invalid, False, None, None, None, None
        )


def test_crossbinding_rejects_unknown_version_and_wrong_role_order(tmp_path: Path):
    context = _context(tmp_path)
    with pytest.raises(SimplifiedMigrationError):
        replace(context, context_version=1)
    with pytest.raises(SimplifiedMigrationError):
        replace(context, artifacts=tuple(reversed(context.artifacts)))


@pytest.mark.parametrize(
    ("phase", "backup", "target", "expected"),
    [
        ("not_started", False, False, SimplifiedMigrationPreflightMode.NEW),
        ("source_verified", False, False, SimplifiedMigrationPreflightMode.RESUME),
        ("backup_started", False, False, SimplifiedMigrationPreflightMode.RECOVERY),
        ("backup_verified", True, False, SimplifiedMigrationPreflightMode.RESUME),
        ("export_started", True, True, SimplifiedMigrationPreflightMode.RECOVERY),
        ("validation_completed", True, True, SimplifiedMigrationPreflightMode.RESUME),
        ("completed", True, True, SimplifiedMigrationPreflightMode.COMPLETED),
    ],
)
def test_preflight_v2_derives_modes(
    tmp_path: Path, phase: str, backup: bool, target: bool, expected
):
    context = _context(tmp_path, phase=phase, backup=backup, target=target)
    assert derive_simplified_migration_preflight_v2(_evidence(context)) is expected


@pytest.mark.parametrize(
    "field",
    [
        "root_approved",
        "fixed_paths_match",
        "single_instance",
        "source_closed",
        "wal_shm_quiet",
        "source_integrity_ok",
        "roles_match_phase",
        "disk_space_ok",
        "permissions_ok",
        "sqlcipher_available",
        "sqlcipher_version_matches",
        "envelope_authenticated",
        "journal_authenticated",
        "anchor_authenticated",
        "lock_authenticated",
        "crossbinding_authenticated",
    ],
)
def test_every_preflight_contradiction_blocks(tmp_path: Path, field: str):
    context = _context(tmp_path)
    assert derive_simplified_migration_preflight_v2(
        _evidence(context, **{field: False})
    ) is SimplifiedMigrationPreflightMode.BLOCKED


def test_unexpected_artifact_blocks_without_mutation(tmp_path: Path):
    context = _context(tmp_path)
    foreign = tmp_path / "foreign.bin"
    foreign.write_bytes(b"do not mutate")
    before = foreign.read_bytes()
    result = derive_simplified_migration_preflight_v2(
        _evidence(context, unexpected_artifacts=(foreign.name,))
    )
    assert result is SimplifiedMigrationPreflightMode.BLOCKED
    assert foreign.read_bytes() == before


def test_recovery_decisions_are_phase_allowlisted(tmp_path: Path):
    started = _context(tmp_path, phase="target_created", backup=True, target=True)
    assert derive_simplified_recovery_decision(
        _evidence(started)
    ) is SimplifiedMigrationRecoveryDecision.QUARANTINE_TARGET

    tmp_path_2 = tmp_path / "next"
    tmp_path_2.mkdir()
    validation = _context(
        tmp_path_2, phase="validation_started", backup=True, target=True
    )
    assert derive_simplified_recovery_decision(
        _evidence(validation)
    ) is SimplifiedMigrationRecoveryDecision.REPEAT_VALIDATION


def test_capture_rejects_symlink(tmp_path: Path):
    real = tmp_path / "real.sqlite"
    real.write_bytes(b"data")
    link = tmp_path / "synthetic-source.sqlite"
    link.symlink_to(real)
    with pytest.raises(SimplifiedMigrationError):
        capture_simplified_artifact(
            tmp_path, role="source", relative_path=link.name
        )
