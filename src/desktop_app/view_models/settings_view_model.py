"""Settings view models for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass


DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE = (
    "Dokumentationsfächer wurden gespeichert."
)


@dataclass(frozen=True)
class DocumentationSubjectOptionViewModel:
    """Display-ready documentation subject option."""

    subject_id: str
    label: str
    selected: bool


@dataclass(frozen=True)
class SettingsViewModel:
    """Display model for app settings."""

    documentation_subjects: tuple[DocumentationSubjectOptionViewModel, ...]
