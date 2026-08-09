"""Focused final-V3 master-data writer and UI tests for SJ-2F."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from src.core.sqlite_store import (
    MasterDataCourseRecord,
    MasterDataGroupRecord,
    SQLiteDatabase,
    SQLiteMasterDataRepository,
)
from src.desktop_app.adapters.master_data_desktop_adapter import (
    MasterDataDesktopAdapter,
)
from src.desktop_app.dialogs.master_data_dialog import MasterDataNameDialog
from src.desktop_app.screens.master_data_screen import MasterDataScreen
from src.desktop_app.view_models.master_data_view_model import (
    COURSE_YEAR_LEVEL_REQUIRED_MESSAGE,
    MasterDataItemViewModel,
    MasterDataViewModel,
)
from tests.helpers.synthetic_v4 import create_synthetic_v4_database


@pytest.fixture
def final_v4_database(tmp_path):
    path = create_synthetic_v4_database(tmp_path / "master-data-v3.sqlite")
    return SQLiteDatabase(
        path,
        create=False,
        initialize_schema=False,
    )


def _assignment_rows(database: SQLiteDatabase) -> tuple[tuple[object, ...], ...]:
    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT
                assignment_id,
                student_id,
                school_year_id,
                group_id,
                course_id,
                assignment_status,
                valid_from,
                valid_to,
                created_at,
                updated_at
            FROM student_school_year_assignments
            ORDER BY assignment_id
            """
        ).fetchall()
    return tuple(tuple(row) for row in rows)


def test_course_level_is_required_and_multiple_courses_may_share_it(
    final_v4_database: SQLiteDatabase,
) -> None:
    adapter = MasterDataDesktopAdapter(
        SimpleNamespace(database=final_v4_database)
    )

    with pytest.raises(ValueError, match="Kursstufe"):
        adapter.add_course("Ohne Stufe")
    with pytest.raises(ValueError, match="Kursstufe"):
        adapter.add_course("Ungültige Stufe", year_level=4)

    first = adapter.add_course("Lerngruppe A", year_level=2)
    second = adapter.add_course("Lerngruppe B", year_level=2)

    assert first.year_level == 2
    assert second.year_level == 2
    with final_v4_database.connect() as connection:
        stored = connection.execute(
            """
            SELECT course_name, year_level
            FROM courses
            WHERE course_id IN (?, ?)
            ORDER BY course_name
            """,
            (first.item_id, second.item_id),
        ).fetchall()
    assert [tuple(row) for row in stored] == [
        ("Lerngruppe A", 2),
        ("Lerngruppe B", 2),
    ]


@pytest.mark.parametrize(
    ("kind", "item_id", "message_fragment", "as_of"),
    (
        ("group", "GRP-TEST-A", "Stammgruppe", date(2025, 7, 1)),
        ("group", "GRP-TEST-A", "Stammgruppe", date(2026, 1, 15)),
        ("course", "CRS-TEST-1", "Kurs", date(2025, 7, 1)),
        ("course", "CRS-TEST-1", "Kurs", date(2026, 1, 15)),
    ),
)
def test_current_or_future_enrollment_blocks_deactivation_atomically(
    final_v4_database: SQLiteDatabase,
    kind: str,
    item_id: str,
    message_fragment: str,
    as_of: date,
) -> None:
    repository = SQLiteMasterDataRepository(final_v4_database)
    assignments_before = _assignment_rows(final_v4_database)

    if kind == "group":
        current = next(
            item
            for item in repository.list_student_groups()
            if item.group_id == item_id
        )
        write = lambda: repository.upsert_student_group(
            MasterDataGroupRecord(
                current.group_id,
                current.group_name,
                False,
                current.sort_order,
            ),
            as_of=as_of,
        )
    else:
        current = next(
            item
            for item in repository.list_courses()
            if item.course_id == item_id
        )
        write = lambda: repository.upsert_course(
            MasterDataCourseRecord(
                current.course_id,
                current.course_name,
                current.color_name,
                current.color_hex,
                False,
                current.sort_order,
                current.year_level,
            ),
            as_of=as_of,
        )

    with pytest.raises(ValueError, match=message_fragment):
        write()

    assert _assignment_rows(final_v4_database) == assignments_before
    with final_v4_database.connect() as connection:
        table = "groups" if kind == "group" else "courses"
        id_column = "group_id" if kind == "group" else "course_id"
        active = connection.execute(
            f"SELECT active FROM {table} WHERE {id_column} = ?",
            (item_id,),
        ).fetchone()[0]
    assert active == 1


def test_only_historical_assignments_allow_deactivation_without_membership_write(
    final_v4_database: SQLiteDatabase,
) -> None:
    repository = SQLiteMasterDataRepository(final_v4_database)
    group = next(
        item
        for item in repository.list_student_groups()
        if item.group_id == "GRP-TEST-A"
    )
    course = next(
        item
        for item in repository.list_courses()
        if item.course_id == "CRS-TEST-1"
    )
    assignments_before = _assignment_rows(final_v4_database)

    repository.upsert_student_group(
        MasterDataGroupRecord(
            group.group_id,
            group.group_name,
            False,
            group.sort_order,
        ),
        as_of=date(2027, 8, 1),
    )
    repository.upsert_course(
        MasterDataCourseRecord(
            course.course_id,
            course.course_name,
            course.color_name,
            course.color_hex,
            False,
            course.sort_order,
            course.year_level,
        ),
        as_of=date(2027, 8, 1),
    )

    assert _assignment_rows(final_v4_database) == assignments_before
    with final_v4_database.connect() as connection:
        assert connection.execute(
            "SELECT active FROM groups WHERE group_id = 'GRP-TEST-A'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT active FROM courses WHERE course_id = 'CRS-TEST-1'"
        ).fetchone()[0] == 0
        stored_assignment = connection.execute(
            """
            SELECT group_id, course_id
            FROM student_school_year_assignments
            WHERE assignment_id = 'ASG-TEST-001'
            """
        ).fetchone()
        assert tuple(stored_assignment) == ("GRP-TEST-A", "CRS-TEST-1")


def test_deactivation_requires_an_explicit_reference_date(
    final_v4_database: SQLiteDatabase,
) -> None:
    repository = SQLiteMasterDataRepository(final_v4_database)
    group = repository.list_student_groups()[0]

    with pytest.raises(ValueError, match="Stichtag"):
        repository.upsert_student_group(
            MasterDataGroupRecord(
                group.group_id,
                group.group_name,
                False,
                group.sort_order,
            )
        )


def test_course_dialog_requires_conscious_level_selection() -> None:
    application = QApplication.instance() or QApplication([])
    dialog = MasterDataNameDialog(
        "Neuer Kurs",
        include_color=True,
        include_year_level=True,
    )
    dialog.name_input.setText("Neuer Kurs")

    dialog.save()
    assert dialog.result() == QDialog.DialogCode.Rejected
    assert dialog.error_label.text() == COURSE_YEAR_LEVEL_REQUIRED_MESSAGE

    dialog.year_level_select.setCurrentIndex(3)
    dialog.save()
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.year_level() == 3
    assert application is not None


def test_master_data_screen_displays_course_level_and_activity() -> None:
    application = QApplication.instance() or QApplication([])
    screen = MasterDataScreen()

    screen.set_master_data(
        MasterDataViewModel(
            groups=(),
            courses=(
                MasterDataItemViewModel(
                    "CRS-TEST",
                    "Testkurs",
                    True,
                    "Blau",
                    "#2563EB",
                    2,
                    False,
                ),
            ),
        )
    )

    assert tuple(
        screen.course_table.horizontalHeaderItem(index).text()
        for index in range(screen.course_table.columnCount())
    ) == ("Kurs", "Kursstufe", "Kursfarbe", "Status", "")
    assert screen.course_table.item(0, 1).text() == "Stufe 2"
    assert "Inaktiv" in screen.course_table.cellWidget(0, 3).accessibleName()
    assert application is not None
