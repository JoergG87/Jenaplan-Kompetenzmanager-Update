"""Application shell for the PySide6 desktop app."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.sqlite_store import SQLITE_SPIKE_PATH
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from src.desktop_app.adapters.master_data_desktop_adapter import MasterDataDesktopAdapter
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.assets import create_app_icon_label
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
from src.desktop_app.theme import set_label_style
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel
from src.desktop_app.view_models.master_data_view_model import CourseGroupViewModel


class AppShell(QMainWindow):
    """Main window with navigation and MVP screens."""

    def __init__(self, database_path: Path = SQLITE_SPIKE_PATH) -> None:
        super().__init__()
        self.adapter = StudentDesktopAdapter(database_path)
        self.master_data_adapter = MasterDataDesktopAdapter(self.adapter)
        self.curriculum_adapter = CurriculumDesktopAdapter(database=self.adapter.database)
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
        root.setObjectName("AppRoot")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 18, 16)
        layout.setSpacing(18)

        sidebar_container = QWidget()
        sidebar_container.setObjectName("AppSidebar")
        sidebar_container.setFixedWidth(196)
        sidebar = QVBoxLayout(sidebar_container)
        sidebar.setContentsMargins(12, 16, 12, 12)
        sidebar.setSpacing(8)
        brand_icon = create_app_icon_label(58)
        sidebar.addWidget(brand_icon, 0, Qt.AlignmentFlag.AlignHCenter)
        brand_title = QLabel("Jenaplan")
        brand_title.setObjectName("SidebarBrandTitle")
        brand_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        brand_subtitle = QLabel("Kompetenzmanager")
        brand_subtitle.setObjectName("SidebarBrandSubtitle")
        brand_subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        sidebar.addWidget(brand_title)
        sidebar.addWidget(brand_subtitle)
        self.navigation = QListWidget()
        self.navigation.setObjectName("AppNavigation")
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
        layout.addWidget(sidebar_container)

        content = QVBoxLayout()
        title = QLabel("Jenaplan Kompetenzmanager")
        set_label_style(title, "app_title")
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
                "Text- und Datei-Exporte folgen separat.",
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
        set_label_style(self.status_label, "muted")
        content.addWidget(self.status_label)
        layout.addLayout(content)

        self.setCentralWidget(root)

        self.overview_screen.group_selected.connect(self.show_students_for_group)
        self.overview_screen.course_selected.connect(self.show_students_for_course_group)
        self.students_screen.new_student_requested.connect(self.open_new_student_dialog)
        self.students_screen.student_selected.connect(self.show_student_profile)
        self.students_screen.observation_requested.connect(
            self.open_quick_observation_dialog
        )
        self.students_screen.back_to_overview_requested.connect(self.return_to_overview)
        self.student_profile_screen.back_requested.connect(self.return_to_students)
        self.student_profile_screen.observation_requested.connect(
            self.open_new_observation_dialog
        )
        self.student_profile_screen.observation_edit_requested.connect(
            self.open_edit_observation_dialog
        )
        self.student_profile_screen.observation_delete_requested.connect(
            self.delete_observation
        )
        self.student_profile_screen.document_add_requested.connect(
            self.open_student_document_dialog
        )
        self.student_profile_screen.competency_confirmation_requested.connect(
            self.confirm_competency_status
        )
        self.master_data_screen.group_add_requested.connect(self.open_new_group_dialog)
        self.master_data_screen.group_rename_requested.connect(
            self.open_rename_group_dialog
        )
        self.master_data_screen.course_add_requested.connect(self.open_new_course_dialog)
        self.master_data_screen.course_rename_requested.connect(
            self.open_rename_course_dialog
        )
        self.master_data_screen.course_group_add_requested.connect(
            self.open_new_course_group_dialog
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
        self.students_screen.set_students(
            students,
            group_filter_name=filter_label,
            show_back_button=self._has_active_student_filter(),
        )
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

    def return_to_overview(self) -> None:
        """Return from a filtered student detail list to the overview."""
        self.selected_group_id = None
        self.selected_course_group_id = None
        self.selected_course_id = None
        self.refresh_all()
        self._show_screen("overview")
        self._select_navigation("overview")

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
        profile = self.adapter.get_student_profile(student_id)
        observations = self.adapter.list_observations_for_student(student_id)
        competency_groups = self.adapter.list_competency_overview_for_student(student_id)
        report_preview = self.adapter.get_report_preview_for_student(student_id)
        documentation_statuses = self.adapter.list_documentation_status_for_student(student_id)
        documents = self.adapter.list_documents_for_student(student_id)
        self.student_profile_screen.set_student(
            profile,
            observations,
            competency_groups,
            report_preview,
            documentation_statuses,
            documents,
        )
        self._show_screen("profile")

    def open_new_student_dialog(self) -> None:
        """Open the existing new-student dialog and refresh after success."""
        dialog = NewStudentDialog(self.adapter, self.master_data_adapter)
        dialog.student_created.connect(self.handle_student_created)
        dialog.exec()

    def open_new_observation_dialog(self, student: StudentDetailViewModel) -> None:
        """Open the persistent observation dialog and refresh after success."""
        dialog = NewObservationDialog(student, self.curriculum_adapter, self.adapter)
        if dialog.exec():
            self.show_student_profile(student.student_id)
            self.status_label.setText("Beobachtung wurde gespeichert.")

    def open_quick_observation_dialog(self, student_id: str) -> None:
        """Open the observation dialog from a student list row."""
        student = self.adapter.get_student_profile(student_id)
        if student is None:
            self.status_label.setText("Schülerprofil wurde nicht gefunden.")
            return
        dialog = NewObservationDialog(student, self.curriculum_adapter, self.adapter)
        if dialog.exec():
            self.refresh_overview()
            self.refresh_students()
            self.status_label.setText("Beobachtung wurde gespeichert.")

    def open_edit_observation_dialog(self, observation_id: str) -> None:
        """Open the observation dialog with persisted observation data."""
        draft = self.adapter.observation_draft_for_edit(observation_id)
        if draft is None:
            self.status_label.setText("Beobachtung wurde nicht gefunden.")
            return
        student = self.adapter.get_student_profile(draft.student_id)
        if student is None:
            self.status_label.setText("Schülerprofil wurde nicht gefunden.")
            return
        dialog = NewObservationDialog(
            student,
            self.curriculum_adapter,
            self.adapter,
            initial_draft=draft,
        )
        if dialog.exec():
            self.show_student_profile(student.student_id)
            self.status_label.setText("Beobachtung wurde aktualisiert.")

    def delete_observation(self, observation_id: str) -> None:
        """Soft-delete an observation and refresh the current profile."""
        draft = self.adapter.observation_draft_for_edit(observation_id)
        if draft is None:
            self.status_label.setText("Beobachtung wurde nicht gefunden.")
            return
        response = QMessageBox.question(
            self,
            "Beobachtung löschen",
            "Diese Beobachtung aus dem Profil ausblenden?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        result = self.adapter.delete_observation(observation_id)
        if not getattr(result, "success", False):
            QMessageBox.warning(
                self,
                "Löschen fehlgeschlagen",
                str(getattr(result, "message", "Beobachtung konnte nicht gelöscht werden.")),
            )
            return
        self.show_student_profile(draft.student_id)
        self.status_label.setText("Beobachtung wurde gelöscht.")

    def open_student_document_dialog(self, student_id: str) -> None:
        """Attach one or more files directly to a student."""
        file_paths, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            "Dateien hinzufügen",
            "",
            "Alle Dateien (*)",
        )
        if not file_paths:
            return
        for file_path in file_paths:
            try:
                self.adapter.add_student_document(
                    student_id=student_id,
                    source_path=Path(file_path),
                )
            except OSError as error:
                QMessageBox.warning(self, "Dokumente & Medien", str(error))
                return
        self.show_student_profile(student_id)
        self.status_label.setText("Dokumente & Medien wurden gespeichert.")

    def confirm_competency_status(
        self,
        student_id: str,
        competency_id: str,
        confirmed_rating: str,
        note: str,
    ) -> None:
        """Persist a teacher-confirmed competency status and refresh profile."""
        try:
            self.adapter.save_competency_confirmation(
                student_id=student_id,
                competency_id=competency_id,
                confirmed_rating=confirmed_rating,
                note=note,
            )
        except ValueError as error:
            QMessageBox.warning(self, "Kompetenzstand", str(error))
            return
        self.show_student_profile(student_id)
        self.status_label.setText("Kompetenzstand wurde bestätigt.")

    def open_app_info_dialog(self) -> None:
        """Open the compact app information dialog."""
        dialog = AppInfoDialog()
        dialog.exec()

    def open_new_group_dialog(self) -> None:
        """Open the persistent new-group dialog."""
        dialog = MasterDataNameDialog("Neue Stammgruppe")
        if dialog.exec():
            self.master_data_adapter.add_group(dialog.name())
            self.refresh_master_data()
            self.status_label.setText("Stammgruppe wurde gespeichert.")

    def open_new_course_dialog(self) -> None:
        """Open the persistent new-course dialog."""
        dialog = MasterDataNameDialog("Neuer Kurs", include_color=True)
        if dialog.exec():
            self.master_data_adapter.add_course(dialog.name(), dialog.color_hex())
            self.refresh_master_data()
            self.status_label.setText("Kurs wurde gespeichert.")

    def open_rename_group_dialog(self, group_id: str) -> None:
        """Open the persistent rename dialog for a group."""
        item = self.master_data_adapter.groups[group_id]
        dialog = MasterDataNameDialog("Stammgruppe umbenennen", item.name)
        if dialog.exec():
            self.master_data_adapter.rename_group(group_id, dialog.name())
            self.refresh_master_data()
            self.status_label.setText("Stammgruppe wurde umbenannt.")

    def open_rename_course_dialog(self, course_id: str) -> None:
        """Open the persistent rename dialog for a course."""
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
            self.status_label.setText("Kurs wurde umbenannt.")

    def open_new_course_group_dialog(self) -> None:
        """Open the persistent dialog for a new course group."""
        view_model = self.master_data_adapter.view_model()
        dialog = CourseGroupDialog(
            CourseGroupViewModel("", "", (), ()),
            view_model.groups,
            view_model.courses,
            title="Neuer Kursverbund",
        )
        if dialog.exec():
            try:
                self.master_data_adapter.add_course_group(
                    dialog.name(),
                    dialog.selected_group_ids(),
                    dialog.selected_course_ids(),
                )
            except ValueError as error:
                QMessageBox.warning(self, "Kursverbund", str(error))
                return
            self.refresh_master_data()
            self.status_label.setText("Kursverbund wurde gespeichert.")

    def open_edit_course_group_dialog(self, course_group_id: str) -> None:
        """Open the persistent edit dialog for one course group."""
        view_model = self.master_data_adapter.view_model()
        course_group = self.master_data_adapter.course_groups[course_group_id]
        dialog = CourseGroupDialog(course_group, view_model.groups, view_model.courses)
        if dialog.exec():
            try:
                updated_course_group = self.master_data_adapter.update_course_group(
                    course_group_id,
                    dialog.name(),
                    dialog.selected_group_ids(),
                    dialog.selected_course_ids(),
                )
            except ValueError as error:
                QMessageBox.warning(self, "Kursverbund", str(error))
                return
            self._clear_invalid_course_group_filter(updated_course_group)
            self.refresh_master_data()
            self.refresh_students()
            self.status_label.setText("Kursverbund wurde gespeichert.")

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

    def _has_active_student_filter(self) -> bool:
        return bool(
            self.selected_group_id
            or (self.selected_course_group_id and self.selected_course_id)
        )

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
