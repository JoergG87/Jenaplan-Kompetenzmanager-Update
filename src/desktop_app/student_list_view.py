"""Student list view for the experimental PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem

from src.desktop_app.student_adapter import StudentListItem


class StudentListView(QTableWidget):
    """Read-only student list fed by adapter DTOs."""

    def __init__(self) -> None:
        super().__init__(0, 4)
        self.setHorizontalHeaderLabels(("ID", "Schüler", "Stammgruppe", "Kurs"))
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)

    def set_students(self, students: tuple[StudentListItem, ...]) -> None:
        """Replace the visible student rows."""
        self.setRowCount(len(students))
        for row_index, student in enumerate(students):
            values = (
                student.student_id,
                student.display_name,
                student.group_name,
                student.course_name,
            )
            for column_index, value in enumerate(values):
                self.setItem(row_index, column_index, QTableWidgetItem(value))
