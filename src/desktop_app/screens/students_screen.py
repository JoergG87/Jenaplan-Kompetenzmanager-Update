"""Students screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.view_models.student_view_model import StudentListItem


class StudentsScreen(QWidget):
    """Student list and new-student action."""

    new_student_requested = Signal()
    student_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.students: tuple[StudentListItem, ...] = ()
        self.group_filter_label = QLabel("")
        self.table = QTableWidget(0, 4)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Schüler")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        new_student_button = QPushButton("+ Schüler")
        new_student_button.clicked.connect(self.new_student_requested.emit)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(new_student_button)
        layout.addLayout(header)
        self.group_filter_label.setStyleSheet("color: #555;")
        layout.addWidget(self.group_filter_label)

        self.table.setHorizontalHeaderLabels(("ID", "Name", "Stammgruppe", "Kurs"))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(self._open_student)
        self.table.itemSelectionChanged.connect(self._select_student)
        layout.addWidget(self.table)

    def set_students(
        self,
        students: tuple[StudentListItem, ...],
        *,
        group_filter_name: str = "",
    ) -> None:
        """Replace student rows."""
        self.students = students
        self.group_filter_label.setText(
            f"Gefiltert nach Stammgruppe: {group_filter_name}"
            if group_filter_name
            else "Alle Schüler"
        )
        self.table.setRowCount(len(students))
        for row_index, student in enumerate(students):
            values = (
                student.student_id,
                student.display_name,
                student.group_name,
                student.course_name,
            )
            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _select_student(self) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        row_index = selected_items[0].row()
        if row_index < len(self.students):
            self.student_selected.emit(self.students[row_index].student_id)

    def _open_student(self, row: int, _column: int) -> None:
        if row < len(self.students):
            self.student_selected.emit(self.students[row].student_id)
