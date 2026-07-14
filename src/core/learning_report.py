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
class LearningReportFinalizationPreview:
    """Validated context shown before one irreversible finalization."""

    report_draft_id: str
    student_display_name: str
    report_type: str
    period_start: str
    period_end: str
    subject_names: tuple[str, ...]
    competency_count: int
    observation_count: int
    revision_number: int
    suggested_responsible_display_name: str


@dataclass(frozen=True)
class LearningReportRevisionState:
    """Read-only revision state for one editable report draft."""

    report: LearningReportRecord | None
    current_revision: LearningReportRevisionRecord | None
    revisions: tuple[LearningReportRevisionRecord, ...]
    draft_changed: bool
    current_snapshot_hash_valid: bool
    comparison_error: str | None = None


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

    def get_revision(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportRevisionRecord | None: ...


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

    def prepare(
        self,
        *,
        report_draft_id: str,
    ) -> LearningReportFinalizationPreview:
        """Validate the saved draft and return its confirmation context."""
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
        # The display name is collected in the confirmation. Use an internal,
        # non-persisted value so all other fachliche rules are checked here.
        self.validator.validate(
            source,
            source.draft.teacher_name.strip() or "Finalisierungsvorschau",
        )
        revisions = (
            self.repository.list_revisions(existing_report.learning_report_id)
            if existing_report is not None
            else ()
        )
        return LearningReportFinalizationPreview(
            report_draft_id=source.draft.report_draft_id,
            student_display_name=(
                source.student.display_name if source.student is not None else ""
            ),
            report_type=source.draft.report_type,
            period_start=source.draft.period_start,
            period_end=source.draft.period_end,
            subject_names=tuple(subject.subject_name for subject in source.subjects),
            competency_count=len(source.draft.competency_ids),
            observation_count=len(source.draft.observation_ids),
            revision_number=max(
                (revision.revision_number for revision in revisions),
                default=0,
            )
            + 1,
            suggested_responsible_display_name=source.draft.teacher_name.strip(),
        )

    def _validate_aggregate_identity(
        self,
        report: LearningReportRecord,
        draft: ReportDraftRecord,
    ) -> None:
        _validate_report_aggregate_identity(report, draft)

    def _timestamp(self) -> str:
        value = self.now()
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()


def _validate_report_aggregate_identity(
    report: LearningReportRecord,
    draft: ReportDraftRecord,
) -> None:
    """Protect the stable RPT identity in write and comparison paths."""
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


class LearningReportRevisionReadService:
    """Read and compare immutable revisions without exposing persistence details."""

    def __init__(
        self,
        repository: LearningReportRepository,
        *,
        validator: LearningReportFinalizationValidator | None = None,
        snapshot_builder: LearningReportSnapshotBuilder | None = None,
    ) -> None:
        self.repository = repository
        self.validator = validator or LearningReportFinalizationValidator()
        self.snapshot_builder = snapshot_builder or LearningReportSnapshotBuilder()

    def report_for_draft(
        self,
        report_draft_id: str,
    ) -> LearningReportRecord | None:
        """Resolve the stable RPT aggregate belonging to one RPD."""
        return self.repository.get_report_for_source_draft(report_draft_id.strip())

    def revision_history_for_draft(
        self,
        report_draft_id: str,
    ) -> tuple[LearningReportRevisionRecord, ...]:
        """Load the immutable revision history newest first."""
        report = self.report_for_draft(report_draft_id)
        if report is None:
            return ()
        return tuple(
            sorted(
                self.repository.list_revisions(report.learning_report_id),
                key=lambda item: item.revision_number,
                reverse=True,
            )
        )

    def current_revision_for_draft(
        self,
        report_draft_id: str,
    ) -> LearningReportRevisionRecord | None:
        """Load the one currently finalized RPV for a draft, if present."""
        return next(
            (
                revision
                for revision in self.revision_history_for_draft(report_draft_id)
                if revision.status == FINALIZED_REVISION_STATUS
            ),
            None,
        )

    def snapshot_hash_valid(self, revision: LearningReportRevisionRecord) -> bool:
        """Verify the stored SHA-256 against the exact stored snapshot bytes."""
        return snapshot_sha256(revision.snapshot_json) == revision.snapshot_sha256

    def state_for_draft(self, report_draft_id: str) -> LearningReportRevisionState:
        """Return current/history status and deterministic draft-change state."""
        normalized_draft_id = report_draft_id.strip()
        report = self.report_for_draft(normalized_draft_id)
        if report is None:
            return LearningReportRevisionState(None, None, (), False, True)
        revisions = tuple(
            sorted(
                self.repository.list_revisions(report.learning_report_id),
                key=lambda item: item.revision_number,
                reverse=True,
            )
        )
        current = next(
            (
                revision
                for revision in revisions
                if revision.status == FINALIZED_REVISION_STATUS
            ),
            None,
        )
        if current is None:
            return LearningReportRevisionState(report, None, revisions, True, True)
        hash_valid = self.snapshot_hash_valid(current)
        try:
            source = self.repository.load_finalization_source(normalized_draft_id)
            if source is None:
                raise ReportFinalizationError("Berichtsentwurf ist nicht mehr verfügbar.")
            _validate_report_aggregate_identity(report, source.draft)
            self.validator.validate(source, current.finalized_by_display_name)
            candidate = self.snapshot_builder.build(
                source,
                responsible_display_name=current.finalized_by_display_name,
                snapshot_created_at=current.finalized_at,
            )
            candidate_hash = snapshot_sha256(canonical_snapshot_json(candidate))
            draft_changed = candidate_hash != current.snapshot_sha256
            comparison_error = None
        except ReportFinalizationError as error:
            draft_changed = True
            comparison_error = str(error)
        return LearningReportRevisionState(
            report,
            current,
            revisions,
            draft_changed,
            hash_valid,
            comparison_error,
        )

    def revision_by_id(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportRevisionRecord | None:
        """Load one revision by its stable RPV identity."""
        return self.repository.get_revision(learning_report_revision_id.strip())

    def snapshot_payload(
        self,
        learning_report_revision_id: str,
    ) -> tuple[LearningReportRevisionRecord, dict[str, object]] | None:
        """Verify and decode only the stored immutable snapshot."""
        revision = self.revision_by_id(learning_report_revision_id)
        if revision is None:
            return None
        if not self.snapshot_hash_valid(revision):
            raise ReportFinalizationError(
                "Der gespeicherte Snapshot-Hash der Berichtrevision ist ungültig."
            )
        try:
            payload = json.loads(revision.snapshot_json)
        except json.JSONDecodeError as error:
            raise ReportFinalizationError(
                "Der gespeicherte Bericht-Snapshot ist nicht lesbar."
            ) from error
        if not isinstance(payload, dict):
            raise ReportFinalizationError(
                "Der gespeicherte Bericht-Snapshot besitzt kein gültiges Format."
            )
        return revision, payload
