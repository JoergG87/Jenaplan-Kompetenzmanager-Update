"""Neutral WebEngine security policy shared by local HTML workspaces."""

from __future__ import annotations

import os

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)


QWEBCHANNEL_URL = "qrc:///qtwebchannel/qwebchannel.js"


class LocalQrcWebEnginePolicy(QWebEngineUrlRequestInterceptor):
    """Allow one exact embedded resource prefix and Qt's WebChannel script."""

    def __init__(self, resource_prefix: str, parent: object | None = None) -> None:
        super().__init__(parent)
        self.resource_prefix = resource_prefix
        self.blocked_urls: list[str] = []

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:  # noqa: N802
        if self.is_allowed(info.requestUrl()):
            return
        self.blocked_urls.append(safe_url_label(info.requestUrl()))
        info.block(True)

    def is_allowed(self, url: QUrl) -> bool:
        if url.scheme() != "qrc":
            return False
        normalized = url.toString()
        return normalized == QWEBCHANNEL_URL or normalized.startswith(
            self.resource_prefix
        )


class LocalQrcWebEnginePage(QWebEnginePage):
    """Block external navigation, popup creation and console payloads."""

    externalNavigationBlocked = Signal(str)

    def __init__(
        self,
        profile: QWebEngineProfile,
        parent: object,
        *,
        index_url: str,
    ) -> None:
        super().__init__(profile, parent)
        self.index_url = index_url

    def acceptNavigationRequest(  # noqa: N802
        self,
        url: QUrl,
        navigation_type: QWebEnginePage.NavigationType,
        is_main_frame: bool,
    ) -> bool:
        del navigation_type
        allowed = is_main_frame and url.toString() == self.index_url
        if not allowed:
            self.externalNavigationBlocked.emit(safe_url_label(url))
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


def configure_ephemeral_profile(
    profile: QWebEngineProfile,
    interceptor: LocalQrcWebEnginePolicy,
) -> None:
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
    profile.setPersistentCookiesPolicy(
        QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
    )
    cookie_store = profile.cookieStore()
    cookie_store.setCookieFilter(lambda _request: False)
    cookie_store.deleteAllCookies()
    permission_policy = getattr(QWebEngineProfile, "PersistentPermissionsPolicy", None)
    if permission_policy is not None:
        profile.setPersistentPermissionsPolicy(permission_policy.AskEveryTime)
    if hasattr(profile, "setPushServiceEnabled"):
        profile.setPushServiceEnabled(False)
    profile.setUrlRequestInterceptor(interceptor)
    profile.downloadRequested.connect(lambda item: item.cancel())


def configure_restricted_page(
    page: QWebEnginePage,
    *,
    devtools_enabled: bool = False,
) -> None:
    settings = page.settings()
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
        page.setDevToolsPage(None)


def deny_feature_permissions(page: QWebEnginePage) -> None:
    page.featurePermissionRequested.connect(
        lambda origin, feature: page.setFeaturePermission(
            origin,
            feature,
            QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
        )
    )


def reject_unsafe_debug_environment(devtools_enabled: bool) -> None:
    if devtools_enabled:
        return
    if os.environ.get("QTWEBENGINE_REMOTE_DEBUGGING"):
        raise RuntimeError("qtwebengine_remote_debugging_not_allowed")
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    unsafe = ("--remote-debugging", "--no-sandbox", "--single-process")
    if any(flag in flags for flag in unsafe):
        raise RuntimeError("unsafe_qtwebengine_chromium_flags")


def safe_url_label(url: QUrl) -> str:
    if url.scheme() == "file":
        return "file://blocked-local-resource"
    host = url.host()
    return f"{url.scheme()}://{host}" if host else url.scheme()
