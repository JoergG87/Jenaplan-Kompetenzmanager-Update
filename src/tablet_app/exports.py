"""Deliberate memory-rendered PDF export through the native iPad sharing port."""
from io import BytesIO
from pathlib import Path
import tempfile
import uuid


class TabletPdfShareService:
    def __init__(self, share_file=None, temporary_root=None):
        self._share_file = share_file
        self.temporary_root = Path(temporary_root or tempfile.gettempdir()).resolve() / 'jkm-tablet-share'

    def share_payload(self, payload: bytes, name: str):
        if not payload.startswith(b'%PDF-'):
            raise ValueError('Keine gültige PDF-Ausgabe.')
        if self.temporary_root.is_symlink():
            raise ValueError('Unsicherer Ausgabeordner.')
        self.temporary_root.mkdir(mode=0o700, exist_ok=True)
        directory = self.temporary_root / uuid.uuid4().hex
        directory.mkdir(mode=0o700)
        safe_name = ''.join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()[:100] or 'Jenaplan'
        path = directory / (safe_name + '.pdf')
        with path.open('xb') as output:
            output.write(payload)
        path.chmod(0o600)
        try:
            consumer = self._share_file
            if consumer is None:
                from jkm_ios_share import share_file
                consumer = share_file
            consumer(str(path))
        except Exception:
            path.unlink(missing_ok=True)
            directory.rmdir()
            raise
        return path

    def competency_pdf(self, model):
        from src.application.competency_pdf_completion import pending_competency_pdf_rows
        from src.application.competency_pdf_export import render_competency_pdf
        if pending_competency_pdf_rows(model):
            raise ValueError('Bitte alle Entwicklungsstände ausdrücklich auswählen.')
        return self.share_payload(render_competency_pdf(model), 'Kompetenzübersicht ' + model.student_name)

    def report_pdf(self, model):
        from prototypes.pdf_engine.renderer import PdfRenderer
        memory = BytesIO()
        PdfRenderer().render(model, memory)
        return self.share_payload(memory.getvalue(), 'Lernentwicklungsbericht ' + model.metadata.student_name)
