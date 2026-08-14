"""Automated smoke test for a built macOS application bundle."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from src.core.runtime_root_protection import prepare_synthetic_test_root


APP_NAME = "Jenaplan-Kompetenzmanager"
PACKAGED_SMOKE_MARKER_ENV = "JENAPLAN_PACKAGED_SMOKE_MARKER"
PACKAGED_SMOKE_MARKER_VALUE = "isolated-v1"


def smoke_test(app_path: Path, *, expected_data_mode: str = "empty") -> dict[str, object]:
    """Launch two frozen processes against one isolated encrypted Final-V4 root."""
    app_path = Path(app_path).resolve()
    executable = app_path / "Contents" / "MacOS" / APP_NAME
    info_plist = app_path / "Contents" / "Info.plist"
    if not executable.is_file() or not info_plist.is_file():
        raise RuntimeError(f"Ungültiges App-Bundle: {app_path}")
    bundled_databases = tuple(app_path.rglob("*.sqlite")) + tuple(app_path.rglob("*.db"))
    if expected_data_mode in {"empty", "release"} and bundled_databases:
        raise RuntimeError(f"Unerwartete Datenbank im App-Bundle: {bundled_databases[0]}")
    if expected_data_mode == "laura" and len(bundled_databases) != 1:
        raise RuntimeError(
            "Laura-Pilot muss genau eine ausdrücklich fiktive Startdatenbank enthalten."
        )

    with tempfile.TemporaryDirectory(prefix="jenaplan-packaged-smoke-") as temp:
        data_root = Path(temp) / "Application Support" / APP_NAME
        data_root.parent.mkdir(parents=True)
        prepare_synthetic_test_root(data_root)
        initialized = _run(executable, data_root, "initialize")
        try:
            restarted = _run(executable, data_root, "restart")
        finally:
            cleanup = _run(executable, data_root, "cleanup")
        if initialized["build_info"].get("data_mode") != expected_data_mode:
            raise RuntimeError(
                "Pilotdaten-Variante stimmt nicht: "
                f"{initialized['build_info'].get('data_mode')}"
            )
        required = (
            data_root / "security" / "security.sqlite",
            data_root / "security-key-runtime-v1" / "data-keysets.sqlite",
            data_root / "security-key-runtime-v1" / "database-key-envelopes-v1.json",
            data_root / "final-v4-sqlcipher-runtime-v1" / "final-v4.sqlcipher",
            data_root / "final-v4-sqlcipher-runtime-v1" / "documents-v1.sqlcipher",
            data_root / "exports",
            data_root / "backups",
            data_root / "logs",
        )
        missing = tuple(path for path in required if not path.exists())
        if missing:
            raise RuntimeError(f"Packaged-App-Smoke: Pfad fehlt: {missing[0]}")
        for payload, first_run in ((initialized, True), (restarted, False)):
            if (
                payload.get("cipher_version") != "4.17.0 community"
                or payload.get("sqlite_version") != "3.53.3"
                or payload.get("cipher_provider") != "commoncrypto"
                or payload.get("final_v4") != 4
                or payload.get("school_year") != "2026/27"
                or payload.get("student_count") != 0
                or payload.get("first_run") is not first_run
                or not payload.get("login_authenticated")
                or not payload.get("regular_exit_completed")
            ):
                raise RuntimeError(f"Final-V4-Paketvertrag ist nicht erfüllt: {payload}")
        stable_fields = (
            "database_context_id",
            "database_key_fingerprint_sha256",
            "dmk_fingerprint_sha256",
        )
        if any(initialized[name] != restarted[name] for name in stable_fields):
            raise RuntimeError("DMK, Database-Key oder Context änderte sich beim Restart.")
        encrypted_database = required[3]
        try:
            with sqlite3.connect(encrypted_database) as connection:
                connection.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        except sqlite3.DatabaseError:
            pass
        else:
            raise RuntimeError("Final-V4-Datenbank ist mit Klartext-SQLite lesbar.")
        if cleanup.get("keychain_cleanup") != "ok":
            raise RuntimeError("Der Final-V4-Pakettest räumte den DMK nicht auf.")
        with info_plist.open("rb") as plist_file:
            plist = plistlib.load(plist_file)
        if plist.get("CFBundleIdentifier") != "de.jenaplan.kompetenzmanager":
            raise RuntimeError("Bundle-ID stimmt nicht.")
        restarted["plist"] = {
            "bundle_id": plist.get("CFBundleIdentifier"),
            "minimum_macos": plist.get("LSMinimumSystemVersion"),
            "version": plist.get("CFBundleShortVersionString"),
        }
        restarted["restart"] = {
            "context_stable": True,
            "database_key_stable": True,
            "dmk_stable": True,
        }
        restarted["keychain_cleanup"] = cleanup["keychain_cleanup"]
        return restarted


def _run(executable: Path, data_root: Path, mode: str) -> dict[str, object]:
    environment = os.environ.copy()
    environment["JENAPLAN_APP_DATA_DIR"] = str(data_root)
    environment[PACKAGED_SMOKE_MARKER_ENV] = PACKAGED_SMOKE_MARKER_VALUE
    environment["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [str(executable), "--packaged-smoke-test", mode],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env=environment,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Packaged-App-Smoke fehlgeschlagen: "
            f"mode={mode}, code={result.returncode}, "
            f"stdout={result.stdout[-1000:]}, stderr={result.stderr[-1000:]}"
        )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("app", type=Path)
    parser.add_argument(
        "--expected-data-mode",
        choices=("empty", "laura", "release"),
        default="empty",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    print(
        json.dumps(
            smoke_test(args.app, expected_data_mode=args.expected_data_mode),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
