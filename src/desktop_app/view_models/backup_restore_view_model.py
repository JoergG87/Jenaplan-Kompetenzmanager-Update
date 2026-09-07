"""Privacy-minimized view models for the settings backup area."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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
class BackupReminderViewModel:
    state: str
    status_text: str
    message: str


def build_backup_reminder(
    summary: BackupSummaryViewModel | None,
    *,
    now: datetime,
    checked: bool,
) -> BackupReminderViewModel:
    """Project a quiet reminder solely from a verified creation timestamp."""
    unknown = BackupReminderViewModel(
        "unknown", "Sicherungsstand nicht bestätigt",
        "Der Sicherungsstand ist noch nicht bestätigt. Prüfe eine vorhandene Sicherung oder erstelle eine neue.",
    )
    if not checked:
        return unknown
    if summary is None:
        return BackupReminderViewModel(
            "missing", "Noch keine geprüfte Sicherung gefunden",
            "Es wurde noch keine geprüfte lokale Sicherung gefunden. Erstelle eine Sicherung über „Backup erstellen“.",
        )
    if not summary.verified:
        return unknown
    try:
        created_at = datetime.fromisoformat(summary.created_at)
    except (TypeError, ValueError):
        return unknown
    if created_at.tzinfo is None:
        return unknown
    age = now.astimezone(UTC) - created_at.astimezone(UTC)
    if age < timedelta(0):
        return unknown
    if age >= timedelta(days=7):
        return BackupReminderViewModel(
            "due", f"Geprüfte Sicherung vor {age.days} Tagen · neue Sicherung empfohlen",
            f"Die letzte bestätigte Sicherung ist {age.days} Tage alt. Erstelle eine aktuelle Sicherung über „Backup erstellen“.",
        )
    return BackupReminderViewModel(
        "current", f"Geprüfte Sicherung vom {created_at.astimezone().strftime('%d.%m.%Y')}", "",
    )


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
    restore_state: str = ""

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
            restore_state=("RESTORE_READY" if restore_id else ""),
        )
