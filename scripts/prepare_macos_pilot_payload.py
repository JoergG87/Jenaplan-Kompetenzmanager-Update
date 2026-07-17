"""Prepare explicit empty-smoke or fictional Laura payloads for macOS."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from pathlib import Path

try:
    from scripts.seed_test_data import seed_test_data
except ModuleNotFoundError:  # direct execution keeps scripts/ on sys.path
    from seed_test_data import seed_test_data
from src.desktop_app.runtime import (
    BUILD_INFO_FILENAME,
    DATABASE_FILENAME,
    INITIAL_DATA_DIRECTORY,
    INITIAL_PATH_TOKEN,
)


def prepare_payload(
    output_dir: Path,
    *,
    data_mode: str,
    version: str,
    git_commit: str,
    source_tree_state: str,
    architecture: str,
) -> Path:
    """Create build metadata and optional explicitly fictional initial data."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    build_info = {
        "app_version": version,
        "architecture": architecture,
        "data_mode": data_mode,
        "git_commit": git_commit,
        "packaged": True,
        "real_student_data_included": False,
        "pilot_data_label": {
            "laura": "Fiktive Pilotdaten",
            "empty": "Technischer Smoke-Test - leer",
            "release": "Release-Kandidat - leer",
        }[data_mode],
        "source_tree_state": source_tree_state,
    }
    (output_dir / BUILD_INFO_FILENAME).write_text(
        json.dumps(build_info, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if data_mode == "laura":
        initial_root = output_dir / INITIAL_DATA_DIRECTORY
        database_path = initial_root / DATABASE_FILENAME
        seed_test_data(database_path, reset=True)
        _normalize_pilot_document_paths(database_path, initial_root)
        (initial_root / "FIKTIVE_PILOTDATEN.txt").write_text(
            "Fiktive Pilotdaten - keine echten Schülerdaten.\n",
            encoding="utf-8",
        )
    elif data_mode not in {"empty", "release"}:
        raise ValueError(f"Unbekannte Pilotdaten-Variante: {data_mode}")
    return output_dir


def _normalize_pilot_document_paths(database_path: Path, initial_root: Path) -> None:
    """Remove all build-machine paths from the fictional pilot database."""
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT document_id, file_path FROM documents"
        ).fetchall()
        for document_id, file_path in rows:
            path = Path(file_path)
            try:
                relative = path.relative_to(initial_root)
            except ValueError as error:
                raise ValueError(
                    f"Demo-Dokument liegt außerhalb des Pilotpayloads: {path}"
                ) from error
            connection.execute(
                "UPDATE documents SET file_path = ? WHERE document_id = ?",
                (f"{INITIAL_PATH_TOKEN}/{relative.as_posix()}", document_id),
            )
        connection.commit()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--data-mode",
        choices=("empty", "laura", "release"),
        required=True,
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--source-tree-state", choices=("clean", "dirty"), required=True)
    parser.add_argument("--architecture", required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    prepare_payload(
        args.output,
        data_mode=args.data_mode,
        version=args.version,
        git_commit=args.git_commit,
        source_tree_state=args.source_tree_state,
        architecture=args.architecture,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
