"""Observation UX prototype view models for the PySide6 desktop app."""

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

OBSERVATION_SAVE_PLACEHOLDER_MESSAGE = (
    "Beobachtungen werden in einem späteren Sprint gespeichert."
)

OBSERVATION_ATTACHMENT_PLACEHOLDER_MESSAGE = (
    "Anhänge werden in einem späteren Sprint gespeichert."
)

OBSERVATION_ATTACHMENT_EMPTY_STATE = "Noch keine Anhänge ausgewählt."


@dataclass(frozen=True)
class ObservationCompetencyRatingDraft:
    """Selected competency rating data kept in the non-persistent draft."""

    subject_key: str
    learning_area: str
    competency_group: str
    competency_text: str
    rating: str

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
            subject_key=getattr(entry, "subject_key"),
            learning_area=getattr(entry, "learning_area"),
            competency_group=getattr(entry, "competency_group"),
            competency_text=getattr(entry, "competency_text"),
            rating=rating,
        )


@dataclass(frozen=True)
class ObservationDraftViewModel:
    """Non-persistent draft state for the observation UX prototype."""

    student_id: str
    student_name: str
    date_text: str
    subject_key: str
    subject: str
    competency_ratings: tuple[ObservationCompetencyRatingDraft, ...]
    context: str
    note: str
    attachment_names: tuple[str, ...] = ()


def observation_rating_keys() -> tuple[str, ...]:
    """Return the stable rating tokens shown in the prototype labels."""
    return tuple(option.split(" ", 1)[0] for option in OBSERVATION_RATING_OPTIONS)
