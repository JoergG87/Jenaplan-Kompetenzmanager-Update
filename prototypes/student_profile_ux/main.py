"""Isolated PySide6 UX prototype for two student-profile directions.

The module intentionally imports no productive application code and uses only
the fictional in-memory data from ``demo_data.py``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from demo_data import (
    BASE,
    SCENARIOS,
    SCENARIO_BY_KEY,
    ObservationDemo,
    ProfileScenario,
    RecognizableDevelopmentDemo,
    recognizable_developments,
)


NAVY = "#17384E"
BLUE = "#2F7096"
TURQUOISE = "#2E8F8A"
INK = "#243942"
MUTED = "#617780"
LINE = "#D8E4E7"
SOFT = "#F3F7F7"
BACKGROUND = "#EAF1F2"

APP_STYLE = f"""
QMainWindow, QWidget#PrototypeRoot {{ background: {BACKGROUND}; color: {INK}; }}
QFrame#PrototypeBar {{ background: {NAVY}; border: none; }}
QLabel#PrototypeEyebrow {{ color: #A8D8D5; font-size: 10px; font-weight: 700; letter-spacing: 1px; }}
QLabel#PrototypeTitle {{ color: white; font-size: 17px; font-weight: 650; }}
QLabel#PrototypeMeta {{ color: #D7E8EA; font-size: 11px; }}
QFrame#ProfileHeader {{ background: white; border: 1px solid {LINE}; border-radius: 18px; }}
QFrame#Card {{ background: white; border: 1px solid {LINE}; border-radius: 14px; }}
QFrame#OrientationCard {{ background: white; border: 1px solid {LINE}; border-radius: 14px; }}
QFrame#SoftCard {{ background: {SOFT}; border: 1px solid #E1E9EA; border-radius: 12px; }}
QFrame#AccentCard {{ background: #EAF4F5; border: 1px solid #CEE1E3; border-radius: 14px; }}
QFrame#Rail {{ background: #F7FAFA; border: 1px solid {LINE}; border-radius: 15px; }}
QFrame#FilterBar {{ background: #F7FAFA; border: 1px solid {LINE}; border-radius: 12px; }}
QFrame#Notice {{ background: #F1F7F6; border: 1px solid #D5E6E3; border-radius: 10px; }}
QFrame#WarningNotice {{ background: #FFF7EA; border: 1px solid #EDDDBE; border-radius: 10px; }}
QFrame#ObservationRow, QFrame#DocumentRow, QFrame#HistoryRow {{ background: #FAFCFC; border: 1px solid #E1E9EB; border-radius: 11px; }}
QWidget#DevelopmentChart {{ background: transparent; }}
QFrame#OrientationSummary {{ background: #F1F6F7; border: 1px solid #D7E4E7; border-radius: 11px; }}
QFrame#OrientationEntry {{ background: #FAFCFC; border: 1px solid #DFE8EA; border-radius: 11px; }}
QFrame#EvidenceStrip {{ background: #F2F7F7; border: none; border-radius: 8px; }}
QFrame#OrientationDivider {{ background: {LINE}; border: none; min-width: 1px; max-width: 1px; }}
QWidget#DocumentationRing {{ background: transparent; }}
QLabel#Avatar {{ color: white; background: {BLUE}; border-radius: 25px; font-size: 17px; font-weight: 700; }}
QLabel#ProfileName {{ color: {NAVY}; font-size: 25px; font-weight: 700; }}
QLabel#ProfileMeta {{ color: {MUTED}; font-size: 12px; }}
QLabel#PageTitle {{ color: {NAVY}; font-size: 21px; font-weight: 700; }}
QLabel#SectionTitle {{ color: {NAVY}; font-size: 15px; font-weight: 700; }}
QLabel#CardTitle {{ color: {NAVY}; font-size: 13px; font-weight: 700; }}
QLabel#Metric {{ color: {NAVY}; font-size: 27px; font-weight: 700; }}
QLabel#OrientationMetric {{ color: {NAVY}; font-size: 22px; font-weight: 700; }}
QLabel#ChangeStatus {{ color: {NAVY}; font-size: 12px; font-weight: 700; }}
QLabel#Body {{ color: {INK}; font-size: 12px; }}
QLabel#Muted {{ color: {MUTED}; font-size: 11px; }}
QLabel#Eyebrow {{ color: {BLUE}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px; }}
QLabel#Badge {{ color: #365966; background: #E9F1F3; border: 1px solid #D4E2E5; border-radius: 9px; padding: 3px 8px; font-size: 10px; font-weight: 650; }}
QLabel#StatusBadge {{ color: #315B59; background: #E8F4F1; border: 1px solid #CFE4DF; border-radius: 9px; padding: 3px 8px; font-size: 10px; font-weight: 650; }}
QLabel#WarningBadge {{ color: #73531F; background: #FFF4DD; border: 1px solid #ECD9AF; border-radius: 9px; padding: 3px 8px; font-size: 10px; font-weight: 650; }}
QPushButton {{ background: white; color: {NAVY}; border: 1px solid #BDD0D6; border-radius: 9px; padding: 8px 13px; min-height: 18px; font-weight: 600; }}
QPushButton:hover {{ background: #EEF5F6; border-color: #98B6C0; }}
QPushButton:focus {{ border: 2px solid {BLUE}; padding: 7px 12px; }}
QPushButton[buttonRole="primary"] {{ background: {BLUE}; color: white; border-color: {BLUE}; padding: 9px 15px; }}
QPushButton[buttonRole="primary"]:hover {{ background: #285F7E; }}
QPushButton[buttonRole="quiet"] {{ background: transparent; border-color: transparent; color: #426271; }}
QPushButton[nav="true"] {{ text-align: left; background: transparent; border-color: transparent; color: #506A74; padding: 10px 12px; }}
QPushButton[nav="true"]:checked {{ color: {NAVY}; background: #E6F0F2; border-left: 3px solid {BLUE}; padding-left: 9px; }}
QPushButton[segment="true"] {{ background: transparent; border-color: transparent; color: #536D77; padding: 8px 14px; }}
QPushButton[segment="true"]:checked {{ background: white; color: {NAVY}; border: 1px solid #CBDADD; }}
QPushButton[chip="true"] {{ min-height: 16px; padding: 6px 10px; border-radius: 13px; background: #F4F8F8; }}
QPushButton[chip="true"]:checked {{ color: white; background: {BLUE}; border-color: {BLUE}; }}
QLineEdit, QComboBox {{ background: white; color: {INK}; border: 1px solid #C3D4D9; border-radius: 8px; padding: 8px 10px; min-height: 18px; }}
QLineEdit:focus, QComboBox:focus {{ border: 2px solid {BLUE}; padding: 7px 9px; }}
QCheckBox {{ color: #D7E8EA; spacing: 7px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QFrame#PrototypeBar QPushButton[segment="true"] {{ color: #D7E8EA; }}
QFrame#PrototypeBar QPushButton[segment="true"]:checked {{ color: {NAVY}; background: white; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #B8C9CE; border-radius: 4px; min-height: 34px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


SECTIONS = (
    ("overview", "Überblick"),
    ("competencies", "Kompetenzen"),
    ("observations", "Beobachtungen"),
    ("documents", "Dokumente"),
    ("history", "Verlauf"),
)

VARIANT_B_SCENARIOS = (
    ("well_documented", "Gut dokumentiertes Kind"),
    ("little_documentation", "Wenig dokumentiertes Kind"),
    ("report_draft", "Berichtsentwurf vorhanden"),
    ("finalized_revisions", "Finalisierte Revisionen vorhanden"),
    ("leg_available", "LEG vorhanden"),
    ("no_observations", "Keine Beobachtungen"),
    ("historical_reference", "Historische Kompetenzreferenz"),
)


def clear_layout(layout: QVBoxLayout | QHBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child_layout = item.layout()
        if widget is not None:
            widget.deleteLater()
        elif child_layout is not None:
            clear_layout(child_layout)  # type: ignore[arg-type]


def text_label(text: str, role: str = "Body", *, wrap: bool = True) -> QLabel:
    label = QLabel(text)
    label.setObjectName(role)
    label.setWordWrap(wrap)
    return label


def make_card(role: str = "Card") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName(role)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(15, 13, 15, 13)
    layout.setSpacing(7)
    return frame, layout


def make_button(
    label: str,
    role: str = "secondary",
    accessible_name: str | None = None,
) -> QPushButton:
    button = QPushButton(label)
    button.setProperty("buttonRole", role)
    button.setAccessibleName(accessible_name or label)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def badge(text: str, *, warning: bool = False, positive: bool = False) -> QLabel:
    role = "WarningBadge" if warning else "StatusBadge" if positive else "Badge"
    label = text_label(text, role, wrap=False)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class DevelopmentChart(QWidget):
    """Static categorical timeline for one selected concrete competency."""

    LEVELS = (
        "Unterstützung",
        "in Entwicklung",
        "erreicht",
        "sicher erreicht",
    )

    def __init__(self, points: tuple[tuple[str, int], ...]) -> None:
        super().__init__()
        self.points = points
        self.setObjectName("DevelopmentChart")
        self.setMinimumHeight(168)
        self.setAccessibleName(
            "Datierter Beobachtungsverlauf der Kompetenz Uhrzeiten ablesen und darstellen"
        )

    def paintEvent(self, _event: object) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart = QRectF(104, 12, max(80, self.width() - 120), max(80, self.height() - 42))
        grid_pen = QPen(QColor("#DCE6E8"), 1)
        label_color = QColor(MUTED)
        painter.setPen(grid_pen)
        for level in range(4):
            y = chart.bottom() - (chart.height() * level / 3)
            painter.drawLine(QPointF(chart.left(), y), QPointF(chart.right(), y))
            painter.setPen(label_color)
            painter.drawText(QRectF(0, y - 9, 98, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.LEVELS[level])
            painter.setPen(grid_pen)
        if not self.points:
            painter.setPen(label_color)
            painter.drawText(chart, Qt.AlignmentFlag.AlignCenter, "Noch keine datierten Kompetenzbeobachtungen")
            return
        step = chart.width() / max(1, len(self.points) - 1)
        mapped: list[QPointF] = []
        for index, (date_label, level) in enumerate(self.points):
            x = chart.left() + (step * index if len(self.points) > 1 else chart.width() / 2)
            y = chart.bottom() - (chart.height() * max(0, min(3, level)) / 3)
            mapped.append(QPointF(x, y))
            painter.setPen(label_color)
            painter.drawText(QRectF(x - 34, chart.bottom() + 7, 68, 18), Qt.AlignmentFlag.AlignHCenter, date_label)
        if len(mapped) > 1:
            painter.setPen(QPen(QColor(TURQUOISE), 2))
            for left, right in zip(mapped, mapped[1:]):
                painter.drawLine(left, right)
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.setBrush(QColor(TURQUOISE))
        for point in mapped:
            painter.drawEllipse(point, 5.5, 5.5)


class DocumentationRing(QWidget):
    """Compact coverage indicator; the arc is documentation, never attainment."""

    def __init__(self, documented: int, total: int, *, diameter: int = 58) -> None:
        super().__init__()
        self.documented = max(0, documented)
        self.total = max(0, total)
        self.setFixedSize(diameter, diameter)
        self.setObjectName("DocumentationRing")
        self.setAccessibleName(f"Dokumentiert: {self.documented} von {self.total} Lernbereichen")

    def paintEvent(self, _event: object) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inset = 5.0
        ring = QRectF(inset, inset, self.width() - inset * 2, self.height() - inset * 2)
        painter.setPen(QPen(QColor("#DFE8EA"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(ring, 0, 360 * 16)
        if self.total:
            span = int(360 * 16 * min(1.0, self.documented / self.total))
            painter.setPen(QPen(QColor(TURQUOISE), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(ring, 90 * 16, -span)
        painter.setPen(QColor(NAVY))
        painter.drawText(ring, Qt.AlignmentFlag.AlignCenter, f"{self.documented}/{self.total}")


class StudentProfilePrototype(QMainWindow):
    """Two switchable, static UX directions with shared content states."""

    def __init__(
        self,
        *,
        variant: str = "a",
        scenario_key: str = BASE.key,
        competency_card_variant: str = "ring",
        width: int = 1400,
        height: int = 900,
    ) -> None:
        super().__init__()
        self.variant = variant
        self.scenario = SCENARIO_BY_KEY.get(scenario_key, BASE)
        self.section_key = "overview"
        self.competency_card_variant = competency_card_variant
        self._compact_layout = width < 1250
        self.setWindowTitle("Schülerprofil · isolierter UX-Prototyp")
        self.setMinimumSize(1100, 720)
        self.resize(width, height)
        self._build()
        self._rebuild_workspace()

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("PrototypeRoot")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._prototype_bar())
        self.workspace = QWidget()
        self.workspace_layout = QVBoxLayout(self.workspace)
        self.workspace_layout.setContentsMargins(18, 16, 18, 14)
        self.workspace_layout.setSpacing(12)
        outer.addWidget(self.workspace, 1)
        self.setCentralWidget(root)

    def _prototype_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("PrototypeBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(10)
        title_block = QWidget()
        title_layout = QVBoxLayout(title_block)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(1)
        title_layout.addWidget(text_label("ISOLIERTER UX-PROTOTYP", "PrototypeEyebrow", wrap=False))
        title_layout.addWidget(text_label("Schülerprofil", "PrototypeTitle", wrap=False))
        layout.addWidget(title_block)
        layout.addStretch(1)

        self.variant_group = QButtonGroup(self)
        self.variant_group.setExclusive(True)
        for key, label in (("a", "Variante A · empfohlen"), ("b", "Variante B")):
            button = make_button(label, "quiet")
            button.setCheckable(True)
            button.setProperty("segment", True)
            button.setChecked(self.variant == key)
            button.clicked.connect(lambda _checked=False, selected=key: self.set_variant(selected))
            self.variant_group.addButton(button)
            layout.addWidget(button)

        self.scenario_combo = QComboBox()
        self.scenario_combo.setAccessibleName("Demozustand auswählen")
        self.scenario_combo.setMinimumWidth(245)
        self._populate_scenario_combo()
        self.scenario_combo.currentIndexChanged.connect(self._scenario_changed)
        layout.addWidget(self.scenario_combo)

        self.card_combo = QComboBox()
        self.card_combo.setAccessibleName("Darstellung der Kompetenzkarte auswählen")
        self.card_combo.addItem("Kompetenzkarte · Ring", "ring")
        self.card_combo.addItem("Kompetenzkarte · Leisten", "bars")
        self.card_combo.setCurrentIndex(max(0, self.card_combo.findData(self.competency_card_variant)))
        self.card_combo.currentIndexChanged.connect(self._card_variant_changed)
        self.card_combo.setVisible(self.variant == "a")
        layout.addWidget(self.card_combo)

        self.reduced_motion = QCheckBox("Reduced Motion")
        self.reduced_motion.setChecked(True)
        self.reduced_motion.setAccessibleName("Reduced Motion simulieren")
        self.reduced_motion.toggled.connect(self._motion_changed)
        layout.addWidget(self.reduced_motion)
        return bar

    def _populate_scenario_combo(self) -> None:
        self.scenario_combo.blockSignals(True)
        self.scenario_combo.clear()
        if self.variant == "a":
            for scenario in SCENARIOS:
                self.scenario_combo.addItem(scenario.label, scenario.key)
        else:
            for key, label in VARIANT_B_SCENARIOS:
                self.scenario_combo.addItem(label, key)
        self.scenario_combo.setCurrentIndex(
            max(0, self.scenario_combo.findData(self.scenario.key))
        )
        self.scenario_combo.blockSignals(False)

    def set_variant(self, variant: str) -> None:
        if variant not in {"a", "b"}:
            return
        self.variant = variant
        if variant == "b" and self.scenario.key not in {key for key, _label in VARIANT_B_SCENARIOS}:
            self.scenario = BASE
        self._populate_scenario_combo()
        self.card_combo.setVisible(variant == "a")
        self.section_key = "overview"
        self._rebuild_workspace()

    def _scenario_changed(self, _index: int) -> None:
        key = str(self.scenario_combo.currentData())
        self.scenario = SCENARIO_BY_KEY[key]
        self.section_key = "overview"
        self._rebuild_workspace()

    def _card_variant_changed(self, _index: int) -> None:
        self.competency_card_variant = str(self.card_combo.currentData())
        self._rebuild_workspace()

    def _motion_changed(self, checked: bool) -> None:
        if hasattr(self, "prototype_status"):
            self.prototype_status.setText(
                "Reduced Motion aktiv · alle Zustände wechseln unmittelbar."
                if checked
                else "Auch ohne Reduced Motion verwendet dieser Prototyp keine Layoutanimationen."
            )

    def resizeEvent(self, event: object) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)  # type: ignore[arg-type]
        compact = self.width() < 1250
        if compact != self._compact_layout and hasattr(self, "workspace_layout"):
            self._compact_layout = compact
            QTimer.singleShot(0, self._rebuild_workspace)

    def _rebuild_workspace(self) -> None:
        clear_layout(self.workspace_layout)
        self.workspace_layout.addWidget(self._profile_header())
        if self.variant == "a":
            self.workspace_layout.addWidget(self._horizontal_navigation())
            self.workspace_layout.addWidget(self._content_scroll(), 1)
        else:
            body = QHBoxLayout()
            body.setSpacing(14)
            body.addWidget(self._vertical_navigation(), 0)
            body.addWidget(self._content_scroll(), 1)
            self.workspace_layout.addLayout(body, 1)
        self.prototype_status = text_label(
            "Statische Beispieldaten · keine Speicherung · keine Produktnavigation",
            "PrototypeMeta",
            wrap=False,
        )
        self.prototype_status.setStyleSheet("color: #607780;")
        self.workspace_layout.addWidget(self.prototype_status)

    def _profile_header(self) -> QFrame:
        if self.variant == "b":
            return self._variant_b_profile_header()
        if self._compact_layout:
            return self._compact_variant_a_profile_header()
        frame, layout = make_card("ProfileHeader")
        layout.setContentsMargins(18, 12, 18, 13)
        top = QHBoxLayout()
        back = make_button("Zurück zur Schülerliste", "quiet")
        back.clicked.connect(lambda: self._feedback("Prototyp: Rückweg zur vorherigen Schülerauswahl."))
        top.addWidget(back)
        top.addStretch(1)
        top.addWidget(badge("UX-Vorlage", positive=True))
        layout.addLayout(top)

        row = QHBoxLayout()
        row.setSpacing(12)
        initials = "".join(part[:1] for part in self.scenario.student_name.split()[:2]).upper()
        avatar = text_label(initials, "Avatar", wrap=False)
        avatar.setFixedSize(50, 50)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setAccessibleName(f"Avatar von {self.scenario.student_name}")
        row.addWidget(avatar)
        name_block = QWidget()
        name_layout = QVBoxLayout(name_block)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(5)
        name_layout.addWidget(text_label(self.scenario.student_name, "ProfileName"))
        chips = QHBoxLayout()
        chips.setSpacing(5)
        chips.addWidget(badge(f"Stammgruppe {self.scenario.group_name}"))
        for course in self.scenario.courses:
            chips.addWidget(badge(course))
        chips.addStretch(1)
        name_layout.addLayout(chips)
        row.addWidget(name_block, 1)
        documentation = QWidget()
        documentation_layout = QHBoxLayout(documentation)
        documentation_layout.setContentsMargins(0, 0, 0, 0)
        documentation_layout.setSpacing(7)
        documentation_layout.addWidget(DocumentationRing(self.scenario.documented_areas, self.scenario.total_areas))
        documentation_text = QVBoxLayout()
        documentation_text.setSpacing(0)
        documentation_text.addWidget(text_label("Dokumentiert", "CardTitle", wrap=False))
        documentation_text.addWidget(text_label(f"{self.scenario.documented_areas} / {self.scenario.total_areas} Lernbereiche", "Muted", wrap=False))
        documentation_layout.addLayout(documentation_text)
        row.addWidget(documentation)
        observation = make_button(
            "Beobachtung erfassen",
            "primary",
            "Neue Beobachtung für dieses Kind erfassen",
        )
        observation.clicked.connect(lambda: self._feedback("Prototyp: zentralen Beobachtungsdialog öffnen."))
        row.addWidget(observation)
        more = make_button("Weitere Aktionen", "quiet")
        more.clicked.connect(lambda: self._feedback("Prototyp: Schüler bearbeiten oder Datei hinzufügen."))
        row.addWidget(more)
        layout.addLayout(row)
        return frame

    def _compact_variant_a_profile_header(self) -> QFrame:
        frame, layout = make_card("ProfileHeader")
        layout.setContentsMargins(14, 9, 14, 9)
        row = QHBoxLayout()
        row.setSpacing(10)
        back = make_button("Schülerliste", "quiet")
        back.clicked.connect(lambda: self._feedback(
            "Prototyp: Rückweg zur vorherigen Schülerauswahl."
        ))
        row.addWidget(back)
        initials = "".join(
            part[:1] for part in self.scenario.student_name.split()[:2]
        ).upper()
        avatar = text_label(initials, "Avatar", wrap=False)
        avatar.setFixedSize(50, 50)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setAccessibleName(f"Avatar von {self.scenario.student_name}")
        row.addWidget(avatar)
        identity = QVBoxLayout()
        identity.setSpacing(2)
        identity.addWidget(text_label(self.scenario.student_name, "ProfileName"))
        identity.addWidget(text_label(
            " · ".join((self.scenario.group_name, *self.scenario.courses)),
            "Muted",
            wrap=False,
        ))
        row.addLayout(identity, 1)
        row.addWidget(badge(
            f"Dokumentiert {self.scenario.documented_areas} / {self.scenario.total_areas}"
        ))
        observation = make_button(
            "Beobachtung erfassen",
            "primary",
            "Neue Beobachtung für dieses Kind erfassen",
        )
        observation.clicked.connect(lambda: self._feedback(
            "Prototyp: zentralen Beobachtungsdialog öffnen."
        ))
        row.addWidget(observation)
        more = make_button("Weitere Aktionen", "quiet")
        more.clicked.connect(lambda: self._feedback(
            "Prototyp: Schüler bearbeiten oder Datei hinzufügen."
        ))
        row.addWidget(more)
        layout.addLayout(row)
        return frame

    def _variant_b_profile_header(self) -> QFrame:
        """Keep the comparison variant's established compact header unchanged."""

        frame, layout = make_card("ProfileHeader")
        layout.setContentsMargins(18, 12, 18, 13)
        top = QHBoxLayout()
        back = make_button("Zurück zur Schülerliste", "quiet")
        back.clicked.connect(lambda: self._feedback(
            "Prototyp: Rückweg zur vorherigen Schülerauswahl."
        ))
        top.addWidget(back)
        top.addStretch(1)
        top.addWidget(badge("UX-Vorlage", positive=True))
        layout.addLayout(top)

        row = QHBoxLayout()
        name_block = QVBoxLayout()
        name_block.setSpacing(2)
        name_block.addWidget(text_label(self.scenario.student_name, "ProfileName"))
        name_block.addWidget(text_label(
            " · ".join((self.scenario.group_name, *self.scenario.courses)),
            "ProfileMeta",
        ))
        row.addLayout(name_block, 1)
        row.addWidget(badge(
            f"Dokumentation {self.scenario.documented_areas}/{self.scenario.total_areas} Lernbereiche"
        ))
        observation = make_button(
            "Beobachtung erfassen",
            "primary",
            "Neue Beobachtung für dieses Kind erfassen",
        )
        observation.clicked.connect(lambda: self._feedback(
            "Prototyp: zentralen Beobachtungsdialog öffnen."
        ))
        row.addWidget(observation)
        more = make_button("Weitere Aktionen", "quiet")
        more.clicked.connect(lambda: self._feedback(
            "Prototyp: Schüler bearbeiten oder Datei hinzufügen."
        ))
        row.addWidget(more)
        layout.addLayout(row)
        return frame

    def _horizontal_navigation(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("FilterBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(2)
        group = QButtonGroup(frame)
        group.setExclusive(True)
        for key, label in SECTIONS:
            if key == "history":
                label = "Entwicklung"
            button = make_button(label, "quiet")
            button.setProperty("segment", True)
            button.setCheckable(True)
            button.setChecked(self.section_key == key)
            button.clicked.connect(lambda _checked=False, selected=key: self._select_section(selected))
            group.addButton(button)
            layout.addWidget(button)
        layout.addStretch(1)
        return frame

    def _vertical_navigation(self) -> QFrame:
        rail, layout = make_card("Rail")
        rail.setFixedWidth(214)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.addWidget(text_label("PROFILBEREICHE", "Eyebrow", wrap=False))
        group = QButtonGroup(rail)
        group.setExclusive(True)
        for key, label in SECTIONS:
            button = make_button(label, "quiet")
            button.setProperty("nav", True)
            button.setCheckable(True)
            button.setChecked(self.section_key == key)
            button.clicked.connect(lambda _checked=False, selected=key: self._select_section(selected))
            group.addButton(button)
            layout.addWidget(button)
        layout.addStretch(1)
        layout.addWidget(text_label("Lokale Navigation\ninnerhalb des Kindes", "Muted"))
        return rail

    def _select_section(self, key: str) -> None:
        self.section_key = key
        self._rebuild_workspace()

    def _content_scroll(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("PrototypeRoot")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 4, 8, 12)
        layout.setSpacing(12)
        page = {
            "overview": self._overview_page,
            "competencies": self._competencies_page,
            "observations": self._observations_page,
            "documents": self._documents_page,
            "history": self._history_page,
        }[self.section_key]()
        layout.addWidget(page)
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _page_header(self, title: str, description: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(text_label(title, "PageTitle"))
        layout.addWidget(text_label(description, "Muted"))
        return widget

    def _overview_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        title = "Arbeitsprofil" if self.variant == "a" else "Fokusprofil"
        description = (
            "Wichtige Informationen zuerst, Details in den fachlichen Bereichen."
            if self.variant == "a"
            else "Ein dominanter Arbeitsbereich, ergänzt durch einen kompakten Dokumentkontext."
        )
        layout.addWidget(self._page_header(title, description))
        if self.variant == "a":
            if self._compact_layout:
                layout.addWidget(self._development_card())
                summary_row = QHBoxLayout()
                summary_row.setSpacing(16)
                summary_row.addWidget(self._competency_summary_card(), 1)
                summary_row.addWidget(self._undocumented_card(), 1)
                layout.addLayout(summary_row)
            else:
                row = QHBoxLayout()
                row.setSpacing(16)
                row.addWidget(self._development_card(), 6)
                row.addWidget(self._competency_summary_card(), 3)
                row.addWidget(self._undocumented_card(), 3)
                layout.addLayout(row)
            lower = QHBoxLayout()
            lower.setSpacing(16)
            lower.addWidget(self._recent_observations_card(limit=3), 7)
            lower.addWidget(self._document_summary_card(), 4)
            layout.addLayout(lower)
            layout.addWidget(self._context_card())
        else:
            row = QHBoxLayout()
            row.setSpacing(12)
            focus, focus_layout = make_card("Card")
            focus_layout.addWidget(text_label("ENTWICKLUNG UND BEOBACHTUNG", "Eyebrow", wrap=False))
            focus_layout.addWidget(text_label("Ausgewählte Kompetenz im Verlauf", "SectionTitle"))
            focus_layout.addWidget(self._compact_documentation_strip())
            focus_layout.addWidget(DevelopmentChart(self.scenario.development_points), 1)
            focus_layout.addWidget(text_label(
                "Konkrete Kompetenz: Uhrzeiten ablesen und darstellen · datierte Einzelbeobachtungen · kein Fachmittelwert",
                "Muted",
            ))
            row.addWidget(focus, 7)
            side = QVBoxLayout()
            side.setSpacing(12)
            side.addWidget(self._undocumented_card())
            side.addWidget(self._document_summary_card())
            row.addLayout(side, 4)
            layout.addLayout(row)
            layout.addWidget(self._recent_observations_card(limit=2))
            layout.addWidget(self._context_card())
        return page

    def _development_card(self) -> QFrame:
        card, layout = make_card("OrientationCard")
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.addWidget(text_label("Lernentwicklung", "SectionTitle"), 1)
        header.addWidget(text_label("Aktuell dokumentiert", "Muted", wrap=False))
        layout.addLayout(header)

        layout.addWidget(self._current_orientation_status())
        layout.addWidget(text_label("NEUESTE ENTWICKLUNG", "Eyebrow", wrap=False))
        changes = recognizable_developments(self.scenario)
        if changes:
            for change in changes:
                layout.addWidget(self._orientation_change_entry(change))
        else:
            layout.addWidget(self._empty_state(
                "Noch keine tatsächliche Statusänderung dokumentiert",
                "Sobald ein reales Ereignis einen neuen Kompetenzstand belegt, erscheint es hier.",
            ))
        return card

    def _current_orientation_status(self) -> QFrame:
        frame, layout = make_card("OrientationSummary")
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(5)
        layout.addWidget(text_label(
            "AKTUELLER DOKUMENTIERTER STAND",
            "Eyebrow",
            wrap=False,
        ))
        secure, developing, first = self.scenario.orientation_counts
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(self._orientation_stat(str(secure), "Kompetenzen sicher"), 1)
        row.addWidget(self._orientation_divider())
        row.addWidget(self._orientation_stat(
            str(developing),
            "Kompetenzen in Entwicklung",
        ), 1)
        row.addWidget(self._orientation_divider())
        row.addWidget(self._orientation_stat(str(first), "erste Beobachtungen"), 1)
        layout.addLayout(row)
        return frame

    @staticmethod
    def _orientation_stat(value: str, description: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        value_label = QLabel(value)
        value_label.setObjectName("OrientationMetric")
        value_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(value_label)
        layout.addWidget(text_label(description, "Body"), 1)
        return widget

    @staticmethod
    def _orientation_divider() -> QFrame:
        divider = QFrame()
        divider.setObjectName("OrientationDivider")
        divider.setFixedHeight(34)
        return divider

    def _orientation_change_entry(self, item: RecognizableDevelopmentDemo) -> QFrame:
        row, layout = make_card("OrientationEntry")
        layout.setContentsMargins(11, 8, 11, 8)
        layout.setSpacing(5)
        top = QHBoxLayout()
        name = QVBoxLayout()
        name.setSpacing(1)
        name.addWidget(text_label(
            item.competency.short_label or item.competency.competency,
            "CardTitle",
        ))
        name.addWidget(text_label(
            f"{item.competency.subject} · {item.competency.topic}",
            "Muted",
        ))
        top.addLayout(name, 1)
        previous, changed = next(
            (previous, changed)
            for previous, changed in reversed(tuple(zip(item.events, item.events[1:])))
            if previous.status != changed.status
        )
        status = QLabel(f"{previous.status} → {changed.status}")
        status.setObjectName("ChangeStatus")
        status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(status)
        top.addWidget(text_label(
            f"{item.first_date} – {item.last_date}",
            "Muted",
            wrap=False,
        ))
        layout.addLayout(top)

        evidence, evidence_layout = make_card("EvidenceStrip")
        evidence_layout.setContentsMargins(9, 5, 9, 5)
        evidence_layout.setSpacing(4)
        evidence_line = QHBoxLayout()
        evidence_line.setSpacing(7)
        evidence_line.addWidget(badge(changed.source))
        quote = text_label(
            f"Dokumentiertes Ereignis vom {changed.date}: {changed.status}",
            "Body",
        )
        quote.setMaximumHeight(32)
        evidence_line.addWidget(quote, 1)
        evidence_layout.addLayout(evidence_line)
        layout.addWidget(evidence)
        return row

    def _competency_summary_card(self) -> QFrame:
        card, layout = make_card("AccentCard")
        layout.addWidget(text_label("KOMPETENZEN", "Eyebrow", wrap=False))
        documented = max(0, self.scenario.documented_areas)
        confirmed = min(documented, max(0, documented // 2))
        observed = max(0, documented - confirmed)
        if self.competency_card_variant == "ring":
            visual = QHBoxLayout()
            visual.addWidget(DocumentationRing(documented, self.scenario.total_areas, diameter=72))
            labels = QVBoxLayout()
            labels.addWidget(text_label(f"{documented} / {self.scenario.total_areas}", "Metric", wrap=False))
            labels.addWidget(text_label("Lernbereiche dokumentiert", "Body"))
            visual.addLayout(labels, 1)
            layout.addLayout(visual)
            layout.addWidget(self._summary_line("Bestätigter Stand", str(confirmed)))
            layout.addWidget(self._summary_line("Beobachtet", str(observed)))
        else:
            layout.addWidget(text_label(f"{documented} / {self.scenario.total_areas}", "Metric", wrap=False))
            layout.addWidget(text_label("Lernbereiche dokumentiert", "Body"))
            layout.addWidget(self._coverage_bar("Bestätigter Stand", confirmed, self.scenario.total_areas, "#2E8F8A"))
            layout.addWidget(self._coverage_bar("Beobachtet", observed, self.scenario.total_areas, "#5A94B1"))
            layout.addWidget(self._coverage_bar("Insgesamt dokumentiert", documented, self.scenario.total_areas, "#765A9E"))
        layout.addWidget(text_label("Umfang und Herkunft der Dokumentation · keine Leistung oder Rangfolge.", "Muted"))
        open_button = make_button("Kompetenz-Cockpit öffnen", "secondary")
        open_button.clicked.connect(lambda: self._select_section("competencies"))
        layout.addWidget(open_button, 0, Qt.AlignmentFlag.AlignLeft)
        return card

    def _coverage_bar(self, label: str, value: int, total: int, color: str) -> QFrame:
        row, layout = make_card("SoftCard")
        layout.setContentsMargins(9, 7, 9, 7)
        header = QHBoxLayout()
        header.addWidget(text_label(label, "CardTitle", wrap=False), 1)
        header.addWidget(text_label(str(value), "Muted", wrap=False))
        layout.addLayout(header)
        track = QFrame()
        track.setFixedHeight(6)
        track.setStyleSheet("background: #DFE8EA; border: none; border-radius: 3px;")
        track_layout = QHBoxLayout(track)
        track_layout.setContentsMargins(0, 0, 0, 0)
        fill = QFrame()
        fill.setStyleSheet(f"background: {color}; border: none; border-radius: 3px;")
        track_layout.addWidget(fill, max(0, value))
        track_layout.addStretch(max(1, total - value))
        layout.addWidget(track)
        return row

    def _undocumented_card(self) -> QFrame:
        card, layout = make_card("WarningNotice")
        layout.addWidget(text_label("NOCH NICHT DOKUMENTIERT", "Eyebrow", wrap=False))
        open_count = max(0, self.scenario.total_areas - self.scenario.documented_areas)
        count_row = QHBoxLayout()
        count_row.addWidget(text_label(str(open_count), "Metric", wrap=False))
        count_row.addWidget(text_label("Lernbereiche ohne vorhandene Dokumentation", "Body"), 1)
        layout.addLayout(count_row)
        subject_counts = self.scenario.open_by_subject
        if self.variant == "b":
            subject_counts = tuple(
                ("EPU" if subject == "Sachunterricht" else subject, count)
                for subject, count in subject_counts
            )
        for subject, count in subject_counts:
            layout.addWidget(self._summary_line(subject, str(count)))
        open_button = make_button("Offene Bereiche ansehen", "quiet")
        open_button.clicked.connect(lambda: self._select_section("competencies"))
        layout.addWidget(open_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(text_label("Hinweis auf Dokumentationsumfang · keine Aussage über Leistung.", "Muted"))
        return card

    def _compact_documentation_strip(self) -> QFrame:
        strip, layout = make_card("AccentCard")
        row = QHBoxLayout()
        row.addWidget(text_label("Kompetenzdokumentation", "CardTitle"), 1)
        row.addWidget(badge(f"{self.scenario.documented_areas}/{self.scenario.total_areas} Lernbereiche"))
        layout.addLayout(row)
        layout.addWidget(text_label("Neutraler Umfangshinweis · keine Bewertung des Kindes", "Muted"))
        return strip

    def _recent_observations_card(self, *, limit: int) -> QFrame:
        card, layout = make_card("Card")
        header = QHBoxLayout()
        header.addWidget(text_label("Neueste Beobachtungen", "SectionTitle"))
        header.addStretch(1)
        all_button = make_button("Alle anzeigen", "quiet")
        all_button.clicked.connect(lambda: self._select_section("observations"))
        header.addWidget(all_button)
        layout.addLayout(header)
        if not self.scenario.observations:
            layout.addWidget(self._empty_state(
                "Noch keine Beobachtungen",
                "Gespeicherte Beobachtungen erscheinen hier chronologisch.",
                action_label="Beobachtung erfassen",
            ))
            return card
        for observation in self.scenario.observations[:limit]:
            layout.addWidget(self._observation_row(observation, compact=True))
        return card

    def _document_summary_card(self) -> QFrame:
        card, layout = make_card("Card")
        header = QHBoxLayout()
        header.addWidget(text_label("Dokumente", "SectionTitle"))
        header.addStretch(1)
        open_button = make_button("Öffnen", "quiet")
        open_button.clicked.connect(lambda: self._select_section("documents"))
        header.addWidget(open_button)
        layout.addLayout(header)
        layout.addWidget(self._document_line("Bericht", self.scenario.report_draft_status, "Öffnen"))
        if self.scenario.revisions:
            layout.addWidget(self._document_line(
                "Revisionen",
                f"{len(self.scenario.revisions)} · Revision {self.scenario.revisions[0].number} aktuell",
                "Ansehen",
            ))
        else:
            layout.addWidget(self._document_line("Revisionen", "Keine finale Revision", "Ansehen"))
        layout.addWidget(self._document_line("LEG", self.scenario.leg_status, "Öffnen"))
        layout.addWidget(self._document_line("Dateien", f"{self.scenario.file_count} hinterlegt", "Ansehen"))
        return card

    def _document_line(self, label: str, value: str, action: str) -> QFrame:
        row = QFrame()
        row.setObjectName("DocumentRow")
        line = QHBoxLayout(row)
        line.setContentsMargins(9, 4, 7, 4)
        line.setSpacing(6)
        line.addWidget(text_label(label, "CardTitle", wrap=False))
        line.addWidget(text_label(value, "Muted"), 1)
        button = make_button(action, "quiet", f"{label}: {action}")
        button.clicked.connect(lambda: self._select_section("documents"))
        line.addWidget(button)
        return row

    def _summary_line(self, label: str, value: str) -> QFrame:
        row, layout = make_card("SoftCard")
        layout.setContentsMargins(10, 8, 10, 8)
        line = QHBoxLayout()
        line.addWidget(text_label(label, "CardTitle", wrap=False))
        line.addStretch(1)
        line.addWidget(text_label(value, "Muted"), 2)
        layout.addLayout(line)
        return row

    def _context_card(self) -> QFrame:
        warning = bool(self.scenario.historical_reference or self.scenario.missing_reference)
        card, layout = make_card("WarningNotice" if warning else "Notice")
        layout.setContentsMargins(12, 10, 12, 10)
        title = "Historische Bezüge" if warning else "Dokumentationshinweis"
        layout.addWidget(text_label(title, "CardTitle"))
        layout.addWidget(text_label(self.scenario.context_hint, "Body"))
        if self.scenario.historical_reference:
            layout.addWidget(text_label(self.scenario.historical_reference, "Muted"))
        if self.scenario.missing_reference:
            layout.addWidget(text_label(self.scenario.missing_reference, "Muted"))
        return card

    def _competencies_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._page_header(
            "Kompetenzen",
            "Fach → Kompetenzbereich → Thema → konkrete Kompetenz. Dokumentationsstand ist keine Schulnote.",
        ))
        layout.addWidget(self._competency_filter_bar())
        if self.scenario.total_areas == 0:
            layout.addWidget(self._empty_state("Kein Kompetenzkatalog", "Für dieses Profil sind keine Kompetenzen verfügbar."))
            return page
        subjects = (
            ("Mathematik", "6 von 8 dokumentiert", "Größen und Messen", "Zeit", "Uhrzeiten ablesen und darstellen"),
            ("Deutsch", "5 von 7 dokumentiert", "Lesen", "Sachtexte", "Zentrale Informationen auffinden"),
            ("EPU", "3 von 4 dokumentiert", "Natur und Umwelt", "Versuche", "Beobachtungen geordnet beschreiben"),
        )
        if self.scenario.documented_areas <= 3:
            subjects = (
                ("Mathematik", "2 von 8 dokumentiert", "Größen und Messen", "Zeit", "Volle Stunden ablesen"),
                ("Deutsch", "1 von 7 dokumentiert", "Lesen", "Sachtexte", "Informationen auffinden"),
            )
        for subject, count, area, topic, competency in subjects:
            layout.addWidget(self._subject_card(subject, count, area, topic, competency))
        if self.scenario.historical_reference:
            history, history_layout = make_card("WarningNotice")
            row = QHBoxLayout()
            row.addWidget(text_label("Historisch dokumentiert", "CardTitle"))
            row.addStretch(1)
            row.addWidget(badge("Separater Lesekontext", warning=True))
            history_layout.addLayout(row)
            history_layout.addWidget(text_label(self.scenario.historical_reference, "Body"))
            history_layout.addWidget(text_label("Nicht für neue Auswahl reaktiviert.", "Muted"))
            layout.addWidget(history)
        return page

    def _competency_filter_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("FilterBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        search = QLineEdit()
        search.setPlaceholderText("Kompetenzen durchsuchen")
        search.setAccessibleName("Kompetenzen durchsuchen")
        subject = QComboBox()
        subject.setAccessibleName("Kompetenzen nach Fach filtern")
        subject.addItems(("Alle Fächer", "Mathematik", "Deutsch", "EPU"))
        state = QComboBox()
        state.setAccessibleName("Kompetenzen nach Dokumentationszustand filtern")
        state.addItems(("Alle Zustände", "Dokumentiert", "Noch nicht dokumentiert", "Bestätigter Stand"))
        stage = QComboBox()
        stage.setAccessibleName("Kompetenzen nach Lernstufe filtern")
        stage.addItems(("Passende Kompetenzen", "Klassenstufe 4", "Alle Kompetenzen"))
        layout.addWidget(search, 2)
        layout.addWidget(subject)
        layout.addWidget(state)
        layout.addWidget(stage)
        return frame

    def _subject_card(self, subject: str, count: str, area: str, topic: str, competency: str) -> QFrame:
        card, layout = make_card("AccentCard")
        header = QHBoxLayout()
        header.addWidget(text_label(subject, "SectionTitle"))
        header.addStretch(1)
        header.addWidget(badge(count))
        open_button = make_button("Bereich öffnen", "quiet", f"Fach {subject} öffnen")
        header.addWidget(open_button)
        layout.addLayout(header)
        layout.addWidget(text_label("Dokumentationsabdeckung · keine Leistungsbewertung", "Muted"))
        detail, detail_layout = make_card("SoftCard")
        detail_layout.addWidget(text_label(area, "CardTitle"))
        detail_layout.addWidget(text_label(f"{topic} · {competency}", "Body"))
        detail_layout.addWidget(text_label("Bestätigter Stand und Beobachtungsbelege erst im Detail.", "Muted"))
        detail.setVisible(False)
        open_button.clicked.connect(lambda: self._toggle_detail(detail, open_button, "Bereich öffnen", "Bereich schließen"))
        layout.addWidget(detail)
        return card

    def _observations_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        header = self._page_header("Beobachtungen", "Neueste zuerst; Details und Bearbeiten bleiben bewusst erreichbar.")
        layout.addWidget(header)
        layout.addWidget(self._observation_filter_bar())
        if not self.scenario.observations:
            layout.addWidget(self._empty_state(
                "Noch keine Beobachtungen",
                "Gespeicherte Beobachtungen erscheinen hier chronologisch.",
                action_label="Beobachtung erfassen",
            ))
            return page
        for observation in self.scenario.observations:
            layout.addWidget(self._observation_row(observation, compact=False))
        return page

    def _observation_filter_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("FilterBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        search = QLineEdit()
        search.setPlaceholderText("Kontext, Notiz oder Kompetenz suchen")
        search.setAccessibleName("Beobachtungen durchsuchen")
        subject = QComboBox()
        subject.setAccessibleName("Beobachtungen nach Fach filtern")
        subject.addItems(("Alle Fächer", "Mathematik", "Deutsch", "EPU", "Fächerübergreifend"))
        rating = QComboBox()
        rating.setAccessibleName("Beobachtungen nach Bewertung filtern")
        rating.addItems(("Alle Bewertungen", "++", "+", "-", "--"))
        reset = make_button("Zurücksetzen", "quiet")
        layout.addWidget(search, 2)
        layout.addWidget(subject)
        layout.addWidget(rating)
        layout.addWidget(reset)
        return frame

    def _observation_row(self, observation: ObservationDemo, *, compact: bool) -> QFrame:
        row, layout = make_card("ObservationRow")
        layout.setContentsMargins(11, 9, 11, 9)
        header = QHBoxLayout()
        header.addWidget(text_label(observation.competency, "CardTitle"), 1)
        if observation.quick:
            header.addWidget(badge("Schnellbeobachtung"))
        if not compact:
            details_button = make_button("Details", "quiet")
            header.addWidget(details_button)
        layout.addLayout(header)
        layout.addWidget(text_label(f"{observation.subject} · {observation.date}", "Muted"))
        note = observation.note
        if compact and len(note) > 105:
            note = note[:102].rstrip() + "…"
        layout.addWidget(text_label(note, "Body"))
        meta_parts = [observation.context]
        if observation.competency_count:
            meta_parts.append(f"{observation.competency_count} Kompetenzbezüge")
        if observation.attachment_count:
            meta_parts.append(f"{observation.attachment_count} Anhang")
        layout.addWidget(text_label(" · ".join(meta_parts), "Muted"))
        if not compact:
            details, details_layout = make_card("SoftCard")
            details_layout.addWidget(text_label("Kompetenzen und Belege", "CardTitle"))
            details_layout.addWidget(text_label(
                "Konkrete Kompetenzbewertungen, Anhänge sowie die Aktionen Beobachtung öffnen, Bearbeiten und Löschen.",
                "Body",
            ))
            actions = QHBoxLayout()
            actions.addStretch(1)
            actions.addWidget(make_button("Bearbeiten", "secondary"))
            actions.addWidget(make_button("Löschen", "quiet"))
            details_layout.addLayout(actions)
            details.setVisible(False)
            details_button.clicked.connect(lambda: self._toggle_detail(details, details_button, "Details", "Details schließen"))
            layout.addWidget(details)
        return row

    def _documents_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        header = QHBoxLayout()
        header.addWidget(self._page_header(
            "Dokumente",
            "Berichtsentwurf, finale Revisionen, LEG und Dateien bleiben fachlich getrennte Wege.",
        ), 1)
        file_button = make_button("Datei hinzufügen", "secondary")
        file_button.clicked.connect(lambda: self._feedback("Prototyp: vorhandenen Datei-Dialog öffnen."))
        header.addWidget(file_button)
        layout.addLayout(header)
        layout.addWidget(self._document_workflow_card(
            "Lernentwicklungsbericht",
            self.scenario.report_draft_status,
            self.scenario.report_draft_meta or "Noch kein Entwurf angelegt.",
            "Bericht öffnen" if "vorhanden" in self.scenario.report_draft_status.lower() or "finalisierung" in self.scenario.report_draft_status.lower() else "Bericht erstellen",
        ))
        if self.scenario.revisions:
            revisions, revisions_layout = make_card("Card")
            revisions_layout.addWidget(text_label("Finalisierte Berichte und Revisionen", "SectionTitle"))
            revisions_layout.addWidget(text_label("Neueste Revision zuerst · schreibgeschützte historische Fassungen", "Muted"))
            for revision in self.scenario.revisions:
                revisions_layout.addWidget(self._revision_row(revision.number, revision.date, revision.responsible, revision.status))
            layout.addWidget(revisions)
        else:
            layout.addWidget(self._empty_state("Noch keine finale Revision", "Finalisierte Fassungen erscheinen hier schreibgeschützt."))
        layout.addWidget(self._document_workflow_card(
            "Lernentwicklungsgespräch",
            self.scenario.leg_status,
            self.scenario.leg_meta or "Noch kein Gesprächsentwurf angelegt.",
            "LEG öffnen" if "vorhanden" in self.scenario.leg_status.lower() else "LEG vorbereiten",
        ))
        if self.scenario.missing_reference:
            warning, warning_layout = make_card("WarningNotice")
            warning_layout.addWidget(text_label("Nicht verfügbare Referenz", "CardTitle"))
            warning_layout.addWidget(text_label(self.scenario.missing_reference, "Body"))
            warning_layout.addWidget(text_label("Gespeicherter Bezug bleibt sichtbar und kann bewusst abgewählt werden.", "Muted"))
            layout.addWidget(warning)
        return page

    def _document_workflow_card(self, title: str, status: str, meta: str, action: str) -> QFrame:
        card, layout = make_card("Card")
        header = QHBoxLayout()
        header.addWidget(text_label(title, "SectionTitle"))
        header.addStretch(1)
        header.addWidget(badge(status, warning="geändert" in status.lower(), positive="vorhanden" in status.lower()))
        layout.addLayout(header)
        layout.addWidget(text_label(meta, "Body"))
        button = make_button(action, "secondary")
        button.clicked.connect(lambda: self._feedback(f"Prototyp: {action}."))
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
        return card

    def _revision_row(self, number: int, date: str, responsible: str, status: str) -> QFrame:
        row, layout = make_card("DocumentRow")
        line = QHBoxLayout()
        line.addWidget(text_label(f"Revision {number}", "CardTitle", wrap=False))
        line.addWidget(badge(status, positive=status == "Aktuell"))
        line.addWidget(text_label(f"{date} · {responsible}", "Muted"), 1)
        line.addWidget(make_button("Öffnen", "quiet", f"Revision {number} öffnen"))
        layout.addLayout(line)
        return row

    def _history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._page_header(
            "Entwicklung" if self.variant == "a" else "Verlauf",
            "Chronologische Arbeitsereignisse und Berichtrevisionen bleiben getrennt lesbar.",
        ))
        observations, observation_layout = make_card("Card")
        observation_layout.addWidget(text_label("Beobachtungsverlauf", "SectionTitle"))
        if self.scenario.observations:
            for observation in self.scenario.observations:
                observation_layout.addWidget(self._history_row(
                    observation.date,
                    observation.subject,
                    observation.context,
                ))
        else:
            observation_layout.addWidget(text_label("Noch keine Beobachtungen dokumentiert.", "Muted"))
        layout.addWidget(observations)
        revisions, revision_layout = make_card("Card")
        revision_layout.addWidget(text_label("Berichtsrevisionen", "SectionTitle"))
        if self.scenario.revisions:
            for revision in self.scenario.revisions:
                revision_layout.addWidget(self._history_row(
                    revision.date,
                    f"Revision {revision.number}",
                    revision.status,
                ))
        else:
            revision_layout.addWidget(text_label("Noch keine finale Revision.", "Muted"))
        layout.addWidget(revisions)
        return page

    def _history_row(self, date: str, title: str, meta: str) -> QFrame:
        row, layout = make_card("HistoryRow")
        line = QHBoxLayout()
        line.addWidget(text_label(date, "CardTitle", wrap=False))
        line.addWidget(text_label(title, "Body"), 1)
        line.addWidget(text_label(meta, "Muted"), 1)
        layout.addLayout(line)
        return row

    def _empty_state(self, title: str, body: str, *, action_label: str = "") -> QFrame:
        card, layout = make_card("SoftCard")
        layout.setContentsMargins(14, 13, 14, 13)
        layout.addWidget(text_label(title, "CardTitle"))
        layout.addWidget(text_label(body, "Muted"))
        if action_label:
            button = make_button(action_label, "primary")
            button.clicked.connect(lambda: self._feedback(f"Prototyp: {action_label}."))
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
        return card

    def _toggle_detail(self, widget: QWidget, button: QPushButton, closed: str, opened: str) -> None:
        visible = widget.isHidden()
        widget.setVisible(visible)
        button.setText(opened if visible else closed)

    def _feedback(self, message: str) -> None:
        if hasattr(self, "prototype_status"):
            self.prototype_status.setText(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("a", "b"), default="a")
    parser.add_argument("--scenario", choices=tuple(SCENARIO_BY_KEY), default=BASE.key)
    parser.add_argument("--competency-card", choices=("ring", "bars"), default="ring")
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--screenshot", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Schülerprofil UX-Prototyp")
    app.setStyleSheet(APP_STYLE)
    window = StudentProfilePrototype(
        variant=args.variant,
        scenario_key=args.scenario,
        competency_card_variant=args.competency_card,
        width=args.width,
        height=args.height,
    )
    window.show()

    if args.screenshot is not None:
        target = args.screenshot.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        def capture() -> None:
            app.processEvents()
            if not window.grab().save(str(target)):
                raise RuntimeError(f"Screenshot konnte nicht gespeichert werden: {target}")
            app.quit()

        QTimer.singleShot(300, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
