"""Observation view models for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass


OBSERVATION_CONTEXT_OPTIONS = (
    "Lernzielkontrolle",
    "Präsentation",
    "Einzelgespräch",
    "Gruppenarbeit",
    "Leseübung",
)

OBSERVATION_RATING_OPTIONS = (
    "++ sicher erreicht",
    "+ erreicht",
    "- in Entwicklung",
    "-- Unterstützungsbedarf",
)

OBSERVATION_SAVE_SUCCESS_MESSAGE = "Beobachtung wurde gespeichert."

OBSERVATION_UPDATE_SUCCESS_MESSAGE = "Beobachtung wurde aktualisiert."

OBSERVATION_SAVE_VALIDATION_MESSAGE = (
    "Bitte mindestens eine Kompetenz mit Bewertung auswählen."
)

OBSERVATION_ATTACHMENT_PLACEHOLDER_MESSAGE = (
    "Anhänge werden in einem späteren Sprint gespeichert."
)

OBSERVATION_ATTACHMENT_EMPTY_STATE = "Noch keine Anhänge ausgewählt."

OBSERVATION_CROSS_SUBJECT_LABEL = "Fächerübergreifend"


@dataclass(frozen=True)
class ObservationCompetencyRatingDraft:
    """Selected competency rating data kept in the observation draft."""

    subject_key: str
    subject_display_name: str
    learning_area: str
    competency_group: str
    competency_text: str
    rating: str
    competency_id: str = ""

    @property
    def display_label(self) -> str:
        """Return the short UI label for selected competencies."""
        return self.learning_area

    @classmethod
    def from_catalog_entry(
        cls,
        entry: object,
        rating: str,
    ) -> "ObservationCompetencyRatingDraft":
        """Create a draft rating from a curriculum catalog entry."""
        return cls(
            competency_id=getattr(entry, "competency_id"),
            subject_key=getattr(entry, "subject_key"),
            subject_display_name=getattr(entry, "subject_display_name"),
            learning_area=getattr(entry, "learning_area"),
            competency_group=getattr(entry, "competency_group"),
            competency_text=getattr(entry, "competency_text"),
            rating=rating,
        )


@dataclass(frozen=True)
class ObservationDraftViewModel:
    """Draft state for the persisted observation workflow."""

    student_id: str
    student_name: str
    date_text: str
    competency_ratings: tuple[ObservationCompetencyRatingDraft, ...]
    context: str
    note: str
    subject_id: str = ""
    subject_display_name: str = ""
    attachment_names: tuple[str, ...] = ()
    observation_id: str = ""


@dataclass(frozen=True)
class ObservationRatingViewModel:
    """Displayed competency rating for one persisted observation."""

    competency_id: str
    subject_display_name: str
    learning_area: str
    competency_group: str
    competency_text: str
    rating: str

    @property
    def display_label(self) -> str:
        """Return the compact display label for the profile list."""
        return f"{self.rating} {self.subject_display_name} · {self.learning_area}"


@dataclass(frozen=True)
class ObservationListItem:
    """Profile-list item for one persisted observation."""

    observation_id: str
    student_id: str
    date_text: str
    subject_display_name: str
    context: str
    note: str
    competency_ratings: tuple[ObservationRatingViewModel, ...]

    @property
    def summary(self) -> str:
        """Return the compact first line for profile rendering."""
        parts = [self.date_text, self.subject_display_name]
        if self.context:
            parts.append(self.context)
        return " · ".join(part for part in parts if part)


@dataclass(frozen=True)
class StudentCompetencyStatusViewModel:
    """Latest observed rating for one student competency."""

    competency_id: str
    competency_label: str
    subject_id: str
    subject_display_name: str
    rating: str
    rating_label: str
    last_observation_date: str
    sort_order: int


@dataclass(frozen=True)
class StudentCompetencySubjectGroup:
    """Student competency statuses grouped by subject."""

    subject_id: str
    subject_display_name: str
    competencies: tuple[StudentCompetencyStatusViewModel, ...]


def observation_rating_label(rating: str) -> str:
    """Return the visible rating label for a persisted rating token."""
    for option in OBSERVATION_RATING_OPTIONS:
        if option.split(" ", 1)[0] == rating:
            return option
    return rating


def observation_rating_keys() -> tuple[str, ...]:
    """Return the stable rating tokens shown in the prototype labels."""
    return tuple(option.split(" ", 1)[0] for option in OBSERVATION_RATING_OPTIONS)
