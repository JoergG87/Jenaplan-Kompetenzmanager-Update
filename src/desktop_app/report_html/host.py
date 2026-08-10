"""Hardened local WebEngine host for one persisted report draft."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget
from shiboken6 import delete

from src.desktop_app.motion import MotionDialog
from src.desktop_app.web_ui.security import (
    LocalQrcWebEnginePage,
    LocalQrcWebEnginePolicy,
    configure_ephemeral_profile,
    configure_restricted_page,
    deny_feature_permissions,
    reject_unsafe_debug_environment,
)

from . import resources_rc  # noqa: F401
from .bridge import LearningReportHtmlBridge


INDEX_URL = "qrc:/jkm-report/index.html"
RESOURCE_PREFIX = "qrc:/jkm-report/"
MAX_CLOSE_PROBE_ATTEMPTS = 500


class ReportLocalOnlyRequestInterceptor(LocalQrcWebEnginePolicy):
    def __init__(self, parent: object | None = None) -> None:
        super().__init__(RESOURCE_PREFIX, parent)


class ReportLocalOnlyPage(LocalQrcWebEnginePage):
    def __init__(self, profile: QWebEngineProfile, parent: object) -> None:
        super().__init__(profile, parent, index_url=INDEX_URL)


class LearningReportHtmlDialog(MotionDialog):
    loaded = Signal(bool)

    def __init__(self, bridge: LearningReportHtmlBridge, parent: QWidget | None = None, *, devtools_enabled: bool = False) -> None:
        super().__init__(parent)
        reject_unsafe_debug_environment(devtools_enabled)
        self.bridge = bridge
        self._close_choice_provider = self._ask_close
        self._close_authorized = False
        self._close_probe_pending = False
        self._close_probe_attempts = 0
        self._disposed = False
        self.setObjectName("LearningReportHtmlDialog")
        self.setWindowTitle(f"Lernentwicklungsbericht · {bridge.session.preparation.student_name}")
        self.setAccessibleName("Berichtswerkstatt mit fünf Bereichen")
        self.resize(1500, 940)
        self.setMinimumSize(1080, 700)

        self.profile = QWebEngineProfile(self)
        self.interceptor = ReportLocalOnlyRequestInterceptor(self.profile)
        configure_ephemeral_profile(self.profile, self.interceptor)
        self.cookie_store = self.profile.cookieStore()
        self.page = ReportLocalOnlyPage(self.profile, self)
        deny_feature_permissions(self.page)
        self.channel = QWebChannel(self.page)
        self.channel.registerObject("reportBridge", bridge)
        self.page.setWebChannel(self.channel)
        self.view = QWebEngineView(self)
        self.view.setObjectName("LearningReportHtmlView")
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.view.setPage(self.page)
        configure_restricted_page(self.page, devtools_enabled=devtools_enabled)
        self.view.loadFinished.connect(self.loaded.emit)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.view.load(QUrl(INDEX_URL))
        self.finished.connect(self._dispose_webengine)

    def reject(self) -> None:
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._close_authorized:
            event.accept()
            QTimer.singleShot(0, self._dispose_webengine)
            return
        event.ignore()
        self._probe_dom_before_close()

    def _probe_dom_before_close(self, *, retry: bool = False) -> None:
        if self._close_probe_pending or self._disposed:
            return
        if not retry:
            self._close_probe_attempts = 0
        self._close_probe_pending = True
        self.page.runJavaScript(
            "({ready:Boolean(window.__jkmReportReady),dirty:Boolean(window.__jkmReportDirty),pending:Number(window.__jkmReportPendingCalls||0),syncToken:Number(window.__jkmReportSyncToken)})",
            self._dom_close_state_ready,
        )

    def _dom_close_state_ready(self, value: object) -> None:
        self._close_probe_pending = False
        if not isinstance(value, dict) or not value.get("ready"):
            self._block_close("Der Browser-Arbeitsstand konnte nicht sicher synchronisiert werden.")
            return
        pending = int(value.get("pending", 0))
        if pending > 0 or self.bridge.operation_pending:
            self._close_probe_attempts += 1
            if self._close_probe_attempts >= MAX_CLOSE_PROBE_ATTEMPTS:
                self._block_close("Eine laufende Eingabe konnte nicht bestätigt werden.")
                return
            QTimer.singleShot(10, lambda: self._probe_dom_before_close(retry=True))
            return
        if int(value.get("syncToken", -1)) != self.bridge.sync_token:
            self._block_close("Der aktuelle Eingabestand ist noch nicht sicher mit Python synchronisiert.")
            return
        dirty = bool(value.get("dirty")) or self.bridge.is_dirty
        if self._confirm_close(dirty):
            self._close_authorized = True
            self.close()

    def _confirm_close(self, dirty: bool) -> bool:
        if not dirty:
            return True
        choice = self._close_choice_provider(self)
        if choice == "discard":
            return True
        if choice != "save":
            return False
        result = json.loads(self.bridge.saveReportDraft())
        return bool(result.get("ok")) and not self.bridge.is_dirty

    @staticmethod
    def _ask_close(parent: QWidget) -> str:
        box = QMessageBox(parent)
        box.setWindowTitle("Ungespeicherte Änderungen")
        box.setText("In der Berichtswerkstatt gibt es ungespeicherte Änderungen.")
        save = box.addButton("Speichern und schließen", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Änderungen verwerfen", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("Weiter bearbeiten", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel)
        box.setEscapeButton(cancel)
        box.exec()
        return "save" if box.clickedButton() is save else "discard" if box.clickedButton() is discard else "cancel"

    def _block_close(self, detail: str) -> None:
        self._close_probe_attempts = 0
        QMessageBox.warning(self, "Berichtswerkstatt bleibt geöffnet", f"{detail} Der Arbeitsstand bleibt zum Schutz vor Datenverlust geöffnet.")

    def _dispose_webengine(self, *_args: object) -> None:
        if self._disposed:
            return
        self._disposed = True
        self.page.setWebChannel(None)
        self.channel.deregisterObject(self.bridge)
        delete(self.view)
        delete(self.page)
        delete(self.profile)
