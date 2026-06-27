"""Klassenübersicht screen for UX prototype v0.2."""

from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.worksheet import Worksheet

from ..components import ExcelCanvas
from ..theme import UiTheme


SHEET_TITLE = "Klassenübersicht"
CLASS_NAME = "Klasse 2a"
SCHOOL_YEAR = "2025/26"
MAX_STUDENTS = 28
GRID_COLUMNS = 4
CARD_ROW_HEIGHT = 25
CARD_START_ROW = 8
CARD_ROW_STEP = 3


@dataclass(frozen=True)
class StudentCard:
    """Static prototype data for one student card."""

    student_id: str
    initials: str
    name: str


STUDENTS = (
    StudentCard("student_mia_becker", "MB", "Mia Becker"),
    StudentCard("student_emma_mueller", "EM", "Emma Müller"),
    StudentCard("student_leon_schmidt", "LS", "Leon Schmidt"),
    StudentCard("student_paul_wagner", "PW", "Paul Wagner"),
    StudentCard("student_anna_fischer", "AF", "Anna Fischer"),
    StudentCard("student_ben_schneider", "BS", "Ben Schneider"),
    StudentCard("student_lina_hoffmann", "LH", "Lina Hoffmann"),
    StudentCard("student_noah_weber", "NW", "Noah Weber"),
    StudentCard("student_sophia_koch", "SK", "Sophia Koch"),
    StudentCard("student_finn_bauer", "FB", "Finn Bauer"),
    StudentCard("student_leni_richter", "LR", "Leni Richter"),
    StudentCard("student_jonas_klein", "JK", "Jonas Klein"),
    StudentCard("student_clara_wolf", "CW", "Clara Wolf"),
    StudentCard("student_luis_schroeder", "LS", "Luis Schröder"),
    StudentCard("student_marie_neumann", "MN", "Marie Neumann"),
    StudentCard("student_ole_schwarz", "OS", "Ole Schwarz"),
    StudentCard("student_ella_braun", "EB", "Ella Braun"),
    StudentCard("student_tom_hartmann", "TH", "Tom Hartmann"),
    StudentCard("student_frida_krueger", "FK", "Frida Krüger"),
    StudentCard("student_henri_lang", "HL", "Henri Lang"),
    StudentCard("student_mila_schmitt", "MS", "Mila Schmitt"),
    StudentCard("student_mats_werner", "MW", "Mats Werner"),
    StudentCard("student_lea_scholz", "LS", "Lea Scholz"),
    StudentCard("student_theo_jung", "TJ", "Theo Jung"),
    StudentCard("student_amelie_vogel", "AV", "Amelie Vogel"),
    StudentCard("student_anton_krause", "AK", "Anton Krause"),
    StudentCard("student_ida_mayer", "IM", "Ida Mayer"),
    StudentCard("student_oskar_lehmann", "OL", "Oskar Lehmann"),
)


class ClassOverviewV02WorkbookBuilder:
    """Build the second-generation UX prototype with only the class overview."""

    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.theme = UiTheme()
        self.canvas = ExcelCanvas(self.theme)

    def build(self) -> Path:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = SHEET_TITLE
        self._configure_workbook(workbook)
        self._configure_sheet(worksheet)
        self._render(worksheet)
        self._define_vba_anchor_names(workbook)

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(self.output_path)
        return self.output_path

    def _configure_workbook(self, workbook: Workbook) -> None:
        workbook.properties.title = "Jenaplan UX Prototype v0.2"
        workbook.properties.subject = "Klassenübersicht"
        workbook.properties.creator = "Jenaplan-Kompetenzmanager"
        if workbook.views:
            workbook.views[0].showSheetTabs = False

    def _configure_sheet(self, worksheet: Worksheet) -> None:
        worksheet.sheet_view.showGridLines = False
        worksheet.sheet_view.showRowColHeaders = False
        worksheet.sheet_view.zoomScale = 90
        worksheet.sheet_properties.tabColor = self.theme.primary

        for column, width in self._column_widths().items():
            worksheet.column_dimensions[column].width = width

        for row in range(1, 34):
            worksheet.row_dimensions[row].height = 18
        for row in (1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 33):
            worksheet.row_dimensions[row].height = 8
        for row in (2, 3):
            worksheet.row_dimensions[row].height = 24
        for row in self._card_content_rows():
            worksheet.row_dimensions[row].height = CARD_ROW_HEIGHT

        self.canvas.paint_block(worksheet, 1, 1, 33, 22, self.theme.canvas)

    def _render(self, worksheet: Worksheet) -> None:
        self._render_app_bar(worksheet)
        self._render_header(worksheet)
        self._render_student_cards(worksheet)
        self._render_footer(worksheet)

    def _render_app_bar(self, worksheet: Worksheet) -> None:
        self.canvas.panel(worksheet, 2, 2, 3, 21, self.theme.app_bar, self.theme.app_bar)
        self.canvas.write_range(
            worksheet,
            2,
            3,
            3,
            9,
            "Jenaplan-Kompetenzmanager",
            font=self.canvas.font(14, bold=True, color=self.theme.surface),
            fill=self.theme.app_bar,
            alignment=self.canvas.alignment("left"),
        )
        self.canvas.write_range(
            worksheet,
            2,
            15,
            3,
            20,
            f"{CLASS_NAME}  ·  Schuljahr {SCHOOL_YEAR}",
            font=self.canvas.font(10, bold=True, color="E9F1ED"),
            fill=self.theme.app_bar,
            alignment=self.canvas.alignment("right"),
        )

    def _render_header(self, worksheet: Worksheet) -> None:
        self.canvas.write_range(
            worksheet,
            5,
            2,
            5,
            7,
            "Klassenübersicht",
            font=self.canvas.font(21, bold=True),
            fill=self.theme.canvas,
            alignment=self.canvas.alignment("left"),
        )
        self.canvas.write_range(
            worksheet,
            6,
            2,
            6,
            8,
            f"{len(STUDENTS)} Schüler · Schüler auswählen",
            font=self.canvas.font(10, color=self.theme.muted),
            fill=self.theme.canvas,
            alignment=self.canvas.alignment("left"),
        )

        self.canvas.panel(worksheet, 5, 12, 6, 17, self.theme.surface, self.theme.border)
        self.canvas.write_range(
            worksheet,
            5,
            12,
            6,
            17,
            "Suche: Name eingeben",
            font=self.canvas.font(10, color=self.theme.disabled_text),
            fill=self.theme.surface,
        )

        self.canvas.panel(worksheet, 5, 18, 6, 21, self.theme.disabled_fill, self.theme.border)
        self.canvas.write_range(
            worksheet,
            5,
            18,
            6,
            21,
            "Neue Beobachtung",
            font=self.canvas.font(9, bold=True, color=self.theme.disabled_text),
            fill=self.theme.disabled_fill,
            alignment=self.canvas.alignment("center"),
        )

    def _render_student_cards(self, worksheet: Worksheet) -> None:
        for index, card in enumerate(STUDENTS[:MAX_STUDENTS]):
            self._render_student_card(worksheet, card, self._card_bounds(index), index)

    def _render_student_card(
        self,
        worksheet: Worksheet,
        card: StudentCard,
        bounds: tuple[int, int, int, int],
        index: int,
    ) -> None:
        row_start, col_start, row_end, col_end = bounds
        avatar_fill = self._avatar_fill(index)
        self.canvas.panel(
            worksheet,
            row_start,
            col_start,
            row_end,
            col_end,
            self.theme.surface,
            self.theme.border,
        )
        self.canvas.panel(
            worksheet,
            row_start,
            col_start,
            row_end,
            col_start,
            avatar_fill,
            avatar_fill,
        )
        self.canvas.write_range(
            worksheet,
            row_start,
            col_start,
            row_end,
            col_start,
            card.initials,
            font=self.canvas.font(9, bold=True, color=self.theme.primary),
            fill=avatar_fill,
            alignment=self.canvas.alignment("center"),
        )
        self.canvas.write_range(
            worksheet,
            row_start,
            col_start + 1,
            row_start,
            col_end - 1,
            card.name,
            font=self.canvas.font(11, bold=True),
            fill=self.theme.surface,
        )
        self.canvas.write_range(
            worksheet,
            row_end,
            col_start + 1,
            row_end,
            col_end - 1,
            CLASS_NAME,
            font=self.canvas.font(8, color=self.theme.muted),
            fill=self.theme.surface,
        )
        self.canvas.write_range(
            worksheet,
            row_start,
            col_end,
            row_end,
            col_end,
            ">",
            font=self.canvas.font(10, bold=True, color=self.theme.border_strong),
            fill=self.theme.surface,
            alignment=self.canvas.alignment("center"),
        )

    def _render_footer(self, worksheet: Worksheet) -> None:
        self.canvas.write_range(
            worksheet,
            32,
            2,
            32,
            8,
            "UX Prototype v0.2",
            font=self.canvas.font(8, color=self.theme.muted),
            fill=self.theme.canvas,
        )
        self.canvas.write_range(
            worksheet,
            32,
            15,
            32,
            21,
            "Microsoft Excel für macOS",
            font=self.canvas.font(8, color=self.theme.muted),
            fill=self.theme.canvas,
            alignment=self.canvas.alignment("right"),
        )

    def _define_vba_anchor_names(self, workbook: Workbook) -> None:
        anchors = {
            "ui_class_search": (5, 12, 6, 17),
            "ui_action_new_observation": (5, 18, 6, 21),
        }
        for index, card in enumerate(STUDENTS[:MAX_STUDENTS]):
            anchors[f"ui_{card.student_id}"] = self._card_bounds(index)

        for name, coordinates in anchors.items():
            workbook.defined_names.add(
                DefinedName(name=name, attr_text=self._sheet_range(*coordinates))
            )

    def _card_bounds(self, index: int) -> tuple[int, int, int, int]:
        grid_row = index // GRID_COLUMNS
        grid_column = index % GRID_COLUMNS
        row_start = CARD_START_ROW + grid_row * CARD_ROW_STEP
        col_start = self._card_start_columns()[grid_column]
        return row_start, col_start, row_start + 1, col_start + 3

    def _sheet_range(self, row_start: int, col_start: int, row_end: int, col_end: int) -> str:
        start = self.canvas.absolute_cell(row_start, col_start)
        end = self.canvas.absolute_cell(row_end, col_end)
        return f"'{SHEET_TITLE}'!{start}:{end}"

    def _column_widths(self) -> dict[str, float]:
        widths = {"A": 2.6, "V": 2.6}
        for column in ("F", "K", "P"):
            widths[column] = 2.0
        for column in ("B", "G", "L", "Q"):
            widths[column] = 4.2
        for column in (
            "C",
            "D",
            "E",
            "H",
            "I",
            "J",
            "M",
            "N",
            "O",
            "R",
            "S",
            "T",
        ):
            widths[column] = 8.6
        for column in ("U",):
            widths[column] = 3.0
        return widths

    def _card_start_columns(self) -> tuple[int, int, int, int]:
        return 2, 7, 12, 17

    def _card_content_rows(self) -> tuple[int, ...]:
        rows: list[int] = []
        for grid_row in range(MAX_STUDENTS // GRID_COLUMNS):
            row_start = CARD_START_ROW + grid_row * CARD_ROW_STEP
            rows.extend((row_start, row_start + 1))
        return tuple(rows)

    def _avatar_fill(self, index: int) -> str:
        fills = (
            self.theme.primary_soft,
            self.theme.accent_soft,
            "E3E9F2",
            "E9E4F0",
        )
        return fills[index % len(fills)]
