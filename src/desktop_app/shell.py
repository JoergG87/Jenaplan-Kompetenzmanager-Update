"""Application shell for the PySide6 desktop app."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QDialog,
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
from src.core.learning_report import ReportFinalizationError
from src.core.learning_report_pdf import LearningReportPdfError
from src.core.learning_conference import LearningConferenceCompletionError
from src.core.learning_conference_pdf import LearningConferencePdfError
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from src.desktop_app.adapters.master_data_desktop_adapter import MasterDataDesktopAdapter
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
from src.desktop_app.assets import create_app_icon_label
from src.desktop_app.components import Toast, configure_button
from src.desktop_app.dialogs.app_info_dialog import AppInfoDialog
from src.desktop_app.dialogs.master_data_dialog import (
    CourseGroupDialog,
    MasterDataNameDialog,
)
from src.desktop_app.dialogs.learning_report_dialog import (
    LearningReportDialog,
    LearningReportRevisionDialog,
)
from src.desktop_app.dialogs.learning_conference_dialog import (
    LearningConferenceDialog,
    LearningConferenceDraftSelectionDialog,
    LearningConferenceRevisionDialog,
)
from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog
from src.desktop_app.dialogs.new_student_dialog import NewStudentDialog
from src.desktop_app.dialogs.timetable_entry_dialog import TimetableEntryDialog
from src.desktop_app.navigation import NAVIGATION_ITEMS, resolve_navigation_target
from src.desktop_app.icons import ICON_SIZE_MEDIUM, load_icon
from src.desktop_app.screens.master_data_screen import MasterDataScreen
from src.desktop_app.screens.overview_screen import OverviewScreen
from src.desktop_app.screens.settings_screen import SettingsScreen
from src.desktop_app.screens.student_profile_screen import StudentProfileScreen
from src.desktop_app.screens.students_workspace import StudentsWorkspace
from src.desktop_app.view_models.settings_view_model import (
    DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE,
)
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel
from src.desktop_app.view_models.observation_view_model import ObservationDraftViewModel
from src.desktop_app.view_models.master_data_view_model import CourseGroupViewModel
from src.desktop_app.view_models.learning_conference_view_model import (
    build_learning_conference_completion_error,
)


class AppShell(QMainWindow):
    """Product shell for the local teacher-facing desktop application."""

    def __init__(
        self,
        database_path: Path = SQLITE_SPIKE_PATH,
        now_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        super().__init__()
        self.now_provider = now_provider
        self.adapter = StudentDesktopAdapter(database_path)
        self.master_data_adapter = MasterDataDesktopAdapter(self.adapter)
        self.curriculum_adapter = CurriculumDesktopAdapter(database=self.adapter.database)
        self.timetable_adapter = TimetableDesktopAdapter(self.adapter.database)
        self.selected_group_id: str | None = None
        self.selected_course_group_id: str | None = None
        self.selected_course_id: str | None = None
        self.pending_observation_subject_id = ""
        self.pending_observation_subject_label = ""
        self.pending_observation_target_label = ""
        self.setWindowTitle("Jenaplan Kompetenzmanager")
        self.setMinimumSize(1100, 720)
        self.resize(1400, 900)
        self._build()
        self.dashboard_refresh_timer = QTimer(self)
        self.dashboard_refresh_timer.setInterval(60_000)
        self.dashboard_refresh_timer.timeout.connect(
            self._refresh_dashboard_if_visible
        )
        self.dashboard_refresh_timer.start()
        self.refresh_all()

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 20, 18)
        layout.setSpacing(20)

        sidebar_container = QWidget()
        sidebar_container.setObjectName("AppSidebar")
        sidebar_container.setFixedWidth(212)
        sidebar = QVBoxLayout(sidebar_container)
        sidebar.setContentsMargins(14, 18, 14, 14)
        sidebar.setSpacing(10)
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
        self.navigation.setAccessibleName("Hauptnavigation")
        self.navigation.setAccessibleDescription(
            "Mit Pfeil hoch und runter direkt zwischen den Bereichen wechseln."
        )
        self.navigation.setIconSize(QSize(ICON_SIZE_MEDIUM, ICON_SIZE_MEDIUM))
        self.navigation.setSpacing(1)
        self.navigation.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        current_section = ""
        for item in NAVIGATION_ITEMS:
            if item.section != current_section:
                section_item = QListWidgetItem(item.section)
                section_item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.navigation.addItem(section_item)
                current_section = item.section
            nav_item = QListWidgetItem(item.label)
            nav_item.setData(Qt.ItemDataRole.UserRole, item.key)
            nav_item.setData(Qt.ItemDataRole.AccessibleTextRole, item.label)
            nav_item.setIcon(load_icon(item.icon_name))
            nav_item.setToolTip(item.label)
            self.navigation.addItem(nav_item)
        self.navigation.currentRowChanged.connect(self._show_navigation_index)
        self.navigation.itemClicked.connect(self._show_navigation_item)
        sidebar.addWidget(self.navigation, 1)
        self.info_button = QPushButton("Über die App")
        self.info_button.setIcon(load_icon("info"))
        self.info_button.setIconSize(QSize(16, 16))
        configure_button(self.info_button, "quiet", "Informationen über die App")
        self.info_button.clicked.connect(self.open_app_info_dialog)
        sidebar.addWidget(self.info_button)
        layout.addWidget(sidebar_container)

        content = QVBoxLayout()
        content.setContentsMargins(0, 18, 0, 0)

        self.stack = QStackedWidget()
        self.dashboard_screen = OverviewScreen()
        self.students_workspace = StudentsWorkspace()
        self.overview_screen = self.students_workspace.groups_screen
        self.courses_screen = self.students_workspace.courses_screen
        self.course_groups_screen = self.students_workspace.course_groups_screen
        self.students_screen = self.students_workspace.students_screen
        self.student_profile_screen = StudentProfileScreen()
        self.master_data_screen = MasterDataScreen()
        self.settings_screen = SettingsScreen()

        self.screen_index = {
            "dashboard": self.stack.addWidget(self.dashboard_screen),
            "students": self.stack.addWidget(self.students_workspace),
            "profile": self.stack.addWidget(self.student_profile_screen),
            "master_data": self.stack.addWidget(self.master_data_screen),
            "settings": self.stack.addWidget(self.settings_screen),
        }

        content.addWidget(self.stack)
        self.status_label = Toast()
        content.addWidget(
            self.status_label,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )
        layout.addLayout(content)

        self.setCentralWidget(root)

        self.overview_screen.group_selected.connect(self.show_students_for_group)
        self.course_groups_screen.course_selected.connect(
            self.show_students_for_course_group
        )
        self.students_workspace.course_selected.connect(self.show_students_for_course)
        self.dashboard_screen.timetable_target_selected.connect(
            self.show_students_for_timetable_target
        )
        self.dashboard_screen.timetable_observation_requested.connect(
            self.prepare_timetable_observation
        )
        self.dashboard_screen.timetable_student_observation_requested.connect(
            self.open_dashboard_observation
        )
        self.dashboard_screen.settings_timetable_requested.connect(
            self.show_timetable_settings
        )
        self.students_workspace.new_student_requested.connect(
            self.open_new_student_dialog
        )
        self.students_workspace.all_students_requested.connect(
            self.show_all_students
        )
        self.students_screen.student_selected.connect(self.show_student_profile)
        self.students_screen.observation_requested.connect(
            self.open_quick_observation_dialog
        )
        self.students_screen.back_to_overview_requested.connect(self.return_to_overview)
        self.student_profile_screen.back_requested.connect(self.return_to_students)
        self.student_profile_screen.observation_requested.connect(
            self.open_new_observation_dialog
        )
        self.student_profile_screen.student_edit_requested.connect(
            self.open_edit_student_dialog
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
        self.student_profile_screen.document_remove_requested.connect(
            self.remove_student_document
        )
        self.student_profile_screen.competency_confirmation_requested.connect(
            self.confirm_competency_status
        )
        self.student_profile_screen.report_requested.connect(
            self.open_learning_report_dialog
        )
        self.student_profile_screen.learning_conference_requested.connect(
            self.open_learning_conference_dialog
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
        self.settings_screen.documentation_subjects_save_requested.connect(
            self.save_documentation_subject_settings
        )
        self.settings_screen.timetable_add_requested.connect(
            self.open_new_timetable_entry_dialog
        )
        self.settings_screen.timetable_edit_requested.connect(
            self.open_edit_timetable_entry_dialog
        )
        self.settings_screen.timetable_delete_requested.connect(
            self.delete_timetable_entry
        )
        self.settings_screen.timetable_active_requested.connect(
            self.set_timetable_entry_active
        )
        self._select_navigation("dashboard")
        self.stack.currentChanged.connect(self._handle_screen_activated)

    def refresh_all(self) -> None:
        """Refresh overview and student list from SQLite."""
        self.refresh_students()
        self.refresh_master_data()
        self.refresh_settings()

    def refresh_overview(self) -> None:
        """Refresh the overview from the current master-data scope."""
        self.students_workspace.set_master_data(
            self.master_data_adapter.view_model(),
            self.adapter.list_group_summaries(),
        )
        self.refresh_dashboard()

    def refresh_dashboard(self, at: datetime | None = None) -> None:
        """Refresh time-sensitive dashboard reads for one explicit instant."""
        instant = at or self.now_provider()
        week = self.timetable_adapter.week_view_model()
        projection = self.timetable_adapter.read_projection(instant)
        occurrence = projection.current or projection.next
        suggested_students = (
            self.adapter.list_dashboard_suggested_students(
                target_type=occurrence.entry.target_type,
                target_id=occurrence.entry.target_id,
                subject_id=occurrence.entry.subject_id,
                subject_label=occurrence.entry.subject_label,
                at=instant,
            )
            if occurrence is not None
            else ()
        )
        self.dashboard_screen.set_dashboard(
            projection,
            self.adapter.dashboard_documentation_heatmap(),
            instant,
            not week.is_empty,
            suggested_students,
        )
        if self.stack.currentWidget() is self.dashboard_screen:
            self.status_label.setText("")

    def _refresh_dashboard_if_visible(self) -> None:
        if self.stack.currentWidget() is self.dashboard_screen:
            self.refresh_dashboard()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Stop shell-owned timers before the Qt window is released."""
        self.dashboard_refresh_timer.stop()
        self.status_label.timer.stop()
        super().closeEvent(event)

    def _handle_screen_activated(self, _index: int) -> None:
        if self.stack.currentWidget() is self.dashboard_screen:
            self.refresh_dashboard()

    def refresh_students(self) -> None:
        """Refresh student rows for the current filter."""
        filter_label = "Alle Schüler"
        group_ids: tuple[str, ...] = ()
        course_ids: tuple[str, ...] = ()
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
        elif self.selected_course_group_id:
            course_group = self._selected_course_group()
            if course_group is not None:
                group_ids = course_group.selected_group_ids
                course_ids = course_group.selected_course_ids
                filter_label = f"Kursverbund: {course_group.name}"
        elif self.selected_course_id:
            filter_label = f"Kurs: {self._course_name(self.selected_course_id)}"
        students = self.adapter.list_students(
            group_id=self.selected_group_id,
            group_ids=group_ids,
            course_id=self.selected_course_id,
            course_ids=course_ids,
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

    def refresh_settings(self) -> None:
        """Refresh settings from SQLite-backed adapter data."""
        self.settings_screen.set_settings(self.adapter.settings_view_model())
        self.settings_screen.set_timetable(self.timetable_adapter.week_view_model())

    def open_new_timetable_entry_dialog(self, weekday: int) -> None:
        """Create one timetable entry from the settings week."""
        week = self.timetable_adapter.week_view_model()
        dialog = TimetableEntryDialog(week, weekday=weekday, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._save_timetable_dialog(dialog)

    def open_edit_timetable_entry_dialog(self, timetable_entry_id: str) -> None:
        """Edit one selected timetable entry."""
        week = self.timetable_adapter.week_view_model()
        entry = next(
            (
                entry
                for day in week.days
                for entry in day.entries
                if entry.timetable_entry_id == timetable_entry_id
            ),
            None,
        )
        if entry is None:
            QMessageBox.warning(self, "Stundenplan", "Der Eintrag wurde nicht gefunden.")
            return
        dialog = TimetableEntryDialog(
            week,
            weekday=entry.weekday,
            entry=entry,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._save_timetable_dialog(dialog)

    def delete_timetable_entry(self, timetable_entry_id: str) -> None:
        """Delete one entry after an explicit confirmation."""
        answer = QMessageBox.question(
            self,
            "Stunde löschen",
            "Diesen Stundenplaneintrag wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.timetable_adapter.delete_entry(timetable_entry_id)
        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Stundenplan", str(error))
            return
        self.refresh_settings()
        self.status_label.setText("Stundenplaneintrag wurde gelöscht.")

    def set_timetable_entry_active(
        self,
        timetable_entry_id: str,
        active: bool,
    ) -> None:
        """Persist an explicit active-state change."""
        try:
            self.timetable_adapter.set_entry_active(timetable_entry_id, active)
        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Stundenplan", str(error))
            self.refresh_settings()
            return
        self.refresh_settings()
        self.status_label.setText(
            "Stundenplaneintrag wurde aktiviert."
            if active
            else "Stundenplaneintrag wurde deaktiviert."
        )

    def _save_timetable_dialog(self, dialog: TimetableEntryDialog) -> None:
        try:
            self.timetable_adapter.save_entry(dialog.command())
        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(dialog, "Stundenplan", str(error))
            return
        self.refresh_settings()
        self.status_label.setText("Stundenplaneintrag wurde gespeichert.")

    def save_documentation_subject_settings(
        self,
        subject_ids: tuple[str, ...],
    ) -> None:
        """Persist documentation subject settings through the adapter."""
        self.adapter.save_active_documentation_subjects(subject_ids)
        self.refresh_settings()
        self.settings_screen.show_documentation_subjects_saved()
        self.status_label.setText(DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE)

    def return_to_students(self) -> None:
        """Return from profile to student list and keep current filter."""
        self.refresh_students()
        self.students_workspace.show_student_list(
            source_key=self.students_workspace.list_source_key()
        )
        self._show_screen("students")
        self._select_navigation("students")

    def return_to_overview(self) -> None:
        """Return from a filtered list to its local student selection."""
        self._clear_pending_timetable_observation()
        self.selected_group_id = None
        self.selected_course_group_id = None
        self.selected_course_id = None
        self.refresh_all()
        self.students_workspace.show_source_selection()
        self._show_screen("students")
        self._select_navigation("students")

    def show_all_students(self) -> None:
        """Open the unfiltered list inside the local student workspace."""
        self._clear_pending_timetable_observation()
        self.selected_group_id = None
        self.selected_course_group_id = None
        self.selected_course_id = None
        self.refresh_students()
        self.students_workspace.show_student_list(source_key="all")
        self._show_screen("students")
        self._select_navigation("students")

    def show_students_for_group(self, group_id: str) -> None:
        """Open students screen filtered to one group."""
        self._clear_pending_timetable_observation()
        self.selected_group_id = group_id
        self.selected_course_group_id = None
        self.selected_course_id = None
        self.refresh_students()
        self.students_workspace.show_student_list(source_key="groups")
        self._show_screen("students")
        self._select_navigation("students")

    def show_students_for_course(self, course_id: str) -> None:
        """Open students screen filtered to one course across all groups."""
        self._clear_pending_timetable_observation()
        self.selected_group_id = None
        self.selected_course_group_id = None
        self.selected_course_id = course_id
        self.refresh_students()
        self.students_workspace.show_student_list(source_key="courses")
        self._show_screen("students")
        self._select_navigation("students")

    def show_students_for_course_group(self, course_group_id: str, course_id: str) -> None:
        """Open students screen filtered to one course inside one course group."""
        self._clear_pending_timetable_observation()
        self.selected_group_id = None
        self.selected_course_group_id = course_group_id
        self.selected_course_id = course_id
        self.refresh_students()
        self.students_workspace.show_student_list(source_key="course_groups")
        self._show_screen("students")
        self._select_navigation("students")

    def show_students_for_timetable_target(
        self,
        target_type: str,
        target_id: str,
    ) -> None:
        """Open the existing student context for one timetable target ID."""
        self._clear_pending_timetable_observation()
        self.selected_group_id = target_id if target_type == "group" else None
        self.selected_course_id = target_id if target_type == "course" else None
        self.selected_course_group_id = (
            target_id if target_type == "course_group" else None
        )
        if target_type not in {"group", "course", "course_group"}:
            self.status_label.setText("Das Unterrichtsziel ist nicht verfügbar.")
            return
        self.refresh_students()
        self.students_workspace.show_student_list(
            source_key={
                "group": "groups",
                "course": "courses",
                "course_group": "course_groups",
            }[target_type]
        )
        self._show_screen("students")
        self._select_navigation("students")

    def prepare_timetable_observation(
        self,
        subject_id: str,
        subject_label: str,
        target_type: str,
        target_id: str,
        target_label: str,
    ) -> None:
        """Remember a transient timetable prefill until a child is selected."""
        self.show_students_for_timetable_target(target_type, target_id)
        self.pending_observation_subject_id = subject_id
        self.pending_observation_subject_label = subject_label
        self.pending_observation_target_label = target_label
        self.status_label.setText(
            "Kind auswählen und „Beobachten“ öffnen · "
            f"{subject_label} und {target_label} sind vorgemerkt."
        )

    def open_dashboard_observation(
        self,
        student_id: str,
        subject_id: str,
        subject_label: str,
        target_label: str,
    ) -> None:
        """Open the existing dialog directly with transient lesson context."""
        self.pending_observation_subject_id = subject_id
        self.pending_observation_subject_label = subject_label
        self.pending_observation_target_label = target_label
        self.open_quick_observation_dialog(student_id)

    def show_timetable_settings(self) -> None:
        """Navigate to the existing timetable settings section."""
        self._clear_pending_timetable_observation()
        self._show_screen("settings")
        self._select_navigation("settings")

    def show_student_profile(self, student_id: str) -> None:
        """Open light profile for selected student."""
        profile = self.adapter.get_student_profile(student_id)
        observations = self.adapter.list_observations_for_student(student_id)
        competency_groups = self.adapter.list_competency_overview_for_student(student_id)
        report_preview = self.adapter.get_report_preview_for_student(student_id)
        documentation_statuses = self.adapter.list_documentation_status_for_student(student_id)
        documents = self.adapter.list_documents_for_student(student_id)
        competency_cockpit = self.adapter.competency_cockpit_for_student(student_id)
        profile_dashboard = self.adapter.student_profile_dashboard_for_student(
            student_id
        )
        self.student_profile_screen.set_student(
            profile,
            observations,
            competency_groups,
            report_preview,
            documentation_statuses,
            documents,
            competency_cockpit,
            profile_dashboard,
        )
        self._show_screen("profile")

    def open_new_student_dialog(self) -> None:
        """Open the existing new-student dialog and refresh after success."""
        dialog = NewStudentDialog(self.adapter, self.master_data_adapter)
        dialog.student_created.connect(self.handle_student_created)
        dialog.exec()

    def open_learning_report_dialog(self, student_id: str) -> None:
        """Open the productive report workspace with the latest saved draft."""
        drafts = self.adapter.list_learning_report_drafts_for_student(student_id)
        initial_draft = drafts[0] if drafts else None
        preparation = self.adapter.learning_report_preparation_for_student(
            student_id,
            retained_competency_ids=(
                initial_draft.competency_ids if initial_draft is not None else ()
            ),
        )
        if preparation is None:
            self.status_label.setText("Schülerprofil wurde nicht gefunden.")
            return
        revision_status = (
            self.adapter.learning_report_revision_status(
                initial_draft.report_draft_id
            )
            if initial_draft is not None
            else None
        )
        dialog = LearningReportDialog(
            preparation,
            self,
            initial_draft,
            revision_status,
        )

        def persist_draft(draft: object, *, finalizing: bool = False) -> object | None:
            try:
                saved = self.adapter.save_learning_report_draft(draft)
            except Exception as error:
                if finalizing:
                    dialog.show_finalization_error(
                        "Der Berichtsentwurf konnte vor der Finalisierung nicht "
                        "gespeichert werden. Bitte die markierten Eingaben prüfen."
                    )
                    return None
                QMessageBox.warning(
                    dialog,
                    "Entwurf konnte nicht gespeichert werden",
                    str(error),
                )
                return None
            dialog.apply_saved_draft(saved)
            dialog.apply_revision_status(
                self.adapter.learning_report_revision_status(
                    saved.report_draft_id
                )
            )
            self.status_label.setText("Lernentwicklungsbericht-Entwurf gespeichert.")
            return saved

        def save_draft(draft: object) -> None:
            persist_draft(draft)

        def request_finalization(draft: object) -> None:
            saved = persist_draft(draft, finalizing=True)
            if saved is None:
                return
            try:
                preview = self.adapter.prepare_learning_report_finalization(
                    saved.report_draft_id
                )
            except ReportFinalizationError as error:
                dialog.show_finalization_error(
                    self.adapter.learning_report_finalization_error_message(error)
                )
                return
            except Exception:
                QMessageBox.warning(
                    dialog,
                    "Finalisierung konnte nicht vorbereitet werden",
                    "Ein unerwarteter technischer Fehler ist aufgetreten. "
                    "Der bestehende Berichtstand wurde nicht verändert.",
                )
                return
            dialog.show_finalization_confirmation(preview)

        def finalize_report(report_draft_id: str, display_name: str) -> None:
            try:
                status = self.adapter.finalize_learning_report(
                    report_draft_id,
                    display_name,
                )
            except ReportFinalizationError as error:
                dialog.show_finalization_error(
                    self.adapter.learning_report_finalization_error_message(error)
                )
                return
            except Exception:
                QMessageBox.warning(
                    dialog,
                    "Bericht konnte nicht finalisiert werden",
                    "Ein unerwarteter technischer Fehler ist aufgetreten. "
                    "Die aktuelle finale Revision bleibt unverändert.",
                )
                return
            dialog.apply_revision_status(status, finalized=True)
            self.status_label.setText(
                f"Berichtrevision {status.current_revision_number} finalisiert."
            )

        def open_revision(learning_report_revision_id: str) -> None:
            try:
                revision = self.adapter.load_learning_report_revision(
                    learning_report_revision_id
                )
            except ReportFinalizationError:
                QMessageBox.warning(
                    dialog,
                    "Finale Fassung konnte nicht geöffnet werden",
                    "Der gespeicherte Snapshot konnte nicht verifiziert werden. "
                    "Aktuelle Schüler- oder Berichtsdaten wurden nicht als Ersatz geladen.",
                )
                return
            except Exception:
                QMessageBox.warning(
                    dialog,
                    "Finale Fassung konnte nicht geöffnet werden",
                    "Ein unerwarteter technischer Fehler ist aufgetreten.",
                )
                return
            if revision is None:
                dialog.show_finalization_error(
                    "Die ausgewählte Berichtrevision ist nicht verfügbar."
                )
                return
            artifact = None
            artifact_error = ""
            try:
                artifact = self.adapter.load_learning_report_pdf_artifact(
                    learning_report_revision_id
                )
            except Exception as error:
                artifact_error = self.adapter.learning_report_pdf_error_message(error)
            revision_dialog = LearningReportRevisionDialog(
                revision,
                dialog,
                artifact,
            )
            if artifact_error:
                revision_dialog.show_pdf_error(artifact_error)

            def generate_final_pdf(revision_id: str) -> None:
                try:
                    generated = self.adapter.generate_learning_report_pdf(revision_id)
                except LearningReportPdfError as error:
                    revision_dialog.show_pdf_error(
                        self.adapter.learning_report_pdf_error_message(error)
                    )
                    return
                except Exception:
                    revision_dialog.show_pdf_error(
                        "Das finale PDF konnte wegen eines technischen Fehlers "
                        "nicht erstellt werden."
                    )
                    return
                revision_dialog.apply_pdf_artifact(generated)
                self.status_label.setText(
                    f"Finales PDF erstellt: {generated.file_name}"
                )

            revision_dialog.pdf_requested.connect(generate_final_pdf)
            revision_dialog.exec()

        dialog.save_requested.connect(save_draft)
        dialog.finalization_requested.connect(request_finalization)
        dialog.finalize_confirmed.connect(finalize_report)
        dialog.revision_open_requested.connect(open_revision)
        dialog.pdf_requested.connect(self.export_learning_report_pdf)
        dialog.exec()

    def open_learning_conference_dialog(self, student_id: str) -> None:
        """Open one unambiguous LEG draft or let the teacher choose calmly."""
        drafts = self.adapter.list_learning_conference_drafts_for_student(student_id)
        initial_draft = drafts[0] if len(drafts) == 1 else None
        if len(drafts) > 1:
            accepted, initial_draft = LearningConferenceDraftSelectionDialog.choose(
                drafts,
                self,
            )
            if not accepted:
                return
        preparation = self.adapter.learning_conference_preparation_for_student(
            student_id,
            retained_competency_ids=(
                initial_draft.competency_ids if initial_draft is not None else ()
            ),
        )
        if preparation is None:
            self.status_label.setText("Schülerprofil wurde nicht gefunden.")
            return
        dialog = LearningConferenceDialog(preparation, self, initial_draft)

        def refresh_revision_status() -> None:
            draft = dialog.draft_view_model()
            if not draft.learning_conference_draft_id:
                return
            try:
                status = self.adapter.learning_conference_revision_status(
                    draft.learning_conference_draft_id
                )
            except LearningConferenceCompletionError as error:
                dialog.show_completion_error(
                    build_learning_conference_completion_error(error)
                )
                return
            dialog.apply_revision_status(status)

        def save_draft(draft: object) -> None:
            try:
                saved = self.adapter.save_learning_conference_draft(draft)
            except Exception as error:
                dialog.show_save_error(str(error))
                return
            dialog.apply_saved_draft(saved)
            refresh_revision_status()
            self.status_label.setText("Lernentwicklungsgespräch-Entwurf gespeichert.")

        def complete_conference(learning_conference_draft_id: str) -> None:
            try:
                status = self.adapter.complete_learning_conference(
                    learning_conference_draft_id
                )
            except LearningConferenceCompletionError as error:
                dialog.show_completion_error(
                    build_learning_conference_completion_error(error)
                )
                return
            dialog.apply_revision_status(status)
            self.status_label.setText("Lernentwicklungsgespräch abgeschlossen.")

        def open_revision(learning_conference_revision_id: str) -> None:
            try:
                revision = self.adapter.load_learning_conference_revision(
                    learning_conference_revision_id
                )
            except LearningConferenceCompletionError as error:
                dialog.show_completion_error(
                    build_learning_conference_completion_error(error)
                )
                return
            artifact = None
            artifact_error = ""
            try:
                artifact = self.adapter.load_learning_conference_pdf_artifact(
                    learning_conference_revision_id
                )
            except Exception as error:
                artifact_error = self.adapter.learning_conference_pdf_error_message(
                    error
                )
            revision_dialog = LearningConferenceRevisionDialog(
                revision,
                dialog,
                artifact,
            )
            if artifact_error:
                revision_dialog.show_pdf_error(artifact_error)

            def generate_final_pdf(revision_id: str) -> None:
                try:
                    generated = self.adapter.generate_learning_conference_pdf(
                        revision_id
                    )
                except LearningConferencePdfError as error:
                    revision_dialog.show_pdf_error(
                        self.adapter.learning_conference_pdf_error_message(error)
                    )
                    return
                except Exception:
                    revision_dialog.show_pdf_error(
                        "Das finale LEG-PDF konnte wegen eines technischen Fehlers "
                        "nicht erstellt werden."
                    )
                    return
                revision_dialog.apply_pdf_artifact(generated)
                self.status_label.setText(
                    f"Finales LEG-PDF erstellt: {generated.file_name}"
                )

            revision_dialog.pdf_requested.connect(generate_final_pdf)
            revision_dialog.exec()

        dialog.save_requested.connect(save_draft)
        dialog.completion_requested.connect(complete_conference)
        dialog.revision_open_requested.connect(open_revision)
        refresh_revision_status()
        dialog.exec()

    def export_learning_report_pdf(self, output_model: object) -> None:
        """Hand a complete neutral output model to the unchanged PDF renderer."""
        metadata = getattr(output_model, "metadata", None)
        student_name = str(getattr(metadata, "student_name", "Lernentwicklungsbericht"))
        safe_name = "_".join(student_name.split()) or "Lernentwicklungsbericht"
        target_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Lernentwicklungsbericht als PDF speichern",
            f"Lernentwicklungsbericht_{safe_name}.pdf",
            "PDF-Datei (*.pdf)",
        )
        if not target_path:
            return
        try:
            from prototypes.pdf_engine.renderer import PdfRenderer

            rendered_path = PdfRenderer().render(output_model, Path(target_path))
        except Exception as error:  # pragma: no cover - platform/reportlab feedback
            QMessageBox.warning(
                self,
                "PDF konnte nicht erstellt werden",
                str(error),
            )
            return
        self.status_label.setText(f"PDF erstellt: {rendered_path}")

    def open_edit_student_dialog(self, student_id: str) -> None:
        """Open the student dialog with persisted student data."""
        student = self.adapter.student_record_for_edit(student_id)
        if student is None:
            self.status_label.setText("Schülerprofil wurde nicht gefunden.")
            return
        dialog = NewStudentDialog(
            self.adapter,
            self.master_data_adapter,
            student=student,
        )
        if dialog.exec():
            self.refresh_overview()
            self.refresh_students()
            self.show_student_profile(student_id)
            self.status_label.setText("Schülerdaten wurden gespeichert.")

    def open_new_observation_dialog(self, student: StudentDetailViewModel) -> None:
        """Open the persistent observation dialog and refresh after success."""
        prefill = self._pending_timetable_observation_draft(student)
        dialog = NewObservationDialog(
            student,
            self.curriculum_adapter,
            self.adapter,
            subject_options=(
                self.adapter.list_observation_subject_options(prefill)
                if prefill is not None
                else self.adapter.list_observation_subject_options()
            ),
            competency_subject_groups=(
                self.adapter.list_observation_competency_subject_groups(prefill)
                if prefill is not None
                else self.adapter.list_observation_competency_subject_groups()
            ),
            recent_competencies=self.adapter.list_recent_observation_competencies(
                student.student_id,
                prefill,
            ),
            prefill_subject_id=self.pending_observation_subject_id,
            prefill_context=prefill.context if prefill is not None else "",
        )
        self._clear_pending_timetable_observation()
        if dialog.exec():
            self.show_student_profile(student.student_id)
            self.status_label.setText("Beobachtung wurde gespeichert.")

    def open_quick_observation_dialog(self, student_id: str) -> None:
        """Open the observation dialog from a student list row."""
        student = self.adapter.get_student_profile(student_id)
        if student is None:
            self.status_label.setText("Schülerprofil wurde nicht gefunden.")
            return
        prefill = self._pending_timetable_observation_draft(student)
        dialog = NewObservationDialog(
            student,
            self.curriculum_adapter,
            self.adapter,
            subject_options=(
                self.adapter.list_observation_subject_options(prefill)
                if prefill is not None
                else self.adapter.list_observation_subject_options()
            ),
            competency_subject_groups=(
                self.adapter.list_observation_competency_subject_groups(prefill)
                if prefill is not None
                else self.adapter.list_observation_competency_subject_groups()
            ),
            recent_competencies=self.adapter.list_recent_observation_competencies(
                student.student_id,
                prefill,
            ),
            prefill_subject_id=self.pending_observation_subject_id,
            prefill_context=prefill.context if prefill is not None else "",
        )
        self._clear_pending_timetable_observation()
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
            subject_options=self.adapter.list_observation_subject_options(draft),
            competency_subject_groups=(
                self.adapter.list_observation_competency_subject_groups(draft)
            ),
            recent_competencies=self.adapter.list_recent_observation_competencies(
                student.student_id,
                draft,
            ),
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
        self.status_label.setText(
            "Beobachtung wurde gelöscht. Profil bleibt geöffnet."
        )

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

    def remove_student_document(self, student_id: str, document_id: str) -> None:
        """Soft-delete one student document after confirmation."""
        response = QMessageBox.question(
            self,
            "Datei entfernen",
            "Diese Datei aus dem Schülerprofil entfernen? "
            "Die Datei bleibt im Dateisystem erhalten.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        self.adapter.remove_document(document_id)
        self.show_student_profile(student_id)
        self.status_label.setText("Datei wurde entfernt.")

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
        self.status_label.setText("Kompetenzstand wurde aktuell bestätigt.")

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
        self.selected_group_id = None
        self.selected_course_group_id = None
        self.selected_course_id = None
        self.refresh_all()
        self.students_workspace.show_student_list(source_key="all")
        self._show_screen("students")
        self._select_navigation("students")
        self.status_label.show_message("Schüler wurde gespeichert.", tone="success")

    def _show_navigation_index(self, index: int) -> None:
        if index < 0:
            return
        self._show_navigation_item(self.navigation.item(index))

    def _show_navigation_item(self, item: QListWidgetItem) -> None:
        key_data = item.data(Qt.ItemDataRole.UserRole)
        if not key_data:
            return
        key = str(key_data)
        self._clear_pending_timetable_observation()
        target = resolve_navigation_target(key)
        if target.reset_group_filter:
            self.selected_group_id = None
            self.selected_course_group_id = None
            self.selected_course_id = None
            self.refresh_students()
            self.students_workspace.show_section("groups")
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
            or self.selected_course_group_id
            or self.selected_course_id
        )

    def _pending_timetable_observation_draft(
        self,
        student: StudentDetailViewModel,
    ) -> ObservationDraftViewModel | None:
        if not self.pending_observation_subject_id:
            return None
        return ObservationDraftViewModel(
            student_id=student.student_id,
            student_name=student.display_name,
            date_text=self.now_provider().date().isoformat(),
            competency_ratings=(),
            context=f"Unterricht · {self.pending_observation_target_label}",
            note="",
            subject_id=self.pending_observation_subject_id,
            subject_display_name=self.pending_observation_subject_label,
        )

    def _clear_pending_timetable_observation(self) -> None:
        self.pending_observation_subject_id = ""
        self.pending_observation_subject_label = ""
        self.pending_observation_target_label = ""

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
