"""Hardened local WebEngine host with the Qt LEG dirty-close contract."""

from __future__ import annotations

import json
import os

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget
from shiboken6 import delete

from src.desktop_app.motion import MotionDialog
from src.desktop_app.dialogs.learning_conference_dialog import (
    LearningConferenceCloseDialog,
)

from .bridge import LearningConferenceHtmlBridge
from . import resources_rc  # noqa: F401 - registers immutable qrc resources


INDEX_URL = "qrc:/jkm-leg/index.html"
RESOURCE_PREFIX = "qrc:/jkm-leg/"
QWEBCHANNEL_URL = "qrc:///qtwebchannel/qwebchannel.js"
MAX_CLOSE_PROBE_ATTEMPTS = 500


class LegLocalOnlyRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Allow only the embedded LEG assets and Qt's WebChannel script."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.blocked_urls: list[str] = []

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:  # noqa: N802
        if self.is_allowed(info.requestUrl()):
            return
        self.blocked_urls.append(_safe_url_label(info.requestUrl()))
        info.block(True)

    @staticmethod
    def is_allowed(url: QUrl) -> bool:
        if url.scheme() != "qrc":
            return False
        normalized = url.toString()
        return normalized == QWEBCHANNEL_URL or normalized.startswith(RESOURCE_PREFIX)


class LegLocalOnlyPage(QWebEnginePage):
    """Block every external navigation, popup and JavaScript console payload."""

    externalNavigationBlocked = Signal(str)

    def acceptNavigationRequest(  # noqa: N802
        self,
        url: QUrl,
        navigation_type: QWebEnginePage.NavigationType,
        is_main_frame: bool,
    ) -> bool:
        del navigation_type
        allowed = is_main_frame and url.toString() == INDEX_URL
        if not allowed:
            self.externalNavigationBlocked.emit(_safe_url_label(url))
        return allowed

    def createWindow(self, window_type: QWebEnginePage.WebWindowType) -> None:  # noqa: N802
        del window_type
        return None

    def javaScriptConsoleMessage(  # noqa: N802
        self,
        level: QWebEnginePage.JavaScriptConsoleMessageLevel,
        message: str,
        line_number: int,
        source_id: str,
    ) -> None:
        del level, message, line_number, source_id


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
        _reject_unsafe_debug_environment(devtools_enabled)
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
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )
        self.cookie_store = self.profile.cookieStore()
        self.cookie_store.setCookieFilter(lambda _request: False)
        self.cookie_store.deleteAllCookies()
        permission_policy = getattr(
            QWebEngineProfile,
            "PersistentPermissionsPolicy",
            None,
        )
        if permission_policy is not None:
            self.profile.setPersistentPermissionsPolicy(permission_policy.AskEveryTime)
        if hasattr(self.profile, "setPushServiceEnabled"):
            self.profile.setPushServiceEnabled(False)
        self.interceptor = LegLocalOnlyRequestInterceptor(self.profile)
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self.profile.downloadRequested.connect(lambda item: item.cancel())

        self.page = LegLocalOnlyPage(self.profile, self)
        self.page.featurePermissionRequested.connect(
            lambda origin, feature: self.page.setFeaturePermission(
                origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
            )
        )
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
        settings = self.page.settings()
        attributes = QWebEngineSettings.WebAttribute
        disabled = (
            "LocalStorageEnabled",
            "DnsPrefetchEnabled",
            "HyperlinkAuditingEnabled",
            "ScreenCaptureEnabled",
            "NavigateOnDropEnabled",
            "AutoLoadIconsForPage",
            "TouchIconsEnabled",
            "ReadingFromCanvasEnabled",
        )
        settings.setAttribute(attributes.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(attributes.LocalContentCanAccessFileUrls, False)
        settings.setAttribute(attributes.JavascriptCanOpenWindows, False)
        settings.setAttribute(attributes.JavascriptCanAccessClipboard, False)
        settings.setAttribute(attributes.PluginsEnabled, False)
        settings.setAttribute(attributes.FullScreenSupportEnabled, False)
        settings.setAttribute(attributes.PdfViewerEnabled, False)
        settings.setAttribute(attributes.WebGLEnabled, False)
        settings.setAttribute(attributes.Accelerated2dCanvasEnabled, False)
        for name in disabled:
            attribute = getattr(attributes, name, None)
            if attribute is not None:
                settings.setAttribute(attribute, False)
        javascript_paste = getattr(attributes, "JavascriptCanPaste", None)
        if javascript_paste is not None:
            settings.setAttribute(javascript_paste, False)
        settings.setUnknownUrlSchemePolicy(
            QWebEngineSettings.UnknownUrlSchemePolicy.DisallowUnknownUrlSchemes
        )
        developer_extras = getattr(attributes, "DeveloperExtrasEnabled", None)
        if developer_extras is not None:
            settings.setAttribute(developer_extras, devtools_enabled)
        if not devtools_enabled:
            self.page.setDevToolsPage(None)

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


def _safe_url_label(url: QUrl) -> str:
    if url.scheme() == "file":
        return "file://blocked-local-resource"
    host = url.host()
    return f"{url.scheme()}://{host}" if host else url.scheme()


def _reject_unsafe_debug_environment(devtools_enabled: bool) -> None:
    if devtools_enabled:
        return
    if os.environ.get("QTWEBENGINE_REMOTE_DEBUGGING"):
        raise RuntimeError("qtwebengine_remote_debugging_not_allowed")
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    unsafe = ("--remote-debugging", "--no-sandbox", "--single-process")
    if any(flag in flags for flag in unsafe):
        raise RuntimeError("unsafe_qtwebengine_chromium_flags")
