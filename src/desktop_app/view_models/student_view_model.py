"""Student view models for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass


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
    development: tuple[StudentReportCompetencyViewModel, ...]
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
