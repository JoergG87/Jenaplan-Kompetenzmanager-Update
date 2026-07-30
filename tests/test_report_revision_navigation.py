"""Regression tests for stable report-revision navigation and ownership."""

from __future__ import annotations

import os
from dataclasses import replace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from src.desktop_app.dialogs.learning_report_dialog import (
    LearningReportDialog,
    LearningReportRevisionDialog,
)
from src.desktop_app.runtime import runtime_paths
from src.desktop_app.shell import AppShell
from tests import test_report_revision_ui as revision_ui_tests


def _product_fixture() -> revision_ui_tests.ReportRevisionProductTest:
    fixture = revision_ui_tests.ReportRevisionProductTest(
        methodName="test_status_without_and_with_current_revision"
    )
    fixture.setUp()
    return fixture


def _two_revisions(
    fixture: revision_ui_tests.ReportRevisionProductTest,
) -> tuple[object, object]:
    first = fixture.adapter.finalize_learning_report(
        fixture.saved.report_draft_id,
        "Laura Testlehrkraft",
    )
    fixture.saved = fixture.adapter.save_learning_report_draft(
        replace(
            fixture.saved,
            overall_text="Zweite unveränderliche Revision.",
        )
    )
    second = fixture.adapter.finalize_learning_report(
        fixture.saved.report_draft_id,
        "Laura Testlehrkraft",
    )
    return first, second


def _shell(
    fixture: revision_ui_tests.ReportRevisionProductTest,
    tmp_path,
) -> AppShell:
    return AppShell(
        fixture.database_path,
        paths=runtime_paths(tmp_path / "runtime"),
    )


def _flush_deferred_deletes(app: QApplication) -> None:
    QCoreApplication.sendPostedEvents(
        None,
        QEvent.Type.DeferredDelete,
    )
    app.processEvents()


def test_mouse_and_enter_emit_one_navigation_with_the_exact_revision_ids() -> None:
    app = QApplication.instance() or QApplication([])
    fixture = _product_fixture()
    try:
        first, second = _two_revisions(fixture)
        preparation = fixture.adapter.learning_report_preparation_for_student(
            fixture.student.student_id,
            period_end=fixture.saved.period_end,
            retained_competency_ids=fixture.saved.competency_ids,
        )
        dialog = LearningReportDialog(
            preparation,
            initial_draft=fixture.saved,
            revision_status=second,
        )
        dialog.show_workspace("revisions")
        dialog.show()
        app.processEvents()
        requested: list[str] = []
        dialog.revision_open_requested.connect(requested.append)

        latest_button = dialog.findChild(
            QPushButton,
            f"LearningReportOpenRevision_{second.current_revision_id}",
        )
        older_button = dialog.findChild(
            QPushButton,
            f"LearningReportOpenRevision_{first.current_revision_id}",
        )
        QTest.mouseClick(latest_button, Qt.MouseButton.LeftButton)
        older_button.setFocus()
        QTest.keyClick(older_button, Qt.Key.Key_Return)

        assert requested == [
            second.current_revision_id,
            first.current_revision_id,
        ]
        dialog.accept()
        app.processEvents()
    finally:
        fixture.tearDown()


def test_revision_mode_survives_workspace_and_profile_refresh(
    tmp_path,
) -> None:
    app = QApplication.instance() or QApplication([])
    fixture = _product_fixture()
    shell = None
    workspace = None
    try:
        _first, second = _two_revisions(fixture)
        shell = _shell(fixture, tmp_path)
        preparation = shell.adapter.learning_report_preparation_for_student(
            fixture.student.student_id,
            period_end=fixture.saved.period_end,
            retained_competency_ids=fixture.saved.competency_ids,
        )
        workspace = LearningReportDialog(
            preparation,
            shell,
            fixture.saved,
            second,
        )
        workspace.show_workspace("revisions")
        workspace.show()
        workspace.overall_input.setPlainText(
            "Ungespeicherter lokaler Entwurf bleibt erhalten."
        )
        unsaved_draft = workspace.report_draft_view_model()
        load_revision = Mock(
            wraps=shell.adapter.load_learning_report_revision
        )
        shell.adapter.load_learning_report_revision = load_revision

        with patch.object(
            LearningReportRevisionDialog,
            "exec",
            side_effect=AssertionError("nested revision event loop"),
        ):
            shell.open_learning_report_revision(
                second.current_revision_id,
                workspace,
            )
        app.processEvents()

        revision_dialog = shell._active_learning_report_revision_dialog
        assert revision_dialog is not None
        assert revision_dialog.isVisible()
        assert revision_dialog.parentWidget() is workspace
        assert revision_dialog.revision.learning_report_revision_id == (
            second.current_revision_id
        )
        assert shell._active_learning_report_revision_id == (
            second.current_revision_id
        )
        load_revision.assert_called_once_with(second.current_revision_id)

        workspace.apply_revision_status(second)
        shell.show_student_profile(fixture.student.student_id)
        app.processEvents()

        assert shell._active_learning_report_revision_dialog is revision_dialog
        assert revision_dialog.isVisible()
        assert workspace.mode_stack.currentIndex() == 3
        assert workspace.report_draft_view_model() == unsaved_draft

        revision_dialog.accept()
        _flush_deferred_deletes(app)
        assert shell._active_learning_report_revision_dialog is None
        assert shell._active_learning_report_revision_id == ""
        assert not any(
            isinstance(widget, LearningReportRevisionDialog)
            for widget in app.topLevelWidgets()
        )
    finally:
        if workspace is not None:
            workspace.accept()
        if shell is not None:
            shell.close()
        app.processEvents()
        fixture.tearDown()


def test_five_revision_opens_leave_no_hidden_top_level_helper(
    tmp_path,
) -> None:
    app = QApplication.instance() or QApplication([])
    fixture = _product_fixture()
    shell = None
    try:
        _first, second = _two_revisions(fixture)
        shell = _shell(fixture, tmp_path)

        for _index in range(5):
            shell.open_learning_report_revision(second.current_revision_id)
            app.processEvents()
            revision_dialog = shell._active_learning_report_revision_dialog
            assert revision_dialog is not None
            assert revision_dialog.isVisible()
            assert revision_dialog.parentWidget() is shell
            revision_dialog.accept()
            _flush_deferred_deletes(app)
            assert shell._active_learning_report_revision_dialog is None
            assert not any(
                isinstance(widget, LearningReportRevisionDialog)
                for widget in app.topLevelWidgets()
            )
    finally:
        if shell is not None:
            shell.close()
        app.processEvents()
        fixture.tearDown()


def test_student_switch_closes_local_revision_mode_without_reopening_it(
    tmp_path,
) -> None:
    app = QApplication.instance() or QApplication([])
    fixture = _product_fixture()
    shell = None
    try:
        _first, second = _two_revisions(fixture)
        shell = _shell(fixture, tmp_path)
        other_student = next(
            student
            for student in shell.adapter.list_students()
            if student.student_id != fixture.student.student_id
        )
        shell.show_student_profile(fixture.student.student_id)
        shell.open_learning_report_revision(second.current_revision_id)
        app.processEvents()
        assert shell._active_learning_report_revision_student_id == (
            fixture.student.student_id
        )

        shell.show_student_profile(other_student.student_id)
        _flush_deferred_deletes(app)
        assert shell._active_learning_report_revision_dialog is None
        assert shell._active_learning_report_revision_id == ""
        assert shell._active_learning_report_revision_student_id == ""

        shell.show_student_profile(fixture.student.student_id)
        app.processEvents()
        assert shell._active_learning_report_revision_dialog is None
        assert not any(
            isinstance(widget, LearningReportRevisionDialog)
            for widget in app.topLevelWidgets()
        )
    finally:
        if shell is not None:
            shell.close()
        app.processEvents()
        fixture.tearDown()
