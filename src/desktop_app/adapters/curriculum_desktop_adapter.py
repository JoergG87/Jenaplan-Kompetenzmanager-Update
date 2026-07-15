"""Read-only curriculum catalog adapter for the PySide6 desktop app."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from src.core.sqlite_store import (
    CompetencyRecord,
    SQLiteCompetencyRepository,
    SQLiteDatabase,
)
from src.desktop_app.runtime import resource_path


CURRICULUM_CATALOG_V1_PATH = resource_path("data", "curriculum_catalog_v1.csv")

CATALOG_REQUIRED_FIELDS = (
    "competency_id",
    "subject_key",
    "subject_display_name",
    "learning_area",
    "competency_group",
    "competency_text",
)

LEARNING_STAGE_VALUES = {"stage_1_3", "stage_4", "cross_stage"}
CATALOG_STATUS_VALUES = {"current", "legacy"}

DOCUMENTATION_SUBJECT_PREFERRED_ORDER = (
    "deutsch",
    "mathematik",
    "epu",
    "musik",
    "kunst",
    "sport",
    "sozialkompetenz",
    "ethik",
    "religion",
    "werken",
    "schulgarten",
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
    learning_stage: str
    learning_area: str
    competency_group: str
    competency_text: str
    catalog_label: str
    source_reference: str
    catalog_status: str
    catalog_default_active: bool
    activation_group_key: str
    is_core_subject: bool
    is_active: bool

    @property
    def subject_id(self) -> str:
        """Return the stable subject key used by observation persistence."""
        return self.subject_key

    @property
    def competency_label(self) -> str:
        """Return the user-facing competency selection label."""
        return self.catalog_label or self.competency_display_name

    @property
    def competency_display_name(self) -> str:
        """Return the short label used in the observation dialog."""
        return self.catalog_label or self.learning_area

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

    def __init__(
        self,
        catalog_path: Path = CURRICULUM_CATALOG_V1_PATH,
        database: SQLiteDatabase | None = None,
    ) -> None:
        self.catalog_path = catalog_path
        self.database = database

    def list_entries(self) -> tuple[CurriculumCatalogEntry, ...]:
        """Return all catalog entries."""
        if self.database is not None:
            return tuple(
                self._entry_from_competency_record(competency)
                for competency in SQLiteCompetencyRepository(
                    self.database
                ).list_competencies()
            )
        with self.catalog_path.open(newline="", encoding="utf-8") as csv_file:
            entries = tuple(
                self._entry_from_row(row)
                for row in csv.DictReader(csv_file, delimiter=";")
            )
        self._validate_unique_competency_ids(entries)
        return entries

    def list_active_subjects(self) -> tuple[CurriculumSubjectOption, ...]:
        """Return active subject options in the canonical subject order."""
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
                key=lambda subject: (
                    DOCUMENTATION_SUBJECT_PREFERRED_ORDER.index(subject.subject_key)
                    if subject.subject_key in DOCUMENTATION_SUBJECT_PREFERRED_ORDER
                    else len(DOCUMENTATION_SUBJECT_PREFERRED_ORDER),
                    subject.display_name.casefold(),
                    subject.subject_key,
                ),
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
        catalog_default_active = self._parse_optional_bool(
            row,
            "catalog_default_active",
            self._parse_bool(row["is_active"]),
        )
        learning_stage = self._validated_optional_value(
            row,
            "learning_stage",
            "cross_stage",
            LEARNING_STAGE_VALUES,
        )
        catalog_status = self._validated_optional_value(
            row,
            "catalog_status",
            "current",
            CATALOG_STATUS_VALUES,
        )
        return CurriculumCatalogEntry(
            competency_id=row["competency_id"].strip(),
            subject_key=row["subject_key"],
            subject_display_name=row["subject_display_name"],
            subject_full_name=row["subject_full_name"],
            official_subject_name=row["official_subject_name"],
            school_context_name=row["school_context_name"],
            grade_band=row["grade_band"],
            learning_stage=learning_stage,
            learning_area=row["learning_area"],
            competency_group=row["competency_group"],
            competency_text=row["competency_text"],
            catalog_label=row.get("competency_label", "").strip(),
            source_reference=row["source_reference"],
            catalog_status=catalog_status,
            catalog_default_active=catalog_default_active,
            activation_group_key=row.get("activation_group_key", "").strip(),
            is_core_subject=self._parse_bool(row["is_core_subject"]),
            is_active=catalog_default_active,
        )

    def _entry_from_competency_record(
        self,
        competency: CompetencyRecord,
    ) -> CurriculumCatalogEntry:
        return CurriculumCatalogEntry(
            competency_id=competency.competency_id,
            subject_key=competency.subject_id,
            subject_display_name=competency.subject_name,
            subject_full_name=competency.subject_full_name,
            official_subject_name=competency.official_subject_name,
            school_context_name=competency.school_context_name,
            grade_band=competency.grade_band,
            learning_stage=competency.learning_stage,
            learning_area=competency.learning_area,
            competency_group=competency.competency_group,
            competency_text=competency.description,
            catalog_label=competency.label,
            source_reference=competency.source_reference,
            catalog_status=competency.catalog_status,
            catalog_default_active=competency.catalog_default_active,
            activation_group_key=competency.activation_group_key,
            is_core_subject=competency.is_core_subject,
            is_active=competency.active,
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

    def _parse_optional_bool(
        self,
        row: dict[str, str],
        field_name: str,
        default: bool,
    ) -> bool:
        value = row.get(field_name)
        if value is None or not value.strip():
            return default
        normalized = value.strip().casefold()
        if normalized not in {"true", "false"}:
            raise ValueError(
                f"Curriculum catalog field {field_name} must be true or false."
            )
        return normalized == "true"

    def _validated_optional_value(
        self,
        row: dict[str, str],
        field_name: str,
        default: str,
        allowed_values: set[str],
    ) -> str:
        value = row.get(field_name, "").strip()
        if not value:
            return default
        if value not in allowed_values:
            allowed = ", ".join(sorted(allowed_values))
            raise ValueError(
                f"Curriculum catalog field {field_name} has unsupported value "
                f"{value!r}; allowed values: {allowed}."
            )
        return value
