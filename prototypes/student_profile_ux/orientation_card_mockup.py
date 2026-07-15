"""High-fidelity mockup for the compact learning-development orientation card."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from main import (
    APP_STYLE,
    BLUE,
    LINE,
    NAVY,
    StudentProfilePrototype,
    badge,
    make_button,
    make_card,
    text_label,
)


ORIENTATION_STYLE = APP_STYLE + f"""
QFrame#OrientationCard {{
    background: white;
    border: 1px solid {LINE};
    border-radius: 14px;
}}
QFrame#OrientationSummary {{
    background: #F1F6F7;
    border: 1px solid #D7E4E7;
    border-radius: 11px;
}}
QFrame#OrientationEntry {{
    background: #FAFCFC;
    border: 1px solid #DFE8EA;
    border-radius: 11px;
}}
QFrame#EvidenceStrip {{
    background: #F2F7F7;
    border: none;
    border-radius: 8px;
}}
QLabel#OrientationMetric {{
    color: {NAVY};
    font-size: 22px;
    font-weight: 700;
}}
QLabel#ChangeStatus {{
    color: {NAVY};
    font-size: 12px;
    font-weight: 700;
}}
QFrame#OrientationDivider {{
    background: {LINE};
    border: none;
    min-width: 1px;
    max-width: 1px;
}}
"""


@dataclass(frozen=True)
class LatestChange:
    competency: str
    subject: str
    new_status: str
    date: str
    event_type: str
    evidence: str


LATEST_CHANGES = (
    LatestChange(
        competency="Zeit lesen",
        subject="Mathematik · Zeit",
        new_status="Sicher bestätigt",
        date="12.07.2026",
        event_type="Beobachtung",
        evidence="Kann Viertelstunden sicher ablesen.",
    ),
    LatestChange(
        competency="Vorlesen",
        subject="Deutsch · Lesen",
        new_status="Erreicht",
        date="05.07.2026",
        event_type="Kompetenz bestätigt",
        evidence="Liest im Lesekreis flüssig und betont passende Stellen.",
    ),
    LatestChange(
        competency="Wasser im Alltag",
        subject="Sachunterricht · Natur und Umwelt",
        new_status="In Entwicklung",
        date="01.07.2026",
        event_type="Beobachtung",
        evidence="Nennt Beispiele für Wassernutzung und erklärt erste Zusammenhänge.",
    ),
)


class OrientationCardMockup(StudentProfilePrototype):
    """Variant A shell with one newly decided orientation card."""

    def __init__(self, *, width: int = 1400, height: int = 900) -> None:
        super().__init__(
            variant="a",
            scenario_key="well_documented",
            competency_card_variant="ring",
            width=width,
            height=height,
        )
        self.setWindowTitle("Schülerprofil · Lernentwicklung kompakt")

    def _prototype_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("PrototypeBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 9, 18, 9)
        title = QVBoxLayout()
        title.setSpacing(1)
        title.addWidget(text_label("HIGH-FIDELITY UX-PROTOTYP", "PrototypeEyebrow", wrap=False))
        title.addWidget(text_label("Schülerprofil · Lernentwicklung", "PrototypeTitle", wrap=False))
        layout.addLayout(title)
        layout.addStretch(1)
        layout.addWidget(badge("Neue Orientierungskarte"))
        return frame

    def _profile_header(self) -> QFrame:
        if self.width() >= 1250:
            return super()._profile_header()
        frame, layout = make_card("ProfileHeader")
        layout.setContentsMargins(14, 9, 14, 9)
        row = QHBoxLayout()
        row.setSpacing(10)
        back = make_button("Schülerliste", "quiet")
        back.clicked.connect(lambda: self._feedback(
            "Prototyp: zurück zur Schülerliste."
        ))
        row.addWidget(back)
        avatar = text_label("MB", "Avatar", wrap=False)
        avatar.setFixedSize(50, 50)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(avatar)
        identity = QVBoxLayout()
        identity.setSpacing(2)
        identity.addWidget(text_label("Mara Beispielkind", "ProfileName"))
        identity.addWidget(text_label(
            "Sonnenbogen · Kurs 3 · Mathematik 3 · Deutsch 3",
            "Muted",
            wrap=False,
        ))
        row.addLayout(identity, 1)
        row.addWidget(badge("Dokumentiert 16 / 21"))
        observation = make_button(
            "Beobachtung erfassen",
            "primary",
            "Neue Beobachtung für Mara Beispielkind erfassen",
        )
        observation.clicked.connect(lambda: self._feedback(
            "Prototyp: zentralen Beobachtungsdialog öffnen."
        ))
        row.addWidget(observation)
        row.addWidget(make_button("Weitere Aktionen", "quiet"))
        layout.addLayout(row)
        return frame

    def _development_card(self) -> QFrame:
        card, layout = make_card("OrientationCard")
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.addWidget(text_label("Lernentwicklung", "SectionTitle"), 1)
        header.addWidget(text_label(
            "Aktuell dokumentiert",
            "Muted",
            wrap=False,
        ))
        layout.addLayout(header)

        layout.addWidget(self._current_status_section())
        layout.addWidget(text_label("NEUESTE ENTWICKLUNG", "Eyebrow", wrap=False))
        for change in LATEST_CHANGES:
            layout.addWidget(self._change_entry(change))
        return card

    def _current_status_section(self) -> QFrame:
        frame, layout = make_card("OrientationSummary")
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(5)
        layout.addWidget(text_label(
            "AKTUELLER DOKUMENTIERTER STAND",
            "Eyebrow",
            wrap=False,
        ))
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(self._stat("16", "Kompetenzen sicher"), 1)
        row.addWidget(self._divider())
        row.addWidget(self._stat("5", "Kompetenzen in Entwicklung"), 1)
        row.addWidget(self._divider())
        row.addWidget(self._stat("2", "erste Beobachtungen"), 1)
        layout.addLayout(row)
        return frame

    @staticmethod
    def _stat(value: str, description: str) -> QWidget:
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
    def _divider() -> QFrame:
        divider = QFrame()
        divider.setObjectName("OrientationDivider")
        divider.setFixedHeight(34)
        return divider

    def _change_entry(self, change: LatestChange) -> QFrame:
        frame, layout = make_card("OrientationEntry")
        layout.setContentsMargins(11, 8, 11, 8)
        layout.setSpacing(5)

        top = QHBoxLayout()
        name = QVBoxLayout()
        name.setSpacing(1)
        name.addWidget(text_label(change.competency, "CardTitle"))
        name.addWidget(text_label(change.subject, "Muted"))
        top.addLayout(name, 1)
        status = QLabel(f"→ {change.new_status}")
        status.setObjectName("ChangeStatus")
        status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(status)
        top.addWidget(text_label(change.date, "Muted", wrap=False))
        layout.addLayout(top)

        evidence, evidence_layout = make_card("EvidenceStrip")
        evidence_layout.setContentsMargins(9, 5, 9, 5)
        evidence_layout.setSpacing(4)
        line = QHBoxLayout()
        line.setSpacing(7)
        line.addWidget(badge(change.event_type))
        quote = text_label(f"„{change.evidence}“", "Body")
        quote.setMaximumHeight(32)
        line.addWidget(quote, 1)
        evidence_layout.addLayout(line)
        layout.addWidget(evidence)
        return frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--screenshot", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Schülerprofil · Lernentwicklung kompakt")
    app.setStyleSheet(ORIENTATION_STYLE)
    window = OrientationCardMockup(width=args.width, height=args.height)
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
