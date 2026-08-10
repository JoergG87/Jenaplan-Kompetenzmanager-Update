"""Light student profile screen for the PySide6 desktop app."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import (
    QCoreApplication,
    QEvent,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.components import (
    AppCard,
    CourseBadge,
    EmptyState,
    FilterBar,
    InlineMessage,
    PageHeader,
    SearchField,
    SectionHeader,
    SegmentedControl,
    StatusBadge,
    configure_button,
)
from src.desktop_app.icons import load_icon
from src.desktop_app.motion import animate_feedback, install_card_motion

from src.desktop_app.view_models.student_view_model import (
    PROFILE_ACTION_MESSAGES,
    PROFILE_SECTION_PLACEHOLDERS,
    REPORT_NO_OBSERVATIONS_MESSAGE,
    StudentDetailViewModel,
    StudentDocumentViewModel,
    StudentProfileDashboardViewModel,
    StudentDocumentationSubjectProjectionViewModel,
    StudentProfileOrientationChangeViewModel,
    StudentReportPreviewViewModel,
    empty_student_profile_dashboard,
    format_student_report_preview_text,
)
from src.desktop_app.view_models.report_overview_view_model import (
    LearningConferenceStatusCardViewModel,
    ReportHistoryItemViewModel,
    ReportNextStepViewModel,
    ReportOverviewActionViewModel,
    ReportOverviewSubjectDocumentationViewModel,
    ReportOverviewTimelineEventViewModel,
    ReportOverviewViewModel,
    ReportStatusCardViewModel,
    empty_report_overview,
)
from src.desktop_app.view_models.observation_view_model import (
    ObservationListItem,
    StudentCompetencyCockpitLearningAreaViewModel,
    StudentCompetencyCockpitSubjectViewModel,
    StudentCompetencyCockpitTopicViewModel,
    StudentCompetencyCockpitViewModel,
    StudentDocumentationSubjectStatus,
    StudentCompetencySubjectGroup,
)
from src.desktop_app.theme import COLOR_NAVY, COLOR_TURQUOISE, set_label_style


REPORT_SUBJECT_SYMBOLS = {
    "deutsch": "Aa",
    "german": "Aa",
    "mathematik": "∑",
    "math": "∑",
    "epu": "⌁",
    "musik": "♫",
    "kunst": "◈",
    "sport": "●",
    "sozialkompetenz": "◎",
    "ethik": "⚖",
    "religion": "✦",
    "werken": "⌘",
    "schulgarten": "♧",
}


class DocumentationRing(QWidget):
    """Neutral documentation coverage ring without performance semantics."""

    def __init__(self, diameter: int = 64) -> None:
        super().__init__()
        self._documented = 0
        self._total = 0
        self.setFixedSize(diameter, diameter)
        self.setObjectName("StudentProfileDocumentationRing")
        self.set_counts(0, 0)

    def set_counts(self, documented: int, total: int) -> None:
        self._documented = max(0, documented)
        self._total = max(0, total)
        self.setAccessibleName(
            f"Dokumentiert: {self._documented} von {self._total} Lernbereichen"
        )
        self.update()

    def paintEvent(self, _event: object) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ring = QRectF(6, 6, self.width() - 12, self.height() - 12)
        painter.setPen(QPen(
            QColor("#DFE8EA"),
            6,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        ))
        painter.drawArc(ring, 0, 360 * 16)
        if self._total:
            span = int(360 * 16 * min(1.0, self._documented / self._total))
            painter.setPen(QPen(
                QColor(COLOR_TURQUOISE),
                6,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            ))
            painter.drawArc(ring, 90 * 16, -span)
        painter.setPen(QColor(COLOR_NAVY))
        painter.drawText(
            ring,
            Qt.AlignmentFlag.AlignCenter,
            f"{self._documented}/{self._total}",
        )


class ReportTimelineScrollArea(QScrollArea):
    """Horizontal timeline viewport with keyboard and trackpad support."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ReportOverviewTimelineScrollArea")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(
            "Dokumentations-Timeline horizontal scrollen"
        )

    def wheelEvent(self, event: object) -> None:  # noqa: N802 - Qt API
        pixel_delta = event.pixelDelta()
        angle_delta = event.angleDelta()
        horizontal_delta = pixel_delta.x() or angle_delta.x()
        shifted_vertical_delta = (
            pixel_delta.y() or angle_delta.y()
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            else 0
        )
        delta = horizontal_delta or shifted_vertical_delta
        if delta:
            bar = self.horizontalScrollBar()
            bar.setValue(bar.value() - delta)
            event.accept()
            return
        # Ordinary vertical scrolling belongs to the outer profile viewport.
        event.ignore()

    def keyPressEvent(self, event: object) -> None:  # noqa: N802 - Qt API
        bar = self.horizontalScrollBar()
        step = max(40, bar.pageStep() // 2)
        if event.key() == Qt.Key.Key_Left:
            bar.setValue(bar.value() - step)
        elif event.key() == Qt.Key.Key_Right:
            bar.setValue(bar.value() + step)
        elif event.key() == Qt.Key.Key_Home:
            bar.setValue(bar.minimum())
        elif event.key() == Qt.Key.Key_End:
            bar.setValue(bar.maximum())
        else:
            super().keyPressEvent(event)
            return
        event.accept()


class StudentProfileScreen(QWidget):
    student_edit_requested = Signal(str)
    """Lightweight read-only student profile."""

    DEFAULT_OBSERVATION_LIMIT = 3

    back_requested = Signal()
    observation_requested = Signal(object)
    observation_edit_requested = Signal(str)
    observation_delete_requested = Signal(str)
    document_add_requested = Signal(str)
    document_replace_requested = Signal(str, str)
    document_remove_requested = Signal(str, str)
    competency_confirmation_requested = Signal(str, str, str, str)
    documentation_subjects_save_requested = Signal(str, str, str, tuple)
    report_requested = Signal(str)
    learning_conference_requested = Signal(str)
    report_draft_requested = Signal(str, str, str, str)
    learning_conference_draft_requested = Signal(str, str)
    report_revision_requested = Signal(str)
    learning_conference_revision_requested = Signal(str)

    def __init__(self, export_directory: Path | None = None) -> None:
        super().__init__()
        self.export_directory = export_directory
        self.current_student: StudentDetailViewModel | None = None
        self.back_button = QPushButton("← Zurück zur Schülerliste")
        configure_button(self.back_button, "quiet", "Zurück zur Schülerliste")
        self.profile_page_header = PageHeader("Kein Schüler ausgewählt")
        self.profile_page_header.setObjectName("StudentProfilePageHeader")
        self.name_label = self.profile_page_header.title_label
        self.meta_label = self.profile_page_header.subtitle_label
        self.meta_label.setObjectName("StudentProfileContextBadge")
        self.course_badge = CourseBadge()
        self.course_badge.hide()
        self.membership_message = InlineMessage()
        self.action_feedback_label = QLabel("", self)
        self.overview_recent_layout = QVBoxLayout()
        self.observation_empty_label = QLabel("", self)
        self.competency_empty_label = QLabel("", self)
        self.documents_empty_label = QLabel("", self)
        self.documents_feedback_label = QLabel("", self)
        self.report_empty_label = QLabel("", self)
        self.report_feedback_label = QLabel("", self)
        self.report_copy_button = QPushButton("Bericht kopieren", self)
        self.report_export_button = QPushButton("Als Text exportieren", self)
        self.report_create_button = QPushButton("Bericht erstellen", self)
        self.report_copy_button.setEnabled(False)
        self.report_export_button.setEnabled(False)
        self.current_observations: tuple[ObservationListItem, ...] = ()
        self.current_documents: tuple[StudentDocumentViewModel, ...] = ()
        self.current_report_preview: StudentReportPreviewViewModel | None = None
        self.current_report_overview = empty_report_overview()
        self.current_competency_cockpit: StudentCompetencyCockpitViewModel | None = None
        self.current_profile_dashboard = empty_student_profile_dashboard()
        self.current_documentation_subjects: (
            StudentDocumentationSubjectProjectionViewModel | None
        ) = None
        self.show_all_observations = False
        self._report_subjects_expanded = False
        self._report_timeline_initialized = False
        self.report_timeline_scroll: ReportTimelineScrollArea | None = None
        self.report_timeline_track: QWidget | None = None
        self.report_timeline_left_button: QPushButton | None = None
        self.report_timeline_right_button: QPushButton | None = None
        self._focused_observation_id = ""
        self._competency_expanded_keys: set[str] = set()
        self._profile_scroll_positions: dict[int, int] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.back_button.clicked.connect(self.back_requested.emit)

        self.profile_primary_action = QPushButton("Beobachtung erfassen")
        self.profile_primary_action.setObjectName("StudentProfilePrimaryAction")
        self.profile_primary_action.setMaximumWidth(210)
        configure_button(
            self.profile_primary_action,
            "primary",
            "Neue Beobachtung für dieses Kind",
        )
        self.profile_primary_action.clicked.connect(self._request_new_observation)
        header_documentation = QWidget()
        header_documentation.setObjectName("StudentProfileHeaderDocumentation")
        header_documentation_layout = QHBoxLayout(header_documentation)
        header_documentation_layout.setContentsMargins(0, 0, 0, 0)
        header_documentation_layout.setSpacing(8)
        self.header_documentation_ring = DocumentationRing(58)
        header_documentation_layout.addWidget(self.header_documentation_ring)
        header_documentation_text = QVBoxLayout()
        header_documentation_text.setSpacing(1)
        header_documentation_title = QLabel("Dokumentiert")
        set_label_style(header_documentation_title, "card_title")
        self.header_documentation_label = QLabel("0 / 0 Lernbereiche")
        set_label_style(self.header_documentation_label, "small")
        header_documentation_text.addWidget(header_documentation_title)
        header_documentation_text.addWidget(self.header_documentation_label)
        header_documentation_layout.addLayout(header_documentation_text)
        self.profile_page_header.add_action(self.course_badge)
        self.profile_page_header.add_action(header_documentation)
        self.profile_page_header.add_action(self.profile_primary_action)

        self.profile_more_action = QPushButton("Weitere Aktionen")
        self.profile_more_action.setObjectName("StudentProfileMoreActions")
        self.profile_more_action.setMaximumWidth(170)
        configure_button(self.profile_more_action, "quiet", "Weitere Profilaktionen")
        more_menu = QMenu(self.profile_more_action)
        more_menu.addAction("Schüler bearbeiten", self._request_edit_student)
        more_menu.addAction("Datei hinzufügen", self._request_add_document)
        more_menu.addAction("Bericht öffnen", self._request_learning_report)
        more_menu.addAction(
            "Lernentwicklungsgespräch öffnen",
            self._request_learning_conference,
        )
        self.profile_more_action.setMenu(more_menu)
        self.profile_page_header.add_action(self.profile_more_action)
        profile_header_surface = AppCard("accent")
        profile_header_surface.setObjectName("StudentProfileHeaderSurface")
        profile_header_layout = QVBoxLayout(profile_header_surface)
        profile_header_layout.setContentsMargins(16, 12, 16, 12)
        back_row = QHBoxLayout()
        back_row.addWidget(self.back_button)
        back_row.addStretch(1)
        profile_header_layout.addLayout(back_row)
        identity_row = QHBoxLayout()
        identity_row.setSpacing(12)
        self.profile_avatar = QLabel("")
        self.profile_avatar.setObjectName("StudentProfileAvatar")
        self.profile_avatar.setFixedSize(52, 52)
        self.profile_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        identity_row.addWidget(self.profile_avatar)
        identity_row.addWidget(self.profile_page_header, 1)
        profile_header_layout.addLayout(identity_row)
        profile_header_layout.addWidget(self.membership_message)
        layout.addWidget(profile_header_surface)

        self.profile_navigation = SegmentedControl((
            ("overview", "Überblick"),
            ("observations", "Beobachtungen"),
            ("competencies", "Kompetenzen"),
            ("report", "Bericht"),
            ("documents", "Dateien"),
        ))
        self.profile_navigation.setObjectName("StudentProfileNavigation")
        self.profile_navigation.setAccessibleName("Bereiche im Schülerprofil")
        self.profile_navigation.selection_changed.connect(
            self._select_profile_section
        )
        layout.addWidget(self.profile_navigation)

        self.profile_tabs = QTabWidget()
        self.profile_tabs.setObjectName("StudentProfileTabs")
        self.profile_tabs.addTab(self._scrollable_tab(self._overview_tab()), "Überblick")
        self.profile_tabs.addTab(
            self._scrollable_tab(self._observations_card()),
            "Beobachtungen",
        )

        self.profile_tabs.addTab(
            self._scrollable_tab(self._competency_cockpit_tab()),
            "Kompetenzen",
        )

        self.profile_tabs.addTab(
            self._scrollable_tab(self._report_preview_card()),
            "Bericht",
        )
        self.profile_tabs.addTab(
            self._scrollable_tab(self._documents_card()),
            "Dateien",
        )
        self.profile_tabs.tabBar().hide()
        self.profile_tabs.currentChanged.connect(self._sync_profile_navigation)
        layout.addWidget(self.profile_tabs, 1)

    def _select_profile_section(self, key: str) -> None:
        keys = ("overview", "observations", "competencies", "report", "documents")
        if key in keys:
            self.profile_tabs.setCurrentIndex(keys.index(key))

    def _sync_profile_navigation(self, index: int) -> None:
        keys = ("overview", "observations", "competencies", "report", "documents")
        if 0 <= index < len(keys):
            self.profile_navigation.set_current_key(keys[index])
            self._update_profile_header_context()

    def _update_profile_header_context(self) -> None:
        if self.current_student is None:
            subtitle = ""
            self.course_badge.hide()
            self.membership_message.set_message("")
            self.profile_primary_action.setEnabled(False)
        else:
            subtitle = " · ".join(
                part
                for part in (
                    "Aktuelle Zuordnung",
                    (
                        f"Stammgruppe {self.current_student.group_name}"
                        if self.current_student.group_name
                        else ""
                    ),
                    self.current_student.status_label,
                )
                if part
            )
            if self.current_student.course_name:
                self.course_badge.set_course(
                    self.current_student.course_name,
                    self.current_student.course_color_hex,
                )
                self.course_badge.show()
            else:
                self.course_badge.hide()
            if self.current_student.membership_blocking:
                self.membership_message.set_message(
                    self.current_student.status_label,
                    tone="error",
                )
            else:
                self.membership_message.set_message("")
            self.profile_primary_action.setEnabled(
                self.current_student.active
                and self.current_student.resolution_status == "enrolled"
            )
        self.meta_label.setText(subtitle)
        context_width = (
            min(480, self.meta_label.fontMetrics().horizontalAdvance(subtitle) + 80)
            if subtitle else 0
        )
        self.meta_label.setMinimumWidth(0)
        self.meta_label.setMaximumWidth(context_width or 16777215)
        self.meta_label.setVisible(bool(subtitle))

    def resizeEvent(self, event: object) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        compact = self.width() < 1200
        if compact != getattr(self, "_overview_compact", None):
            self._apply_overview_card_layout(compact=compact)
        report_columns = self._report_overview_column_count(self.width())
        if report_columns != getattr(self, "_report_overview_columns", None):
            self._apply_report_overview_layout(columns=report_columns)

    def _scrollable_tab(self, content: QWidget) -> QScrollArea:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 8, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(content)
        wrapper_layout.addStretch(1)

        scroll_area.setWidget(wrapper)
        return scroll_area

    def _overview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(SectionHeader(
            "Arbeitsprofil",
            "Wichtige Informationen zuerst, Details in den fachlichen Bereichen.",
        ))
        self.overview_cards = QWidget()
        self.overview_cards.setObjectName("StudentProfileOverviewCards")
        self.overview_cards_layout = QGridLayout(self.overview_cards)
        self.overview_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.overview_cards_layout.setHorizontalSpacing(16)
        self.overview_cards_layout.setVerticalSpacing(12)
        self.overview_orientation_card = self._orientation_card()
        self.overview_competency_card = self._competency_summary_card()
        self.overview_undocumented_card = self._undocumented_card()
        layout.addWidget(self.overview_cards)
        self._apply_overview_card_layout(compact=False)
        layout.addWidget(self._documentation_subjects_card())
        layout.addWidget(
            self._overview_list_card("Neueste Beobachtungen", self.overview_recent_layout)
        )
        layout.addStretch(1)
        return tab

    def _documentation_subjects_card(self) -> QFrame:
        card = self._card("soft")
        card.setObjectName("StudentProfileDocumentationSubjectsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        title_row = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(2)
        title = QLabel("Fächer für die Dokumentation")
        set_label_style(title, "card_title")
        self.documentation_subject_summary = QLabel("Keine Auswahl verfügbar")
        self.documentation_subject_summary.setWordWrap(True)
        set_label_style(self.documentation_subject_summary, "subtle")
        self.documentation_subject_school_year = QLabel("")
        set_label_style(self.documentation_subject_school_year, "subtle")
        heading.addWidget(title)
        heading.addWidget(self.documentation_subject_summary)
        title_row.addLayout(heading, 1)
        title_row.addWidget(self.documentation_subject_school_year)
        self.documentation_subject_toggle_button = QPushButton("Aufklappen")
        self.documentation_subject_toggle_button.setCheckable(True)
        configure_button(
            self.documentation_subject_toggle_button,
            "quiet",
            "Fächer für die Dokumentation aufklappen",
        )
        self.documentation_subject_toggle_button.toggled.connect(
            self._set_documentation_subjects_expanded
        )
        title_row.addWidget(self.documentation_subject_toggle_button)
        layout.addLayout(title_row)

        self.documentation_subjects_body = QWidget(card)
        body_layout = QVBoxLayout(self.documentation_subjects_body)
        body_layout.setContentsMargins(0, 4, 0, 0)
        body_layout.setSpacing(8)

        self.documentation_subject_inherit = QRadioButton(
            "Globale Fachauswahl verwenden",
            card,
        )
        self.documentation_subject_custom = QRadioButton(
            "Für dieses Kind individuell festlegen",
            card,
        )
        self.documentation_subject_inherit.toggled.connect(
            self._update_documentation_subject_editability
        )
        self.documentation_subject_custom.toggled.connect(
            self._update_documentation_subject_editability
        )
        body_layout.addWidget(self.documentation_subject_inherit)
        body_layout.addWidget(self.documentation_subject_custom)

        self.documentation_subject_options_layout = QVBoxLayout()
        self.documentation_subject_options_layout.setContentsMargins(20, 0, 0, 0)
        self.documentation_subject_options_layout.setSpacing(5)
        self.documentation_subject_checkboxes: dict[str, QCheckBox] = {}
        body_layout.addLayout(self.documentation_subject_options_layout)

        help_label = QLabel(
            "Diese Auswahl legt fest, welche Fächer bei diesem Kind für die "
            "Dokumentation berücksichtigt werden. Bestehende Beobachtungen "
            "bleiben erhalten."
        )
        help_label.setWordWrap(True)
        set_label_style(help_label, "small")
        body_layout.addWidget(help_label)

        actions = QHBoxLayout()
        self.documentation_subject_save_button = QPushButton("Speichern")
        self.documentation_subject_cancel_button = QPushButton("Abbrechen")
        configure_button(
            self.documentation_subject_save_button,
            "primary",
            "Fächerauswahl für dieses Kind speichern",
        )
        configure_button(
            self.documentation_subject_cancel_button,
            "quiet",
            "Änderungen an der Fächerauswahl verwerfen",
        )
        self.documentation_subject_save_button.clicked.connect(
            self._request_documentation_subjects_save
        )
        self.documentation_subject_cancel_button.clicked.connect(
            self._reset_documentation_subject_editor
        )
        actions.addWidget(self.documentation_subject_save_button)
        actions.addWidget(self.documentation_subject_cancel_button)
        actions.addStretch(1)
        body_layout.addLayout(actions)
        self.documentation_subject_feedback = QLabel("")
        self.documentation_subject_feedback.setWordWrap(True)
        set_label_style(self.documentation_subject_feedback, "subtle")
        body_layout.addWidget(self.documentation_subject_feedback)
        layout.addWidget(self.documentation_subjects_body)
        self._set_documentation_subjects_expanded(False)
        return card

    def _set_documentation_subjects_expanded(self, expanded: bool) -> None:
        self.documentation_subjects_body.setVisible(expanded)
        self.documentation_subject_toggle_button.setChecked(expanded)
        self.documentation_subject_toggle_button.setText(
            "Einklappen" if expanded else "Aufklappen"
        )
        self.documentation_subject_toggle_button.setAccessibleName(
            "Fächer für die Dokumentation "
            + ("einklappen" if expanded else "aufklappen")
        )

    def set_documentation_subjects(
        self,
        projection: StudentDocumentationSubjectProjectionViewModel | None,
    ) -> None:
        self.current_documentation_subjects = projection
        self._reset_documentation_subject_editor()

    def _reset_documentation_subject_editor(self) -> None:
        projection = self.current_documentation_subjects
        self._clear_layout(self.documentation_subject_options_layout)
        self.documentation_subject_checkboxes = {}
        if projection is None:
            self.documentation_subject_school_year.setText("")
            self.documentation_subject_summary.setText("Keine Auswahl verfügbar")
            self.documentation_subject_inherit.setChecked(True)
            self.documentation_subject_inherit.setEnabled(False)
            self.documentation_subject_custom.setEnabled(False)
            self.documentation_subject_save_button.setEnabled(False)
            self.documentation_subject_cancel_button.setEnabled(False)
            self.documentation_subject_feedback.setText("")
            return
        self.documentation_subject_school_year.setText(
            projection.school_year_label
        )
        subject_count = len(projection.selected_subject_ids)
        mode_label = (
            "Globale Auswahl"
            if projection.mode == "inherit"
            else "Individuelle Auswahl"
        )
        self.documentation_subject_summary.setText(
            f"{mode_label} · {subject_count} "
            f"{'Fach' if subject_count == 1 else 'Fächer'}"
        )
        selected = set(projection.selected_subject_ids)
        for subject in projection.available_subjects:
            checkbox = QCheckBox(subject.label)
            checkbox.setChecked(subject.subject_id in selected)
            self.documentation_subject_checkboxes[subject.subject_id] = checkbox
            self.documentation_subject_options_layout.addWidget(checkbox)
        for subject in projection.retained_inactive_subjects:
            checkbox = QCheckBox(f"{subject.label} (nicht mehr verfügbar)")
            checkbox.setChecked(True)
            checkbox.setEnabled(False)
            checkbox.setAccessibleDescription(
                "Gespeicherte historische Auswahl; bleibt unverändert erhalten."
            )
            self.documentation_subject_options_layout.addWidget(checkbox)
        is_inherit = projection.mode == "inherit"
        self.documentation_subject_inherit.setChecked(is_inherit)
        self.documentation_subject_custom.setChecked(not is_inherit)
        editable = not projection.is_read_only
        self.documentation_subject_inherit.setEnabled(editable)
        self.documentation_subject_custom.setEnabled(editable)
        self.documentation_subject_save_button.setEnabled(editable)
        self.documentation_subject_cancel_button.setEnabled(editable)
        self.documentation_subject_feedback.setText(
            (
                "Nur lesbar"
                if projection.is_read_only
                else (
                    "Die individuelle Auswahl enthält ein nicht mehr verfügbares "
                    "Fach und bleibt unverändert. Ein Wechsel zur globalen "
                    "Fachauswahl ist weiterhin möglich."
                    if projection.retained_inactive_subjects
                    else ""
                )
            )
        )
        self._update_documentation_subject_editability()

    def _update_documentation_subject_editability(self) -> None:
        projection = self.current_documentation_subjects
        editable = bool(
            projection is not None
            and not projection.is_read_only
            and self.documentation_subject_custom.isChecked()
            and not projection.retained_inactive_subjects
        )
        for checkbox in self.documentation_subject_checkboxes.values():
            checkbox.setEnabled(editable)
        can_save = bool(
            projection is not None
            and not projection.is_read_only
            and (
                self.documentation_subject_inherit.isChecked()
                or not projection.retained_inactive_subjects
            )
        )
        self.documentation_subject_save_button.setEnabled(can_save)

    def _request_documentation_subjects_save(self) -> None:
        projection = self.current_documentation_subjects
        if projection is None or projection.is_read_only or not self.current_student:
            return
        mode = (
            "custom" if self.documentation_subject_custom.isChecked() else "inherit"
        )
        selected = tuple(
            subject.subject_id
            for subject in projection.available_subjects
            if self.documentation_subject_checkboxes[subject.subject_id].isChecked()
        )
        self.documentation_subject_feedback.setText("")
        self.documentation_subjects_save_requested.emit(
            self.current_student.student_id,
            projection.school_year_id,
            mode,
            selected,
        )

    def show_documentation_subjects_error(self, message: str) -> None:
        self._set_documentation_subjects_expanded(True)
        self.documentation_subject_feedback.setText(message)

    def _orientation_card(self) -> QFrame:
        card = self._card()
        card.setObjectName("StudentProfileOrientationCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        title_row = QHBoxLayout()
        title = QLabel("Lernentwicklung")
        set_label_style(title, "section_title")
        title_row.addWidget(title, 1)
        layout.addLayout(title_row)
        self.orientation_changes_layout = QVBoxLayout()
        self.orientation_changes_layout.setContentsMargins(0, 0, 0, 0)
        self.orientation_changes_layout.setSpacing(8)
        layout.addLayout(self.orientation_changes_layout)
        return card

    def _competency_summary_card(self) -> QFrame:
        card = self._card("accent")
        card.setObjectName("StudentProfileCompetencySummaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(9)
        eyebrow = QLabel("KOMPETENZEN")
        eyebrow.setObjectName("StudentProfileEyebrow")
        layout.addWidget(eyebrow)
        metric_row = QHBoxLayout()
        self.overview_documentation_ring = DocumentationRing(72)
        metric_row.addWidget(self.overview_documentation_ring)
        metric_text = QVBoxLayout()
        metric_text.setSpacing(2)
        self.overview_documentation_metric = QLabel("0 / 0")
        self.overview_documentation_metric.setObjectName(
            "StudentProfileDocumentationMetric"
        )
        metric_text.addWidget(self.overview_documentation_metric)
        metric_text.addWidget(self._overview_text("Lernbereiche dokumentiert", "body"))
        metric_row.addLayout(metric_text, 1)
        layout.addLayout(metric_row)
        self.overview_competency_counts_layout = QVBoxLayout()
        self.overview_competency_counts_layout.setSpacing(7)
        layout.addLayout(self.overview_competency_counts_layout)
        layout.addWidget(self._overview_text(
            "Umfang und Herkunft der Dokumentation · keine Leistung oder Rangfolge.",
            "small",
        ))
        button = QPushButton("Kompetenz-Cockpit öffnen")
        button.setObjectName("StudentProfileOpenCompetencyCockpit")
        configure_button(button, "secondary", "Kompetenz-Cockpit öffnen")
        button.clicked.connect(
            lambda _checked=False: self._select_profile_section("competencies")
        )
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
        return card

    def _undocumented_card(self) -> QFrame:
        card = self._card("soft")
        card.setObjectName("StudentProfileUndocumentedCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(9)
        eyebrow = QLabel("NOCH NICHT DOKUMENTIERT")
        eyebrow.setObjectName("StudentProfileEyebrow")
        layout.addWidget(eyebrow)
        count_row = QHBoxLayout()
        self.overview_undocumented_metric = QLabel("0")
        self.overview_undocumented_metric.setObjectName(
            "StudentProfileDocumentationMetric"
        )
        count_row.addWidget(self.overview_undocumented_metric)
        count_row.addWidget(self._overview_text(
            "Lernbereiche ohne vorhandene Dokumentation",
            "body",
        ), 1)
        layout.addLayout(count_row)
        self.overview_undocumented_subjects_layout = QVBoxLayout()
        self.overview_undocumented_subjects_layout.setSpacing(7)
        layout.addLayout(self.overview_undocumented_subjects_layout)
        button = QPushButton("Offene Bereiche ansehen")
        button.setObjectName("StudentProfileOpenUndocumented")
        configure_button(button, "quiet", "Noch nicht dokumentierte Bereiche ansehen")
        button.clicked.connect(
            lambda _checked=False: self._open_undocumented_competencies()
        )
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        layout.addWidget(self._overview_text(
            "Hinweis auf Dokumentationsumfang · keine Aussage über Leistung.",
            "small",
        ))
        return card

    def _apply_overview_card_layout(self, *, compact: bool) -> None:
        if not hasattr(self, "overview_cards_layout"):
            return
        for widget in (
            self.overview_orientation_card,
            self.overview_competency_card,
            self.overview_undocumented_card,
        ):
            self.overview_cards_layout.removeWidget(widget)
        if compact:
            self.overview_cards_layout.addWidget(
                self.overview_orientation_card, 0, 0, 1, 2
            )
            self.overview_cards_layout.addWidget(
                self.overview_competency_card, 1, 0
            )
            self.overview_cards_layout.addWidget(
                self.overview_undocumented_card, 1, 1
            )
            self.overview_cards_layout.setColumnStretch(0, 1)
            self.overview_cards_layout.setColumnStretch(1, 1)
            self.overview_cards_layout.setColumnStretch(2, 0)
        else:
            self.overview_cards_layout.addWidget(
                self.overview_orientation_card, 0, 0
            )
            self.overview_cards_layout.addWidget(
                self.overview_competency_card, 0, 1
            )
            self.overview_cards_layout.addWidget(
                self.overview_undocumented_card, 0, 2
            )
            self.overview_cards_layout.setColumnStretch(0, 6)
            self.overview_cards_layout.setColumnStretch(1, 3)
            self.overview_cards_layout.setColumnStretch(2, 3)
        self._overview_compact = compact

    def _open_undocumented_competencies(self) -> None:
        self._select_profile_section("competencies")
        index = self.competency_documentation_filter.findData("undocumented")
        if index >= 0:
            self.competency_documentation_filter.setCurrentIndex(index)

    def _overview_list_card(self, title: str, content_layout: QVBoxLayout) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        title_label = QLabel(title)
        set_label_style(title_label, "card_title")
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)
        layout.addWidget(title_label)
        layout.addLayout(content_layout)
        return card

    def _actions_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        title = QLabel("Schnellaktionen")
        set_label_style(title, "card_title")
        button_row = QHBoxLayout()
        observation_button = QPushButton("+ Beobachtung")
        document_button = QPushButton("+ Datei hinzufügen")
        edit_button = QPushButton("Schüler bearbeiten")
        observation_button.clicked.connect(self._request_new_observation)
        document_button.clicked.connect(self._request_add_document)
        edit_button.clicked.connect(self._request_edit_student)
        button_row.addWidget(observation_button)
        button_row.addWidget(document_button)
        button_row.addWidget(edit_button)
        button_row.addStretch()
        set_label_style(self.action_feedback_label, "muted")
        layout.addWidget(title)
        layout.addLayout(button_row)
        layout.addWidget(self.action_feedback_label)
        return card

    def _placeholder_card(self, title: str, placeholder: str, hint: str) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        set_label_style(title_label, "card_title")
        placeholder_label = QLabel(placeholder)
        set_label_style(placeholder_label, "body")
        hint_label = QLabel(hint)
        set_label_style(hint_label, "subtle")
        layout.addWidget(title_label)
        layout.addWidget(placeholder_label)
        layout.addWidget(hint_label)
        return card

    def _observations_card(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        title_label = SectionHeader(
            "Beobachtungen",
            "Datum, Fach und Kontext bleiben beim Scannen klar getrennt.",
        )
        self.observation_subject_filter = QComboBox()
        self.observation_rating_filter = QComboBox()
        self.observation_search_input = SearchField(
            "Kontext, Notiz oder Kompetenz suchen",
            accessible_name="Beobachtungen durchsuchen",
            accessible_description=(
                "Filtert die Beobachtungen dieses Kindes nach Kontext, Notiz und Kompetenz."
            ),
        )
        self.observation_reset_button = QPushButton("Zurücksetzen")
        self.observation_show_all_button = QPushButton("")
        self.observation_show_all_button.setObjectName("ObservationTextActionButton")
        self.observation_show_all_button.clicked.connect(self.toggle_observation_limit)
        self.observations_container = QWidget()
        self.observations_layout = QVBoxLayout(self.observations_container)
        self.observations_layout.setContentsMargins(0, 0, 0, 0)
        self.observations_layout.setSpacing(8)
        set_label_style(self.observation_empty_label, "body")
        layout.addWidget(title_label)
        layout.addWidget(self._observation_filter_card())
        layout.addWidget(self.observations_container)
        layout.addWidget(self.observation_show_all_button)
        return section

    def _observation_filter_card(self) -> QFrame:
        card = FilterBar(self.observation_search_input)
        card.setAccessibleName("Beobachtungen suchen und filtern")
        self.observation_subject_filter.currentIndexChanged.connect(
            lambda _index: self.apply_observation_filters()
        )
        self.observation_rating_filter.addItems(("Alle", "++", "+", "-", "--"))
        self.observation_rating_filter.currentIndexChanged.connect(
            lambda _index: self.apply_observation_filters()
        )
        self.observation_search_input.textChanged.connect(
            lambda _text: self.apply_observation_filters()
        )
        self.observation_reset_button.setObjectName("ObservationResetButton")
        self.observation_subject_filter.setMinimumWidth(150)
        self.observation_rating_filter.setMinimumWidth(118)
        self.observation_search_input.setMinimumWidth(190)
        self.observation_search_input.setMaximumWidth(320)
        self.observation_reset_button.clicked.connect(self.reset_observation_filters)
        self.observation_subject_filter.setAccessibleName("Beobachtungen nach Fach filtern")
        self.observation_rating_filter.setAccessibleName(
            "Beobachtungen nach Bewertung filtern"
        )
        card.add_filter_widget(self.observation_subject_filter)
        card.add_filter_widget(self.observation_rating_filter)
        card.add_filter_widget(self.observation_reset_button)
        card.reset_requested.connect(self.reset_observation_filters)
        self.observation_filter_bar = card
        return card

    def _filter_label(self, label: str) -> QLabel:
        filter_label = QLabel(label)
        set_label_style(filter_label, "field_label")
        return filter_label

    def _competency_cockpit_tab(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)
        title = SectionHeader(
            "Kompetenz-Cockpit",
            "Fach → Kompetenzbereich → Thema → Kompetenz",
            (
                "Der Dokumentationsstand beschreibt vorhandene pädagogische "
                "Dokumentation und ist keine Schulnote oder Leistungsquote."
            ),
        )
        self.competency_search_input = SearchField(
            "Kompetenzen durchsuchen …",
            accessible_name="Kompetenzen im Profil durchsuchen",
            accessible_description=(
                "Filtert die sichtbare Kompetenzhierarchie dieses Kindes."
            ),
        )
        self.competency_search_input.setObjectName("CompetencyCockpitSearch")
        self.competency_subject_filter = QComboBox()
        self.competency_subject_filter.setObjectName("CompetencyCockpitSubjectFilter")
        self.competency_subject_filter.addItem("Alle Fächer", "")
        self.competency_documentation_filter = QComboBox()
        self.competency_documentation_filter.setObjectName(
            "CompetencyCockpitDocumentationFilter"
        )
        for label, state in (
            ("Alle", ""),
            ("Dokumentiert", "documented"),
            ("Noch nicht dokumentiert", "undocumented"),
            ("Beobachtet, noch nicht bestätigt", "observed_unconfirmed"),
            ("Bestätigter Stand", "confirmed"),
            ("Neuere Beobachtungen nach Bestätigung", "newer_observations"),
            (
                "Bestätigungsstand unklar",
                "confirmation_unknown",
            ),
        ):
            self.competency_documentation_filter.addItem(label, state)
        self.competency_reset_button = QPushButton("Filter zurücksetzen")
        self.competency_reset_button.setObjectName("CompetencyCockpitFilterResetButton")
        self.competency_stage_filter = SegmentedControl((
            ("matching", "Passende Kompetenzen"),
            ("stage_4", "Klassenstufe 4"),
            ("all", "Alle Kompetenzen"),
        ))
        self.competency_stage_filter.setObjectName("CompetencyCockpitStageFilter")
        self.competency_stage_filter.setAccessibleName("Klassenstufenfilter")
        self.competency_stage_filter.setToolTip(
            "Klassenstufe 4 ist nicht gesperrt, sondern in der passenden Ansicht ausgeblendet."
        )
        self.competency_subject_filter.currentIndexChanged.connect(
            self.apply_competency_cockpit_filters
        )
        self.competency_documentation_filter.currentIndexChanged.connect(
            self.apply_competency_cockpit_filters
        )
        self.competency_search_input.textChanged.connect(
            lambda _text: self.apply_competency_cockpit_filters()
        )
        self.competency_stage_filter.selection_changed.connect(
            lambda _key: self.apply_competency_cockpit_filters()
        )
        self.competency_reset_button.clicked.connect(self.reset_competency_cockpit_filters)
        filters = FilterBar(self.competency_search_input)
        filters.setObjectName("CompetencyCockpitFilterBar")
        filters.setAccessibleName("Kompetenzen suchen und filtern")
        self.competency_subject_filter.setAccessibleName("Kompetenzen nach Fach filtern")
        self.competency_documentation_filter.setAccessibleName(
            "Kompetenzen nach Dokumentationszustand filtern"
        )
        filters.add_filter_widget(self.competency_subject_filter)
        filters.add_filter_widget(self.competency_documentation_filter)
        filters.add_filter_widget(self.competency_reset_button)
        filters.reset_requested.connect(self.reset_competency_cockpit_filters)
        self.competency_filter_bar = filters
        self.competency_cockpit_container = QWidget()
        self.competency_cockpit_layout = QVBoxLayout(
            self.competency_cockpit_container
        )
        self.competency_cockpit_layout.setContentsMargins(0, 0, 0, 0)
        self.competency_cockpit_layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(filters)
        layout.addWidget(self.competency_stage_filter)
        layout.addWidget(self.competency_cockpit_container)
        return section

    def _documents_card(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        header = QHBoxLayout()
        title_label = QLabel("Dokumente & Medien")
        set_label_style(title_label, "section_title")
        add_button = QPushButton("+ Datei hinzufügen")
        add_button.clicked.connect(self._request_add_document)
        header.addWidget(title_label)
        header.addStretch(1)
        header.addWidget(add_button)
        self.documents_container = QWidget()
        self.documents_layout = QVBoxLayout(self.documents_container)
        self.documents_layout.setContentsMargins(0, 0, 0, 0)
        self.documents_layout.setSpacing(8)
        set_label_style(self.documents_empty_label, "body")
        set_label_style(self.documents_feedback_label, "subtle")
        layout.addLayout(header)
        layout.addWidget(self.documents_feedback_label)
        layout.addWidget(self.documents_container)
        return section

    def _report_preview_card(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(SectionHeader(
            "Entwicklungsübersicht und Berichtsvorbereitung",
            "Timeline und Fachkarten im aktuellen Schuljahr; Berichtstände im gewählten Berichtszeitraum.",
        ))
        self.report_period_summary = QLabel("Kein Berichtszeitraum gewählt")
        self.report_period_summary.setObjectName("ReportOverviewPeriod")
        self.report_period_summary.setWordWrap(True)
        self.report_period_summary.setAccessibleName(
            "Ausgewählter Berichtszeitraum"
        )
        set_label_style(self.report_period_summary, "body")
        layout.addWidget(self.report_period_summary)

        self.report_overview_grid = QGridLayout()
        self.report_overview_grid.setContentsMargins(0, 0, 0, 0)
        self.report_overview_grid.setHorizontalSpacing(16)
        self.report_overview_grid.setVerticalSpacing(16)

        self.report_status_card, self.report_status_layout = (
            self._report_overview_card(
                "Bericht",
                "",
                "ReportOverviewReportStatusCard",
            )
        )
        (
            self.learning_conference_status_card,
            self.learning_conference_status_layout,
        ) = self._report_overview_card(
            "Lernentwicklungsgespräch (LEG)",
            "",
            "ReportOverviewLearningConferenceStatusCard",
        )
        self.next_steps_card, self.next_steps_layout = self._report_overview_card(
            "Nächste Schritte",
            "",
            "ReportOverviewNextStepsCard",
        )
        self.timeline_card, self.report_timeline_layout = self._report_overview_card(
            "Dokumentations-Timeline",
            "Aktuelles Schuljahr · reale Dokumentations- und Dokumentereignisse",
            "ReportOverviewTimelineCard",
        )
        self.subjects_card, self.report_subjects_layout = self._report_overview_card(
            "Fachübersicht",
            "Aktuelles Schuljahr · effektive Schülerfächer",
            "ReportOverviewSubjectsCard",
        )
        self.timeline_card.setMinimumHeight(235)
        self.subjects_card.setMinimumHeight(235)
        self.history_card, self.report_history_layout = self._report_overview_card(
            "Berichte & LEG (Übersicht)",
            "Gemeinsame Anzeige, getrennte fachliche Quellen",
            "ReportOverviewHistoryCard",
        )
        self._report_overview_cards = (
            self.report_status_card,
            self.learning_conference_status_card,
            self.next_steps_card,
            self.timeline_card,
            self.subjects_card,
            self.history_card,
        )
        layout.addLayout(self.report_overview_grid)
        self._apply_report_overview_layout(columns=3)

        # The former live preparation remains available as a ViewModel to the
        # existing copy/export helpers, without retaining a hidden widget tree.
        set_label_style(self.report_empty_label, "body")
        set_label_style(self.report_feedback_label, "subtle")
        self.report_copy_button.clicked.connect(self.copy_report_text_to_clipboard)
        self.report_export_button.clicked.connect(self.export_report_text)
        self.report_create_button.clicked.connect(self._request_learning_report)
        self.set_report_overview(empty_report_overview())
        return section

    def _report_overview_card(
        self,
        title: str,
        subtitle: str,
        object_name: str,
    ) -> tuple[QFrame, QVBoxLayout]:
        card = self._card()
        card.setObjectName(object_name)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(
            SectionHeader(title, subtitle),
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(7)
        layout.addLayout(body)
        layout.addStretch(1)
        return card, body

    def _report_compact_empty_state(
        self,
        text: str,
        *,
        title: str,
    ) -> QWidget:
        state = QWidget()
        state.setObjectName("ReportOverviewEmptyState")
        state.setAccessibleName(f"{title}. {text}")
        layout = QVBoxLayout(state)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        set_label_style(title_label, "card_title")
        detail_label = QLabel(text)
        detail_label.setWordWrap(True)
        set_label_style(detail_label, "subtle")
        layout.addWidget(title_label)
        layout.addWidget(detail_label)
        return state

    @staticmethod
    def _report_overview_column_count(width: int) -> int:
        if width >= 1280:
            return 3
        if width >= 960:
            return 2
        return 1

    def _apply_report_overview_layout(self, *, columns: int) -> None:
        if not hasattr(self, "report_overview_grid"):
            return
        self._report_overview_columns = columns
        while self.report_overview_grid.count():
            self.report_overview_grid.takeAt(0)
        for column in range(3):
            self.report_overview_grid.setColumnStretch(
                column,
                1 if column < columns else 0,
            )
        if columns == 1:
            for row, card in enumerate(self._report_overview_cards):
                self.report_overview_grid.addWidget(
                    card,
                    row,
                    0,
                    alignment=Qt.AlignmentFlag.AlignTop,
                )
        elif columns == 2:
            self.report_overview_grid.addWidget(
                self.report_status_card,
                0,
                0,
            )
            self.report_overview_grid.addWidget(
                self.learning_conference_status_card,
                0,
                1,
            )
            self.report_overview_grid.addWidget(
                self.next_steps_card,
                1,
                0,
            )
            self.report_overview_grid.addWidget(
                self.history_card,
                1,
                1,
            )
            self.report_overview_grid.addWidget(
                self.timeline_card,
                2,
                0,
                1,
                2,
            )
            self.report_overview_grid.addWidget(
                self.subjects_card,
                3,
                0,
                1,
                2,
            )
        else:
            self.report_overview_grid.addWidget(self.report_status_card, 0, 0)
            self.report_overview_grid.addWidget(
                self.learning_conference_status_card,
                0,
                1,
            )
            self.report_overview_grid.addWidget(self.next_steps_card, 0, 2)
            self.report_overview_grid.addWidget(
                self.timeline_card,
                1,
                0,
                1,
                3,
            )
            self.report_overview_grid.addWidget(
                self.subjects_card,
                2,
                0,
                1,
                3,
            )
            self.report_overview_grid.addWidget(
                self.history_card,
                3,
                0,
                1,
                3,
            )
        if hasattr(self, "current_report_overview"):
            self._render_report_subjects(self.current_report_overview)
            self._render_report_timeline(
                self.current_report_overview.timeline_events
            )
            self._update_report_tab_order()

    def _report_action_row(self) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        actions.addWidget(self.report_create_button)
        actions.addWidget(self.report_copy_button)
        actions.addWidget(self.report_export_button)
        actions.addStretch(1)
        return actions

    def _card(self, variant: str = "default") -> QFrame:
        return AppCard(variant)

    def _make_clickable_card(
        self,
        card: QFrame,
        action: Callable[[], None],
        tooltip: str,
    ) -> None:
        card.setProperty("interactive", True)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        card.setAccessibleName(tooltip)
        card.setToolTip(tooltip)
        install_card_motion(card)
        original_key_press_event = card.keyPressEvent

        def handle_mouse_release(event: object) -> None:
            if isinstance(card, AppCard):
                card.set_pressed(False)
            button = getattr(event, "button", lambda: None)()
            if button != Qt.MouseButton.LeftButton:
                getattr(event, "accept", lambda: None)()
                return
            position = (
                event.position().toPoint()
                if hasattr(event, "position")
                else event.pos()
            )
            child = card.childAt(position)
            while child is not None and child is not card:
                if isinstance(child, (QPushButton, QComboBox, QLineEdit)):
                    getattr(event, "accept", lambda: None)()
                    return
                child = child.parentWidget()
            action()
            getattr(event, "accept", lambda: None)()

        def handle_key_press(event: object) -> None:
            key = getattr(event, "key", lambda: None)()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
                action()
                getattr(event, "accept", lambda: None)()
                return
            original_key_press_event(event)

        card.mouseReleaseEvent = handle_mouse_release
        card.keyPressEvent = handle_key_press

    def _show_placeholder_message(self, message: str) -> None:
        self.action_feedback_label.setText(message)

    def _request_new_observation(self) -> None:
        if self.current_student is None:
            self._show_placeholder_message(PROFILE_ACTION_MESSAGES["observation"])
            return
        if (
            not self.current_student.active
            or self.current_student.resolution_status != "enrolled"
        ):
            self._show_placeholder_message(
                self.current_student.status_label
                or "Für dieses Kind kann aktuell keine Beobachtung erfasst werden."
            )
            return
        self.observation_requested.emit(self.current_student)

    def _request_add_document(self) -> None:
        if self.current_student is None:
            self._show_placeholder_message(PROFILE_ACTION_MESSAGES["document"])
            return
        self.document_add_requested.emit(self.current_student.student_id)

    def _request_edit_student(self) -> None:
        if self.current_student is None:
            self._show_placeholder_message(PROFILE_ACTION_MESSAGES["edit"])
            return
        self.student_edit_requested.emit(self.current_student.student_id)

    def _request_learning_report(self) -> None:
        if self.current_student is None:
            self.report_feedback_label.setText("Bitte zuerst einen Schüler auswählen.")
            return
        self.report_requested.emit(self.current_student.student_id)

    def _request_learning_conference(self) -> None:
        if self.current_student is None:
            self.action_feedback_label.setText("Bitte zuerst einen Schüler auswählen.")
            return
        self.learning_conference_requested.emit(self.current_student.student_id)

    def _render_profile_overview(
        self,
        student: StudentDetailViewModel | None,
        observations: tuple[ObservationListItem, ...],
        dashboard: StudentProfileDashboardViewModel,
    ) -> None:
        self._clear_layout(self.overview_recent_layout)
        self._clear_layout(self.orientation_changes_layout)
        self._clear_layout(self.overview_competency_counts_layout)
        self._clear_layout(self.overview_undocumented_subjects_layout)
        if student is None:
            self.orientation_changes_layout.addWidget(
                EmptyState("Bitte zuerst ein Kind auswählen.")
            )
            return
        summary = dashboard.documentation_summary
        documented = summary.documented_learning_area_count
        total = summary.total_learning_area_count
        self.header_documentation_ring.set_counts(documented, total)
        self.header_documentation_label.setText(
            f"{documented} / {total} Lernbereiche"
        )
        self.overview_documentation_ring.set_counts(documented, total)
        self.overview_documentation_metric.setText(f"{documented} / {total}")
        self.overview_undocumented_metric.setText(str(dashboard.undocumented_count))
        self.overview_competency_counts_layout.addWidget(
            self._dashboard_summary_row(
                "Bestätigter Stand",
                str(dashboard.confirmed_documented_count),
            )
        )
        self.overview_competency_counts_layout.addWidget(
            self._dashboard_summary_row(
                "Beobachtet",
                str(dashboard.observed_only_count),
            )
        )
        for subject in dashboard.undocumented_subjects:
            self.overview_undocumented_subjects_layout.addWidget(
                self._dashboard_summary_row(
                    subject.subject_display_name,
                    str(subject.count),
                )
            )
        if not dashboard.undocumented_subjects:
            self.overview_undocumented_subjects_layout.addWidget(
                self._overview_text(
                    "Alle dokumentationsrelevanten Kompetenzen sind belegt.",
                    "small",
                )
            )
        if dashboard.orientation_changes:
            for change in dashboard.orientation_changes:
                self.orientation_changes_layout.addWidget(
                    self._orientation_change_row(change)
                )
        else:
            self.orientation_changes_layout.addWidget(EmptyState(
                (
                    "Sobald zu einer Kompetenz unterschiedliche dokumentierte "
                    "Stände vorliegen, erscheint sie hier."
                ),
                title="Noch keine Entwicklung über mehrere Zeitpunkte sichtbar",
            ))
        self._render_overview_recent_observations(observations)

    def _orientation_change_row(
        self,
        change: StudentProfileOrientationChangeViewModel,
    ) -> QFrame:
        row = self._card("soft")
        row.setObjectName("StudentProfileOrientationChange")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        summary = QHBoxLayout()
        summary.setSpacing(14)
        title = QVBoxLayout()
        title.setSpacing(3)
        competency = QLabel(change.competency_label)
        competency.setWordWrap(True)
        set_label_style(competency, "card_title")
        topic = QLabel(
            " · ".join(
                part
                for part in (change.subject_display_name, change.topic_label)
                if part
            )
        )
        set_label_style(topic, "small")
        title.addWidget(competency)
        title.addWidget(topic)
        if change.historical:
            historical = QLabel("Historische Referenz")
            historical.setObjectName("StudentProfileHistoricalBadge")
            title.addWidget(historical, 0, Qt.AlignmentFlag.AlignLeft)
        summary.addLayout(title, 1)

        status = QFrame()
        status.setObjectName("StudentProfileOrientationStatusChange")
        status_layout = QVBoxLayout(status)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(2)
        status_layout.addLayout(self._orientation_status_row(
            "Ausgangslage",
            change.previous_rating,
            change.previous_status_label,
        ))
        arrow = QLabel("↓")
        arrow.setObjectName("StudentProfileDevelopmentArrow")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setAccessibleName("Veränderung zum aktuell dokumentierten Stand")
        status_layout.addWidget(arrow)
        status_layout.addLayout(self._orientation_status_row(
            "Aktueller dokumentierter Stand",
            change.new_rating,
            change.new_status_label,
        ))
        summary.addWidget(status)
        layout.addLayout(summary)

        evidence = QFrame()
        evidence.setObjectName("StudentProfileOrientationEvidence")
        evidence_layout = QVBoxLayout(evidence)
        evidence_layout.setContentsMargins(9, 6, 9, 6)
        evidence_layout.setSpacing(3)
        evidence_meta = QHBoxLayout()
        evidence_meta.setSpacing(7)
        event_date = QLabel(change.triggering_event.event_date.strftime("%d.%m.%Y"))
        set_label_style(event_date, "small")
        evidence_meta.addWidget(event_date)
        source_text = (
            "Bestätigung"
            if change.triggering_event.source == "confirmation"
            else change.triggering_event.source_label
        )
        source = QLabel(source_text)
        source.setObjectName("StudentProfileEvidenceBadge")
        evidence_meta.addWidget(source)
        evidence_meta.addStretch(1)
        evidence_layout.addLayout(evidence_meta)
        evidence_text = QLabel(
            self._orientation_evidence_excerpt(change.triggering_event)
        )
        evidence_text.setWordWrap(True)
        set_label_style(evidence_text, "body")
        evidence_layout.addWidget(evidence_text)
        layout.addWidget(evidence)
        if change.triggering_event.reference_id:
            self._make_clickable_card(
                row,
                lambda observation_id=change.triggering_event.reference_id: (
                    self._show_observations_tab(observation_id)
                ),
                f"Beobachtung zu {change.competency_label} öffnen",
            )
        else:
            self._make_clickable_card(
                row,
                lambda: self._select_profile_section("competencies"),
                f"Kompetenz {change.competency_label} öffnen",
            )
        row.setAccessibleName(
            f"{change.competency_label}. Ausgangslage {change.previous_status_label}. "
            f"Aktueller dokumentierter Stand {change.new_status_label}. "
            f"{source_text} am {change.triggering_event.event_date.strftime('%d.%m.%Y')}. "
            f"{self._orientation_evidence_excerpt(change.triggering_event)}"
        )
        return row

    def _orientation_status_row(
        self,
        label: str,
        rating: str,
        status_label: str,
    ) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        stage = QLabel(label)
        set_label_style(stage, "small")
        row.addWidget(stage, 1)
        badge = StatusBadge(status_label, rating_token=rating)
        row.addWidget(badge, 0)
        return row

    @staticmethod
    def _orientation_evidence_excerpt(event: object) -> str:
        evidence_label = str(getattr(event, "evidence_label", "")).strip()
        if getattr(event, "source", "") == "observation":
            if " · " in evidence_label:
                return f"„{evidence_label.rsplit(' · ', 1)[-1].strip()}“"
            return "Dokumentierter Stand durch Beobachtung belegt."
        if getattr(event, "source", "") == "confirmation":
            return "Dokumentierter Stand wurde bestätigt."
        return evidence_label

    def _dashboard_summary_row(self, label: str, value: str) -> QFrame:
        row = self._card("soft")
        row.setObjectName("StudentProfileDashboardSummaryRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 8, 10, 8)
        title = QLabel(label)
        set_label_style(title, "card_title")
        count = QLabel(value)
        set_label_style(count, "small")
        layout.addWidget(title, 1)
        layout.addWidget(count)
        return row

    def _overview_text(self, text: str, style: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        set_label_style(label, style)
        return label

    def _render_overview_recent_observations(
        self,
        observations: tuple[ObservationListItem, ...],
    ) -> None:
        if not observations:
            self.overview_recent_layout.addWidget(
                self._overview_text("Noch keine Beobachtungen dokumentiert.", "subtle")
            )
            return
        for observation in sorted(
            observations,
            key=lambda item: item.date_text,
            reverse=True,
        )[:3]:
            parts = [
                observation.date_text,
                observation.subject_display_name,
                observation.context,
                self._note_preview(observation.note, 72),
            ]
            self.overview_recent_layout.addWidget(
                self._overview_text(" · ".join(part for part in parts if part), "small")
            )

    def set_student(
        self,
        student: StudentDetailViewModel | None,
        observations: tuple[ObservationListItem, ...] = (),
        competency_groups: tuple[StudentCompetencySubjectGroup, ...] = (),
        report_preview: StudentReportPreviewViewModel | None = None,
        documentation_statuses: tuple[StudentDocumentationSubjectStatus, ...] = (),
        documents: tuple[StudentDocumentViewModel, ...] = (),
        competency_cockpit: StudentCompetencyCockpitViewModel | None = None,
        profile_dashboard: StudentProfileDashboardViewModel | None = None,
        report_overview: ReportOverviewViewModel | None = None,
        documentation_subjects: (
            StudentDocumentationSubjectProjectionViewModel | None
        ) = None,
    ) -> None:
        """Render selected student or empty state."""
        previous_student_id = (
            self.current_student.student_id
            if self.current_student is not None
            else None
        )
        previous_tab_index = self.profile_tabs.currentIndex()
        self._capture_profile_scroll_positions()

        self.current_student = student
        self.current_profile_dashboard = (
            profile_dashboard or empty_student_profile_dashboard()
        )
        should_reset_tab = (
            student is None
            or previous_student_id is None
            or previous_student_id != student.student_id
        )
        if should_reset_tab:
            self.profile_tabs.setCurrentIndex(0)
            self._competency_expanded_keys.clear()
            self._report_subjects_expanded = False
            self._report_timeline_initialized = False
            self._set_documentation_subjects_expanded(False)
            self.reset_competency_cockpit_filters()

        if student is None:
            self.name_label.setText("Kein Schüler ausgewählt")
            self._update_profile_header_context()
            self.profile_avatar.setText("")
            self.action_feedback_label.setText("")
            self.set_observations(())
            self.set_competency_cockpit(None)
            self.set_report_preview(None)
            self.set_report_overview(None)
            self.set_documents(())
            self.set_documentation_subjects(None)
            self._render_profile_overview(
                None,
                (),
                self.current_profile_dashboard,
            )
            return
        self.name_label.setText(student.display_name)
        self.profile_avatar.setText(
            "".join(
                part[:1]
                for part in student.display_name.split()[:2]
                if part
            ).upper()
        )
        self.profile_avatar.setAccessibleName(f"Avatar von {student.display_name}")
        self._update_profile_header_context()
        self.action_feedback_label.setText("")
        self._render_profile_overview(
            student,
            observations,
            self.current_profile_dashboard,
        )
        self.set_observations(
            observations,
            preserve_view_state=not should_reset_tab,
        )
        self.set_competency_cockpit(competency_cockpit)
        self.set_report_preview(report_preview)
        self.set_report_overview(report_overview)
        self.set_documents(documents)
        self.set_documentation_subjects(documentation_subjects)

        if not should_reset_tab and 0 <= previous_tab_index < self.profile_tabs.count():
            self.profile_tabs.setCurrentIndex(previous_tab_index)
            self._restore_profile_scroll_positions()
        self._update_profile_header_context()

    def set_observations(
        self,
        observations: tuple[ObservationListItem, ...],
        *,
        preserve_view_state: bool = False,
    ) -> None:
        """Render persisted observations for the current profile."""
        self.current_observations = observations
        if not preserve_view_state:
            self.show_all_observations = False
            self._focused_observation_id = ""
        self._populate_observation_subject_filter(observations)
        self.apply_observation_filters()

    def _capture_profile_scroll_positions(self) -> None:
        """Keep profile-local tab positions while the same student refreshes."""
        self._profile_scroll_positions = {
            index: scroll_area.verticalScrollBar().value()
            for index in range(self.profile_tabs.count())
            if (scroll_area := self.profile_tabs.widget(index)) is not None
        }

    def _restore_profile_scroll_positions(self) -> None:
        """Restore saved positions; Qt clamps values to rebuilt tab content."""
        for index, position in self._profile_scroll_positions.items():
            scroll_area = self.profile_tabs.widget(index)
            if isinstance(scroll_area, QScrollArea):
                scroll_area.verticalScrollBar().setValue(position)

    def apply_observation_filters(self) -> None:
        """Render observations matching the profile-local filter state."""
        self._clear_observations()
        if hasattr(self, "observation_filter_bar"):
            active_labels = tuple(
                label
                for label in (
                    (
                        f"Fach: {self.observation_subject_filter.currentText()}"
                        if self.observation_subject_filter.currentData()
                        else ""
                    ),
                    (
                        f"Bewertung: {self.observation_rating_filter.currentText()}"
                        if self.observation_rating_filter.currentText() != "Alle"
                        else ""
                    ),
                )
                if label
            )
            self.observation_filter_bar.set_context_filter(
                " · ".join(active_labels),
                bool(active_labels),
            )
        if not self.current_observations:
            self.observation_show_all_button.setVisible(False)
            self.observations_layout.addWidget(
                self._empty_observations_card()
            )
            return
        filtered_observations = self._filtered_observations()
        if not filtered_observations:
            self.observation_show_all_button.setVisible(False)
            self.observations_layout.addWidget(
                self._empty_observations_card(
                    "Keine passenden Beobachtungen.",
                    "Filter ändern oder zurücksetzen.",
                )
            )
            return
        visible_observations = self._visible_observations(filtered_observations)
        for observation in visible_observations:
            self.observations_layout.addWidget(
                self._observation_card(observation)
            )
        self._update_observation_limit_action(filtered_observations)

    def _empty_observations_card(
        self,
        title: str | None = None,
        hint: str | None = None,
    ) -> QFrame:
        card = EmptyState(
            hint or PROFILE_SECTION_PLACEHOLDERS["observations_hint"],
            title=title or PROFILE_SECTION_PLACEHOLDERS["observations_title"],
        )
        if title is None:
            action = QPushButton("Neue Beobachtung")
            configure_button(action, "primary", "Erste Beobachtung erfassen")
            action.clicked.connect(self._request_new_observation)
            card.layout().addWidget(action, 0, Qt.AlignmentFlag.AlignCenter)
        return card

    def _populate_observation_subject_filter(
        self,
        observations: tuple[ObservationListItem, ...],
    ) -> None:
        current_subject = str(self.observation_subject_filter.currentData() or "")
        subjects: dict[str, str] = {}
        for observation in observations:
            subject_label = observation.subject_display_name or "-"
            subjects.setdefault(subject_label, subject_label)
        self.observation_subject_filter.blockSignals(True)
        try:
            self.observation_subject_filter.clear()
            self.observation_subject_filter.addItem("Alle", "")
            for subject_label in subjects:
                self.observation_subject_filter.addItem(subject_label, subject_label)
            subject_index = self.observation_subject_filter.findData(current_subject)
            if subject_index >= 0:
                self.observation_subject_filter.setCurrentIndex(subject_index)
        finally:
            self.observation_subject_filter.blockSignals(False)
        self._set_observation_filters_enabled(bool(observations))

    def _set_observation_filters_enabled(self, enabled: bool) -> None:
        self.observation_subject_filter.setEnabled(enabled)
        self.observation_rating_filter.setEnabled(enabled)
        self.observation_search_input.setEnabled(enabled)
        self.observation_reset_button.setEnabled(enabled)

    def reset_observation_filters(self) -> None:
        """Reset all profile-local observation filters."""
        self.show_all_observations = False
        self.observation_subject_filter.setCurrentIndex(0)
        self.observation_rating_filter.setCurrentIndex(0)
        self.observation_search_input.clear()
        self.apply_observation_filters()

    def toggle_observation_limit(self) -> None:
        """Toggle between the compact observation limit and all observations."""
        self.show_all_observations = not self.show_all_observations
        self.apply_observation_filters()

    def _filtered_observations(self) -> tuple[ObservationListItem, ...]:
        subject_filter = str(self.observation_subject_filter.currentData() or "")
        rating_filter = self.observation_rating_filter.currentText()
        search_text = self.observation_search_input.text().strip().casefold()
        return tuple(
            observation
            for observation in self.current_observations
            if self._matches_observation_filters(
                observation,
                subject_filter,
                rating_filter,
                search_text,
            )
        )

    def _visible_observations(
        self,
        observations: tuple[ObservationListItem, ...],
    ) -> tuple[ObservationListItem, ...]:
        if self._observation_filter_is_active() or self.show_all_observations:
            return observations
        return observations[: self.DEFAULT_OBSERVATION_LIMIT]

    def _update_observation_limit_action(
        self,
        observations: tuple[ObservationListItem, ...],
    ) -> None:
        should_show = (
            not self._observation_filter_is_active()
            and len(observations) > self.DEFAULT_OBSERVATION_LIMIT
        )
        self.observation_show_all_button.setVisible(should_show)
        if not should_show:
            self.observation_show_all_button.setText("")
            return
        if self.show_all_observations:
            self.observation_show_all_button.setText("Weniger anzeigen")
        else:
            self.observation_show_all_button.setText(
                f"Alle Beobachtungen anzeigen ({len(observations)})"
            )

    def _observation_filter_is_active(self) -> bool:
        return any((
            bool(str(self.observation_subject_filter.currentData() or "")),
            self.observation_rating_filter.currentText() != "Alle",
            bool(self.observation_search_input.text().strip()),
        ))

    def _matches_observation_filters(
        self,
        observation: ObservationListItem,
        subject_filter: str,
        rating_filter: str,
        search_text: str,
    ) -> bool:
        if subject_filter and observation.subject_display_name != subject_filter:
            return False
        if rating_filter != "Alle" and not any(
            rating.rating == rating_filter for rating in observation.competency_ratings
        ):
            return False
        if search_text and search_text not in self._observation_search_text(observation):
            return False
        return True

    def _observation_search_text(self, observation: ObservationListItem) -> str:
        search_parts = [
            observation.context,
            observation.note,
            *(
                " ".join((
                    rating.learning_area,
                    rating.competency_group,
                    rating.competency_text,
                    rating.subject_display_name,
                ))
                for rating in observation.competency_ratings
            ),
        ]
        return " ".join(search_parts).casefold()

    def _observation_card(self, observation: ObservationListItem) -> QFrame:
        card = self._card("soft")
        card.setObjectName("ProfileObservationCard")
        card.setProperty("observation_id", observation.observation_id)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        details_widget = QWidget()
        details_widget.setVisible(False)
        details_button = QPushButton("Details anzeigen")
        details_button.setObjectName("ObservationTextActionButton")
        def toggle_details() -> None:
            self._toggle_observation_details(details_widget, details_button)

        details_button.clicked.connect(lambda _checked=False: toggle_details())
        self._make_clickable_card(card, toggle_details, "Details anzeigen")
        layout.addLayout(self._observation_header(observation, details_button))
        layout.addWidget(self._observation_summary(observation))
        if observation.observation_id == self._focused_observation_id:
            focused_label = QLabel("Aus dem Kompetenzverlauf geöffnet")
            focused_label.setObjectName("ProfileObservationFocusHint")
            set_label_style(focused_label, "subtle")
            layout.addWidget(focused_label)
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 4, 0, 0)
        details_layout.setSpacing(5)
        details_layout.addWidget(self._observation_field("Notiz", observation.note or "-"))
        competencies_title = QLabel("Kompetenzen")
        set_label_style(competencies_title, "field_label")
        details_layout.addWidget(competencies_title)
        if not observation.competency_ratings:
            empty_competencies = QLabel(
                "Diese Beobachtung wurde ohne Kompetenzbezug erfasst."
            )
            set_label_style(empty_competencies, "subtle")
            details_layout.addWidget(empty_competencies)
            details_layout.addWidget(self._observation_attachments_block(observation))
            details_layout.addLayout(self._observation_actions(observation))
            layout.addWidget(details_widget)
            return card
        for rating in observation.competency_ratings:
            details_layout.addWidget(self._rating_row(rating))
        details_layout.addWidget(self._observation_attachments_block(observation))
        details_layout.addLayout(self._observation_actions(observation))
        layout.addWidget(details_widget)
        return card

    def _observation_header(
        self,
        observation: ObservationListItem,
        details_button: QPushButton,
    ) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        date_label = QLabel(observation.date_text)
        set_label_style(date_label, "card_title")
        subject_label = StatusBadge(observation.subject_display_name or "-", tone="info")
        header.addWidget(date_label, 0)
        header.addWidget(subject_label, 1)
        if observation.is_quick_observation:
            quick_label = StatusBadge("Schnellbeobachtung", tone="neutral")
            quick_label.setObjectName("ObservationQuickObservationBadge")
            header.addWidget(quick_label, 0)
        header.addWidget(details_button, 0)
        return header

    def _observation_summary(self, observation: ObservationListItem) -> QLabel:
        preview = self._note_preview(observation.note)

        competency_count = len(observation.competency_ratings)
        competency_label = (
            "1 Kompetenz"
            if competency_count == 1
            else f"{competency_count} Kompetenzen"
        )

        attachment_count = len(observation.attachments)
        attachment_label = ""
        if attachment_count == 1:
            attachment_label = "1 Anhang"
        elif attachment_count > 1:
            attachment_label = f"{attachment_count} Anhänge"

        parts = [
            observation.context or "-",
            preview,
            competency_label,
            attachment_label,
        ]
        summary = QLabel(" · ".join(part for part in parts if part))
        summary.setWordWrap(True)
        set_label_style(summary, "body")
        return summary

    def _note_preview(self, note: str, max_length: int = 90) -> str:
        cleaned_note = " ".join(note.split())
        if not cleaned_note:
            return "Keine Notiz"
        if len(cleaned_note) <= max_length:
            return cleaned_note
        return f"{cleaned_note[:max_length].rstrip()}..."

    def _toggle_observation_details(
        self,
        details_widget: QWidget,
        details_button: QPushButton,
    ) -> None:
        details_widget.setVisible(details_widget.isHidden())
        details_button.setText(
            "Details ausblenden"
            if not details_widget.isHidden()
            else "Details anzeigen"
        )
        animate_feedback(details_button, key="profile_observation_disclosure")

    def _observation_actions(self, observation: ObservationListItem) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 2, 0, 0)
        actions.setSpacing(8)
        edit_button = QPushButton("Bearbeiten")
        delete_button = QPushButton("Löschen")
        edit_button.setObjectName("ObservationTextActionButton")
        delete_button.setObjectName("ObservationTextActionButton")
        edit_button.clicked.connect(
            lambda _checked=False, observation_id=observation.observation_id: (
                self.observation_edit_requested.emit(observation_id)
            )
        )
        delete_button.clicked.connect(
            lambda _checked=False, observation_id=observation.observation_id: (
                self.observation_delete_requested.emit(observation_id)
            )
        )
        actions.addStretch()
        actions.addWidget(edit_button)
        actions.addWidget(delete_button)
        return actions

    def _observation_field(self, label: str, value: str) -> QLabel:
        field = QLabel(f"{label}: {value}")
        field.setWordWrap(True)
        set_label_style(field, "body")
        return field

    def _rating_row(self, rating: object) -> QLabel:
        rating_label = QLabel(
            f"{getattr(rating, 'rating', '')}  "
            f"{getattr(rating, 'learning_area', '')}"
        )
        rating_label.setWordWrap(True)
        rating_label.setToolTip(getattr(rating, "competency_text", ""))
        detail_parts = (
            getattr(rating, "subject_display_name", ""),
            getattr(rating, "competency_group", ""),
        )
        detail = " · ".join(part for part in detail_parts if part)
        if detail:
            rating_label.setText(f"{rating_label.text()} · {detail}")
        set_label_style(rating_label, "small")
        return rating_label

    def _observation_attachments_block(
        self,
        observation: ObservationListItem,
    ) -> QWidget:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(3)
        title = QLabel("Dokumente & Medien")
        set_label_style(title, "field_label")
        layout.addWidget(title)
        if not observation.attachments:
            empty = QLabel(
                "Zu dieser Beobachtung wurden keine Dokumente oder Medien hinzugefügt."
            )
            set_label_style(empty, "subtle")
            layout.addWidget(empty)
            return block
        for document in observation.attachments:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            line = QLabel(
                f"{getattr(document, 'document_type', '')} · "
                f"{getattr(document, 'display_title', '')}"
            )
            line.setWordWrap(True)
            set_label_style(line, "small")

            open_button = QPushButton("Öffnen")
            open_button.clicked.connect(
                lambda _checked=False, file_path=document.file_path: (
                    self.open_document_file(file_path)
                )
            )

            row_layout.addWidget(line, 1)
            row_layout.addWidget(open_button, 0)
            layout.addWidget(row)
        return block

    def set_competency_cockpit(
        self,
        cockpit: StudentCompetencyCockpitViewModel | None,
    ) -> None:
        """Store and render the read-only cockpit from the Sprint-6B projection."""
        self.current_competency_cockpit = cockpit
        self._populate_competency_subject_filter(cockpit)
        self.apply_competency_cockpit_filters()

    def _populate_competency_subject_filter(
        self,
        cockpit: StudentCompetencyCockpitViewModel | None,
    ) -> None:
        selected_subject_id = self.competency_subject_filter.currentData()
        self.competency_subject_filter.blockSignals(True)
        self.competency_subject_filter.clear()
        self.competency_subject_filter.addItem("Alle Fächer", "")
        if cockpit is not None:
            for subject in cockpit.subjects:
                self.competency_subject_filter.addItem(
                    subject.subject_display_name, subject.subject_id
                )
        selected_index = self.competency_subject_filter.findData(selected_subject_id)
        self.competency_subject_filter.setCurrentIndex(max(selected_index, 0))
        self.competency_subject_filter.blockSignals(False)

    def apply_competency_cockpit_filters(self, _index: int = 0) -> None:
        """Filter only visible canonical cockpit rows without changing their values."""
        self._clear_layout(self.competency_cockpit_layout)
        cockpit = self.current_competency_cockpit
        if cockpit is None:
            self.competency_cockpit_layout.addWidget(
                self._empty_competency_cockpit_card()
            )
            return
        subject_id = self.competency_subject_filter.currentData() or ""
        documentation_filter = self.competency_documentation_filter.currentData() or ""
        learning_stage_filter = self.competency_stage_filter.current_key()
        search_text = self.competency_search_input.text().strip().casefold()
        active_labels = tuple(
            label
            for label in (
                (
                    f"Fach: {self.competency_subject_filter.currentText()}"
                    if subject_id
                    else ""
                ),
                (
                    f"Stand: {self.competency_documentation_filter.currentText()}"
                    if documentation_filter
                    else ""
                ),
            )
            if label
        )
        self.competency_filter_bar.set_context_filter(
            " · ".join(active_labels),
            bool(active_labels),
        )
        visible_subjects = tuple(
            (subject, filtered_subject)
            for subject in cockpit.subjects
            if (not subject_id or subject.subject_id == subject_id)
            for filtered_subject in (
                self._filtered_cockpit_subject(
                    subject,
                    documentation_filter,
                    learning_stage_filter,
                    search_text,
                ),
            )
            if filtered_subject is not None
        )
        if not cockpit.subjects:
            self.competency_cockpit_layout.addWidget(
                self._empty_competency_cockpit_card()
            )
        elif not visible_subjects:
            self.competency_cockpit_layout.addWidget(
                self._empty_filtered_competency_cockpit_card(subject_id)
            )
        for source_subject, filtered_subject in visible_subjects:
            self.competency_cockpit_layout.addWidget(
                self._cockpit_subject_card(
                    filtered_subject,
                    historical=False,
                    progress_subject=source_subject,
                )
            )
        if cockpit.historical_subjects:
            self.competency_cockpit_layout.addWidget(
                self._historical_competency_section(cockpit.historical_subjects)
            )

    def reset_competency_cockpit_filters(self) -> None:
        self.competency_subject_filter.setCurrentIndex(0)
        self.competency_documentation_filter.setCurrentIndex(0)
        self.competency_search_input.clear()
        self.competency_stage_filter.set_current_key("matching")
        self.apply_competency_cockpit_filters()

    def _filtered_cockpit_subject(
        self,
        subject: StudentCompetencyCockpitSubjectViewModel,
        documentation_filter: str,
        learning_stage_filter: str,
        search_text: str,
    ) -> StudentCompetencyCockpitSubjectViewModel | None:
        areas = tuple(
            filtered_area
            for area in subject.learning_areas
            for filtered_area in (
                self._filtered_cockpit_learning_area(
                    area,
                    documentation_filter,
                    learning_stage_filter,
                    search_text,
                ),
            )
            if filtered_area is not None
        )
        if not areas:
            return None
        return StudentCompetencyCockpitSubjectViewModel(
            subject.subject_id, subject.subject_display_name, areas
        )

    def _filtered_cockpit_learning_area(
        self,
        area: StudentCompetencyCockpitLearningAreaViewModel,
        documentation_filter: str,
        learning_stage_filter: str,
        search_text: str,
    ) -> StudentCompetencyCockpitLearningAreaViewModel | None:
        topics = tuple(
            StudentCompetencyCockpitTopicViewModel(
                topic.competency_group,
                tuple(
                    competency
                    for competency in topic.competencies
                    if self._matches_competency_documentation_filter(
                        competency, documentation_filter
                    )
                    and self._matches_competency_learning_stage(
                        competency,
                        learning_stage_filter,
                    )
                    and self._matches_competency_search(
                        competency,
                        area.learning_area,
                        topic.competency_group,
                        search_text,
                    )
                ),
            )
            for topic in area.topics
        )
        visible_topics = tuple(topic for topic in topics if topic.competencies)
        if not visible_topics:
            return None
        return StudentCompetencyCockpitLearningAreaViewModel(
            area.learning_area, visible_topics
        )

    @staticmethod
    def _matches_competency_documentation_filter(
        competency: object,
        documentation_filter: str,
    ) -> bool:
        state = getattr(competency, "documentation_state")
        if not documentation_filter:
            return True
        if documentation_filter == "documented":
            return state != "undocumented"
        if documentation_filter == "confirmed":
            return state in {"confirmed", "newer_observations"}
        return state == documentation_filter

    @staticmethod
    def _matches_competency_learning_stage(
        competency: object,
        learning_stage_filter: str,
    ) -> bool:
        learning_stage = str(getattr(competency, "learning_stage", "") or "cross_stage")
        if learning_stage_filter == "all":
            return True
        if learning_stage_filter == "stage_4":
            return learning_stage in {"stage_4", "cross_stage"}
        return learning_stage in {"stage_1_3", "cross_stage"}

    @staticmethod
    def _matches_competency_search(
        competency: object,
        learning_area: str,
        topic: str,
        search_text: str,
    ) -> bool:
        if not search_text:
            return True
        haystack = " ".join((
            str(getattr(competency, "competency_label", "")),
            str(getattr(competency, "competency_text", "")),
            learning_area,
            topic,
            str(getattr(competency, "subject_display_name", "")),
        )).casefold()
        return search_text in haystack

    def _empty_competency_cockpit_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        message = QLabel(
            "Für dieses Profil sind keine aktiven Kompetenzen verfügbar. "
            "Prüfe bei Bedarf den aktiven Kompetenzkatalog."
        )
        message.setWordWrap(True)
        set_label_style(message, "body")
        layout.addWidget(message)
        return card

    def _empty_filtered_competency_cockpit_card(self, subject_id: str) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        subject_name = self.competency_subject_filter.currentText()
        message = (
            f"Für {subject_name} entsprechen keine Kompetenzen den gewählten Filtern. "
            "Ändere die Suche oder setze die Filter zurück."
            if subject_id
            else "Keine Kompetenzen entsprechen den gewählten Filtern. "
            "Ändere die Suche oder setze die Filter zurück."
        )
        label = QLabel(message)
        label.setObjectName("CompetencyCockpitEmptyFilterState")
        label.setWordWrap(True)
        set_label_style(label, "body")
        layout.addWidget(label)
        return card

    def _cockpit_subject_card(
        self,
        subject: StudentCompetencyCockpitSubjectViewModel,
        *,
        historical: bool,
        progress_subject: StudentCompetencyCockpitSubjectViewModel | None = None,
    ) -> QFrame:
        progress_subject = progress_subject or subject
        key = f"{'historical' if historical else 'current'}:subject:{subject.subject_id}"
        card = self._card("accent")
        card.setObjectName("CompetencyCockpitSubjectCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(7)
        header = QHBoxLayout()
        title = QLabel(subject.subject_display_name)
        set_label_style(title, "card_title")
        count = QLabel(
            f"{progress_subject.documented_count} / {progress_subject.total_count} Kompetenzen dokumentiert"
        )
        set_label_style(count, "small")
        button = QPushButton("Öffnen ▾")
        button.setObjectName("CompetencyCockpitSubjectButton")
        configure_button(button, "quiet", f"Fach {subject.subject_display_name} öffnen")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(count)
        header.addWidget(button)
        layout.addLayout(header)
        layout.addWidget(self._cockpit_progress(progress_subject.progress_percent))
        details = QWidget()
        details.setObjectName("CompetencyCockpitSubjectDetails")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 5, 0, 0)
        details_layout.setSpacing(7)
        for area in subject.learning_areas:
            details_layout.addWidget(
                self._cockpit_learning_area_card(
                    subject.subject_id,
                    area,
                    historical=historical,
                    progress_area=next(
                        (
                            source_area
                            for source_area in progress_subject.learning_areas
                            if source_area.learning_area == area.learning_area
                        ),
                        area,
                    ),
                )
            )
        self._configure_cockpit_toggle(key, details, button, "Öffnen ▾", "Schließen ▴")
        layout.addWidget(details)
        self._make_clickable_card(
            card,
            lambda: self._toggle_cockpit_section(
                key, details, button, "Öffnen ▾", "Schließen ▴"
            ),
            "Fach öffnen",
        )
        return card

    def _cockpit_learning_area_card(
        self,
        subject_id: str,
        area: StudentCompetencyCockpitLearningAreaViewModel,
        *,
        historical: bool,
        progress_area: StudentCompetencyCockpitLearningAreaViewModel | None = None,
    ) -> QFrame:
        progress_area = progress_area or area
        key = (
            f"{'historical' if historical else 'current'}:area:"
            f"{subject_id}:{area.learning_area}"
        )
        card = self._card("soft")
        card.setObjectName("CompetencyCockpitLearningAreaCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        header = QHBoxLayout()
        title = QLabel(area.learning_area)
        set_label_style(title, "field_label")
        count = QLabel(f"{progress_area.documented_count} / {progress_area.total_count}")
        set_label_style(count, "small")
        button = QPushButton("Öffnen ▾")
        button.setObjectName("CompetencyCockpitLearningAreaButton")
        configure_button(button, "quiet", f"Kompetenzbereich {area.learning_area} öffnen")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(count)
        header.addWidget(button)
        layout.addLayout(header)
        layout.addWidget(self._cockpit_progress(progress_area.progress_percent))
        details = QWidget()
        details.setObjectName("CompetencyCockpitLearningAreaDetails")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 4, 0, 0)
        details_layout.setSpacing(6)
        for topic in area.topics:
            details_layout.addWidget(
                self._cockpit_topic_card(
                    subject_id,
                    area.learning_area,
                    topic,
                    historical=historical,
                )
            )
        self._configure_cockpit_toggle(key, details, button, "Öffnen ▾", "Schließen ▴")
        layout.addWidget(details)
        self._make_clickable_card(
            card,
            lambda: self._toggle_cockpit_section(
                key, details, button, "Öffnen ▾", "Schließen ▴"
            ),
            f"Kompetenzbereich {area.learning_area} öffnen oder schließen",
        )
        return card

    def _cockpit_topic_card(
        self,
        subject_id: str,
        learning_area: str,
        topic: StudentCompetencyCockpitTopicViewModel,
        *,
        historical: bool,
    ) -> QFrame:
        key = (
            f"{'historical' if historical else 'current'}:topic:"
            f"{subject_id}:{learning_area}:{topic.competency_group}"
        )
        card = self._card("default")
        card.setObjectName("CompetencyCockpitTopicCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        header = QHBoxLayout()
        title = QLabel(topic.competency_group)
        set_label_style(title, "body")
        count = QLabel(f"{topic.documented_count} / {topic.total_count}")
        set_label_style(count, "subtle")
        button = QPushButton("Öffnen ▾")
        button.setObjectName("CompetencyCockpitTopicButton")
        configure_button(button, "quiet", f"Thema {topic.competency_group} öffnen")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(count)
        header.addWidget(button)
        layout.addLayout(header)
        details = QWidget()
        details.setObjectName("CompetencyCockpitTopicDetails")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 4, 0, 0)
        details_layout.setSpacing(3)
        for competency in topic.competencies:
            details_layout.addWidget(self._cockpit_competency_row(competency))
        self._configure_cockpit_toggle(key, details, button, "Öffnen ▾", "Schließen ▴")
        layout.addWidget(details)
        self._make_clickable_card(
            card,
            lambda: self._toggle_cockpit_section(
                key, details, button, "Öffnen ▾", "Schließen ▴"
            ),
            f"Thema {topic.competency_group} öffnen oder schließen",
        )
        return card

    def _cockpit_competency_row(self, competency: object) -> QWidget:
        row = self._card("default")
        row.setObjectName("CompetencyCockpitCompetencyRow")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(3)
        documented = getattr(competency, "documentation_state") != "undocumented"
        button = QPushButton(
            f"{'☑' if documented else '☐'} {getattr(competency, 'competency_label')}"
        )
        button.setObjectName("CompetencyCockpitCompetencyButton")
        button.setAccessibleName(
            f"Kompetenz {getattr(competency, 'competency_label')} öffnen"
        )
        configure_button(button, "quiet")
        details = self._cockpit_competency_details(competency)
        details.setObjectName("CompetencyCockpitCompetencyDetails")
        key = f"competency:{getattr(competency, 'competency_id')}"
        self._configure_cockpit_toggle(key, details, button, button.text(), button.text())
        layout.addWidget(button)
        layout.addWidget(details)
        self._make_clickable_card(
            row,
            lambda: self._toggle_cockpit_section(
                key, details, button, button.text(), button.text()
            ),
            f"Kompetenz {getattr(competency, 'competency_label')} öffnen oder schließen",
        )
        return row

    def _cockpit_competency_details(self, competency: object) -> QFrame:
        details = self._card()
        layout = QVBoxLayout(details)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)
        rows = (
            (
                "Kompetenz",
                getattr(competency, "competency_text")
                or getattr(competency, "competency_label"),
            ),
            ("Dokumentationszustand", getattr(competency, "documentation_state_label")),
        )
        for label, value in rows:
            line = QLabel(f"{label}: {value}")
            line.setWordWrap(True)
            set_label_style(line, "small")
            layout.addWidget(line)
        if getattr(competency, "missing_catalog_reference", False):
            catalog_hint = QLabel("Katalogreferenz nicht mehr vorhanden")
            catalog_hint.setObjectName("CompetencyCockpitMissingCatalogReferenceHint")
            set_label_style(catalog_hint, "subtle")
            layout.addWidget(catalog_hint)
        self._add_competency_confirmation_block(layout, competency)
        self._add_competency_proposal_block(layout, competency)
        self._add_competency_evidence_block(layout, competency)
        return details

    def _add_competency_confirmation_block(
        self,
        layout: QVBoxLayout,
        competency: object,
    ) -> None:
        confirmed_rating = str(getattr(competency, "confirmed_rating", ""))
        if not confirmed_rating:
            return
        title = QLabel("Bestätigter Stand")
        title.setObjectName("CompetencyCockpitConfirmationTitle")
        set_label_style(title, "field_label")
        layout.addWidget(title)
        for label, value in (
            ("Bewertung", confirmed_rating),
            ("Bestätigt am", str(getattr(competency, "confirmed_at", "")) or "-"),
        ):
            line = QLabel(f"{label}: {value}")
            line.setWordWrap(True)
            set_label_style(line, "small")
            layout.addWidget(line)
        note = str(getattr(competency, "confirmation_note", ""))
        if note:
            note_label = QLabel(f"Notiz: {note}")
            note_label.setWordWrap(True)
            set_label_style(note_label, "small")
            layout.addWidget(note_label)
        if getattr(competency, "has_observations_newer_than_confirmation", False):
            newer_label = QLabel("Neuere Beobachtungen vorhanden")
            newer_label.setObjectName("CompetencyCockpitNewerObservationsHint")
            set_label_style(newer_label, "subtle")
            layout.addWidget(newer_label)

    def _add_competency_proposal_block(
        self,
        layout: QVBoxLayout,
        competency: object,
    ) -> None:
        proposal = str(getattr(competency, "observed_proposal", ""))
        if not proposal:
            return
        title = QLabel("Vorschlag aus Beobachtungen")
        title.setObjectName("CompetencyCockpitProposalTitle")
        set_label_style(title, "field_label")
        layout.addWidget(title)
        proposal_label = QLabel(f"Bewertung: {proposal}")
        set_label_style(proposal_label, "small")
        layout.addWidget(proposal_label)

    def _add_competency_evidence_block(
        self,
        layout: QVBoxLayout,
        competency: object,
    ) -> None:
        evidence = tuple(getattr(competency, "evidence", ()))
        title = QLabel("Beobachtungsverlauf")
        title.setObjectName("CompetencyCockpitEvidenceTitle")
        set_label_style(title, "field_label")
        layout.addWidget(title)
        if not evidence:
            empty = QLabel(
                "Zu dieser Kompetenz gibt es noch keine aktive Beobachtung. "
                "Eine neue Beobachtung kann den Verlauf ergänzen."
            )
            empty.setObjectName("CompetencyCockpitEvidenceEmptyState")
            empty.setWordWrap(True)
            set_label_style(empty, "subtle")
            layout.addWidget(empty)
            return
        for item in evidence:
            layout.addWidget(self._competency_evidence_row(item))

    def _competency_evidence_row(self, evidence: object) -> QFrame:
        row = self._card()
        row.setObjectName("CompetencyCockpitEvidenceRow")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)
        header = QLabel(
            f"{getattr(evidence, 'observation_date')} · Bewertung: "
            f"{getattr(evidence, 'rating')}"
        )
        set_label_style(header, "small")
        layout.addWidget(header)
        context = str(getattr(evidence, "context", ""))
        if context:
            context_label = QLabel(context)
            context_label.setWordWrap(True)
            set_label_style(context_label, "subtle")
            layout.addWidget(context_label)
        actions = QHBoxLayout()
        open_button = QPushButton("Beobachtung öffnen")
        open_button.setObjectName("CompetencyCockpitObservationOpenButton")
        edit_button = QPushButton("Bearbeiten")
        edit_button.setObjectName("CompetencyCockpitObservationEditButton")
        observation_id = str(getattr(evidence, "observation_id"))
        open_button.clicked.connect(
            lambda _checked=False, observation_id=observation_id: (
                self._show_observations_tab(observation_id)
            )
        )
        edit_button.clicked.connect(
            lambda _checked=False, observation_id=observation_id: (
                self.observation_edit_requested.emit(observation_id)
            )
        )
        actions.addWidget(open_button)
        actions.addWidget(edit_button)
        actions.addStretch()
        layout.addLayout(actions)
        return row

    def _historical_competency_section(
        self,
        subjects: tuple[StudentCompetencyCockpitSubjectViewModel, ...],
    ) -> QFrame:
        key = "historical"
        card = self._card()
        card.setObjectName("CompetencyCockpitHistoricalCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        button = QPushButton("Historisch dokumentiert ▾")
        button.setObjectName("CompetencyCockpitHistoricalButton")
        details = QWidget()
        details.setObjectName("CompetencyCockpitHistoricalDetails")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 6, 0, 0)
        details_layout.setSpacing(7)
        for subject in subjects:
            details_layout.addWidget(self._cockpit_subject_card(subject, historical=True))
        self._configure_cockpit_toggle(
            key, details, button, "Historisch dokumentiert ▾", "Historisch dokumentiert ▴"
        )
        layout.addWidget(button)
        layout.addWidget(details)
        return card

    def _cockpit_progress(self, percent: int) -> QProgressBar:
        progress = QProgressBar()
        progress.setObjectName("CompetencyCockpitProgressBar")
        progress.setRange(0, 100)
        progress.setValue(percent)
        progress.setTextVisible(False)
        progress.setAccessibleName(f"Dokumentationsfortschritt {percent} Prozent")
        return progress

    def _configure_cockpit_toggle(
        self,
        key: str,
        details: QWidget,
        button: QPushButton,
        collapsed_text: str,
        expanded_text: str,
    ) -> None:
        expanded = key in self._competency_expanded_keys
        details.setVisible(expanded)
        button.setText(expanded_text if expanded else collapsed_text)
        button.setAccessibleDescription(
            "Bereich ist geöffnet" if expanded else "Bereich ist geschlossen"
        )
        button.clicked.connect(
            lambda _checked=False: self._toggle_cockpit_section(
                key, details, button, collapsed_text, expanded_text
            )
        )

    def _toggle_cockpit_section(
        self,
        key: str,
        details: QWidget,
        button: QPushButton,
        collapsed_text: str,
        expanded_text: str,
    ) -> None:
        expanded = details.isHidden()
        details.setVisible(expanded)
        if expanded:
            self._competency_expanded_keys.add(key)
        else:
            self._competency_expanded_keys.discard(key)
        button.setText(expanded_text if expanded else collapsed_text)
        button.setAccessibleDescription(
            "Bereich ist geöffnet" if expanded else "Bereich ist geschlossen"
        )
        animate_feedback(button, key="competency_cockpit_disclosure")

    def _show_observations_tab(self, observation_id: str = "") -> None:
        """Show the existing observation tab and mark a requested observation."""
        self._focused_observation_id = observation_id
        if observation_id:
            self.reset_observation_filters()
            self.show_all_observations = True
            self.apply_observation_filters()
        self.profile_tabs.setCurrentIndex(1)

    def set_report_overview(
        self,
        overview: ReportOverviewViewModel | None,
    ) -> None:
        """Render the display-ready Paket-1 projection without recalculation."""
        self.current_report_overview = overview or empty_report_overview()
        current = self.current_report_overview
        self.report_period_summary.setText(current.report_period_label)
        self.report_period_summary.setAccessibleDescription(
            (
                f"Beginn {current.report_period_start_label}, "
                f"Ende {current.report_period_end_label}"
                if current.report_content_available
                else "Kein eindeutiger Berichtsentwurf ausgewählt"
            )
        )
        self._render_report_status_card(
            self.report_status_layout,
            self.report_status_card,
            current.report_status,
        )
        self._render_report_status_card(
            self.learning_conference_status_layout,
            self.learning_conference_status_card,
            current.learning_conference_status,
        )
        self._render_report_next_steps(current.next_steps)
        self._render_report_subjects(current)
        self._render_report_timeline(current.timeline_events)
        self._render_report_history(current.history)
        self._update_report_tab_order()

    def _update_report_tab_order(self) -> None:
        """Keep keyboard traversal aligned with the visible card reading order."""
        ordered_buttons: list[QPushButton] = []
        for card in self._report_overview_cards:
            ordered_buttons.extend(card.findChildren(QPushButton))
        for previous, following in zip(ordered_buttons, ordered_buttons[1:]):
            QWidget.setTabOrder(previous, following)

    def _render_report_status_card(
        self,
        layout: QVBoxLayout,
        card: QFrame,
        status: ReportStatusCardViewModel | LearningConferenceStatusCardViewModel,
    ) -> None:
        self._clear_layout(layout)
        tone = {
            "finalized": "success",
            "completed": "success",
            "integrity_error": "error",
            "draft_changed": "warning",
            "multiple_drafts": "info",
        }.get(status.state, "neutral")
        badge = StatusBadge(status.status_label, tone=tone)
        badge.setAccessibleName(f"Status: {status.status_label}")
        heading = QWidget()
        heading_layout = QHBoxLayout(heading)
        heading_layout.setContentsMargins(0, 0, 0, 0)
        heading_layout.setSpacing(8)
        heading_layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        heading_layout.addStretch(1)
        if status.primary_action is not None:
            heading_layout.addWidget(
                self._report_action_button(status.primary_action, role="secondary")
            )
        layout.addWidget(heading)
        metadata = QLabel(
            "  ·  ".join(
                (
                    f"Zeitraum: {status.period_label}",
                    f"Revision: {status.revision_label}",
                    f"Letzte Änderung: {status.last_changed_label}",
                )
            )
        )
        metadata.setObjectName("ReportOverviewStatusMetadata")
        metadata.setWordWrap(True)
        set_label_style(metadata, "small")
        layout.addWidget(metadata)
        hint = QLabel(status.hint_text)
        hint.setWordWrap(True)
        set_label_style(hint, "subtle")
        layout.addWidget(hint)
        card.setAccessibleName(
            ". ".join(
                (
                    status.status_label,
                    status.period_label,
                    status.revision_label,
                    status.last_changed_label,
                )
            )
        )

    def _render_report_next_steps(
        self,
        steps: tuple[ReportNextStepViewModel, ...],
    ) -> None:
        self._clear_layout(self.next_steps_layout)
        if not steps:
            self.next_steps_layout.addWidget(self._report_compact_empty_state(
                "Aus den vorhandenen fachlichen Zuständen ergibt sich aktuell "
                "keine weitere Aktion.",
                title="Kein offener Schritt",
            ))
            return
        for step in steps:
            row = QWidget()
            row.setObjectName("ReportOverviewNextStepRow")
            row.setAccessibleName(
                f"{step.title}. {step.detail}. Aktion: {step.action.label}."
            )
            row.setToolTip(step.detail)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(10)
            title = QLabel(f"•  {step.title}")
            title.setWordWrap(True)
            set_label_style(title, "card_title")
            title.setToolTip(step.detail)
            row_layout.addWidget(title, 1)
            row_layout.addWidget(
                self._report_action_button(step.action, role="quiet"),
                0,
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter,
            )
            self.next_steps_layout.addWidget(row)

    def _render_report_subjects(self, overview: ReportOverviewViewModel) -> None:
        self._clear_layout(self.report_subjects_layout)
        for warning in overview.projection_warnings:
            warning_label = QLabel(warning.text)
            warning_label.setObjectName("ReportOverviewProjectionWarning")
            warning_label.setWordWrap(True)
            warning_label.setAccessibleName(warning.accessible_name)
            set_label_style(warning_label, "subtle")
            self.report_subjects_layout.addWidget(warning_label)
        if not overview.subject_documentation:
            self.report_subjects_layout.addWidget(self._report_compact_empty_state(
                "Im aktuellen Schuljahr sind keine relevanten Fächer verfügbar.",
                title="Keine Fachkarten im aktuellen Schuljahr",
            ))
            return
        subjects = (
            overview.subject_documentation
            if self._report_subjects_expanded
            else overview.subject_documentation[:4]
        )
        tile_container = QWidget()
        tile_container.setObjectName("ReportOverviewSubjectGrid")
        tile_layout = QGridLayout(tile_container)
        tile_layout.setContentsMargins(0, 0, 0, 0)
        tile_layout.setHorizontalSpacing(10)
        tile_layout.setVerticalSpacing(10)
        tile_columns = {
            3: 4,
            2: 2,
            1: 1,
        }.get(getattr(self, "_report_overview_columns", 3), 4)
        for index, subject in enumerate(subjects):
            tile = AppCard("soft")
            tile.setObjectName("ReportOverviewSubjectTile")
            tile.setMinimumHeight(136)
            row_layout = QVBoxLayout(tile)
            row_layout.setContentsMargins(10, 9, 10, 9)
            row_layout.setSpacing(6)
            subject_header = QHBoxLayout()
            subject_header.setContentsMargins(0, 0, 0, 0)
            subject_header.setSpacing(7)
            subject_symbol = QLabel(
                REPORT_SUBJECT_SYMBOLS.get(subject.subject_id, "•")
            )
            subject_symbol.setObjectName("ReportOverviewSubjectSymbol")
            subject_symbol.setProperty("subject_id", subject.subject_id)
            subject_symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
            subject_symbol.setAccessibleName(
                f"Fachsymbol {subject.subject_name}"
            )
            label = QLabel(subject.subject_name)
            label.setWordWrap(True)
            set_label_style(label, "card_title")
            subject_header.addWidget(subject_symbol)
            subject_header.addWidget(label, 1)
            competency_count = QLabel(subject.competency_count_text)
            competency_count.setObjectName("ReportOverviewCompetencyCount")
            competency_count.setWordWrap(True)
            set_label_style(competency_count, "small")
            observations = QLabel(subject.observation_count_text)
            observations.setObjectName("ReportOverviewObservationCount")
            set_label_style(observations, "subtle")
            confirmation = None
            if subject.confirmation_count_text:
                confirmation = QLabel(subject.confirmation_count_text)
                confirmation.setObjectName("ReportOverviewConfirmationCount")
                confirmation.setWordWrap(True)
                set_label_style(confirmation, "subtle")
            segment_grid = self._report_competency_segments(subject)
            actions = QHBoxLayout()
            actions.setContentsMargins(0, 0, 0, 0)
            actions.setSpacing(8)
            evidence_button = self._report_action_button(
                subject.evidence_action,
                role="quiet",
            )
            evidence_button.setObjectName(
                f"ReportOverviewEvidenceSubject_{subject.subject_id}"
            )
            evidence_button.setAccessibleName(
                f"Belege für {subject.subject_name} ansehen"
            )
            prepare_button = self._report_action_button(
                subject.prepare_action,
                role="link",
            )
            prepare_button.setObjectName(
                f"ReportOverviewPrepareSubject_{subject.subject_id}"
            )
            prepare_button.setAccessibleName(
                f"Bericht für {subject.subject_name} vorbereiten"
            )
            row_layout.addLayout(subject_header)
            row_layout.addWidget(segment_grid)
            row_layout.addWidget(competency_count)
            row_layout.addWidget(observations)
            if confirmation is not None:
                row_layout.addWidget(confirmation)
            row_layout.addStretch(1)
            actions.addWidget(evidence_button)
            actions.addWidget(prepare_button)
            actions.addStretch(1)
            row_layout.addLayout(actions)
            tile.setAccessibleName(subject.accessible_name)
            tile_layout.addWidget(
                tile,
                index // tile_columns,
                index % tile_columns,
            )
        for column in range(tile_columns):
            tile_layout.setColumnStretch(column, 1)
        self.report_subjects_layout.addWidget(tile_container)
        if len(overview.subject_documentation) > 4:
            toggle_container = QWidget()
            toggle_row = QHBoxLayout(toggle_container)
            toggle_row.setContentsMargins(0, 0, 0, 0)
            toggle_row.addStretch(1)
            toggle = QPushButton(
                "Weniger anzeigen"
                if self._report_subjects_expanded
                else f"Alle anzeigen ({len(overview.subject_documentation)})"
            )
            toggle.setObjectName("ReportOverviewSubjectsToggle")
            configure_button(
                toggle,
                "link",
                (
                    "Fachübersicht auf vier Fächer reduzieren"
                    if self._report_subjects_expanded
                    else "Alle Fächer in der Fachübersicht anzeigen"
                ),
            )
            toggle.clicked.connect(self._toggle_report_subjects)
            toggle_row.addWidget(toggle)
            self.report_subjects_layout.addWidget(toggle_container)

    def _report_competency_segments(
        self,
        subject: ReportOverviewSubjectDocumentationViewModel,
    ) -> QWidget:
        """Render exactly one neutral segment per supplied competency identity."""
        container = QWidget()
        container.setObjectName("ReportOverviewCompetencySegments")
        container.setAccessibleName(subject.accessible_name)
        segment_layout = QGridLayout(container)
        segment_layout.setContentsMargins(0, 2, 0, 2)
        segment_layout.setHorizontalSpacing(4)
        segment_layout.setVerticalSpacing(4)
        segments_per_row = {
            3: 8,
            2: 6,
            1: 4,
        }.get(getattr(self, "_report_overview_columns", 3), 8)
        for index, competency_id in enumerate(subject.competency_ids):
            segment = QFrame()
            segment.setObjectName("ReportOverviewCompetencySegment")
            segment.setProperty("competency_id", competency_id)
            segment.setFixedSize(18, 8)
            segment_layout.addWidget(
                segment,
                index // segments_per_row,
                index % segments_per_row,
            )
        segment_layout.setColumnStretch(segments_per_row, 1)
        return container

    def _toggle_report_subjects(self) -> None:
        self._report_subjects_expanded = not self._report_subjects_expanded
        self._render_report_subjects(self.current_report_overview)
        self._update_report_tab_order()

    def _render_report_timeline(
        self,
        events: tuple[ReportOverviewTimelineEventViewModel, ...],
    ) -> None:
        previous_at_end, previous_anchor, previous_value = (
            self._capture_report_timeline_state()
        )
        self._clear_layout(self.report_timeline_layout)
        self.report_timeline_scroll = None
        self.report_timeline_track = None
        self.report_timeline_left_button = None
        self.report_timeline_right_button = None
        if not events:
            self._report_timeline_initialized = False
            self.report_timeline_layout.addWidget(
                self._report_compact_empty_state(
                    "Vorhandene Beobachtungen, abgeschlossene Dokumente und "
                    "sichere Bestätigungsstände erscheinen hier im aktuellen "
                    "Schuljahr.",
                    title="Keine Dokumentationsereignisse im aktuellen Schuljahr",
                )
            )
            return
        controls = QWidget()
        controls.setObjectName("ReportOverviewTimelineControls")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(7)
        left_button = QPushButton("‹")
        left_button.setObjectName("ReportOverviewTimelinePrevious")
        left_button.setAccessibleName(
            "Zu älteren Dokumentationsereignissen scrollen"
        )
        left_button.setToolTip(
            "Zu älteren Dokumentationsereignissen scrollen"
        )
        left_button.setFixedWidth(32)
        configure_button(left_button, "quiet")
        right_button = QPushButton("›")
        right_button.setObjectName("ReportOverviewTimelineNext")
        right_button.setAccessibleName(
            "Zu neueren Dokumentationsereignissen scrollen"
        )
        right_button.setToolTip(
            "Zu neueren Dokumentationsereignissen scrollen"
        )
        right_button.setFixedWidth(32)
        configure_button(right_button, "quiet")
        scroll = ReportTimelineScrollArea()
        scroll.setMinimumHeight(188)
        track = QWidget()
        track.setObjectName("ReportOverviewTimelineTrack")
        track_layout = QHBoxLayout(track)
        track_layout.setContentsMargins(8, 0, 8, 0)
        track_layout.setSpacing(0)
        card_width = self._report_timeline_card_width()
        icon_styles = {
            "report": ("report", "#E7F1FB", "#2F78B7"),
            "learning_conference": ("conference", "#F0EAFE", "#7959C7"),
            "observation": ("observation", "#EAF5F5", "#278D91"),
            "confirmation": ("student-record", "#E4F4EF", "#23866F"),
        }
        for index, event in enumerate(events):
            event_card = QWidget()
            event_card.setObjectName("ReportOverviewTimelineEventCard")
            event_card.setProperty(
                "source_identity",
                event.source_identity,
            )
            event_card.setFixedWidth(card_width)
            event_card.setMinimumHeight(148)
            event_card.setAccessibleName(event.accessible_name)
            event_layout = QVBoxLayout(event_card)
            event_layout.setContentsMargins(0, 6, 0, 4)
            event_layout.setSpacing(4)
            date_label = QLabel(event.date_label)
            date_label.setObjectName("ReportOverviewTimelineEventDate")
            date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            set_label_style(date_label, "small")
            event_layout.addWidget(date_label)

            axis = QHBoxLayout()
            axis.setContentsMargins(0, 0, 0, 0)
            axis.setSpacing(0)
            left_connector = QFrame()
            left_connector.setObjectName(
                "ReportOverviewTimelineConnector"
            )
            left_connector.setFixedHeight(2)
            left_connector.setProperty("edge", index == 0)
            right_connector = QFrame()
            right_connector.setObjectName(
                "ReportOverviewTimelineConnector"
            )
            right_connector.setFixedHeight(2)
            right_connector.setProperty(
                "edge",
                index == len(events) - 1,
            )
            marker = QPushButton()
            marker.setObjectName("ReportOverviewTimelineEventAction")
            marker.setFixedSize(36, 36)
            icon_name, background, border = icon_styles.get(
                event.event_type,
                ("info", "#EEF3F6", "#7B93A3"),
            )
            marker.setIcon(load_icon(icon_name))
            marker.setIconSize(QSize(18, 18))
            marker.setAccessibleName(event.accessible_name)
            marker.setToolTip(
                f"{event.date_label} · {event.title} · {event.detail_text}"
            )
            marker.setStyleSheet(
                "QPushButton#ReportOverviewTimelineEventAction {"
                f"background-color: {background};"
                f"border: 1px solid {border};"
                "border-radius: 18px;"
                "padding: 0;"
                "}"
                "QPushButton#ReportOverviewTimelineEventAction:hover {"
                "background-color: #FFFFFF;"
                "}"
                "QPushButton#ReportOverviewTimelineEventAction:focus {"
                f"border: 2px solid {border};"
                "}"
                "QPushButton#ReportOverviewTimelineEventAction:disabled {"
                f"background-color: {background};"
                f"border: 1px solid {border};"
                "}"
            )
            if event.action is not None:
                marker.clicked.connect(
                    lambda _checked=False, selected=event.action: (
                        self._dispatch_report_overview_action(selected)
                    )
                )
            else:
                marker.setEnabled(False)
            axis.addWidget(left_connector, 1)
            axis.addWidget(marker)
            axis.addWidget(right_connector, 1)
            event_layout.addLayout(axis)

            title = QLabel(event.title)
            title.setObjectName("ReportOverviewTimelineEventTitle")
            title.setWordWrap(True)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            set_label_style(title, "card_title")
            detail = QLabel(event.detail_text)
            detail.setObjectName("ReportOverviewTimelineEventDetail")
            detail.setWordWrap(True)
            detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
            set_label_style(detail, "subtle")
            event_layout.addWidget(title)
            event_layout.addWidget(detail)
            event_layout.addStretch(1)
            track_layout.addWidget(event_card)
        track.adjustSize()
        track.setMinimumSize(track.sizeHint())
        scroll.setWidget(track)
        bar = scroll.horizontalScrollBar()
        left_button.clicked.connect(
            lambda _checked=False: (
                bar.setValue(bar.value() - bar.pageStep())
            )
        )
        right_button.clicked.connect(
            lambda _checked=False: (
                bar.setValue(bar.value() + bar.pageStep())
            )
        )
        bar.rangeChanged.connect(
            lambda _minimum, _maximum: (
                self._update_report_timeline_controls()
            )
        )
        bar.valueChanged.connect(
            lambda _value: self._update_report_timeline_controls()
        )
        controls_layout.addWidget(left_button)
        controls_layout.addWidget(scroll, 1)
        controls_layout.addWidget(right_button)
        self.report_timeline_layout.addWidget(controls)
        self.report_timeline_scroll = scroll
        self.report_timeline_track = track
        self.report_timeline_left_button = left_button
        self.report_timeline_right_button = right_button
        first_render = not getattr(
            self,
            "_report_timeline_initialized",
            False,
        )

        def restore_position() -> None:
            if self.report_timeline_scroll is not scroll:
                return
            current_bar = scroll.horizontalScrollBar()
            if first_render or previous_at_end:
                current_bar.setValue(current_bar.maximum())
            elif previous_anchor:
                anchored_card = next(
                    (
                        card
                        for card in track.findChildren(QWidget)
                        if (
                            card.objectName()
                            == "ReportOverviewTimelineEventCard"
                            and tuple(
                                card.property("source_identity") or ()
                            ) == previous_anchor
                        )
                    ),
                    None,
                )
                current_bar.setValue(
                    anchored_card.x()
                    if anchored_card is not None
                    else previous_value
                )
            else:
                current_bar.setValue(previous_value)
            self._report_timeline_initialized = True
            self._update_report_timeline_controls()

        QTimer.singleShot(0, restore_position)

    def _capture_report_timeline_state(
        self,
    ) -> tuple[bool, tuple[str, ...], int]:
        scroll = getattr(self, "report_timeline_scroll", None)
        track = getattr(self, "report_timeline_track", None)
        if not isinstance(scroll, QScrollArea) or track is None:
            return False, (), 0
        bar = scroll.horizontalScrollBar()
        at_end = bar.value() >= max(bar.minimum(), bar.maximum() - 2)
        anchor = ()
        cards = tuple(
            card
            for card in track.findChildren(QWidget)
            if card.objectName() == "ReportOverviewTimelineEventCard"
        )
        for card in cards:
            if card.x() + card.width() > bar.value():
                anchor = tuple(card.property("source_identity") or ())
                break
        return at_end, anchor, bar.value()

    def _report_timeline_card_width(self) -> int:
        capacity = (
            5
            if self.width() >= 1280
            else 4
            if self.width() >= 960
            else 2
        )
        available_width = max(360, self.width() - 150)
        return max(140, int((available_width - (capacity - 1) * 8) / capacity))

    def _update_report_timeline_controls(self) -> None:
        scroll = getattr(self, "report_timeline_scroll", None)
        left_button = getattr(self, "report_timeline_left_button", None)
        right_button = getattr(self, "report_timeline_right_button", None)
        if (
            not isinstance(scroll, QScrollArea)
            or left_button is None
            or right_button is None
        ):
            return
        bar = scroll.horizontalScrollBar()
        left_button.setEnabled(bar.value() > bar.minimum())
        right_button.setEnabled(bar.value() < bar.maximum())

    def _render_report_history(
        self,
        history: tuple[ReportHistoryItemViewModel, ...],
    ) -> None:
        self._clear_layout(self.report_history_layout)
        if not history:
            self.report_history_layout.addWidget(self._report_compact_empty_state(
                "Noch keine Bericht- oder LEG-Arbeitsstände vorhanden.",
                title="Keine Historie",
            ))
            return
        for item in history:
            row = AppCard("soft")
            row.setObjectName("ReportOverviewHistoryItem")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(10)
            text = QVBoxLayout()
            text.setSpacing(2)
            title = QLabel(f"{item.document_type} · {item.version_label}")
            title.setWordWrap(True)
            set_label_style(title, "card_title")
            metadata = QLabel(
                f"{item.period_label}  ·  {item.status_label}  ·  {item.activity_label}"
            )
            metadata.setWordWrap(True)
            set_label_style(metadata, "subtle")
            text.addWidget(title)
            text.addWidget(metadata)
            row_layout.addLayout(text, 1)
            open_button = self._report_action_button(item.action, role="quiet")
            open_button.setAccessibleName(
                f"{item.document_type} {item.version_label} öffnen, "
                f"{item.period_label}, {item.status_label}"
            )
            row_layout.addWidget(open_button)
            row.setAccessibleName(
                f"{item.document_type}. {item.version_label}. {item.period_label}. "
                f"{item.status_label}. {item.activity_label}."
            )
            self.report_history_layout.addWidget(row)

    def _report_action_button(
        self,
        action: ReportOverviewActionViewModel,
        *,
        role: str,
    ) -> QPushButton:
        button = QPushButton(action.label)
        configure_button(button, role, action.label)
        button.clicked.connect(
            lambda _checked=False, selected=action: (
                self._dispatch_report_overview_action(selected)
            )
        )
        return button

    def _dispatch_report_overview_action(
        self,
        action: ReportOverviewActionViewModel,
    ) -> None:
        if self.current_student is None:
            return
        student_id = self.current_student.student_id
        if action.action_key in {"create_report", "select_report"}:
            self.report_requested.emit(student_id)
        elif action.action_key == "open_report":
            self.report_draft_requested.emit(
                student_id,
                action.target_id,
                "",
                "",
            )
        elif action.action_key == "finalize_report":
            self.report_draft_requested.emit(
                student_id,
                action.target_id,
                "",
                "revisions",
            )
        elif action.action_key == "prepare_subject":
            self.report_draft_requested.emit(
                student_id,
                action.target_id,
                action.subject_id,
                "",
            )
        elif action.action_key == "show_subject_evidence":
            self._select_profile_section("competencies")
            subject_id = action.subject_id or action.target_id
            subject_index = self.competency_subject_filter.findData(
                subject_id
            )
            if subject_index >= 0:
                self.competency_subject_filter.setCurrentIndex(subject_index)
        elif action.action_key == "show_observation":
            self._show_observations_tab(action.target_id)
        elif action.action_key == "show_competency":
            self._select_profile_section("competencies")
        elif action.action_key == "select_learning_conference":
            self.learning_conference_requested.emit(student_id)
        elif action.action_key == "open_learning_conference":
            self.learning_conference_draft_requested.emit(
                student_id,
                action.target_id,
            )
        elif action.action_key == "open_report_revision":
            self.report_revision_requested.emit(action.target_id)
        elif action.action_key == "open_learning_conference_revision":
            self.learning_conference_revision_requested.emit(action.target_id)

    def set_report_preview(
        self,
        report_preview: StudentReportPreviewViewModel | None,
    ) -> None:
        """Retain the derived report preparation for copy/export helpers."""
        self.current_report_preview = report_preview
        has_report_text = self.current_student is not None and report_preview is not None
        self.report_copy_button.setEnabled(has_report_text)
        self.report_export_button.setEnabled(has_report_text)
        self.report_feedback_label.setText("")

    def _empty_report_preview_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        empty_label = QLabel(REPORT_NO_OBSERVATIONS_MESSAGE)
        empty_label.setWordWrap(True)
        set_label_style(empty_label, "body")

        hint_label = QLabel(
            "Berichtsvorschau erscheint nach aktiven Beobachtungen."
        )
        hint_label.setWordWrap(True)
        set_label_style(hint_label, "subtle")

        layout.addWidget(empty_label)
        layout.addWidget(hint_label)
        return card

    def set_documents(
        self,
        documents: tuple[StudentDocumentViewModel, ...],
    ) -> None:
        """Render student documents and media."""
        self.current_documents = documents
        self.documents_feedback_label.setText("")
        self._clear_layout(self.documents_layout)
        if not documents:
            self.documents_layout.addWidget(self._empty_documents_card())
            return
        for document in documents:
            self.documents_layout.addWidget(self._document_row(document))

    def _empty_documents_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        empty_label = QLabel(PROFILE_SECTION_PLACEHOLDERS["documents_title"])
        empty_label.setWordWrap(True)
        set_label_style(empty_label, "body")

        hint_label = QLabel(PROFILE_SECTION_PLACEHOLDERS["documents_hint"])
        hint_label.setWordWrap(True)
        set_label_style(hint_label, "subtle")

        layout.addWidget(empty_label)
        layout.addWidget(hint_label)
        return card

    def _document_row(self, document: StudentDocumentViewModel) -> QFrame:
        row = self._card()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        text_block = QWidget()
        text_layout = QVBoxLayout(text_block)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        title = QLabel(f"{document.document_type} · {document.display_title}")
        title.setWordWrap(True)
        set_label_style(title, "body")
        meta_parts = [document.created_date_label]
        if document.observation_link_label:
            meta_parts.append(document.observation_link_label)
        meta = QLabel(" · ".join(meta_parts))
        set_label_style(meta, "subtle")
        text_layout.addWidget(title)
        text_layout.addWidget(meta)
        open_button = None
        replace_button = None
        if document.managed_encrypted:
            replace_button = QPushButton("Ersetzen")
            replace_button.setObjectName("DocumentReplaceButton")
            replace_button.clicked.connect(
                lambda _checked=False, document_id=document.document_id: (
                    self._request_document_replace(document_id)
                )
            )
        else:
            open_button = QPushButton("Öffnen")
            open_button.clicked.connect(
                lambda _checked=False, file_path=document.file_path: (
                    self.open_document_file(file_path)
                )
            )
        remove_button = QPushButton("Entfernen")
        remove_button.setObjectName("DocumentRemoveButton")
        remove_button.clicked.connect(
            lambda _checked=False, document_id=document.document_id: (
                self._request_document_remove(document_id)
            )
        )
        layout.addWidget(text_block, 1)
        if open_button is not None:
            layout.addWidget(open_button, 0)
        if replace_button is not None:
            layout.addWidget(replace_button, 0)
        layout.addWidget(remove_button, 0)
        if not document.managed_encrypted:
            self._make_clickable_card(
                row,
                lambda file_path=document.file_path: self.open_document_file(file_path),
                "Datei öffnen",
            )
        return row

    def _request_document_replace(self, document_id: str) -> None:
        if self.current_student is None:
            return
        self.document_replace_requested.emit(
            self.current_student.student_id,
            document_id,
        )

    def _request_document_remove(self, document_id: str) -> None:
        if self.current_student is None:
            return
        self.document_remove_requested.emit(
            self.current_student.student_id,
            document_id,
        )

    def open_document_file(self, file_path: str) -> None:
        """Open a document through the operating system if the path exists."""
        path = Path(file_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.resolve()

        if not path.exists():
            self.documents_feedback_label.setText(
                f"Datei wurde nicht gefunden: {path}"
            )
            return

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        if opened:
            self.documents_feedback_label.setText("Datei wird geöffnet.")
        else:
            self.documents_feedback_label.setText(
                f"Datei konnte nicht geöffnet werden: {path}"
            )

    def _report_subject_card(self, section: object) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        title = QLabel(getattr(section, "subject_display_name"))
        set_label_style(title, "card_title")
        layout.addWidget(title)
        layout.addWidget(self._report_bucket(
            "Aktueller Stand",
            getattr(section, "current_statuses"),
        ))
        layout.addWidget(self._report_bucket(
            "Stärken",
            getattr(section, "strengths"),
        ))
        layout.addWidget(self._report_bucket(
            "Entwicklung",
            getattr(section, "development"),
        ))
        layout.addWidget(self._report_bucket(
            "Unterstützungsbedarf",
            getattr(section, "support_needs"),
        ))
        layout.addWidget(self._report_evidence_block(
            getattr(section, "example_observations")
        ))
        return card

    def _report_bucket(self, title: str, competencies: tuple[object, ...]) -> QWidget:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        title_label = QLabel(title)
        set_label_style(title_label, "field_label")
        layout.addWidget(title_label)
        if not competencies:
            empty_label = QLabel(
                "Für diesen Abschnitt wurden keine Kompetenzen zugeordnet."
            )
            set_label_style(empty_label, "subtle")
            layout.addWidget(empty_label)
            return block
        for competency in competencies:
            line = QLabel(getattr(competency, "display_label"))
            line.setWordWrap(True)
            set_label_style(line, "small")
            layout.addWidget(line)
        return block

    def _report_evidence_block(
        self,
        observations: tuple[object, ...],
    ) -> QWidget:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        title_label = QLabel("Beispielbeobachtungen")
        set_label_style(title_label, "field_label")
        layout.addWidget(title_label)
        if not observations:
            empty_label = QLabel(
                "Für diesen Abschnitt wurden keine passenden Beobachtungsbelege ausgewählt."
            )
            set_label_style(empty_label, "subtle")
            layout.addWidget(empty_label)
            return block
        for observation in observations:
            line = QLabel(getattr(observation, "display_label"))
            line.setWordWrap(True)
            set_label_style(line, "small")
            layout.addWidget(line)
            competencies = QLabel(
                " · ".join(getattr(observation, "competency_labels"))
            )
            competencies.setWordWrap(True)
            set_label_style(competencies, "subtle")
            layout.addWidget(competencies)
        return block

    def report_text(self) -> str:
        """Return the current report preparation as plain text."""
        if self.current_student is None:
            return ""
        return format_student_report_preview_text(
            self.current_student,
            self.current_report_preview,
        )

    def copy_report_text_to_clipboard(self) -> None:
        """Copy the current report preparation into the system clipboard."""
        text = self.report_text()
        if not text:
            self.report_feedback_label.setText("Kein Bericht zum Kopieren vorhanden.")
            return
        QApplication.clipboard().setText(text)
        self.report_feedback_label.setText("Bericht wurde kopiert.")

    def export_report_text(self) -> None:
        """Ask for a text path and export the current report preparation."""
        if self.current_student is None:
            self.report_feedback_label.setText("Kein Bericht zum Exportieren vorhanden.")
            return
        target_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Bericht als Text exportieren",
            self._default_report_export_filename(),
            "Markdown-Datei (*.md);;Textdatei (*.txt)",
        )
        if not target_path:
            return
        self.export_report_text_to_path(Path(target_path))

    def export_report_text_to_path(self, target_path: Path) -> None:
        """Write the current report preparation to a text file."""
        text = self.report_text()
        if not text:
            self.report_feedback_label.setText("Kein Bericht zum Exportieren vorhanden.")
            return
        target_path.write_text(text, encoding="utf-8")
        self.report_feedback_label.setText("Bericht wurde exportiert.")

    def _default_report_export_filename(self) -> str:
        if self.current_student is None:
            filename = "Berichtsvorbereitung.md"
        else:
            safe_name = "_".join(self.current_student.display_name.split())
            safe_id = self.current_student.student_id.replace("/", "-")
            filename = f"Berichtsvorbereitung_{safe_name}_{safe_id}.md"
        if self.export_directory is None:
            return filename
        return str(self.export_directory / filename)

    def _clear_observations(self) -> None:
        self._clear_layout(self.observations_layout)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            layout_item = layout.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
                QCoreApplication.sendPostedEvents(
                    widget,
                    QEvent.Type.DeferredDelete,
                )
