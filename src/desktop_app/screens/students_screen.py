"""Students screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.view_models.student_view_model import (
    StudentListItem,
    filter_student_list,
)
from src.desktop_app.theme import set_label_style


STUDENT_SEARCH_PLACEHOLDER = "Schüler suchen …"
STUDENT_LIST_EMPTY_STATE = (
    "Noch keine Schüler vorhanden.\nLege über „+ Schüler“ den ersten Schüler an."
)
STUDENT_SEARCH_EMPTY_STATE = "Keine Schüler gefunden."


class StudentsScreen(QWidget):
    """Student list and new-student action."""

    new_student_requested = Signal()
    student_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.students: tuple[StudentListItem, ...] = ()
        self.filtered_students: tuple[StudentListItem, ...] = ()
        self.group_filter_label = QLabel("")
        self.empty_state_label = QLabel("")
        self.search_input = QLineEdit()
        self.table = QTableWidget(0, 3)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Schüler")
        set_label_style(title, "screen_title")
        new_student_button = QPushButton("+ Schüler")
        new_student_button.clicked.connect(self.new_student_requested.emit)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(new_student_button)
        layout.addLayout(header)

        search_row = QHBoxLayout()
        self.search_input.setPlaceholderText(STUDENT_SEARCH_PLACEHOLDER)
        self.search_input.textChanged.connect(self.apply_search)
        clear_search_button = QPushButton("Zurücksetzen")
        clear_search_button.clicked.connect(self.search_input.clear)
        search_row.addWidget(self.search_input)
        search_row.addWidget(clear_search_button)
        layout.addLayout(search_row)

        set_label_style(self.group_filter_label, "muted")
        layout.addWidget(self.group_filter_label)
        set_label_style(self.empty_state_label, "subtle")
        self.empty_state_label.setWordWrap(True)
        layout.addWidget(self.empty_state_label)

        self.table.setHorizontalHeaderLabels(("Name", "Kurs", "Dokumentation"))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
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
        self.apply_search()

    def search_text(self) -> str:
        """Return current search text."""
        return self.search_input.text()

    def apply_search(self) -> None:
        """Apply search text to the already loaded student rows."""
        self.filtered_students = filter_student_list(
            self.students,
            self.search_input.text(),
        )
        self._render_students(self.filtered_students)

    def _render_students(self, students: tuple[StudentListItem, ...]) -> None:
        self.table.setRowCount(len(students))
        self._update_empty_state(students)
        for row_index, student in enumerate(students):
            self.table.setItem(row_index, 0, QTableWidgetItem(student.display_name))
            self.table.setCellWidget(row_index, 1, self._course_cell(student))
            self.table.setItem(
                row_index,
                2,
                QTableWidgetItem(student.documentation_status.list_label),
            )

    def _course_cell(self, student: StudentListItem) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)

        marker = QLabel("●")
        marker.setFixedWidth(14)
        marker.setStyleSheet(f"color: {student.course_color_hex or '#6B7280'};")

        course_label = QLabel(student.course_name)
        set_label_style(course_label, "body")

        layout.addWidget(marker)
        layout.addWidget(course_label)
        layout.addStretch(1)
        return cell

    def _update_empty_state(self, students: tuple[StudentListItem, ...]) -> None:
        if students:
            self.empty_state_label.setText("")
            return
        if self.search_input.text().strip():
            self.empty_state_label.setText(STUDENT_SEARCH_EMPTY_STATE)
            return
        self.empty_state_label.setText(STUDENT_LIST_EMPTY_STATE)

    def _select_student(self) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        row_index = selected_items[0].row()
        if row_index < len(self.filtered_students):
            self.student_selected.emit(self.filtered_students[row_index].student_id)

    def _open_student(self, row: int, _column: int) -> None:
        if row < len(self.filtered_students):
            self.student_selected.emit(self.filtered_students[row].student_id)
