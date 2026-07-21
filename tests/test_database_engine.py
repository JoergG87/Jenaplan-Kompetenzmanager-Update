from __future__ import annotations

from contextlib import closing
from pathlib import Path
import secrets
import sqlite3

import pytest

from src.core.database_engine import (
    DEFAULT_DATABASE_ENGINE,
    DatabaseEngine,
    DatabaseEngineConfigurationError,
    SQLiteConnectionProvider,
)
from src.core.sqlite_store import SQLiteDatabase


def test_standard_sqlite_remains_the_explicit_default(tmp_path: Path) -> None:
    assert DEFAULT_DATABASE_ENGINE is DatabaseEngine.SQLITE
    database_path = tmp_path / "ordinary.sqlite"
    database = SQLiteDatabase(database_path)
    with closing(database.connect()) as connection:
        assert isinstance(connection, sqlite3.Connection)
        assert connection.row_factory is sqlite3.Row
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        connection.execute("CREATE TABLE sample(value TEXT NOT NULL)")
        connection.execute("INSERT INTO sample VALUES (?)", ("ordinary",))
        connection.commit()
        assert connection.execute("SELECT value FROM sample").fetchone()["value"] == "ordinary"
    assert database_path.read_bytes().startswith(b"SQLite format 3\x00")


def test_standard_provider_never_accepts_key_material(tmp_path: Path) -> None:
    test_key = secrets.token_bytes(32)
    with pytest.raises(DatabaseEngineConfigurationError) as caught:
        SQLiteConnectionProvider().connect(
            tmp_path / "ordinary.sqlite", create=True, key_material=test_key
        )
    assert caught.value.code == "sqlite_key_not_supported"
