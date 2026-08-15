"""Regression tests for toast layout ownership."""

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.components import Toast


def test_nested_layout_toast_is_managed_and_reserves_wrapped_height() -> None:
    """Shell-style nested layouts must not be mistaken for toast overlays."""
    app = QApplication.instance() or QApplication([])

    root = QWidget()
    root.resize(900, 300)

    outer = QHBoxLayout(root)
    inner = QVBoxLayout()
    outer.addLayout(inner)

    toast = Toast()
    inner.addWidget(toast)

    root.show()
    app.processEvents()

    message = (
        "Kein eindeutiges aktuelles Schuljahr: "
        "Schülerbezogene Bereiche bleiben gesperrt."
    )
    toast.show_message(
        message,
        duration_ms=10_000,
    )
    app.processEvents()

    assert toast.parentWidget() is root
    assert toast._is_parent_overlay() is False

    required_height = toast.heightForWidth(max(1, toast.width()))
    assert toast.height() >= required_height
    assert toast.geometry().bottom() <= root.contentsRect().bottom()

    root.close()
