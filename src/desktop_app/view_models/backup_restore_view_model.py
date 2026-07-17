"""Privacy-minimized view models for the settings backup area."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BackupSummaryViewModel:
    created_at: str
    file_name: str
    size_bytes: int
    verified: bool

    @property
    def size_label(self) -> str:
        return f"{self.size_bytes / 1024 / 1024:.1f} MB"


@dataclass(frozen=True)
class RestorePreviewViewModel:
    created_at: str
    app_version: str
    compatibility_status: str
    students_count: int
    observations_count: int
    learning_report_revisions_count: int
    learning_conference_revisions_count: int
    managed_files_count: int
    external_references_count: int
    external_missing_count: int
    archive_path: Path
    restore_id: str = ""

    @classmethod
    def from_preview(cls, preview: object, status: str, path: Path, *, restore_id: str = "") -> "RestorePreviewViewModel":
        return cls(
            created_at=preview.created_at,
            app_version=preview.app_version,
            compatibility_status=status,
            students_count=preview.students_count,
            observations_count=preview.observations_count,
            learning_report_revisions_count=preview.learning_report_revisions_count,
            learning_conference_revisions_count=preview.learning_conference_revisions_count,
            managed_files_count=preview.managed_files_count,
            external_references_count=preview.external_references_count,
            external_missing_count=preview.external_missing_count,
            archive_path=Path(path),
            restore_id=restore_id,
        )
