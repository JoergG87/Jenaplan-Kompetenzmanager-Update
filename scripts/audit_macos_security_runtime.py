"""Fail-closed dependency and architecture checks for the macOS RC build."""

from __future__ import annotations

import argparse
from importlib import metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCIPHER_4_17_SQLITE_VERSION,
)


EXPECTED_VERSIONS = {
    "PySide6": "6.11.1",
    "shiboken6": "6.11.1",
    "PyNaCl": "1.6.2",
    "cryptography": "49.0.0",
    "cffi": "2.0.0",
    "sqlcipher3": SQLCIPHER_4_17_BINDING_VERSION,
    "pyinstaller": "6.21.0",
}


def audit_environment() -> dict[str, object]:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Security-RC-Build benötigt macOS arm64.")
    observed = {
        name: metadata.version(name)
        for name in EXPECTED_VERSIONS
    }
    if observed != EXPECTED_VERSIONS:
        raise RuntimeError("Gepinnte Security-Buildversionen stimmen nicht.")

    import _cffi_backend
    import nacl._sodium
    import PySide6.QtCore
    import shiboken6.Shiboken
    import sqlcipher3

    with tempfile.TemporaryDirectory(prefix="jkm-macos-runtime-audit-") as temp_name:
        database = Path(temp_name) / "runtime-audit.sqlcipher"
        connection = sqlcipher3.connect(database)
        try:
            connection.execute("PRAGMA key = \"x'" + ("00" * 32) + "'\"")
            connection.execute("CREATE TABLE audit(value TEXT NOT NULL)")
            connection.execute("INSERT INTO audit VALUES ('synthetic')")
            connection.commit()
            cipher_version = str(
                connection.execute("PRAGMA cipher_version").fetchone()[0]
            )
            sqlite_version = str(
                connection.execute("SELECT sqlite_version()").fetchone()[0]
            )
            cipher_provider = str(
                connection.execute("PRAGMA cipher_provider").fetchone()[0]
            )
            cipher_provider_version = str(
                connection.execute("PRAGMA cipher_provider_version").fetchone()[0]
            )
            cipher_integrity = connection.execute(
                "PRAGMA cipher_integrity_check"
            ).fetchall()
        finally:
            connection.close()
    if cipher_version != SQLCIPHER_4_17_ENGINE_VERSION:
        raise RuntimeError("Unerwartete SQLCipher-Laufzeit.")
    if sqlite_version != SQLCIPHER_4_17_SQLITE_VERSION:
        raise RuntimeError("Unerwartete gebündelte SQLite-Laufzeit.")
    if cipher_provider != "commoncrypto" or not cipher_provider_version:
        raise RuntimeError("SQLCipher verwendet nicht CommonCrypto.")
    if cipher_integrity:
        raise RuntimeError("SQLCipher-Integritätsprüfung ist fehlgeschlagen.")

    native_files = {
        "_cffi_backend": Path(_cffi_backend.__file__).resolve(),
        "libsodium": Path(nacl._sodium.__file__).resolve(),
        "PySide6": Path(PySide6.QtCore.__file__).resolve(),
        "Shiboken": Path(shiboken6.Shiboken.__file__).resolve(),
        "sqlcipher3": Path(sqlcipher3._sqlite3.__file__).resolve(),
    }
    architectures = {
        name: _architectures(path)
        for name, path in native_files.items()
    }
    if any("arm64" not in values for values in architectures.values()):
        raise RuntimeError("Native Buildabhängigkeit enthält kein arm64.")
    return {
        "architectures": architectures,
        "sqlcipher": cipher_version,
        "sqlcipher_binding": observed["sqlcipher3"],
        "sqlcipher_provider": cipher_provider,
        "sqlcipher_provider_version": cipher_provider_version,
        "sqlite": sqlite_version,
        "versions": observed,
    }


def _architectures(path: Path) -> list[str]:
    result = subprocess.run(
        ["lipo", "-archs", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Architekturprüfung fehlgeschlagen: {path.name}")
    values = result.stdout.strip().split()
    if not values:
        raise RuntimeError(f"Keine Mach-O-Architektur gefunden: {path.name}")
    return values


def main() -> int:
    argparse.ArgumentParser().parse_args()
    print(
        json.dumps(
            audit_environment(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
