from __future__ import annotations

from collections import Counter
from contextlib import closing
import csv
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from src.core.final_v4_schema import FinalV4SchemaInitializer
from src.core.sqlite_store import SQLiteCompetencyRepository, SQLiteDatabase
from src.desktop_app.adapters.curriculum_desktop_adapter import (
    CurriculumDesktopAdapter,
    DOCUMENTATION_SUBJECT_PREFERRED_ORDER,
)
from src.desktop_app.dialogs.new_observation_dialog import ObservationRatingSelector
from src.desktop_app.view_models.observation_view_model import (
    OBSERVATION_RATING_OPTIONS,
    OBSERVATION_RATING_TOKENS,
    rating_chip_options_for_competency,
    rating_profile_for_competency,
)
from src.security.cipher_product_runtime import (
    PILOT_FIRST_RUN_SCHOOL_YEAR_END,
    PILOT_FIRST_RUN_SCHOOL_YEAR_ID,
    PILOT_FIRST_RUN_SCHOOL_YEAR_LABEL,
    PILOT_FIRST_RUN_SCHOOL_YEAR_START,
)


CATALOG_PATH = Path("data/curriculum_catalog_v1.csv")
INVENTORY_PATH = Path("data/entwicklungsbuch_catalog_inventory_v1.csv")

EXPECTED_SUBJECTS = (
    "selbst_sozialkompetenz",
    "arbeits_lernkompetenz",
    "epu",
    "deutsch",
    "mathematik",
    "kreatives_gestalten",
    "sport",
    "ethik",
    "religion",
    "musik",
    "englisch",
    "schulgarten",
)


def _read(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as stream:
        return tuple(csv.DictReader(stream, delimiter=";"))


def _entry(subject_key: str) -> object:
    return next(
        entry
        for entry in CurriculumDesktopAdapter().list_entries()
        if entry.subject_key == subject_key
    )


def test_catalog_is_only_the_new_entwicklungsbuch_catalog_in_source_order() -> None:
    rows = _read(CATALOG_PATH)
    subject_order = tuple(dict.fromkeys(row["subject_key"] for row in rows))

    assert len(rows) == 331
    assert subject_order == EXPECTED_SUBJECTS
    assert DOCUMENTATION_SUBJECT_PREFERRED_ORDER == EXPECTED_SUBJECTS
    assert all(row["competency_id"].startswith("CMP-100") for row in rows)
    assert all(row["catalog_status"] == "current" for row in rows)
    assert all(row["catalog_default_active"] == "true" for row in rows)
    assert all(row["is_active"] == "true" for row in rows)
    assert all(row["source_reference"].startswith(
        "Entwicklungsbuch Jenaplanschule Erfurt, S. "
    ) for row in rows)


def test_catalog_has_no_duplicates_empty_competencies_or_documentation_rows() -> None:
    rows = _read(CATALOG_PATH)
    identities = tuple(
        (
            row["subject_key"],
            row["learning_area"],
            row["competency_group"],
            row["competency_text"],
        )
        for row in rows
    )
    texts = {row["competency_text"] for row in rows}

    assert len({row["competency_id"] for row in rows}) == len(rows)
    assert len(set(identities)) == len(rows)
    assert all(all(value.strip() for value in identity) for identity in identities)
    assert "Kennenlernen verschiedener Künstler und deren Werke" not in texts
    assert "Behandelte Musikstücke/ musikalische Werke" not in texts
    assert "Name, Alter, Wohnort" not in texts
    assert "Mein Körper" not in texts
    assert "Hobbies" not in texts


def test_catalog_learning_stage_report_is_uniform_cross_stage() -> None:
    rows = _read(CATALOG_PATH)
    expected_by_subject = {
        "Selbst- und Sozialkompetenz": 8,
        "Arbeits-/Lernkompetenz": 13,
        "EPU": 6,
        "Deutsch": 41,
        "Mathematik": 67,
        "Kreatives Gestalten": 34,
        "Sport": 64,
        "Ethik": 30,
        "Religion": 20,
        "Musik": 29,
        "Englisch": 11,
        "Schulgarten": 8,
    }

    assert Counter(row["learning_stage"] for row in rows) == {
        "cross_stage": 331
    }
    assert Counter(row["subject_display_name"] for row in rows) == (
        expected_by_subject
    )
    assert all(row["grade_band"] == "1-4" for row in rows)


def test_inventory_accounts_for_every_catalog_row_and_exclusion() -> None:
    catalog = _read(CATALOG_PATH)
    inventory = _read(INVENTORY_PATH)
    competencies = tuple(
        row for row in inventory if row["entry_type"] == "competency"
    )
    exclusions = tuple(
        row for row in inventory if row["entry_type"] == "excluded_documentation"
    )

    assert len(competencies) == len(catalog) == 331
    assert {row["competency_id"] for row in competencies} == {
        row["competency_id"] for row in catalog
    }
    assert len(exclusions) == 23
    assert all(row["decision_reason"].strip() for row in exclusions)
    assert {
        row["learning_area"] for row in exclusions
    } == {
        "Kunstbetrachtung",
        "Behandelte Musikstücke/ musikalische Werke",
        "Behandelte Themen im Englischunterricht",
    }


def test_inventory_profiles_match_the_central_resolver() -> None:
    inventory_by_id = {
        row["competency_id"]: row
        for row in _read(INVENTORY_PATH)
        if row["entry_type"] == "competency"
    }

    for entry in CurriculumDesktopAdapter().list_entries():
        assert inventory_by_id[entry.competency_id]["rating_profile"] == (
            rating_profile_for_competency(entry)
        )


def test_rating_profiles_keep_tokens_and_standard_labels() -> None:
    standard = rating_chip_options_for_competency(_entry("deutsch"))
    social = dict(rating_chip_options_for_competency(
        _entry("selbst_sozialkompetenz")
    ))
    sport = dict(rating_chip_options_for_competency(_entry("sport")))

    assert tuple(token for token, _label in standard) == OBSERVATION_RATING_TOKENS
    assert tuple(label for _token, label in standard) == OBSERVATION_RATING_OPTIONS
    assert tuple(social[token] for token in ("--", "-", "+", "++")) == (
        "Kaum vorhanden", "Teilweise", "Gut", "Ausgeprägt",
    )
    assert tuple(sport[token] for token in ("--", "-", "+", "++")) == (
        "Erste Übungen", "Übt noch", "Meist", "Sicher",
    )
    assert not any("Level " in label for _token, label in standard)


@pytest.mark.parametrize(
    "subject_key,expected_labels",
    (
        ("selbst_sozialkompetenz", {"--": "Kaum vorhanden", "++": "Ausgeprägt"}),
        ("sport", {"--": "Erste Übungen", "++": "Sicher"}),
        ("deutsch", {"--": "-- Unterstützungsbedarf", "++": "++ sicher erreicht"}),
        ("mathematik", {"--": "-- Unterstützungsbedarf", "++": "++ sicher erreicht"}),
    ),
)
def test_observation_selector_uses_profile_and_shared_color_tokens(
    subject_key: str,
    expected_labels: dict[str, str],
) -> None:
    QApplication.instance() or QApplication([])
    selector = ObservationRatingSelector("+", _entry(subject_key))

    assert selector.currentData() == "+"
    for token, expected_label in expected_labels.items():
        button = selector.buttons[token]
        assert button.text() == expected_label
        assert button.property("rating") == token
        assert button.property("ratingToken") == token


def test_profile_switch_relabels_without_changing_persistent_value() -> None:
    QApplication.instance() or QApplication([])
    selector = ObservationRatingSelector("-", _entry("deutsch"))

    selector.set_competency(_entry("selbst_sozialkompetenz"))
    assert selector.currentData() == "-"
    assert selector.buttons["-"].text() == "✓ Teilweise"

    selector.set_competency(_entry("sport"))
    assert selector.currentData() == "-"
    assert selector.buttons["-"].text() == "✓ Übt noch"


def test_fresh_v4_seed_has_new_catalog_and_no_synthetic_work_data(
    tmp_path: Path,
) -> None:
    path = tmp_path / "fresh-v4.sqlite"
    FinalV4SchemaInitializer().initialize(path)
    database = SQLiteDatabase(path, create=False)
    SQLiteCompetencyRepository(database).ensure_catalog_defaults(
        CurriculumDesktopAdapter().list_entries()
    )
    with closing(database.connect()) as connection:
        connection.execute(
            """
            INSERT INTO school_years (
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES (?, ?, ?, ?, 'current', '2026-08-11T00:00:00Z', NULL)
            """,
            (
                PILOT_FIRST_RUN_SCHOOL_YEAR_ID,
                PILOT_FIRST_RUN_SCHOOL_YEAR_LABEL,
                PILOT_FIRST_RUN_SCHOOL_YEAR_START.isoformat(),
                PILOT_FIRST_RUN_SCHOOL_YEAR_END.isoformat(),
            ),
        )
        connection.commit()

        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        assert connection.execute("SELECT COUNT(*) FROM competencies").fetchone()[0] == 331
        assert connection.execute(
            "SELECT label FROM school_years WHERE status = 'current'"
        ).fetchone()[0] == "2026/27"
        for table in (
            "students", "groups", "courses", "student_school_year_assignments",
            "observations", "report_drafts", "learning_conference_drafts",
        ):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0

    SQLiteCompetencyRepository(database).ensure_catalog_defaults(
        CurriculumDesktopAdapter().list_entries()
    )
    assert len(SQLiteCompetencyRepository(database).list_competencies()) == 331
