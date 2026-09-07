"""Focused contracts for the internally gated LEG-only HTML product path."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QFile, QIODevice, QTimer, QUrl
from PySide6.QtWidgets import QApplication

from src.core.learning_conference import (
    LearningConferenceCompletionError,
    LearningConferenceCompletionErrorCode,
)
from src.desktop_app.leg_html.bridge import (
    LearningConferenceHtmlBridge,
    LearningConferenceHtmlSession,
)
from src.desktop_app.leg_html.host import (
    INDEX_URL,
    QWEBCHANNEL_URL,
    LegLocalOnlyRequestInterceptor,
)
from src.desktop_app.leg_ui import leg_ui_mode
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceCompetencyViewModel,
    LearningConferenceDraftViewModel,
    LearningConferencePdfArtifactViewModel,
    LearningConferencePreparationViewModel,
    LearningConferenceRevisionListItemViewModel,
    LearningConferenceRevisionStatusViewModel,
    LearningConferenceSubjectViewModel,
)
from tests.helpers.synthetic_v4 import (
    SYNTHETIC_LEG_DRAFT_ID,
    SYNTHETIC_STUDENT_IDS,
    create_synthetic_v4_database,
)


def _session(*, competency_count: int = 3) -> LearningConferenceHtmlSession:
    competencies = tuple(
        LearningConferenceCompetencyViewModel(
            competency_id=f"K-DE-{index + 1:03d}",
            subject_id="deutsch",
            subject_name="Deutsch",
            learning_area="Lesen",
            competency_group="Texte verstehen",
            competency_text=f"Synthetische Kompetenz {index + 1}",
            documentation_state="undocumented",
            observed_proposal="",
            confirmed_rating="",
            historical=False,
            selectable=True,
            sort_order=index,
        )
        for index in range(competency_count)
    )
    return LearningConferenceHtmlSession(
        preparation=LearningConferencePreparationViewModel(
            student_id="STU-TEST-001",
            student_name="Mara Beispiel",
            group_name="Sonnenbogen",
            subjects=(LearningConferenceSubjectViewModel("deutsch", "Deutsch", competencies),),
            cross_topics=(),
            evidence=(),
        ),
        draft=LearningConferenceDraftViewModel(
            student_id="STU-TEST-001",
            learning_conference_draft_id="LCD-TEST-001",
            conference_date=date(2026, 8, 10),
            subject_ids=("deutsch",),
        ),
        revision_status=LearningConferenceRevisionStatusViewModel(
            has_completion=True,
            status_label="Abgeschlossen · Revision 1",
            draft_changed=False,
            hash_valid=True,
            current_revision_number=1,
            revisions=(LearningConferenceRevisionListItemViewModel(
                "LCV-TEST-001", 1, "completed", "Aktuell",
                "10.08.2026, 12:00", "Beispiel-Lehrkraft", "synthetic-snapshot",
            ),),
        ),
        save_draft=lambda draft: replace(draft, updated_at="2026-08-10T12:00:00"),
    )


def test_leg_ui_gate_defaults_to_qt_and_only_accepts_explicit_modes() -> None:
    assert leg_ui_mode({}) == "qt"
    assert leg_ui_mode({"JKM_LEG_UI": "html"}) == "html"
    assert leg_ui_mode({"JKM_LEG_UI": " QT "}) == "qt"

    try:
        leg_ui_mode({"JKM_LEG_UI": "browser"})
    except ValueError as error:
        assert str(error) == "leg_ui_mode_invalid"
    else:  # pragma: no cover - explicit fail-closed assertion
        raise AssertionError("invalid LEG gate was accepted")


def test_bridge_allowlist_has_no_generic_command_or_database_surface() -> None:
    bridge = LearningConferenceHtmlBridge(_session())
    meta = bridge.metaObject()

    for signature in (
        "initialState()",
        "loadEvidenceState()",
        "updateText(QString,QString)",
        "updateDate(QString,QString)",
        "setSelection(QString,QString,bool)",
        "saveConferenceDraft()",
        "completeConference()",
        "openRevision(QString)",
        "showFinalPdf(QString)",
    ):
        assert meta.indexOfMethod(signature) >= 0
    for forbidden in (
        "invoke(QString,QVariant)",
        "execute(QString)",
        "eval(QString)",
        "queryDatabase(QString)",
    ):
        assert meta.indexOfMethod(forbidden) == -1


def test_python_draft_is_source_of_truth_and_save_resets_dirty_baseline() -> None:
    session = _session()
    bridge = LearningConferenceHtmlBridge(session)

    before = session.draft
    initial = json.loads(bridge.initialState())
    assert session.draft == before
    assert initial["dirty"] is False
    assert all("competencies" not in subject for subject in initial["preparation"]["subjects"])
    assert "evidence" not in initial["preparation"]

    assert json.loads(bridge.updateText("agreed_goals_text", "Gemeinsames Ziel"))["ok"]
    assert json.loads(bridge.updateDate("next_review_date", "2026-09-15"))["ok"]
    assert json.loads(bridge.setSelection("competency", "K-DE-001", True))["ok"]
    assert bridge.is_dirty
    assert session.draft.next_review_date == date(2026, 9, 15)

    assert json.loads(bridge.saveConferenceDraft()) == {
        "ok": True,
        "code": "draft_saved",
    }
    assert not bridge.is_dirty
    assert session.draft.updated_at == "2026-08-10T12:00:00"


def test_bridge_loads_existing_draft_through_exact_synthetic_final_v4(
    tmp_path: Path,
) -> None:
    database = create_synthetic_v4_database(tmp_path / "leg-html-final-v4.sqlite")
    adapter = StudentDesktopAdapter(
        database,
        database_create_allowed=False,
        today_provider=lambda: date(2026, 8, 10),
    )
    draft = adapter.load_learning_conference_draft(SYNTHETIC_LEG_DRAFT_ID)
    assert draft is not None
    preparation = adapter.learning_conference_preparation_for_student(
        SYNTHETIC_STUDENT_IDS[0],
        conference_date=draft.conference_date,
        retained_competency_ids=draft.competency_ids,
    )
    assert preparation is not None

    bridge = LearningConferenceHtmlBridge(
        LearningConferenceHtmlSession(
            preparation=preparation,
            draft=draft,
            save_draft=adapter.save_learning_conference_draft,
            complete_conference=adapter.complete_learning_conference,
            refresh_revision_status=adapter.learning_conference_revision_status,
            load_final_artifact=adapter.load_learning_conference_pdf_artifact,
        )
    )
    state = json.loads(bridge.initialState())

    assert state["draft"]["has_persistent_id"] is True
    assert state["preparation"]["student_name"]
    assert state["preparation"]["subjects"]
    evidence_state = json.loads(bridge.loadEvidenceState())
    assert evidence_state["subjects"][0]["competencies"]
    assert bridge.session.draft == draft


def test_completion_uses_saved_id_and_exposes_only_curated_error() -> None:
    session = _session()
    session.draft = replace(
        session.draft,
        learning_conference_draft_id="LCD-TEST-001",
    )

    def fail(_draft_id: str) -> object:
        raise LearningConferenceCompletionError(
            LearningConferenceCompletionErrorCode.OBSERVATION_UNAVAILABLE,
            "internal OBS-SECRET-999 at /private/path",
            reference_ids=("OBS-SECRET-999",),
        )

    session.complete_conference = fail  # type: ignore[assignment]
    bridge = LearningConferenceHtmlBridge(session)
    result = json.loads(bridge.completeConference())

    assert result == {
        "ok": False,
        "code": "completion_not_ready",
        "message": "Ein ausgewählter Beleg ist nicht mehr verfügbar.",
        "phase_key": "evidence",
    }
    assert "OBS-SECRET" not in json.dumps(result)
    assert "/private" not in json.dumps(result)


def test_competency_projection_preserves_canonical_sort_and_four_levels() -> None:
    session = _session(competency_count=3)
    subject = session.preparation.subjects[0]
    reordered = (
        replace(subject.competencies[0], learning_area="Bereich B", competency_group="Thema 2", sort_order=20),
        replace(subject.competencies[1], learning_area="Bereich A", competency_group="Thema 1", sort_order=10),
        replace(subject.competencies[2], learning_area="Bereich A", competency_group="Thema 1", sort_order=11),
    )
    second_subject = replace(
        subject,
        subject_id="first-by-existing-order",
        subject_name="Zuerst geliefert",
        competencies=(replace(reordered[0], subject_id="first-by-existing-order", sort_order=999),),
    )
    session.preparation = replace(
        session.preparation,
        subjects=(second_subject, replace(subject, competencies=reordered)),
    )

    bridge = LearningConferenceHtmlBridge(session)
    initial = json.loads(bridge.initialState())
    assert [item["subject_id"] for item in initial["preparation"]["subjects"]] == [
        "first-by-existing-order",
        subject.subject_id,
    ]
    state = json.loads(bridge.loadEvidenceState())
    competencies = state["subjects"][1]["competencies"]
    assert [item["competency_id"] for item in competencies] == [
        reordered[1].competency_id,
        reordered[2].competency_id,
        reordered[0].competency_id,
    ]
    javascript = _qrc_text(":/jkm-leg/app.js")
    assert 'grouped(subject.competencies, "learning_area")' in javascript
    assert 'grouped(area.items, "competency_group")' in javascript


def test_historical_selection_unavailable_evidence_and_all_charts_remain_editable() -> None:
    session = _session(competency_count=2)
    subject = session.preparation.subjects[0]
    historical = replace(subject.competencies[0], selectable=False, historical=True)
    session.preparation = replace(
        session.preparation,
        subjects=(replace(subject, competencies=(historical, subject.competencies[1])),),
    )
    session.draft = replace(
        session.draft,
        competency_ids=(historical.competency_id,),
        observation_ids=("OBS-MISSING-001",),
        unavailable_observation_ids=("OBS-MISSING-001",),
    )
    bridge = LearningConferenceHtmlBridge(session)

    evidence = json.loads(bridge.loadEvidenceState())
    assert evidence["unavailable_observation_ids"] == ["OBS-MISSING-001"]
    assert json.loads(bridge.setSelection("competency", historical.competency_id, False))["ok"]
    assert json.loads(bridge.setSelection("observation", "OBS-MISSING-001", False))["ok"]
    for chart in (
        "documentation_coverage",
        "competency_timeline",
        "observation_timeline",
    ):
        assert json.loads(bridge.setSelection("chart", chart, True))["ok"]


def test_save_bridge_rejects_reentrant_request() -> None:
    bridge = LearningConferenceHtmlBridge(_session())
    bridge._save_pending = True

    assert json.loads(bridge.saveConferenceDraft()) == {
        "ok": False,
        "code": "save_in_progress",
    }


def test_six_phase_field_matrix_matches_qt_contract() -> None:
    javascript = _qrc_text(":/jkm-leg/app.js")
    phase_titles = (
        "Gesprächsziel",
        "Was gelingt dem Kind?",
        "Welche Entwicklung sehen wir?",
        "Woran möchten wir gemeinsam arbeiten?",
        "Welche Beispiele stützen unsere Einschätzung?",
        "Welche Unterstützung und Vereinbarungen treffen wir?",
    )
    for title in phase_titles:
        assert f'label: "{title}"' in javascript
        assert f'phaseIntro("{title}"' in javascript
    expected_fields = {
        "goal": ("responsible_teacher", "conversation_entry_text", "period_start", "period_end", "conference_date"),
        "strengths": ("strengths_text", "child_retrospective_text"),
        "development": ("teacher_perspective_text", "development_fields_text"),
        "goals": ("prepared_goals_text", "agreed_goals_text"),
        "agreements": ("prepared_support_text", "prepared_agreements_text", "agreed_support_text", "agreed_agreements_text", "responsibilities_text", "next_review_date"),
    }
    for phase, fields in expected_fields.items():
        phase_source = javascript.split(f"function {phase}Phase()", 1)[1].split("\n  function ", 1)[0]
        for field_name in fields:
            assert f'"{field_name}"' in phase_source
    assert '"prepared_support_text"' not in javascript.split("function goalsPhase()", 1)[1].split("\n  function ", 1)[0]


def test_html_evidence_filters_match_qt_period_and_unavailable_search_contract() -> None:
    javascript = _qrc_text(":/jkm-leg/app.js")

    assert "const hasCompletePeriod = Boolean(state.draft.period_start && state.draft.period_end);" in javascript
    assert 'row.dataset.searchText = String(observationId).toLocaleLowerCase("de");' in javascript
    assert 'row.hidden = Boolean(search && !row.dataset.searchText.includes(search));' in javascript


def test_close_probe_has_bounded_fail_closed_timeout() -> None:
    host_source = Path("src/desktop_app/leg_html/host.py").read_text(encoding="utf-8")

    assert "MAX_CLOSE_PROBE_ATTEMPTS = 500" in host_source
    assert "Lernentwicklungsgespräch bleibt geöffnet" in host_source
    assert "retry=True" in host_source


def test_final_pdf_projection_is_pathless_and_calls_python_viewer() -> None:
    session = _session()
    status = session.revision_status
    assert status is not None and status.revisions
    revision_id = status.revisions[0].learning_conference_revision_id
    artifact = LearningConferencePdfArtifactViewModel(
        "LCA-TEST-001",
        revision_id,
        "/private/secret/final.pdf",
        "Finales PDF",
        1234,
        "snapshot-secret",
        "pdf-hash-secret",
        "10.08.2026, 12:00",
    )
    session.artifacts_by_revision_id = {revision_id: artifact}
    opened: list[str] = []
    session.show_final_pdf = opened.append
    bridge = LearningConferenceHtmlBridge(session)

    state_text = bridge.initialState()
    state = json.loads(state_text)
    projected = state["revision_status"]["revisions"][0]["artifact"]
    assert projected == {
        "artifact_id": "LCA-TEST-001",
        "file_name": "Finales PDF",
        "created_at": "10.08.2026, 12:00",
    }
    assert "/private/secret" not in state_text
    assert "pdf-hash-secret" not in state_text
    result = json.loads(bridge.showFinalPdf("LCA-TEST-001"))
    assert result["code"] == "final_pdf_open_requested"
    assert opened == ["LCA-TEST-001"]
    assert json.loads(bridge.showFinalPdf("LCA-UNKNOWN"))["code"] == "final_pdf_unavailable"
    assert opened == ["LCA-TEST-001"]


def test_resources_csp_dom_navigation_and_request_policy_are_local_only() -> None:
    html = _qrc_text(":/jkm-leg/index.html")
    javascript = _qrc_text(":/jkm-leg/app.js")
    stylesheet = _qrc_text(":/jkm-leg/app.css")

    assert "connect-src 'none'" in html
    assert "'unsafe-inline'" not in html
    assert "'unsafe-eval'" not in html
    assert "http://" not in html + javascript
    assert "https://" not in html + javascript
    for forbidden in (
        "innerHTML",
        "insertAdjacentHTML",
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "eval(",
        "localStorage",
        "document.cookie",
        "window.close",
        ".accept(",
        ".reject(",
    ):
        assert forbidden not in javascript
    assert "[hidden] { display: none !important; }" in stylesheet
    assert 'phase.hidden = phase !== target' in javascript
    assert "savePending" in javascript
    host_source = Path("src/desktop_app/leg_html/host.py").read_text(encoding="utf-8")
    security_source = Path("src/desktop_app/web_ui/security.py").read_text(
        encoding="utf-8"
    )
    assert "configure_ephemeral_profile" in host_source
    assert "configure_restricted_page" in host_source
    assert "setCookieFilter(lambda _request: False)" in security_source
    for name in ("index.html", "app.js", "app.css"):
        assert _qrc_text(f":/jkm-leg/{name}") == Path(
            f"src/desktop_app/leg_html/static/{name}"
        ).read_text(encoding="utf-8")

    interceptor = LegLocalOnlyRequestInterceptor()
    assert interceptor.is_allowed(QUrl(INDEX_URL))
    assert interceptor.is_allowed(QUrl(QWEBCHANNEL_URL))
    assert not interceptor.is_allowed(QUrl("https://example.invalid/leg"))
    assert not interceptor.is_allowed(QUrl.fromLocalFile("/tmp/final.pdf"))
    assert not interceptor.is_allowed(QUrl("data:text/html,blocked"))


def test_qt_fallback_stays_default_and_webengine_import_is_lazy_in_shell() -> None:
    shell_source = Path("src/desktop_app/shell.py").read_text(encoding="utf-8")
    gate_source = Path("src/desktop_app/leg_ui.py").read_text(encoding="utf-8")

    assert 'values.get(LEG_UI_ENV, "qt")' in gate_source
    assert 'if selected_ui == "html":' in shell_source
    assert "dialog = LearningConferenceDialog(preparation, self, initial_draft)" in shell_source
    assert "from src.desktop_app.leg_html.host import" in shell_source
    assert "from PySide6.QtWebEngine" not in shell_source
    assert "_active_learning_conference_student_ids" in shell_source


def test_pyinstaller_spec_enables_official_webengine_dependency_hooks() -> None:
    spec = Path("packaging/macos_pilot.spec").read_text(encoding="utf-8")

    for module in (
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "src.desktop_app.leg_html.host",
        "src.desktop_app.leg_html.resources_rc",
    ):
        assert f'"{module}"' in spec
    excludes = spec.split("excludes=[", 1)[1].split("]", 1)[0]
    for required_dependency in (
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
    ):
        assert required_dependency not in excludes


@pytest.mark.skipif(
    os.environ.get("QT_QPA_PLATFORM") != "cocoa",
    reason="real WebEngine lifecycle requires visible macOS Cocoa",
)
def test_cocoa_host_keeps_dirty_draft_open_until_explicit_discard() -> None:
    from src.desktop_app.leg_html.host import LearningConferenceHtmlDialog

    app = QApplication.instance() or QApplication(sys.argv)
    bridge = LearningConferenceHtmlBridge(_session())
    host = LearningConferenceHtmlDialog(bridge)
    host.show()
    assert _wait_signal(host.loaded)
    assert _wait_until(
        lambda: _run_javascript(
            host,
            "Boolean(window.__jkmLegMetrics"
            " && window.__jkmLegMetrics.firstUsableMs !== null)",
        ) is True
    )
    assert _run_javascript(
        host,
        "(()=>{const input=document.querySelector('input[type=text]');"
        "input.value='DOM noch nicht gespeichert';"
        "input.dispatchEvent(new Event('input',{bubbles:true}));return true;})()",
    ) is True
    choices: list[str] = []
    host._close_choice_provider = lambda _parent: choices.append("asked") or "cancel"

    host.close()
    assert _wait_until(lambda: bool(choices))
    assert host.isVisible()
    assert bridge.is_dirty
    assert bridge.session.draft.responsible_teacher == "DOM noch nicht gespeichert"

    host._close_choice_provider = lambda _parent: "discard"
    host.close()
    assert _wait_until(lambda: not host.isVisible())
    assert not host.isVisible()
    host.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def _wait_signal(signal: object, timeout_ms: int = 10_000) -> bool:
    loop = QEventLoop()
    result = {"ok": False}

    def done(ok: bool) -> None:
        result["ok"] = ok
        loop.quit()

    signal.connect(done)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    return result["ok"]


def _wait_until(predicate: object, timeout_ms: int = 5_000) -> bool:
    loop = QEventLoop()
    result = {"ok": False}

    def check() -> None:
        if predicate():
            result["ok"] = True
            loop.quit()
        else:
            QTimer.singleShot(10, check)

    QTimer.singleShot(0, check)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    return result["ok"]


def _run_javascript(host: object, script: str) -> object:
    loop = QEventLoop()
    result: list[object] = []
    host.page.runJavaScript(script, lambda value: (result.append(value), loop.quit()))
    QTimer.singleShot(10_000, loop.quit)
    loop.exec()
    return result[0] if result else None


def _qrc_text(path: str) -> str:
    resource = QFile(path)
    assert resource.open(QIODevice.OpenModeFlag.ReadOnly)
    return bytes(resource.readAll()).decode("utf-8")
