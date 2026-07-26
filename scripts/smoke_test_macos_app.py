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


APP_NAME = "Jenaplan-Kompetenzmanager"
PACKAGED_SMOKE_MARKER_ENV = "JENAPLAN_PACKAGED_SMOKE_MARKER"
PACKAGED_SMOKE_MARKER_VALUE = "isolated-v1"


def smoke_test(app_path: Path, *, expected_data_mode: str = "empty") -> dict[str, object]:
    """Launch the bundled executable against an isolated temporary user root."""
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
        environment = os.environ.copy()
        environment["JENAPLAN_APP_DATA_DIR"] = str(data_root)
        environment[PACKAGED_SMOKE_MARKER_ENV] = PACKAGED_SMOKE_MARKER_VALUE
        environment["QT_QPA_PLATFORM"] = "offscreen"
        result = subprocess.run(
            [str(executable), "--packaged-smoke-test"],
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
            env=environment,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Packaged-App-Smoke fehlgeschlagen.\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        payload = json.loads(lines[-1])
        if payload["build_info"].get("data_mode") != expected_data_mode:
            raise RuntimeError(
                "Pilotdaten-Variante stimmt nicht: "
                f"{payload['build_info'].get('data_mode')}"
            )
        required = (
            data_root / "kompetenzmanager.sqlite",
            data_root / "documents",
            data_root / "exports",
            data_root / "backups",
            data_root / "logs",
            data_root / "exports" / "packaged-app-smoke.pdf",
        )
        missing = tuple(path for path in required if not path.exists())
        if missing:
            raise RuntimeError(f"Packaged-App-Smoke: Pfad fehlt: {missing[0]}")
        backups = tuple((data_root / "backups").glob("*.jkmbackup"))
        if len(backups) != 1 or not payload.get("backup_exists"):
            raise RuntimeError(
                "Packaged-App-Smoke hat kein eindeutiges Anwendungsbackup erzeugt."
            )
        if not payload.get("backup_verified"):
            raise RuntimeError("Packaged-App-Smoke hat das Backup nicht verifiziert.")
        if not payload.get("login_authenticated"):
            raise RuntimeError("Packaged-App-Smoke hat den Login nicht bestätigt.")
        if not payload.get("document_access_verified") or not payload.get(
            "document_probe_removed"
        ):
            raise RuntimeError(
                "Packaged-App-Smoke hat den Dokumentpfad nicht sauber geprüft."
            )
        restore = payload.get("restore", {})
        if (
            not restore.get("archive_verified")
            or restore.get("prepared_status") != "verified"
            or restore.get("restore_id") != "RST-PACKAGED-SMOKE"
        ):
            raise RuntimeError(
                "Packaged-App-Smoke hat ZIP-v1-Restore-Staging nicht bestätigt."
            )
        if not payload.get("regular_exit_completed"):
            raise RuntimeError(
                "Packaged-App-Smoke hat das reguläre Beenden nicht bestätigt."
            )
        if payload.get("security_integration_imported"):
            raise RuntimeError(
                "Gate-Off-Startup hat den Security-Integrationspfad importiert."
            )
        with sqlite3.connect(data_root / "kompetenzmanager.sqlite") as connection:
            student_count = connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            report_revision_count = connection.execute(
                "SELECT COUNT(*) FROM learning_report_revisions"
            ).fetchone()[0]
            conference_revision_count = connection.execute(
                "SELECT COUNT(*) FROM learning_conference_revisions"
            ).fetchone()[0]
        if expected_data_mode in {"empty", "release"} and student_count != 0:
            raise RuntimeError("Leeres Pilotpaket enthält unerwartet Schülerdaten.")
        if expected_data_mode == "laura" and (
            student_count != 24
            or report_revision_count < 2
            or conference_revision_count < 2
        ):
            raise RuntimeError(
                "Laura-Pilotdaten sind unvollständig: "
                f"Kinder={student_count}, Berichtrevisionen={report_revision_count}, "
                f"LEG-Revisionen={conference_revision_count}"
            )
        with info_plist.open("rb") as plist_file:
            plist = plistlib.load(plist_file)
        if plist.get("CFBundleIdentifier") != "de.jenaplan.kompetenzmanager":
            raise RuntimeError("Bundle-ID stimmt nicht.")
        payload["plist"] = {
            "bundle_id": plist.get("CFBundleIdentifier"),
            "minimum_macos": plist.get("LSMinimumSystemVersion"),
            "version": plist.get("CFBundleShortVersionString"),
        }
        payload["pilot_data"] = {
            "student_count": student_count,
            "report_revision_count": report_revision_count,
            "conference_revision_count": conference_revision_count,
        }
        payload["backup"] = {
            "count": len(backups),
            "suffix": backups[0].suffix,
        }
        return payload


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
