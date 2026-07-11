"""Isolated visual prototype for the Sprint 5B1 observation workspace.

This module deliberately uses static demo data only. It does not import the
productive observation dialog, adapters, repositories, SQLite or the catalog.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from PySide6.QtCore import QDate, QTimer, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.theme import (
    COLOR_BACKGROUND,
    COLOR_BLUE,
    COLOR_BLUE_SOFT,
    COLOR_BORDER,
    COLOR_GREEN,
    COLOR_NAVY,
    COLOR_SURFACE,
    COLOR_SURFACE_SOFT,
    COLOR_TEXT_MUTED,
    PRIMARY_BUTTON_STYLESHEET,
    apply_app_theme,
    set_label_style,
)


RATING_OPTIONS = (
    "++ sicher erreicht",
    "+ erreicht",
    "- in Entwicklung",
    "-- Unterstützungsbedarf",
)


@dataclass(frozen=True)
class DemoCompetency:
    competency_id: str
    subject: str
    learning_area: str
    topic: str
    text: str
    historical: bool = False


@dataclass
class SelectedCompetency:
    competency: DemoCompetency
    rating: str


DEMO_CATALOG: dict[str, tuple[DemoCompetency, ...]] = {
    "Deutsch": (
        DemoCompetency(
            "DEU-01",
            "Deutsch",
            "Sprechen und Zuhören",
            "Gespräche führen",
            "beteiligt sich aufmerksam an Gesprächen, greift Beiträge anderer auf und begründet die eigene Sicht verständlich",
        ),
        DemoCompetency(
            "DEU-02",
            "Deutsch",
            "Sprechen und Zuhören",
            "Präsentieren",
            "stellt ein Arbeitsergebnis adressatengerecht vor und beantwortet Rückfragen zum gewählten Vorgehen",
        ),
        DemoCompetency(
            "DEU-03",
            "Deutsch",
            "Lesen",
            "Texte erschließen",
            "entnimmt einem längeren Sachtext gezielt Informationen, verknüpft Aussagen aus mehreren Abschnitten und belegt Schlussfolgerungen mit passenden Textstellen",
        ),
        DemoCompetency(
            "DEU-04",
            "Deutsch",
            "Lesen",
            "Leseerfahrung",
            "beschreibt die Wirkung einer Figur oder Handlung und tauscht sich über unterschiedliche Lesarten aus",
        ),
        DemoCompetency(
            "DEU-05",
            "Deutsch",
            "Schreiben",
            "Texte planen und verfassen",
            "plant einen Text mit einer passenden Gliederung und überarbeitet ihn im Hinblick auf Verständlichkeit und Wirkung",
        ),
    ),
    "Mathematik": (
        DemoCompetency(
            "MAT-01",
            "Mathematik",
            "Zahlen und Operationen",
            "Rechenstrategien",
            "nutzt halbschriftliche Rechenstrategien flexibel und erklärt den gewählten Lösungsweg nachvollziehbar",
        ),
        DemoCompetency(
            "MAT-02",
            "Mathematik",
            "Zahlen und Operationen",
            "Zahlvorstellungen",
            "ordnet und vergleicht Zahlen im Zahlenraum und nutzt Stellenwerte zur Begründung",
        ),
        DemoCompetency(
            "MAT-03",
            "Mathematik",
            "Größen und Messen",
            "Zeit",
            "liest Uhrzeiten sicher ab, bestimmt Zeitspannen und verwendet passende Einheiten in Sachsituationen",
        ),
        DemoCompetency(
            "MAT-04",
            "Mathematik",
            "Raum und Form",
            "Geometrische Körper",
            "beschreibt geometrische Körper anhand ihrer Eigenschaften und erkennt sie in unterschiedlichen Darstellungen wieder",
        ),
    ),
    "EPU": (
        DemoCompetency(
            "EPU-01",
            "EPU",
            "Natur und Umwelt",
            "Lebensräume untersuchen",
            "beobachtet Veränderungen in einem Lebensraum systematisch und dokumentiert Zusammenhänge in geeigneter Form",
        ),
        DemoCompetency(
            "EPU-02",
            "EPU",
            "Natur und Umwelt",
            "Nachhaltig handeln",
            "entwickelt begründete Ideen für einen verantwortungsvollen Umgang mit natürlichen Ressourcen im Schulalltag",
        ),
        DemoCompetency(
            "EPU-03",
            "EPU",
            "Zeit und Wandel",
            "Vergangenheit erschließen",
            "nutzt Quellen, um Fragen an die Vergangenheit zu beantworten, und unterscheidet Beobachtung von Vermutung",
        ),
        DemoCompetency(
            "EPU-04",
            "EPU",
            "Gemeinschaft und Zusammenleben",
            "Entscheidungen treffen",
            "vergleicht verschiedene Interessen und beteiligt sich konstruktiv an einer gemeinsamen Entscheidung",
        ),
    ),
}


HISTORICAL_COMPETENCY = DemoCompetency(
    "HIST-01",
    "Deutsch",
    "Lesen",
    "Historischer Bestand",
    "liest altersgemäße Texte sinnentnehmend und gibt wesentliche Inhalte wieder",
    historical=True,
)


PROTOTYPE_STYLESHEET = f"""
QWidget#PrototypeRoot {{
    background-color: {COLOR_BACKGROUND};
}}
QFrame#PrototypeZone {{
    background-color: rgba(255, 255, 255, 248);
    border: 1px solid {COLOR_BORDER};
    border-radius: 16px;
}}
QFrame#PrototypeSubtleCard {{
    background-color: {COLOR_SURFACE_SOFT};
    border: 1px solid #DDE7EE;
    border-radius: 10px;
}}
QFrame#CatalogCompetencyTile {{
    background-color: {COLOR_SURFACE};
    border: 1px solid #D7E4ED;
    border-radius: 10px;
}}
QFrame#CatalogCompetencyTile[is_selected="false"]:hover {{
    background-color: #EEF6FB;
    border-color: #AFCADC;
}}
QFrame#CatalogCompetencyTile[is_selected="false"]:focus {{
    border: 2px solid {COLOR_BLUE};
}}
QFrame#CatalogCompetencyTile[is_selected="true"] {{
    background-color: #F2F7FA;
    border-color: #D9E5EC;
}}
QFrame#SelectedCompetencyCard {{
    background-color: {COLOR_SURFACE};
    border: 1px solid #D6E3EC;
    border-radius: 11px;
}}
QFrame#SelectedCompetencyCard[historical="true"] {{
    background-color: #FFFAF5;
    border-color: #E9E1D6;
}}
QLabel#PrototypeBadge {{
    color: {COLOR_NAVY};
    background-color: {COLOR_BLUE_SOFT};
    border-radius: 8px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#HistoricalBadge {{
    color: #8B5A2B;
    background-color: #FDF0E3;
    border: 1px solid #F0D9BE;
    border-radius: 8px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#Avatar {{
    color: white;
    background-color: {COLOR_BLUE};
    border-radius: 24px;
    font-size: 16px;
    font-weight: 700;
}}
QPushButton#HierarchyToggle {{
    background-color: transparent;
    border: none;
    border-radius: 7px;
    color: {COLOR_NAVY};
    padding: 7px 5px;
    text-align: left;
    font-weight: 600;
}}
QPushButton#HierarchyToggle:hover {{
    background-color: #EEF6FB;
}}
QPushButton#HierarchyToggle:focus {{
    border: 1px solid {COLOR_BLUE};
}}
QPushButton#AddCompetencyButton {{
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
    border-radius: 8px;
}}
QPushButton#RemoveCompetencyButton {{
    background-color: #F7FAFC;
    border: 1px solid #D7E3EC;
    color: {COLOR_TEXT_MUTED};
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    border-radius: 8px;
    padding: 2px;
}}
QPushButton#RemoveCompetencyButton:hover {{
    background-color: #FFF2F2;
    border-color: #EFB9B9;
    color: #9F2525;
}}
QPushButton#RemoveCompetencyButton:focus {{
    border: 2px solid {COLOR_BLUE};
}}
QPushButton#RatingChip {{
    background-color: #F7FAFC;
    border: 1px solid #D2E0EA;
    border-radius: 7px;
    color: #38546B;
    min-height: 27px;
    padding: 3px 7px;
    font-size: 11px;
    font-weight: 600;
}}
QPushButton#RatingChip:hover {{
    background-color: #EEF6FB;
    border-color: #ABC7DB;
}}
QPushButton#RatingChip:checked {{
    background-color: {COLOR_BLUE};
    border-color: {COLOR_BLUE};
    color: #FFFFFF;
}}
QPushButton#RatingChip:focus {{
    border: 2px solid {COLOR_NAVY};
}}
QPushButton#AttachmentButton {{
    border-style: dashed;
    min-height: 30px;
    padding: 5px 9px;
}}
QLabel#DemoStatus {{
    color: {COLOR_GREEN};
    background-color: #ECFDF3;
    border: 1px solid #B7E4C7;
    border-radius: 8px;
    padding: 7px 9px;
}}
QScrollArea#PrototypeScroll {{
    background-color: #F8FBFD;
    border: 1px solid #E0EAF1;
    border-radius: 10px;
}}
QWidget#PrototypeScrollContent {{
    background-color: #F8FBFD;
}}
QSplitter::handle {{
    background-color: transparent;
    width: 10px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #C5D5E1;
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


class CollapsibleSection(QWidget):
    """Small disclosure section used for areas and topics in the demo catalog."""

    def __init__(self, title: str, *, expanded: bool, level: int = 0) -> None:
        super().__init__()
        self._title = title
        self._expanded = expanded
        layout = QVBoxLayout(self)
        layout.setContentsMargins(level * 12, 0, 0, 0)
        layout.setSpacing(3)

        self.toggle = QPushButton()
        self.toggle.setObjectName("HierarchyToggle")
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.clicked.connect(self._toggle)
        if level:
            self.toggle.setStyleSheet("font-weight: 500; color: #38546B;")
        layout.addWidget(self.toggle)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(12, 1, 0, 6)
        self.content_layout.setSpacing(5)
        layout.addWidget(self.content)
        self._sync_state()

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._sync_state()

    def _sync_state(self) -> None:
        self.toggle.setText(f"{'▾' if self._expanded else '▸'}  {self._title}")
        self.toggle.setAccessibleName(
            f"{self._title}, {'geöffnet' if self._expanded else 'geschlossen'}"
        )
        self.content.setVisible(self._expanded)


class CompetencyCatalogTile(QFrame):
    """A complete, focusable catalog tile that adds one demo competency."""

    def __init__(
        self, competency: DemoCompetency, is_selected: bool, on_add: object
    ) -> None:
        super().__init__()
        self._is_selected = is_selected
        self._on_add = on_add
        self.setObjectName("CatalogCompetencyTile")
        self.setProperty("is_selected", "true" if is_selected else "false")
        self.setAccessibleName(
            f"{competency.text}, "
            f"{'bereits ausgewählt' if is_selected else 'zur Auswahl hinzufügen'}"
        )
        if is_selected:
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        else:
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def mouseReleaseEvent(self, event: object) -> None:
        if (
            not self._is_selected
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self._on_add()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: object) -> None:
        if not self._is_selected and event.key() in {
            Qt.Key.Key_Space,
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        }:
            self._on_add()
            event.accept()
            return
        super().keyPressEvent(event)


class RatingSelector(QWidget):
    """Keep all rating labels readable at both prototype target widths."""

    def __init__(
        self,
        competency_id: str,
        selected: SelectedCompetency,
        on_change: object,
    ) -> None:
        super().__init__()
        self._columns = 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(5)
        self._grid.setVerticalSpacing(4)
        self._buttons: list[QPushButton] = []
        group = QButtonGroup(self)
        group.setExclusive(True)

        for option in RATING_OPTIONS:
            chip = QPushButton(option)
            chip.setObjectName("RatingChip")
            chip.setCheckable(True)
            chip.setChecked(option == selected.rating)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setToolTip(option)
            chip.setAccessibleName(f"{option} für diese Kompetenz")
            chip.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            chip.clicked.connect(
                lambda _checked=False, value=option, item_id=competency_id: on_change(
                    item_id, value
                )
            )
            group.addButton(chip)
            self._buttons.append(chip)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        columns = 4 if self.width() >= 510 else 2
        if columns == self._columns:
            return
        self._columns = columns
        while self._grid.count():
            self._grid.takeAt(0)
        for index, chip in enumerate(self._buttons):
            self._grid.addWidget(chip, index // columns, index % columns)


class ObservationWorkspacePrototype(QMainWindow):
    """Static, non-persistent three-zone observation workspace prototype."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sprint 5B4 · Beobachtungs-Arbeitsfläche · UX-Prototyp")
        self.resize(1320, 820)
        self.setMinimumSize(1100, 700)
        self.selected: dict[str, SelectedCompetency] = {
            "DEU-03": SelectedCompetency(DEMO_CATALOG["Deutsch"][2], RATING_OPTIONS[0]),
            "MAT-01": SelectedCompetency(DEMO_CATALOG["Mathematik"][0], RATING_OPTIONS[1]),
            "HIST-01": SelectedCompetency(HISTORICAL_COMPETENCY, RATING_OPTIONS[2]),
        }
        self.attachment_count = 1
        self.catalog_add_buttons: dict[str, QPushButton] = {}
        self._build()

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("PrototypeRoot")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 16, 18, 18)
        root_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(1)
        title = QLabel("Beobachtung erfassen")
        set_label_style(title, "screen_title")
        subtitle = QLabel("Arbeitsfläche für eine fokussierte, kompetenzbezogene Dokumentation")
        set_label_style(subtitle, "muted")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header.addLayout(title_stack)
        header.addStretch(1)
        badge = QLabel("UX-PROTOTYP · KEINE PERSISTENZ")
        badge.setObjectName("PrototypeBadge")
        header.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        root_layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)
        splitter.addWidget(self._build_context_zone())
        splitter.addWidget(self._build_competency_zone())
        splitter.addWidget(self._build_observation_zone())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([250, 704, 310])
        root_layout.addWidget(splitter, 1)

    def _build_context_zone(self) -> QWidget:
        zone = self._zone("Kontext", "Kind und Katalogfilter")
        zone.setMinimumWidth(225)
        zone.setMaximumWidth(290)
        layout = zone.layout()

        student_card = QFrame()
        student_card.setObjectName("PrototypeSubtleCard")
        student_layout = QVBoxLayout(student_card)
        student_layout.setContentsMargins(12, 12, 12, 12)
        student_layout.setSpacing(7)
        avatar = QLabel("ML")
        avatar.setObjectName("Avatar")
        avatar.setFixedSize(48, 48)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        student_layout.addWidget(avatar)
        name = QLabel("Mila Lorenz")
        name.setFont(QFont(name.font().family(), 14, QFont.Weight.DemiBold))
        student_layout.addWidget(name)
        detail = QLabel("Stammgruppe Sonnenblume\nKurs 4 · Blau")
        detail.setWordWrap(True)
        set_label_style(detail, "muted")
        student_layout.addWidget(detail)
        layout.addWidget(student_card)

        layout.addSpacing(5)
        layout.addWidget(self._field_label("Fach · Katalogfilter"))
        self.subject_select = QComboBox()
        self.subject_select.addItems(DEMO_CATALOG.keys())
        self.subject_select.currentTextChanged.connect(self._refresh_catalog)
        layout.addWidget(self.subject_select)

        layout.addWidget(self._field_label("Beobachtungskontext"))
        context_select = QComboBox()
        context_select.addItems(
            ("Freiarbeit", "Fachunterricht", "Projektzeit", "Kleingruppe")
        )
        layout.addWidget(context_select)

        context_hint = QLabel(
            "Der Fachwechsel filtert nur den Katalog. Bereits ausgewählte Kompetenzen bleiben erhalten."
        )
        context_hint.setWordWrap(True)
        context_hint.setStyleSheet("color: #536B7D; font-size: 12px;")
        layout.addWidget(context_hint)
        layout.addStretch(1)
        return zone

    def _build_competency_zone(self) -> QWidget:
        zone = QFrame()
        zone.setObjectName("PrototypeZone")
        zone.setMinimumWidth(480)
        layout = QVBoxLayout(zone)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        selected_header = QHBoxLayout()
        selected_header.addWidget(self._section_title("Ausgewählte Kompetenzen"))
        selected_header.addStretch(1)
        self.selection_count = QLabel()
        self.selection_count.setStyleSheet("color: #536B7D; font-size: 12px;")
        selected_header.addWidget(self.selection_count)
        layout.addLayout(selected_header)

        self.selected_scroll = QScrollArea()
        self.selected_scroll.setObjectName("PrototypeScroll")
        self.selected_scroll.setWidgetResizable(True)
        self.selected_scroll.setMinimumHeight(250)
        self.selected_scroll.setMaximumHeight(320)
        self.selected_content = QWidget()
        self.selected_content.setObjectName("PrototypeScrollContent")
        self.selected_layout = QVBoxLayout(self.selected_content)
        self.selected_layout.setContentsMargins(0, 0, 4, 0)
        self.selected_layout.setSpacing(7)
        self.selected_scroll.setWidget(self.selected_content)
        layout.addWidget(self.selected_scroll, 0)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color: {COLOR_BORDER};")
        layout.addWidget(divider)

        catalog_header = QHBoxLayout()
        catalog_title_stack = QVBoxLayout()
        catalog_title_stack.setSpacing(1)
        catalog_title_stack.addWidget(self._section_title("Kompetenzkatalog"))
        self.catalog_hint = QLabel()
        self.catalog_hint.setStyleSheet("color: #536B7D; font-size: 12px;")
        catalog_title_stack.addWidget(self.catalog_hint)
        catalog_header.addLayout(catalog_title_stack)
        catalog_header.addStretch(1)
        catalog_header.addWidget(QLabel("＋ nur hinzufügen"))
        layout.addLayout(catalog_header)

        self.catalog_scroll = QScrollArea()
        self.catalog_scroll.setObjectName("PrototypeScroll")
        self.catalog_scroll.setWidgetResizable(True)
        self.catalog_content = QWidget()
        self.catalog_content.setObjectName("PrototypeScrollContent")
        self.catalog_layout = QVBoxLayout(self.catalog_content)
        self.catalog_layout.setContentsMargins(0, 0, 4, 0)
        self.catalog_layout.setSpacing(6)
        self.catalog_scroll.setWidget(self.catalog_content)
        layout.addWidget(self.catalog_scroll, 1)

        self._refresh_selected()
        self._refresh_catalog(self.subject_select.currentText())
        return zone

    def _build_observation_zone(self) -> QWidget:
        zone = self._zone("Beobachtung", "Notiz und Anhänge")
        zone.setMinimumWidth(285)
        zone.setMaximumWidth(350)
        layout = zone.layout()

        layout.addWidget(self._field_label("Datum"))
        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDate(QDate.currentDate())
        date_input.setDisplayFormat("dd.MM.yyyy")
        layout.addWidget(date_input)

        layout.addWidget(self._field_label("Notiz"))
        note_input = QTextEdit()
        note_input.setPlaceholderText("Was war konkret zu beobachten?")
        note_input.setPlainText(
            "Mila erklärte ihrer Partnerin den gewählten Rechenweg ruhig und griff eine Rückfrage direkt auf."
        )
        note_input.setMinimumHeight(165)
        layout.addWidget(note_input, 1)

        layout.addWidget(self._field_label("Dokumente & Medien"))
        attachment_card = QFrame()
        attachment_card.setObjectName("PrototypeSubtleCard")
        attachment_layout = QHBoxLayout(attachment_card)
        attachment_layout.setContentsMargins(9, 7, 9, 7)
        attachment_layout.setSpacing(8)
        attachment_icon = QLabel("▣")
        attachment_icon.setStyleSheet(f"color: {COLOR_BLUE}; font-size: 16px;")
        attachment_layout.addWidget(attachment_icon, 0, Qt.AlignmentFlag.AlignTop)
        attachment_stack = QVBoxLayout()
        attachment_stack.setSpacing(1)
        attachment_name = QLabel("rechenweg_foto.jpg")
        attachment_name.setWordWrap(True)
        attachment_stack.addWidget(attachment_name)
        attachment_meta = QLabel("Foto · 1,8 MB · Demo")
        attachment_meta.setStyleSheet("color: #536B7D; font-size: 12px;")
        attachment_stack.addWidget(attachment_meta)
        attachment_layout.addLayout(attachment_stack, 1)
        layout.addWidget(attachment_card)

        add_attachment = QPushButton("Datei hinzufügen")
        add_attachment.setObjectName("AttachmentButton")
        add_attachment.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        )
        add_attachment.clicked.connect(self._demo_add_attachment)
        layout.addWidget(add_attachment)

        self.save_status = QLabel("Demo: Speichern verändert keine Daten.")
        self.save_status.setWordWrap(True)
        self.save_status.setStyleSheet("color: #536B7D; font-size: 12px;")
        layout.addWidget(self.save_status)

        save_button = QPushButton("Beobachtung speichern")
        save_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        )
        save_button.setMinimumHeight(42)
        save_button.setStyleSheet(PRIMARY_BUTTON_STYLESHEET)
        save_button.clicked.connect(self._demo_save)
        layout.addWidget(save_button)
        return zone

    def _zone(self, title: str, subtitle: str) -> QFrame:
        zone = QFrame()
        zone.setObjectName("PrototypeZone")
        layout = QVBoxLayout(zone)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        layout.addWidget(self._section_title(title))
        subtitle_label = QLabel(subtitle)
        set_label_style(subtitle_label, "small")
        layout.addWidget(subtitle_label)
        return zone

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        set_label_style(label, "section_title")
        return label

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        set_label_style(label, "field_label")
        return label

    def _refresh_selected(self) -> None:
        self._clear_layout(self.selected_layout)
        self.selection_count.setText(f"{len(self.selected)} ausgewählt")
        if not self.selected:
            empty = QFrame()
            empty.setObjectName("PrototypeSubtleCard")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(14, 14, 14, 14)
            hint = QLabel("Noch keine Kompetenz ausgewählt")
            set_label_style(hint, "muted")
            empty_layout.addWidget(hint)
            self.selected_layout.addWidget(empty)
        else:
            for competency_id, selected in self.selected.items():
                self.selected_layout.addWidget(
                    self._selected_competency_card(competency_id, selected)
                )
        self.selected_layout.addStretch(1)

    def _selected_competency_card(
        self, competency_id: str, selected: SelectedCompetency
    ) -> QFrame:
        competency = selected.competency
        card = QFrame()
        card.setObjectName("SelectedCompetencyCard")
        card.setProperty("historical", "true" if competency.historical else "false")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(9, 6, 8, 6)
        layout.setSpacing(3)

        meta_row = QHBoxLayout()
        meta = QLabel(
            f"{competency.subject}  ·  {competency.learning_area}  ·  {competency.topic}"
        )
        meta.setStyleSheet("color: #50687B; font-size: 10px; font-weight: 500;")
        meta.setWordWrap(True)
        meta_row.addWidget(meta, 1)
        if competency.historical:
            historical = QLabel("Historischer Bestand")
            historical.setObjectName("HistoricalBadge")
            historical.setToolTip(
                "Diese Kompetenz stammt aus einer bestehenden Beobachtung und ist nicht mehr Teil des aktuellen Katalogs."
            )
            meta_row.addWidget(historical)
        layout.addLayout(meta_row)

        text = QLabel(competency.text)
        text.setWordWrap(True)
        text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text.setStyleSheet("color: #243644; font-size: 14px; font-weight: 500;")
        text.setMaximumHeight(38)
        text.setToolTip(competency.text)
        layout.addWidget(text)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        action_row.addWidget(self._rating_selector(competency_id, selected), 1)

        remove = QPushButton()
        remove.setObjectName("RemoveCompetencyButton")
        remove.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        )
        remove.setToolTip("Aus Auswahl entfernen")
        remove.setAccessibleName("Kompetenz aus Auswahl entfernen")
        remove.clicked.connect(lambda _checked=False, item_id=competency_id: self._remove(item_id))
        action_row.addWidget(remove)
        layout.addLayout(action_row)
        return card

    def _rating_selector(
        self, competency_id: str, selected: SelectedCompetency
    ) -> QWidget:
        """Return an exclusive, keyboard-focusable four-value rating selector."""
        selector = RatingSelector(competency_id, selected, self._change_rating)
        selector.setAccessibleName(f"Bewertung für {selected.competency.text}")
        return selector

    def _refresh_catalog(
        self, subject: str, *, preserve_scroll_position: bool = False
    ) -> None:
        if not hasattr(self, "catalog_layout"):
            return
        previous_scroll_position = self.catalog_scroll.verticalScrollBar().value()
        self._clear_layout(self.catalog_layout)
        self.catalog_add_buttons.clear()
        self.catalog_hint.setText(
            f"{subject} · Kompetenzbereich → Thema → Kompetenz"
        )
        grouped: dict[str, dict[str, list[DemoCompetency]]] = {}
        for competency in DEMO_CATALOG[subject]:
            grouped.setdefault(competency.learning_area, {}).setdefault(
                competency.topic, []
            ).append(competency)

        for area, topics in grouped.items():
            area_section = CollapsibleSection(area, expanded=False, level=0)
            for topic, competencies in topics.items():
                topic_section = CollapsibleSection(topic, expanded=False, level=1)
                for competency in competencies:
                    topic_section.content_layout.addWidget(
                        self._catalog_competency_row(competency)
                    )
                area_section.content_layout.addWidget(topic_section)
            self.catalog_layout.addWidget(area_section)
        self.catalog_layout.addStretch(1)
        if preserve_scroll_position:
            QTimer.singleShot(
                0,
                lambda: self.catalog_scroll.verticalScrollBar().setValue(
                    min(
                        previous_scroll_position,
                        self.catalog_scroll.verticalScrollBar().maximum(),
                    )
                ),
            )
        else:
            self.catalog_scroll.verticalScrollBar().setValue(0)

    def _catalog_competency_row(self, competency: DemoCompetency) -> QFrame:
        is_selected = competency.competency_id in self.selected
        row = CompetencyCatalogTile(
            competency, is_selected, lambda: self._add(competency)
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(9, 7, 7, 7)
        layout.setSpacing(8)
        text = QLabel(competency.text)
        text.setWordWrap(True)
        text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text.setStyleSheet("color: #2F4353; font-size: 13px;")
        text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(text, 1)
        add = QPushButton("+")
        add.setObjectName("AddCompetencyButton")
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        add.setEnabled(not is_selected)
        if is_selected:
            add.setText("✓")
        add.setToolTip(
            "Bereits ausgewählt"
            if is_selected
            else "Zur Auswahl hinzufügen"
        )
        add.setAccessibleName(
            "Bereits ausgewählt" if is_selected else "Kompetenz zur Auswahl hinzufügen"
        )
        self.catalog_add_buttons[competency.competency_id] = add
        add.clicked.connect(
            lambda _checked=False, item=competency: self._add(item)
        )
        layout.addWidget(add, 0, Qt.AlignmentFlag.AlignTop)
        return row

    def _add(self, competency: DemoCompetency) -> None:
        if competency.competency_id in self.selected:
            return
        new_selection = SelectedCompetency(competency, RATING_OPTIONS[1])
        self.selected = {competency.competency_id: new_selection, **self.selected}
        self._refresh_selected()
        self._refresh_catalog(
            self.subject_select.currentText(), preserve_scroll_position=True
        )
        QTimer.singleShot(0, self._scroll_selected_to_top)
        QTimer.singleShot(
            0, lambda: self._focus_catalog_after_add(competency.competency_id)
        )

    def _remove(self, competency_id: str) -> None:
        self.selected.pop(competency_id, None)
        self._refresh_selected()
        self._refresh_catalog(
            self.subject_select.currentText(), preserve_scroll_position=True
        )

    def _change_rating(self, competency_id: str, rating: str) -> None:
        selected = self.selected.get(competency_id)
        if selected is not None:
            selected.rating = rating

    def _scroll_selected_to_top(self) -> None:
        """Reveal the latest addition without moving the surrounding workspace."""
        self.selected_scroll.verticalScrollBar().setValue(
            self.selected_scroll.verticalScrollBar().minimum()
        )

    def _focus_catalog_after_add(self, added_competency_id: str) -> None:
        """Keep keyboard work in the catalog after its add button was rebuilt."""
        button_ids = list(self.catalog_add_buttons)
        try:
            start_index = button_ids.index(added_competency_id) + 1
        except ValueError:
            start_index = 0
        for competency_id in button_ids[start_index:] + button_ids[:start_index]:
            button = self.catalog_add_buttons[competency_id]
            if button.isEnabled():
                button.setFocus(Qt.FocusReason.OtherFocusReason)
                return
        self.catalog_scroll.setFocus(Qt.FocusReason.OtherFocusReason)

    def _demo_save(self) -> None:
        self.save_status.setObjectName("DemoStatus")
        self.save_status.setText("Demo bestätigt: Es wurden keine Daten gespeichert.")
        self.save_status.style().unpolish(self.save_status)
        self.save_status.style().polish(self.save_status)

    def _demo_add_attachment(self) -> None:
        self.attachment_count += 1
        self.save_status.setText(
            f"Demo-Anhang {self.attachment_count} vorgemerkt · keine Datei ausgewählt."
        )

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                ObservationWorkspacePrototype._clear_layout(child_layout)


def main() -> int:
    """Launch the isolated Sprint 5B1 prototype."""
    app = QApplication(sys.argv)
    apply_app_theme(app)
    app.setStyleSheet(app.styleSheet() + PROTOTYPE_STYLESHEET)
    window = ObservationWorkspacePrototype()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
