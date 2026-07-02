"""Master-data light view models for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass


MASTER_DATA_EMPTY_NAME_MESSAGE = "Bitte einen Namen eingeben."
MASTER_DATA_SAVE_PLACEHOLDER_MESSAGE = (
    "Stammdaten werden in einem späteren Sprint dauerhaft gespeichert."
)


@dataclass(frozen=True)
class MasterDataItemViewModel:
    """Display-ready group or course row for the master-data light screen."""

    item_id: str
    name: str
    is_persistent: bool

    @property
    def status_label(self) -> str:
        """Return whether the item comes from the current data source."""
        if self.is_persistent:
            return "Vorhanden"
        return "Nur vorgemerkt"


@dataclass(frozen=True)
class MasterDataViewModel:
    """Display model for group and course master data."""

    groups: tuple[MasterDataItemViewModel, ...]
    courses: tuple[MasterDataItemViewModel, ...]


def normalize_master_data_name(name: str) -> str:
    """Return a validated master-data name for non-persistent UI edits."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError(MASTER_DATA_EMPTY_NAME_MESSAGE)
    return normalized_name
