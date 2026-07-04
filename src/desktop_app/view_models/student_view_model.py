"""Student view models for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class StudentDocumentationSummaryViewModel:
    """Compact documentation progress for student lists and profile headers."""

    documented_learning_area_count: int
    total_learning_area_count: int
    status_label: str
    weak_subject_names: tuple[str, ...] = ()

    @property
    def list_label(self) -> str:
        """Return a compact label for student list rows."""
        if self.total_learning_area_count == 0:
            return "keine Katalogdaten"
        return (
            f"{self.documented_learning_area_count}/"
            f"{self.total_learning_area_count} Bereiche · {self.status_label}"
        )

    @property
    def profile_summary_label(self) -> str:
        """Return the profile summary label."""
        if self.total_learning_area_count == 0:
            return "Noch kein Kompetenzkatalog verfügbar."
        return (
            f"{self.documented_learning_area_count}/"
            f"{self.total_learning_area_count} Lernbereiche dokumentiert"
        )

    @property
    def weak_subjects_label(self) -> str:
        """Return up to three subjects that still need documentation."""
        if not self.weak_subject_names:
            return ""
        return "Noch wenig dokumentiert: " + ", ".join(self.weak_subject_names[:3])


def empty_documentation_summary() -> StudentDocumentationSummaryViewModel:
    """Return an empty documentation summary."""
    return StudentDocumentationSummaryViewModel(0, 0, "keine Dokumentation")


def documentation_summary_from_subjects(
    statuses: tuple[object, ...],
) -> StudentDocumentationSummaryViewModel:
    """Derive a compact documentation summary from per-subject statuses."""
    total = sum(getattr(status, "total_count", 0) for status in statuses)
    documented = sum(getattr(status, "documented_count", 0) for status in statuses)
    if total <= 0:
        return empty_documentation_summary()
    weak_subjects = tuple(
        getattr(status, "subject_display_name", "")
        for status in sorted(
            (
                status
                for status in statuses
                if getattr(status, "documented_count", 0)
                < getattr(status, "total_count", 0)
            ),
            key=lambda status: (
                _documentation_ratio(status),
                getattr(status, "sort_order", 0),
                getattr(status, "subject_display_name", ""),
            ),
        )
        if getattr(status, "subject_display_name", "")
    )
    return StudentDocumentationSummaryViewModel(
        documented,
        total,
        _documentation_status_label(documented, total),
        weak_subjects[:3],
    )


def _documentation_ratio(status: object) -> float:
    total = getattr(status, "total_count", 0)
    if total <= 0:
        return 0.0
    return getattr(status, "documented_count", 0) / total


def _documentation_status_label(documented: int, total: int) -> str:
    if total <= 0 or documented <= 0:
        return "keine Dokumentation"
    if documented >= total:
        return "vollständig"
    ratio = documented / total
    if ratio < 0.34:
        return "wenig dokumentiert"
    if ratio < 0.75:
        return "teilweise dokumentiert"
    return "gut dokumentiert"


@dataclass(frozen=True)
class StudentListItem:
    """Display-ready student row for desktop lists."""

    student_id: str
    first_name: str
    last_name: str
    group_id: str
    group_name: str
    course_id: str
    course_name: str
    course_color_name: str = ""
    course_color_hex: str = ""
    documentation_status: StudentDocumentationSummaryViewModel = field(
        default_factory=empty_documentation_summary
    )

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


def filter_student_list(
    students: tuple[StudentListItem, ...],
    search_text: str,
) -> tuple[StudentListItem, ...]:
    """Filter loaded students for the desktop list."""
    query = search_text.strip().casefold()
    if not query:
        return students

    return tuple(
        student
        for student in students
        if _student_matches_query(student, query)
    )


def sort_student_list(
    students: tuple[StudentListItem, ...],
    course_order_by_id: dict[str, int],
) -> tuple[StudentListItem, ...]:
    """Sort students by course order and then by visible name."""
    return tuple(
        sorted(
            students,
            key=lambda student: (
                course_order_by_id.get(student.course_id, len(course_order_by_id)),
                student.display_name.casefold(),
                student.student_id,
            ),
        )
    )


def _student_matches_query(student: StudentListItem, query: str) -> bool:
    searchable_values = (
        student.first_name,
        student.last_name,
        student.display_name,
        student.group_name,
        student.course_name,
    )
    return any(query in value.casefold() for value in searchable_values)


@dataclass(frozen=True)
class StudentDetailViewModel:
    """Display model for the light student profile."""

    student_id: str
    display_name: str
    group_name: str
    course_name: str
    student_notes: str
    active: bool


@dataclass(frozen=True)
class StudentDocumentViewModel:
    """Display-ready document or media metadata for a student."""

    document_id: str
    student_id: str
    observation_id: str
    title: str
    document_type: str
    file_path: str
    original_filename: str
    created_at: str
    note: str = ""

    @property
    def display_title(self) -> str:
        """Return the primary document title."""
        return self.title or self.original_filename

    @property
    def created_date_label(self) -> str:
        """Return the compact creation date."""
        return self.created_at[:10]

    @property
    def observation_link_label(self) -> str:
        """Return a visible observation-link hint."""
        if not self.observation_id:
            return ""
        return f"mit Beobachtung {self.observation_id} verknüpft"


PROFILE_ACTION_MESSAGES = {
    "observation": "Bitte zuerst einen Schüler auswählen.",
    "document": "Dokumente werden in einem späteren Sprint verwaltet.",
    "edit": "Bearbeiten wird in einem späteren Sprint umgesetzt.",
}

PROFILE_SECTION_PLACEHOLDERS = {
    "observations_title": "Noch keine Beobachtungen vorhanden.",
    "observations_hint": "Gespeicherte Beobachtungen erscheinen hier chronologisch.",
    "competencies_title": "Noch keine Kompetenzbewertungen vorhanden.",
    "competencies_hint": "Kompetenzen erscheinen hier, sobald Beobachtungen bewertet wurden.",
    "documents_title": "Noch keine Dokumente hinterlegt.",
    "documents_hint": "Dokumente werden schülerzentriert verwaltet.",
}

REPORT_NO_OBSERVATIONS_MESSAGE = "Noch keine Beobachtungen dokumentiert."


@dataclass(frozen=True)
class GroupSummaryViewModel:
    """Display model for overview group cards."""

    group_id: str
    group_name: str
    active_student_count: int


@dataclass(frozen=True)
class StudentReportCompetencyViewModel:
    """Report-preview competency line derived from observed status."""

    competency_id: str
    competency_label: str
    rating: str
    rating_source: str
    rating_label: str

    @property
    def display_label(self) -> str:
        """Return a compact report-preview line."""
        return f"{self.competency_label} · {self.rating_source}: {self.rating}"


@dataclass(frozen=True)
class StudentReportDevelopmentViewModel:
    """Report-preview development line derived from observation history."""

    competency_id: str
    competency_label: str
    development_label: str
    rating_history: tuple[str, ...]

    @property
    def display_label(self) -> str:
        """Return a readable development line."""
        return f"{self.competency_label} · {self.development_label}"


@dataclass(frozen=True)
class StudentReportEvidenceViewModel:
    """Observation snippet used as evidence in the report preview."""

    observation_id: str
    date_text: str
    context: str
    note_preview: str
    competency_labels: tuple[str, ...]

    @property
    def display_label(self) -> str:
        """Return a compact evidence label."""
        parts = [self.date_text]
        if self.context:
            parts.append(self.context)
        if self.note_preview:
            parts.append(self.note_preview)
        return " · ".join(parts)


@dataclass(frozen=True)
class StudentReportSubjectSectionViewModel:
    """One subject section in the student report preview."""

    subject_id: str
    subject_display_name: str
    strengths: tuple[StudentReportCompetencyViewModel, ...]
    development: tuple[StudentReportDevelopmentViewModel, ...]
    support_needs: tuple[StudentReportCompetencyViewModel, ...]
    example_observations: tuple[StudentReportEvidenceViewModel, ...]

    @property
    def has_content(self) -> bool:
        """Return whether the section contains report-relevant data."""
        return any((
            self.strengths,
            self.development,
            self.support_needs,
            self.example_observations,
        ))


@dataclass(frozen=True)
class StudentReportPreviewViewModel:
    """Structured, derived report preparation for one student."""

    student_id: str
    student_name: str
    subject_sections: tuple[StudentReportSubjectSectionViewModel, ...]

    @property
    def has_content(self) -> bool:
        """Return whether report preview data is available."""
        return bool(self.subject_sections)


def format_student_report_preview_text(
    student: StudentDetailViewModel,
    report_preview: StudentReportPreviewViewModel | None,
    created_date: str | None = None,
) -> str:
    """Return a reusable plain-text report preparation."""
    report_date = created_date or date.today().isoformat()
    lines = [
        "Berichtsvorbereitung",
        "",
        f"Schüler: {student.display_name}",
    ]
    if student.group_name:
        lines.append(f"Stammgruppe: {student.group_name}")
    if student.course_name:
        lines.append(f"Kurs: {student.course_name}")
    lines.extend([
        f"Erstellt am: {report_date}",
        "",
    ])
    if report_preview is None or not report_preview.has_content:
        lines.append(REPORT_NO_OBSERVATIONS_MESSAGE)
        return "\n".join(lines).rstrip() + "\n"
    for section in report_preview.subject_sections:
        lines.extend(_format_report_subject_section(section))
    return "\n".join(lines).rstrip() + "\n"


def _format_report_subject_section(
    section: StudentReportSubjectSectionViewModel,
) -> list[str]:
    lines = [
        f"## {section.subject_display_name}",
        "",
        "Stärken",
        *_format_report_competencies(section.strengths),
        "",
        "Entwicklung",
        *_format_report_competencies(section.development),
        "",
        "Unterstützungsbedarf",
        *_format_report_competencies(section.support_needs),
        "",
        "Beispielbeobachtungen",
        *_format_report_evidence(section.example_observations),
        "",
    ]
    return lines


def _format_report_competencies(
    competencies: tuple[object, ...],
) -> list[str]:
    if not competencies:
        return ["- Keine Einträge."]
    return [f"- {competency.display_label}" for competency in competencies]


def _format_report_evidence(
    observations: tuple[StudentReportEvidenceViewModel, ...],
) -> list[str]:
    if not observations:
        return ["- Keine passenden Beobachtungen."]
    lines: list[str] = []
    for observation in observations:
        lines.append(f"- {observation.display_label}")
        lines.extend(
            f"  - {competency_label}"
            for competency_label in observation.competency_labels
        )
    return lines
