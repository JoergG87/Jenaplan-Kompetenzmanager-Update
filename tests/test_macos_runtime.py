"""Deployment checks for safe macOS runtime paths and initial data."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
import json
from pathlib import Path

from src.desktop_app.runtime import (
    APP_DATA_DIR_ENV,
    DATABASE_FILENAME,
    INITIAL_DATA_DIRECTORY,
    INITIAL_PATH_TOKEN,
    RuntimeStorageError,
    application_data_root,
    prepare_runtime_storage,
)
from scripts.prepare_macos_pilot_payload import prepare_payload


class MacosRuntimeTest(unittest.TestCase):
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
