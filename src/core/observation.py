"""Observation domain model and write service."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from .constants import ID_SEQUENCE_WIDTH, OBSERVATION_ID_PREFIX


OBSERVATION_RATING_KEYS = ("++", "+", "-", "--")


class ObservationValidationError(ValueError):
    """Raised when observation data violates the registered schema."""


class ObservationRepositoryError(RuntimeError):
    """Raised when observation storage cannot be updated consistently."""


@dataclass(frozen=True)
class ObservationCompetencyRatingRecord:
    """Persisted rating for one competency inside one observation."""

    competency_id: str
    subject_id: str
    subject_display_name: str
    learning_area: str
    competency_group: str
    competency_text: str
    rating: str


@dataclass(frozen=True)
class ObservationRecord:
    """Persisted observation including its competency ratings."""

    observation_id: str
    student_id: str
    date: str
    subject_id: str
    context: str
    note: str
    active: bool
    created_at: str
    updated_at: str
    competency_ratings: tuple[ObservationCompetencyRatingRecord, ...]


class ObservationValidator:
    """Validate observation data against service-provided reference data."""

    def validate(
        self,
        observation_data: dict[str, object],
        valid_student_ids: Iterable[str],
    ) -> None:
        student_id = self._require_text(observation_data, "student_id")
        if student_id not in set(valid_student_ids):
            raise ObservationValidationError(f"Unbekannte student_id: {student_id}")
        self._require_text(observation_data, "date")
        self._require_text(observation_data, "subject_id")
        ratings = observation_data.get("competency_ratings")
        if not isinstance(ratings, tuple) or not ratings:
            raise ObservationValidationError("Mindestens eine Kompetenzbewertung ist erforderlich.")
        seen_competency_ids: set[str] = set()
        for rating in ratings:
            if not isinstance(rating, ObservationCompetencyRatingRecord):
                raise ObservationValidationError("Kompetenzbewertung hat ein unbekanntes Format.")
            self._validate_rating(rating, seen_competency_ids)

    def _validate_rating(
        self,
        rating: ObservationCompetencyRatingRecord,
        seen_competency_ids: set[str],
    ) -> None:
        for field_name in (
            "competency_id",
            "subject_id",
            "subject_display_name",
            "learning_area",
            "competency_text",
        ):
            value = getattr(rating, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ObservationValidationError(f"{field_name} darf nicht leer sein.")
        if rating.competency_id in seen_competency_ids:
            raise ObservationValidationError(
                f"competency_id mehrfach in Beobachtung: {rating.competency_id}"
            )
        seen_competency_ids.add(rating.competency_id)
        if rating.rating not in OBSERVATION_RATING_KEYS:
            raise ObservationValidationError(f"Ungueltige Bewertung: {rating.rating}")

    def _require_text(self, observation_data: dict[str, object], field_name: str) -> str:
        value = observation_data.get(field_name)
        if value is None:
            raise ObservationValidationError(f"Pflichtfeld fehlt: {field_name}")
        if not isinstance(value, str):
            raise ObservationValidationError(f"{field_name} muss Text sein.")
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ObservationValidationError(f"{field_name} darf nicht leer sein.")
        return cleaned_value


class ObservationService:
    """Coordinate observation write processes."""

    def __init__(
        self,
        repository: object,
        validator: ObservationValidator,
        valid_student_ids: Iterable[str],
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.validator = validator
        self.valid_student_ids = tuple(valid_student_ids)
        self.now_provider = now_provider or (lambda: datetime.now(UTC))

    def create_observation(
        self,
        *,
        student_id: str,
        date: str,
        subject_id: str,
        context: str,
        note: str,
        competency_ratings: tuple[ObservationCompetencyRatingRecord, ...],
    ) -> ObservationRecord:
        observation_data = {
            "student_id": student_id,
            "date": date,
            "subject_id": subject_id,
            "context": context,
            "note": note,
            "competency_ratings": competency_ratings,
        }
        self.validator.validate(observation_data, self.valid_student_ids)
        timestamp = self._timestamp()
        observation = ObservationRecord(
            self._generate_observation_id(),
            student_id.strip(),
            date.strip(),
            subject_id.strip(),
            context.strip(),
            note,
            True,
            timestamp,
            timestamp,
            competency_ratings,
        )
        return self.repository.create_observation(observation)

    def update_observation(
        self,
        *,
        observation_id: str,
        student_id: str,
        date: str,
        subject_id: str,
        context: str,
        note: str,
        competency_ratings: tuple[ObservationCompetencyRatingRecord, ...],
    ) -> ObservationRecord:
        observation_id = self._require_observation_id(observation_id)
        existing_observation = self.repository.get_observation(observation_id)
        if existing_observation is None:
            raise ObservationRepositoryError(
                f"observation_id nicht gefunden: {observation_id}"
            )
        observation_data = {
            "student_id": student_id,
            "date": date,
            "subject_id": subject_id,
            "context": context,
            "note": note,
            "competency_ratings": competency_ratings,
        }
        self.validator.validate(observation_data, self.valid_student_ids)
        observation = ObservationRecord(
            observation_id,
            student_id.strip(),
            date.strip(),
            subject_id.strip(),
            context.strip(),
            note,
            True,
            existing_observation.created_at,
            self._timestamp(),
            competency_ratings,
        )
        return self.repository.update_observation(observation)

    def delete_observation(self, *, observation_id: str) -> ObservationRecord:
        observation_id = self._require_observation_id(observation_id)
        existing_observation = self.repository.get_observation(observation_id)
        if existing_observation is None:
            raise ObservationRepositoryError(
                f"observation_id nicht gefunden: {observation_id}"
            )
        return self.repository.deactivate_observation(
            observation_id,
            self._timestamp(),
        )

    def _generate_observation_id(self) -> str:
        used_ids = {
            observation.observation_id
            for observation in self.repository.list_observations()
        }
        next_number = 1
        while True:
            observation_id = f"{OBSERVATION_ID_PREFIX}-{next_number:0{ID_SEQUENCE_WIDTH}}"
            if observation_id not in used_ids:
                return observation_id
            next_number += 1

    def _timestamp(self) -> str:
        return self.now_provider().replace(microsecond=0).isoformat()

    def _require_observation_id(self, observation_id: str) -> str:
        if not isinstance(observation_id, str) or not observation_id.strip():
            raise ObservationValidationError("observation_id darf nicht leer sein.")
        return observation_id.strip()
