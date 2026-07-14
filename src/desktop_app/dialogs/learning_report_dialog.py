"""Prototype-faithful PySide workspace for persistent learning-report drafts."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt, QTimer, Signal
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

from src.desktop_app.theme import PRIMARY_BUTTON_STYLESHEET, create_card, set_label_style
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportChartSelectionViewModel,
    LearningReportDraft,
    LearningReportDraftViewModel,
    LearningReportEvidenceViewModel,
    LearningReportPreparationViewModel,
    LearningReportSubjectDraftViewModel,
    LearningReportSubjectViewModel,
    build_report_output_model,
)


CHART_OPTIONS = (
    ("documentation_coverage", "Dokumentationsabdeckung"),
    ("competency_timeline", "Kompetenzentwicklung mit Einzelständen"),
    ("observation_timeline", "Zeitachse ausgewählter Beobachtungen"),
)


class LearningReportDialog(QDialog):
    """Edit, persist, preview and export one report draft through explicit signals."""

    save_requested = Signal(object)
    pdf_requested = Signal(object)

    def __init__(
        self,
        preparation: LearningReportPreparationViewModel,
        parent: QWidget | None = None,
        initial_draft: LearningReportDraftViewModel | None = None,
    ) -> None:
        super().__init__(parent)
        self.preparation = preparation
        self._saved_draft = initial_draft
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
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(120)
        self._preview_timer.timeout.connect(self.update_preview)

        self.setWindowTitle(f"Lernentwicklungsbericht · {preparation.student_name}")
        self.resize(1500, 980)
        self.setMinimumSize(760, 680)
        self._build()
        self._connect_live_preview()
        self.update_preview()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._top_bar())
        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self._editor_screen())
        self.mode_stack.addWidget(self._preview_screen())
        root.addWidget(self.mode_stack, 1)

    def _top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("LearningReportTopBar")
        bar.setFixedHeight(68)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 10, 20, 10)
        title = QVBoxLayout()
        title.setSpacing(0)
        brand = QLabel("Jenaplan Kompetenzmanager")
        brand.setObjectName("LearningReportBrand")
        subtitle = QLabel(
            f"Lernentwicklungsbericht · {self.preparation.student_name} · "
            f"{self.preparation.group_name or 'ohne Stammgruppe'}"
        )
        subtitle.setObjectName("LearningReportTopHint")
        title.addWidget(brand)
        title.addWidget(subtitle)
        layout.addLayout(title)
        layout.addStretch(1)
        self.edit_mode_button = QPushButton("✎  Bericht bearbeiten")
        self.preview_mode_button = QPushButton("▤  Berichtsvorschau")
        for button in (self.edit_mode_button, self.preview_mode_button):
            button.setObjectName("LearningReportModeButton")
            button.setCheckable(True)
            layout.addWidget(button)
        self.edit_mode_button.setChecked(True)
        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.setExclusive(True)
        self.mode_button_group.addButton(self.edit_mode_button)
        self.mode_button_group.addButton(self.preview_mode_button)
        self.edit_mode_button.clicked.connect(lambda: self._set_mode(0))
        self.preview_mode_button.clicked.connect(lambda: self._set_mode(1))
        return bar

    def _set_mode(self, index: int) -> None:
        self.mode_stack.setCurrentIndex(index)
        self.edit_mode_button.setChecked(index == 0)
        self.preview_mode_button.setChecked(index == 1)
        if index == 1:
            self.update_preview()

    def _editor_screen(self) -> QWidget:
        screen = QWidget()
        layout = QHBoxLayout(screen)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._editor_sidebar())
        self.editor_stack = QStackedWidget()
        self.editor_stack.addWidget(self._overview_editor())
        for subject in self.preparation.subjects:
            self.editor_stack.addWidget(self._subject_editor(subject))
        self.editor_stack.addWidget(self._closing_editor())
        layout.addWidget(self.editor_stack, 1)
        return screen

    def _editor_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("LearningReportSidebar")
        sidebar.setFixedWidth(248)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 18)
        layout.setSpacing(5)
        layout.addWidget(self._eyebrow("ARBEITSBEREICHE"))
        self.navigation_group = QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        entries = [("Dokument & Gesamtblick", 0)]
        entries.extend(
            (subject.subject_name, index + 1)
            for index, subject in enumerate(self.preparation.subjects)
        )
        entries.append(("Abschluss", len(self.preparation.subjects) + 1))
        for title, index in entries:
            button = QPushButton(title)
            button.setObjectName("LearningReportSubjectButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.clicked.connect(
                lambda _checked=False, target=index: self.editor_stack.setCurrentIndex(
                    target
                )
            )
            self.navigation_group.addButton(button)
            layout.addWidget(button)
        layout.addStretch(1)
        self.draft_status = QLabel(self._draft_status_text())
        self.draft_status.setWordWrap(True)
        set_label_style(self.draft_status, "subtle")
        layout.addWidget(self.draft_status)
        self.save_button = QPushButton("Entwurf speichern")
        self.save_button.clicked.connect(self._request_save)
        layout.addWidget(self.save_button)
        preview = QPushButton("Vorschau öffnen  →")
        preview.setStyleSheet(PRIMARY_BUTTON_STYLESHEET)
        preview.clicked.connect(lambda: self._set_mode(1))
        layout.addWidget(preview)
        close = QPushButton("Schließen")
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        return sidebar

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
            self._read_only_field("Stammgruppe", self.preparation.group_name or "–"),
            1,
            1,
        )
        layout.addWidget(self._read_only_field("Berichtsart", "Lernentwicklungsbericht"), 2, 0)
        self.teacher_input = QLineEdit(
            self._saved_draft.teacher_name if self._saved_draft else ""
        )
        layout.addWidget(self._field("Verantwortliche Lehrkraft", self.teacher_input), 2, 1)
        today = date.today()
        period_start = self._saved_draft.period_start if self._saved_draft else date(today.year, 1, 1)
        period_end = self._saved_draft.period_end if self._saved_draft else date(today.year, 12, 31)
        self.period_start = QDateEdit(QDate(period_start.year, period_start.month, period_start.day))
        self.period_end = QDateEdit(QDate(period_end.year, period_end.month, period_end.day))
        for editor in (self.period_start, self.period_end):
            editor.setCalendarPopup(True)
            editor.setDisplayFormat("dd.MM.yyyy")
        layout.addWidget(self._field("Zeitraum von", self.period_start), 3, 0)
        layout.addWidget(self._field("Zeitraum bis", self.period_end), 3, 1)
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
        title.addWidget(self._eyebrow("FACHAUSWAHL · ARBEITSBEREICH"))
        heading = QLabel(subject.subject_name)
        set_label_style(heading, "screen_title")
        title.addWidget(heading)
        title.addWidget(
            self._small_label(
                "Interne Arbeitsgrundlage und spätere Berichtsinhalte bleiben bewusst getrennt."
            )
        )
        title_row.addLayout(title, 1)
        include = QCheckBox("Fachabschnitt in Vorschau")
        include.setChecked(subject.subject_id in self.selected_subject_ids)
        title_row.addWidget(include, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(title_row)

        internal = QFrame()
        internal.setObjectName("LearningReportInternalCard")
        internal_layout = QVBoxLayout(internal)
        internal_layout.setContentsMargins(20, 18, 20, 20)
        internal_layout.setSpacing(12)
        internal_title = QHBoxLayout()
        label = QLabel("Interne Dokumentationsübersicht")
        set_label_style(label, "section_title")
        internal_title.addWidget(label)
        internal_title.addStretch(1)
        badge = QLabel("NUR ARBEITSGRUNDLAGE")
        badge.setObjectName("LearningReportInternalBadge")
        internal_title.addWidget(badge)
        internal_layout.addLayout(internal_title)
        internal_layout.addWidget(
            self._small_label(
                f"{subject.documented_count} von {subject.current_count} aktuellen Kompetenzen dokumentiert. "
                "Diese Hinweise werden nicht automatisch zu Berichtsaussagen."
            )
        )
        competency_title = QLabel("Konkrete Kompetenzen auswählen")
        set_label_style(competency_title, "card_title")
        internal_layout.addWidget(competency_title)
        internal_layout.addWidget(self._small_label("Fach → Kompetenzbereich → Thema → Kompetenz"))
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setRootIsDecorated(True)
        tree.setIndentation(20)
        tree.setMinimumHeight(300)
        self._populate_competency_tree(subject, tree)
        internal_layout.addWidget(tree)
        evidence_title = QLabel("Beobachtungsbelege auswählen")
        set_label_style(evidence_title, "card_title")
        internal_layout.addWidget(evidence_title)
        internal_layout.addWidget(
            self._small_label(
                "Angeboten werden nur Beobachtungen zu den bewusst ausgewählten Kompetenzen."
            )
        )
        evidence_container = QWidget()
        evidence_layout = QVBoxLayout(evidence_container)
        evidence_layout.setContentsMargins(0, 0, 0, 0)
        evidence_layout.setSpacing(8)
        internal_layout.addWidget(evidence_container)
        layout.addWidget(internal)

        report_card = QFrame()
        report_card.setObjectName("LearningReportReportCard")
        report_layout = QVBoxLayout(report_card)
        report_layout.setContentsMargins(20, 18, 20, 22)
        report_layout.setSpacing(12)
        report_title = QHBoxLayout()
        label = QLabel("Von Laura verantwortete Berichtsinhalte")
        set_label_style(label, "section_title")
        report_title.addWidget(label)
        report_title.addStretch(1)
        report_title.addWidget(self._eyebrow("SPÄTERE AUSGABE"))
        report_layout.addLayout(report_title)
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
            edit.setMinimumHeight(100)
            report_layout.addWidget(edit)
            text_edits[key] = edit
        layout.addWidget(report_card)

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
            checkbox.setChecked((subject.subject_id, chart_type) in self._selected_charts)
            chart_layout.addWidget(checkbox)
            chart_checks[chart_type] = checkbox
        layout.addWidget(chart_card)

        self.subject_widgets[subject.subject_id] = {
            "include": include,
            "tree": tree,
            "evidence_container": evidence_container,
            "evidence_layout": evidence_layout,
            "texts": text_edits,
            "charts": chart_checks,
        }
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
        for edit in text_edits.values():
            edit.textChanged.connect(self._schedule_preview)
        for checkbox in chart_checks.values():
            checkbox.toggled.connect(self._schedule_preview)
        self._render_evidence(subject)
        return self._scroll_page(content)

    def _closing_editor(self) -> QScrollArea:
        content, layout = self._page_canvas()
        layout.addLayout(
            self._page_heading(
                "ABSCHLUSS",
                "Bericht prüfen und ausgeben",
                "Die Vorschau zeigt den aktuellen Entwurf. Speichern und PDF-Erzeugung bleiben getrennte bewusste Aktionen.",
            )
        )
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
        if self._unavailable_observation_ids:
            layout.addWidget(self._unavailable_evidence_card())
        actions = QHBoxLayout()
        actions.addStretch(1)
        save = QPushButton("Entwurf speichern")
        save.clicked.connect(self._request_save)
        preview = QPushButton("Berichtsvorschau öffnen  →")
        preview.setStyleSheet(PRIMARY_BUTTON_STYLESHEET)
        preview.clicked.connect(lambda: self._set_mode(1))
        actions.addWidget(save)
        actions.addWidget(preview)
        layout.addLayout(actions)
        return self._scroll_page(content)

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
        title.addWidget(self._eyebrow("BERICHTSVORSCHAU"))
        heading = QLabel("Mehrseitige Dokumentansicht · live aus dem aktuellen Entwurf")
        set_label_style(heading, "card_title")
        title.addWidget(heading)
        tools_layout.addLayout(title)
        tools_layout.addStretch(1)
        self.preview_status = self._small_label("Aktueller Entwurf")
        tools_layout.addWidget(self.preview_status)
        back = QPushButton("←  Weiter bearbeiten")
        back.clicked.connect(lambda: self._set_mode(0))
        tools_layout.addWidget(back)
        save = QPushButton("Entwurf speichern")
        save.clicked.connect(self._request_save)
        tools_layout.addWidget(save)
        self.pdf_button = QPushButton("PDF erstellen")
        self.pdf_button.setStyleSheet(PRIMARY_BUTTON_STYLESHEET)
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
        subject_item = QTreeWidgetItem([subject.subject_name])
        subject_item.setFlags(subject_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        tree.addTopLevelItem(subject_item)
        areas: dict[str, QTreeWidgetItem] = {}
        topics: dict[tuple[str, str], QTreeWidgetItem] = {}
        for competency in subject.competencies:
            area = areas.get(competency.learning_area)
            if area is None:
                area = QTreeWidgetItem([competency.learning_area])
                subject_item.addChild(area)
                areas[competency.learning_area] = area
            topic_key = (competency.learning_area, competency.competency_group)
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
        subject_item.setExpanded(True)
        tree.blockSignals(False)

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
                self._reset_tree_checks(tree)
        self._render_evidence(subject)
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
        subject = self._subject(subject_id)
        if subject:
            self._render_evidence(subject)
        self._schedule_preview()

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

    def _period_changed(self) -> None:
        for subject in self.preparation.subjects:
            self._render_evidence(subject)
        self._schedule_preview()

    def report_draft_view_model(self) -> LearningReportDraftViewModel:
        subjects: list[LearningReportSubjectDraftViewModel] = []
        chart_selections: list[LearningReportChartSelectionViewModel] = []
        for subject in self.preparation.subjects:
            if subject.subject_id not in self.selected_subject_ids:
                continue
            widgets = self.subject_widgets[subject.subject_id]
            texts = widgets["texts"]
            charts = widgets["charts"]
            if not isinstance(texts, dict) or not isinstance(charts, dict):
                continue
            subjects.append(
                LearningReportSubjectDraftViewModel(
                    subject.subject_id,
                    self._edit_text(texts.get("strengths")),
                    self._edit_text(texts.get("development")),
                    self._edit_text(texts.get("support")),
                    self._edit_text(texts.get("goals")),
                )
            )
            for chart_type, checkbox in charts.items():
                if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
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
        self.draft_status.setText(self._draft_status_text())
        self.save_button.setText("Entwurf gespeichert")
        QTimer.singleShot(1600, lambda: self.save_button.setText("Entwurf speichern"))

    def _request_save(self) -> None:
        if not self._validate_period():
            return
        self.save_requested.emit(self.report_draft_view_model())

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
            QMessageBox.warning(
                self,
                "Bericht vorbereiten",
                "Das Ende des Berichtszeitraums muss nach dem Beginn liegen.",
            )
            return False
        return True

    def update_preview(self) -> None:
        if not hasattr(self, "preview_layout"):
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
        self.preview_status.setText(f"Live aktualisiert · {len(pages)} Seiten")
        if hasattr(self, "closing_summary"):
            self.closing_summary.setText(
                f"{len(self.selected_subject_ids)} Fachabschnitte · "
                f"{len(self.selected_competency_ids)} Kompetenzen · "
                f"{len(self.selected_observation_ids)} Beobachtungsbelege"
            )

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
            state = (
                "Fachabschnitt ausgewählt"
                if subject.subject_id in self.selected_subject_ids
                else "nicht für Ausgabe ausgewählt"
            )
            row.addWidget(self._small_label(state))
            layout.addWidget(self._layout_card(row))
        return page

    def _subject_preview_page(self, subject: LearningReportSubjectViewModel) -> QFrame:
        page, layout = self._paper_page(subject.subject_name)
        heading = QLabel(subject.subject_name)
        set_label_style(heading, "screen_title")
        layout.addWidget(heading)
        widgets = self.subject_widgets[subject.subject_id]
        texts = widgets["texts"]
        if isinstance(texts, dict):
            grid = QGridLayout()
            grid.setHorizontalSpacing(24)
            grid.setVerticalSpacing(16)
            for index, (title, key) in enumerate(
                (
                    ("Lernentwicklung", "development"),
                    ("Stärken", "strengths"),
                    ("Unterstützungsbedarf", "support"),
                    ("Nächste Ziele", "goals"),
                )
            ):
                block = QVBoxLayout()
                label = QLabel(title)
                set_label_style(label, "card_title")
                block.addWidget(label)
                body = QLabel(self._edit_text(texts.get(key)) or "Noch kein Text eingetragen.")
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
            layout.addWidget(self._small_label("Keine konkrete Kompetenz ausgewählt."))
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
            item
            for item in self._visible_evidence_for_subject(subject)
            if item.observation_id in self.selected_observation_ids
        )
        title = QLabel("Bewusst ausgewählte Beobachtungsbelege")
        set_label_style(title, "section_title")
        layout.addWidget(title)
        if not evidence:
            layout.addWidget(self._small_label("Keine Beobachtungsbelege ausgewählt."))
        for item in evidence:
            body = QLabel(
                f"{item.observed_on.strftime('%d.%m.%Y')} · {item.context}\n"
                f"{item.note or 'Keine Notiz'}"
            )
            body.setWordWrap(True)
            layout.addWidget(self._document_block(body))
        charts = widgets["charts"]
        selected_chart_types = []
        if isinstance(charts, dict):
            selected_chart_types = [
                chart_type
                for chart_type, checkbox in charts.items()
                if isinstance(checkbox, QCheckBox) and checkbox.isChecked()
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
            texts = self.subject_widgets[subject.subject_id]["texts"]
            if not isinstance(texts, dict):
                continue
            title = QLabel(subject.subject_name)
            set_label_style(title, "section_title")
            layout.addWidget(title)
            body = QLabel(
                self._edit_text(texts.get("goals"))
                or self._edit_text(texts.get("support"))
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
            for observation_id in selected_unavailable:
                layout.addWidget(
                    self._small_label(f"{observation_id} · nicht mehr verfügbar")
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
                "Nur die gespeicherte ID bleibt sichtbar. Es werden keine Inhalte rekonstruiert."
            )
        )
        for observation_id in sorted(self._unavailable_observation_ids):
            check = QCheckBox(
                f"{observation_id} · gespeicherten Bezug beibehalten"
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

    def _schedule_preview(self, *_args: object) -> None:
        self._preview_timer.start()

    def _draft_status_text(self) -> str:
        if self._saved_draft and self._saved_draft.report_draft_id:
            return f"Gespeicherter Entwurf\n{self._saved_draft.report_draft_id}"
        return "Neuer Entwurf\nNoch nicht gespeichert"

    @staticmethod
    def _documentation_state_label(state: str) -> str:
        return {
            "undocumented": "Noch nicht dokumentiert",
            "observed_unconfirmed": "Beobachtet, noch nicht bestätigt",
            "confirmed": "Bestätigter Stand",
            "newer_observations": "Neue Beobachtungen seit Bestätigung",
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
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout is not None:
                cls._clear_layout(child_layout)  # type: ignore[arg-type]
