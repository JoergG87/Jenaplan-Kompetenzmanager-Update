"""LEG-specific completion aggregate, immutable revisions and snapshot contract."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
from typing import Protocol

from .learning_conference_draft import (
    LEARNING_CONFERENCE_DRAFT_STATUS,
    LearningConferenceDraftRecord,
)


LEARNING_CONFERENCE_SNAPSHOT_SCHEMA_VERSION = 1
COMPLETED_REVISION_STATUS = "completed"
SUPERSEDED_REVISION_STATUS = "superseded"


class LearningConferenceCompletionErrorCode(str, Enum):
    """Stable error categories transported to application and UI projections."""

    INVALID_REQUEST = "invalid_request"
    DRAFT_NOT_FOUND = "draft_not_found"
    DRAFT_CHANGED = "draft_changed"
    STUDENT_MISSING = "student_missing"
    ASSIGNMENT_MISSING = "assignment_missing"
    ASSIGNMENT_AMBIGUOUS = "assignment_ambiguous"
    ASSIGNMENT_EXITED = "assignment_exited"
    CONFERENCE_DATE_MISSING = "conference_date_missing"
    CONFERENCE_DATE_INVALID = "conference_date_invalid"
    RESPONSIBLE_TEACHER_MISSING = "responsible_teacher_missing"
    SHARED_RESULT_MISSING = "shared_result_missing"
    PERIOD_INVALID = "period_invalid"
    SUBJECT_REFERENCE_MISSING = "subject_reference_missing"
    COMPETENCY_REFERENCE_MISSING = "competency_reference_missing"
    COMPETENCY_REFERENCE_INVALID = "competency_reference_invalid"
    OBSERVATION_UNAVAILABLE = "observation_unavailable"
    OBSERVATION_INVALID = "observation_invalid"
    AGGREGATE_CONFLICT = "aggregate_conflict"
    REVISION_NOT_FOUND = "revision_not_found"
    SNAPSHOT_INVALID = "snapshot_invalid"
    PERSISTENCE_FAILED = "persistence_failed"


class LearningConferenceCompletionError(ValueError):
    """Typed LEG completion failure without UI string interpretation."""

    def __init__(
        self,
        code: LearningConferenceCompletionErrorCode,
        message: str,
        *,
        reference_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.reference_ids = reference_ids


@dataclass(frozen=True)
class LearningConferenceRecord:
    """Stable LEG aggregate created once for one editable LCD."""

    learning_conference_id: str
    source_learning_conference_draft_id: str
    student_id: str
    created_at: str


@dataclass(frozen=True)
class LearningConferenceRevisionRecord:
    """Immutable LEG completion revision except for superseding transition."""

    learning_conference_revision_id: str
    learning_conference_id: str
    revision_number: int
    status: str
    snapshot_schema_version: int
    snapshot_json: str
    snapshot_sha256: str
    completed_at: str
    completed_by_display_name: str
    superseded_at: str | None


@dataclass(frozen=True)
class LearningConferenceRevisionHistory:
    """One stable LEG aggregate with all immutable revisions."""

    conference: LearningConferenceRecord
    revisions: tuple[LearningConferenceRevisionRecord, ...]


@dataclass(frozen=True)
class LearningConferenceCompletionResult:
    """Aggregate and current revision returned by one completion command."""

    conference: LearningConferenceRecord
    revision: LearningConferenceRevisionRecord
    created_revision: bool


@dataclass(frozen=True)
class LearningConferenceRevisionState:
    """Read-only completion state for one editable LCD."""

    conference: LearningConferenceRecord | None
    current_revision: LearningConferenceRevisionRecord | None
    revisions: tuple[LearningConferenceRevisionRecord, ...]
    draft_changed: bool
    current_snapshot_hash_valid: bool
    comparison_error: LearningConferenceCompletionError | None = None


@dataclass(frozen=True)
class LearningConferenceStudentSource:
    student_id: str
    first_name: str
    last_name: str
    group_id: str
    group_name: str
    course_id: str
    course_name: str

    @property
    def display_name(self) -> str:
        return " ".join(
            part for part in (self.first_name, self.last_name) if part
        ).strip()


@dataclass(frozen=True)
class LearningConferenceSubjectSource:
    subject_id: str
    subject_name: str


@dataclass(frozen=True)
class LearningConferenceCompetencySource:
    competency_id: str
    subject_id: str
    subject_name: str
    learning_area: str
    competency_group: str
    competency_text: str
    historical_reference: bool
    active_at_completion: bool
    catalog_status_at_completion: str


@dataclass(frozen=True)
class LearningConferenceObservationRatingSource:
    competency_id: str
    subject_id: str
    subject_name: str
    learning_area: str
    competency_group: str
    competency_text: str
    rating: str


@dataclass(frozen=True)
class LearningConferenceObservationSource:
    observation_id: str
    observed_on: str
    subject_id: str
    subject_name: str
    context: str
    note: str
    ratings: tuple[LearningConferenceObservationRatingSource, ...] = ()


@dataclass(frozen=True)
class LearningConferenceCompletionSource:
    """Complete resolved source for validating one explicit LCD completion."""

    draft: LearningConferenceDraftRecord
    student: LearningConferenceStudentSource | None
    subjects: tuple[LearningConferenceSubjectSource, ...]
    competencies: tuple[LearningConferenceCompetencySource, ...]
    observations: tuple[LearningConferenceObservationSource, ...]
    missing_subject_ids: tuple[str, ...] = ()
    missing_competency_ids: tuple[str, ...] = ()
    invalid_competency_ids: tuple[str, ...] = ()
    unavailable_observation_ids: tuple[str, ...] = ()
    invalid_observation_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class LearningConferenceVerifiedRevision:
    """One LCV plus its hash-verified, snapshot-only payload."""

    revision: LearningConferenceRevisionRecord
    snapshot: dict[str, object]


class LearningConferenceRepository(Protocol):
    def completion_transaction(self): ...

    def load_completion_source(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceCompletionSource | None: ...

    def save_completed_revision(
        self,
        source: LearningConferenceCompletionSource,
        *,
        snapshot_json: str,
        snapshot_sha256: str,
        completed_at: str,
        completed_by_display_name: str,
    ) -> LearningConferenceCompletionResult: ...

    def get_conference_for_source_draft(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceRecord | None: ...

    def list_revisions(
        self,
        learning_conference_id: str,
    ) -> tuple[LearningConferenceRevisionRecord, ...]: ...

    def get_revision(
        self,
        learning_conference_revision_id: str,
    ) -> LearningConferenceRevisionRecord | None: ...

    def list_revision_histories_for_student(
        self,
        student_id: str,
    ) -> tuple[LearningConferenceRevisionHistory, ...]: ...


class LearningConferenceCompletionValidator:
    """Validate shared results and every deliberately selected reference."""

    def validate(self, source: LearningConferenceCompletionSource) -> None:
        draft = source.draft
        if draft.status != LEARNING_CONFERENCE_DRAFT_STATUS:
            self._raise(
                LearningConferenceCompletionErrorCode.INVALID_REQUEST,
                "Nur ein bearbeitbarer LCD kann abgeschlossen werden.",
            )
        if source.student is None or source.student.student_id != draft.student_id:
            self._raise(
                LearningConferenceCompletionErrorCode.STUDENT_MISSING,
                "Der Schülerbezug des LEG ist nicht auflösbar.",
            )
        if not draft.conference_date:
            self._raise(
                LearningConferenceCompletionErrorCode.CONFERENCE_DATE_MISSING,
                "Für den Abschluss ist ein Gesprächsdatum erforderlich.",
            )
        try:
            date.fromisoformat(draft.conference_date)
        except ValueError as error:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.CONFERENCE_DATE_INVALID,
                "Das Gesprächsdatum ist ungültig.",
            ) from error
        if not draft.responsible_teacher.strip():
            self._raise(
                LearningConferenceCompletionErrorCode.RESPONSIBLE_TEACHER_MISSING,
                "Für den Abschluss ist eine verantwortliche Lehrkraft erforderlich.",
            )
        if not any(
            value.strip()
            for value in (
                draft.agreed_goals_text,
                draft.agreed_support_text,
                draft.agreed_agreements_text,
            )
        ):
            self._raise(
                LearningConferenceCompletionErrorCode.SHARED_RESULT_MISSING,
                "Mindestens ein gemeinsames Ziel, eine Unterstützung oder eine Vereinbarung ist erforderlich.",
            )
        self._validate_period(draft)
        if source.missing_subject_ids or len(source.subjects) != len(draft.subject_ids):
            ids = source.missing_subject_ids or draft.subject_ids
            self._raise(
                LearningConferenceCompletionErrorCode.SUBJECT_REFERENCE_MISSING,
                "Ausgewählte Fachreferenzen sind nicht vollständig auflösbar.",
                ids,
            )
        if source.missing_competency_ids or len(source.competencies) != len(
            draft.competency_ids
        ):
            ids = source.missing_competency_ids or draft.competency_ids
            self._raise(
                LearningConferenceCompletionErrorCode.COMPETENCY_REFERENCE_MISSING,
                "Ausgewählte Kompetenzreferenzen sind nicht vollständig auflösbar.",
                ids,
            )
        if source.invalid_competency_ids:
            self._raise(
                LearningConferenceCompletionErrorCode.COMPETENCY_REFERENCE_INVALID,
                "Ausgewählte Kompetenzen gehören nicht zu den gewählten Fachbereichen.",
                source.invalid_competency_ids,
            )
        if source.unavailable_observation_ids or len(source.observations) != len(
            draft.observation_ids
        ):
            ids = source.unavailable_observation_ids or draft.observation_ids
            self._raise(
                LearningConferenceCompletionErrorCode.OBSERVATION_UNAVAILABLE,
                "Ausgewählte Beobachtungsbelege sind nicht mehr verfügbar.",
                ids,
            )
        if source.invalid_observation_ids:
            self._raise(
                LearningConferenceCompletionErrorCode.OBSERVATION_INVALID,
                "Ausgewählte Beobachtungsbelege gehören nicht zu diesem Kind.",
                source.invalid_observation_ids,
            )

    def _validate_period(self, draft: LearningConferenceDraftRecord) -> None:
        if not (draft.period_start or draft.period_end):
            return
        if not (draft.period_start and draft.period_end):
            self._raise(
                LearningConferenceCompletionErrorCode.PERIOD_INVALID,
                "Ein LEG-Zeitraum benötigt Start und Ende.",
            )
        try:
            start = date.fromisoformat(draft.period_start)
            end = date.fromisoformat(draft.period_end)
        except ValueError as error:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.PERIOD_INVALID,
                "Der LEG-Zeitraum enthält ungültige Datumswerte.",
            ) from error
        if end < start:
            self._raise(
                LearningConferenceCompletionErrorCode.PERIOD_INVALID,
                "Das Ende des LEG-Zeitraums darf nicht vor dem Anfang liegen.",
            )

    @staticmethod
    def _raise(
        code: LearningConferenceCompletionErrorCode,
        message: str,
        reference_ids: tuple[str, ...] = (),
    ) -> None:
        raise LearningConferenceCompletionError(
            code,
            message,
            reference_ids=tuple(sorted(reference_ids)),
        )


class LearningConferenceSnapshotBuilder:
    """Build only the shared, historically reproducible LEG completion state."""

    _cross_topic_labels = {
        "work_habits": "Arbeitsverhalten",
        "social_behavior": "Sozialverhalten",
        "independence": "Selbstständigkeit",
        "learning_organization": "Lernorganisation",
    }

    def build(self, source: LearningConferenceCompletionSource) -> dict[str, object]:
        draft = source.draft
        student = source.student
        if student is None:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.STUDENT_MISSING,
                "Schülerdaten fehlen für den Abschluss-Snapshot.",
            )
        return {
            "snapshot_schema_version": LEARNING_CONFERENCE_SNAPSHOT_SCHEMA_VERSION,
            "source_learning_conference_draft_id": draft.learning_conference_draft_id,
            "student": {
                "student_id": student.student_id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "display_name": student.display_name,
                "group": {"group_id": student.group_id, "group_name": student.group_name},
                "course": {"course_id": student.course_id, "course_name": student.course_name},
            },
            "conference_date": draft.conference_date,
            "period": {"start": draft.period_start, "end": draft.period_end},
            "responsible_teacher": draft.responsible_teacher,
            "shared_results": {
                "goals": draft.agreed_goals_text,
                "support": draft.agreed_support_text,
                "agreements": draft.agreed_agreements_text,
                "responsibilities": draft.responsibilities_text,
                "next_review_date": draft.next_review_date,
            },
            "subjects": [
                {"subject_id": item.subject_id, "subject_name": item.subject_name}
                for item in source.subjects
            ],
            "cross_topics": [
                {"key": key, "label": self._cross_topic_labels[key]}
                for key in draft.cross_topic_keys
            ],
            "competencies": [
                {
                    "competency_id": item.competency_id,
                    "subject_id": item.subject_id,
                    "subject_name": item.subject_name,
                    "learning_area": item.learning_area,
                    "competency_group": item.competency_group,
                    "competency_text": item.competency_text,
                    "historical_reference": item.historical_reference,
                    "active_at_completion": item.active_at_completion,
                    "catalog_status_at_completion": item.catalog_status_at_completion,
                }
                for item in source.competencies
            ],
            "observations": [
                {
                    "observation_id": item.observation_id,
                    "observed_on": item.observed_on,
                    "subject_id": item.subject_id,
                    "subject_name": item.subject_name,
                    "context": item.context,
                    "content": item.note,
                    "ratings": [
                        {
                            "competency_id": rating.competency_id,
                            "subject_id": rating.subject_id,
                            "subject_name": rating.subject_name,
                            "learning_area": rating.learning_area,
                            "competency_group": rating.competency_group,
                            "competency_text": rating.competency_text,
                            "rating": rating.rating,
                        }
                        for rating in item.ratings
                    ],
                }
                for item in source.observations
            ],
        }


def canonical_learning_conference_snapshot_json(snapshot: dict[str, object]) -> str:
    return json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def learning_conference_snapshot_sha256(canonical_json: str) -> str:
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class LearningConferenceCompletionService:
    """Validate, snapshot, hash and persist one explicit LCD completion."""

    def __init__(
        self,
        repository: LearningConferenceRepository,
        *,
        validator: LearningConferenceCompletionValidator | None = None,
        snapshot_builder: LearningConferenceSnapshotBuilder | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.validator = validator or LearningConferenceCompletionValidator()
        self.snapshot_builder = snapshot_builder or LearningConferenceSnapshotBuilder()
        self.now = now or (lambda: datetime.now(UTC))

    def build_candidate(
        self,
        learning_conference_draft_id: str,
    ) -> tuple[LearningConferenceCompletionSource, str, str]:
        draft_id = learning_conference_draft_id.strip()
        if not draft_id:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.INVALID_REQUEST,
                "learning_conference_draft_id darf nicht leer sein.",
            )
        source = self.repository.load_completion_source(draft_id)
        if source is None:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.DRAFT_NOT_FOUND,
                f"LEG-Entwurf nicht gefunden: {draft_id}",
            )
        self.validator.validate(source)
        snapshot_json = canonical_learning_conference_snapshot_json(
            self.snapshot_builder.build(source)
        )
        return (
            source,
            snapshot_json,
            learning_conference_snapshot_sha256(snapshot_json),
        )

    def complete(
        self,
        *,
        learning_conference_draft_id: str,
    ) -> LearningConferenceCompletionResult:
        with self.repository.completion_transaction():
            source, snapshot_json, snapshot_sha256 = self.build_candidate(
                learning_conference_draft_id
            )
            return self.repository.save_completed_revision(
                source,
                snapshot_json=snapshot_json,
                snapshot_sha256=snapshot_sha256,
                completed_at=self._timestamp(),
                completed_by_display_name=(
                    source.draft.responsible_teacher
                ),
            )

    def _timestamp(self) -> str:
        return self.now().astimezone(UTC).replace(microsecond=0).isoformat()


class LearningConferenceRevisionReadService:
    """Verify immutable snapshots before any historical UI projection."""

    def __init__(
        self,
        repository: LearningConferenceRepository,
        completion_service: LearningConferenceCompletionService | None = None,
    ) -> None:
        self.repository = repository
        self.completion_service = completion_service or LearningConferenceCompletionService(
            repository
        )

    def load_verified_revision(
        self,
        learning_conference_revision_id: str,
    ) -> LearningConferenceVerifiedRevision:
        revision = self.repository.get_revision(
            learning_conference_revision_id.strip()
        )
        if revision is None:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.REVISION_NOT_FOUND,
                "LEG-Revision wurde nicht gefunden.",
            )
        snapshot = self.verify_revision(revision)
        return LearningConferenceVerifiedRevision(revision, snapshot)

    def revision_histories_for_student(
        self,
        student_id: str,
    ) -> tuple[LearningConferenceRevisionHistory, ...]:
        """Load every LEG history for one student in one repository read."""
        return self.repository.list_revision_histories_for_student(
            student_id.strip()
        )

    def verify_revision(
        self,
        revision: LearningConferenceRevisionRecord,
    ) -> dict[str, object]:
        """Verify one already loaded immutable LEG snapshot."""
        return self._verify_snapshot(revision)

    def state_for_draft(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceRevisionState:
        conference = self.repository.get_conference_for_source_draft(
            learning_conference_draft_id.strip()
        )
        if conference is None:
            return LearningConferenceRevisionState(None, None, (), False, True)
        revisions = self.repository.list_revisions(conference.learning_conference_id)
        current = next(
            (item for item in revisions if item.status == COMPLETED_REVISION_STATUS),
            None,
        )
        hash_valid = current is not None
        if current is not None:
            try:
                self.verify_revision(current)
            except LearningConferenceCompletionError:
                hash_valid = False
        try:
            _, _, candidate_hash = self.completion_service.build_candidate(
                learning_conference_draft_id
            )
            changed = current is None or candidate_hash != current.snapshot_sha256
            comparison_error = None
        except LearningConferenceCompletionError as error:
            changed = True
            comparison_error = error
        return LearningConferenceRevisionState(
            conference,
            current,
            tuple(sorted(revisions, key=lambda item: item.revision_number, reverse=True)),
            changed,
            hash_valid,
            comparison_error,
        )

    def _verify_snapshot(
        self,
        revision: LearningConferenceRevisionRecord,
    ) -> dict[str, object]:
        if revision.snapshot_schema_version != LEARNING_CONFERENCE_SNAPSHOT_SCHEMA_VERSION:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.SNAPSHOT_INVALID,
                "Die Snapshot-Schemaversion der LEG-Revision wird nicht unterstützt.",
            )
        if learning_conference_snapshot_sha256(revision.snapshot_json) != revision.snapshot_sha256:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.SNAPSHOT_INVALID,
                "Die SHA-256-Prüfung der LEG-Revision ist fehlgeschlagen.",
            )
        try:
            value = json.loads(revision.snapshot_json)
        except (TypeError, json.JSONDecodeError) as error:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.SNAPSHOT_INVALID,
                "Der Snapshot der LEG-Revision ist ungültig.",
            ) from error
        if not isinstance(value, dict):
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.SNAPSHOT_INVALID,
                "Der Snapshot der LEG-Revision besitzt keine Objektstruktur.",
            )
        required = {
            "snapshot_schema_version",
            "source_learning_conference_draft_id",
            "student",
            "conference_date",
            "responsible_teacher",
            "shared_results",
            "subjects",
            "cross_topics",
            "competencies",
            "observations",
        }
        if required - set(value):
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.SNAPSHOT_INVALID,
                "Der Snapshot der LEG-Revision ist unvollständig.",
            )
        student = value.get("student")
        shared_results = value.get("shared_results")
        if (
            value.get("snapshot_schema_version")
            != LEARNING_CONFERENCE_SNAPSHOT_SCHEMA_VERSION
            or not str(value.get("source_learning_conference_draft_id", "")).strip()
            or not isinstance(student, dict)
            or not str(student.get("student_id", "")).strip()
            or not isinstance(shared_results, dict)
            or not str(value.get("responsible_teacher", "")).strip()
            or any(
                not isinstance(value.get(key), list)
                for key in ("subjects", "cross_topics", "competencies", "observations")
            )
        ):
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.SNAPSHOT_INVALID,
                "Der Snapshotvertrag der LEG-Revision ist ungültig.",
            )
        try:
            date.fromisoformat(str(value.get("conference_date", "")))
        except ValueError as error:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.SNAPSHOT_INVALID,
                "Der Snapshot enthält kein gültiges Gesprächsdatum.",
            ) from error
        for key in ("subjects", "cross_topics", "competencies", "observations"):
            if any(not isinstance(item, dict) for item in value[key]):
                raise LearningConferenceCompletionError(
                    LearningConferenceCompletionErrorCode.SNAPSHOT_INVALID,
                    "Der Snapshot enthält ungültige Referenzdaten.",
                )
        if canonical_learning_conference_snapshot_json(value) != revision.snapshot_json:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.SNAPSHOT_INVALID,
                "Der Snapshot der LEG-Revision ist nicht kanonisch gespeichert.",
            )
        return value
