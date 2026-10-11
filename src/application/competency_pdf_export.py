"""Memory-only PDF rendering and deliberate exclusive external export; no database writes."""
from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import stat
import sys
from uuid import uuid4
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    Flowable, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from src.core.runtime_root_protection import require_unprotected_output_path


class CompetencyPdfExportError(ValueError):
    """An export cannot be completed without risking existing data."""


_TOKENS = ("--", "-", "+", "++")
_LEGENDS = {
    "standard": (
        "Du hast erste Erfahrungen gesammelt.",
        "Du kannst dein Wissen mit Unterstützung anwenden.",
        "Du kannst deine erworbenen Kenntnisse meist anwenden.",
        "Du kannst das Erlernte eigenständig und sicher anwenden.",
    ),
    "social": ("Kaum vorhanden", "Teilweise", "Gut", "Ausgeprägt"),
    "sport": ("Erste Übungen", "Übt noch", "Meist", "Sicher"),
}
_NAVY = colors.HexColor("#123F67")
_TEAL = colors.HexColor("#087F83")
_BORDER = colors.HexColor("#CBD8E2")


class _StageBar(Flowable):
    def __init__(self, rating: str):
        super().__init__()
        self.rating = rating
        self.width, self.height = 176, 16

    def draw(self):
        c = self.canv
        segment = self.width / 4
        c.setFillColor(colors.HexColor("#F0F5F8"))
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        if self.rating:
            count = _TOKENS.index(self.rating) + 1
            c.setFillColor(colors.HexColor("#A5D4CE"))
            c.rect(0, 0, count * segment, self.height, fill=1, stroke=0)
            c.setFillColor(_TEAL)
            c.circle((count - .5) * segment, self.height / 2, 2.5, fill=1, stroke=0)
        c.setStrokeColor(_BORDER)
        c.setLineWidth(.5)
        c.rect(0, 0, self.width, self.height, fill=0, stroke=1)
        for i in range(1, 4):
            c.line(i * segment, 0, i * segment, self.height)


def render_competency_pdf(model: object) -> bytes:
    """Render the registered immutable display model without using runtime paths."""
    from src.application.competency_pdf_completion import validate_competency_pdf_ready
    validate_competency_pdf_ready(model)
    resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    plants = resource_root / "assets/competency_plants"
    font, bold = "Helvetica", "Helvetica-Bold"
    regular = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    heavy = regular.with_name("Arial Bold.ttf")
    if regular.is_file() and heavy.is_file():
        pdfmetrics.registerFont(TTFont("CompetencySans", str(regular)))
        pdfmetrics.registerFont(TTFont("CompetencySansBold", str(heavy)))
        font, bold = "CompetencySans", "CompetencySansBold"
    body = ParagraphStyle("body", fontName=font, fontSize=9, leading=12, textColor=_NAVY)
    small = ParagraphStyle("small", parent=body, fontSize=7.5, leading=10,
                           textColor=colors.HexColor("#556372"))
    title = ParagraphStyle("title", parent=body, fontName=bold, fontSize=20, leading=25)
    heading = ParagraphStyle("heading", parent=body, fontName=bold, fontSize=14, leading=19)
    header = ParagraphStyle("header", parent=body, fontName=bold)
    def p(text, style=body):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)
    def image(stage, width=26, height=34):
        path = plants / f"stage_{stage}.png"
        if not path.is_file():
            raise CompetencyPdfExportError("Die Pflanzenbilder fehlen. Bitte die App neu installieren.")
        return Image(str(path), width=width, height=height, kind="proportional", mask="auto")
    story = []
    for index, subject in enumerate(model.subjects):
        if index:
            story.append(PageBreak())
        story.extend([
            p("Kompetenzübersicht", title), Spacer(1, 5),
            p(subject.name, heading),
            p(f"{model.student_name} · Fachauswahl Schuljahr {model.school_year}", body),
            Spacer(1, 8),
        ])
        labels = _LEGENDS[subject.rating_profile]
        legend = [
            [image(1, 20, 27), p(labels[0], small), image(2, 20, 27), p(labels[1], small)],
            [image(3, 20, 27), p(labels[2], small), image(4, 20, 27), p(labels[3], small)],
        ]
        legend_table = Table(legend, colWidths=[28, 227, 28, 228])
        legend_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                         ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                         ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        story.append(KeepTogether([legend_table, Spacer(1, 10)]))
        plant_header = Table([[image(i) for i in range(1, 5)]], colWidths=[44]*4)
        plant_header.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                         ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                         ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        data = [[p("Kompetenz · " + subject.name, header), [p("Entwicklungsstand", header), plant_header]]]
        for row in subject.rows:
            data.append([
                [p(row.text), Spacer(1, 3), p(row.context, small)],
                [_StageBar(row.rating)],
            ])
        table = Table(data, colWidths=[307, 204], repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF4FE")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F9FB")]),
            ("GRID", (0, 0), (-1, -1), .4, _BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(table)
    stream = BytesIO()
    def footer(c, doc):
        c.setFont(font, 8)
        c.setFillColor(_NAVY)
        c.drawString(42, 40, f"{model.student_name} · Fachauswahl Schuljahr {model.school_year}")
        c.drawString(42, 27, "Jenaplan-Kompetenzmanager · Kompetenzübersicht")
        c.drawRightString(A4[0]-42, 27, f"Seite {doc.page}")
    doc = SimpleDocTemplate(stream, pagesize=A4, leftMargin=42, rightMargin=42,
                           topMargin=38, bottomMargin=45,
                           title="Kompetenzübersicht", author="Jenaplan-Kompetenzmanager")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()


def export_competency_pdf(model: object, target: Path, *, runtime_root: Path) -> Path:
    """Create one new external PDF, never overwrite or publish an incomplete file."""
    target = Path(target).expanduser().absolute()
    if target.suffix.lower() != ".pdf":
        raise CompetencyPdfExportError("Bitte eine neue Datei mit der Endung .pdf wählen.")
    parent = target.parent
    if parent.resolve(strict=True) != parent:
        raise CompetencyPdfExportError("Bitte einen Zielordner ohne symbolische Verknüpfungen wählen.")
    if parent.is_relative_to(Path(runtime_root).resolve()):
        raise CompetencyPdfExportError("Bitte einen Ordner außerhalb der App-Daten wählen.")
    require_unprotected_output_path(target)
    payload = render_competency_pdf(model)
    directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    pending = f".jkm-competency-{uuid4().hex}.tmp"
    descriptor = None
    created = False
    published = False
    try:
        # Refuse existing files before staging and again atomically at publication.
        try:
            os.stat(target.name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError(target)
        descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=directory)
        created = True
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CompetencyPdfExportError("Das Exportziel ist keine normale Datei.")
        with os.fdopen(descriptor, "wb") as file:
            descriptor = None
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.link(pending, target.name, src_dir_fd=directory, dst_dir_fd=directory,
                follow_symlinks=False)
        published = True
        os.fsync(directory)
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        if published:
            os.unlink(target.name, dir_fd=directory)
        raise
    finally:
        if created:
            os.unlink(pending, dir_fd=directory)
        os.close(directory)
    return target
