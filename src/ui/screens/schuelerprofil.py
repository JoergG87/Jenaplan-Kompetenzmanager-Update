"""Schülerprofil screen for UX prototype v0.2."""

from dataclasses import dataclass

from openpyxl.workbook import Workbook
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.worksheet import Worksheet

from ..components import ExcelCanvas
from ..theme import UiTheme


SHEET_TITLE = "Schülerprofil"
CLASS_OVERVIEW_SHEET = "Klassenübersicht"
CLASS_NAME = "Klasse 2a"
STUDENT_ID = "s001"


@dataclass(frozen=True)
class StudentProfile:
    """Profile data projected from the student model for the UX prototype."""

    student_id: str
    first_name: str
    last_name: str
    class_name: str

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self) -> str:
        return f"{self.first_name[0]}{self.last_name[0]}"


@dataclass(frozen=True)
class ObservationCard:
    """Static observation projection for the profile prototype."""

    date: str
    context: str
    note: str
    competencies: tuple[str, ...]


PROFILE_STUDENT = StudentProfile(STUDENT_ID, "Mia", "Becker", CLASS_NAME)

OBSERVATIONS = (
    ObservationCard(
        "18.06.2026",
        "Deutsch · Leseübung",
        "Mia liest den kurzen Sachtext flüssig und markiert die wichtigsten Informationen selbstständig.",
        ("Informationen aus Texten entnehmen", "Lesestrategien anwenden"),
    ),
    ObservationCard(
        "12.06.2026",
        "Stammgruppe · Partnerarbeit",
        "Sie erklärt ihrem Partner ihren Lösungsweg ruhig und nutzt passende Fachbegriffe.",
        ("Beiträge strukturiert formulieren",),
    ),
    ObservationCard(
        "05.06.2026",
        "Mathematik · Lernzeit",
        "Bei Additionsaufgaben im Zahlenraum 100 kontrolliert Mia ihre Ergebnisse mit Material.",
        ("Rechenwege darstellen", "Ergebnisse prüfen"),
    ),
)


class SchuelerprofilScreenBuilder:
    """Render the student profile as the second v0.2 UX screen."""

    def __init__(self, theme: UiTheme) -> None:
        self.theme = theme
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
        self._render_app_bar(worksheet)
        self._render_header(worksheet)
        self._render_primary_action(worksheet)
        self._render_observations(worksheet)
        self._render_side_panel(worksheet)
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
            f"{PROFILE_STUDENT.class_name}  ·  Schülerprofil",
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
            PROFILE_STUDENT.initials,
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
            PROFILE_STUDENT.display_name,
            font=self.canvas.font(21, bold=True),
            fill=self.theme.surface,
        )
        self.canvas.write_range(
            worksheet,
            6,
            4,
            7,
            11,
            f"{PROFILE_STUDENT.class_name} · student_id {PROFILE_STUDENT.student_id}",
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
            "< Zurück zur Klassenübersicht",
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

        for index, observation in enumerate(OBSERVATIONS):
            row_start = 15 + index * 6
            self._render_observation_card(worksheet, row_start, observation)

    def _render_observation_card(
        self,
        worksheet: Worksheet,
        row_start: int,
        observation: ObservationCard,
    ) -> None:
        self.canvas.panel(worksheet, row_start, 2, row_start + 4, 14, self.theme.surface, self.theme.border)
        self.canvas.write_range(
            worksheet,
            row_start,
            2,
            row_start,
            4,
            observation.date,
            font=self.canvas.font(9, bold=True, color=self.theme.primary),
            fill=self.theme.surface,
        )
        self.canvas.write_range(
            worksheet,
            row_start,
            5,
            row_start,
            13,
            observation.context,
            font=self.canvas.font(9, bold=True, color=self.theme.muted),
            fill=self.theme.surface,
        )
        self.canvas.write_range(
            worksheet,
            row_start + 1,
            2,
            row_start + 2,
            13,
            observation.note,
            font=self.canvas.font(10),
            fill=self.theme.surface,
        )
        self.canvas.write_range(
            worksheet,
            row_start + 3,
            2,
            row_start + 4,
            13,
            " · ".join(observation.competencies),
            font=self.canvas.font(8, color=self.theme.primary),
            fill=self.theme.primary_soft,
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
            "Der Button öffnet später denselben zentralen Beobachtungsdialog wie der Schnellzugriff der Klassenübersicht.",
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
            "UX Prototype v0.2 · student_id s001",
            font=self.canvas.font(8, color=self.theme.muted),
            fill=self.theme.canvas,
        )

    def _define_names(self, workbook: Workbook) -> None:
        workbook.defined_names.add(
            DefinedName(name="ui_profile_student_s001", attr_text=f"'{SHEET_TITLE}'!$B$5:$N$7")
        )
        workbook.defined_names.add(
            DefinedName(name="ui_profile_new_observation", attr_text=f"'{SHEET_TITLE}'!$B$9:$H$11")
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
