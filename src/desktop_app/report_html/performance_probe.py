"""Focused timing probe for the local report HTML host."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from .bridge import LearningReportHtmlBridge
from .host import LearningReportHtmlDialog


@dataclass(frozen=True)
class ReportHtmlPerformanceResult:
    host_to_usable_ms: float
    first_draft_render_ms: float
    page_switch_max_ms: float
    evidence_first_build_ms: float
    revisions_open_ms: float


def measure_report_html(
    bridge_factory: Callable[[], LearningReportHtmlBridge],
    *,
    timeout_ms: int = 8000,
) -> ReportHtmlPerformanceResult:
    app = QApplication.instance() or QApplication([])
    started = perf_counter()
    host = LearningReportHtmlDialog(bridge_factory())
    host.show()
    _wait_until(app, lambda: bool(_javascript(host, "Boolean(window.__jkmReportReady)")), timeout_ms)
    usable = (perf_counter() - started) * 1000
    first_draft_render = float(
        _javascript(host, "Number(window.__jkmReportDraftRenderedMs)") or usable
    )
    switches = []
    for key in ("subjects", "preview", "writing"):
        point = perf_counter()
        visible = _javascript(host, f"show('{key}');document.querySelectorAll('[data-main-page]:not([hidden])').length")
        if visible != 1:
            raise RuntimeError("report_html_visible_page_contract_broken")
        switches.append((perf_counter() - point) * 1000)
    point = perf_counter()
    _javascript(host, "show('evidence')")
    _wait_until(app, lambda: bool(_javascript(host, "Boolean(evidence)")), timeout_ms)
    evidence_ms = (perf_counter() - point) * 1000
    point = perf_counter()
    _javascript(host, "show('revisions')")
    if _javascript(host, "document.querySelectorAll('[data-main-page]:not([hidden])').length") != 1:
        raise RuntimeError("report_html_visible_page_contract_broken")
    revisions_ms = (perf_counter() - point) * 1000
    host._close_authorized = True
    host.close()
    app.processEvents()
    return ReportHtmlPerformanceResult(
        usable,
        first_draft_render,
        max(switches),
        evidence_ms,
        revisions_ms,
    )


def _javascript(host: LearningReportHtmlDialog, source: str) -> object:
    loop = QEventLoop()
    result: list[object] = []
    host.page.runJavaScript(source, lambda value: (result.append(value), loop.quit()))
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    return result[0] if result else None


def _wait_until(app: QApplication, predicate: Callable[[], bool], timeout_ms: int) -> None:
    deadline = perf_counter() + timeout_ms / 1000
    while perf_counter() < deadline:
        app.processEvents()
        if predicate():
            return
    raise TimeoutError("report_html_performance_probe_timeout")
