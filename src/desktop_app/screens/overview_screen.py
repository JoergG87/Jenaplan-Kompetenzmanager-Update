"""Overview screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.view_models.student_view_model import GroupSummaryViewModel


class OverviewScreen(QWidget):
    """Start screen with lightweight group overview."""

    group_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.cards_layout = QGridLayout()
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Übersicht")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        subtitle = QLabel("Stammgruppen und Schülerbestand")
        subtitle.setStyleSheet("color: #555;")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(self.cards_layout)
        layout.addStretch()

    def set_groups(self, groups: tuple[GroupSummaryViewModel, ...]) -> None:
        """Replace group cards."""
        self._clear_cards()
        if not groups:
            self.cards_layout.addWidget(QLabel("Noch keine Stammgruppen vorhanden."), 0, 0)
            return
        for index, group in enumerate(groups):
            self.cards_layout.addWidget(self._group_card(group), index // 2, index % 2)

    def _group_card(self, group: GroupSummaryViewModel) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet("QFrame { background: #ffffff; border-radius: 6px; }")
        layout = QVBoxLayout(card)
        name = QLabel(group.group_name)
        name.setStyleSheet("font-size: 16px; font-weight: 600;")
        count = QLabel(f"{group.active_student_count} Schüler")
        open_button = QPushButton("Schüler anzeigen")
        open_button.clicked.connect(lambda: self.group_selected.emit(group.group_id))
        layout.addWidget(name)
        layout.addWidget(count)
        layout.addWidget(open_button)
        return card

    def _clear_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
