"""Display-only Qt mapping for the SJ-3B.1 transition preview."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.school_year_transition import (
    SchoolYearTransitionPreview,
    SchoolYearTransitionPreviewItem,
    SchoolYearTransitionTargetStatus,
)


EMPTY_VALUE = "—"

_TARGET_STATUS_LABELS = {
    SchoolYearTransitionTargetStatus.ADVANCE_1_TO_2: "Wechsel 1 → 2",
    SchoolYearTransitionTargetStatus.ADVANCE_2_TO_3: "Wechsel 2 → 3",
    SchoolYearTransitionTargetStatus.UNRESOLVED: "Ungelöst",
}

_ISSUE_LABELS = {
    "CURRENT_ASSIGNMENT_AMBIGUOUS": "Bisherige Zuordnung ist nicht eindeutig.",
    "CURRENT_ASSIGNMENT_MISSING": "Bisherige Zuordnung fehlt.",
    "CURRENT_ASSIGNMENT_STATUS_INVALID": "Bisheriger Zuordnungsstatus ist ungültig.",
    "CURRENT_COURSE_INVALID": "Bisheriger Kurs ist nicht gültig.",
    "CURRENT_GROUP_INVALID": "Bisherige Stammgruppe ist nicht gültig.",
    "CURRENT_SCHOOL_YEAR_AMBIGUOUS": "Aktuelles Schuljahr ist nicht eindeutig.",
    "CURRENT_SCHOOL_YEAR_MISSING": "Aktuelles Schuljahr fehlt.",
    "CURRENT_SCHOOL_YEAR_UNAVAILABLE": "Aktuelles Schuljahr ist nicht verfügbar.",
    "CURRENT_YEAR_LEVEL_INVALID": "Bisherige Kursstufe ist nicht gültig.",
    "NEW_SCHOOL_YEAR_DATE_INVALID": "Zeitraum des neuen Schuljahres ist ungültig.",
    "NEW_SCHOOL_YEAR_DATE_RANGE_INVALID": "Zeitraum des neuen Schuljahres ist ungültig.",
    "NEW_SCHOOL_YEAR_LABEL_INVALID": "Bezeichnung des neuen Schuljahres fehlt.",
    "NEW_SCHOOL_YEAR_NOT_AFTER_CURRENT": (
        "Das neue Schuljahr liegt nicht nach dem aktuellen Schuljahr."
    ),
    "NEW_SCHOOL_YEAR_OVERLAP": "Das neue Schuljahr überschneidet ein vorhandenes.",
    "SCHOOL_YEAR_GAP": "Zwischen den Schuljahren besteht eine Lücke.",
    "STUDENT_ARCHIVED": "Kind ist archiviert.",
    "STUDENT_EXITED": "Kind ist ausgeschieden.",
    "TARGET_COURSE_AMBIGUOUS": "Zielkurs ist nicht eindeutig.",
    "TARGET_COURSE_MISSING": "Passender Zielkurs fehlt.",
    "YEAR_LEVEL_THREE_SELECTION_REQUIRED": (
        "Für Kursstufe 3 ist eine spätere Entscheidung erforderlich."
    ),
}


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPreviewRowViewModel:
    """One display-ready row in unchanged preview order."""

    student_id: str
    child_label: str
    current_group_label: str
    current_course_label: str
    current_year_level_label: str
    proposed_group_label: str
    proposed_course_label: str
    target_status_label: str
    warnings_label: str
    resolved: bool
    accessible_description: str


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPreviewViewModel:
    """Complete display mapping of one existing transition preview."""

    current_school_year_label: str
    planned_school_year_label: str
    period_label: str
    student_count: int
    advance_1_to_2_count: int
    advance_2_to_3_count: int
    unresolved_count: int
    status_label: str
    status_description: str
    rows: tuple[SchoolYearTransitionPreviewRowViewModel, ...]
    global_issues_label: str

    @classmethod
    def from_preview(
        cls,
        preview: SchoolYearTransitionPreview,
    ) -> "SchoolYearTransitionPreviewViewModel":
        """Map only existing projection values without reordering or validation."""
        rows = tuple(_row_from_item(item) for item in preview.items)
        complete = preview.executable
        status_label = (
            "Vorschau vollständig"
            if complete
            else "Entscheidungen erforderlich"
        )
        status_description = (
            "Alle Vorschläge sind vollständig."
            if complete
            else (
                f"{preview.unresolved_count} von {preview.student_count} "
                "Kindern sind noch ungelöst."
            )
        )
        global_issues = tuple(
            _issue_label(issue.code)
            for issue in preview.validation_issues
            if issue.student_id is None
        )
        return cls(
            current_school_year_label=(
                preview.current_school_year.label
                if preview.current_school_year is not None
                else "Nicht eindeutig verfügbar"
            ),
            planned_school_year_label=preview.planned_school_year.label,
            period_label=_period_label(
                preview.planned_school_year.start_date,
                preview.planned_school_year.end_date,
            ),
            student_count=preview.student_count,
            advance_1_to_2_count=preview.advance_1_to_2_count,
            advance_2_to_3_count=preview.advance_2_to_3_count,
            unresolved_count=preview.unresolved_count,
            status_label=status_label,
            status_description=status_description,
            rows=rows,
            global_issues_label=" ".join(global_issues),
        )


def _row_from_item(
    item: SchoolYearTransitionPreviewItem,
) -> SchoolYearTransitionPreviewRowViewModel:
    issue_codes = tuple(dict.fromkeys(item.warning_codes + item.blocker_codes))
    warnings_label = (
        " ".join(_issue_label(code) for code in issue_codes)
        if issue_codes
        else "Keine"
    )
    target_status_label = _TARGET_STATUS_LABELS[item.target_status]
    current_group_label = item.current_group_name or EMPTY_VALUE
    current_course_label = item.current_course_name or EMPTY_VALUE
    current_year_level_label = _year_level_label(item.current_year_level)
    proposed_group_label = item.proposed_group_name or EMPTY_VALUE
    proposed_course_label = item.proposed_course_name or EMPTY_VALUE
    accessible_description = (
        f"Kind {item.student_id}. "
        f"Bisherige Stammgruppe {current_group_label}. "
        f"Bisheriger Kurs {current_course_label}. "
        f"Bisherige Kursstufe {current_year_level_label}. "
        f"Vorgeschlagene Stammgruppe {proposed_group_label}. "
        f"Vorgeschlagener Kurs {proposed_course_label}. "
        f"Zielstatus {target_status_label}. "
        f"Warnungen {warnings_label}"
    )
    return SchoolYearTransitionPreviewRowViewModel(
        student_id=item.student_id,
        child_label=item.student_id,
        current_group_label=current_group_label,
        current_course_label=current_course_label,
        current_year_level_label=current_year_level_label,
        proposed_group_label=proposed_group_label,
        proposed_course_label=proposed_course_label,
        target_status_label=target_status_label,
        warnings_label=warnings_label,
        resolved=item.resolved,
        accessible_description=accessible_description,
    )


def _issue_label(code: str) -> str:
    return _ISSUE_LABELS.get(code, f"Hinweis: {code}")


def _year_level_label(year_level: int | None) -> str:
    return f"Stufe {year_level}" if year_level is not None else EMPTY_VALUE


def _period_label(start_date: object, end_date: object) -> str:
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        return "Nicht verfügbar"
    return f"{start_date:%d.%m.%Y} – {end_date:%d.%m.%Y}"
