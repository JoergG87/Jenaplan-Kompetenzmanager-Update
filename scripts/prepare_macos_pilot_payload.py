"""Prepare explicit empty-smoke or fictional Laura payloads for macOS."""

from __future__ import annotations

import argparse
import json
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
from src.core.runtime_root_protection import require_unprotected_output_path


def prepare_payload(
    output_dir: Path,
    *,
    data_mode: str,
    version: str,
    git_commit: str,
    source_tree_state: str,
    architecture: str,
    test_profile: Path | None = None,
) -> Path:
    """Create build metadata and optional explicitly fictional initial data."""
    output_dir = Path(output_dir)
    profile = None
    if test_profile is not None:
        from scripts.macos_package_profile import load_profile
        profile = load_profile(test_profile, before_build=False)
        if data_mode != "empty" or output_dir != Path(profile.build_root) / "payload":
            raise ValueError("test_profile_invalid")
    require_unprotected_output_path(output_dir)
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("Das Payload-Ziel muss vollständig neu sein.")
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
        "release_channel": "pilot",
        "pilot_features": ["guided_testdata_restore", "sparkle_updates"],
        "source_tree_state": source_tree_state,
    }
    if profile is not None:
        build_info.update(
            app_name=profile.app_name, bundle_id=profile.bundle_id,
            installation_id=profile.installation_id, package_profile="internal-test",
            release_channel="internal-test", pilot_features=[],
            pilot_data_label="Internes synthetisches Testpaket – nicht zur Verteilung",
        )
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
    parser.add_argument("--test-profile", type=Path)
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
        test_profile=args.test_profile,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
