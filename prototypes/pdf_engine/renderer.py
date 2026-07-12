"""ReportLab renderer for neutral output models. Contains no product logic."""

from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

try:
    from .output_models import (
        ChartBlock,
        CompetencyTimelineData,
        DocumentationCoverageData,
        HeadingBlock,
        ImagePlaceholderBlock,
        KeyValueBlock,
        ObservationTimelineData,
        ParagraphBlock,
        ReportOutputModel,
        SignatureBlock,
        SpacerBlock,
        TableBlock,
    )
except ImportError:
    from output_models import (  # type: ignore[no-redef]
        ChartBlock,
        CompetencyTimelineData,
        DocumentationCoverageData,
        HeadingBlock,
        ImagePlaceholderBlock,
        KeyValueBlock,
        ObservationTimelineData,
        ParagraphBlock,
        ReportOutputModel,
        SignatureBlock,
        SpacerBlock,
        TableBlock,
    )


INK = colors.HexColor("#23384A")
BLUE = colors.HexColor("#315F7D")
TEAL = colors.HexColor("#2A7774")
PALE = colors.HexColor("#EEF4F3")
LINE = colors.HexColor("#C9D5D9")
MUTED = colors.HexColor("#667782")
PAPER = colors.white


def _register_fonts() -> tuple[str, str]:
    candidates = (
        (
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
    )
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("ReportSans", str(regular)))
            pdfmetrics.registerFont(TTFont("ReportSans-Bold", str(bold)))
            return "ReportSans", "ReportSans-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = _register_fonts()


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    parts = [escape(part.strip()) for part in text.split("\n\n") if part.strip()]
    return Paragraph("<br/><br/>".join(parts), style)


class ImagePlaceholder(Flowable):
    def __init__(self, label: str, width: float, height: float) -> None:
        super().__init__()
        self.label = label
        self.width = width
        self.height = height

    def draw(self) -> None:
        self.canv.setStrokeColor(TEAL)
        self.canv.setLineWidth(1.2)
        self.canv.roundRect(0, 0, self.width, self.height, 7 * mm, stroke=1, fill=0)
        self.canv.setFillColor(TEAL)
        self.canv.setFont(FONT_BOLD, 11)
        self.canv.drawCentredString(self.width / 2, self.height / 2 - 4, self.label)


class DocumentationCoverageChart(Flowable):
    """Reusable chart that renders only supplied coverage values."""

    def __init__(self, data: DocumentationCoverageData, width: float) -> None:
        super().__init__()
        self.data = data
        self.width = width
        self.height = (20 + 16 * len(data.items) + 22) * mm / 3.78
        self.height = max(self.height, 45 * mm)

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 11)
        c.drawString(0, self.height - 12, self.data.title)
        y = self.height - 30
        label_width = 52 * mm
        bar_width = self.width - label_width - 23 * mm
        for item in self.data.items:
            c.setFillColor(INK)
            c.setFont(FONT, 8.5)
            c.drawString(0, y + 3, item.label)
            c.setFillColor(colors.HexColor("#E2E9EB"))
            c.roundRect(label_width, y, bar_width, 7, 3.5, stroke=0, fill=1)
            ratio = item.documented / item.total if item.total else 0
            c.setFillColor(TEAL)
            c.roundRect(label_width, y, bar_width * ratio, 7, 3.5, stroke=0, fill=1)
            c.setFillColor(INK)
            c.drawRightString(self.width, y + 2, f"{item.documented} von {item.total}")
            y -= 16
        note = Paragraph(
            escape(self.data.note),
            ParagraphStyle("chart-note", fontName=FONT, fontSize=7.5, leading=10, textColor=MUTED),
        )
        _, note_height = note.wrap(self.width, 18 * mm)
        note.drawOn(c, 0, 1)


class CompetencyTimelineChart(Flowable):
    """Reusable marker timeline. It never joins, scores, or interprets points."""

    def __init__(self, data: CompetencyTimelineData, width: float) -> None:
        super().__init__()
        self.data = data
        self.width = width
        self.row_height = 11.3 * mm
        self.height = 35 * mm + self.row_height * len(data.series)

    def _x_for(self, value: date, left: float, chart_width: float) -> float:
        span = (self.data.period_end - self.data.period_start).days
        position = (value - self.data.period_start).days / span
        return left + max(0.0, min(1.0, position)) * chart_width

    def draw(self) -> None:
        c = self.canv
        label_width = 82 * mm
        chart_left = label_width + 4 * mm
        chart_width = self.width - chart_left
        color_map = {name: colors.HexColor(value) for name, value in self.data.state_colors}
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 11)
        c.drawString(0, self.height - 10, self.data.title)
        y = self.height - 28
        for series in self.data.series:
            label = Paragraph(
                escape(series.label),
                ParagraphStyle("timeline-label", fontName=FONT, fontSize=7.4, leading=9, textColor=INK),
            )
            _, label_height = label.wrap(label_width - 4 * mm, self.row_height - 2)
            label.drawOn(c, 0, y - min(label_height, self.row_height - 2) / 2 + 2)
            c.setStrokeColor(LINE)
            c.setLineWidth(0.7)
            c.line(chart_left, y, chart_left + chart_width, y)
            if series.points:
                for point in series.points:
                    x = self._x_for(point.recorded_on, chart_left, chart_width)
                    c.setFillColor(color_map.get(point.state_label, MUTED))
                    c.circle(x, y, 3.2, stroke=0, fill=1)
            else:
                c.setFillColor(MUTED)
                c.setFont(FONT, 7)
                c.drawString(chart_left + 2, y + 3, "keine datierten Angaben")
            y -= self.row_height
        c.setFillColor(MUTED)
        c.setFont(FONT, 7)
        c.drawString(chart_left, y + 5, self.data.period_start.strftime("%d.%m.%Y"))
        c.drawRightString(chart_left + chart_width, y + 5, self.data.period_end.strftime("%d.%m.%Y"))
        legend_x = 0
        legend_y = 12 * mm
        for name, color_value in self.data.state_colors:
            c.setFillColor(colors.HexColor(color_value))
            c.circle(legend_x + 3, legend_y + 2, 3, stroke=0, fill=1)
            c.setFillColor(INK)
            c.setFont(FONT, 7.2)
            c.drawString(legend_x + 9, legend_y, name)
            legend_x += pdfmetrics.stringWidth(name, FONT, 7.2) + 23
        note = Paragraph(
            escape(self.data.note),
            ParagraphStyle("timeline-note", fontName=FONT, fontSize=7.2, leading=9, textColor=MUTED),
        )
        note.wrapOn(c, self.width, 9 * mm)
        note.drawOn(c, 0, 0)


class ObservationTimelineChart(Flowable):
    """Reusable chronological event chart based solely on supplied events."""

    def __init__(self, data: ObservationTimelineData, width: float) -> None:
        super().__init__()
        self.data = data
        self.width = width
        self.height = 50 * mm

    def _x_for(self, value: date, left: float, chart_width: float) -> float:
        span = (self.data.period_end - self.data.period_start).days
        return left + ((value - self.data.period_start).days / span) * chart_width

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 11)
        c.drawString(0, self.height - 10, self.data.title)
        left, right, axis_y = 7 * mm, self.width - 7 * mm, 24 * mm
        c.setStrokeColor(LINE)
        c.setLineWidth(1)
        c.line(left, axis_y, right, axis_y)
        for index, event in enumerate(self.data.events):
            x = self._x_for(event.observed_on, left, right - left)
            c.setFillColor(TEAL if index % 2 == 0 else BLUE)
            c.circle(x, axis_y, 3.2, stroke=0, fill=1)
            c.setStrokeColor(LINE)
            c.line(x, axis_y + 4, x, axis_y + 15)
            c.setFillColor(INK)
            c.setFont(FONT_BOLD, 6.8)
            c.drawCentredString(x, axis_y + 20, event.observed_on.strftime("%d.%m."))
            c.setFont(FONT, 6.5)
            c.drawCentredString(x, axis_y + 12, event.context[:18])
        c.setFillColor(MUTED)
        c.setFont(FONT, 7.2)
        c.drawString(0, 2, self.data.note)


class PdfRenderer:
    """Renders a complete output model without reading or deriving product data."""

    def __init__(self) -> None:
        base = getSampleStyleSheet()
        self.styles = {
            "cover": ParagraphStyle(
                "cover", parent=base["Title"], fontName=FONT_BOLD, fontSize=29,
                leading=34, textColor=INK, alignment=TA_CENTER, spaceAfter=8 * mm,
            ),
            "h1": ParagraphStyle(
                "h1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=21,
                leading=25, textColor=INK, spaceAfter=7 * mm,
            ),
            "h2": ParagraphStyle(
                "h2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=13,
                leading=17, textColor=TEAL, spaceBefore=2 * mm, spaceAfter=4 * mm,
            ),
            "body": ParagraphStyle(
                "body", parent=base["BodyText"], fontName=FONT, fontSize=10.2,
                leading=15.4, textColor=INK, alignment=TA_LEFT, spaceAfter=3.5 * mm,
            ),
            "lead": ParagraphStyle(
                "lead", parent=base["BodyText"], fontName=FONT, fontSize=11.2,
                leading=16, textColor=MUTED, spaceAfter=5 * mm,
            ),
            "small": ParagraphStyle(
                "small", parent=base["BodyText"], fontName=FONT, fontSize=8.3,
                leading=11, textColor=INK,
            ),
            "table_head": ParagraphStyle(
                "table_head", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=8.6,
                leading=11, textColor=PAPER,
            ),
        }

    def render(self, model: ReportOutputModel, output_path: str | Path) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        document = BaseDocTemplate(
            str(target), pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm,
            topMargin=25 * mm, bottomMargin=20 * mm,
            title=model.metadata.document_title,
            author=model.metadata.school_name,
            subject=f"{model.metadata.document_title} - {model.metadata.student_name}",
            creator="Isolierter Jenaplan PDF-Engine-Prototyp",
        )
        frame = Frame(
            document.leftMargin, document.bottomMargin, document.width, document.height,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )
        document.addPageTemplates(
            PageTemplate("report", frames=(frame,), onPage=lambda canvas, doc: self._page_decorations(canvas, doc, model))
        )

        story: list[Flowable] = []
        for page_index, page in enumerate(model.pages):
            if page_index:
                story.append(PageBreak())
            for block in page.blocks:
                story.extend(self._render_block(block, document.width))
        document.build(story)
        return target

    def _render_block(self, block: object, width: float) -> list[Flowable]:
        if isinstance(block, HeadingBlock):
            key = "cover" if block.level == 0 else "h1" if block.level == 1 else "h2"
            return [_paragraph(block.text, self.styles[key])]
        if isinstance(block, ParagraphBlock):
            style = self.styles["lead"] if block.emphasis == "lead" else self.styles["body"]
            return [_paragraph(block.text, style)]
        if isinstance(block, SpacerBlock):
            return [Spacer(1, block.height_mm * mm)]
        if isinstance(block, ImagePlaceholderBlock):
            placeholder = ImagePlaceholder(block.label, block.width_mm * mm, block.height_mm * mm)
            return [Table([[placeholder]], colWidths=[width], style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))]
        if isinstance(block, KeyValueBlock):
            rows = [
                [Paragraph(escape(key), self.styles["small"]), Paragraph(escape(value), self.styles["body"])]
                for key, value in block.items
            ]
            table = Table(rows, colWidths=(38 * mm, width - 38 * mm), hAlign="LEFT")
            table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            return [table]
        if isinstance(block, TableBlock):
            weights = block.column_weights or tuple(1.0 for _ in block.headers)
            total = sum(weights)
            widths = [width * value / total for value in weights]
            rows = [[Paragraph(escape(value), self.styles["table_head"]) for value in block.headers]]
            rows.extend(
                [Paragraph(escape(value), self.styles["small"]) for value in row]
                for row in block.rows
            )
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), (PAPER, PALE)),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            return [table]
        if isinstance(block, ChartBlock):
            if isinstance(block.data, DocumentationCoverageData):
                return [DocumentationCoverageChart(block.data, width)]
            if isinstance(block.data, CompetencyTimelineData):
                return [CompetencyTimelineChart(block.data, width)]
            if isinstance(block.data, ObservationTimelineData):
                return [ObservationTimelineChart(block.data, width)]
        if isinstance(block, SignatureBlock):
            cells = []
            for label in block.labels:
                cells.append(Paragraph(f"<br/><br/><br/>_________________________<br/>{escape(label)}", self.styles["small"]))
            table = Table([cells], colWidths=[width / len(cells)] * len(cells))
            table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("ALIGN", (0, 0), (-1, -1), "LEFT")]))
            return [KeepTogether([table])]
        raise TypeError(f"Unsupported output block: {type(block).__name__}")

    def _page_decorations(self, canvas, document, model: ReportOutputModel) -> None:
        page_number = canvas.getPageNumber()
        canvas.saveState()
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(document.leftMargin, A4[1] - 17 * mm, A4[0] - document.rightMargin, A4[1] - 17 * mm)
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(document.leftMargin, A4[1] - 13 * mm, model.metadata.header_text)
        canvas.line(document.leftMargin, 14 * mm, A4[0] - document.rightMargin, 14 * mm)
        canvas.drawString(document.leftMargin, 9 * mm, model.metadata.footer_text)
        canvas.drawRightString(A4[0] - document.rightMargin, 9 * mm, f"Seite {page_number} von {len(model.pages)}")
        canvas.restoreState()
