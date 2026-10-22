"""Focused aggregate and existing-chip regressions; no persistence involved."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from dataclasses import replace
from types import SimpleNamespace
import pytest
from PySide6.QtWidgets import QApplication, QLabel, QWidget
from src.desktop_app.view_models.observation_view_model import (
    StudentCompetencyStatusViewModel, build_student_competency_cockpit,
    subject_development_stage, calculated_rating_from_history,
)
from src.desktop_app.view_models.report_overview_view_model import (
    ReportOverviewSubjectDocumentationViewModel, ReportOverviewActionViewModel,
)
from src.desktop_app.screens.student_profile_screen import StudentProfileScreen


def status(key="C1", token="+", **changes):
    return replace(StudentCompetencyStatusViewModel(
        key, key, "math", "Mathematik", token, token, "2026-10-22", 1,
        observed_proposal=token, documentation_state="observed_unconfirmed",
        is_active=True, catalog_status="current", learning_area="Zahlen",
        competency_group="Rechnen",
    ), **changes)


def subject(*rows):
    return build_student_competency_cockpit(rows).subjects[0]


def test_average_only_rated_current_competencies():
    assert subject_development_stage(subject(
        status(token="--"), status("C2", "++"),
        status("C3", "", documentation_state="undocumented"),
    )) == 3  # Existing 1.5 threshold maps to +.


def test_confirmation_precedes_newer_proposal():
    assert subject_development_stage(subject(status(
        token="--", confirmed_rating="++", documentation_state="newer_observations",
    ))) == 4


def test_history_is_one_current_state_and_identity_is_counted_once():
    token, score = calculated_rating_from_history(("++", "--", "--"))
    row = status(token=token, weighted_score=score,
                 rating_history=("--", "--", "++"), observation_count=3)
    original = subject(row, status("C2", "++"))
    area = original.learning_areas[0]
    topic = area.topics[0]
    duplicated = replace(original, learning_areas=(replace(
        area, topics=(replace(topic, competencies=topic.competencies + (row,)),)),))
    assert subject_development_stage(duplicated) == subject_development_stage(original)


@pytest.mark.parametrize("changes", [
    dict(documentation_state="undocumented", observed_proposal=""),
    dict(documentation_state="confirmation_unknown"),
    dict(observed_proposal="invalid"),
    dict(missing_catalog_reference=True),
])
def test_missing_or_invalid_state_is_neutral(changes):
    assert subject_development_stage(subject(status(**changes))) is None
    assert subject_development_stage(None) is None


def test_historical_and_inactive_do_not_contribute():
    current = subject(status(token="++"))
    area = current.learning_areas[0]
    topic = area.topics[0]
    rows = topic.competencies + (status("C2", "--", historical=True),
                                status("C3", "--", is_active=False))
    current = replace(current, learning_areas=(replace(
        area, topics=(replace(topic, competencies=rows),)),))
    assert subject_development_stage(current) == 4


def tile_subject(key):
    return ReportOverviewSubjectDocumentationViewModel(
        key, "Fach " + key, ("C1",), ("O1",), "1 Kompetenz dokumentiert",
        "1 Beobachtung im aktuellen Schuljahr", "Fach " + key,
        ReportOverviewActionViewModel("show_subject_evidence", "Belege ansehen", key, key),
        None,
    )


def test_all_chips_keep_information_actions_and_small_plant_after_refresh():
    app = QApplication.instance() or QApplication([])
    screen = StudentProfileScreen()
    screen.set_competency_cockpit(build_student_competency_cockpit((status(),)))
    screen.current_student = SimpleNamespace(student_id="STU-1")
    subjects = tuple(tile_subject(key) for key in ("math", "german", "art", "music", "sport", "english"))
    overview = type("Overview", (), dict(subject_documentation=subjects, projection_warnings=()))()
    screen.current_report_overview = overview
    screen._report_subjects_expanded = True
    screen._render_report_subjects(overview)
    plants = screen.findChildren(QLabel, "ReportOverviewSubjectPlant")
    assert len(plants) == 6
    plant = next(p for p in plants if p.property("subject_id") == "math")
    assert plant.property("development_stage") == 3
    assert not plant.pixmap().isNull()
    assert plant.width() == plant.height() == 32
    neutral = next(p for p in plants if p.property("subject_id") == "german")
    assert neutral.property("development_stage") is None
    assert "Keine bewerteten" in neutral.toolTip()
    tile = plant.parentWidget()
    tile.resize(260, tile.sizeHint().height())
    tile.layout().activate()
    for label in tile.findChildren(QLabel):
        if label is not plant and label.parentWidget() is tile:
            assert not plant.geometry().intersects(label.geometry())
    button = screen.findChild(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton,
                              "ReportOverviewEvidenceSubject_math")
    button.click()
    assert screen.competency_subject_filter.currentData() == "math"
    assert "1 Kompetenz dokumentiert" in [p.text() for p in tile.findChildren(QLabel)]
    screen.set_competency_cockpit(build_student_competency_cockpit((status(token="--"),)))
    app.processEvents()
    refreshed = screen.findChildren(QLabel, "ReportOverviewSubjectPlant")
    assert len(refreshed) == 6
    assert next(p for p in refreshed if p.property("subject_id") == "math").property("development_stage") == 1
    screen.close()
