"""Changelog sheet for the Jenaplan Kompetenzmanager."""

from openpyxl import Workbook

from .styles import StyleManager


class ChangelogSheet:
    """Create the changelog worksheet."""

    title = "Changelog"
    table_name = "ChangelogTabelle"

    def __init__(self, styles: StyleManager) -> None:
        """Initialize the sheet with shared styles."""
        self.styles = styles

    def create(self, workbook: Workbook) -> None:
        """Create the changelog worksheet."""
        worksheet = workbook.create_sheet(self.title)
        self.styles.apply_base_sheet(worksheet, self.title)
        self.styles.write_table(
            worksheet,
            self.styles.content_start_row,
            ("Version", "Datum", "Änderung", "Status"),
            self.table_name,
        )
