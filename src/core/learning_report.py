"""Immutable learning-report revisions and their domain snapshot contract."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

from .constants import LEARNING_REPORT_ID_PREFIX, LEARNING_REPORT_REVISION_ID_PREFIX
from .report_draft import LEARNING_DEVELOPMENT_REPORT_TYPE, ReportDraftRecord


LEARNING_REPORT_SNAPSHOT_SCHEMA_VERSION = 1
FINALIZED_REVISION_STATUS = "finalized"
SUPERSEDED_REVISION_STATUS = "superseded"


class ReportFinalizationError(ValueError):
    """Raised when a report draft cannot be finalized safely."""


@dataclass(frozen=True)
class LearningReportRecord:
    """Stable report aggregate created once for one editable report draft."""

    learning_report_id: str
    source_report_draft_id: str
    student_id: str
    report_type: str
    period_start: str
    period_end: str
    created_at: str


@dataclass(frozen=True)
class LearningReportRevisionRecord:
    """One immutable report revision, except for its superseding transition."""

    learning_report_revision_id: str
    learning_report_id: str
    revision_number: int
    status: str
    snapshot_schema_version: int
    snapshot_json: str
    snapshot_sha256: str
    finalized_at: str
    finalized_by_display_name: str
    superseded_at: str | None


@dataclass(frozen=True)
class LearningReportFinalizationResult:
    """Aggregate and newly created revision returned by one finalization."""

    report: LearningReportRecord
    revision: LearningReportRevisionRecord


@dataclass(frozen=True)
class LearningReportStudentSource:
    """Visible student master data frozen into the report snapshot."""

    student_id: str
    first_name: str
    last_name: str
    group_id: str
    group_name: str
    course_id: str
    course_name: str

    @property
    def display_name(self) -> str:
        return " ".join(part for part in (self.first_name, self.last_name) if part).strip()


@dataclass(frozen=True)
class LearningReportSubjectSource:
    """One selected subject plus its visible name and coverage values."""

    subject_id: str
    subject_name: str
    documented_competency_count: int
    current_competency_count: int


@dataclass(frozen=True)
class LearningReportCompetencyEvidenceSource:
    """One dated source value used by a deliberately selected chart."""

    recorded_on: str
    rating: str
    source_type: str
    source_id: str


@dataclass(frozen=True)
class LearningReportCompetencySource:
    """Resolved visible competency data and its historical-selection state."""

    competency_id: str
    subject_id: str
    subject_name: str
    learning_area: str
    competency_group: str
    competency_text: str
    historical_reference: bool
    active_at_finalization: bool
    catalog_status_at_finalization: str
    evidence_points: tuple[LearningReportCompetencyEvidenceSource, ...] = ()


@dataclass(frozen=True)
class LearningReportObservationSource:
    """Resolved active observation selected as report evidence."""

    observation_id: str
    observed_on: str
    subject_id: str
    subject_name: str
    context: str
    note: str
    matched_subject_ids: tuple[str, ...]


@dataclass(frozen=True)
class LearningReportFinalizationSource:
    """Complete in-memory source needed to validate and build one snapshot."""

    draft: ReportDraftRecord
    student: LearningReportStudentSource | None
    subjects: tuple[LearningReportSubjectSource, ...]
    competencies: tuple[LearningReportCompetencySource, ...]
    observations: tuple[LearningReportObservationSource, ...]
    missing_subject_ids: tuple[str, ...] = ()
    missing_competency_ids: tuple[str, ...] = ()
    invalid_competency_ids: tuple[str, ...] = ()
    unavailable_observation_ids: tuple[str, ...] = ()
    invalid_observation_ids: tuple[str, ...] = ()


class LearningReportRepository(Protocol):
    """Persistence and source-resolution boundary for report finalization."""

    def load_finalization_source(
        self,
        report_draft_id: str,
    ) -> LearningReportFinalizationSource | None: ...

    def save_finalized_revision(
        self,
        source: LearningReportFinalizationSource,
        *,
        snapshot_json: str,
        snapshot_sha256: str,
        finalized_at: str,
        finalized_by_display_name: str,
    ) -> LearningReportFinalizationResult: ...

    def get_report_for_source_draft(
        self,
        report_draft_id: str,
    ) -> LearningReportRecord | None: ...

    def list_revisions(
        self,
        learning_report_id: str,
    ) -> tuple[LearningReportRevisionRecord, ...]: ...


class LearningReportFinalizationValidator:
    """Validate the approved minimum content and all persisted references."""

    def validate(
        self,
        source: LearningReportFinalizationSource,
        finalized_by_display_name: str,
    ) -> None:
        draft = source.draft
        if not finalized_by_display_name.strip():
            raise ReportFinalizationError(
                "finalized_by_display_name darf nicht leer sein."
            )
        if source.student is None or source.student.student_id != draft.student_id:
            raise ReportFinalizationError(
                f"student_id nicht aufloesbar: {draft.student_id}"
            )
        if draft.report_type != LEARNING_DEVELOPMENT_REPORT_TYPE:
            raise ReportFinalizationError(
                "report_type ist fuer die Finalisierung nicht zugelassen."
            )
        try:
            period_start = date.fromisoformat(draft.period_start)
            period_end = date.fromisoformat(draft.period_end)
        except ValueError as error:
            raise ReportFinalizationError(
                "Berichtszeitraum muss gueltige ISO-Datumswerte enthalten."
            ) from error
        if period_end <= period_start:
            raise ReportFinalizationError(
                "period_end muss nach period_start liegen."
            )
        if not draft.subjects:
            raise ReportFinalizationError(
                "Mindestens ein Fach muss ausgewaehlt sein."
            )
        if source.missing_subject_ids:
            raise ReportFinalizationError(
                "Fachreferenzen nicht aufloesbar: "
                + ", ".join(source.missing_subject_ids)
            )
        selected_subject_ids = {subject.subject_id for subject in draft.subjects}
        if len(source.subjects) != len(draft.subjects):
            raise ReportFinalizationError(
                "Nicht alle ausgewaehlten Faecher wurden aufgeloest."
            )
        invalid_chart_subject_ids = tuple(
            sorted(
                {
                    chart.subject_id
                    for chart in draft.chart_selections
                    if chart.subject_id not in selected_subject_ids
                }
            )
        )
        if invalid_chart_subject_ids:
            raise ReportFinalizationError(
                "Diagrammreferenzen sind fachfremd: "
                + ", ".join(invalid_chart_subject_ids)
            )
        if not self._has_manual_content(draft):
            raise ReportFinalizationError(
                "Mindestens ein manuell verantworteter Berichtstext ist erforderlich."
            )
        if source.missing_competency_ids or source.invalid_competency_ids:
            invalid = tuple(
                sorted(
                    set(source.missing_competency_ids)
                    | set(source.invalid_competency_ids)
                )
            )
            raise ReportFinalizationError(
                "Kompetenzreferenzen nicht vollstaendig aufloesbar oder fachfremd: "
                + ", ".join(invalid)
            )
        if len(source.competencies) != len(draft.competency_ids):
            raise ReportFinalizationError(
                "Nicht alle ausgewaehlten Kompetenzen wurden aufgeloest."
            )
        if source.unavailable_observation_ids:
            raise ReportFinalizationError(
                "Nicht verfuegbare Beobachtungsreferenzen muessen vor der "
                "Finalisierung aus dem Draft entfernt werden: "
                + ", ".join(source.unavailable_observation_ids)
            )
        if source.invalid_observation_ids:
            raise ReportFinalizationError(
                "Beobachtungsreferenzen sind kind- oder fachfremd: "
                + ", ".join(source.invalid_observation_ids)
            )
        if len(source.observations) != len(draft.observation_ids):
            raise ReportFinalizationError(
                "Nicht alle ausgewaehlten Beobachtungen wurden aufgeloest."
            )

    def _has_manual_content(self, draft: ReportDraftRecord) -> bool:
        values = [draft.overall_text]
        for subject in draft.subjects:
            values.extend(
                (
                    subject.strengths_text,
                    subject.development_text,
                    subject.support_needs_text,
                    subject.next_goals_text,
                )
            )
        return any(value.strip() for value in values)


class LearningReportSnapshotBuilder:
    """Build the report-specific historical snapshot from validated sources."""

    def build(
        self,
        source: LearningReportFinalizationSource,
        *,
        responsible_display_name: str,
        snapshot_created_at: str,
    ) -> dict[str, object]:
        draft = source.draft
        subject_by_id = {subject.subject_id: subject for subject in source.subjects}
        competency_by_subject: dict[str, list[LearningReportCompetencySource]] = {}
        for competency in source.competencies:
            competency_by_subject.setdefault(competency.subject_id, []).append(
                competency
            )
        observation_by_subject: dict[str, list[LearningReportObservationSource]] = {}
        for observation in source.observations:
            for subject_id in observation.matched_subject_ids:
                observation_by_subject.setdefault(subject_id, []).append(observation)

        return {
            "snapshot_schema_version": LEARNING_REPORT_SNAPSHOT_SCHEMA_VERSION,
            "source_report_draft_id": draft.report_draft_id,
            "student": self._student_payload(source.student),
            "report_type": draft.report_type,
            "period": {
                "start": draft.period_start,
                "end": draft.period_end,
            },
            "responsible_display_name": responsible_display_name.strip(),
            "manual_texts": {
                "overall_text": draft.overall_text,
                "subjects": [
                    {
                        "subject_id": subject.subject_id,
                        "strengths_text": subject.strengths_text,
                        "development_text": subject.development_text,
                        "support_needs_text": subject.support_needs_text,
                        "next_goals_text": subject.next_goals_text,
                    }
                    for subject in draft.subjects
                ],
            },
            "subjects": [
                {
                    "subject_id": subject.subject_id,
                    "subject_name": subject.subject_name,
                }
                for subject in source.subjects
            ],
            "competencies": [
                self._competency_payload(competency)
                for competency in source.competencies
            ],
            "observations": [
                {
                    "observation_id": observation.observation_id,
                    "observed_on": observation.observed_on,
                    "subject_id": observation.subject_id,
                    "subject_name": observation.subject_name,
                    "matched_subject_ids": list(observation.matched_subject_ids),
                    "context": observation.context,
                    "content": observation.note,
                }
                for observation in source.observations
            ],
            "charts": [
                self._chart_payload(
                    selection.subject_id,
                    selection.chart_type,
                    subject_by_id[selection.subject_id],
                    tuple(competency_by_subject.get(selection.subject_id, ())),
                    tuple(observation_by_subject.get(selection.subject_id, ())),
                    draft.period_start,
                    draft.period_end,
                )
                for selection in draft.chart_selections
            ],
            "snapshot_created_at": snapshot_created_at,
        }

    def _student_payload(
        self,
        student: LearningReportStudentSource | None,
    ) -> dict[str, object]:
        if student is None:
            raise ReportFinalizationError("Schuelerdaten fehlen fuer den Snapshot.")
        return {
            "student_id": student.student_id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "display_name": student.display_name,
            "group": {
                "group_id": student.group_id,
                "group_name": student.group_name,
            },
            "course": {
                "course_id": student.course_id,
                "course_name": student.course_name,
            },
        }

    def _competency_payload(
        self,
        competency: LearningReportCompetencySource,
    ) -> dict[str, object]:
        return {
            "competency_id": competency.competency_id,
            "subject_id": competency.subject_id,
            "subject_name": competency.subject_name,
            "learning_area": competency.learning_area,
            "competency_group": competency.competency_group,
            "competency_text": competency.competency_text,
            "historical_reference": competency.historical_reference,
            "active_at_finalization": competency.active_at_finalization,
            "catalog_status_at_finalization": competency.catalog_status_at_finalization,
        }

    def _chart_payload(
        self,
        subject_id: str,
        chart_type: str,
        subject: LearningReportSubjectSource,
        competencies: tuple[LearningReportCompetencySource, ...],
        observations: tuple[LearningReportObservationSource, ...],
        period_start: str,
        period_end: str,
    ) -> dict[str, object]:
        base: dict[str, object] = {
            "subject_id": subject_id,
            "subject_name": subject.subject_name,
            "chart_type": chart_type,
        }
        if chart_type == "documentation_coverage":
            base["values"] = {
                "documented_competency_count": subject.documented_competency_count,
                "current_competency_count": subject.current_competency_count,
            }
        elif chart_type == "competency_timeline":
            base["values"] = {
                "period_start": period_start,
                "period_end": period_end,
                "series": [
                    {
                        "competency_id": competency.competency_id,
                        "label": competency.competency_text,
                        "points": [
                            {
                                "recorded_on": point.recorded_on,
                                "rating": point.rating,
                                "source_type": point.source_type,
                                "source_id": point.source_id,
                            }
                            for point in competency.evidence_points
                            if period_start <= point.recorded_on <= period_end
                        ],
                    }
                    for competency in competencies
                ],
            }
        elif chart_type == "observation_timeline":
            base["values"] = {
                "period_start": period_start,
                "period_end": period_end,
                "events": [
                    {
                        "observation_id": observation.observation_id,
                        "observed_on": observation.observed_on,
                        "context": observation.context,
                        "content": observation.note,
                    }
                    for observation in observations
                    if period_start <= observation.observed_on <= period_end
                ],
            }
        else:
            raise ReportFinalizationError(
                f"Unzulaessiger Diagrammtyp im Snapshot: {chart_type}"
            )
        return base


def canonical_snapshot_json(snapshot: dict[str, object]) -> str:
    """Serialize one snapshot to the exact canonical form stored in SQLite."""
    return json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def snapshot_sha256(canonical_json: str) -> str:
    """Hash exactly the UTF-8 bytes of the stored canonical JSON string."""
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class ReportFinalizationService:
    """Validate, snapshot and atomically persist one final report revision."""

    def __init__(
        self,
        repository: LearningReportRepository,
        *,
        validator: LearningReportFinalizationValidator | None = None,
        snapshot_builder: LearningReportSnapshotBuilder | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.validator = validator or LearningReportFinalizationValidator()
        self.snapshot_builder = snapshot_builder or LearningReportSnapshotBuilder()
        self.now = now or (lambda: datetime.now(UTC))

    def finalize(
        self,
        *,
        report_draft_id: str,
        finalized_by_display_name: str,
    ) -> LearningReportFinalizationResult:
        normalized_draft_id = report_draft_id.strip()
        if not normalized_draft_id:
            raise ReportFinalizationError("report_draft_id darf nicht leer sein.")
        source = self.repository.load_finalization_source(normalized_draft_id)
        if source is None:
            raise ReportFinalizationError(
                f"report_draft_id nicht gefunden: {normalized_draft_id}"
            )
        existing_report = self.repository.get_report_for_source_draft(
            normalized_draft_id
        )
        if existing_report is not None:
            self._validate_aggregate_identity(existing_report, source.draft)
        self.validator.validate(source, finalized_by_display_name)
        finalized_at = self._timestamp()
        snapshot = self.snapshot_builder.build(
            source,
            responsible_display_name=finalized_by_display_name,
            snapshot_created_at=finalized_at,
        )
        canonical_json = canonical_snapshot_json(snapshot)
        digest = snapshot_sha256(canonical_json)
        return self.repository.save_finalized_revision(
            source,
            snapshot_json=canonical_json,
            snapshot_sha256=digest,
            finalized_at=finalized_at,
            finalized_by_display_name=finalized_by_display_name.strip(),
        )

    def _validate_aggregate_identity(
        self,
        report: LearningReportRecord,
        draft: ReportDraftRecord,
    ) -> None:
        mismatches = tuple(
            field_name
            for field_name, report_value, draft_value in (
                (
                    "source_report_draft_id",
                    report.source_report_draft_id,
                    draft.report_draft_id,
                ),
                ("student_id", report.student_id, draft.student_id),
                ("report_type", report.report_type, draft.report_type),
                ("period_start", report.period_start, draft.period_start),
                ("period_end", report.period_end, draft.period_end),
            )
            if report_value != draft_value
        )
        if mismatches:
            raise ReportFinalizationError(
                "Die Aggregateidentitaet des bestehenden RPT weicht vom RPD ab "
                f"({', '.join(mismatches)}). Fuer einen anderen Berichtstyp oder "
                "Zeitraum ist ein neuer Berichtsdraft erforderlich."
            )

    def _timestamp(self) -> str:
        value = self.now()
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
