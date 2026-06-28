"""Schülerprofil screen for product version v0.4."""

from openpyxl.workbook import Workbook
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.worksheet import Worksheet

from ...core.workbook_data import TABLE_COURSES, TABLE_GROUPS, TABLE_STUDENTS, WorkbookData
from ..components import ExcelCanvas
from ..theme import UiTheme


SHEET_TITLE = "Schülerprofil"
PRODUCT_VERSION = "v0.4"
CLASS_OVERVIEW_SHEET = "Stammgruppenübersicht"
SELECTED_STUDENT_ID_CELL = "X2"
SELECTED_STUDENT_ID_REFERENCE = "$X$2"
PROFILE_FIRST_NAME_CELL = "Y2"
PROFILE_LAST_NAME_CELL = "Z2"
PROFILE_DISPLAY_NAME_CELL = "AA2"
PROFILE_GROUP_ID_CELL = "AB2"
PROFILE_COURSE_ID_CELL = "AC2"
PROFILE_GROUP_NAME_CELL = "AD2"
PROFILE_COURSE_NAME_CELL = "AE2"
PROFILE_INITIALS_CELL = "AF2"


class SchuelerprofilScreenBuilder:
    """Render the student profile as the second v0.2 UX screen."""

    def __init__(self, theme: UiTheme, data: WorkbookData) -> None:
        self.theme = theme
        self.data = data
        self.canvas = ExcelCanvas(theme)

    def create(self, workbook: Workbook) -> Worksheet:
        worksheet = workbook.create_sheet(SHEET_TITLE)
        self._configure_sheet(worksheet)
        self._render(worksheet)
        self._define_names(workbook)
        return worksheet

    def _configure_sheet(self, worksheet: Worksheet) -> None:
        worksheet.sheet_view.showGridLines = False
        worksheet.sheet_view.showRowColHeaders = False
        worksheet.sheet_view.zoomScale = 90
        worksheet.sheet_properties.tabColor = self.theme.primary

        for column, width in self._column_widths().items():
            worksheet.column_dimensions[column].width = width
        for column in ("X", "Y", "Z", "AA", "AB", "AC", "AD", "AE", "AF"):
            worksheet.column_dimensions[column].hidden = True

        for row in range(1, 34):
            worksheet.row_dimensions[row].height = 20
        for row in (1, 4, 8, 13, 19, 25, 33):
            worksheet.row_dimensions[row].height = 8
        for row in (2, 3):
            worksheet.row_dimensions[row].height = 24
        for row in (6, 7):
            worksheet.row_dimensions[row].height = 28
        for row in (10, 16, 22):
            worksheet.row_dimensions[row].height = 26

        self.canvas.paint_block(worksheet, 1, 1, 33, 22, self.theme.canvas)

    def _render(self, worksheet: Worksheet) -> None:
        self._render_profile_projection(worksheet)
        self._render_app_bar(worksheet)
        self._render_header(worksheet)
        self._render_primary_action(worksheet)
        self._render_observations(worksheet)
        self._render_side_panel(worksheet)
        self._render_footer(worksheet)

    def _render_profile_projection(self, worksheet: Worksheet) -> None:
        worksheet[SELECTED_STUDENT_ID_CELL] = self.data.default_student_id
        worksheet[PROFILE_FIRST_NAME_CELL] = self._student_lookup_formula("first_name")
        worksheet[PROFILE_LAST_NAME_CELL] = self._student_lookup_formula("last_name")
        worksheet[PROFILE_DISPLAY_NAME_CELL] = (
            f'=IF({SELECTED_STUDENT_ID_REFERENCE}="","",{PROFILE_FIRST_NAME_CELL}&" "&{PROFILE_LAST_NAME_CELL})'
        )
        worksheet[PROFILE_GROUP_ID_CELL] = self._student_lookup_formula("group_id")
        worksheet[PROFILE_COURSE_ID_CELL] = self._student_lookup_formula("course_id")
        worksheet[PROFILE_GROUP_NAME_CELL] = (
            f'=IFERROR("Stammgruppe "&INDEX({TABLE_GROUPS}[group_name],'
            f'MATCH({PROFILE_GROUP_ID_CELL},{TABLE_GROUPS}[group_id],0)),"")'
        )
        worksheet[PROFILE_COURSE_NAME_CELL] = (
            f'=IFERROR(INDEX({TABLE_COURSES}[course_name],'
            f'MATCH({PROFILE_COURSE_ID_CELL},{TABLE_COURSES}[course_id],0)),"")'
        )
        worksheet[PROFILE_INITIALS_CELL] = (
            f'=IF({SELECTED_STUDENT_ID_REFERENCE}="","",'
            f'LEFT({PROFILE_FIRST_NAME_CELL},1)&LEFT({PROFILE_LAST_NAME_CELL},1))'
        )

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
            f'={PROFILE_GROUP_NAME_CELL}&"  ·  Schülerprofil"',
            font=self.canvas.font(10, bold=True, color="E9F1ED"),
            fill=self.theme.app_bar,
            alignment=self.canvas.alignment("right"),
        )

    def _render_header(self, worksheet: Worksheet) -> None:
        self.canvas.panel(worksheet, 5, 2, 7, 14, self.theme.surface, self.theme.border)
        self.canvas.panel(worksheet, 5, 2, 7, 3, self.theme.primary_soft, self.theme.primary_soft)
        self.canvas.write_range(
            worksheet,
            5,
            2,
            7,
            3,
            f"={PROFILE_INITIALS_CELL}",
            font=self.canvas.font(14, bold=True, color=self.theme.primary),
            fill=self.theme.primary_soft,
            alignment=self.canvas.alignment("center"),
        )
        self.canvas.write_range(
            worksheet,
            5,
            4,
            5,
            11,
            f"={PROFILE_DISPLAY_NAME_CELL}",
            font=self.canvas.font(21, bold=True),
            fill=self.theme.surface,
        )
        self.canvas.write_range(
            worksheet,
            6,
            4,
            7,
            11,
            (
                f'=IF({SELECTED_STUDENT_ID_REFERENCE}="","",'
                f'{PROFILE_GROUP_NAME_CELL}&" · "&{PROFILE_COURSE_NAME_CELL}'
                f'&" · student_id "&{SELECTED_STUDENT_ID_REFERENCE})'
            ),
            font=self.canvas.font(9, color=self.theme.muted),
            fill=self.theme.surface,
        )
        self.canvas.panel(worksheet, 5, 16, 7, 21, self.theme.surface, self.theme.border)
        self.canvas.write_range(
            worksheet,
            5,
            16,
            7,
            21,
            "< Zurück zur Stammgruppenübersicht",
            font=self.canvas.font(10, bold=True, color=self.theme.primary),
            fill=self.theme.surface,
            alignment=self.canvas.alignment("center"),
        )
        self.canvas.link_range(
            worksheet,
            5,
            16,
            7,
            21,
            f"#'{CLASS_OVERVIEW_SHEET}'!A1",
        )

    def _render_primary_action(self, worksheet: Worksheet) -> None:
        self.canvas.panel(worksheet, 9, 2, 11, 8, self.theme.primary, self.theme.primary)
        self.canvas.write_range(
            worksheet,
            9,
            2,
            11,
            8,
            "+ Neue Beobachtung",
            font=self.canvas.font(12, bold=True, color=self.theme.surface),
            fill=self.theme.primary,
            alignment=self.canvas.alignment("center"),
        )
        self.canvas.write_range(
            worksheet,
            9,
            10,
            11,
            14,
            "Platzhalter für den zentralen Beobachtungsdialog",
            font=self.canvas.font(9, color=self.theme.muted),
            fill=self.theme.canvas,
        )

    def _render_observations(self, worksheet: Worksheet) -> None:
        self.canvas.write_range(
            worksheet,
            13,
            2,
            13,
            12,
            "Bisherige Beobachtungen",
            font=self.canvas.font(14, bold=True),
            fill=self.theme.canvas,
        )
        self.canvas.panel(worksheet, 15, 2, 18, 14, self.theme.surface, self.theme.border)
        self.canvas.write_range(
            worksheet,
            15,
            2,
            18,
            14,
            "Noch keine Beobachtungen erfasst.",
            font=self.canvas.font(10, color=self.theme.muted),
            fill=self.theme.surface,
            alignment=self.canvas.alignment("center"),
        )

    def _render_side_panel(self, worksheet: Worksheet) -> None:
        self.canvas.panel(worksheet, 9, 16, 24, 21, self.theme.surface, self.theme.border)
        self.canvas.write_range(
            worksheet,
            9,
            16,
            9,
            20,
            "Arbeitsfokus",
            font=self.canvas.font(12, bold=True),
            fill=self.theme.surface,
        )
        self.canvas.write_range(
            worksheet,
            11,
            16,
            13,
            20,
            "Beobachtungen erfassen und Entwicklung nachvollziehen.",
            font=self.canvas.font(10, color=self.theme.muted),
            fill=self.theme.surface,
        )
        self.canvas.write_range(
            worksheet,
            15,
            16,
            16,
            20,
            "Keine Auswertung. Kein Dashboard. Keine Verwaltung.",
            font=self.canvas.font(9, color=self.theme.muted),
            fill=self.theme.surface_alt,
        )
        self.canvas.write_range(
            worksheet,
            19,
            16,
            21,
            20,
            "Der Button öffnet später denselben zentralen Beobachtungsdialog wie der Schnellzugriff der Stammgruppenübersicht.",
            font=self.canvas.font(9, color=self.theme.muted),
            fill=self.theme.surface,
        )

    def _render_footer(self, worksheet: Worksheet) -> None:
        self.canvas.write_range(
            worksheet,
            32,
            2,
            32,
            8,
            f'="Jenaplan Kompetenzmanager {PRODUCT_VERSION} · student_id "&{SELECTED_STUDENT_ID_REFERENCE}',
            font=self.canvas.font(8, color=self.theme.muted),
            fill=self.theme.canvas,
        )

    def _define_names(self, workbook: Workbook) -> None:
        workbook.defined_names.add(
            DefinedName(
                name="ui_profile_selected_student_id",
                attr_text=f"'{SHEET_TITLE}'!{SELECTED_STUDENT_ID_REFERENCE}",
            )
        )
        workbook.defined_names.add(
            DefinedName(name="ui_profile_student_s001", attr_text=f"'{SHEET_TITLE}'!$B$5:$N$7")
        )
        workbook.defined_names.add(
            DefinedName(name="ui_profile_new_observation", attr_text=f"'{SHEET_TITLE}'!$B$9:$H$11")
        )

    def _student_lookup_formula(self, field_name: str) -> str:
        return (
            f'=IFERROR(INDEX({TABLE_STUDENTS}[{field_name}],'
            f'MATCH({SELECTED_STUDENT_ID_REFERENCE},{TABLE_STUDENTS}[student_id],0)),"")'
        )

    def _column_widths(self) -> dict[str, float]:
        widths = {"A": 2.6, "V": 2.6}
        for column in ("B", "G", "L", "Q"):
            widths[column] = 4.2
        for column in (
            "C",
            "D",
            "E",
            "F",
            "H",
            "I",
            "J",
            "K",
            "M",
            "N",
            "O",
            "P",
            "R",
            "S",
            "T",
            "U",
        ):
            widths[column] = 8.6
        return widths
