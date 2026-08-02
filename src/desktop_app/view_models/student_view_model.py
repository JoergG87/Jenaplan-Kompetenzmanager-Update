"""Student view models for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.desktop_app.view_models.observation_view_model import (
    ObservationListItem,
    StudentCompetencyCockpitViewModel,
    StudentCompetencySubjectGroup,
    StudentDocumentationSubjectStatus,
    observation_rating_label,
)


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
        return "Noch wenig belegt: " + ", ".join(self.weak_subject_names[:3])


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
    course_color_name: str = ""
    course_color_hex: str = ""
    resolution_status: str = "enrolled"
    status_label: str = ""
    membership_blocking: bool = False


@dataclass(frozen=True)
class DashboardDocumentationCellViewModel:
    """Neutral documentation coverage for one group and subject."""

    subject_id: str
    subject_display_name: str
    documented_count: int
    total_count: int

    @property
    def coverage_ratio(self) -> float:
        """Return display-only coverage without interpreting performance."""
        if self.total_count <= 0:
            return 0.0
        return self.documented_count / self.total_count

    @property
    def coverage_label(self) -> str:
        """Return an explicitly documentation-only label."""
        return f"{self.documented_count} / {self.total_count} Kinder dokumentiert"


@dataclass(frozen=True)
class DashboardDocumentationGroupViewModel:
    """Documentation cells for one active student group."""

    group_id: str
    group_name: str
    cells: tuple[DashboardDocumentationCellViewModel, ...]


@dataclass(frozen=True)
class DashboardDocumentationHeatmapViewModel:
    """Group-by-subject documentation overview without achievement values."""

    groups: tuple[DashboardDocumentationGroupViewModel, ...]

    @property
    def is_empty(self) -> bool:
        return not self.groups or not any(group.cells for group in self.groups)


@dataclass(frozen=True)
class DashboardSuggestedStudentViewModel:
    """One neutral documentation suggestion for the highlighted lesson."""

    student_id: str
    display_name: str
    documentation_hint: str
    last_documentation_date: date | None = None
    documented_today: bool = False
    course_name: str = ""
    course_color_name: str = ""
    course_color_hex: str = ""


@dataclass(frozen=True)
class StudentProfileOverviewViewModel:
    """Teacher-facing first-read summary for the student profile."""

    observation_count_label: str
    documentation_label: str
    latest_observation_label: str
    strengths: tuple[str, ...]
    watch_items: tuple[str, ...]
    development_items: tuple[str, ...]
    reliability_hint: str = ""


@dataclass(frozen=True)
class StudentProfileOrientationEventViewModel:
    """One real dated observation or confirmation in the profile projection."""

    event_date: date
    rating: str
    rating_label: str
    source: str
    source_label: str
    reference_id: str
    evidence_label: str


@dataclass(frozen=True)
class StudentProfileOrientationChangeViewModel:
    """One actual status change selected for the Variant-A orientation card."""

    competency_id: str
    competency_label: str
    subject_display_name: str
    topic_label: str
    previous_rating: str
    previous_status_label: str
    new_rating: str
    new_status_label: str
    period_label: str
    latest_change_date: date
    triggering_event: StudentProfileOrientationEventViewModel
    sort_order: int
    historical: bool = False


@dataclass(frozen=True)
class StudentProfileUndocumentedSubjectViewModel:
    """Neutral open-documentation count for one curricular subject."""

    subject_display_name: str
    count: int
    sort_order: int


@dataclass(frozen=True)
class StudentProfileDashboardViewModel:
    """Read-only Variant-A composition for the productive student profile."""

    documentation_summary: StudentDocumentationSummaryViewModel
    confirmed_documented_count: int
    observed_only_count: int
    undocumented_count: int
    undocumented_subjects: tuple[StudentProfileUndocumentedSubjectViewModel, ...]
    orientation_changes: tuple[StudentProfileOrientationChangeViewModel, ...]


@dataclass(frozen=True)
class StudentProfileProjectionBundle:
    """Navigation-local composition of the existing student profile projections."""

    student: StudentDetailViewModel | None
    observations: tuple[ObservationListItem, ...]
    competency_groups: tuple[StudentCompetencySubjectGroup, ...]
    documentation_statuses: tuple[StudentDocumentationSubjectStatus, ...]
    documents: tuple[StudentDocumentViewModel, ...]
    competency_cockpit: StudentCompetencyCockpitViewModel
    profile_dashboard: StudentProfileDashboardViewModel


def empty_student_profile_dashboard() -> StudentProfileDashboardViewModel:
    """Return a neutral empty Variant-A dashboard projection."""
    return StudentProfileDashboardViewModel(
        empty_documentation_summary(),
        0,
        0,
        0,
        (),
        (),
    )


def build_student_profile_dashboard(
    statuses: tuple[object, ...],
    documentation_statuses: tuple[object, ...],
    as_of: date,
) -> StudentProfileDashboardViewModel:
    """Compose Variant A from canonical status rows without recalculating status."""
    documentation_subject_ids = {
        str(getattr(status, "subject_id", "")).strip()
        for status in documentation_statuses
        if str(getattr(status, "subject_id", "")).strip()
    }
    documented_statuses = tuple(
        status
        for status in statuses
        if getattr(status, "subject_id", "") in documentation_subject_ids
        and getattr(status, "is_active", False)
        and not getattr(status, "historical", False)
        and getattr(status, "documentation_state", "undocumented")
        != "undocumented"
    )
    confirmed_documented_count = sum(
        bool(getattr(status, "confirmed_rating", ""))
        for status in documented_statuses
    )
    observed_only_count = sum(
        not bool(getattr(status, "confirmed_rating", ""))
        for status in documented_statuses
    )
    (
        documentation_summary,
        area_confirmed_count,
        area_observed_count,
        undocumented_subjects,
    ) = _profile_documentation_metrics(
        statuses,
        documentation_statuses,
        confirmed_documented_count,
        observed_only_count,
        as_of,
    )
    confirmed_documented_count = area_confirmed_count
    observed_only_count = area_observed_count
    changes = tuple(
        change
        for status in statuses
        if (change := _orientation_change(status, as_of)) is not None
    )
    orientation_changes = tuple(
        sorted(
            changes,
            key=lambda item: (
                -item.latest_change_date.toordinal(),
                item.sort_order,
                item.subject_display_name.casefold(),
                item.competency_id,
            ),
        )[:3]
    )
    return StudentProfileDashboardViewModel(
        documentation_summary,
        confirmed_documented_count,
        observed_only_count,
        sum(item.count for item in undocumented_subjects),
        undocumented_subjects,
        orientation_changes,
    )


def _profile_documentation_metrics(
    statuses: tuple[object, ...],
    documentation_statuses: tuple[object, ...],
    fallback_confirmed_count: int,
    fallback_observed_count: int,
    as_of: date,
) -> tuple[
    StudentDocumentationSummaryViewModel,
    int,
    int,
    tuple[StudentProfileUndocumentedSubjectViewModel, ...],
]:
    area_rows = tuple(
        (
            str(getattr(subject, "subject_id", "")),
            str(getattr(subject, "subject_display_name", "")),
            int(getattr(subject, "sort_order", 0)),
            area,
        )
        for subject in documentation_statuses
        for area in getattr(subject, "learning_area_statuses", ())
    )
    if not area_rows:
        summary = documentation_summary_from_subjects(documentation_statuses)
        open_subjects = tuple(
            StudentProfileUndocumentedSubjectViewModel(
                str(getattr(subject, "subject_display_name", "")),
                max(
                    0,
                    int(getattr(subject, "total_count", 0))
                    - int(getattr(subject, "documented_count", 0)),
                ),
                int(getattr(subject, "sort_order", 0)),
            )
            for subject in sorted(
                documentation_statuses,
                key=lambda item: (
                    int(getattr(item, "sort_order", 0)),
                    str(getattr(item, "subject_display_name", "")).casefold(),
                ),
            )
            if int(getattr(subject, "total_count", 0))
            > int(getattr(subject, "documented_count", 0))
        )
        return (
            summary,
            fallback_confirmed_count,
            fallback_observed_count,
            open_subjects,
        )

    documented_areas = 0
    confirmed_areas = 0
    observed_areas = 0
    open_by_subject: dict[tuple[int, str], int] = {}
    for subject_id, subject_name, sort_order, area in area_rows:
        area_name = str(getattr(area, "learning_area", ""))
        matching = tuple(
            status
            for status in statuses
            if getattr(status, "subject_id", "") == subject_id
            and getattr(status, "learning_area", "") == area_name
            and getattr(status, "is_active", False)
            and not getattr(status, "historical", False)
            and getattr(status, "documentation_state", "undocumented")
            != "undocumented"
        )
        documented_matching = tuple(
            status
            for status in matching
            if _orientation_events(status, as_of)
        )
        if not documented_matching:
            key = (sort_order, subject_name)
            open_by_subject[key] = open_by_subject.get(key, 0) + 1
            continue
        documented_areas += 1
        if any(
            getattr(status, "confirmed_rating", "")
            and (
                confirmed_at := _profile_date(
                    getattr(status, "confirmed_at", "")
                )
            ) is not None
            and confirmed_at <= as_of
            for status in documented_matching
        ):
            confirmed_areas += 1
        else:
            observed_areas += 1
    total_areas = len(area_rows)
    weak_subject_names = tuple(
        subject_name
        for _sort_order, subject_name in sorted(open_by_subject)
    )
    summary = StudentDocumentationSummaryViewModel(
        documented_areas,
        total_areas,
        _documentation_status_label(documented_areas, total_areas),
        weak_subject_names[:3],
    )
    open_subjects = tuple(
        StudentProfileUndocumentedSubjectViewModel(
            subject_name,
            open_by_subject[(sort_order, subject_name)],
            sort_order,
        )
        for sort_order, subject_name in sorted(open_by_subject)
    )
    return summary, confirmed_areas, observed_areas, open_subjects


def _orientation_change(
    status: object,
    as_of: date,
) -> StudentProfileOrientationChangeViewModel | None:
    events = _orientation_events(status, as_of)
    if len(events) < 2:
        return None
    changed_pairs = tuple(
        (previous, current)
        for previous, current in zip(events, events[1:])
        if previous.rating != current.rating
    )
    if not changed_pairs:
        return None
    previous, current = changed_pairs[-1]
    topic_label = str(getattr(status, "competency_group", "")).strip()
    if not topic_label:
        topic_label = str(getattr(status, "learning_area", "")).strip()
    return StudentProfileOrientationChangeViewModel(
        competency_id=str(getattr(status, "competency_id", "")),
        competency_label=(
            str(getattr(status, "competency_label", "")).strip()
            or str(getattr(status, "competency_text", "")).strip()
        ),
        subject_display_name=str(
            getattr(status, "subject_display_name", "")
        ).strip(),
        topic_label=topic_label,
        previous_rating=previous.rating,
        previous_status_label=previous.rating_label,
        new_rating=current.rating,
        new_status_label=current.rating_label,
        period_label=(
            f"{_format_profile_date(events[0].event_date)} – "
            f"{_format_profile_date(events[-1].event_date)}"
        ),
        latest_change_date=current.event_date,
        triggering_event=current,
        sort_order=int(getattr(status, "sort_order", 0)),
        historical=bool(getattr(status, "historical", False)),
    )


def _orientation_events(
    status: object,
    as_of: date,
) -> tuple[StudentProfileOrientationEventViewModel, ...]:
    events: list[tuple[StudentProfileOrientationEventViewModel, int]] = []
    for evidence in getattr(status, "evidence", ()):
        event_date = _profile_date(getattr(evidence, "observation_date", ""))
        if event_date is None or event_date > as_of:
            continue
        rating = str(getattr(evidence, "rating", "")).strip()
        if not rating:
            continue
        source_label = "Beobachtung"
        context = str(getattr(evidence, "context", "")).strip()
        evidence_label = (
            f"{source_label} vom {_format_profile_date(event_date)}: "
            f"{observation_rating_label(rating)}"
        )
        if context:
            evidence_label += f" · {context}"
        events.append((
            StudentProfileOrientationEventViewModel(
                event_date,
                rating,
                observation_rating_label(rating),
                "observation",
                source_label,
                str(getattr(evidence, "observation_id", "")),
                evidence_label,
            ),
            0,
        ))
    confirmed_rating = str(getattr(status, "confirmed_rating", "")).strip()
    confirmed_at = _profile_date(getattr(status, "confirmed_at", ""))
    if confirmed_rating and confirmed_at is not None and confirmed_at <= as_of:
        source_label = "Kompetenz bestätigt"
        events.append((
            StudentProfileOrientationEventViewModel(
                confirmed_at,
                confirmed_rating,
                observation_rating_label(confirmed_rating),
                "confirmation",
                source_label,
                "",
                (
                    f"{source_label} am {_format_profile_date(confirmed_at)}: "
                    f"{observation_rating_label(confirmed_rating)}"
                ),
            ),
            1,
        ))
    return tuple(
        event
        for event, _priority in sorted(
            events,
            key=lambda item: (
                item[0].event_date,
                item[1],
                item[0].reference_id,
            ),
        )
    )


def _profile_date(value: object) -> date | None:
    text = str(value).strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _format_profile_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def build_student_profile_overview(
    observations: tuple[object, ...],
    competency_groups: tuple[object, ...],
    documentation_statuses: tuple[object, ...],
) -> StudentProfileOverviewViewModel:
    """Derive a compact teacher overview from existing profile data."""
    documentation_summary = documentation_summary_from_subjects(documentation_statuses)
    strengths = _overview_strengths(competency_groups)
    watch_items = _overview_watch_items(documentation_statuses, competency_groups, observations)
    development_items = _overview_development_items(
        competency_groups,
        exclude_labels=strengths,
    )
    return StudentProfileOverviewViewModel(
        observation_count_label=_observation_count_label(len(observations)),
        documentation_label=documentation_summary.profile_summary_label,
        latest_observation_label=_latest_observation_label(observations),
        strengths=strengths,
        watch_items=watch_items,
        development_items=development_items,
        reliability_hint=_overview_reliability_hint(observations, strengths),
    )


def _observation_count_label(observation_count: int) -> str:
    if observation_count == 1:
        return "1 Beobachtung"
    return f"{observation_count} Beobachtungen"


def _latest_observation_label(observations: tuple[object, ...]) -> str:
    if not observations:
        return "Letzte Beobachtung: noch keine Beobachtung dokumentiert"
    latest = max(observations, key=lambda observation: getattr(observation, "date_text", ""))
    parts = [
        f"Letzte Beobachtung: {getattr(latest, 'date_text', '')}",
        getattr(latest, "subject_display_name", ""),
        getattr(latest, "context", ""),
    ]
    return " · ".join(part for part in parts if part)


def _overview_strengths(competency_groups: tuple[object, ...]) -> tuple[str, ...]:
    strengths: list[str] = []
    for competency in _iter_competencies(competency_groups):
        rating = getattr(competency, "confirmed_rating", "") or getattr(competency, "rating", "")
        observation_count = getattr(competency, "observation_count", 0)
        if rating == "++" or (rating == "+" and observation_count >= 2):
            label = str(getattr(competency, "competency_label", "")).strip()
            if label and label not in strengths:
                strengths.append(label)
        if len(strengths) >= 3:
            break
    return tuple(strengths)


def _overview_watch_items(
    documentation_statuses: tuple[object, ...],
    competency_groups: tuple[object, ...],
    observations: tuple[object, ...],
) -> tuple[str, ...]:
    items: list[str] = []
    documentation_subject_ids = {
        str(getattr(status, "subject_id", "")).strip()
        for status in documentation_statuses
        if str(getattr(status, "subject_id", "")).strip()
    }
    if not documentation_subject_ids:
        return ()
    for competency in _iter_competencies(competency_groups):
        if getattr(competency, "subject_id", "") not in documentation_subject_ids:
            continue
        rating = getattr(competency, "rating", "")
        if rating in ("-", "--"):
            label = str(getattr(competency, "competency_label", "")).strip()
            if label:
                items.append(f"{label} weiter beobachten")
        if len(items) >= 3:
            return tuple(items)
    for status in sorted(
        documentation_statuses,
        key=lambda entry: (
            _documentation_ratio(entry),
            getattr(entry, "sort_order", 0),
            getattr(entry, "subject_display_name", ""),
        ),
    ):
        subject_name = str(getattr(status, "subject_display_name", "")).strip()
        if not subject_name:
            continue
        if getattr(status, "documented_count", 0) < getattr(status, "total_count", 0):
            item = f"{subject_name} weiter beobachten"
            if item not in items:
                items.append(item)
        if len(items) >= 3:
            return tuple(items)
    if not observations and not items:
        return ("Erste Beobachtungen sammeln, um Entwicklung sichtbar zu machen.",)
    return tuple(items)


def _overview_development_items(
    competency_groups: tuple[object, ...],
    *,
    exclude_labels: tuple[str, ...] = (),
) -> tuple[str, ...]:
    items: list[str] = []
    excluded = set(exclude_labels)
    for competency in _iter_competencies(competency_groups):
        history = tuple(getattr(competency, "rating_history", ()))
        if len(history) < 2 or len(set(history)) <= 1:
            continue
        label = str(getattr(competency, "competency_label", "")).strip()
        if not label or label in excluded:
            continue
        items.append(f"{label}: {' → '.join(history)}")
        if len(items) >= 3:
            break
    return tuple(items)


def _overview_reliability_hint(
    observations: tuple[object, ...],
    strengths: tuple[str, ...],
) -> str:
    if len(observations) == 0:
        return "Noch keine Beobachtungen für eine verlässliche Einschätzung."
    if len(observations) < 3 and not strengths:
        return "Noch zu wenig Beobachtungen für eine verlässliche Einschätzung."
    return ""


def _iter_competencies(competency_groups: tuple[object, ...]) -> tuple[object, ...]:
    competencies: list[object] = []
    for group in competency_groups:
        competencies.extend(getattr(group, "competencies", ()))
    return tuple(
        sorted(
            competencies,
            key=lambda competency: (
                -getattr(competency, "observation_count", 0),
                getattr(competency, "subject_display_name", ""),
                getattr(competency, "sort_order", 0),
                getattr(competency, "competency_label", ""),
            ),
        )
    )


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
        return (
            f"{self.competency_label} · "
            f"Aktueller Stand: {self.rating_label} · "
            f"{self.rating_source}"
        )


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
    current_statuses: tuple[StudentReportCompetencyViewModel, ...]
    strengths: tuple[StudentReportCompetencyViewModel, ...]
    development: tuple[StudentReportDevelopmentViewModel, ...]
    support_needs: tuple[StudentReportCompetencyViewModel, ...]
    example_observations: tuple[StudentReportEvidenceViewModel, ...]

    @property
    def has_content(self) -> bool:
        """Return whether the section contains report-relevant data."""
        return any((
            self.current_statuses,
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
        "Aktueller Stand",
        *_format_report_competencies(section.current_statuses),
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
