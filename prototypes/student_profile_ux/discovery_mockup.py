"""Isolated PySide6 mockup for evidence-led competency development chapters."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


NAVY = "#17384E"
BLUE = "#2F7096"
INK = "#243942"
MUTED = "#617780"
LINE = "#D8E4E7"
BACKGROUND = "#EAF1F2"
STYLE = f"""
QMainWindow, QWidget#Root {{ background: {BACKGROUND}; color: {INK}; }}
QFrame#DiscoveryBar {{ background: {NAVY}; border: none; }}
QFrame#ProfileHeader, QFrame#Card {{ background: white; border: 1px solid {LINE}; border-radius: 16px; }}
QFrame#DetailHeader {{ background: #EEF6F6; border: 1px solid #CFE1E2; border-radius: 13px; }}
QFrame#EventCard {{ background: #FAFCFC; border: 1px solid #DEE8EA; border-radius: 12px; }}
QFrame#Transition {{ background: #F0F6F7; border: 1px solid #D6E5E7; border-radius: 10px; }}
QFrame#Navigation {{ background: #F7FAFA; border: 1px solid {LINE}; border-radius: 12px; }}
QLabel#BarEyebrow {{ color: #A8D8D5; font-size: 10px; font-weight: 700; letter-spacing: 1px; }}
QLabel#BarTitle {{ color: white; font-size: 16px; font-weight: 700; }}
QLabel#ProfileName {{ color: {NAVY}; font-size: 24px; font-weight: 700; }}
QLabel#PageTitle {{ color: {NAVY}; font-size: 21px; font-weight: 700; }}
QLabel#SectionTitle {{ color: {NAVY}; font-size: 15px; font-weight: 700; }}
QLabel#CardTitle {{ color: {NAVY}; font-size: 13px; font-weight: 700; }}
QLabel#Body {{ color: {INK}; font-size: 12px; }}
QLabel#Muted {{ color: {MUTED}; font-size: 11px; }}
QLabel#Eyebrow {{ color: {BLUE}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px; }}
QLabel#Badge {{ color: #365966; background: #E9F1F3; border: 1px solid #D4E2E5; border-radius: 9px; padding: 3px 8px; font-size: 10px; font-weight: 650; }}
QLabel#StatusBadge {{ color: #285B60; background: #DFF0EE; border: 1px solid #C3DEDB; border-radius: 10px; padding: 5px 10px; font-size: 11px; font-weight: 700; }}
QPushButton {{ background: white; color: {NAVY}; border: 1px solid #BDD0D6; border-radius: 9px; padding: 8px 13px; min-height: 20px; font-weight: 600; }}
QPushButton:hover {{ background: #EEF5F6; border-color: #98B6C0; }}
QPushButton:focus {{ border: 2px solid {BLUE}; padding: 7px 12px; }}
QPushButton[role="primary"] {{ background: {BLUE}; color: white; border-color: {BLUE}; padding: 9px 15px; }}
QPushButton[role="quiet"] {{ background: transparent; border-color: transparent; color: #426271; }}
QPushButton[nav="true"] {{ background: transparent; border-color: transparent; color: #506A74; padding: 8px 12px; }}
QPushButton[nav="true"]:checked {{ background: white; color: {NAVY}; border: 1px solid #CBDADD; }}
QPushButton#CompetencyChoice {{ text-align: left; background: #F8FBFB; border: 1px solid #DDE8EA; border-radius: 11px; padding: 12px; min-height: 64px; }}
QPushButton#CompetencyChoice:checked {{ background: #E8F2F3; border: 2px solid {BLUE}; padding: 11px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #B8C9CE; border-radius: 4px; min-height: 34px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


@dataclass(frozen=True)
class EvidenceEvent:
    date: str
    source: str
    context: str
    status: str
    note: str


@dataclass(frozen=True)
class CompetencyStory:
    key: str
    short_label: str
    full_text: str
    subject: str
    topic: str
    events: tuple[EvidenceEvent, ...]


STORIES = (
    CompetencyStory(
        key="time",
        short_label="Uhrzeiten ablesen",
        full_text="Volle Stunden und Minuten an analogen sowie digitalen Uhren ablesen",
        subject="Mathematik",
        topic="Zeit",
        events=(
            EvidenceEvent(
                "15. September 2025",
                "Beobachtung",
                "Lernzeit",
                "- in Entwicklung",
                "Mara liest volle Stunden sicher und orientiert sich bei Minuten noch an Hilfsmarkierungen.",
            ),
            EvidenceEvent(
                "18. November 2025",
                "Beobachtung",
                "Partnerarbeit",
                "+ erreicht",
                "Analoge Uhrzeiten werden selbstständig gelesen und passend digital notiert.",
            ),
            EvidenceEvent(
                "4. Februar 2026",
                "Bestätigung",
                "Lernzielkontrolle",
                "+ erreicht",
                "Der dokumentierte Stand wurde in einem neuen Kontext erneut bestätigt.",
            ),
            EvidenceEvent(
                "13. Juli 2026",
                "Bestätigung",
                "Alltagssituation",
                "++ sicher erreicht",
                "Mara liest minutengenaue Uhrzeiten sicher und erklärt ihre Orientierung an der Uhr.",
            ),
        ),
    ),
    CompetencyStory(
        key="reading",
        short_label="Informationen auffinden",
        full_text="Zentrale Informationen in längeren Sachtexten auffinden und benennen",
        subject="Deutsch",
        topic="Lesen",
        events=(
            EvidenceEvent(
                "22. September 2025",
                "Beobachtung",
                "Lesezeit",
                "-- Unterstützungsbedarf",
                "Zentrale Textstellen werden mit gezielten Fragen gemeinsam gefunden.",
            ),
            EvidenceEvent(
                "14. Januar 2026",
                "Beobachtung",
                "Sachtextarbeit",
                "- in Entwicklung",
                "Mara markiert wichtige Informationen, benötigt beim Zusammenfassen noch Impulse.",
            ),
            EvidenceEvent(
                "10. Juli 2026",
                "Bestätigung",
                "Leseübung",
                "+ erreicht",
                "Zentrale Informationen werden selbstständig ausgewählt und knapp benannt.",
            ),
        ),
    ),
    CompetencyStory(
        key="experiment",
        short_label="Versuchsaufbau beschreiben",
        full_text="Einen Versuchsaufbau nachvollziehbar und fachsprachlich angemessen beschreiben",
        subject="Sachunterricht",
        topic="Natur und Umwelt",
        events=(
            EvidenceEvent(
                "15. April 2026",
                "Beobachtung",
                "Forscherzeit",
                "-- Unterstützungsbedarf",
                "Einzelne Materialien werden benannt; die Reihenfolge wird noch gemeinsam geklärt.",
            ),
            EvidenceEvent(
                "2. Juli 2026",
                "Beobachtung",
                "Präsentation",
                "- in Entwicklung",
                "Mara beschreibt Aufbau und Reihenfolge in kurzen, verständlichen Schritten.",
            ),
        ),
    ),
)


def label(text: str, role: str = "Body", *, wrap: bool = True) -> QLabel:
    item = QLabel(text)
    item.setObjectName(role)
    item.setWordWrap(wrap)
    return item


def badge(text: str, *, status: bool = False) -> QLabel:
    item = label(text, "StatusBadge" if status else "Badge", wrap=False)
    item.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return item


def button(text: str, role: str = "secondary") -> QPushButton:
    item = QPushButton(text)
    item.setProperty("role", role)
    item.setCursor(Qt.CursorShape.PointingHandCursor)
    return item


def card(role: str = "Card") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName(role)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(15, 13, 15, 13)
    layout.setSpacing(7)
    return frame, layout


def clear(layout: QVBoxLayout | QHBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        nested = item.layout()
        if widget is not None:
            widget.deleteLater()
        elif nested is not None:
            clear(nested)  # type: ignore[arg-type]


class DevelopmentDiscoveryMockup(QMainWindow):
    def __init__(self, *, width: int = 1400, height: int = 900) -> None:
        super().__init__()
        self.story = STORIES[0]
        self._compact = width < 1250 or height < 820
        self.resize(width, height)
        self.setMinimumSize(1100, 720)
        self.setWindowTitle("UX Discovery · Beobachtungskapitel")
        self._build()

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._discovery_bar())

        workspace = QWidget()
        workspace.setObjectName("Root")
        self.workspace_layout = QVBoxLayout(workspace)
        self.workspace_layout.setContentsMargins(18, 16, 18, 12)
        self.workspace_layout.setSpacing(12)
        self.workspace_layout.addWidget(self._profile_header())
        self.workspace_layout.addWidget(self._navigation())
        self.workspace_layout.addWidget(self._content(), 1)
        self.footer = label(
            "Statische Beispieldaten · keine Speicherung · keine Produktnavigation",
            "Muted",
            wrap=False,
        )
        self.workspace_layout.addWidget(self.footer)
        outer.addWidget(workspace, 1)
        self.setCentralWidget(root)

    def _discovery_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("DiscoveryBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 9, 18, 9)
        title = QVBoxLayout()
        title.setSpacing(1)
        title.addWidget(label("UX DISCOVERY", "BarEyebrow", wrap=False))
        title.addWidget(label("Kompetenzentwicklung neu gedacht", "BarTitle", wrap=False))
        layout.addLayout(title)
        layout.addStretch(1)
        layout.addWidget(badge("Gewähltes Konzept · Beobachtungskapitel"))
        return frame

    def _profile_header(self) -> QFrame:
        if self._compact:
            return self._compact_profile_header()
        frame, layout = card("ProfileHeader")
        layout.setContentsMargins(18, 12, 18, 13)
        top = QHBoxLayout()
        back = button("Zurück zur Schülerliste", "quiet")
        back.clicked.connect(lambda: self._feedback("Prototyp: zurück zur Schülerliste."))
        top.addWidget(back)
        top.addStretch(1)
        top.addWidget(badge("UX-Vorlage"))
        layout.addLayout(top)

        row = QHBoxLayout()
        identity = QVBoxLayout()
        identity.setSpacing(3)
        identity.addWidget(label("Mara Beispielkind", "ProfileName"))
        identity.addWidget(label(
            "Stammgruppe Sonnenbogen · Kurs 3 · Mathematik 3 · Deutsch 3",
            "Muted",
        ))
        row.addLayout(identity, 1)
        observation = button("Beobachtung erfassen", "primary")
        observation.setAccessibleName("Neue Beobachtung für Mara Beispielkind erfassen")
        observation.clicked.connect(lambda: self._feedback(
            "Prototyp: zentralen Beobachtungsdialog öffnen."
        ))
        row.addWidget(observation)
        row.addWidget(button("Weitere Aktionen", "quiet"))
        layout.addLayout(row)
        return frame

    def _compact_profile_header(self) -> QFrame:
        frame, layout = card("ProfileHeader")
        layout.setContentsMargins(14, 9, 14, 9)
        row = QHBoxLayout()
        row.setSpacing(10)
        back = button("Schülerliste", "quiet")
        back.clicked.connect(lambda: self._feedback("Prototyp: zurück zur Schülerliste."))
        row.addWidget(back)
        identity = QVBoxLayout()
        identity.setSpacing(2)
        identity.addWidget(label("Mara Beispielkind", "ProfileName"))
        identity.addWidget(label(
            "Sonnenbogen · Kurs 3 · Mathematik 3 · Deutsch 3",
            "Muted",
            wrap=False,
        ))
        row.addLayout(identity, 1)
        observation = button("Beobachtung erfassen", "primary")
        observation.setAccessibleName("Neue Beobachtung für Mara Beispielkind erfassen")
        observation.clicked.connect(lambda: self._feedback(
            "Prototyp: zentralen Beobachtungsdialog öffnen."
        ))
        row.addWidget(observation)
        row.addWidget(button("Weitere Aktionen", "quiet"))
        layout.addLayout(row)
        return frame

    def _navigation(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Navigation")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(2)
        group = QButtonGroup(frame)
        group.setExclusive(True)
        for text in ("Überblick", "Kompetenzen", "Beobachtungen", "Dokumente", "Entwicklung"):
            item = button(text, "quiet")
            item.setProperty("nav", True)
            item.setCheckable(True)
            item.setChecked(text == "Entwicklung")
            group.addButton(item)
            layout.addWidget(item)
        layout.addStretch(1)
        return frame

    def _content(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("Root")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 2, 8, 12)
        layout.setSpacing(10)
        layout.addWidget(label("Kompetenzentwicklung", "PageTitle"))
        layout.addWidget(label(
            "Aktueller dokumentierter Stand und die realen Ereignisse, die zu ihm geführt haben.",
            "Muted",
        ))

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._competency_list(), 0)
        self.detail = QFrame()
        self.detail.setObjectName("Card")
        self.detail_layout = QVBoxLayout(self.detail)
        self.detail_layout.setContentsMargins(16, 14, 16, 16)
        self.detail_layout.setSpacing(9)
        self._render_story()
        body.addWidget(self.detail, 1)
        layout.addLayout(body)
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _competency_list(self) -> QFrame:
        frame, layout = card("Card")
        frame.setFixedWidth(294)
        layout.addWidget(label("KOMPETENZEN", "Eyebrow", wrap=False))
        layout.addWidget(label("Mit dokumentierten Ereignissen", "SectionTitle"))
        layout.addWidget(label(
            "Eine Kompetenz auswählen, um ihre Beobachtungskapitel zu lesen.",
            "Muted",
        ))
        group = QButtonGroup(frame)
        group.setExclusive(True)
        for story in STORIES:
            latest = story.events[-1]
            item = QPushButton(
                f"{story.short_label}\n{latest.status} · {len(story.events)} Ereignisse"
            )
            item.setObjectName("CompetencyChoice")
            item.setCheckable(True)
            item.setChecked(story.key == self.story.key)
            item.setAccessibleName(
                f"{story.short_label}, aktuell {latest.status}, {len(story.events)} Ereignisse"
            )
            item.setToolTip(story.full_text)
            item.clicked.connect(
                lambda _checked=False, selected=story: self._select_story(selected)
            )
            group.addButton(item)
            layout.addWidget(item)
        layout.addStretch(1)
        all_button = button("Alle Kompetenzen ansehen", "quiet")
        all_button.clicked.connect(lambda: self._feedback(
            "Prototyp: vollständige Kompetenzübersicht öffnen."
        ))
        layout.addWidget(all_button)
        return frame

    def _select_story(self, story: CompetencyStory) -> None:
        self.story = story
        self._render_story()
        self._feedback(f"Ausgewählt: {story.short_label}")

    def _render_story(self) -> None:
        clear(self.detail_layout)
        self.detail_layout.addWidget(self._story_header())
        heading = QHBoxLayout()
        heading.addWidget(label("So entstand der dokumentierte Stand", "SectionTitle"), 1)
        heading.addWidget(label("ältestes → neuestes Ereignis", "Muted", wrap=False))
        self.detail_layout.addLayout(heading)

        previous: EvidenceEvent | None = None
        for event in self.story.events:
            if previous is not None and previous.status != event.status:
                self.detail_layout.addWidget(self._transition(previous.status, event.status))
            self.detail_layout.addWidget(self._event_card(event))
            previous = event
        self.detail_layout.addStretch(1)

    def _story_header(self) -> QFrame:
        frame, layout = card("DetailHeader")
        top = QHBoxLayout()
        title = QVBoxLayout()
        title.setSpacing(3)
        title.addWidget(label(
            f"{self.story.subject} · {self.story.topic}",
            "Eyebrow",
            wrap=False,
        ))
        title.addWidget(label(self.story.short_label, "PageTitle"))
        title.addWidget(label(self.story.full_text, "Body"))
        top.addLayout(title, 1)
        latest = self.story.events[-1]
        status = QVBoxLayout()
        status.setSpacing(4)
        status.addWidget(label("AKTUELL DOKUMENTIERT", "Eyebrow", wrap=False))
        status.addWidget(badge(latest.status, status=True))
        status.addWidget(label(latest.date, "Muted", wrap=False))
        top.addLayout(status)
        layout.addLayout(top)
        meta = QHBoxLayout()
        meta.addWidget(badge(f"{len(self.story.events)} reale Ereignisse"))
        meta.addWidget(label(
            "Einzelne dokumentierte Ereignisse · keine kontinuierliche Messung",
            "Muted",
        ), 1)
        layout.addLayout(meta)
        return frame

    def _transition(self, before: str, after: str) -> QFrame:
        frame, layout = card("Transition")
        layout.setContentsMargins(12, 7, 12, 7)
        line = QHBoxLayout()
        line.addWidget(label("DOKUMENTIERTER STATUSWECHSEL", "Eyebrow", wrap=False))
        line.addStretch(1)
        line.addWidget(label(f"{before}  →  {after}", "CardTitle", wrap=False))
        layout.addLayout(line)
        return frame

    def _event_card(self, event: EvidenceEvent) -> QFrame:
        frame, layout = card("EventCard")
        layout.setContentsMargins(13, 10, 13, 10)
        top = QHBoxLayout()
        top.addWidget(label(event.date, "CardTitle", wrap=False))
        top.addWidget(badge(event.source))
        top.addWidget(label(event.context, "Muted"), 1)
        top.addWidget(badge(event.status, status=True))
        layout.addLayout(top)
        layout.addWidget(label(event.note, "Body"))
        return frame

    def _feedback(self, text: str) -> None:
        self.footer.setText(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--screenshot", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("UX Discovery · Beobachtungskapitel")
    app.setStyleSheet(STYLE)
    window = DevelopmentDiscoveryMockup(width=args.width, height=args.height)
    window.show()
    if args.screenshot is not None:
        target = args.screenshot.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        def capture() -> None:
            app.processEvents()
            if not window.grab().save(str(target)):
                raise RuntimeError(f"Screenshot konnte nicht gespeichert werden: {target}")
            app.quit()

        QTimer.singleShot(350, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
