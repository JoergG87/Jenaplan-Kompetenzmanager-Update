"""Quiet timetable-based dashboard for the PySide6 desktop app."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.components import (
    AppCard,
    CourseBadge,
    DialogHeader,
    PageHeader,
    SectionHeader,
    configure_button,
)
from src.desktop_app.motion import MotionDialog
from src.desktop_app.theme import set_label_style
from src.desktop_app.view_models.master_data_view_model import (
    CourseGroupViewModel,
    MasterDataItemViewModel,
    MasterDataViewModel,
)
from src.desktop_app.view_models.student_view_model import (
    DashboardDocumentationCellViewModel,
    DashboardDocumentationHeatmapViewModel,
    DashboardSuggestedStudentViewModel,
    GroupSummaryViewModel,
)
from src.desktop_app.view_models.timetable_view_model import (
    WEEKDAY_LABELS,
    TimetableOccurrenceViewModel,
    TimetableReadProjectionViewModel,
)


OVERVIEW_GROUP_EMPTY_STATE = (
    "Noch keine Stammgruppen angelegt. Lege sie unter „Stammdaten“ an."
)
OVERVIEW_COURSE_EMPTY_STATE = (
    "Noch keine Kurse angelegt. Lege sie unter „Stammdaten“ an."
)
DASHBOARD_DOCUMENTATION_HELP_TITLE = "Hilfe zu Dokumentation im Überblick"
DASHBOARD_DOCUMENTATION_HELP_TEXT = (
    "Die Übersicht zeigt für die am aktuellen Dashboard-Tag im aktuellen "
    "Schuljahr aktiv zugeordneten Kinder je Stammgruppe und "
    "dokumentationsrelevantem Fach, bei wie vielen mindestens eine Kompetenz "
    "dokumentiert ist. Berücksichtigt werden alle vorhandenen aktiven "
    "Beobachtungen mit Kompetenzzuordnung sowie Kompetenzbestätigungen; diese "
    "Dokumentationen sind nicht auf das aktuelle Schuljahr oder einen eigenen "
    "Zeitraum begrenzt. Die Abstufungen beschreiben ausschließlich den Umfang "
    "vorhandener Dokumentation. Sie bewerten weder Leistung noch "
    "Lernentwicklung und erlauben keine Aussage über Stärken, Schwächen oder "
    "Zielerreichung."
)


def dashboard_greeting(at: datetime, display_name: str | None = None) -> str:
    """Return the plain-text greeting for one explicit local instant."""
    if at.hour < 11:
        greeting = "Guten Morgen"
    elif at.hour < 18:
        greeting = "Guten Tag"
    else:
        greeting = "Guten Abend"
    return f"{greeting}, {display_name}" if display_name else greeting


class DashboardLessonCard(AppCard):
    """Keyboard- and pointer-activatable lesson block."""

    def __init__(
        self,
        occurrence: TimetableOccurrenceViewModel,
        state: str,
        activate: Callable[[], None],
    ) -> None:
        super().__init__("interactive", interactive=True)
        self._activate = activate
        self.setObjectName("DashboardLessonCard")
        self.setProperty("lessonState", state)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(
            f"{occurrence.entry.time_label}, {occurrence.entry.subject_label}, "
            f"{occurrence.entry.target_label} öffnen"
        )
        self.setMinimumWidth(150)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(5)
        header = QHBoxLayout()
        time = QLabel(occurrence.entry.time_label)
        set_label_style(time, "card_title")
        status = QLabel("JETZT" if state == "current" else "")
        status.setObjectName("DashboardLessonState")
        status.setVisible(state == "current")
        header.addWidget(time)
        header.addStretch(1)
        header.addWidget(status)
        subject = QLabel(occurrence.entry.subject_label)
        set_label_style(subject, "card_title")
        meta = QLabel(self._meta_text(occurrence))
        meta.setWordWrap(True)
        set_label_style(meta, "muted")
        layout.addLayout(header)
        layout.addWidget(subject)
        layout.addWidget(meta)
        layout.addStretch(1)

    @staticmethod
    def _meta_text(occurrence: TimetableOccurrenceViewModel) -> str:
        entry = occurrence.entry
        parts = [entry.target_type_label, entry.target_label]
        if entry.room:
            parts.append(entry.room)
        return " · ".join(parts)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_pressed(False)
            self._activate()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.set_pressed(True)
            self._activate()
            self.set_pressed(False)
            event.accept()
            return
        super().keyPressEvent(event)


class OverviewScreen(QWidget):
    """Read-only dashboard with timetable and calm navigation."""

    timetable_target_selected = Signal(str, str)
    timetable_observation_requested = Signal(str, str, str, str, str)
    timetable_student_observation_requested = Signal(str, str, str, str)
    settings_timetable_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.hero_layout = QHBoxLayout()
        self.today_layout = QHBoxLayout()
        self.heatmap_layout = QVBoxLayout()
        self.matching_children_layout = QVBoxLayout()
        self._hero_occurrence: TimetableOccurrenceViewModel | None = None
        self._documentation_help_dialog: MotionDialog | None = None
        self.documentation_help_button: QPushButton | None = None
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(14)
        self.greeting_label = QLabel("Guten Tag")
        self.greeting_label.setObjectName("DashboardGreeting")
        self.greeting_label.setTextFormat(Qt.TextFormat.PlainText)
        set_label_style(self.greeting_label, "section_title")
        outer.addWidget(self.greeting_label)
        header = PageHeader("Heute", "Unterricht und Dokumentation im Blick")
        self.header_observation_button = QPushButton("+ Beobachtung")
        configure_button(
            self.header_observation_button,
            "primary",
            "Beobachtung für die hervorgehobene Stunde vorbereiten",
        )
        self.header_observation_button.clicked.connect(
            self._emit_header_observation
        )
        header.add_action(self.header_observation_button)
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setObjectName("DashboardScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 8, 8, 16)
        layout.setSpacing(16)
        layout.addWidget(self._section_card("", self.hero_layout, "DashboardHero"))
        layout.addWidget(
            self._section_card(
                "Stundenplan heute", self.today_layout, "DashboardTimeline"
            )
        )
        layout.addWidget(
            self._section_card(
                "Passende Kinder für diese Stunde",
                self.matching_children_layout,
                "DashboardMatchingChildren",
            )
        )
        layout.addWidget(
            self._section_card(
                "Dokumentation im Überblick",
                self.heatmap_layout,
                "DashboardHeatmap",
            )
        )
        layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    def set_dashboard(
        self,
        projection: TimetableReadProjectionViewModel,
        heatmap: DashboardDocumentationHeatmapViewModel,
        at: datetime,
        has_timetable_entries: bool,
        suggested_students: tuple[DashboardSuggestedStudentViewModel, ...] = (),
        display_name: str | None = None,
    ) -> None:
        """Render canonical read projections for one explicit point in time."""
        self.greeting_label.setText(dashboard_greeting(at, display_name))
        self._clear_layout(self.hero_layout)
        self._clear_layout(self.today_layout)
        self._clear_layout(self.heatmap_layout)
        self._clear_layout(self.matching_children_layout)
        self._render_hero(projection, has_timetable_entries, at)
        self._render_today(projection, at)
        self._render_heatmap(heatmap)
        self._render_matching_children(projection, suggested_students)

    def set_membership_blocked(self, message: str) -> None:
        """Clear stale student actions and render one neutral blocking state."""
        self._hero_occurrence = None
        self.header_observation_button.setVisible(False)
        self._clear_layout(self.hero_layout)
        self._clear_layout(self.today_layout)
        self._clear_layout(self.heatmap_layout)
        self._clear_layout(self.matching_children_layout)
        blocked = QLabel(message)
        blocked.setWordWrap(True)
        blocked.setAccessibleName("Schülerbezogene Bereiche gesperrt")
        set_label_style(blocked, "muted")
        self.hero_layout.addWidget(blocked)

    def _render_hero(
        self,
        projection: TimetableReadProjectionViewModel,
        has_timetable_entries: bool,
        at: datetime,
    ) -> None:
        occurrence = projection.current or projection.next
        self._hero_occurrence = occurrence
        self.header_observation_button.setVisible(occurrence is not None)
        left = QWidget()
        left.setObjectName("DashboardHeroContent")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 2, 16, 2)
        left_layout.setSpacing(7)
        if occurrence is None:
            title = QLabel("Für diese Stunde")
            title.setObjectName("DashboardHeroTitle")
            left_layout.addWidget(title)
            message = (
                "Noch kein Stundenplan eingerichtet"
                if not has_timetable_entries
                else "Keine aktive Stunde geplant"
            )
            headline = QLabel(message)
            set_label_style(headline, "card_title")
            hint = QLabel("Nächster guter Blick: Stammgruppen und Kinder öffnen.")
            hint.setWordWrap(True)
            set_label_style(hint, "muted")
            left_layout.addWidget(headline)
            left_layout.addWidget(hint)
            actions = QHBoxLayout()
            if not has_timetable_entries:
                settings = QPushButton("Zu Einstellungen · Stundenplan")
                configure_button(settings, "secondary", "Stundenplan einrichten")
                settings.clicked.connect(self.settings_timetable_requested.emit)
                actions.addWidget(settings)
            actions.addStretch(1)
            left_layout.addLayout(actions)
            left_layout.addStretch(1)
            self.hero_layout.addWidget(left, 3)
            self.hero_layout.addWidget(
                self._hero_visual(projection.today, projection.current), 2
            )
            return

        entry = occurrence.entry
        status_text = (
            "Jetzt" if projection.current else self._next_status(occurrence, at)
        )
        status = QLabel(status_text)
        status.setObjectName("DashboardHeroStatus")
        title = QLabel("Für diese Stunde")
        title.setObjectName("DashboardHeroTitle")
        subject = QLabel(entry.subject_label)
        subject.setObjectName("DashboardHeroSubject")
        time = QLabel(entry.time_label)
        time.setObjectName("DashboardHeroTime")
        target = QLabel(f"{entry.target_type_label} · {entry.target_label}")
        set_label_style(target, "card_title")
        left_layout.addWidget(title)
        left_layout.addWidget(status)
        left_layout.addWidget(time)
        left_layout.addWidget(subject)
        left_layout.addWidget(target)
        if entry.room:
            room = QLabel(f"Raum · {entry.room}")
            set_label_style(room, "muted")
            left_layout.addWidget(room)
        actions = QHBoxLayout()
        open_target = QPushButton("Kinder anzeigen")
        configure_button(open_target, "secondary", "Kinder dieser Stunde anzeigen")
        open_target.clicked.connect(
            lambda: self.timetable_target_selected.emit(
                entry.target_type, entry.target_id
            )
        )
        actions.addWidget(open_target)
        actions.addStretch(1)
        left_layout.addLayout(actions)
        left_layout.addStretch(1)
        self.hero_layout.addWidget(left, 3)
        self.hero_layout.addWidget(
            self._hero_visual(projection.today, projection.current), 2
        )

    def _emit_header_observation(self) -> None:
        if self._hero_occurrence is not None:
            self._emit_observation(self._hero_occurrence.entry)

    def _emit_observation(self, entry: object) -> None:
        self.timetable_observation_requested.emit(
            entry.subject_id,
            entry.subject_label,
            entry.target_type,
            entry.target_id,
            entry.target_label,
        )

    @staticmethod
    def _hero_visual(
        occurrences: tuple[TimetableOccurrenceViewModel, ...],
        current: TimetableOccurrenceViewModel | None,
    ) -> QFrame:
        visual = QFrame()
        visual.setObjectName("DashboardHeroIllustrationSpace")
        layout = QVBoxLayout(visual)
        layout.setContentsMargins(24, 18, 24, 18)
        grid = QGridLayout()
        current_id = current.entry.timetable_entry_id if current is not None else ""
        for row, occurrence in enumerate(occurrences):
            time = QLabel(occurrence.entry.start_time)
            time.setObjectName("DashboardHeroVisualTime")
            grid.addWidget(time, row, 0)
            block = QFrame()
            block.setObjectName(
                "DashboardHeroVisualCurrent"
                if occurrence.entry.timetable_entry_id == current_id
                else "DashboardHeroVisualBlock"
            )
            grid.addWidget(block, row, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        return visual

    def _render_today(
        self,
        projection: TimetableReadProjectionViewModel,
        at: datetime,
    ) -> None:
        if not projection.today:
            empty = QLabel(
                "Heute sind keine aktiven Stunden geplant. "
                "Den Wochenplan kannst du unter „Einstellungen“ prüfen."
            )
            empty.setWordWrap(True)
            set_label_style(empty, "muted")
            self.today_layout.addWidget(empty)
            self.today_layout.addStretch(1)
            return
        current_id = (
            projection.current.entry.timetable_entry_id
            if projection.current is not None
            else ""
        )
        for occurrence in projection.today:
            entry = occurrence.entry
            state = (
                "current"
                if entry.timetable_entry_id == current_id
                else "past"
                if occurrence.ends_at <= at
                else "upcoming"
            )
            card = DashboardLessonCard(
                occurrence,
                state,
                lambda target_type=entry.target_type, target_id=entry.target_id: (
                    self.timetable_target_selected.emit(target_type, target_id)
                ),
            )
            self.today_layout.addWidget(card, 1)

    def _render_heatmap(
        self,
        heatmap: DashboardDocumentationHeatmapViewModel,
    ) -> None:
        if heatmap.is_empty:
            empty = QLabel(
                "Noch keine Dokumentationsübersicht verfügbar. "
                "Sie erscheint, sobald Stammgruppen und dokumentationsrelevante Fächer vorliegen."
            )
            empty.setWordWrap(True)
            set_label_style(empty, "muted")
            self.heatmap_layout.addWidget(empty)
            return
        hint = QLabel(
            "Stammgruppen × dokumentationsrelevante Fächer · keine Leistung"
        )
        set_label_style(hint, "muted")
        self.heatmap_layout.addWidget(hint)
        subjects: list[tuple[str, str]] = []
        for group in heatmap.groups:
            for cell in group.cells:
                subject = (cell.subject_id, cell.subject_display_name)
                if subject not in subjects:
                    subjects.append(subject)
        matrix = QWidget()
        matrix.setObjectName("DashboardHeatmapMatrix")
        grid = QGridLayout(matrix)
        grid.setContentsMargins(0, 4, 0, 2)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        for column, (_subject_id, subject_name) in enumerate(subjects, start=1):
            header = QLabel(subject_name)
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            set_label_style(header, "small")
            grid.addWidget(header, 0, column)
        for row, group in enumerate(heatmap.groups, start=1):
            group_label = QLabel(group.group_name)
            set_label_style(group_label, "card_title")
            grid.addWidget(group_label, row, 0)
            cells_by_subject = {cell.subject_id: cell for cell in group.cells}
            for column, (subject_id, _subject_name) in enumerate(subjects, start=1):
                cell = cells_by_subject.get(subject_id)
                if cell is not None:
                    grid.addWidget(self._heatmap_cell(cell, group.group_name), row, column)
        matrix_scroll = QScrollArea()
        matrix_scroll.setObjectName("DashboardHeatmapScroll")
        matrix_scroll.setWidgetResizable(True)
        matrix_scroll.setFrameShape(QFrame.Shape.NoFrame)
        matrix_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        matrix_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        matrix_scroll.setWidget(matrix)
        matrix_scroll.setMinimumHeight(min(250, 48 * (len(heatmap.groups) + 1)))
        self.heatmap_layout.addWidget(matrix_scroll)

    @staticmethod
    def _heatmap_cell(
        cell: DashboardDocumentationCellViewModel,
        group_name: str,
    ) -> QFrame:
        frame = QFrame()
        frame.setObjectName("DashboardHeatmapCell")
        frame.setProperty("coverageLevel", str(min(4, int(cell.coverage_ratio * 4))))
        frame.setMinimumWidth(76)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(9, 7, 9, 7)
        layout.setSpacing(6)
        marker = QFrame()
        marker.setObjectName("DashboardHeatmapMarker")
        coverage = QLabel(f"{cell.documented_count}/{cell.total_count}")
        set_label_style(coverage, "small")
        layout.addWidget(marker)
        layout.addWidget(coverage)
        spoken = (
            f"{group_name}, {cell.subject_display_name}: {cell.coverage_label}. "
            "Dokumentationsumfang, keine Leistungsbewertung."
        )
        frame.setAccessibleName(spoken)
        frame.setToolTip(spoken)
        return frame

    def _render_matching_children(
        self,
        projection: TimetableReadProjectionViewModel,
        suggested_students: tuple[DashboardSuggestedStudentViewModel, ...],
    ) -> None:
        occurrence = projection.current or projection.next
        if occurrence is None:
            empty = QLabel(
                "Ohne aktuelle oder nächste Stunde werden hier keine Kinder vorgeschlagen. "
                "Öffne den Schülerbereich für die vollständige Liste."
            )
            empty.setWordWrap(True)
            set_label_style(empty, "muted")
            self.matching_children_layout.addWidget(empty)
            return
        entry = occurrence.entry
        if not suggested_students:
            empty = QLabel(
                "Für diesen Unterrichtskontext sind keine aktiven Kinder zugeordnet. "
                "Prüfe bei Bedarf Stammgruppen, Kurse oder Kursverbünde."
            )
            empty.setWordWrap(True)
            set_label_style(empty, "muted")
            self.matching_children_layout.addWidget(empty)
        for student in suggested_students:
            row = QFrame()
            row.setObjectName("DashboardMatchingChildRow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 8, 12, 8)
            labels = QVBoxLayout()
            identity = QHBoxLayout()
            identity.setSpacing(8)
            name = QLabel(student.display_name)
            set_label_style(name, "card_title")
            identity.addWidget(name)
            identity.addWidget(
                CourseBadge(student.course_name, student.course_color_hex)
            )
            identity.addStretch(1)
            hint = QLabel(student.documentation_hint)
            set_label_style(hint, "muted")
            labels.addLayout(identity)
            labels.addWidget(hint)
            layout.addLayout(labels, 1)
            observe = QPushButton("Beobachten")
            configure_button(
                observe,
                "quiet",
                f"Neue Beobachtung für {student.display_name}",
            )
            observe.clicked.connect(
                lambda _checked=False,
                student_id=student.student_id: self.timetable_student_observation_requested.emit(
                    student_id,
                    entry.subject_id,
                    entry.subject_label,
                    entry.target_label,
                )
            )
            layout.addWidget(observe)
            self.matching_children_layout.addWidget(row)
        footer = QHBoxLayout()
        footer.addStretch(1)
        open_button = QPushButton("Alle Kinder anzeigen")
        configure_button(
            open_button,
            "secondary",
            "Alle Kinder der hervorgehobenen Stunde anzeigen",
        )
        open_button.clicked.connect(
            lambda: self.timetable_target_selected.emit(
                entry.target_type, entry.target_id
            )
        )
        footer.addWidget(open_button)
        self.matching_children_layout.addLayout(footer)

    @staticmethod
    def _next_status(
        occurrence: TimetableOccurrenceViewModel,
        at: datetime,
    ) -> str:
        if occurrence.occurrence_date == at.date():
            return "Als Nächstes · heute"
        weekday = WEEKDAY_LABELS.get(occurrence.occurrence_date.isoweekday(), "")
        return f"Nächster Unterrichtskontext · {weekday}, {occurrence.occurrence_date:%d.%m.}"

    def _section_card(
        self,
        title: str,
        content_layout: object,
        object_name: str = "",
    ) -> QFrame:
        card = AppCard("accent" if object_name == "DashboardHero" else "default")
        if object_name:
            card.setObjectName(object_name)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        if title:
            descriptions = {
                "Stundenplan heute": "Jetzt, danach und der weitere Unterrichtstag",
                "Passende Kinder für diese Stunde": "Transparente Dokumentationshilfe im aktuellen Unterrichtskontext",
                "Dokumentation im Überblick": "Neutrale Abdeckung je Stammgruppe und Fach · keine Leistung",
            }
            help_text = (
                DASHBOARD_DOCUMENTATION_HELP_TEXT
                if object_name == "DashboardHeatmap"
                else ""
            )
            header = SectionHeader(title, descriptions.get(title, ""), help_text)
            layout.addWidget(header)
            if object_name == "DashboardHeatmap" and header.help_button is not None:
                self.documentation_help_button = header.help_button
                header.help_button.clicked.connect(
                    self._open_documentation_help
                )
        layout.addLayout(content_layout)
        return card

    def _open_documentation_help(self) -> None:
        """Open the existing compact information-dialog pattern for the heatmap."""
        active_dialog = self._documentation_help_dialog
        if active_dialog is not None and active_dialog.isVisible():
            active_dialog.raise_()
            active_dialog.activateWindow()
            close_button = active_dialog.findChild(
                QPushButton,
                "DashboardDocumentationHelpCloseButton",
            )
            if close_button is not None:
                close_button.setFocus(Qt.FocusReason.OtherFocusReason)
            return

        return_button = self.documentation_help_button
        dialog = MotionDialog(self)
        dialog.setObjectName("DashboardDocumentationHelpDialog")
        dialog.setWindowTitle(DASHBOARD_DOCUMENTATION_HELP_TITLE)
        dialog.setAccessibleName(DASHBOARD_DOCUMENTATION_HELP_TITLE)
        dialog.setModal(True)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dialog.setMinimumSize(300, 220)
        host = self.window()
        dialog.resize(
            min(560, max(320, host.width() - 80)),
            min(360, max(240, host.height() - 80)),
        )

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(
            DialogHeader(
                "Dokumentation im Überblick",
                "Dokumentationshilfe",
                icon_name="info",
            )
        )

        help_scroll = QScrollArea()
        help_scroll.setObjectName("DashboardDocumentationHelpScroll")
        help_scroll.setWidgetResizable(True)
        help_scroll.setFrameShape(QFrame.Shape.NoFrame)
        help_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        help_content = QWidget()
        help_layout = QVBoxLayout(help_content)
        help_layout.setContentsMargins(0, 0, 8, 0)
        help_text = QLabel(DASHBOARD_DOCUMENTATION_HELP_TEXT)
        help_text.setObjectName("DashboardDocumentationHelpText")
        help_text.setWordWrap(True)
        help_text.setAccessibleName(
            f"Erklärung zur Dokumentationsübersicht. {DASHBOARD_DOCUMENTATION_HELP_TEXT}"
        )
        set_label_style(help_text, "body")
        help_layout.addWidget(help_text)
        help_layout.addStretch(1)
        help_scroll.setWidget(help_content)
        layout.addWidget(help_scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.setObjectName("DialogActionBar")
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.setObjectName("DashboardDocumentationHelpCloseButton")
            close_button.setText("Schließen")
            close_button.setDefault(True)
            configure_button(
                close_button,
                "secondary",
                "Dokumentationshilfe schließen",
            )
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        def finish_help(_result: int) -> None:
            if self._documentation_help_dialog is dialog:
                self._documentation_help_dialog = None

            def restore_focus() -> None:
                if return_button is None:
                    return
                try:
                    if return_button.isVisible() and return_button.isEnabled():
                        return_button.window().activateWindow()
                        return_button.setFocus(Qt.FocusReason.OtherFocusReason)
                except RuntimeError:
                    pass

            QTimer.singleShot(0, restore_focus)

        dialog.finished.connect(finish_help)
        self._documentation_help_dialog = dialog
        dialog.open()
        if close_button is not None:
            QTimer.singleShot(
                0,
                lambda: close_button.setFocus(Qt.FocusReason.OtherFocusReason),
            )

    @staticmethod
    def _clear_layout(layout: object) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout is not None:
                OverviewScreen._clear_layout(child_layout)


class GroupOverviewScreen(QWidget):
    """Group and course-group projections for the local student workspace."""

    group_selected = Signal(str)
    course_selected = Signal(str, str)
    direct_course_selected = Signal(str)

    def __init__(
        self,
        *,
        section: str = "all",
        show_header: bool = True,
    ) -> None:
        super().__init__()
        if section not in {"all", "groups", "courses", "course_groups"}:
            raise ValueError(f"Unbekannter Übersichtsbereich: {section}")
        self.section = section
        self.show_header = show_header
        self.groups_layout = QGridLayout()
        self.courses_layout = QGridLayout()
        self.course_groups_layout = QVBoxLayout()
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        if self.show_header:
            layout.addWidget(
                PageHeader("Schüler", "Stammgruppen und Kursverbünde auswählen")
            )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        groups_card = self._section_card("Stammgruppen", self.groups_layout)
        groups_card.setVisible(self.section in {"all", "groups"})
        content_layout.addWidget(groups_card)
        courses_card = self._section_card("Kurse", self.courses_layout)
        courses_card.setVisible(self.section in {"all", "courses"})
        content_layout.addWidget(courses_card)
        course_groups_card = self._section_card(
            "Kursverbünde",
            self.course_groups_layout,
        )
        course_groups_card.setVisible(self.section in {"all", "course_groups"})
        content_layout.addWidget(course_groups_card)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

    def set_master_data(
        self,
        view_model: MasterDataViewModel,
        group_summaries: tuple[GroupSummaryViewModel, ...] = (),
    ) -> None:
        """Replace overview lists with the existing master-data scope."""
        OverviewScreen._clear_layout(self.groups_layout)
        OverviewScreen._clear_layout(self.courses_layout)
        OverviewScreen._clear_layout(self.course_groups_layout)
        group_counts = {
            group.group_id: group.active_student_count for group in group_summaries
        }
        groups_by_id = {group.item_id: group for group in view_model.groups}
        courses_by_id = {course.item_id: course for course in view_model.courses}
        if not view_model.groups:
            self.groups_layout.addWidget(QLabel(OVERVIEW_GROUP_EMPTY_STATE), 0, 0)
        for index, group in enumerate(view_model.groups):
            self.groups_layout.addWidget(
                self._group_card(group, group_counts.get(group.item_id)),
                index // 2,
                index % 2,
            )
        if not view_model.courses:
            self.courses_layout.addWidget(QLabel(OVERVIEW_COURSE_EMPTY_STATE), 0, 0)
        for index, course in enumerate(view_model.courses):
            self.courses_layout.addWidget(
                self._course_card(course),
                index // 2,
                index % 2,
            )
        if not view_model.course_groups:
            self.course_groups_layout.addWidget(QLabel(
                "Noch keine Kursverbünde angelegt. Lege sie unter „Stammdaten“ an."
            ))
        for course_group in view_model.course_groups:
            self.course_groups_layout.addWidget(
                self._course_group_card(course_group, groups_by_id, courses_by_id)
            )

    def _section_card(self, title: str, content_layout: object) -> QFrame:
        card = AppCard("soft")
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        set_label_style(title_label, "section_title")
        layout.addWidget(title_label)
        layout.addLayout(content_layout)
        return card

    def _course_card(self, course: MasterDataItemViewModel) -> QFrame:
        card = AppCard("default")
        layout = QVBoxLayout(card)
        heading = QHBoxLayout()
        marker = QFrame()
        marker.setObjectName("CourseColorMarker")
        marker.setFixedSize(10, 10)
        palette = marker.palette()
        palette.setColor(
            QPalette.ColorRole.Window,
            QColor(course.color_hex or "#6B7280"),
        )
        marker.setPalette(palette)
        marker.setAutoFillBackground(True)
        name = QLabel(course.name)
        set_label_style(name, "section_title")
        heading.addWidget(marker)
        heading.addWidget(name)
        heading.addStretch(1)
        open_button = QPushButton("Schüler anzeigen")
        configure_button(
            open_button,
            "secondary",
            f"Schüler im Kurs {course.name} anzeigen",
        )
        open_button.setEnabled(course.is_persistent)
        open_button.clicked.connect(
            lambda _checked=False, course_id=course.item_id: self.direct_course_selected.emit(
                course_id
            )
        )
        layout.addLayout(heading)
        layout.addWidget(open_button)
        return card

    def _group_card(
        self,
        group: MasterDataItemViewModel,
        active_student_count: int | None,
    ) -> QFrame:
        card = AppCard("default")
        layout = QVBoxLayout(card)
        name = QLabel(group.name)
        set_label_style(name, "section_title")
        count = QLabel(
            f"{active_student_count} Schüler"
            if active_student_count is not None
            else group.status_label
        )
        open_button = QPushButton("Schüler anzeigen")
        configure_button(
            open_button,
            "secondary",
            f"Schüler der Stammgruppe {group.name} anzeigen",
        )
        open_button.setEnabled(group.is_persistent)
        open_button.clicked.connect(lambda: self.group_selected.emit(group.item_id))
        layout.addWidget(name)
        layout.addWidget(count)
        layout.addWidget(open_button)
        return card

    def _course_group_card(
        self,
        course_group: CourseGroupViewModel,
        groups_by_id: dict[str, MasterDataItemViewModel],
        courses_by_id: dict[str, MasterDataItemViewModel],
    ) -> QFrame:
        card = AppCard("soft")
        layout = QVBoxLayout(card)
        title = QLabel(course_group.name)
        set_label_style(title, "section_title")
        group_names = tuple(
            groups_by_id[group_id].name
            for group_id in course_group.selected_group_ids
            if group_id in groups_by_id
        )
        groups_label = QLabel(f"Stammgruppen: {', '.join(group_names)}")
        set_label_style(groups_label, "muted")
        layout.addWidget(title)
        layout.addWidget(groups_label)
        for course_id in course_group.selected_course_ids:
            course = courses_by_id.get(course_id)
            if course is not None:
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(4, 0, 4, 0)
                marker = QFrame()
                marker.setObjectName("CourseColorMarker")
                marker.setFixedSize(10, 10)
                palette = marker.palette()
                palette.setColor(
                    QPalette.ColorRole.Window,
                    QColor(course.color_hex or "#6B7280"),
                )
                marker.setPalette(palette)
                marker.setAutoFillBackground(True)
                open_button = QPushButton(course.name)
                configure_button(
                    open_button,
                    "link",
                    f"Schüler im Kurs {course.name} anzeigen",
                )
                open_button.clicked.connect(
                    lambda _checked=False,
                    course_group_id=course_group.course_group_id,
                    selected_course_id=course.item_id: self.course_selected.emit(
                        course_group_id, selected_course_id
                    )
                )
                row_layout.addWidget(marker)
                row_layout.addWidget(open_button)
                row_layout.addStretch(1)
                layout.addWidget(row)
        return card
