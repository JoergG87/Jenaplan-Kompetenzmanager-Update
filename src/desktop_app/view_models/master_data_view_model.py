"""Master-data view models for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.constants import COURSE_COLOR_OPTIONS


MASTER_DATA_EMPTY_NAME_MESSAGE = "Bitte einen Namen eingeben."
MASTER_DATA_SAVE_PLACEHOLDER_MESSAGE = "Stammdaten wurden gespeichert."
COURSE_GROUP_EMPTY_GROUPS_MESSAGE = "Bitte mindestens eine Stammgruppe auswählen."
COURSE_GROUP_EMPTY_COURSES_MESSAGE = "Bitte mindestens einen Kurs auswählen."


@dataclass(frozen=True)
class MasterDataItemViewModel:
    """Display-ready group or course row for the master-data screen."""

    item_id: str
    name: str
    is_persistent: bool
    color_name: str = ""
    color_hex: str = ""

    @property
    def status_label(self) -> str:
        """Return whether the item comes from the current data source."""
        if self.is_persistent:
            return "Vorhanden"
        return "Nicht gespeichert"

    @property
    def has_color(self) -> bool:
        """Return whether this item carries a course color."""
        return bool(self.color_hex)


@dataclass(frozen=True)
class MasterDataViewModel:
    """Display model for group and course master data."""

    groups: tuple[MasterDataItemViewModel, ...]
    courses: tuple[MasterDataItemViewModel, ...]
    course_groups: tuple["CourseGroupViewModel", ...] = ()


@dataclass(frozen=True)
class CourseGroupViewModel:
    """Persisted course-group configuration for Mathe/Deutsch courses."""

    course_group_id: str
    name: str
    selected_group_ids: tuple[str, ...]
    selected_course_ids: tuple[str, ...]


def normalize_master_data_name(name: str) -> str:
    """Return a validated master-data name for UI edits."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError(MASTER_DATA_EMPTY_NAME_MESSAGE)
    return normalized_name


def course_color_from_key(color_key: str, fallback_index: int = 0) -> tuple[str, str]:
    """Return a stable UI course color from a stored key or fallback index."""
    normalized_color_key = color_key.strip()
    if normalized_color_key and not normalized_color_key.startswith("#"):
        normalized_color_key = f"#{normalized_color_key}"
    for color_name, color_hex in COURSE_COLOR_OPTIONS:
        if normalized_color_key.upper() == color_hex.upper():
            return color_name, color_hex
    return COURSE_COLOR_OPTIONS[fallback_index % len(COURSE_COLOR_OPTIONS)]


def course_color_name(color_hex: str) -> str:
    """Return the visible color name for a course color."""
    for option_name, option_hex in COURSE_COLOR_OPTIONS:
        if color_hex.upper() == option_hex.upper():
            return option_name
    return "Grau"
