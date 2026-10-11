"""Application shell for the PySide6 desktop app."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
import weakref

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
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
from shiboken6 import isValid

from src.core.app_preferences import (
    AppPreferences,
    AppPreferencesFile,
    ONBOARDING_BASE_STEP_COUNT,
)
from src.core.onboarding import OnboardingController, OnboardingSession
from src.core.sqlite_store import SQLITE_SPIKE_PATH
from src.core.sqlite_school_year_assignment import (
    SchoolYearAssignmentRepositoryError,
)
from src.application.school_year_transition_preview import (
    SchoolYearTransitionPreviewService,
)
from src.application.commands.backup import CreateBackupCommand
from src.application.commands.school_year_transition_backup import (
    VerifiedCipherSchoolYearTransitionBackupAdapter,
    VerifiedSchoolYearTransitionBackupAdapter,
)
from src.application.school_year_transition_execution import (
    ExecuteSchoolYearTransition,
)
from src.application.school_year_transition_step_up import (
    SchoolYearTransitionStepUpService,
)
from src.core.learning_report import ReportFinalizationError
from src.core.learning_report_pdf import LearningReportPdfError
from src.core.learning_conference import LearningConferenceCompletionError
from src.core.learning_conference_pdf import LearningConferencePdfError
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from src.desktop_app.adapters.master_data_desktop_adapter import MasterDataDesktopAdapter
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
from src.desktop_app.adapters.backup_restore_desktop_adapter import (
    BackupRestoreDesktopAdapter,
    CipherBackupRestoreUnavailableError,
)
from src.desktop_app.backup_restore_operations import (
    BackupRestoreOperationErrorInfo,
    BackupRestoreOperationsController,
    BackupRestoreOperationType,
    BackupRestoreProgressPhase,
)
from src.desktop_app.assets import create_app_icon_label
from src.desktop_app.components import Toast, configure_button, create_confirmation_message
from src.desktop_app.dialogs.app_info_dialog import AppInfoDialog
from src.desktop_app.dialogs.master_data_dialog import (
    CourseGroupDialog,
    MasterDataNameDialog,
)
from src.desktop_app.dialogs.learning_report_dialog import (
    LearningReportDialog,
    LearningReportDraftSelectionDialog,
    LearningReportPeriodSelectionDialog,
    LearningReportRevisionDialog,
)
from src.desktop_app.dialogs.learning_conference_dialog import (
    LearningConferenceDialog,
    LearningConferenceDraftSelectionDialog,
    LearningConferenceRevisionDialog,
)
from src.desktop_app.dialogs.pdf_artifact_viewer_dialog import (
    PdfArtifactBufferConsumer,
    PdfArtifactViewerDialog,
)
from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog
from src.desktop_app.dialogs.new_student_dialog import NewStudentDialog
from src.desktop_app.dialogs.school_year_transition_preview_dialog import (
    SchoolYearTransitionPreviewDialog,
)
from src.desktop_app.school_year_transition_activation import (
    SchoolYearTransitionActivationController,
)
from src.desktop_app.dialogs.timetable_entry_dialog import TimetableEntryDialog
from src.desktop_app.navigation import NAVIGATION_ITEMS, resolve_navigation_target
from src.desktop_app.icons import ICON_SIZE_MEDIUM, load_icon
from src.desktop_app.motion import install_item_selection_motion
from src.desktop_app.screens.master_data_screen import MasterDataScreen
from src.desktop_app.screens.overview_screen import OverviewScreen
from src.desktop_app.screens.onboarding_screen import (
    OnboardingScreen,
    OnboardingStatusProjection,
)
from src.desktop_app.screens.settings_screen import SettingsScreen
from src.desktop_app.runtime import RuntimePaths, runtime_paths, load_build_info
from src.desktop_app.view_models.backup_restore_view_model import RestorePreviewViewModel
from src.version import APP_VERSION
from src.version import APP_BUILD_VERSION
from src.updater.application import UpdateApplicationService
from src.updater.domain import UpdateChannel
from src.updater.infrastructure import build_native_update_adapter
from src.core.restore_runtime import RuntimeInstanceLock
from src.desktop_app.restore_worker import RestoreWorkerProcess
from src.desktop_app.screens.student_profile_screen import StudentProfileScreen
from src.desktop_app.screens.students_workspace import StudentsWorkspace
from src.desktop_app.view_models.settings_view_model import (
    DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE,
)
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel
from src.desktop_app.view_models.observation_view_model import ObservationDraftViewModel
from src.desktop_app.view_models.master_data_view_model import CourseGroupViewModel
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceDraftViewModel,
    LearningConferencePreparationViewModel,
    LearningConferenceRevisionStatusViewModel,
    build_learning_conference_completion_error,
)
from src.desktop_app.leg_ui import leg_ui_mode
from src.desktop_app.report_ui import report_ui_mode
from src.desktop_app.window_policy import (
    exec_maximized_workspace,
    open_maximized_workspace,
    prepare_maximized_workspace,
)


SCHOOL_YEAR_BLOCK_MESSAGE = (
    "Kein eindeutiges aktuelles Schuljahr: "
    "Schülerbezogene Bereiche bleiben gesperrt."
)
ASSIGNMENT_BLOCK_MESSAGE = (
    "Aktuelle Schülerzuordnungen sind nicht eindeutig: "
    "Schülerbezogene Bereiche bleiben gesperrt."
)
INVALID_TARGET_SCHOOL_YEAR_ISSUES = frozenset(
    {
        "NEW_SCHOOL_YEAR_DATE_INVALID",
        "NEW_SCHOOL_YEAR_DATE_RANGE_INVALID",
        "NEW_SCHOOL_YEAR_LABEL_INVALID",
        "NEW_SCHOOL_YEAR_NOT_AFTER_CURRENT",
        "NEW_SCHOOL_YEAR_OVERLAP",
        "SCHOOL_YEAR_GAP",
    }
)


class _SidebarNavigationList(QListWidget):
    """Keep the pointer cursor scoped to mouse-activatable sidebar items."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pointer_position: QPoint | None = None
        self._pointer_inside = False
        self._application_active = (
            QApplication.applicationState()
            == Qt.ApplicationState.ApplicationActive
        )
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.verticalScrollBar().valueChanged.connect(self._schedule_cursor_refresh)
        self.horizontalScrollBar().valueChanged.connect(self._schedule_cursor_refresh)
        model = self.model()
        model.rowsInserted.connect(self._schedule_cursor_refresh)
        model.rowsRemoved.connect(self._schedule_cursor_refresh)
        model.modelReset.connect(self._schedule_cursor_refresh)
        model.layoutChanged.connect(self._schedule_cursor_refresh)
        model.dataChanged.connect(self._schedule_cursor_refresh)
        QApplication.instance().applicationStateChanged.connect(
            self._application_state_changed
        )

    def viewportEvent(self, event: QEvent) -> bool:  # noqa: N802 - Qt API
        event_type = event.type()
        if event_type == QEvent.Type.MouseMove:
            self._pointer_inside = True
            self._pointer_position = event.position().toPoint()
        elif event_type == QEvent.Type.Enter:
            self._pointer_inside = True
            self._pointer_position = event.position().toPoint()
        elif event_type in {QEvent.Type.Leave, QEvent.Type.Hide}:
            self._pointer_inside = False
            self._pointer_position = None

        handled = super().viewportEvent(event)
        if event_type in {
            QEvent.Type.MouseMove,
            QEvent.Type.Enter,
            QEvent.Type.Leave,
            QEvent.Type.Hide,
        }:
            self._refresh_cursor()
        return handled

    def _application_state_changed(self, state: Qt.ApplicationState) -> None:
        self._application_active = state == Qt.ApplicationState.ApplicationActive
        if self._application_active:
            self._schedule_cursor_refresh()
        else:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def _schedule_cursor_refresh(self, *_args: object) -> None:
        navigation_ref = weakref.ref(self)

        def refresh_if_valid() -> None:
            navigation = navigation_ref()
            if navigation is not None and isValid(navigation):
                navigation._refresh_cursor()

        QTimer.singleShot(0, refresh_if_valid)

    def _refresh_cursor(self) -> None:
        position = self._pointer_position
        item = (
            self.itemAt(position)
            if self._pointer_inside
            and position is not None
            and self.viewport().rect().contains(position)
            else None
        )
        flags = item.flags() if item is not None else Qt.ItemFlag.NoItemFlags
        activatable = bool(
            item is not None
            and self._application_active
            and item.data(Qt.ItemDataRole.UserRole)
            and flags & Qt.ItemFlag.ItemIsEnabled
            and flags & Qt.ItemFlag.ItemIsSelectable
        )
        self.viewport().setCursor(
            Qt.CursorShape.PointingHandCursor
            if activatable
            else Qt.CursorShape.ArrowCursor
        )


class AppShell(QMainWindow):
    """Product shell for the local teacher-facing desktop application."""

    lock_requested = Signal()
    password_change_requested = Signal()
    recovery_codes_requested = Signal()
    support_reset_requested = Signal()
    inactivity_minutes_changed = Signal(int)
    device_credential_enable_requested = Signal()
    device_credential_disable_requested = Signal()
    touch_id_preference_changed = Signal(bool)
    display_name_changed = Signal(str)
    restore_handoff_started = Signal()

    def __init__(
        self,
        database_path: Path = SQLITE_SPIKE_PATH,
        now_provider: Callable[[], datetime] = datetime.now,
        *,
        paths: RuntimePaths | None = None,
        runtime_lock: RuntimeInstanceLock | None = None,
        update_service: UpdateApplicationService | None = None,
        database_create_allowed: bool = False,
        student_adapter: StudentDesktopAdapter | None = None,
        backup_restore_available: bool = True,
        backup_restore_adapter: BackupRestoreDesktopAdapter | None = None,
    ) -> None:
        super().__init__()
        self.now_provider = now_provider
        self.display_name: str | None = None
        self.runtime_paths = paths or runtime_paths(database_path.parent)
        self.backup_restore_available = bool(backup_restore_available)
        if not self.backup_restore_available and student_adapter is None:
            raise ValueError("cipher_product_student_adapter_required")
        self.adapter = student_adapter or StudentDesktopAdapter(
            database_path,
            database_create_allowed=database_create_allowed,
            today_provider=lambda: self.now_provider().date(),
            now_provider=self.now_provider,
        )
        self.maintenance_gate = self.adapter.database.maintenance_gate
        self.exports_directory = self.runtime_paths.exports
        self.master_data_adapter = MasterDataDesktopAdapter(self.adapter)
        self.curriculum_adapter = CurriculumDesktopAdapter(database=self.adapter.database)
        self.timetable_adapter = TimetableDesktopAdapter(self.adapter.database)
        build_info = load_build_info()
        self.pilot_testdata_onboarding = False
        self.update_service = update_service or UpdateApplicationService(
            build_native_update_adapter(),
            current_version=APP_VERSION,
            build_version=APP_BUILD_VERSION,
            channel=UpdateChannel.PILOT,
        )
        self.backup_restore_adapter = backup_restore_adapter or (
            BackupRestoreDesktopAdapter(
                self.runtime_paths,
                app_version=APP_VERSION,
                build_commit=str(build_info.get("git_commit", "unknown")),
                source_tree_state=(str(build_info["source_tree_state"]) if build_info.get("source_tree_state") is not None else None),
                lock=runtime_lock,
                enabled=self.backup_restore_available,
            )
        )
        self.backup_restore_operations = BackupRestoreOperationsController(
            backup_service=self.backup_restore_adapter.backup_service,
            restore_service=self.backup_restore_adapter.restore_service,
            parent=self,
        )
        self._prepared_restore_preview: RestorePreviewViewModel | None = None
        self._restore_worker_process: RestoreWorkerProcess | None = None
        self._restore_worker_start_attempted = False
        self._restore_confirmed = False
        self._restore_shutdown_in_progress = False
        self._backup_status_loaded = False
        self._school_year_transition_step_up: (
            SchoolYearTransitionStepUpService | None
        ) = None
        self._school_year_transition_executor: (
            ExecuteSchoolYearTransition | None
        ) = None
        self._active_school_year_transition_controller: (
            SchoolYearTransitionActivationController | None
        ) = None
        self._active_school_year_transition_dialog: (
            SchoolYearTransitionPreviewDialog | None
        ) = None
        self.onboarding_controller: OnboardingController | None = None
        self.selected_group_id: str | None = None
        self.selected_course_group_id: str | None = None
        self.selected_course_id: str | None = None
        self.pending_observation_subject_id = ""
        self.pending_observation_subject_label = ""
        self.pending_observation_target_label = ""
        self._selected_report_draft_ids: dict[str, str] = {}
        self._selected_learning_conference_draft_ids: dict[str, str] = {}
        self._active_learning_conference_student_ids: set[str] = set()
        self._active_learning_conference_dialog: LearningConferenceDialog | None = None
        self._active_learning_report_dialog: LearningReportDialog | None = None
        self._active_learning_report_revision_id = ""
        self._active_learning_report_revision_student_id = ""
        self._active_learning_report_revision_dialog: (
            LearningReportRevisionDialog | None
        ) = None
        self._active_pdf_viewer_dialog: PdfArtifactViewerDialog | None = None
        self.setWindowTitle("Jenaplan Kompetenzmanager")
        self.setMinimumSize(1100, 720)
        self.resize(1400, 900)
        self._build()
        self.new_observation_action = QAction("Neue Beobachtung", self)
        self.new_observation_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_observation_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.new_observation_action.setAutoRepeat(False)
        self.new_observation_action.triggered.connect(self._open_observation_shortcut)
        self.addAction(self.new_observation_action)
        self.student_profile_screen.profile_primary_action.setToolTip(
            "Neue Beobachtung ("
            + self.new_observation_action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
            + ")"
        )
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
        self.navigation = _SidebarNavigationList()
        self.navigation.setObjectName("AppNavigation")
        self.navigation.setAccessibleName("Hauptnavigation")
        self.navigation.setAccessibleDescription(
            "Mit Pfeil hoch und runter direkt zwischen den Bereichen wechseln."
        )
        self.navigation.setIconSize(QSize(ICON_SIZE_MEDIUM, ICON_SIZE_MEDIUM))
        self.navigation.setSpacing(1)
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
        install_item_selection_motion(self.navigation)
        sidebar.addWidget(self.navigation, 1)
        self.info_button = QPushButton("Über die App")
        self.info_button.setIcon(load_icon("info"))
        self.info_button.setIconSize(QSize(16, 16))
        configure_button(self.info_button, "quiet", "Informationen über die App")
        self.info_button.clicked.connect(self.open_app_info_dialog)
        sidebar.addWidget(self.info_button)
        self.lock_button = QPushButton("App sperren")
        configure_button(self.lock_button, "quiet", "App jetzt sperren")
        self.lock_button.clicked.connect(self.lock_requested)
        sidebar.addWidget(self.lock_button)
        layout.addWidget(sidebar_container)

        content = QVBoxLayout()
        content.setContentsMargins(0, 18, 0, 0)
        self.onboarding_return_button = QPushButton("‹ Zurück zu Erste Schritte")
        self.onboarding_return_button.setObjectName("OnboardingReturnButton")
        configure_button(
            self.onboarding_return_button,
            "quiet",
            "Zurück zu Erste Schritte",
        )
        self.onboarding_return_button.clicked.connect(self._return_to_onboarding)
        self.onboarding_return_button.setVisible(False)
        content.addWidget(
            self.onboarding_return_button,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )

        self.stack = QStackedWidget()
        self.dashboard_screen = OverviewScreen()
        self.onboarding_screen = OnboardingScreen()
        self.students_workspace = StudentsWorkspace()
        self.overview_screen = self.students_workspace.groups_screen
        self.courses_screen = self.students_workspace.courses_screen
        self.course_groups_screen = self.students_workspace.course_groups_screen
        self.students_screen = self.students_workspace.students_screen
        self.student_profile_screen = StudentProfileScreen(
            export_directory=self.exports_directory
        )
        self.master_data_screen = MasterDataScreen()
        self.settings_screen = SettingsScreen(now_provider=self.now_provider)
        self.settings_screen.set_backup_restore_available(
            self.backup_restore_available
        )
        self.settings_screen.set_cipher_product_mode(
            self.backup_restore_adapter.backup_extension == ".jkmebackup"
        )

        self.screen_index = {
            "dashboard": self.stack.addWidget(self.dashboard_screen),
            "onboarding": self.stack.addWidget(self.onboarding_screen),
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
        self.dashboard_screen.timetable_student_profile_requested.connect(
            self.show_student_profile
        )
        self.dashboard_screen.settings_timetable_requested.connect(
            self.show_timetable_settings
        )
        self.onboarding_screen.next_requested.connect(self._onboarding_next)
        self.onboarding_screen.back_requested.connect(self._onboarding_back)
        self.onboarding_screen.skip_confirmed.connect(self._onboarding_dismiss)
        self.onboarding_screen.finish_requested.connect(self._onboarding_complete)
        self.onboarding_screen.navigation_requested.connect(
            self._navigate_from_onboarding
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
        self.student_profile_screen.document_replace_requested.connect(
            self.replace_student_document
        )
        self.student_profile_screen.document_remove_requested.connect(
            self.remove_student_document
        )
        self.student_profile_screen.competency_confirmation_requested.connect(
            self.confirm_competency_status
        )
        self.student_profile_screen.documentation_subjects_save_requested.connect(
            self.save_student_documentation_subjects
        )
        self.student_profile_screen.competency_pdf_requested.connect(
            self.export_competency_overview_pdf
        )
        self.student_profile_screen.report_requested.connect(
            self.open_learning_report_dialog
        )
        self.student_profile_screen.learning_conference_requested.connect(
            self.open_learning_conference_dialog
        )
        self.student_profile_screen.report_draft_requested.connect(
            self.open_learning_report_dialog
        )
        self.student_profile_screen.learning_conference_draft_requested.connect(
            self.open_learning_conference_dialog
        )
        self.student_profile_screen.report_revision_requested.connect(
            self.open_learning_report_revision
        )
        self.student_profile_screen.learning_conference_revision_requested.connect(
            self.open_learning_conference_revision
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
        self.settings_screen.backup_create_requested.connect(self.create_backup)
        self.settings_screen.backup_verify_requested.connect(self.verify_backup)
        self.settings_screen.restore_prepare_requested.connect(self.prepare_restore)
        self.settings_screen.restore_start_requested.connect(self.start_restore)
        self.settings_screen.backup_restore_page_opened.connect(
            self._load_backup_status
        )
        self.settings_screen.updates_page_opened.connect(self.refresh_update_status)
        self.settings_screen.update_check_requested.connect(self.check_for_updates)
        self.settings_screen.school_year_transition_preview_requested.connect(
            self.open_school_year_transition_preview
        )
        self.settings_screen.onboarding_requested.connect(self.open_onboarding_from_settings)
        self.settings_screen.lock_requested.connect(self.lock_requested)
        self.settings_screen.password_change_requested.connect(
            self.password_change_requested
        )
        self.settings_screen.recovery_codes_requested.connect(
            self.recovery_codes_requested
        )
        self.settings_screen.support_reset_requested.connect(
            self.support_reset_requested
        )
        self.settings_screen.inactivity_minutes_changed.connect(
            self.inactivity_minutes_changed
        )
        self.settings_screen.device_credential_enable_requested.connect(
            self.device_credential_enable_requested
        )
        self.settings_screen.device_credential_disable_requested.connect(
            self.device_credential_disable_requested
        )
        self.settings_screen.touch_id_preference_changed.connect(
            self.touch_id_preference_changed
        )
        self.settings_screen.display_name_changed.connect(self.display_name_changed)
        self.backup_restore_operations.progress.connect(
            self._show_backup_restore_progress
        )
        self.backup_restore_operations.succeeded.connect(
            self._handle_backup_restore_success
        )
        self.backup_restore_operations.failed.connect(
            self._handle_backup_restore_failure
        )
        self.backup_restore_operations.state_changed.connect(
            self._handle_backup_restore_state
        )
        self._select_navigation("dashboard")
        self.stack.currentChanged.connect(self._handle_screen_activated)
        self.refresh_update_status()

    def refresh_all(self) -> None:
        """Refresh overview and student list from SQLite."""
        self.refresh_students()
        self.refresh_master_data()
        self.refresh_settings()

    def refresh_overview(self) -> None:
        """Refresh the overview from the current master-data scope."""
        if self.adapter.current_school_year() is None:
            self.students_workspace.set_master_data(
                self.master_data_adapter.view_model(),
                (),
            )
            self.dashboard_screen.set_membership_blocked(
                SCHOOL_YEAR_BLOCK_MESSAGE
            )
            self.status_label.setText(SCHOOL_YEAR_BLOCK_MESSAGE)
            return
        try:
            group_summaries = self.adapter.list_group_summaries()
        except SchoolYearAssignmentRepositoryError as error:
            message = self._membership_block_message(error)
            self.students_workspace.set_master_data(
                self.master_data_adapter.view_model(),
                (),
            )
            self.dashboard_screen.set_membership_blocked(message)
            self.status_label.setText(message)
            return
        self.students_workspace.set_master_data(
            self.master_data_adapter.view_model(),
            group_summaries,
        )
        self.refresh_dashboard()

    def refresh_dashboard(self, at: datetime | None = None) -> None:
        """Refresh time-sensitive dashboard reads for one explicit instant."""
        if self.adapter.current_school_year() is None:
            self.dashboard_screen.set_membership_blocked(
                SCHOOL_YEAR_BLOCK_MESSAGE
            )
            self.status_label.setText(SCHOOL_YEAR_BLOCK_MESSAGE)
            return
        instant = at or self.now_provider()
        week = self.timetable_adapter.week_view_model()
        projection = self.timetable_adapter.read_projection(instant)
        occurrence = projection.current or projection.next
        try:
            if occurrence is not None:
                heatmap, suggested_students = (
                    self.adapter.dashboard_documentation_refresh(
                        target_type=occurrence.entry.target_type,
                        target_id=occurrence.entry.target_id,
                        subject_id=occurrence.entry.subject_id,
                        subject_label=occurrence.entry.subject_label,
                        at=instant,
                    )
                )
            else:
                heatmap, suggested_students = (
                    self.adapter.dashboard_documentation_refresh(
                        at=instant,
                    )
                )
        except SchoolYearAssignmentRepositoryError as error:
            message = self._membership_block_message(error)
            self.dashboard_screen.set_membership_blocked(message)
            self.status_label.setText(message)
            return
        self.dashboard_screen.set_dashboard(
            projection,
            heatmap,
            instant,
            not week.is_empty,
            suggested_students,
            self.display_name,
        )
        if self.stack.currentWidget() is self.dashboard_screen:
            self.status_label.setText("")

    def _refresh_dashboard_if_visible(self) -> None:
        if self.stack.currentWidget() is self.dashboard_screen:
            self.refresh_dashboard()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Stop shell-owned timers before the Qt window is released."""
        transition_busy = (
            self._active_school_year_transition_controller is not None
            and self._active_school_year_transition_controller.is_busy
        )
        transition_close_blocked = (
            self._active_school_year_transition_dialog is not None
            and self._active_school_year_transition_dialog.close_blocked
        )
        if (
            self.backup_restore_operations.is_busy
            or transition_busy
            or transition_close_blocked
        ):
            event.ignore()
            self.settings_screen.show_close_blocked()
            return
        self.dashboard_refresh_timer.stop()
        self.status_label.timer.stop()
        super().closeEvent(event)

    def configure_school_year_transition_activation(
        self,
        security_service: object,
    ) -> None:
        """Attach the authenticated product services after security startup."""
        if not self.backup_restore_available:
            raise CipherBackupRestoreUnavailableError()
        step_up = SchoolYearTransitionStepUpService(
            security_service,
            now_provider=lambda: datetime.now(UTC),
        )
        if self.backup_restore_adapter.backup_extension == ".jkmebackup":
            cipher_service = getattr(
                self.backup_restore_adapter.backup_service,
                "service",
                None,
            )
            if cipher_service is None:
                raise RuntimeError("cipher_transition_backup_service_missing")
            backup = VerifiedCipherSchoolYearTransitionBackupAdapter(
                service=cipher_service,
                connection_factory=self.adapter.database.connect,
                target_directory=self.runtime_paths.backups,
                now_provider=lambda: datetime.now(UTC),
            )
        else:
            backup = VerifiedSchoolYearTransitionBackupAdapter(
                service=self.backup_restore_adapter.backup_service,
                command=CreateBackupCommand(
                    database_path=self.runtime_paths.database,
                    runtime_paths=self.runtime_paths,
                    target_path=self.runtime_paths.backups,
                    app_version=self.backup_restore_adapter.app_version,
                    build_commit=self.backup_restore_adapter.build_commit,
                    source_tree_state=(
                        self.backup_restore_adapter.source_tree_state
                    ),
                ),
                now_provider=lambda: datetime.now(UTC),
            )
        self._school_year_transition_step_up = step_up
        self._school_year_transition_executor = ExecuteSchoolYearTransition(
            self.adapter.database.connect,
            maintenance_gate=self.maintenance_gate,
            step_up_service=step_up,
            backup_service=backup,
            now_provider=lambda: datetime.now(UTC),
        )

    def configure_onboarding(
        self,
        *,
        preferences_file: AppPreferencesFile,
        preferences: AppPreferences,
        automatic_open: bool = True,
        packaged_smoke: bool = False,
        pilot_mode: bool | None = None,
    ) -> None:
        """Attach local onboarding persistence after the shell exists."""
        self.onboarding_controller = OnboardingController(
            preferences_file,
            preferences=preferences,
            step_count=ONBOARDING_BASE_STEP_COUNT,
        )
        self.onboarding_screen.pilot_mode = False
        if (
            automatic_open
            and self.onboarding_controller.should_open_automatically(
                packaged_smoke=packaged_smoke
            )
        ):
            QTimer.singleShot(0, self._open_onboarding_automatically)

    def open_onboarding_from_settings(self) -> None:
        self._open_onboarding(manual=True)

    def _handle_screen_activated(self, _index: int) -> None:
        if self.stack.currentWidget() is self.dashboard_screen:
            self.refresh_dashboard()

    def refresh_students(self) -> None:
        """Refresh student rows for the current filter."""
        if self.adapter.current_school_year() is None:
            self.students_screen.set_students(
                (),
                group_filter_name="Aktuelle Zuordnung nicht verfügbar",
                show_back_button=False,
            )
            self.dashboard_screen.set_membership_blocked(
                SCHOOL_YEAR_BLOCK_MESSAGE
            )
            self.status_label.setText(SCHOOL_YEAR_BLOCK_MESSAGE)
            return
        filter_label = "Alle Schüler"
        if self.selected_group_id:
            groups = {group.group_id: group.group_name for group in self.adapter.list_groups()}
            filter_label = (
                "Stammgruppe: "
                f"{groups.get(self.selected_group_id, 'nicht verfügbar')}"
            )
        elif self.selected_course_group_id and self.selected_course_id:
            course_group = self._selected_course_group()
            course_name = self._course_name(self.selected_course_id)
            if course_group is not None:
                filter_label = f"{course_group.name} · {course_name}"
            else:
                filter_label = f"Kurs: {course_name}"
        elif self.selected_course_group_id:
            course_group = self._selected_course_group()
            if course_group is not None:
                filter_label = f"Kursverbund: {course_group.name}"
            else:
                filter_label = "Kursverbund nicht verfügbar"
        elif self.selected_course_id:
            filter_label = f"Kurs: {self._course_name(self.selected_course_id)}"
        try:
            students = self.adapter.list_students(
                group_id=self.selected_group_id,
                course_id=self.selected_course_id,
                course_group_id=self.selected_course_group_id,
            )
        except SchoolYearAssignmentRepositoryError as error:
            message = self._membership_block_message(error)
            self.students_screen.set_students(
                (),
                group_filter_name="Aktuelle Zuordnung nicht verfügbar",
                show_back_button=False,
            )
            self.dashboard_screen.set_membership_blocked(message)
            self.status_label.setText(message)
            return
        self.students_screen.set_students(
            students,
            group_filter_name=filter_label,
            show_back_button=self._has_active_student_filter(),
            show_group_column=self.selected_group_id is None,
        )
        shown_count = len(self.students_screen.filtered_students)
        if self.students_screen.search_text().strip():
            self.status_label.setText(f"{shown_count} von {len(students)} Schülern angezeigt")
        else:
            self.status_label.setText(f"{len(students)} Schüler angezeigt")

    @staticmethod
    def _membership_block_message(
        error: SchoolYearAssignmentRepositoryError,
    ) -> str:
        if error.code == "assignment_ambiguous":
            return ASSIGNMENT_BLOCK_MESSAGE
        return SCHOOL_YEAR_BLOCK_MESSAGE

    def refresh_master_data(self) -> None:
        """Refresh the master-data light screen from the adapter draft."""
        self.master_data_screen.set_master_data(self.master_data_adapter.view_model())
        self.refresh_overview()

    def refresh_settings(self) -> None:
        """Refresh settings from SQLite-backed adapter data."""
        self.settings_screen.set_settings(self.adapter.settings_view_model())
        self.settings_screen.set_timetable(self.timetable_adapter.week_view_model())
        current_school_year = self.adapter.current_school_year()
        self.settings_screen.set_current_school_year(
            (
                current_school_year.label
                if current_school_year is not None
                else None
            ),
            (
                current_school_year.start_date
                if current_school_year is not None
                else None
            ),
            (
                current_school_year.end_date
                if current_school_year is not None
                else None
            ),
        )

    def open_school_year_transition_preview(
        self,
        label: str,
        start_date: date,
        end_date: date,
    ) -> None:
        """Open only the transient plan produced by the read-only service."""
        if self._active_school_year_transition_dialog is not None:
            self._active_school_year_transition_dialog.raise_()
            self._active_school_year_transition_dialog.activateWindow()
            return
        self.settings_screen.clear_school_year_transition_error()
        try:
            plan = SchoolYearTransitionPreviewService(
                self.adapter.database.connect
            ).preview_plan(
                label=label,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception:
            self.settings_screen.show_school_year_transition_error(
                "Die Vorschau konnte mit diesen Angaben nicht erstellt werden."
            )
            return

        if any(
            issue.code in INVALID_TARGET_SCHOOL_YEAR_ISSUES
            for issue in plan.original_validation_issues
        ):
            self.settings_screen.show_school_year_transition_error(
                "Das neue Schuljahr konnte mit diesen Angaben nicht "
                "vorbereitet werden. Bitte Bezeichnung, Beginn und Ende prüfen."
            )
            return

        controller = None
        if (
            self._school_year_transition_step_up is not None
            and self._school_year_transition_executor is not None
        ):
            controller = SchoolYearTransitionActivationController(
                step_up_service=self._school_year_transition_step_up,
                executor=self._school_year_transition_executor,
                parent=self,
            )
            controller.succeeded.connect(lambda _result: self.refresh_all())
            self._active_school_year_transition_controller = controller
        dialog = SchoolYearTransitionPreviewDialog(
            plan,
            self,
            activation_controller=controller,
        )
        self._active_school_year_transition_dialog = dialog
        dialog.finished.connect(self._school_year_transition_preview_finished)
        prepare_maximized_workspace(dialog, self)
        dialog.showMaximized()

    def _school_year_transition_preview_finished(self, _result: int) -> None:
        dialog = self._active_school_year_transition_dialog
        controller = self._active_school_year_transition_controller
        self._active_school_year_transition_dialog = None
        self._active_school_year_transition_controller = None
        if dialog is not None:
            dialog.deleteLater()
        if controller is not None and not controller.is_busy:
            controller.deleteLater()

    def refresh_update_status(self) -> None:
        """Project native update state without exposing Sparkle to the view."""
        self.settings_screen.set_update_status(self.update_service.projection())

    def check_for_updates(self) -> None:
        """Start one explicit supervised check; Sparkle owns the update dialog."""
        projection = self.update_service.check_for_updates()
        self.settings_screen.set_update_status(projection)

    def set_display_name(self, display_name: str | None) -> None:
        """Project the local app profile without owning its persistence."""
        self.display_name = display_name
        self.settings_screen.set_display_name(display_name)
        if self.stack.currentWidget() is self.onboarding_screen:
            self._render_onboarding()
        self.refresh_dashboard()

    def _open_onboarding_automatically(self) -> None:
        self._open_onboarding(manual=False)

    def _open_onboarding(self, *, manual: bool) -> None:
        if self.onboarding_controller is None:
            return
        try:
            session = self.onboarding_controller.start(manual=manual)
        except Exception:
            self.status_label.setText("Erste Schritte konnten nicht geöffnet werden.")
            return
        self._show_onboarding_session(session)

    def _show_onboarding_session(self, session: OnboardingSession) -> None:
        self._render_onboarding(session.current_step)
        self.onboarding_return_button.setVisible(False)
        self._show_screen("onboarding")
        self._clear_navigation_selection()

    def _render_onboarding(self, step: int | None = None) -> None:
        if self.onboarding_controller is None:
            return
        session = self.onboarding_controller.session
        current_step = (
            step
            if step is not None
            else session.current_step if session is not None else 0
        )
        self.onboarding_screen.set_context(
            step=current_step,
            display_name=self.display_name,
            status_projection=self._onboarding_status_projection(),
            pilot_mode=self.onboarding_screen.pilot_mode,
        )

    def _onboarding_status_projection(self) -> OnboardingStatusProjection:
        try:
            week = self.timetable_adapter.week_view_model()
            timetable = any(day.entries for day in week.days)
        except Exception:
            timetable = None
        try:
            master_data = self.master_data_adapter.view_model()
            group = bool(master_data.groups)
            course = bool(master_data.courses)
        except Exception:
            group = None
            course = None
        try:
            children = bool(self.adapter.list_students())
        except Exception:
            children = None
        try:
            backup = (
                None
                if not self.backup_restore_available
                else any(
                    self.runtime_paths.backups.glob(
                        f"*{self.backup_restore_adapter.backup_extension}"
                    )
                )
            )
        except Exception:
            backup = None
        return OnboardingStatusProjection(
            group_configured=group,
            course_configured=course,
            timetable_configured=timetable,
            children_configured=children,
            backup_configured=backup,
        )

    def _onboarding_next(self) -> None:
        if self.onboarding_controller is None:
            return
        try:
            session = self.onboarding_controller.next_step()
        except Exception:
            self.status_label.setText("Erste Schritte konnten nicht gespeichert werden.")
            return
        self._show_onboarding_session(session)

    def _onboarding_back(self) -> None:
        if self.onboarding_controller is None:
            return
        try:
            session = self.onboarding_controller.previous_step()
        except Exception:
            self.status_label.setText("Erste Schritte konnten nicht gespeichert werden.")
            return
        self._show_onboarding_session(session)

    def _onboarding_complete(self) -> None:
        if self.onboarding_controller is None:
            return
        try:
            self.onboarding_controller.complete()
        except Exception:
            self.status_label.setText("Erste Schritte konnten nicht gespeichert werden.")
            return
        self.onboarding_return_button.setVisible(False)
        self._show_screen("dashboard")
        self._select_navigation("dashboard")

    def _onboarding_dismiss(self) -> None:
        if self.onboarding_controller is None:
            return
        try:
            self.onboarding_controller.dismiss()
        except Exception:
            self.status_label.setText("Erste Schritte konnten nicht gespeichert werden.")
            return
        self.onboarding_return_button.setVisible(False)
        self._show_screen("dashboard")
        self._select_navigation("dashboard")

    def _navigate_from_onboarding(self, target: str) -> None:
        if self.onboarding_controller is not None:
            try:
                self.onboarding_controller.mark_navigation()
            except Exception:
                self.status_label.setText(
                    "Der aktuelle Schritt konnte nicht gespeichert werden."
                )
                return
        self.onboarding_return_button.setVisible(True)
        if target == "settings_timetable":
            self._show_settings_page("timetable")
        elif target == "settings_backup_restore":
            self._show_settings_page("backup_restore")
        elif target == "master_data":
            self._show_screen("master_data")
            self._select_navigation("master_data")
        elif target == "students":
            self.return_to_overview()
        else:
            self.status_label.setText("Dieses Ziel ist aktuell nicht verfügbar.")

    def _show_settings_page(self, page_key: str) -> None:
        self._show_screen("settings")
        self.settings_screen.show_page(page_key)
        self._select_navigation("settings")

    def _return_to_onboarding(self) -> None:
        if self.onboarding_controller is None:
            return
        session = self.onboarding_controller.session
        if session is None:
            session = self.onboarding_controller.start(manual=True)
        self._show_onboarding_session(session)

    def create_backup(self) -> None:
        if self._block_unavailable_backup_restore():
            return
        if self.backup_restore_operations.is_busy:
            return
        target = QFileDialog.getExistingDirectory(self, "Backup-Zielordner wählen", str(self.runtime_paths.backups))
        if not target:
            return
        self.backup_restore_operations.start(
            self.backup_restore_adapter.create_backup_operation(Path(target))
        )

    def _load_backup_status(self) -> None:
        if self._block_unavailable_backup_restore():
            return
        if self._backup_status_loaded or self.backup_restore_operations.is_busy:
            return
        self.backup_restore_operations.start(
            self.backup_restore_adapter.discover_verified_backups_operation()
        )

    def verify_backup(self) -> None:
        if self._block_unavailable_backup_restore():
            return
        if self.backup_restore_operations.is_busy:
            return
        extension = self.backup_restore_adapter.backup_extension
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Backup prüfen",
            str(self.runtime_paths.backups),
            f"Jenaplan-Sicherung (*{extension})",
        )
        if not path:
            return
        self.backup_restore_operations.start(
            self.backup_restore_adapter.verify_backup_operation(Path(path))
        )

    def prepare_restore(self) -> None:
        if self._block_unavailable_backup_restore():
            return
        if self.backup_restore_operations.is_busy:
            return
        extension = self.backup_restore_adapter.backup_extension
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sicherung wiederherstellen",
            str(self.runtime_paths.backups),
            f"Jenaplan-Sicherung (*{extension})",
        )
        if not path:
            return
        self._prepared_restore_preview = None
        self._restore_worker_start_attempted = False
        self._restore_confirmed = False
        self.settings_screen.clear_restore_preview()
        self.backup_restore_operations.start(
            self.backup_restore_adapter.verify_restore_operation(Path(path))
        )

    def start_restore(self) -> None:
        if self._block_unavailable_backup_restore():
            return
        if self.backup_restore_operations.is_busy:
            return
        preview: RestorePreviewViewModel | None = self.settings_screen.restore_preview
        if preview is None:
            return
        message, confirm = create_confirmation_message(
            self,
            "Wiederherstellung starten",
            "Der aktuelle lokale Datenbestand wird ersetzt. Vorher wird automatisch ein Sicherheitsbackup erstellt. Nicht gespeicherte Änderungen in geöffneten Arbeitsfenstern werden verworfen. Die App wird anschließend neu gestartet.\n\nWiederherstellung jetzt starten?",
            confirm_text="Wiederherstellen",
        )
        message.exec()
        confirmed = message.clickedButton() is confirm
        message.deleteLater()
        if not confirmed:
            return
        self._restore_confirmed = True
        self._prepared_restore_preview = preview if preview.restore_id else None
        self._restore_worker_start_attempted = False
        operation = (
            self.backup_restore_adapter.verify_prepared_restore_operation(
                preview.restore_id
            )
            if preview.restore_id
            else self.backup_restore_adapter.prepare_restore_operation(
                preview.archive_path
            )
        )
        self.backup_restore_operations.start(operation)

    def _block_unavailable_backup_restore(self) -> bool:
        if self.backup_restore_available:
            return False
        message = "Datensicherung und Wiederherstellung sind noch nicht verfügbar."
        self.settings_screen.show_backup_error(message)
        self.settings_screen.show_restore_error(message)
        return True

    def _handle_backup_restore_state(self, state: str) -> None:
        active = state != "idle"
        self.navigation.setDisabled(active)
        if state == "running":
            self.settings_screen.set_operation_active(
                True,
                "Technischer Vorgang wird vorbereitet …",
            )
        elif state == "finishing":
            self.settings_screen.set_operation_active(
                True,
                "Vorgang wird sicher abgeschlossen …",
            )
        else:
            self.settings_screen.set_operation_active(False)

    def _show_backup_restore_progress(
        self,
        _operation_type: BackupRestoreOperationType,
        phase: BackupRestoreProgressPhase,
    ) -> None:
        messages = {
            BackupRestoreProgressPhase.PREPARING_BACKUP: "Sicherung wird vorbereitet …",
            BackupRestoreProgressPhase.VERIFYING_BACKUP: "Dateien werden geprüft …",
            BackupRestoreProgressPhase.VERIFYING_RESTORE: "Wiederherstellung wird geprüft …",
            BackupRestoreProgressPhase.PREPARING_RESTORE: "Wiederherstellung wird vorbereitet …",
            BackupRestoreProgressPhase.VERIFYING_PREPARED_RESTORE: "Sicherung wird verifiziert …",
            BackupRestoreProgressPhase.PREPARING_SAFETY_BACKUP: "Sicherheitsbackup wird vorbereitet …",
        }
        self.settings_screen.set_operation_active(True, messages[phase])

    def _handle_backup_restore_success(
        self,
        operation_type: BackupRestoreOperationType,
        result: object,
    ) -> None:
        if operation_type is BackupRestoreOperationType.CREATE_BACKUP:
            self._backup_status_loaded = True
            verified = getattr(result, "verification", result)
            self.settings_screen.show_backup_success(
                self.backup_restore_adapter.backup_summary(verified)
            )
            return
        if operation_type is BackupRestoreOperationType.DISCOVER_VERIFIED_BACKUPS:
            self._backup_status_loaded = True
            self.settings_screen.set_backup_status(
                self.backup_restore_adapter.latest_backup_summary(result)
            )
            return
        if operation_type is BackupRestoreOperationType.VERIFY_BACKUP:
            self._backup_status_loaded = True
            self.settings_screen.show_backup_success(
                self.backup_restore_adapter.backup_summary(result),
                verified=True,
            )
            return
        if operation_type is BackupRestoreOperationType.VERIFY_RESTORE_BACKUP:
            self.settings_screen.show_restore_preview(
                self.backup_restore_adapter.restore_preview(result)
            )
            return
        if operation_type is BackupRestoreOperationType.PREPARE_RESTORE_STAGING:
            source_preview = self.settings_screen.restore_preview
            if source_preview is None:
                self._show_restore_workflow_error()
                return
            prepared = self.backup_restore_adapter.staged_restore_preview(
                result,
                source_preview.archive_path,
            )
            self._prepared_restore_preview = prepared
            if not self.backup_restore_operations.start(
                self.backup_restore_adapter.verify_prepared_restore_operation(
                    prepared.restore_id
                )
            ):
                self._show_restore_workflow_error()
            return
        if operation_type is BackupRestoreOperationType.VERIFY_PREPARED_RESTORE:
            prepared = self._prepared_restore_preview
            if prepared is None or prepared.restore_id != result.restore_id:
                self._show_restore_workflow_error()
                return
            self._launch_verified_restore(prepared)

    def _handle_backup_restore_failure(
        self,
        operation_type: BackupRestoreOperationType,
        error_info: BackupRestoreOperationErrorInfo,
    ) -> None:
        if operation_type in {
            BackupRestoreOperationType.VERIFY_RESTORE_BACKUP,
            BackupRestoreOperationType.PREPARE_RESTORE_STAGING,
            BackupRestoreOperationType.VERIFY_PREPARED_RESTORE,
        }:
            self._restore_confirmed = False
        if operation_type is BackupRestoreOperationType.CREATE_BACKUP:
            self.settings_screen.show_backup_error(
                "Die Sicherung konnte nicht erstellt werden."
            )
        elif operation_type is BackupRestoreOperationType.VERIFY_BACKUP:
            messages = {
                "backup_context_mismatch": (
                    "Die Sicherung gehört nicht zu dieser Installation oder "
                    "diesem Datenbestand."
                ),
                "backup_key_unavailable": (
                    "Der benötigte lokale Sicherheitsschlüssel ist nicht verfügbar."
                ),
                "backup_invalid": (
                    "Die Sicherung ist ungültig oder wurde verändert."
                ),
            }
            self.settings_screen.show_backup_error(
                messages.get(
                    error_info.error_code,
                    "Die ausgewählte Sicherung konnte nicht bestätigt werden.",
                )
            )
        elif operation_type is BackupRestoreOperationType.DISCOVER_VERIFIED_BACKUPS:
            self._backup_status_loaded = False
            self.settings_screen.set_backup_status(None, checked=False)
        else:
            messages = {
                "backup_context_mismatch": (
                    "Die Sicherung gehört nicht zu dieser Installation oder "
                    "diesem Datenbestand."
                ),
                "backup_key_unavailable": (
                    "Der benötigte lokale Sicherheitsschlüssel ist nicht verfügbar."
                ),
                "backup_invalid": (
                    "Die Sicherung ist ungültig oder wurde verändert."
                ),
                "restore_staging_failed": (
                    "Die Wiederherstellung konnte nicht sicher vorbereitet werden."
                ),
                "restore_ready_invalid": (
                    "Die vorbereitete Wiederherstellung ist nicht mehr gültig."
                ),
                "restore_safety_backup_failed": (
                    "Das Sicherheitsbackup vor der Wiederherstellung konnte "
                    "nicht erstellt werden."
                ),
            }
            self._show_restore_workflow_error(
                messages.get(error_info.error_code)
            )

    def _launch_verified_restore(self, preview: RestorePreviewViewModel) -> None:
        if self._restore_worker_start_attempted:
            return
        self._restore_worker_start_attempted = True
        try:
            handoff = self.backup_restore_adapter.create_restore_handoff(preview)
            self._restore_worker_process = (
                self.backup_restore_adapter.launch_prepared_restore(handoff)
            )
        except Exception as error:
            code = str(getattr(error, "code", ""))
            message = {
                "worker_handoff_failed": (
                    "Die sichere Übergabe an die Wiederherstellung ist fehlgeschlagen."
                ),
                "worker_takeover_failed": (
                    "Die Wiederherstellung konnte die App nicht sicher übernehmen."
                ),
                "manual_recovery_required": (
                    "Der Datenbestand benötigt eine manuelle Sicherheitswiederherstellung."
                ),
            }.get(code)
            self._show_restore_workflow_error(message)
            return
        self._close_restore_workspaces()
        self._restore_shutdown_in_progress = True
        self.restore_handoff_started.emit()
        application = QApplication.instance()
        if application is None:
            self.close()
        else:
            for widget in application.topLevelWidgets():
                widget.hide()
            QTimer.singleShot(0, self._finish_restore_shutdown)

    def _close_restore_workspaces(self) -> None:
        """Unwind every dialog loop after the explicit restore confirmation."""
        application = QApplication.instance()
        if application is None:
            return
        for widget in tuple(application.topLevelWidgets()):
            if widget is self:
                continue
            if isinstance(widget, QDialog):
                widget.done(QDialog.DialogCode.Rejected)
            else:
                widget.hide()

    def _finish_restore_shutdown(self) -> None:
        """Close the shell normally after nested dialog stacks have unwound."""
        if not self._restore_shutdown_in_progress:
            return
        application = QApplication.instance()
        self.close()
        if application is not None:
            application.quit()

    def _show_restore_workflow_error(self, message: str | None = None) -> None:
        self._prepared_restore_preview = None
        self._restore_confirmed = False
        self.settings_screen.clear_restore_preview()
        self.settings_screen.show_restore_error(
            (message or "Die Wiederherstellung konnte nicht sicher gestartet werden.")
            + " Die App bleibt geöffnet; der lokale Datenbestand wurde nicht ersetzt."
        )

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
        message, confirm = create_confirmation_message(
            self,
            "Stunde löschen",
            "Diesen Stundenplaneintrag wirklich löschen?",
            confirm_text="Stunde löschen",
        )
        message.exec()
        confirmed = message.clickedButton() is confirm
        message.deleteLater()
        if not confirmed:
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
        self.settings_screen.show_page("timetable")
        self._select_navigation("settings")

    def show_student_profile(self, student_id: str) -> None:
        """Open light profile for selected student."""
        active_revision = self._active_learning_report_revision_dialog
        if (
            active_revision is not None
            and self._active_learning_report_revision_student_id
            and self._active_learning_report_revision_student_id != student_id
        ):
            active_revision.reject()
        profile_projection = self.adapter.student_profile_projection_bundle(
            student_id
        )
        report_overview = self.adapter.report_overview_for_student(
            student_id,
            selected_report_draft_id=(
                self._selected_report_draft_ids.get(student_id, "")
            ),
            selected_learning_conference_draft_id=(
                self._selected_learning_conference_draft_ids.get(
                    student_id,
                    "",
                )
            ),
        )
        self.student_profile_screen.set_student(
            profile_projection.student,
            profile_projection.observations,
            profile_projection.competency_groups,
            None,
            profile_projection.documentation_statuses,
            profile_projection.documents,
            profile_projection.competency_cockpit,
            profile_projection.profile_dashboard,
            report_overview,
            profile_projection.documentation_subjects,
        )
        self._show_screen("profile")

    def save_student_documentation_subjects(
        self,
        student_id: str,
        school_year_id: str,
        mode: str,
        subject_ids: tuple[str, ...],
    ) -> None:
        """Save and immediately reload all student-profile projections."""
        try:
            self.adapter.save_student_documentation_subjects(
                student_id,
                school_year_id,
                mode,
                subject_ids,
            )
        except (RuntimeError, ValueError):
            self.student_profile_screen.show_documentation_subjects_error(
                "Die Fächerauswahl konnte nicht gespeichert werden. "
                "Die bisherige Auswahl bleibt erhalten."
            )
            return
        self.show_student_profile(student_id)
        self.status_label.setText(
            "Fächer für die Dokumentation wurden gespeichert."
        )

    def open_new_student_dialog(self) -> None:
        """Open the existing new-student dialog and refresh after success."""
        dialog = NewStudentDialog(self.adapter, self.master_data_adapter)
        dialog.student_created.connect(self.handle_student_created)
        dialog.exec()

    def open_learning_report_dialog(
        self,
        student_id: str,
        report_draft_id: str = "",
        subject_id: str = "",
        workspace_key: str = "",
    ) -> None:
        """Choose an existing report draft or start a deliberate new one."""
        active_dialog = getattr(self, "_active_learning_report_dialog", None)
        if isinstance(active_dialog, QDialog) and active_dialog.isVisible():
            active_dialog.raise_()
            active_dialog.activateWindow()
            return
        try:
            drafts = self.adapter.list_learning_report_drafts_for_student(
                student_id
            )
        except Exception:
            QMessageBox.warning(
                self,
                "Berichtstände nicht lesbar",
                "Die vorhandenen Berichtstände konnten nicht sicher geladen werden. "
                "Es wurde kein Entwurf geöffnet oder verändert.",
            )
            return
        try:
            selected_ui = report_ui_mode()
        except ValueError:
            QMessageBox.warning(
                self,
                "Bericht-Oberfläche nicht verfügbar",
                "Das interne Bericht-Oberflächengate ist ungültig. "
                "Der sichere Qt-Fallback bleibt aktiv.",
            )
            selected_ui = "qt"
        initial_draft = None
        initial_period = None
        if report_draft_id:
            initial_draft = next(
                (
                    draft
                    for draft in drafts
                    if draft.report_draft_id == report_draft_id
                ),
                None,
            )
            if initial_draft is None:
                self.status_label.setText(
                    "Der ausgewählte Berichtsentwurf ist nicht verfügbar."
                )
                return
            self._selected_report_draft_ids[student_id] = report_draft_id
        elif len(drafts) == 1 and selected_ui == "qt":
            initial_draft = next(iter(drafts))
            self._selected_report_draft_ids[student_id] = initial_draft.report_draft_id
        elif drafts:
            accepted, initial_draft = LearningReportDraftSelectionDialog.choose(
                drafts,
                self,
            )
            if not accepted:
                return
            if initial_draft is not None:
                self._selected_report_draft_ids[student_id] = (
                    initial_draft.report_draft_id
                )
                if selected_ui == "qt" and not subject_id and not workspace_key:
                    self.show_student_profile(student_id)
                    return
        if initial_draft is None:
            if selected_ui == "html":
                QMessageBox.information(
                    self,
                    "Qt-Bericht für neuen Entwurf",
                    "Die HTML-Berichtswerkstatt öffnet ausschließlich einen bewusst "
                    "gewählten gespeicherten Entwurf. Ein neuer Entwurf wird im "
                    "unveränderten Qt-Bericht angelegt.",
                )
                selected_ui = "qt"
            self._selected_report_draft_ids.pop(student_id, None)
            current_school_year = self.adapter.current_school_year()
            accepted, initial_period = LearningReportPeriodSelectionDialog.choose(
                self,
                (
                    (current_school_year.start_date, current_school_year.end_date)
                    if current_school_year is not None
                    else None
                ),
            )
            if not accepted or initial_period is None:
                return
        preparation = self.adapter.learning_report_preparation_for_student(
            student_id,
            period_end=(
                initial_draft.period_end
                if initial_draft is not None
                else initial_period[1]
            ),
            retained_competency_ids=(
                initial_draft.competency_ids if initial_draft is not None else ()
            ),
            retained_observation_ids=(
                initial_draft.observation_ids if initial_draft is not None else ()
            ),
            retained_subject_ids=(
                initial_draft.selected_subject_ids
                if initial_draft is not None
                else ()
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
        if selected_ui == "html" and initial_draft is not None:
            self._open_learning_report_html_dialog(
                student_id,
                preparation,
                initial_draft,
                revision_status,
                subject_id=subject_id,
                workspace_key=workspace_key,
            )
            return
        dialog = LearningReportDialog(
            preparation,
            self,
            initial_draft,
            revision_status,
            initial_period,
        )
        if subject_id:
            dialog.focus_evidence_subject(subject_id)
        elif workspace_key:
            dialog.show_workspace(workspace_key)

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
                dialog.show_save_error(str(error))
                return None
            dialog.apply_saved_draft(saved)
            self._selected_report_draft_ids[student_id] = saved.report_draft_id
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
            self.open_learning_report_revision(
                learning_report_revision_id,
                dialog,
            )

        dialog.save_requested.connect(save_draft)
        dialog.finalization_requested.connect(request_finalization)
        dialog.finalize_confirmed.connect(finalize_report)
        dialog.revision_open_requested.connect(open_revision)
        dialog.pdf_requested.connect(
            lambda output_model: self.export_learning_report_pdf(
                output_model,
                parent=dialog,
            )
        )
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._active_learning_report_dialog = dialog

        def clear_active_report(*_args: object) -> None:
            if self._active_learning_report_dialog is dialog:
                self._active_learning_report_dialog = None

        def finish_report_workspace(*_args: object) -> None:
            clear_active_report()
            self.show_student_profile(student_id)

        dialog.finished.connect(finish_report_workspace)
        dialog.destroyed.connect(clear_active_report)
        open_maximized_workspace(dialog, self)

    def _open_learning_report_html_dialog(
        self,
        student_id: str,
        preparation: object,
        initial_draft: object,
        revision_status: object,
        *,
        subject_id: str = "",
        workspace_key: str = "",
    ) -> None:
        """Compose one persisted RPD with the gated report-only HTML host."""
        from src.desktop_app.report_html.bridge import (
            LearningReportHtmlBridge,
            LearningReportHtmlSession,
        )
        from src.desktop_app.report_html.host import LearningReportHtmlDialog

        artifacts = {}
        if revision_status is not None:
            for revision in revision_status.history:
                try:
                    artifact = self.adapter.load_learning_report_pdf_artifact(
                        revision.learning_report_revision_id
                    )
                except Exception:
                    artifact = None
                if artifact is not None:
                    artifacts[revision.learning_report_revision_id] = artifact

        def save_draft(value: object):
            saved = self.adapter.save_learning_report_draft(value)
            self._selected_report_draft_ids[student_id] = saved.report_draft_id
            self.status_label.setText("Lernentwicklungsbericht-Entwurf gespeichert.")
            return saved

        def finalize_report(report_draft_id: str, display_name: str):
            status = self.adapter.finalize_learning_report(report_draft_id, display_name)
            self.status_label.setText(
                f"Berichtrevision {status.current_revision_number} finalisiert."
            )
            return status

        session = LearningReportHtmlSession(
            preparation=preparation,
            draft=initial_draft,
            revision_status=revision_status,
            artifacts_by_revision_id=artifacts,
            save_draft=save_draft,
            prepare_finalization=self.adapter.prepare_learning_report_finalization,
            finalize_report=finalize_report,
            finalization_error_message=self.adapter.learning_report_finalization_error_message,
            refresh_revision_status=self.adapter.learning_report_revision_status,
            load_revision=self.adapter.load_learning_report_revision,
            load_final_artifact=self.adapter.load_learning_report_pdf_artifact,
            show_final_pdf=None,
        )
        bridge = LearningReportHtmlBridge(session)
        dialog = LearningReportHtmlDialog(bridge, self)
        session.show_final_pdf = lambda artifact_id: self._open_final_pdf_artifact(
            artifact_id,
            parent=dialog,
        )
        target_workspace = (
            "evidence"
            if subject_id
            else {
                "writing": "writing",
                "evidence": "evidence",
                "preview": "preview",
                "revisions": "revisions",
            }.get(workspace_key, "writing")
        )
        dialog.loaded.connect(
            lambda ok: dialog.page.runJavaScript(f"show('{target_workspace}')")
            if ok
            else None
        )
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._active_learning_report_dialog = dialog
        finished = False

        def clear_active(*_args: object) -> None:
            if self._active_learning_report_dialog is dialog:
                self._active_learning_report_dialog = None

        def finish(*_args: object) -> None:
            nonlocal finished
            if finished:
                return
            finished = True
            clear_active()
            self.show_student_profile(student_id)

        dialog.finished.connect(finish)
        dialog.destroyed.connect(clear_active)
        open_maximized_workspace(dialog, self)

    def open_learning_report_revision(
        self,
        learning_report_revision_id: str,
        parent: QWidget | None = None,
    ) -> None:
        """Open one immutable report revision from any existing navigation."""
        active_dialog = self._active_learning_report_revision_dialog
        if active_dialog is not None and active_dialog.isVisible():
            active_dialog.raise_()
            active_dialog.activateWindow()
            return
        dialog_parent = parent or self
        try:
            revision = self.adapter.load_learning_report_revision(
                learning_report_revision_id
            )
        except ReportFinalizationError:
            QMessageBox.warning(
                dialog_parent,
                "Finale Fassung konnte nicht geöffnet werden",
                "Der gespeicherte Snapshot konnte nicht verifiziert werden. "
                "Aktuelle Schüler- oder Berichtsdaten wurden nicht als Ersatz geladen.",
            )
            return
        except Exception:
            QMessageBox.warning(
                dialog_parent,
                "Finale Fassung konnte nicht geöffnet werden",
                "Ein unerwarteter technischer Fehler ist aufgetreten.",
            )
            return
        if revision is None:
            QMessageBox.warning(
                dialog_parent,
                "Finale Fassung konnte nicht geöffnet werden",
                "Die ausgewählte Berichtrevision ist nicht verfügbar.",
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
            dialog_parent,
            artifact,
        )
        revision_dialog.setAttribute(
            Qt.WidgetAttribute.WA_DeleteOnClose,
            True,
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
        revision_dialog.pdf_open_requested.connect(
            lambda artifact_id: self._open_final_pdf_artifact(
                artifact_id,
                parent=revision_dialog,
            )
        )
        self._active_learning_report_revision_id = (
            revision.learning_report_revision_id
        )
        self._active_learning_report_revision_student_id = (
            dialog_parent.preparation.student_id
            if isinstance(dialog_parent, LearningReportDialog)
            else (
                self.student_profile_screen.current_student.student_id
                if self.student_profile_screen.current_student is not None
                else ""
            )
        )
        self._active_learning_report_revision_dialog = revision_dialog

        def clear_revision_mode(*_args: object) -> None:
            if self._active_learning_report_revision_dialog is revision_dialog:
                self._active_learning_report_revision_id = ""
                self._active_learning_report_revision_student_id = ""
                self._active_learning_report_revision_dialog = None

        def finish_revision_mode(*_args: object) -> None:
            clear_revision_mode()
            revision_dialog.deleteLater()

        revision_dialog.finished.connect(finish_revision_mode)
        revision_dialog.destroyed.connect(clear_revision_mode)
        revision_dialog.open()

    def open_learning_conference_dialog(
        self,
        student_id: str,
        learning_conference_draft_id: str = "",
    ) -> None:
        """Choose an existing LEG draft or start an independent new one."""
        try:
            drafts = self.adapter.list_learning_conference_drafts_for_student(
                student_id
            )
        except Exception:
            QMessageBox.warning(
                self,
                "LEG-Stände nicht lesbar",
                "Die vorhandenen LEG-Stände konnten nicht sicher geladen werden. "
                "Es wurde kein Arbeitsstand geöffnet oder verändert.",
            )
            return
        initial_draft = None
        if learning_conference_draft_id:
            initial_draft = next(
                (
                    draft
                    for draft in drafts
                    if draft.learning_conference_draft_id
                    == learning_conference_draft_id
                ),
                None,
            )
            if initial_draft is None:
                self.status_label.setText(
                    "Der ausgewählte LEG-Arbeitsstand ist nicht verfügbar."
                )
                return
            self._selected_learning_conference_draft_ids[student_id] = (
                learning_conference_draft_id
            )
        elif drafts:
            accepted, initial_draft = LearningConferenceDraftSelectionDialog.choose(
                drafts,
                self,
            )
            if not accepted:
                return
            if initial_draft is not None:
                self._selected_learning_conference_draft_ids[student_id] = (
                    initial_draft.learning_conference_draft_id
                )
        else:
            self._selected_learning_conference_draft_ids.pop(student_id, None)
        preparation = self.adapter.learning_conference_preparation_for_student(
            student_id,
            conference_date=(
                initial_draft.conference_date
                if initial_draft is not None
                else None
            ),
            retained_competency_ids=(
                initial_draft.competency_ids if initial_draft is not None else ()
            ),
        )
        if preparation is None:
            self.status_label.setText("Schülerprofil wurde nicht gefunden.")
            return
        draft_lock_key = (
            initial_draft.learning_conference_draft_id
            if initial_draft is not None
            else f"new:{student_id}"
        )
        active_student_ids = getattr(
            self,
            "_active_learning_conference_student_ids",
            set(),
        )
        if student_id in active_student_ids:
            self.status_label.setText(
                "Dieser LEG-Arbeitsstand ist bereits geöffnet."
            )
            return
        try:
            selected_ui = leg_ui_mode()
        except ValueError:
            QMessageBox.warning(
                self,
                "LEG-Oberfläche nicht verfügbar",
                "Das interne LEG-Oberflächengate ist ungültig. "
                "Der sichere Qt-Fallback bleibt aktiv.",
            )
            selected_ui = "qt"
        if selected_ui == "html":
            active_student_ids.add(student_id)
            try:
                self._open_learning_conference_html_dialog(
                    student_id,
                    preparation,
                    initial_draft,
                    draft_lock_key,
                )
            finally:
                active_student_ids.discard(student_id)
            self.show_student_profile(student_id)
            return
        dialog = LearningConferenceDialog(preparation, self, initial_draft)
        dialog.setProperty("learningConferenceDraftKey", draft_lock_key)

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
            self._selected_learning_conference_draft_ids[student_id] = (
                saved.learning_conference_draft_id
            )
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
            self.open_learning_conference_revision(
                learning_conference_revision_id,
                dialog,
            )

        dialog.save_requested.connect(save_draft)
        dialog.completion_requested.connect(complete_conference)
        dialog.revision_open_requested.connect(open_revision)
        refresh_revision_status()
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._active_learning_conference_dialog = dialog
        active_student_ids.add(student_id)

        def clear_active_learning_conference(*_args: object) -> None:
            if self._active_learning_conference_dialog is dialog:
                self._active_learning_conference_dialog = None
            active_student_ids.discard(student_id)

        def finish_learning_conference_workspace(*_args: object) -> None:
            clear_active_learning_conference()
            self.show_student_profile(student_id)

        dialog.finished.connect(finish_learning_conference_workspace)
        dialog.destroyed.connect(clear_active_learning_conference)
        open_maximized_workspace(dialog, self)

    def _open_learning_conference_html_dialog(
        self,
        student_id: str,
        preparation: LearningConferencePreparationViewModel,
        initial_draft: LearningConferenceDraftViewModel | None,
        draft_lock_key: str,
    ) -> None:
        """Compose the gated LEG-only WebEngine host without importing it on Qt."""
        from src.desktop_app.leg_html.bridge import (
            LearningConferenceHtmlBridge,
            LearningConferenceHtmlSession,
        )
        from src.desktop_app.leg_html.host import LearningConferenceHtmlDialog

        draft = initial_draft or LearningConferenceDraftViewModel(
            student_id=student_id,
            conference_date=date.today(),
        )
        revision_status = None
        artifacts = {}
        if draft.learning_conference_draft_id:
            try:
                revision_status = self.adapter.learning_conference_revision_status(
                    draft.learning_conference_draft_id
                )
            except Exception:
                revision_status = None
        if revision_status is not None:
            for revision in revision_status.revisions:
                try:
                    artifact = self.adapter.load_learning_conference_pdf_artifact(
                        revision.learning_conference_revision_id
                    )
                except Exception:
                    artifact = None
                if artifact is not None:
                    artifacts[revision.learning_conference_revision_id] = artifact

        def save_draft(
            value: LearningConferenceDraftViewModel,
        ) -> LearningConferenceDraftViewModel:
            saved = self.adapter.save_learning_conference_draft(value)
            self._selected_learning_conference_draft_ids[student_id] = (
                saved.learning_conference_draft_id
            )
            self.status_label.setText(
                "Lernentwicklungsgespräch-Entwurf gespeichert."
            )
            return saved

        def complete_conference(
            learning_conference_draft_id: str,
        ) -> LearningConferenceRevisionStatusViewModel:
            status = self.adapter.complete_learning_conference(
                learning_conference_draft_id
            )
            self.status_label.setText("Lernentwicklungsgespräch abgeschlossen.")
            return status

        session = LearningConferenceHtmlSession(
            preparation=preparation,
            draft=draft,
            revision_status=revision_status,
            artifacts_by_revision_id=artifacts,
            save_draft=save_draft,
            complete_conference=complete_conference,
            refresh_revision_status=self.adapter.learning_conference_revision_status,
            load_final_artifact=self.adapter.load_learning_conference_pdf_artifact,
            open_revision=None,
            show_final_pdf=None,
        )
        bridge = LearningConferenceHtmlBridge(session)
        dialog = LearningConferenceHtmlDialog(bridge, self)
        session.open_revision = lambda revision_id: self.open_learning_conference_revision(
            revision_id,
            dialog,
        )
        session.show_final_pdf = lambda artifact_id: self._open_final_pdf_artifact(
            artifact_id,
            parent=dialog,
        )
        dialog.setProperty("learningConferenceDraftKey", draft_lock_key)
        exec_maximized_workspace(dialog, self)

    def open_learning_conference_revision(
        self,
        learning_conference_revision_id: str,
        parent: QWidget | None = None,
    ) -> None:
        """Open one immutable LEG revision from any existing navigation."""
        dialog_parent = parent or self
        try:
            revision = self.adapter.load_learning_conference_revision(
                learning_conference_revision_id
            )
        except LearningConferenceCompletionError as error:
            visible = build_learning_conference_completion_error(error)
            QMessageBox.warning(
                dialog_parent,
                "LEG-Abschluss konnte nicht geöffnet werden",
                visible.message,
            )
            return
        except Exception:
            QMessageBox.warning(
                dialog_parent,
                "LEG-Abschluss konnte nicht geöffnet werden",
                "Ein unerwarteter technischer Fehler ist aufgetreten.",
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
            dialog_parent,
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
        revision_dialog.pdf_open_requested.connect(
            lambda artifact_id: self._open_final_pdf_artifact(
                artifact_id,
                parent=revision_dialog,
            )
        )
        revision_dialog.exec()

    def _open_final_pdf_artifact(
        self,
        artifact_id: str,
        *,
        parent: QWidget,
    ) -> None:
        """Read one opaque RPA/LCA identity into the shared in-memory viewer."""
        active = self._active_pdf_viewer_dialog
        if active is not None and isValid(active):
            active.close()

        consumer = PdfArtifactBufferConsumer()
        try:
            self.adapter.read_final_pdf_artifact(
                artifact_id=artifact_id,
                consumer=consumer,
            )
            pdf_bytes = consumer.take()
            viewer = PdfArtifactViewerDialog(
                pdf_bytes=pdf_bytes,
                parent=parent,
            )
            del pdf_bytes
        except Exception as error:
            consumer.clear()
            QMessageBox.warning(
                parent,
                "PDF konnte nicht geöffnet werden",
                self.adapter.final_pdf_artifact_error_message(error),
            )
            return

        viewer.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._active_pdf_viewer_dialog = viewer

        def clear_pdf_viewer(*_args: object) -> None:
            if self._active_pdf_viewer_dialog is viewer:
                self._active_pdf_viewer_dialog = None

        viewer.finished.connect(clear_pdf_viewer)
        viewer.destroyed.connect(clear_pdf_viewer)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(viewer.close)
        viewer.open()

    def export_competency_overview_pdf(self, student_id: str, subject_id: str = "") -> None:
        """Choose an explicit external cleartext export; keep domain work outside Qt."""
        confirmation = QMessageBox.question(
            self,
            "Kompetenzen als PDF exportieren",
            "Das PDF enthält den Namen und die bestätigten Entwicklungsstände des Kindes. "
            "Es wird außerhalb der App unverschlüsselt gespeichert. Möchtest du es exportieren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return
        target, _filter = QFileDialog.getSaveFileName(
            self, "Kompetenzübersicht als PDF speichern",
            str(Path.home() / "Downloads" / "Kompetenzuebersicht.pdf"),
            "PDF-Datei (*.pdf)", options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not target:
            return
        if not Path(target).suffix:
            target += ".pdf"
        try:
            from src.application.competency_pdf_export import export_competency_pdf

            with self.maintenance_gate.begin_writer():
                model = self.adapter.competency_pdf_for_student(student_id, subject_id)
                exported = export_competency_pdf(
                    model, Path(target), runtime_root=self.runtime_paths.root,
                )
        except FileExistsError:
            QMessageBox.warning(self, "PDF nicht exportiert",
                                "Die Datei existiert bereits. Bitte einen neuen Dateinamen wählen.")
            return
        except Exception:
            QMessageBox.warning(self, "PDF nicht exportiert",
                                "Der Export konnte nicht sicher abgeschlossen werden. "
                                "Bitte Fachauswahl und Zielordner prüfen.")
            return
        self.status_label.setText(f"Kompetenzübersicht exportiert: {exported.name}")

    def export_learning_report_pdf(
        self,
        output_model: object,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """Hand a complete neutral output model to the unchanged PDF renderer."""
        dialog_parent = parent or self
        metadata = getattr(output_model, "metadata", None)
        student_name = str(getattr(metadata, "student_name", "Lernentwicklungsbericht"))
        safe_name = "_".join(student_name.split()) or "Lernentwicklungsbericht"
        target_path, _selected_filter = QFileDialog.getSaveFileName(
            dialog_parent,
            "Lernentwicklungsbericht als PDF speichern",
            str(self.exports_directory / f"Lernentwicklungsbericht_{safe_name}.pdf"),
            "PDF-Datei (*.pdf)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not target_path:
            return
        try:
            from prototypes.pdf_engine.renderer import PdfRenderer

            rendered_path = PdfRenderer().render(output_model, Path(target_path))
        except Exception as error:  # pragma: no cover - platform/reportlab feedback
            QMessageBox.warning(
                dialog_parent,
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

    def _open_observation_shortcut(self) -> None:
        if (
            not self.isEnabled()
            or QApplication.activeWindow() is not self
            or QApplication.activeModalWidget() is not None
            or QApplication.activePopupWidget() is not None
        ):
            return
        if self.stack.currentWidget() is self.student_profile_screen:
            current = self.student_profile_screen.current_student
            if current is not None:
                student = self.adapter.get_student_profile(current.student_id)
                if student is not None:
                    self.open_new_observation_dialog(student)
                    return
        elif (
            self.stack.currentWidget() is self.students_workspace
            and self.students_workspace.current_content_key() in {"all", "filtered_students"}
        ):
            student_id = self.students_screen.selected_student_id()
            if student_id is not None:
                self.open_quick_observation_dialog(student_id)
                return
        self.show_all_students()
        self.students_screen.search_input.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.status_label.setText(
            "Wähle ein Kind und öffne „Beobachten“ oder drücke erneut das Kürzel."
        )

    def open_new_observation_dialog(self, student: StudentDetailViewModel) -> None:
        """Open the persistent observation dialog and refresh after success."""
        if student.resolution_status != "enrolled" or not student.active:
            self.status_label.setText(
                student.status_label
                or "Für dieses Kind kann aktuell keine Beobachtung erfasst werden."
            )
            return
        prefill = self._pending_timetable_observation_draft(student)
        dialog = NewObservationDialog(
            student,
            self.curriculum_adapter,
            self.adapter,
            subject_options=(
                self.adapter.list_observation_subject_options(
                    student.student_id,
                    prefill,
                )
                if prefill is not None
                else self.adapter.list_observation_subject_options(
                    student.student_id
                )
            ),
            competency_subject_groups=(
                self.adapter.list_observation_competency_subject_groups(
                    student.student_id,
                    prefill,
                )
                if prefill is not None
                else self.adapter.list_observation_competency_subject_groups(
                    student.student_id
                )
            ),
            recent_competencies=self.adapter.list_recent_observation_competencies(
                student.student_id,
                prefill,
            ),
            prefill_subject_id=self.pending_observation_subject_id,
            prefill_context=prefill.context if prefill is not None else "",
            parent=self,
        )
        self._clear_pending_timetable_observation()
        if exec_maximized_workspace(dialog, self) or dialog.has_saved_observation is True:
            self.show_student_profile(student.student_id)
            self.status_label.setText("Beobachtung wurde gespeichert.")

    def open_quick_observation_dialog(self, student_id: str) -> None:
        """Open the observation dialog from a student list row."""
        student = self.adapter.get_student_profile(student_id)
        if student is None:
            self.status_label.setText("Schülerprofil wurde nicht gefunden.")
            return
        if student.resolution_status != "enrolled" or not student.active:
            self.status_label.setText(
                student.status_label
                or "Für dieses Kind kann aktuell keine Beobachtung erfasst werden."
            )
            return
        prefill = self._pending_timetable_observation_draft(student)
        dialog = NewObservationDialog(
            student,
            self.curriculum_adapter,
            self.adapter,
            subject_options=(
                self.adapter.list_observation_subject_options(
                    student.student_id,
                    prefill,
                )
                if prefill is not None
                else self.adapter.list_observation_subject_options(
                    student.student_id
                )
            ),
            competency_subject_groups=(
                self.adapter.list_observation_competency_subject_groups(
                    student.student_id,
                    prefill,
                )
                if prefill is not None
                else self.adapter.list_observation_competency_subject_groups(
                    student.student_id
                )
            ),
            recent_competencies=self.adapter.list_recent_observation_competencies(
                student.student_id,
                prefill,
            ),
            prefill_subject_id=self.pending_observation_subject_id,
            prefill_context=prefill.context if prefill is not None else "",
            parent=self,
        )
        self._clear_pending_timetable_observation()
        if exec_maximized_workspace(dialog, self) or dialog.has_saved_observation is True:
            self.refresh_overview()
            self.refresh_students()
            self.status_label.setText("Beobachtung wurde gespeichert.")

    def open_edit_observation_dialog(self, observation_id: str) -> None:
        """Open the observation dialog with persisted observation data."""
        draft = self.adapter.observation_draft_for_edit(observation_id)
        if draft is None:
            self.status_label.setText("Beobachtung wurde nicht gefunden.")
            return
        try:
            reference_date = date.fromisoformat(draft.date_text)
        except ValueError:
            self.status_label.setText(
                "Das Beobachtungsdatum ist ungültig; "
                "die Zuordnung kann nicht sicher angezeigt werden."
            )
            return
        student = self.adapter.get_student_profile(
            draft.student_id,
            reference_date=reference_date,
        )
        if student is None:
            self.status_label.setText("Schülerprofil wurde nicht gefunden.")
            return
        dialog = NewObservationDialog(
            student,
            self.curriculum_adapter,
            self.adapter,
            initial_draft=draft,
            subject_options=self.adapter.list_observation_subject_options(
                student.student_id,
                draft,
            ),
            competency_subject_groups=(
                self.adapter.list_observation_competency_subject_groups(
                    student.student_id,
                    draft,
                )
            ),
            recent_competencies=self.adapter.list_recent_observation_competencies(
                student.student_id,
                draft,
            ),
            parent=self,
        )
        if exec_maximized_workspace(dialog, self):
            self.show_student_profile(student.student_id)
            self.status_label.setText("Beobachtung wurde aktualisiert.")

    def delete_observation(self, observation_id: str) -> None:
        """Soft-delete an observation and refresh the current profile."""
        draft = self.adapter.observation_draft_for_edit(observation_id)
        if draft is None:
            self.status_label.setText("Beobachtung wurde nicht gefunden.")
            return
        message, confirm = create_confirmation_message(
            self,
            "Beobachtung löschen",
            "Diese Beobachtung aus dem Profil ausblenden?",
            confirm_text="Beobachtung löschen",
        )
        message.exec()
        confirmed = message.clickedButton() is confirm
        message.deleteLater()
        if not confirmed:
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
            except Exception as error:
                QMessageBox.warning(self, "Dokumente & Medien", str(error))
                return
        self.show_student_profile(student_id)
        self.status_label.setText("Dokumente & Medien wurden gespeichert.")

    def remove_student_document(self, student_id: str, document_id: str) -> None:
        """Soft-delete one student document after confirmation."""
        message, confirm = create_confirmation_message(
            self,
            "Datei entfernen",
            "Diese Datei aus dem Schülerprofil entfernen? "
            "Die Datei bleibt im Dateisystem erhalten.",
            confirm_text="Datei entfernen",
        )
        message.exec()
        confirmed = message.clickedButton() is confirm
        message.deleteLater()
        if not confirmed:
            return
        try:
            self.adapter.remove_document(document_id)
        except Exception as error:
            QMessageBox.warning(self, "Dokumente & Medien", str(error))
            return
        self.show_student_profile(student_id)
        self.status_label.setText("Datei wurde entfernt.")

    def replace_student_document(self, student_id: str, document_id: str) -> None:
        """Replace one encrypted managed document through the adapter."""
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Datei ersetzen",
            "",
            "Alle Dateien (*)",
        )
        if not file_path:
            return
        try:
            self.adapter.replace_student_document(
                document_id=document_id,
                source_path=Path(file_path),
            )
        except Exception as error:
            QMessageBox.warning(self, "Dokumente & Medien", str(error))
            return
        self.show_student_profile(student_id)
        self.status_label.setText("Datei wurde ersetzt.")

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
        dialog = MasterDataNameDialog(
            "Neuer Kurs",
            include_color=True,
            include_year_level=True,
        )
        if dialog.exec():
            self.master_data_adapter.add_course(
                dialog.name(),
                dialog.color_hex(),
                dialog.year_level(),
            )
            self.refresh_master_data()
            self.status_label.setText("Kurs wurde gespeichert.")

    def open_rename_group_dialog(self, group_id: str) -> None:
        """Open the persistent rename dialog for a group."""
        item = self.master_data_adapter.groups[group_id]
        dialog = MasterDataNameDialog(
            "Stammgruppe bearbeiten",
            item.name,
            include_active=True,
            initial_active=item.is_active,
        )
        if dialog.exec():
            try:
                self.master_data_adapter.rename_group(
                    group_id,
                    dialog.name(),
                    active=dialog.is_active(),
                    as_of=self.adapter.operation_date(),
                )
            except ValueError as error:
                QMessageBox.warning(self, "Stammgruppe", str(error))
                return
            self.refresh_master_data()
            self.status_label.setText("Stammgruppe wurde gespeichert.")

    def open_rename_course_dialog(self, course_id: str) -> None:
        """Open the persistent rename dialog for a course."""
        item = self.master_data_adapter.courses[course_id]
        dialog = MasterDataNameDialog(
            "Kurs bearbeiten",
            item.name,
            include_color=True,
            initial_color_hex=item.color_hex,
            include_year_level=True,
            initial_year_level=item.year_level,
            include_active=True,
            initial_active=item.is_active,
        )
        if dialog.exec():
            try:
                self.master_data_adapter.rename_course(
                    course_id,
                    dialog.name(),
                    dialog.color_hex(),
                    year_level=dialog.year_level(),
                    active=dialog.is_active(),
                    as_of=self.adapter.operation_date(),
                )
            except ValueError as error:
                QMessageBox.warning(self, "Kurs", str(error))
                return
            self.refresh_master_data()
            self.status_label.setText("Kurs wurde gespeichert.")

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
        # A mouse selection changes the row on press and emits itemClicked on
        # release. Pointer navigation therefore dispatches from itemClicked;
        # keyboard and programmatic row changes continue through this path.
        if QGuiApplication.mouseButtons() != Qt.MouseButton.NoButton:
            return
        self._show_navigation_item(self.navigation.item(index))

    def _show_navigation_item(self, item: QListWidgetItem) -> None:
        if self.backup_restore_operations.is_busy:
            return
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
        if target.screen_key == "settings":
            self.settings_screen.reset_navigation()

    def _selected_course_group(self) -> CourseGroupViewModel | None:
        for course_group in self.master_data_adapter.view_model().course_groups:
            if course_group.course_group_id == self.selected_course_group_id:
                return course_group
        return None

    def _course_name(self, course_id: str) -> str:
        for course in self.master_data_adapter.view_model().courses:
            if course.item_id == course_id:
                return course.name
        return "Kurs nicht verfügbar"

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

    def _clear_navigation_selection(self) -> None:
        self.navigation.blockSignals(True)
        self.navigation.clearSelection()
        self.navigation.setCurrentRow(-1)
        self.navigation.blockSignals(False)
