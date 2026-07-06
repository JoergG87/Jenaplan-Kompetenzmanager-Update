"""Application command dispatcher."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, is_dataclass
from typing import Any, Protocol


class CommandHandler(Protocol):
    """Callable command handler contract."""

    def __call__(self, command: object) -> object:
        """Handle an application command."""


class CommandDispatchError(RuntimeError):
    """Raised when a command cannot be dispatched."""


@dataclass(frozen=True)
class SuccessResult:
    """Successful application command result."""

    command_name: str
    value: object
    success: bool = True


@dataclass(frozen=True)
class ErrorResult:
    """Failed application command result."""

    command_name: str
    message: str
    error_type: str
    success: bool = False


class ApplicationCommandDispatcher:
    """Dispatch application commands to registered domain service handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, command_name: str, handler: CommandHandler) -> None:
        """Register a handler for a command name."""
        if not command_name:
            raise CommandDispatchError("command_name darf nicht leer sein.")
        self._handlers[command_name] = handler

    def dispatch(self, command: object) -> object:
        """Dispatch a command object to its registered handler."""
        command_name = self._command_name(command)
        handler = self._handlers.get(command_name)
        if handler is None:
            return ErrorResult(
                command_name,
                f"Kein Handler fuer Command registriert: {command_name}",
                CommandDispatchError.__name__,
            )
        try:
            return SuccessResult(command_name, handler(command))
        except Exception as exc:
            return ErrorResult(command_name, str(exc), type(exc).__name__)

    def registered_commands(self) -> tuple[str, ...]:
        """Return registered command names."""
        return tuple(sorted(self._handlers))

    def _command_name(self, command: object) -> str:
        command_name = getattr(command, "command_name", None)
        if isinstance(command_name, str) and command_name:
            return command_name
        if is_dataclass(command):
            raise CommandDispatchError("Dataclass-Command ohne command_name.")
        raise CommandDispatchError("Command muss ein command_name-Attribut besitzen.")


def student_create_handler(service: Any) -> Callable[[object], object]:
    """Create a handler that delegates `student.create` to StudentService."""

    def handle(command: object) -> object:
        return service.create_student(
            first_name=getattr(command, "first_name"),
            last_name=getattr(command, "last_name"),
            group_id=getattr(command, "group_id"),
            course_id=getattr(command, "course_id"),
            student_notes=getattr(command, "student_notes", ""),
        )

    return handle


def student_update_handler(service: Any) -> Callable[[object], object]:
    """Create a handler that delegates `student.update` to StudentService."""

    def handle(command: object) -> object:
        return service.update_student(
            student_id=getattr(command, "student_id"),
            first_name=getattr(command, "first_name"),
            last_name=getattr(command, "last_name"),
            group_id=getattr(command, "group_id"),
            course_id=getattr(command, "course_id"),
            student_notes=getattr(command, "student_notes", ""),
        )

    return handle


def observation_create_handler(service: Any) -> Callable[[object], object]:
    """Create a handler that delegates `observation.create` to ObservationService."""

    def handle(command: object) -> object:
        return service.create_observation(
            student_id=getattr(command, "student_id"),
            date=getattr(command, "date"),
            subject_id=getattr(command, "subject_id"),
            context=getattr(command, "context"),
            note=getattr(command, "note"),
            competency_ratings=getattr(command, "competency_ratings"),
        )

    return handle


def observation_update_handler(service: Any) -> Callable[[object], object]:
    """Create a handler that delegates `observation.update` to ObservationService."""

    def handle(command: object) -> object:
        return service.update_observation(
            observation_id=getattr(command, "observation_id"),
            student_id=getattr(command, "student_id"),
            date=getattr(command, "date"),
            subject_id=getattr(command, "subject_id"),
            context=getattr(command, "context"),
            note=getattr(command, "note"),
            competency_ratings=getattr(command, "competency_ratings"),
        )

    return handle


def observation_delete_handler(service: Any) -> Callable[[object], object]:
    """Create a handler that delegates `observation.delete` to ObservationService."""

    def handle(command: object) -> object:
        return service.delete_observation(
            observation_id=getattr(command, "observation_id"),
        )

    return handle
