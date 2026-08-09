"""Tests for the single final-schema compatibility policy."""

from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from src.core.database_compatibility import (
    FINAL_SCHEMA_FINGERPRINT,
    FINAL_SCHEMA_VERSION,
    DatabaseCompatibilityError,
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityPolicy,
    DatabaseCompatibilityStatus,
    DatabaseSchemaIdentity,
    DatabaseVersionMismatchError,
    UnknownDatabaseSchemaError,
    UnsupportedDatabaseVersionError,
)
from src.core.final_v4_schema import FinalV4SchemaInitializer


HISTORICAL_FINAL_V3_FINGERPRINT = (
    "d75b803552ba961bff5578ec0853c1d0a2d035845db6a7b624b1528cf546e731"
)


def test_exact_final_schema_is_the_only_compatible_database(
    tmp_path: Path,
) -> None:
    path = tmp_path / "final.sqlite"
    FinalV4SchemaInitializer().initialize(path)

    result = DatabaseCompatibilityInspector().inspect(path)

    assert result.status is DatabaseCompatibilityStatus.EXACT
    assert result.version.sqlite_user_version == FINAL_SCHEMA_VERSION == 4
    assert result.version.compatibility_version == FINAL_SCHEMA_VERSION
    assert result.schema_identity.fingerprint == FINAL_SCHEMA_FINGERPRINT
    assert DatabaseCompatibilityPolicy.require_backup_compatible(result) is result


def test_unknown_development_schema_is_not_product_compatible(
    tmp_path: Path,
) -> None:
    path = tmp_path / "unknown-development.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE legacy_student(value TEXT)")
        connection.execute("PRAGMA user_version = 2")

    result = DatabaseCompatibilityInspector().inspect(path)

    assert result.status is DatabaseCompatibilityStatus.INCOMPATIBLE
    assert result.version.compatibility_version is None
    with pytest.raises(UnknownDatabaseSchemaError):
        DatabaseCompatibilityPolicy.require_backup_compatible(result)


def test_historical_exact_v3_identity_is_rejected_without_migration() -> None:
    result = DatabaseCompatibilityPolicy().evaluate(
        sqlite_user_version=3,
        schema_identity=DatabaseSchemaIdentity(
            HISTORICAL_FINAL_V3_FINGERPRINT,
            95,
        ),
    )

    assert result.status is DatabaseCompatibilityStatus.INCOMPATIBLE
    assert result.version.compatibility_version is None
    with pytest.raises(UnknownDatabaseSchemaError):
        DatabaseCompatibilityPolicy.require_backup_compatible(result)


def test_v3_file_is_rejected_without_mutation_or_sidecars(tmp_path: Path) -> None:
    path = tmp_path / "historical-v3.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE historical_v3(value TEXT)")
        connection.execute("PRAGMA user_version = 3")
    before = path.read_bytes()

    result = DatabaseCompatibilityInspector().inspect(path)

    assert result.status is DatabaseCompatibilityStatus.INCOMPATIBLE
    assert result.version.sqlite_user_version == 3
    assert path.read_bytes() == before
    assert not Path(f"{path}-wal").exists()
    assert not Path(f"{path}-shm").exists()


def test_same_version_with_unknown_schema_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "unknown.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE unexpected(value TEXT)")
        connection.execute(f"PRAGMA user_version = {FINAL_SCHEMA_VERSION}")

    result = DatabaseCompatibilityInspector().inspect(path)

    assert result.status is DatabaseCompatibilityStatus.INCOMPATIBLE
    with pytest.raises(DatabaseVersionMismatchError):
        DatabaseCompatibilityPolicy.require_backup_compatible(result)


def test_future_version_is_rejected() -> None:
    identity = DatabaseSchemaIdentity("f" * 64, 1)
    result = DatabaseCompatibilityPolicy().evaluate(
        sqlite_user_version=FINAL_SCHEMA_VERSION + 1,
        schema_identity=identity,
    )

    with pytest.raises(UnsupportedDatabaseVersionError):
        DatabaseCompatibilityPolicy.require_backup_compatible(result)


def test_unversioned_unknown_schema_is_rejected() -> None:
    result = DatabaseCompatibilityPolicy().evaluate(
        sqlite_user_version=0,
        schema_identity=DatabaseSchemaIdentity("e" * 64, 1),
    )

    assert result.status is DatabaseCompatibilityStatus.INCOMPATIBLE
    with pytest.raises(UnknownDatabaseSchemaError):
        DatabaseCompatibilityPolicy.require_backup_compatible(result)


def test_inspector_is_read_only(tmp_path: Path) -> None:
    path = tmp_path / "readonly.sqlite"
    FinalV4SchemaInitializer().initialize(path)
    before = path.read_bytes()

    DatabaseCompatibilityInspector().inspect(path)

    assert path.read_bytes() == before
    assert not Path(f"{path}-wal").exists()
    assert not Path(f"{path}-shm").exists()


def test_missing_database_raises_controlled_error(tmp_path: Path) -> None:
    with pytest.raises(DatabaseCompatibilityError):
        DatabaseCompatibilityInspector().inspect(tmp_path / "missing.sqlite")
