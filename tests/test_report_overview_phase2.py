"""Pure Phase-2 projection tests without Qt, SQLite, or adapter integration."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportDraftViewModel,
)
from src.desktop_app.view_models.report_overview_view_model import (
    build_report_overview,
)


PERIOD_START = date(2026, 2, 1)
PERIOD_END = date(2026, 7, 31)


def _overview(
    *,
    selected_report_draft_id: str = "RPD-SELECTED",
    report_draft_ids: tuple[str, ...] = ("RPD-SELECTED",),
    phase2_period_start: object = PERIOD_START,
    phase2_period_end: object = PERIOD_END,
    observations: tuple[dict[str, object], ...] = (),
    reports: tuple[dict[str, object], ...] = (),
    learning_conferences: tuple[dict[str, object], ...] = (),
    confirmations: tuple[dict[str, object], ...] = (),
    subjects: tuple[dict[str, object], ...] = (),
    source_errors: tuple[str, ...] = (),
):
    drafts = tuple(
        LearningReportDraftViewModel(
            student_id="STU-1",
            period_start=PERIOD_START,
            period_end=PERIOD_END,
            report_draft_id=draft_id,
            updated_at="2026-07-01T08:00:00+00:00",
        )
        for draft_id in report_draft_ids
    )
    return build_report_overview(
        drafts,
        {},
        (),
        {},
        None,
        selected_report_draft_id=selected_report_draft_id,
        phase2_period_start=phase2_period_start,
        phase2_period_end=phase2_period_end,
        phase2_observations=observations,
        phase2_report_revisions=reports,
        phase2_learning_conference_revisions=learning_conferences,
        phase2_confirmations=confirmations,
        phase2_subjects=subjects,
        phase2_source_errors=source_errors,
    )


def _observation(
    observation_id: str,
    observed_on: object,
    *,
    subject_id: str = "math",
    assignments: tuple[dict[str, object], ...] = (),
    active: bool = True,
    **context: object,
) -> dict[str, object]:
    return {
        "observation_id": observation_id,
        "observed_on": observed_on,
        "subject_id": subject_id,
        "assignments": assignments,
        "active": active,
        **context,
    }


def _assignment(
    competency_id: str,
    subject_id: str,
    *,
    active: bool = True,
    catalog_status: str = "regular",
) -> dict[str, object]:
    return {
        "competency_id": competency_id,
        "subject_id": subject_id,
        "active": active,
        "catalog_status": catalog_status,
    }


def _report_revision(
    draft_id: str,
    revision_number: int,
    finalized_at: object,
    *,
    revision_id: str | None = None,
    hash_valid: bool = True,
    status: str = "finalized",
) -> dict[str, object]:
    return {
        "report_draft_id": draft_id,
        "learning_report_revision_id": (
            revision_id or f"RPV-{draft_id}-{revision_number}"
        ),
        "revision_number": revision_number,
        "finalized_at": finalized_at,
        "hash_valid": hash_valid,
        "status": status,
    }


def _leg_revision(
    draft_id: str,
    revision_number: int,
    conference_date: object,
    *,
    completed_at: object = "2099-12-31T23:59:59+00:00",
    revision_id: str | None = None,
    hash_valid: bool = True,
    status: str = "completed",
) -> dict[str, object]:
    return {
        "learning_conference_draft_id": draft_id,
        "learning_conference_revision_id": (
            revision_id or f"LCV-{draft_id}-{revision_number}"
        ),
        "revision_number": revision_number,
        "conference_date": conference_date,
        "completed_at": completed_at,
        "hash_valid": hash_valid,
        "status": status,
    }


def _confirmation(
    competency_id: str,
    confirmed_at: object,
    *,
    student_id: str = "STU-1",
    subject_id: str = "math",
    documentation_state: str = "confirmed",
    active: bool = True,
    catalog_status: str = "regular",
) -> dict[str, object]:
    return {
        "student_id": student_id,
        "competency_id": competency_id,
        "subject_id": subject_id,
        "competency_text": f"Kompetenz {competency_id}",
        "confirmed_at": confirmed_at,
        "documentation_state": documentation_state,
        "active": active,
        "catalog_status": catalog_status,
    }


SUBJECTS = (
    {"subject_id": "math", "subject_name": "Mathematik"},
    {"subject_id": "german", "subject_name": "Deutsch"},
    {"subject_id": "science", "subject_name": "Naturwissenschaften"},
)


def test_period_boundaries_are_inclusive_and_outside_events_are_excluded() -> None:
    overview = _overview(
        observations=(
            _observation("OBS-START", PERIOD_START),
            _observation("OBS-END", PERIOD_END),
            _observation("OBS-BEFORE", PERIOD_START - timedelta(days=1)),
            _observation("OBS-AFTER", PERIOD_END + timedelta(days=1)),
        ),
        subjects=SUBJECTS,
    )

    assert [event.source_identity for event in overview.timeline_events] == [
        ("observation", "OBS-START"),
        ("observation", "OBS-END"),
    ]


def test_cross_curricular_cards_have_evidence_but_no_subject_report_action() -> None:
    overview = _overview(
        subjects=(
            {
                "subject_id": "selbst_sozialkompetenz",
                "subject_name": "Selbst- und Sozialkompetenz",
            },
            {
                "subject_id": "arbeits_lernkompetenz",
                "subject_name": "Arbeits-/Lernkompetenz",
            },
            {"subject_id": "mathematik", "subject_name": "Mathematik"},
        ),
    )

    by_id = {subject.subject_id: subject for subject in overview.subject_documentation}
    assert by_id["selbst_sozialkompetenz"].evidence_action.label == "Belege ansehen"
    assert by_id["arbeits_lernkompetenz"].evidence_action.label == "Belege ansehen"
    assert by_id["selbst_sozialkompetenz"].prepare_action is None
    assert by_id["arbeits_lernkompetenz"].prepare_action is None
    assert by_id["mathematik"].prepare_action is not None
    assert by_id["mathematik"].prepare_action.label == "Bericht vorbereiten"


@pytest.mark.parametrize(
    ("period_start", "period_end", "warning_key"),
    (
        ("", PERIOD_END, "period_start_invalid"),
        (PERIOD_START, "", "period_end_invalid"),
        ("nicht-parsebar", PERIOD_END, "period_start_invalid"),
        (PERIOD_END, PERIOD_START, "period_end_before_start"),
    ),
)
def test_invalid_period_blocks_projection_neutrally(
    period_start: object,
    period_end: object,
    warning_key: str,
) -> None:
    overview = _overview(
        phase2_period_start=period_start,
        phase2_period_end=period_end,
        observations=(_observation("OBS-1", PERIOD_START),),
    )

    assert overview.timeline_events == ()
    assert overview.subject_documentation == ()
    assert warning_key in {
        warning.warning_key
        for warning in overview.projection_warnings
    }


def test_no_explicit_or_stale_rpd_selection_keeps_development_projection() -> None:
    event = _observation("OBS-1", PERIOD_START)

    no_selection = _overview(
        selected_report_draft_id="",
        observations=(event,),
    )
    stale_selection = _overview(
        selected_report_draft_id="RPD-STALE",
        observations=(event,),
    )

    assert [event.source_identity for event in no_selection.timeline_events] == [
        ("observation", "OBS-1")
    ]
    assert no_selection.projection_warnings == ()
    assert [event.source_identity for event in stale_selection.timeline_events] == [
        ("observation", "OBS-1")
    ]
    assert stale_selection.projection_warnings == ()


@pytest.mark.parametrize(
    ("draft_ids", "selected_id"),
    (
        ((), ""),
        (("RPD-SELECTED",), ""),
        (("RPD-A", "RPD-B"), ""),
    ),
)
def test_development_projection_is_identical_for_zero_one_or_many_drafts(
    draft_ids: tuple[str, ...],
    selected_id: str,
) -> None:
    overview = _overview(
        report_draft_ids=draft_ids,
        selected_report_draft_id=selected_id,
        phase2_period_start=date(2026, 8, 1),
        phase2_period_end=date(2027, 7, 31),
        observations=(
            _observation("OBS-IN", date(2026, 8, 1)),
            _observation("OBS-BEFORE", date(2026, 7, 31)),
            _observation("OBS-END", date(2027, 7, 31)),
            _observation("OBS-AFTER", date(2027, 8, 1)),
        ),
        subjects=SUBJECTS,
    )

    assert [event.source_identity for event in overview.timeline_events] == [
        ("observation", "OBS-IN"),
        ("observation", "OBS-END"),
    ]
    assert overview.selected_report_draft_id == ""
    assert [subject.subject_id for subject in overview.subject_documentation] == [
        "math",
        "german",
        "science",
    ]


def test_unparseable_observation_date_warns_without_removing_valid_events() -> None:
    overview = _overview(
        observations=(
            _observation("OBS-BROKEN", "kein-datum"),
            _observation("OBS-VALID", PERIOD_START),
        ),
    )

    assert [event.source_identity for event in overview.timeline_events] == [
        ("observation", "OBS-VALID")
    ]
    assert {
        warning.warning_key
        for warning in overview.projection_warnings
    } == {"observation_date_invalid:OBS-BROKEN"}


def test_one_observation_with_multiple_assignments_is_one_neutral_event() -> None:
    overview = _overview(
        observations=(
            _observation(
                "OBS-1",
                "2026-04-03",
                assignments=(
                    _assignment("CMP-1", "math"),
                    _assignment("CMP-2", "math"),
                ),
                competency_area="Zahlen",
                topic="Brüche",
                context="Lernzeit",
            ),
        ),
        subjects=SUBJECTS,
    )

    assert len(overview.timeline_events) == 1
    event = overview.timeline_events[0]
    assert event.source_identity == ("observation", "OBS-1")
    assert "2 Kompetenzen zugeordnet" in event.detail_text
    assert "Zahlen" in event.detail_text
    assert "Brüche" in event.detail_text
    assert "Lernzeit" in event.detail_text


def test_report_aggregate_uses_only_latest_valid_revision() -> None:
    overview = _overview(
        reports=(
            _report_revision(
                "RPD-A",
                1,
                "2026-03-01T10:00:00+01:00",
                status="superseded",
            ),
            _report_revision(
                "RPD-A",
                2,
                "2026-04-01T10:00:00+02:00",
                revision_id="RPV-LATEST",
            ),
            _report_revision(
                "RPD-A",
                3,
                "2026-05-01T10:00:00+02:00",
                revision_id="RPV-BROKEN",
                hash_valid=False,
            ),
        ),
    )

    assert len(overview.timeline_events) == 1
    event = overview.timeline_events[0]
    assert event.source_identity == ("report", "RPD-A")
    assert event.date_label == "01.04.2026"
    assert event.action is not None
    assert event.action.target_id == "RPV-LATEST"
    assert "report_revision_invalid:RPD-A" in {
        warning.warning_key
        for warning in overview.projection_warnings
    }


def test_leg_aggregate_uses_conference_date_not_completed_at() -> None:
    overview = _overview(
        learning_conferences=(
            _leg_revision(
                "LCD-A",
                1,
                "2026-03-02",
                completed_at="2026-03-20T10:00:00+01:00",
                status="superseded",
            ),
            _leg_revision(
                "LCD-A",
                2,
                "2026-05-06",
                completed_at="2099-12-31T23:59:59+00:00",
                revision_id="LCV-LATEST",
            ),
        ),
    )

    assert len(overview.timeline_events) == 1
    event = overview.timeline_events[0]
    assert event.source_identity == ("learning_conference", "LCD-A")
    assert event.date_label == "06.05.2026"
    assert event.action is not None
    assert event.action.target_id == "LCV-LATEST"


def test_only_current_safe_confirmation_creates_an_event() -> None:
    overview = _overview(
        confirmations=(
            _confirmation("CMP-SAFE", "2026-03-01"),
            _confirmation(
                "CMP-UNKNOWN",
                "2026-03-02",
                documentation_state="confirmation_unknown",
            ),
            _confirmation(
                "CMP-HIST",
                "2026-03-03",
                catalog_status="historical",
            ),
            _confirmation(
                "CMP-INACTIVE",
                "2026-03-04",
                active=False,
            ),
        ),
    )

    assert [event.source_identity for event in overview.timeline_events] == [
        ("confirmation", "STU-1", "CMP-SAFE")
    ]


def test_equal_dates_use_stable_source_identity_order() -> None:
    overview = _overview(
        observations=(
            _observation("OBS-B", "2026-05-01"),
            _observation("OBS-A", "2026-05-01"),
        ),
        confirmations=(
            _confirmation("CMP-B", "2026-05-01"),
            _confirmation("CMP-A", "2026-05-01"),
        ),
    )

    assert [event.source_identity for event in overview.timeline_events] == [
        ("confirmation", "STU-1", "CMP-A"),
        ("confirmation", "STU-1", "CMP-B"),
        ("observation", "OBS-A"),
        ("observation", "OBS-B"),
    ]


@pytest.mark.parametrize("event_count", (0, 1, 14, 15))
def test_timeline_can_remain_below_or_reach_target_without_artificial_events(
    event_count: int,
) -> None:
    observations = tuple(
        _observation(
            f"OBS-{index:02d}",
            PERIOD_START + timedelta(days=index),
        )
        for index in range(event_count)
    )

    overview = _overview(observations=observations)

    assert len(overview.timeline_events) == event_count
    assert all(
        event.event_type == "observation"
        for event in overview.timeline_events
    )


def test_more_than_fifteen_document_events_all_remain_without_supplements() -> None:
    reports = tuple(
        _report_revision(
            f"RPD-{index:02d}",
            1,
            PERIOD_START + timedelta(days=index),
        )
        for index in range(16)
    )
    overview = _overview(
        reports=reports,
        observations=(_observation("OBS-IGNORED", PERIOD_END),),
        confirmations=(_confirmation("CMP-IGNORED", PERIOD_END),),
    )

    assert len(overview.timeline_events) == 16
    assert all(event.event_type == "report" for event in overview.timeline_events)


def test_documents_are_kept_and_newest_supplements_fill_remaining_capacity() -> None:
    reports = tuple(
        _report_revision(
            f"RPD-{index:02d}",
            1,
            PERIOD_START + timedelta(days=index),
        )
        for index in range(13)
    )
    observations = tuple(
        _observation(
            f"OBS-{index}",
            date(2026, 6, 1) + timedelta(days=index),
        )
        for index in range(4)
    )
    overview = _overview(reports=reports, observations=observations)

    identities = [event.source_identity for event in overview.timeline_events]
    assert len(identities) == 15
    assert sum(identity[0] == "report" for identity in identities) == 13
    assert ("observation", "OBS-3") in identities
    assert ("observation", "OBS-2") in identities
    assert ("observation", "OBS-0") not in identities
    assert [event.occurred_on for event in overview.timeline_events] == sorted(
        event.occurred_on
        for event in overview.timeline_events
    )


def test_subject_competencies_deduplicate_across_observations() -> None:
    overview = _overview(
        observations=(
            _observation(
                "OBS-1",
                "2026-03-01",
                assignments=(_assignment("CMP-1", "math"),),
            ),
            _observation(
                "OBS-2",
                "2026-03-02",
                assignments=(_assignment("CMP-1", "math"),),
            ),
        ),
        subjects=SUBJECTS,
    )

    math = overview.subject_documentation[0]
    assert math.competency_ids == ("CMP-1",)
    assert math.observation_ids == ("OBS-1", "OBS-2")
    assert math.competency_count_text == "1 Kompetenz dokumentiert"


def test_quick_observation_counts_without_creating_a_competency_segment() -> None:
    overview = _overview(
        observations=(_observation("OBS-QUICK", "2026-03-01"),),
        subjects=SUBJECTS,
    )

    math = overview.subject_documentation[0]
    assert math.competency_ids == ()
    assert math.observation_ids == ("OBS-QUICK",)
    assert math.observation_count_text == "1 Beobachtung im aktuellen Schuljahr"


def test_subject_card_shows_only_existing_neutral_confirmation_information() -> None:
    overview = _overview(
        confirmations=(
            _confirmation("CMP-MATH", "2026-03-01", subject_id="math"),
        ),
        subjects=SUBJECTS,
    )

    math, german, science = overview.subject_documentation
    assert math.confirmation_count_text == (
        "Aktuell bestätigter Stand für 1 Kompetenz vorhanden"
    )
    assert german.confirmation_count_text == ""
    assert science.confirmation_count_text == ""


def test_multi_subject_observation_counts_once_per_actual_subject_and_once_globally() -> None:
    overview = _overview(
        observations=(
            _observation(
                "OBS-MULTI",
                "2026-03-01",
                subject_id="science",
                assignments=(
                    _assignment("CMP-MATH", "math"),
                    _assignment("CMP-GERMAN", "german"),
                    _assignment("CMP-MATH-2", "math"),
                ),
            ),
        ),
        subjects=SUBJECTS,
    )

    math, german, science = overview.subject_documentation
    assert math.observation_ids == ("OBS-MULTI",)
    assert german.observation_ids == ("OBS-MULTI",)
    assert science.observation_ids == ()
    assert len(overview.timeline_events) == 1


def test_assignments_disable_observation_subject_fallback() -> None:
    overview = _overview(
        observations=(
            _observation(
                "OBS-1",
                "2026-03-01",
                subject_id="math",
                assignments=(_assignment("CMP-1", "german"),),
            ),
        ),
        subjects=SUBJECTS,
    )

    math, german, _science = overview.subject_documentation
    assert math.observation_ids == ()
    assert german.observation_ids == ("OBS-1",)


def test_without_assignments_only_observation_subject_is_used() -> None:
    overview = _overview(
        observations=(
            _observation(
                "OBS-1",
                "2026-03-01",
                subject_id="german",
            ),
        ),
        subjects=SUBJECTS,
    )

    math, german, _science = overview.subject_documentation
    assert math.observation_ids == ()
    assert german.observation_ids == ("OBS-1",)


def test_cross_subject_never_creates_a_subject_card_or_counter() -> None:
    overview = _overview(
        observations=(
            _observation(
                "OBS-CROSS",
                "2026-03-01",
                subject_id="cross_subject",
            ),
        ),
        subjects=(
            *SUBJECTS,
            {"subject_id": "cross_subject", "subject_name": "Fächerübergreifend"},
        ),
    )

    assert [
        subject.subject_id
        for subject in overview.subject_documentation
    ] == ["math", "german", "science"]
    assert all(
        not subject.observation_ids
        for subject in overview.subject_documentation
    )


def test_historical_and_inactive_competencies_are_not_current_segments() -> None:
    overview = _overview(
        observations=(
            _observation(
                "OBS-1",
                "2026-03-01",
                assignments=(
                    _assignment(
                        "CMP-HIST",
                        "math",
                        catalog_status="historical",
                    ),
                    _assignment("CMP-INACTIVE", "math", active=False),
                    _assignment("CMP-CURRENT", "math"),
                ),
            ),
        ),
        confirmations=(_confirmation("CMP-ONLY-CONFIRM", "2026-03-02"),),
        subjects=SUBJECTS,
    )

    math = overview.subject_documentation[0]
    assert math.competency_ids == ("CMP-CURRENT",)
    assert math.observation_ids == ("OBS-1",)


def test_subject_order_is_canonical_and_never_quantity_sorted() -> None:
    overview = _overview(
        observations=(
            _observation(
                "OBS-1",
                "2026-03-01",
                assignments=(
                    _assignment("CMP-1", "science"),
                    _assignment("CMP-2", "science"),
                    _assignment("CMP-3", "science"),
                ),
            ),
        ),
        subjects=SUBJECTS,
    )

    assert [
        subject.subject_id
        for subject in overview.subject_documentation
    ] == ["math", "german", "science"]


def test_warning_projection_is_neutral_and_deduplicated() -> None:
    overview = _overview(
        source_errors=("live_read", "live_read", "report_read"),
    )

    assert [
        warning.warning_key
        for warning in overview.projection_warnings
    ] == ["source:live_read", "source:report_read"]
    assert all(
        warning.text
        == "Dokumentationsdaten konnten nicht vollständig gelesen werden."
        for warning in overview.projection_warnings
    )
    forbidden = (
        "Stärke",
        "Schwäche",
        "Defizit",
        "Förderbedarf",
        "Trend",
        "Priorität",
    )
    assert all(
        term not in warning.text
        for warning in overview.projection_warnings
        for term in forbidden
    )
