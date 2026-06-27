"""Workbook builder for the Jenaplan Kompetenzmanager."""

from pathlib import Path

from .ux_prototype import UXPrototypeWorkbookBuilder


class WorkbookBuilder:
    """Build and save the UX prototype workbook."""

    def __init__(self, output_path: Path) -> None:
        """Initialize the workbook builder."""
        self.output_path = output_path

    def build(self) -> Path:
        """Create the workbook, add sheets, and save the file."""
        # Sprint 2c routes the build through the UX prototype on purpose.
        # The earlier technical generator is no longer the UX reference.
        return UXPrototypeWorkbookBuilder(self.output_path).build()
