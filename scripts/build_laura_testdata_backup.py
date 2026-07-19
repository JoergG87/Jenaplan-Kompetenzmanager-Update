"""Build and verify Laura's synthetic eight-month pilot backup."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.seed_test_data import SeedResult, seed_test_data
from src.application.commands.backup import (
    BackupApplicationService,
    CreateBackupCommand,
    VerifyBackupQuery,
)
from src.desktop_app.runtime import runtime_paths


BACKUP_CREATED_AT = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
FORBIDDEN_RUNTIME_NAMES = {
    "app-preferences.json",
    "enrollment.marker",
    "security.sqlite",
}


def build_laura_testdata_backup(
    *,
    output_directory: Path,
    version: str,
    build_commit: str,
    source_tree_state: str | None,
) -> tuple[Path, SeedResult]:
    """Create one official backup from an isolated synthetic runtime."""
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    final_path = output_directory / f"Laura-Testdaten-{version}.jkmbackup"
    final_path.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="jenaplan-laura-testdata-") as temp_name:
        work_root = Path(temp_name)
        paths = runtime_paths(work_root / "runtime")
        seed_result = seed_test_data(paths.database, reset=True)
        _assert_runtime_contains_only_business_data(paths.root)

        service = BackupApplicationService(now=lambda: BACKUP_CREATED_AT)
        created = service.create(
            CreateBackupCommand(
                database_path=paths.database,
                runtime_paths=paths,
                target_path=work_root / "backups",
                app_version=version,
                build_commit=build_commit,
                source_tree_state=source_tree_state,
            )
        )
        shutil.copy2(created.path, final_path)

    verification = BackupApplicationService().verify(VerifyBackupQuery(final_path))
    _assert_expected_seed_counts(verification.manifest.counts, seed_result)
    _assert_archive_contains_no_security_material(final_path)
    return final_path, seed_result


def _assert_runtime_contains_only_business_data(runtime_root: Path) -> None:
    forbidden = [
        path
        for path in runtime_root.rglob("*")
        if path.name in FORBIDDEN_RUNTIME_NAMES or "security" in path.parts
    ]
    if forbidden:
        raise RuntimeError(
            "Der synthetische Quellbestand enthält unerlaubte Sicherheitsdaten: "
            + ", ".join(str(path.relative_to(runtime_root)) for path in forbidden)
        )


def _assert_expected_seed_counts(counts, seed_result: SeedResult) -> None:
    expected = (
        seed_result.student_count,
        seed_result.observation_count,
        seed_result.report_revision_count,
        seed_result.conference_revision_count,
    )
    actual = (
        counts.students,
        counts.observations,
        counts.learning_report_revisions,
        counts.learning_conference_revisions,
    )
    if actual != expected:
        raise RuntimeError(
            f"Backup-Zählwerte stimmen nicht mit dem Seed überein: {actual} != {expected}"
        )


def _assert_archive_contains_no_security_material(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = tuple(archive.namelist())
    forbidden_tokens = (
        "security",
        "credential",
        "password",
        "recovery",
        "token",
        "private-key",
        "public-key",
        "enrollment.marker",
        "app-preferences.json",
    )
    offenders = [
        name for name in names if any(token in name.casefold() for token in forbidden_tokens)
    ]
    if offenders:
        raise RuntimeError(
            "Das Backup enthält unerlaubte Sicherheitsartefakte: " + ", ".join(offenders)
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--build-commit", required=True)
    parser.add_argument("--source-tree-state", choices=("clean", "dirty"))
    args = parser.parse_args()
    path, result = build_laura_testdata_backup(
        output_directory=args.output_directory,
        version=args.version,
        build_commit=args.build_commit,
        source_tree_state=args.source_tree_state,
    )
    print(path)
    print(f"Schueler: {result.student_count}")
    print(f"Beobachtungen: {result.observation_count}")
    print(f"Dokumente/Medien: {result.document_count}")
    print(f"Stundenplaneintraege: {result.timetable_count}")
    print(f"Berichtsentwuerfe: {result.report_draft_count}")
    print(f"Berichtrevisionen: {result.report_revision_count}")
    print(f"LEG-Entwuerfe: {result.conference_draft_count}")
    print(f"LEG-Revisionen: {result.conference_revision_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
