"""Shared UI theme values for generated Excel prototypes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UiTheme:
    """Visual system for the Excel/macOS UX prototypes."""

    font_name: str = "Aptos"
    canvas: str = "F4F6F8"
    app_bar: str = "243D35"
    surface: str = "FFFFFF"
    surface_alt: str = "EEF4F1"
    border: str = "D8E1DD"
    border_strong: str = "B8C8C1"
    text: str = "1E2623"
    muted: str = "66736E"
    primary: str = "2F6F5E"
    primary_soft: str = "DDEDE7"
    accent_soft: str = "F4E7D4"
    disabled_fill: str = "E8ECEA"
    disabled_text: str = "87918D"
