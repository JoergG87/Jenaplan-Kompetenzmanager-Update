"""Read-only curriculum catalog adapter for the PySide6 desktop app."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


CURRICULUM_CATALOG_V1_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "curriculum_catalog_v1.csv"
)

CATALOG_REQUIRED_FIELDS = (
    "competency_id",
    "subject_key",
    "subject_display_name",
    "learning_area",
    "competency_group",
    "competency_text",
)


@dataclass(frozen=True)
class CurriculumCatalogEntry:
    """One row in the curriculum catalog v1."""

    competency_id: str
    subject_key: str
    subject_display_name: str
    subject_full_name: str
    official_subject_name: str
    school_context_name: str
    grade_band: str
    learning_area: str
    competency_group: str
    competency_text: str
    source_reference: str
    is_core_subject: bool
    is_active: bool

    @property
    def subject_id(self) -> str:
        """Return the stable subject key used by observation persistence."""
        return self.subject_key

    @property
    def competency_label(self) -> str:
        """Return the user-facing competency selection label."""
        return self.competency_display_name

    @property
    def competency_display_name(self) -> str:
        """Return the short label used in the observation dialog."""
        return self.learning_area

    @property
    def competency_detail_label(self) -> str:
        """Return the full catalog detail text for tooltips or later detail views."""
        return (
            f"{self.learning_area} - {self.competency_group}: "
            f"{self.competency_text}"
        )


@dataclass(frozen=True)
class CurriculumSubjectOption:
    """Display option for a subject in the observation dialog."""

    subject_key: str
    display_name: str
    is_core_subject: bool


@dataclass(frozen=True)
class CurriculumCompetencyGroup:
    """Active competencies grouped by one subject."""

    subject: CurriculumSubjectOption
    competencies: tuple[CurriculumCatalogEntry, ...]


class CurriculumDesktopAdapter:
    """Load curriculum catalog data for desktop UI selection controls."""

    def __init__(self, catalog_path: Path = CURRICULUM_CATALOG_V1_PATH) -> None:
        self.catalog_path = catalog_path

    def list_entries(self) -> tuple[CurriculumCatalogEntry, ...]:
        """Return all catalog entries."""
        with self.catalog_path.open(newline="", encoding="utf-8") as csv_file:
            entries = tuple(
                self._entry_from_row(row)
                for row in csv.DictReader(csv_file, delimiter=";")
            )
        self._validate_unique_competency_ids(entries)
        return entries

    def list_active_subjects(self) -> tuple[CurriculumSubjectOption, ...]:
        """Return active subject options, core subjects first."""
        subject_by_key: dict[str, CurriculumSubjectOption] = {}
        for entry in self.list_entries():
            if not entry.is_active:
                continue
            subject_by_key.setdefault(
                entry.subject_key,
                CurriculumSubjectOption(
                    subject_key=entry.subject_key,
                    display_name=entry.subject_display_name,
                    is_core_subject=entry.is_core_subject,
                ),
            )
        return tuple(
            sorted(
                subject_by_key.values(),
                key=lambda subject: (not subject.is_core_subject, list(subject_by_key).index(subject.subject_key)),
            )
        )

    def list_competencies_for_subject(
        self,
        subject_key: str,
    ) -> tuple[CurriculumCatalogEntry, ...]:
        """Return active competency catalog rows for one subject."""
        return tuple(
            entry
            for entry in self.list_entries()
            if entry.is_active and entry.subject_key == subject_key
        )

    def list_competencies_grouped_by_subject(self) -> tuple[CurriculumCompetencyGroup, ...]:
        """Return active competencies grouped by their visible subject."""
        return tuple(
            CurriculumCompetencyGroup(
                subject,
                self.list_competencies_for_subject(subject.subject_key),
            )
            for subject in self.list_active_subjects()
        )

    def _entry_from_row(
        self,
        row: dict[str, str],
    ) -> CurriculumCatalogEntry:
        self._validate_required_fields(row)
        return CurriculumCatalogEntry(
            competency_id=row["competency_id"].strip(),
            subject_key=row["subject_key"],
            subject_display_name=row["subject_display_name"],
            subject_full_name=row["subject_full_name"],
            official_subject_name=row["official_subject_name"],
            school_context_name=row["school_context_name"],
            grade_band=row["grade_band"],
            learning_area=row["learning_area"],
            competency_group=row["competency_group"],
            competency_text=row["competency_text"],
            source_reference=row["source_reference"],
            is_core_subject=self._parse_bool(row["is_core_subject"]),
            is_active=self._parse_bool(row["is_active"]),
        )

    def _validate_required_fields(self, row: dict[str, str]) -> None:
        for field_name in CATALOG_REQUIRED_FIELDS:
            if not row.get(field_name, "").strip():
                raise ValueError(f"Curriculum catalog field is required: {field_name}")

    def _validate_unique_competency_ids(
        self,
        entries: tuple[CurriculumCatalogEntry, ...],
    ) -> None:
        seen_ids: set[str] = set()
        for entry in entries:
            if entry.competency_id in seen_ids:
                raise ValueError(
                    f"Duplicate curriculum competency_id: {entry.competency_id}"
                )
            seen_ids.add(entry.competency_id)

    def _parse_bool(self, value: str) -> bool:
        return value.strip().casefold() == "true"
