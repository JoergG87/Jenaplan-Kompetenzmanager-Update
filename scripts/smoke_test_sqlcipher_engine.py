#!/usr/bin/env python3
"""Isolated SQLCipher and packaging smoke with no persistent key or database."""

from __future__ import annotations

from contextlib import closing
import secrets
import sqlite3
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.database_engine import (
    DatabaseKeyRejectedError,
    SQLCIPHER_SPIKE_ENGINE_VERSION,
    SQLCipherConnectionProvider,
)


def run_smoke(
    *,
    key_material: bytes | bytearray | None = None,
    wrong_key_material: bytes | bytearray | None = None,
) -> str:
    provider = SQLCipherConnectionProvider()
    key = bytearray(
        secrets.token_bytes(32) if key_material is None else key_material
    )
    wrong_key = bytearray(
        secrets.token_bytes(32)
        if wrong_key_material is None
        else wrong_key_material
    )
    marker = f"synthetic-{secrets.token_hex(12)}"
    try:
        with TemporaryDirectory(prefix="jkm-sqlcipher-smoke-") as directory:
            database = Path(directory) / "synthetic.sqlcipher"
            with closing(
                provider.connect(database, create=True, key_material=key)
            ) as connection:
                connection.execute("CREATE TABLE sample(value TEXT NOT NULL)")
                connection.execute("INSERT INTO sample VALUES (?)", (marker,))
                connection.commit()

            with closing(
                provider.connect(database, create=False, key_material=key)
            ) as connection:
                if connection.execute("SELECT value FROM sample").fetchone()[0] != marker:
                    raise RuntimeError("sqlcipher_smoke_read_failed")

            try:
                unexpected = provider.connect(
                    database, create=False, key_material=wrong_key
                )
            except DatabaseKeyRejectedError:
                pass
            else:
                unexpected.close()
                raise RuntimeError("sqlcipher_smoke_wrong_key_accepted")

            try:
                with closing(
                    sqlite3.connect(
                        f"{database.resolve().as_uri()}?mode=ro&immutable=1", uri=True
                    )
                ) as plaintext:
                    plaintext.execute("SELECT count(*) FROM sqlite_schema").fetchone()
            except sqlite3.DatabaseError:
                pass
            else:
                raise RuntimeError("sqlcipher_smoke_plaintext_open_succeeded")

            if marker.encode("utf-8") in database.read_bytes():
                raise RuntimeError("sqlcipher_smoke_plaintext_marker_found")
    finally:
        for material in (key, wrong_key):
            for index in range(len(material)):
                material[index] = 0
    return f"SQLCipher infrastructure smoke passed ({SQLCIPHER_SPIKE_ENGINE_VERSION})."


def main() -> int:
    print(run_smoke())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
