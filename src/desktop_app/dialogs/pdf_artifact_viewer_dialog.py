"""Shared in-memory viewer for verified encrypted final-PDF artifacts."""

from __future__ import annotations

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.components import DialogHeader, configure_button
from src.desktop_app.motion import MotionDialog


class PdfArtifactViewerError(RuntimeError):
    """Sanitized viewer error which never exposes PDF or storage details."""


class PdfArtifactBufferConsumer:
    """Collect one already verified adapter stream for the shared viewer."""

    def __init__(self) -> None:
        self._payload = bytearray()
        self._started = False
        self._finished = False

    def start(self, _artifact: object) -> None:
        self.clear()
        self._started = True

    def write(self, chunk: bytes) -> None:
        if not self._started or self._finished:
            raise PdfArtifactViewerError("pdf_viewer_consumer_state_invalid")
        self._payload.extend(chunk)

    def finish(self, _artifact: object) -> None:
        if not self._started:
            raise PdfArtifactViewerError("pdf_viewer_consumer_state_invalid")
        self._finished = True

    def abort(self, _reason: str) -> None:
        self.clear()

    def take(self) -> bytes:
        if not self._started or not self._finished or not self._payload:
            raise PdfArtifactViewerError("pdf_viewer_consumer_incomplete")
        result = bytes(self._payload)
        self.clear()
        return result

    def clear(self) -> None:
        self._payload.clear()
        self._started = False
        self._finished = False


class PdfArtifactViewerDialog(MotionDialog):
    """Display verified PDF bytes without creating a plaintext temp file."""

    _MINIMUM_ZOOM = 0.25
    _MAXIMUM_ZOOM = 4.0
    _ZOOM_STEP = 1.2

    def __init__(
        self,
        *,
        pdf_bytes: bytes,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._released = False
        self.setObjectName("PdfArtifactViewerDialog")
        self.setWindowTitle("Finales PDF")
        self.resize(1050, 820)
        self.setMinimumSize(760, 560)
        self.setWindowModality(Qt.WindowModality.WindowModal)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)
        root.addWidget(
            DialogHeader(
                "Finales PDF",
                "Schreibgeschützte Ansicht",
                "Das Dokument wird sicher aus dem verschlüsselten Speicher gelesen.",
                icon_name="report",
                context_role="report",
            )
        )

        self._pdf_data = QByteArray(pdf_bytes)
        self._pdf_buffer = QBuffer(self._pdf_data, self)
        if not self._pdf_buffer.open(QIODevice.OpenModeFlag.ReadOnly):
            self._release()
            raise PdfArtifactViewerError("pdf_viewer_buffer_open_failed")

        self._document = QPdfDocument(self)
        self._document.load(self._pdf_buffer)
        if (
            self._document.status() != QPdfDocument.Status.Ready
            or self._document.error() != QPdfDocument.Error.None_
            or self._document.pageCount() < 1
        ):
            self._release()
            raise PdfArtifactViewerError("pdf_viewer_document_invalid")

        self.viewer = QPdfView(self)
        self.viewer.setObjectName("PdfArtifactViewer")
        self.viewer.setAccessibleName("Finales PDF, schreibgeschützt")
        self.viewer.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.viewer.setDocument(self._document)
        self.viewer.setPageMode(QPdfView.PageMode.MultiPage)
        self.viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        root.addWidget(self.viewer, 1)

        actions = QHBoxLayout()
        status = QLabel("Finales PDF · schreibgeschützt")
        status.setAccessibleName("Finales PDF, schreibgeschützt")
        actions.addWidget(status)
        actions.addStretch(1)

        zoom_out = QPushButton("–")
        zoom_out.setObjectName("PdfArtifactZoomOutButton")
        configure_button(zoom_out, "secondary", "PDF verkleinern")
        zoom_out.clicked.connect(lambda: self._change_zoom(1 / self._ZOOM_STEP))
        actions.addWidget(zoom_out)

        self._zoom_label = QLabel("Breite")
        self._zoom_label.setMinimumWidth(64)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setAccessibleName("Aktuelle PDF-Vergrößerung")
        actions.addWidget(self._zoom_label)

        zoom_in = QPushButton("+")
        zoom_in.setObjectName("PdfArtifactZoomInButton")
        configure_button(zoom_in, "secondary", "PDF vergrößern")
        zoom_in.clicked.connect(lambda: self._change_zoom(self._ZOOM_STEP))
        actions.addWidget(zoom_in)

        fit_width = QPushButton("Breite")
        fit_width.setObjectName("PdfArtifactFitWidthButton")
        configure_button(fit_width, "secondary", "PDF an Fensterbreite anpassen")
        fit_width.clicked.connect(self._fit_to_width)
        actions.addWidget(fit_width)

        close_button = QPushButton("Schließen")
        close_button.setObjectName("PdfArtifactCloseButton")
        configure_button(close_button, "primary", "PDF-Ansicht schließen")
        close_button.clicked.connect(self.accept)
        actions.addWidget(close_button)
        root.addLayout(actions)

    @property
    def resources_released(self) -> bool:
        return self._released

    def _change_zoom(self, factor: float) -> None:
        current = self.viewer.zoomFactor()
        target = min(self._MAXIMUM_ZOOM, max(self._MINIMUM_ZOOM, current * factor))
        self.viewer.setZoomMode(QPdfView.ZoomMode.Custom)
        self.viewer.setZoomFactor(target)
        self._zoom_label.setText(f"{round(target * 100)} %")

    def _fit_to_width(self) -> None:
        self.viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._zoom_label.setText("Breite")

    def _release(self) -> None:
        if self._released:
            return
        self._released = True
        document = getattr(self, "_document", None)
        if document is not None:
            document.close()
        buffer = getattr(self, "_pdf_buffer", None)
        if buffer is not None:
            buffer.close()
        data = getattr(self, "_pdf_data", None)
        if data is not None:
            data.fill(0)
            data.clear()

    def done(self, result: int) -> None:
        self._release()
        super().done(result)
