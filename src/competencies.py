"""Competency sheet for the Jenaplan Kompetenzmanager."""

from openpyxl import Workbook

from .styles import StyleManager


class CompetencySheet:
    """Create the competency worksheet."""

    title = "Kompetenzen"
    table_name = "KompetenzenTabelle"

    def __init__(self, styles: StyleManager) -> None:
        """Initialize the sheet with shared styles."""
        self.styles = styles

    def create(self, workbook: Workbook) -> None:
        """Create the competency worksheet."""
        worksheet = workbook.create_sheet(self.title)
        self.styles.apply_base_sheet(worksheet, self.title)
        self.styles.write_table(
            worksheet,
            self.styles.content_start_row,
            ("Kompetenz-ID", "Bereich", "Kompetenz", "Beschreibung", "Aktiv"),
            self.table_name,
        )
