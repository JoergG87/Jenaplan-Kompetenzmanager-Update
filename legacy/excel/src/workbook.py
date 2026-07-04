"""Workbook builder for the Jenaplan Kompetenzmanager."""

from pathlib import Path

from .ux_prototype import UXPrototypeWorkbookBuilder


class WorkbookBuilder:
    """Build and save the UX prototype workbook."""

    def __init__(self, output_path: Path, prototype_version: str = "v0.4") -> None:
        """Initialize the workbook builder."""
        self.output_path = output_path
        self.prototype_version = prototype_version

    def build(self) -> Path:
        """Create the workbook, add sheets, and save the file."""
        return UXPrototypeWorkbookBuilder(
            self.output_path,
            prototype_version=self.prototype_version,
        ).build()
