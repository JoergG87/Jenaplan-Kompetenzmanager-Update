#!/usr/bin/env python3
"""Isolated SQLCipher 4.17.0 technical smoke for the source-built wheel."""

from __future__ import annotations

from contextlib import closing
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import secrets
import sqlite3
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.database_engine import (  # noqa: E402
    DatabaseFormatUnsupportedError,
    DatabaseKeyRejectedError,
    SQLCipherConnectionProvider,
)


BINDING_VERSION = "0.6.2+jkm.sqlcipher4170.1"
ENGINE_VERSION = "4.17.0 community"
SQLITE_VERSION = "3.53.3"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _erase(*values: bytearray) -> None:
    for value in values:
        for index in range(len(value)):
            value[index] = 0


def run_smoke() -> dict[str, object]:
    from sqlcipher3 import dbapi2 as driver
    from sqlcipher3 import _sqlite3 as native_driver

    native_path = Path(native_driver.__file__).resolve()
    venv_root = Path(sys.prefix).resolve()
    if sys.prefix == sys.base_prefix or not native_path.is_relative_to(venv_root):
        raise RuntimeError("sqlcipher_417_not_loaded_from_test_venv")

    runtime = {
        "machine": platform.machine(),
        "python": platform.python_version(),
        "binding": metadata.version("sqlcipher3"),
        "sqlite": driver.sqlite_version,
        "native_extension": str(native_path),
    }
    expected = {
        "machine": "arm64",
        "python": "3.14.6",
        "binding": BINDING_VERSION,
        "sqlite": SQLITE_VERSION,
    }
    if {key: runtime[key] for key in expected} != expected:
        raise RuntimeError(f"sqlcipher_417_runtime_mismatch:{runtime}")

    provider = SQLCipherConnectionProvider(
        expected_binding_version=BINDING_VERSION,
        expected_engine_version=ENGINE_VERSION,
    )
    key = bytearray(secrets.token_bytes(32))
    wrong_key = bytearray(secrets.token_bytes(32))
    marker = f"synthetic-sqlcipher-417-{secrets.token_hex(16)}"
    evidence: dict[str, object] = {}
    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-417-smoke-") as directory:
            root = Path(directory)
            encrypted = root / "encrypted.sqlcipher"
            with closing(
                provider.connect(encrypted, create=True, key_material=key)
            ) as connection:
                connection.execute("CREATE TABLE sample(value TEXT NOT NULL)")
                connection.execute("INSERT INTO sample VALUES (?)", (marker,))
                connection.commit()
                cipher_version = connection.execute(
                    "PRAGMA cipher_version"
                ).fetchone()[0]
                cipher_provider = connection.execute(
                    "PRAGMA cipher_provider"
                ).fetchone()[0]
                provider_version = connection.execute(
                    "PRAGMA cipher_provider_version"
                ).fetchone()[0]
                cipher_status = connection.execute(
                    "PRAGMA cipher_status"
                ).fetchone()[0]
                cipher_integrity = connection.execute(
                    "PRAGMA cipher_integrity_check"
                ).fetchall()
                integrity = connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]
                foreign_keys = connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall()
            if str(cipher_version) != ENGINE_VERSION:
                raise RuntimeError("sqlcipher_417_engine_version_mismatch")
            if str(cipher_provider) != "commoncrypto":
                raise RuntimeError("sqlcipher_417_provider_mismatch")
            if not str(provider_version):
                raise RuntimeError("sqlcipher_417_provider_version_missing")
            if str(cipher_status) != "1":
                raise RuntimeError("sqlcipher_417_cipher_inactive")
            if cipher_integrity or str(integrity) != "ok" or foreign_keys:
                raise RuntimeError("sqlcipher_417_integrity_failed")

            with closing(
                provider.connect(encrypted, create=False, key_material=key)
            ) as connection:
                if connection.execute("SELECT value FROM sample").fetchone()[0] != marker:
                    raise RuntimeError("sqlcipher_417_reopen_failed")

            encrypted_before_wrong_key = _sha256(encrypted)
            try:
                unexpected = provider.connect(
                    encrypted, create=False, key_material=wrong_key
                )
            except DatabaseKeyRejectedError:
                pass
            else:
                unexpected.close()
                raise RuntimeError("sqlcipher_417_wrong_key_accepted")
            if _sha256(encrypted) != encrypted_before_wrong_key:
                raise RuntimeError("sqlcipher_417_wrong_key_changed_database")

            try:
                with closing(
                    sqlite3.connect(
                        f"{encrypted.resolve().as_uri()}?mode=ro&immutable=1",
                        uri=True,
                    )
                ) as plaintext_reader:
                    plaintext_reader.execute(
                        "SELECT count(*) FROM sqlite_schema"
                    ).fetchone()
            except sqlite3.DatabaseError:
                pass
            else:
                raise RuntimeError("sqlcipher_417_plaintext_reader_accepted")

            content = encrypted.read_bytes()
            if content.startswith(b"SQLite format 3\x00") or marker.encode() in content:
                raise RuntimeError("sqlcipher_417_plaintext_leak")

            plaintext = root / "plaintext.sqlite"
            with sqlite3.connect(plaintext) as connection:
                connection.execute("CREATE TABLE sample(value TEXT NOT NULL)")
                connection.execute("INSERT INTO sample VALUES ('synthetic')")
            plaintext_hash = _sha256(plaintext)
            try:
                provider.connect(plaintext, create=False, key_material=key)
            except DatabaseFormatUnsupportedError:
                pass
            else:
                raise RuntimeError("sqlcipher_417_plaintext_database_accepted")
            if _sha256(plaintext) != plaintext_hash:
                raise RuntimeError("sqlcipher_417_plaintext_database_changed")

            evidence = {
                **runtime,
                "cipher_version": str(cipher_version),
                "cipher_provider": str(cipher_provider),
                "cipher_provider_version": str(provider_version),
                "cipher_status": str(cipher_status),
                "cipher_integrity_check": "ok",
                "integrity_check": str(integrity),
                "foreign_key_check": "ok",
                "reopen": "ok",
                "wrong_key_rejected": True,
                "plaintext_sqlite_rejected": True,
                "plaintext_database_rejected": True,
            }
    finally:
        _erase(key, wrong_key)
    return evidence


def main() -> int:
    print(json.dumps(run_smoke(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
