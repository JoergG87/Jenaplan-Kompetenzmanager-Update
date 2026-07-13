"""Domain records and service for persistent learning-report drafts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from typing import Protocol


REPORT_DRAFT_STATUS = "draft"
LEARNING_DEVELOPMENT_REPORT_TYPE = "learning_development"
REPORT_DRAFT_CHART_TYPES = (
    "documentation_coverage",
    "competency_timeline",
    "observation_timeline",
)


class ReportDraftError(ValueError):
    """Raised when a report draft violates its approved MVP contract."""


@dataclass(frozen=True)
class ReportDraftSubjectRecord:
    """One selected subject and its teacher-authored report texts."""

    subject_id: str
    strengths_text: str = ""
    development_text: str = ""
    support_needs_text: str = ""
    next_goals_text: str = ""


@dataclass(frozen=True)
class ReportDraftChartSelectionRecord:
    """One deliberately selected neutral chart for a selected subject."""

    subject_id: str
    chart_type: str


@dataclass(frozen=True)
class ReportDraftRecord:
    """Persistent, editable work state; explicitly not a final report version."""

    report_draft_id: str
    student_id: str
    report_type: str
    period_start: str
    period_end: str
    status: str
    teacher_name: str
    overall_text: str
    created_at: str
    updated_at: str
    subjects: tuple[ReportDraftSubjectRecord, ...] = ()
    competency_ids: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()
    chart_selections: tuple[ReportDraftChartSelectionRecord, ...] = ()


class ReportDraftRepository(Protocol):
    """Persistence contract for the report-draft aggregate."""

    def next_report_draft_id(self) -> str: ...

    def create_report_draft(self, draft: ReportDraftRecord) -> ReportDraftRecord: ...

    def update_report_draft(self, draft: ReportDraftRecord) -> ReportDraftRecord: ...

    def get_report_draft(self, report_draft_id: str) -> ReportDraftRecord | None: ...

    def list_report_drafts_for_student(
        self,
        student_id: str,
    ) -> tuple[ReportDraftRecord, ...]: ...


class ReportDraftService:
    """Validate and coordinate create/update operations for report drafts."""

    def __init__(
        self,
        repository: ReportDraftRepository,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.now = now or (lambda: datetime.now(UTC))

    def create_report_draft(
        self,
        *,
        student_id: str,
        report_type: str,
        period_start: str,
        period_end: str,
        teacher_name: str,
        overall_text: str,
        subjects: tuple[ReportDraftSubjectRecord, ...],
        competency_ids: tuple[str, ...],
        observation_ids: tuple[str, ...],
        chart_selections: tuple[ReportDraftChartSelectionRecord, ...],
    ) -> ReportDraftRecord:
        timestamp = self._timestamp()
        draft = ReportDraftRecord(
            report_draft_id=self.repository.next_report_draft_id(),
            student_id=student_id.strip(),
            report_type=report_type.strip(),
            period_start=period_start.strip(),
            period_end=period_end.strip(),
            status=REPORT_DRAFT_STATUS,
            teacher_name=teacher_name.strip(),
            overall_text=overall_text.strip(),
            created_at=timestamp,
            updated_at=timestamp,
            subjects=self._normalize_subjects(subjects),
            competency_ids=self._normalize_ids(competency_ids),
            observation_ids=self._normalize_ids(observation_ids),
            chart_selections=self._normalize_charts(chart_selections),
        )
        self._validate(draft)
        return self.repository.create_report_draft(draft)

    def update_report_draft(
        self,
        *,
        report_draft_id: str,
        student_id: str,
        report_type: str,
        period_start: str,
        period_end: str,
        teacher_name: str,
        overall_text: str,
        subjects: tuple[ReportDraftSubjectRecord, ...],
        competency_ids: tuple[str, ...],
        observation_ids: tuple[str, ...],
        chart_selections: tuple[ReportDraftChartSelectionRecord, ...],
    ) -> ReportDraftRecord:
        existing = self.repository.get_report_draft(report_draft_id.strip())
        if existing is None:
            raise ReportDraftError(
                f"report_draft_id nicht gefunden: {report_draft_id.strip()}"
            )
        if student_id.strip() != existing.student_id:
            raise ReportDraftError("student_id eines Berichtsentwurfs darf nicht wechseln.")
        if report_type.strip() != existing.report_type:
            raise ReportDraftError("report_type eines Berichtsentwurfs darf nicht wechseln.")
        draft = replace(
            existing,
            student_id=student_id.strip(),
            report_type=report_type.strip(),
            period_start=period_start.strip(),
            period_end=period_end.strip(),
            status=REPORT_DRAFT_STATUS,
            teacher_name=teacher_name.strip(),
            overall_text=overall_text.strip(),
            updated_at=self._timestamp(),
            subjects=self._normalize_subjects(subjects),
            competency_ids=self._normalize_ids(competency_ids),
            observation_ids=self._normalize_ids(observation_ids),
            chart_selections=self._normalize_charts(chart_selections),
        )
        self._validate(draft)
        return self.repository.update_report_draft(draft)

    def _validate(self, draft: ReportDraftRecord) -> None:
        if not draft.student_id:
            raise ReportDraftError("student_id darf nicht leer sein.")
        if draft.report_type != LEARNING_DEVELOPMENT_REPORT_TYPE:
            raise ReportDraftError(
                "report_type muss in Sprint 7F.1 learning_development sein."
            )
        if draft.status != REPORT_DRAFT_STATUS:
            raise ReportDraftError("status muss in Sprint 7F.1 draft sein.")
        try:
            start = date.fromisoformat(draft.period_start)
            end = date.fromisoformat(draft.period_end)
        except ValueError as error:
            raise ReportDraftError("Berichtszeitraum muss ISO-Datumswerte enthalten.") from error
        if end <= start:
            raise ReportDraftError("period_end muss nach period_start liegen.")
        selected_subject_ids = {subject.subject_id for subject in draft.subjects}
        if "" in selected_subject_ids:
            raise ReportDraftError("subject_id darf nicht leer sein.")
        if any(
            chart.subject_id not in selected_subject_ids
            for chart in draft.chart_selections
        ):
            raise ReportDraftError(
                "Diagramme duerfen nur fuer ausgewaehlte Faecher gespeichert werden."
            )

    def _normalize_subjects(
        self,
        subjects: tuple[ReportDraftSubjectRecord, ...],
    ) -> tuple[ReportDraftSubjectRecord, ...]:
        normalized = tuple(
            ReportDraftSubjectRecord(
                subject.subject_id.strip(),
                subject.strengths_text.strip(),
                subject.development_text.strip(),
                subject.support_needs_text.strip(),
                subject.next_goals_text.strip(),
            )
            for subject in subjects
        )
        if len({subject.subject_id for subject in normalized}) != len(normalized):
            raise ReportDraftError("Jedes Fach darf im Entwurf nur einmal vorkommen.")
        return tuple(sorted(normalized, key=lambda item: item.subject_id))

    def _normalize_ids(self, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ReportDraftError("Referenz-IDs duerfen nicht leer sein.")
        if len(set(normalized)) != len(normalized):
            raise ReportDraftError("Referenz-IDs duerfen nicht doppelt vorkommen.")
        return tuple(sorted(normalized))

    def _normalize_charts(
        self,
        charts: tuple[ReportDraftChartSelectionRecord, ...],
    ) -> tuple[ReportDraftChartSelectionRecord, ...]:
        normalized = tuple(
            ReportDraftChartSelectionRecord(
                chart.subject_id.strip(),
                chart.chart_type.strip(),
            )
            for chart in charts
        )
        keys = {(chart.subject_id, chart.chart_type) for chart in normalized}
        if len(keys) != len(normalized):
            raise ReportDraftError("Diagrammauswahlen duerfen nicht doppelt vorkommen.")
        if any(
            not chart.subject_id or chart.chart_type not in REPORT_DRAFT_CHART_TYPES
            for chart in normalized
        ):
            raise ReportDraftError("Unzulaessige Diagrammauswahl.")
        return tuple(sorted(normalized, key=lambda item: (item.subject_id, item.chart_type)))

    def _timestamp(self) -> str:
        return self.now().astimezone(UTC).replace(microsecond=0).isoformat()
