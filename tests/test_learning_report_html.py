"""Focused contracts for the gated report-only HTML workspace."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QFile, QIODevice, QUrl

from src.desktop_app import shell
from src.desktop_app.report_html import host as report_html_host
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.report_ui import report_ui_mode
from src.desktop_app.report_html.bridge import (
    LearningReportHtmlBridge,
    LearningReportHtmlSession,
)
from src.desktop_app.report_html.host import (
    INDEX_URL,
    LearningReportHtmlDialog,
    ReportLocalOnlyRequestInterceptor,
)
from src.desktop_app.report_html.performance_probe import measure_report_html
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportCompetencyViewModel,
    LearningReportDraftViewModel,
    LearningReportEvidenceViewModel,
    LearningReportPdfArtifactViewModel,
    LearningReportPreparationViewModel,
    LearningReportRevisionHistoryItemViewModel,
    LearningReportRevisionStatusViewModel,
    LearningReportSubjectDraftViewModel,
    LearningReportSubjectViewModel,
)
from tests.helpers.synthetic_v4 import (
    SYNTHETIC_REPORT_DRAFT_ID,
    create_synthetic_v4_database,
)


def _session() -> LearningReportHtmlSession:
    competencies = (
        LearningReportCompetencyViewModel("CMP-2", "math", "Mathematik", "Zahlen", "Addieren", "Zweite", "confirmed", False, True, (), 20),
        LearningReportCompetencyViewModel("CMP-1", "math", "Mathematik", "Zahlen", "Addieren", "Erste", "confirmed", False, True, (), 10),
    )
    evidence = (
        LearningReportEvidenceViewModel("OBS-1", date(2026, 9, 1), "Mathematik", "Unterricht", "Beleg", ("CMP-1",)),
    )
    preparation = LearningReportPreparationViewModel(
        "STU-1", "Mara Beispiel", "Sonnenbogen",
        (LearningReportSubjectViewModel("math", "Mathematik", competencies, evidence),),
        "Kurs 2",
    )
    draft = LearningReportDraftViewModel(
        student_id="STU-1", period_start=date(2026, 8, 1), period_end=date(2027, 1, 31),
        teacher_name="Laura", overall_text="Gesamttext",
        subjects=(LearningReportSubjectDraftViewModel("math", "Stärken", "Entwicklung", "Unterstützung", "Ziele"),),
        competency_ids=("CMP-1",), observation_ids=("OBS-1",), report_draft_id="RPD-1",
    )
    return LearningReportHtmlSession(preparation, draft, save_draft=lambda value: replace(value, updated_at="saved"))


def _qrc_text(path: str) -> str:
    handle = QFile(path)
    assert handle.open(QIODevice.OpenModeFlag.ReadOnly)
    return bytes(handle.readAll()).decode("utf-8")


def _final_v4_session(tmp_path: Path) -> LearningReportHtmlSession:
    database = create_synthetic_v4_database(tmp_path / "report-html-probe-final-v4.sqlite")
    adapter = StudentDesktopAdapter(
        database,
        database_create_allowed=False,
        today_provider=lambda: date(2026, 8, 11),
    )
    draft = adapter.load_learning_report_draft(SYNTHETIC_REPORT_DRAFT_ID)
    assert draft is not None
    preparation = adapter.learning_report_preparation_for_student(
        draft.student_id,
        period_end=draft.period_end,
        retained_competency_ids=draft.competency_ids,
    )
    assert preparation is not None
    return LearningReportHtmlSession(
        preparation,
        draft,
        revision_status=adapter.learning_report_revision_status(draft.report_draft_id),
        save_draft=adapter.save_learning_report_draft,
        prepare_finalization=adapter.prepare_learning_report_finalization,
        finalize_report=adapter.finalize_learning_report,
        refresh_revision_status=adapter.learning_report_revision_status,
        load_revision=adapter.load_learning_report_revision,
        load_final_artifact=adapter.load_learning_report_pdf_artifact,
    )


def test_report_gate_defaults_to_qt_and_is_independent_from_leg() -> None:
    assert report_ui_mode({}) == "qt"
    assert report_ui_mode({"JKM_REPORT_UI": " HTML ", "JKM_LEG_UI": "qt"}) == "html"
    with pytest.raises(ValueError, match="report_ui_mode_invalid"):
        report_ui_mode({"JKM_REPORT_UI": "browser"})


def test_html_bridge_requires_one_concrete_persisted_rpd_and_keeps_its_period() -> None:
    session = _session()
    bridge = LearningReportHtmlBridge(session)
    state = json.loads(bridge.initialState())
    assert state["draft"]["period_start"] == "2026-08-01"
    assert state["draft"]["period_end"] == "2027-01-31"
    with pytest.raises(ValueError, match="report_html_draft_id_required"):
        LearningReportHtmlBridge(replace(session, draft=replace(session.draft, report_draft_id="")))


def test_bridge_allowlist_is_explicit_and_full_save_resets_dirty() -> None:
    session = _session()
    bridge = LearningReportHtmlBridge(session)
    meta = bridge.metaObject()
    for signature in (
        "initialState()", "loadEvidenceState()", "updateHeaderField(QString,QString)",
        "updateOverallText(QString)", "updateSubjectText(QString,QString,QString)",
        "setSelection(QString,QString,bool)", "setChartSelection(QString,QString,bool)",
        "saveReportDraft()", "prepareFinalization()", "confirmFinalization(QString,bool)",
        "openRevision(QString)", "showFinalPdf(QString)",
    ):
        assert meta.indexOfMethod(signature) >= 0
    assert meta.indexOfMethod("invoke(QString,QVariant)") == -1
    assert json.loads(bridge.updateOverallText("Neu"))["ok"]
    assert bridge.is_dirty
    assert json.loads(bridge.saveReportDraft()) == {"ok": True, "code": "draft_saved"}
    assert not bridge.is_dirty


def test_rejected_mutation_keeps_python_state_and_dom_requeries_before_pending_ends() -> None:
    session = _session()
    bridge = LearningReportHtmlBridge(session)
    before = session.draft
    result = json.loads(bridge.updateHeaderField("period_end", "2026-01-01"))
    assert result["code"] == "period_invalid"
    assert session.draft == before
    javascript = Path("src/desktop_app/report_html/static/app.js").read_text(encoding="utf-8")
    requery = javascript.index("bridge.initialState")
    pending_end = javascript.index("window.__jkmReportPendingCalls--", requery)
    assert requery < pending_end


def test_existing_rpd_load_and_full_save_use_exact_synthetic_final_v4(tmp_path: Path) -> None:
    database = create_synthetic_v4_database(tmp_path / "report-html-final-v4.sqlite")
    adapter = StudentDesktopAdapter(database, database_create_allowed=False, today_provider=lambda: date(2026, 8, 11))
    draft = adapter.load_learning_report_draft(SYNTHETIC_REPORT_DRAFT_ID)
    assert draft is not None
    preparation = adapter.learning_report_preparation_for_student(
        draft.student_id, period_end=draft.period_end, retained_competency_ids=draft.competency_ids
    )
    assert preparation is not None
    bridge = LearningReportHtmlBridge(
        LearningReportHtmlSession(preparation, draft, save_draft=adapter.save_learning_report_draft)
    )
    assert json.loads(bridge.updateOverallText("HTML-Roundtrip"))["ok"]
    assert json.loads(bridge.saveReportDraft())["ok"]
    reloaded = adapter.load_learning_report_draft(SYNTHETIC_REPORT_DRAFT_ID)
    assert reloaded is not None
    assert reloaded.overall_text == "HTML-Roundtrip"
    assert reloaded.period_start == draft.period_start
    assert reloaded.period_end == draft.period_end


def test_subject_text_selection_and_chart_mutate_only_complete_python_draft() -> None:
    session = _session()
    bridge = LearningReportHtmlBridge(session)
    assert json.loads(bridge.updateSubjectText("math", "goals", "Neues Ziel"))["ok"]
    assert json.loads(bridge.setSelection("competency", "CMP-2", True))["ok"]
    assert json.loads(bridge.setChartSelection("math", "documentation_coverage", True))["ok"]
    assert session.draft.subjects[0].next_goals_text == "Neues Ziel"
    assert session.draft.competency_ids == ("CMP-1", "CMP-2")
    assert session.draft.chart_selections[0].chart_type == "documentation_coverage"


def test_finalization_and_read_only_revision_use_existing_final_v4_services(tmp_path: Path) -> None:
    session = _final_v4_session(tmp_path)
    bridge = LearningReportHtmlBridge(session)
    prepared = json.loads(bridge.prepareFinalization())
    assert prepared["code"] == "finalization_prepared"
    assert prepared["preview"]["period"]
    assert prepared["preview"]["subjects"]
    rejected = json.loads(bridge.confirmFinalization("Laura", False))
    assert rejected["code"] == "confirmation_required"
    finalized = json.loads(bridge.confirmFinalization("Laura", True))
    assert finalized["code"] == "report_finalized"
    revision_id = session.revision_status.history[0].learning_report_revision_id
    revision = json.loads(bridge.openRevision(revision_id))
    assert revision["code"] == "revision_loaded"
    assert revision["revision"]["subjects"]
    assert "snapshot" not in json.dumps(revision).casefold()


def test_finalization_uses_existing_visible_error_projection() -> None:
    session = _session()
    session.prepare_finalization = lambda _draft_id: (_ for _ in ()).throw(
        ValueError("Berichtstext fehlt")
    )
    session.finalization_error_message = lambda _error: (
        "Bitte mindestens einen bewusst verfassten Berichtstext ergänzen."
    )
    result = json.loads(LearningReportHtmlBridge(session).prepareFinalization())
    assert result == {
        "ok": False,
        "code": "finalization_not_ready",
        "message": "Bitte mindestens einen bewusst verfassten Berichtstext ergänzen.",
    }


def test_lazy_evidence_preserves_python_sort_order_and_stable_ids() -> None:
    bridge = LearningReportHtmlBridge(_session())
    evidence = json.loads(bridge.loadEvidenceState())
    assert [item["competency_id"] for item in evidence["subjects"][0]["competencies"]] == ["CMP-2", "CMP-1"]
    assert [item["sort_order"] for item in evidence["subjects"][0]["competencies"]] == [20, 10]


def test_pdf_projection_contains_only_opaque_artifact_id_and_blocked_action() -> None:
    session = _session()
    history = LearningReportRevisionHistoryItemViewModel("RPV-1", 1, "finalized", "Aktuell", "10.08.2026", "Laura", "01.08.2026 bis 31.01.2027", "Lernentwicklungsbericht", "SECRET-HASH")
    session.revision_status = LearningReportRevisionStatusViewModel("finalized", "Finalisiert · Revision 1", "Final", "RPV-1", 1, history=(history,))
    session.artifacts_by_revision_id = {"RPV-1": LearningReportPdfArtifactViewModel("RPA-1", "RPV-1", "/private/secret.pdf", "secret.pdf", 12, "SNAPSHOT", "PDFHASH", "heute")}
    bridge = LearningReportHtmlBridge(session)
    raw = bridge.initialState()
    assert "RPA-1" in raw
    for forbidden in ("/private", "secret.pdf", "SNAPSHOT", "PDFHASH"):
        assert forbidden not in raw
    assert json.loads(bridge.showFinalPdf("RPA-1"))["code"] == "final_pdf_viewer_blocked"


def test_qrc_csp_five_pages_and_local_request_policy() -> None:
    html = _qrc_text(":/jkm-report/index.html")
    javascript = _qrc_text(":/jkm-report/app.js")
    assert "connect-src 'none'" in html
    assert "'unsafe-inline'" not in html
    assert "'unsafe-eval'" not in html
    assert 'pages=["writing","subjects","evidence","preview","revisions"]' in javascript
    assert "data-main-page" in javascript
    assert "fetch(" not in javascript
    assert "beforeunload" not in javascript
    assert 'type==="date"?"change":"input"' in javascript
    assert 'chartLabels[item.chart_type]||"Entwicklungsdarstellung"' in javascript
    host_source = Path("src/desktop_app/report_html/host.py").read_text(encoding="utf-8")
    assert "syncToken" in host_source
    assert "operation_pending" in host_source
    assert "saveReportDraft" in host_source
    for name in ("index.html", "app.js", "app.css"):
        assert _qrc_text(f":/jkm-report/{name}") == Path(
            f"src/desktop_app/report_html/static/{name}"
        ).read_text(encoding="utf-8")
    interceptor = ReportLocalOnlyRequestInterceptor()
    assert interceptor.is_allowed(QUrl(INDEX_URL))
    assert not interceptor.is_allowed(QUrl("https://example.invalid"))
    assert not interceptor.is_allowed(QUrl.fromLocalFile("/tmp/report.pdf"))


class _CloseBridge:
    def __init__(self) -> None:
        self.operation_pending = False
        self.sync_token = 4
        self.is_dirty = True
        self.save_calls = 0

    def saveReportDraft(self) -> str:  # noqa: N802
        self.save_calls += 1
        self.is_dirty = False
        return json.dumps({"ok": True})


def _close_harness() -> SimpleNamespace:
    harness = SimpleNamespace(
        _close_probe_pending=True,
        _close_probe_attempts=0,
        _close_authorized=False,
        bridge=_CloseBridge(),
        blocked=[],
        retried=[],
        closed=0,
    )
    harness._block_close = harness.blocked.append
    harness._probe_dom_before_close = lambda **kwargs: harness.retried.append(kwargs)
    harness._confirm_close = lambda dirty: False
    harness.close = lambda: setattr(harness, "closed", harness.closed + 1)
    return harness


def test_report_host_close_probe_blocks_invalid_pending_and_token_mismatch(monkeypatch) -> None:
    harness = _close_harness()
    LearningReportHtmlDialog._dom_close_state_ready(harness, None)
    assert harness.blocked == ["Der Browser-Arbeitsstand konnte nicht sicher synchronisiert werden."]

    harness = _close_harness()
    monkeypatch.setattr(report_html_host.QTimer, "singleShot", lambda _delay, callback: callback())
    LearningReportHtmlDialog._dom_close_state_ready(
        harness, {"ready": True, "dirty": True, "pending": 1, "syncToken": 4}
    )
    assert harness.retried == [{"retry": True}]
    assert harness.closed == 0

    harness = _close_harness()
    LearningReportHtmlDialog._dom_close_state_ready(
        harness, {"ready": True, "dirty": True, "pending": 0, "syncToken": 3}
    )
    assert harness.blocked == ["Der aktuelle Eingabestand ist noch nicht sicher mit Python synchronisiert."]


@pytest.mark.parametrize(
    ("choice", "expected", "save_calls"),
    (("save", True, 1), ("discard", True, 0), ("cancel", False, 0)),
)
def test_report_host_dirty_close_save_discard_cancel(choice, expected, save_calls) -> None:
    harness = SimpleNamespace(
        bridge=_CloseBridge(),
        _close_choice_provider=lambda _parent: choice,
    )
    assert LearningReportHtmlDialog._confirm_close(harness, True) is expected
    assert harness.bridge.save_calls == save_calls


def test_report_host_cleanup_deregisters_and_deletes_webengine_objects(monkeypatch) -> None:
    events = []
    page = SimpleNamespace(setWebChannel=lambda value: events.append(("channel", value)))
    channel = SimpleNamespace(deregisterObject=lambda value: events.append(("deregister", value)))
    harness = SimpleNamespace(
        _disposed=False,
        page=page,
        channel=channel,
        bridge="bridge",
        view="view",
        profile="profile",
    )
    monkeypatch.setattr(report_html_host, "delete", lambda value: events.append(("delete", value)))
    LearningReportHtmlDialog._dispose_webengine(harness)
    LearningReportHtmlDialog._dispose_webengine(harness)
    assert harness._disposed
    assert events == [
        ("channel", None),
        ("deregister", "bridge"),
        ("delete", "view"),
        ("delete", page),
        ("delete", "profile"),
    ]


def test_shell_keeps_qt_default_and_html_selection_deliberate() -> None:
    source = inspect.getsource(shell.AppShell.open_learning_report_dialog)
    helper = inspect.getsource(shell.AppShell._open_learning_report_html_dialog)
    assert "selected_ui = report_ui_mode()" in source
    assert 'len(drafts) == 1 and selected_ui == "qt"' in source
    assert 'selected_ui == "qt" and not subject_id and not workspace_key' in source
    assert 'selected_ui == "html" and initial_draft is not None' in source
    assert "LearningReportDialog(" in source
    assert "LearningReportHtmlSession(" in helper
    assert "show_final_pdf=None" in helper


def test_packaging_declares_report_lazy_imports() -> None:
    spec = Path("packaging/macos_pilot.spec").read_text(encoding="utf-8")
    for module in ("src.desktop_app.report_html.bridge", "src.desktop_app.report_html.host", "src.desktop_app.report_html.resources_rc", "src.desktop_app.web_ui.security"):
        assert f'"{module}"' in spec


def test_real_webengine_performance_probe_is_responsive(tmp_path: Path) -> None:
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        pytest.skip("Qt WebEngine requires the native Cocoa lifecycle on macOS")
    result = measure_report_html(
        lambda: LearningReportHtmlBridge(_final_v4_session(tmp_path))
    )
    assert result.host_to_usable_ms < 5000
    assert result.first_draft_render_ms < 5000
    assert result.page_switch_max_ms < 500
    assert result.evidence_first_build_ms < 1000
    assert result.revisions_open_ms < 500
