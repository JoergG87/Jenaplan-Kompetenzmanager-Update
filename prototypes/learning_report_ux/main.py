"""Isolated PySide UX prototype for a fictional learning-development report.

This module deliberately imports no productive project module and performs no I/O.
All state lives in widgets for the lifetime of the process.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from demo_data import DEMO_CONTEXT, RATING_LEVELS, SUBJECTS


NAVY = "#17324D"
BLUE = "#2D6F93"
TURQUOISE = "#2A8C8C"
GREEN = "#5D8A68"
ORANGE = "#C98542"
INK = "#263746"
MUTED = "#657684"
PALE = "#F3F7F8"
LINE = "#D8E2E7"


APP_STYLE = f"""
QMainWindow, QWidget#PrototypeRoot {{ background: #EDF3F5; }}
QWidget {{ font-family: "Aptos", "Helvetica Neue", Arial; font-size: 14px; color: {INK}; }}
QFrame#TopBar {{ background: {NAVY}; border: none; }}
QLabel#Brand {{ color: white; font-size: 17px; font-weight: 700; }}
QLabel#PrototypeTag {{ color: #D8E9F0; font-size: 12px; }}
QPushButton#ModeButton {{ background: transparent; color: #DCEAF0; border: none; border-radius: 9px; padding: 9px 18px; font-weight: 600; }}
QPushButton#ModeButton:hover {{ background: #244661; }}
QPushButton#ModeButton:checked {{ background: white; color: {NAVY}; }}
QFrame#Sidebar {{ background: #F7FAFB; border-right: 1px solid {LINE}; }}
QLabel#Eyebrow {{ color: {BLUE}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
QLabel#ScreenTitle {{ color: {NAVY}; font-size: 28px; font-weight: 700; }}
QLabel#SectionTitle {{ color: {NAVY}; font-size: 18px; font-weight: 700; }}
QLabel#CardTitle {{ color: {NAVY}; font-size: 15px; font-weight: 700; }}
QLabel#Hint {{ color: {MUTED}; font-size: 12px; }}
QLabel#StatusPill {{ color: #73521C; background: #FFF4DB; border: 1px solid #ECD8A6; border-radius: 10px; padding: 4px 10px; font-weight: 600; }}
QLabel#ResponsibilityNote {{ color: #31526B; background: #EDF6FA; border: 1px solid #CFE2EA; border-radius: 9px; padding: 10px; }}
QLabel#InternalBadge {{ color: #76501E; background: #FFF6E8; border-radius: 8px; padding: 4px 8px; font-size: 11px; font-weight: 700; }}
QFrame#Card {{ background: white; border: 1px solid {LINE}; border-radius: 14px; }}
QFrame#InternalCard {{ background: #F4F7F8; border: 1px dashed #B7C7CF; border-radius: 12px; }}
QFrame#ReportCard {{ background: #FFFFFF; border: 1px solid #CFE0E6; border-radius: 12px; }}
QFrame#PaperPage {{ background: white; border: 1px solid #D6DEE2; border-radius: 3px; }}
QLineEdit, QTextEdit, QComboBox {{ background: white; border: 1px solid #C9D7DE; border-radius: 9px; padding: 8px 10px; selection-background-color: {BLUE}; }}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border: 1px solid {BLUE}; }}
QTextEdit {{ line-height: 1.4; }}
QComboBox {{ min-height: 24px; }}
QCheckBox {{ spacing: 9px; }}
QCheckBox::indicator {{ width: 17px; height: 17px; border: 1px solid #9CB0BB; border-radius: 4px; background: white; }}
QCheckBox::indicator:checked {{ background: {BLUE}; border-color: {BLUE}; image: none; }}
QPushButton {{ background: white; color: {NAVY}; border: 1px solid #BFD0D8; border-radius: 9px; padding: 8px 14px; font-weight: 600; }}
QPushButton:hover {{ background: #EDF5F8; border-color: #9DB8C5; }}
QPushButton#PrimaryButton {{ background: {BLUE}; color: white; border-color: {BLUE}; padding: 10px 18px; }}
QPushButton#PrimaryButton:hover {{ background: #255F7E; }}
QPushButton#SubjectButton {{ text-align: left; background: transparent; border: none; padding: 10px 12px; color: #49606F; }}
QPushButton#SubjectButton:checked {{ background: #E5F0F4; color: {NAVY}; border-left: 3px solid {BLUE}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C1CED4; border-radius: 5px; min-height: 32px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


def clear_layout(layout: QVBoxLayout | QHBoxLayout | QGridLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child = item.layout()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        elif child is not None:
            clear_layout(child)  # type: ignore[arg-type]


def label(text: str, role: str | None = None, wrap: bool = True) -> QLabel:
    item = QLabel(text)
    if role:
        item.setObjectName(role)
    item.setWordWrap(wrap)
    return item


def card(layout: QVBoxLayout | QHBoxLayout, object_name: str = "Card") -> QFrame:
    frame = QFrame()
    frame.setObjectName(object_name)
    frame.setLayout(layout)
    return frame


def section_header(title: str, hint: str | None = None) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(4)
    layout.addWidget(label(title, "SectionTitle"))
    if hint:
        layout.addWidget(label(hint, "Hint"))
    return layout


class CoverageChart(QWidget):
    """Documentation coverage only; deliberately carries no performance semantics."""

    def __init__(self, rows: list[tuple[str, int, int]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.rows = rows
        self.setMinimumHeight(72 + len(rows) * 42)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(INK))
        painter.setFont(QFont("Aptos", 10, QFont.Weight.DemiBold))
        painter.drawText(12, 22, "Dokumentationsstand · keine Leistungsbewertung")
        top = 47
        for name, documented, total in self.rows:
            painter.setPen(QColor(MUTED))
            painter.setFont(QFont("Aptos", 9))
            painter.drawText(12, top, name)
            painter.drawText(self.width() - 112, top, 100, 18, Qt.AlignmentFlag.AlignRight, f"{documented} von {total}")
            bar_y = top + 10
            bar_x = 12
            bar_width = max(80, self.width() - 24)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#E6EDF0"))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_width, 9), 4.5, 4.5)
            painter.setBrush(QColor("#66869A"))
            fill = bar_width * (documented / total if total else 0)
            painter.drawRoundedRect(QRectF(bar_x, bar_y, fill, 9), 4.5, 4.5)
            top += 42


class TimelineChart(QWidget):
    """One competency's evidence points, without aggregation or interpretation."""

    def __init__(self, points: list[tuple[str, int, str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.points = points
        self.setMinimumHeight(235)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        left, right, top, bottom = 154.0, float(self.width() - 30), 18.0, 164.0
        painter.setFont(QFont("Aptos", 9))
        for index, level in enumerate(RATING_LEVELS):
            y = bottom - index * ((bottom - top) / 3)
            painter.setPen(QPen(QColor("#E0E7EA"), 1))
            painter.drawLine(QPointF(left, y), QPointF(right, y))
            painter.setPen(QColor(MUTED))
            painter.drawText(QRectF(4, y - 10, left - 12, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, level)

        spacing = (right - left) / max(1, len(self.points) - 1)
        path = QPainterPath()
        coords: list[tuple[float, float, str, str]] = []
        for index, (period, score, point_type) in enumerate(self.points):
            x = left + spacing * index
            y = bottom - score * ((bottom - top) / 3)
            coords.append((x, y, period, point_type))
            if index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        if len(self.points) >= 2:
            painter.setPen(QPen(QColor("#95A8B1"), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        for x, y, period, point_type in coords:
            if point_type == "confirmed":
                painter.setPen(QPen(QColor(TURQUOISE), 2))
                painter.setBrush(QColor(TURQUOISE))
                painter.drawEllipse(QPointF(x, y), 5.5, 5.5)
            else:
                painter.setPen(QPen(QColor(BLUE), 2))
                painter.setBrush(QColor("#FFFFFF"))
                painter.drawEllipse(QPointF(x, y), 5.5, 5.5)
            painter.setPen(QColor(MUTED))
            painter.drawText(
                QRectF(x - 48, bottom + 9, 96, 38),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                period,
            )


class DensityChart(QWidget):
    """Quiet observation distribution; counts indicate documentation activity only."""

    def __init__(self, points: list[tuple[str, int]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.points = points
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(INK))
        painter.setFont(QFont("Aptos", 10, QFont.Weight.DemiBold))
        painter.drawText(12, 22, "Beobachtungsverteilung im Berichtszeitraum")
        painter.setFont(QFont("Aptos", 8))
        painter.setPen(QColor(MUTED))
        painter.drawText(12, 40, "Anzahl dokumentierter Beobachtungen · keine Leistungsbewertung")
        base_y, top_y = 145.0, 64.0
        left, right = 28.0, float(self.width() - 22)
        slot = (right - left) / max(1, len(self.points))
        max_count = max((count for _, count in self.points), default=1) or 1
        for index, (period, count) in enumerate(self.points):
            x = left + index * slot + slot * 0.18
            width = slot * 0.64
            height = (base_y - top_y) * count / max_count
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#D9E8EA"))
            painter.drawRoundedRect(QRectF(x, top_y, width, base_y - top_y), 5, 5)
            painter.setBrush(QColor("#5F9295"))
            painter.drawRoundedRect(QRectF(x, base_y - height, width, height), 5, 5)
            painter.setPen(QColor(MUTED))
            painter.drawText(QRectF(x, base_y + 7, width, 18), Qt.AlignmentFlag.AlignCenter, period)
            painter.drawText(QRectF(x, base_y - height - 20, width, 18), Qt.AlignmentFlag.AlignCenter, str(count))


@dataclass
class SubjectWidgets:
    include_subject: QCheckBox
    include_competencies: QCheckBox
    include_evidence: QCheckBox
    competency_checks: list[QCheckBox]
    competency_states: list[QComboBox]
    evidence_checks: list[QCheckBox]
    strengths: QTextEdit
    development: QTextEdit
    support: QTextEdit
    goals: QTextEdit
    chart_area_checks: list[QCheckBox]


class PrototypeWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sprint 7C · UX-Prototyp Lernentwicklungsbericht")
        self.resize(1500, 980)
        self.setMinimumSize(760, 680)
        self.subject_widgets: dict[str, SubjectWidgets] = {}
        self.subject_pages: dict[str, QWidget] = {}
        self._build_ui()
        self._connect_preview_updates()
        self.rebuild_preview()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("PrototypeRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._top_bar())
        self.mode_stack = QStackedWidget()
        self.editor_screen = self._editor_screen()
        self.preview_screen = self._preview_screen()
        self.mode_stack.addWidget(self.editor_screen)
        self.mode_stack.addWidget(self.preview_screen)
        root_layout.addWidget(self.mode_stack, 1)
        self.setCentralWidget(root)

    def _top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(68)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 10, 20, 10)
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(0)
        brand_layout.addWidget(label("Jenaplan Kompetenzmanager", "Brand", False))
        brand_layout.addWidget(label("Sprint 7C · isolierter UX-Prototyp · nur Demo-Daten", "PrototypeTag", False))
        layout.addLayout(brand_layout)
        layout.addStretch()
        self.edit_mode_button = QPushButton("✎  Bericht bearbeiten")
        self.preview_mode_button = QPushButton("▤  Berichtsvorschau")
        for button in (self.edit_mode_button, self.preview_mode_button):
            button.setObjectName("ModeButton")
            button.setCheckable(True)
            layout.addWidget(button)
        self.edit_mode_button.setChecked(True)
        group = QButtonGroup(self)
        group.setExclusive(True)
        group.addButton(self.edit_mode_button)
        group.addButton(self.preview_mode_button)
        self.edit_mode_button.clicked.connect(lambda: self._set_mode(0))
        self.preview_mode_button.clicked.connect(lambda: self._set_mode(1))
        return bar

    def _set_mode(self, index: int) -> None:
        self.mode_stack.setCurrentIndex(index)
        self.edit_mode_button.setChecked(index == 0)
        self.preview_mode_button.setChecked(index == 1)
        if index == 1:
            self.rebuild_preview()

    def _editor_screen(self) -> QWidget:
        screen = QWidget()
        layout = QHBoxLayout(screen)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._editor_sidebar())

        self.editor_stack = QStackedWidget()
        self.editor_stack.addWidget(self._overview_editor())
        for subject_name in SUBJECTS:
            page = self._subject_editor(subject_name)
            self.subject_pages[subject_name] = page
            self.editor_stack.addWidget(page)
        self.editor_stack.addWidget(self._closing_editor())
        layout.addWidget(self.editor_stack, 1)
        return screen

    def _editor_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(248)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 18)
        layout.setSpacing(5)
        layout.addWidget(label("ARBEITSBEREICHE", "Eyebrow"))
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        entries = [("Dokument & Gesamtblick", 0)]
        entries.extend((name, index + 1) for index, name in enumerate(SUBJECTS))
        entries.append(("Abschluss", len(SUBJECTS) + 1))
        for title, index in entries:
            button = QPushButton(title)
            button.setObjectName("SubjectButton")
            button.setCheckable(True)
            if index == 0:
                button.setChecked(True)
            button.clicked.connect(lambda checked=False, target=index: self.editor_stack.setCurrentIndex(target))
            self.nav_group.addButton(button)
            layout.addWidget(button)
        layout.addStretch()
        note = label("Flüchtiger Demo-Stand\nKeine Speicherung · keine PDF-Erzeugung", "Hint")
        layout.addWidget(note)
        preview = QPushButton("Vorschau öffnen  →")
        preview.setObjectName("PrimaryButton")
        preview.clicked.connect(lambda: self._set_mode(1))
        layout.addWidget(preview)
        return sidebar

    def _scroll_page(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    def _page_canvas(self) -> tuple[QWidget, QVBoxLayout]:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 30, 46, 56)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        return content, layout

    def _overview_editor(self) -> QScrollArea:
        content, layout = self._page_canvas()
        title_row = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.addWidget(label("BERICHT BEARBEITEN", "Eyebrow"))
        title_block.addWidget(label("Dokumentkontext & pädagogischer Gesamtblick", "ScreenTitle"))
        title_row.addLayout(title_block, 1)
        title_row.addWidget(label("Entwurf", "StatusPill"), 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(title_row)
        layout.addWidget(label("Alle Angaben sind eindeutig fiktive Demo-Daten und werden nur im Arbeitsspeicher gehalten.", "Hint"))

        context_layout = QGridLayout()
        context_layout.setContentsMargins(22, 20, 22, 22)
        context_layout.setHorizontalSpacing(18)
        context_layout.setVerticalSpacing(8)
        context_layout.addWidget(label("Dokumentkontext", "SectionTitle"), 0, 0, 1, 4)
        fields = [
            ("Schülername", "student_name"),
            ("Stammgruppe", "group_name"),
            ("Berichtsart", "report_type"),
            ("Verantwortliche Lehrkraft", "teacher_name"),
            ("Zeitraum von", "period_from"),
            ("Zeitraum bis", "period_to"),
        ]
        self.context_fields: dict[str, QLineEdit] = {}
        for index, (title, key) in enumerate(fields):
            row = 1 + index // 2 * 2
            column = (index % 2) * 2
            context_layout.addWidget(label(title, "Hint"), row, column)
            field = QLineEdit(DEMO_CONTEXT[key])
            self.context_fields[key] = field
            context_layout.addWidget(field, row + 1, column)
        context_layout.setColumnStretch(0, 1)
        context_layout.setColumnStretch(2, 1)
        layout.addWidget(card(context_layout))

        overall_layout = QVBoxLayout()
        overall_layout.setContentsMargins(22, 20, 22, 22)
        overall_layout.setSpacing(10)
        heading = QHBoxLayout()
        heading.addWidget(label("Pädagogischer Gesamtblick", "SectionTitle"))
        heading.addStretch()
        self.include_overall = QCheckBox("In Vorschau zeigen")
        self.include_overall.setChecked(True)
        heading.addWidget(self.include_overall)
        overall_layout.addLayout(heading)
        overall_layout.addWidget(label("Von der Lehrkraft verfasst und pädagogisch verantwortet", "ResponsibilityNote"))
        self.overall_edit = QTextEdit(DEMO_CONTEXT["overall"])
        self.overall_edit.setMinimumHeight(190)
        overall_layout.addWidget(self.overall_edit)
        overall_layout.addWidget(label("Schreibhilfe: Beschreibe beobachtbare Lernwege, hilfreiche Bedingungen und nächste pädagogische Schritte in deiner eigenen Sprache. Es werden keine Formulierungen automatisch erzeugt.", "Hint"))
        layout.addWidget(card(overall_layout))
        return self._scroll_page(content)

    def _subject_editor(self, subject_name: str) -> QScrollArea:
        data = SUBJECTS[subject_name]
        content, layout = self._page_canvas()
        title_row = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.addWidget(label("FACHAUSWAHL · ARBEITSBEREICH", "Eyebrow"))
        title_block.addWidget(label(subject_name, "ScreenTitle"))
        title_block.addWidget(label("Interne Arbeitsgrundlage und spätere Berichtsinhalte bleiben bewusst getrennt.", "Hint"))
        title_row.addLayout(title_block, 1)
        include_subject = QCheckBox("Fachabschnitt in Vorschau")
        include_subject.setChecked(subject_name in ("Deutsch", "Mathematik"))
        title_row.addWidget(include_subject, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(title_row)

        internal_layout = QVBoxLayout()
        internal_layout.setContentsMargins(20, 18, 20, 20)
        internal_layout.setSpacing(12)
        internal_title = QHBoxLayout()
        internal_title.addWidget(label("Interne Dokumentationsübersicht", "SectionTitle"))
        internal_title.addStretch()
        internal_title.addWidget(label("NUR ARBEITSGRUNDLAGE", "InternalBadge"))
        internal_layout.addLayout(internal_title)
        internal_layout.addWidget(label(data["summary"], "CardTitle"))
        internal_layout.addWidget(label("Diese Hinweise liefern Material für Lauras Einordnung. Sie werden nicht automatisch zu Berichtsaussagen.", "Hint"))

        internal_layout.addWidget(label("Kompetenzbereiche auswählen", "CardTitle"))
        area_row = QHBoxLayout()
        for area in data["areas"]:
            checkbox = QCheckBox(area)
            checkbox.setChecked(True)
            area_row.addWidget(checkbox)
        area_row.addStretch()
        internal_layout.addLayout(area_row)

        internal_layout.addWidget(label("Konkrete Kompetenzen und Arbeitsstände", "CardTitle"))
        competency_checks: list[QCheckBox] = []
        competency_states: list[QComboBox] = []
        for competency, state in data["competencies"]:
            row = QHBoxLayout()
            checkbox = QCheckBox(competency)
            checkbox.setChecked(True)
            checkbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            selector = QComboBox()
            selector.addItems([
                "Beobachtet · mit Unterstützung",
                "Beobachtet · zunehmend sicher",
                "Bestätigt · zunehmend sicher",
                "Bestätigt · sicher",
            ])
            if selector.findText(state) >= 0:
                selector.setCurrentText(state)
            row.addWidget(checkbox, 1)
            row.addWidget(selector)
            internal_layout.addLayout(row)
            competency_checks.append(checkbox)
            competency_states.append(selector)

        internal_layout.addWidget(label("Beobachtungsbelege auswählen", "CardTitle"))
        evidence_checks: list[QCheckBox] = []
        for evidence in data["evidence"]:
            checkbox = QCheckBox(evidence)
            checkbox.setChecked(len(evidence_checks) < 2)
            checkbox.setToolTip("Bewusste Auswahl durch die Lehrkraft")
            internal_layout.addWidget(checkbox)
            evidence_checks.append(checkbox)
        layout.addWidget(card(internal_layout, "InternalCard"))

        report_layout = QVBoxLayout()
        report_layout.setContentsMargins(20, 18, 20, 22)
        report_layout.setSpacing(14)
        report_title = QHBoxLayout()
        report_title.addWidget(label("Von Laura verantwortete Berichtsinhalte", "SectionTitle"))
        report_title.addStretch()
        report_title.addWidget(label("SPÄTERE AUSGABE", "Eyebrow"))
        report_layout.addLayout(report_title)
        text_widgets: list[QTextEdit] = []
        for title, key in (
            ("Stärken", "strengths"),
            ("Lernentwicklung", "development"),
            ("Unterstützungsbedarf", "support"),
            ("Nächste Ziele", "goals"),
        ):
            report_layout.addWidget(label(title, "CardTitle"))
            edit = QTextEdit(data[key])
            edit.setMinimumHeight(100)
            report_layout.addWidget(edit)
            text_widgets.append(edit)
        layout.addWidget(card(report_layout, "ReportCard"))

        graphics_layout = QVBoxLayout()
        graphics_layout.setContentsMargins(20, 18, 20, 22)
        graphics_layout.setSpacing(9)
        graphics_layout.addWidget(label("Kompetenzbereiche für Entwicklungsdarstellung", "SectionTitle"))
        graphics_layout.addWidget(label("Laura wählt ausschließlich Kompetenzbereiche für die grafische Darstellung. Die Auswahl ist keine pädagogische Priorisierung oder Leistungsentscheidung und verändert weder Berichtstext, konkrete Kompetenzen noch Belege.", "ResponsibilityNote"))
        chart_area_checks: list[QCheckBox] = []
        for area in data["areas"]:
            checkbox = QCheckBox(area)
            checkbox.setChecked(False)
            checkbox.setToolTip("Kompetenzbereich nur für die Entwicklungsdarstellung auswählen")
            checkbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            graphics_layout.addWidget(checkbox)
            chart_area_checks.append(checkbox)
        graphics_layout.addWidget(label("Ohne ausgewählten Kompetenzbereich erscheint in der Vorschau ein neutraler Hinweis statt eines leeren Diagramms.", "Hint"))
        layout.addWidget(card(graphics_layout))

        visibility = QHBoxLayout()
        include_competencies = QCheckBox("Konkrete Kompetenzen ausgeben")
        include_evidence = QCheckBox("Ausgewählte Belege ausgeben")
        include_competencies.setChecked(True)
        include_evidence.setChecked(True)
        visibility.addWidget(include_competencies)
        visibility.addWidget(include_evidence)
        visibility.addStretch()
        layout.addLayout(visibility)

        self.subject_widgets[subject_name] = SubjectWidgets(
            include_subject=include_subject,
            include_competencies=include_competencies,
            include_evidence=include_evidence,
            competency_checks=competency_checks,
            competency_states=competency_states,
            evidence_checks=evidence_checks,
            strengths=text_widgets[0],
            development=text_widgets[1],
            support=text_widgets[2],
            goals=text_widgets[3],
            chart_area_checks=chart_area_checks,
        )
        return self._scroll_page(content)

    def _closing_editor(self) -> QScrollArea:
        content, layout = self._page_canvas()
        layout.addLayout(section_header("Abschluss", "Übergreifende Einordnung, nächste Schritte und eine klar getrennte interne Notiz."))

        report_layout = QVBoxLayout()
        report_layout.setContentsMargins(22, 20, 22, 22)
        report_layout.setSpacing(10)
        report_layout.addWidget(label("Allgemeine nächste Schritte", "CardTitle"))
        self.next_steps_edit = QTextEdit(DEMO_CONTEXT["next_steps"])
        self.next_steps_edit.setMinimumHeight(135)
        report_layout.addWidget(self.next_steps_edit)
        report_layout.addWidget(label("Abschließende Einordnung", "CardTitle"))
        self.closing_edit = QTextEdit(DEMO_CONTEXT["closing"])
        self.closing_edit.setMinimumHeight(135)
        report_layout.addWidget(self.closing_edit)
        layout.addWidget(card(report_layout, "ReportCard"))

        internal_layout = QVBoxLayout()
        internal_layout.setContentsMargins(22, 20, 22, 22)
        internal_title = QHBoxLayout()
        internal_title.addWidget(label("Interne Notiz", "SectionTitle"))
        internal_title.addStretch()
        internal_title.addWidget(label("NICHT FÜR DIE AUSGABE", "InternalBadge"))
        internal_layout.addLayout(internal_title)
        self.internal_note_edit = QTextEdit(DEMO_CONTEXT["internal_note"])
        self.internal_note_edit.setMinimumHeight(110)
        internal_layout.addWidget(self.internal_note_edit)
        internal_layout.addWidget(label("Die Vorschau übernimmt diesen Inhalt absichtlich nicht.", "Hint"))
        layout.addWidget(card(internal_layout, "InternalCard"))

        action_row = QHBoxLayout()
        action_row.addStretch()
        button = QPushButton("Vorschau mit aktuellem Demo-Stand öffnen  →")
        button.setObjectName("PrimaryButton")
        button.clicked.connect(lambda: self._set_mode(1))
        action_row.addWidget(button)
        layout.addLayout(action_row)
        return self._scroll_page(content)

    def _preview_screen(self) -> QWidget:
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        tools = QFrame()
        tools.setObjectName("Sidebar")
        tools.setFixedHeight(68)
        tools_layout = QHBoxLayout(tools)
        tools_layout.setContentsMargins(28, 12, 28, 12)
        title = QVBoxLayout()
        title.setSpacing(1)
        title.addWidget(label("BERICHTSVORSCHAU", "Eyebrow"))
        title.addWidget(label("Mehrseitige Dokumentansicht · wird aus Demo-Eingaben aktualisiert", "CardTitle"))
        tools_layout.addLayout(title)
        tools_layout.addStretch()
        self.preview_status = label("Aktueller Demo-Stand", "Hint")
        tools_layout.addWidget(self.preview_status)
        back = QPushButton("←  Weiter bearbeiten")
        back.clicked.connect(lambda: self._set_mode(0))
        tools_layout.addWidget(back)
        layout.addWidget(tools)

        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_content = QWidget()
        self.preview_pages_layout = QVBoxLayout(self.preview_content)
        self.preview_pages_layout.setContentsMargins(30, 34, 30, 60)
        self.preview_pages_layout.setSpacing(30)
        self.preview_pages_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.preview_scroll.setWidget(self.preview_content)
        layout.addWidget(self.preview_scroll, 1)
        return screen

    def _connect_preview_updates(self) -> None:
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(120)
        self._preview_timer.timeout.connect(self.rebuild_preview)

        def schedule(*args) -> None:
            self._preview_timer.start()

        for field in self.context_fields.values():
            field.textChanged.connect(schedule)
        for edit in (self.overall_edit, self.next_steps_edit, self.closing_edit):
            edit.textChanged.connect(schedule)
        self.include_overall.toggled.connect(schedule)
        for widgets in self.subject_widgets.values():
            for checkbox in (
                widgets.include_subject,
                widgets.include_competencies,
                widgets.include_evidence,
                *widgets.chart_area_checks,
                *widgets.competency_checks,
                *widgets.evidence_checks,
            ):
                checkbox.toggled.connect(schedule)
            for selector in widgets.competency_states:
                selector.currentTextChanged.connect(schedule)
            for edit in (widgets.strengths, widgets.development, widgets.support, widgets.goals):
                edit.textChanged.connect(schedule)

    def _paper(self, page_number: int, kicker: str) -> tuple[QFrame, QVBoxLayout]:
        page = QFrame()
        page.setObjectName("PaperPage")
        page.setFixedWidth(820)
        page.setMinimumHeight(1120)
        page.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(66, 54, 66, 48)
        layout.setSpacing(18)
        header = QHBoxLayout()
        header.addWidget(label("JENAPLAN · DEMO-SCHULPLATZHALTER", "Eyebrow"))
        header.addStretch()
        header.addWidget(label(kicker, "Hint"))
        layout.addLayout(header)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"color: {LINE};")
        layout.addWidget(separator)
        page.setProperty("page_number", page_number)
        return page, layout

    def _page_footer(self, layout: QVBoxLayout, page_number: int) -> None:
        layout.addStretch()
        footer = QHBoxLayout()
        footer.addWidget(label("Fiktiver UX-Prototyp · kein freigegebener Bericht", "Hint"))
        footer.addStretch()
        footer.addWidget(label(f"Seite {page_number}", "Hint"))
        layout.addLayout(footer)

    def rebuild_preview(self) -> None:
        if not hasattr(self, "preview_pages_layout"):
            return
        clear_layout(self.preview_pages_layout)
        pages: list[QFrame] = []
        pages.append(self._build_cover_page(1))
        pages.append(self._build_overview_page(2))
        page_number = 3
        for subject_name, widgets in self.subject_widgets.items():
            if widgets.include_subject.isChecked():
                pages.append(self._build_subject_page(subject_name, widgets, page_number))
                page_number += 1
        pages.append(self._build_closing_page(page_number))
        for page in pages:
            self.preview_pages_layout.addWidget(page, 0, Qt.AlignmentFlag.AlignHCenter)
        self.preview_pages_layout.addStretch()
        if hasattr(self, "preview_status"):
            self.preview_status.setText(f"Live aktualisiert · {len(pages)} simulierte Seiten")

    def _context(self, key: str) -> str:
        return self.context_fields[key].text().strip() or "—"

    def _build_cover_page(self, page_number: int) -> QFrame:
        page, layout = self._paper(page_number, "Lernentwicklungsbericht")
        layout.addSpacing(22)
        layout.addWidget(label("Lernentwicklungsbericht", "ScreenTitle"))
        layout.addWidget(label("Eine zeitraumbezogene pädagogische Dokumentation", "Hint"))
        layout.addSpacing(10)

        name = label(self._context("student_name"))
        name.setStyleSheet(f"font-size: 27px; font-weight: 650; color: {NAVY};")
        layout.addWidget(name)
        meta = QGridLayout()
        meta.setHorizontalSpacing(34)
        meta.setVerticalSpacing(10)
        meta_items = [
            ("Stammgruppe", self._context("group_name")),
            ("Zeitraum", f"{self._context('period_from')} – {self._context('period_to')}"),
            ("Berichtsart", self._context("report_type")),
            ("Verantwortliche Lehrkraft", self._context("teacher_name")),
        ]
        for index, (title, value) in enumerate(meta_items):
            meta.addWidget(label(title.upper(), "Eyebrow"), index, 0)
            meta.addWidget(label(value, "CardTitle"), index, 1)
        layout.addLayout(meta)
        layout.addSpacing(24)
        if self.include_overall.isChecked():
            layout.addWidget(label("Pädagogischer Gesamtblick", "SectionTitle"))
            overall = label(self.overall_edit.toPlainText().strip() or "Noch kein Text eingetragen.")
            overall.setStyleSheet("font-size: 16px; line-height: 1.55; color: #334955;")
            layout.addWidget(overall)
        self._page_footer(layout, page_number)
        return page

    def _build_overview_page(self, page_number: int) -> QFrame:
        page, layout = self._paper(page_number, "Überblick")
        layout.addWidget(label("Überblick über die Fachabschnitte", "ScreenTitle"))
        layout.addWidget(label("Die Übersicht zeigt den Umfang vorhandener Dokumentation. Sie enthält weder Gesamtpunktzahl noch allgemeinen Leistungswert.", "ResponsibilityNote"))
        for subject_name, widgets in self.subject_widgets.items():
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(16, 12, 16, 12)
            text = QVBoxLayout()
            text.addWidget(label(subject_name, "CardTitle"))
            text.addWidget(label(SUBJECTS[subject_name]["summary"], "Hint"))
            row_layout.addLayout(text, 1)
            state = "Fachabschnitt ausgewählt" if widgets.include_subject.isChecked() else "nicht für Ausgabe ausgewählt"
            state_label = label(state, "Hint")
            row_layout.addWidget(state_label)
            layout.addWidget(card(row_layout, "ReportCard"))
        layout.addSpacing(10)
        layout.addWidget(label("Hinweis zur Datenbasis", "SectionTitle"))
        layout.addWidget(label("Die dargestellten Informationen beruhen in diesem Prototyp ausschließlich auf fiktiven Beobachtungen und manuell gewählten Demo-Ständen. Dokumentationsabdeckung beschreibt, zu welchen konkreten Kompetenzen Hinweise vorliegen; sie bewertet weder Lernerfolg noch Leistung."))
        self._page_footer(layout, page_number)
        return page

    def _build_subject_page(self, subject_name: str, widgets: SubjectWidgets, page_number: int) -> QFrame:
        data = SUBJECTS[subject_name]
        page, layout = self._paper(page_number, subject_name)
        layout.addWidget(label(subject_name, "ScreenTitle"))
        layout.addWidget(label(data["summary"], "Hint"))

        narrative_grid = QGridLayout()
        narrative_grid.setHorizontalSpacing(24)
        narrative_grid.setVerticalSpacing(16)
        narrative_items = [
            ("Lernentwicklung", widgets.development.toPlainText()),
            ("Stärken", widgets.strengths.toPlainText()),
            ("Unterstützungsbedarf", widgets.support.toPlainText()),
            ("Nächste Ziele", widgets.goals.toPlainText()),
        ]
        for index, (title, text_value) in enumerate(narrative_items):
            block = QVBoxLayout()
            block.addWidget(label(title, "CardTitle"))
            block.addWidget(label(text_value.strip() or "Noch kein Text eingetragen.", None))
            narrative_grid.addLayout(block, index // 2, index % 2)
        layout.addLayout(narrative_grid)

        if widgets.include_competencies.isChecked():
            layout.addWidget(label("Ausgewählte konkrete Kompetenzen", "SectionTitle"))
            selected = [
                (checkbox.text(), selector.currentText())
                for checkbox, selector in zip(widgets.competency_checks, widgets.competency_states)
                if checkbox.isChecked()
            ]
            if selected:
                for competency, state in selected:
                    row = QHBoxLayout()
                    bullet = label("•", None, False)
                    bullet.setStyleSheet(f"color: {TURQUOISE}; font-size: 18px;")
                    row.addWidget(bullet, 0, Qt.AlignmentFlag.AlignTop)
                    text = QVBoxLayout()
                    text.setSpacing(1)
                    text.addWidget(label(competency))
                    text.addWidget(label(state, "Hint"))
                    row.addLayout(text, 1)
                    layout.addLayout(row)
            else:
                layout.addWidget(label("Keine konkrete Kompetenz für die Ausgabe ausgewählt.", "Hint"))

        if widgets.include_evidence.isChecked():
            layout.addWidget(label("Bewusst ausgewählte Beobachtungsbelege", "SectionTitle"))
            selected_evidence = [item.text() for item in widgets.evidence_checks if item.isChecked()]
            if selected_evidence:
                for evidence in selected_evidence:
                    layout.addWidget(label(f"—  {evidence}"))
            else:
                layout.addWidget(label("Keine Beobachtungsbelege für die Ausgabe ausgewählt.", "Hint"))

        selected_charts = [
            (index, checkbox.text())
            for index, checkbox in enumerate(widgets.chart_area_checks)
            if checkbox.isChecked()
        ]
        layout.addWidget(label("Entwicklungsdarstellungen", "SectionTitle"))
        if not selected_charts:
            layout.addWidget(label("Für diesen Fachbereich wurde kein Kompetenzbereich für eine Entwicklungsdarstellung ausgewählt.", "ResponsibilityNote"))
        for index, area in selected_charts:
            points = data["area_timelines"][index]
            chart_layout = QVBoxLayout()
            chart_layout.setContentsMargins(16, 14, 16, 14)
            chart_layout.setSpacing(8)
            chart_layout.addWidget(label(area, "CardTitle"))
            chart_layout.addWidget(label("Beobachtete und bestätigte Stände in diesem Kompetenzbereich · keine Fachnote, keine Gesamtleistung und keine Trendinterpretation", "Hint"))
            chart_layout.addWidget(TimelineChart(points))
            legend = label("○ Beobachtung    ● bestätigter Stand", "Hint")
            legend.setStyleSheet(f"color: {MUTED}; padding-top: 2px;")
            chart_layout.addWidget(legend)
            if len(points) == 1:
                chart_layout.addWidget(label("Für diesen Kompetenzbereich liegt ein Datenpunkt vor. Er wird ohne Verbindungslinie dargestellt; die Datenbasis ist begrenzt.", "ResponsibilityNote"))
            elif len(points) == 2:
                chart_layout.addWidget(label("Zwei dokumentierte Zeitpunkte werden verbunden. Daraus wird keine Entwicklungstendenz abgeleitet.", "Hint"))
            layout.addWidget(card(chart_layout, "ReportCard"))
        self._page_footer(layout, page_number)
        return page

    def _build_closing_page(self, page_number: int) -> QFrame:
        page, layout = self._paper(page_number, "Abschluss")
        layout.addWidget(label("Übergreifende Entwicklung & nächste Schritte", "ScreenTitle"))
        layout.addWidget(label("Nächste Schritte", "SectionTitle"))
        layout.addWidget(label(self.next_steps_edit.toPlainText().strip() or "Noch kein Text eingetragen."))
        layout.addSpacing(8)
        layout.addWidget(label("Abschlussbemerkung", "SectionTitle"))
        layout.addWidget(label(self.closing_edit.toPlainText().strip() or "Noch kein Text eingetragen."))
        layout.addSpacing(22)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(18, 16, 18, 16)
        info_layout.addWidget(label("Erstellungs- und Freigabeinformation", "CardTitle"))
        info_layout.addWidget(label(f"Verantwortliche Lehrkraft: {self._context('teacher_name')}"))
        info_layout.addWidget(label("Status im Prototyp: Entwurf · noch nicht fachlich freigegeben", "Hint"))
        info_layout.addWidget(label("Eine spätere Ausgabe würde ausschließlich einen freigegebenen, eingefrorenen Ausgabestand verwenden.", "Hint"))
        layout.addWidget(card(info_layout, "ReportCard"))
        layout.addSpacing(34)
        signature = QHBoxLayout()
        for title in ("Kenntnisnahme", "Lehrkraft"):
            block = QVBoxLayout()
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("color: #AEBBC1;")
            block.addWidget(line)
            block.addWidget(label(title, "Hint"))
            signature.addLayout(block, 1)
            signature.addSpacing(40)
        layout.addLayout(signature)
        self._page_footer(layout, page_number)
        return page


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Lernentwicklungsbericht UX-Prototyp")
    app.setStyleSheet(APP_STYLE)
    window = PrototypeWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
