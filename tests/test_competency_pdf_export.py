"""Export semantics, actual PDF pagination, external-file safety and UI routing."""
from dataclasses import replace
from io import BytesIO
import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from pypdf import PdfReader
from PySide6.QtWidgets import QApplication, QMessageBox

from src.application.competency_pdf_export import export_competency_pdf, render_competency_pdf, CompetencyPdfExportError
from src.desktop_app.view_models.competency_pdf import build_competency_pdf_model
from src.desktop_app.view_models.observation_view_model import StudentCompetencyStatusViewModel, build_student_competency_cockpit


def status(**changes):
    base = StudentCompetencyStatusViewModel(
        "CMP-1", "Text", "schulgarten", "Schulgarten", "++", "++", "2026-09-01", 1,
        confirmed_rating="-", confirmed_at="2026-09-02T12:00:00",
        competency_text="Pflanzen & Tiere <kennen>", learning_area="Garten", competency_group="Natur",
        documentation_state="confirmed", observed_proposal="++", is_active=True, catalog_status="current",
    )
    return replace(base, **changes)


def model(*rows, subject_id=""):
    return build_competency_pdf_model("Musterkind", "2026/27", build_student_competency_cockpit(tuple(rows)), subject_id)


@pytest.mark.parametrize("token", ["--", "-", "+", "++"])
def test_exact_confirmed_value_never_observation_proposal(token):
    output = model(status(confirmed_rating=token))
    assert output.subjects[0].rows[0].rating == token
    assert "2026-09-02" in output.subjects[0].rows[0].source


@pytest.mark.parametrize("state,label", [
    ("undocumented", "Noch nicht dokumentiert"),
    ("observed_unconfirmed", "Beobachtet, noch nicht bestätigt"),
    ("confirmation_unknown", "Bestätigungsstand unklar"),
])
def test_missing_or_unsafe_confirmation_never_becomes_lowest_stage(state,label):
    row=model(status(documentation_state=state)).subjects[0].rows[0]
    assert row.rating == ""
    assert row.source == label


def test_newer_observations_keep_confirmation_and_explicit_source():
    row=model(status(documentation_state="newer_observations")).subjects[0].rows[0]
    assert row.rating == "-"
    assert "neuere Beobachtungen" in row.source


def test_subject_filter_and_history_preserve_current_catalog_only():
    rows=(status(), status(competency_id="CMP-2",subject_id="sport",subject_display_name="Sport"),
          status(competency_id="CMP-old",historical=True,catalog_status="historical"))
    assert len(model(*rows).subjects)==2
    assert len(model(*rows,subject_id="schulgarten").subjects[0].rows)==1
    assert model(*rows,subject_id="sport").subjects[0].rating_profile=="sport"
    with pytest.raises(ValueError):model(*rows,subject_id="absent")


def test_pdf_repeats_header_and_preserves_all_long_texts():
    rows=tuple(status(competency_id=f"CMP-{i}",sort_order=i,
                      competency_text=f"Eindeutige Kompetenz {i:03d} " + "langer Kompetenztext "*12)
               for i in range(67))
    output=render_competency_pdf(model(*rows))
    reader=PdfReader(BytesIO(output))
    assert len(reader.pages)>1
    for page in reader.pages:
        text=page.extract_text()
        assert "Bestätigter Entwicklungsstand" in text
        assert "Jenaplan-Kompetenzmanager" in text
    text="\n".join(p.extract_text() for p in reader.pages)
    for i in range(67):assert f"Eindeutige Kompetenz {i:03d}" in text
    assert sum(len(p.images) for p in reader.pages)>=4


def test_pdf_escapes_catalog_markup():
    text=PdfReader(BytesIO(render_competency_pdf(model(status())))).pages[0].extract_text()
    assert "Pflanzen & Tiere <kennen>" in text


def test_external_export_is_private_and_no_clobber(tmp_path):
    target=tmp_path/'new.pdf';runtime=tmp_path/'runtime';runtime.mkdir()
    export_competency_pdf(model(status()),target,runtime_root=runtime)
    assert target.stat().st_mode & 0o777 == 0o600
    before=target.read_bytes()
    with pytest.raises(FileExistsError):export_competency_pdf(model(status()),target,runtime_root=runtime)
    assert target.read_bytes()==before


def test_runtime_and_symlink_targets_are_rejected(tmp_path):
    runtime=tmp_path/'runtime';runtime.mkdir()
    with pytest.raises(CompetencyPdfExportError):export_competency_pdf(model(status()),runtime/'out.pdf',runtime_root=runtime)
    outside=tmp_path/'existing';outside.write_text('unchanged')
    link=tmp_path/'link.pdf';link.symlink_to(outside)
    with pytest.raises(FileExistsError):export_competency_pdf(model(status()),link,runtime_root=runtime)
    assert outside.read_text()=='unchanged'
    folder=tmp_path/'linked';folder.symlink_to(runtime,target_is_directory=True)
    with pytest.raises(CompetencyPdfExportError):export_competency_pdf(model(status()),folder/'out.pdf',runtime_root=runtime)


def test_failed_write_removes_only_own_partial_output(tmp_path):
    target=tmp_path/'out.pdf'
    with patch('src.application.competency_pdf_export.os.fsync',side_effect=OSError('disk full')):
        with pytest.raises(OSError):export_competency_pdf(model(status()),target,runtime_root=tmp_path/'runtime')
    assert not target.exists()


def test_adapter_ui_export_and_cancellation(tmp_path):
    from tests.test_report_revision_ui import ReportRevisionProductTest
    from src.desktop_app.runtime import runtime_paths
    from src.desktop_app.shell import AppShell
    app=QApplication.instance() or QApplication([])
    fixture=ReportRevisionProductTest(methodName='test_status_without_and_with_current_revision');fixture.setUp()
    shell=None
    try:
        shell=AppShell(fixture.database_path,paths=runtime_paths(tmp_path/'runtime'))
        shell.show_student_profile(fixture.student.student_id)
        screen=shell.student_profile_screen
        assert screen.competency_pdf_button.isEnabled()
        screen.competency_search_input.setText('filter-with-no-matches')
        target=tmp_path/'all.pdf'
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes), patch('src.desktop_app.shell.QFileDialog.getSaveFileName',return_value=(str(target),'')):
            screen.competency_pdf_button.click()
        assert target.is_file()
        assert len(PdfReader(target).pages)>1
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel), patch('src.desktop_app.shell.QFileDialog.getSaveFileName') as choose:
            screen.competency_pdf_button.click()
            choose.assert_not_called()
        assert shell.maintenance_gate.active_writer_count==0
    finally:
        if shell:shell.close();shell.deleteLater();app.processEvents()
        fixture.tearDown()
