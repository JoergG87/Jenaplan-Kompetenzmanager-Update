"""Regressions for preserving the live report workspace during draft PDF export."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMessageBox,
    QPushButton,
    QScrollArea,
)

from prototypes.pdf_engine.renderer import PdfRenderer
from src.desktop_app.dialogs.learning_report_dialog import LearningReportDialog
from src.desktop_app.runtime import runtime_paths
from src.desktop_app.shell import AppShell
from tests import test_report_revision_ui as revision_ui_tests


def _product_fixture() -> revision_ui_tests.ReportRevisionProductTest:
    fixture = revision_ui_tests.ReportRevisionProductTest(
        methodName="test_status_without_and_with_current_revision"
    )
    fixture.setUp()
    return fixture


def _workspace(fixture, tmp_path) -> tuple[QApplication, AppShell, LearningReportDialog]:
    app = QApplication.instance() or QApplication([])
    shell = AppShell(
        fixture.database_path,
        paths=runtime_paths(tmp_path / "runtime"),
    )
    preparation = shell.adapter.learning_report_preparation_for_student(
        fixture.student.student_id,
        period_end=fixture.saved.period_end,
        retained_competency_ids=fixture.saved.competency_ids,
    )
    workspace = LearningReportDialog(
        preparation,
        shell,
        fixture.saved,
        shell.adapter.learning_report_revision_status(
            fixture.saved.report_draft_id
        ),
    )
    workspace.pdf_requested.connect(
        lambda output_model: shell.export_learning_report_pdf(
            output_model,
            parent=workspace,
        )
    )
    workspace.resize(1180, 760)
    workspace.show()
    app.processEvents()
    return app, shell, workspace


def _make_unsaved_preview_state(
    app: QApplication,
    workspace: LearningReportDialog,
    fixture,
) -> None:
    workspace.overall_input.setPlainText(
        "Ungespeicherter Gesamttext.\n" + "\n".join(
            f"Lange sichtbare Zeile {index}" for index in range(120)
        )
    )
    subject_id = fixture.competency.subject_id
    subject_index = next(
        index
        for index, subject in enumerate(workspace.preparation.subjects)
        if subject.subject_id == subject_id
    )
    workspace._set_editor_section(subject_index + 1)
    subject_texts = workspace.subject_widgets[subject_id]["texts"]
    subject_texts["strengths"].setPlainText("Ungespeicherter Fachtext.")
    workspace.show_workspace("evidence")
    workspace._set_evidence_section(subject_index)
    evidence = workspace._evidence_checks[subject_id][fixture.observation.observation_id]
    evidence.setChecked(False)
    workspace.show_workspace("preview")
    workspace.show_workspace("preview")
    app.processEvents()
    QTest.qWait(workspace._preview_timer.interval() + 20)
    app.processEvents()
    preview_scroll = workspace.findChild(
        QScrollArea,
        "LearningReportPreviewScroll",
    )
    preview_scroll.verticalScrollBar().setValue(
        preview_scroll.verticalScrollBar().maximum() // 2
    )
    app.processEvents()


def _state(workspace: LearningReportDialog) -> tuple[object, ...]:
    preview_scroll = workspace.findChild(
        QScrollArea,
        "LearningReportPreviewScroll",
    )
    return (
        workspace.report_draft_view_model(),
        workspace._dirty,
        workspace.workspace_navigation.current_key(),
        workspace.mode_stack.currentIndex(),
        workspace.editor_stack.currentIndex(),
        workspace.evidence_stack.currentIndex()
        if workspace.workspace_built["evidence"]
        else -1,
        preview_scroll.verticalScrollBar().value(),
    )


def _lifecycle_events(workspace: LearningReportDialog) -> list[str]:
    events: list[str] = []
    workspace.accepted.connect(lambda: events.append("accept"))
    workspace.rejected.connect(lambda: events.append("reject"))
    workspace.finished.connect(lambda _result: events.append("done"))
    workspace.destroyed.connect(lambda: events.append("destroy"))
    return events


def _close(
    app: QApplication,
    shell: AppShell,
    workspace: LearningReportDialog,
    fixture,
) -> None:
    workspace.accept()
    shell.close()
    app.processEvents()
    fixture.tearDown()


def test_successful_export_keeps_all_unsaved_workspace_state_and_persistence(
    tmp_path,
) -> None:
    fixture = _product_fixture()
    app, shell, workspace = _workspace(fixture, tmp_path)
    try:
        _make_unsaved_preview_state(app, workspace, fixture)
        before = _state(workspace)
        persisted_before = shell.adapter.list_learning_report_drafts_for_student(
            fixture.student.student_id
        )
        lifecycle = _lifecycle_events(workspace)
        selected_target = tmp_path / "draft-export.pdf"
        owners: list[object] = []

        def choose_target(parent, *_args, **kwargs):
            owners.append(parent)
            assert kwargs["options"] == QFileDialog.Option.DontUseNativeDialog
            return str(selected_target), "PDF-Datei (*.pdf)"

        with (
            patch.object(QFileDialog, "getSaveFileName", side_effect=choose_target),
            patch.object(PdfRenderer, "render", return_value=selected_target) as render,
        ):
            workspace.pdf_button.click()
            app.processEvents()

        assert owners == [workspace]
        render.assert_called_once()
        assert workspace.isVisible()
        assert lifecycle == []
        assert _state(workspace) == before
        assert workspace._dirty
        assert (
            shell.adapter.list_learning_report_drafts_for_student(
                fixture.student.student_id
            )
            == persisted_before
        )
        revision_status = shell.adapter.learning_report_revision_status(
            fixture.saved.report_draft_id
        )
        assert revision_status.state == "not_finalized"
        assert revision_status.history == ()
    finally:
        _close(app, shell, workspace, fixture)


def test_cancelled_export_changes_no_workspace_or_draft_state(tmp_path) -> None:
    fixture = _product_fixture()
    app, shell, workspace = _workspace(fixture, tmp_path)
    try:
        _make_unsaved_preview_state(app, workspace, fixture)
        before = _state(workspace)
        lifecycle = _lifecycle_events(workspace)
        owners: list[object] = []

        def cancel(parent, *_args, **kwargs):
            owners.append(parent)
            assert kwargs["options"] == QFileDialog.Option.DontUseNativeDialog
            return "", ""

        with (
            patch.object(QFileDialog, "getSaveFileName", side_effect=cancel),
            patch.object(PdfRenderer, "render") as render,
        ):
            workspace.pdf_button.click()
            app.processEvents()

        assert owners == [workspace]
        render.assert_not_called()
        assert workspace.isVisible()
        assert lifecycle == []
        assert _state(workspace) == before
    finally:
        _close(app, shell, workspace, fixture)


def test_failed_export_keeps_state_and_owns_error_message(tmp_path) -> None:
    fixture = _product_fixture()
    app, shell, workspace = _workspace(fixture, tmp_path)
    try:
        _make_unsaved_preview_state(app, workspace, fixture)
        before = _state(workspace)
        lifecycle = _lifecycle_events(workspace)
        error_parents: list[object] = []

        def record_warning(parent, *_args):
            error_parents.append(parent)
            return QMessageBox.StandardButton.Ok

        with (
            patch.object(
                QFileDialog,
                "getSaveFileName",
                return_value=(str(tmp_path / "blocked.pdf"), "PDF-Datei (*.pdf)"),
            ) as chooser,
            patch.object(PdfRenderer, "render", side_effect=OSError("Ziel gesperrt")),
            patch.object(QMessageBox, "warning", side_effect=record_warning),
        ):
            workspace.pdf_button.click()
            app.processEvents()

        assert error_parents == [workspace]
        assert (
            chooser.call_args.kwargs["options"]
            == QFileDialog.Option.DontUseNativeDialog
        )
        assert workspace.isVisible()
        assert lifecycle == []
        assert _state(workspace) == before
    finally:
        _close(app, shell, workspace, fixture)


def test_repeated_export_keeps_one_workspace_without_state_duplicates(
    tmp_path,
) -> None:
    fixture = _product_fixture()
    app, shell, workspace = _workspace(fixture, tmp_path)
    try:
        _make_unsaved_preview_state(app, workspace, fixture)
        before = _state(workspace)
        lifecycle = _lifecycle_events(workspace)
        preexisting_top_levels = set(app.topLevelWidgets())
        targets = (
            tmp_path / "draft-export-1.pdf",
            tmp_path / "draft-export-2.pdf",
        )
        chooser = Mock(
            side_effect=[
                (str(targets[0]), "PDF-Datei (*.pdf)"),
                (str(targets[1]), "PDF-Datei (*.pdf)"),
            ]
        )

        with (
            patch.object(QFileDialog, "getSaveFileName", chooser),
            patch.object(PdfRenderer, "render", side_effect=targets) as render,
        ):
            workspace.pdf_button.click()
            workspace.pdf_button.click()
            app.processEvents()

        assert [call.args[0] for call in chooser.call_args_list] == [
            workspace,
            workspace,
        ]
        assert all(
            call.kwargs["options"] == QFileDialog.Option.DontUseNativeDialog
            for call in chooser.call_args_list
        )
        assert render.call_count == 2
        assert workspace.isVisible()
        assert lifecycle == []
        assert _state(workspace) == before
        assert set(app.topLevelWidgets()) == preexisting_top_levels
    finally:
        _close(app, shell, workspace, fixture)


def test_saved_draft_export_stays_open_and_remains_clean(tmp_path) -> None:
    fixture = _product_fixture()
    app, shell, workspace = _workspace(fixture, tmp_path)
    try:
        workspace.show_workspace("preview")
        app.processEvents()
        before = _state(workspace)
        lifecycle = _lifecycle_events(workspace)
        target = tmp_path / "saved-draft.pdf"

        with (
            patch.object(
                QFileDialog,
                "getSaveFileName",
                return_value=(str(target), "PDF-Datei (*.pdf)"),
            ) as chooser,
            patch.object(PdfRenderer, "render", return_value=target),
        ):
            workspace.pdf_button.click()
            app.processEvents()

        assert chooser.call_args.args[0] is workspace
        assert (
            chooser.call_args.kwargs["options"]
            == QFileDialog.Option.DontUseNativeDialog
        )
        assert workspace.isVisible()
        assert lifecycle == []
        assert _state(workspace) == before
        assert not workspace._dirty
    finally:
        _close(app, shell, workspace, fixture)


def test_shell_wires_export_to_the_concrete_open_workspace(tmp_path) -> None:
    fixture = _product_fixture()
    app = QApplication.instance() or QApplication([])
    shell = AppShell(
        fixture.database_path,
        paths=runtime_paths(tmp_path / "runtime"),
    )
    owners: list[object] = []
    workspaces: list[LearningReportDialog] = []
    target = tmp_path / "wired-export.pdf"

    def choose_target(parent, *_args, **kwargs):
        owners.append(parent)
        assert kwargs["options"] == QFileDialog.Option.DontUseNativeDialog
        return str(target), "PDF-Datei (*.pdf)"

    def open_workspace(workspace, owner):
        assert owner is shell
        workspaces.append(workspace)
        workspace.show_workspace("preview")
        workspace.show()
        app.processEvents()
        workspace.pdf_button.click()
        app.processEvents()
        assert workspace.isVisible()
        workspace.accept()

    try:
        with (
            patch(
                "src.desktop_app.shell.open_maximized_workspace",
                side_effect=open_workspace,
            ),
            patch.object(QFileDialog, "getSaveFileName", side_effect=choose_target),
            patch.object(PdfRenderer, "render", return_value=target),
        ):
            shell.open_learning_report_dialog(
                fixture.student.student_id,
                fixture.saved.report_draft_id,
            )

        assert len(workspaces) == 1
        assert owners == workspaces
    finally:
        shell.close()
        app.processEvents()
        fixture.tearDown()


def test_export_does_not_bypass_later_unsaved_close_confirmation(
    tmp_path,
) -> None:
    fixture = _product_fixture()
    app, shell, workspace = _workspace(fixture, tmp_path)
    try:
        _make_unsaved_preview_state(app, workspace, fixture)
        target = tmp_path / "close-confirmation.pdf"
        lifecycle = _lifecycle_events(workspace)
        with (
            patch.object(
                QFileDialog,
                "getSaveFileName",
                return_value=(str(target), "PDF-Datei (*.pdf)"),
            ),
            patch.object(PdfRenderer, "render", return_value=target),
        ):
            workspace.pdf_button.click()
            app.processEvents()

        close_actions: list[set[str]] = []

        def keep_editing(message: QMessageBox) -> int:
            close_actions.append(
                {
                    button.text()
                    for button in message.buttons()
                    if isinstance(button, QPushButton)
                }
            )
            return int(QMessageBox.DialogCode.Rejected)

        with patch.object(QMessageBox, "exec", new=keep_editing):
            workspace.reject()
        app.processEvents()

        assert close_actions == [
            {"Weiter bearbeiten", "Änderungen verwerfen"}
        ]
        assert workspace.isVisible()
        assert lifecycle == []
        assert workspace._dirty
    finally:
        _close(app, shell, workspace, fixture)
