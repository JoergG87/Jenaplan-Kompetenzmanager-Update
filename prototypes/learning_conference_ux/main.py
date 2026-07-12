"""Isolierter PySide6-UX-Prototyp fuer ein Lernentwicklungsgespraech."""

from __future__ import annotations

import sys
from collections import defaultdict
from collections.abc import Iterable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from demo_data import (
    CHARTS,
    COMPETENCIES,
    COMPETENCY_MOMENTS,
    COVERAGE_DEMO,
    CROSS_CUTTING_AREAS,
    DOCUMENT_HEADER,
    GUIDE,
    OBSERVATIONS,
    SUBJECT_AREAS,
    ChartDemo,
    CompetencyDemo,
    ObservationDemo,
)


NAVY = "#173B55"
BLUE = "#347AA5"
TURQUOISE = "#3FA7A3"
GREEN = "#6EA66E"
ORANGE = "#D98A45"
INK = "#253943"
MUTED = "#687D86"
LINE = "#DCE6E9"
SURFACE = "#F4F8F8"
AREA_COLORS = {
    "Deutsch": BLUE,
    "Mathematik": TURQUOISE,
    "EPU": ORANGE,
    "Kunst": "#7D79A8",
    "Arbeitsverhalten": "#67899B",
    "Sozialverhalten": GREEN,
    "Selbstständigkeit": "#B17A58",
    "Lernorganisation": "#6A8790",
}


APP_STYLE = f"""
QWidget {{
    color: {INK};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 14px;
}}
QMainWindow, QWidget#AppRoot {{ background: #EAF1F2; }}
QFrame#TopBar {{ background: {NAVY}; border: none; }}
QLabel#AppEyebrow {{ color: #A9D7D5; font-size: 11px; font-weight: 700; letter-spacing: 1.3px; }}
QLabel#AppTitle {{ color: white; font-size: 24px; font-weight: 650; }}
QLabel#DemoBadge {{
    color: white; background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 13px;
    padding: 6px 12px; font-size: 11px; font-weight: 700;
}}
QFrame#WorkspacePanel {{ background: {SURFACE}; border: none; }}
QFrame#ConversationPanel {{ background: #F8FAF9; border: none; }}
QFrame#Card {{ background: white; border: 1px solid {LINE}; border-radius: 15px; }}
QFrame#SoftBlock {{ background: #F7FAFA; border: none; border-radius: 10px; }}
QFrame#ConversationSection {{ background: transparent; border: none; border-bottom: 1px solid #E1E8E8; }}
QFrame#ChartCard {{ background: #F7FAF9; border: 1px solid #E3EBEA; border-radius: 12px; }}
QFrame#HeaderSummary {{ background: #EAF4F3; border: none; border-radius: 10px; }}
QFrame#ConversationHero {{ background: {NAVY}; border: none; border-radius: 18px; }}
QFrame#PreparedAgreement {{ background: #F2F7F6; border: none; border-radius: 11px; }}
QFrame#SharedAgreement {{ background: white; border: 1px dashed #BFCFD0; border-radius: 11px; }}
QLabel#PanelEyebrow, QLabel#SectionNumber, QLabel#FieldLabel {{
    color: {MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;
}}
QLabel#SectionNumber {{ color: {TURQUOISE}; }}
QLabel#PanelTitle {{ color: {NAVY}; font-size: 22px; font-weight: 650; }}
QLabel#SectionTitle {{ color: {NAVY}; font-size: 19px; font-weight: 650; }}
QLabel#CardTitle {{ color: {NAVY}; font-size: 14px; font-weight: 650; }}
QLabel#Hint {{ color: {MUTED}; font-size: 12px; }}
QLabel#Warning {{ color: #865424; background: #FFF5E8; border: none; border-radius: 9px; padding: 9px 11px; }}
QLabel#HeroEyebrow {{ color: #A9D7D5; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
QLabel#HeroTitle {{ color: white; font-size: 26px; font-weight: 650; }}
QLabel#HeroMeta {{ color: #DCEAEC; font-size: 13px; }}
QLabel#EmptyState {{ color: {MUTED}; background: #F5F8F8; border: none; border-radius: 10px; padding: 13px; }}
QLineEdit, QTextEdit {{ background: white; border: 1px solid #C8D6DA; border-radius: 9px; padding: 9px 11px; selection-background-color: {TURQUOISE}; }}
QLineEdit:focus, QTextEdit:focus {{ border: 2px solid {TURQUOISE}; }}
QCheckBox {{ spacing: 9px; padding: 3px 0; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
QCheckBox::indicator:unchecked {{ background: white; border: 1px solid #AABBC0; border-radius: 5px; }}
QCheckBox::indicator:checked {{ background: {TURQUOISE}; border: 1px solid {TURQUOISE}; border-radius: 5px; }}
QToolButton#HierarchyButton {{ color: {NAVY}; background: transparent; border: none; text-align: left; padding: 7px 5px; font-weight: 650; }}
QToolButton#HierarchyButton:hover {{ background: #EFF5F4; border-radius: 7px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 3px; }}
QScrollBar::handle:vertical {{ background: #B9C9CD; min-height: 34px; border-radius: 4px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QSplitter::handle {{ background: #D7E2E4; width: 1px; }}
"""


def make_label(text: str, role: str | None = None, wrap: bool = True) -> QLabel:
    widget = QLabel(text)
    if role:
        widget.setObjectName(role)
    widget.setWordWrap(wrap)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


def clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())
            item.layout().deleteLater()


def card(layout: QLayout, role: str = "Card") -> QFrame:
    frame = QFrame()
    frame.setObjectName(role)
    frame.setLayout(layout)
    return frame


def pill(text: str, color: str = TURQUOISE) -> QLabel:
    widget = make_label(text, wrap=False)
    widget.setStyleSheet(
        f"color: {color}; background: #F4F8F7; border: none; "
        "border-radius: 10px; padding: 4px 9px; font-size: 11px; font-weight: 650;"
    )
    widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return widget


class CollapsibleSection(QWidget):
    """Leichte, rein lokale Aufklappsektion fuer die Demo-Hierarchie."""

    def __init__(self, title: str, content: QWidget, expanded: bool = False, indent: int = 0) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(indent, 0, 0, 0)
        layout.setSpacing(2)
        self.button = QToolButton()
        self.button.setObjectName("HierarchyButton")
        self.button.setText(title)
        self.button.setCheckable(True)
        self.button.setChecked(expanded)
        self.button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.content = content
        self.content.setVisible(expanded)
        self.button.toggled.connect(self._set_expanded)
        layout.addWidget(self.button)
        layout.addWidget(self.content)

    def _set_expanded(self, expanded: bool) -> None:
        self.button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.content.setVisible(expanded)


class LearningConferencePrototype(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LEG vorbereiten · isolierter UX-Prototyp")
        self.resize(1680, 1000)
        self.setMinimumSize(1200, 760)

        self.header_fields: dict[str, QLineEdit] = {}
        self.subject_checks: list[tuple[str, QCheckBox]] = []
        self.cross_area_checks: list[tuple[str, QCheckBox]] = []
        self.competency_checks: list[tuple[CompetencyDemo, QCheckBox]] = []
        self.observation_checks: list[tuple[ObservationDemo, QCheckBox]] = []
        self.chart_checks: list[tuple[ChartDemo, QCheckBox]] = []
        self.hierarchy_sections: list[CollapsibleSection] = []
        self.competency_subject_sections: dict[str, CollapsibleSection] = {}
        self.observation_widgets: list[tuple[ObservationDemo, QWidget]] = []

        root = QWidget()
        root.setObjectName("AppRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._top_bar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._preparation_panel())
        splitter.addWidget(self._conversation_panel())
        splitter.setSizes([760, 920])
        splitter.setStretchFactor(0, 9)
        splitter.setStretchFactor(1, 11)
        root_layout.addWidget(splitter, 1)
        self.setCentralWidget(root)

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(60)
        self._preview_timer.timeout.connect(self.rebuild_conversation)
        self._connect_live_updates()
        self._update_preparation_filters()
        self._update_evidence_warning()
        self.rebuild_conversation()

    def _top_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("TopBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(30, 16, 30, 16)
        title = QVBoxLayout()
        title.setSpacing(2)
        title.addWidget(make_label("SPRINT 7D.1 · UX-PROTOTYP", "AppEyebrow"))
        title.addWidget(make_label("Lernentwicklungsgespräch vorbereiten", "AppTitle"))
        layout.addLayout(title)
        layout.addStretch()
        layout.addWidget(make_label("NUR FIKTIVE IN-MEMORY-DATEN", "DemoBadge", False))
        return frame

    def _preparation_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("WorkspacePanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 28, 28, 52)
        layout.setSpacing(18)
        layout.addWidget(make_label("VORBEREITUNG DER LEHRKRAFT", "PanelEyebrow"))
        layout.addWidget(make_label("In fünf Minuten gesprächsbereit", "PanelTitle"))
        layout.addWidget(make_label("Wenige Schwerpunkte, konkrete Beispiele und ein kurzer Leitfaden reichen für den Gesprächseinstieg.", "Hint"))
        layout.addWidget(self._document_header_card())
        layout.addWidget(self._focus_card())
        layout.addWidget(self._competencies_card())
        layout.addWidget(self._observations_card())
        layout.addWidget(self._guide_card())
        layout.addWidget(self._charts_card())
        layout.addStretch()
        scroll.setWidget(content)
        panel_layout.addWidget(scroll)
        return panel

    def _document_header_card(self) -> QFrame:
        layout = QGridLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)
        layout.addWidget(make_label("Gesprächsrahmen", "SectionTitle"), 0, 0, 1, 2)
        fields = (("student", "Kind"), ("period", "Zeitraum"), ("date", "Datum"), ("teacher", "Lehrkraft"))
        for index, (key, title) in enumerate(fields, start=1):
            column = (index - 1) % 2
            row = 1 + ((index - 1) // 2) * 2
            layout.addWidget(make_label(title.upper(), "FieldLabel"), row, column)
            field = QLineEdit(DOCUMENT_HEADER[key])
            field.setAccessibleName(title)
            self.header_fields[key] = field
            layout.addWidget(field, row + 1, column)
        group_layout = QHBoxLayout()
        group_layout.setContentsMargins(12, 9, 12, 9)
        group_layout.addWidget(make_label("STAMMGRUPPE", "FieldLabel", False))
        group_layout.addWidget(make_label(DOCUMENT_HEADER["group"], "CardTitle", False))
        group_layout.addStretch()
        layout.addWidget(card(group_layout, "HeaderSummary"), 5, 0, 1, 2)
        return card(layout)

    def _focus_card(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(make_label("Gesprächsschwerpunkte", "SectionTitle"))
        layout.addWidget(make_label("Die Auswahl bestimmt, welche Bereiche rechts zur Sprache kommen.", "Hint"))
        layout.addWidget(make_label("FACHLICHE BEREICHE", "FieldLabel"))
        layout.addLayout(self._area_grid(SUBJECT_AREAS, self.subject_checks, "SubjectArea"))
        layout.addSpacing(7)
        layout.addWidget(make_label("ÜBERGREIFENDE GESPRÄCHSTHEMEN", "FieldLabel"))
        layout.addLayout(self._area_grid(CROSS_CUTTING_AREAS, self.cross_area_checks, "CrossArea"))
        return card(layout)

    def _area_grid(self, areas: tuple[tuple[str, bool], ...], target: list, prefix: str) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(6)
        for index, (name, selected) in enumerate(areas):
            checkbox = QCheckBox(name)
            checkbox.setObjectName(f"{prefix}_{index}")
            checkbox.setChecked(selected)
            target.append((name, checkbox))
            grid.addWidget(checkbox, index // 2, index % 2)
        return grid

    def _competencies_card(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(9)
        layout.addWidget(make_label("Kompetenzen als Gesprächsbelege", "SectionTitle"))
        layout.addWidget(make_label("Hier erscheinen nur die oben gewählten Fächer. Konkrete Kompetenzen werden erst im geöffneten Thema sichtbar.", "Hint"))
        self.competency_filter_empty = make_label(
            "Bitte zuerst mindestens einen fachlichen Bereich auswählen.", "EmptyState"
        )
        layout.addWidget(self.competency_filter_empty)

        grouped: dict[str, dict[str, dict[str, list[CompetencyDemo]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        for competency in COMPETENCIES:
            grouped[competency.subject][competency.learning_area][competency.topic].append(competency)

        for subject, learning_areas in grouped.items():
            area_box = QWidget()
            area_layout = QVBoxLayout(area_box)
            area_layout.setContentsMargins(12, 0, 0, 0)
            area_layout.setSpacing(3)
            for learning_area, topics in learning_areas.items():
                topic_box = QWidget()
                topic_layout = QVBoxLayout(topic_box)
                topic_layout.setContentsMargins(12, 0, 0, 0)
                topic_layout.setSpacing(3)
                for topic, competencies in topics.items():
                    competency_box = QWidget()
                    competency_layout = QVBoxLayout(competency_box)
                    competency_layout.setContentsMargins(12, 2, 0, 5)
                    competency_layout.setSpacing(7)
                    for data in competencies:
                        competency_layout.addWidget(self._competency_option(data))
                    topic_section = CollapsibleSection(
                        topic,
                        competency_box,
                        expanded=subject == "Mathematik" and topic == "Zeit",
                        indent=0,
                    )
                    self.hierarchy_sections.append(topic_section)
                    topic_layout.addWidget(topic_section)
                area_section = CollapsibleSection(
                    learning_area,
                    topic_box,
                    expanded=subject == "Mathematik",
                    indent=0,
                )
                self.hierarchy_sections.append(area_section)
                area_layout.addWidget(area_section)
            subject_section = CollapsibleSection(subject, area_box, expanded=subject == "Mathematik")
            self.hierarchy_sections.append(subject_section)
            self.competency_subject_sections[subject] = subject_section
            layout.addWidget(subject_section)
        return card(layout)

    def _competency_option(self, data: CompetencyDemo) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 9, 12, 10)
        layout.setSpacing(5)
        checkbox = QCheckBox(data.short_label)
        checkbox.setChecked(data.selected)
        checkbox.setObjectName(f"CompetencyOption_{len(self.competency_checks)}")
        self.competency_checks.append((data, checkbox))
        layout.addWidget(checkbox)
        layout.addWidget(make_label(data.text, "Hint"))
        meta = QGridLayout()
        meta.setHorizontalSpacing(10)
        meta.addWidget(make_label("BESTÄTIGTER STAND", "FieldLabel"), 0, 0)
        meta.addWidget(make_label(data.confirmed_state, "Hint"), 0, 1)
        meta.addWidget(make_label("LETZTE BEOBACHTUNG", "FieldLabel"), 1, 0)
        meta.addWidget(make_label(data.last_observation, "Hint"), 1, 1)
        layout.addLayout(meta)
        return card(layout, "SoftBlock")

    def _observations_card(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(9)
        layout.addWidget(make_label("Beobachtungsbelege", "SectionTitle"))
        layout.addWidget(make_label("Hier erscheinen nur Belege zu den oben gewählten Fächern und Gesprächsthemen. Richtwert: drei bis fünf Beispiele.", "Hint"))
        self.evidence_warning = make_label("", "Warning")
        self.evidence_warning.setObjectName("EvidenceLimitWarning")
        layout.addWidget(self.evidence_warning)
        self.observation_filter_empty = make_label(
            "Für die gewählten Bereiche sind keine Beobachtungsbelege sichtbar.", "EmptyState"
        )
        layout.addWidget(self.observation_filter_empty)
        for data in OBSERVATIONS:
            item = QVBoxLayout()
            item.setContentsMargins(12, 9, 12, 10)
            item.setSpacing(4)
            heading = QHBoxLayout()
            heading.addWidget(pill(data.area, AREA_COLORS[data.area]))
            heading.addWidget(make_label(f"{data.date} · {data.context}", "Hint"), 1)
            item.addLayout(heading)
            item.addWidget(make_label(data.note))
            checkbox = QCheckBox("Für das Gespräch auswählen")
            checkbox.setChecked(data.selected)
            checkbox.setObjectName(f"ObservationEvidence_{len(self.observation_checks)}")
            self.observation_checks.append((data, checkbox))
            item.addWidget(checkbox)
            observation_widget = card(item, "SoftBlock")
            self.observation_widgets.append((data, observation_widget))
            layout.addWidget(observation_widget)
        return card(layout)

    def _guide_card(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(8)
        layout.addWidget(make_label("Gesprächsleitfaden", "SectionTitle"))
        layout.addWidget(make_label("Manuelle Vorbereitung · keine Textvorschläge werden erzeugt oder gespeichert.", "Hint"))
        fields = (
            ("strengths", "Was gelingt dem Kind besonders?"),
            ("development", "Welche Entwicklung sehen wir?"),
            ("shared_work", "Woran möchten wir gemeinsam arbeiten?"),
            ("support", "Welche Unterstützung vereinbaren wir?"),
        )
        self.guide_edits: dict[str, QTextEdit] = {}
        for key, title in fields:
            layout.addWidget(make_label(title.upper(), "FieldLabel"))
            edit = QTextEdit(GUIDE[key])
            edit.setMinimumHeight(92)
            edit.setAccessibleName(title)
            edit.setObjectName(f"Guide_{key}")
            self.guide_edits[key] = edit
            layout.addWidget(edit)
        return card(layout)

    def _charts_card(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(9)
        layout.addWidget(make_label("Optionale Gesprächsbilder", "SectionTitle"))
        layout.addWidget(make_label("Nur drei neutrale Darstellungen; ohne Durchschnitt, Score, Note oder Trendlinie.", "Hint"))
        for data in CHARTS:
            checkbox = QCheckBox(data.title)
            checkbox.setChecked(data.selected)
            checkbox.setObjectName(f"ChartOption_{len(self.chart_checks)}")
            layout.addWidget(checkbox)
            layout.addWidget(make_label(data.description, "Hint"))
            self.chart_checks.append((data, checkbox))
        return card(layout)

    def _conversation_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("ConversationPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.conversation_content = QWidget()
        self.conversation_layout = QVBoxLayout(self.conversation_content)
        self.conversation_layout.setContentsMargins(44, 34, 44, 70)
        self.conversation_layout.setSpacing(8)
        scroll.setWidget(self.conversation_content)
        panel_layout.addWidget(scroll)
        return panel

    def _connect_live_updates(self) -> None:
        def schedule(*_args: object) -> None:
            self._preview_timer.start()

        for field in self.header_fields.values():
            field.textChanged.connect(schedule)
        for _, checkbox in (*self.subject_checks, *self.cross_area_checks):
            checkbox.toggled.connect(self._update_preparation_filters)
            checkbox.toggled.connect(schedule)
        for _, checkbox in (*self.competency_checks, *self.chart_checks):
            checkbox.toggled.connect(schedule)
        for _, checkbox in self.observation_checks:
            checkbox.toggled.connect(self._update_evidence_warning)
            checkbox.toggled.connect(schedule)
        for edit in self.guide_edits.values():
            edit.textChanged.connect(schedule)

    def _update_preparation_filters(self, *_args: object) -> None:
        selected_subjects = set(self._selected_subjects())
        selected_areas = set(self._selected_areas())
        for subject, section in self.competency_subject_sections.items():
            section.setVisible(subject in selected_subjects)
        self.competency_filter_empty.setVisible(not selected_subjects)

        visible_observation_count = 0
        for data, widget in self.observation_widgets:
            visible = data.area in selected_areas
            widget.setVisible(visible)
            visible_observation_count += int(visible)
        self.observation_filter_empty.setVisible(visible_observation_count == 0)
        self._update_evidence_warning()

    def _update_evidence_warning(self, *_args: object) -> None:
        count = len(self._selected_observations())
        self.evidence_warning.setText(
            f"{count} Belege ausgewählt. Für ein ruhiges Gespräch empfehlen sich drei bis fünf. Die Auswahl bleibt unverändert."
            if count > 5 else ""
        )
        self.evidence_warning.setVisible(count > 5)

    def _field(self, key: str) -> str:
        return self.header_fields[key].text().strip() or "—"

    def _selected_subjects(self) -> list[str]:
        return [name for name, checkbox in self.subject_checks if checkbox.isChecked()]

    def _selected_cross_areas(self) -> list[str]:
        return [name for name, checkbox in self.cross_area_checks if checkbox.isChecked()]

    def _selected_areas(self) -> list[str]:
        return [*self._selected_subjects(), *self._selected_cross_areas()]

    def _selected_competencies(self) -> list[CompetencyDemo]:
        subjects = set(self._selected_subjects())
        return [data for data, checkbox in self.competency_checks if checkbox.isChecked() and data.subject in subjects]

    def _selected_observations(self, all_areas: bool = False) -> list[ObservationDemo]:
        areas = set(self._selected_areas())
        return [
            data for data, checkbox in self.observation_checks
            if checkbox.isChecked() and (all_areas or data.area in areas)
        ]

    def _selected_charts(self) -> list[str]:
        return [data.title for data, checkbox in self.chart_checks if checkbox.isChecked()]

    def rebuild_conversation(self) -> None:
        clear_layout(self.conversation_layout)
        subjects = self._selected_subjects()
        cross_areas = self._selected_cross_areas()
        areas = [*subjects, *cross_areas]
        competencies = self._selected_competencies()
        observations = self._selected_observations()

        self.conversation_layout.addWidget(make_label("GESPRÄCHSMAPPE", "PanelEyebrow"))
        hero = QVBoxLayout()
        hero.setContentsMargins(28, 24, 28, 26)
        hero.setSpacing(5)
        hero.addWidget(make_label("LERNENTWICKLUNGSGESPRÄCH", "HeroEyebrow"))
        hero.addWidget(make_label(f"Gespräch mit {self._field('student')}", "HeroTitle"))
        hero.addWidget(make_label(f"{DOCUMENT_HEADER['group']} · {self._field('period')} · {self._field('date')} · {self._field('teacher')}", "HeroMeta"))
        self.conversation_layout.addWidget(card(hero, "ConversationHero"))

        self.conversation_layout.addWidget(self._conversation_goal(areas))
        self.conversation_layout.addWidget(self._guide_section(2, "Was gelingt dem Kind?", "strengths"))
        self.conversation_layout.addWidget(self._guide_section(3, "Welche Entwicklung sehen wir?", "development"))
        self.conversation_layout.addWidget(self._guide_section(4, "Woran möchten wir gemeinsam arbeiten?", "shared_work"))
        self.conversation_layout.addWidget(self._evidence_section(competencies, observations, areas))
        self.conversation_layout.addWidget(self._agreements_section())
        self.conversation_layout.addStretch()

    def _section(self, number: int, title: str, contents: Iterable[QWidget]) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 25, 4, 28)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        heading.addWidget(make_label(f"{number:02d}", "SectionNumber", False))
        heading.addWidget(make_label(title, "SectionTitle"), 1)
        layout.addLayout(heading)
        for widget in contents:
            layout.addWidget(widget)
        return card(layout, "ConversationSection")

    def _conversation_goal(self, areas: list[str]) -> QFrame:
        if areas:
            items = QWidget()
            row = QHBoxLayout(items)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(7)
            for name in areas:
                row.addWidget(pill(name, AREA_COLORS[name]))
            row.addStretch()
            text = f"Heute schauen wir gemeinsam auf ausgewählte Lern- und Gesprächsbereiche von {self._field('student')}."
            return self._section(1, "Gesprächsziel", [make_label(text), items])
        return self._section(1, "Gesprächsziel", [make_label("Noch keine Gesprächsbereiche ausgewählt.", "EmptyState")])

    def _guide_section(self, number: int, title: str, key: str) -> QFrame:
        text = self.guide_edits[key].toPlainText().strip() or "Noch nicht formuliert."
        return self._section(number, title, [make_label(text)])

    def _evidence_section(
        self,
        competencies: list[CompetencyDemo],
        observations: list[ObservationDemo],
        areas: list[str],
    ) -> QFrame:
        widgets: list[QWidget] = []
        if competencies:
            widgets.append(make_label("AUSGEWÄHLTE KOMPETENZEN", "FieldLabel"))
            for data in competencies:
                row = QHBoxLayout()
                row.setContentsMargins(12, 8, 12, 8)
                row.addWidget(pill(data.subject, AREA_COLORS[data.subject]))
                row.addWidget(make_label(f"{data.topic} · {data.short_label}"), 1)
                widgets.append(card(row, "SoftBlock"))
        if observations:
            widgets.append(make_label("AUSGEWÄHLTE BEOBACHTUNGSBELEGE", "FieldLabel"))
            for data in observations:
                block = QVBoxLayout()
                block.setContentsMargins(12, 9, 12, 10)
                block.setSpacing(4)
                block.addWidget(make_label(f"{data.date} · {data.context}", "CardTitle"))
                block.addWidget(make_label(data.note))
                widgets.append(card(block, "SoftBlock"))
        if not competencies and not observations:
            widgets.append(make_label("Noch keine gesprächsgeeigneten Beispiele ausgewählt.", "EmptyState"))
        selected_charts = self._selected_charts()
        if selected_charts:
            widgets.append(make_label("OPTIONALE GESPRÄCHSBILDER", "FieldLabel"))
            for title in selected_charts:
                if title == "Dokumentationsabdeckung":
                    widgets.append(self._coverage_chart(areas))
                elif title == "Kompetenzentwicklung":
                    widgets.append(self._competency_chart(competencies))
                elif title == "Zeitachse ausgewählter Beobachtungsbelege":
                    widgets.append(self._timeline_chart(observations))
        return self._section(5, "Welche Beispiele stützen unsere Einschätzung?", widgets)

    def _chart_shell(self, title: str, note: str, body: QLayout) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 13, 15, 15)
        layout.setSpacing(8)
        layout.addWidget(make_label(title, "CardTitle"))
        layout.addWidget(make_label(note, "Hint"))
        layout.addLayout(body)
        return card(layout, "ChartCard")

    def _coverage_chart(self, areas: list[str]) -> QFrame:
        body = QVBoxLayout()
        body.setSpacing(7)
        if not areas:
            body.addWidget(make_label("Noch kein Gesprächsbereich ausgewählt.", "EmptyState"))
        for area in areas:
            row = QHBoxLayout()
            row.addWidget(make_label(area, "Hint"), 1)
            for covered in COVERAGE_DEMO[area]:
                dot = QLabel("●" if covered else "○")
                dot.setStyleSheet(f"color: {AREA_COLORS[area] if covered else '#B7C4C8'}; font-size: 18px;")
                dot.setFixedWidth(17)
                row.addWidget(dot)
            body.addLayout(row)
        body.addWidget(make_label("● Beleg vorhanden    ○ derzeit kein ausgewählter Beleg", "Hint"))
        return self._chart_shell("Dokumentationsabdeckung", "Die Abdeckung beschreibt Dokumentation, nicht Leistung.", body)

    def _competency_chart(self, competencies: list[CompetencyDemo]) -> QFrame:
        body = QVBoxLayout()
        body.setSpacing(9)
        shown = [item for item in competencies if item.short_label in COMPETENCY_MOMENTS][:4]
        if not shown:
            body.addWidget(make_label("Für die ausgewählten Kompetenzen sind keine Demo-Einzelstände vorbereitet.", "EmptyState"))
        for item in shown:
            body.addWidget(make_label(item.short_label, "Hint"))
            moments = COMPETENCY_MOMENTS[item.short_label]
            row = QHBoxLayout()
            for date, state in moments:
                block = QVBoxLayout()
                block.setContentsMargins(9, 7, 9, 7)
                block.addWidget(make_label(date, "FieldLabel"))
                block.addWidget(make_label(state, "Hint"))
                row.addWidget(card(block, "HeaderSummary"), 1)
            if len(moments) == 1:
                row.addStretch(2)
            body.addLayout(row)
        return self._chart_shell("Kompetenzentwicklung", "Datierte Einzelstände ohne Verbindungslinie, Richtung oder automatische Deutung.", body)

    def _timeline_chart(self, observations: list[ObservationDemo]) -> QFrame:
        body = QVBoxLayout()
        body.setSpacing(7)
        if not observations:
            body.addWidget(make_label("Noch kein Beobachtungsbeleg für die Zeitachse ausgewählt.", "EmptyState"))
        for data in sorted(observations, key=lambda item: item.date):
            row = QHBoxLayout()
            row.addWidget(make_label(data.date[:5], "FieldLabel", False))
            row.addWidget(pill(data.area, AREA_COLORS[data.area]))
            row.addWidget(make_label(data.context, "Hint"), 1)
            body.addLayout(row)
        return self._chart_shell("Zeitachse ausgewählter Beobachtungsbelege", "Ordnet die bewusst gewählten Beispiele ein, ohne sie zu gewichten.", body)

    def _agreements_section(self) -> QFrame:
        prepared = QVBoxLayout()
        prepared.setContentsMargins(14, 12, 14, 14)
        prepared.addWidget(make_label("VORBEREITUNG DER LEHRKRAFT", "FieldLabel"))
        prepared.addWidget(make_label(self.guide_edits["support"].toPlainText().strip() or "Noch nicht formuliert."))
        shared = QVBoxLayout()
        shared.setContentsMargins(14, 12, 14, 14)
        shared.addWidget(make_label("IM GESPRÄCH VEREINBART", "FieldLabel"))
        shared.addWidget(make_label("Wird erst im Gespräch gemeinsam festgehalten.", "Hint"))
        return self._section(6, "Welche Unterstützung und Vereinbarungen treffen wir?", [card(prepared, "PreparedAgreement"), card(shared, "SharedAgreement")])


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LEG UX-Prototyp")
    app.setStyleSheet(APP_STYLE)
    window = LearningConferencePrototype()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
