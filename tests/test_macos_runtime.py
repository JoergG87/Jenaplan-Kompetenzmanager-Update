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
from src.core.runtime_root_protection import prepare_synthetic_test_root


class MacosRuntimeTest(unittest.TestCase):
    def test_macos_build_never_recursively_replaces_caller_output_roots(self) -> None:
        source = Path("scripts/build_macos_pilot.sh").read_text(encoding="utf-8")
        self.assertNotIn('rm -rf "$BUILD_ROOT" "$DIST_ROOT"', source)
        self.assertIn("require_unprotected_output_path", source)
        self.assertIn("Build- und Distributionsziele müssen vollständig neu sein", source)

    def test_data_root_aware_build_and_smoke_tools_use_product_guard(self) -> None:
        backup = Path("scripts/backup_macos_pilot.sh").read_text(encoding="utf-8")
        self.assertIn("require_unprotected_output_path", backup)
        restore_smoke = Path("scripts/smoke_test_packaged_restore_worker.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("prepare_synthetic_test_root(data_root)", restore_smoke)

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
            data_root.parent.mkdir(parents=True)
            prepare_synthetic_test_root(data_root)
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
                for name in (
                    "exports",
                    "backups",
                    "logs",
                    "security",
                    "security-key-runtime-v1",
                    "final-v4-sqlcipher-runtime-v1",
                ):
                    (data_root / name).mkdir(parents=True, exist_ok=True)
                for relative in (
                    "security/security.sqlite",
                    "security-key-runtime-v1/data-keysets.sqlite",
                    "security-key-runtime-v1/database-key-envelopes-v1.json",
                    "final-v4-sqlcipher-runtime-v1/final-v4.sqlcipher",
                    "final-v4-sqlcipher-runtime-v1/documents-v1.sqlcipher",
                ):
                    (data_root / relative).write_bytes(b"encrypted synthetic bytes")
                mode = args[0][-1]
                payload = {
                    "build_info": {"data_mode": "empty"},
                    "cipher_provider": "commoncrypto",
                    "cipher_version": "4.17.0 community",
                    "database_context_id": "ctx",
                    "database_key_fingerprint_sha256": "a" * 64,
                    "dmk_fingerprint_sha256": "b" * 64,
                    "final_v4": 4,
                    "first_run": mode == "initialize",
                    "keychain_cleanup": "ok" if mode == "cleanup" else None,
                    "login_authenticated": True,
                    "mode": mode,
                    "regular_exit_completed": True,
                    "school_year": "2026/27",
                    "sqlite_version": "3.53.3",
                    "student_count": 0,
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
            self.assertTrue(result["restart"]["dmk_stable"])
            self.assertEqual(result["keychain_cleanup"], "ok")

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

    def test_packaged_initial_database_is_not_installed_by_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "user-data"
            initial = base / "resources" / INITIAL_DATA_DIRECTORY
            initial.mkdir(parents=True)
            initial_database = initial / DATABASE_FILENAME
            initial_database.write_bytes(b"synthetic predecessor bytes")

            paths = prepare_runtime_storage(
                data_root=root,
                resource_root_path=base / "resources",
            )

            self.assertFalse(paths.database.exists())
            self.assertEqual(
                initial_database.read_bytes(),
                b"synthetic predecessor bytes",
            )
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
                student_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(students)"
                    ).fetchall()
                }
                self.assertNotIn("group_id", student_columns)
                self.assertNotIn("course_id", student_columns)
                self.assertEqual(
                    connection.execute(
                        """
                        SELECT label, status
                        FROM school_years
                        ORDER BY start_date
                        """
                    ).fetchall(),
                    [("2025/26", "closed"), ("2026/27", "current")],
                )
                self.assertEqual(
                    connection.execute(
                        """
                        SELECT year_level
                        FROM courses
                        WHERE active = 1
                        ORDER BY sort_order, course_id
                        """
                    ).fetchall(),
                    [(1,), (2,), (3,)],
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM students").fetchone()[0],
                    24,
                )
                self.assertEqual(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM student_school_year_assignments AS assignment
                        JOIN school_years AS school_year
                          ON school_year.school_year_id = assignment.school_year_id
                        WHERE assignment.assignment_status = 'enrolled'
                          AND school_year.status = 'current'
                        """
                    ).fetchone()[0],
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
