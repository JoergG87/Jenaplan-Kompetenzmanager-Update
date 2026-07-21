from __future__ import annotations

from contextlib import closing
import hashlib
import hmac
import importlib.util
from pathlib import Path
import secrets
import sqlite3
from tempfile import TemporaryDirectory

import pytest

from src.core.database_engine import (
    DatabaseCorruptError,
    DatabaseEngineConfigurationError,
    DatabaseFormatUnsupportedError,
    DatabaseKeyInvalidError,
    DatabaseKeyMissingError,
    DatabaseKeyRejectedError,
    SQLCipherUnavailableError,
    SQLCipherVersionError,
    SQLCipherConnectionProvider,
)
from scripts.smoke_test_sqlcipher_engine import run_smoke


requires_sqlcipher = pytest.mark.skipif(
    importlib.util.find_spec("sqlcipher3") is None,
    reason="isolated real-engine test requires requirements-sqlcipher-spike.txt",
)


def _runtime_key() -> bytearray:
    return bytearray(secrets.token_bytes(32))


def _erase(*values: bytearray) -> None:
    for value in values:
        for index in range(len(value)):
            value[index] = 0


def _digest(path: Path) -> tuple[int, str]:
    content = path.read_bytes()
    return len(content), hashlib.sha256(content).hexdigest()


def _create_database(path: Path, key: bytearray, marker: str) -> None:
    provider = SQLCipherConnectionProvider()
    with closing(provider.connect(path, create=True, key_material=key)) as connection:
        connection.execute("CREATE TABLE sample(value TEXT NOT NULL)")
        connection.execute("INSERT INTO sample VALUES (?)", (marker,))
        connection.commit()


@requires_sqlcipher
def test_encrypted_database_roundtrip_integrity_and_plaintext_rejection() -> None:
    key = _runtime_key()
    marker = f"synthetic-{secrets.token_hex(16)}"
    root: Path | None = None
    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            root = Path(directory)
            database = root / "synthetic.sqlcipher"
            provider = SQLCipherConnectionProvider()
            _create_database(database, key, marker)
            expected_count = 1

            for _ in range(3):
                with closing(
                    provider.connect(database, create=False, key_material=key)
                ) as connection:
                    row = connection.execute(
                        "SELECT value FROM sample"
                    ).fetchone()
                    assert row["value"] == marker
                    assert connection.execute(
                        "SELECT COUNT(*) FROM sample"
                    ).fetchone()[0] == expected_count
                    assert connection.execute("PRAGMA cipher_status").fetchone()[0] == "1"
                    assert connection.execute(
                        "PRAGMA cipher_integrity_check"
                    ).fetchall() == []
                    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

            content = database.read_bytes()
            assert not content.startswith(b"SQLite format 3\x00")
            assert marker.encode("utf-8") not in content
            with closing(
                sqlite3.connect(
                    f"{database.resolve().as_uri()}?mode=ro&immutable=1", uri=True
                )
            ) as plaintext:
                with pytest.raises(sqlite3.DatabaseError):
                    plaintext.execute("SELECT value FROM sample").fetchall()
    finally:
        _erase(key)
    assert root is not None and not root.exists()


@requires_sqlcipher
def test_commit_and_rollback_are_preserved() -> None:
    key = _runtime_key()
    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "transactions.sqlcipher"
            provider = SQLCipherConnectionProvider()
            with closing(
                provider.connect(database, create=True, key_material=key)
            ) as connection:
                connection.execute("CREATE TABLE sample(value TEXT NOT NULL)")
                connection.execute("INSERT INTO sample VALUES (?)", ("committed",))
                connection.commit()
                connection.execute("INSERT INTO sample VALUES (?)", ("rolled-back",))
                connection.rollback()
            with closing(
                provider.connect(database, create=False, key_material=key)
            ) as connection:
                assert [row[0] for row in connection.execute("SELECT value FROM sample")] == [
                    "committed"
                ]
    finally:
        _erase(key)


@pytest.mark.parametrize("key_material", [None, b"", b"short", "not-bytes"])
def test_missing_or_invalid_keys_fail_before_database_creation(key_material) -> None:
    with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
        database = Path(directory) / "must-not-exist.sqlcipher"
        expected = DatabaseKeyMissingError if key_material is None else DatabaseKeyInvalidError
        with pytest.raises(expected) as caught:
            SQLCipherConnectionProvider().connect(
                database, create=True, key_material=key_material
            )
        assert caught.value.code in {"database_key_missing", "database_key_invalid"}
        assert not database.exists()


@requires_sqlcipher
def test_wrong_key_is_sanitized_and_never_changes_the_database(capsys) -> None:
    key = _runtime_key()
    wrong_key = _runtime_key()
    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "wrong-key.sqlcipher"
            _create_database(database, key, "synthetic-wrong-key")
            before = _digest(database)
            with pytest.raises(DatabaseKeyRejectedError) as caught:
                SQLCipherConnectionProvider().connect(
                    database, create=False, key_material=wrong_key
                )
            assert caught.value.code == "database_key_or_header_rejected"
            assert wrong_key.hex() not in str(caught.value)
            assert hmac.compare_digest(str(before), str(_digest(database)))
            assert not Path(f"{database}-wal").exists()
            assert not Path(f"{database}-shm").exists()
            captured = capsys.readouterr()
            for secret in (bytes(key), bytes(wrong_key)):
                assert secret not in database.read_bytes()
                assert secret.hex().encode("ascii") not in database.read_bytes()
                assert secret.hex() not in captured.out
                assert secret.hex() not in captured.err
    finally:
        _erase(key, wrong_key)


def test_plaintext_sqlite_is_rejected_without_modification() -> None:
    key = _runtime_key()
    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "plaintext.sqlite"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE sample(value TEXT)")
                connection.execute("INSERT INTO sample VALUES ('synthetic')")
            before = _digest(database)
            with pytest.raises(DatabaseFormatUnsupportedError) as caught:
                SQLCipherConnectionProvider().connect(
                    database, create=False, key_material=key
                )
            assert caught.value.code == "plaintext_sqlite_not_supported"
            assert before == _digest(database)
    finally:
        _erase(key)


@requires_sqlcipher
def test_truncated_database_is_rejected_without_replacement() -> None:
    key = _runtime_key()
    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "truncated.sqlcipher"
            _create_database(database, key, "synthetic-corruption")
            database.write_bytes(database.read_bytes()[:-1])
            before = _digest(database)
            with pytest.raises(DatabaseCorruptError):
                SQLCipherConnectionProvider().connect(
                    database, create=False, key_material=key
                )
            assert before == _digest(database)
    finally:
        _erase(key)


@requires_sqlcipher
def test_encrypted_header_corruption_is_rejected_with_the_correct_key() -> None:
    key = _runtime_key()
    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "header-corrupt.sqlcipher"
            _create_database(database, key, "synthetic-header-corruption")
            content = bytearray(database.read_bytes())
            content[0] ^= 0x01
            database.write_bytes(content)
            before = _digest(database)
            with pytest.raises(DatabaseKeyRejectedError) as caught:
                SQLCipherConnectionProvider().connect(
                    database, create=False, key_material=key
                )
            assert caught.value.code == "database_key_or_header_rejected"
            assert before == _digest(database)
    finally:
        _erase(key)


@requires_sqlcipher
def test_authenticated_page_corruption_fails_integrity_checks() -> None:
    key = _runtime_key()
    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "page-corrupt.sqlcipher"
            provider = SQLCipherConnectionProvider()
            with closing(
                provider.connect(database, create=True, key_material=key)
            ) as connection:
                connection.execute("CREATE TABLE sample(value TEXT NOT NULL)")
                connection.executemany(
                    "INSERT INTO sample VALUES (?)",
                    ((f"synthetic-{index}-" + "x" * 1000,) for index in range(80)),
                )
                connection.commit()
            content = bytearray(database.read_bytes())
            assert len(content) >= 3 * 4096
            content[-128] ^= 0x01
            database.write_bytes(content)
            with pytest.raises(DatabaseCorruptError):
                provider.connect(database, create=False, key_material=key)
    finally:
        _erase(key)


def test_missing_binding_and_incompatible_binding_version_fail_closed() -> None:
    key = _runtime_key()

    def missing_driver():
        raise ModuleNotFoundError("simulated")

    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "unavailable.sqlcipher"
            provider = SQLCipherConnectionProvider(driver_loader=missing_driver)
            with pytest.raises(SQLCipherUnavailableError):
                provider.connect(database, create=True, key_material=key)
            assert not database.exists()

            provider = SQLCipherConnectionProvider(
                binding_version_loader=lambda: "unsupported"
            )
            with pytest.raises(SQLCipherVersionError) as binding_error:
                provider.connect(database, create=True, key_material=key)
            assert binding_error.value.code == "sqlcipher_binding_version_incompatible"
            assert not database.exists()

    finally:
        _erase(key)


@requires_sqlcipher
def test_incompatible_engine_version_fails_before_database_creation() -> None:
    key = _runtime_key()
    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "wrong-version.sqlcipher"
            provider = SQLCipherConnectionProvider(
                expected_engine_version="0.0.0 unsupported"
            )
            with pytest.raises(SQLCipherVersionError) as engine_error:
                provider.connect(database, create=True, key_material=key)
            assert engine_error.value.code == "sqlcipher_engine_version_incompatible"
            assert not database.exists()
    finally:
        _erase(key)


def test_create_never_overwrites_an_existing_file() -> None:
    key = _runtime_key()
    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "existing.sqlcipher"
            database.write_bytes(secrets.token_bytes(4096))
            before = _digest(database)
            with pytest.raises(DatabaseEngineConfigurationError) as caught:
                SQLCipherConnectionProvider().connect(
                    database, create=True, key_material=key
                )
            assert caught.value.code == "sqlcipher_create_target_exists"
            assert before == _digest(database)
    finally:
        _erase(key)


def test_create_identity_swap_is_rejected_without_deleting_foreign_file() -> None:
    foreign_content = secrets.token_bytes(4096)
    key = _runtime_key()

    class Cursor:
        def fetchone(self):
            return ("4.12.0 community",)

    class Probe:
        def execute(self, _statement):
            return Cursor()

        def close(self):
            pass

    class SwappedConnection:
        closed = False

        def close(self):
            self.closed = True
            raise RuntimeError("simulated close failure")

    swapped = SwappedConnection()

    class Driver:
        Row = object

        @staticmethod
        def connect(target, **_kwargs):
            if target == ":memory:":
                return Probe()
            target_path = Path(target)
            target_path.unlink()
            target_path.write_bytes(foreign_content)
            return swapped

    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "identity-swap.sqlcipher"
            provider = SQLCipherConnectionProvider(
                driver_loader=lambda: Driver,
                binding_version_loader=lambda: "0.6.2",
            )
            with pytest.raises(DatabaseEngineConfigurationError) as caught:
                provider.connect(database, create=True, key_material=key)
            assert caught.value.code == "sqlcipher_create_target_changed"
            assert database.read_bytes() == foreign_content
            assert swapped.closed is True
    finally:
        _erase(key)


def test_failed_owned_creation_is_removed_after_sanitized_failure() -> None:
    key = _runtime_key()

    class Cursor:
        def fetchone(self):
            return ("4.12.0 community",)

    class Probe:
        def execute(self, _statement):
            return Cursor()

        def close(self):
            pass

    class FailingConnection:
        def execute(self, _statement):
            raise RuntimeError("simulated key failure")

        def close(self):
            pass

    class Driver:
        Row = object

        @staticmethod
        def connect(target, **_kwargs):
            return Probe() if target == ":memory:" else FailingConnection()

    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "failed-owned.sqlcipher"
            provider = SQLCipherConnectionProvider(
                driver_loader=lambda: Driver,
                binding_version_loader=lambda: "0.6.2",
            )
            with pytest.raises(DatabaseKeyRejectedError):
                provider.connect(database, create=True, key_material=key)
            assert not database.exists()
    finally:
        _erase(key)


def test_existing_file_identity_swap_is_rejected_without_deletion() -> None:
    key = _runtime_key()
    replacement = secrets.token_bytes(4096)

    class Cursor:
        def fetchone(self):
            return ("4.12.0 community",)

    class Probe:
        def execute(self, _statement):
            return Cursor()

        def close(self):
            pass

    class SwappedConnection:
        def close(self):
            pass

    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-test-") as directory:
            database = Path(directory) / "existing-swap.sqlcipher"
            database.write_bytes(secrets.token_bytes(4096))

            class Driver:
                Row = object

                @staticmethod
                def connect(target, **_kwargs):
                    if target == ":memory:":
                        return Probe()
                    database.unlink()
                    database.write_bytes(replacement)
                    return SwappedConnection()

            provider = SQLCipherConnectionProvider(
                driver_loader=lambda: Driver,
                binding_version_loader=lambda: "0.6.2",
            )
            with pytest.raises(DatabaseEngineConfigurationError) as caught:
                provider.connect(database, create=False, key_material=key)
            assert caught.value.code == "sqlcipher_create_target_changed"
            assert database.read_bytes() == replacement
    finally:
        _erase(key)


@requires_sqlcipher
def test_smoke_output_contains_no_key_material(capsys) -> None:
    key = _runtime_key()
    wrong_key = _runtime_key()
    try:
        message = run_smoke(key_material=key, wrong_key_material=wrong_key)
        print(message)
        captured = capsys.readouterr()
        assert "SQLCipher infrastructure smoke passed" in captured.out
        for secret in (bytes(key), bytes(wrong_key)):
            assert secret.hex() not in captured.out
            assert secret.hex() not in captured.err
    finally:
        _erase(key, wrong_key)
