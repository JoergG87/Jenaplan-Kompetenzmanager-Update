"""Deployment checks for safe macOS runtime paths and initial data."""

from __future__ import annotations

import json
import os
import plistlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from scripts.build_laura_pilot_package import build_package
from scripts.build_laura_testdata_backup import build_laura_testdata_backup
from scripts.prepare_macos_pilot_payload import prepare_payload
from scripts.smoke_test_macos_app import (
    PACKAGED_SMOKE_MARKER_ENV,
    PACKAGED_SMOKE_MARKER_VALUE,
    smoke_test,
)
from src.desktop_app import main as desktop_main
from src.application.commands.restore import (
    RestoreApplicationService,
    VerifyRestoreBackupQuery,
)
from src.desktop_app.runtime import (
    APP_DATA_DIR_ENV,
    DATABASE_FILENAME,
    INITIAL_DATA_DIRECTORY,
    INITIAL_PATH_TOKEN,
    RuntimeStorageError,
    application_data_root,
    prepare_runtime_storage,
)


class MacosRuntimeTest(unittest.TestCase):
    def test_release_packages_separate_empty_and_laura_testdata_handoffs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = root / "inputs"
            inputs.mkdir()
            files = {
                "dmg": inputs / "Jenaplan-Kompetenzmanager-0.2.0-macOS-arm64.dmg",
                "manual": inputs / "manual.pdf",
                "first": inputs / "first.pdf",
                "quick": inputs / "quick.pdf",
                "installation": inputs / "installation.pdf",
                "backup": inputs / "backup.pdf",
                "workbook": inputs / "Pilottest_Laura_Schuelerprofil_Variante_A.xlsx",
                "notes": inputs / "RELEASE_NOTES.md",
                "inventory": inputs / "RELEASE_INVENTORY-0.2.0.txt",
            }
            for name, path in files.items():
                path.write_bytes(f"test-{name}".encode())
            pilot_backup, _seed = build_laura_testdata_backup(
                output_directory=inputs,
                version="0.2.0",
                build_commit="e48436d2249ac108246d77a817e141e15611ab0f",
                source_tree_state="dirty",
            )

            empty_root, empty_zip = build_package(
                output_root=root / "dist",
                version="0.2.0",
                architecture="arm64",
                dmg=files["dmg"],
                first_steps_pdf=files["first"],
                manual_pdf=files["manual"],
                quickstart_pdf=files["quick"],
                installation_pdf=files["installation"],
                backup_guide_pdf=files["backup"],
                pilot_workbook=files["workbook"],
                release_notes=files["notes"],
                release_inventory=files["inventory"],
                variant="empty",
            )
            laura_root, laura_zip = build_package(
                output_root=root / "dist",
                version="0.2.0",
                architecture="arm64",
                dmg=files["dmg"],
                first_steps_pdf=files["first"],
                manual_pdf=files["manual"],
                quickstart_pdf=files["quick"],
                installation_pdf=files["installation"],
                backup_guide_pdf=files["backup"],
                pilot_workbook=files["workbook"],
                release_notes=files["notes"],
                release_inventory=files["inventory"],
                variant="laura_testdata",
                pilot_backup=pilot_backup,
            )

            self.assertTrue(empty_zip.is_file())
            self.assertTrue(laura_zip.is_file())
            self.assertEqual(
                {path.name for path in empty_root.iterdir()},
                {
                    "README.txt",
                    "Jenaplan-Kompetenzmanager-0.2.0-macOS-arm64.dmg",
                    "Jenaplan-Kompetenzmanager-0.2.0-Benutzerhandbuch.pdf",
                    "Jenaplan-Kompetenzmanager-0.2.0-Erste-Schritte.pdf",
                    "Jenaplan-Kompetenzmanager-0.2.0-Schnellstart.pdf",
                    "Jenaplan-Kompetenzmanager-0.2.0-Installationsanleitung.pdf",
                    "Jenaplan-Kompetenzmanager-0.2.0-Backup-Anleitung.pdf",
                    "Pilottest_Laura_Schuelerprofil_Variante_A.xlsx",
                    "RELEASE_NOTES.md",
                    "SHA256SUMS-0.2.0.txt",
                    "RELEASE_INVENTORY-0.2.0.txt",
                },
            )
            self.assertEqual(
                {path.name for path in laura_root.iterdir()},
                {path.name for path in empty_root.iterdir()}
                | {"Laura-Testdaten-0.2.0.jkmbackup"},
            )
            self.assertNotIn("jkmbackup", (empty_root / "README.txt").read_text())
            self.assertIn(
                "normalen Restore-Weg",
                (laura_root / "README.txt").read_text(),
            )
            self.assertEqual(
                (empty_root / files["dmg"].name).read_bytes(),
                (laura_root / files["dmg"].name).read_bytes(),
            )
            with zipfile.ZipFile(empty_zip) as archive:
                self.assertIsNone(archive.testzip())
                empty_names = archive.namelist()
            with zipfile.ZipFile(laura_zip) as archive:
                self.assertIsNone(archive.testzip())
                laura_names = archive.namelist()
            self.assertEqual(len(empty_names), 11)
            self.assertEqual(len(laura_names), 12)
            self.assertFalse(any("__MACOSX" in name for name in (*empty_names, *laura_names)))

    def test_laura_testdata_backup_uses_official_restore_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            backup, seed = build_laura_testdata_backup(
                output_directory=Path(temp),
                version="0.2.0",
                build_commit="e48436d2249ac108246d77a817e141e15611ab0f",
                source_tree_state="dirty",
            )
            verified = RestoreApplicationService().verify(
                VerifyRestoreBackupQuery(backup)
            )

            self.assertEqual(backup.name, "Laura-Testdaten-0.2.0.jkmbackup")
            self.assertEqual(verified.preview.students_count, seed.student_count)
            self.assertEqual(
                verified.preview.observations_count,
                seed.observation_count,
            )
            self.assertEqual(
                verified.preview.learning_report_revisions_count,
                seed.report_revision_count,
            )
            self.assertEqual(
                verified.preview.learning_conference_revisions_count,
                seed.conference_revision_count,
            )
            with zipfile.ZipFile(backup) as archive:
                names = tuple(archive.namelist())
            self.assertEqual(names[0], "manifest.json")
            self.assertIn("database/kompetenzmanager.sqlite", names)
            self.assertFalse(any("security" in name.casefold() for name in names))

    def test_developer_and_packaged_data_roots_are_separate(self) -> None:
        self.assertEqual(
            application_data_root(packaged=False, environ={}),
            Path("data"),
        )
        self.assertEqual(
            application_data_root(
                packaged=True,
                home=Path("/Users/laura"),
                environ={},
            ),
            Path("/Users/laura/Library/Application Support/Jenaplan-Kompetenzmanager"),
        )

    def test_explicit_test_override_is_honored(self) -> None:
        self.assertEqual(
            application_data_root(
                packaged=True,
                environ={APP_DATA_DIR_ENV: "/tmp/jenaplan-smoke"},
            ),
            Path("/tmp/jenaplan-smoke"),
        )

    def test_packaged_smoke_without_marker_stops_before_runtime_initialization(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            productive_root = Path(temp) / "normal-user-data"
            productive_root.mkdir()
            sentinel = productive_root / "existing-user-data.txt"
            sentinel.write_bytes(b"unchanged")
            with (
                mock.patch.dict(
                    os.environ,
                    {APP_DATA_DIR_ENV: str(productive_root)},
                    clear=True,
                ),
                mock.patch.object(
                    sys,
                    "argv",
                    ["app", "--packaged-smoke-test"],
                ),
                mock.patch.object(desktop_main, "QApplication") as application,
                mock.patch.object(
                    desktop_main,
                    "prepare_runtime_storage",
                ) as prepare,
            ):
                self.assertEqual(desktop_main.main(), 2)
            application.assert_not_called()
            prepare.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), b"unchanged")
            self.assertEqual(tuple(productive_root.iterdir()), (sentinel,))

    def test_packaged_smoke_marker_with_normal_path_is_rejected_without_writes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            productive_root = Path(temp) / "normal-user-data"
            productive_root.mkdir()
            sentinel = productive_root / "existing-user-data.txt"
            sentinel.write_bytes(b"unchanged")
            with (
                mock.patch.dict(
                    os.environ,
                    {
                        APP_DATA_DIR_ENV: str(productive_root),
                        PACKAGED_SMOKE_MARKER_ENV: PACKAGED_SMOKE_MARKER_VALUE,
                    },
                    clear=True,
                ),
                mock.patch.object(
                    sys,
                    "argv",
                    ["app", "--packaged-smoke-test"],
                ),
                mock.patch.object(desktop_main, "QApplication") as application,
                mock.patch.object(
                    desktop_main,
                    "prepare_runtime_storage",
                ) as prepare,
            ):
                self.assertEqual(desktop_main.main(), 2)
            application.assert_not_called()
            prepare.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), b"unchanged")
            self.assertEqual(tuple(productive_root.iterdir()), (sentinel,))

    def test_packaged_smoke_accepts_marker_and_dedicated_temporary_root(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="jenaplan-packaged-smoke-"
        ) as temp:
            data_root = Path(temp) / "Application Support" / "Jenaplan-Kompetenzmanager"
            validated = desktop_main._validated_packaged_smoke_data_root(
                {
                    APP_DATA_DIR_ENV: str(data_root),
                    PACKAGED_SMOKE_MARKER_ENV: PACKAGED_SMOKE_MARKER_VALUE,
                }
            )
            self.assertEqual(validated, data_root.resolve())

    def test_packaged_smoke_harness_sets_both_isolation_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            app_path = Path(temp) / "Jenaplan-Kompetenzmanager.app"
            executable = (
                app_path
                / "Contents"
                / "MacOS"
                / "Jenaplan-Kompetenzmanager"
            )
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"executable")
            info_plist = app_path / "Contents" / "Info.plist"
            with info_plist.open("wb") as plist_file:
                plistlib.dump(
                    {
                        "CFBundleIdentifier": "de.jenaplan.kompetenzmanager",
                        "CFBundleShortVersionString": "0.2.0",
                        "LSMinimumSystemVersion": "13.0",
                    },
                    plist_file,
                )
            observed_environment: dict[str, str] = {}

            def simulate_packaged_run(*args, **kwargs):
                environment = kwargs["env"]
                observed_environment.update(environment)
                data_root = Path(environment[APP_DATA_DIR_ENV])
                for name in ("documents", "exports", "backups", "logs"):
                    (data_root / name).mkdir(parents=True, exist_ok=True)
                database = data_root / DATABASE_FILENAME
                with sqlite3.connect(database) as connection:
                    connection.execute("CREATE TABLE students (student_id TEXT)")
                    connection.execute(
                        "CREATE TABLE learning_report_revisions (revision_id TEXT)"
                    )
                    connection.execute(
                        "CREATE TABLE learning_conference_revisions (revision_id TEXT)"
                    )
                (data_root / "exports" / "packaged-app-smoke.pdf").write_bytes(b"pdf")
                (data_root / "backups" / "smoke.jkmbackup").write_bytes(b"backup")
                payload = {
                    "backup_exists": True,
                    "backup_verified": True,
                    "build_info": {"data_mode": "empty"},
                }
                return subprocess.CompletedProcess(
                    args=args[0],
                    returncode=0,
                    stdout=json.dumps(payload) + "\n",
                    stderr="",
                )

            with mock.patch(
                "scripts.smoke_test_macos_app.subprocess.run",
                side_effect=simulate_packaged_run,
            ):
                result = smoke_test(app_path)
            self.assertEqual(
                observed_environment[PACKAGED_SMOKE_MARKER_ENV],
                PACKAGED_SMOKE_MARKER_VALUE,
            )
            self.assertIn(
                "jenaplan-packaged-smoke-",
                observed_environment[APP_DATA_DIR_ENV],
            )
            self.assertEqual(result["backup"]["count"], 1)

    def test_empty_first_start_creates_all_mutable_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "user-data"
            resources = Path(temp) / "resources"
            resources.mkdir()

            paths = prepare_runtime_storage(
                data_root=root,
                resource_root_path=resources,
            )

            self.assertFalse(paths.database.exists())
            self.assertTrue(paths.documents.is_dir())
            self.assertTrue(paths.exports.is_dir())
            self.assertTrue(paths.backups.is_dir())
            self.assertTrue(paths.logs.is_dir())

    def test_initial_pilot_data_is_copied_once_and_document_paths_are_rebased(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "user-data"
            initial = base / "resources" / INITIAL_DATA_DIRECTORY
            initial.mkdir(parents=True)
            initial_document = initial / "documents" / "STU-000001" / "demo.txt"
            initial_document.parent.mkdir(parents=True)
            initial_document.write_text("fiktiv", encoding="utf-8")
            initial_database = initial / DATABASE_FILENAME
            with sqlite3.connect(initial_database) as connection:
                connection.execute(
                    "CREATE TABLE documents (document_id TEXT PRIMARY KEY, file_path TEXT NOT NULL)"
                )
                connection.execute(
                    "INSERT INTO documents VALUES (?, ?)",
                    (
                        "MED-000001",
                        f"{INITIAL_PATH_TOKEN}/documents/STU-000001/demo.txt",
                    ),
                )

            paths = prepare_runtime_storage(
                data_root=root,
                resource_root_path=base / "resources",
            )
            with sqlite3.connect(paths.database) as connection:
                stored_path = connection.execute(
                    "SELECT file_path FROM documents WHERE document_id = ?",
                    ("MED-000001",),
                ).fetchone()[0]

            self.assertEqual(
                stored_path,
                str(root / "documents" / "STU-000001" / "demo.txt"),
            )
            self.assertEqual(
                (root / "documents" / "STU-000001" / "demo.txt").read_text(
                    encoding="utf-8"
                ),
                "fiktiv",
            )

            paths.database.write_bytes(b"existing-user-database")
            prepare_runtime_storage(
                data_root=root,
                resource_root_path=base / "resources",
            )
            self.assertEqual(paths.database.read_bytes(), b"existing-user-database")

    def test_empty_and_laura_build_payloads_are_strictly_separated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            empty = prepare_payload(
                root / "empty",
                data_mode="empty",
                version="0.1.0",
                git_commit="test-commit",
                source_tree_state="clean",
                architecture="arm64",
            )
            empty_info = json.loads(
                (empty / "pilot_build_info.json").read_text(encoding="utf-8")
            )
            self.assertEqual(empty_info["pilot_data_label"], "Technischer Smoke-Test - leer")
            self.assertFalse(tuple(empty.rglob("*.sqlite")))

            release = prepare_payload(
                root / "release",
                data_mode="release",
                version="0.2.0",
                git_commit="test-commit",
                source_tree_state="clean",
                architecture="arm64",
            )
            release_info = json.loads(
                (release / "pilot_build_info.json").read_text(encoding="utf-8")
            )
            self.assertEqual(release_info["pilot_data_label"], "Release-Kandidat - leer")
            self.assertFalse(tuple(release.rglob("*.sqlite")))

            laura = prepare_payload(
                root / "laura",
                data_mode="laura",
                version="0.1.0",
                git_commit="test-commit",
                source_tree_state="clean",
                architecture="arm64",
            )
            laura_info = json.loads(
                (laura / "pilot_build_info.json").read_text(encoding="utf-8")
            )
            self.assertEqual(laura_info["pilot_data_label"], "Fiktive Pilotdaten")
            self.assertTrue(
                (laura / INITIAL_DATA_DIRECTORY / "FIKTIVE_PILOTDATEN.txt").is_file()
            )
            database = laura / INITIAL_DATA_DIRECTORY / DATABASE_FILENAME
            with sqlite3.connect(database) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM students").fetchone()[0],
                    24,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM learning_report_revisions"
                    ).fetchone()[0],
                    2,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM learning_conference_revisions"
                    ).fetchone()[0],
                    2,
                )

    def test_non_directory_data_root_fails_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "not-a-directory"
            root.write_text("occupied", encoding="utf-8")
            with self.assertRaises(RuntimeStorageError):
                prepare_runtime_storage(
                    data_root=root,
                    resource_root_path=Path(temp),
                )


if __name__ == "__main__":
    unittest.main()
