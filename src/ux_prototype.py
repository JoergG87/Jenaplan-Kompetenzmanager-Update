"""UX prototype workbook screens for the Jenaplan Kompetenzmanager."""

from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .ui.screens.klassenuebersicht import ClassOverviewV02WorkbookBuilder


@dataclass(frozen=True)
class Theme:
    """Shared visual theme for the prototype workbook."""

    app_name: str = "Jenaplan UX Prototype v0.1"
    prototype_label: str = "Jenaplan-Kompetenzmanager"
    font_name: str = "Aptos"

    canvas: str = "F5F8FC"
    surface: str = "FFFFFF"
    surface_soft: str = "EEF4FA"
    border: str = "D9E2EC"
    border_strong: str = "B8C6D6"
    primary: str = "173B5B"
    primary_soft: str = "DCEAF6"
    accent: str = "2B6C8E"
    accent_soft: str = "E7F1F7"
    text: str = "1F2937"
    muted: str = "637381"
    success: str = "DFF1E5"
    success_text: str = "1F6B46"
    info: str = "E5F0FB"
    info_text: str = "245A7A"
    warning: str = "F6E8C8"
    warning_text: str = "7A5C1E"
    danger: str = "F8E2E0"
    danger_text: str = "8A3A36"
    neutral: str = "EEF2F5"
    neutral_text: str = "39424E"


SHEET_OVERVIEW = "Klassenübersicht"
SHEET_PROFILE = "Schülerprofil"
SHEET_OBSERVATION = "Neue Beobachtung"
SHEET_COMPETENCE = "Kompetenzansicht"

NAV_TARGETS = (
    (SHEET_OVERVIEW, "Klassenübersicht"),
    (SHEET_PROFILE, "Schülerprofil"),
    (SHEET_OBSERVATION, "Neue Beobachtung"),
    (SHEET_COMPETENCE, "Kompetenzansicht"),
)

CLASS_NAME = "Klasse 2a"
SCHOOL_YEAR = "2025/26"

STUDENTS = (
    "Mia Becker",
    "Emma Müller",
    "Leon Schmidt",
    "Paul Wagner",
)

PROFILE_COMPETENCIES = (
    {
        "area": "Lesen",
        "name": "Informationen aus Texten entnehmen",
        "status": "auf Kurs",
        "observations": "5 Beobachtungen",
        "last_observation": "12.06.2026",
    },
    {
        "area": "Schreiben",
        "name": "Rechtschreibung anwenden",
        "status": "in Entwicklung",
        "observations": "3 Beobachtungen",
        "last_observation": "08.06.2026",
    },
    {
        "area": "Sprechen",
        "name": "Beiträge strukturiert formulieren",
        "status": "sicher",
        "observations": "4 Beobachtungen",
        "last_observation": "11.06.2026",
    },
)

OBSERVATION_COMPETENCIES = (
    "Lesen - Informationen aus Texten entnehmen",
    "Schreiben - Rechtschreibung anwenden",
    "Sprechen - Beiträge strukturiert formulieren",
)

COMPETENCE_NAME = "Lesen - Informationen aus Texten entnehmen"
COMPETENCE_STATUS = "auf Kurs"
COMPETENCE_OBSERVATIONS = "5"
COMPETENCE_LAST_DATE = "12.06.2026"
COMPETENCE_TIMELINE = (
    ("12.06.2026", "Präsentation in Partnerarbeit", "++"),
    ("05.06.2026", "Lernzielkontrolle", "+"),
    ("28.05.2026", "Unterrichtsbeobachtung", "+"),
)


class PrototypeSheet:
    """Common rendering helpers for the prototype workbook."""

    title: str = ""
    subtitle: str = ""

    def __init__(self, theme: Theme) -> None:
        self.theme = theme

    def create(self, workbook: Workbook) -> None:
        worksheet = workbook.create_sheet(self.title)
        self._configure_sheet(worksheet)
        self._render(worksheet)

    def _configure_sheet(self, worksheet: Worksheet) -> None:
        worksheet.sheet_view.showGridLines = False
        worksheet.sheet_view.zoomScale = 90
        worksheet.freeze_panes = "B5"

        for column, width in {
            "A": 3,
            "B": 16,
            "C": 16,
            "D": 16,
            "E": 4,
            "F": 16,
            "G": 16,
            "H": 16,
            "I": 16,
            "J": 16,
            "K": 16,
            "L": 3,
        }.items():
            worksheet.column_dimensions[column].width = width

        for row, height in {
            1: 28,
            2: 22,
            3: 24,
            4: 10,
            5: 24,
            6: 24,
            7: 24,
            8: 24,
            9: 24,
            10: 24,
            11: 24,
            12: 24,
            13: 24,
            14: 24,
            15: 24,
            16: 24,
            17: 24,
            18: 24,
            19: 24,
            20: 24,
            21: 24,
            22: 24,
            23: 24,
            24: 24,
            25: 24,
            26: 24,
            27: 24,
            28: 24,
            29: 24,
            30: 24,
            31: 24,
            32: 24,
        }.items():
            worksheet.row_dimensions[row].height = height

        self._paint_area(worksheet, 1, 1, 32, 12, self.theme.canvas)
        self._paint_area(worksheet, 1, 2, 1, 11, self.theme.primary)
        self._paint_area(worksheet, 2, 2, 2, 11, self.theme.surface)
        self._paint_area(worksheet, 3, 2, 3, 11, self.theme.surface_soft)

        self._write_cell(
            worksheet,
            1,
            2,
            self.theme.app_name,
            font=self._font(14, bold=True, color=self.theme.surface),
            fill=self.theme.primary,
        )
        self._write_cell(
            worksheet,
            1,
            10,
            self.theme.prototype_label,
            font=self._font(10, bold=True, color=self.theme.surface),
            fill=self.theme.primary,
            alignment=self._alignment("right"),
        )
        self._write_cell(
            worksheet,
            2,
            2,
            self.title,
            font=self._font(17, bold=True, color=self.theme.text),
            fill=self.theme.surface,
        )
        self._write_cell(
            worksheet,
            2,
            10,
            self.subtitle,
            font=self._font(10, color=self.theme.muted),
            fill=self.theme.surface,
            alignment=self._alignment("right"),
        )

        self._render_nav(worksheet)

    def _render_nav(self, worksheet: Worksheet) -> None:
        nav_cells = {
            SHEET_OVERVIEW: (3, 2, 3, 3),
            SHEET_PROFILE: (3, 4, 3, 5),
            SHEET_OBSERVATION: (3, 6, 3, 7),
            SHEET_COMPETENCE: (3, 8, 3, 9),
        }

        for sheet_name, label in NAV_TARGETS:
            row1, col1, row2, col2 = nav_cells[sheet_name]
            active = sheet_name == self.title
            fill = self.theme.primary if active else self.theme.surface
            text_color = self.theme.surface if active else self.theme.text
            border_color = self.theme.primary if active else self.theme.border_strong
            self._paint_area(worksheet, row1, col1, row2, col2, fill, border_color)
            self._write_cell(
                worksheet,
                row1,
                col1,
                label,
                font=self._font(10, bold=True, color=text_color),
                fill=fill,
                alignment=self._alignment("center"),
                hyperlink=None if active else self._sheet_link(sheet_name),
            )

    def _render(self, worksheet: Worksheet) -> None:
        raise NotImplementedError

    def _paint_area(
        self,
        worksheet: Worksheet,
        row_start: int,
        col_start: int,
        row_end: int,
        col_end: int,
        fill_color: str,
        border_color: str | None = None,
    ) -> None:
        border = self._border(border_color or self.theme.border)
        fill = self._fill(fill_color)
        for row in range(row_start, row_end + 1):
            for column in range(col_start, col_end + 1):
                cell = worksheet.cell(row=row, column=column)
                cell.fill = fill
                cell.border = border

    def _write_cell(
        self,
        worksheet: Worksheet,
        row: int,
        column: int,
        value: str,
        *,
        font: Font,
        fill: PatternFill | str | None = None,
        alignment: Alignment | None = None,
        hyperlink: str | None = None,
    ) -> None:
        cell = worksheet.cell(row=row, column=column, value=value)
        cell.font = font
        if fill is not None:
            cell.fill = fill if isinstance(fill, PatternFill) else self._fill(fill)
        cell.alignment = alignment or self._alignment("left")
        if hyperlink is not None:
            cell.hyperlink = hyperlink

    def _font(
        self,
        size: int,
        *,
        bold: bool = False,
        color: str | None = None,
        italic: bool = False,
        underline: str | None = None,
    ) -> Font:
        return Font(
            name=self.theme.font_name,
            size=size,
            bold=bold,
            italic=italic,
            underline=underline,
            color=color or self.theme.text,
        )

    def _fill(self, color: str) -> PatternFill:
        return PatternFill("solid", fgColor=color)

    def _border(self, color: str) -> Border:
        side = Side(style="thin", color=color)
        return Border(left=side, right=side, top=side, bottom=side)

    def _alignment(self, horizontal: str = "left") -> Alignment:
        return Alignment(horizontal=horizontal, vertical="center", wrap_text=True)

    def _sheet_link(self, sheet_name: str, anchor: str = "A1") -> str:
        return f"#'{sheet_name}'!{anchor}"

    def _button(
        self,
        worksheet: Worksheet,
        row_start: int,
        col_start: int,
        row_end: int,
        col_end: int,
        label: str,
        *,
        fill_color: str,
        text_color: str,
        link: str | None = None,
        border_color: str | None = None,
        font_size: int = 11,
    ) -> None:
        self._paint_area(worksheet, row_start, col_start, row_end, col_end, fill_color, border_color)
        text_row = row_start + (row_end - row_start) // 2
        text_col = col_start + max(0, (col_end - col_start + 1) // 2)
        self._write_cell(
            worksheet,
            text_row,
            text_col,
            label,
            font=self._font(font_size, bold=True, color=text_color),
            fill=self._fill(fill_color),
            alignment=self._alignment("center"),
            hyperlink=link,
        )

    def _panel_title(self, worksheet: Worksheet, row: int, col: int, title: str) -> None:
        self._write_cell(
            worksheet,
            row,
            col,
            title,
            font=self._font(11, bold=True, color=self.theme.text),
            fill=self._fill(self.theme.surface),
        )
        self._paint_area(worksheet, row, col, row, col + 2, self.theme.surface)

    def _card_label(self, worksheet: Worksheet, row: int, col: int, label: str) -> None:
        self._write_cell(
            worksheet,
            row,
            col,
            label,
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )

    def _card_value(self, worksheet: Worksheet, row: int, col: int, value: str, *, color: str | None = None) -> None:
        self._write_cell(
            worksheet,
            row,
            col,
            value,
            font=self._font(12, bold=True, color=color or self.theme.text),
            fill=self._fill(self.theme.surface),
        )

    def _card_text(self, worksheet: Worksheet, row: int, col: int, value: str, *, color: str | None = None) -> None:
        self._write_cell(
            worksheet,
            row,
            col,
            value,
            font=self._font(10, color=color or self.theme.muted),
            fill=self._fill(self.theme.surface),
        )


class KlassenuebersichtSheet(PrototypeSheet):
    title = SHEET_OVERVIEW
    subtitle = "Schüler auswählen"

    def _render(self, worksheet: Worksheet) -> None:
        self._paint_area(worksheet, 5, 2, 11, 6, self.theme.surface, self.theme.border)
        self._write_cell(
            worksheet,
            5,
            2,
            "Klassenname",
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            6,
            2,
            CLASS_NAME,
            font=self._font(16, bold=True, color=self.theme.text),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            8,
            2,
            "Schuljahr",
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            9,
            2,
            SCHOOL_YEAR,
            font=self._font(12, bold=True, color=self.theme.primary),
            fill=self._fill(self.theme.surface),
        )

        self._paint_area(worksheet, 5, 8, 11, 11, self.theme.surface, self.theme.border)
        self._write_cell(
            worksheet,
            5,
            8,
            "Suchfeld",
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            6,
            8,
            "Mia, Emma, Leon, Paul",
            font=self._font(11, color=self.theme.muted),
            fill=self._fill(self.theme.surface_soft),
        )
        self._write_cell(
            worksheet,
            8,
            8,
            "Alphabetische Schülerliste",
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            9,
            8,
            "Ein Klick führt direkt ins Schülerprofil.",
            font=self._font(10, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )

        self._paint_area(worksheet, 13, 2, 22, 11, self.theme.canvas, self.theme.canvas)
        student_rows = (13, 15, 17, 19)
        for row, student in zip(student_rows, STUDENTS, strict=True):
            self._button(
                worksheet,
                row,
                2,
                row + 1,
                11,
                student,
                fill_color=self.theme.surface,
                text_color=self.theme.text,
                link=self._sheet_link(SHEET_PROFILE),
                border_color=self.theme.border_strong,
            )
            self._write_cell(
                worksheet,
                row,
                10,
                "Schülerprofil öffnen",
                font=self._font(9, bold=True, color=self.theme.accent),
                fill=self._fill(self.theme.surface),
                alignment=self._alignment("right"),
                hyperlink=self._sheet_link(SHEET_PROFILE),
            )


class SchuelerprofilSheet(PrototypeSheet):
    title = SHEET_PROFILE
    subtitle = "Arbeitsplatz der Lehrkraft"

    def _render(self, worksheet: Worksheet) -> None:
        self._paint_area(worksheet, 5, 2, 7, 11, self.theme.surface, self.theme.border_strong)
        self._write_cell(
            worksheet,
            5,
            2,
            "Schülername",
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            6,
            2,
            "Emma Müller",
            font=self._font(17, bold=True, color=self.theme.text),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            5,
            7,
            "Klasse",
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            6,
            7,
            CLASS_NAME,
            font=self._font(12, bold=True, color=self.theme.primary),
            fill=self._fill(self.theme.surface),
        )

        self._button(
            worksheet,
            5,
            9,
            7,
            11,
            "Neue Beobachtung",
            fill_color=self.theme.primary,
            text_color=self.theme.surface,
            link=self._sheet_link(SHEET_OBSERVATION),
            border_color=self.theme.primary,
            font_size=12,
        )

        self._paint_area(worksheet, 9, 2, 24, 5, self.theme.surface, self.theme.border)
        self._write_cell(
            worksheet,
            9,
            2,
            "Lehrplanstruktur",
            font=self._font(11, bold=True, color=self.theme.text),
            fill=self._fill(self.theme.surface),
        )
        left_tree = (
            ("Fach", "Deutsch"),
            ("Kompetenzbereich", "Lesen"),
            ("Kompetenzgruppe", "Informationen entnehmen"),
            ("Kompetenz", "Texte sicher verstehen"),
        )
        row = 11
        for label, value in left_tree:
            self._write_cell(
                worksheet,
                row,
                2,
                label,
                font=self._font(9, bold=True, color=self.theme.muted),
                fill=self._fill(self.theme.surface),
            )
            self._write_cell(
                worksheet,
                row + 1,
                2,
                value,
                font=self._font(11, color=self.theme.text),
                fill=self._fill(self.theme.surface_soft),
            )
            row += 3

        self._paint_area(worksheet, 9, 7, 24, 11, self.theme.surface, self.theme.border)
        self._write_cell(
            worksheet,
            9,
            7,
            "Kompetenzbereich",
            font=self._font(11, bold=True, color=self.theme.text),
            fill=self._fill(self.theme.surface),
        )

        card_rows = (11, 16, 21)
        for row, competency in zip(card_rows, PROFILE_COMPETENCIES, strict=True):
            status_fill = {
                "sicher": (self.theme.success, self.theme.success_text),
                "auf Kurs": (self.theme.info, self.theme.info_text),
                "in Entwicklung": (self.theme.warning, self.theme.warning_text),
            }.get(competency["status"], (self.theme.neutral, self.theme.neutral_text))
            self._paint_area(worksheet, row, 7, row + 3, 11, self.theme.surface, self.theme.border_strong)
            self._write_cell(
                worksheet,
                row,
                7,
                competency["area"],
                font=self._font(9, bold=True, color=self.theme.muted),
                fill=self._fill(self.theme.surface),
            )
            self._write_cell(
                worksheet,
                row + 1,
                7,
                competency["name"],
                font=self._font(11, bold=True, color=self.theme.text),
                fill=self._fill(self.theme.surface),
            )
            self._write_cell(
                worksheet,
                row + 1,
                10,
                competency["status"],
                font=self._font(9, bold=True, color=status_fill[1]),
                fill=self._fill(status_fill[0]),
                alignment=self._alignment("center"),
            )
            self._write_cell(
                worksheet,
                row + 2,
                7,
                competency["observations"],
                font=self._font(10, color=self.theme.muted),
                fill=self._fill(self.theme.surface),
            )
            self._write_cell(
                worksheet,
                row + 2,
                10,
                competency["last_observation"],
                font=self._font(10, color=self.theme.muted),
                fill=self._fill(self.theme.surface),
                alignment=self._alignment("right"),
            )
            self._write_cell(
                worksheet,
                row + 3,
                10,
                "Kompetenzansicht öffnen",
                font=self._font(9, bold=True, color=self.theme.accent),
                fill=self._fill(self.theme.surface),
                alignment=self._alignment("right"),
                hyperlink=self._sheet_link(SHEET_COMPETENCE),
            )


class NeueBeobachtungSheet(PrototypeSheet):
    title = SHEET_OBSERVATION
    subtitle = "Schnell erfassen, ruhig entscheiden"

    def _render(self, worksheet: Worksheet) -> None:
        self._paint_area(worksheet, 5, 3, 26, 10, self.theme.surface, self.theme.border_strong)
        self._write_cell(
            worksheet,
            5,
            3,
            "Schülerprofil: Emma Müller",
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            6,
            3,
            "Klasse 2a",
            font=self._font(12, bold=True, color=self.theme.primary),
            fill=self._fill(self.theme.surface),
        )

        self._write_cell(
            worksheet,
            8,
            3,
            "Notiz",
            font=self._font(11, bold=True, color=self.theme.text),
            fill=self._fill(self.theme.surface),
        )
        self._paint_area(worksheet, 9, 3, 12, 10, self.theme.surface_soft, self.theme.border_strong)
        self._write_cell(
            worksheet,
            10,
            4,
            "Beobachtung knapp festhalten. Zum Beispiel: Emma erklärt im Gruppenauftrag ihre Lösung.",
            font=self._font(10, color=self.theme.muted),
            fill=self._fill(self.theme.surface_soft),
        )

        self._write_cell(
            worksheet,
            14,
            3,
            "Kompetenz auswählen",
            font=self._font(11, bold=True, color=self.theme.text),
            fill=self._fill(self.theme.surface),
        )
        competence_rows = (15, 16, 17)
        for row, label in zip(competence_rows, OBSERVATION_COMPETENCIES, strict=True):
            self._button(
                worksheet,
                row,
                3,
                row,
                10,
                label,
                fill_color=self.theme.surface,
                text_color=self.theme.text,
                link=self._sheet_link(SHEET_COMPETENCE),
                border_color=self.theme.border_strong,
                font_size=10,
            )

        self._write_cell(
            worksheet,
            19,
            3,
            "Bewertung",
            font=self._font(11, bold=True, color=self.theme.text),
            fill=self._fill(self.theme.surface),
        )
        rating_blocks = (
            (20, 3, 21, 4, "++", self.theme.success, self.theme.success_text),
            (20, 5, 21, 6, "+", self.theme.info, self.theme.info_text),
            (20, 7, 21, 8, "-", self.theme.warning, self.theme.warning_text),
            (20, 9, 21, 10, "–", self.theme.danger, self.theme.danger_text),
        )
        for row1, col1, row2, col2, label, fill, text_color in rating_blocks:
            self._button(
                worksheet,
                row1,
                col1,
                row2,
                col2,
                label,
                fill_color=fill,
                text_color=text_color,
                border_color=self.theme.border_strong,
                font_size=12,
            )

        self._button(
            worksheet,
            23,
            7,
            24,
            10,
            "Speichern",
            fill_color=self.theme.primary,
            text_color=self.theme.surface,
            link=self._sheet_link(SHEET_PROFILE),
            border_color=self.theme.primary,
            font_size=12,
        )


class KompetenzansichtSheet(PrototypeSheet):
    title = SHEET_COMPETENCE
    subtitle = "Entwicklung einer Kompetenz nachvollziehen"

    def _render(self, worksheet: Worksheet) -> None:
        self._paint_area(worksheet, 5, 2, 7, 11, self.theme.surface, self.theme.border_strong)
        self._write_cell(
            worksheet,
            5,
            2,
            "Kompetenzname",
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            6,
            2,
            COMPETENCE_NAME,
            font=self._font(15, bold=True, color=self.theme.text),
            fill=self._fill(self.theme.surface),
        )

        kpi_blocks = (
            (9, 2, 12, 4, "Kompetenzstand", COMPETENCE_STATUS, self.theme.info, self.theme.info_text),
            (9, 5, 12, 7, "Anzahl Beobachtungen", COMPETENCE_OBSERVATIONS, self.theme.surface, self.theme.primary),
            (9, 8, 12, 10, "Datum der letzten Beobachtung", COMPETENCE_LAST_DATE, self.theme.surface, self.theme.text),
        )
        for row1, col1, row2, col2, label, value, fill, value_color in kpi_blocks:
            self._paint_area(worksheet, row1, col1, row2, col2, fill, self.theme.border_strong)
            self._write_cell(
                worksheet,
                row1,
                col1,
                label,
                font=self._font(9, bold=True, color=self.theme.muted),
                fill=self._fill(fill),
            )
            self._write_cell(
                worksheet,
                row1 + 1,
                col1,
                value,
                font=self._font(13, bold=True, color=value_color),
                fill=self._fill(fill),
            )

        self._button(
            worksheet,
            14,
            2,
            15,
            4,
            "Verlauf",
            fill_color=self.theme.primary,
            text_color=self.theme.surface,
            link=self._sheet_link(SHEET_COMPETENCE, "B20"),
            border_color=self.theme.primary,
            font_size=12,
        )

        self._paint_area(worksheet, 19, 2, 29, 11, self.theme.surface, self.theme.border)
        self._write_cell(
            worksheet,
            19,
            2,
            "Verlauf",
            font=self._font(11, bold=True, color=self.theme.text),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            20,
            2,
            "Datum",
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            20,
            4,
            "Situation",
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )
        self._write_cell(
            worksheet,
            20,
            9,
            "Bewertung",
            font=self._font(9, bold=True, color=self.theme.muted),
            fill=self._fill(self.theme.surface),
        )
        row = 21
        for date_value, situation, rating in COMPETENCE_TIMELINE:
            self._write_cell(
                worksheet,
                row,
                2,
                date_value,
                font=self._font(10, color=self.theme.text),
                fill=self._fill(self.theme.surface),
            )
            self._write_cell(
                worksheet,
                row,
                4,
                situation,
                font=self._font(10, color=self.theme.text),
                fill=self._fill(self.theme.surface),
            )
            self._button(
                worksheet,
                row,
                9,
                row,
                10,
                rating,
                fill_color=self.theme.neutral,
                text_color=self.theme.neutral_text,
                border_color=self.theme.border_strong,
                font_size=10,
            )
            row += 2


class UXPrototypeWorkbookBuilder:
    """Build the first clickable UX prototype workbook."""

    def __init__(self, output_path: Path, prototype_version: str = "v0.2") -> None:
        self.output_path = output_path
        self.prototype_version = prototype_version
        self.theme = Theme(app_name=f"Jenaplan UX Prototype {prototype_version}")

    def build(self) -> Path:
        if self.prototype_version == "v0.2":
            return ClassOverviewV02WorkbookBuilder(self.output_path).build()

        workbook = Workbook()
        workbook.remove(workbook.active)

        for sheet in (
            KlassenuebersichtSheet(self.theme),
            SchuelerprofilSheet(self.theme),
            NeueBeobachtungSheet(self.theme),
            KompetenzansichtSheet(self.theme),
        ):
            sheet.create(workbook)

        workbook.active = 0
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(self.output_path)
        return self.output_path
