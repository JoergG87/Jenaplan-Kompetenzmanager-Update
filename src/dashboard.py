"""Dashboard sheet for the Jenaplan Kompetenzmanager."""

from datetime import date

from openpyxl import Workbook

from .styles import StyleManager


class DashboardSheet:
    """Create the dashboard worksheet."""

    title = "Dashboard"
    table_name = "DashboardTabelle"

    def __init__(self, styles: StyleManager) -> None:
        """Initialize the sheet with shared styles."""
        self.styles = styles

    def create(self, workbook: Workbook) -> None:
        """Create the dashboard worksheet."""
        worksheet = workbook.create_sheet(self.title)
        self.styles.apply_base_sheet(worksheet, self.title)
        next_row = self.styles.write_key_values(
            worksheet,
            self.styles.content_start_row,
            (
                ("Projektname", "Jenaplan-Kompetenzmanager"),
                ("Excel-Version", "Jenaplan_v3.2.xlsx"),
                ("Projektversion", self.styles.project_version),
                ("Erstellungsdatum", date.today().isoformat()),
            ),
        )
        self.styles.write_table(
            worksheet,
            next_row + 1,
            ("Bereich", "Status", "Hinweis"),
            self.table_name,
        )
