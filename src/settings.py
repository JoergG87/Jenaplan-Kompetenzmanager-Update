"""Settings sheet for the Jenaplan Kompetenzmanager."""

from openpyxl import Workbook

from .styles import StyleManager


class SettingsSheet:
    """Create the settings worksheet."""

    title = "Einstellungen"
    table_name = "EinstellungenTabelle"

    def __init__(self, styles: StyleManager) -> None:
        """Initialize the sheet with shared styles."""
        self.styles = styles

    def create(self, workbook: Workbook) -> None:
        """Create the settings worksheet."""
        worksheet = workbook.create_sheet(self.title)
        self.styles.apply_base_sheet(worksheet, self.title)
        self.styles.write_table(
            worksheet,
            self.styles.content_start_row,
            ("Schlüssel", "Wert", "Beschreibung"),
            self.table_name,
        )
