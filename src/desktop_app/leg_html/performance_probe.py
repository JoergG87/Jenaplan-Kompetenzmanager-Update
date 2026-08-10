"""Visible Cocoa timing probe for the gated production LEG HTML host."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import sqlite3
from statistics import median
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid

from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from tests.helpers.synthetic_v4 import (
    SYNTHETIC_LEG_DRAFT_ID,
    SYNTHETIC_STUDENT_IDS,
    create_synthetic_v4_database,
)
from .bridge import LearningConferenceHtmlBridge, LearningConferenceHtmlSession
from .host import LearningConferenceHtmlDialog


PHASES = ("strengths", "development", "goals", "evidence", "agreements", "goal")


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    with TemporaryDirectory(prefix="jkm-leg-html-v4-") as directory:
        bridge_factory, projection_ms, projected_competencies = _final_v4_bridge_factory(Path(directory))
        result = _measure(app, bridge_factory, projected_competencies)
    result["final_v4_source_projection_ms"] = round(projection_ms, 2)
    target_met = (
        float(result["host_to_usable_ms_median"]) < 2000
        and float(result["dom_phase_change_ms_max"]) < 1000
        and float(result["dom_evidence_first_build_ms_median"]) < 2000
    )
    result["no_multi_second_blockade_target_met"] = target_met
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if target_met else 1


def _final_v4_bridge_factory(
    root: Path,
) -> tuple[object, float, int]:
    database = create_synthetic_v4_database(root / "leg-html-performance.sqlite")
    _seed_large_final_v4_catalog(database)
    adapter = StudentDesktopAdapter(
        database,
        database_create_allowed=False,
        today_provider=lambda: date(2026, 8, 10),
    )
    draft = adapter.load_learning_conference_draft(SYNTHETIC_LEG_DRAFT_ID)
    if draft is None:
        raise RuntimeError("synthetic_final_v4_leg_draft_missing")
    projection_started = perf_counter()
    preparation = adapter.learning_conference_preparation_for_student(
        SYNTHETIC_STUDENT_IDS[0],
        conference_date=draft.conference_date,
        retained_competency_ids=draft.competency_ids,
    )
    projection_ms = (perf_counter() - projection_started) * 1000
    if preparation is None or not preparation.subjects:
        raise RuntimeError("synthetic_final_v4_leg_preparation_missing")
    competency_count = sum(len(subject.competencies) for subject in preparation.subjects)
    if competency_count < 960:
        raise RuntimeError(f"synthetic_final_v4_competency_count:{competency_count}")
    workload_draft = replace(
        draft,
        subject_ids=tuple(subject.subject_id for subject in preparation.subjects),
        competency_ids=(),
    )

    def factory() -> LearningConferenceHtmlBridge:
        return LearningConferenceHtmlBridge(
            LearningConferenceHtmlSession(
                preparation=preparation,
                draft=workload_draft,
                revision_status=None,
                save_draft=None,
            )
        )

    return factory, projection_ms, competency_count


def _seed_large_final_v4_catalog(database: Path) -> None:
    rows = []
    for subject_index in range(3):
        subject_id = "SUB-TEST-DE" if subject_index == 0 else f"PERF-SUBJECT-{subject_index + 1}"
        subject_name = "Testsprache" if subject_index == 0 else f"Synthetisches Fach {subject_index + 1}"
        first_index = 1 if subject_index == 0 else 0
        for index in range(first_index, 320):
            rows.append(
                (
                    f"PERF-COMP-{subject_index + 1}-{index + 1:04d}",
                    subject_id,
                    subject_name,
                    subject_name,
                    subject_name,
                    "Testkontext",
                    "1-3",
                    f"Synthetische Kompetenz {index + 1}",
                    "Ausschließlich für den technischen Performance-Nachweis.",
                    "stage_1_3",
                    f"Kompetenzbereich {index // 80 + 1}",
                    f"Thema {index // 20 + 1}",
                    "SYNTHETIC-PERFORMANCE",
                    "current",
                    "PERFORMANCE",
                    subject_index * 320 + index,
                    1,
                    1,
                    1,
                )
            )
    with sqlite3.connect(database) as connection:
        connection.executemany(
            """
            INSERT INTO competencies(
                competency_id, subject_id, subject_name, subject_full_name,
                official_subject_name, school_context_name, grade_band,
                label, description, learning_stage, learning_area,
                competency_group, source_reference, catalog_status,
                activation_group_key, sort_order, active,
                catalog_default_active, is_core_subject
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _measure(
    app: QApplication,
    bridge_factory: object,
    projected_competencies: int,
) -> dict[str, object]:
    loads: list[float] = []
    first_usable: list[float] = []
    phase_changes: list[float] = []
    evidence_builds: list[float] = []
    repeated_evidence: list[float] = []
    navigation_integrity: list[bool] = []
    surface_visibility: list[bool] = []
    for _cycle in range(5):
        started = perf_counter()
        host = LearningConferenceHtmlDialog(bridge_factory())
        host.resize(1400, 900)
        host.show()
        if not _wait_loaded(host) or not _wait_ready(host):
            raise RuntimeError("leg_html_load_timeout")
        loads.append((perf_counter() - started) * 1000)
        surface_visibility.append(bool(_javascript(
            host,
            "getComputedStyle(document.getElementById('loading')).display === 'none'"
            " && !document.getElementById('app').hidden",
        )))
        for phase in PHASES:
            _javascript(host, f"window.__jkmLegActivatePhase('{phase}')")
            if phase == "evidence" and not _wait_evidence_ready(host):
                raise RuntimeError("leg_html_evidence_timeout")
            visible_count = _javascript(
                host,
                "document.querySelectorAll('[data-phase]:not([hidden])').length",
            )
            navigation_integrity.append(float(visible_count) == 1.0 and host.isVisible())
        repeated_started = perf_counter()
        _javascript(host, "window.__jkmLegActivatePhase('evidence')")
        repeated_evidence.append((perf_counter() - repeated_started) * 1000)
        raw_metrics = _javascript(host, "JSON.stringify(window.__jkmLegMetrics)")
        metrics = json.loads(raw_metrics) if isinstance(raw_metrics, str) else raw_metrics
        first_usable.append(float(metrics["firstUsableMs"]))
        phase_changes.extend(float(value) for value in metrics["navigationSamples"])
        if metrics["evidenceBuildMs"] is not None:
            evidence_builds.append(float(metrics["evidenceBuildMs"]))
        host._close_authorized = True
        page = host.page
        profile = host.profile
        host.close()
        _drain_events()
        if not host._disposed:
            raise RuntimeError("leg_html_webengine_not_disposed")
        if isValid(page) or isValid(profile):
            raise RuntimeError("leg_html_webengine_objects_still_valid")
        host.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        _drain_events()
    return {
        "cycles": len(loads),
        "persisted_catalog_competencies": 960,
        "projected_competencies": projected_competencies,
        "source_database": "exact_synthetic_final_v4",
        "host_to_usable_ms_median": round(median(loads), 2),
        "dom_first_usable_ms_median": round(median(first_usable), 2),
        "dom_phase_change_ms_median": round(median(phase_changes), 3),
        "dom_phase_change_ms_max": round(max(phase_changes), 3),
        "dom_evidence_first_build_ms_median": round(median(evidence_builds), 2),
        "repeated_evidence_roundtrip_ms_median": round(median(repeated_evidence), 2),
        "one_visible_phase_and_host_open": all(navigation_integrity),
        "loading_hidden_and_surface_visible": all(surface_visibility),
    }


def _wait_loaded(host: LearningConferenceHtmlDialog) -> bool:
    loop = QEventLoop()
    result = {"ok": False}

    def finished(ok: bool) -> None:
        result["ok"] = ok
        loop.quit()

    host.loaded.connect(finished)
    QTimer.singleShot(15_000, loop.quit)
    loop.exec()
    return bool(result["ok"])


def _wait_ready(host: LearningConferenceHtmlDialog) -> bool:
    loop = QEventLoop()
    result = {"ready": False}

    def check() -> None:
        host.page.runJavaScript(
            "Boolean(window.__jkmLegMetrics"
            " && window.__jkmLegMetrics.firstUsableMs !== null)",
            checked,
        )

    def checked(ready: object) -> None:
        if bool(ready):
            result["ready"] = True
            loop.quit()
        else:
            QTimer.singleShot(10, check)

    QTimer.singleShot(0, check)
    QTimer.singleShot(15_000, loop.quit)
    loop.exec()
    return result["ready"]


def _wait_evidence_ready(host: LearningConferenceHtmlDialog) -> bool:
    loop = QEventLoop()
    result = {"ready": False}

    def check() -> None:
        host.page.runJavaScript(
            "Boolean(window.__jkmLegMetrics.evidenceBuildMs !== null)",
            checked,
        )

    def checked(ready: object) -> None:
        if bool(ready):
            result["ready"] = True
            loop.quit()
        else:
            QTimer.singleShot(10, check)

    QTimer.singleShot(0, check)
    QTimer.singleShot(15_000, loop.quit)
    loop.exec()
    return result["ready"]


def _javascript(host: LearningConferenceHtmlDialog, script: str) -> object:
    loop = QEventLoop()
    result: list[object] = []

    def finished(value: object) -> None:
        result.append(value)
        loop.quit()

    host.page.runJavaScript(script, finished)
    QTimer.singleShot(10_000, loop.quit)
    loop.exec()
    if not result:
        raise RuntimeError("leg_html_javascript_timeout")
    return result[0]


def _drain_events() -> None:
    loop = QEventLoop()
    QTimer.singleShot(50, loop.quit)
    loop.exec()


if __name__ == "__main__":
    raise SystemExit(main())
