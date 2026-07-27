"""Build the reproducible, reader-oriented PDF guides for the pilot."""

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image as PillowImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.frames import Frame
from reportlab.platypus.tableofcontents import TableOfContents


# Shared A4 design tokens. Their editorial rationale is documented in
# docs/user_manual/DOCUMENT_DESIGN_SYSTEM.md.
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 22 * mm
MARGIN_TOP = 22 * mm
MARGIN_BOTTOM = 20 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X
INK = colors.HexColor("#203148")
MUTED = colors.HexColor("#66758A")
ACCENT = colors.HexColor("#355A7A")
ACCENT_SOFT = colors.HexColor("#EAF1F7")
PALE = colors.HexColor("#F2F6FA")
LINE = colors.HexColor("#DCE5EE")
SUCCESS = colors.HexColor("#EAF5F1")
SUCCESS_INK = colors.HexColor("#246B56")
WARM = colors.HexColor("#FFF7E6")
WARM_INK = colors.HexColor("#885B0C")
NEUTRAL = colors.HexColor("#EEF3F7")
SCREEN_PANEL = colors.HexColor("#F5F8FB")


@dataclass(frozen=True)
class DocumentProfile:
    source: Path
    filename: str
    title: str
    short_title: str
    subtitle: str
    audience: str
    status: str
    include_cover: bool = True
    include_toc: bool = False
    compact: bool = False


def _register_fonts() -> None:
    font_root = Path("/System/Library/Fonts/Supplemental")
    pdfmetrics.registerFont(TTFont("PilotSans", font_root / "Arial.ttf"))
    pdfmetrics.registerFont(TTFont("PilotSans-Bold", font_root / "Arial Bold.ttf"))
    pdfmetrics.registerFontFamily(
        "PilotSans",
        normal="PilotSans",
        bold="PilotSans-Bold",
    )


class PilotDocTemplate(BaseDocTemplate):
    def __init__(
        self,
        filename: str,
        *,
        version: str,
        build_version: str,
        document_date: str,
        title: str,
        short_title: str,
        header_on_first_page: bool,
    ) -> None:
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=MARGIN_X,
            rightMargin=MARGIN_X,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title=title,
            author="Jenaplan-Kompetenzmanager",
            subject=f"Version {version} · Build {build_version}",
        )
        self.version = version
        self.build_version = build_version
        self.document_date = document_date
        self.document_title = title
        self.short_title = short_title
        self.header_on_first_page = header_on_first_page
        self.current_chapter = ""
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="body",
        )
        self.addPageTemplates(
            PageTemplate(id="pilot", frames=(frame,), onPage=self._page)
        )

    def beforeDocument(self) -> None:
        self.current_chapter = ""

    def _page(self, canvas, doc) -> None:  # type: ignore[no-untyped-def]
        canvas.saveState()
        if doc.page > 1 or self.header_on_first_page:
            canvas.setFont("PilotSans", 8)
            canvas.setFillColor(MUTED)
            canvas.drawString(MARGIN_X, PAGE_HEIGHT - 12 * mm, self.short_title)
            chapter = self.current_chapter
            if chapter:
                canvas.drawRightString(
                    PAGE_WIDTH - MARGIN_X,
                    PAGE_HEIGHT - 12 * mm,
                    chapter,
                )
            canvas.setStrokeColor(LINE)
            canvas.line(
                MARGIN_X,
                PAGE_HEIGHT - 15 * mm,
                PAGE_WIDTH - MARGIN_X,
                PAGE_HEIGHT - 15 * mm,
            )
        canvas.setFont("PilotSans", 7.7)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            MARGIN_X,
            10.8 * mm,
            f"Jenaplan-Kompetenzmanager · Version {self.version} / Build {self.build_version}",
        )
        canvas.drawCentredString(PAGE_WIDTH / 2, 10.8 * mm, self.document_date)
        canvas.drawRightString(
            PAGE_WIDTH - MARGIN_X,
            10.8 * mm,
            f"Seite {doc.page}",
        )
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:  # type: ignore[no-untyped-def]
        if isinstance(flowable, Paragraph) and flowable.style.name == "PilotH1":
            text = flowable.getPlainText()
            self.current_chapter = text
            key = f"heading-{self.seq.nextf('heading')}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=0, closed=False)
            self.notify("TOCEntry", (0, text, self.page, key))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "PilotBody",
            parent=base["BodyText"],
            fontName="PilotSans",
            fontSize=10.2,
            leading=14.6,
            textColor=INK,
            spaceAfter=6.5,
            allowWidows=0,
            allowOrphans=0,
        ),
        "lead": ParagraphStyle(
            "PilotLead",
            parent=base["BodyText"],
            fontName="PilotSans",
            fontSize=11.2,
            leading=16.2,
            textColor=INK,
            spaceAfter=9,
        ),
        "h1": ParagraphStyle(
            "PilotH1",
            parent=base["Heading1"],
            fontName="PilotSans-Bold",
            fontSize=18.5,
            leading=23,
            textColor=ACCENT,
            spaceBefore=12,
            spaceAfter=9,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "PilotH2",
            parent=base["Heading2"],
            fontName="PilotSans-Bold",
            fontSize=13.2,
            leading=17,
            textColor=INK,
            spaceBefore=10,
            spaceAfter=5.5,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "PilotH3",
            parent=base["Heading3"],
            fontName="PilotSans-Bold",
            fontSize=11.2,
            leading=14.5,
            textColor=INK,
            spaceBefore=8,
            spaceAfter=4.5,
            keepWithNext=True,
        ),
        "bullet": ParagraphStyle(
            "PilotBullet",
            parent=base["BodyText"],
            fontName="PilotSans",
            fontSize=9.9,
            leading=13.8,
            textColor=INK,
        ),
        "step_number": ParagraphStyle(
            "PilotStepNumber",
            parent=base["BodyText"],
            fontName="PilotSans-Bold",
            fontSize=9.3,
            leading=12,
            alignment=TA_CENTER,
            textColor=ACCENT,
        ),
        "caption": ParagraphStyle(
            "PilotCaption",
            parent=base["BodyText"],
            fontName="PilotSans",
            fontSize=8.6,
            leading=11.5,
            alignment=TA_CENTER,
            textColor=MUTED,
            spaceBefore=3,
            spaceAfter=10,
            keepWithNext=True,
        ),
        "code": ParagraphStyle(
            "PilotCode",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8.3,
            leading=11.3,
            leftIndent=4 * mm,
            rightIndent=4 * mm,
            borderColor=LINE,
            borderWidth=0.5,
            borderPadding=5,
            backColor=PALE,
            textColor=INK,
            spaceAfter=8,
        ),
        "table": ParagraphStyle(
            "PilotTable",
            parent=base["BodyText"],
            fontName="PilotSans",
            fontSize=9,
            leading=12,
            textColor=INK,
        ),
        "table_header": ParagraphStyle(
            "PilotTableHeader",
            parent=base["BodyText"],
            fontName="PilotSans-Bold",
            fontSize=9,
            leading=12,
            textColor=INK,
        ),
        "callout_label": ParagraphStyle(
            "PilotCalloutLabel",
            parent=base["BodyText"],
            fontName="PilotSans-Bold",
            fontSize=8.4,
            leading=10.5,
            textColor=ACCENT,
            spaceAfter=2,
        ),
        "callout": ParagraphStyle(
            "PilotCallout",
            parent=base["BodyText"],
            fontName="PilotSans",
            fontSize=9.5,
            leading=13.1,
            textColor=INK,
            spaceAfter=0,
        ),
        "cover_brand": ParagraphStyle(
            "PilotCoverBrand",
            parent=base["BodyText"],
            fontName="PilotSans-Bold",
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            textColor=ACCENT,
            spaceAfter=5,
        ),
    }


def _inline(value: str) -> str:
    value = value.replace("–", "-").replace("—", "-").replace("‑", "-")
    escaped = html.escape(value, quote=False)
    escaped = re.sub(
        r"`([^`]+)`",
        r"<font name='Courier' color='#355A7A'>\1</font>",
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", escaped)
    return escaped


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_inline(" ".join(text.split())), style)


def _list_table(
    items: list[tuple[str, str]],
    styles: dict[str, ParagraphStyle],
) -> Table:
    rows = [
        [
            Paragraph(_inline(marker), styles["step_number"]),
            Paragraph(_inline(content), styles["bullet"]),
        ]
        for marker, content in items
    ]
    table = Table(
        rows,
        colWidths=[10 * mm, CONTENT_WIDTH - 10 * mm],
        hAlign="LEFT",
        splitByRow=1,
        spaceBefore=1,
        spaceAfter=7,
    )
    table.setStyle(
        TableStyle(
            (
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), ACCENT_SOFT),
                ("BOX", (0, 0), (0, -1), 0.4, LINE),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, LINE),
                ("LEFTPADDING", (0, 0), (0, -1), 2),
                ("RIGHTPADDING", (0, 0), (0, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (1, 0), (1, -1), 6),
                ("RIGHTPADDING", (1, 0), (1, -1), 1),
            )
        )
    )
    return table


def _adaptive_widths(rows: list[list[str]]) -> list[float]:
    columns = max(len(row) for row in rows)
    weights = [
        max(8, max((len(row[index]) if index < len(row) else 0) for row in rows))
        for index in range(columns)
    ]
    available = CONTENT_WIDTH
    total = sum(weights)
    widths = [available * weight / total for weight in weights]
    minimum = 24 * mm
    if columns > 1 and any(width < minimum for width in widths):
        shortfall = sum(max(0, minimum - width) for width in widths)
        largest = max(range(columns), key=lambda index: widths[index])
        widths = [max(minimum, width) for width in widths]
        widths[largest] -= shortfall
    return widths


def _markdown_table(rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> Table:
    widths = _adaptive_widths(rows)
    data = [
        [
            Paragraph(
                _inline(cell),
                styles["table_header"] if row_index == 0 else styles["table"],
            )
            for cell in row
        ]
        for row_index, row in enumerate(rows)
    ]
    table = Table(
        data,
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT",
        spaceBefore=3,
        spaceAfter=9,
    )
    table.setStyle(
        TableStyle(
            (
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT_SOFT),
                ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                ("LINEABOVE", (0, 0), (-1, 0), 0.7, ACCENT),
                ("LINEBELOW", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            )
        )
    )
    return table


def _callout(
    kind: str,
    content: Iterable[str],
    styles: dict[str, ParagraphStyle],
) -> Table:
    canonical = kind.upper()
    palette = {
        "TIPP": (ACCENT_SOFT, ACCENT),
        "HINWEIS": (PALE, ACCENT),
        "SICHERHEIT": (SUCCESS, SUCCESS_INK),
        "VORAUSSETZUNG": (NEUTRAL, ACCENT),
        "KONTROLLE": (SUCCESS, SUCCESS_INK),
        "FEHLERBEHEBUNG": (WARM, WARM_INK),
        "WARNUNG": (WARM, WARM_INK),
    }
    background, label_color = palette.get(canonical, palette["HINWEIS"])
    title = Paragraph(
        _inline(canonical.title()),
        ParagraphStyle(
            f"Callout{canonical}",
            parent=styles["callout_label"],
            textColor=label_color,
        ),
    )
    body_lines = list(content)
    body: list[object] = [title]
    bullets = [line[2:].strip() for line in body_lines if line.startswith("- ")]
    prose = [line for line in body_lines if not line.startswith("- ")]
    if prose:
        body.append(_paragraph(" ".join(prose), styles["callout"]))
    if bullets:
        body.append(Spacer(1, 2))
        for bullet in bullets:
            body.append(
                Paragraph(f"•&nbsp;&nbsp;{_inline(bullet)}", styles["callout"])
            )
    table = Table(
        [[body]],
        colWidths=[CONTENT_WIDTH],
        hAlign="LEFT",
        spaceBefore=4,
        spaceAfter=9,
    )
    table.setStyle(
        TableStyle(
            (
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("LINEBEFORE", (0, 0), (0, -1), 2.2, label_color),
                ("BOX", (0, 0), (-1, -1), 0.4, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            )
        )
    )
    return table


def _image_block(
    image_path: Path,
    caption: str,
    styles: dict[str, ParagraphStyle],
) -> KeepTogether:
    with PillowImage.open(image_path) as source_image:
        width, height = source_image.size
    max_width = 162 * mm
    image_height_limits = {
        "15_anmeldung.png": 72 * mm,
        "16_passwortanlage.png": 72 * mm,
        "17_sicherheit_touch_id.png": 76 * mm,
        "20_backup.png": 72 * mm,
        "21_restore_vorschau.png": 72 * mm,
        "22_restore_neustart.png": 45 * mm,
        "23_about_build_302.png": 62 * mm,
    }
    max_height = image_height_limits.get(image_path.name, 94 * mm)
    scale = min(max_width / width, max_height / height)
    image = Image(str(image_path), width=width * scale, height=height * scale)
    frame = Table(
        [[image]],
        colWidths=[max_width],
        hAlign="CENTER",
        style=TableStyle(
            (
                ("BACKGROUND", (0, 0), (-1, -1), SCREEN_PANEL),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            )
        ),
    )
    return KeepTogether(
        [
            Spacer(1, 2),
            frame,
            Paragraph(_inline(caption), styles["caption"]),
        ]
    )


def _collect_list(lines: list[str], index: int) -> tuple[list[tuple[str, str]], int]:
    entries: list[tuple[str, str]] = []
    while index < len(lines):
        stripped = lines[index].strip()
        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        numbered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        checklist = re.match(r"^- \[[ xX]\]\s+(.+)$", stripped)
        if not bullet and not numbered:
            break
        if checklist:
            marker = "✓" if "[x]" in stripped.lower() else "□"
            content = checklist.group(1)
        elif numbered:
            marker = f"{numbered.group(1)}"
            content = numbered.group(2)
        else:
            marker = "•"
            content = bullet.group(1)
        index += 1
        while index < len(lines):
            continuation = lines[index]
            continuation_stripped = continuation.strip()
            if not continuation_stripped:
                break
            if re.match(r"^\s+", continuation) and not re.match(
                r"^\s*(?:[-*]\s+|\d+\.\s+)", continuation
            ):
                content += " " + continuation_stripped
                index += 1
                continue
            break
        entries.append((marker, content))
        if index < len(lines) and not lines[index].strip():
            break
    return entries, index


def _markdown_story(
    source_path: Path,
    styles: dict[str, ParagraphStyle],
    *,
    version: str,
    build_version: str,
) -> list[object]:
    lines = (
        source_path.read_text(encoding="utf-8")
        .replace("{{PILOT_VERSION}}", version)
        .replace("{{PILOT_BUILD}}", build_version)
        .splitlines()
    )
    story: list[object] = []
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []
    index = 0

    def flush() -> None:
        if paragraph:
            style = styles["lead"] if not story else styles["body"]
            story.append(_paragraph(" ".join(paragraph), style))
            paragraph.clear()

    while index < len(lines):
        raw = lines[index].rstrip()
        stripped = raw.strip()
        if stripped.startswith("```"):
            flush()
            if in_code:
                story.append(
                    Paragraph(
                        "<br/>".join(html.escape(line) for line in code_lines),
                        styles["code"],
                    )
                )
                code_lines.clear()
            in_code = not in_code
            index += 1
            continue
        if in_code:
            code_lines.append(raw)
            index += 1
            continue
        callout = re.fullmatch(r">\s*\[!([A-Za-zÄÖÜäöü]+)\]", stripped)
        if callout:
            flush()
            content: list[str] = []
            index += 1
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                callout_line = lines[index].lstrip()[1:].strip()
                if callout_line and content and not callout_line.startswith("- ") and content[-1].startswith("- "):
                    content[-1] += " " + callout_line
                else:
                    content.append(callout_line)
                index += 1
            story.append(_callout(callout.group(1), content, styles))
            continue
        image_match = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", stripped)
        if image_match:
            flush()
            image_path = (source_path.parent / image_match.group(2)).resolve()
            if not image_path.is_file():
                raise FileNotFoundError(f"Handbuchbild fehlt: {image_path}")
            story.append(_image_block(image_path, image_match.group(1), styles))
            index += 1
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            flush()
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows = [
                [cell.strip() for cell in row.strip("|").split("|")]
                for row in table_lines
                if not re.fullmatch(r"\|?[\s:|-]+\|?", row)
            ]
            if rows:
                story.append(_markdown_table(rows, styles))
            continue
        heading = re.match(r"^(#{2,4})\s+(.+)$", stripped)
        if heading:
            flush()
            level = len(heading.group(1))
            if level == 2:
                story.append(CondPageBreak(62 * mm))
            elif level == 3:
                story.append(CondPageBreak(34 * mm))
            story.append(
                Paragraph(
                    _inline(heading.group(2)),
                    styles[{2: "h1", 3: "h2", 4: "h3"}[level]],
                )
            )
            index += 1
            continue
        if stripped.startswith("# "):
            flush()
            index += 1
            continue
        if stripped == "<!-- pagebreak -->":
            flush()
            story.append(PageBreak())
            index += 1
            continue
        if re.match(r"^(?:[-*]\s+|\d+\.\s+)", stripped):
            flush()
            items, index = _collect_list(lines, index)
            list_table = _list_table(items, styles)
            story.append(KeepTogether([list_table]) if len(items) <= 8 else list_table)
            continue
        if stripped in ("---", ""):
            flush()
            if stripped == "---":
                story.append(Spacer(1, 5))
            index += 1
            continue
        paragraph.append(stripped)
        index += 1
    flush()
    return story


def _metadata_block(
    profile: DocumentProfile,
    version: str,
    build_version: str,
    document_date: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    rows = [
        [
            Paragraph("<b>Zielgruppe</b><br/>" + _inline(profile.audience), styles["table"]),
            Paragraph("<b>Dokumentstand</b><br/>" + _inline(document_date), styles["table"]),
        ],
        [
            Paragraph(
                f"<b>Version</b><br/>{_inline(version)} · Build {_inline(build_version)}",
                styles["table"],
            ),
            Paragraph("<b>Status</b><br/>" + _inline(profile.status), styles["table"]),
        ],
    ]
    table = Table(
        rows,
        colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2],
        hAlign="CENTER",
        style=TableStyle(
            (
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("LINEABOVE", (0, 0), (-1, 0), 0.8, ACCENT),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, LINE),
                ("LINEAFTER", (0, 0), (0, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            )
        ),
    )
    return table


def _cover(
    profile: DocumentProfile,
    version: str,
    build_version: str,
    document_date: str,
    icon_path: Path,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["h1"],
        fontSize=26,
        leading=32,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["body"],
        fontSize=13,
        leading=18,
        alignment=TA_CENTER,
        textColor=MUTED,
        spaceAfter=14,
    )
    return [
        Spacer(1, 20 * mm),
        Image(str(icon_path), width=31 * mm, height=31 * mm, hAlign="CENTER"),
        Spacer(1, 8 * mm),
        Paragraph("Jenaplan-Kompetenzmanager", styles["cover_brand"]),
        Paragraph(_inline(profile.title), title_style),
        Paragraph(_inline(profile.subtitle), subtitle_style),
        Spacer(1, 16 * mm),
        _metadata_block(profile, version, build_version, document_date, styles),
        Spacer(1, 12 * mm),
        Paragraph(
            "Lokale Desktop-App · macOS auf Apple Silicon",
            ParagraphStyle(
                "CoverFootnote",
                parent=styles["caption"],
                alignment=TA_CENTER,
                textColor=MUTED,
            ),
        ),
        PageBreak(),
    ]


def _compact_header(
    profile: DocumentProfile,
    version: str,
    build_version: str,
    document_date: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    title_style = ParagraphStyle(
        "CompactTitle",
        parent=styles["h1"],
        fontSize=16,
        leading=20,
        spaceBefore=0,
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "CompactSubtitle",
        parent=styles["body"],
        fontSize=10,
        leading=14,
        textColor=MUTED,
        spaceAfter=0,
    )
    meta = Paragraph(
        f"{_inline(profile.audience)}<br/>Version {version} · Build {build_version}<br/>{_inline(document_date)}",
        ParagraphStyle(
            "CompactMeta",
            parent=styles["table"],
            alignment=TA_LEFT,
            textColor=MUTED,
        ),
    )
    table = Table(
        [[
            [Paragraph(_inline(profile.title), title_style), Paragraph(_inline(profile.subtitle), subtitle_style)],
            meta,
        ]],
        colWidths=[CONTENT_WIDTH * 0.60, CONTENT_WIDTH * 0.40],
        hAlign="LEFT",
        spaceAfter=12,
    )
    table.setStyle(
        TableStyle(
            (
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("LINEBEFORE", (0, 0), (0, -1), 2.5, ACCENT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            )
        )
    )
    return table


def build_pdf(
    profile: DocumentProfile,
    output: Path,
    *,
    version: str,
    build_version: str,
    document_date: str,
    icon: Path,
) -> None:
    styles = _styles()
    story: list[object] = []
    if profile.include_cover:
        story.extend(
            _cover(
                profile,
                version,
                build_version,
                document_date,
                icon,
                styles,
            )
        )
    elif profile.compact:
        story.append(
            _compact_header(profile, version, build_version, document_date, styles)
        )
    if profile.include_toc:
        toc_heading = ParagraphStyle("TOCHeading", parent=styles["h1"], spaceBefore=0)
        story.append(Paragraph("Inhaltsverzeichnis", toc_heading))
        story.append(
            Paragraph(
                "Die Kapitel folgen der Bedienung und den wichtigen Kontrollpunkten.",
                styles["lead"],
            )
        )
        toc = TableOfContents()
        toc.levelStyles = (
            ParagraphStyle(
                "TOC1",
                fontName="PilotSans",
                fontSize=10,
                leading=15,
                leftIndent=0,
                firstLineIndent=0,
                textColor=INK,
            ),
        )
        story.extend((toc, PageBreak()))
    story.extend(
        _markdown_story(
            profile.source,
            styles,
            version=version,
            build_version=build_version,
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    PilotDocTemplate(
        str(output),
        version=version,
        build_version=build_version,
        document_date=document_date,
        title=profile.title,
        short_title=profile.short_title,
        header_on_first_page=profile.compact,
    ).multiBuild(story)


def _build_name(version: str, build_version: str, suffix: str) -> str:
    return f"Jenaplan-Kompetenzmanager-{version}-Build-{build_version}-{suffix}.pdf"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--build-version", required=True)
    parser.add_argument("--pilot-commit", default="", help=argparse.SUPPRESS)
    parser.add_argument("--document-date", default="27. Juli 2026")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manual-only", action="store_true")
    parser.add_argument("--manual-output", type=Path)
    parser.add_argument("--named-for-build", action="store_true")
    parser.add_argument("--extended-guides", action="store_true")
    parser.add_argument("--installation-source", type=Path, required=True)
    parser.add_argument("--manual-source", type=Path, required=True)
    parser.add_argument("--first-steps-source", type=Path, required=True)
    parser.add_argument("--quickstart-source", type=Path, required=True)
    parser.add_argument("--backup-source", type=Path, required=True)
    parser.add_argument(
        "--security-source",
        type=Path,
        default=Path("docs/SICHERHEIT_UND_VERSCHLUESSELUNG.md"),
    )
    parser.add_argument(
        "--support-reset-source",
        type=Path,
        default=Path("docs/SUPPORT_RESET_OPERATIONS.md"),
    )
    parser.add_argument(
        "--release-notes-source",
        type=Path,
        default=Path("docs/RELEASE_NOTES.md"),
    )
    parser.add_argument("--icon", type=Path, default=Path("assets/app_icon.png"))
    args = parser.parse_args()
    _register_fonts()

    legacy_names = not args.named_for_build
    manual_output = args.manual_output or (
        args.output_dir
        / (
            f"Jenaplan-Kompetenzmanager-Pilot-{args.version}-Benutzerhandbuch.pdf"
            if legacy_names
            else _build_name(args.version, args.build_version, "Benutzerhandbuch")
        )
    )
    profiles = [
        (
            DocumentProfile(
                args.manual_source,
                "Benutzerhandbuch",
                "Benutzerhandbuch",
                "Benutzerhandbuch",
                "Sicher orientieren, dokumentieren und Berichte vorbereiten",
                "Lehrkräfte, Stammdatenpflege und technische Betreuung",
                "Interner, nicht öffentlicher Pilotstand",
                include_toc=True,
            ),
            manual_output,
        ),
    ]
    if not args.manual_only:
        installation_name = (
            f"Jenaplan-Kompetenzmanager-Pilot-{args.version}-Installationsanleitung.pdf"
            if legacy_names
            else _build_name(args.version, args.build_version, "Installationsanleitung")
        )
        first_steps_name = (
            f"Jenaplan-Kompetenzmanager-Pilot-{args.version}-Erste-Schritte.pdf"
            if legacy_names
            else _build_name(args.version, args.build_version, "Erste-Schritte")
        )
        quickstart_name = (
            f"Jenaplan-Kompetenzmanager-Pilot-{args.version}-Schnellstart-Lehrkraefte.pdf"
            if legacy_names
            else _build_name(args.version, args.build_version, "Schnellstart-Lehrkraefte")
        )
        backup_name = (
            f"Jenaplan-Kompetenzmanager-Pilot-{args.version}-Backup-Anleitung.pdf"
            if legacy_names
            else _build_name(args.version, args.build_version, "Backup-und-Wiederherstellung")
        )
        profiles.extend(
            [
                (
                    DocumentProfile(
                        args.installation_source,
                        "Installationsanleitung",
                        "Installation des Jenaplan-Kompetenzmanagers",
                        "Installation",
                        "Schritt für Schritt zum ersten Start",
                        "Lehrkräfte und schulische technische Betreuung",
                        "Hilfe zum vorgesehenen internen Stand",
                    ),
                    args.output_dir / installation_name,
                ),
                (
                    DocumentProfile(
                        args.first_steps_source,
                        "Erste Schritte",
                        "Erste Schritte",
                        "Erste Schritte",
                        "Ruhig in der lokalen App ankommen",
                        "Lehrkräfte",
                        "Kompakter Einstieg",
                        include_cover=False,
                        compact=True,
                    ),
                    args.output_dir / first_steps_name,
                ),
                (
                    DocumentProfile(
                        args.quickstart_source,
                        "Schnellstart",
                        "Schnellstart für Lehrkräfte",
                        "Schnellstart",
                        "Die wichtigsten Wege im Pilotstand",
                        "Lehrkräfte",
                        "Kompaktguide",
                        include_cover=False,
                        compact=True,
                    ),
                    args.output_dir / quickstart_name,
                ),
                (
                    DocumentProfile(
                        args.backup_source,
                        "Backup und Wiederherstellung",
                        "Backup und Wiederherstellung",
                        "Backup und Wiederherstellung",
                        "Lokale Daten sichern und kontrolliert wiederherstellen",
                        "Lehrkräfte und schulische technische Betreuung",
                        "Lokaler Produktpfad",
                        include_cover=False,
                        compact=True,
                    ),
                    args.output_dir / backup_name,
                ),
            ]
        )
    if args.extended_guides and not args.manual_only:
        profiles.extend(
            [
                (
                    DocumentProfile(
                        args.security_source,
                        "Sicherheit und Verschlüsselung",
                        "Sicherheit und Verschlüsselung",
                        "Sicherheit",
                        "Schutzstand, Grenzen und Verantwortlichkeiten",
                        "Lehrkräfte, technische Betreuung und Releaseverantwortliche",
                        "Interne Pilot- und Releasevorbereitung, kein öffentlicher Release",
                        include_toc=True,
                    ),
                    args.output_dir
                    / _build_name(
                        args.version,
                        args.build_version,
                        "Sicherheit-und-Verschluesselung",
                    ),
                ),
                (
                    DocumentProfile(
                        args.support_reset_source,
                        "Support-Reset-Betriebsanleitung",
                        "Jenaplan Support-Reset",
                        "Support-Reset",
                        "Kontrollierter Offlineprozess für die technische Betreuung",
                        "Schulische technische Betreuung",
                        "Interne Betriebsanleitung",
                        include_cover=False,
                        compact=True,
                    ),
                    args.output_dir
                    / _build_name(
                        args.version,
                        args.build_version,
                        "Support-Reset-Betriebsanleitung",
                    ),
                ),
                (
                    DocumentProfile(
                        args.release_notes_source,
                        "Release Notes",
                        "Release Notes 0.3.0",
                        "Release Notes",
                        "Produktumfang, Schutzgrenzen und offene Übergabegates",
                        "Lehrkräfte und schulische technische Betreuung",
                        "Vorbereiteter interner Releasekandidat",
                        include_cover=False,
                        compact=True,
                    ),
                    args.output_dir
                    / _build_name(args.version, args.build_version, "Release-Notes"),
                ),
            ]
        )

    for profile, output in profiles:
        build_pdf(
            profile,
            output,
            version=args.version,
            build_version=args.build_version,
            document_date=args.document_date,
            icon=args.icon,
        )
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
