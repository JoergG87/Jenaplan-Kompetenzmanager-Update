"""ViewModels for persistent LEG drafts and their Live preparation data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from src.core.learning_conference_draft import (
    LEARNING_CONFERENCE_DRAFT_STATUS,
    LearningConferenceDraftRecord,
)
from src.core.learning_conference import (
    COMPLETED_REVISION_STATUS,
    LearningConferenceCompletionError,
    LearningConferenceCompletionErrorCode,
    LearningConferenceRevisionState,
    LearningConferenceVerifiedRevision,
)
from src.core.learning_conference_pdf import LearningConferencePdfArtifactRecord


LEARNING_CONFERENCE_CROSS_TOPICS = (
    ("work_habits", "Arbeitsverhalten"),
    ("social_behavior", "Sozialverhalten"),
    ("independence", "Selbstständigkeit"),
    ("learning_organization", "Lernorganisation"),
)


@dataclass(frozen=True)
class LearningConferenceCompetencyViewModel:
    """One canonical competency row prepared for conscious LEG selection."""

    competency_id: str
    subject_id: str
    subject_name: str
    learning_area: str
    competency_group: str
    competency_text: str
    documentation_state: str
    observed_proposal: str
    confirmed_rating: str
    historical: bool
    selectable: bool
    observation_dates: tuple[str, ...] = ()
    has_current_confirmation: bool = False

    def is_documented_in_period(
        self,
        period_start: date | None,
        period_end: date | None,
    ) -> bool:
        """Use canonical evidence references for LEG visibility, not status derivation."""
        if self.has_current_confirmation:
            return True
        if period_start is None or period_end is None:
            return bool(self.observation_dates)
        return any(
            period_start <= observation_date <= period_end
            for value in self.observation_dates
            if (observation_date := _parse_evidence_date(value)) is not None
        )


@dataclass(frozen=True)
class LearningConferenceSubjectViewModel:
    """One subject preserving the approved four-level hierarchy data."""

    subject_id: str
    subject_name: str
    competencies: tuple[LearningConferenceCompetencyViewModel, ...]


@dataclass(frozen=True)
class LearningConferenceCrossTopicViewModel:
    """One approved cross-cutting conversation topic."""

    cross_topic_key: str
    label: str


@dataclass(frozen=True)
class LearningConferenceEvidenceViewModel:
    """One active observation offered as a deliberate textual reference."""

    observation_id: str
    date_text: str
    subject_name: str
    context: str
    note: str
    competency_ids: tuple[str, ...]
    is_quick_observation: bool


@dataclass(frozen=True)
class LearningConferencePreparationViewModel:
    """Read-only Live input projection for the later prototype port."""

    student_id: str
    student_name: str
    group_name: str
    subjects: tuple[LearningConferenceSubjectViewModel, ...]
    cross_topics: tuple[LearningConferenceCrossTopicViewModel, ...]
    evidence: tuple[LearningConferenceEvidenceViewModel, ...]
    course_name: str = ""
    membership_status_label: str = ""
    membership_blocking: bool = False


@dataclass(frozen=True)
class LearningConferenceDraftViewModel:
    """Complete editable state for a persistent LEG work draft."""

    student_id: str
    period_start: date | None = None
    period_end: date | None = None
    conference_date: date | None = None
    responsible_teacher: str = ""
    conversation_entry_text: str = ""
    child_retrospective_text: str = ""
    teacher_perspective_text: str = ""
    strengths_text: str = ""
    development_fields_text: str = ""
    prepared_goals_text: str = ""
    prepared_support_text: str = ""
    prepared_agreements_text: str = ""
    agreed_goals_text: str = ""
    agreed_support_text: str = ""
    agreed_agreements_text: str = ""
    responsibilities_text: str = ""
    next_review_date: date | None = None
    subject_ids: tuple[str, ...] = ()
    cross_topic_keys: tuple[str, ...] = ()
    competency_ids: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()
    chart_types: tuple[str, ...] = ()
    learning_conference_draft_id: str = ""
    status: str = LEARNING_CONFERENCE_DRAFT_STATUS
    created_at: str = ""
    updated_at: str = ""
    unavailable_observation_ids: tuple[str, ...] = ()

    @classmethod
    def from_record(
        cls,
        record: LearningConferenceDraftRecord,
        *,
        unavailable_observation_ids: tuple[str, ...] = (),
    ) -> "LearningConferenceDraftViewModel":
        return cls(
            student_id=record.student_id,
            period_start=_parse_optional_date(record.period_start),
            period_end=_parse_optional_date(record.period_end),
            conference_date=_parse_optional_date(record.conference_date),
            responsible_teacher=record.responsible_teacher,
            conversation_entry_text=record.conversation_entry_text,
            child_retrospective_text=record.child_retrospective_text,
            teacher_perspective_text=record.teacher_perspective_text,
            strengths_text=record.strengths_text,
            development_fields_text=record.development_fields_text,
            prepared_goals_text=record.prepared_goals_text,
            prepared_support_text=record.prepared_support_text,
            prepared_agreements_text=record.prepared_agreements_text,
            agreed_goals_text=record.agreed_goals_text,
            agreed_support_text=record.agreed_support_text,
            agreed_agreements_text=record.agreed_agreements_text,
            responsibilities_text=record.responsibilities_text,
            next_review_date=_parse_optional_date(record.next_review_date),
            subject_ids=record.subject_ids,
            cross_topic_keys=record.cross_topic_keys,
            competency_ids=record.competency_ids,
            observation_ids=record.observation_ids,
            chart_types=record.chart_types,
            learning_conference_draft_id=record.learning_conference_draft_id,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            unavailable_observation_ids=unavailable_observation_ids,
        )


def build_learning_conference_preparation(
    student: object,
    statuses: tuple[object, ...],
    observations: tuple[object, ...],
) -> LearningConferencePreparationViewModel:
    """Wrap canonical status and observation projections without recalculation."""
    grouped: dict[str, list[LearningConferenceCompetencyViewModel]] = {}
    subject_names: dict[str, str] = {}
    for status in statuses:
        subject_id = str(getattr(status, "subject_id", "")).strip()
        competency_id = str(getattr(status, "competency_id", "")).strip()
        if not subject_id or not competency_id:
            continue
        subject_name = str(
            getattr(status, "subject_display_name", subject_id)
        ).strip() or subject_id
        historical = bool(getattr(status, "historical", False))
        subject_names.setdefault(subject_id, subject_name)
        grouped.setdefault(subject_id, []).append(
            LearningConferenceCompetencyViewModel(
                competency_id=competency_id,
                subject_id=subject_id,
                subject_name=subject_name,
                learning_area=str(getattr(status, "learning_area", "")),
                competency_group=str(getattr(status, "competency_group", "")),
                competency_text=(
                    str(getattr(status, "competency_text", ""))
                    or str(getattr(status, "competency_label", ""))
                ),
                documentation_state=_documentation_state_label(
                    str(getattr(status, "documentation_state", ""))
                ),
                observed_proposal=_rating_label(
                    str(getattr(status, "observed_proposal", ""))
                ),
                confirmed_rating=_rating_label(
                    str(getattr(status, "confirmed_rating", ""))
                ),
                historical=historical,
                selectable=(
                    bool(getattr(status, "is_active", False))
                    and str(getattr(status, "catalog_status", "current")) == "current"
                    and not historical
                ),
                observation_dates=tuple(
                    str(getattr(evidence, "observation_date", ""))
                    for evidence in getattr(status, "evidence", ())
                    if str(getattr(evidence, "observation_date", "")).strip()
                ),
                has_current_confirmation=bool(
                    str(getattr(status, "documentation_state", ""))
                    != "confirmation_unknown"
                    and (
                        str(getattr(status, "confirmed_rating", "")).strip()
                        or str(getattr(status, "confirmed_at", "")).strip()
                    )
                ),
            )
        )

    subjects = tuple(
        LearningConferenceSubjectViewModel(
            subject_id,
            subject_names[subject_id],
            tuple(
                sorted(
                    competencies,
                    key=lambda item: (
                        item.historical,
                        item.learning_area.casefold(),
                        item.competency_group.casefold(),
                        item.competency_text.casefold(),
                        item.competency_id,
                    ),
                )
            ),
        )
        for subject_id, competencies in sorted(
            grouped.items(),
            key=lambda item: subject_names[item[0]].casefold(),
        )
    )
    evidence = tuple(
        LearningConferenceEvidenceViewModel(
            observation_id=str(getattr(observation, "observation_id", "")),
            date_text=str(getattr(observation, "date_text", "")),
            subject_name=str(
                getattr(observation, "subject_display_name", "")
            ),
            context=str(getattr(observation, "context", "")),
            note=str(getattr(observation, "note", "")),
            competency_ids=tuple(
                str(getattr(rating, "competency_id", ""))
                for rating in getattr(observation, "competency_ratings", ())
                if str(getattr(rating, "competency_id", ""))
            ),
            is_quick_observation=not bool(
                getattr(observation, "competency_ratings", ())
            ),
        )
        for observation in observations
        if str(getattr(observation, "observation_id", "")).strip()
    )
    return LearningConferencePreparationViewModel(
        student_id=str(getattr(student, "student_id", "")),
        student_name=str(getattr(student, "display_name", "")),
        group_name=str(getattr(student, "group_name", "")),
        subjects=subjects,
        cross_topics=tuple(
            LearningConferenceCrossTopicViewModel(key, label)
            for key, label in LEARNING_CONFERENCE_CROSS_TOPICS
        ),
        evidence=evidence,
        course_name=str(getattr(student, "course_name", "")),
        membership_status_label=str(
            getattr(student, "status_label", "")
        ),
        membership_blocking=bool(
            getattr(student, "membership_blocking", False)
        ),
    )


def _parse_optional_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def _parse_evidence_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _documentation_state_label(value: str) -> str:
    return {
        "undocumented": "Noch nicht dokumentiert",
        "observed_unconfirmed": "Durch Beobachtungen dokumentiert",
        "confirmed": "Bestätigter Stand vorhanden",
        "newer_observations": "Neue Beobachtungen seit der Bestätigung",
        "confirmation_unknown": "Bestätigungsstand unklar – bitte erneut bestätigen",
    }.get(value, value)


def _rating_label(value: str) -> str:
    return {
        "++": "sicher erreicht",
        "+": "erreicht",
        "-": "in Entwicklung",
        "--": "Unterstützungsbedarf",
    }.get(value, value)


@dataclass(frozen=True)
class LearningConferenceCompletionErrorViewModel:
    """Typed UI feedback and optional phase target for one completion failure."""

    code: str
    message: str
    phase_key: str | None
    reference_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class LearningConferenceRevisionListItemViewModel:
    learning_conference_revision_id: str
    revision_number: int
    status: str
    status_label: str
    completed_at_text: str
    completed_by_display_name: str
    snapshot_sha256: str


@dataclass(frozen=True)
class LearningConferenceRevisionStatusViewModel:
    has_completion: bool
    status_label: str
    draft_changed: bool
    hash_valid: bool
    current_revision_number: int | None
    revisions: tuple[LearningConferenceRevisionListItemViewModel, ...]
    comparison_error: LearningConferenceCompletionErrorViewModel | None = None


@dataclass(frozen=True)
class LearningConferenceRevisionViewModel:
    """Snapshot-only projection for one immutable historical LCV."""

    learning_conference_revision_id: str
    revision_number: int
    status: str
    status_label: str
    completed_at_text: str
    completed_by_display_name: str
    snapshot_sha256: str
    student_name: str
    group_name: str
    course_name: str
    conference_date_text: str
    period_text: str
    responsible_teacher: str
    goals: str
    support: str
    agreements: str
    responsibilities: str
    next_review_date_text: str
    subject_names: tuple[str, ...]
    cross_topic_labels: tuple[str, ...]
    competency_lines: tuple[str, ...]
    observation_lines: tuple[str, ...]


@dataclass(frozen=True)
class LearningConferencePdfArtifactViewModel:
    """UI-ready verified reference to one immutable final LEG PDF file."""

    learning_conference_pdf_artifact_id: str
    learning_conference_revision_id: str
    file_path: str
    file_name: str
    file_size_bytes: int
    snapshot_sha256: str
    pdf_sha256: str
    created_at: str


def build_learning_conference_pdf_artifact_view_model(
    artifact: LearningConferencePdfArtifactRecord,
    file_path: Path | None,
) -> LearningConferencePdfArtifactViewModel:
    return LearningConferencePdfArtifactViewModel(
        artifact.learning_conference_pdf_artifact_id,
        artifact.learning_conference_revision_id,
        "" if file_path is None else str(file_path),
        "Finales PDF" if file_path is None else file_path.name,
        artifact.file_size_bytes,
        artifact.snapshot_sha256,
        artifact.pdf_sha256,
        _format_revision_timestamp(artifact.created_at),
    )


def build_learning_conference_completion_error(
    error: LearningConferenceCompletionError,
) -> LearningConferenceCompletionErrorViewModel:
    phase_by_code = {
        LearningConferenceCompletionErrorCode.STUDENT_MISSING: "goal",
        LearningConferenceCompletionErrorCode.ASSIGNMENT_MISSING: "goal",
        LearningConferenceCompletionErrorCode.ASSIGNMENT_AMBIGUOUS: "goal",
        LearningConferenceCompletionErrorCode.ASSIGNMENT_EXITED: "goal",
        LearningConferenceCompletionErrorCode.CONFERENCE_DATE_MISSING: "goal",
        LearningConferenceCompletionErrorCode.CONFERENCE_DATE_INVALID: "goal",
        LearningConferenceCompletionErrorCode.RESPONSIBLE_TEACHER_MISSING: "goal",
        LearningConferenceCompletionErrorCode.PERIOD_INVALID: "goal",
        LearningConferenceCompletionErrorCode.SHARED_RESULT_MISSING: "agreements",
        LearningConferenceCompletionErrorCode.SUBJECT_REFERENCE_MISSING: "goal",
        LearningConferenceCompletionErrorCode.COMPETENCY_REFERENCE_MISSING: "evidence",
        LearningConferenceCompletionErrorCode.COMPETENCY_REFERENCE_INVALID: "evidence",
        LearningConferenceCompletionErrorCode.OBSERVATION_UNAVAILABLE: "evidence",
        LearningConferenceCompletionErrorCode.OBSERVATION_INVALID: "evidence",
    }
    return LearningConferenceCompletionErrorViewModel(
        error.code.value,
        str(error),
        phase_by_code.get(error.code),
        error.reference_ids,
    )


def build_learning_conference_revision_status(
    state: LearningConferenceRevisionState,
) -> LearningConferenceRevisionStatusViewModel:
    current = state.current_revision
    if current is None:
        label = "Noch nicht abgeschlossen"
    elif not state.current_snapshot_hash_valid:
        label = "Integritätsprüfung fehlgeschlagen"
    elif state.draft_changed:
        label = f"Entwurf seit Abschluss geändert · Revision {current.revision_number}"
    else:
        label = f"Abgeschlossen · Revision {current.revision_number}"
    return LearningConferenceRevisionStatusViewModel(
        has_completion=current is not None,
        status_label=label,
        draft_changed=state.draft_changed,
        hash_valid=state.current_snapshot_hash_valid,
        current_revision_number=current.revision_number if current else None,
        revisions=tuple(
            LearningConferenceRevisionListItemViewModel(
                item.learning_conference_revision_id,
                item.revision_number,
                item.status,
                "Aktuell" if item.status == COMPLETED_REVISION_STATUS else "Ersetzt",
                _format_revision_timestamp(item.completed_at),
                item.completed_by_display_name,
                item.snapshot_sha256,
            )
            for item in state.revisions
        ),
        comparison_error=(
            build_learning_conference_completion_error(state.comparison_error)
            if state.comparison_error is not None
            else None
        ),
    )


def build_learning_conference_revision_view_model(
    verified: LearningConferenceVerifiedRevision,
) -> LearningConferenceRevisionViewModel:
    revision = verified.revision
    snapshot = verified.snapshot
    student = _mapping(snapshot.get("student"))
    group = _mapping(student.get("group"))
    course = _mapping(student.get("course"))
    period = _mapping(snapshot.get("period"))
    shared = _mapping(snapshot.get("shared_results"))
    subjects = _mapping_items(snapshot.get("subjects"))
    topics = _mapping_items(snapshot.get("cross_topics"))
    competencies = _mapping_items(snapshot.get("competencies"))
    observations = _mapping_items(snapshot.get("observations"))
    return LearningConferenceRevisionViewModel(
        learning_conference_revision_id=revision.learning_conference_revision_id,
        revision_number=revision.revision_number,
        status=revision.status,
        status_label=(
            "Aktuell" if revision.status == COMPLETED_REVISION_STATUS else "Ersetzt"
        ),
        completed_at_text=_format_revision_timestamp(revision.completed_at),
        completed_by_display_name=revision.completed_by_display_name,
        snapshot_sha256=revision.snapshot_sha256,
        student_name=str(student.get("display_name", "")),
        group_name=str(group.get("group_name", "")),
        course_name=str(course.get("course_name", "")),
        conference_date_text=_format_iso_date(str(snapshot.get("conference_date", ""))),
        period_text=_format_period(period),
        responsible_teacher=str(snapshot.get("responsible_teacher", "")),
        goals=str(shared.get("goals", "")),
        support=str(shared.get("support", "")),
        agreements=str(shared.get("agreements", "")),
        responsibilities=str(shared.get("responsibilities", "")),
        next_review_date_text=_format_iso_date(
            str(shared.get("next_review_date", ""))
        ),
        subject_names=tuple(str(item.get("subject_name", "")) for item in subjects),
        cross_topic_labels=tuple(str(item.get("label", "")) for item in topics),
        competency_lines=tuple(
            (
                f"{item.get('subject_name', '')} · {item.get('competency_text', '')}"
                + (" · historischer Bezug" if item.get("historical_reference") else "")
            ).strip(" ·")
            for item in competencies
        ),
        observation_lines=tuple(
            f"{_format_iso_date(str(item.get('observed_on', '')))} · "
            f"{item.get('subject_name', '')} · {item.get('content', '')}".strip(" ·")
            for item in observations
        ),
    )


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _mapping_items(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _format_iso_date(value: str) -> str:
    if not value:
        return "Nicht festgelegt"
    try:
        return date.fromisoformat(value[:10]).strftime("%d.%m.%Y")
    except ValueError:
        return value


def _format_period(period: dict[str, object]) -> str:
    start = str(period.get("start", ""))
    end = str(period.get("end", ""))
    if not start and not end:
        return "Kein Zeitraum festgelegt"
    return f"{_format_iso_date(start)} bis {_format_iso_date(end)}"


def _format_revision_timestamp(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime(
            "%d.%m.%Y, %H:%M"
        )
    except ValueError:
        return value
