"""Students screen for the PySide6 desktop app."""

from __future__ import annotations

from time import monotonic

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QFrame,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.components import (
    EmptyState,
    InlineMessage,
    PageHeader,
    SearchField,
    configure_button,
)
from src.desktop_app.view_models.student_view_model import (
    StudentListItem,
    filter_student_list,
)
from src.desktop_app.theme import set_label_style


STUDENT_SEARCH_PLACEHOLDER = "Schüler suchen …"
STUDENT_LIST_EMPTY_STATE = (
    "Noch keine Schüler vorhanden.\nLege über „Schüler anlegen“ den ersten Schüler an."
)
STUDENT_SEARCH_EMPTY_STATE = "Keine Schüler gefunden."


class StudentsScreen(QWidget):
    """Student list and new-student action."""

    new_student_requested = Signal()
    student_selected = Signal(str)
    observation_requested = Signal(str)
    back_to_overview_requested = Signal()

    def __init__(self, *, show_header: bool = True) -> None:
        super().__init__()
        self.students: tuple[StudentListItem, ...] = ()
        self.filtered_students: tuple[StudentListItem, ...] = ()
        self.filter_message = InlineMessage()
        self.group_filter_label = self.filter_message.label
        self.empty_state = EmptyState()
        self.empty_state_label = self.empty_state.label
        self.search_input = SearchField(STUDENT_SEARCH_PLACEHOLDER)
        self.back_to_overview_button = QPushButton("Zurück zur Auswahl")
        self.table = QTableWidget(0, 4)
        self._show_header = show_header
        self._last_pointer_activation: tuple[str, float] | None = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.back_to_overview_button.clicked.connect(
            self.back_to_overview_requested.emit
        )
        configure_button(
            self.back_to_overview_button,
            "quiet",
            "Zurück zu Stammgruppen oder Kursverbünden",
        )
        self.back_to_overview_button.setVisible(False)
        if self._show_header:
            page_header = PageHeader("Schüler", "Alle Schüler durchsuchen und öffnen")
            new_student_button = QPushButton("Schüler anlegen")
            configure_button(new_student_button, "primary", "Neuen Schüler anlegen")
            new_student_button.clicked.connect(self.new_student_requested.emit)
            page_header.add_action(new_student_button)
            layout.addWidget(page_header)
        header.addWidget(self.back_to_overview_button)
        header.addStretch()
        layout.addLayout(header)

        search_row = QHBoxLayout()
        self.search_input.textChanged.connect(self.apply_search)
        search_row.addWidget(self.search_input)
        search_row.addStretch(1)
        layout.addLayout(search_row)

        layout.addWidget(self.filter_message)
        layout.addWidget(self.empty_state)

        self.table.setHorizontalHeaderLabels(
            ("Name", "Kurs", "Dokumentation", "Aktion")
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setAccessibleName("Schülerliste")
        self.table.setAccessibleDescription(
            "Zeile anklicken oder mit Eingabe das Profil öffnen."
        )
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
        self.table.horizontalHeader().setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.table.cellClicked.connect(self._activate_student_cell)
        self.table.cellDoubleClicked.connect(self._activate_student_cell)
        self.table.installEventFilter(self)
        layout.addWidget(self.table)

    def set_students(
        self,
        students: tuple[StudentListItem, ...],
        *,
        group_filter_name: str = "",
        show_back_button: bool = False,
    ) -> None:
        """Replace student rows."""
        self.students = students
        self.filter_message.set_message(group_filter_name or "Alle Schüler")
        self.back_to_overview_button.setVisible(show_back_button)
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
            self.table.setCellWidget(row_index, 3, self._observation_action_cell(student))

    def _course_cell(self, student: StudentListItem) -> QWidget:
        cell = QWidget()
        cell.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)

        marker = QFrame()
        marker.setObjectName("CourseColorMarker")
        marker.setFixedSize(10, 10)
        palette = marker.palette()
        palette.setColor(
            QPalette.ColorRole.Window,
            QColor(student.course_color_hex or "#6B7280"),
        )
        marker.setPalette(palette)
        marker.setAutoFillBackground(True)

        course_label = QLabel(student.course_name)
        set_label_style(course_label, "body")

        layout.addWidget(marker)
        layout.addWidget(course_label)
        layout.addStretch(1)
        return cell

    def _observation_action_cell(self, student: StudentListItem) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        observe_button = QPushButton("Beobachten")
        configure_button(
            observe_button,
            "quiet",
            f"Neue Beobachtung für {student.display_name}",
        )
        observe_button.setToolTip(f"Neue Beobachtung für {student.display_name}")
        observe_button.clicked.connect(
            lambda _checked=False, student_id=student.student_id: self.observation_requested.emit(
                student_id
            )
        )
        profile_button = QPushButton("Profil öffnen")
        configure_button(
            profile_button,
            "secondary",
            f"Profil von {student.display_name} öffnen",
        )
        profile_button.clicked.connect(
            lambda _checked=False, student_id=student.student_id: self.student_selected.emit(
                student_id
            )
        )
        layout.addWidget(observe_button)
        layout.addWidget(profile_button)
        return cell

    def _update_empty_state(self, students: tuple[StudentListItem, ...]) -> None:
        if students:
            self.empty_state.set_message("")
            return
        if self.search_input.text().strip():
            self.empty_state.set_message(STUDENT_SEARCH_EMPTY_STATE)
            return
        self.empty_state.set_message(STUDENT_LIST_EMPTY_STATE)

    def eventFilter(self, watched: object, event: QEvent) -> bool:  # noqa: N802
        if (
            watched is self.table
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        ):
            self._activate_student_row(self.table.currentRow())
            return True
        return super().eventFilter(watched, event)

    def _activate_student_cell(self, row: int, column: int) -> None:
        if column == 3 or row >= len(self.filtered_students):
            return
        student_id = self.filtered_students[row].student_id
        now = monotonic()
        if self._last_pointer_activation is not None:
            previous_student_id, previous_at = self._last_pointer_activation
            application = QApplication.instance()
            double_click_interval = (
                application.doubleClickInterval() / 1000
                if application is not None
                else 0.4
            )
            if (
                previous_student_id == student_id
                and now - previous_at
                <= double_click_interval
            ):
                return
        self._last_pointer_activation = (student_id, now)
        self.student_selected.emit(student_id)

    def _activate_student_row(self, row: int) -> None:
        if 0 <= row < len(self.filtered_students):
            self.student_selected.emit(self.filtered_students[row].student_id)
