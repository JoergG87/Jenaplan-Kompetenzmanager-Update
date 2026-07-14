"""Local information architecture for all student-related entry points."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QStackedWidget, QVBoxLayout, QWidget

from src.desktop_app.components import PageHeader, SegmentedControl, configure_button
from src.desktop_app.screens.overview_screen import GroupOverviewScreen
from src.desktop_app.screens.students_screen import StudentsScreen
from src.desktop_app.view_models.master_data_view_model import MasterDataViewModel
from src.desktop_app.view_models.student_view_model import GroupSummaryViewModel


STUDENT_WORKSPACE_SEGMENTS = (
    ("groups", "Stammgruppen"),
    ("courses", "Kurse"),
    ("course_groups", "Kursverbünde"),
    ("all", "Alle Schüler"),
)


class StudentsWorkspace(QWidget):
    """Compose existing projections behind one local student navigation."""

    new_student_requested = Signal()
    all_students_requested = Signal()
    course_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("StudentsWorkspace")
        self._list_source_key = "all"
        self.groups_screen = GroupOverviewScreen(section="groups", show_header=False)
        self.courses_screen = GroupOverviewScreen(section="courses", show_header=False)
        self.course_groups_screen = GroupOverviewScreen(
            section="course_groups",
            show_header=False,
        )
        self.students_screen = StudentsScreen(show_header=False)
        self.courses_screen.direct_course_selected.connect(self.course_selected.emit)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = PageHeader(
            "Schüler",
            "Stammgruppen, Kurse, Kursverbünde und alle Schüler an einem Ort",
        )
        new_student_button = QPushButton("Schüler anlegen")
        configure_button(new_student_button, "primary", "Neuen Schüler anlegen")
        new_student_button.clicked.connect(self.new_student_requested.emit)
        header.add_action(new_student_button)
        layout.addWidget(header)

        self.segmented_control = SegmentedControl(STUDENT_WORKSPACE_SEGMENTS)
        self.segmented_control.setAccessibleName("Schülerbereich auswählen")
        self.segmented_control.selection_changed.connect(self.show_section)
        layout.addWidget(self.segmented_control)

        self.stack = QStackedWidget()
        self._screen_index = {
            "groups": self.stack.addWidget(self.groups_screen),
            "courses": self.stack.addWidget(self.courses_screen),
            "course_groups": self.stack.addWidget(self.course_groups_screen),
            "all": self.stack.addWidget(self.students_screen),
        }
        layout.addWidget(self.stack, 1)

    def set_master_data(
        self,
        view_model: MasterDataViewModel,
        group_summaries: tuple[GroupSummaryViewModel, ...],
    ) -> None:
        """Refresh both local selection projections from existing view models."""
        self.groups_screen.set_master_data(view_model, group_summaries)
        self.courses_screen.set_master_data(view_model, group_summaries)
        self.course_groups_screen.set_master_data(view_model, group_summaries)

    def show_section(self, key: str) -> None:
        """Show one local top-level section."""
        if key not in self._screen_index:
            raise ValueError(f"Unbekannter Schülerbereich: {key}")
        self.segmented_control.set_current_key(key)
        self.stack.setCurrentIndex(self._screen_index[key])
        self._list_source_key = key
        if key == "all":
            self.all_students_requested.emit()

    def show_student_list(self, *, source_key: str) -> None:
        """Drill into the list while retaining its local navigation origin."""
        if source_key not in {"groups", "courses", "course_groups", "all"}:
            raise ValueError(f"Unbekannter Listenursprung: {source_key}")
        self._list_source_key = source_key
        self.segmented_control.set_current_key(source_key)
        self.stack.setCurrentWidget(self.students_screen)

    def show_source_selection(self) -> str:
        """Return from a filtered list to its local group selection."""
        source_key = self._list_source_key
        if source_key == "all":
            self.stack.setCurrentWidget(self.students_screen)
        else:
            self.stack.setCurrentIndex(self._screen_index[source_key])
        self.segmented_control.set_current_key(source_key)
        return source_key

    def list_source_key(self) -> str:
        """Return the local section from which the current list was opened."""
        return self._list_source_key

    def current_content_key(self) -> str:
        """Expose the visible projection for tests and shell coordination."""
        if self.stack.currentWidget() is self.students_screen:
            return "all" if self._list_source_key == "all" else "filtered_students"
        for key, index in self._screen_index.items():
            if self.stack.currentIndex() == index:
                return key
        return ""
