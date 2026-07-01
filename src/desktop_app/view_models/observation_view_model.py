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
class ObservationDraftViewModel:
    """Non-persistent draft state for the observation UX prototype."""

    student_id: str
    student_name: str
    date_text: str
    subject: str
    competencies: tuple[str, ...]
    context: str
    rating: str
    note: str
    attachment_names: tuple[str, ...] = ()


def observation_rating_keys() -> tuple[str, ...]:
    """Return the stable rating tokens shown in the prototype labels."""
    return tuple(option.split(" ", 1)[0] for option in OBSERVATION_RATING_OPTIONS)
