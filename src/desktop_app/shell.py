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
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.sqlite_store import SQLITE_SPIKE_PATH
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from src.desktop_app.adapters.master_data_desktop_adapter import MasterDataDesktopAdapter
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.dialogs.app_info_dialog import AppInfoDialog
from src.desktop_app.dialogs.master_data_dialog import (
    CourseGroupDialog,
    MasterDataNameDialog,
)
from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog
from src.desktop_app.dialogs.new_student_dialog import NewStudentDialog
from src.desktop_app.navigation import NAVIGATION_ITEMS, resolve_navigation_target
from src.desktop_app.screens.master_data_screen import MasterDataScreen
from src.desktop_app.screens.overview_screen import OverviewScreen
from src.desktop_app.screens.placeholder_screen import PlaceholderScreen
from src.desktop_app.screens.student_profile_screen import StudentProfileScreen
from src.desktop_app.screens.students_screen import StudentsScreen
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel
from src.desktop_app.view_models.master_data_view_model import CourseGroupViewModel


class AppShell(QMainWindow):
    """Main window with navigation and MVP screens."""

    def __init__(self, database_path: Path = SQLITE_SPIKE_PATH) -> None:
        super().__init__()
        self.adapter = StudentDesktopAdapter(database_path)
        self.master_data_adapter = MasterDataDesktopAdapter(self.adapter)
        self.curriculum_adapter = CurriculumDesktopAdapter()
        self.selected_group_id: str | None = None
        self.selected_course_group_id: str | None = None
        self.selected_course_id: str | None = None
        self.setWindowTitle("Jenaplan Kompetenzmanager")
        self.setMinimumSize(1100, 720)
        self.resize(1400, 900)
        self._build()
        self.refresh_all()

    def _build(self) -> None:
        root = QWidget()
        layout = QHBoxLayout(root)

        sidebar = QVBoxLayout()
        self.navigation = QListWidget()
        self.navigation.setFixedWidth(180)
        for item in NAVIGATION_ITEMS:
            nav_item = QListWidgetItem(item.label)
            nav_item.setData(Qt.ItemDataRole.UserRole, item.key)
            self.navigation.addItem(nav_item)
        self.navigation.currentRowChanged.connect(self._show_navigation_index)
        self.navigation.itemClicked.connect(self._show_navigation_item)
        sidebar.addWidget(self.navigation, 1)
        self.info_button = QPushButton("Info")
        self.info_button.clicked.connect(self.open_app_info_dialog)
        sidebar.addWidget(self.info_button)
        layout.addLayout(sidebar)

        content = QVBoxLayout()
        title = QLabel("Jenaplan Kompetenzmanager")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        content.addWidget(title)

        self.stack = QStackedWidget()
        self.overview_screen = OverviewScreen()
        self.students_screen = StudentsScreen()
        self.student_profile_screen = StudentProfileScreen()
        self.master_data_screen = MasterDataScreen()
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
            "master_data": self.stack.addWidget(self.master_data_screen),
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
        self.overview_screen.course_selected.connect(self.show_students_for_course_group)
        self.students_screen.new_student_requested.connect(self.open_new_student_dialog)
        self.students_screen.student_selected.connect(self.show_student_profile)
        self.student_profile_screen.back_requested.connect(self.return_to_students)
        self.student_profile_screen.observation_requested.connect(
            self.open_new_observation_dialog
        )
        self.master_data_screen.group_add_requested.connect(self.open_new_group_dialog)
        self.master_data_screen.group_rename_requested.connect(
            self.open_rename_group_dialog
        )
        self.master_data_screen.course_add_requested.connect(self.open_new_course_dialog)
        self.master_data_screen.course_rename_requested.connect(
            self.open_rename_course_dialog
        )
        self.master_data_screen.course_group_edit_requested.connect(
            self.open_edit_course_group_dialog
        )
        self.navigation.setCurrentRow(0)

    def refresh_all(self) -> None:
        """Refresh overview and student list from SQLite."""
        self.refresh_overview()
        self.refresh_students()
        self.refresh_master_data()

    def refresh_overview(self) -> None:
        """Refresh the overview from the current master-data scope."""
        self.overview_screen.set_master_data(
            self.master_data_adapter.view_model(),
            self.adapter.list_group_summaries(),
        )

    def refresh_students(self) -> None:
        """Refresh student rows for the current filter."""
        filter_label = "Alle Schüler"
        group_ids: tuple[str, ...] = ()
        if self.selected_group_id:
            groups = {group.group_id: group.group_name for group in self.adapter.list_groups()}
            filter_label = f"Stammgruppe: {groups.get(self.selected_group_id, self.selected_group_id)}"
        elif self.selected_course_group_id and self.selected_course_id:
            course_group = self._selected_course_group()
            course_name = self._course_name(self.selected_course_id)
            if course_group is not None:
                group_ids = course_group.selected_group_ids
                filter_label = f"{course_group.name} · {course_name}"
            else:
                filter_label = f"Kurs: {course_name}"
        students = self.adapter.list_students(
            group_id=self.selected_group_id,
            group_ids=group_ids,
            course_id=self.selected_course_id,
        )
        self.students_screen.set_students(students, group_filter_name=filter_label)
        shown_count = len(self.students_screen.filtered_students)
        if self.students_screen.search_text().strip():
            self.status_label.setText(f"{shown_count} von {len(students)} Schülern angezeigt")
        else:
            self.status_label.setText(f"{len(students)} Schüler angezeigt")

    def refresh_master_data(self) -> None:
        """Refresh the master-data light screen from the adapter draft."""
        self.master_data_screen.set_master_data(self.master_data_adapter.view_model())
        self.refresh_overview()

    def return_to_students(self) -> None:
        """Return from profile to student list and keep current filter."""
        self.refresh_students()
        self._show_screen("students")
        self._select_navigation("students")

    def show_students_for_group(self, group_id: str) -> None:
        """Open students screen filtered to one group."""
        self.selected_group_id = group_id
        self.selected_course_group_id = None
        self.selected_course_id = None
        self.refresh_students()
        self._show_screen("students")
        self._select_navigation("students")

    def show_students_for_course_group(self, course_group_id: str, course_id: str) -> None:
        """Open students screen filtered to one course inside one course group."""
        self.selected_group_id = None
        self.selected_course_group_id = course_group_id
        self.selected_course_id = course_id
        self.refresh_students()
        self._show_screen("students")
        self._select_navigation("students")

    def show_student_profile(self, student_id: str) -> None:
        """Open light profile for selected student."""
        self.student_profile_screen.set_student(self.adapter.get_student_profile(student_id))
        self._show_screen("profile")

    def open_new_student_dialog(self) -> None:
        """Open the existing new-student dialog and refresh after success."""
        dialog = NewStudentDialog(self.adapter, self.master_data_adapter)
        dialog.student_created.connect(self.handle_student_created)
        dialog.exec()

    def open_new_observation_dialog(self, student: StudentDetailViewModel) -> None:
        """Open the non-persistent observation UX prototype."""
        dialog = NewObservationDialog(student, self.curriculum_adapter)
        dialog.exec()

    def open_app_info_dialog(self) -> None:
        """Open the compact app information dialog."""
        dialog = AppInfoDialog()
        dialog.exec()

    def open_new_group_dialog(self) -> None:
        """Open the non-persistent new-group dialog."""
        dialog = MasterDataNameDialog("Neue Stammgruppe")
        if dialog.exec():
            self.master_data_adapter.add_group(dialog.name())
            self.refresh_master_data()
            self.status_label.setText(
                "Stammgruppe wurde vorgemerkt. Dauerhaftes Speichern folgt später."
            )

    def open_new_course_dialog(self) -> None:
        """Open the non-persistent new-course dialog."""
        dialog = MasterDataNameDialog("Neuer Kurs", include_color=True)
        if dialog.exec():
            self.master_data_adapter.add_course(dialog.name(), dialog.color_hex())
            self.refresh_master_data()
            self.status_label.setText(
                "Kurs wurde vorgemerkt. Dauerhaftes Speichern folgt später."
            )

    def open_rename_group_dialog(self, group_id: str) -> None:
        """Open the non-persistent rename dialog for a group."""
        item = self.master_data_adapter.groups[group_id]
        dialog = MasterDataNameDialog("Stammgruppe umbenennen", item.name)
        if dialog.exec():
            self.master_data_adapter.rename_group(group_id, dialog.name())
            self.refresh_master_data()
            self.status_label.setText(
                "Stammgruppe wurde umbenannt. Dauerhaftes Speichern folgt später."
            )

    def open_rename_course_dialog(self, course_id: str) -> None:
        """Open the non-persistent rename dialog for a course."""
        item = self.master_data_adapter.courses[course_id]
        dialog = MasterDataNameDialog(
            "Kurs umbenennen",
            item.name,
            include_color=True,
            initial_color_hex=item.color_hex,
        )
        if dialog.exec():
            self.master_data_adapter.rename_course(
                course_id,
                dialog.name(),
                dialog.color_hex(),
            )
            self.refresh_master_data()
            self.status_label.setText(
                "Kurs wurde umbenannt. Dauerhaftes Speichern folgt später."
            )

    def open_edit_course_group_dialog(self, course_group_id: str) -> None:
        """Open the non-persistent edit dialog for one course group."""
        view_model = self.master_data_adapter.view_model()
        course_group = self.master_data_adapter.course_groups[course_group_id]
        dialog = CourseGroupDialog(course_group, view_model.groups, view_model.courses)
        if dialog.exec():
            updated_course_group = self.master_data_adapter.update_course_group(
                course_group_id,
                dialog.name(),
                dialog.selected_group_ids(),
                dialog.selected_course_ids(),
            )
            self._clear_invalid_course_group_filter(updated_course_group)
            self.refresh_master_data()
            self.refresh_students()
            self.status_label.setText(
                "Kursverbund wurde aktualisiert. Dauerhaftes Speichern folgt später."
            )

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
            self.selected_course_group_id = None
            self.selected_course_id = None
            self.refresh_students()
        self._show_screen(target.screen_key)

    def _selected_course_group(self) -> CourseGroupViewModel | None:
        for course_group in self.master_data_adapter.view_model().course_groups:
            if course_group.course_group_id == self.selected_course_group_id:
                return course_group
        return None

    def _course_name(self, course_id: str) -> str:
        for course in self.master_data_adapter.view_model().courses:
            if course.item_id == course_id:
                return course.name
        return course_id

    def _clear_invalid_course_group_filter(
        self,
        course_group: CourseGroupViewModel,
    ) -> None:
        if self.selected_course_group_id != course_group.course_group_id:
            return
        if self.selected_course_id in course_group.selected_course_ids:
            return
        self.selected_course_group_id = None
        self.selected_course_id = None

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
