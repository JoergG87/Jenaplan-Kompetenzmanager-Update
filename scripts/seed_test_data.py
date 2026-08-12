"""Seed realistic local test data for the PySide pilot database."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.application.school_year_assignment import (  # noqa: E402
    CreateStudentWithInitialEnrollment,
    EnrollStudent,
)
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
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteDocumentRepository,
    SQLiteMasterDataRepository,
    SQLiteObservationRepository,
    SQLiteStudentCompetencyConfirmationRepository,
    SQLiteTimetableRepository,
    StudentCompetencyConfirmationRecord,
)
from src.core.records import (  # noqa: E402
    CourseRecord,
    GroupRecord,
    ReferenceData,
    seed_reference_data,
)
from src.core.school_year import V3Student  # noqa: E402
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
from src.desktop_app.view_models.observation_view_model import (  # noqa: E402
    COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS,
    ObservationAttachmentDraft,
    ObservationCompetencyRatingDraft,
    ObservationDraftViewModel,
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
    ("Kurs 1", "Blau", "#2563EB", 1),
    ("Kurs 2", "Gruen", "#16A34A", 2),
    ("Kurs 3", "Orange", "#F97316", 3),
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

SEED_TIMESTAMP = datetime(2025, 7, 1, 8, 0, tzinfo=UTC)
CIPHER_PILOT_TEST_ROOT_PREFIX = "jkm-final-v4-pilot-testdata-"
CIPHER_PILOT_REFERENCE_DAY = date(2026, 8, 9)
_CIPHER_REQUIRED_TEACHING_SUBJECTS = (
    "deutsch",
    "mathematik",
    "sport",
    "kreatives_gestalten",
    "englisch",
)
_CIPHER_RATING_TOKENS = ("--", "-", "+", "++")


def seed_test_data(
    database_path: Path = SQLITE_SPIKE_PATH,
    *,
    reset: bool = False,
    teacher_name: str = "Laura Lernbegleiterin",
) -> SeedResult:
    """Seed the requested database with deterministic, explicitly synthetic data."""
    database_path = Path(database_path)
    documents_root = database_path.parent / "documents"
    if reset:
        _reset_runtime_data(database_path, documents_root)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database = SQLiteDatabase(database_path)
    _seed_final_v3_foundation(database)
    _initialize_catalog(database)
    _seed_course_groups(database)
    _seed_timetable(database)
    students = _seed_students(database)
    observation_ids = _seed_observations(database, students)
    _seed_confirmations(database)
    document_count = _seed_documents(database, documents_root, observation_ids)
    workflow_counts = _seed_pilot_workflows(
        database_path,
        students,
        teacher_name=teacher_name,
    )
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


def seed_cipher_pilot_test_data(opened_runtime, *, source_root: Path) -> SeedResult:
    """Build the explicit comparison fixture through Final-V4 product boundaries."""
    from src.desktop_app.adapters.master_data_desktop_adapter import (
        MasterDataDesktopAdapter,
    )
    from src.desktop_app.main import _build_cipher_product_student_adapter

    source_root = Path(source_root).resolve(strict=True)
    if _database_has_seed_data(opened_runtime.database):
        raise SeedDataError("Der Final-V4-Testbestand ist nicht fachlich leer.")
    adapter = _build_cipher_product_student_adapter(opened_runtime)
    adapter._today_provider = lambda: CIPHER_PILOT_REFERENCE_DAY
    adapter._now_provider = lambda: datetime(2026, 8, 9, 10, 0, tzinfo=UTC)
    master = MasterDataDesktopAdapter(adapter)
    groups = tuple(
        master.add_group(name)
        for name in ("Sternengruppe", "Regenbogengruppe", "Wiesengruppe")
    )
    courses = tuple(
        master.add_course(name, color, year_level=level)
        for name, color, level in (
            ("Basiskurs", "#2563EB", 1),
            ("Aufbaukurs", "#16A34A", 2),
            ("Vertiefungskurs", "#F97316", 3),
        )
    )
    master.add_course_group(
        "Pilot-Kursverbund",
        tuple(item.item_id for item in groups),
        tuple(item.item_id for item in courses),
    )

    students = []
    for index in range(1, 25):
        created = adapter.save_new_student(
            first_name="Pilotkind",
            last_name=f"Testfall-{index:02d}",
            group_id=groups[(index - 1) % len(groups)].item_id,
            course_id=courses[(index - 1) % len(courses)].item_id,
            student_notes="Ausschließlich synthetischer Pilot-Testdatensatz.",
        )
        if not getattr(created, "success", False):
            raise SeedDataError(f"Synthetischer Schüler {index} wurde nicht angelegt.")
        students.append(created.value)

    subject_options = {
        option.subject_id: option
        for option in adapter.list_documentation_subject_options()
        if option.selected
        and option.subject_id not in COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS
    }
    missing_subjects = tuple(
        subject_id
        for subject_id in _CIPHER_REQUIRED_TEACHING_SUBJECTS
        if subject_id not in subject_options
    )
    if missing_subjects:
        raise SeedDataError(
            "Der Vergleichstestbestand benötigt alle freigegebenen Pflichtfächer."
        )
    current_year = adapter.current_school_year()
    if current_year is None or current_year.label != "2026/27":
        raise SeedDataError("Der Cipher-Produktpfad hat nicht das Schuljahr 2026/27 erzeugt.")
    custom_subject_profiles = {
        0: (),
        1: _CIPHER_REQUIRED_TEACHING_SUBJECTS,
        2: ("deutsch", "mathematik"),
        3: ("sport", "kreatives_gestalten", "englisch"),
        4: ("deutsch", "sport"),
        5: ("mathematik", "englisch"),
    }
    for index, subject_ids in custom_subject_profiles.items():
        adapter.save_student_documentation_subjects(
            students[index].student_id,
            current_year.school_year_id,
            "custom",
            subject_ids,
        )

    competencies = tuple(
        item
        for item in SQLiteCompetencyRepository(opened_runtime.database).list_competencies()
        if item.active and item.catalog_status == "current"
    )
    _require_cipher_comparison_catalog(competencies)
    competencies_by_subject = {
        subject_id: tuple(
            item for item in competencies if item.subject_id == subject_id
        )
        for subject_id in tuple(COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS)
        + _CIPHER_REQUIRED_TEACHING_SUBJECTS
    }
    observations = []
    with tempfile.TemporaryDirectory(prefix="jkm-pilot-seed-sources-") as source_name:
        sources = Path(source_name)
        social_note = sources / "synthetische-gespraechsnotiz.txt"
        social_note.write_text(
            "Synthetische Gesprächsnotiz zur sozialen Entwicklung.\n",
            encoding="utf-8",
        )
        work_sample = sources / "synthetische-arbeitsprobe.txt"
        work_sample.write_text(
            "Synthetische Arbeitsprobe zur Lernorganisation.\n",
            encoding="utf-8",
        )
        subject_evidence = sources / "synthetische-lernzielkontrolle.txt"
        subject_evidence.write_text(
            "Synthetischer Beleg aus einem Unterrichtsfach.\n",
            encoding="utf-8",
        )
        general_report = sources / "synthetischer-foerderhinweis.txt"
        general_report.write_text(
            "Synthetischer Förderhinweis für den manuellen Vergleichstest.\n",
            encoding="utf-8",
        )
        general_note = sources / "synthetische-schuelernotiz.txt"
        general_note.write_text(
            "Synthetische allgemeine Schülernotiz.\n",
            encoding="utf-8",
        )
        for index, student in enumerate(students):
            social_competency = competencies_by_subject[
                "selbst_sozialkompetenz"
            ][index % len(competencies_by_subject["selbst_sozialkompetenz"])]
            work_competency = competencies_by_subject[
                "arbeits_lernkompetenz"
            ][index % len(competencies_by_subject["arbeits_lernkompetenz"])]
            social_attachments = (
                (
                    ObservationAttachmentDraft(
                        str(social_note),
                        "Gesprächsnotiz zur sozialen Entwicklung",
                        "Gesprächsnotiz",
                        "Nur für den synthetischen Vergleichstestbestand.",
                    ),
                )
                if index == 0
                else ()
            )
            work_attachments = (
                (
                    ObservationAttachmentDraft(
                        str(work_sample),
                        "Arbeitsprobe zur Lernorganisation",
                        "Arbeitsprobe",
                        "Nur für den synthetischen Vergleichstestbestand.",
                    ),
                )
                if index == 1
                else ()
            )
            observations.append(
                _save_cipher_observation(
                    adapter,
                    student,
                    social_competency,
                    rating=_CIPHER_RATING_TOKENS[index % 4],
                    observation_date=date(2026, 9, index + 1),
                    context=("Partnerarbeit", "Gruppenarbeit")[index % 2],
                    note=(
                        "Synthetische Beobachtung zur Selbst- und Sozialkompetenz "
                        "für Entwicklungsübersicht, Bericht und LEG."
                    ),
                    attachments=social_attachments,
                )
            )
            observations.append(
                _save_cipher_observation(
                    adapter,
                    student,
                    work_competency,
                    rating=_CIPHER_RATING_TOKENS[(index + 1) % 4],
                    observation_date=date(2027, 1, index + 2),
                    context=("Einzelgespräch", "Präsentation")[index % 2],
                    note=(
                        "Synthetische Beobachtung zur Arbeits-/Lernkompetenz "
                        "für den schuljahresweiten Entwicklungsvergleich."
                    ),
                    attachments=work_attachments,
                )
            )
            if index == 0:
                continue
            allowed_subject_ids = custom_subject_profiles.get(
                index, _CIPHER_REQUIRED_TEACHING_SUBJECTS
            )
            subject_id = allowed_subject_ids[(index - 1) % len(allowed_subject_ids)]
            subject_competencies = competencies_by_subject[subject_id]
            subject_competency = subject_competencies[index % len(subject_competencies)]
            teaching_attachments = (
                (
                    ObservationAttachmentDraft(
                        str(subject_evidence),
                        "Synthetische Lernzielkontrolle",
                        "Lernzielkontrolle",
                        "Nur für den synthetischen Vergleichstestbestand.",
                    ),
                )
                if index == 2
                else ()
            )
            observations.append(
                _save_cipher_observation(
                    adapter,
                    student,
                    subject_competency,
                    rating=_CIPHER_RATING_TOKENS[(index + 2) % 4],
                    observation_date=date(2027, 5, index + 1),
                    context=("Lernzielkontrolle", "Leseübung", "Präsentation")[
                        index % 3
                    ],
                    note=(
                        f"Synthetische Fachbeobachtung in {subject_competency.subject_name} "
                        "für Dashboard-, Profil-, Berichts- und LEG-Tests."
                    ),
                    attachments=teaching_attachments,
                )
            )
        adapter.add_student_document(
            student_id=students[0].student_id,
            source_path=general_report,
            document_type="Bericht",
            title="Synthetischer Förderhinweis",
            note="Nur für den synthetischen Vergleichstestbestand.",
        )
        adapter.add_student_document(
            student_id=students[1].student_id,
            source_path=general_note,
            document_type="Gesprächsnotiz",
            title="Synthetische Schülernotiz",
            note="Nur für den synthetischen Vergleichstestbestand.",
        )

    for index in range(4):
        adapter.save_competency_confirmation(
            student_id=students[index].student_id,
            competency_id=competencies[index].competency_id,
            confirmed_rating=_CIPHER_RATING_TOKENS[index],
            note="Synthetische Bestätigung für den Vergleichstest.",
        )
    _seed_cipher_timetable(opened_runtime.database, groups, courses, competencies)
    workflow_counts = _seed_cipher_workflows(
        adapter, tuple(students), tuple(observations)
    )
    return SeedResult(
        database_path=opened_runtime.database.path,
        student_count=len(students),
        observation_count=len(observations),
        document_count=sum(
            len(adapter.list_documents_for_student(student.student_id))
            for student in students
        ),
        timetable_count=len(
            SQLiteTimetableRepository(opened_runtime.database).list_entries()
        ),
        report_draft_count=workflow_counts[0],
        report_revision_count=workflow_counts[1],
        conference_draft_count=workflow_counts[2],
        conference_revision_count=workflow_counts[3],
    )


def _require_cipher_comparison_catalog(competencies: tuple[object, ...]) -> None:
    expected_ids = tuple(f"CMP-{100000 + index:06d}" for index in range(1, 332))
    actual_ids = tuple(getattr(item, "competency_id") for item in competencies)
    domains = {getattr(item, "subject_id") for item in competencies}
    areas = {
        (getattr(item, "subject_id"), getattr(item, "learning_area"))
        for item in competencies
    }
    topics = {
        (
            getattr(item, "subject_id"),
            getattr(item, "learning_area"),
            getattr(item, "competency_group"),
        )
        for item in competencies
    }
    if (
        actual_ids != expected_ids
        or len(domains) != 12
        or len(areas) != 48
        or len(topics) != 81
        or any(getattr(item, "catalog_status") != "current" for item in competencies)
        or any(not getattr(item, "active") for item in competencies)
        or not set(COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS).issubset(domains)
    ):
        raise SeedDataError(
            "Der aktive Kompetenzkatalog entspricht nicht dem 331er-Entwicklungsbuchvertrag."
        )


def _save_cipher_observation(
    adapter,
    student,
    competency,
    *,
    rating: str,
    observation_date: date,
    context: str,
    note: str,
    attachments: tuple[ObservationAttachmentDraft, ...] = (),
):
    saved = adapter.save_observation(
        ObservationDraftViewModel(
            student_id=student.student_id,
            student_name=f"{student.first_name} {student.last_name}",
            date_text=observation_date.isoformat(),
            subject_id=competency.subject_id,
            subject_display_name=competency.subject_name,
            competency_ratings=(
                ObservationCompetencyRatingDraft(
                    competency_id=competency.competency_id,
                    subject_key=competency.subject_id,
                    subject_display_name=competency.subject_name,
                    learning_area=competency.learning_area,
                    competency_group=competency.competency_group,
                    competency_text=competency.description,
                    rating=rating,
                ),
            ),
            context=context,
            note=note,
            attachments=attachments,
        )
    )
    if not getattr(saved, "success", False):
        raise SeedDataError(
            f"Synthetische Beobachtung für {student.student_id} wurde nicht angelegt."
        )
    return saved.value


def _database_has_seed_data(database: SQLiteDatabase) -> bool:
    with database.connect() as connection:
        return any(
            connection.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() is not None
            for table in ("students", "groups", "courses", "observations")
        )


def _seed_cipher_timetable(database, groups, courses, competencies) -> None:
    adapter = TimetableDesktopAdapter(database)
    subject_ids = tuple(dict.fromkeys(item.subject_id for item in competencies))
    for weekday in range(1, 6):
        for slot in range(2):
            target_type, target_id = (
                ("group", groups[(weekday + slot) % len(groups)].item_id)
                if slot == 0
                else ("course", courses[(weekday + slot) % len(courses)].item_id)
            )
            adapter.save_entry(
                SaveTimetableEntryCommand(
                    "",
                    weekday,
                    f"{8 + slot:02d}:00",
                    f"{8 + slot:02d}:45",
                    subject_ids[(weekday + slot) % len(subject_ids)],
                    target_type,
                    target_id,
                    "Pilotraum",
                    True,
                )
            )


def _seed_cipher_workflows(
    adapter,
    students,
    observations,
) -> tuple[int, int, int, int]:
    focus = students[1]
    second = students[2]
    focus_observations = tuple(
        item for item in observations if item.student_id == focus.student_id
    )
    second_observations = tuple(
        item
        for item in observations
        if item.student_id == second.student_id and item.date >= "2027-01-01"
    )
    focus_competency_ids = tuple(
        dict.fromkeys(
            rating.competency_id
            for item in focus_observations
            for rating in item.competency_ratings
        )
    )
    second_competency_ids = tuple(
        dict.fromkeys(
            rating.competency_id
            for item in second_observations
            for rating in item.competency_ratings
        )
    )
    focus_subject_ids = tuple(
        dict.fromkeys(
            rating.subject_id
            for item in focus_observations
            for rating in item.competency_ratings
        )
    )
    second_subject_ids = tuple(
        dict.fromkeys(
            rating.subject_id
            for item in second_observations
            for rating in item.competency_ratings
        )
    )
    if not (
        focus_observations
        and second_observations
        and focus_competency_ids
        and second_competency_ids
        and focus_subject_ids
        and second_subject_ids
    ):
        raise SeedDataError("Bericht und LEG benötigen synthetische Fachbelege.")
    final_report = adapter.save_learning_report_draft(
        LearningReportDraftViewModel(
            student_id=focus.student_id,
            period_start=date(2026, 8, 1),
            period_end=date(2027, 6, 30),
            teacher_name="Pilot-Lernbegleitung",
            overall_text=(
                "Der synthetische Verlauf zeigt nachvollziehbare Entwicklung "
                "in überfachlichen und fachlichen Bereichen."
            ),
            subjects=tuple(
                LearningReportSubjectDraftViewModel(
                    subject_id,
                    "Synthetische Stärke mit konkretem Beobachtungsbeleg.",
                    "Die Entwicklung ist über mehrere Monate sichtbar.",
                    "Kleine strukturierte Zwischenschritte geben Sicherheit.",
                    "Den nächsten Lernschritt zunehmend selbst benennen.",
                )
                for subject_id in focus_subject_ids
            ),
            competency_ids=focus_competency_ids,
            observation_ids=tuple(
                item.observation_id for item in focus_observations
            ),
        )
    )
    report_status = adapter.finalize_learning_report(
        final_report.report_draft_id,
        "Pilot-Lernbegleitung",
    )
    adapter.generate_learning_report_pdf(report_status.current_revision_id)
    adapter.save_learning_report_draft(
        LearningReportDraftViewModel(
            student_id=second.student_id,
            period_start=date(2027, 1, 1),
            period_end=date(2027, 7, 15),
            teacher_name="Pilot-Lernbegleitung",
            overall_text=(
                "Synthetischer bearbeitbarer Berichtsentwurf für das zweite Halbjahr."
            ),
            subjects=tuple(
                LearningReportSubjectDraftViewModel(
                    subject_id,
                    "Erste synthetische Stärken sind belegt.",
                    "Der Entwurf wird im manuellen Test weiterbearbeitet.",
                    "Unterstützung wird im nächsten Schritt konkretisiert.",
                    "Ein nächstes Ziel ist bereits vorbereitet.",
                )
                for subject_id in second_subject_ids
            ),
            competency_ids=second_competency_ids,
            observation_ids=tuple(
                item.observation_id for item in second_observations
            ),
        )
    )
    final_leg = adapter.save_learning_conference_draft(
        LearningConferenceDraftViewModel(
            student_id=focus.student_id,
            period_start=date(2026, 8, 1),
            period_end=date(2027, 6, 30),
            conference_date=date(2027, 6, 30),
            responsible_teacher="Pilot-Lernbegleitung",
            conversation_entry_text="Synthetischer Gesprächseinstieg.",
            child_retrospective_text="Synthetische Rückschau auf das Schuljahr.",
            teacher_perspective_text="Synthetische Vorbereitung der Lernbegleitung.",
            strengths_text="Synthetische Stärke mit Beobachtungsbeleg.",
            development_fields_text="Synthetisches Entwicklungsfeld.",
            prepared_goals_text="Synthetisches vorbereitetes Ziel.",
            agreed_goals_text="Synthetisches vereinbartes Ziel.",
            responsibilities_text="Synthetische Zuständigkeit.",
            next_review_date=date(2027, 7, 15),
            subject_ids=focus_subject_ids,
            cross_topic_keys=("social_behavior", "work_habits", "independence"),
            competency_ids=focus_competency_ids,
            observation_ids=tuple(
                item.observation_id for item in focus_observations
            ),
        )
    )
    leg_status = adapter.complete_learning_conference(
        final_leg.learning_conference_draft_id
    )
    completed = next(
        item for item in leg_status.revisions if item.status == "completed"
    )
    adapter.generate_learning_conference_pdf(completed.learning_conference_revision_id)
    adapter.save_learning_conference_draft(
        LearningConferenceDraftViewModel(
            student_id=second.student_id,
            period_start=date(2027, 1, 1),
            period_end=date(2027, 7, 15),
            conference_date=date(2027, 7, 15),
            responsible_teacher="Pilot-Lernbegleitung",
            conversation_entry_text="Synthetischer LEG-Entwurf.",
            child_retrospective_text="Die Rückschau wird im manuellen Test ergänzt.",
            strengths_text="Erste synthetische Stärke ist vorbereitet.",
            development_fields_text="Entwicklungsfelder sind noch in Bearbeitung.",
            subject_ids=second_subject_ids,
            cross_topic_keys=("work_habits",),
            competency_ids=second_competency_ids,
            observation_ids=tuple(
                item.observation_id for item in second_observations
            ),
        )
    )
    return (2, len(report_status.history), 2, len(leg_status.revisions))


def _reset_runtime_data(database_path: Path, documents_root: Path) -> None:
    database_path.unlink(missing_ok=True)
    if documents_root.exists():
        shutil.rmtree(documents_root)


def _initialize_catalog(database: SQLiteDatabase) -> None:
    SQLiteCompetencyRepository(database).ensure_catalog_defaults(
        CurriculumDesktopAdapter().list_entries()
    )


def _seed_final_v3_foundation(database: SQLiteDatabase) -> None:
    try:
        database.replace_seed_data(_pilot_reference_data())
    except RuntimeError as error:
        raise SeedDataError(
            "Die Datenbank ist nicht vollstaendig leer. "
            "Nutze --reset fuer ein bewusstes frisches Testsystem."
        ) from error


def _pilot_reference_data() -> ReferenceData:
    reference = seed_reference_data()
    return replace(
        reference,
        students=(),
        groups=tuple(
            GroupRecord(
                f"{GROUP_ID_PREFIX}-{index:06d}",
                group_name,
                True,
            )
            for index, (group_name, _sort_order) in enumerate(GROUPS, start=1)
        ),
        courses=tuple(
            CourseRecord(
                f"{COURSE_ID_PREFIX}-{index:06d}",
                course_name,
                color_hex,
                True,
                year_level,
            )
            for index, (
                course_name,
                _color_name,
                color_hex,
                year_level,
            ) in enumerate(COURSES, start=1)
        ),
        assignments=(),
    )


def _seed_course_groups(database: SQLiteDatabase) -> None:
    repository = SQLiteMasterDataRepository(database)
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


def _seed_students(database: SQLiteDatabase) -> tuple[V3Student, ...]:
    reference = seed_reference_data()
    students: list[V3Student] = []
    for index, (first_name, last_name, group_index, course_index) in enumerate(
        STUDENTS, start=1
    ):
        student_id = f"{STUDENT_ID_PREFIX}-{index:06d}"
        assignment_id = f"ASG-TEST-2026-{index:06d}"
        result = CreateStudentWithInitialEnrollment(
            database.connect,
            student_id_factory=lambda value=student_id: value,
            assignment_id_factory=lambda value=assignment_id: value,
            now_provider=lambda: SEED_TIMESTAMP,
        ).execute(
            first_name=first_name,
            last_name=last_name,
            notes=(
                "Kuenstlicher Datensatz fuer einen realistischen "
                "Acht-Monats-Test."
            ),
            school_year_id=reference.school_year.school_year_id,
            valid_from=reference.school_year.start_date,
            valid_to=reference.school_year.end_date,
            group_id=f"{GROUP_ID_PREFIX}-{group_index + 1:06d}",
            course_id=f"{COURSE_ID_PREFIX}-{course_index + 1:06d}",
        )
        historical_year = reference.historical_school_years[0]
        EnrollStudent(
            database.connect,
            assignment_id_factory=lambda value=(
                f"ASG-TEST-{index:06d}"
            ): value,
            now_provider=lambda: SEED_TIMESTAMP,
        ).execute(
            student_id,
            school_year_id=historical_year.school_year_id,
            valid_from=historical_year.start_date,
            valid_to=historical_year.end_date,
            group_id=f"{GROUP_ID_PREFIX}-{group_index + 1:06d}",
            course_id=f"{COURSE_ID_PREFIX}-{course_index + 1:06d}",
        )
        students.append(result.student)
    return tuple(students)


def _seed_observations(
    database: SQLiteDatabase,
    students: tuple[V3Student, ...],
) -> tuple[str, ...]:
    repository = SQLiteObservationRepository(database)
    service = ObservationService(
        repository,
        ObservationValidator(),
        (student.student_id for student in students),
    )
    created_ids: list[str] = []
    observation_specs = (
        (0, "2025-09-09", "deutsch", "Leseuebung", "Liest kurze Texte noch stockend und braucht bei unbekannten Woertern Unterstuetzung.", (("CMP-100034", "--"),)),
        (0, "2025-10-21", "deutsch", "Leseuebung", "Liest zunehmend fluessiger und markiert zentrale Woerter selbststaendig.", (("CMP-100034", "-"),)),
        (0, "2026-01-15", "deutsch", "Gespraech ueber Text", "Erfasst Kernaussagen und begruendet eigene Leseeindruecke nachvollziehbar.", (("CMP-100034", "+"),)),
        (0, "2025-11-12", "deutsch", "Schreibprobe", "Plant den eigenen Text und ueberarbeitet nach Rueckmeldung sorgfaeltig.", (("CMP-100050", "+"), ("CMP-100056", "-"))),
        (0, "2026-01-20", "fachuebergreifend", "EPU-Praesentation", "Praesentiert Naturbeobachtungen frei und bindet die Gruppe aufmerksam ein.", (("CMP-100023", "+"), ("CMP-100043", "+"), ("CMP-100007", "+"))),
        (1, "2025-09-16", "mathematik", "Kopfrechnen", "Nutzt Zahlzerlegungen sicher und erklaert kurze Rechenwege.", (("CMP-100084", "+"),)),
        (1, "2025-11-18", "mathematik", "Zahlenraum", "Rechnet im Zahlenraum sicher und kontrolliert Ergebnisse selbststaendig.", (("CMP-100084", "+"),)),
        (1, "2026-01-12", "mathematik", "Lernzielkontrolle", "Loest Aufgaben sicher und begruendet Rechenwege nachvollziehbar.", (("CMP-100084", "++"), ("CMP-100113", "++"))),
        (1, "2025-12-03", "deutsch", "Vortrag", "Spricht klar, braucht aber noch Impulse beim Aufgreifen von Rueckfragen.", (("CMP-100043", "+"),)),
        (2, "2025-09-23", "epu", "Experiment", "Beobachtet genau, benoetigt beim Erklaeren des Naturphaenomens noch Hilfen.", (("CMP-100023", "-"),)),
        (2, "2025-11-05", "epu", "Forscherfrage", "Formuliert Vermutungen und ordnet Beobachtungen passend.", (("CMP-100023", "+"), ("CMP-100024", "+"))),
        (2, "2026-01-09", "epu", "Plakatpraesentation", "Stellt Ergebnisse strukturiert dar und nutzt Medien sachbezogen.", (("CMP-100023", "++"), ("CMP-100024", "+"))),
        (3, "2025-09-18", "selbst_sozialkompetenz", "Materialverantwortung", "Uebernimmt Materialdienst, braucht bei der Vollstaendigkeit noch Erinnerung.", (("CMP-100007", "-"), ("CMP-100004", "-"))),
        (3, "2025-11-20", "selbst_sozialkompetenz", "Gruppenarbeit", "Bringt sich konstruktiv ein und klaert Zustaendigkeiten mit der Gruppe.", (("CMP-100005", "+"), ("CMP-100007", "+"))),
        (3, "2026-01-16", "selbst_sozialkompetenz", "Gespraechsregeln", "Wartet Gespraechsregeln noch nicht immer ab, nimmt Rueckmeldungen aber an.", (("CMP-100006", "-"), ("CMP-100007", "+"))),
        (4, "2025-09-25", "deutsch", "Einzelgespraech", "Erzaehlt strukturiert und hoert Rueckfragen aufmerksam zu.", (("CMP-100043", "+"),)),
        (4, "2025-12-10", "deutsch", "Vortrag", "Spricht sicher vor der Gruppe und bezieht Zuhoerende ein.", (("CMP-100043", "++"),)),
        (4, "2026-01-21", "kreatives_gestalten", "Bildbetrachtung", "Waehlt Farben bewusst und beschreibt die eigene Gestaltungsidee.", (("CMP-100136", "+"),)),
        (5, "2025-09-30", "mathematik", "Sachaufgabe", "Braucht beim Herausloesen der Rechenfrage deutliche Unterstuetzung.", (("CMP-100115", "--"), ("CMP-100116", "--"))),
        (5, "2025-11-27", "mathematik", "Sachaufgabe", "Findet mit Material einen passenden Ansatz, prueft Ergebnisse aber noch unsicher.", (("CMP-100115", "-"), ("CMP-100116", "-"))),
        (5, "2026-01-18", "mathematik", "Lernzielkontrolle", "Unterstuetzungsbedarf bei mehrschrittigen Aufgaben bleibt sichtbar.", (("CMP-100115", "-"), ("CMP-100116", "--"))),
        (6, "2025-10-02", "fachuebergreifend", "Projektarbeit", "Verbindet Messdaten, Notizen und Teamabsprachen in der Gruppe.", (("CMP-100115", "+"), ("CMP-100050", "+"), ("CMP-100005", "+"))),
        (6, "2025-12-15", "fachuebergreifend", "Praesentation", "Erklaert den Arbeitsprozess nachvollziehbar und nutzt Rueckmeldungen.", (("CMP-100113", "+"), ("CMP-100043", "+"), ("CMP-100001", "+"))),
        (7, "2025-10-07", "epu", "Praesentation", "Stellt einen Ablauf in eigenen Worten dar.", (("CMP-100025", "+"),)),
        (8, "2025-10-09", "deutsch", "Schreibzeit", "Plant einen kurzen Text mit Anfang, Mitte und Schluss.", (("CMP-100050", "+"),)),
        (9, "2025-09-11", "selbst_sozialkompetenz", "Gruppenarbeit", "Arbeitet engagiert mit, unterbricht aber mehrfach andere Kinder.", (("CMP-100006", "-"),)),
        (9, "2025-10-30", "selbst_sozialkompetenz", "Konfliktloesung", "Klaert einen Konflikt nach Moderation und benennt eigene Anteile.", (("CMP-100008", "+"), ("CMP-100006", "+"))),
        (9, "2026-01-14", "selbst_sozialkompetenz", "Gruppenarbeit", "Faellt bei hoher Aktivitaet wieder in Unterbrechungen zurueck.", (("CMP-100006", "-"), ("CMP-100008", "+"))),
        (10, "2025-09-19", "mathematik", "Geometrie", "Beschreibt Formen sicher und nutzt Fachbegriffe zunehmend passend.", (("CMP-100128", "+"),)),
        (10, "2026-01-13", "mathematik", "Geometrie", "Begruendet Lagebeziehungen sicher und hilft anderen beim Sortieren.", (("CMP-100128", "++"), ("CMP-100113", "+"))),
        (11, "2025-09-26", "epu", "Forscherrunde", "Ordnet Informationen aus Medien sachbezogen.", (("CMP-100024", "+"), ("CMP-100026", "+"))),
        (11, "2025-11-21", "musik", "Singen", "Haelt Melodie und Rhythmus zunehmend sicher.", (("CMP-100286", "+"),)),
        (11, "2026-01-17", "sport", "Bewegungsspiel", "Bewegt sich fair im Spiel und nimmt Regeln an.", (("CMP-100175", "+"),)),
        # Verdichtete Halbjahresdaten fuer Laura-Pilottest:
        # Fokus-Schueler 1: gut dokumentiertes Kind mit vielen Bereichen und echten Verlaeufen.
        (0, "2025-09-08", "deutsch", "Leseuebung", "Liest kurze Texte stockend, erkennt bekannte Woerter aber sicher wieder.", (("CMP-100034", "-"), ("CMP-100043", "-"))),
        (0, "2025-10-06", "deutsch", "Leseuebung", "Liest vertraute Texte fluessiger und fragt bei unbekannten Woertern gezielt nach.", (("CMP-100034", "+"), ("CMP-100043", "+"))),
        (0, "2025-11-17", "deutsch", "Textgespraech", "Erschliesst den Inhalt zunehmend selbststaendig und belegt Antworten am Text.", (("CMP-100034", "+"), ("CMP-100035", "+"))),
        (0, "2026-01-15", "deutsch", "Lesevortrag", "Liest betont und sicher vor, kann Rueckfragen zum Inhalt beantworten.", (("CMP-100034", "++"), ("CMP-100035", "+"))),
        (0, "2025-09-16", "deutsch", "Schreibprobe", "Plant einen kurzen Text mit Hilfefragen, Satzgrenzen sind noch unsicher.", (("CMP-100050", "-"), ("CMP-100056", "-"))),
        (0, "2025-11-04", "deutsch", "Schreibzeit", "Ueberarbeitet den eigenen Text nach Rueckmeldung sorgfaeltig.", (("CMP-100050", "+"), ("CMP-100056", "+"))),
        (0, "2026-01-20", "deutsch", "Schreibprobe", "Schreibt einen zusammenhaengenden Text mit nachvollziehbarer Struktur.", (("CMP-100050", "+"), ("CMP-100056", "+"))),
        (0, "2025-09-22", "mathematik", "Kopfrechnen", "Rechnet einfache Aufgaben sicher, braucht bei Zehneruebergaengen Zeit.", (("CMP-100084", "+"), ("CMP-100113", "-"))),
        (0, "2025-10-28", "mathematik", "Sachaufgabe", "Markiert wichtige Angaben und findet mit Material einen passenden Rechenweg.", (("CMP-100115", "-"), ("CMP-100116", "-"))),
        (0, "2025-12-02", "mathematik", "Sachaufgabe", "Erklaert den Rechenweg zunehmend nachvollziehbar und prueft Ergebnisse.", (("CMP-100115", "+"), ("CMP-100116", "+"), ("CMP-100113", "+"))),
        (0, "2026-01-22", "mathematik", "Lernzielkontrolle", "Loest mehrschrittige Aufgaben sicher und kontrolliert Ergebnisse selbststaendig.", (("CMP-100084", "++"), ("CMP-100115", "+"), ("CMP-100116", "+"), ("CMP-100113", "++"))),
        (0, "2025-10-01", "epu", "Experiment", "Beobachtet Veraenderungen genau und haelt Ergebnisse mit Symbolen fest.", (("CMP-100025", "+"), ("CMP-100023", "+"))),
        (0, "2025-11-26", "epu", "Forscherfrage", "Formuliert Vermutungen und vergleicht sie mit den Beobachtungen.", (("CMP-100023", "+"), ("CMP-100024", "+"))),
        (0, "2026-01-10", "epu", "Praesentation", "Stellt Ergebnisse strukturiert vor und nutzt Fachbegriffe zunehmend sicher.", (("CMP-100025", "++"), ("CMP-100024", "+"), ("CMP-100026", "+"))),
        (0, "2025-09-29", "selbst_sozialkompetenz", "Gruppenarbeit", "Arbeitet freundlich mit, braucht aber Erinnerung an Gespraechsregeln.", (("CMP-100005", "+"), ("CMP-100006", "-"))),
        (0, "2025-11-12", "selbst_sozialkompetenz", "Konfliktloesung", "Hoert anderen zu und findet mit der Gruppe eine faire Loesung.", (("CMP-100006", "+"), ("CMP-100008", "+"))),
        (0, "2026-01-19", "selbst_sozialkompetenz", "Gruppenarbeit", "Uebernimmt Verantwortung in der Gruppe und achtet auf Absprachen.", (("CMP-100005", "++"), ("CMP-100007", "+"), ("CMP-100001", "+"))),
        (0, "2025-12-08", "kreatives_gestalten", "Gestaltung", "Waehlt Farben bewusst und beschreibt die eigene Gestaltungsidee.", (("CMP-100136", "+"),)),
        (0, "2025-12-18", "musik", "Rhythmusuebung", "Haelt einen einfachen Rhythmus sicher und setzt Einsaetze passend.", (("CMP-100286", "+"),)),
        (0, "2026-01-11", "sport", "Bewegungsspiel", "Bewegt sich fair im Spiel und haelt vereinbarte Regeln ein.", (("CMP-100175", "+"),)),

        # Fokus-Schueler 2: teilweise dokumentiert mit positiver, aber noch nicht abgeschlossener Entwicklung.
        (1, "2025-09-10", "deutsch", "Leseuebung", "Liest kurze Woerter sicher, braucht bei Saetzen noch starke Unterstuetzung.", (("CMP-100034", "--"), ("CMP-100043", "-"))),
        (1, "2025-10-22", "deutsch", "Leseuebung", "Liest einfache Saetze mit Pausen und nutzt bekannte Lesestrategien.", (("CMP-100034", "-"), ("CMP-100043", "-"))),
        (1, "2025-12-05", "deutsch", "Textgespraech", "Kann zentrale Inhalte wiedergeben, benoetigt bei Begruendungen Hilfen.", (("CMP-100034", "-"), ("CMP-100035", "-"))),
        (1, "2026-01-23", "deutsch", "Leseuebung", "Liest vertraute Texte zunehmend fluessig und beantwortet einfache Rueckfragen.", (("CMP-100034", "+"), ("CMP-100035", "-"))),
        (1, "2025-09-24", "mathematik", "Zahlenraum", "Zaehlt sicher weiter, vertauscht bei groesseren Zahlen noch Stellenwerte.", (("CMP-100084", "-"), ("CMP-100113", "-"))),
        (1, "2025-11-19", "mathematik", "Kopfrechnen", "Rechnet mit Material sicherer und erklaert einzelne Schritte.", (("CMP-100084", "+"), ("CMP-100113", "-"))),
        (1, "2026-01-16", "mathematik", "Sachaufgabe", "Findet die Rechenfrage mit Hilfe und prueft Ergebnisse noch unsicher.", (("CMP-100115", "-"), ("CMP-100116", "-"))),
        (1, "2025-10-15", "selbst_sozialkompetenz", "Partnerarbeit", "Arbeitet gern mit Partnern, verliert bei Schwierigkeiten schnell den Fokus.", (("CMP-100005", "-"), ("CMP-100007", "-"))),
        (1, "2025-12-12", "selbst_sozialkompetenz", "Materialverantwortung", "Bereitet Material zuverlaessig vor und fragt bei Unsicherheit nach.", (("CMP-100007", "+"), ("CMP-100001", "+"))),

        # Fokus-Schueler 5: sichtbarer Unterstuetzungsbedarf mit kleinen Fortschritten.
        (4, "2025-09-12", "deutsch", "Schreibprobe", "Schreibt einzelne Woerter, benoetigt beim Satzbau deutliche Hilfe.", (("CMP-100050", "--"), ("CMP-100056", "--"))),
        (4, "2025-10-31", "deutsch", "Schreibzeit", "Schreibt mit Satzstarter kurze Saetze und uebernimmt Rueckmeldungen.", (("CMP-100050", "-"), ("CMP-100056", "-"))),
        (4, "2026-01-09", "deutsch", "Schreibprobe", "Formuliert kurze Saetze, braucht bei Rechtschreibung und Struktur weiter Hilfe.", (("CMP-100050", "-"), ("CMP-100056", "-"))),
        (4, "2025-09-17", "mathematik", "Kopfrechnen", "Braucht Material und viel Zeit beim Rechnen im Zahlenraum.", (("CMP-100084", "--"), ("CMP-100113", "--"))),
        (4, "2025-11-07", "mathematik", "Zahlenraum", "Nutzen von Material gelingt besser, Ergebnisse werden noch selten geprueft.", (("CMP-100084", "-"), ("CMP-100113", "-"))),
        (4, "2026-01-21", "mathematik", "Lernzielkontrolle", "Loest einfache Aufgaben mit Material, mehrschrittige Aufgaben bleiben schwierig.", (("CMP-100084", "-"), ("CMP-100115", "-"), ("CMP-100113", "-"))),
        (4, "2025-10-10", "selbst_sozialkompetenz", "Gespraechsregeln", "Faellt haeufig ins Dazwischenrufen, reagiert aber auf klare Signale.", (("CMP-100006", "--"), ("CMP-100001", "-"))),
        (4, "2025-12-19", "selbst_sozialkompetenz", "Gruppenarbeit", "Kann eine Rolle in der Gruppe uebernehmen, braucht aber enge Begleitung.", (("CMP-100005", "-"), ("CMP-100006", "-"), ("CMP-100007", "-"))),

        # Wechselhafte Entwicklung fuer Berichtsvorschau.
        (8, "2025-09-15", "deutsch", "Vortrag", "Spricht gern vor der Gruppe, verliert aber bei Rueckfragen den roten Faden.", (("CMP-100043", "+"),)),
        (8, "2025-11-10", "deutsch", "Textgespraech", "Beteiligt sich wenig und braucht starke Impulse zum Antworten.", (("CMP-100043", "-"), ("CMP-100035", "-"))),
        (8, "2026-01-18", "deutsch", "Praesentation", "Bereitet sich sichtbar vor und spricht wieder sicherer vor der Gruppe.", (("CMP-100043", "+"), ("CMP-100035", "+"))),

        (2, "2025-09-05", "deutsch", "Altbeobachtung", "Diese soft-geloeschte Beobachtung darf nicht in Entwicklung oder Bericht einfliessen.", (("CMP-100034", "--"),)),
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
    students: tuple[V3Student, ...],
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
            "CMP-100034",
            "++",
            "2026-01-24T12:00:00+00:00",
            "Laura-Test: bewusst hoeher bestaetigt als berechneter Vorschlag.",
        )
    )
    repository.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            f"{STUDENT_ID_PREFIX}-000004",
            "CMP-100007",
            "+",
            "2026-01-24T12:10:00+00:00",
            "Bestaetigt fuer Pilottest.",
        )
    )
    repository.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            f"{STUDENT_ID_PREFIX}-000006",
            "CMP-100115",
            "+",
            "2026-01-24T12:20:00+00:00",
            "Lehrkraft sieht im Alltag mehr Sicherheit als die Testbeobachtungen zeigen.",
        )
    )
    repository.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            f"{STUDENT_ID_PREFIX}-000010",
            "CMP-100006",
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
    students: tuple[V3Student, ...],
    *,
    teacher_name: str,
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
            teacher_name=teacher_name,
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
        teacher_name,
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
        teacher_name,
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
                teacher_name=teacher_name,
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
            responsible_teacher=teacher_name,
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
                responsible_teacher=teacher_name,
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
    parser.add_argument(
        "--cipher-root",
        type=Path,
        help=(
            "Noch nicht existierender absoluter System-Temporärroot mit Präfix "
            f"{CIPHER_PILOT_TEST_ROOT_PREFIX}; erzeugt Final V4 ohne Reset."
        ),
    )
    return parser.parse_args(argv)


def build_cipher_pilot_test_root(root: Path) -> dict[str, object]:
    """Create one restartable same-installation macOS Cipher test root."""
    from src.core.database_engine import SQLCipherConnectionProvider
    from src.desktop_app.runtime import (
        prepare_cipher_runtime_storage,
        prepare_security_runtime_storage,
    )
    from src.security.cipher_product_runtime import open_cipher_product_runtime
    from src.security.domain import AuthenticationStatus
    from src.security.final_v4_backup_runtime import (
        build_final_v4_encrypted_backup_service,
    )
    from src.security.startup import build_security_runtime

    target = _require_fresh_cipher_test_root(root)
    target.mkdir(mode=0o700)
    security_paths = prepare_security_runtime_storage(data_root=target)
    security = build_security_runtime(security_paths)
    password = _cipher_pilot_password(target)
    enrollment = security.service.prepare_local_account_enrollment(password)
    if not security.service.confirm_local_account_enrollment(enrollment.recovery_set_id):
        raise SeedDataError("Die synthetische Testinstallation wurde nicht aktiviert.")
    if security.service.authenticate_password(password).status is not AuthenticationStatus.AUTHENTICATED:
        raise SeedDataError("Die synthetische Testinstallation wurde nicht authentifiziert.")
    account = security.repository.load_account()
    provider = SQLCipherConnectionProvider(
        expected_binding_version="0.6.2+jkm.sqlcipher4170.1",
        expected_engine_version="4.17.0 community",
    )
    opened = open_cipher_product_runtime(
        paths=security_paths,
        account_loader=lambda: account,
        authentication_confirmed=True,
        first_run_allowed=True,
        sqlcipher_provider=provider,
    )
    seed_cipher_pilot_test_data(opened, source_root=target)
    restarted = open_cipher_product_runtime(
        paths=security_paths,
        account_loader=lambda: account,
        authentication_confirmed=True,
        first_run_allowed=False,
        sqlcipher_provider=provider,
    )
    paths = prepare_cipher_runtime_storage(data_root=target)
    backup_service = build_final_v4_encrypted_backup_service(
        opened_runtime=restarted.runtime,
        account_loader=lambda: account,
        environ=os.environ,
        sqlcipher_provider=provider,
        product_paths=paths,
    )
    backup_path = paths.backups / "Pilot-Testbestand-2026-27.jkmebackup"
    backup = backup_service.create(backup_path)
    verified = backup_service.verify(backup_path)
    restore_parent = target / "encrypted-restore-staging"
    restore_parent.mkdir(mode=0o700)
    restore = backup_service.restore_staging(
        backup_path,
        restore_parent / "pilot-seed-verification",
    )
    ready = backup_service.verify_restore_ready(
        restore.staging_root,
        expected_container_sha256=verified.container_sha256,
    )
    preview = backup_service.restore_preview_counts(
        ready.staging_root,
        expected_container_sha256=verified.container_sha256,
    )
    inventory = _cipher_database_inventory(restarted.database)
    storage = _cipher_storage_inventory(paths)
    _require_complete_cipher_comparison_inventory(
        inventory,
        managed_documents=preview.managed_documents,
        storage=storage,
    )
    compatibility = restarted.runtime.final_v4.compatibility
    return {
        "backup": str(backup.path),
        "backup_sha256": backup.container_sha256,
        "cipher_provider": compatibility.cipher_provider,
        "cipher_version": compatibility.cipher_version,
        "database": str(paths.final_v4_database),
        "restore_state": restore.state if ready.ready_path.is_file() else "INVALID",
        "root": str(target),
        "sqlite_version": compatibility.sqlite_version,
        "managed_documents": preview.managed_documents,
        **inventory,
        **storage,
    }


def verify_cipher_pilot_test_root(root: Path) -> dict[str, object]:
    """Reopen and verify a retained synthetic root in a separate app process."""
    from src.core.database_engine import SQLCipherConnectionProvider
    from src.desktop_app.runtime import (
        prepare_cipher_runtime_storage,
        prepare_security_runtime_storage,
    )
    from src.security.cipher_product_runtime import open_cipher_product_runtime
    from src.security.domain import AuthenticationStatus
    from src.security.final_v4_backup_runtime import (
        build_final_v4_encrypted_backup_service,
    )
    from src.security.startup import build_security_runtime

    target = Path(root).expanduser().resolve(strict=True)
    if (
        target.parent not in {
            Path("/private/tmp").resolve(strict=True),
            Path(tempfile.gettempdir()).resolve(strict=True),
        }
        or not target.name.startswith(CIPHER_PILOT_TEST_ROOT_PREFIX)
        or target.is_symlink()
    ):
        raise SeedDataError("Der Cipher-Testroot liegt nicht in der freigegebenen Temporärwurzel.")
    security_paths = prepare_security_runtime_storage(data_root=target)
    security = build_security_runtime(security_paths)
    password = _cipher_pilot_password(target)
    if security.service.authenticate_password(password).status is not AuthenticationStatus.AUTHENTICATED:
        raise SeedDataError("Die synthetische Testinstallation wurde nicht authentifiziert.")
    account = security.repository.load_account()
    provider = SQLCipherConnectionProvider(
        expected_binding_version="0.6.2+jkm.sqlcipher4170.1",
        expected_engine_version="4.17.0 community",
    )
    opened = open_cipher_product_runtime(
        paths=security_paths,
        account_loader=lambda: account,
        authentication_confirmed=True,
        first_run_allowed=False,
        sqlcipher_provider=provider,
    )
    paths = prepare_cipher_runtime_storage(data_root=target)
    service = build_final_v4_encrypted_backup_service(
        opened_runtime=opened.runtime,
        account_loader=lambda: account,
        environ=os.environ,
        sqlcipher_provider=provider,
        product_paths=paths,
    )
    backup_path = paths.backups / "Pilot-Testbestand-2026-27.jkmebackup"
    verified = service.verify(backup_path)
    ready = service.verify_restore_ready(
        target / "encrypted-restore-staging" / "pilot-seed-verification",
        expected_container_sha256=verified.container_sha256,
    )
    preview = service.restore_preview_counts(
        ready.staging_root,
        expected_container_sha256=verified.container_sha256,
    )
    inventory = _cipher_database_inventory(opened.database)
    storage = _cipher_storage_inventory(paths)
    _require_complete_cipher_comparison_inventory(
        inventory,
        managed_documents=preview.managed_documents,
        storage=storage,
    )
    if preview.students != 24 or preview.observations != 71:
        raise SeedDataError("Die Backup-Vorschau stimmt nicht mit dem Testbestand überein.")
    compatibility = opened.runtime.final_v4.compatibility
    return {
        "backup": str(backup_path),
        "backup_sha256": verified.container_sha256,
        "cipher_provider": compatibility.cipher_provider,
        "cipher_version": compatibility.cipher_version,
        "database_context_id": opened.database_context_id,
        "database_key_fingerprint_sha256": opened.database_key_fingerprint_sha256,
        "dmk_fingerprint_sha256": opened.dmk_fingerprint_sha256,
        "managed_documents": preview.managed_documents,
        "restore_state": "RESTORE_READY",
        "root": str(target),
        "sqlite_version": compatibility.sqlite_version,
        **inventory,
        **storage,
    }


def _cipher_database_inventory(database: SQLiteDatabase) -> dict[str, object]:
    with database.connect() as connection:
        catalog = connection.execute(
            """
            SELECT competency_id, subject_id, learning_area, competency_group,
                   catalog_status, active
            FROM competencies
            ORDER BY sort_order, competency_id
            """
        ).fetchall()
        rating_tokens = tuple(
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT rating FROM observation_competency_ratings"
            ).fetchall()
        )

        def tokens_for_subject(subject_id: str) -> list[str]:
            present = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT DISTINCT rating
                    FROM observation_competency_ratings
                    WHERE subject_id = ?
                    """,
                    (subject_id,),
                ).fetchall()
            }
            return [token for token in _CIPHER_RATING_TOKENS if token in present]

        observation_range = tuple(
            connection.execute(
                "SELECT MIN(date), MAX(date) FROM observations"
            ).fetchone()
        )
        profile_sizes = sorted(
            int(row[0])
            for row in connection.execute(
                """
                SELECT COUNT(selection.subject_id)
                FROM student_documentation_subject_profiles AS profile
                LEFT JOIN student_documentation_subject_selections AS selection
                  ON selection.student_id = profile.student_id
                 AND selection.school_year_id = profile.school_year_id
                GROUP BY profile.student_id
                """
            ).fetchall()
        )
        return {
            "assignments": int(connection.execute(
                "SELECT COUNT(*) FROM student_school_year_assignments"
            ).fetchone()[0]),
            "catalog_active_assessable": len(catalog),
            "catalog_areas": len({(row[1], row[2]) for row in catalog}),
            "catalog_cmp000_rows": sum(
                str(row[0]).startswith("CMP-000") for row in catalog
            ),
            "catalog_domains": len({row[1] for row in catalog}),
            "catalog_first_id": str(catalog[0][0]) if catalog else "",
            "catalog_last_id": str(catalog[-1][0]) if catalog else "",
            "catalog_legacy_rows": sum(row[4] != "current" for row in catalog),
            "catalog_topics": len({(row[1], row[2], row[3]) for row in catalog}),
            "conference_drafts": int(connection.execute(
                "SELECT COUNT(*) FROM learning_conference_drafts"
            ).fetchone()[0]),
            "conference_pdf_artifacts": int(connection.execute(
                "SELECT COUNT(*) FROM learning_conference_pdf_artifacts"
            ).fetchone()[0]),
            "conference_revisions": int(connection.execute(
                "SELECT COUNT(*) FROM learning_conference_revisions"
            ).fetchone()[0]),
            "courses": int(connection.execute(
                "SELECT COUNT(*) FROM courses"
            ).fetchone()[0]),
            "document_types": sorted(
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT document_type FROM documents"
                ).fetchall()
            ),
            "documents": int(connection.execute(
                "SELECT COUNT(*) FROM documents"
            ).fetchone()[0]),
            "empty_custom_subject_profiles": profile_sizes.count(0),
            "foreign_key_violations": len(
                connection.execute("PRAGMA foreign_key_check").fetchall()
            ),
            "groups": int(connection.execute(
                "SELECT COUNT(*) FROM groups"
            ).fetchone()[0]),
            "observation_date_end": observation_range[1],
            "observation_date_start": observation_range[0],
            "observations": int(connection.execute(
                "SELECT COUNT(*) FROM observations"
            ).fetchone()[0]),
            "overfachlich_observations": {
                subject_id: int(connection.execute(
                    "SELECT COUNT(*) FROM observations WHERE subject_id = ?",
                    (subject_id,),
                ).fetchone()[0])
                for subject_id in COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS
            },
            "rating_tokens": [
                token for token in _CIPHER_RATING_TOKENS if token in rating_tokens
            ],
            "rating_tokens_social": tokens_for_subject(
                "selbst_sozialkompetenz"
            ),
            "rating_tokens_sport": tokens_for_subject("sport"),
            "rating_tokens_standard": tokens_for_subject(
                "arbeits_lernkompetenz"
            ),
            "report_drafts": int(connection.execute(
                "SELECT COUNT(*) FROM report_drafts"
            ).fetchone()[0]),
            "report_pdf_artifacts": int(connection.execute(
                "SELECT COUNT(*) FROM learning_report_pdf_artifacts"
            ).fetchone()[0]),
            "report_revisions": int(connection.execute(
                "SELECT COUNT(*) FROM learning_report_revisions"
            ).fetchone()[0]),
            "student_subject_profile_sizes": profile_sizes,
            "students": int(connection.execute(
                "SELECT COUNT(*) FROM students"
            ).fetchone()[0]),
            "teaching_subjects_observed": sorted(
                row[0]
                for row in connection.execute(
                    """
                    SELECT DISTINCT subject_id FROM observations
                    WHERE subject_id NOT IN (?, ?)
                    """,
                    tuple(COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS),
                ).fetchall()
            ),
            "timetable_entries": int(connection.execute(
                "SELECT COUNT(*) FROM timetable_entries"
            ).fetchone()[0]),
            "user_version": int(connection.execute(
                "PRAGMA user_version"
            ).fetchone()[0]),
        }


def _cipher_storage_inventory(paths) -> dict[str, object]:
    managed_files = tuple(paths.encrypted_document_storage.rglob("*.jkmedoc"))
    plaintext_payloads = 0
    for path in managed_files:
        payload = path.read_bytes()
        if (
            payload.startswith(b"%PDF")
            or b"Synthetisch" in payload
            or b"synthetisch" in payload
        ):
            plaintext_payloads += 1
    return {
        "managed_document_files": len(managed_files),
        "managed_plaintext_payloads": plaintext_payloads,
        "plaintext_pdf_files": len(tuple(paths.root.rglob("*.pdf"))),
        "plaintext_text_files": len(tuple(paths.root.rglob("*.txt"))),
    }


def _require_complete_cipher_comparison_inventory(
    inventory: dict[str, object],
    *,
    managed_documents: int,
    storage: dict[str, object],
) -> None:
    required_tokens = list(_CIPHER_RATING_TOKENS)
    if (
        inventory["user_version"] != 4
        or inventory["students"] != 24
        or inventory["groups"] != 3
        or inventory["courses"] != 3
        or inventory["assignments"] != 24
        or inventory["observations"] != 71
        or inventory["catalog_active_assessable"] != 331
        or inventory["catalog_first_id"] != "CMP-100001"
        or inventory["catalog_last_id"] != "CMP-100331"
        or inventory["catalog_domains"] != 12
        or inventory["catalog_areas"] != 48
        or inventory["catalog_topics"] != 81
        or inventory["catalog_cmp000_rows"] != 0
        or inventory["catalog_legacy_rows"] != 0
        or inventory["empty_custom_subject_profiles"] < 1
        or inventory["rating_tokens"] != required_tokens
        or inventory["rating_tokens_standard"] != required_tokens
        or inventory["rating_tokens_social"] != required_tokens
        or inventory["rating_tokens_sport"] != required_tokens
        or not set(_CIPHER_REQUIRED_TEACHING_SUBJECTS).issubset(
            set(inventory["teaching_subjects_observed"])
        )
        or inventory["report_drafts"] != 2
        or inventory["report_revisions"] != 1
        or inventory["report_pdf_artifacts"] != 1
        or inventory["conference_drafts"] != 2
        or inventory["conference_revisions"] != 1
        or inventory["conference_pdf_artifacts"] != 1
        or managed_documents != 7
        or storage["managed_document_files"] != managed_documents
        or storage["managed_plaintext_payloads"] != 0
        or storage["plaintext_pdf_files"] != 0
        or storage["plaintext_text_files"] != 0
        or inventory["foreign_key_violations"] != 0
    ):
        raise SeedDataError("Der synthetische Final-V4-Vergleichstestbestand ist unvollständig.")


def _cipher_pilot_password(root: Path) -> str:
    digest = hashlib.sha256(
        f"cipher-pilot-test-data:{Path(root).name}".encode("utf-8")
    ).hexdigest()
    return f"synthetic-only-{digest}"


def _require_fresh_cipher_test_root(root: Path) -> Path:
    candidate = Path(root).expanduser()
    if not candidate.is_absolute() or candidate.name.startswith("."):
        raise SeedDataError("Der Cipher-Testroot muss absolut und eindeutig benannt sein.")
    if candidate.exists() or candidate.is_symlink():
        raise SeedDataError("Der Cipher-Testroot muss vollständig neu sein.")
    parent = candidate.parent.resolve(strict=True)
    allowed_parents = {
        Path("/private/tmp").resolve(strict=True),
        Path(tempfile.gettempdir()).resolve(strict=True),
    }
    if parent not in allowed_parents or not candidate.name.startswith(
        CIPHER_PILOT_TEST_ROOT_PREFIX
    ):
        raise SeedDataError("Der Cipher-Testroot liegt nicht in der freigegebenen Temporärwurzel.")
    parent_status = parent.stat()
    private_temp_parent = bool(parent_status.st_mode & stat.S_ISVTX)
    if parent.is_symlink() or (
        parent_status.st_uid != os.getuid() and not private_temp_parent
    ):
        raise SeedDataError("Die Temporärwurzel besitzt keine sichere Identität.")
    return parent / candidate.name


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    if args.cipher_root is not None:
        if args.reset or args.database != SQLITE_SPIKE_PATH:
            print("Cipher-Testdaten nicht geschrieben: --reset/--database sind unzulässig.")
            return 2
        try:
            result = build_cipher_pilot_test_root(args.cipher_root)
        except SeedDataError as error:
            print(f"Cipher-Testdaten nicht geschrieben: {error}")
            return 1
        except Exception as error:
            code = str(getattr(error, "code", "cipher_pilot_seed_failed"))
            print(f"Cipher-Testdaten nicht geschrieben: {code}")
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
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
