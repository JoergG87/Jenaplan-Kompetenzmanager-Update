"""Hardened local WebEngine host with the Qt LEG dirty-close contract."""

from __future__ import annotations

import json
from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget
from shiboken6 import delete

from src.desktop_app.motion import MotionDialog
from src.desktop_app.web_ui.security import (
    QWEBCHANNEL_URL,
    LocalQrcWebEnginePage,
    LocalQrcWebEnginePolicy,
    configure_ephemeral_profile,
    configure_restricted_page,
    deny_feature_permissions,
    reject_unsafe_debug_environment,
)
from src.desktop_app.dialogs.learning_conference_dialog import (
    LearningConferenceCloseDialog,
)

from .bridge import LearningConferenceHtmlBridge
from . import resources_rc  # noqa: F401 - registers immutable qrc resources


INDEX_URL = "qrc:/jkm-leg/index.html"
RESOURCE_PREFIX = "qrc:/jkm-leg/"
MAX_CLOSE_PROBE_ATTEMPTS = 500


class LegLocalOnlyRequestInterceptor(LocalQrcWebEnginePolicy):
    """Allow only the embedded LEG assets and Qt's WebChannel script."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(RESOURCE_PREFIX, parent)

    @staticmethod
    def is_allowed(url: QUrl) -> bool:
        if url.scheme() != "qrc":
            return False
        normalized = url.toString()
        return normalized == QWEBCHANNEL_URL or normalized.startswith(RESOURCE_PREFIX)


class LegLocalOnlyPage(LocalQrcWebEnginePage):
    """Block every external navigation, popup and JavaScript console payload."""

    def __init__(self, profile: QWebEngineProfile, parent: object) -> None:
        super().__init__(profile, parent, index_url=INDEX_URL)


class LearningConferenceHtmlDialog(MotionDialog):
    """Modal LEG workspace; phase navigation remains entirely DOM-local."""

    loaded = Signal(bool)

    def __init__(
        self,
        bridge: LearningConferenceHtmlBridge,
        parent: QWidget | None = None,
        *,
        devtools_enabled: bool = False,
    ) -> None:
        super().__init__(parent)
        reject_unsafe_debug_environment(devtools_enabled)
        self.bridge = bridge
        self._close_choice_provider = LearningConferenceCloseDialog.ask
        self._close_authorized = False
        self._close_probe_pending = False
        self._close_probe_attempts = 0
        self._disposed = False
        self.setObjectName("LearningConferenceHtmlDialog")
        self.setWindowTitle(
            f"Lernentwicklungsgespräch · {bridge.session.preparation.student_name}"
        )
        self.setAccessibleName("Lernentwicklungsgespräch in sechs Phasen")
        self.resize(1400, 900)
        self.setMinimumSize(1080, 700)

        self.profile = QWebEngineProfile(self)
        self.interceptor = LegLocalOnlyRequestInterceptor(self.profile)
        configure_ephemeral_profile(self.profile, self.interceptor)
        self.cookie_store = self.profile.cookieStore()

        self.page = LegLocalOnlyPage(self.profile, self)
        deny_feature_permissions(self.page)
        self.channel = QWebChannel(self.page)
        self.channel.registerObject("legBridge", bridge)
        self.page.setWebChannel(self.channel)

        self.view = QWebEngineView(self)
        self.view.setObjectName("LearningConferenceHtmlView")
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.view.setPage(self.page)
        self._configure_settings(devtools_enabled)
        self.view.loadFinished.connect(self.loaded.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.view.load(QUrl(INDEX_URL))
        self.finished.connect(self._dispose_webengine)

    def _configure_settings(self, devtools_enabled: bool) -> None:
        configure_restricted_page(self.page, devtools_enabled=devtools_enabled)

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
            "({dirty:Boolean(window.__jkmLegDirty),"
            "pending:Number(window.__jkmLegPendingCalls || 0)})",
            self._dom_close_state_ready,
        )

    def _dom_close_state_ready(self, value: object) -> None:
        self._close_probe_pending = False
        state = value if isinstance(value, dict) else {}
        pending = int(state.get("pending", 0))
        if pending > 0:
            self._close_probe_attempts += 1
            if self._close_probe_attempts >= MAX_CLOSE_PROBE_ATTEMPTS:
                self._close_probe_attempts = 0
                QMessageBox.warning(
                    self,
                    "Lernentwicklungsgespräch bleibt geöffnet",
                    "Eine laufende Eingabe konnte nicht bestätigt werden. "
                    "Der Arbeitsstand bleibt zum Schutz vor Datenverlust geöffnet. "
                    "Bitte prüfen Sie die Eingabe und versuchen Sie das Schließen erneut.",
                )
                return
            QTimer.singleShot(10, lambda: self._probe_dom_before_close(retry=True))
            return
        self._close_probe_attempts = 0
        dirty = bool(state.get("dirty", False)) or self.bridge.is_dirty
        if self._confirm_close(dirty):
            self._close_authorized = True
            self.close()

    def _confirm_close(self, dirty: bool | None = None) -> bool:
        if dirty is None:
            dirty = self.bridge.is_dirty
        if not dirty:
            return True
        choice = self._close_choice_provider(self)
        if choice == "discard":
            return True
        if choice != "save":
            return False
        result = json.loads(self.bridge.saveConferenceDraft())
        return bool(result.get("ok")) and not self.bridge.is_dirty

    def _dispose_webengine(self, *_args: object) -> None:
        if self._disposed:
            return
        self._disposed = True
        self.page.setWebChannel(None)
        self.channel.deregisterObject(self.bridge)
        delete(self.view)
        delete(self.page)
        delete(self.profile)
