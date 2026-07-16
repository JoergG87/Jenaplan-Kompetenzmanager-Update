"""Focused tests for the SQLite database compatibility contract."""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from unittest import mock

import pytest

import src.core.database_compatibility as compatibility_module
from src.core.database_compatibility import (
    DATABASE_COMPATIBILITY_VERSION,
    KNOWN_UNVERSIONED_V1_PREDECESSOR_FINGERPRINT,
    V1_COMPATIBILITY_FINGERPRINT,
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityPolicy,
    DatabaseCompatibilityStatus,
    DatabaseVersionMismatchError,
    UnknownDatabaseSchemaError,
    UnsupportedDatabaseVersionError,
)
from src.core.sqlite_store import SQLiteDatabase


def _v1_database(path: Path) -> Path:
    SQLiteDatabase(path).initialize_schema()
    return path


def _user_version(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _set_user_version(path: Path, value: int) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(f"PRAGMA user_version = {value}")


def test_new_empty_database_receives_user_version_one(tmp_path: Path) -> None:
    database = _v1_database(tmp_path / "new.sqlite")
    assert _user_version(database) == DATABASE_COMPATIBILITY_VERSION == 1


def test_existing_unversioned_database_remains_unversioned(tmp_path: Path) -> None:
    database = _v1_database(tmp_path / "existing.sqlite")
    _set_user_version(database, 0)
    before = database.read_bytes()
    SQLiteDatabase(database).initialize_schema()
    assert _user_version(database) == 0
    assert database.read_bytes() == before


def test_schema_and_user_version_are_rolled_back_together(tmp_path: Path) -> None:
    database = tmp_path / "rollback.sqlite"
    with mock.patch.object(
        SQLiteDatabase,
        "_backfill_course_colors",
        side_effect=RuntimeError("simulierter Schemafehler"),
    ):
        with pytest.raises(RuntimeError, match="Schemafehler"):
            SQLiteDatabase(database).initialize_schema()
    with sqlite3.connect(database) as connection:
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
        objects = connection.execute(
            "SELECT name FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
    assert user_version == 0
    assert objects == []


def test_exact_v1_is_accepted(tmp_path: Path) -> None:
    result = DatabaseCompatibilityInspector().inspect(
        _v1_database(tmp_path / "exact.sqlite")
    )
    assert result.status is DatabaseCompatibilityStatus.EXACT
    assert result.version.compatibility_version == 1
    assert result.schema_identity.fingerprint == V1_COMPATIBILITY_FINGERPRINT


def test_known_unversioned_predecessor_requires_migration(tmp_path: Path) -> None:
    database = _v1_database(tmp_path / "predecessor.sqlite")
    _set_user_version(database, 0)
    result = DatabaseCompatibilityInspector().inspect(database)
    assert result.status is DatabaseCompatibilityStatus.MIGRATION_REQUIRED
    assert result.schema_identity.fingerprint == (
        KNOWN_UNVERSIONED_V1_PREDECESSOR_FINGERPRINT
    )


@pytest.mark.parametrize("user_version", (0, 1))
def test_unknown_v0_and_v1_schema_are_incompatible(
    tmp_path: Path,
    user_version: int,
) -> None:
    database = _v1_database(tmp_path / f"unknown-{user_version}.sqlite")
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE unknown_extension (value TEXT)")
        connection.execute(f"PRAGMA user_version = {user_version}")
    result = DatabaseCompatibilityInspector().inspect(database)
    assert result.status is DatabaseCompatibilityStatus.INCOMPATIBLE
    error = (
        UnknownDatabaseSchemaError
        if user_version == 0
        else DatabaseVersionMismatchError
    )
    with pytest.raises(error):
        DatabaseCompatibilityPolicy.require_backup_compatible(result)


def test_newer_database_version_is_incompatible(tmp_path: Path) -> None:
    database = _v1_database(tmp_path / "newer.sqlite")
    _set_user_version(database, 2)
    result = DatabaseCompatibilityInspector().inspect(database)
    assert result.status is DatabaseCompatibilityStatus.INCOMPATIBLE
    with pytest.raises(UnsupportedDatabaseVersionError, match="neuer"):
        DatabaseCompatibilityPolicy.require_backup_compatible(result)


def test_app_version_does_not_influence_database_compatibility(
    tmp_path: Path,
) -> None:
    database = _v1_database(tmp_path / "independent.sqlite")
    before = DatabaseCompatibilityInspector().inspect(database)
    application_versions = ("0.1.2", "99.42.7", "unknown")
    after = tuple(DatabaseCompatibilityInspector().inspect(database) for _ in application_versions)
    assert all(result == before for result in after)


@pytest.mark.parametrize(
    ("first_sql", "second_sql"),
    (
        (
            "CREATE TABLE items (value INTEGER CHECK (value > 0))",
            "CREATE TABLE items (value INTEGER CHECK (value >= 0))",
        ),
        (
            "CREATE TABLE items (value TEXT); "
            "CREATE TRIGGER trg_items AFTER INSERT ON items BEGIN "
            "UPDATE items SET value = upper(value); END",
            "CREATE TABLE items (value TEXT); "
            "CREATE TRIGGER trg_items AFTER INSERT ON items BEGIN "
            "UPDATE items SET value = lower(value); END",
        ),
        (
            "CREATE TABLE items (value TEXT); "
            "CREATE VIEW visible_items AS SELECT value FROM items",
            "CREATE TABLE items (value TEXT); "
            "CREATE VIEW visible_items AS SELECT value FROM items WHERE value <> ''",
        ),
        (
            "CREATE TABLE items (value INTEGER NOT NULL DEFAULT 1)",
            "CREATE TABLE items (value INTEGER NOT NULL DEFAULT 2)",
        ),
        (
            "CREATE TABLE items (item_id TEXT, active INTEGER); "
            "CREATE INDEX idx_items_active ON items(item_id) WHERE active = 1",
            "CREATE TABLE items (item_id TEXT, active INTEGER); "
            "CREATE INDEX idx_items_active ON items(item_id) WHERE active = 0",
        ),
    ),
)
def test_compatibility_fingerprint_detects_schema_details(
    tmp_path: Path,
    first_sql: str,
    second_sql: str,
) -> None:
    fingerprints: list[str] = []
    for index, schema_sql in enumerate((first_sql, second_sql)):
        database = tmp_path / f"detail-{index}.sqlite"
        with sqlite3.connect(database) as connection:
            connection.executescript(schema_sql)
        fingerprints.append(
            DatabaseCompatibilityInspector.schema_identity(database).fingerprint
        )
    assert fingerprints[0] != fingerprints[1]


def test_identical_schema_has_identical_fingerprint(tmp_path: Path) -> None:
    fingerprints: list[str] = []
    for index in range(2):
        database = tmp_path / f"same-{index}.sqlite"
        with sqlite3.connect(database) as connection:
            connection.executescript(
                "CREATE TABLE parent (id TEXT PRIMARY KEY);"
                "CREATE TABLE child (id TEXT PRIMARY KEY, parent_id TEXT NOT NULL, "
                "FOREIGN KEY (parent_id) REFERENCES parent(id));"
                "CREATE INDEX idx_child_parent ON child(parent_id);"
            )
        fingerprints.append(
            DatabaseCompatibilityInspector.schema_identity(database).fingerprint
        )
    assert fingerprints[0] == fingerprints[1]


def test_sqlite_internal_structures_and_sequence_values_are_excluded(
    tmp_path: Path,
) -> None:
    database = tmp_path / "internal.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            "CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE);"
            "INSERT INTO items (code) VALUES ('one');"
        )
        before_structure = compatibility_module._compatibility_schema(connection)
        before = DatabaseCompatibilityInspector.schema_identity(database).fingerprint
        connection.execute("INSERT INTO items (code) VALUES ('two')")
        connection.execute("DELETE FROM items")
    after = DatabaseCompatibilityInspector.schema_identity(database).fingerprint
    canonical = json.dumps(before_structure, sort_keys=True)
    assert before == after
    assert "sqlite_sequence" not in canonical
    assert "sqlite_autoindex" not in canonical


def test_known_pilot_database_user_version_is_not_changed(tmp_path: Path) -> None:
    source = Path("data/kompetenzmanager.sqlite")
    if not source.is_file():
        pytest.skip("Keine lokale Pilotdatenbank vorhanden.")
    copied = tmp_path / source.name
    shutil.copy2(source, copied)
    before = _user_version(copied)
    before_bytes = copied.read_bytes()
    SQLiteDatabase(copied).initialize_schema()
    after = _user_version(copied)
    assert before == after == 0
    assert copied.read_bytes() == before_bytes
