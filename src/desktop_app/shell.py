"""Application shell for the PySide6 desktop app."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.sqlite_store import SQLITE_SPIKE_PATH
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.dialogs.new_student_dialog import NewStudentDialog
from src.desktop_app.navigation import NAVIGATION_ITEMS, resolve_navigation_target
from src.desktop_app.screens.overview_screen import OverviewScreen
from src.desktop_app.screens.placeholder_screen import PlaceholderScreen
from src.desktop_app.screens.student_profile_screen import StudentProfileScreen
from src.desktop_app.screens.students_screen import StudentsScreen


class AppShell(QMainWindow):
    """Main window with navigation and MVP screens."""

    def __init__(self, database_path: Path = SQLITE_SPIKE_PATH) -> None:
        super().__init__()
        self.adapter = StudentDesktopAdapter(database_path)
        self.selected_group_id: str | None = None
        self.setWindowTitle("Jenaplan Kompetenzmanager")
        self.setMinimumSize(1100, 720)
        self.resize(1400, 900)
        self._build()
        self.refresh_all()

    def _build(self) -> None:
        root = QWidget()
        layout = QHBoxLayout(root)

        self.navigation = QListWidget()
        self.navigation.setFixedWidth(180)
        for item in NAVIGATION_ITEMS:
            nav_item = QListWidgetItem(item.label)
            nav_item.setData(Qt.ItemDataRole.UserRole, item.key)
            self.navigation.addItem(nav_item)
        self.navigation.currentRowChanged.connect(self._show_navigation_index)
        self.navigation.itemClicked.connect(self._show_navigation_item)
        layout.addWidget(self.navigation)

        content = QVBoxLayout()
        title = QLabel("Jenaplan Kompetenzmanager")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        content.addWidget(title)

        self.stack = QStackedWidget()
        self.overview_screen = OverviewScreen()
        self.students_screen = StudentsScreen()
        self.student_profile_screen = StudentProfileScreen()
        self.placeholder_screens = {
            "observations": PlaceholderScreen(
                "Beobachtungen",
                "Beobachtungsmaske folgt in einem späteren Sprint.",
            ),
            "competencies": PlaceholderScreen(
                "Kompetenzen",
                "Kompetenzübersicht folgt in einem späteren Sprint.",
            ),
            "reports": PlaceholderScreen(
                "Berichte",
                "Excel-Export und Berichte folgen separat.",
            ),
            "settings": PlaceholderScreen(
                "Einstellungen",
                "Datenbankpfad, Backup und Restore sind noch offen.",
            ),
        }

        self.screen_index = {
            "overview": self.stack.addWidget(self.overview_screen),
            "students": self.stack.addWidget(self.students_screen),
            "profile": self.stack.addWidget(self.student_profile_screen),
        }
        for key, screen in self.placeholder_screens.items():
            self.screen_index[key] = self.stack.addWidget(screen)

        content.addWidget(self.stack)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #555;")
        content.addWidget(self.status_label)
        layout.addLayout(content)

        self.setCentralWidget(root)

        self.overview_screen.group_selected.connect(self.show_students_for_group)
        self.students_screen.new_student_requested.connect(self.open_new_student_dialog)
        self.students_screen.student_selected.connect(self.show_student_profile)
        self.student_profile_screen.back_requested.connect(self.return_to_students)
        self.navigation.setCurrentRow(0)

    def refresh_all(self) -> None:
        """Refresh overview and student list from SQLite."""
        self.overview_screen.set_groups(self.adapter.list_group_summaries())
        self.refresh_students()

    def refresh_students(self) -> None:
        """Refresh student rows for the current filter."""
        group_name = ""
        if self.selected_group_id:
            groups = {group.group_id: group.group_name for group in self.adapter.list_groups()}
            group_name = groups.get(self.selected_group_id, self.selected_group_id)
        students = self.adapter.list_students(group_id=self.selected_group_id)
        self.students_screen.set_students(students, group_filter_name=group_name)
        shown_count = len(self.students_screen.filtered_students)
        if self.students_screen.search_text().strip():
            self.status_label.setText(f"{shown_count} von {len(students)} Schülern angezeigt")
        else:
            self.status_label.setText(f"{len(students)} Schüler angezeigt")

    def return_to_students(self) -> None:
        """Return from profile to student list and keep current filter."""
        self.refresh_students()
        self._show_screen("students")
        self._select_navigation("students")

    def show_students_for_group(self, group_id: str) -> None:
        """Open students screen filtered to one group."""
        self.selected_group_id = group_id
        self.refresh_students()
        self._show_screen("students")
        self._select_navigation("students")

    def show_student_profile(self, student_id: str) -> None:
        """Open light profile for selected student."""
        self.student_profile_screen.set_student(self.adapter.get_student_profile(student_id))
        self._show_screen("profile")

    def open_new_student_dialog(self) -> None:
        """Open the existing new-student dialog and refresh after success."""
        dialog = NewStudentDialog(self.adapter)
        dialog.student_created.connect(self.handle_student_created)
        dialog.exec()

    def handle_student_created(self, student_id: str) -> None:
        """Refresh views and show non-modal success feedback."""
        self.refresh_all()
        self._show_screen("students")
        self._select_navigation("students")
        self.status_label.setText("Schüler wurde gespeichert.")

    def _show_navigation_index(self, index: int) -> None:
        if index < 0:
            return
        self._show_navigation_item(self.navigation.item(index))

    def _show_navigation_item(self, item: QListWidgetItem) -> None:
        key = str(item.data(Qt.ItemDataRole.UserRole))
        target = resolve_navigation_target(key)
        if target.reset_group_filter:
            self.selected_group_id = None
            self.refresh_students()
        self._show_screen(target.screen_key)

    def _show_screen(self, key: str) -> None:
        screen_index = self.screen_index.get(key)
        if screen_index is not None:
            self.stack.setCurrentIndex(screen_index)

    def _select_navigation(self, key: str) -> None:
        for row_index in range(self.navigation.count()):
            if self.navigation.item(row_index).data(Qt.ItemDataRole.UserRole) == key:
                self.navigation.blockSignals(True)
                self.navigation.setCurrentRow(row_index)
                self.navigation.blockSignals(False)
                return
