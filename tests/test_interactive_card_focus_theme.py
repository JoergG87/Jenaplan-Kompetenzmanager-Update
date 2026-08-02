"""Rendered regressions for simultaneous selection and focus on cards."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QWidget

from src.desktop_app import theme
from src.desktop_app.components import AppCard
from src.desktop_app.dialogs.new_observation_dialog import (
    ObservationCatalogCompetencyTile,
)


def _color_at(card: AppCard, point: QPoint) -> str:
    return card.grab().toImage().pixelColor(point).name().upper()


def _assert_color_close(actual: str, expected: str) -> None:
    actual_channels = tuple(
        int(actual[index : index + 2], 16) for index in (1, 3, 5)
    )
    expected_channels = tuple(
        int(expected[index : index + 2], 16) for index in (1, 3, 5)
    )
    difference = max(
        abs(left - right)
        for left, right in zip(actual_channels, expected_channels)
    )
    assert difference <= 2


def _shown_card() -> tuple[QWidget, AppCard]:
    host = QWidget()
    host.resize(180, 100)
    card = AppCard("interactive", interactive=True)
    card.setGeometry(30, 20, 120, 60)
    card.setAccessibleName("Kompetenzkarte")
    card.setParent(host)
    host.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    host.show()
    host.activateWindow()
    host.setFocus(Qt.FocusReason.OtherFocusReason)
    QApplication.processEvents()
    return host, card


def test_interactive_card_states_render_with_existing_theme_colors() -> None:
    app = QApplication.instance() or QApplication([])
    theme.apply_app_theme(app)
    host, card = _shown_card()
    original_geometry = card.geometry()

    assert _color_at(card, QPoint(60, 0)) == "#D5E0E8"

    card.setFocus(Qt.FocusReason.TabFocusReason)
    QApplication.processEvents()
    assert card.hasFocus()
    assert _color_at(card, QPoint(60, 0)) == theme.COLOR_FOCUS

    card.clearFocus()
    card.set_selected(True)
    QApplication.processEvents()
    assert _color_at(card, QPoint(60, 0)) == theme.COLOR_BLUE
    selected_contents_rect = card.contentsRect()

    card.setFocus(Qt.FocusReason.TabFocusReason)
    QApplication.processEvents()
    assert _color_at(card, QPoint(60, 0)) == theme.COLOR_FOCUS
    assert _color_at(card, QPoint(0, 30)) == theme.COLOR_BLUE
    assert _color_at(card, QPoint(60, 30)) == "#EEF5FF"
    assert card.contentsRect() == selected_contents_rect

    QTest.mouseMove(card, QPoint(60, 30))
    QApplication.processEvents()
    assert _color_at(card, QPoint(60, 0)) == theme.COLOR_FOCUS
    assert _color_at(card, QPoint(0, 30)) == theme.COLOR_BLUE
    assert card.contentsRect() == selected_contents_rect

    card.set_pressed(True)
    QApplication.processEvents()
    assert _color_at(card, QPoint(60, 0)) == theme.COLOR_FOCUS
    assert _color_at(card, QPoint(0, 30)) == theme.COLOR_BLUE
    assert card.contentsRect() == selected_contents_rect
    card.set_pressed(False)

    card.setEnabled(False)
    QApplication.processEvents()
    assert _color_at(card, QPoint(60, 0)) == "#E2E8ED"
    assert _color_at(card, QPoint(60, 30)) == "#F3F6F8"
    assert card.geometry() == original_geometry
    assert card.contentsRect() == selected_contents_rect
    host.close()


def test_observation_competency_card_keeps_tab_accessibility_and_action() -> None:
    app = QApplication.instance() or QApplication([])
    theme.apply_app_theme(app)
    host = QWidget()
    layout = QHBoxLayout(host)
    before = QPushButton("Vorher")
    activations: list[str] = []
    card = ObservationCatalogCompetencyTile(
        "CMP-1", lambda: activations.append("CMP-1"), selected=False
    )
    card.setFixedSize(120, 60)
    after = QPushButton("Nachher")
    layout.addWidget(before)
    layout.addWidget(card)
    layout.addWidget(after)
    host.show()
    host.activateWindow()
    before.setFocus(Qt.FocusReason.TabFocusReason)
    QApplication.processEvents()

    QTest.keyClick(before, Qt.Key.Key_Tab)
    assert card.hasFocus()
    assert card.accessibleName() == "Kompetenz zur Auswahl hinzufügen"
    QTest.keyClick(card, Qt.Key.Key_Space)
    assert activations == ["CMP-1"]

    card.set_selected(True)
    assert card.accessibleName() == "Bereits ausgewählte Kompetenz"
    QApplication.processEvents()
    _assert_color_close(
        _color_at(card, QPoint(card.width() // 2, 0)), theme.COLOR_FOCUS
    )
    _assert_color_close(
        _color_at(card, QPoint(0, card.height() // 2)), theme.COLOR_BLUE
    )
    QTest.keyClick(card, Qt.Key.Key_Space)
    assert activations == ["CMP-1"]
    host.close()
