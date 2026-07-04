"""Assessment sheet for the Jenaplan Kompetenzmanager."""

from openpyxl import Workbook

from .styles import StyleManager


class AssessmentSheet:
    """Create the assessment worksheet."""

    title = "Bewertungen"
    table_name = "BewertungenTabelle"

    def __init__(self, styles: StyleManager) -> None:
        """Initialize the sheet with shared styles."""
        self.styles = styles

    def create(self, workbook: Workbook) -> None:
        """Create the assessment worksheet."""
        worksheet = workbook.create_sheet(self.title)
        self.styles.apply_base_sheet(worksheet, self.title)
        self.styles.write_table(
            worksheet,
            self.styles.content_start_row,
            ("Bewertung-ID", "Schüler-ID", "Kompetenz-ID", "Bewertung", "Datum"),
            self.table_name,
        )
