"""Seed realistic local test data for the PySide pilot database."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.constants import (  # noqa: E402
    COURSE_ID_PREFIX,
    GROUP_ID_PREFIX,
    STUDENT_ID_PREFIX,
)
from src.core.observation import (  # noqa: E402
    ObservationCompetencyRatingRecord,
    ObservationService,
    ObservationValidator,
)
from src.application.commands.timetable import SaveTimetableEntryCommand  # noqa: E402
from src.core.sqlite_store import (  # noqa: E402
    SQLITE_SPIKE_PATH,
    DocumentRecord,
    MasterDataCourseGroupRecord,
    MasterDataCourseRecord,
    MasterDataGroupRecord,
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteDocumentRepository,
    SQLiteMasterDataRepository,
    SQLiteObservationRepository,
    SQLiteStudentCompetencyConfirmationRepository,
    SQLiteStudentRepository,
    SQLiteTimetableRepository,
    StudentCompetencyConfirmationRecord,
)
from src.core.records import StudentRecord  # noqa: E402
from src.desktop_app.adapters.curriculum_desktop_adapter import (  # noqa: E402
    CurriculumDesktopAdapter,
)
from src.desktop_app.adapters.timetable_desktop_adapter import (  # noqa: E402
    TimetableDesktopAdapter,
)
from src.desktop_app.adapters.student_desktop_adapter import (  # noqa: E402
    StudentDesktopAdapter,
)
from src.desktop_app.view_models.learning_conference_view_model import (  # noqa: E402
    LearningConferenceDraftViewModel,
)
from src.desktop_app.view_models.learning_report_view_model import (  # noqa: E402
    LearningReportChartSelectionViewModel,
    LearningReportDraftViewModel,
    LearningReportSubjectDraftViewModel,
)


class SeedDataError(RuntimeError):
    """Raised when test data cannot be seeded safely."""


@dataclass(frozen=True)
class SeedResult:
    """Summary of seeded records."""

    database_path: Path
    student_count: int
    observation_count: int
    document_count: int
    timetable_count: int
    report_draft_count: int
    report_revision_count: int
    conference_draft_count: int
    conference_revision_count: int


COURSES = (
    ("Kurs 1", "Blau", "#2563EB"),
    ("Kurs 2", "Gruen", "#16A34A"),
    ("Kurs 3", "Orange", "#F97316"),
)

GROUPS = (
    ("Grashüpfer", 0),
    ("Libellen", 1),
    ("Feldmäuse", 2),
    ("Mäuse", 3),
)

STUDENTS = (
    ("Amelie", "Vogel", 0, 0),
    ("Jonas", "Bauer", 0, 1),
    ("Emma", "Schulz", 0, 2),
    ("Noah", "Klein", 0, 0),
    ("Mila", "Hartmann", 0, 1),
    ("Luca", "Werner", 0, 2),
    ("Lea", "Fischer", 1, 0),
    ("Ben", "Richter", 1, 1),
    ("Lina", "Wolf", 1, 2),
    ("Finn", "Neumann", 1, 0),
    ("Clara", "Schwarz", 1, 1),
    ("Paul", "Zimmer", 1, 2),
    ("Sophie", "Krause", 2, 0),
    ("Elias", "Hofmann", 2, 1),
    ("Marie", "Koch", 2, 2),
    ("Henry", "Becker", 2, 0),
    ("Ida", "Schmitt", 2, 1),
    ("Theo", "Krüger", 2, 2),
    ("Ella", "Lange", 3, 0),
    ("Anton", "Weber", 3, 1),
    ("Greta", "Lehmann", 3, 2),
    ("Oskar", "König", 3, 0),
    ("Frieda", "Schröder", 3, 1),
    ("Max", "Brandt", 3, 2),
)


def seed_test_data(
    database_path: Path = SQLITE_SPIKE_PATH,
    *,
    reset: bool = False,
) -> SeedResult:
    """Seed the requested database with deterministic Laura-pilot test data."""
    database_path = Path(database_path)
    documents_root = database_path.parent / "documents"
    if reset:
        _reset_runtime_data(database_path, documents_root)
    database = SQLiteDatabase(database_path)
    _initialize_catalog(database)
    _guard_existing_data(database, reset=reset)
    _seed_master_data(database)
    _seed_timetable(database)
    students = _seed_students(database)
    observation_ids = _seed_observations(database, students)
    _seed_confirmations(database)
    document_count = _seed_documents(database, documents_root, observation_ids)
    workflow_counts = _seed_pilot_workflows(database_path, students)
    return SeedResult(
        database_path=database_path,
        student_count=len(students),
        observation_count=len(SQLiteObservationRepository(database).list_observations()),
        document_count=document_count,
        timetable_count=len(SQLiteTimetableRepository(database).list_entries()),
        report_draft_count=workflow_counts[0],
        report_revision_count=workflow_counts[1],
        conference_draft_count=workflow_counts[2],
        conference_revision_count=workflow_counts[3],
    )


def _reset_runtime_data(database_path: Path, documents_root: Path) -> None:
    database_path.unlink(missing_ok=True)
    if documents_root.exists():
        shutil.rmtree(documents_root)


def _initialize_catalog(database: SQLiteDatabase) -> None:
    database.initialize_schema()
    SQLiteCompetencyRepository(database).ensure_catalog_defaults(
        CurriculumDesktopAdapter().list_entries()
    )


def _guard_existing_data(database: SQLiteDatabase, *, reset: bool) -> None:
    if reset:
        return
    student_count = len(SQLiteStudentRepository(database).list_students())
    observation_count = len(SQLiteObservationRepository(database).list_observations())
    document_count = sum(
        1
        for student in SQLiteStudentRepository(database).list_students()
        for _document in SQLiteDocumentRepository(database).list_documents_for_student(
            student.student_id
        )
    )
    timetable_count = len(SQLiteTimetableRepository(database).list_entries())
    if any((student_count, observation_count, document_count, timetable_count)):
        raise SeedDataError(
            "Die Datenbank enthaelt bereits Schueler, Beobachtungen, Dokumente "
            "oder Stundenplaneintraege. "
            "Nutze --reset fuer ein bewusstes frisches Testsystem."
        )


def _seed_master_data(database: SQLiteDatabase) -> None:
    repository = SQLiteMasterDataRepository(database)
    for index, (group_name, sort_order) in enumerate(GROUPS, start=1):
        repository.upsert_student_group(
            MasterDataGroupRecord(
                f"{GROUP_ID_PREFIX}-{index:06d}",
                group_name,
                True,
                sort_order,
            )
        )
    for index, (course_name, color_name, color_hex) in enumerate(COURSES, start=1):
        repository.upsert_course(
            MasterDataCourseRecord(
                f"{COURSE_ID_PREFIX}-{index:06d}",
                course_name,
                color_name,
                color_hex,
                True,
                index - 1,
            )
        )
    repository.update_course_group(
        MasterDataCourseGroupRecord(
            "course-group-default",
            "Kursverbund A",
            (f"{GROUP_ID_PREFIX}-000001", f"{GROUP_ID_PREFIX}-000003"),
            tuple(f"{COURSE_ID_PREFIX}-{index:06d}" for index in range(1, 4)),
            True,
            0,
        )
    )
    repository.update_course_group(
        MasterDataCourseGroupRecord(
            "CRG-000001",
            "Kursverbund B",
            (f"{GROUP_ID_PREFIX}-000002", f"{GROUP_ID_PREFIX}-000004"),
            tuple(f"{COURSE_ID_PREFIX}-{index:06d}" for index in range(1, 4)),
            True,
            1,
        )
    )
    repository.update_course_group(
        MasterDataCourseGroupRecord(
            "CRG-000002",
            "Mathematik jahrgangsgemischt",
            (f"{GROUP_ID_PREFIX}-000001", f"{GROUP_ID_PREFIX}-000002"),
            (f"{COURSE_ID_PREFIX}-000002", f"{COURSE_ID_PREFIX}-000003"),
            True,
            2,
        )
    )


def _seed_timetable(database: SQLiteDatabase) -> None:
    adapter = TimetableDesktopAdapter(database)
    week = adapter.week_view_model()
    subject_ids = tuple(option.item_id for option in week.subjects)
    if not subject_ids:
        raise SeedDataError("Der Kompetenzkatalog enthaelt keine Stundenplanfaecher.")
    time_slots = (
        ("08:00", "08:45"),
        ("09:00", "09:45"),
        ("10:15", "11:00"),
        ("11:15", "12:00"),
        ("12:15", "13:00"),
    )
    target_cycles = (
        (
            ("group", f"{GROUP_ID_PREFIX}-000001"),
            ("course", f"{COURSE_ID_PREFIX}-000001"),
            ("course_group", "course-group-default"),
            ("group", f"{GROUP_ID_PREFIX}-000003"),
            ("course", f"{COURSE_ID_PREFIX}-000002"),
        ),
        (
            ("group", f"{GROUP_ID_PREFIX}-000002"),
            ("course", f"{COURSE_ID_PREFIX}-000002"),
            ("course_group", "CRG-000001"),
            ("group", f"{GROUP_ID_PREFIX}-000004"),
            ("course", f"{COURSE_ID_PREFIX}-000003"),
        ),
        (
            ("course_group", "CRG-000002"),
            ("group", f"{GROUP_ID_PREFIX}-000001"),
            ("course", f"{COURSE_ID_PREFIX}-000003"),
            ("group", f"{GROUP_ID_PREFIX}-000002"),
            ("course_group", "course-group-default"),
        ),
        (
            ("group", f"{GROUP_ID_PREFIX}-000003"),
            ("course", f"{COURSE_ID_PREFIX}-000001"),
            ("course_group", "CRG-000001"),
            ("group", f"{GROUP_ID_PREFIX}-000004"),
            ("course", f"{COURSE_ID_PREFIX}-000002"),
        ),
        (
            ("group", f"{GROUP_ID_PREFIX}-000001"),
            ("course_group", "CRG-000002"),
            ("course", f"{COURSE_ID_PREFIX}-000003"),
            ("group", f"{GROUP_ID_PREFIX}-000002"),
            ("course_group", "CRG-000001"),
        ),
    )
    rooms = ("Raum 2", "Atelier", "Werkraum", "Schulgarten", "Turnhalle")
    for weekday, targets in enumerate(target_cycles, start=1):
        for slot_index, ((start_time, end_time), (target_type, target_id)) in enumerate(
            zip(time_slots, targets, strict=True)
        ):
            adapter.save_entry(
                SaveTimetableEntryCommand(
                    "",
                    weekday,
                    start_time,
                    end_time,
                    subject_ids[(weekday * 3 + slot_index) % len(subject_ids)],
                    target_type,
                    target_id,
                    rooms[(weekday + slot_index) % len(rooms)],
                    True,
                )
            )


def _seed_students(database: SQLiteDatabase) -> tuple[StudentRecord, ...]:
    repository = SQLiteStudentRepository(database)
    students: list[StudentRecord] = []
    timestamp = "2026-07-04T09:00:00+00:00"
    for index, (first_name, last_name, group_index, course_index) in enumerate(
        STUDENTS, start=1
    ):
        student = StudentRecord(
            f"{STUDENT_ID_PREFIX}-{index:06d}",
            first_name,
            last_name,
            f"{GROUP_ID_PREFIX}-{group_index + 1:06d}",
            f"{COURSE_ID_PREFIX}-{course_index + 1:06d}",
            "Kuenstlicher Datensatz fuer einen realistischen Acht-Monats-Test.",
            True,
            timestamp,
            timestamp,
            None,
        )
        repository.create_student(student)
        students.append(student)
    return tuple(students)


def _seed_observations(
    database: SQLiteDatabase,
    students: tuple[StudentRecord, ...],
) -> tuple[str, ...]:
    repository = SQLiteObservationRepository(database)
    service = ObservationService(
        repository,
        ObservationValidator(),
        (student.student_id for student in students),
    )
    created_ids: list[str] = []
    observation_specs = (
        (0, "2025-09-09", "deutsch", "Leseuebung", "Liest kurze Texte noch stockend und braucht bei unbekannten Woertern Unterstuetzung.", (("CMP-000001", "--"),)),
        (0, "2025-10-21", "deutsch", "Leseuebung", "Liest zunehmend fluessiger und markiert zentrale Woerter selbststaendig.", (("CMP-000001", "-"),)),
        (0, "2026-01-15", "deutsch", "Gespraech ueber Text", "Erfasst Kernaussagen und begruendet eigene Leseeindruecke nachvollziehbar.", (("CMP-000001", "+"),)),
        (0, "2025-11-12", "deutsch", "Schreibprobe", "Plant den eigenen Text und ueberarbeitet nach Rueckmeldung sorgfaeltig.", (("CMP-000003", "+"), ("CMP-000005", "-"))),
        (0, "2026-01-20", "fachuebergreifend", "EPU-Praesentation", "Praesentiert Naturbeobachtungen frei und bindet die Gruppe aufmerksam ein.", (("CMP-000014", "+"), ("CMP-000002", "+"), ("CMP-000035", "+"))),
        (1, "2025-09-16", "mathematik", "Kopfrechnen", "Nutzt Zahlzerlegungen sicher und erklaert kurze Rechenwege.", (("CMP-000006", "+"),)),
        (1, "2025-11-18", "mathematik", "Zahlenraum", "Rechnet im Zahlenraum sicher und kontrolliert Ergebnisse selbststaendig.", (("CMP-000006", "+"),)),
        (1, "2026-01-12", "mathematik", "Lernzielkontrolle", "Loest Aufgaben sicher und begruendet Rechenwege nachvollziehbar.", (("CMP-000006", "++"), ("CMP-000010", "++"))),
        (1, "2025-12-03", "deutsch", "Vortrag", "Spricht klar, braucht aber noch Impulse beim Aufgreifen von Rueckfragen.", (("CMP-000002", "+"),)),
        (2, "2025-09-23", "epu", "Experiment", "Beobachtet genau, benoetigt beim Erklaeren des Naturphaenomens noch Hilfen.", (("CMP-000014", "-"),)),
        (2, "2025-11-05", "epu", "Forscherfrage", "Formuliert Vermutungen und ordnet Beobachtungen passend.", (("CMP-000014", "+"), ("CMP-000015", "+"))),
        (2, "2026-01-09", "epu", "Plakatpraesentation", "Stellt Ergebnisse strukturiert dar und nutzt Medien sachbezogen.", (("CMP-000014", "++"), ("CMP-000015", "+"))),
        (3, "2025-09-18", "sozialkompetenz", "Materialverantwortung", "Uebernimmt Materialdienst, braucht bei der Vollstaendigkeit noch Erinnerung.", (("CMP-000035", "-"), ("CMP-000036", "-"))),
        (3, "2025-11-20", "sozialkompetenz", "Gruppenarbeit", "Bringt sich konstruktiv ein und klaert Zustaendigkeiten mit der Gruppe.", (("CMP-000033", "+"), ("CMP-000035", "+"))),
        (3, "2026-01-16", "sozialkompetenz", "Gespraechsregeln", "Wartet Gespraechsregeln noch nicht immer ab, nimmt Rueckmeldungen aber an.", (("CMP-000034", "-"), ("CMP-000035", "+"))),
        (4, "2025-09-25", "deutsch", "Einzelgespraech", "Erzaehlt strukturiert und hoert Rueckfragen aufmerksam zu.", (("CMP-000002", "+"),)),
        (4, "2025-12-10", "deutsch", "Vortrag", "Spricht sicher vor der Gruppe und bezieht Zuhoerende ein.", (("CMP-000002", "++"),)),
        (4, "2026-01-21", "kunst", "Bildbetrachtung", "Waehlt Farben bewusst und beschreibt die eigene Gestaltungsidee.", (("CMP-000022", "+"),)),
        (5, "2025-09-30", "mathematik", "Sachaufgabe", "Braucht beim Herausloesen der Rechenfrage deutliche Unterstuetzung.", (("CMP-000007", "--"), ("CMP-000009", "--"))),
        (5, "2025-11-27", "mathematik", "Sachaufgabe", "Findet mit Material einen passenden Ansatz, prueft Ergebnisse aber noch unsicher.", (("CMP-000007", "-"), ("CMP-000009", "-"))),
        (5, "2026-01-18", "mathematik", "Lernzielkontrolle", "Unterstuetzungsbedarf bei mehrschrittigen Aufgaben bleibt sichtbar.", (("CMP-000007", "-"), ("CMP-000009", "--"))),
        (6, "2025-10-02", "fachuebergreifend", "Projektarbeit", "Verbindet Messdaten, Notizen und Teamabsprachen in der Gruppe.", (("CMP-000007", "+"), ("CMP-000003", "+"), ("CMP-000033", "+"))),
        (6, "2025-12-15", "fachuebergreifend", "Praesentation", "Erklaert den Arbeitsprozess nachvollziehbar und nutzt Rueckmeldungen.", (("CMP-000010", "+"), ("CMP-000002", "+"), ("CMP-000038", "+"))),
        (7, "2025-10-07", "epu", "Praesentation", "Stellt einen Ablauf in eigenen Worten dar.", (("CMP-000012", "+"),)),
        (8, "2025-10-09", "deutsch", "Schreibzeit", "Plant einen kurzen Text mit Anfang, Mitte und Schluss.", (("CMP-000003", "+"),)),
        (9, "2025-09-11", "sozialkompetenz", "Gruppenarbeit", "Arbeitet engagiert mit, unterbricht aber mehrfach andere Kinder.", (("CMP-000034", "-"),)),
        (9, "2025-10-30", "sozialkompetenz", "Konfliktloesung", "Klaert einen Konflikt nach Moderation und benennt eigene Anteile.", (("CMP-000037", "+"), ("CMP-000034", "+"))),
        (9, "2026-01-14", "sozialkompetenz", "Gruppenarbeit", "Faellt bei hoher Aktivitaet wieder in Unterbrechungen zurueck.", (("CMP-000034", "-"), ("CMP-000037", "+"))),
        (10, "2025-09-19", "mathematik", "Geometrie", "Beschreibt Formen sicher und nutzt Fachbegriffe zunehmend passend.", (("CMP-000008", "+"),)),
        (10, "2026-01-13", "mathematik", "Geometrie", "Begruendet Lagebeziehungen sicher und hilft anderen beim Sortieren.", (("CMP-000008", "++"), ("CMP-000010", "+"))),
        (11, "2025-09-26", "epu", "Forscherrunde", "Ordnet Informationen aus Medien sachbezogen.", (("CMP-000015", "+"), ("CMP-000016", "+"))),
        (11, "2025-11-21", "musik", "Singen", "Haelt Melodie und Rhythmus zunehmend sicher.", (("CMP-000017", "+"),)),
        (11, "2026-01-17", "sport", "Bewegungsspiel", "Bewegt sich fair im Spiel und nimmt Regeln an.", (("CMP-000026", "+"),)),
        # Verdichtete Halbjahresdaten fuer Laura-Pilottest:
        # Fokus-Schueler 1: gut dokumentiertes Kind mit vielen Bereichen und echten Verlaeufen.
        (0, "2025-09-08", "deutsch", "Leseuebung", "Liest kurze Texte stockend, erkennt bekannte Woerter aber sicher wieder.", (("CMP-000001", "-"), ("CMP-000002", "-"))),
        (0, "2025-10-06", "deutsch", "Leseuebung", "Liest vertraute Texte fluessiger und fragt bei unbekannten Woertern gezielt nach.", (("CMP-000001", "+"), ("CMP-000002", "+"))),
        (0, "2025-11-17", "deutsch", "Textgespraech", "Erschliesst den Inhalt zunehmend selbststaendig und belegt Antworten am Text.", (("CMP-000001", "+"), ("CMP-000004", "+"))),
        (0, "2026-01-15", "deutsch", "Lesevortrag", "Liest betont und sicher vor, kann Rueckfragen zum Inhalt beantworten.", (("CMP-000001", "++"), ("CMP-000004", "+"))),
        (0, "2025-09-16", "deutsch", "Schreibprobe", "Plant einen kurzen Text mit Hilfefragen, Satzgrenzen sind noch unsicher.", (("CMP-000003", "-"), ("CMP-000005", "-"))),
        (0, "2025-11-04", "deutsch", "Schreibzeit", "Ueberarbeitet den eigenen Text nach Rueckmeldung sorgfaeltig.", (("CMP-000003", "+"), ("CMP-000005", "+"))),
        (0, "2026-01-20", "deutsch", "Schreibprobe", "Schreibt einen zusammenhaengenden Text mit nachvollziehbarer Struktur.", (("CMP-000003", "+"), ("CMP-000005", "+"))),
        (0, "2025-09-22", "mathematik", "Kopfrechnen", "Rechnet einfache Aufgaben sicher, braucht bei Zehneruebergaengen Zeit.", (("CMP-000006", "+"), ("CMP-000010", "-"))),
        (0, "2025-10-28", "mathematik", "Sachaufgabe", "Markiert wichtige Angaben und findet mit Material einen passenden Rechenweg.", (("CMP-000007", "-"), ("CMP-000009", "-"))),
        (0, "2025-12-02", "mathematik", "Sachaufgabe", "Erklaert den Rechenweg zunehmend nachvollziehbar und prueft Ergebnisse.", (("CMP-000007", "+"), ("CMP-000009", "+"), ("CMP-000010", "+"))),
        (0, "2026-01-22", "mathematik", "Lernzielkontrolle", "Loest mehrschrittige Aufgaben sicher und kontrolliert Ergebnisse selbststaendig.", (("CMP-000006", "++"), ("CMP-000007", "+"), ("CMP-000009", "+"), ("CMP-000010", "++"))),
        (0, "2025-10-01", "epu", "Experiment", "Beobachtet Veraenderungen genau und haelt Ergebnisse mit Symbolen fest.", (("CMP-000012", "+"), ("CMP-000014", "+"))),
        (0, "2025-11-26", "epu", "Forscherfrage", "Formuliert Vermutungen und vergleicht sie mit den Beobachtungen.", (("CMP-000014", "+"), ("CMP-000015", "+"))),
        (0, "2026-01-10", "epu", "Praesentation", "Stellt Ergebnisse strukturiert vor und nutzt Fachbegriffe zunehmend sicher.", (("CMP-000012", "++"), ("CMP-000015", "+"), ("CMP-000016", "+"))),
        (0, "2025-09-29", "sozialkompetenz", "Gruppenarbeit", "Arbeitet freundlich mit, braucht aber Erinnerung an Gespraechsregeln.", (("CMP-000033", "+"), ("CMP-000034", "-"))),
        (0, "2025-11-12", "sozialkompetenz", "Konfliktloesung", "Hoert anderen zu und findet mit der Gruppe eine faire Loesung.", (("CMP-000034", "+"), ("CMP-000037", "+"))),
        (0, "2026-01-19", "sozialkompetenz", "Gruppenarbeit", "Uebernimmt Verantwortung in der Gruppe und achtet auf Absprachen.", (("CMP-000033", "++"), ("CMP-000035", "+"), ("CMP-000038", "+"))),
        (0, "2025-12-08", "kunst", "Gestaltung", "Waehlt Farben bewusst und beschreibt die eigene Gestaltungsidee.", (("CMP-000022", "+"),)),
        (0, "2025-12-18", "musik", "Rhythmusuebung", "Haelt einen einfachen Rhythmus sicher und setzt Einsaetze passend.", (("CMP-000017", "+"),)),
        (0, "2026-01-11", "sport", "Bewegungsspiel", "Bewegt sich fair im Spiel und haelt vereinbarte Regeln ein.", (("CMP-000026", "+"),)),

        # Fokus-Schueler 2: teilweise dokumentiert mit positiver, aber noch nicht abgeschlossener Entwicklung.
        (1, "2025-09-10", "deutsch", "Leseuebung", "Liest kurze Woerter sicher, braucht bei Saetzen noch starke Unterstuetzung.", (("CMP-000001", "--"), ("CMP-000002", "-"))),
        (1, "2025-10-22", "deutsch", "Leseuebung", "Liest einfache Saetze mit Pausen und nutzt bekannte Lesestrategien.", (("CMP-000001", "-"), ("CMP-000002", "-"))),
        (1, "2025-12-05", "deutsch", "Textgespraech", "Kann zentrale Inhalte wiedergeben, benoetigt bei Begruendungen Hilfen.", (("CMP-000001", "-"), ("CMP-000004", "-"))),
        (1, "2026-01-23", "deutsch", "Leseuebung", "Liest vertraute Texte zunehmend fluessig und beantwortet einfache Rueckfragen.", (("CMP-000001", "+"), ("CMP-000004", "-"))),
        (1, "2025-09-24", "mathematik", "Zahlenraum", "Zaehlt sicher weiter, vertauscht bei groesseren Zahlen noch Stellenwerte.", (("CMP-000006", "-"), ("CMP-000010", "-"))),
        (1, "2025-11-19", "mathematik", "Kopfrechnen", "Rechnet mit Material sicherer und erklaert einzelne Schritte.", (("CMP-000006", "+"), ("CMP-000010", "-"))),
        (1, "2026-01-16", "mathematik", "Sachaufgabe", "Findet die Rechenfrage mit Hilfe und prueft Ergebnisse noch unsicher.", (("CMP-000007", "-"), ("CMP-000009", "-"))),
        (1, "2025-10-15", "sozialkompetenz", "Partnerarbeit", "Arbeitet gern mit Partnern, verliert bei Schwierigkeiten schnell den Fokus.", (("CMP-000033", "-"), ("CMP-000035", "-"))),
        (1, "2025-12-12", "sozialkompetenz", "Materialverantwortung", "Bereitet Material zuverlaessig vor und fragt bei Unsicherheit nach.", (("CMP-000035", "+"), ("CMP-000038", "+"))),

        # Fokus-Schueler 5: sichtbarer Unterstuetzungsbedarf mit kleinen Fortschritten.
        (4, "2025-09-12", "deutsch", "Schreibprobe", "Schreibt einzelne Woerter, benoetigt beim Satzbau deutliche Hilfe.", (("CMP-000003", "--"), ("CMP-000005", "--"))),
        (4, "2025-10-31", "deutsch", "Schreibzeit", "Schreibt mit Satzstarter kurze Saetze und uebernimmt Rueckmeldungen.", (("CMP-000003", "-"), ("CMP-000005", "-"))),
        (4, "2026-01-09", "deutsch", "Schreibprobe", "Formuliert kurze Saetze, braucht bei Rechtschreibung und Struktur weiter Hilfe.", (("CMP-000003", "-"), ("CMP-000005", "-"))),
        (4, "2025-09-17", "mathematik", "Kopfrechnen", "Braucht Material und viel Zeit beim Rechnen im Zahlenraum.", (("CMP-000006", "--"), ("CMP-000010", "--"))),
        (4, "2025-11-07", "mathematik", "Zahlenraum", "Nutzen von Material gelingt besser, Ergebnisse werden noch selten geprueft.", (("CMP-000006", "-"), ("CMP-000010", "-"))),
        (4, "2026-01-21", "mathematik", "Lernzielkontrolle", "Loest einfache Aufgaben mit Material, mehrschrittige Aufgaben bleiben schwierig.", (("CMP-000006", "-"), ("CMP-000007", "-"), ("CMP-000010", "-"))),
        (4, "2025-10-10", "sozialkompetenz", "Gespraechsregeln", "Faellt haeufig ins Dazwischenrufen, reagiert aber auf klare Signale.", (("CMP-000034", "--"), ("CMP-000038", "-"))),
        (4, "2025-12-19", "sozialkompetenz", "Gruppenarbeit", "Kann eine Rolle in der Gruppe uebernehmen, braucht aber enge Begleitung.", (("CMP-000033", "-"), ("CMP-000034", "-"), ("CMP-000035", "-"))),

        # Wechselhafte Entwicklung fuer Berichtsvorschau.
        (8, "2025-09-15", "deutsch", "Vortrag", "Spricht gern vor der Gruppe, verliert aber bei Rueckfragen den roten Faden.", (("CMP-000002", "+"),)),
        (8, "2025-11-10", "deutsch", "Textgespraech", "Beteiligt sich wenig und braucht starke Impulse zum Antworten.", (("CMP-000002", "-"), ("CMP-000004", "-"))),
        (8, "2026-01-18", "deutsch", "Praesentation", "Bereitet sich sichtbar vor und spricht wieder sicherer vor der Gruppe.", (("CMP-000002", "+"), ("CMP-000004", "+"))),

        (2, "2025-09-05", "deutsch", "Altbeobachtung", "Diese soft-geloeschte Beobachtung darf nicht in Entwicklung oder Bericht einfliessen.", (("CMP-000001", "--"),)),
    )
    competencies = {
        competency.competency_id: competency
        for competency in SQLiteCompetencyRepository(database).list_competencies()
    }
    for spec_index, (student_index, date, subject_id, context, note, ratings) in enumerate(
        observation_specs
    ):
        observation = service.create_observation(
            student_id=students[student_index].student_id,
            date=date,
            subject_id=subject_id,
            context=context,
            note=note,
            competency_ratings=tuple(
                _rating_record(competencies[competency_id], rating)
                for competency_id, rating in ratings
            ),
        )
        created_ids.append(observation.observation_id)
        if spec_index == len(observation_specs) - 1:
            service.delete_observation(observation_id=observation.observation_id)
    created_ids.extend(
        _seed_all_subject_history(database, service, students)
    )
    return tuple(created_ids)


def _seed_all_subject_history(
    database: SQLiteDatabase,
    service: ObservationService,
    students: tuple[StudentRecord, ...],
) -> tuple[str, ...]:
    competencies_by_subject: dict[str, list[object]] = {}
    for competency in SQLiteCompetencyRepository(database).list_competencies():
        if not competency.active or competency.catalog_status != "current":
            continue
        competencies_by_subject.setdefault(competency.subject_id, []).append(competency)
    subjects = tuple(
        sorted(
            competencies_by_subject,
            key=lambda subject_id: (
                min(item.sort_order for item in competencies_by_subject[subject_id]),
                subject_id,
            ),
        )
    )
    if not subjects:
        raise SeedDataError("Keine aktiven aktuellen Katalogfaecher fuer Testdaten gefunden.")

    created_ids: list[str] = []
    history_start = date(2025, 12, 1)
    rating_cycle = ("+", "-", "++", "+")
    contexts = (
        "Unterrichtsbeobachtung",
        "Arbeitsphase",
        "Praesentation",
        "Partnerarbeit",
        "Lernprodukt",
    )
    for student_index, student in enumerate(students):
        for subject_index, subject_id in enumerate(subjects):
            if student_index >= 18 and (student_index + subject_index) % 3 != 0:
                continue
            competencies = competencies_by_subject[subject_id]
            competency = competencies[(student_index + subject_index) % len(competencies)]
            observation_date = history_start + timedelta(
                days=(student_index * 17 + subject_index * 29) % 218
            )
            observation = service.create_observation(
                student_id=student.student_id,
                date=observation_date.isoformat(),
                subject_id=subject_id,
                context=contexts[(student_index + subject_index) % len(contexts)],
                note=(
                    f"Dokumentiert eine konkrete Lernhandlung in {competency.subject_name}; "
                    "kuenstlicher Acht-Monats-Testdatensatz."
                ),
                competency_ratings=(
                    _rating_record(
                        competency,
                        rating_cycle[(student_index + subject_index) % len(rating_cycle)],
                    ),
                ),
            )
            created_ids.append(observation.observation_id)

            if subject_id in {"deutsch", "mathematik", "epu"} and student_index < 12:
                recent_day = 13 if student_index % 6 == 0 else 1 + (
                    student_index * 2 + subject_index
                ) % 11
                recent_competency = competencies[
                    (student_index + subject_index + 1) % len(competencies)
                ]
                recent = service.create_observation(
                    student_id=student.student_id,
                    date=date(2026, 7, recent_day).isoformat(),
                    subject_id=subject_id,
                    context="Aktuelle Unterrichtsbeobachtung",
                    note=(
                        f"Aktueller kuenstlicher Nachweis in {recent_competency.subject_name} "
                        "fuer Dashboard-, Profil- und Berichtstests."
                    ),
                    competency_ratings=(
                        _rating_record(
                            recent_competency,
                            rating_cycle[(student_index + subject_index + 1) % len(rating_cycle)],
                        ),
                    ),
                )
                created_ids.append(recent.observation_id)

        if student_index % 5 == 0:
            quick_subject_id = subjects[student_index % len(subjects)]
            quick_subject_name = competencies_by_subject[quick_subject_id][0].subject_name
            quick = service.create_observation(
                student_id=student.student_id,
                date=date(2026, 7, 13).isoformat(),
                subject_id=quick_subject_id,
                context="Schnellbeobachtung im Unterricht",
                note=(
                    f"Eindeutige kurze Fachbeobachtung in {quick_subject_name}; "
                    "kuenstlicher Testdatensatz."
                ),
                competency_ratings=(),
                is_quick_observation=True,
            )
            created_ids.append(quick.observation_id)
    return tuple(created_ids)


def _rating_record(competency: object, rating: str) -> ObservationCompetencyRatingRecord:
    return ObservationCompetencyRatingRecord(
        getattr(competency, "competency_id"),
        getattr(competency, "subject_id"),
        getattr(competency, "subject_name"),
        getattr(competency, "learning_area"),
        getattr(competency, "competency_group"),
        getattr(competency, "description"),
        rating,
    )


def _seed_confirmations(database: SQLiteDatabase) -> None:
    repository = SQLiteStudentCompetencyConfirmationRepository(database)
    repository.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            f"{STUDENT_ID_PREFIX}-000001",
            "CMP-000001",
            "++",
            "2026-01-24T12:00:00+00:00",
            "Laura-Test: bewusst hoeher bestaetigt als berechneter Vorschlag.",
        )
    )
    repository.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            f"{STUDENT_ID_PREFIX}-000004",
            "CMP-000035",
            "+",
            "2026-01-24T12:10:00+00:00",
            "Bestaetigt fuer Pilottest.",
        )
    )
    repository.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            f"{STUDENT_ID_PREFIX}-000006",
            "CMP-000007",
            "+",
            "2026-01-24T12:20:00+00:00",
            "Lehrkraft sieht im Alltag mehr Sicherheit als die Testbeobachtungen zeigen.",
        )
    )
    repository.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            f"{STUDENT_ID_PREFIX}-000010",
            "CMP-000034",
            "-",
            "2026-01-24T12:30:00+00:00",
            "Wechselnde Lage bewusst vorsichtig bestaetigt.",
        )
    )


def _seed_documents(
    database: SQLiteDatabase,
    documents_root: Path,
    observation_ids: tuple[str, ...],
) -> int:
    repository = SQLiteDocumentRepository(database)
    documents_root.mkdir(parents=True, exist_ok=True)
    documents = (
        (
            "MED-000001",
            f"{STUDENT_ID_PREFIX}-000001",
            "",
            "Foerderplan Demo",
            "Bericht",
            "Foerderplan_Demo.txt",
            "Demo-Datei: direkt am Schueler hinterlegtes Dokument.\n",
        ),
        (
            "MED-000002",
            f"{STUDENT_ID_PREFIX}-000001",
            observation_ids[2],
            "Praesentation Naturbeobachtung",
            "Arbeitsprobe",
            "Praesentation_Naturbeobachtung.txt",
            "Demo-Datei: Anhang zur fachuebergreifenden Beobachtung.\n",
        ),
        (
            "MED-000003",
            f"{STUDENT_ID_PREFIX}-000002",
            observation_ids[7],
            "Lernzielkontrolle Mathematik",
            "Lernzielkontrolle",
            "Lernzielkontrolle_Mathematik.txt",
            "Demo-Datei: harmlose Platzhalterdatei zu einer Lernzielkontrolle.\n",
        ),
    )
    for document_id, student_id, observation_id, title, document_type, filename, content in documents:
        student_folder = documents_root / student_id
        student_folder.mkdir(parents=True, exist_ok=True)
        file_path = student_folder / f"{document_id}_{filename}"
        file_path.write_text(content, encoding="utf-8")
        repository.create_document(
            DocumentRecord(
                document_id,
                student_id,
                observation_id,
                title,
                document_type,
                str(file_path),
                filename,
                "2026-07-04T10:00:00+00:00",
                "Kuenstliche Demo-Datei fuer Laura-Pilottest.",
                True,
            )
        )
    return len(documents)


def _seed_pilot_workflows(
    database_path: Path,
    students: tuple[StudentRecord, ...],
) -> tuple[int, int, int, int]:
    """Add fictional report and LEG states through the productive boundaries."""
    adapter = StudentDesktopAdapter(database_path)

    focus_student = students[0]
    observation_repository = SQLiteObservationRepository(adapter.database)
    focus_observations = tuple(
        observation
        for observation in observation_repository.list_observations_for_student(
            focus_student.student_id
        )
        if observation.competency_ratings
    )[:4]
    focus_competencies = tuple(
        dict.fromkeys(
            rating.competency_id
            for observation in focus_observations
            for rating in observation.competency_ratings
        )
    )
    focus_subjects = tuple(
        dict.fromkeys(
            rating.subject_id
            for observation in focus_observations
            for rating in observation.competency_ratings
        )
    )
    if not focus_observations or not focus_competencies or not focus_subjects:
        raise SeedDataError("Die fiktiven Pilotdaten enthalten keine Berichtbelege.")

    report = adapter.save_learning_report_draft(
        LearningReportDraftViewModel(
            student_id=focus_student.student_id,
            period_start=date(2025, 8, 1),
            period_end=date(2026, 1, 31),
            teacher_name="Laura Lernbegleiterin",
            overall_text=(
                "Amelie arbeitet zunehmend selbstständig und nutzt Rückmeldungen "
                "sichtbar für ihre nächsten Lernschritte."
            ),
            subjects=tuple(
                LearningReportSubjectDraftViewModel(
                    subject_id,
                    "Stärken werden an konkreten Beobachtungen sichtbar.",
                    "Die Entwicklung über das Halbjahr ist gut nachvollziehbar.",
                    "Überschaubare Zwischenschritte geben Sicherheit.",
                    "Eigene Lösungswege weiter erklären und festhalten.",
                )
                for subject_id in focus_subjects
            ),
            competency_ids=focus_competencies,
            observation_ids=tuple(
                observation.observation_id for observation in focus_observations
            ),
            chart_selections=(
                LearningReportChartSelectionViewModel(
                    focus_subjects[0],
                    "documentation_coverage",
                ),
                LearningReportChartSelectionViewModel(
                    focus_subjects[0],
                    "competency_timeline",
                ),
            ),
        )
    )
    adapter.finalize_learning_report(
        report.report_draft_id,
        "Laura Lernbegleiterin",
    )
    report = adapter.save_learning_report_draft(
        replace(
            report,
            overall_text=(
                "Amelie arbeitet zunehmend selbstständig, begründet ihre Wege "
                "klarer und nutzt Rückmeldungen sicher für nächste Lernschritte."
            ),
        )
    )
    report_status = adapter.finalize_learning_report(
        report.report_draft_id,
        "Laura Lernbegleiterin",
    )
    adapter.generate_learning_report_pdf(
        report_status.current_revision_id
    )

    second_student = students[1]
    second_observations = tuple(
        observation
        for observation in observation_repository.list_observations_for_student(
            second_student.student_id
        )
        if observation.competency_ratings
    )[:2]
    second_ratings = tuple(
        rating
        for observation in second_observations
        for rating in observation.competency_ratings
    )
    if second_observations and second_ratings:
        second_subjects = tuple(dict.fromkeys(rating.subject_id for rating in second_ratings))
        adapter.save_learning_report_draft(
            LearningReportDraftViewModel(
                student_id=second_student.student_id,
                period_start=date(2025, 8, 1),
                period_end=date(2026, 1, 31),
                teacher_name="Laura Lernbegleiterin",
                overall_text="Fiktiver, noch bearbeitbarer Berichtsentwurf.",
                subjects=tuple(
                    LearningReportSubjectDraftViewModel(
                        subject_id,
                        "Sicherer Lernweg in den beobachteten Situationen.",
                        "Nächste Schritte werden im Entwurf weiter ergänzt.",
                        "",
                        "",
                    )
                    for subject_id in second_subjects
                ),
                competency_ids=tuple(
                    dict.fromkeys(rating.competency_id for rating in second_ratings)
                ),
                observation_ids=tuple(
                    observation.observation_id for observation in second_observations
                ),
            )
        )

    conference = adapter.save_learning_conference_draft(
        LearningConferenceDraftViewModel(
            student_id=focus_student.student_id,
            period_start=date(2025, 8, 1),
            period_end=date(2026, 1, 31),
            conference_date=date(2026, 1, 28),
            responsible_teacher="Laura Lernbegleiterin",
            conversation_entry_text="Ruhiger Einstieg mit einem gelungenen Lernmoment.",
            child_retrospective_text="Ich kann meinen Lernweg immer besser erklären.",
            teacher_perspective_text="Fiktive interne Vorbereitung für den Pilottest.",
            strengths_text="Amelie bleibt an Aufgaben dran und fragt gezielt nach.",
            development_fields_text="Eigene Lösungswege noch regelmäßiger festhalten.",
            prepared_goals_text="Lösungswege mit einem Beispiel erklären.",
            prepared_support_text="Zeit für kurze Reflexionspausen einplanen.",
            prepared_agreements_text="Wöchentlich einen Lernweg auswählen.",
            agreed_goals_text="Ich erkläre jede Woche einen Lernweg.",
            agreed_support_text="Die Lehrkraft gibt dafür eine ruhige Reflexionszeit.",
            agreed_agreements_text="Freitags wählen wir gemeinsam ein Beispiel aus.",
            responsibilities_text="Amelie: Beispiel auswählen; Lehrkraft: Zeit geben.",
            next_review_date=date(2026, 3, 27),
            subject_ids=focus_subjects,
            cross_topic_keys=("work_habits", "independence"),
            competency_ids=focus_competencies,
            observation_ids=tuple(
                observation.observation_id for observation in focus_observations
            ),
            chart_types=("documentation_coverage",),
        )
    )
    adapter.complete_learning_conference(conference.learning_conference_draft_id)
    conference = adapter.save_learning_conference_draft(
        replace(
            conference,
            agreed_agreements_text=(
                "Freitags wählen wir gemeinsam ein Beispiel aus und halten den "
                "nächsten Schritt kurz fest."
            ),
        )
    )
    conference_status = adapter.complete_learning_conference(
        conference.learning_conference_draft_id
    )
    current_conference_revision = next(
        item for item in conference_status.revisions if item.status == "completed"
    )
    adapter.generate_learning_conference_pdf(
        current_conference_revision.learning_conference_revision_id
    )

    if second_observations and second_ratings:
        adapter.save_learning_conference_draft(
            LearningConferenceDraftViewModel(
                student_id=second_student.student_id,
                period_start=date(2025, 8, 1),
                period_end=date(2026, 1, 31),
                conference_date=date(2026, 2, 4),
                responsible_teacher="Laura Lernbegleiterin",
                conversation_entry_text="Fiktiver Gesprächseinstieg.",
                child_retrospective_text="Das möchte ich im Gespräch ergänzen.",
                strengths_text="Erste Stärken sind vorbereitet.",
                development_fields_text="Entwicklungsfelder werden gemeinsam besprochen.",
                subject_ids=tuple(
                    dict.fromkeys(rating.subject_id for rating in second_ratings)
                ),
                competency_ids=tuple(
                    dict.fromkeys(rating.competency_id for rating in second_ratings)
                ),
                observation_ids=tuple(
                    observation.observation_id for observation in second_observations
                ),
            )
        )

    return (
        sum(len(adapter.list_learning_report_drafts_for_student(student.student_id)) for student in students),
        len(report_status.history),
        sum(len(adapter.list_learning_conference_drafts_for_student(student.student_id)) for student in students),
        len(conference_status.revisions),
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed Laura-Pilottestdaten in eine SQLite-Datenbank."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=SQLITE_SPIKE_PATH,
        help="Ziel-Datenbankpfad, Standard: data/kompetenzmanager.sqlite",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Bestehende Testdatenbank und data/documents kontrolliert neu erzeugen.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    try:
        result = seed_test_data(args.database, reset=args.reset)
    except SeedDataError as error:
        print(f"Testdaten nicht geschrieben: {error}")
        return 1
    print(f"Testdaten geschrieben: {result.database_path}")
    print(f"Schueler: {result.student_count}")
    print(f"Beobachtungen: {result.observation_count}")
    print(f"Dokumente/Medien: {result.document_count}")
    print(f"Stundenplaneintraege: {result.timetable_count}")
    print(f"Berichtsentwuerfe: {result.report_draft_count}")
    print(f"Berichtrevisionen: {result.report_revision_count}")
    print(f"LEG-Entwuerfe: {result.conference_draft_count}")
    print(f"LEG-Revisionen: {result.conference_revision_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
