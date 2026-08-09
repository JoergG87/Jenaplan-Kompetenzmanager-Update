"""Product adapter coverage for separated Final-V3 student lifecycles."""

from __future__ import annotations

from datetime import UTC, date, datetime
import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

from src.application.dispatcher import ErrorResult, SuccessResult
from src.application.school_year_assignment import MembershipChangeStatus
from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.adapters.master_data_desktop_adapter import (
    MasterDataDesktopAdapter,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.dialogs.new_student_dialog import (
    StudentMembershipChangeDialog,
)
from tests.helpers.synthetic_v4 import create_pre_transition_v4_database


create_synthetic_v4_database = create_pre_transition_v4_database


AS_OF = date(2026, 1, 15)


def _adapter(path, *, as_of: date = AS_OF) -> StudentDesktopAdapter:
    return StudentDesktopAdapter(
        database=SQLiteDatabase(
            path,
            create=False,
            initialize_schema=False,
        ),
        today_provider=lambda: as_of,
        now_provider=lambda: datetime(
            as_of.year,
            as_of.month,
            as_of.day,
            12,
            tzinfo=UTC,
        ),
    )


def test_product_create_writes_master_data_and_assignment_atomically(
    tmp_path,
) -> None:
    path = create_synthetic_v4_database(tmp_path / "product.sqlite")
    adapter = _adapter(path)

    result = adapter.save_new_student(
        first_name="Ada",
        last_name="Beispiel",
        group_id="GRP-TEST-A",
        course_id="CRS-TEST-1",
        student_notes="Neu",
    )

    assert isinstance(result, SuccessResult)
    with sqlite3.connect(path) as connection:
        student = connection.execute(
            """
            SELECT first_name, last_name, notes
            FROM students
            WHERE student_id = ?
            """,
            (result.value.student_id,),
        ).fetchone()
        assignment = connection.execute(
            """
            SELECT group_id, course_id, assignment_status, valid_from, valid_to
            FROM student_school_year_assignments
            WHERE student_id = ?
            """,
            (result.value.student_id,),
        ).fetchone()
    assert student == ("Ada", "Beispiel", "Neu")
    assert assignment == (
        "GRP-TEST-A",
        "CRS-TEST-1",
        "enrolled",
        AS_OF.isoformat(),
        "2026-07-31",
    )


def test_product_create_without_current_school_year_writes_nothing(
    tmp_path,
) -> None:
    path = create_synthetic_v4_database(tmp_path / "missing-current.sqlite")
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE school_years SET status = 'closed', closed_at = ?",
            ("2026-01-14T00:00:00+00:00",),
        )
        before = connection.execute("SELECT count(*) FROM students").fetchone()[0]

    result = _adapter(path).save_new_student(
        first_name="Ada",
        last_name="Beispiel",
        group_id="GRP-TEST-A",
        course_id="CRS-TEST-1",
    )

    assert isinstance(result, ErrorResult)
    assert "aktuelles Schuljahr" in result.message
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT count(*) FROM students").fetchone()[0] == before


def test_master_data_update_never_changes_assignment(tmp_path) -> None:
    path = create_synthetic_v4_database(tmp_path / "master-data.sqlite")
    adapter = _adapter(path)
    with sqlite3.connect(path) as connection:
        before = connection.execute(
            """
            SELECT group_id, course_id, valid_from, valid_to
            FROM student_school_year_assignments
            WHERE student_id = 'STD-TEST-001'
            """
        ).fetchall()

    result = adapter.save_existing_student(
        student_id="STD-TEST-001",
        first_name="Neuer",
        last_name="Name",
        student_notes="Nur Stammdaten",
    )

    assert isinstance(result, SuccessResult)
    with sqlite3.connect(path) as connection:
        after = connection.execute(
            """
            SELECT group_id, course_id, valid_from, valid_to
            FROM student_school_year_assignments
            WHERE student_id = 'STD-TEST-001'
            """
        ).fetchall()
    assert after == before


def test_product_membership_change_and_no_change(tmp_path) -> None:
    path = create_synthetic_v4_database(tmp_path / "change.sqlite")
    adapter = _adapter(path)

    changed = adapter.change_student_membership(
        "STD-TEST-001",
        effective_on=date(2026, 2, 1),
        group_id="GRP-TEST-B",
        course_id="CRS-TEST-2",
    )
    no_change = adapter.change_student_membership(
        "STD-TEST-001",
        effective_on=date(2026, 2, 2),
        group_id="GRP-TEST-B",
        course_id="CRS-TEST-2",
    )

    assert isinstance(changed, SuccessResult)
    assert changed.value.status is MembershipChangeStatus.CHANGED
    assert isinstance(no_change, SuccessResult)
    assert no_change.value.status is MembershipChangeStatus.NO_CHANGE
    with sqlite3.connect(path) as connection:
        intervals = connection.execute(
            """
            SELECT group_id, course_id, valid_from, valid_to
            FROM student_school_year_assignments
            WHERE student_id = 'STD-TEST-001'
            ORDER BY valid_from
            """
        ).fetchall()
    assert intervals == [
        ("GRP-TEST-A", "CRS-TEST-1", "2025-08-01", "2026-01-31"),
        ("GRP-TEST-B", "CRS-TEST-2", "2026-02-01", "2026-07-31"),
    ]


def test_change_preview_resolves_source_at_selected_effective_date(
    tmp_path,
) -> None:
    app = QApplication.instance() or QApplication([])
    path = create_synthetic_v4_database(tmp_path / "planned-change.sqlite")
    adapter = _adapter(path)
    planned = adapter.change_student_membership(
        "STD-TEST-001",
        effective_on=date(2026, 2, 1),
        group_id="GRP-TEST-B",
        course_id="CRS-TEST-2",
    )
    assert isinstance(planned, SuccessResult)

    dialog = StudentMembershipChangeDialog(
        adapter,
        MasterDataDesktopAdapter(adapter),
        "STD-TEST-001",
    )
    dialog.effective_on.setDate(QDate(2026, 3, 1))
    dialog.course_select.setCurrentIndex(
        dialog.course_select.findData("CRS-TEST-1")
    )

    assert "Am Stichtag: Testgruppe B · Testkurs 2" in dialog.preview.text()
    assert "Ab 01.03.2026: Testgruppe B · Testkurs 1" in dialog.preview.text()
    assert dialog.save_button.isEnabled()
    dialog.close()
    assert app is not None


def test_exit_and_archive_remain_separate(tmp_path) -> None:
    path = create_synthetic_v4_database(tmp_path / "exit.sqlite")
    adapter = _adapter(path)

    blocked = adapter.archive_student_master_data("STD-TEST-001")
    exited = adapter.exit_student_from_school_year(
        "STD-TEST-001",
        effective_on=date(2026, 2, 1),
    )
    archived = _adapter(path, as_of=date(2026, 2, 1)).archive_student_master_data(
        "STD-TEST-001"
    )

    assert isinstance(blocked, ErrorResult)
    assert isinstance(exited, SuccessResult)
    assert isinstance(archived, SuccessResult)
    with sqlite3.connect(path) as connection:
        student = connection.execute(
            "SELECT active, archived_at FROM students WHERE student_id = 'STD-TEST-001'"
        ).fetchone()
        exited_assignment = connection.execute(
            """
            SELECT assignment_status, group_id, course_id
            FROM student_school_year_assignments
            WHERE student_id = 'STD-TEST-001' AND valid_from = '2026-02-01'
            """
        ).fetchone()
    assert student[0] == 0
    assert student[1] is not None
    assert exited_assignment == ("exited", None, None)


def test_archive_timestamp_never_precedes_same_day_master_data_update(
    tmp_path,
) -> None:
    path = create_synthetic_v4_database(tmp_path / "archive-time.sqlite")
    as_of = date(2026, 2, 1)
    adapter = _adapter(path, as_of=as_of)
    exited = adapter.exit_student_from_school_year(
        "STD-TEST-001",
        effective_on=as_of,
    )
    updated = adapter.save_existing_student(
        student_id="STD-TEST-001",
        first_name="Ada",
        last_name="Beispiel",
        student_notes="Am selben Tag aktualisiert",
    )
    archived = adapter.archive_student_master_data("STD-TEST-001")

    assert isinstance(exited, SuccessResult)
    assert isinstance(updated, SuccessResult)
    assert isinstance(archived, SuccessResult)
    with sqlite3.connect(path) as connection:
        updated_at, archived_at = connection.execute(
            """
            SELECT updated_at, archived_at
            FROM students
            WHERE student_id = 'STD-TEST-001'
            """
        ).fetchone()
    assert archived_at == updated_at


def test_archive_normalizes_shell_style_naive_now_provider(tmp_path) -> None:
    path = create_synthetic_v4_database(tmp_path / "archive-local-time.sqlite")
    as_of = date(2026, 2, 1)
    adapter = StudentDesktopAdapter(
        database=SQLiteDatabase(
            path,
            create=False,
            initialize_schema=False,
        ),
        today_provider=lambda: as_of,
        now_provider=lambda: datetime(2026, 2, 1, 12),
    )
    exited = adapter.exit_student_from_school_year(
        "STD-TEST-001",
        effective_on=as_of,
    )
    archived = adapter.archive_student_master_data("STD-TEST-001")

    assert isinstance(exited, SuccessResult)
    assert isinstance(archived, SuccessResult)
    with sqlite3.connect(path) as connection:
        archived_at = connection.execute(
            """
            SELECT archived_at
            FROM students
            WHERE student_id = 'STD-TEST-001'
            """
        ).fetchone()[0]
    assert datetime.fromisoformat(archived_at).utcoffset() is not None
