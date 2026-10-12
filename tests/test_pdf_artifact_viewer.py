"""Focused regressions for the shared verified final-PDF viewer."""

from __future__ import annotations

from io import BytesIO
import inspect
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtPdf import QPdfDocument
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget
from reportlab.pdfgen.canvas import Canvas

from src.desktop_app.dialogs.learning_conference_dialog import (
    LearningConferenceRevisionDialog,
)
from src.desktop_app.dialogs.pdf_artifact_viewer_dialog import (
    PdfArtifactViewerDialog,
    PdfArtifactViewerError,
)
from src.desktop_app.shell import AppShell


def _pdf_bytes(*, pages: int = 2) -> bytes:
    target = BytesIO()
    canvas = Canvas(target)
    for page in range(1, pages + 1):
        canvas.drawString(72, 760, f"Synthetisches finales PDF · Seite {page}")
        canvas.showPage()
    canvas.save()
    return target.getvalue()


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_viewer_supports_multiple_pages_zoom_and_deterministic_cleanup() -> None:
    app = _app()
    dialog = PdfArtifactViewerDialog(pdf_bytes=_pdf_bytes())
    dialog.show()
    app.processEvents()

    assert dialog._document.pageCount() == 2
    assert dialog.viewer.pageMode() is dialog.viewer.PageMode.MultiPage
    assert dialog.viewer.zoomMode() is dialog.viewer.ZoomMode.FitToWidth
    QTest.mouseClick(
        dialog.findChild(QPushButton, "PdfArtifactZoomInButton"),
        Qt.MouseButton.LeftButton,
    )
    assert dialog.viewer.zoomMode() is dialog.viewer.ZoomMode.Custom
    QTest.mouseClick(
        dialog.findChild(QPushButton, "PdfArtifactFitWidthButton"),
        Qt.MouseButton.LeftButton,
    )
    assert dialog.viewer.zoomMode() is dialog.viewer.ZoomMode.FitToWidth

    QTest.mouseClick(
        dialog.findChild(QPushButton, "PdfArtifactCloseButton"),
        Qt.MouseButton.LeftButton,
    )
    assert dialog.resources_released
    assert dialog._document.status() is QPdfDocument.Status.Null
    assert not dialog._pdf_buffer.isOpen()
    assert dialog._pdf_data.isEmpty()


def test_viewer_rejects_invalid_pdf_without_plaintext_path() -> None:
    _app()
    with pytest.raises(PdfArtifactViewerError, match="pdf_viewer_document_invalid"):
        PdfArtifactViewerDialog(pdf_bytes=b"%PDF-not-a-valid-document")


class _ViewerAdapter:
    def __init__(self) -> None:
        self.artifact_ids: list[str] = []

    def read_final_pdf_artifact(self, *, artifact_id: str, consumer: object) -> None:
        self.artifact_ids.append(artifact_id)
        consumer.start(object())
        consumer.write(_pdf_bytes(pages=1))
        consumer.finish(object())

    @staticmethod
    def final_pdf_artifact_error_message(_error: Exception) -> str:
        return "sanitized"


def test_report_and_leg_ids_open_and_reopen_the_same_shell_viewer_contract() -> None:
    app = _app()
    parent = QWidget()
    harness = SimpleNamespace(
        adapter=_ViewerAdapter(),
        _create_dialog=lambda dialog_type, *args, **kwargs: dialog_type(*args, **kwargs),
        _open_dialog=lambda dialog: dialog.open(),
        _active_pdf_viewer_dialog=None,
    )

    AppShell._open_final_pdf_artifact(harness, "RPA-000001", parent=parent)
    report_viewer = harness._active_pdf_viewer_dialog
    assert isinstance(report_viewer, PdfArtifactViewerDialog)
    assert report_viewer.isVisible()
    report_viewer.close()
    assert report_viewer.resources_released

    AppShell._open_final_pdf_artifact(harness, "LCA-000001", parent=parent)
    leg_viewer = harness._active_pdf_viewer_dialog
    assert isinstance(leg_viewer, PdfArtifactViewerDialog)
    assert leg_viewer is not report_viewer
    assert harness.adapter.artifact_ids == ["RPA-000001", "LCA-000001"]
    leg_viewer.close()
    assert leg_viewer.resources_released
    app.processEvents()


def test_qt_leg_action_emits_only_opaque_artifact_id() -> None:
    _app()
    revision = SimpleNamespace(
        revision_number=1,
        student_name="Pilotkind Testfall",
        completed_at_text="10.08.2026",
        status_label="Aktuell",
        status="completed",
        learning_conference_revision_id="LCV-1",
        conference_date_text="10.08.2026",
        period_text="01.08.2026 bis 10.08.2026",
        responsible_teacher="Pilot-Lernbegleitung",
        group_name="Pilotgruppe A",
        course_name="Pilotkurs 1",
        goals="Ziel",
        support="Unterstützung",
        agreements="Vereinbarung",
        responsibilities="Zuständigkeit",
        next_review_date_text="Nicht festgelegt",
        competency_lines=(),
        observation_lines=(),
        snapshot_sha256="a" * 64,
    )
    artifact = SimpleNamespace(
        learning_conference_pdf_artifact_id="LCA-1",
        learning_conference_revision_id="LCV-1",
        file_name="Finales PDF",
        created_at="10.08.2026",
        pdf_sha256="b" * 64,
    )
    dialog = LearningConferenceRevisionDialog(revision, artifact=artifact)
    opened: list[str] = []
    generated: list[str] = []
    dialog.pdf_open_requested.connect(opened.append)
    dialog.pdf_requested.connect(generated.append)

    button = dialog.findChild(
        QPushButton,
        "LearningConferenceGenerateFinalPdfButton",
    )
    assert button.text() == "Finales PDF anzeigen"
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)

    assert opened == ["LCA-1"]
    assert generated == []
    assert "b" * 12 not in " ".join(
        label.text() for label in dialog.findChildren(QLabel)
    )
    dialog.close()


def test_viewer_path_has_no_file_open_download_or_decryption_implementation() -> None:
    viewer_source = inspect.getsource(
        __import__(
            "src.desktop_app.dialogs.pdf_artifact_viewer_dialog",
            fromlist=["PdfArtifactViewerDialog"],
        )
    )
    shell_source = inspect.getsource(AppShell._open_final_pdf_artifact)
    for forbidden in (
        "QDesktopServices",
        "QFileDialog",
        "ManagedDocumentStore",
        ".jkmedoc",
        "blob:",
        "data:",
        "base64",
    ):
        assert forbidden not in viewer_source
        assert forbidden not in shell_source
