"""Observation commands for the application layer."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.observation import ObservationCompetencyRatingRecord


@dataclass(frozen=True)
class CreateObservationCommand:
    """Command DTO for creating an observation through the application layer."""

    student_id: str
    date: str
    subject_id: str
    context: str
    note: str
    competency_ratings: tuple[ObservationCompetencyRatingRecord, ...]

    command_name: str = "observation.create"


@dataclass(frozen=True)
class UpdateObservationCommand:
    """Command DTO for updating an existing observation."""

    observation_id: str
    student_id: str
    date: str
    subject_id: str
    context: str
    note: str
    competency_ratings: tuple[ObservationCompetencyRatingRecord, ...]

    command_name: str = "observation.update"


@dataclass(frozen=True)
class DeleteObservationCommand:
    """Command DTO for soft-deleting an existing observation."""

    observation_id: str

    command_name: str = "observation.delete"
