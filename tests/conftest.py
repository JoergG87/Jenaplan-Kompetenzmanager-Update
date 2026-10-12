"""Dispose test-owned Qt windows before Python collects their wrappers."""
from __future__ import annotations

import sys
import pytest

_qt_test_application = None


@pytest.fixture(autouse=True)
def dispose_qt_test_windows():
    """Keep shared QApplication alive and release only this test's windows."""
    global _qt_test_application
    widgets = sys.modules.get("PySide6.QtWidgets")
    app = widgets.QApplication.instance() if widgets is not None else None
    previous = set(app.topLevelWidgets()) if app is not None else set()
    yield
    widgets = sys.modules.get("PySide6.QtWidgets")
    app = widgets.QApplication.instance() if widgets is not None else None
    if app is None:
        return
    _qt_test_application = app
    from PySide6.QtCore import QCoreApplication, QEvent
    from shiboken6 import isValid
    for widget in app.topLevelWidgets():
        if widget not in previous and isValid(widget):
            widget.hide()
            widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
