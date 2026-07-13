"""Domain records and service for persistent learning-conference drafts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol


LEARNING_CONFERENCE_DRAFT_ID_PREFIX = "LCD"
LEARNING_CONFERENCE_DRAFT_STATUS = "draft"
LEARNING_CONFERENCE_CROSS_TOPIC_KEYS = (
    "work_habits",
    "social_behavior",
    "independence",
    "learning_organization",
)
LEARNING_CONFERENCE_CHART_TYPES = (
    "documentation_coverage",
    "competency_timeline",
    "observation_timeline",
)


class LearningConferenceDraftError(ValueError):
    """Raised when a LEG draft violates its approved contract."""


@dataclass(frozen=True)
class LearningConferenceDraftRecord:
    """Persistent editable LEG state; explicitly not a final conversation record."""

    learning_conference_draft_id: str
    student_id: str
    period_start: str
    period_end: str
    conference_date: str
    status: str
    responsible_teacher: str
    conversation_entry_text: str
    child_retrospective_text: str
    teacher_perspective_text: str
    strengths_text: str
    development_fields_text: str
    prepared_goals_text: str
    prepared_support_text: str
    prepared_agreements_text: str
    agreed_goals_text: str
    agreed_support_text: str
    agreed_agreements_text: str
    responsibilities_text: str
    next_review_date: str
    created_at: str
    updated_at: str
    subject_ids: tuple[str, ...] = ()
    cross_topic_keys: tuple[str, ...] = ()
    competency_ids: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()
    chart_types: tuple[str, ...] = ()


class LearningConferenceDraftRepository(Protocol):
    """Persistence contract for the complete LEG-draft aggregate."""

    def next_learning_conference_draft_id(self) -> str: ...

    def create_learning_conference_draft(
        self,
        draft: LearningConferenceDraftRecord,
    ) -> LearningConferenceDraftRecord: ...

    def update_learning_conference_draft(
        self,
        draft: LearningConferenceDraftRecord,
    ) -> LearningConferenceDraftRecord: ...

    def get_learning_conference_draft(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceDraftRecord | None: ...

    def list_learning_conference_drafts_for_student(
        self,
        student_id: str,
    ) -> tuple[LearningConferenceDraftRecord, ...]: ...


class LearningConferenceDraftService:
    """Validate and coordinate create/update operations for LEG drafts."""

    def __init__(
        self,
        repository: LearningConferenceDraftRepository,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.now = now or (lambda: datetime.now(UTC))

    def create_learning_conference_draft(
        self,
        **values: object,
    ) -> LearningConferenceDraftRecord:
        timestamp = self._timestamp()
        draft = self._record(
            learning_conference_draft_id=(
                self.repository.next_learning_conference_draft_id()
            ),
            status=LEARNING_CONFERENCE_DRAFT_STATUS,
            created_at=timestamp,
            updated_at=timestamp,
            **values,
        )
        self._validate(draft)
        return self.repository.create_learning_conference_draft(draft)

    def update_learning_conference_draft(
        self,
        *,
        learning_conference_draft_id: str,
        **values: object,
    ) -> LearningConferenceDraftRecord:
        draft_id = learning_conference_draft_id.strip()
        existing = self.repository.get_learning_conference_draft(draft_id)
        if existing is None:
            raise LearningConferenceDraftError(
                f"learning_conference_draft_id nicht gefunden: {draft_id}"
            )
        student_id = str(values.get("student_id", "")).strip()
        if student_id != existing.student_id:
            raise LearningConferenceDraftError(
                "student_id eines LEG-Entwurfs darf nicht wechseln."
            )
        updated = self._record(
            learning_conference_draft_id=existing.learning_conference_draft_id,
            status=LEARNING_CONFERENCE_DRAFT_STATUS,
            created_at=existing.created_at,
            updated_at=self._timestamp(),
            **values,
        )
        self._validate(updated)
        return self.repository.update_learning_conference_draft(updated)

    def _record(self, **values: object) -> LearningConferenceDraftRecord:
        text_fields = (
            "student_id",
            "period_start",
            "period_end",
            "conference_date",
            "responsible_teacher",
            "conversation_entry_text",
            "child_retrospective_text",
            "teacher_perspective_text",
            "strengths_text",
            "development_fields_text",
            "prepared_goals_text",
            "prepared_support_text",
            "prepared_agreements_text",
            "agreed_goals_text",
            "agreed_support_text",
            "agreed_agreements_text",
            "responsibilities_text",
            "next_review_date",
        )
        normalized = dict(values)
        for field_name in text_fields:
            normalized[field_name] = str(normalized.get(field_name, "")).strip()
        for field_name in (
            "learning_conference_draft_id",
            "status",
            "created_at",
            "updated_at",
        ):
            normalized[field_name] = str(normalized[field_name]).strip()
        normalized["subject_ids"] = self._normalize_ids(
            tuple(normalized.get("subject_ids", ()))
        )
        normalized["competency_ids"] = self._normalize_ids(
            tuple(normalized.get("competency_ids", ()))
        )
        normalized["observation_ids"] = self._normalize_ids(
            tuple(normalized.get("observation_ids", ()))
        )
        normalized["cross_topic_keys"] = self._normalize_choices(
            tuple(normalized.get("cross_topic_keys", ())),
            LEARNING_CONFERENCE_CROSS_TOPIC_KEYS,
            "Uebergreifende Gespraechsthemen",
        )
        normalized["chart_types"] = self._normalize_choices(
            tuple(normalized.get("chart_types", ())),
            LEARNING_CONFERENCE_CHART_TYPES,
            "Diagrammtypen",
        )
        return LearningConferenceDraftRecord(**normalized)

    def _validate(self, draft: LearningConferenceDraftRecord) -> None:
        if not draft.student_id:
            raise LearningConferenceDraftError("student_id darf nicht leer sein.")
        if draft.status != LEARNING_CONFERENCE_DRAFT_STATUS:
            raise LearningConferenceDraftError("status muss in Sprint 7G.1 draft sein.")
        has_period = bool(draft.period_start or draft.period_end)
        if has_period and not (draft.period_start and draft.period_end):
            raise LearningConferenceDraftError(
                "Ein LEG-Zeitraum braucht period_start und period_end."
            )
        if not has_period and not draft.conference_date:
            raise LearningConferenceDraftError(
                "LEG-Entwurf braucht einen Zeitraum oder ein Gespraechsdatum."
            )
        if has_period:
            start = self._parse_date(draft.period_start, "period_start")
            end = self._parse_date(draft.period_end, "period_end")
            if end < start:
                raise LearningConferenceDraftError(
                    "period_end darf nicht vor period_start liegen."
                )
        if draft.conference_date:
            self._parse_date(draft.conference_date, "conference_date")
        if draft.next_review_date:
            self._parse_date(draft.next_review_date, "next_review_date")

    def _parse_date(self, value: str, field_name: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise LearningConferenceDraftError(
                f"{field_name} muss ein ISO-Datum sein."
            ) from error

    def _normalize_ids(self, values: tuple[object, ...]) -> tuple[str, ...]:
        normalized = tuple(str(value).strip() for value in values)
        if any(not value for value in normalized):
            raise LearningConferenceDraftError("Referenz-IDs duerfen nicht leer sein.")
        if len(set(normalized)) != len(normalized):
            raise LearningConferenceDraftError(
                "Referenz-IDs duerfen nicht doppelt vorkommen."
            )
        return tuple(sorted(normalized))

    def _normalize_choices(
        self,
        values: tuple[object, ...],
        allowed: tuple[str, ...],
        label: str,
    ) -> tuple[str, ...]:
        normalized = self._normalize_ids(values)
        invalid = set(normalized) - set(allowed)
        if invalid:
            raise LearningConferenceDraftError(
                f"Unzulaessige {label}: {', '.join(sorted(invalid))}"
            )
        return normalized

    def _timestamp(self) -> str:
        return self.now().astimezone(UTC).replace(microsecond=0).isoformat()
