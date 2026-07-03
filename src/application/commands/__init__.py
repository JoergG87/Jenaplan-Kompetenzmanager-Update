"""Application command definitions."""

from .observation import CreateObservationCommand
from .student import CreateStudentCommand

__all__ = ["CreateObservationCommand", "CreateStudentCommand"]
