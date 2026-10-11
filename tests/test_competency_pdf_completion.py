from contextlib import closing
from dataclasses import replace
from io import BytesIO
import pytest
from pypdf import PdfReader
from PySide6.QtWidgets import QApplication
from src.application.competency_pdf_completion import (
    pending_competency_pdf_rows, validate_competency_pdf_completion,
)
from src.application.competency_pdf_export import render_competency_pdf
from src.core.sqlite_store import (
    SQLiteStudentCompetencyConfirmationRepository, StudentCompetencyConfirmationRecord,
)
from src.desktop_app.dialogs.competency_pdf_completion_dialog import CompetencyPdfCompletionDialog
from tests.test_competency_pdf_export import model, status


@pytest.fixture
def fixture():
    from tests.test_report_revision_ui import ReportRevisionProductTest
    f = ReportRevisionProductTest(methodName='test_status_without_and_with_current_revision')
    f.setUp()
    yield f
    f.tearDown()


def test_parent_pdf_hides_all_internal_confirmation_text():
    text=' '.join(p.extract_text() for p in PdfReader(BytesIO(render_competency_pdf(model(status())))).pages)
    assert 'Entwicklungsstand' in text
    assert 'Bestätig' not in text
    assert '2026-09-02' not in text
    assert 'Nur bestätigte' not in text


def test_unconfirmed_direct_render_is_refused():
    with pytest.raises(ValueError, match='alle aktuellen Kompetenzen'):
        render_competency_pdf(model(status(documentation_state='observed_unconfirmed')))


def test_explicit_completion_covers_all_and_preserves_existing(fixture):
    adapter=fixture.adapter; student=fixture.student.student_id
    prepared=adapter.competency_pdf_for_student(student)
    before={r.competency_id:r for s in prepared.subjects for r in s.rows if r.rating}
    choices={r.competency_id:('--','-','+','++')[i%4]
             for i,(_,r) in enumerate(pending_competency_pdf_rows(prepared))}
    complete=adapter.complete_competency_pdf(student,prepared,choices)
    assert not pending_competency_pdf_rows(complete)
    assert all(before[r.competency_id]==r for s in complete.subjects for r in s.rows if r.competency_id in before)
    assert set(choices.values())=={'--','-','+','++'}


def test_changed_catalog_text_rejects_old_dialog_without_writes(fixture):
    adapter=fixture.adapter; student=fixture.student.student_id
    prepared=adapter.competency_pdf_for_student(student)
    pending=pending_competency_pdf_rows(prepared)
    repo=SQLiteStudentCompetencyConfirmationRepository(adapter.database)
    before=repo.list_confirmations_for_student(student)
    with closing(adapter.database.connect()) as connection:
        with connection:
            connection.execute('UPDATE competencies SET description=description || ? WHERE competency_id=?',
                               (' (Katalogänderung)',pending[0][1].competency_id))
    with pytest.raises(ValueError, match='geändert'):
        adapter.complete_competency_pdf(student,prepared,{r.competency_id:'+' for _,r in pending})
    assert repo.list_confirmations_for_student(student)==before


@pytest.mark.parametrize('kind',['missing','extra','invalid'])
def test_invalid_selection_is_rejected_before_mutation(fixture,kind):
    adapter=fixture.adapter; student=fixture.student.student_id
    prepared=adapter.competency_pdf_for_student(student)
    choices={r.competency_id:'+' for _,r in pending_competency_pdf_rows(prepared)}
    if kind=='missing': choices.pop(next(iter(choices)))
    if kind=='extra': choices['foreign']='+'
    if kind=='invalid': choices[next(iter(choices))]='invalid'
    repo=SQLiteStudentCompetencyConfirmationRepository(adapter.database)
    before=repo.list_confirmations_for_student(student)
    with pytest.raises(ValueError): adapter.complete_competency_pdf(student,prepared,choices)
    assert repo.list_confirmations_for_student(student)==before


def test_batch_rollback_includes_events(fixture):
    adapter=fixture.adapter; student=fixture.student.student_id
    pending=pending_competency_pdf_rows(adapter.competency_pdf_for_student(student))
    repo=SQLiteStudentCompetencyConfirmationRepository(adapter.database)
    before=repo.list_confirmations_for_student(student)
    with closing(adapter.database.connect()) as c:
        events=c.execute('SELECT COUNT(*) FROM persistence_events').fetchone()[0]
    records=[StudentCompetencyConfirmationRecord(student,pending[i][1].competency_id,
              '+' if i==0 else 'invalid','2026-10-11T12:00:00+00:00','') for i in range(2)]
    with pytest.raises(ValueError): repo.upsert_confirmations(records)
    assert repo.list_confirmations_for_student(student)==before
    with closing(adapter.database.connect()) as c:
        assert c.execute('SELECT COUNT(*) FROM persistence_events').fetchone()[0]==events


def test_dialog_has_no_default_and_cancel_preserves_state():
    app=QApplication.instance() or QApplication([])
    prepared=model(status(documentation_state='undocumented'),
                   status(competency_id='CMP-2',documentation_state='observed_unconfirmed'))
    dialog=CompetencyPdfCompletionDialog(prepared)
    assert not dialog.save_button.isEnabled()
    assert all(not v.currentData() for v in dialog.rating_inputs.values())
    for choice in dialog.rating_inputs.values(): choice.setCurrentIndex(2)
    assert dialog.save_button.isEnabled()
    assert set(dialog.selections().values())=={'-'}
    dialog.reject()
    assert pending_competency_pdf_rows(prepared)
    dialog.deleteLater(); app.processEvents()


def test_shell_completion_cancel_never_opens_file_dialog(fixture,tmp_path):
    from unittest.mock import patch
    from src.desktop_app.shell import AppShell
    from src.desktop_app.runtime import runtime_paths
    from PySide6.QtWidgets import QDialog
    app=QApplication.instance() or QApplication([])
    shell=AppShell(fixture.database_path,paths=runtime_paths(tmp_path/'runtime'))
    student=fixture.student.student_id
    repo=SQLiteStudentCompetencyConfirmationRepository(fixture.adapter.database)
    before=repo.list_confirmations_for_student(student)
    try:
        with patch.object(CompetencyPdfCompletionDialog,'exec',return_value=QDialog.DialogCode.Rejected), \
             patch('src.desktop_app.shell.QFileDialog.getSaveFileName') as choose:
            shell.export_competency_overview_pdf(student)
            choose.assert_not_called()
        assert repo.list_confirmations_for_student(student)==before
    finally:
        shell.close();shell.deleteLater();app.processEvents()


def test_shell_explicit_save_survives_later_file_export_cancel(fixture,tmp_path):
    from unittest.mock import patch
    from src.desktop_app.shell import AppShell
    from src.desktop_app.runtime import runtime_paths
    from PySide6.QtWidgets import QDialog,QMessageBox
    app=QApplication.instance() or QApplication([])
    shell=AppShell(fixture.database_path,paths=runtime_paths(tmp_path/'runtime'))
    student=fixture.student.student_id
    shell.show_student_profile(student)
    def accept(dialog):
        for choice in dialog.rating_inputs.values(): choice.setCurrentIndex(2)
        return QDialog.DialogCode.Accepted
    try:
        with patch.object(CompetencyPdfCompletionDialog,'exec',accept), \
             patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel), \
             patch('src.desktop_app.shell.QFileDialog.getSaveFileName') as choose:
            shell.export_competency_overview_pdf(student)
            choose.assert_not_called()
        assert not pending_competency_pdf_rows(fixture.adapter.competency_pdf_for_student(student))
    finally:
        shell.close();shell.deleteLater();app.processEvents()
