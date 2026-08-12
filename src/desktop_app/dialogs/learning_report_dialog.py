"""Prototype-faithful PySide workspace for persistent learning-report drafts."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from PySide6.QtCore import QDate, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.theme import create_card, set_label_style
from src.desktop_app.components import (
    AppCard,
    DialogHeader,
    EmptyState,
    InlineMessage,
    SegmentedControl,
    SectionHeader,
    StatusBadge,
    Toast,
    configure_button,
    stabilize_message_box_buttons,
)
from src.desktop_app.motion import (
    MotionDialog,
    animate_save_confirmation,
)
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportChartSelectionViewModel,
    LearningReportDraft,
    LearningReportDraftViewModel,
    LearningReportEvidenceViewModel,
    LearningReportPreparationViewModel,
    LearningReportFinalizationPreviewViewModel,
    LearningReportRevisionStatusViewModel,
    LearningReportRevisionViewModel,
    LearningReportPdfArtifactViewModel,
    LearningReportSubjectDraftViewModel,
    LearningReportSubjectViewModel,
    build_selected_report_evidence,
    build_report_output_model,
)


CHART_OPTIONS = (
    ("documentation_coverage", "Dokumentationsabdeckung"),
    ("competency_timeline", "Kompetenzentwicklung mit Einzelständen"),
    ("observation_timeline", "Zeitachse ausgewählter Beobachtungen"),
)


def _selection_label(text: str, role: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    set_label_style(label, role)
    return label


class LearningReportDraftSelectionDialog(MotionDialog):
    """Choose an existing report draft or deliberately start a new one."""

    def __init__(
        self,
        drafts: Sequence[LearningReportDraftViewModel],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("LearningReportDraftSelectionDialog")
        self.setWindowTitle("Lernentwicklungsbericht auswählen")
        self.setMinimumSize(660, 420)
        self.selected_draft: LearningReportDraftViewModel | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(
            DialogHeader(
                "Entwurf weiterbearbeiten",
                "Lernentwicklungsbericht",
                "Wähle einen gespeicherten Stand oder lege einen neuen bearbeitbaren Entwurf an.",
                icon_name="report",
                context_role="report",
            )
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 4, 0)
        content_layout.setSpacing(10)
        for draft in drafts:
            card = AppCard("default")
            card.setObjectName(f"LearningReportDraftChoice_{draft.report_draft_id}")
            card.setAccessibleDescription(
                f"Technische Entwurfskennung {draft.report_draft_id}"
            )
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 14, 16, 14)
            text = QVBoxLayout()
            period = (
                f"Zeitraum {draft.period_start.strftime('%d.%m.%Y')} bis "
                f"{draft.period_end.strftime('%d.%m.%Y')}"
            )
            text.addWidget(_selection_label(period, "card_title"))
            text.addWidget(_selection_label("Status: Entwurf", "body"))
            text.addWidget(_selection_label(
                draft.teacher_name or "Lehrkraft offen",
                "small",
            ))
            row.addLayout(text, 1)
            open_button = QPushButton("Öffnen")
            configure_button(open_button, "secondary", f"Entwurf für {period} öffnen")
            open_button.clicked.connect(
                lambda _checked=False, item=draft: self._choose(item)
            )
            row.addWidget(open_button)
            content_layout.addWidget(card)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        actions = QHBoxLayout()
        cancel_button = QPushButton("Abbrechen")
        new_button = QPushButton("Neuer Entwurf")
        configure_button(cancel_button, "quiet", "Auswahl abbrechen")
        configure_button(new_button, "primary", "Neuen Berichtsentwurf anlegen")
        cancel_button.clicked.connect(self.reject)
        new_button.clicked.connect(lambda: self._choose(None))
        actions.addWidget(cancel_button)
        actions.addStretch(1)
        actions.addWidget(new_button)
        layout.addLayout(actions)

    def _choose(self, draft: LearningReportDraftViewModel | None) -> None:
        self.selected_draft = draft
        self.accept()

    @classmethod
    def choose(
        cls,
        drafts: Sequence[LearningReportDraftViewModel],
        parent: QWidget,
    ) -> tuple[bool, LearningReportDraftViewModel | None]:
        dialog = cls(drafts, parent)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        return accepted, dialog.selected_draft


class LearningReportPeriodSelectionDialog(MotionDialog):
    """Collect an explicit reporting period before opening a new draft."""

    _UNSELECTED_DATE = QDate(1900, 1, 1)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LearningReportPeriodSelectionDialog")
        self.setWindowTitle("Berichtszeitraum auswählen")
        self.setMinimumSize(520, 300)
        self.selected_period: tuple[date, date] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(
            DialogHeader(
                "Berichtszeitraum festlegen",
                "Lernentwicklungsbericht",
                "Wähle den Zeitraum bewusst aus, bevor du den Bericht vorbereitest.",
                icon_name="report",
                context_role="report",
            )
        )
        self.start_input = self._date_input("Beginn des Berichtszeitraums")
        self.end_input = self._date_input("Ende des Berichtszeitraums")
        fields = QGridLayout()
        fields.setHorizontalSpacing(18)
        fields.setVerticalSpacing(8)
        fields.addWidget(_selection_label("Zeitraum von", "body"), 0, 0)
        fields.addWidget(_selection_label("Zeitraum bis", "body"), 0, 1)
        fields.addWidget(self.start_input, 1, 0)
        fields.addWidget(self.end_input, 1, 1)
        layout.addLayout(fields)
        self.validation_message = _selection_label("", "small")
        self.validation_message.setObjectName("LearningReportPeriodSelectionMessage")
        layout.addWidget(self.validation_message)
        actions = QHBoxLayout()
        cancel_button = QPushButton("Abbrechen")
        continue_button = QPushButton("Weiter")
        configure_button(cancel_button, "quiet", "Zeitraumauswahl abbrechen")
        configure_button(continue_button, "primary", "Gewählten Berichtszeitraum übernehmen")
        cancel_button.clicked.connect(self.reject)
        continue_button.clicked.connect(self._accept_selected_period)
        actions.addWidget(cancel_button)
        actions.addStretch(1)
        actions.addWidget(continue_button)
        layout.addLayout(actions)

    def _date_input(self, accessible_name: str) -> QDateEdit:
        editor = QDateEdit(self._UNSELECTED_DATE)
        editor.setMinimumDate(self._UNSELECTED_DATE)
        editor.setSpecialValueText("Bitte wählen")
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("dd.MM.yyyy")
        editor.setAccessibleName(accessible_name)
        return editor

    def _accept_selected_period(self) -> None:
        start = self._selected_date(self.start_input)
        end = self._selected_date(self.end_input)
        if start is None or end is None:
            self.validation_message.setText(
                "Bitte wähle Beginn und Ende des Berichtszeitraums aus."
            )
            return
        if end <= start:
            self.validation_message.setText(
                "Das Ende des Berichtszeitraums muss nach dem Beginn liegen."
            )
            return
        self.selected_period = (start, end)
        self.accept()

    def _selected_date(self, editor: QDateEdit) -> date | None:
        value = editor.date()
        return None if value == self._UNSELECTED_DATE else value.toPython()

    @classmethod
    def choose(cls, parent: QWidget) -> tuple[bool, tuple[date, date] | None]:
        dialog = cls(parent)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        return accepted, dialog.selected_period


class LearningReportDialog(QDialog):
    """Edit, persist, preview and export one report draft through explicit signals."""

    save_requested = Signal(object)
    pdf_requested = Signal(object)
    finalization_requested = Signal(object)
    finalize_confirmed = Signal(str, str)
    revision_open_requested = Signal(str)

    def __init__(
        self,
        preparation: LearningReportPreparationViewModel,
        parent: QWidget | None = None,
        initial_draft: LearningReportDraftViewModel | None = None,
        revision_status: LearningReportRevisionStatusViewModel | None = None,
        initial_period: tuple[date, date] | None = None,
    ) -> None:
        super().__init__(parent)
        self.preparation = preparation
        self._saved_draft = initial_draft
        self._initial_period = initial_period
        self._revision_status = revision_status or LearningReportRevisionStatusViewModel(
            "not_finalized",
            "Entwurf",
            "Für diesen Bericht existiert noch keine unveränderliche Fassung.",
        )
        self.selected_subject_ids = set(
            initial_draft.selected_subject_ids if initial_draft else ()
        )
        self.selected_competency_ids = set(
            initial_draft.competency_ids if initial_draft else ()
        )
        self.selected_observation_ids = set(
            initial_draft.observation_ids if initial_draft else ()
        )
        self._unavailable_observation_ids = set(
            initial_draft.unavailable_observation_ids if initial_draft else ()
        )
        self._selected_charts = {
            (chart.subject_id, chart.chart_type)
            for chart in (initial_draft.chart_selections if initial_draft else ())
        }
        self._subject_texts = {
            subject.subject_id: subject
            for subject in (initial_draft.subjects if initial_draft else ())
        }
        self.subject_widgets: dict[str, dict[str, object]] = {}
        self._evidence_checks: dict[str, dict[str, QCheckBox]] = {}
        self._evidence_scrolls: dict[str, QScrollArea] = {}
        self._evidence_subject_buttons: dict[str, QPushButton] = {}
        self.workspace_pages: dict[str, QWidget] = {}
        self.workspace_built = {
            key: False for key in ("writing", "evidence", "preview", "revisions")
        }
        self._workspace_builders = {
            "writing": self._editor_screen,
            "evidence": self._evidence_screen,
            "preview": self._preview_screen,
            "revisions": self._closing_editor,
        }
        self.editor_subject_pages: dict[str, QWidget] = {}
        self.editor_subject_built = {
            subject.subject_id: False for subject in preparation.subjects
        }
        self.evidence_subject_pages: dict[str, QWidget] = {}
        self.evidence_subject_built = {
            subject.subject_id: False for subject in preparation.subjects
        }
        self._pending_evidence_subject_index: int | None = None
        self._preview_stale = True
        self._revision_stale = True
        self.finalize_button: QPushButton | None = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(120)
        self._preview_timer.timeout.connect(self.update_preview)
        self._ui_ready = False
        self._dirty = False

        self.setWindowTitle(f"Lernentwicklungsbericht · {preparation.student_name}")
        self.setProperty("dialogContext", "report")
        self.resize(1500, 980)
        self.setMinimumSize(980, 680)
        self._build()
        self._connect_live_preview()
        self._ui_ready = True
        self._refresh_workspace_context()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._top_bar())
        self.toast = Toast(self)
        root.addWidget(self.toast, 0, Qt.AlignmentFlag.AlignHCenter)
        navigation_shell = QFrame()
        navigation_shell.setObjectName("LearningReportWorkspaceNavigation")
        navigation_layout = QHBoxLayout(navigation_shell)
        navigation_layout.setContentsMargins(24, 10, 24, 10)
        self.workspace_navigation = SegmentedControl(
            (
                ("writing", "Schreiben"),
                ("evidence", "Kompetenzen && Belege"),
                ("preview", "Vorschau"),
                ("revisions", "Revisionen"),
            )
        )
        self.workspace_navigation.setAccessibleName("Bereiche der Berichtswerkstatt")
        self.workspace_navigation.selection_changed.connect(self._set_workspace)
        navigation_layout.addWidget(self.workspace_navigation)
        navigation_layout.addStretch(1)
        root.addWidget(navigation_shell)
        self.selected_subject_context = QLabel()
        self.selected_subject_context.setObjectName(
            "LearningReportSelectedSubjectContext"
        )
        self.selected_subject_context.setAccessibleName(
            "Aktuell ausgewählte Berichtsfächer"
        )
        self.selected_subject_context.setWordWrap(True)
        self.selected_subject_context.setContentsMargins(24, 8, 24, 8)
        set_label_style(self.selected_subject_context, "muted")
        root.addWidget(self.selected_subject_context)
        self._refresh_subject_selection_summary()
        self.workspace_message = InlineMessage()
        root.addWidget(self.workspace_message)

        self.mode_stack = QStackedWidget()
        self.mode_stack.setObjectName("LearningReportWorkspaceStack")
        for key in ("writing", "evidence", "preview", "revisions"):
            page = QWidget()
            page.setObjectName(f"LearningReportWorkspaceContainer_{key}")
            page.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            page.setAccessibleName(
                {
                    "writing": "Schreiben",
                    "evidence": "Kompetenzen und Belege",
                    "preview": "Vorschau",
                    "revisions": "Revisionen",
                }[key]
            )
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            self.workspace_pages[key] = page
            self.mode_stack.addWidget(page)
        root.addWidget(self.mode_stack, 1)
        root.addWidget(self._action_bar())
        self._ensure_workspace_built("writing")
        initial_workspace = "writing"
        if self._saved_draft is None:
            initial_workspace = "evidence"
            self._ensure_workspace_built(initial_workspace)
        self.workspace_navigation.set_current_key(initial_workspace)
        self._activate_workspace_page(initial_workspace)

    def _top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("LearningReportTopBar")
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(24, 16, 24, 14)
        layout.setSpacing(8)
        self.page_header = DialogHeader(
            f"Lernentwicklungsbericht · {self.preparation.student_name}",
            "Berichtswerkstatt · bearbeitbarer Entwurf",
            "Schreiben, Belege prüfen, Vorschau lesen und Revisionen nachvollziehen.",
            icon_name="report",
            context_role="report",
        )
        self.header_status_badge = StatusBadge()
        self.page_header.add_action(self.header_status_badge)
        layout.addWidget(self.page_header)
        context_row = QHBoxLayout()
        context_row.setSpacing(14)
        self.header_context = QLabel()
        self.header_context.setWordWrap(True)
        set_label_style(self.header_context, "muted")
        context_row.addWidget(self.header_context, 1)
        self.header_revision_context = QLabel()
        self.header_revision_context.setWordWrap(True)
        self.header_revision_context.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        set_label_style(self.header_revision_context, "muted")
        context_row.addWidget(self.header_revision_context)
        layout.addLayout(context_row)
        return bar

    def _set_mode(self, index: int) -> None:
        key = ("writing", "evidence", "preview", "revisions")[index]
        self.workspace_navigation.set_current_key(key)
        self._set_workspace(key)

    def _set_workspace(self, key: str) -> None:
        indexes = {"writing": 0, "evidence": 1, "preview": 2, "revisions": 3}
        index = indexes.get(key, 0)
        key = ("writing", "evidence", "preview", "revisions")[index]
        self._ensure_workspace_built(key)
        self._activate_workspace_page(key)
        if index == 2:
            self.update_preview()
        if index == 3 and self._revision_stale:
            self._render_revision_context()

    def _activate_workspace_page(self, key: str) -> None:
        active_page = self.workspace_pages[key]
        self.mode_stack.setCurrentWidget(active_page)
        for page in self.workspace_pages.values():
            is_active = page is active_page
            page.setGraphicsEffect(None)
            page.setEnabled(is_active)
            page.setVisible(is_active)
        active_page.raise_()
        self.mode_stack.update()

    def _ensure_workspace_built(self, key: str) -> None:
        if self.workspace_built[key]:
            return
        page_layout = self.workspace_pages[key].layout()
        if page_layout is None:
            raise RuntimeError(f"Berichtswerkstatt-Seitencontainer ohne Layout: {key}")
        page_layout.addWidget(self._workspace_builders[key]())
        self.workspace_built[key] = True

    def _editor_screen(self) -> QWidget:
        screen = QWidget()
        layout = QHBoxLayout(screen)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._editor_sidebar())
        self.editor_stack = QStackedWidget()
        self.editor_stack.addWidget(self._overview_editor())
        for subject in self.preparation.subjects:
            page = QWidget()
            page.setObjectName(
                f"LearningReportEditorSubjectContainer_{subject.subject_id}"
            )
            page.setAccessibleName(f"Fachtext {subject.subject_name}")
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            self.editor_subject_pages[subject.subject_id] = page
            self.editor_stack.addWidget(page)
        layout.addWidget(self.editor_stack, 1)
        return screen

    def _editor_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("LearningReportSidebar")
        sidebar.setFixedWidth(248)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 18)
        layout.setSpacing(5)
        layout.addWidget(self._eyebrow("SCHREIBBEREICHE"))
        self.navigation_group = QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        entries = [("Gesamttext", 0)]
        entries.extend(
            (subject.subject_name, index + 1)
            for index, subject in enumerate(self.preparation.subjects)
        )
        for title, index in entries:
            button = QPushButton(title)
            button.setObjectName("LearningReportSubjectButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.clicked.connect(
                lambda _checked=False, target=index: self._set_editor_section(target)
            )
            self.navigation_group.addButton(button)
            layout.addWidget(button)
        layout.addStretch(1)
        note = QLabel(
            "Gesamttext und Fachtexte werden bewusst formuliert und gemeinsam als Entwurf gespeichert."
        )
        note.setWordWrap(True)
        set_label_style(note, "subtle")
        layout.addWidget(note)
        return sidebar

    def _evidence_screen(self) -> QWidget:
        screen = QWidget()
        layout = QHBoxLayout(screen)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("LearningReportSidebar")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 24, 18, 18)
        sidebar_layout.setSpacing(5)
        sidebar_layout.addWidget(self._eyebrow("FÄCHER"))
        self.evidence_navigation_group = QButtonGroup(self)
        self.evidence_navigation_group.setExclusive(True)
        self.evidence_stack = QStackedWidget()
        primary_ids = set(self.preparation.primary_subject_ids)
        retained_ids = set(self.preparation.retained_subject_ids)
        previous_group = ""
        for index, subject in enumerate(self.preparation.subjects):
            group = (
                "primary"
                if subject.subject_id in primary_ids
                else "retained"
                if subject.subject_id in retained_ids
                else "additional"
            )
            if group != previous_group:
                group_label = self._eyebrow(
                    "FÄCHER DES KINDES"
                    if group == "primary"
                    else "GESPEICHERTE FACHABSCHNITTE"
                    if group == "retained"
                    else "WEITERE FÄCHER"
                )
                group_label.setObjectName("LearningReportSubjectGroupLabel")
                sidebar_layout.addWidget(group_label)
                previous_group = group
            button = QPushButton(subject.subject_name)
            button.setObjectName("LearningReportSubjectButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setAccessibleName(f"Kompetenzen und Belege für {subject.subject_name}")
            button.clicked.connect(
                lambda _checked=False, target=index: self._set_evidence_section(target)
            )
            self.evidence_navigation_group.addButton(button)
            self._evidence_subject_buttons[subject.subject_id] = button
            sidebar_layout.addWidget(button)
            page = QWidget()
            page.setObjectName(
                f"LearningReportEvidenceSubjectContainer_{subject.subject_id}"
            )
            page.setAccessibleName(
                f"Kompetenzen und Belege für {subject.subject_name}"
            )
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            self.evidence_subject_pages[subject.subject_id] = page
            self.evidence_stack.addWidget(page)
        sidebar_layout.addStretch(1)
        self.evidence_selection_summary = QLabel()
        self.evidence_selection_summary.setObjectName(
            "LearningReportEvidenceSelectionSummary"
        )
        self.evidence_selection_summary.setAccessibleName(
            "Ausgewählte Berichtsfächer"
        )
        self.evidence_selection_summary.setWordWrap(True)
        set_label_style(self.evidence_selection_summary, "muted")
        sidebar_layout.addWidget(self.evidence_selection_summary)
        self.continue_to_writing_button = QPushButton("Weiter zum Schreibbereich")
        configure_button(
            self.continue_to_writing_button,
            "primary",
            "Mit den ausgewählten Fächern zum Schreibbereich wechseln",
        )
        self.continue_to_writing_button.clicked.connect(
            lambda: self.show_workspace("writing")
        )
        sidebar_layout.addWidget(self.continue_to_writing_button)
        sidebar_layout.addWidget(
            InlineMessage(
                "Auswahl ist immer bewusst. Historische Bezüge bleiben lesbar, werden aber nicht neu aktiviert.",
                tone="info",
            )
        )
        layout.addWidget(sidebar)
        layout.addWidget(self.evidence_stack, 1)
        if self.preparation.subjects:
            initial_index = self._pending_evidence_subject_index or 0
            self._ensure_evidence_subject_built(initial_index)
            self.evidence_stack.setCurrentIndex(initial_index)
        self._refresh_subject_selection_summary()
        return screen

    def _refresh_subject_selection_summary(self) -> None:
        selected_names = tuple(
            subject.subject_name
            for subject in self.preparation.subjects
            if subject.subject_id in self.selected_subject_ids
        )
        if hasattr(self, "selected_subject_context"):
            self.selected_subject_context.setText(
                f"Ausgewählte Berichtsfächer: {', '.join(selected_names)}"
                if selected_names
                else "Ausgewählte Berichtsfächer: noch keine"
            )
        if not hasattr(self, "evidence_selection_summary"):
            return
        self.evidence_selection_summary.setText(
            f"Ausgewählt: {', '.join(selected_names)}"
            if selected_names
            else "Noch kein Fach ausgewählt"
        )
        self.continue_to_writing_button.setEnabled(bool(selected_names))

    def _set_editor_section(self, index: int) -> None:
        if index > 0:
            self._ensure_editor_subject_built(index)
        self._activate_content_stack_page(self.editor_stack, index)

    def _set_evidence_section(self, index: int) -> None:
        self._ensure_evidence_subject_built(index)
        self._activate_content_stack_page(self.evidence_stack, index)

    @staticmethod
    def _activate_content_stack_page(stack: QStackedWidget, index: int) -> None:
        """Make a report content section visible without compositing effects."""
        stack.setCurrentIndex(index)
        active_page = stack.currentWidget()
        for page_index in range(stack.count()):
            page = stack.widget(page_index)
            is_active = page is active_page
            page.setGraphicsEffect(None)
            page.setEnabled(is_active)
            page.setVisible(is_active)
        if active_page is not None:
            active_page.raise_()
        stack.update()

    def _ensure_editor_subject_built(self, index: int) -> None:
        if index <= 0 or index > len(self.preparation.subjects):
            return
        subject = self.preparation.subjects[index - 1]
        if self.editor_subject_built[subject.subject_id]:
            return
        page_layout = self.editor_subject_pages[subject.subject_id].layout()
        if page_layout is None:
            raise RuntimeError(
                f"Bericht-Fachtextcontainer ohne Layout: {subject.subject_id}"
            )
        page_layout.addWidget(self._subject_editor(subject))
        self.editor_subject_built[subject.subject_id] = True

    def _ensure_evidence_subject_built(self, index: int) -> None:
        if index < 0 or index >= len(self.preparation.subjects):
            return
        subject = self.preparation.subjects[index]
        if self.evidence_subject_built[subject.subject_id]:
            return
        page_layout = self.evidence_subject_pages[subject.subject_id].layout()
        if page_layout is None:
            raise RuntimeError(
                f"Bericht-Belegcontainer ohne Layout: {subject.subject_id}"
            )
        page_layout.addWidget(self._subject_evidence_editor(subject))
        self.evidence_subject_built[subject.subject_id] = True

    def show_workspace(self, key: str) -> None:
        """Open one existing workspace section without changing draft state."""
        if key not in {"writing", "evidence", "preview", "revisions"}:
            return
        self.workspace_navigation.set_current_key(key)
        self._set_workspace(key)
        if key == "revisions" and self.finalize_button is not None:
            QTimer.singleShot(0, self.finalize_button.setFocus)

    def focus_evidence_subject(self, subject_id: str) -> bool:
        """Focus the existing competency area without selecting a competency."""
        subject_ids = tuple(
            subject.subject_id for subject in self.preparation.subjects
        )
        if subject_id not in subject_ids:
            return False
        index = subject_ids.index(subject_id)
        self._pending_evidence_subject_index = index
        try:
            self.show_workspace("evidence")
        finally:
            self._pending_evidence_subject_index = None
        button = self._evidence_subject_buttons[subject_id]
        button.setChecked(True)
        self._set_evidence_section(index)
        tree = self.subject_widgets.get(subject_id, {}).get("tree")
        scroll = self._evidence_scrolls.get(subject_id)
        if not isinstance(tree, QTreeWidget) or scroll is None:
            return False

        def focus_target() -> None:
            self.activateWindow()
            scroll.ensureWidgetVisible(tree, 20, 20)
            tree.setFocus(Qt.FocusReason.ShortcutFocusReason)

        focus_target()
        QTimer.singleShot(0, lambda: QTimer.singleShot(0, focus_target))
        return True

    def _action_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("LearningReportActionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(10)
        self.draft_status = QLabel(self._draft_status_text())
        self.draft_status.setWordWrap(True)
        if self._saved_draft and self._saved_draft.report_draft_id:
            self.draft_status.setToolTip(self._saved_draft.report_draft_id)
        set_label_style(self.draft_status, "muted")
        layout.addWidget(self.draft_status, 1)
        close = QPushButton("Schließen")
        configure_button(close, "quiet", "Berichtswerkstatt schließen")
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        preview = QPushButton("Vorschau")
        configure_button(preview, "secondary", "Vorschau des aktuellen Entwurfs öffnen")
        preview.clicked.connect(lambda: self._set_mode(2))
        layout.addWidget(preview)
        self.save_button = QPushButton("Entwurf speichern")
        self.save_button.setObjectName("LearningReportSaveButton")
        configure_button(self.save_button, "primary", "Berichtsentwurf speichern")
        self.save_button.setShortcut(QKeySequence.StandardKey.Save)
        self.save_button.clicked.connect(self._request_save)
        layout.addWidget(self.save_button)
        return bar

    def _overview_editor(self) -> QScrollArea:
        content, layout = self._page_canvas()
        title_row = QHBoxLayout()
        title = QVBoxLayout()
        title.addWidget(self._eyebrow("BERICHT BEARBEITEN"))
        heading = QLabel("Dokumentkontext & pädagogischer Gesamtblick")
        set_label_style(heading, "screen_title")
        title.addWidget(heading)
        title_row.addLayout(title, 1)
        status = QLabel("ENTWURF")
        status.setObjectName("LearningReportStatusPill")
        title_row.addWidget(status, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(title_row)
        hint = QLabel(
            "Manuelle Berichtsinhalte werden als bearbeitbarer Entwurf gespeichert. "
            "Es findet keine automatische Texterstellung statt."
        )
        hint.setWordWrap(True)
        set_label_style(hint, "subtle")
        layout.addWidget(hint)
        layout.addWidget(self._context_card())
        layout.addWidget(self._overall_card())
        return self._scroll_page(content)

    def _context_card(self) -> QFrame:
        card = create_card()
        layout = QGridLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(8)
        title = QLabel("Dokumentkontext")
        set_label_style(title, "section_title")
        layout.addWidget(title, 0, 0, 1, 2)
        layout.addWidget(self._read_only_field("Schülername", self.preparation.student_name), 1, 0)
        layout.addWidget(
            self._read_only_field(
                "Stammgruppe",
                self.preparation.group_name
                or self.preparation.membership_status_label
                or "–",
            ),
            1,
            1,
        )
        layout.addWidget(
            self._read_only_field(
                "Kurs",
                self.preparation.course_name
                or self.preparation.membership_status_label
                or "–",
            ),
            2,
            0,
        )
        layout.addWidget(
            self._read_only_field("Berichtsart", "Lernentwicklungsbericht"),
            2,
            1,
        )
        self.teacher_input = QLineEdit(
            self._saved_draft.teacher_name if self._saved_draft else ""
        )
        layout.addWidget(
            self._field("Verantwortliche Lehrkraft", self.teacher_input),
            3,
            0,
            1,
            2,
        )
        today = date.today()
        period_start = (
            self._saved_draft.period_start
            if self._saved_draft
            else self._initial_period[0] if self._initial_period else date(today.year, 1, 1)
        )
        period_end = (
            self._saved_draft.period_end
            if self._saved_draft
            else self._initial_period[1] if self._initial_period else date(today.year, 12, 31)
        )
        self.period_start = QDateEdit(QDate(period_start.year, period_start.month, period_start.day))
        self.period_end = QDateEdit(QDate(period_end.year, period_end.month, period_end.day))
        for editor in (self.period_start, self.period_end):
            editor.setCalendarPopup(True)
            editor.setDisplayFormat("dd.MM.yyyy")
        layout.addWidget(self._field("Zeitraum von", self.period_start), 4, 0)
        layout.addWidget(self._field("Zeitraum bis", self.period_end), 4, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        return card

    def _overall_card(self) -> QFrame:
        card = create_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(10)
        title = QLabel("Pädagogischer Gesamtblick")
        set_label_style(title, "section_title")
        layout.addWidget(title)
        layout.addWidget(
            self._responsibility_note(
                "Von der Lehrkraft verfasst und pädagogisch verantwortet. "
                "Es werden keine Formulierungen oder Bewertungen automatisch erzeugt."
            )
        )
        self.overall_input = QTextEdit(
            self._saved_draft.overall_text if self._saved_draft else ""
        )
        self.overall_input.setPlaceholderText(
            "Beobachtbare Lernwege, hilfreiche Bedingungen und nächste pädagogische Schritte …"
        )
        self.overall_input.setMinimumHeight(190)
        layout.addWidget(self.overall_input)
        return card

    def _subject_editor(self, subject: LearningReportSubjectViewModel) -> QScrollArea:
        content, layout = self._page_canvas()
        title_row = QHBoxLayout()
        title = QVBoxLayout()
        title.addWidget(self._eyebrow("FACHTEXT"))
        heading = QLabel(subject.subject_name)
        set_label_style(heading, "screen_title")
        title.addWidget(heading)
        title.addWidget(
            self._small_label(
                "Stärken, Lernentwicklung, Unterstützung und nächste Ziele in Ruhe formulieren."
            )
        )
        title_row.addLayout(title, 1)
        selection_badge = StatusBadge(
            "Für Bericht ausgewählt"
            if subject.subject_id in self.selected_subject_ids
            else "Noch nicht ausgewählt",
            tone="info" if subject.subject_id in self.selected_subject_ids else "neutral",
        )
        title_row.addWidget(selection_badge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(title_row)
        layout.addWidget(
            InlineMessage(
                "Ob dieser Fachabschnitt in den Bericht gehört, wird im Bereich „Kompetenzen & Belege“ bewusst ausgewählt.",
                tone="info",
            )
        )
        report_card = AppCard()
        report_card.setObjectName("LearningReportReportCard")
        report_layout = QVBoxLayout(report_card)
        report_layout.setContentsMargins(20, 18, 20, 22)
        report_layout.setSpacing(14)
        report_layout.addWidget(
            SectionHeader(
                "Fachtext schreiben",
                "Leere Abschnitte bleiben leer; es werden keine Texte ergänzt oder umformuliert.",
            )
        )
        saved_text = self._subject_texts.get(subject.subject_id)
        text_edits: dict[str, QTextEdit] = {}
        for key, visible_title, placeholder in (
            ("strengths", "Stärken", "Beobachtbare Stärken in eigener Sprache …"),
            ("development", "Lernentwicklung", "Lernwege und Entwicklung in eigener Sprache …"),
            ("support", "Unterstützungsbedarf", "Hilfreiche Unterstützung in eigener Sprache …"),
            ("goals", "Nächste Ziele", "Nächste Ziele in eigener Sprache …"),
        ):
            label = QLabel(visible_title)
            set_label_style(label, "card_title")
            report_layout.addWidget(label)
            value = ""
            if saved_text:
                value = {
                    "strengths": saved_text.strengths_text,
                    "development": saved_text.development_text,
                    "support": saved_text.support_needs_text,
                    "goals": saved_text.next_goals_text,
                }[key]
            edit = QTextEdit(value)
            edit.setPlaceholderText(placeholder)
            edit.setMinimumHeight(118)
            edit.setObjectName(f"LearningReportSubjectText_{subject.subject_id}_{key}")
            edit.setAccessibleName(f"{visible_title} im Fach {subject.subject_name}")
            report_layout.addWidget(edit)
            text_edits[key] = edit
        layout.addWidget(report_card)

        self.subject_widgets.setdefault(subject.subject_id, {}).update(
            {"texts": text_edits, "selection_badge": selection_badge}
        )
        for edit in text_edits.values():
            edit.textChanged.connect(self._schedule_preview)
        return self._scroll_page(content)

    def _subject_evidence_editor(
        self, subject: LearningReportSubjectViewModel
    ) -> QScrollArea:
        content, layout = self._page_canvas()
        title_row = QHBoxLayout()
        title = QVBoxLayout()
        title.addWidget(self._eyebrow("BEWUSSTE AUSWAHL"))
        heading = QLabel(subject.subject_name)
        set_label_style(heading, "screen_title")
        title.addWidget(heading)
        title.addWidget(
            self._small_label(
                "Kompetenzen, Beobachtungsbelege und Diagramme für diesen Fachabschnitt auswählen."
            )
        )
        title_row.addLayout(title, 1)
        include = QCheckBox("Fach im Bericht verwenden")
        include.setObjectName(f"LearningReportIncludeSubject_{subject.subject_id}")
        include.setAccessibleName(f"Fach {subject.subject_name} im Bericht verwenden")
        include.setChecked(subject.subject_id in self.selected_subject_ids)
        title_row.addWidget(include, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(title_row)

        internal = AppCard("soft")
        internal.setObjectName("LearningReportInternalCard")
        internal_layout = QVBoxLayout(internal)
        internal_layout.setContentsMargins(20, 18, 20, 20)
        internal_layout.setSpacing(12)
        header = SectionHeader(
            "Kompetenzen und Beobachtungsbelege",
            self._evidence_header_text(subject),
        )
        header.add_action(StatusBadge("Bewusste Auswahl", tone="info"))
        internal_layout.addWidget(header)
        internal_layout.addWidget(self._small_label("Fach → Kompetenzbereich → Thema → Kompetenz"))
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setRootIsDecorated(True)
        tree.setIndentation(20)
        tree.setMinimumHeight(310)
        tree.setWordWrap(True)
        tree.setUniformRowHeights(False)
        tree.setAnimated(False)
        tree.setAllColumnsShowFocus(True)
        tree.setAccessibleName(f"Kompetenzauswahl für {subject.subject_name}")
        tree.setAccessibleDescription(
            "Kompetenzen mit Belegen im Berichtszeitraum stehen zuerst. "
            "Historische Einträge sind textlich gekennzeichnet und nicht neu auswählbar."
        )
        self._populate_competency_tree(subject, tree)
        internal_layout.addWidget(tree)
        evidence_header = SectionHeader(
            "Beobachtungsbelege",
            "Es erscheinen nur Belege zu bewusst ausgewählten Kompetenzen; Auswahl erfolgt per Kontrollkästchen.",
        )
        internal_layout.addWidget(evidence_header)
        evidence_container = QWidget()
        evidence_layout = QVBoxLayout(evidence_container)
        evidence_layout.setContentsMargins(0, 0, 0, 0)
        evidence_layout.setSpacing(8)
        internal_layout.addWidget(evidence_container)
        layout.addWidget(internal)

        chart_card = create_card()
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(20, 18, 20, 22)
        chart_layout.setSpacing(9)
        chart_title = QLabel("Diagramme für die Entwicklungsdarstellung")
        set_label_style(chart_title, "section_title")
        chart_layout.addWidget(chart_title)
        chart_layout.addWidget(
            self._responsibility_note(
                "Diagramme werden bewusst gewählt. Sie zeigen Dokumentationsumfang oder "
                "Einzelstände, aber keine Scores, Trendlinien oder Leistungsbewertung."
            )
        )
        chart_checks: dict[str, QCheckBox] = {}
        for chart_type, chart_label in CHART_OPTIONS:
            checkbox = QCheckBox(chart_label)
            checkbox.setAccessibleName(
                f"Diagramm {chart_label} für {subject.subject_name} auswählen"
            )
            checkbox.setChecked((subject.subject_id, chart_type) in self._selected_charts)
            chart_layout.addWidget(checkbox)
            chart_checks[chart_type] = checkbox
        layout.addWidget(chart_card)

        if (
            self._unavailable_observation_ids
            and subject == self.preparation.subjects[0]
        ):
            layout.addWidget(self._unavailable_evidence_card())

        self.subject_widgets.setdefault(subject.subject_id, {}).update({
            "include": include,
            "tree": tree,
            "evidence_container": evidence_container,
            "evidence_layout": evidence_layout,
            "charts": chart_checks,
            "evidence_header": header,
        })
        include.toggled.connect(
            lambda checked, subject_id=subject.subject_id: self._toggle_subject(
                subject_id, checked
            )
        )
        tree.itemChanged.connect(
            lambda item, column, subject_id=subject.subject_id: self._toggle_competency(
                subject_id, item, column
            )
        )
        for chart_type, checkbox in chart_checks.items():
            checkbox.toggled.connect(
                lambda checked, subject_id=subject.subject_id, selected_type=chart_type: (
                    self._toggle_chart(subject_id, selected_type, checked)
                )
            )
        self._render_evidence(subject)
        scroll = self._scroll_page(content)
        self._evidence_scrolls[subject.subject_id] = scroll
        return scroll

    def _closing_editor(self) -> QScrollArea:
        content, layout = self._page_canvas()
        layout.addLayout(
            self._page_heading(
                "FINALISIERUNG UND HISTORIE",
                "Revisionen prüfen und bewusst finalisieren",
                "Der Entwurf bleibt bearbeitbar. Finale Revisionen sind unveränderliche historische Fassungen.",
            )
        )
        self.finalization_message = InlineMessage()
        layout.addWidget(self.finalization_message)
        self.revision_context = QWidget()
        self.revision_context_layout = QVBoxLayout(self.revision_context)
        self.revision_context_layout.setContentsMargins(0, 0, 0, 0)
        self.revision_context_layout.setSpacing(14)
        layout.addWidget(self.revision_context)
        self._render_revision_context()
        summary = create_card()
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(22, 20, 22, 22)
        summary_layout.setSpacing(10)
        title = QLabel("Aktueller Arbeitsstand")
        set_label_style(title, "section_title")
        summary_layout.addWidget(title)
        self.closing_summary = QLabel()
        self.closing_summary.setWordWrap(True)
        set_label_style(self.closing_summary, "body")
        summary_layout.addWidget(self.closing_summary)
        layout.addWidget(summary)
        self._refresh_closing_summary()
        return self._scroll_page(content)

    def _render_revision_context(self) -> None:
        if not hasattr(self, "revision_context_layout"):
            return
        self._revision_stale = False
        self._clear_layout(self.revision_context_layout)
        status = self._revision_status
        self.finalize_button = None
        card = AppCard("soft")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(10)
        header = SectionHeader(
            "Finalisierungsstatus",
            "Entwurf und historische Fassungen bleiben fachlich getrennt.",
        )
        badge_tone = "success" if status.state == "finalized" else "info"
        badge = StatusBadge(status.badge_text, tone=badge_tone)
        header.add_action(badge)
        card_layout.addWidget(header)
        hint = QLabel(status.hint_text)
        hint.setWordWrap(True)
        set_label_style(hint, "body")
        card_layout.addWidget(hint)
        if status.has_current_revision:
            metadata = QLabel(
                f"Finalisiert am {status.finalized_at} · "
                f"verantwortlich: {status.finalized_by_display_name}"
            )
            metadata.setWordWrap(True)
            set_label_style(metadata, "muted")
            card_layout.addWidget(metadata)
            badge.setToolTip(
                f"{status.current_revision_id}\nSnapshot SHA-256: "
                f"{next((item.snapshot_sha256 for item in status.history if item.learning_report_revision_id == status.current_revision_id), '')}"
            )
        if not status.snapshot_hash_valid:
            card_layout.addWidget(
                InlineMessage(
                    "Der gespeicherte Snapshot-Hash konnte nicht bestätigt werden. "
                    "Die Revision wird nicht geöffnet.",
                    tone="error",
                )
            )
        actions = QHBoxLayout()
        actions.addStretch(1)
        if status.state == "not_finalized":
            finalize = QPushButton("Bericht finalisieren")
            finalize.setObjectName("LearningReportFinalizeButton")
            configure_button(finalize, "secondary")
            finalize.clicked.connect(self._request_finalization)
            self.finalize_button = finalize
            actions.addWidget(finalize)
        elif status.state == "draft_changed":
            open_current = QPushButton("Letzte finale Fassung öffnen")
            configure_button(open_current, "quiet")
            open_current.clicked.connect(
                lambda: self.revision_open_requested.emit(status.current_revision_id)
            )
            finalize = QPushButton("Neue Revision finalisieren")
            finalize.setObjectName("LearningReportFinalizeButton")
            configure_button(finalize, "secondary")
            finalize.clicked.connect(self._request_finalization)
            self.finalize_button = finalize
            actions.addWidget(open_current)
            actions.addWidget(finalize)
        else:
            open_current = QPushButton("Finale Fassung öffnen")
            open_current.setObjectName("LearningReportOpenCurrentRevisionButton")
            configure_button(open_current, "secondary")
            open_current.clicked.connect(
                lambda: self.revision_open_requested.emit(status.current_revision_id)
            )
            actions.addWidget(open_current)
        card_layout.addLayout(actions)
        self.revision_context_layout.addWidget(card)

        history_header = SectionHeader(
            "Revisionsprotokoll",
            "Historische Revisionen sind schreibgeschützt und bleiben unverändert.",
        )
        self.revision_context_layout.addWidget(history_header)
        if not status.history:
            self.revision_context_layout.addWidget(
                EmptyState(
                    "Nach der ersten Finalisierung erscheint hier die Historie.",
                    title="Noch keine Revision",
                )
            )
            return
        for item in status.history:
            row = AppCard()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(16, 12, 16, 12)
            labels = QVBoxLayout()
            title = QLabel(f"Revision {item.revision_number}")
            set_label_style(title, "card_title")
            labels.addWidget(title)
            detail = QLabel(
                f"{item.finalized_at} · {item.finalized_by_display_name}\n"
                f"{item.report_type_label} · {item.period_label}"
            )
            detail.setWordWrap(True)
            set_label_style(detail, "muted")
            labels.addWidget(detail)
            row_layout.addLayout(labels, 1)
            item_badge = StatusBadge(
                item.status_label,
                tone="success" if item.status_label == "Aktuell" else "neutral",
            )
            item_badge.setToolTip(
                f"{item.learning_report_revision_id}\nSnapshot SHA-256: {item.snapshot_sha256}"
            )
            row_layout.addWidget(item_badge)
            open_button = QPushButton("Öffnen")
            open_button.setObjectName(
                f"LearningReportOpenRevision_{item.learning_report_revision_id}"
            )
            configure_button(open_button, "quiet")
            open_button.clicked.connect(
                lambda _checked=False, revision_id=item.learning_report_revision_id: (
                    self.revision_open_requested.emit(revision_id)
                )
            )
            row_layout.addWidget(open_button)
            self.revision_context_layout.addWidget(row)

    def _preview_screen(self) -> QWidget:
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        tools = QFrame()
        tools.setObjectName("LearningReportSidebar")
        tools.setFixedHeight(68)
        tools_layout = QHBoxLayout(tools)
        tools_layout.setContentsMargins(28, 12, 28, 12)
        title = QVBoxLayout()
        title.setSpacing(1)
        title.addWidget(self._eyebrow("DRAFT-VORSCHAU"))
        heading = QLabel("Vorschau des aktuellen Entwurfs")
        set_label_style(heading, "card_title")
        title.addWidget(heading)
        tools_layout.addLayout(title)
        tools_layout.addStretch(1)
        self.preview_status = self._small_label("Vorschau des aktuellen Entwurfs")
        self.preview_status.setAccessibleName("Status der Entwurfsvorschau")
        tools_layout.addWidget(self.preview_status)
        back = QPushButton("←  Weiter bearbeiten")
        configure_button(back, "quiet", "Zum Schreibbereich zurückkehren")
        back.clicked.connect(lambda: self._set_mode(0))
        tools_layout.addWidget(back)
        self.pdf_button = QPushButton("Entwurfs-PDF exportieren")
        configure_button(
            self.pdf_button,
            "secondary",
            "PDF aus der Vorschau des aktuellen Entwurfs exportieren",
        )
        self.pdf_button.clicked.connect(self._request_pdf)
        tools_layout.addWidget(self.pdf_button)
        layout.addWidget(tools)
        scroll = QScrollArea()
        scroll.setObjectName("LearningReportPreviewScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.preview_container = QWidget()
        self.preview_container.setObjectName("LearningReportPreviewCanvas")
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.preview_layout.setContentsMargins(30, 34, 30, 60)
        self.preview_layout.setSpacing(30)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        scroll.setWidget(self.preview_container)
        layout.addWidget(scroll, 1)
        return screen

    def _connect_live_preview(self) -> None:
        self.period_start.dateChanged.connect(lambda _value: self._period_changed())
        self.period_end.dateChanged.connect(lambda _value: self._period_changed())
        self.teacher_input.textChanged.connect(self._schedule_preview)
        self.overall_input.textChanged.connect(self._schedule_preview)

    def _populate_competency_tree(
        self, subject: LearningReportSubjectViewModel, tree: QTreeWidget
    ) -> None:
        tree.blockSignals(True)
        tree.clear()
        subject_item = QTreeWidgetItem([subject.subject_name])
        subject_item.setFlags(subject_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        tree.addTopLevelItem(subject_item)
        period_start = self.period_start.date().toPython()
        period_end = self.period_end.date().toPython()
        evidenced_competency_ids = set(
            subject.competency_ids_with_evidence_in_period(
                period_start,
                period_end,
            )
        )
        section_specs = (
            (
                "evidenced",
                "Mit Belegen im Berichtszeitraum",
                lambda competency: competency.selectable
                and competency.competency_id in evidenced_competency_ids,
            ),
            (
                "retained",
                "Gespeicherte historische Auswahl",
                lambda competency: not competency.selectable
                and competency.competency_id in self.selected_competency_ids,
            ),
            (
                "available",
                "Weitere auswählbare Kompetenzen",
                lambda competency: competency.selectable
                and competency.competency_id not in evidenced_competency_ids,
            ),
            (
                "historical",
                "Weitere historische Einträge",
                lambda competency: not competency.selectable
                and competency.competency_id not in self.selected_competency_ids,
            ),
        )
        sections: dict[str, QTreeWidgetItem] = {}
        areas: dict[tuple[str, str], QTreeWidgetItem] = {}
        topics: dict[tuple[str, str, str], QTreeWidgetItem] = {}
        ordered_competencies = tuple(
            competency
            for _section_key, _section_title, predicate in section_specs
            for competency in subject.competencies
            if predicate(competency)
        )
        for competency in ordered_competencies:
            section_key, section_title = next(
                (key, title)
                for key, title, predicate in section_specs
                if predicate(competency)
            )
            section = sections.get(section_key)
            if section is None:
                section = QTreeWidgetItem([section_title])
                section.setFlags(
                    section.flags() & ~Qt.ItemFlag.ItemIsSelectable
                )
                subject_item.addChild(section)
                sections[section_key] = section
            area_key = (section_key, competency.learning_area)
            area = areas.get(area_key)
            if area is None:
                area = QTreeWidgetItem([competency.learning_area])
                section.addChild(area)
                areas[area_key] = area
            topic_key = (
                section_key,
                competency.learning_area,
                competency.competency_group,
            )
            topic = topics.get(topic_key)
            if topic is None:
                topic = QTreeWidgetItem([competency.competency_group])
                area.addChild(topic)
                topics[topic_key] = topic
            is_selected = competency.competency_id in self.selected_competency_ids
            if not competency.selectable and is_selected:
                suffix = " · historisch ausgewählt · nicht mehr regulär verfügbar"
            elif not competency.selectable:
                suffix = " · historisch · nicht regulär verfügbar"
            elif competency.competency_id in evidenced_competency_ids:
                suffix = " · Beleg im Berichtszeitraum"
            else:
                suffix = ""
            item = QTreeWidgetItem([f"{competency.competency_text}{suffix}"])
            item.setData(0, Qt.ItemDataRole.UserRole, competency.competency_id)
            item.setToolTip(0, self._documentation_state_label(competency.documentation_state))
            if competency.selectable or is_selected:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    0,
                    Qt.CheckState.Checked
                    if is_selected
                    else Qt.CheckState.Unchecked,
                )
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            topic.addChild(item)
        for section in sections.values():
            section.setExpanded(True)
        subject_item.setExpanded(True)
        tree.blockSignals(False)

    def _evidence_header_text(
        self,
        subject: LearningReportSubjectViewModel,
    ) -> str:
        evidenced_count = subject.evidenced_count(
            self.period_start.date().toPython(),
            self.period_end.date().toPython(),
        )
        return (
            f"{evidenced_count} von {subject.current_count} aktuellen Kompetenzen "
            "mit Beleg im Berichtszeitraum. Die Übersicht ist Arbeitsgrundlage "
            "und keine automatische Auswertung."
        )

    def _toggle_subject(self, subject_id: str, checked: bool) -> None:
        subject = self._subject(subject_id)
        if subject is None:
            return
        if checked:
            self.selected_subject_ids.add(subject_id)
        else:
            self.selected_subject_ids.discard(subject_id)
            self.selected_competency_ids.difference_update(
                competency.competency_id for competency in subject.competencies
            )
            self.selected_observation_ids.difference_update(
                evidence.observation_id for evidence in subject.evidence
            )
            tree = self.subject_widgets[subject_id]["tree"]
            if isinstance(tree, QTreeWidget):
                self._populate_competency_tree(subject, tree)
        badge = self.subject_widgets.get(subject_id, {}).get("selection_badge")
        if isinstance(badge, StatusBadge):
            badge.setText("Für Bericht ausgewählt" if checked else "Noch nicht ausgewählt")
            badge.setAccessibleName(badge.text())
            badge.setProperty("badgeTone", "info" if checked else "neutral")
            badge.style().unpolish(badge)
            badge.style().polish(badge)
        self._render_evidence(subject)
        self._refresh_subject_selection_summary()
        self._schedule_preview()

    def _toggle_competency(
        self, subject_id: str, item: QTreeWidgetItem, column: int
    ) -> None:
        competency_id = str(item.data(column, Qt.ItemDataRole.UserRole) or "")
        if not competency_id:
            return
        if subject_id not in self.selected_subject_ids:
            item.setCheckState(column, Qt.CheckState.Unchecked)
            return
        if item.checkState(column) == Qt.CheckState.Checked:
            self.selected_competency_ids.add(competency_id)
        else:
            self.selected_competency_ids.discard(competency_id)
            subject = self._subject(subject_id)
            competency = next(
                (
                    entry
                    for entry in subject.competencies
                    if entry.competency_id == competency_id
                ),
                None,
            ) if subject else None
            if competency is not None and not competency.selectable:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                tree = self.subject_widgets.get(subject_id, {}).get("tree")
                if isinstance(tree, QTreeWidget):
                    QTimer.singleShot(
                        0,
                        tree,
                        lambda current_subject=subject: self._refresh_competency_tree(
                            current_subject
                        ),
                    )
        subject = self._subject(subject_id)
        if subject:
            self._render_evidence(subject)
        self._schedule_preview()

    def _refresh_competency_tree(
        self,
        subject: LearningReportSubjectViewModel,
    ) -> None:
        tree = self.subject_widgets.get(subject.subject_id, {}).get("tree")
        if isinstance(tree, QTreeWidget):
            self._populate_competency_tree(subject, tree)

    def _visible_evidence_for_subject(
        self, subject: LearningReportSubjectViewModel
    ) -> tuple[LearningReportEvidenceViewModel, ...]:
        selected = {
            competency.competency_id
            for competency in subject.competencies
            if competency.competency_id in self.selected_competency_ids
        }
        if not selected:
            return ()
        return tuple(
            evidence
            for evidence in subject.evidence
            if selected.intersection(evidence.competency_ids)
        )

    def _render_evidence(self, subject: LearningReportSubjectViewModel) -> None:
        widgets = self.subject_widgets.get(subject.subject_id)
        if not widgets:
            return
        evidence_layout = widgets["evidence_layout"]
        if not isinstance(evidence_layout, QVBoxLayout):
            return
        self._clear_layout(evidence_layout)
        checks: dict[str, QCheckBox] = {}
        items = self._visible_evidence_for_subject(subject)
        if not items:
            empty = self._small_label(
                "Wähle zuerst konkrete Kompetenzen. Passende Beobachtungsbelege erscheinen dann hier."
            )
            evidence_layout.addWidget(empty)
        for evidence in items:
            in_period = (
                self.period_start.date().toPython()
                <= evidence.observed_on
                <= self.period_end.date().toPython()
            )
            suffix = "" if in_period else " · außerhalb des Berichtszeitraums"
            checkbox = QCheckBox(f"{evidence.display_label}{suffix}")
            checkbox.setChecked(evidence.observation_id in self.selected_observation_ids)
            checkbox.setEnabled(subject.subject_id in self.selected_subject_ids and in_period)
            checkbox.setToolTip("Bewusste Auswahl durch die Lehrkraft")
            checkbox.toggled.connect(
                lambda checked, observation_id=evidence.observation_id: self._toggle_evidence(
                    observation_id, checked
                )
            )
            evidence_layout.addWidget(checkbox)
            checks[evidence.observation_id] = checkbox
        self._evidence_checks[subject.subject_id] = checks

    def _toggle_evidence(self, observation_id: str, checked: bool) -> None:
        if checked:
            self.selected_observation_ids.add(observation_id)
        else:
            self.selected_observation_ids.discard(observation_id)
        self._schedule_preview()

    def _toggle_chart(self, subject_id: str, chart_type: str, checked: bool) -> None:
        selection = (subject_id, chart_type)
        if checked:
            self._selected_charts.add(selection)
        else:
            self._selected_charts.discard(selection)
        self._schedule_preview()

    def _period_changed(self) -> None:
        for subject in self.preparation.subjects:
            tree = self.subject_widgets.get(subject.subject_id, {}).get("tree")
            if isinstance(tree, QTreeWidget):
                self._populate_competency_tree(subject, tree)
            evidence_header = self.subject_widgets.get(
                subject.subject_id,
                {},
            ).get("evidence_header")
            if isinstance(evidence_header, SectionHeader):
                evidence_header.description_label.setText(
                    self._evidence_header_text(subject)
                )
            self._render_evidence(subject)
        self._refresh_workspace_context()
        self._schedule_preview()

    def report_draft_view_model(self) -> LearningReportDraftViewModel:
        subjects: list[LearningReportSubjectDraftViewModel] = []
        chart_selections: list[LearningReportChartSelectionViewModel] = []
        for subject in self.preparation.subjects:
            if subject.subject_id not in self.selected_subject_ids:
                continue
            subjects.append(self._subject_draft_state(subject.subject_id))
            for available_subject_id, chart_type in sorted(self._selected_charts):
                if available_subject_id == subject.subject_id:
                    chart_selections.append(
                        LearningReportChartSelectionViewModel(subject.subject_id, chart_type)
                    )
        saved = self._saved_draft
        return LearningReportDraftViewModel(
            student_id=self.preparation.student_id,
            period_start=self.period_start.date().toPython(),
            period_end=self.period_end.date().toPython(),
            teacher_name=self.teacher_input.text(),
            overall_text=self.overall_input.toPlainText(),
            subjects=tuple(subjects),
            competency_ids=tuple(sorted(self.selected_competency_ids)),
            observation_ids=tuple(sorted(self.selected_observation_ids)),
            chart_selections=tuple(chart_selections),
            report_draft_id=saved.report_draft_id if saved else "",
            report_type=saved.report_type if saved else "learning_development",
            status=saved.status if saved else "draft",
            created_at=saved.created_at if saved else "",
            updated_at=saved.updated_at if saved else "",
            unavailable_observation_ids=tuple(
                sorted(
                    self._unavailable_observation_ids
                    & self.selected_observation_ids
                )
            ),
        )

    def report_draft(self) -> LearningReportDraft:
        persisted = self.report_draft_view_model()
        return LearningReportDraft(
            period_start=persisted.period_start,
            period_end=persisted.period_end,
            teacher_name=persisted.teacher_name,
            overall_view=persisted.overall_text,
            goals="",
            support="",
            selected_subject_ids=persisted.selected_subject_ids,
            selected_competency_ids=persisted.competency_ids,
            selected_observation_ids=persisted.observation_ids,
            subject_texts=persisted.subjects,
            chart_selections=persisted.chart_selections,
            unavailable_observation_ids=persisted.unavailable_observation_ids,
        )

    def report_output_model(self) -> object:
        return build_report_output_model(self.preparation, self.report_draft())

    def apply_saved_draft(self, saved: LearningReportDraftViewModel) -> None:
        self._saved_draft = saved
        self._dirty = False
        self._preview_stale = True
        self.draft_status.setText(self._draft_status_text())
        self.draft_status.setToolTip(saved.report_draft_id)
        self.save_button.setText("Entwurf gespeichert")
        animate_save_confirmation(self.save_button)
        self.workspace_message.set_message("")
        self.toast.show_message("Berichtsentwurf gespeichert.", tone="success")
        self._refresh_workspace_context()
        self.update_preview()
        QTimer.singleShot(1600, lambda: self.save_button.setText("Entwurf speichern"))

    def apply_revision_status(
        self,
        status: LearningReportRevisionStatusViewModel,
        *,
        finalized: bool = False,
    ) -> None:
        self._revision_status = status
        self._revision_stale = True
        if hasattr(self, "finalization_message"):
            self.finalization_message.set_message("")
        self.workspace_message.set_message("")
        if self.workspace_built["revisions"]:
            self._render_revision_context()
        self._refresh_workspace_context()
        if finalized:
            self.toast.show_message(
                f"Revision {status.current_revision_number} wurde unveränderlich gespeichert.",
                tone="success",
            )

    def show_finalization_error(self, message: str) -> None:
        self._ensure_workspace_built("revisions")
        self.finalization_message.set_message(message, tone="error")
        self.workspace_message.set_message(message, tone="error")
        self._set_mode(3)
        self.finalization_message.setFocus()

    def _request_finalization(self) -> None:
        if not self._validate_period():
            return
        self.finalization_message.set_message("")
        self.workspace_message.set_message("")
        self.finalization_requested.emit(self.report_draft_view_model())

    def show_finalization_confirmation(
        self,
        preview: LearningReportFinalizationPreviewViewModel,
    ) -> None:
        confirmation = self.create_finalization_confirmation(preview)
        confirmation.exec()

    def create_finalization_confirmation(
        self,
        preview: LearningReportFinalizationPreviewViewModel,
    ) -> QDialog:
        """Create the serious, non-destructive irreversible confirmation dialog."""
        dialog = QDialog(self)
        dialog.setObjectName("LearningReportFinalizationConfirmation")
        dialog.setWindowTitle(
            "Bericht finalisieren"
            if preview.revision_number == 1
            else "Neue Revision finalisieren"
        )
        dialog.setModal(True)
        dialog.setMinimumWidth(600)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        layout.addWidget(
            DialogHeader(
                f"Revision {preview.revision_number} finalisieren",
                f"{preview.student_display_name} · {preview.period_label}",
                "Bitte den gespeicherten Berichtsentwurf vor der Bestätigung prüfen.",
                icon_name="report",
                context_role="report",
            )
        )
        summary = AppCard("soft")
        summary_layout = QGridLayout(summary)
        summary_layout.setContentsMargins(18, 16, 18, 16)
        summary_layout.setHorizontalSpacing(20)
        summary_layout.setVerticalSpacing(8)
        values = (
            ("Kind", preview.student_display_name),
            ("Berichtstyp", preview.report_type_label),
            ("Zeitraum", preview.period_label),
            ("Fächer", ", ".join(preview.subject_names)),
            ("Kompetenzen", str(preview.competency_count)),
            ("Beobachtungen", str(preview.observation_count)),
            ("Neue Revision", str(preview.revision_number)),
        )
        for row, (label_text, value) in enumerate(values):
            label = QLabel(label_text)
            set_label_style(label, "field_label")
            content = QLabel(value or "–")
            content.setWordWrap(True)
            set_label_style(content, "body")
            summary_layout.addWidget(label, row, 0)
            summary_layout.addWidget(content, row, 1)
        layout.addWidget(summary)
        responsible = QLineEdit(preview.suggested_responsible_display_name)
        responsible.setObjectName("LearningReportFinalizedByInput")
        responsible.setPlaceholderText("Anzeigename der verantwortlichen Lehrkraft")
        responsible.setAccessibleName("Verantwortliche Lehrkraft für die neue Revision")
        layout.addWidget(
            self._field("Verantwortliche Lehrkraft", responsible)
        )
        layout.addWidget(
            InlineMessage(
                "Diese Revision wird unveränderlich gespeichert. Spätere Korrekturen "
                "erfolgen im bestehenden Entwurf und erzeugen eine neue Revision; "
                "bestehende Revisionen bleiben erhalten.",
                tone="warning",
            )
        )
        acknowledge = QCheckBox(
            "Ich habe den Bericht geprüft und möchte ihn als unveränderliche Revision finalisieren."
        )
        acknowledge.setObjectName("LearningReportFinalizationAcknowledgement")
        acknowledge.setAccessibleName(
            "Bestätigung für die unveränderliche Finalisierung"
        )
        layout.addWidget(acknowledge)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Abbrechen")
        configure_button(cancel, "quiet")
        cancel.clicked.connect(dialog.reject)
        confirm = QPushButton(
            "Bericht finalisieren"
            if preview.revision_number == 1
            else "Neue Revision finalisieren"
        )
        confirm.setObjectName("LearningReportFinalizationConfirmButton")
        configure_button(confirm, "primary")
        confirm.setAccessibleDescription(
            "Wird erst nach Name und ausdrücklicher Bestätigung verfügbar."
        )
        confirm.setEnabled(False)

        def update_confirmation_state() -> None:
            confirm.setEnabled(
                bool(responsible.text().strip()) and acknowledge.isChecked()
            )

        responsible.textChanged.connect(lambda _text: update_confirmation_state())
        acknowledge.toggled.connect(lambda _checked: update_confirmation_state())

        def confirm_finalization() -> None:
            name = responsible.text().strip()
            if not name:
                return
            dialog.accept()
            self.finalize_confirmed.emit(preview.report_draft_id, name)

        confirm.clicked.connect(confirm_finalization)
        buttons.addWidget(cancel)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)
        return dialog

    def _request_save(self) -> None:
        if not self._validate_period():
            return
        self.save_requested.emit(self.report_draft_view_model())

    def reject(self) -> None:
        if not self._dirty:
            super().reject()
            return
        confirmation = QMessageBox(self)
        confirmation.setIcon(QMessageBox.Icon.Warning)
        confirmation.setWindowTitle("Ungespeicherte Änderungen")
        confirmation.setText("In der Berichtswerkstatt gibt es ungespeicherte Änderungen.")
        confirmation.setInformativeText(
            "Weiter bearbeiten behält den aktuellen Arbeitsstand geöffnet. "
            "Änderungen verwerfen schließt die Berichtswerkstatt ohne Speichern."
        )
        continue_button = confirmation.addButton(
            "Weiter bearbeiten",
            QMessageBox.ButtonRole.RejectRole,
        )
        discard_button = confirmation.addButton(
            "Änderungen verwerfen",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        configure_button(continue_button, "primary", "Bericht weiter bearbeiten")
        configure_button(discard_button, "destructive", "Änderungen verwerfen")
        confirmation.setDefaultButton(continue_button)
        confirmation.setEscapeButton(continue_button)
        stabilize_message_box_buttons(
            confirmation,
            (discard_button, continue_button),
        )
        confirmation.exec()
        if confirmation.clickedButton() is discard_button:
            super().reject()

    def _request_pdf(self) -> None:
        if not self.selected_subject_ids:
            QMessageBox.information(
                self, "Bericht vorbereiten", "Bitte mindestens ein Fach auswählen."
            )
            return
        if not self._validate_period():
            return
        try:
            output_model = self.report_output_model()
        except ValueError as error:
            QMessageBox.warning(self, "Bericht vorbereiten", str(error))
            return
        self.pdf_requested.emit(output_model)

    def _validate_period(self) -> bool:
        if self.period_end.date() <= self.period_start.date():
            message = "Das Ende des Berichtszeitraums muss nach dem Beginn liegen."
            if hasattr(self, "workspace_message"):
                self.workspace_message.set_message(message, tone="error")
            if hasattr(self, "finalization_message"):
                self.finalization_message.set_message(message, tone="error")
            else:
                QMessageBox.warning(self, "Bericht vorbereiten", message)
            return False
        return True

    def update_preview(self) -> None:
        if not self.workspace_built["preview"] or not hasattr(self, "preview_layout"):
            return
        if not self._preview_stale:
            return
        self._clear_layout(self.preview_layout)
        pages = [self._cover_preview_page(), self._overview_preview_page()]
        pages.extend(
            self._subject_preview_page(subject)
            for subject in self.preparation.subjects
            if subject.subject_id in self.selected_subject_ids
        )
        pages.append(self._closing_preview_page())
        for page_number, page in enumerate(pages, 1):
            self._set_page_number(page, page_number, len(pages))
            self.preview_layout.addWidget(page, 0, Qt.AlignmentFlag.AlignHCenter)
        self.preview_layout.addStretch(1)
        source_status = (
            "enthält noch nicht gespeicherte Änderungen"
            if self._dirty
            else "entspricht dem gespeicherten Entwurf"
        )
        self.preview_status.setText(
            f"Vorschau des aktuellen Entwurfs · {source_status} · {len(pages)} Seiten"
        )
        self._refresh_closing_summary()
        self._preview_stale = False

    def _cover_preview_page(self) -> QFrame:
        page, layout = self._paper_page("Lernentwicklungsbericht")
        layout.addSpacing(22)
        heading = QLabel("Lernentwicklungsbericht")
        set_label_style(heading, "screen_title")
        layout.addWidget(heading)
        layout.addWidget(self._small_label("Eine zeitraumbezogene pädagogische Dokumentation"))
        name = QLabel(self.preparation.student_name)
        name.setStyleSheet("font-size: 27px; font-weight: 650; color: #17324D;")
        layout.addWidget(name)
        meta = QGridLayout()
        meta.setHorizontalSpacing(34)
        meta.setVerticalSpacing(10)
        for row, (key, value) in enumerate(
            (
                ("STAMMGRUPPE", self.preparation.group_name or "–"),
                ("KURS", self.preparation.course_name or "–"),
                ("ZEITRAUM", f"{self.period_start.text()} – {self.period_end.text()}"),
                ("BERICHTSART", "Lernentwicklungsbericht"),
                ("VERANTWORTLICHE LEHRKRAFT", self.teacher_input.text().strip() or "Noch offen"),
            )
        ):
            meta.addWidget(self._eyebrow(key), row, 0)
            value_label = QLabel(value)
            set_label_style(value_label, "card_title")
            meta.addWidget(value_label, row, 1)
        layout.addLayout(meta)
        layout.addSpacing(20)
        title = QLabel("Pädagogischer Gesamtblick")
        set_label_style(title, "section_title")
        layout.addWidget(title)
        body = QLabel(self.overall_input.toPlainText().strip() or "Noch kein Text eingetragen.")
        body.setWordWrap(True)
        set_label_style(body, "body")
        layout.addWidget(body)
        return page

    def _overview_preview_page(self) -> QFrame:
        page, layout = self._paper_page("Überblick")
        heading = QLabel("Überblick über die Fachabschnitte")
        set_label_style(heading, "screen_title")
        layout.addWidget(heading)
        layout.addWidget(
            self._responsibility_note(
                "Die Übersicht zeigt Dokumentationsumfang, keine Gesamtpunktzahl und keinen Leistungswert."
            )
        )
        for subject in self.preparation.subjects:
            if subject.subject_id not in self.selected_subject_ids:
                continue
            row = QHBoxLayout()
            row.setContentsMargins(16, 12, 16, 12)
            text = QVBoxLayout()
            title = QLabel(subject.subject_name)
            set_label_style(title, "card_title")
            text.addWidget(title)
            text.addWidget(
                self._small_label(
                    f"{subject.documented_count} von {subject.current_count} aktuellen Kompetenzen dokumentiert"
                )
            )
            row.addLayout(text, 1)
            row.addWidget(self._small_label("Fachabschnitt ausgewählt"))
            layout.addWidget(self._layout_card(row))
        return page

    def _subject_preview_page(self, subject: LearningReportSubjectViewModel) -> QFrame:
        page, layout = self._paper_page(subject.subject_name)
        heading = QLabel(subject.subject_name)
        set_label_style(heading, "screen_title")
        layout.addWidget(heading)
        subject_draft = self._subject_draft_state(subject.subject_id)
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)
        for index, (title, text) in enumerate(
            (
                ("Lernentwicklung", subject_draft.development_text),
                ("Stärken", subject_draft.strengths_text),
                ("Unterstützungsbedarf", subject_draft.support_needs_text),
                ("Nächste Ziele", subject_draft.next_goals_text),
            )
        ):
            block = QVBoxLayout()
            label = QLabel(title)
            set_label_style(label, "card_title")
            block.addWidget(label)
            body = QLabel(text or "Noch kein Text eingetragen.")
            body.setWordWrap(True)
            block.addWidget(body)
            grid.addLayout(block, index // 2, index % 2)
        layout.addLayout(grid)
        selected = tuple(
            competency
            for competency in subject.competencies
            if competency.competency_id in self.selected_competency_ids
        )
        title = QLabel("Ausgewählte konkrete Kompetenzen")
        set_label_style(title, "section_title")
        layout.addWidget(title)
        if not selected:
            layout.addWidget(self._small_label(
                "Keine konkrete Kompetenz ausgewählt. Die Auswahl kann im Bereich „Kompetenzen & Belege“ ergänzt werden."
            ))
        for competency in selected:
            suffix = (
                " · historisch ausgewählt; nicht mehr regulär verfügbar"
                if not competency.selectable
                else ""
            )
            item = QLabel(
                f"•  {competency.learning_area} → {competency.competency_group}\n"
                f"   {competency.competency_text}{suffix}"
            )
            item.setWordWrap(True)
            layout.addWidget(item)
        evidence = tuple(
            selection.evidence
            for selection in build_selected_report_evidence(
                self.preparation,
                self.report_draft(),
            )
            if selection.subject_id == subject.subject_id
        )
        title = QLabel("Bewusst ausgewählte Beobachtungsbelege")
        set_label_style(title, "section_title")
        layout.addWidget(title)
        if not evidence:
            layout.addWidget(self._small_label(
                "Keine Beobachtungsbelege ausgewählt. Die Auswahl kann im Bereich „Kompetenzen & Belege“ ergänzt werden."
            ))
        for item in evidence:
            body = QLabel(
                f"{item.observed_on.strftime('%d.%m.%Y')} · {item.context}\n"
                f"{item.note or 'Keine Notiz'}"
            )
            body.setWordWrap(True)
            layout.addWidget(self._document_block(body))
        selected_chart_types = [
            chart_type
            for subject_id, chart_type in sorted(self._selected_charts)
            if subject_id == subject.subject_id
        ]
        title = QLabel("Entwicklungsdarstellungen")
        set_label_style(title, "section_title")
        layout.addWidget(title)
        if not selected_chart_types:
            layout.addWidget(
                self._responsibility_note(
                    "Für diesen Fachbereich wurde kein Diagramm ausgewählt."
                )
            )
        for chart_type in selected_chart_types:
            layout.addWidget(self._chart_preview(subject, chart_type, selected, evidence))
        return page

    def _chart_preview(
        self,
        subject: LearningReportSubjectViewModel,
        chart_type: str,
        selected_competencies: tuple[object, ...],
        selected_evidence: tuple[LearningReportEvidenceViewModel, ...],
    ) -> QFrame:
        block = QVBoxLayout()
        title = dict(CHART_OPTIONS)[chart_type]
        label = QLabel(title)
        set_label_style(label, "card_title")
        block.addWidget(label)
        if chart_type == "documentation_coverage":
            progress = QProgressBar()
            progress.setObjectName("CompetencyCockpitProgressBar")
            progress.setTextVisible(False)
            progress.setRange(0, max(1, subject.current_count))
            progress.setValue(subject.documented_count)
            block.addWidget(progress)
            block.addWidget(
                self._small_label(
                    f"{subject.documented_count} von {subject.current_count} dokumentiert · keine Leistungsbewertung"
                )
            )
        elif chart_type == "competency_timeline":
            block.addWidget(
                self._small_label(
                    f"{len(selected_competencies)} ausgewählte Kompetenzen · datierte Einzelstände · keine Trendlinie"
                )
            )
        else:
            block.addWidget(
                self._small_label(
                    f"{len(selected_evidence)} bewusst ausgewählte Beobachtungen in zeitlicher Reihenfolge"
                )
            )
        return self._layout_card(block, "LearningReportDocumentBlock")

    def _closing_preview_page(self) -> QFrame:
        page, layout = self._paper_page("Abschluss")
        heading = QLabel("Übergreifende Entwicklung & nächste Schritte")
        set_label_style(heading, "screen_title")
        layout.addWidget(heading)
        for subject in self.preparation.subjects:
            if subject.subject_id not in self.selected_subject_ids:
                continue
            subject_draft = self._subject_draft_state(subject.subject_id)
            title = QLabel(subject.subject_name)
            set_label_style(title, "section_title")
            layout.addWidget(title)
            body = QLabel(
                subject_draft.next_goals_text
                or subject_draft.support_needs_text
                or "Noch kein nächster Schritt eingetragen."
            )
            body.setWordWrap(True)
            layout.addWidget(body)
        layout.addSpacing(22)
        selected_unavailable = tuple(
            sorted(
                self._unavailable_observation_ids
                & self.selected_observation_ids
            )
        )
        if selected_unavailable:
            title = QLabel("Nicht mehr verfügbare Beobachtungsbelege")
            set_label_style(title, "section_title")
            layout.addWidget(title)
            layout.addWidget(
                self._responsibility_note(
                    "Die gespeicherten Referenzen bleiben erhalten; Inhalte werden nicht rekonstruiert."
                )
            )
            for index, _observation_id in enumerate(selected_unavailable, 1):
                layout.addWidget(
                    self._small_label(
                        f"Gespeicherter Beobachtungsbeleg {index} · nicht mehr verfügbar"
                    )
                )
            layout.addSpacing(12)
        layout.addWidget(
            self._small_label(
                f"Verantwortliche Lehrkraft: {self.teacher_input.text().strip() or 'Noch offen'}"
            )
        )
        layout.addWidget(self._small_label("Status: Entwurf · noch nicht fachlich freigegeben"))
        return page

    def _unavailable_evidence_card(self) -> QFrame:
        card = create_card()
        card.setObjectName("LearningReportUnavailableEvidence")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(8)
        title = QLabel("Nicht mehr verfügbare Beobachtungsbelege")
        set_label_style(title, "section_title")
        layout.addWidget(title)
        layout.addWidget(
            self._small_label(
                "Die gespeicherten Bezüge bleiben erhalten. Es werden keine Inhalte rekonstruiert."
            )
        )
        for index, observation_id in enumerate(
            sorted(self._unavailable_observation_ids),
            1,
        ):
            check = QCheckBox(
                f"Nicht verfügbaren Beobachtungsbeleg {index} beibehalten"
            )
            check.setObjectName(
                f"LearningReportUnavailableEvidence_{observation_id}"
            )
            check.setChecked(observation_id in self.selected_observation_ids)
            check.toggled.connect(
                lambda checked, selected_id=observation_id: self._toggle_evidence(
                    selected_id, checked
                )
            )
            layout.addWidget(check)
        return card

    def _paper_page(self, kicker: str) -> tuple[QFrame, QVBoxLayout]:
        page = QFrame()
        page.setObjectName("LearningReportPaperPage")
        page.setFixedWidth(820)
        page.setMinimumHeight(1120)
        page.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(66, 54, 66, 48)
        layout.setSpacing(18)
        header = QHBoxLayout()
        header.addWidget(self._eyebrow("JENAPLAN-SCHULE"))
        header.addStretch(1)
        header.addWidget(self._small_label(kicker))
        layout.addLayout(header)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #D8E2E7;")
        layout.addWidget(separator)
        footer = QHBoxLayout()
        footer.addWidget(self._small_label("Vertraulicher Lernentwicklungsbericht"))
        footer.addStretch(1)
        page._learning_report_footer = footer
        return page, layout

    def _set_page_number(self, page: QFrame, page_number: int, total: int) -> None:
        layout = page.layout()
        if not isinstance(layout, QVBoxLayout):
            return
        layout.addStretch(1)
        footer = getattr(page, "_learning_report_footer", None)
        if isinstance(footer, QHBoxLayout):
            footer.addWidget(self._small_label(f"Seite {page_number} von {total}"))
            layout.addLayout(footer)

    def _page_canvas(self) -> tuple[QWidget, QVBoxLayout]:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 30, 46, 56)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        return content, layout

    def _scroll_page(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    def _page_heading(self, eyebrow: str, title: str, hint: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.addWidget(self._eyebrow(eyebrow))
        heading = QLabel(title)
        set_label_style(heading, "screen_title")
        layout.addWidget(heading)
        layout.addWidget(self._small_label(hint))
        return layout

    def _responsibility_note(self, text: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("LearningReportResponsibilityNote")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.addWidget(self._small_label(text))
        return frame

    def _document_block(self, widget: QWidget) -> QFrame:
        layout = QVBoxLayout()
        layout.addWidget(widget)
        return self._layout_card(layout, "LearningReportDocumentBlock")

    def _layout_card(
        self, layout: QVBoxLayout | QHBoxLayout, object_name: str = "LearningReportReportCard"
    ) -> QFrame:
        frame = QFrame()
        frame.setObjectName(object_name)
        layout.setContentsMargins(16, 12, 16, 12)
        frame.setLayout(layout)
        return frame

    def _eyebrow(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("LearningReportEyebrow")
        return label

    def _small_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        set_label_style(label, "small")
        return label

    def _read_only_field(self, label_text: str, value: str) -> QWidget:
        value_label = QLabel(value)
        value_label.setWordWrap(True)
        set_label_style(value_label, "body")
        return self._field(label_text, value_label)

    def _field(self, label_text: str, widget: QWidget) -> QWidget:
        field = QWidget()
        layout = QVBoxLayout(field)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(label_text)
        set_label_style(label, "field_label")
        layout.addWidget(label)
        layout.addWidget(widget)
        return field

    def _subject(self, subject_id: str) -> LearningReportSubjectViewModel | None:
        return next(
            (subject for subject in self.preparation.subjects if subject.subject_id == subject_id),
            None,
        )

    def _subject_draft_state(
        self, subject_id: str
    ) -> LearningReportSubjectDraftViewModel:
        texts = self.subject_widgets.get(subject_id, {}).get("texts")
        if isinstance(texts, dict):
            return LearningReportSubjectDraftViewModel(
                subject_id,
                self._edit_text(texts.get("strengths")),
                self._edit_text(texts.get("development")),
                self._edit_text(texts.get("support")),
                self._edit_text(texts.get("goals")),
            )
        return self._subject_texts.get(
            subject_id,
            LearningReportSubjectDraftViewModel(subject_id),
        )

    def _schedule_preview(self, *_args: object) -> None:
        if self._ui_ready:
            self._dirty = True
            self.draft_status.setText(self._draft_status_text())
            self._refresh_workspace_context()
        self._preview_stale = True
        self._refresh_closing_summary()
        if (
            self.workspace_built["preview"]
            and self.workspace_navigation.current_key() == "preview"
        ):
            self._preview_timer.start()

    def _refresh_closing_summary(self) -> None:
        if not hasattr(self, "closing_summary"):
            return
        self.closing_summary.setText(
            f"{len(self.selected_subject_ids)} Fachabschnitte · "
            f"{len(self.selected_competency_ids)} Kompetenzen · "
            f"{len(self.selected_observation_ids)} Beobachtungsbelege"
        )

    def _draft_status_text(self) -> str:
        if self._dirty:
            return "Ungespeicherte Änderungen"
        if self._saved_draft and self._saved_draft.report_draft_id:
            return "Entwurf gespeichert"
        return "Neuer Entwurf · noch nicht gespeichert"

    def _refresh_workspace_context(self) -> None:
        if not hasattr(self, "header_context"):
            return
        teacher = self.teacher_input.text().strip() if hasattr(self, "teacher_input") else ""
        if hasattr(self, "period_start") and hasattr(self, "period_end"):
            period = f"{self.period_start.text()} bis {self.period_end.text()}"
        else:
            period = "Zeitraum offen"
        self.header_context.setText(
            f"Stammgruppe {self.preparation.group_name or '–'}  ·  "
            f"Kurs {self.preparation.course_name or '–'}  ·  "
            f"Lernentwicklungsbericht  ·  {period}  ·  "
            f"Verantwortlich: {teacher or 'noch offen'}"
        )
        status = self._revision_status
        self.header_status_badge.setText(status.badge_text)
        self.header_status_badge.setAccessibleName(f"Draftstatus: {status.badge_text}")
        tone = (
            "success"
            if status.state == "finalized"
            else "warning" if status.state == "draft_changed" else "info"
        )
        self.header_status_badge.setProperty("badgeTone", tone)
        self.header_status_badge.style().unpolish(self.header_status_badge)
        self.header_status_badge.style().polish(self.header_status_badge)
        if status.has_current_revision:
            self.header_revision_context.setText(
                f"Revision {status.current_revision_number} · {status.finalized_at}\n"
                f"{status.finalized_by_display_name}"
            )
            self.header_revision_context.setToolTip(status.current_revision_id)
        else:
            self.header_revision_context.setText("Noch keine finale Revision")
            self.header_revision_context.setToolTip("")

    @staticmethod
    def _documentation_state_label(state: str) -> str:
        return {
            "undocumented": "Noch nicht dokumentiert",
            "observed_unconfirmed": "Beobachtet, noch nicht bestätigt",
        "confirmed": "Bestätigter Stand",
        "newer_observations": "Neue Beobachtungen seit Bestätigung",
        "confirmation_unknown": "Bestätigungsstand unklar – bitte erneut bestätigen",
        }.get(state, state)

    @staticmethod
    def _edit_text(widget: object) -> str:
        return widget.toPlainText() if isinstance(widget, QTextEdit) else ""

    @staticmethod
    def _reset_tree_checks(tree: QTreeWidget) -> None:
        tree.blockSignals(True)
        iterator = QTreeWidgetItemIterator(tree)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.ItemDataRole.UserRole):
                item.setCheckState(0, Qt.CheckState.Unchecked)
            iterator += 1
        tree.blockSignals(False)

    @classmethod
    def _clear_layout(cls, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                cls._clear_layout(child_layout)  # type: ignore[arg-type]


class LearningReportRevisionDialog(MotionDialog):
    """Fully read-only final report view backed only by one snapshot projection."""

    pdf_requested = Signal(str)
    pdf_open_requested = Signal(str)

    def __init__(
        self,
        revision: LearningReportRevisionViewModel,
        parent: QWidget | None = None,
        artifact: LearningReportPdfArtifactViewModel | None = None,
    ) -> None:
        super().__init__(parent)
        self.revision = revision
        self.artifact = artifact
        self.setObjectName("LearningReportRevisionDialog")
        self.setWindowTitle(
            f"Finale Berichtfassung · Revision {revision.revision_number}"
        )
        self.resize(1180, 820)
        self.setMinimumSize(760, 620)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        header_shell = QFrame()
        header_shell.setObjectName("LearningReportTopBar")
        header_layout = QVBoxLayout(header_shell)
        header_layout.setContentsMargins(24, 16, 24, 14)
        header_layout.setSpacing(8)
        close = QPushButton("Zurück")
        configure_button(close, "secondary", "Zur Berichtswerkstatt zurückkehren")
        close.clicked.connect(self.accept)
        header = DialogHeader(
            f"{self.revision.report_type_label} · Revision {self.revision.revision_number}",
            f"{self.revision.student_display_name} · {self.revision.period_label}",
            "Historisches, schreibgeschütztes Dokument aus dem gespeicherten Snapshot.",
            icon_name="report",
            context_role="report",
        )
        if self.revision.status == "finalized":
            self.pdf_button = QPushButton("Finales PDF erstellen")
            self.pdf_button.setObjectName("LearningReportGenerateFinalPdfButton")
            configure_button(
                self.pdf_button,
                "secondary",
                "Finales PDF ausschließlich aus dieser unveränderlichen Revision erstellen",
            )
            self.pdf_button.clicked.connect(self._request_pdf_action)
            header.add_action(self.pdf_button)
        header.add_action(close)
        header_layout.addWidget(header)
        context_row = QHBoxLayout()
        badge = StatusBadge(
            f"{self.revision.status_label} · Revision {self.revision.revision_number}",
            tone="success" if self.revision.status_label == "Aktuell" else "neutral",
        )
        badge.setToolTip(
            f"{self.revision.learning_report_revision_id}\n"
            f"Snapshot SHA-256: {self.revision.snapshot_sha256}"
        )
        context_row.addWidget(badge)
        read_only = StatusBadge("Schreibgeschützt", tone="neutral")
        read_only.setAccessibleName("Diese Revision ist schreibgeschützt")
        context_row.addWidget(read_only)
        context_row.addStretch(1)
        metadata = QLabel(
            f"Finalisiert am {self.revision.finalized_at} · "
            f"verantwortlich: {self.revision.finalized_by_display_name}"
        )
        metadata.setWordWrap(True)
        set_label_style(metadata, "muted")
        context_row.addWidget(metadata)
        header_layout.addLayout(context_row)
        root.addWidget(header_shell)
        snapshot_message = InlineMessage(
            "Diese Ansicht liest ausschließlich den bei der Finalisierung "
            "gespeicherten Snapshot. Aktuelle Stammdaten und Beobachtungen "
            "werden nicht nachgeladen.",
            tone="info",
        )
        snapshot_message.setAccessibleName(
            "Hinweis zur historischen, unveränderlichen Datenquelle"
        )
        root.addWidget(
            snapshot_message
        )
        self.pdf_status = InlineMessage()
        self.pdf_status.setObjectName("LearningReportFinalPdfStatus")
        root.addWidget(self.pdf_status)
        if self.artifact is not None:
            self.apply_pdf_artifact(self.artifact)
        scroll = QScrollArea()
        scroll.setAccessibleName(
            f"Historische Berichtrevision {self.revision.revision_number}"
        )
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        canvas = QWidget()
        canvas.setObjectName("LearningReportRevisionCanvas")
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(24, 28, 24, 44)
        canvas_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        paper = QFrame()
        paper.setObjectName("LearningReportRevisionPaper")
        paper.setMaximumWidth(920)
        paper.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(paper)
        layout.setContentsMargins(54, 46, 54, 54)
        layout.setSpacing(16)
        document_title = QLabel(self.revision.report_type_label)
        set_label_style(document_title, "screen_title")
        layout.addWidget(document_title)
        document_context = QLabel(
            f"{self.revision.student_display_name} · {self.revision.period_label} · "
            f"Revision {self.revision.revision_number}"
        )
        document_context.setWordWrap(True)
        set_label_style(document_context, "muted")
        layout.addWidget(document_context)
        layout.addWidget(self._context_card())
        layout.addWidget(
            self._text_card("Pädagogischer Gesamtblick", self.revision.overall_text)
        )
        for subject in self.revision.subjects:
            layout.addWidget(self._subject_card(subject))
        layout.addStretch(1)
        canvas_layout.addWidget(paper)
        scroll.setWidget(canvas)
        root.addWidget(scroll, 1)

    def apply_pdf_artifact(
        self,
        artifact: LearningReportPdfArtifactViewModel,
    ) -> None:
        """Show the verified immutable artifact without exposing storage logic."""
        self.artifact = artifact
        self.pdf_status.set_message(
            f"Finales PDF vorhanden: {artifact.file_name} · "
            f"erstellt {artifact.created_at}",
            tone="success",
        )
        if hasattr(self, "pdf_button"):
            self.pdf_button.setText("Finales PDF anzeigen")
            self.pdf_button.setEnabled(True)
            self.pdf_button.setAccessibleName(
                "Verifiziertes finales PDF dieser Berichtrevision anzeigen"
            )

    def _request_pdf_action(self) -> None:
        if self.artifact is None:
            self.pdf_requested.emit(self.revision.learning_report_revision_id)
            return
        self.pdf_open_requested.emit(
            self.artifact.learning_report_pdf_artifact_id
        )

    def show_pdf_error(self, message: str) -> None:
        self.pdf_status.set_message(message, tone="error")

    def _context_card(self) -> AppCard:
        card = AppCard("soft")
        layout = QGridLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setHorizontalSpacing(22)
        layout.setVerticalSpacing(10)
        values = (
            ("Kind", self.revision.student_display_name),
            ("Stammgruppe", self.revision.group_name or "–"),
            ("Kurs", self.revision.course_name or "–"),
            ("Berichtstyp", self.revision.report_type_label),
            ("Zeitraum", self.revision.period_label),
            ("Finalisiert am", self.revision.finalized_at),
            ("Finalisiert von", self.revision.finalized_by_display_name),
        )
        for row, (label_text, value) in enumerate(values):
            label = QLabel(label_text)
            set_label_style(label, "field_label")
            content = QLabel(value)
            content.setWordWrap(True)
            set_label_style(content, "body")
            layout.addWidget(label, row, 0)
            layout.addWidget(content, row, 1)
        return card

    def _text_card(self, title_text: str, text: str) -> AppCard:
        card = AppCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        layout.addWidget(SectionHeader(title_text))
        body = QLabel(text or "Kein Text gespeichert.")
        body.setWordWrap(True)
        set_label_style(body, "body")
        layout.addWidget(body)
        return card

    def _subject_card(self, subject: object) -> AppCard:
        card = AppCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(SectionHeader(str(getattr(subject, "subject_name", "Fach"))))
        for title, text in (
            ("Lernentwicklung", str(getattr(subject, "development_text", ""))),
            ("Stärken", str(getattr(subject, "strengths_text", ""))),
            ("Unterstützungsbedarf", str(getattr(subject, "support_needs_text", ""))),
            ("Nächste Ziele", str(getattr(subject, "next_goals_text", ""))),
        ):
            heading = QLabel(title)
            set_label_style(heading, "card_title")
            layout.addWidget(heading)
            body = QLabel(text or "Kein Text gespeichert.")
            body.setWordWrap(True)
            layout.addWidget(body)
        layout.addWidget(SectionHeader("Eingefrorene Kompetenzen"))
        competencies = tuple(getattr(subject, "competencies", ()))
        if not competencies:
            layout.addWidget(EmptyState(
                "In dieser Revision wurde keine Kompetenz ausgewählt. "
                "Der eingefrorene Stand bleibt unverändert."
            ))
        for competency in competencies:
            suffix = " · historisch" if getattr(competency, "historical_reference", False) else ""
            item = QLabel(
                f"{getattr(competency, 'learning_area', '')} → "
                f"{getattr(competency, 'competency_group', '')}\n"
                f"{getattr(competency, 'competency_text', '')}{suffix}"
            )
            item.setWordWrap(True)
            layout.addWidget(item)
        layout.addWidget(SectionHeader("Eingefrorene Beobachtungsbelege"))
        observations = tuple(getattr(subject, "observations", ()))
        if not observations:
            layout.addWidget(EmptyState(
                "In dieser Revision wurde kein Beobachtungsbeleg ausgewählt. "
                "Der eingefrorene Stand bleibt unverändert."
            ))
        for observation in observations:
            item = QLabel(
                f"{getattr(observation, 'observed_on', '')} · "
                f"{getattr(observation, 'context', '')}\n"
                f"{getattr(observation, 'content', '')}"
            )
            item.setWordWrap(True)
            layout.addWidget(item)
        charts = tuple(getattr(subject, "charts", ()))
        if charts:
            layout.addWidget(SectionHeader("Gespeicherte Diagrammdaten"))
            for chart in charts:
                chart_label = QLabel(
                    f"{getattr(chart, 'title', '')} · {getattr(chart, 'summary', '')}"
                )
                chart_label.setWordWrap(True)
                layout.addWidget(chart_label)
                for detail in tuple(getattr(chart, "details", ())):
                    detail_label = QLabel(f"• {detail}")
                    detail_label.setWordWrap(True)
                    set_label_style(detail_label, "muted")
                    layout.addWidget(detail_label)
        return card
