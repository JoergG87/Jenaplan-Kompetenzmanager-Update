"""Application command definitions."""

from .observation import (
    CreateObservationCommand,
    DeleteObservationCommand,
    UpdateObservationCommand,
)
from .student import CreateStudentCommand

__all__ = [
    "CreateObservationCommand",
    "DeleteObservationCommand",
    "UpdateObservationCommand",
    "CreateStudentCommand",
]
