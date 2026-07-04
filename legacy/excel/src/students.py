"""Student sheet for the Jenaplan Kompetenzmanager."""

from openpyxl import Workbook

from .styles import StyleManager


class StudentSheet:
    """Create the student worksheet."""

    title = "Schüler"
    table_name = "SchuelerTabelle"

    def __init__(self, styles: StyleManager) -> None:
        """Initialize the sheet with shared styles."""
        self.styles = styles

    def create(self, workbook: Workbook) -> None:
        """Create the student worksheet."""
        worksheet = workbook.create_sheet(self.title)
        self.styles.apply_base_sheet(worksheet, self.title)
        self.styles.write_table(
            worksheet,
            self.styles.content_start_row,
            ("Schüler-ID", "Vorname", "Nachname", "Klasse", "Status"),
            self.table_name,
        )
