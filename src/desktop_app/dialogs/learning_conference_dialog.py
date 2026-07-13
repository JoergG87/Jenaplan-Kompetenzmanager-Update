"""Prototype-faithful workspace for persistent learning-conference drafts."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date

from PySide6.QtCore import QDate, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.theme import set_label_style
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceCompetencyViewModel,
    LearningConferenceDraftViewModel,
    LearningConferenceEvidenceViewModel,
    LearningConferencePreparationViewModel,
)


CHART_OPTIONS = (
    ("documentation_coverage", "Dokumentationsabdeckung"),
    ("competency_timeline", "Kompetenzentwicklung"),
    ("observation_timeline", "Zeitachse ausgewählter Beobachtungsbelege"),
)


def _clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


def _label(text: str, role: str | None = None) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    if role:
        set_label_style(label, role)
    return label


def _frame(layout: QLayout, name: str = "LearningConferenceCard") -> QFrame:
    frame = QFrame()
    frame.setObjectName(name)
    frame.setLayout(layout)
    return frame


class _CollapsibleSection(QWidget):
    def __init__(self, title: str, content: QWidget, *, expanded: bool = False, indent: int = 0) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(indent, 0, 0, 0)
        layout.setSpacing(2)
        self.button = QToolButton()
        self.button.setObjectName("LearningConferenceHierarchyButton")
        self.button.setText(title)
        self.button.setCheckable(True)
        self.button.setChecked(expanded)
        self.button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.content = content
        self.content.setVisible(expanded)
        self.button.toggled.connect(self._toggle)
        layout.addWidget(self.button)
        layout.addWidget(content)

    def _toggle(self, expanded: bool) -> None:
        self.button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.content.setVisible(expanded)


class LearningConferenceDialog(QDialog):
    """Edit one LEG draft while keeping preparation and conversation distinct."""

    save_requested = Signal(object)

    def __init__(
        self,
        preparation: LearningConferencePreparationViewModel,
        parent: QWidget | None = None,
        initial_draft: LearningConferenceDraftViewModel | None = None,
    ) -> None:
        super().__init__(parent)
        self.preparation = preparation
        self._saved_draft = initial_draft
        self._selected_subject_ids = set(initial_draft.subject_ids if initial_draft else ())
        self._selected_cross_topics = set(initial_draft.cross_topic_keys if initial_draft else ())
        self._selected_competency_ids = set(initial_draft.competency_ids if initial_draft else ())
        self._selected_observation_ids = set(initial_draft.observation_ids if initial_draft else ())
        self._selected_chart_types = set(initial_draft.chart_types if initial_draft else ())
        self.subject_checks: dict[str, QCheckBox] = {}
        self.cross_topic_checks: dict[str, QCheckBox] = {}
        self.competency_checks: dict[str, QCheckBox] = {}
        self.competency_models: dict[str, LearningConferenceCompetencyViewModel] = {}
        self.competency_widgets: dict[str, QWidget] = {}
        self.competency_filter_notes: dict[str, QLabel] = {}
        self.competency_sections: dict[str, _CollapsibleSection] = {}
        self.competency_area_sections: list[tuple[str, tuple[str, ...], _CollapsibleSection]] = []
        self.competency_topic_sections: list[tuple[str, tuple[str, ...], _CollapsibleSection]] = []
        self.competency_empty_by_subject: dict[str, QLabel] = {}
        self.evidence_checks: dict[str, QCheckBox] = {}
        self.evidence_widgets: dict[str, QWidget] = {}
        self.chart_checks: dict[str, QCheckBox] = {}
        self.text_inputs: dict[str, QTextEdit] = {}
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(60)
        self._preview_timer.timeout.connect(self.rebuild_conversation)
        self.setWindowTitle(f"Lernentwicklungsgespräch · {preparation.student_name}")
        self.resize(1680, 1000)
        self.setMinimumSize(1200, 760)
        self._build()
        self._connect_updates()
        self._update_filters()
        self.rebuild_conversation()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._top_bar())
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("LearningConferenceWorkspace")
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._preparation_panel())
        splitter.addWidget(self._conversation_panel())
        splitter.setSizes([760, 920])
        splitter.setStretchFactor(0, 9)
        splitter.setStretchFactor(1, 11)
        root.addWidget(splitter, 1)

    def _top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("LearningConferenceTopBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(30, 13, 24, 13)
        title = QVBoxLayout()
        eyebrow = QLabel("LERNENTWICKLUNGSGESPRÄCH")
        eyebrow.setObjectName("LearningConferenceEyebrow")
        heading = QLabel("Gespräch vorbereiten und gemeinsam führen")
        heading.setObjectName("LearningConferenceTopTitle")
        self.status_label = QLabel(self._draft_status_text())
        self.status_label.setObjectName("LearningConferenceTopMeta")
        title.addWidget(eyebrow)
        title.addWidget(heading)
        title.addWidget(self.status_label)
        layout.addLayout(title)
        layout.addStretch(1)
        self.save_button = QPushButton("Entwurf speichern")
        self.save_button.setObjectName("LearningConferenceSaveButton")
        self.save_button.clicked.connect(self._request_save)
        close_button = QPushButton("Schließen")
        close_button.clicked.connect(self.reject)
        layout.addWidget(self.save_button)
        layout.addWidget(close_button)
        return bar

    def _preparation_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("LearningConferencePreparationPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        page = QVBoxLayout(content)
        page.setContentsMargins(28, 28, 28, 52)
        page.setSpacing(18)
        eyebrow = _label("VORBEREITUNG DER LEHRKRAFT", "field_label")
        eyebrow.setObjectName("LearningConferencePreparationEyebrow")
        page.addWidget(eyebrow)
        page.addWidget(_label("In fünf Minuten gesprächsbereit", "screen_title"))
        page.addWidget(_label("Wenige Schwerpunkte, konkrete Beispiele und ein kurzer Leitfaden reichen für den Gesprächseinstieg.", "subtle"))
        page.addWidget(self._context_card())
        page.addWidget(self._focus_card())
        page.addWidget(self._competencies_card())
        page.addWidget(self._evidence_card())
        page.addWidget(self._guide_card())
        page.addWidget(self._charts_card())
        page.addWidget(self._shared_result_card())
        page.addStretch(1)
        scroll = QScrollArea()
        scroll.setObjectName("LearningConferencePreparationScroll")
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return panel

    def _context_card(self) -> QFrame:
        layout = QGridLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(_label("Gesprächsrahmen", "section_title"), 0, 0, 1, 2)
        layout.addWidget(self._read_only_field("Kind", self.preparation.student_name), 1, 0)
        layout.addWidget(self._read_only_field("Stammgruppe", self.preparation.group_name or "–"), 1, 1)
        draft = self._saved_draft
        today = date.today()
        period_start = draft.period_start if draft else None
        period_end = draft.period_end if draft else None
        conference_date = draft.conference_date if draft and draft.conference_date else today
        self.period_start = self._optional_date_edit(period_start, "Zeitraum von")
        self.period_end = self._optional_date_edit(period_end, "Zeitraum bis")
        self.conference_date = self._date_edit(conference_date, "Gesprächsdatum")
        self.teacher_input = QLineEdit(draft.responsible_teacher if draft else "")
        self.teacher_input.setAccessibleName("Verantwortliche Lehrkraft")
        layout.addWidget(self._field("Zeitraum von", self.period_start), 2, 0)
        layout.addWidget(self._field("Zeitraum bis", self.period_end), 2, 1)
        layout.addWidget(self._field("Gesprächsdatum", self.conference_date), 3, 0)
        layout.addWidget(self._field("Lehrkraft", self.teacher_input), 3, 1)
        return _frame(layout)

    def _focus_card(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(_label("Gesprächsschwerpunkte", "section_title"))
        layout.addWidget(_label("Fachbereiche und übergreifende Themen bleiben bewusst getrennt.", "subtle"))
        layout.addWidget(_label("FACHLICHE BEREICHE", "field_label"))
        subject_grid = QGridLayout()
        for index, subject in enumerate(self.preparation.subjects):
            check = QCheckBox(subject.subject_name)
            check.setObjectName(f"LearningConferenceSubject_{subject.subject_id}")
            check.setChecked(subject.subject_id in self._selected_subject_ids)
            self.subject_checks[subject.subject_id] = check
            subject_grid.addWidget(check, index // 2, index % 2)
        layout.addLayout(subject_grid)
        layout.addWidget(_label("ÜBERGREIFENDE GESPRÄCHSTHEMEN", "field_label"))
        cross_grid = QGridLayout()
        for index, topic in enumerate(self.preparation.cross_topics):
            check = QCheckBox(topic.label)
            check.setObjectName(f"LearningConferenceCrossTopic_{topic.cross_topic_key}")
            check.setChecked(topic.cross_topic_key in self._selected_cross_topics)
            self.cross_topic_checks[topic.cross_topic_key] = check
            cross_grid.addWidget(check, index // 2, index % 2)
        layout.addLayout(cross_grid)
        return _frame(layout)

    def _competencies_card(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(9)
        layout.addWidget(_label("Kompetenzen als Gesprächsbelege", "section_title"))
        layout.addWidget(_label("Fach → Kompetenzbereich → Thema → Kompetenz. Der angezeigte Stand ist kanonisch und nicht editierbar.", "subtle"))
        self.competency_empty = _label("Bitte zuerst mindestens einen fachlichen Bereich auswählen.", "subtle")
        self.competency_empty.setObjectName("LearningConferenceCompetencyEmpty")
        layout.addWidget(self.competency_empty)
        for subject in self.preparation.subjects:
            grouped: dict[str, dict[str, list[LearningConferenceCompetencyViewModel]]] = defaultdict(lambda: defaultdict(list))
            for competency in subject.competencies:
                grouped[competency.learning_area or "Ohne Kompetenzbereich"][competency.competency_group or "Ohne Thema"].append(competency)
            area_host = QWidget()
            area_layout = QVBoxLayout(area_host)
            area_layout.setContentsMargins(12, 0, 0, 0)
            area_layout.setSpacing(3)
            for learning_area, topics in grouped.items():
                topic_host = QWidget()
                topic_layout = QVBoxLayout(topic_host)
                topic_layout.setContentsMargins(12, 0, 0, 0)
                topic_layout.setSpacing(3)
                for topic, competencies in topics.items():
                    options = QWidget()
                    options_layout = QVBoxLayout(options)
                    options_layout.setContentsMargins(12, 2, 0, 5)
                    competency_ids = tuple(
                        competency.competency_id for competency in competencies
                    )
                    for competency in competencies:
                        options_layout.addWidget(self._competency_option(competency))
                    topic_section = _CollapsibleSection(
                        topic,
                        options,
                        expanded=subject.subject_id in self._selected_subject_ids,
                    )
                    self.competency_topic_sections.append(
                        (subject.subject_id, competency_ids, topic_section)
                    )
                    topic_layout.addWidget(topic_section)
                area_competency_ids = tuple(
                    competency.competency_id
                    for competencies in topics.values()
                    for competency in competencies
                )
                area_section = _CollapsibleSection(
                    learning_area,
                    topic_host,
                    expanded=subject.subject_id in self._selected_subject_ids,
                )
                self.competency_area_sections.append(
                    (subject.subject_id, area_competency_ids, area_section)
                )
                area_layout.addWidget(area_section)
            section = _CollapsibleSection(subject.subject_name, area_host, expanded=subject.subject_id in self._selected_subject_ids)
            self.competency_sections[subject.subject_id] = section
            layout.addWidget(section)
            empty = _label(
                f"Für dieses Kind sind in {subject.subject_name} und im gewählten Zeitraum noch keine kompetenzbezogenen Beobachtungen dokumentiert.",
                "subtle",
            )
            empty.setObjectName(f"LearningConferenceCompetencyEmpty_{subject.subject_id}")
            self.competency_empty_by_subject[subject.subject_id] = empty
            layout.addWidget(empty)
        return _frame(layout)

    def _competency_option(self, competency: LearningConferenceCompetencyViewModel) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 9, 12, 10)
        check = QCheckBox(competency.competency_text)
        check.setObjectName(f"LearningConferenceCompetency_{competency.competency_id}")
        selected = competency.competency_id in self._selected_competency_ids
        check.setChecked(selected)
        check.setEnabled(competency.selectable or selected)
        if selected and not competency.selectable:
            check.toggled.connect(lambda checked, widget=check: widget.setEnabled(checked))
        self.competency_checks[competency.competency_id] = check
        self.competency_models[competency.competency_id] = competency
        layout.addWidget(check)
        status_parts = [part for part in (competency.documentation_state, competency.observed_proposal, competency.confirmed_rating) if part]
        status_text = " · ".join(status_parts) or "Noch kein dokumentierter Stand"
        status = _label(f"Dokumentationsstand: {status_text}", "small")
        status.setObjectName("LearningConferenceCanonicalStatus")
        layout.addWidget(status)
        filter_note = _label(
            "Bereits im Entwurf ausgewählt – außerhalb des aktuellen Filters.",
            "subtle",
        )
        filter_note.setObjectName("LearningConferenceCompetencyFilterNote")
        filter_note.setVisible(False)
        self.competency_filter_notes[competency.competency_id] = filter_note
        layout.addWidget(filter_note)
        if competency.historical or not competency.selectable:
            layout.addWidget(_label("Historischer Bezug · bleibt sichtbar, ist aber nicht neu auswählbar.", "subtle"))
        widget = _frame(layout, "LearningConferenceSoftBlock")
        self.competency_widgets[competency.competency_id] = widget
        return widget

    def _evidence_card(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(9)
        layout.addWidget(_label("Beobachtungsbelege", "section_title"))
        layout.addWidget(_label("Nur passende Belege dieses Kindes. Richtwert: drei bis fünf Beispiele.", "subtle"))
        self.evidence_warning = _frame(QHBoxLayout(), "LearningConferenceWarning")
        self.evidence_warning.layout().setContentsMargins(11, 9, 11, 9)
        self.evidence_warning_label = QLabel("")
        self.evidence_warning_label.setObjectName("LearningConferenceWarningText")
        self.evidence_warning_label.setWordWrap(True)
        self.evidence_warning.layout().addWidget(self.evidence_warning_label)
        layout.addWidget(self.evidence_warning)
        self.evidence_empty = _label("Für die gewählten Bereiche sind keine Beobachtungsbelege sichtbar.", "subtle")
        layout.addWidget(self.evidence_empty)
        for evidence in self.preparation.evidence:
            block = QVBoxLayout()
            block.setContentsMargins(12, 9, 12, 10)
            heading = QHBoxLayout()
            heading.addWidget(_label(evidence.subject_name or "Übergreifend", "card_title"))
            heading.addWidget(_label(f"{evidence.date_text} · {evidence.context}", "small"), 1)
            block.addLayout(heading)
            block.addWidget(_label(evidence.note or "Ohne Notiz", "body"))
            check = QCheckBox("Für das Gespräch auswählen")
            check.setObjectName(f"LearningConferenceEvidence_{evidence.observation_id}")
            check.setChecked(evidence.observation_id in self._selected_observation_ids)
            block.addWidget(check)
            if evidence.is_quick_observation:
                block.addWidget(_label("Schnellbeobachtung · nur als Textbeleg, nicht für Kompetenzvisualisierungen.", "subtle"))
            widget = _frame(block, "LearningConferenceSoftBlock")
            self.evidence_checks[evidence.observation_id] = check
            self.evidence_widgets[evidence.observation_id] = widget
            layout.addWidget(widget)
        unavailable = self._saved_draft.unavailable_observation_ids if self._saved_draft else ()
        for observation_id in unavailable:
            block = QVBoxLayout()
            block.setContentsMargins(12, 9, 12, 10)
            block.addWidget(_label("Nicht mehr verfügbarer Beobachtungsbeleg", "card_title"))
            block.addWidget(_label(f"{observation_id} · Die gespeicherte Referenz bleibt erhalten.", "subtle"))
            check = QCheckBox("Gespeicherten Bezug beibehalten")
            check.setChecked(True)
            block.addWidget(check)
            self.evidence_checks[observation_id] = check
            widget = _frame(block, "LearningConferenceSoftBlock")
            widget.setObjectName("LearningConferenceUnavailableEvidence")
            self.evidence_widgets[observation_id] = widget
            layout.addWidget(widget)
        return _frame(layout)

    def _guide_card(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(8)
        layout.addWidget(_label("Gesprächsleitfaden", "section_title"))
        layout.addWidget(_label("Vorbereitung der Lehrkraft · manuelle pädagogische Formulierungen.", "subtle"))
        fields = (
            ("conversation_entry_text", "Gesprächseinstieg"),
            ("child_retrospective_text", "Rückblick des Kindes"),
            ("teacher_perspective_text", "Sicht der Lehrkraft"),
            ("strengths_text", "Was gelingt dem Kind?"),
            ("development_fields_text", "Welche Entwicklung sehen wir?"),
            ("prepared_goals_text", "Vorbereitete Ziele"),
            ("prepared_support_text", "Vorbereitete Unterstützung"),
            ("prepared_agreements_text", "Vorbereitete Vereinbarungen"),
        )
        for key, title in fields:
            layout.addWidget(_label(title.upper(), "field_label"))
            value = getattr(self._saved_draft, key, "") if self._saved_draft else ""
            edit = QTextEdit(value)
            edit.setObjectName(f"LearningConferenceInput_{key}")
            edit.setAccessibleName(title)
            edit.setMinimumHeight(82)
            self.text_inputs[key] = edit
            layout.addWidget(edit)
        return _frame(layout)

    def _charts_card(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(9)
        layout.addWidget(_label("Optionale Gesprächsbilder", "section_title"))
        layout.addWidget(_label("Nur neutrale Dokumentations- und Evidenzdarstellungen; keine Scores oder automatische Trends.", "subtle"))
        for key, title in CHART_OPTIONS:
            check = QCheckBox(title)
            check.setObjectName(f"LearningConferenceChart_{key}")
            check.setChecked(key in self._selected_chart_types)
            self.chart_checks[key] = check
            layout.addWidget(check)
        return _frame(layout)

    def _shared_result_card(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(8)
        layout.addWidget(_label("Im Gespräch gemeinsam vereinbart", "section_title"))
        layout.addWidget(_label("Dieser Ergebnisteil bleibt sichtbar getrennt von der Vorbereitung.", "subtle"))
        fields = (
            ("agreed_goals_text", "Gemeinsam vereinbarte Ziele"),
            ("agreed_support_text", "Gemeinsam vereinbarte Unterstützung"),
            ("agreed_agreements_text", "Gemeinsam vereinbarte Vereinbarungen"),
            ("responsibilities_text", "Zuständigkeiten"),
        )
        for key, title in fields:
            layout.addWidget(_label(title.upper(), "field_label"))
            value = getattr(self._saved_draft, key, "") if self._saved_draft else ""
            edit = QTextEdit(value)
            edit.setObjectName(f"LearningConferenceInput_{key}")
            edit.setAccessibleName(title)
            edit.setMinimumHeight(82)
            self.text_inputs[key] = edit
            layout.addWidget(edit)
        review_date = self._saved_draft.next_review_date if self._saved_draft and self._saved_draft.next_review_date else date.today()
        self.next_review_date = self._date_edit(review_date, "Nächster Überprüfungszeitpunkt")
        layout.addWidget(self._field("Nächster Überprüfungszeitpunkt", self.next_review_date))
        return _frame(layout, "LearningConferenceShared")

    def _conversation_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("LearningConferenceConversationPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.conversation_content = QWidget()
        self.conversation_layout = QVBoxLayout(self.conversation_content)
        self.conversation_layout.setContentsMargins(44, 34, 44, 70)
        self.conversation_layout.setSpacing(8)
        scroll = QScrollArea()
        scroll.setObjectName("LearningConferenceConversationScroll")
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.conversation_content)
        layout.addWidget(scroll)
        return panel

    def _connect_updates(self) -> None:
        controls: Iterable[object] = (
            *self.subject_checks.values(), *self.cross_topic_checks.values(),
            *self.competency_checks.values(), *self.evidence_checks.values(),
            *self.chart_checks.values(),
        )
        for control in controls:
            control.toggled.connect(self._schedule_preview)
        for control in (*self.subject_checks.values(), *self.cross_topic_checks.values()):
            control.toggled.connect(self._update_filters)
        for control in self.competency_checks.values():
            control.toggled.connect(self._update_filters)
        for control in self.evidence_checks.values():
            control.toggled.connect(self._update_evidence_warning)
        for edit in self.text_inputs.values():
            edit.textChanged.connect(self._schedule_preview)
        for edit in (self.period_start, self.period_end, self.conference_date, self.next_review_date):
            edit.dateChanged.connect(self._schedule_preview)
        self.period_start.dateChanged.connect(self._update_filters)
        self.period_end.dateChanged.connect(self._update_filters)
        self.teacher_input.textChanged.connect(self._schedule_preview)

    def _schedule_preview(self, *_args: object) -> None:
        self._preview_timer.start()

    def _update_filters(self, *_args: object) -> None:
        selected_subjects = self._subject_ids()
        self.competency_empty.setVisible(not selected_subjects)
        self._update_competency_visibility(selected_subjects)
        selected_labels = {
            subject.subject_name for subject in self.preparation.subjects if subject.subject_id in selected_subjects
        }
        selected_labels.update(
            topic.label for topic in self.preparation.cross_topics if topic.cross_topic_key in self._cross_topic_keys()
        )
        visible_count = 0
        for evidence in self.preparation.evidence:
            visible = evidence.subject_name in selected_labels or bool(set(evidence.competency_ids) & self._competency_ids())
            self.evidence_widgets[evidence.observation_id].setVisible(visible)
            visible_count += int(visible)
        self.evidence_empty.setVisible(visible_count == 0)
        self._update_evidence_warning()

    def _update_competency_visibility(self, selected_subjects: set[str]) -> None:
        period_start, period_end = self._competency_filter_period()
        visible_ids: set[str] = set()
        for competency_id, competency in self.competency_models.items():
            selected = self.competency_checks[competency_id].isChecked()
            documented = competency.is_documented_in_period(period_start, period_end)
            visible = documented or selected
            self.competency_widgets[competency_id].setVisible(visible)
            self.competency_filter_notes[competency_id].setVisible(
                selected and not documented
            )
            if visible:
                visible_ids.add(competency_id)
        for subject_id, competency_ids, section in self.competency_topic_sections:
            section.setVisible(
                subject_id in selected_subjects
                and bool(set(competency_ids) & visible_ids)
            )
        for subject_id, competency_ids, section in self.competency_area_sections:
            section.setVisible(
                subject_id in selected_subjects
                and bool(set(competency_ids) & visible_ids)
            )
        for subject_id, section in self.competency_sections.items():
            subject_has_visible_competency = any(
                competency.subject_id == subject_id
                and competency_id in visible_ids
                for competency_id, competency in self.competency_models.items()
            )
            section.setVisible(
                subject_id in selected_subjects and subject_has_visible_competency
            )
            self.competency_empty_by_subject[subject_id].setVisible(
                subject_id in selected_subjects and not subject_has_visible_competency
            )
            subject_name = next(
                subject.subject_name
                for subject in self.preparation.subjects
                if subject.subject_id == subject_id
            )
            period_suffix = (
                " und im gewählten Zeitraum"
                if period_start is not None and period_end is not None
                else ""
            )
            self.competency_empty_by_subject[subject_id].setText(
                f"Für dieses Kind sind in {subject_name}{period_suffix} noch keine kompetenzbezogenen Beobachtungen dokumentiert."
            )

    def _competency_filter_period(self) -> tuple[date | None, date | None]:
        period_start = self._optional_date_value(self.period_start)
        period_end = self._optional_date_value(self.period_end)
        if period_start is None or period_end is None:
            return None, None
        return period_start, period_end

    def _update_evidence_warning(self, *_args: object) -> None:
        count = len(self._observation_ids())
        self.evidence_warning_label.setText(
            f"{count} Belege ausgewählt. Für ein ruhiges Gespräch empfehlen sich drei bis fünf. Die Auswahl bleibt unverändert."
            if count > 5 else ""
        )
        self.evidence_warning.setVisible(count > 5)

    def rebuild_conversation(self) -> None:
        _clear_layout(self.conversation_layout)
        self.conversation_layout.addWidget(_label("GESPRÄCHSMAPPE", "field_label"))
        hero = QVBoxLayout()
        hero.setContentsMargins(28, 24, 28, 26)
        title = QLabel(f"Gespräch mit {self.preparation.student_name}")
        title.setObjectName("LearningConferenceHeroTitle")
        meta = QLabel(f"{self.preparation.group_name or 'ohne Stammgruppe'} · {self._period_text()} · {self.conference_date.date().toString('dd.MM.yyyy')} · {self.teacher_input.text().strip() or 'Lehrkraft offen'}")
        meta.setObjectName("LearningConferenceHeroMeta")
        meta.setWordWrap(True)
        hero.addWidget(title)
        hero.addWidget(meta)
        self.conversation_layout.addWidget(_frame(hero, "LearningConferenceHero"))
        areas = self._selected_area_labels()
        goal_widgets = [_label(self._text("conversation_entry_text") or "Noch nicht formuliert.")]
        goal_widgets.extend(_label(name, "small") for name in areas)
        self.conversation_layout.addWidget(self._conversation_section(1, "Gesprächsziel", goal_widgets))
        self.conversation_layout.addWidget(self._conversation_section(2, "Was gelingt dem Kind?", [
            self._preview_block("RÜCKBLICK DES KINDES", self._text("child_retrospective_text")),
            self._preview_block("STÄRKEN", self._text("strengths_text")),
        ]))
        self.conversation_layout.addWidget(self._conversation_section(3, "Welche Entwicklung sehen wir?", [
            self._preview_block("SICHT DER LEHRKRAFT", self._text("teacher_perspective_text")),
            self._preview_block("ENTWICKLUNGSFELDER", self._text("development_fields_text")),
        ]))
        self.conversation_layout.addWidget(self._conversation_section(4, "Woran möchten wir gemeinsam arbeiten?", [
            self._preview_block("VORBEREITETE ZIELE", self._text("prepared_goals_text")),
        ]))
        self.conversation_layout.addWidget(self._evidence_section())
        self.conversation_layout.addWidget(self._agreements_section())
        self.conversation_layout.addStretch(1)

    def _conversation_section(self, number: int, title: str, widgets: Iterable[QWidget]) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 25, 4, 28)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        number_label = QLabel(f"{number:02d}")
        number_label.setObjectName("LearningConferenceSectionNumber")
        heading.addWidget(number_label)
        heading.addWidget(_label(title, "section_title"), 1)
        layout.addLayout(heading)
        for widget in widgets:
            layout.addWidget(widget)
        return _frame(layout, "LearningConferenceSection")

    def _evidence_section(self) -> QFrame:
        widgets: list[QWidget] = []
        competency_by_id = {
            competency.competency_id: competency
            for subject in self.preparation.subjects for competency in subject.competencies
        }
        for competency_id in sorted(self._competency_ids()):
            competency = competency_by_id.get(competency_id)
            if competency:
                widgets.append(self._preview_block(competency.subject_name.upper(), f"{competency.competency_group} · {competency.competency_text}"))
        evidence_by_id = {evidence.observation_id: evidence for evidence in self.preparation.evidence}
        for observation_id in sorted(self._observation_ids()):
            evidence = evidence_by_id.get(observation_id)
            if evidence:
                widgets.append(self._preview_block(f"{evidence.date_text} · {evidence.context}", evidence.note))
            else:
                widgets.append(self._preview_block("BELEG NICHT MEHR VERFÜGBAR", f"{observation_id} · Referenz bleibt erhalten."))
        for chart_type in sorted(self._chart_types()):
            if chart_type == "competency_timeline" and not self._competency_ids():
                continue
            if chart_type == "observation_timeline":
                chart_evidence = [e for e in self.preparation.evidence if e.observation_id in self._observation_ids() and not e.is_quick_observation]
                if not chart_evidence:
                    continue
            widgets.append(self._chart_widget(chart_type, competency_by_id, evidence_by_id))
        if not widgets:
            widgets.append(_label("Noch keine gesprächsgeeigneten Beispiele ausgewählt.", "subtle"))
        return self._conversation_section(5, "Welche Beispiele stützen unsere Einschätzung?", widgets)

    def _agreements_section(self) -> QFrame:
        prepared = QVBoxLayout()
        prepared.setContentsMargins(14, 12, 14, 14)
        prepared.addWidget(_label("VORBEREITUNG DER LEHRKRAFT", "field_label"))
        prepared.addWidget(_label(self._joined_text("prepared_support_text", "prepared_agreements_text")))
        shared = QVBoxLayout()
        shared.setContentsMargins(14, 12, 14, 14)
        shared.addWidget(_label("IM GESPRÄCH GEMEINSAM VEREINBART", "field_label"))
        shared.addWidget(_label(self._joined_text("agreed_goals_text", "agreed_support_text", "agreed_agreements_text", "responsibilities_text")))
        shared.addWidget(_label(f"Nächster Überprüfungszeitpunkt: {self.next_review_date.date().toString('dd.MM.yyyy')}", "small"))
        return self._conversation_section(6, "Welche Unterstützung und Vereinbarungen treffen wir?", [
            _frame(prepared, "LearningConferencePrepared"),
            _frame(shared, "LearningConferenceShared"),
        ])

    def draft_view_model(self) -> LearningConferenceDraftViewModel:
        return LearningConferenceDraftViewModel(
            student_id=self.preparation.student_id,
            period_start=self._optional_date_value(self.period_start),
            period_end=self._optional_date_value(self.period_end),
            conference_date=self.conference_date.date().toPython(),
            responsible_teacher=self.teacher_input.text().strip(),
            conversation_entry_text=self._text("conversation_entry_text"),
            child_retrospective_text=self._text("child_retrospective_text"),
            teacher_perspective_text=self._text("teacher_perspective_text"),
            strengths_text=self._text("strengths_text"),
            development_fields_text=self._text("development_fields_text"),
            prepared_goals_text=self._text("prepared_goals_text"),
            prepared_support_text=self._text("prepared_support_text"),
            prepared_agreements_text=self._text("prepared_agreements_text"),
            agreed_goals_text=self._text("agreed_goals_text"),
            agreed_support_text=self._text("agreed_support_text"),
            agreed_agreements_text=self._text("agreed_agreements_text"),
            responsibilities_text=self._text("responsibilities_text"),
            next_review_date=self.next_review_date.date().toPython(),
            subject_ids=tuple(sorted(self._subject_ids())),
            cross_topic_keys=tuple(sorted(self._cross_topic_keys())),
            competency_ids=tuple(sorted(self._competency_ids())),
            observation_ids=tuple(sorted(self._observation_ids())),
            chart_types=tuple(sorted(self._chart_types())),
            learning_conference_draft_id=self._saved_draft.learning_conference_draft_id if self._saved_draft else "",
            status=self._saved_draft.status if self._saved_draft else "draft",
            created_at=self._saved_draft.created_at if self._saved_draft else "",
            updated_at=self._saved_draft.updated_at if self._saved_draft else "",
            unavailable_observation_ids=self._saved_draft.unavailable_observation_ids if self._saved_draft else (),
        )

    def apply_saved_draft(self, draft: LearningConferenceDraftViewModel) -> None:
        self._saved_draft = draft
        self.status_label.setText(self._draft_status_text())

    def _request_save(self) -> None:
        self.save_requested.emit(self.draft_view_model())

    def _subject_ids(self) -> set[str]:
        return {key for key, check in self.subject_checks.items() if check.isChecked()}

    def _cross_topic_keys(self) -> set[str]:
        return {key for key, check in self.cross_topic_checks.items() if check.isChecked()}

    def _competency_ids(self) -> set[str]:
        return {key for key, check in self.competency_checks.items() if check.isChecked()}

    def _observation_ids(self) -> set[str]:
        return {key for key, check in self.evidence_checks.items() if check.isChecked()}

    def _chart_types(self) -> set[str]:
        return {key for key, check in self.chart_checks.items() if check.isChecked()}

    def _text(self, key: str) -> str:
        return self.text_inputs[key].toPlainText().strip()

    def _joined_text(self, *keys: str) -> str:
        values = [self._text(key) for key in keys if self._text(key)]
        return "\n\n".join(values) or "Noch nicht formuliert."

    def _selected_area_labels(self) -> tuple[str, ...]:
        labels = [subject.subject_name for subject in self.preparation.subjects if subject.subject_id in self._subject_ids()]
        labels.extend(topic.label for topic in self.preparation.cross_topics if topic.cross_topic_key in self._cross_topic_keys())
        return tuple(labels)

    def _period_text(self) -> str:
        period_start, period_end = self._competency_filter_period()
        if period_start is None or period_end is None:
            return "Zeitraum offen"
        return f"{period_start.strftime('%d.%m.%Y')}–{period_end.strftime('%d.%m.%Y')}"

    def _draft_status_text(self) -> str:
        if self._saved_draft and self._saved_draft.updated_at:
            return f"Entwurf gespeichert · {self._saved_draft.updated_at}"
        return "Neuer bearbeitbarer Entwurf · noch nicht gespeichert"

    def _preview_block(self, title: str, text: str) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 9, 12, 10)
        layout.addWidget(_label(title, "field_label"))
        layout.addWidget(_label(text or "Noch nicht formuliert."))
        return _frame(layout, "LearningConferenceSoftBlock")

    def _chart_description(self, chart_type: str) -> str:
        return {
            "documentation_coverage": "Zeigt, in welchen ausgewählten Gesprächsbereichen Dokumentation vorliegt – ohne Leistungswert.",
            "competency_timeline": "Datierte Einzelstände ausgewählter Kompetenzen – ohne Verbindungslinie oder automatische Deutung.",
            "observation_timeline": "Ordnet bewusst ausgewählte Beobachtungsbelege chronologisch ein – ohne Gewichtung.",
        }[chart_type]

    def _chart_widget(
        self,
        chart_type: str,
        competency_by_id: dict[str, LearningConferenceCompetencyViewModel],
        evidence_by_id: dict[str, LearningConferenceEvidenceViewModel],
    ) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 13, 15, 15)
        layout.setSpacing(8)
        layout.addWidget(_label(dict(CHART_OPTIONS)[chart_type], "card_title"))
        layout.addWidget(_label(self._chart_description(chart_type), "subtle"))
        selected_evidence = [
            evidence_by_id[observation_id]
            for observation_id in self._observation_ids()
            if observation_id in evidence_by_id
        ]
        if chart_type == "documentation_coverage":
            for area in self._selected_area_labels():
                has_evidence = any(evidence.subject_name == area for evidence in selected_evidence)
                row = QHBoxLayout()
                row.addWidget(_label(area, "small"), 1)
                marker = QLabel("●" if has_evidence else "○")
                marker.setStyleSheet("color: #0EA5A7; font-size: 18px;")
                row.addWidget(marker)
                layout.addLayout(row)
            layout.addWidget(_label("● ausgewählter Beleg vorhanden    ○ derzeit kein ausgewählter Beleg", "small"))
        elif chart_type == "competency_timeline":
            for competency_id in sorted(self._competency_ids()):
                competency = competency_by_id.get(competency_id)
                if competency is None:
                    continue
                layout.addWidget(_label(competency.competency_text, "small"))
                moments = sorted(
                    evidence.date_text
                    for evidence in selected_evidence
                    if not evidence.is_quick_observation and competency_id in evidence.competency_ids
                )
                if not moments:
                    layout.addWidget(_label("Kein ausgewählter datierter Kompetenzbeleg.", "subtle"))
                    continue
                row = QHBoxLayout()
                for moment in moments:
                    point = QVBoxLayout()
                    point.setContentsMargins(9, 7, 9, 7)
                    point.addWidget(_label(moment, "field_label"))
                    point.addWidget(_label("dokumentierter Einzelpunkt", "small"))
                    row.addWidget(_frame(point, "LearningConferenceSoftBlock"), 1)
                if len(moments) == 1:
                    row.addStretch(2)
                layout.addLayout(row)
        else:
            timeline = sorted(
                (evidence for evidence in selected_evidence if not evidence.is_quick_observation),
                key=lambda evidence: evidence.date_text,
            )
            for evidence in timeline:
                row = QHBoxLayout()
                row.addWidget(_label(evidence.date_text, "field_label"))
                row.addWidget(_label(evidence.subject_name, "card_title"))
                row.addWidget(_label(evidence.context, "small"), 1)
                layout.addLayout(row)
        return _frame(layout, "LearningConferenceChartCard")

    def _read_only_field(self, title: str, value: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_label(title.upper(), "field_label"))
        layout.addWidget(_label(value, "card_title"))
        return widget

    def _field(self, title: str, widget: QWidget) -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_label(title.upper(), "field_label"))
        layout.addWidget(widget)
        return host

    def _date_edit(self, value: date, accessible_name: str) -> QDateEdit:
        edit = QDateEdit(QDate(value.year, value.month, value.day))
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("dd.MM.yyyy")
        edit.setAccessibleName(accessible_name)
        return edit

    def _optional_date_edit(
        self,
        value: date | None,
        accessible_name: str,
    ) -> QDateEdit:
        minimum = QDate(1900, 1, 1)
        edit = QDateEdit()
        edit.setMinimumDate(minimum)
        edit.setSpecialValueText("Nicht gesetzt")
        edit.setDate(
            QDate(value.year, value.month, value.day) if value is not None else minimum
        )
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("dd.MM.yyyy")
        edit.setAccessibleName(accessible_name)
        return edit

    def _optional_date_value(self, edit: QDateEdit) -> date | None:
        if edit.date() == edit.minimumDate():
            return None
        return edit.date().toPython()
