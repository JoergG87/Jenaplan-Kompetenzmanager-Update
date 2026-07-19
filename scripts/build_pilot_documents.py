"""Build the teacher installation guide and user manual as branded PDFs."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from PIL import Image as PillowImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.frames import Frame


PAGE_WIDTH, PAGE_HEIGHT = A4
INK = colors.HexColor("#203148")
MUTED = colors.HexColor("#66758A")
ACCENT = colors.HexColor("#355A7A")
PALE = colors.HexColor("#F2F6FA")
LINE = colors.HexColor("#DCE5EE")


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
        pilot_commit: str,
        title: str,
        header_on_first_page: bool = False,
    ) -> None:
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=22 * mm,
            rightMargin=22 * mm,
            topMargin=22 * mm,
            bottomMargin=20 * mm,
            title=title,
            author="Jenaplan-Kompetenzmanager",
            subject=f"Pilot-Commit {pilot_commit}",
        )
        self.version = version
        self.pilot_commit = pilot_commit
        self.document_title = title
        self.header_on_first_page = header_on_first_page
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="body",
        )
        self.addPageTemplates(PageTemplate(id="pilot", frames=(frame,), onPage=self._page))

    def _page(self, canvas, doc) -> None:  # type: ignore[no-untyped-def]
        canvas.saveState()
        if doc.page > 1 or self.header_on_first_page:
            canvas.setFont("PilotSans", 8)
            canvas.setFillColor(MUTED)
            canvas.drawString(22 * mm, PAGE_HEIGHT - 12 * mm, self.document_title)
            canvas.setStrokeColor(LINE)
            canvas.line(22 * mm, PAGE_HEIGHT - 15 * mm, PAGE_WIDTH - 22 * mm, PAGE_HEIGHT - 15 * mm)
        canvas.setFont("PilotSans", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            22 * mm,
            11 * mm,
            f"Pilotversion {self.version} · Pilot-Commit {self.pilot_commit}",
        )
        canvas.drawRightString(PAGE_WIDTH - 22 * mm, 11 * mm, f"Seite {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:  # type: ignore[no-untyped-def]
        if isinstance(flowable, Paragraph) and flowable.style.name == "PilotH1":
            text = flowable.getPlainText()
            key = f"heading-{self.seq.nextf('heading')}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=0, closed=False)
            self.notify("TOCEntry", (0, text, self.page, key))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles = {
        "body": ParagraphStyle(
            "PilotBody",
            parent=base["BodyText"],
            fontName="PilotSans",
            fontSize=10,
            leading=15,
            textColor=INK,
            spaceAfter=6,
        ),
        "h1": ParagraphStyle(
            "PilotH1",
            parent=base["Heading1"],
            fontName="PilotSans-Bold",
            fontSize=19,
            leading=24,
            textColor=ACCENT,
            spaceBefore=12,
            spaceAfter=9,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "PilotH2",
            parent=base["Heading2"],
            fontName="PilotSans-Bold",
            fontSize=13,
            leading=17,
            textColor=INK,
            spaceBefore=9,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "PilotH3",
            parent=base["Heading3"],
            fontName="PilotSans-Bold",
            fontSize=11,
            leading=15,
            textColor=INK,
            spaceBefore=7,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "bullet": ParagraphStyle(
            "PilotBullet",
            parent=base["BodyText"],
            fontName="PilotSans",
            fontSize=10,
            leading=14,
            leftIndent=7 * mm,
            firstLineIndent=-4 * mm,
            textColor=INK,
            spaceAfter=3,
        ),
        "caption": ParagraphStyle(
            "PilotCaption",
            parent=base["BodyText"],
            fontName="PilotSans",
            fontSize=8,
            leading=11,
            alignment=TA_CENTER,
            textColor=MUTED,
            spaceAfter=8,
        ),
        "code": ParagraphStyle(
            "PilotCode",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8,
            leading=11,
            leftIndent=5 * mm,
            rightIndent=5 * mm,
            borderColor=LINE,
            borderWidth=0.5,
            borderPadding=5,
            backColor=PALE,
            textColor=INK,
            spaceAfter=7,
        ),
    }
    return styles


def _inline(value: str) -> str:
    value = value.replace("–", "-").replace("—", "-").replace("‑", "-")
    escaped = html.escape(value, quote=False)
    escaped = re.sub(r"`([^`]+)`", r"<font color='#355A7A'>\1</font>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", escaped)
    return escaped


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_inline(" ".join(text.split())), style)


def _markdown_story(
    source_path: Path,
    styles: dict[str, ParagraphStyle],
    *,
    version: str,
) -> list[object]:
    lines = source_path.read_text(encoding="utf-8").replace(
        "{{PILOT_VERSION}}",
        version,
    ).splitlines()
    story: list[object] = []
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []
    index = 0

    def flush() -> None:
        if paragraph:
            story.append(_paragraph(" ".join(paragraph), styles["body"]))
            paragraph.clear()

    while index < len(lines):
        raw = lines[index].rstrip()
        stripped = raw.strip()
        if stripped.startswith("```"):
            flush()
            if in_code:
                story.append(Paragraph("<br/>".join(html.escape(line) for line in code_lines), styles["code"]))
                code_lines.clear()
            in_code = not in_code
            index += 1
            continue
        if in_code:
            code_lines.append(raw)
            index += 1
            continue
        image_match = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", stripped)
        if image_match:
            flush()
            image_path = (source_path.parent / image_match.group(2)).resolve()
            if not image_path.is_file():
                raise FileNotFoundError(f"Handbuchbild fehlt: {image_path}")
            with PillowImage.open(image_path) as source_image:
                width, height = source_image.size
            max_width = 166 * mm
            max_height = 105 * mm
            scale = min(max_width / width, max_height / height)
            story.append(KeepTogether([
                Image(str(image_path), width=width * scale, height=height * scale),
                Paragraph(_inline(image_match.group(1)), styles["caption"]),
            ]))
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
                data = [[Paragraph(_inline(cell), styles["body"]) for cell in row] for row in rows]
                column_width = 166 * mm / max(len(row) for row in rows)
                table = Table(data, colWidths=[column_width] * max(len(row) for row in rows), repeatRows=1)
                table.setStyle(TableStyle((
                    ("BACKGROUND", (0, 0), (-1, 0), PALE),
                    ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                    ("FONTNAME", (0, 0), (-1, 0), "PilotSans-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                )))
                story.extend((table, Spacer(1, 6)))
            continue
        heading = re.match(r"^(#{2,4})\s+(.+)$", stripped)
        if heading:
            flush()
            level = len(heading.group(1))
            story.append(Paragraph(_inline(heading.group(2)), styles[{2: "h1", 3: "h2", 4: "h3"}[level]]))
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
        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        numbered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if bullet or numbered:
            flush()
            marker = "•" if bullet else f"{numbered.group(1)}."
            content = bullet.group(1) if bullet else numbered.group(2)
            story.append(Paragraph(f"{marker}&nbsp;&nbsp;{_inline(content)}", styles["bullet"]))
            index += 1
            continue
        if stripped in ("---", ""):
            flush()
            if stripped == "---":
                story.append(Spacer(1, 4))
            index += 1
            continue
        paragraph.append(stripped)
        index += 1
    flush()
    return story


def _cover(
    title: str,
    subtitle: str,
    version: str,
    pilot_commit: str,
    icon_path: Path,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    return [
        Spacer(1, 24 * mm),
        Image(str(icon_path), width=34 * mm, height=34 * mm, hAlign="CENTER"),
        Spacer(1, 12 * mm),
        Paragraph(_inline(title), ParagraphStyle("CoverTitle", parent=styles["h1"], fontSize=25, leading=31, alignment=TA_CENTER, spaceAfter=10)),
        Paragraph(_inline(subtitle), ParagraphStyle("CoverSubtitle", parent=styles["body"], fontSize=14, leading=20, alignment=TA_CENTER, textColor=MUTED)),
        Spacer(1, 22 * mm),
        Table(
            [[Paragraph(
                f"<b>Pilotversion {html.escape(version)}</b><br/>"
                f"Pilot-Commit {html.escape(pilot_commit)}<br/>"
                "Apple Silicon - macOS 13 oder neuer",
                styles["body"],
            )]],
            colWidths=[110 * mm],
            hAlign="CENTER",
            style=TableStyle((("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.8, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10))),
        ),
        PageBreak(),
    ]


def build_pdf(
    source: Path,
    output: Path,
    *,
    title: str,
    subtitle: str,
    version: str,
    pilot_commit: str,
    icon: Path,
    include_toc: bool,
    include_cover: bool = True,
    header_on_first_page: bool = False,
) -> None:
    styles = _styles()
    story = (
        _cover(title, subtitle, version, pilot_commit, icon, styles)
        if include_cover
        else []
    )
    if include_toc:
        toc_heading = ParagraphStyle("TOCHeading", parent=styles["h1"])
        story.append(Paragraph("Inhaltsverzeichnis", toc_heading))
        toc = TableOfContents()
        toc.levelStyles = (
            ParagraphStyle("TOC1", fontName="PilotSans", fontSize=10, leading=15, leftIndent=0, firstLineIndent=0, textColor=INK),
        )
        story.extend((toc, PageBreak()))
    story.extend(_markdown_story(source, styles, version=version))
    output.parent.mkdir(parents=True, exist_ok=True)
    PilotDocTemplate(
        str(output),
        version=version,
        pilot_commit=pilot_commit,
        title=title,
        header_on_first_page=header_on_first_page,
    ).multiBuild(story)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--pilot-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--installation-source", type=Path, required=True)
    parser.add_argument("--manual-source", type=Path, required=True)
    parser.add_argument("--first-steps-source", type=Path, required=True)
    parser.add_argument("--quickstart-source", type=Path, required=True)
    parser.add_argument("--backup-source", type=Path, required=True)
    parser.add_argument("--icon", type=Path, default=Path("assets/app_icon.png"))
    args = parser.parse_args()
    _register_fonts()
    installation_output = args.output_dir / f"Jenaplan-Kompetenzmanager-Pilot-{args.version}-Installationsanleitung.pdf"
    manual_output = args.output_dir / f"Jenaplan-Kompetenzmanager-Pilot-{args.version}-Benutzerhandbuch.pdf"
    first_steps_output = args.output_dir / f"Jenaplan-Kompetenzmanager-Pilot-{args.version}-Erste-Schritte.pdf"
    quickstart_output = args.output_dir / f"Jenaplan-Kompetenzmanager-Pilot-{args.version}-Schnellstart-Lehrkraefte.pdf"
    backup_output = args.output_dir / f"Jenaplan-Kompetenzmanager-Pilot-{args.version}-Backup-Anleitung.pdf"
    build_pdf(
        args.installation_source,
        installation_output,
        title="Installation des Jenaplan-Kompetenzmanagers - Pilotversion",
        subtitle="Schritt für Schritt zum ersten Start",
        version=args.version,
        pilot_commit=args.pilot_commit,
        icon=args.icon,
        include_toc=False,
    )
    build_pdf(
        args.manual_source,
        manual_output,
        title="Jenaplan-Kompetenzmanager - Benutzerhandbuch",
        subtitle="Sicher orientieren, dokumentieren und Berichte vorbereiten",
        version=args.version,
        pilot_commit=args.pilot_commit,
        icon=args.icon,
        include_toc=True,
    )
    build_pdf(
        args.first_steps_source,
        first_steps_output,
        title="Erste Schritte - Jenaplan-Kompetenzmanager",
        subtitle="Ein ruhiger Einstieg in den Pilottest",
        version=args.version,
        pilot_commit=args.pilot_commit,
        icon=args.icon,
        include_toc=False,
        include_cover=False,
        header_on_first_page=True,
    )
    build_pdf(
        args.quickstart_source,
        quickstart_output,
        title="Schnellstart für Lehrkräfte",
        subtitle="Die wichtigsten Wege im Pilottest",
        version=args.version,
        pilot_commit=args.pilot_commit,
        icon=args.icon,
        include_toc=False,
        include_cover=False,
        header_on_first_page=True,
    )
    build_pdf(
        args.backup_source,
        backup_output,
        title="Backup für den Pilottest",
        subtitle="Lokale Pilotdaten sicher sichern",
        version=args.version,
        pilot_commit=args.pilot_commit,
        icon=args.icon,
        include_toc=False,
    )
    print(installation_output)
    print(manual_output)
    print(first_steps_output)
    print(quickstart_output)
    print(backup_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
