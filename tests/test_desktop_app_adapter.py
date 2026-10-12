"""Tests for the experimental PySide6 desktop adapter."""

from __future__ import annotations

import inspect
import importlib
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from unittest import mock
from dataclasses import fields, replace
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QWidget,
)

from src.application.commands import (
    CreateObservationCommand,
    UpdateObservationCommand,
)
from src.application.dispatcher import SuccessResult
from src.core.constants import COURSE_ID_PREFIX, GROUP_ID_PREFIX, STUDENT_ID_PREFIX
from src.core.observation import ObservationCompetencyRatingRecord, ObservationRecord
from src.core.records import seed_reference_data
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteDocumentRepository,
    SQLiteObservationRepository,
    SQLiteStudentRepository,
    create_sqlite_seed_database,
)
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from src.desktop_app.adapters.master_data_desktop_adapter import MasterDataDesktopAdapter
from src.desktop_app.adapters import student_desktop_adapter
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.dialogs import app_info_dialog
from src.desktop_app.dialogs import dialog_buttons
from src.desktop_app.dialogs import master_data_dialog
from src.desktop_app.dialogs import new_student_dialog
from src.desktop_app.dialogs import new_observation_dialog
from src.desktop_app import components
from src.desktop_app import icons
from src.desktop_app import motion
from src.desktop_app.navigation import NAVIGATION_ITEMS, resolve_navigation_target
from src.desktop_app.screens import master_data_screen
from src.desktop_app.screens import overview_screen
from src.desktop_app.screens import settings_screen
from src.desktop_app.screens import student_profile_screen
from src.desktop_app.screens import students_screen
from src.desktop_app.screens import students_workspace
from src.desktop_app import assets
from src.desktop_app import main
from src.desktop_app import shell
from src.desktop_app import theme
from src.desktop_app.view_models.master_data_view_model import (
    COURSE_GROUP_EMPTY_COURSES_MESSAGE,
    COURSE_GROUP_DUPLICATE_NAME_MESSAGE,
    COURSE_GROUP_EMPTY_GROUPS_MESSAGE,
    COURSE_COLOR_OPTIONS,
    MASTER_DATA_EMPTY_NAME_MESSAGE,
    CourseGroupViewModel,
    MasterDataItemViewModel,
    MasterDataViewModel,
    course_color_from_key,
    normalize_master_data_name,
)
from src.desktop_app.view_models.observation_view_model import (
    OBSERVATION_ATTACHMENT_EMPTY_STATE,
    OBSERVATION_CONTEXT_OPTIONS,
    OBSERVATION_CROSS_SUBJECT_LABEL,
    DOCUMENT_TYPE_OPTIONS,
    ObservationAttachmentDraft,
    OBSERVATION_RATING_OPTIONS,
    OBSERVATION_SAVE_SUCCESS_MESSAGE,
    OBSERVATION_SAVE_VALIDATION_MESSAGE,
    ObservationCompetencyOptionViewModel,
    ObservationCompetencyRatingDraft,
    ObservationCompetencySubjectGroupViewModel,
    ObservationDraftViewModel,
    ObservationListItem,
    ObservationRatingViewModel,
    StudentCompetencyEvidenceViewModel,
    ObservationSubjectOptionViewModel,
    StudentDocumentationLearningAreaStatus,
    StudentDocumentationSubjectStatus,
    StudentCompetencyStatusViewModel,
    StudentCompetencySubjectGroup,
    StudentMissingCompetencyViewModel,
    build_student_competency_cockpit,
    calculated_rating_from_history,
    observation_rating_keys,
    rating_from_weighted_score,
)
from src.desktop_app.view_models.settings_view_model import (
    DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE,
    DocumentationSubjectOptionViewModel,
    SettingsViewModel,
)
from src.desktop_app.view_models.student_view_model import (
    PROFILE_ACTION_MESSAGES,
    PROFILE_SECTION_PLACEHOLDERS,
    REPORT_NO_OBSERVATIONS_MESSAGE,
    StudentDetailViewModel,
    StudentDocumentationSubjectOptionViewModel,
    StudentDocumentationSubjectProjectionViewModel,
    StudentDocumentViewModel,
    StudentProfileDashboardViewModel,
    StudentProfileOrientationChangeViewModel,
    StudentProfileOrientationEventViewModel,
    StudentProfileUndocumentedSubjectViewModel,
    StudentReportDevelopmentViewModel,
    StudentListItem,
    StudentReportCompetencyViewModel,
    StudentReportEvidenceViewModel,
    StudentReportPreviewViewModel,
    StudentReportSubjectSectionViewModel,
    build_student_profile_dashboard,
    build_student_profile_overview,
    documentation_summary_from_subjects,
    filter_student_list,
    format_student_report_preview_text,
    sort_student_list,
)
from tests.helpers.synthetic_v4 import create_synthetic_v4_database


def _create_empty_final_v4_database(database_path: Path) -> SQLiteDatabase:
    database = SQLiteDatabase(database_path)
    reference = seed_reference_data()
    database.replace_seed_data(
        replace(reference, students=(), assignments=())
    )
    return database


class DesktopAppAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "kompetenzmanager.sqlite"
        self.database = create_sqlite_seed_database(self.database_path)
        self.adapter = StudentDesktopAdapter(self.database_path)
        self.master_data_adapter = MasterDataDesktopAdapter(self.adapter)
        self.curriculum_adapter = CurriculumDesktopAdapter()
        self.math_time_competency_id = self._catalog_competency_id(
            "mathematik",
            "Ablesen, Einstellen und Aufschreiben der Uhrzeit",
        )
        self.math_addition_competency_id = self._catalog_competency_id(
            "mathematik",
            "Schriftliche Addition",
        )
        self.math_subtraction_competency_id = self._catalog_competency_id(
            "mathematik",
            "Schriftliche Subtraktion",
        )
        self.german_listening_competency_id = self._catalog_competency_id(
            "deutsch",
            "Wahrnehmen und Unterscheiden von Lauten",
        )
        self.german_word_competency_id = self._catalog_competency_id(
            "deutsch",
            "Wahrnehmen und Darstellen von Silben",
        )
        self.epu_competency_id = self._catalog_competency_id(
            "epu",
            "Selbstständige Arbeitsweise",
        )
        self.music_listening_competency_id = self._catalog_competency_id(
            "musik",
            "Gefühle und Stimmungen in der Musik erkennen und beschreiben",
        )
        self.math_first_competency_id = self._catalog_competency_id(
            "mathematik",
            "Bilden, Erfassen und Darstellen",
        )
        self.math_last_competency_id = self._catalog_competency_id(
            "mathematik",
            "Verwenden von Zeichen- und Messgeräten",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _catalog_competency_id(self, subject_key: str, competency_text: str) -> str:
        matches = tuple(
            entry.competency_id
            for entry in self.curriculum_adapter.list_entries()
            if entry.subject_key == subject_key
            and entry.competency_text == competency_text
        )
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_save_new_student_uses_application_stack(self) -> None:
        result = self.adapter.save_new_student(
            first_name="Jule",
            last_name="Schneider",
            group_id=f"{GROUP_ID_PREFIX}-000001",
            course_id=f"{COURSE_ID_PREFIX}-000001",
            student_notes="Liest gern.",
        )

        self.assertIsInstance(result, SuccessResult)
        student = result.value
        self.assertTrue(student.student_id.startswith("STD-"))

        stored_student = SQLiteStudentRepository(
            self.database,
            as_of=date(2026, 7, 13),
        ).get_student_by_id(student.student_id)
        self.assertIsNotNone(stored_student)
        self.assertEqual(stored_student.first_name, "Jule")
        self.assertEqual(
            len(
                SQLiteStudentRepository(
                    self.database,
                    as_of=date(2026, 7, 13),
                ).list_students()
            ),
            29,
        )

    def test_adapter_creates_create_observation_command(self) -> None:
        draft = self._sample_observation_draft()

        command = self.adapter.create_observation_command(draft)

        self.assertIsInstance(command, CreateObservationCommand)
        self.assertEqual(command.command_name, "observation.create")
        self.assertEqual(command.student_id, f"{STUDENT_ID_PREFIX}-000001")
        self.assertEqual(command.date, "2026-07-03")
        self.assertEqual(command.subject_id, "deutsch")
        self.assertEqual(command.context, "Leseübung")
        self.assertEqual(command.note, "Liest einen bekannten Text.")
        self.assertEqual(
            command.competency_ratings[0].competency_id,
            self.german_listening_competency_id,
        )
        self.assertEqual(command.competency_ratings[0].rating, "+")

    def test_save_observation_uses_application_stack_and_sqlite(self) -> None:
        result = self.adapter.save_observation(self._sample_observation_draft())

        self.assertIsInstance(result, SuccessResult)
        observation = result.value
        self.assertEqual(observation.observation_id, "OBS-000001")
        stored_observations = SQLiteObservationRepository(
            self.database
        ).list_observations_for_student(f"{STUDENT_ID_PREFIX}-000001")
        self.assertEqual(len(stored_observations), 1)
        self.assertEqual(stored_observations[0].competency_ratings[0].rating, "+")

    def test_normal_observation_without_competency_is_invalid(self) -> None:
        result = self.adapter.save_observation(
            self._sample_observation_draft(competency_ratings=())
        )

        self.assertFalse(result.success)
        self.assertIn("Mindestens eine Kompetenzbewertung", result.message)

    def test_quick_observation_without_competency_and_with_note_is_persisted(self) -> None:
        result = self.adapter.save_observation(
            self._sample_observation_draft(
                competency_ratings=(),
                is_quick_observation=True,
                note="Kurze Beobachtung ohne Kompetenzzuordnung.",
            )
        )

        self.assertTrue(result.success)
        stored = SQLiteObservationRepository(self.database).get_observation(
            result.value.observation_id
        )
        self.assertIsNotNone(stored)
        self.assertEqual(stored.competency_ratings, ())
        listed = self.adapter.list_observations_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        self.assertTrue(listed[0].is_quick_observation)

    def test_quick_observation_requires_non_whitespace_note(self) -> None:
        for note in ("", "   "):
            with self.subTest(note=repr(note)):
                result = self.adapter.save_observation(
                    self._sample_observation_draft(
                        competency_ratings=(),
                        is_quick_observation=True,
                        note=note,
                    )
                )
                self.assertFalse(result.success)
                self.assertIn("note darf nicht leer sein", result.message)

    def test_quick_observation_does_not_change_competency_projection(self) -> None:
        before = self.adapter.list_competency_status_projection_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        documentation_before = self.adapter.list_documentation_status_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        self.adapter.save_observation(
            self._sample_observation_draft(
                competency_ratings=(),
                is_quick_observation=True,
            )
        )
        after = self.adapter.list_competency_status_projection_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        documentation_after = self.adapter.list_documentation_status_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(after, before)
        self.assertEqual(documentation_after, documentation_before)

    def test_student_document_is_copied_and_metadata_survives_reload(self) -> None:
        source_path = Path(self.temp_dir.name) / "Foerderplan.pdf"
        source_path.write_text("PDF-Platzhalter", encoding="utf-8")

        document = self.adapter.add_student_document(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            source_path=source_path,
            document_type="Bericht",
            title="Foerderplan",
        )
        reloaded_adapter = StudentDesktopAdapter(self.database_path)
        reloaded_documents = reloaded_adapter.list_documents_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(document.document_type, "Bericht")
        self.assertEqual(document.title, "Foerderplan")
        self.assertTrue(Path(document.file_path).exists())
        self.assertIn("documents", Path(document.file_path).parts)
        self.assertEqual(len(reloaded_documents), 1)
        self.assertEqual(reloaded_documents[0].original_filename, "Foerderplan.pdf")

    def test_adapter_remove_document_hides_document_without_deleting_file(self) -> None:
        source_path = Path(self.temp_dir.name) / "Foerderplan.pdf"
        source_path.write_text("PDF-Platzhalter", encoding="utf-8")
        document = self.adapter.add_student_document(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            source_path=source_path,
            document_type="Bericht",
            title="Foerderplan",
        )
        stored_path = Path(document.file_path)

        self.adapter.remove_document(document.document_id)
        documents = self.adapter.list_documents_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(documents, ())
        self.assertTrue(stored_path.exists())

    def test_observation_can_save_attachment_metadata(self) -> None:
        source_path = Path(self.temp_dir.name) / "Arbeitsprobe.txt"
        source_path.write_text("Arbeitsprobe", encoding="utf-8")
        draft = self._sample_observation_draft(
            attachments=(
                ObservationAttachmentDraft(
                    str(source_path),
                    "Arbeitsprobe Lesen",
                    "Arbeitsprobe",
                    original_filename="Arbeitsprobe.txt",
                ),
            )
        )

        self.adapter.save_observation(draft)
        documents = self.adapter.list_documents_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        observations = self.adapter.list_observations_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].observation_id, "OBS-000001")
        self.assertEqual(documents[0].document_type, "Arbeitsprobe")
        self.assertEqual(len(observations[0].attachments), 1)
        self.assertEqual(observations[0].attachments[0].title, "Arbeitsprobe Lesen")

    def test_editing_observation_can_add_and_remove_attachments(self) -> None:
        first_path = Path(self.temp_dir.name) / "alt.txt"
        second_path = Path(self.temp_dir.name) / "neu.txt"
        first_path.write_text("alt", encoding="utf-8")
        second_path.write_text("neu", encoding="utf-8")
        self.adapter.save_observation(self._sample_observation_draft(
            attachments=(
                ObservationAttachmentDraft(
                    str(first_path),
                    "Alte Anlage",
                    "Sonstiges",
                    original_filename="alt.txt",
                ),
            )
        ))
        edit_draft = self.adapter.observation_draft_for_edit("OBS-000001")
        self.assertIsNotNone(edit_draft)
        updated_draft = self._sample_observation_draft(
            observation_id="OBS-000001",
            attachments=(
                ObservationAttachmentDraft(
                    str(second_path),
                    "Neue Anlage",
                    "Foto",
                    original_filename="neu.txt",
                ),
            ),
        )

        self.adapter.update_observation(updated_draft)
        documents = self.adapter.list_documents_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        observation_documents = SQLiteDocumentRepository(
            self.database
        ).list_documents_for_observation("OBS-000001")

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].title, "Neue Anlage")
        self.assertEqual(documents[0].document_type, "Foto")
        self.assertEqual(len(observation_documents), 1)
        self.assertEqual(observation_documents[0].original_filename, "neu.txt")

    def test_soft_deleted_observation_keeps_document_metadata_student_centered(self) -> None:
        source_path = Path(self.temp_dir.name) / "gespraech.txt"
        source_path.write_text("Gespräch", encoding="utf-8")
        self.adapter.save_observation(self._sample_observation_draft(
            attachments=(
                ObservationAttachmentDraft(
                    str(source_path),
                    "Gesprächsnotiz",
                    "Gesprächsnotiz",
                    original_filename="gespraech.txt",
                ),
            )
        ))

        self.adapter.delete_observation("OBS-000001")
        observations = self.adapter.list_observations_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        documents = self.adapter.list_documents_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(observations, ())
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].observation_id, "OBS-000001")

    def test_adapter_creates_update_observation_command(self) -> None:
        draft = self._sample_observation_draft(observation_id="OBS-000001")

        command = self.adapter.create_update_observation_command(draft)

        self.assertIsInstance(command, UpdateObservationCommand)
        self.assertEqual(command.command_name, "observation.update")
        self.assertEqual(command.observation_id, "OBS-000001")
        self.assertEqual(command.subject_id, "deutsch")

    def test_update_observation_updates_saved_data_and_replaces_ratings(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft())
        edit_draft = self._sample_observation_draft(
            observation_id="OBS-000001",
            date_text="2026-07-04",
            context="Präsentation",
            note="Aktualisierte Beobachtung.",
            competency_ratings=(
                self._sample_observation_rating(
                    self.epu_competency_id,
                    "epu",
                    "EPU",
                    "Natur und Umwelt",
                    "Erkunden und beschreiben",
                    "Naturphänomene beobachten und beschreiben",
                    "--",
                ),
            ),
        )

        result = self.adapter.update_observation(edit_draft)
        stored_observation = SQLiteObservationRepository(
            self.database
        ).get_observation("OBS-000001")

        self.assertIsInstance(result, SuccessResult)
        self.assertIsNotNone(stored_observation)
        self.assertEqual(stored_observation.date, "2026-07-04")
        self.assertEqual(stored_observation.subject_id, "epu")
        self.assertEqual(stored_observation.context, "Präsentation")
        self.assertEqual(stored_observation.note, "Aktualisierte Beobachtung.")
        self.assertEqual(
            tuple(rating.competency_id for rating in stored_observation.competency_ratings),
            (self.epu_competency_id,),
        )
        self.assertEqual(stored_observation.competency_ratings[0].rating, "--")

    def test_delete_observation_uses_soft_delete_and_hides_profile_item(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft())

        result = self.adapter.delete_observation("OBS-000001")
        stored_observation = SQLiteObservationRepository(
            self.database
        ).get_observation("OBS-000001")
        visible_observations = self.adapter.list_observations_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertIsInstance(result, SuccessResult)
        self.assertFalse(result.value.active)
        self.assertIsNotNone(stored_observation)
        self.assertFalse(stored_observation.active)
        self.assertEqual(visible_observations, ())

    def test_deleted_observation_does_not_affect_competency_overview(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft())
        self.assertTrue(self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        ))

        self.adapter.delete_observation("OBS-000001")
        groups = self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(groups, ())

    def test_update_multisubject_observation_recalculates_subject_label(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft())
        edit_draft = self._sample_observation_draft(
            observation_id="OBS-000001",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
                self._sample_observation_rating(
                    self.epu_competency_id,
                    "epu",
                    "EPU",
                    "Natur und Umwelt",
                    "Erkunden und beschreiben",
                    "Naturphänomene beobachten und beschreiben",
                    "-",
                ),
            ),
        )

        result = self.adapter.update_observation(edit_draft)
        observations = self.adapter.list_observations_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(result.value.subject_id, "cross_subject")
        self.assertEqual(observations[0].subject_display_name, OBSERVATION_CROSS_SUBJECT_LABEL)
        self.assertEqual(
            tuple(rating.subject_display_name for rating in observations[0].competency_ratings),
            ("EPU", "Deutsch"),
        )

    def test_observation_is_loaded_after_adapter_reinitialization(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft())

        reloaded_adapter = StudentDesktopAdapter(self.database_path)
        observations = reloaded_adapter.list_observations_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].student_id, f"{STUDENT_ID_PREFIX}-000001")
        self.assertEqual(observations[0].date_text, "2026-07-03")
        self.assertEqual(observations[0].subject_display_name, "Deutsch")
        self.assertEqual(observations[0].context, "Leseübung")
        self.assertEqual(observations[0].note, "Liest einen bekannten Text.")
        self.assertEqual(observations[0].competency_ratings[0].rating, "+")
        self.assertIn("Deutsch", observations[0].competency_ratings[0].display_label)

    def test_observation_subject_label_uses_single_competency_subject(self) -> None:
        draft = self._sample_observation_draft(
            subject_id="epu",
            subject_display_name="EPU",
        )

        command = self.adapter.create_observation_command(draft)
        self.adapter.save_observation(draft)
        observations = self.adapter.list_observations_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(command.subject_id, "deutsch")
        self.assertEqual(observations[0].subject_display_name, "Deutsch")
        self.assertNotEqual(observations[0].subject_display_name, "EPU")

    def test_observation_subject_label_marks_cross_subject_ratings(self) -> None:
        draft = self._sample_observation_draft(
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
                self._sample_observation_rating(
                    self.epu_competency_id,
                    "epu",
                    "EPU",
                    "Natur und Umwelt",
                    "Erkunden und beschreiben",
                    "Naturphänomene beobachten und beschreiben",
                    "-",
                ),
            ),
        )

        command = self.adapter.create_observation_command(draft)
        self.adapter.save_observation(draft)
        observations = self.adapter.list_observations_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(command.subject_id, "cross_subject")
        self.assertEqual(
            observations[0].subject_display_name,
            OBSERVATION_CROSS_SUBJECT_LABEL,
        )
        self.assertEqual(
            tuple(rating.subject_display_name for rating in observations[0].competency_ratings),
            ("EPU", "Deutsch"),
        )
        self.assertEqual(
            tuple(rating.rating for rating in observations[0].competency_ratings),
            ("-", "+"),
        )

    def test_observation_list_keeps_newest_observations_first(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-02",
            note="Aeltere Beobachtung.",
        ))
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            note="Neuere Beobachtung.",
        ))

        observations = self.adapter.list_observations_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(
            tuple(observation.date_text for observation in observations),
            ("2026-07-03", "2026-07-02"),
        )

    def test_student_adapter_seeds_competency_catalog_in_sqlite(self) -> None:
        competencies = SQLiteCompetencyRepository(self.database).list_competencies()

        self.assertGreater(len(competencies), 0)
        self.assertEqual(len(competencies), 331)
        self.assertEqual(competencies[0].competency_id, "CMP-100001")
        self.assertEqual(competencies[0].subject_id, "selbst_sozialkompetenz")
        self.assertEqual(competencies[0].subject_name, "Selbst- und Sozialkompetenz")
        self.assertTrue(all(not item.competency_id.startswith("CMP-000") for item in competencies))
        self.assertTrue(all(item.catalog_status == "current" for item in competencies))
        self.assertTrue(competencies[0].label)

    def test_documentation_subject_options_default_to_active_catalog_subjects(self) -> None:
        options = self.adapter.list_documentation_subject_options()

        self.assertGreater(len(options), 0)
        self.assertEqual(
            tuple(option.subject_id for option in options[:4]),
            (
                "selbst_sozialkompetenz",
                "arbeits_lernkompetenz",
                "epu",
                "deutsch",
            ),
        )
        self.assertIn(
            "Selbst- und Sozialkompetenz",
            tuple(option.label for option in options),
        )
        self.assertTrue(all(option.selected for option in options))

    def test_student_documentation_subject_selection_excludes_cross_curricular_domains(
        self,
    ) -> None:
        projection = self.adapter.student_profile_projection_bundle(
            f"{STUDENT_ID_PREFIX}-000001"
        ).documentation_subjects

        available_ids = tuple(
            subject.subject_id for subject in projection.available_subjects
        )
        self.assertEqual(
            available_ids,
            (
                "epu",
                "deutsch",
                "mathematik",
                "kreatives_gestalten",
                "sport",
                "ethik",
                "religion",
                "musik",
                "englisch",
                "schulgarten",
            ),
        )
        self.assertNotIn("selbst_sozialkompetenz", projection.selected_subject_ids)
        self.assertNotIn("arbeits_lernkompetenz", projection.selected_subject_ids)

    def test_save_active_documentation_subjects_updates_selected_options_only(
        self,
    ) -> None:
        competency_repository = SQLiteCompetencyRepository(self.database)
        active_by_competency = {
            competency.competency_id: competency.active
            for competency in competency_repository.list_competencies()
        }

        self.adapter.save_active_documentation_subjects(("epu", "deutsch"))
        options = self.adapter.list_documentation_subject_options()
        selected_subject_ids = tuple(
            option.subject_id for option in options if option.selected
        )
        active_after_save = {
            competency.competency_id: competency.active
            for competency in competency_repository.list_competencies()
        }

        self.assertEqual(selected_subject_ids, ("epu", "deutsch"))
        self.assertEqual(active_after_save, active_by_competency)

    def test_documentation_subject_selection_survives_adapter_reinitialization(
        self,
    ) -> None:
        self.adapter.save_active_documentation_subjects(("kreatives_gestalten",))

        reloaded_adapter = StudentDesktopAdapter(self.database_path)
        options = reloaded_adapter.list_documentation_subject_options()

        self.assertEqual(
            tuple(option.subject_id for option in options if option.selected),
            ("kreatives_gestalten",),
        )

    def test_observation_subject_options_use_documentation_subject_selection(
        self,
    ) -> None:
        student_id = f"{STUDENT_ID_PREFIX}-000001"
        self._save_custom_documentation_subjects(
            student_id,
            ("deutsch", "mathematik"),
        )

        options = self.adapter.list_observation_subject_options(student_id)

        self.assertEqual(
            tuple(option.subject_key for option in options if option.is_primary),
            (
                "selbst_sozialkompetenz",
                "arbeits_lernkompetenz",
                "deutsch",
                "mathematik",
            ),
        )
        self.assertEqual(
            tuple(
                option.subject_key
                for option in options
                if not option.is_primary
            ),
            (
                "epu",
                "kreatives_gestalten",
                "sport",
                "ethik",
                "religion",
                "musik",
                "englisch",
                "schulgarten",
            ),
        )

    def test_observation_subject_options_keep_cross_curricular_primary_for_empty_custom(
        self,
    ) -> None:
        student_id = f"{STUDENT_ID_PREFIX}-000001"
        self._save_custom_documentation_subjects(student_id, ())

        options = self.adapter.list_observation_subject_options(student_id)

        self.assertEqual(
            tuple(option.subject_key for option in options if option.is_primary),
            ("selbst_sozialkompetenz", "arbeits_lernkompetenz"),
        )
        self.assertEqual(
            tuple(option.subject_key for option in options if not option.is_primary),
            (
                "epu",
                "deutsch",
                "mathematik",
                "kreatives_gestalten",
                "sport",
                "ethik",
                "religion",
                "musik",
                "englisch",
                "schulgarten",
            ),
        )

    def test_observation_subject_options_default_to_active_catalog_subjects(
        self,
    ) -> None:
        options = self.adapter.list_observation_subject_options(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        expected_subject_ids = tuple(
            option.subject_id
            for option in self.adapter.list_documentation_subject_options()
        )

        self.assertEqual(
            tuple(option.subject_key for option in options),
            expected_subject_ids,
        )
        self.assertIn(
            "selbst_sozialkompetenz",
            {option.subject_key for option in options},
        )
        self.assertTrue(all(option.is_primary for option in options))

    def test_competency_cockpit_keeps_cross_curricular_for_empty_custom(
        self,
    ) -> None:
        student_id = f"{STUDENT_ID_PREFIX}-000001"
        self._save_custom_documentation_subjects(student_id, ())

        cockpit = self.adapter.competency_cockpit_for_student(student_id)

        self.assertEqual(
            tuple(subject.subject_id for subject in cockpit.subjects),
            ("selbst_sozialkompetenz", "arbeits_lernkompetenz"),
        )

    def test_competency_cockpit_combines_cross_curricular_and_effective_subjects(
        self,
    ) -> None:
        student_id = f"{STUDENT_ID_PREFIX}-000001"
        self._save_custom_documentation_subjects(
            student_id,
            ("deutsch", "sport", "englisch"),
        )

        cockpit = self.adapter.competency_cockpit_for_student(student_id)

        self.assertEqual(
            tuple(subject.subject_id for subject in cockpit.subjects),
            (
                "selbst_sozialkompetenz",
                "arbeits_lernkompetenz",
                "deutsch",
                "sport",
                "englisch",
            ),
        )

    def test_observation_subject_options_keep_initial_additional_subject(
        self,
    ) -> None:
        student_id = f"{STUDENT_ID_PREFIX}-000001"
        self._save_custom_documentation_subjects(
            student_id,
            ("deutsch", "mathematik"),
        )
        initial_draft = self._sample_observation_draft(
            subject_id="musik",
            subject_display_name="Musik",
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000025",
                    "musik",
                    "Musik",
                    "Musik wahrnehmen",
                    "Hoeren und beschreiben",
                    "Musikalische Eindruecke beschreiben",
                    "+",
                ),
            ),
        )

        options = self.adapter.list_observation_subject_options(
            student_id,
            initial_draft,
        )
        music_options = tuple(
            option for option in options if option.subject_key == "musik"
        )

        self.assertEqual(len(music_options), 1)
        self.assertEqual(music_options[0].display_name, "Musik")
        self.assertFalse(music_options[0].is_primary)

    def obsolete_observation_competency_hierarchy_defaults_to_active_catalog_subjects(
        self,
    ) -> None:
        groups = self.adapter.list_observation_competency_subject_groups(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        expected_subject_ids = tuple(
            option.subject_id
            for option in self.adapter.list_documentation_subject_options()
        )

        self.assertEqual(
            tuple(group.subject_key for group in groups),
            expected_subject_ids,
        )
        self.assertTrue(all(group.learning_area_groups for group in groups))
        self.assertTrue(all(
            isinstance(group, ObservationCompetencySubjectGroupViewModel)
            for group in groups
        ))
        self.assertIsNone(
            self._find_observation_competency_option(groups, self.music_listening_competency_id)
        )

    def test_observation_competency_hierarchy_covers_primary_and_additional_subjects(
        self,
    ) -> None:
        student_id = f"{STUDENT_ID_PREFIX}-000001"
        self._save_custom_documentation_subjects(
            student_id,
            ("deutsch", "mathematik"),
        )

        groups = self.adapter.list_observation_competency_subject_groups(
            student_id
        )
        options = self.adapter.list_observation_subject_options(student_id)

        self.assertEqual(
            tuple(group.subject_key for group in groups),
            tuple(option.subject_key for option in options),
        )
        self.assertIn("epu", {group.subject_key for group in groups})
        self.assertIn("deutsch", {group.subject_key for group in groups})

    def obsolete_observation_competency_hierarchy_contains_concrete_math_time_competency(
        self,
    ) -> None:
        groups = self.adapter.list_observation_competency_subject_groups(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        competency = self._find_observation_competency_option(groups, self.math_time_competency_id)
        subject_group = self._observation_subject_group(groups, "mathematik")

        self.assertIsNotNone(subject_group)
        self.assertIsNotNone(competency)
        self.assertEqual(subject_group.subject_display_name, "Mathematik")
        if competency is not None:
            self.assertEqual(competency.subject_key, "mathematik")
            self.assertEqual(
                competency.learning_area,
                "Größenvorstellungen nutzen und mit Größen umgehen",
            )
            self.assertEqual(competency.competency_group, "Zeit")
            self.assertEqual(
                competency.competency_text,
                "Ablesen, Einstellen und Aufschreiben der Uhrzeit",
            )
            self.assertEqual(competency.competency_label, "Minutengenau ablesen")

    def test_observation_competency_hierarchy_preserves_catalog_sort_order(
        self,
    ) -> None:
        groups = self.adapter.list_observation_competency_subject_groups(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        for subject in groups:
            area_orders = [
                min(
                    competency.sort_order
                    for topic in area.competency_groups
                    for competency in topic.competencies
                )
                for area in subject.learning_area_groups
            ]
            self.assertEqual(area_orders, sorted(area_orders))
            for area in subject.learning_area_groups:
                topic_orders = [
                    min(competency.sort_order for competency in topic.competencies)
                    for topic in area.competency_groups
                ]
                self.assertEqual(topic_orders, sorted(topic_orders))
                for topic in area.competency_groups:
                    competency_order = [
                        (competency.sort_order, competency.competency_id)
                        for competency in topic.competencies
                    ]
                    self.assertEqual(competency_order, sorted(competency_order))

    def obsolete_observation_competency_hierarchy_keeps_replaced_math_time_snapshot(
        self,
    ) -> None:
        initial_draft = self._sample_observation_draft(
            subject_id="mathematik",
            subject_display_name="Mathematik",
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000318",
                    "mathematik",
                    "Mathematik",
                    "Größenvorstellungen nutzen und mit Größen umgehen",
                    "Zeit",
                    "Uhrzeiten ablesen, einstellen, notieren und auf verschiedene Weise benennen.",
                    "+",
                ),
            ),
        )

        groups = self.adapter.list_observation_competency_subject_groups(
            f"{STUDENT_ID_PREFIX}-000001",
            initial_draft,
        )
        competency = self._find_observation_competency_option(groups, "CMP-000318")

        self.assertIsNotNone(competency)
        if competency is not None:
            self.assertTrue(competency.selected)
            self.assertEqual(competency.rating, "+")
            self.assertEqual(competency.catalog_status, "legacy")
            self.assertFalse(competency.is_active)
            self.assertEqual(
                competency.competency_text,
                "Uhrzeiten ablesen, einstellen, notieren und auf verschiedene Weise benennen.",
            )

    def obsolete_observation_competency_hierarchy_keeps_current_deutsch_competency(
        self,
    ) -> None:
        groups = self.adapter.list_observation_competency_subject_groups(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        competency = self._find_observation_competency_option(groups, self.german_listening_competency_id)

        self.assertIsNotNone(competency)
        if competency is not None:
            self.assertEqual(competency.subject_key, "deutsch")
            self.assertEqual(competency.subject_display_name, "Deutsch")
            self.assertEqual(competency.catalog_status, "current")
            self.assertTrue(competency.is_active)
            self.assertEqual(
                competency.competency_text,
                "Wörter, Sätze sowie literarische und nicht literarische "
                "altersgemäße Texte sinnverstehend lesen",
            )

    def obsolete_observation_competency_hierarchy_marks_initial_draft_rating(
        self,
    ) -> None:
        initial_draft = self._sample_observation_draft(
            subject_id="mathematik",
            subject_display_name="Mathematik",
            competency_ratings=(
                self._sample_observation_rating(
                    self.math_time_competency_id,
                    "mathematik",
                    "Mathematik",
                    "Größenvorstellungen nutzen und mit Größen umgehen",
                    "Zeit",
                    "Ablesen, Einstellen und Aufschreiben der Uhrzeit",
                    "++",
                ),
            ),
        )

        groups = self.adapter.list_observation_competency_subject_groups(
            f"{STUDENT_ID_PREFIX}-000001",
            initial_draft
        )
        selected = self._find_observation_competency_option(groups, self.math_time_competency_id)
        unselected = self._find_observation_competency_option(groups, "CMP-000319")

        self.assertIsNotNone(selected)
        if selected is not None:
            self.assertTrue(selected.selected)
            self.assertEqual(selected.rating, "++")
        self.assertIsNotNone(unselected)
        if unselected is not None:
            self.assertFalse(unselected.selected)
            self.assertEqual(unselected.rating, "")

    def obsolete_observation_competency_hierarchy_keeps_initial_non_documentation_subject(
        self,
    ) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))
        legacy_competency = next(
            competency
            for competency in CurriculumDesktopAdapter(
                database=self.database
            ).list_entries()
            if competency.competency_id == self.music_listening_competency_id
        )
        self.assertEqual(legacy_competency.catalog_status, "legacy")
        self.assertFalse(legacy_competency.is_active)
        initial_draft = self._sample_observation_draft(
            subject_id="musik",
            subject_display_name="Musik",
            competency_ratings=(
                self._sample_observation_rating(
                    self.music_listening_competency_id,
                    "musik",
                    "Musik",
                    "Musik hören",
                    "Allgemein",
                    "Musik aufmerksam hören, Eindrücke beschreiben und "
                    "musikalische Merkmale erkennen",
                    "+",
                ),
            ),
        )

        groups = self.adapter.list_observation_competency_subject_groups(
            f"{STUDENT_ID_PREFIX}-000001",
            initial_draft
        )
        music_group = self._observation_subject_group(groups, "musik")
        selected = self._find_observation_competency_option(groups, self.music_listening_competency_id)

        self.assertEqual(
            tuple(group.subject_key for group in groups),
            ("deutsch", "mathematik", "musik"),
        )
        self.assertIsNotNone(music_group)
        if music_group is not None:
            self.assertEqual(
                music_group.subject_display_name,
                "Musik (nicht dokumentationsrelevant)",
            )
        self.assertIsNotNone(selected)
        if selected is not None:
            self.assertTrue(selected.selected)
            self.assertEqual(selected.rating, "+")
            self.assertEqual(selected.catalog_status, "legacy")
            self.assertFalse(selected.is_active)

    def obsolete_recent_observation_competencies_are_newest_distinct_and_limited(self) -> None:
        for date_text, competency_ratings in (
            ("2026-07-01", (self._recent_rating(self.german_listening_competency_id),)),
            ("2026-07-02", (
                self._recent_rating(self.math_time_competency_id),
                self._recent_rating(self.math_addition_competency_id),
            )),
            ("2026-07-03", (
                self._recent_rating(self.math_subtraction_competency_id),
                self._recent_rating(self.math_time_competency_id),
            )),
            ("2026-07-04", (self._recent_rating("CMP-000319"),)),
        ):
            self.adapter.save_observation(self._sample_observation_draft(
                date_text=date_text,
                competency_ratings=competency_ratings,
            ))

        recent = self.adapter.list_recent_observation_competencies(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(
            tuple(competency.competency_id for competency in recent),
            ("CMP-000319", self.math_subtraction_competency_id, self.math_time_competency_id, self.math_addition_competency_id),
        )

    def obsolete_recent_observation_competencies_filter_legacy_and_inactive_catalog_rows(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            competency_ratings=(
                self._sample_observation_rating(
                    self.music_listening_competency_id, "musik", "Musik", "Musik hören",
                    "Allgemein", "Gefühle und Stimmungen in der Musik erkennen und beschreiben", "+",
                ),
                self._recent_rating(self.math_time_competency_id),
            ),
        ))

        recent = self.adapter.list_recent_observation_competencies(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(
            tuple(competency.competency_id for competency in recent),
            (self.math_time_competency_id,),
        )
        self.assertTrue(all(competency.is_active for competency in recent))
        self.assertTrue(all(competency.catalog_status == "current" for competency in recent))

    def test_recent_observation_competencies_update_from_successful_save(self) -> None:
        student_id = f"{STUDENT_ID_PREFIX}-000001"
        self.assertEqual(self.adapter.list_recent_observation_competencies(student_id), ())

        result = self.adapter.save_observation(self._sample_observation_draft(
            competency_ratings=(self._recent_rating(self.math_time_competency_id),),
        ))

        self.assertIsInstance(result, SuccessResult)
        self.assertEqual(
            tuple(
                competency.competency_id
                for competency in self.adapter.list_recent_observation_competencies(student_id)
            ),
            (self.math_time_competency_id,),
        )

    def test_recent_observation_competency_projection_has_no_write_path(self) -> None:
        source = inspect.getsource(
            StudentDesktopAdapter.list_recent_observation_competencies
        )

        self.assertIn("list_observations_for_student", source)
        self.assertNotIn(".dispatch(", source)
        self.assertNotIn("save_", source)
        self.assertNotIn("update_", source)

    def test_settings_screen_shows_documentation_subject_checkboxes_and_saves(
        self,
    ) -> None:
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)
        screen = settings_screen.SettingsScreen()
        emitted_subject_ids: list[tuple[str, ...]] = []
        screen.documentation_subjects_save_requested.connect(
            emitted_subject_ids.append
        )

        screen.set_settings(
            SettingsViewModel(
                (
                    DocumentationSubjectOptionViewModel("deutsch", "Deutsch", True),
                    DocumentationSubjectOptionViewModel("musik", "Musik", False),
                )
            )
        )
        music_checkbox = screen.findChild(
            QCheckBox,
            "DocumentationSubjectCheckbox_musik",
        )
        save_button = screen.findChild(QPushButton, "DocumentationSubjectSaveButton")
        self.assertIsNotNone(music_checkbox)
        self.assertIsNotNone(save_button)

        if music_checkbox is not None:
            music_checkbox.setChecked(True)
        if save_button is not None:
            save_button.click()
        screen.show_documentation_subjects_saved()
        status_label = screen.findChild(QLabel, "SettingsStatusLabel")

        self.assertIsNotNone(status_label)
        self.assertEqual(emitted_subject_ids, [("deutsch", "musik")])
        if status_label is not None:
            self.assertEqual(
                status_label.text(),
                DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE,
            )

    def obsolete_student_adapter_upserts_catalog_without_removing_local_competencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            database = create_sqlite_seed_database(database_path)
            with database.connect() as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO competencies (
                            competency_id,
                            subject_id,
                            subject_name,
                            label,
                            description,
                            learning_area,
                            competency_group,
                            sort_order,
                            active,
                            is_core_subject
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "CMP-999999",
                            "eigener_bereich",
                            "Eigener Bereich",
                            "Eigene Kompetenz",
                            "Eigene Beschreibung",
                            "Eigene Kompetenz",
                            "Eigene Gruppe",
                            0,
                            1,
                            1,
                        ),
                    )

            StudentDesktopAdapter(database_path)
            competencies = SQLiteCompetencyRepository(database).list_competencies()
            competencies_by_id = {
                competency.competency_id: competency
                for competency in competencies
            }

        self.assertIn("CMP-999999", competencies_by_id)
        self.assertEqual(
            competencies_by_id["CMP-999999"].label,
            "Eigene Kompetenz",
        )
        self.assertIn("CMP-000059", competencies_by_id)
        self.assertIn("CMP-000212", competencies_by_id)
        self.assertEqual(
            len({competency.competency_id for competency in competencies}),
            len(competencies),
        )

    def test_competency_overview_resolves_labels_from_sqlite(self) -> None:
        with self.database.connect() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE competencies
                    SET label = ?
                    WHERE competency_id = ?
                    """,
                    ("SQLite-Lesekompetenz", self.german_listening_competency_id),
                )
        self.adapter.save_observation(self._sample_observation_draft(
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Leseverstehen",
                    "Sinnverstehendes Lesen",
                    "Wörter, Sätze sowie literarische und nicht literarische "
                    "altersgemäße Texte sinnverstehend lesen",
                    "+",
                ),
            ),
        ))

        groups = self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        competencies = [
            competency
            for group in groups
            for competency in group.competencies
        ]

        self.assertIn(
            "SQLite-Lesekompetenz",
            {competency.competency_label for competency in competencies},
        )

    def test_competency_overview_groups_by_subject_and_calculates_current_status(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-01",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "-",
                ),
            ),
        ))
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
                self._sample_observation_rating(
                    self.epu_competency_id,
                    "epu",
                    "EPU",
                    "Raum und Zeit",
                    "Orientierung in Raum und Zeit",
                    "Sich in vertrauten Räumen orientieren",
                    "++",
                ),
            ),
        ))

        groups = self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        group_by_subject = {group.subject_display_name: group for group in groups}
        deutsch_status = group_by_subject["Deutsch"].competencies[0]
        epu_status = group_by_subject["EPU"].competencies[0]

        self.assertEqual(deutsch_status.rating, "+")
        self.assertEqual(deutsch_status.rating_label, "Kenntnisse meist anwenden")
        self.assertEqual(deutsch_status.rating_history, ("-", "+"))
        self.assertEqual(deutsch_status.rating_history_label, "- → +")
        self.assertEqual(deutsch_status.observation_count, 2)
        self.assertEqual(deutsch_status.observation_count_label, "2 Beobachtungen")
        self.assertEqual(deutsch_status.last_observation_date, "2026-07-03")
        self.assertEqual(epu_status.rating, "++")
        self.assertEqual(epu_status.rating_history, ("++",))
        self.assertEqual(epu_status.observation_count_label, "1 Beobachtung")
        self.assertEqual(epu_status.last_observation_date, "2026-07-03")

    def test_competency_status_weighting_keeps_older_observations_in_score(self) -> None:
        rating, score = calculated_rating_from_history(("++", "--"))

        self.assertEqual(rating, "+")
        self.assertAlmostEqual(score, 1.7647058824)

    def test_competency_status_weighting_prioritizes_newer_observations(self) -> None:
        newer_positive, newer_positive_score = calculated_rating_from_history(("++", "--"))
        newer_negative, newer_negative_score = calculated_rating_from_history(("--", "++"))

        self.assertEqual(newer_positive, "+")
        self.assertEqual(newer_negative, "-")
        self.assertGreater(newer_positive_score, newer_negative_score)

    def test_competency_status_thresholds_map_to_rating_tokens(self) -> None:
        self.assertEqual(rating_from_weighted_score(0.74), "--")
        self.assertEqual(rating_from_weighted_score(0.75), "-")
        self.assertEqual(rating_from_weighted_score(1.49), "-")
        self.assertEqual(rating_from_weighted_score(1.50), "+")
        self.assertEqual(rating_from_weighted_score(2.49), "+")
        self.assertEqual(rating_from_weighted_score(2.50), "++")

    def test_profile_dashboard_limits_real_changes_and_uses_curricular_tie_order(
        self,
    ) -> None:
        statuses = tuple(
            self._cockpit_status(
                f"CMP-TEST-{index}",
                f"Kompetenz {index}",
                sort_order=sort_order,
                observation_count=2,
                evidence=(
                    StudentCompetencyEvidenceViewModel(
                        f"OBS-{index}-1", "2026-01-10", "-", "mathematik",
                        "Mathematik", "Größen und Messen", "Zeit",
                        f"Kompetenz {index}", "Unterricht",
                    ),
                    StudentCompetencyEvidenceViewModel(
                        f"OBS-{index}-2", change_date, "+", "mathematik",
                        "Mathematik", "Größen und Messen", "Zeit",
                        f"Kompetenz {index}", "Lernzielkontrolle",
                    ),
                ),
            )
            for index, sort_order, change_date in (
                (1, 30, "2026-07-10"),
                (2, 10, "2026-07-10"),
                (3, 20, "2026-07-10"),
                (4, 5, "2026-07-01"),
            )
        )

        dashboard = build_student_profile_dashboard(
            statuses,
            (),
            date(2026, 7, 14),
        )

        self.assertEqual(
            tuple(change.competency_id for change in dashboard.orientation_changes),
            ("CMP-TEST-2", "CMP-TEST-3", "CMP-TEST-1"),
        )

    def test_profile_dashboard_uses_cutoff_and_never_interpolates(self) -> None:
        changed = self._cockpit_status(
            "CMP-TEST-1",
            "Zeitspannen bestimmen",
            sort_order=1,
            observation_count=3,
            evidence=(
                StudentCompetencyEvidenceViewModel(
                    "OBS-3", "2026-12-01", "++", "mathematik", "Mathematik",
                    "Größen und Messen", "Zeit", "Zeitspannen bestimmen", "Test",
                ),
                StudentCompetencyEvidenceViewModel(
                    "OBS-2", "2026-06-01", "+", "mathematik", "Mathematik",
                    "Größen und Messen", "Zeit", "Zeitspannen bestimmen", "Projekt",
                ),
                StudentCompetencyEvidenceViewModel(
                    "OBS-1", "2026-01-01", "-", "mathematik", "Mathematik",
                    "Größen und Messen", "Zeit", "Zeitspannen bestimmen", "Unterricht",
                ),
            ),
        )
        unchanged = self._cockpit_status(
            "CMP-TEST-2",
            "Uhrzeiten lesen",
            sort_order=2,
            observation_count=2,
            evidence=(
                StudentCompetencyEvidenceViewModel(
                    "OBS-5", "2026-05-01", "+", "mathematik", "Mathematik",
                    "Größen und Messen", "Zeit", "Uhrzeiten lesen", "Unterricht",
                ),
                StudentCompetencyEvidenceViewModel(
                    "OBS-4", "2026-03-01", "+", "mathematik", "Mathematik",
                    "Größen und Messen", "Zeit", "Uhrzeiten lesen", "Unterricht",
                ),
            ),
        )

        dashboard = build_student_profile_dashboard(
            (changed, unchanged),
            (),
            date(2026, 7, 14),
        )

        self.assertEqual(len(dashboard.orientation_changes), 1)
        change = dashboard.orientation_changes[0]
        self.assertEqual(change.previous_rating, "-")
        self.assertEqual(change.new_rating, "+")
        self.assertEqual(change.period_label, "01.01.2026 – 01.06.2026")
        self.assertEqual(change.triggering_event.reference_id, "OBS-2")
        self.assertNotIn("2026-12-01", change.triggering_event.evidence_label)

    def test_profile_dashboard_cutoff_excludes_future_documentation(self) -> None:
        future_only = self._cockpit_status(
            "CMP-TEST-FUTURE",
            "Künftige Beobachtung",
            learning_area="Größen und Messen",
            observation_count=1,
            evidence=(StudentCompetencyEvidenceViewModel(
                "OBS-FUTURE", "2026-12-01", "+", "mathematik", "Mathematik",
                "Größen und Messen", "Zeit", "Künftige Beobachtung", "Test",
            ),),
        )
        documentation_statuses = (StudentDocumentationSubjectStatus(
            "mathematik",
            "Mathematik",
            1,
            1,
            (),
            0,
            (StudentDocumentationLearningAreaStatus(
                "Größen und Messen", 1, 1,
            ),),
        ),)

        dashboard = build_student_profile_dashboard(
            (future_only,),
            documentation_statuses,
            date(2026, 7, 14),
        )

        self.assertEqual(
            dashboard.documentation_summary.documented_learning_area_count,
            0,
        )
        self.assertEqual(
            dashboard.documentation_summary.total_learning_area_count,
            1,
        )
        self.assertEqual(dashboard.undocumented_count, 1)
        self.assertEqual(
            dashboard.undocumented_subjects[0].subject_display_name,
            "Mathematik",
        )

    def test_profile_dashboard_keeps_confirmation_and_historical_evidence(self) -> None:
        status = self._cockpit_status(
            "CMP-HIST-1",
            "Zeitspannen bestimmen (alter Katalogstand)",
            sort_order=1,
            observation_count=1,
            confirmed_rating="+",
            confirmed_at="2026-06-12T09:00:00+00:00",
            historical=True,
            evidence=(
                StudentCompetencyEvidenceViewModel(
                    "OBS-HIST-1", "2026-02-01", "-", "mathematik",
                    "Mathematik", "Größen und Messen", "Zeit",
                    "Zeitspannen bestimmen (alter Katalogstand)", "Unterricht",
                ),
            ),
        )

        dashboard = build_student_profile_dashboard(
            (status,),
            (),
            date(2026, 7, 14),
        )

        change = dashboard.orientation_changes[0]
        self.assertTrue(change.historical)
        self.assertEqual(change.triggering_event.source, "confirmation")
        self.assertEqual(change.triggering_event.source_label, "Kompetenz bestätigt")
        self.assertEqual(change.previous_rating, "-")
        self.assertEqual(change.new_rating, "+")

    def test_profile_dashboard_adapter_projects_real_observation_events(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-02-01",
            competency_ratings=(self._sample_observation_rating(
                self.german_listening_competency_id, "deutsch", "Deutsch",
                "Mit Texten und Medien umgehen", "Lesen und Verstehen",
                "Texte lesen und zentrale Informationen entnehmen", "-",
            ),),
        ))
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-06-01",
            competency_ratings=(self._sample_observation_rating(
                self.german_listening_competency_id, "deutsch", "Deutsch",
                "Mit Texten und Medien umgehen", "Lesen und Verstehen",
                "Texte lesen und zentrale Informationen entnehmen", "+",
            ),),
        ))

        dashboard = self.adapter.student_profile_dashboard_for_student(
            f"{STUDENT_ID_PREFIX}-000001",
            as_of=date(2026, 7, 14),
        )
        documentation_statuses = self.adapter.list_documentation_status_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        change = next(
            item
            for item in dashboard.orientation_changes
            if item.competency_id == self.german_listening_competency_id
        )
        self.assertEqual(change.previous_rating, "-")
        self.assertEqual(change.new_rating, "+")
        self.assertEqual(change.triggering_event.reference_id, "OBS-000002")
        self.assertEqual(
            dashboard.documentation_summary.total_learning_area_count,
            sum(len(status.learning_area_statuses) for status in documentation_statuses),
        )
        self.assertEqual(
            dashboard.documentation_summary.documented_learning_area_count,
            sum(
                area.documented_count > 0
                for status in documentation_statuses
                for area in status.learning_area_statuses
            ),
        )

    def test_deleted_observation_is_excluded_from_calculated_competency_status(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-01",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "--",
                ),
            ),
        ))
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "++",
                ),
            ),
        ))
        self.adapter.delete_observation("OBS-000002")

        groups = self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        status = groups[0].competencies[0]

        self.assertEqual(status.rating, "--")
        self.assertEqual(status.rating_history, ("--",))
        self.assertEqual(status.observation_count, 1)
        self.assertEqual(status.last_observation_date, "2026-07-01")

    def test_competency_confirmation_can_adopt_proposal_and_persists_after_reload(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
            ),
        ))
        status = self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )[0].competencies[0]

        confirmation = self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=status.competency_id,
            confirmed_rating=status.rating,
        )
        reloaded_adapter = StudentDesktopAdapter(self.database_path)
        reloaded_status = reloaded_adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )[0].competencies[0]
        observations = SQLiteObservationRepository(
            self.database
        ).list_observations_for_student(f"{STUDENT_ID_PREFIX}-000001")

        self.assertEqual(confirmation.student_id, f"{STUDENT_ID_PREFIX}-000001")
        self.assertEqual(confirmation.competency_id, self.german_listening_competency_id)
        self.assertEqual(confirmation.confirmed_rating, "+")
        self.assertTrue(confirmation.confirmed_at)
        self.assertEqual(reloaded_status.rating, "+")
        self.assertEqual(reloaded_status.confirmed_rating, "+")
        self.assertEqual(
            reloaded_status.confirmation_status_label,
            "aus Beobachtungen abgeleitet: + · von Laura bestätigt: +",
        )
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].competency_ratings[0].rating, "+")

    def test_competency_confirmation_can_manually_override_proposal(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "-",
                ),
            ),
        ))

        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="+",
            note="Lehrkraft entscheidet nach Gespräch.",
        )
        status = self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )[0].competencies[0]

        self.assertEqual(status.rating, "-")
        self.assertEqual(status.confirmed_rating, "+")
        self.assertEqual(status.confirmation_note, "Lehrkraft entscheidet nach Gespräch.")
        self.assertEqual(
            status.confirmation_status_label,
            "aus Beobachtungen abgeleitet: - · von Laura bestätigt: +",
        )

    def test_new_observation_updates_proposal_but_not_confirmed_status(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
            ),
        ))
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="+",
        )
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-04",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "-",
                ),
            ),
        ))

        status = self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )[0].competencies[0]

        self.assertEqual(status.rating, "-")
        self.assertEqual(status.confirmed_rating, "+")
        self.assertEqual(
            status.confirmation_status_label,
            "aus Beobachtungen abgeleitet: - · von Laura bestätigt: +",
        )

    def test_competency_overview_shows_confirmed_status_without_active_observation(self) -> None:
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="+",
            note="im Lerngespraech bestaetigt",
        )

        groups = self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        deutsch_group = next(
            group for group in groups if group.subject_display_name == "Deutsch"
        )
        status = next(
            competency
            for competency in deutsch_group.competencies
            if competency.competency_id == self.german_listening_competency_id
        )

        self.assertEqual(status.rating, "+")
        self.assertEqual(status.confirmed_rating, "+")
        self.assertEqual(status.rating_history, ())
        self.assertEqual(status.observation_count, 0)
        self.assertEqual(status.confirmation_note, "im Lerngespraech bestaetigt")
        self.assertEqual(status.confirmation_status_label, "von Laura bestätigt: +")
        self.assertNotIn(
            self.german_listening_competency_id,
            {competency.competency_id for competency in deutsch_group.missing_competencies},
        )

    def test_report_preview_uses_confirmation_without_active_observation(self) -> None:
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="+",
        )

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        deutsch_section = next(
            section
            for section in preview.subject_sections
            if section.subject_display_name == "Deutsch"
        )

        self.assertEqual(deutsch_section.strengths[0].rating, "+")
        self.assertEqual(
            deutsch_section.strengths[0].rating_source,
            "von Laura bestätigt",
        )
        self.assertEqual(deutsch_section.current_statuses[0].rating, "+")
        self.assertEqual(
            deutsch_section.current_statuses[0].rating_source,
            "von Laura bestätigt",
        )
        self.assertEqual(
            deutsch_section.current_statuses[0].display_label,
            "Wahrnehmen und Unterscheiden von Lauten · "
            "Aktueller Stand: Kenntnisse meist anwenden · von Laura bestätigt",
        )
        self.assertEqual(deutsch_section.development, ())
        self.assertEqual(deutsch_section.example_observations, ())

    def test_confirmed_status_stays_visible_after_observation_soft_delete(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Leseverstehen",
                    "Sinnverstehendes Lesen",
                    "Wörter, Sätze sowie literarische und nicht literarische "
                    "altersgemäße Texte sinnverstehend lesen",
                    "-",
                ),
            ),
        ))
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="+",
        )
        self.adapter.delete_observation("OBS-000001")

        groups = self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        status = next(
            competency
            for group in groups
            for competency in group.competencies
            if competency.competency_id == self.german_listening_competency_id
        )
        deutsch_section = next(
            section
            for section in preview.subject_sections
            if section.subject_display_name == "Deutsch"
        )

        self.assertEqual(status.rating_history, ())
        self.assertEqual(status.confirmed_rating, "+")
        self.assertEqual(status.confirmation_status_label, "von Laura bestätigt: +")
        self.assertEqual(deutsch_section.strengths[0].rating, "+")
        self.assertEqual(
            deutsch_section.strengths[0].rating_source,
            "von Laura bestätigt",
        )
        self.assertEqual(
            deutsch_section.current_statuses[0].display_label,
            "Wahrnehmen und Unterscheiden von Lauten · "
            "Aktueller Stand: Kenntnisse meist anwenden · von Laura bestätigt",
        )
        self.assertEqual(deutsch_section.development, ())
        self.assertEqual(deutsch_section.example_observations, ())

    def test_report_preview_uses_confirmed_competency_status_when_available(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "-",
                ),
            ),
        ))
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="+",
        )

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        deutsch_section = preview.subject_sections[0]

        self.assertIsNotNone(preview)
        self.assertEqual(deutsch_section.subject_display_name, "Deutsch")
        self.assertEqual(deutsch_section.strengths[0].rating, "+")
        self.assertEqual(
            deutsch_section.strengths[0].rating_source,
            "von Laura bestätigt",
        )
        self.assertEqual(
            deutsch_section.current_statuses[0].display_label,
            "Wahrnehmen und Unterscheiden von Lauten · "
            "Aktueller Stand: Kenntnisse meist anwenden · von Laura bestätigt",
        )
        self.assertEqual(
            deutsch_section.development[0].development_label,
            "Einzelbeobachtung vorhanden, noch kein Verlauf ableitbar.",
        )

    def test_report_preview_shows_current_confirmed_competency_status(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "-",
                ),
            ),
        ))
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="+",
        )

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        deutsch_section = preview.subject_sections[0]

        self.assertEqual(
            deutsch_section.current_statuses[0].display_label,
            "Wahrnehmen und Unterscheiden von Lauten · "
            "Aktueller Stand: Kenntnisse meist anwenden · von Laura bestätigt",
        )
        self.assertEqual(deutsch_section.current_statuses[0].rating, "+")
        self.assertEqual(
            deutsch_section.current_statuses[0].rating_source,
            "von Laura bestätigt",
        )

    def test_report_preview_shows_current_derived_competency_status_without_confirmation(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
            ),
        ))

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        deutsch_section = preview.subject_sections[0]

        self.assertEqual(
            deutsch_section.current_statuses[0].display_label,
            "Wahrnehmen und Unterscheiden von Lauten · "
            "Aktueller Stand: Kenntnisse meist anwenden · aus Beobachtungen abgeleitet",
        )
        self.assertEqual(deutsch_section.current_statuses[0].rating, "+")
        self.assertEqual(
            deutsch_section.current_statuses[0].rating_source,
            "aus Beobachtungen abgeleitet",
        )

    def test_report_preview_uses_calculated_proposal_without_confirmation(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "-",
                ),
            ),
        ))

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        deutsch_section = preview.subject_sections[0]

        self.assertEqual(
            deutsch_section.current_statuses[0].display_label,
            "Wahrnehmen und Unterscheiden von Lauten · "
            "Aktueller Stand: Mit Unterstützung · aus Beobachtungen abgeleitet",
        )
        self.assertEqual(
            deutsch_section.development[0].development_label,
            "Einzelbeobachtung vorhanden, noch kein Verlauf ableitbar.",
        )
        self.assertEqual(deutsch_section.strengths, ())

    def test_report_preview_shows_positive_development_from_history(self) -> None:
        for date_text, rating in (
            ("2026-09-12", "--"),
            ("2026-11-08", "-"),
            ("2027-01-10", "+"),
        ):
            self.adapter.save_observation(self._sample_observation_draft(
                date_text=date_text,
                competency_ratings=(
                    self._sample_observation_rating(
                        self.german_listening_competency_id,
                        "deutsch",
                        "Deutsch",
                        "Mit Texten und Medien umgehen",
                        "Lesen und Verstehen",
                        "Texte lesen und zentrale Informationen entnehmen",
                        rating,
                    ),
                ),
            ))

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        development = preview.subject_sections[0].development[0]

        self.assertEqual(
            development.development_label,
            "Entwicklung: -- → + · positive Entwicklung erkennbar",
        )
        self.assertEqual(development.rating_history, ("--", "-", "+"))

    def test_report_preview_shows_stable_development_from_history(self) -> None:
        for date_text in ("2026-09-12", "2027-01-10"):
            self.adapter.save_observation(self._sample_observation_draft(
                date_text=date_text,
                competency_ratings=(
                    self._sample_observation_rating(
                        self.german_listening_competency_id,
                        "deutsch",
                        "Deutsch",
                        "Mit Texten und Medien umgehen",
                        "Lesen und Verstehen",
                        "Texte lesen und zentrale Informationen entnehmen",
                        "+",
                    ),
                ),
            ))

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(
            preview.subject_sections[0].development[0].development_label,
            "Stabil beobachtet: +",
        )

    def test_report_preview_marks_changing_development_from_history(self) -> None:
        for date_text, rating in (
            ("2026-09-12", "+"),
            ("2026-11-08", "-"),
            ("2027-01-10", "+"),
        ):
            self.adapter.save_observation(self._sample_observation_draft(
                date_text=date_text,
                competency_ratings=(
                    self._sample_observation_rating(
                        self.german_listening_competency_id,
                        "deutsch",
                        "Deutsch",
                        "Mit Texten und Medien umgehen",
                        "Lesen und Verstehen",
                        "Texte lesen und zentrale Informationen entnehmen",
                        rating,
                    ),
                ),
            ))

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(
            preview.subject_sections[0].development[0].development_label,
            "Wechselnde Beobachtungslage, weitere Beobachtungen sinnvoll. "
            "Verlauf: + → - → +",
        )

    def test_report_preview_development_ignores_soft_deleted_observations(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-09-12",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
            ),
        ))
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2027-01-10",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "--",
                ),
            ),
        ))
        self.adapter.delete_observation("OBS-000002")

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertEqual(
            preview.subject_sections[0].development[0].development_label,
            "Einzelbeobachtung vorhanden, noch kein Verlauf ableitbar.",
        )

    def test_report_preview_shows_active_observations_as_evidence(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            context="Leseübung",
            note="Liest einen bekannten Text und markiert zentrale Aussagen.",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
            ),
        ))

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        evidence = preview.subject_sections[0].example_observations[0]

        self.assertEqual(evidence.observation_id, "OBS-000001")
        self.assertIn("2026-07-03", evidence.display_label)
        self.assertIn("Leseübung", evidence.display_label)
        self.assertIn("+ Mit Texten und Medien umgehen", evidence.competency_labels)

    def test_report_preview_excludes_soft_deleted_observations(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
            ),
        ))

        self.adapter.delete_observation("OBS-000001")
        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        self.assertIsNotNone(preview)
        self.assertEqual(preview.subject_sections, ())

    def test_report_text_contains_student_date_subjects_and_evidence(self) -> None:
        report_text = format_student_report_preview_text(
            self._sample_student_detail(),
            self._sample_report_preview(),
            created_date="2026-07-04",
        )

        self.assertIn("Schüler: Emma Müller", report_text)
        self.assertIn("Stammgruppe: Grashüpfer", report_text)
        self.assertIn("Kurs: Kurs 1", report_text)
        self.assertIn("Erstellt am: 2026-07-04", report_text)
        self.assertIn("## Deutsch", report_text)
        self.assertIn("Aktueller Stand", report_text)
        self.assertIn(
            "- Mit Texten und Medien umgehen · "
            "Aktueller Stand: Kenntnisse meist anwenden · von Laura bestätigt",
            report_text,
        )
        self.assertIn(
            "- Wörter und Sätze · Einzelbeobachtung vorhanden, noch kein Verlauf ableitbar.",
            report_text,
        )
        self.assertIn("Beispielbeobachtungen", report_text)
        self.assertIn("- 2026-07-03 · Leseübung · Liest einen bekannten Text.", report_text)
        self.assertIn("  - + Mit Texten und Medien umgehen", report_text)

    def test_report_text_keeps_soft_deleted_observations_absent(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            note="Diese Beobachtung wird gelöscht.",
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
            ),
        ))
        self.adapter.delete_observation("OBS-000001")
        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        report_text = format_student_report_preview_text(
            self._sample_student_detail(),
            preview,
            created_date="2026-07-04",
        )

        self.assertNotIn("Diese Beobachtung wird gelöscht.", report_text)
        self.assertIn(REPORT_NO_OBSERVATIONS_MESSAGE, report_text)

    def test_documentation_status_starts_with_zero_documented_competencies(self) -> None:
        statuses = self.adapter.list_documentation_status_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        expected_subject_ids = tuple(
            dict.fromkeys(
                competency.subject_id
                for competency in SQLiteCompetencyRepository(
                    self.database
                ).list_competencies()
                if competency.active and competency.catalog_status == "current"
            )
        )

        self.assertTrue(statuses)
        self.assertEqual(
            tuple(status.subject_id for status in statuses),
            expected_subject_ids,
        )
        self.assertTrue(all(status.total_count > 0 for status in statuses))
        self.assertTrue(all(status.documented_count == 0 for status in statuses))
        self.assertTrue(
            all(
                len(status.missing_competencies) >= status.total_count
                for status in statuses
            )
        )
        self.assertTrue(
            any(status.progress_label.startswith("Deutsch: 0 / ") for status in statuses)
        )

    def test_documentation_status_uses_only_documentation_subject_selection(self) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))

        statuses = self.adapter.list_documentation_status_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        expected_total_count = sum(
            len({
                competency.competency_id
                for competency in SQLiteCompetencyRepository(
                    self.database
                ).list_competencies()
                if competency.active
                and competency.catalog_status == "current"
                and competency.subject_id == subject_id
            })
            for subject_id in ("deutsch", "mathematik")
        )

        self.assertEqual(
            tuple(status.subject_id for status in statuses),
            ("deutsch", "mathematik"),
        )
        self.assertEqual(
            sum(status.total_count for status in statuses),
            expected_total_count,
        )
        self.assertNotIn("epu", {status.subject_id for status in statuses})

    def test_documentation_status_counts_active_observation_learning_areas(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Leseverstehen",
                    "Sinnverstehendes Lesen",
                    "Wörter, Sätze sowie literarische und nicht literarische "
                    "altersgemäße Texte sinnverstehend lesen",
                    "+",
                ),
                self._sample_observation_rating(
                    self.german_word_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Über Sprache, Sprachverwendung und Sprachenlernen reflektieren",
                    "Wortarten",
                    "Substantiv, Artikel, Adjektiv, Verb und Personalpronomen unterscheiden",
                    "-",
                ),
            ),
        ))

        statuses = self.adapter.list_documentation_status_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        deutsch_status = next(
            status for status in statuses if status.subject_display_name == "Deutsch"
        )

        self.assertEqual(deutsch_status.documented_count, 2)
        self.assertEqual(
            deutsch_status.total_count - deutsch_status.documented_count,
            deutsch_status.total_count - 2,
        )

    def test_documentation_status_ignores_soft_deleted_observations(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
            ),
        ))
        self.adapter.delete_observation("OBS-000001")

        statuses = self.adapter.list_documentation_status_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        deutsch_status = next(
            status for status in statuses if status.subject_display_name == "Deutsch"
        )

        self.assertEqual(deutsch_status.documented_count, 0)

    def test_documentation_status_counts_confirmed_competency_status(self) -> None:
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="+",
        )

        statuses = self.adapter.list_documentation_status_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        deutsch_status = next(
            status for status in statuses if status.subject_display_name == "Deutsch"
        )

        self.assertEqual(deutsch_status.documented_count, 1)
        self.assertNotIn(
            self.german_listening_competency_id,
            {competency.competency_id for competency in deutsch_status.missing_competencies},
        )

    def test_canonical_status_projection_includes_undocumented_current_goals(self) -> None:
        statuses = self.adapter.list_competency_status_projection_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )

        status = next(item for item in statuses if item.competency_id == self.german_listening_competency_id)
        self.assertEqual(status.documentation_state, "undocumented")
        self.assertEqual(status.observation_count, 0)
        self.assertFalse(status.historical)
        self.assertTrue(status.is_active)
        self.assertEqual(status.catalog_status, "current")

    def test_canonical_status_projection_keeps_multiple_ratings_as_proposal(self) -> None:
        for date_text, rating in (("2026-07-03", "-"), ("2026-07-04", "+")):
            self.adapter.save_observation(self._sample_observation_draft(
                date_text=date_text,
                competency_ratings=(
                    self._sample_observation_rating(
                        self.german_listening_competency_id, "deutsch", "Deutsch",
                        "Mit Texten und Medien umgehen", "Lesen und Verstehen",
                        "Snapshottext", rating,
                    ),
                ),
            ))

        status = self._canonical_status(self.german_listening_competency_id)
        self.assertEqual(status.documentation_state, "observed_unconfirmed")
        self.assertEqual(status.observation_count, 2)
        self.assertEqual(status.rating_history, ("-", "+"))
        self.assertEqual(status.observed_proposal, status.rating)
        self.assertEqual(
            tuple(evidence.observation_date for evidence in status.evidence),
            ("2026-07-04", "2026-07-03"),
        )
        self.assertEqual(
            len({evidence.observation_id for evidence in status.evidence}),
            len(status.evidence),
        )

    def test_canonical_status_projection_keeps_confirmation_separate_from_proposal(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft())
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="-",
            note="Bewusst getrennt.",
        )

        status = self._canonical_status(self.german_listening_competency_id)
        self.assertEqual(status.documentation_state, "confirmed")
        self.assertEqual(status.observed_proposal, "+")
        self.assertEqual(status.confirmed_rating, "-")
        self.assertEqual(status.confirmation_note, "Bewusst getrennt.")

    def test_canonical_status_projection_keeps_confirmation_without_observation(self) -> None:
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="+",
        )

        status = self._canonical_status(self.german_listening_competency_id)
        self.assertEqual(status.documentation_state, "confirmed")
        self.assertEqual(status.observed_proposal, "")
        self.assertEqual(status.observation_count, 0)

    def test_canonical_status_projection_marks_newer_observation_after_confirmation(self) -> None:
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="-",
        )
        self.adapter.save_observation(self._sample_observation_draft(
            date_text=(date.today() + timedelta(days=1)).isoformat(),
        ))

        status = self._canonical_status(self.german_listening_competency_id)
        self.assertEqual(status.documentation_state, "newer_observations")
        self.assertTrue(status.has_observations_newer_than_confirmation)
        self.assertEqual(status.confirmed_rating, "-")

    def test_canonical_status_projection_excludes_soft_deleted_observations(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id, "deutsch", "Deutsch", "Leseverstehen",
                    "Sinnverstehendes Lesen", "Aktueller Snapshot", "+",
                ),
            ),
        ))
        self.adapter.delete_observation("OBS-000001")

        status = self._canonical_status(self.german_listening_competency_id)
        self.assertEqual(status.documentation_state, "undocumented")
        self.assertEqual(status.observation_count, 0)

    def obsolete_canonical_status_projection_keeps_legacy_snapshot_without_overwriting_it(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            subject_id="epu",
            subject_display_name="EPU historisch",
            competency_ratings=(
                self._sample_observation_rating(
                    self.epu_competency_id, "epu", "EPU historisch", "Historischer Bereich",
                    "Historisches Thema", "Historischer Snapshot", "+",
                ),
            ),
        ))

        status = self._canonical_status(self.epu_competency_id)
        self.assertTrue(status.historical)
        self.assertEqual(status.competency_text, "Historischer Snapshot")
        self.assertEqual(status.subject_display_name, "EPU historisch")

    def obsolete_replaced_math_competency_stays_in_status_cockpit_and_report_history(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            subject_id="mathematik",
            subject_display_name="Mathematik",
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000318", "mathematik", "Mathematik",
                    "Größenvorstellungen nutzen und mit Größen umgehen",
                    "Zeit", "Historischer Uhrzeiten-Snapshot", "+",
                ),
            ),
        ))
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id="CMP-000318",
            confirmed_rating="+",
            note="Historisch bestaetigt.",
        )

        status = self._canonical_status("CMP-000318")
        cockpit = self.adapter.competency_cockpit_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        historical_cockpit_ids = {
            competency.competency_id
            for subject in cockpit.historical_subjects
            for area in subject.learning_areas
            for topic in area.topics
            for competency in topic.competencies
        }
        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        self.assertIsNotNone(preview)
        report_ids = {
            competency.competency_id
            for section in (() if preview is None else preview.subject_sections)
            for competency in section.current_statuses
        }

        self.assertTrue(status.historical)
        self.assertEqual(status.competency_text, "Historischer Uhrzeiten-Snapshot")
        self.assertEqual(status.confirmed_rating, "+")
        self.assertEqual(status.confirmation_note, "Historisch bestaetigt.")
        self.assertIn("CMP-000318", historical_cockpit_ids)
        self.assertIn("CMP-000318", report_ids)

    def test_canonical_status_projection_keeps_missing_catalog_snapshot(self) -> None:
        SQLiteObservationRepository(self.database).create_observation(ObservationRecord(
            "OBS-MISSING", f"{STUDENT_ID_PREFIX}-000001", "2026-07-03", "altfach",
            "", "", True, "2026-07-03T00:00:00+00:00", "2026-07-03T00:00:00+00:00",
            (ObservationCompetencyRatingRecord(
                "CMP-MISSING", "altfach", "Altes Fach", "Alter Bereich",
                "Altes Thema", "Historischer Snapshot ohne Katalog", "+",
            ),),
        ))

        status = self._canonical_status("CMP-MISSING")
        self.assertTrue(status.missing_catalog_reference)
        self.assertTrue(status.historical)
        self.assertEqual(status.competency_text, "Historischer Snapshot ohne Katalog")

    def test_status_projection_neither_mutates_snapshots_nor_migrates_missing_ids(self) -> None:
        SQLiteObservationRepository(self.database).create_observation(ObservationRecord(
            "OBS-MISSING-IMMUTABLE", f"{STUDENT_ID_PREFIX}-000001", "2026-07-03",
            "altfach", "", "", True, "2026-07-03T00:00:00+00:00",
            "2026-07-03T00:00:00+00:00", (ObservationCompetencyRatingRecord(
                "CMP-MISSING-IMMUTABLE", "altfach", "Altes Fach", "Alter Bereich",
                "Altes Thema", "Unveränderter Snapshot", "+",
            ),),
        ))
        catalog_ids_before = {
            entry.competency_id
            for entry in SQLiteCompetencyRepository(self.database).list_competencies()
        }

        status = self._canonical_status("CMP-MISSING-IMMUTABLE")

        catalog_ids_after = {
            entry.competency_id
            for entry in SQLiteCompetencyRepository(self.database).list_competencies()
        }
        self.assertEqual(status.competency_id, "CMP-MISSING-IMMUTABLE")
        self.assertEqual(status.competency_label, "Unveränderter Snapshot")
        self.assertEqual(status.competency_text, "Unveränderter Snapshot")
        self.assertTrue(status.missing_catalog_reference)
        self.assertEqual(catalog_ids_after, catalog_ids_before)

    def test_documentation_totals_count_one_competency_id_once(self) -> None:
        for date_text in ("2026-07-03", "2026-07-04"):
            self.adapter.save_observation(self._sample_observation_draft(
                date_text=date_text,
                competency_ratings=(
                    self._sample_observation_rating(
                        self.german_listening_competency_id, "deutsch", "Deutsch", "Leseverstehen",
                        "Sinnverstehendes Lesen", "Snapshot", "+",
                    ),
                ),
            ))

        deutsch = next(
            item
            for item in self.adapter.list_documentation_status_for_student(
                f"{STUDENT_ID_PREFIX}-000001"
            )
            if item.subject_id == "deutsch"
        )

        self.assertEqual(deutsch.documented_count, 1)
        self.assertEqual(
            sum(item.documented_count for item in deutsch.learning_area_statuses),
            1,
        )

    def test_documentation_status_counts_concrete_competencies_and_learning_areas(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id, "deutsch", "Deutsch", "Leseverstehen",
                    "Sinnverstehendes Lesen", "Text 1", "+",
                ),
                self._sample_observation_rating(
                    self.german_word_competency_id, "deutsch", "Deutsch", "Über Sprache, Sprachverwendung und Sprachenlernen reflektieren",
                    "Wortarten", "Text 2", "-",
                ),
            ),
        ))

        deutsch = next(
            item for item in self.adapter.list_documentation_status_for_student(
                f"{STUDENT_ID_PREFIX}-000001"
            ) if item.subject_id == "deutsch"
        )
        self.assertEqual(deutsch.documented_count, 2)
        self.assertEqual(sum(item.total_count for item in deutsch.learning_area_statuses), deutsch.total_count)
        self.assertEqual(sum(item.documented_count for item in deutsch.learning_area_statuses), 2)

    def test_canonical_status_projection_keeps_cross_subject_observation_evidence(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            subject_id=OBSERVATION_CROSS_SUBJECT_LABEL,
            subject_display_name=OBSERVATION_CROSS_SUBJECT_LABEL,
            competency_ratings=(
                self._sample_observation_rating(
                    self.german_listening_competency_id, "deutsch", "Deutsch", "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen", "Deutsch-Snapshot", "+",
                ),
                self._sample_observation_rating(
                    self.epu_competency_id, "epu", "EPU", "Raum und Zeit",
                    "Orientierung", "EPU-Snapshot", "-",
                ),
            ),
        ))

        self.assertEqual(self._canonical_status(self.german_listening_competency_id).subject_id, "deutsch")
        self.assertEqual(self._canonical_status(self.epu_competency_id).subject_id, "epu")

    def test_report_preview_remains_available_from_canonical_documented_statuses(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft())
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.german_listening_competency_id,
            confirmed_rating="-",
        )

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        deutsch = next(section for section in preview.subject_sections if section.subject_id == "deutsch")
        self.assertEqual(deutsch.current_statuses[0].rating, "-")
        self.assertEqual(deutsch.current_statuses[0].rating_source, "von Laura bestätigt")

    def test_missing_competencies_ignore_non_documentation_subjects(self) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))
        self.adapter.save_observation(self._sample_observation_draft(
            subject_id="epu",
            subject_display_name="EPU",
            competency_ratings=(
                self._sample_observation_rating(
                    self.epu_competency_id,
                    "epu",
                    "EPU",
                    "Raum und Zeit",
                    "Orientierung in Raum und Zeit",
                    "Sich in vertrauten Räumen orientieren",
                    "-",
                ),
            ),
        ))

        groups = self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        statuses = self.adapter.list_documentation_status_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        epu_group = next(group for group in groups if group.subject_id == "epu")
        deutsch_status = next(
            status
            for status in statuses
            if status.subject_id == "deutsch"
        )

        self.assertEqual(epu_group.missing_competencies, ())
        self.assertNotIn("epu", {status.subject_id for status in statuses})
        self.assertTrue(deutsch_status.missing_competencies)

    def test_observations_in_non_documentation_subjects_stay_visible(self) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))
        self.adapter.save_observation(self._sample_observation_draft(
            subject_id="epu",
            subject_display_name="EPU",
            competency_ratings=(
                self._sample_observation_rating(
                    self.epu_competency_id,
                    "epu",
                    "EPU",
                    "Raum und Zeit",
                    "Orientierung in Raum und Zeit",
                    "Sich in vertrauten Räumen orientieren",
                    "+",
                ),
            ),
        ))

        observations = self.adapter.list_observations_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        groups = self.adapter.list_competency_overview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        epu_group = next(group for group in groups if group.subject_id == "epu")

        self.assertEqual(observations[0].subject_display_name, "EPU")
        self.assertEqual(epu_group.competencies[0].rating_history, ("+",))

    def test_report_keeps_confirmed_status_for_non_documentation_subject(self) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id=self.epu_competency_id,
            confirmed_rating="+",
        )

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        epu_section = next(
            section
            for section in preview.subject_sections
            if section.subject_id == "epu"
        )

        self.assertEqual(epu_section.current_statuses[0].rating, "+")
        self.assertEqual(
            epu_section.current_statuses[0].rating_source,
            "von Laura bestätigt",
        )

    def test_documentation_summary_labels_compact_list_progress(self) -> None:
        summary = documentation_summary_from_subjects(
            (
                StudentDocumentationSubjectStatus("deutsch", "Deutsch", 2, 3, (), 0),
                StudentDocumentationSubjectStatus("epu", "EPU", 0, 2, (), 2),
            )
        )

        self.assertEqual(summary.list_label, "2/5 Bereiche · teilweise dokumentiert")
        self.assertEqual(
            summary.profile_summary_label,
            "2/5 Lernbereiche dokumentiert",
        )
        self.assertEqual(summary.weak_subjects_label, "Noch wenig belegt: EPU, Deutsch")

    def test_new_app_database_starts_without_demo_students(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            _create_empty_final_v4_database(database_path)
            adapter = StudentDesktopAdapter(database_path)

            self.assertTrue(database_path.exists())
            self.assertEqual(adapter.list_students(), ())
            self.assertEqual(
                adapter.group_id_by_name()["Grashüpfer"],
                f"{GROUP_ID_PREFIX}-000001",
            )
            self.assertEqual(
                adapter.course_id_by_name()["Kurs 1"],
                f"{COURSE_ID_PREFIX}-000001",
            )

    def test_new_student_persists_after_adapter_reinitialization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            _create_empty_final_v4_database(database_path)
            adapter = StudentDesktopAdapter(database_path)

            result = adapter.save_new_student(
                first_name="Mila",
                last_name="Neumann",
                group_id=f"{GROUP_ID_PREFIX}-000001",
                course_id=f"{COURSE_ID_PREFIX}-000001",
                student_notes="Mag Zahlen.",
            )
            self.assertIsInstance(result, SuccessResult)

            reloaded_adapter = StudentDesktopAdapter(database_path)
            students = reloaded_adapter.list_students()
            profile = reloaded_adapter.get_student_profile(result.value.student_id)
            search_result = filter_student_list(students, "neumann")
            group_students = reloaded_adapter.list_students(
                group_id=f"{GROUP_ID_PREFIX}-000001",
            )
            course_students = reloaded_adapter.list_students(
                course_id=f"{COURSE_ID_PREFIX}-000001",
            )
            course_group_students = reloaded_adapter.list_students(
                group_ids=(f"{GROUP_ID_PREFIX}-000001",),
                course_id=f"{COURSE_ID_PREFIX}-000001",
            )

        self.assertTrue(result.value.student_id.startswith("STD-"))
        self.assertEqual(len(students), 1)
        self.assertEqual(students[0].first_name, "Mila")
        self.assertEqual(students[0].last_name, "Neumann")
        self.assertEqual(students[0].group_id, f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(students[0].group_name, "Grashüpfer")
        self.assertEqual(students[0].course_id, f"{COURSE_ID_PREFIX}-000001")
        self.assertEqual(students[0].course_name, "Kurs 1")
        self.assertEqual(students[0].course_color_name, "Blau")
        self.assertEqual(students[0].course_color_hex, "#2563EB")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.display_name, "Mila Neumann")
        self.assertEqual(profile.group_name, "Grashüpfer")
        self.assertEqual(profile.course_name, "Kurs 1")
        self.assertEqual(profile.student_notes, "Mag Zahlen.")
        self.assertEqual(search_result, students)
        self.assertEqual(group_students, students)
        self.assertEqual(course_students, students)
        self.assertEqual(course_group_students, students)

    def test_reopening_existing_database_does_not_add_demo_students(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            _create_empty_final_v4_database(database_path)
            adapter = StudentDesktopAdapter(database_path)
            result = adapter.save_new_student(
                first_name="Oskar",
                last_name="Klein",
                group_id=f"{GROUP_ID_PREFIX}-000001",
                course_id=f"{COURSE_ID_PREFIX}-000002",
            )
            self.assertIsInstance(result, SuccessResult)

            reloaded_adapter = StudentDesktopAdapter(database_path)
            students = reloaded_adapter.list_students()

        self.assertEqual(len(students), 1)
        self.assertEqual(students[0].display_name, "Oskar Klein")
        self.assertEqual(students[0].course_id, f"{COURSE_ID_PREFIX}-000002")

    def test_group_and_course_name_mapping_uses_ids(self) -> None:
        group_ids = self.adapter.group_id_by_name()
        course_ids = self.adapter.course_id_by_name()

        self.assertEqual(group_ids["Grashüpfer"], f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(course_ids["Kurs 1"], f"{COURSE_ID_PREFIX}-000001")
        self.assertEqual(course_ids["Kurs 2"], f"{COURSE_ID_PREFIX}-000002")
        self.assertEqual(course_ids["Kurs 3"], f"{COURSE_ID_PREFIX}-000003")

    def test_student_list_uses_readable_group_and_course_names(self) -> None:
        students = self.adapter.list_students()

        self.assertEqual(len(students), 28)
        self.assertEqual(students[0].group_id, f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(students[0].group_name, "Grashüpfer")
        self.assertEqual(students[0].course_id, f"{COURSE_ID_PREFIX}-000001")
        course_one_students = tuple(
            student
            for student in students
            if student.course_id == f"{COURSE_ID_PREFIX}-000001"
        )
        self.assertEqual(
            tuple(student.display_name for student in course_one_students),
            tuple(
                sorted(
                    (student.display_name for student in course_one_students),
                    key=str.casefold,
                )
            ),
        )
        self.assertIn(students[0].course_id, {
            f"{COURSE_ID_PREFIX}-000001",
            f"{COURSE_ID_PREFIX}-000002",
            f"{COURSE_ID_PREFIX}-000003",
        })
        self.assertIn(students[0].course_name, {"Kurs 1", "Kurs 2", "Kurs 3"})
        self.assertIn("Bereiche", students[0].documentation_status.list_label)
        self.assertNotIn("Deutsch:", students[0].documentation_status.list_label)

    def test_student_list_sort_key_uses_course_order_then_name_then_unknown_course(self) -> None:
        students = (
            StudentListItem("STU-000003", "Zara", "Muster", "GRP-1", "Gruppe", "CRS-2", "Kurs 2"),
            StudentListItem("STU-000002", "Ben", "Muster", "GRP-1", "Gruppe", "CRS-1", "Kurs 1"),
            StudentListItem("STU-000004", "Ohne", "Kurs", "GRP-1", "Gruppe", "", ""),
            StudentListItem("STU-000001", "Anna", "Muster", "GRP-1", "Gruppe", "CRS-1", "Kurs 1"),
        )

        sorted_students = sort_student_list(students, {"CRS-1": 0, "CRS-2": 1})

        self.assertEqual(
            tuple(student.student_id for student in sorted_students),
            ("STU-000001", "STU-000002", "STU-000003", "STU-000004"),
        )

    def test_student_adapter_sorts_all_students_by_course_order_and_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            _create_empty_final_v4_database(database_path)
            adapter = StudentDesktopAdapter(database_path)
            adapter.save_new_student(
                first_name="Zara",
                last_name="Muster",
                group_id=f"{GROUP_ID_PREFIX}-000001",
                course_id=f"{COURSE_ID_PREFIX}-000002",
            )
            adapter.save_new_student(
                first_name="Ben",
                last_name="Muster",
                group_id=f"{GROUP_ID_PREFIX}-000001",
                course_id=f"{COURSE_ID_PREFIX}-000001",
            )
            adapter.save_new_student(
                first_name="Anna",
                last_name="Muster",
                group_id=f"{GROUP_ID_PREFIX}-000001",
                course_id=f"{COURSE_ID_PREFIX}-000001",
            )

            students = adapter.list_students()
            group_students = adapter.list_students(group_id=f"{GROUP_ID_PREFIX}-000001")
            course_students = adapter.list_students(course_id=f"{COURSE_ID_PREFIX}-000001")

        self.assertEqual(
            tuple(student.display_name for student in students),
            ("Anna Muster", "Ben Muster", "Zara Muster"),
        )
        self.assertEqual(
            tuple(student.display_name for student in group_students),
            ("Anna Muster", "Ben Muster", "Zara Muster"),
        )
        self.assertEqual(
            tuple(student.display_name for student in course_students),
            ("Anna Muster", "Ben Muster"),
        )

    def test_group_summary_counts_active_students(self) -> None:
        groups = self.adapter.list_group_summaries()

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_id, f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(groups[0].group_name, "Grashüpfer")
        self.assertEqual(groups[0].active_student_count, 28)

    def test_navigation_contains_master_data_screen(self) -> None:
        navigation_labels = tuple(item.label for item in NAVIGATION_ITEMS)
        navigation_keys = tuple(item.key for item in NAVIGATION_ITEMS)

        self.assertIn("Stammdaten", navigation_labels)
        self.assertIn("master_data", navigation_keys)
        self.assertEqual(
            resolve_navigation_target("master_data").screen_key,
            "master_data",
        )

    def test_macos_launcher_exists_and_starts_desktop_app_module(self) -> None:
        launcher_path = Path("launcher/Jenaplan_Kompetenzmanager.command")
        launcher_source = launcher_path.read_text(encoding="utf-8")

        self.assertTrue(launcher_path.exists())
        self.assertTrue(os.access(launcher_path, os.X_OK))
        self.assertIn(".venv/bin/python", launcher_source)
        self.assertIn("python3", launcher_source)
        self.assertIn("-m src.desktop_app.main", launcher_source)

    def test_desktop_app_starts_maximized_without_full_screen_mode(self) -> None:
        source = inspect.getsource(main.main)

        self.assertIn("window.showMaximized()", source)
        self.assertNotIn("window.showFullScreen()", source)

    def test_master_data_view_model_displays_groups_and_courses(self) -> None:
        view_model = self.master_data_adapter.view_model()

        self.assertIsInstance(view_model, MasterDataViewModel)
        self.assertEqual(view_model.groups[0].item_id, f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(view_model.groups[0].name, "Grashüpfer")
        self.assertTrue(view_model.groups[0].is_persistent)
        self.assertEqual(view_model.groups[0].status_label, "Vorhanden")
        self.assertEqual(
            {course.name for course in view_model.courses},
            {"Kurs 1", "Kurs 2", "Kurs 3"},
        )
        self.assertEqual(view_model.courses[0].color_name, "Blau")
        self.assertEqual(view_model.courses[0].color_hex, "#2563EB")
        self.assertTrue(view_model.courses[0].has_color)
        self.assertEqual(len(view_model.course_groups), 1)
        self.assertEqual(
            view_model.course_groups[0].name,
            "Mathe/Deutsch Kursverbund A",
        )
        self.assertEqual(
            view_model.course_groups[0].selected_group_ids,
            (f"{GROUP_ID_PREFIX}-000001",),
        )
        self.assertEqual(
            view_model.course_groups[0].selected_course_ids,
            (
                f"{COURSE_ID_PREFIX}-000001",
                f"{COURSE_ID_PREFIX}-000002",
                f"{COURSE_ID_PREFIX}-000003",
            ),
        )

    def test_course_group_view_model_contains_groups_and_courses(self) -> None:
        course_group = CourseGroupViewModel(
            "course-group-a",
            "Mathe/Deutsch Kursverbund A",
            (f"{GROUP_ID_PREFIX}-000001", f"{GROUP_ID_PREFIX}-000002"),
            (f"{COURSE_ID_PREFIX}-000001", f"{COURSE_ID_PREFIX}-000002"),
        )

        self.assertEqual(course_group.course_group_id, "course-group-a")
        self.assertIn(f"{GROUP_ID_PREFIX}-000001", course_group.selected_group_ids)
        self.assertIn(f"{COURSE_ID_PREFIX}-000001", course_group.selected_course_ids)

    def test_master_data_adapter_updates_course_group_persistently(self) -> None:
        updated_course_group = self.master_data_adapter.update_course_group(
            "course-group-default",
            "Mathe/Deutsch Kursverbund B",
            (f"{GROUP_ID_PREFIX}-000001",),
            (f"{COURSE_ID_PREFIX}-000001", f"{COURSE_ID_PREFIX}-000002"),
        )
        reloaded_adapter = MasterDataDesktopAdapter(StudentDesktopAdapter(self.database_path))
        view_model = reloaded_adapter.view_model()

        self.assertEqual(updated_course_group.name, "Mathe/Deutsch Kursverbund B")
        self.assertEqual(
            updated_course_group.selected_group_ids,
            (f"{GROUP_ID_PREFIX}-000001",),
        )
        self.assertEqual(
            updated_course_group.selected_course_ids,
            (f"{COURSE_ID_PREFIX}-000001", f"{COURSE_ID_PREFIX}-000002"),
        )
        self.assertEqual(view_model.course_groups[0], updated_course_group)

    def test_master_data_adapter_adds_course_group_persistently(self) -> None:
        second_group = self.master_data_adapter.add_group("Eulen")

        course_group = self.master_data_adapter.add_course_group(
            "Mathe/Deutsch Kursverbund B",
            (f"{GROUP_ID_PREFIX}-000001", second_group.item_id),
            (f"{COURSE_ID_PREFIX}-000001", f"{COURSE_ID_PREFIX}-000002"),
        )
        reloaded_adapter = MasterDataDesktopAdapter(StudentDesktopAdapter(self.database_path))
        reloaded_course_groups = reloaded_adapter.view_model().course_groups

        self.assertTrue(course_group.course_group_id.startswith("CRG-"))
        self.assertEqual(course_group.name, "Mathe/Deutsch Kursverbund B")
        self.assertEqual(
            course_group.selected_group_ids,
            (f"{GROUP_ID_PREFIX}-000001", second_group.item_id),
        )
        self.assertEqual(
            course_group.selected_course_ids,
            (f"{COURSE_ID_PREFIX}-000001", f"{COURSE_ID_PREFIX}-000002"),
        )
        self.assertIn(
            course_group,
            reloaded_course_groups,
        )

    def test_master_data_adapter_rejects_duplicate_course_group_name(self) -> None:
        self.master_data_adapter.add_course_group(
            "Mathe/Deutsch Kursverbund B",
            (f"{GROUP_ID_PREFIX}-000001",),
            (f"{COURSE_ID_PREFIX}-000001",),
        )

        with self.assertRaisesRegex(ValueError, COURSE_GROUP_DUPLICATE_NAME_MESSAGE):
            self.master_data_adapter.add_course_group(
                "mathe/deutsch kursverbund b",
                (f"{GROUP_ID_PREFIX}-000001",),
                (f"{COURSE_ID_PREFIX}-000002",),
            )

    def test_course_group_update_replaces_old_relations_persistently(self) -> None:
        second_group = self.master_data_adapter.add_group("Eulen")
        self.master_data_adapter.update_course_group(
            "course-group-default",
            "Mathe/Deutsch Kursverbund B",
            (second_group.item_id,),
            (f"{COURSE_ID_PREFIX}-000003",),
        )
        reloaded_adapter = MasterDataDesktopAdapter(StudentDesktopAdapter(self.database_path))
        course_group = reloaded_adapter.view_model().course_groups[0]

        self.assertEqual(course_group.selected_group_ids, (second_group.item_id,))
        self.assertEqual(course_group.selected_course_ids, (f"{COURSE_ID_PREFIX}-000003",))
        self.assertNotIn(f"{GROUP_ID_PREFIX}-000001", course_group.selected_group_ids)
        self.assertNotIn(f"{COURSE_ID_PREFIX}-000001", course_group.selected_course_ids)

    def test_course_group_update_validation_rejects_empty_values(self) -> None:
        with self.assertRaisesRegex(ValueError, MASTER_DATA_EMPTY_NAME_MESSAGE):
            self.master_data_adapter.update_course_group(
                "course-group-default",
                "",
                (f"{GROUP_ID_PREFIX}-000001",),
                (f"{COURSE_ID_PREFIX}-000001",),
            )
        with self.assertRaisesRegex(ValueError, COURSE_GROUP_EMPTY_GROUPS_MESSAGE):
            self.master_data_adapter.update_course_group(
                "course-group-default",
                "Mathe/Deutsch Kursverbund A",
                (),
                (f"{COURSE_ID_PREFIX}-000001",),
            )
        with self.assertRaisesRegex(ValueError, COURSE_GROUP_EMPTY_COURSES_MESSAGE):
            self.master_data_adapter.update_course_group(
                "course-group-default",
                "Mathe/Deutsch Kursverbund A",
                (f"{GROUP_ID_PREFIX}-000001",),
                (),
            )

    def test_course_color_options_are_registered_for_master_data_light(self) -> None:
        self.assertEqual(
            COURSE_COLOR_OPTIONS,
            (
                ("Blau", "#2563EB"),
                ("Grün", "#16A34A"),
                ("Orange", "#F97316"),
                ("Gelb", "#EAB308"),
                ("Lila", "#9333EA"),
                ("Rot", "#DC2626"),
                ("Grau", "#6B7280"),
            ),
        )
        self.assertEqual(course_color_from_key("", 0), ("Blau", "#2563EB"))
        self.assertEqual(course_color_from_key("", 1), ("Grün", "#16A34A"))
        self.assertEqual(course_color_from_key("#EAB308"), ("Gelb", "#EAB308"))

    def test_master_data_adapter_persists_new_groups_and_courses(self) -> None:
        group = self.master_data_adapter.add_group("Eulen")
        course = self.master_data_adapter.add_course("Kurs 4", "#9333EA", 1)
        reloaded_adapter = MasterDataDesktopAdapter(StudentDesktopAdapter(self.database_path))
        view_model = reloaded_adapter.view_model()

        self.assertIsInstance(group, MasterDataItemViewModel)
        self.assertEqual(group.name, "Eulen")
        self.assertTrue(group.is_persistent)
        self.assertEqual(group.status_label, "Vorhanden")
        self.assertEqual(course.name, "Kurs 4")
        self.assertEqual(course.color_name, "Lila")
        self.assertEqual(course.color_hex, "#9333EA")
        self.assertEqual(course.year_level, 1)
        self.assertTrue(course.is_persistent)
        self.assertIn("Eulen", {item.name for item in view_model.groups})
        self.assertIn("Kurs 4", {item.name for item in view_model.courses})
        self.assertIn(
            group.item_id,
            view_model.course_groups[0].selected_group_ids,
        )
        self.assertIn(
            course.item_id,
            view_model.course_groups[0].selected_course_ids,
        )

    def test_master_data_adapter_persists_yellow_course_color(self) -> None:
        course = self.master_data_adapter.add_course("Kurs Gelb", "#EAB308", 2)
        reloaded_adapter = MasterDataDesktopAdapter(StudentDesktopAdapter(self.database_path))
        reloaded_course = reloaded_adapter.courses[course.item_id]

        self.assertEqual(reloaded_course.color_name, "Gelb")
        self.assertEqual(reloaded_course.color_hex, "#EAB308")
        self.assertEqual(reloaded_course.year_level, 2)

    def test_master_data_adapter_persists_renames(self) -> None:
        group = self.master_data_adapter.rename_group(
            f"{GROUP_ID_PREFIX}-000001",
            "Grashüpfer A",
        )
        course = self.master_data_adapter.rename_course(
            f"{COURSE_ID_PREFIX}-000001",
            "Kurs 1A",
            "#DC2626",
        )
        reloaded_adapter = MasterDataDesktopAdapter(StudentDesktopAdapter(self.database_path))
        view_model = reloaded_adapter.view_model()

        self.assertEqual(group.name, "Grashüpfer A")
        self.assertEqual(course.name, "Kurs 1A")
        self.assertEqual(course.color_name, "Rot")
        self.assertEqual(course.color_hex, "#DC2626")
        self.assertIn("Grashüpfer A", {item.name for item in view_model.groups})
        self.assertIn("Kurs 1A", {item.name for item in view_model.courses})

    def test_master_data_empty_names_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, MASTER_DATA_EMPTY_NAME_MESSAGE):
            normalize_master_data_name("   ")
        with self.assertRaisesRegex(ValueError, MASTER_DATA_EMPTY_NAME_MESSAGE):
            self.master_data_adapter.add_group("")
        with self.assertRaisesRegex(ValueError, MASTER_DATA_EMPTY_NAME_MESSAGE):
            self.master_data_adapter.add_course("")

    def test_master_data_widgets_do_not_access_sqlite_directly(self) -> None:
        screen_source = inspect.getsource(master_data_screen)
        dialog_source = inspect.getsource(master_data_dialog)

        self.assertNotIn("sqlite", screen_source.casefold())
        self.assertNotIn("sqlite", dialog_source.casefold())
        self.assertNotIn("INSERT INTO", screen_source)
        self.assertNotIn("UPDATE ", screen_source)
        self.assertNotIn("DELETE FROM", screen_source)

    def test_dialogs_use_consistent_save_cancel_buttons(self) -> None:
        button_source = inspect.getsource(dialog_buttons)

        self.assertIn('DIALOG_CANCEL_TEXT = "Abbrechen"', button_source)
        self.assertIn('DIALOG_SAVE_TEXT = "Speichern"', button_source)
        self.assertIn("configure_save_cancel_buttons(buttons)", inspect.getsource(new_student_dialog))
        self.assertIn("configure_save_cancel_buttons(buttons)", inspect.getsource(new_observation_dialog))
        self.assertIn("configure_save_cancel_buttons(buttons)", inspect.getsource(master_data_dialog))
        self.assertNotIn("DIALOG_PRIMARY_BUTTON_STYLE", button_source)
        self.assertNotIn("PRIMARY_BUTTON_STYLESHEET", button_source)
        self.assertIn('configure_button(save_button, "primary"', button_source)
        self.assertIn('configure_button(cancel_button, "secondary"', button_source)
        self.assertNotIn("save_button.setStyleSheet", button_source)
        self.assertIn("save_button.setDefault(True)", button_source)
        self.assertIn('cancel_button.setShortcut("Esc")', button_source)

    def test_pyside_app_uses_icon_based_visual_theme(self) -> None:
        theme_source = inspect.getsource(theme)
        main_source = inspect.getsource(main)
        shell_source = inspect.getsource(shell)
        screen_source = inspect.getsource(students_screen)
        component_source = inspect.getsource(components)

        self.assertEqual(theme.BRAND_NAVY, "#123F67")
        self.assertEqual(theme.BRAND_BLUE, "#176BC1")
        self.assertEqual(theme.BRAND_TEAL, "#087F83")
        self.assertEqual(theme.BRAND_GREEN, "#3B7F34")
        self.assertEqual(theme.BRAND_LIME, "#8DCB22")
        self.assertEqual(theme.BRAND_ORANGE, "#B2530A")
        self.assertEqual(theme.COLOR_NAVY, theme.BRAND_NAVY)
        self.assertEqual(theme.COLOR_BLUE, theme.BRAND_BLUE)
        self.assertEqual(theme.COLOR_TURQUOISE, theme.BRAND_TEAL)
        self.assertEqual(theme.COLOR_GREEN, theme.BRAND_GREEN)
        self.assertEqual(theme.COLOR_ORANGE, theme.BRAND_ORANGE)
        self.assertEqual(
            (
                theme.LIGHT_BLUE,
                theme.LIGHT_TEAL,
                theme.LIGHT_GREEN,
                theme.LIGHT_LIME,
                theme.LIGHT_ORANGE,
                theme.LIGHT_NEUTRAL,
            ),
            ("#EAF4FE", "#E8F7F5", "#EDF7EA", "#F4F9E8", "#FFF2E5", "#F6F9FB"),
        )
        self.assertIn("APP_STYLESHEET", theme_source)
        self.assertIn("QWidget#AppSidebar", theme.APP_STYLESHEET)
        self.assertIn("QListWidget#AppNavigation", theme.APP_STYLESHEET)
        self.assertIn("QFrame#AppCard", theme.APP_STYLESHEET)
        self.assertIn("rgba(255, 255, 255, 246)", theme.APP_STYLESHEET)
        self.assertIn("COLOR_GLASS", theme_source)
        self.assertIn("def apply_app_theme(", theme_source)
        self.assertIn("def create_card(", theme_source)
        self.assertIn("def set_label_style(", theme_source)
        self.assertIn("def set_button_role(", theme_source)
        self.assertNotIn('FONT_FAMILY = "Arial"', theme_source)
        self.assertIn("class PageHeader", component_source)
        self.assertIn("class SegmentedControl", component_source)
        self.assertIn("class Toast", component_source)
        self.assertIn("apply_app_theme(app)", main_source)
        self.assertIn('root.setObjectName("AppRoot")', shell_source)
        self.assertIn('sidebar_container.setObjectName("AppSidebar")', shell_source)
        self.assertIn('self.navigation.setObjectName("AppNavigation")', shell_source)
        self.assertIn('PageHeader("Schüler"', screen_source)

    def test_pilot_interaction_styles_keep_text_contrast_in_all_states(self) -> None:
        stylesheet = theme.APP_STYLESHEET

        def rule(selector: str) -> str:
            return stylesheet.split(f"{selector} {{", 1)[1].split("}", 1)[0]

        for selector in (
            "QPushButton#ObservationHierarchyToggle:hover",
            "QPushButton#ObservationHierarchyToggle:focus",
            "QPushButton#ObservationHierarchyToggle:pressed",
            "QPushButton#RatingBadgeButton:hover",
            "QPushButton#RatingBadgeButton:focus",
            "QPushButton#RatingBadgeButton:checked",
            'QPushButton[buttonRole="secondary"]:hover',
            'QPushButton[buttonRole="secondary"]:focus',
            'QPushButton[buttonRole="secondary"]:pressed',
        ):
            self.assertIn("color:", rule(selector), selector)

        self.assertIn(
            "QFrame#ObservationCatalogCompetencyTile:hover QLabel",
            stylesheet,
        )
        self.assertIn(
            "QFrame#ObservationCatalogCompetencyTile:focus QLabel",
            stylesheet,
        )
        self.assertIn(
            'QFrame#ObservationCatalogCompetencyTile[selected="true"] QLabel',
            stylesheet,
        )
        self.assertIn("color: #FFFFFF", rule("QFrame#Toast QLabel"))
        self.assertNotEqual(
            rule('QFrame#Toast[toastTone="success"]'),
            rule('QFrame#Toast[toastTone="error"]'),
        )

    def test_app_icon_asset_and_helpers_are_available(self) -> None:
        source = inspect.getsource(assets)

        self.assertIn('APP_ICON_RELATIVE_PATH = Path("assets") / "app_icon.png"', source)
        self.assertNotIn("/Users/", source)
        self.assertTrue(assets.app_icon_path().exists())
        self.assertEqual(assets.app_icon_path().name, "app_icon.png")
        app = QApplication.instance() or QApplication([])
        pixmap = assets.load_app_icon_pixmap(64)
        self.assertFalse(pixmap.isNull())
        label = assets.create_app_icon_label(64)
        self.assertIsInstance(label, QLabel)
        self.assertEqual(label.objectName(), "AppIconLabel")
        self.assertIsNotNone(app)

    def test_app_info_dialog_contains_non_technical_app_information(self) -> None:
        source = inspect.getsource(app_info_dialog)
        shell_source = inspect.getsource(shell)

        self.assertIn('APP_INFO_APP_NAME = "Jenaplan-Kompetenzmanager"', source)
        self.assertIn('APP_INFO_MODE = "Lokale Desktop-App"', source)
        self.assertIn(
            'APP_INFO_VERSION = f"Version {APP_VERSION} · Build {APP_BUILD_VERSION}"',
            source,
        )
        self.assertIn('APP_INFO_DEVELOPER_NAME = "Jörg Gehrke"', source)
        self.assertIn('APP_INFO_DESCRIPTION = "Kompetenzmanagement und Entwicklungsdokumentation für Jenaplan-Schulen"', source)
        self.assertIn('APP_INFO_COPYRIGHT = "© 2026 Jörg Gehrke"', source)
        self.assertNotIn("APP_INFO_STORAGE_HINT", source)
        self.assertNotIn("PySide6 Prototyp", source)
        self.assertNotIn("nicht dauerhaft gespeichert", source)
        self.assertIn("AppInfoDialog", shell_source)
        self.assertIn('self.info_button = QPushButton("Über die App")', shell_source)
        self.assertIn("create_app_icon_label(112)", source)
        self.assertIn("open_app_info_dialog", shell_source)
        app = QApplication.instance() or QApplication([])
        info_dialog = app_info_dialog.AppInfoDialog()
        visible_text = "\n".join(
            label.text() for label in info_dialog.findChildren(QLabel)
        )
        self.assertIn("Jenaplan-Kompetenzmanager", visible_text)
        self.assertIn("Version 0.4.3 · Build 403", visible_text)
        self.assertIn("Entwickelt von", visible_text)
        self.assertIn("Jörg Gehrke", visible_text)
        self.assertIn("© 2026 Jörg Gehrke", visible_text)
        self.assertNotIn("v0.4", visible_text)
        self.assertNotIn("/Users/", visible_text)
        info_dialog.close()
        self.assertIsNotNone(app)

    def test_sidebar_and_info_dialog_include_app_icon_without_click_tests(self) -> None:
        app = QApplication.instance() or QApplication([])
        window = shell.AppShell(self.database_path)
        info_dialog = app_info_dialog.AppInfoDialog()

        self.assertIsNotNone(window.findChild(QLabel, "AppIconLabel"))
        self.assertIsNotNone(info_dialog.findChild(QLabel, "AppIconLabel"))
        self.assertIsNotNone(app)
        window.close()
        info_dialog.close()

    def test_master_data_course_screen_shows_course_color_marker(self) -> None:
        source = inspect.getsource(master_data_screen)
        dialog_source = inspect.getsource(master_data_dialog)
        shell_source = inspect.getsource(shell.AppShell.open_new_course_dialog)

        self.assertIn(
            '("Kurs", "Kursstufe", "Kursfarbe", "Status", "")',
            source,
        )
        self.assertIn("self._course_color_cell(item)", source)
        self.assertIn("CourseBadge(item.color_name, item.color_hex)", source)
        self.assertIn("dient zur Orientierung und Zugehörigkeit", source)
        self.assertNotIn('marker.setObjectName("CourseColorMarker")', source)
        self.assertNotIn('QTableWidgetItem(f"●', source)
        self.assertIn("COURSE_COLOR_OPTIONS", dialog_source)
        self.assertIn('form.addRow("Farbe", self.color_select)', dialog_source)
        self.assertIn(
            'form.addRow("Kursstufe", self.year_level_select)',
            dialog_source,
        )
        self.assertIn("include_color=True", shell_source)
        self.assertIn("include_year_level=True", shell_source)
        self.assertIn("dialog.color_hex()", shell_source)
        self.assertIn("dialog.year_level()", shell_source)

    def test_student_list_items_include_course_color(self) -> None:
        students = self.adapter.list_students()

        self.assertEqual(students[0].group_name, "Grashüpfer")
        self.assertIn(students[0].course_name, {"Kurs 1", "Kurs 2", "Kurs 3"})
        self.assertIn(students[0].course_color_name, {"Blau", "Grün", "Orange"})
        self.assertIn(
            students[0].course_color_hex,
            {"#2563EB", "#16A34A", "#F97316"},
        )

        course_badges = tuple(
            components.CourseBadge(course_name, color_hex)
            for course_name, color_hex in (
                ("Kurs 1", "#2563EB"),
                ("Kurs 2", "#16A34A"),
                ("Kurs 3", "#F97316"),
            )
        )
        self.assertEqual(
            tuple(badge.label.text() for badge in course_badges),
            ("Kurs 1", "Kurs 2", "Kurs 3"),
        )
        self.assertEqual(
            tuple(badge.property("courseColorHex") for badge in course_badges),
            ("#2563EB", "#16A34A", "#F97316"),
        )
        for badge, expected_color in zip(
            course_badges,
            ("#2563EB", "#16A34A", "#F97316"),
            strict=True,
        ):
            self.assertIn(f"background-color: {expected_color}", badge.styleSheet())

    def test_students_screen_shows_course_color_marker(self) -> None:
        source = inspect.getsource(importlib.import_module(
            "src.desktop_app.screens.students_screen"
        ))

        self.assertIn(
            '"Name", "Stammgruppe", "Kurs", "Dokumentation", "Aktion"',
            source,
        )
        self.assertIn(
            "self.table.setCellWidget(row_index, 2, self._course_cell(student))",
            source,
        )
        self.assertIn(
            "CourseBadge(student.course_name, student.course_color_hex)",
            source,
        )
        self.assertNotIn('marker.setObjectName("CourseColorMarker")', source)
        self.assertIn("QHeaderView.ResizeMode.Fixed", source)
        self.assertIn("self.table.setColumnWidth(2, 150)", source)
        self.assertIn("self.table.setColumnWidth(4, 250)", source)
        self.assertIn('"Stammgruppe", "Kurs"', source)
        self.assertIn("self.table.setItem(row_index, 1, group_item)", source)

    def test_overview_screen_shows_master_data_groups_and_courses(self) -> None:
        source = inspect.getsource(overview_screen)
        shell_source = inspect.getsource(shell.AppShell.refresh_overview)

        self.assertIn("MasterDataViewModel", source)
        self.assertIn("MasterDataItemViewModel", source)
        self.assertIn("CourseGroupViewModel", source)
        self.assertIn("def set_master_data(", source)
        self.assertIn("view_model.groups", source)
        self.assertIn("view_model.course_groups", source)
        self.assertIn("course_group.selected_group_ids", source)
        self.assertIn("course_group.selected_course_ids", source)
        self.assertIn("course_selected = Signal(str, str)", source)
        self.assertIn('marker.setObjectName("CourseColorMarker")', source)
        self.assertIn('QColor(course.color_hex or "#6B7280")', source)
        self.assertNotIn('QLabel("●")', source)
        self.assertIn("self.master_data_adapter.view_model()", shell_source)
        self.assertIn("self.adapter.list_group_summaries()", shell_source)

    def test_master_data_screen_shows_course_groups(self) -> None:
        source = inspect.getsource(master_data_screen)
        dialog_source = inspect.getsource(master_data_dialog)
        shell_source = inspect.getsource(shell.AppShell.open_edit_course_group_dialog)

        self.assertIn("Noch keine Kursverbünde angelegt.", source)
        self.assertIn('"Kursverbünde"', source)
        self.assertIn('"+ Kursverbund"', source)
        self.assertIn("course_group_add_requested = Signal()", source)
        self.assertIn("course_group_edit_requested = Signal(str)", source)
        self.assertIn("self.course_group_table = QTableWidget(0, 3)", source)
        self.assertIn(
            'table.setHorizontalHeaderLabels(("Kursverbund", "Zuordnung", ""))',
            source,
        )
        self.assertIn("item.selected_group_ids", source)
        self.assertIn("item.selected_course_ids", source)
        self.assertIn('QLabel(f"Stammgruppen · {group_names or \'Keine\'}")', source)
        self.assertIn('QLabel(f"Kurse · {course_names or \'Keine\'}")', source)
        self.assertIn('edit_button = QPushButton("Bearbeiten")', source)
        self.assertIn("CourseGroupDialog", dialog_source)
        self.assertIn("QCheckBox", dialog_source)
        self.assertIn("COURSE_GROUP_EMPTY_GROUPS_MESSAGE", dialog_source)
        self.assertIn("COURSE_GROUP_EMPTY_COURSES_MESSAGE", dialog_source)
        self.assertIn("configure_save_cancel_buttons(buttons)", dialog_source)
        self.assertIn("open_new_course_group_dialog", inspect.getsource(shell.AppShell))
        self.assertIn("add_course_group(", inspect.getsource(shell.AppShell.open_new_course_group_dialog))
        self.assertIn("update_course_group(", shell_source)
        self.assertIn("_clear_invalid_course_group_filter", shell_source)

    def test_course_group_filter_limits_course_to_selected_groups(self) -> None:
        with self.database.connect() as connection:
            with connection:
                connection.execute(
                    "INSERT INTO groups (group_id, group_name, active) VALUES (?, ?, ?)",
                    (f"{GROUP_ID_PREFIX}-000002", "Füchse", 1),
                )
                connection.execute(
                    """
                    INSERT INTO students (
                        student_id,
                        first_name,
                        last_name,
                        notes,
                        active,
                        created_at,
                        updated_at,
                        archived_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"{STUDENT_ID_PREFIX}-999999",
                        "Test",
                        "Fuchs",
                        "",
                        1,
                        "2026-07-02",
                        "2026-07-02",
                        None,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO student_school_year_assignments(
                        assignment_id,
                        student_id,
                        school_year_id,
                        group_id,
                        course_id,
                        assignment_status,
                        valid_from,
                        valid_to,
                        created_at,
                        updated_at
                    )
                    SELECT
                        'ASG-999999',
                        ?,
                        school_year_id,
                        ?,
                        ?,
                        'enrolled',
                        start_date,
                        end_date,
                        '2026-07-02',
                        '2026-07-02'
                    FROM school_years
                    WHERE status = 'current'
                    """,
                    (
                        f"{STUDENT_ID_PREFIX}-999999",
                        f"{GROUP_ID_PREFIX}-000002",
                        f"{COURSE_ID_PREFIX}-000001",
                    ),
                )

        adapter = StudentDesktopAdapter(self.database_path)
        global_course_students = adapter.list_students(
            course_id=f"{COURSE_ID_PREFIX}-000001",
        )
        course_group_students = adapter.list_students(
            course_id=f"{COURSE_ID_PREFIX}-000001",
            group_ids=(f"{GROUP_ID_PREFIX}-000001",),
        )

        self.assertIn(
            f"{STUDENT_ID_PREFIX}-999999",
            {student.student_id for student in global_course_students},
        )
        self.assertNotIn(
            f"{STUDENT_ID_PREFIX}-999999",
            {student.student_id for student in course_group_students},
        )
        self.assertTrue(all(
            student.group_id == f"{GROUP_ID_PREFIX}-000001"
            for student in course_group_students
        ))

    def test_student_list_search_and_empty_states_are_polished(self) -> None:
        source = inspect.getsource(students_screen)

        self.assertIn('STUDENT_SEARCH_PLACEHOLDER = "Schüler suchen …"', source)
        self.assertIn("Noch keine Schüler vorhanden.", source)
        self.assertIn("Lege über „Schüler anlegen“ den ersten Schüler an.", source)
        self.assertIn("Keine Schüler passen zu dieser Suche.", source)
        self.assertIn("lösche ihn mit Escape", source)
        self.assertIn("SearchField(STUDENT_SEARCH_PLACEHOLDER)", source)
        self.assertIn("setClearButtonEnabled(True)", inspect.getsource(components))
        self.assertIn("self.search_input.text().strip()", source)

    def test_master_data_empty_states_are_registered(self) -> None:
        source = inspect.getsource(master_data_screen)

        self.assertIn(
            "Noch keine Stammgruppen angelegt.",
            source,
        )
        self.assertIn(
            "Noch keine Kurse angelegt.",
            source,
        )
        self.assertIn("self.group_empty_state.setVisible(not items)", source)
        self.assertIn("self.course_empty_state.setVisible(not items)", source)
        self.assertIn("table.setVisible(bool(items))", source)

    def test_new_student_dialog_uses_master_data_for_group_and_course_options(self) -> None:
        source = inspect.getsource(new_student_dialog)
        shell_source = inspect.getsource(shell.AppShell.open_new_student_dialog)

        self.assertIn("MasterDataDesktopAdapter", source)
        self.assertIn("self.master_data_adapter.view_model()", source)
        self.assertIn("master_data.active_groups", source)
        self.assertIn("master_data.active_courses", source)
        self.assertIn(
            "self.current_school_year = self.adapter.current_school_year()",
            source,
        )
        self.assertIn("self._populate_master_data_select(", source)
        self.assertIn("select.addItem(item.name, item.item_id)", source)
        self.assertIn("master_data_payload = {", source)
        self.assertIn("result = self.adapter.save_existing_student(", source)
        self.assertIn("layout.addWidget(self._membership_card())", source)
        self.assertIn("self._create_dialog(NewStudentDialog, self.adapter, self.master_data_adapter)", shell_source)

    def test_new_student_dialog_uses_required_dropdown_placeholders(self) -> None:
        source = inspect.getsource(new_student_dialog)

        self.assertIn('STUDENT_DIALOG_SELECT_PLACEHOLDER = "Bitte auswählen"', source)
        self.assertIn('"Keine Stammgruppen – zuerst unter Stammdaten anlegen"', source)
        self.assertIn('"Keine Kurse – zuerst unter Stammdaten anlegen"', source)
        self.assertIn("select.addItem(STUDENT_DIALOG_SELECT_PLACEHOLDER, \"\")", source)

    def test_new_student_dialog_validates_name_group_and_course(self) -> None:
        source = inspect.getsource(new_student_dialog)

        self.assertIn('STUDENT_DIALOG_EMPTY_NAME_MESSAGE = "Bitte einen Namen eingeben."', source)
        self.assertIn(
            'STUDENT_DIALOG_GROUP_REQUIRED_MESSAGE = "Bitte eine Stammgruppe auswählen."',
            source,
        )
        self.assertIn(
            'STUDENT_DIALOG_COURSE_REQUIRED_MESSAGE = "Bitte einen Kurs auswählen."',
            source,
        )
        self.assertIn("if not self.first_name_input.text().strip()", source)
        self.assertIn("if not self.last_name_input.text().strip()", source)
        self.assertIn("if group is None", source)
        self.assertIn("if course is None", source)
        self.assertIn("if not group.is_persistent", source)
        self.assertIn("if not course.is_persistent", source)

    def test_new_student_dialog_widgets_do_not_access_sqlite_directly(self) -> None:
        source = inspect.getsource(new_student_dialog)

        self.assertNotIn("sqlite", source.casefold())
        self.assertNotIn("INSERT INTO", source)
        self.assertNotIn("UPDATE ", source)
        self.assertNotIn("DELETE FROM", source)

    def test_selected_student_creates_profile_view_model(self) -> None:
        students = self.adapter.list_students()
        profile = self.adapter.get_student_profile(students[0].student_id)

        self.assertIsNotNone(profile)
        self.assertEqual(profile.student_id, students[0].student_id)
        self.assertEqual(profile.display_name, students[0].display_name)
        self.assertEqual(profile.group_name, "Grashüpfer")
        self.assertIn(profile.course_name, {"Kurs 1", "Kurs 2", "Kurs 3"})
        self.assertIn(profile.course_color_name, {"Blau", "Grün", "Orange"})
        self.assertIn(
            profile.course_color_hex,
            {"#2563EB", "#16A34A", "#F97316"},
        )
        self.assertIsInstance(profile.student_notes, str)
        self.assertTrue(profile.active)

    def test_student_profile_view_model_contains_header_and_basis_data(self) -> None:
        students = self.adapter.list_students()
        profile = self.adapter.get_student_profile(students[0].student_id)

        self.assertIsNotNone(profile)
        self.assertTrue(profile.student_id.startswith(STUDENT_ID_PREFIX))
        self.assertEqual(profile.display_name, students[0].display_name)
        self.assertEqual(profile.group_name, students[0].group_name)
        self.assertEqual(profile.course_name, students[0].course_name)
        self.assertIsInstance(profile.student_notes, str)

        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(profile)
        self.assertEqual(
            screen.meta_label.text(),
            f"Aktuelle Zuordnung · Stammgruppe {profile.group_name}",
        )
        self.assertEqual(screen.course_badge.label.text(), profile.course_name)
        self.assertEqual(
            screen.course_badge.property("courseColorHex"),
            profile.course_color_hex,
        )
        self.assertEqual(
            screen.course_badge.accessibleName(),
            f"Kurszugehörigkeit: {profile.course_name}",
        )

    def test_student_documentation_subjects_start_collapsed_with_summary(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        projection = StudentDocumentationSubjectProjectionViewModel(
            school_year_id="SY-2026-27",
            school_year_label="2026/27",
            mode="custom",
            available_subjects=(
                StudentDocumentationSubjectOptionViewModel("deutsch", "Deutsch"),
                StudentDocumentationSubjectOptionViewModel(
                    "mathematik",
                    "Mathematik",
                ),
                StudentDocumentationSubjectOptionViewModel("epu", "EPU"),
            ),
            selected_subject_ids=("deutsch", "mathematik"),
            is_read_only=False,
            retained_inactive_subjects=(
                StudentDocumentationSubjectOptionViewModel(
                    "kreatives_gestalten",
                    "Kreatives Gestalten",
                ),
            ),
        )

        screen.set_documentation_subjects(projection)

        self.assertTrue(screen.documentation_subjects_body.isHidden())
        self.assertEqual(
            screen.documentation_subject_summary.text(),
            "Individuelle Auswahl · 2 Fächer",
        )
        screen.documentation_subject_toggle_button.click()
        self.assertFalse(screen.documentation_subjects_body.isHidden())
        subject_checks = tuple(
            check
            for check in screen.findChildren(QCheckBox)
            if check.text() in {
                "Deutsch",
                "Mathematik",
                "EPU",
                "Kreatives Gestalten (nicht mehr verfügbar)",
            }
        )
        self.assertEqual(len(subject_checks), 4)
        self.assertTrue(all(not check.icon().isNull() for check in subject_checks))
        screen._set_documentation_subjects_expanded(False)
        screen.show_documentation_subjects_error("Speichern fehlgeschlagen")
        self.assertFalse(screen.documentation_subjects_body.isHidden())
        self.assertIsNotNone(app)

    def test_profile_placeholder_messages_are_registered(self) -> None:
        self.assertEqual(
            PROFILE_ACTION_MESSAGES["observation"],
            "Bitte zuerst einen Schüler auswählen.",
        )
        self.assertEqual(
            PROFILE_ACTION_MESSAGES["document"],
            "Dokumente werden in einem späteren Sprint verwaltet.",
        )
        self.assertEqual(
            PROFILE_ACTION_MESSAGES["edit"],
            "Bearbeiten wird in einem späteren Sprint umgesetzt.",
        )
        self.assertEqual(
            PROFILE_SECTION_PLACEHOLDERS["observations_title"],
            "Noch keine Beobachtungen vorhanden.",
        )
        self.assertEqual(
            PROFILE_SECTION_PLACEHOLDERS["observations_hint"],
            "Gespeicherte Beobachtungen erscheinen hier chronologisch.",
        )
        self.assertEqual(
            PROFILE_SECTION_PLACEHOLDERS["competencies_title"],
            "Noch keine Kompetenzbewertungen vorhanden.",
        )
        self.assertEqual(
            PROFILE_SECTION_PLACEHOLDERS["competencies_hint"],
            "Kompetenzen erscheinen hier, sobald Beobachtungen bewertet wurden.",
        )
        self.assertEqual(
            PROFILE_SECTION_PLACEHOLDERS["documents_hint"],
            "Dokumente werden schülerzentriert verwaltet.",
        )

    def test_observation_rating_options_use_required_scale(self) -> None:
        self.assertEqual(observation_rating_keys(), ("++", "+", "-", "--"))
        self.assertEqual(
            OBSERVATION_RATING_OPTIONS,
            (
                "Eigenständig und sicher",
                "Kenntnisse meist anwenden",
                "Mit Unterstützung",
                "Erste Erfahrungen",
            ),
        )

    def test_document_type_options_match_mvp_scope(self) -> None:
        self.assertEqual(
            DOCUMENT_TYPE_OPTIONS,
            (
                "Arbeitsprobe",
                "Lernzielkontrolle",
                "Gesprächsnotiz",
                "Bericht",
                "Foto",
                "Audio",
                "Sonstiges",
            ),
        )

    def obsolete_curriculum_catalog_loads_active_subjects(self) -> None:
        subjects = self.curriculum_adapter.list_active_subjects()

        self.assertEqual(
            tuple(subject.display_name for subject in subjects),
            (
                "Deutsch",
                "Mathematik",
                "EPU",
                "Musik",
                "Kunst",
                "Sport",
                "Sozialkompetenz",
                "Ethik",
                "Religion",
                "Werken",
                "Schulgarten",
            ),
        )

    def obsolete_curriculum_catalog_uses_epu_instead_of_sachunterricht(self) -> None:
        entries = self.curriculum_adapter.list_entries()
        subject_names = {entry.subject_display_name for entry in entries}
        epu_entries = [entry for entry in entries if entry.subject_key == "epu"]

        self.assertIn("EPU", subject_names)
        self.assertNotIn("Sachunterricht", subject_names)
        self.assertTrue(epu_entries)
        self.assertTrue(all(
            entry.official_subject_name == "Heimat- und Sachkunde"
            for entry in epu_entries
        ))
        self.assertTrue(all(
            entry.subject_full_name == "Epochaler Projektunterricht"
            for entry in epu_entries
        ))

    def obsolete_curriculum_catalog_entries_have_stable_id_subject_and_label(self) -> None:
        entries = self.curriculum_adapter.list_entries()
        competency_ids = [entry.competency_id for entry in entries]

        self.assertEqual(len(competency_ids), len(set(competency_ids)))
        self.assertTrue(all(entry.competency_id.startswith("CMP-") for entry in entries))
        self.assertTrue(all(entry.subject_id for entry in entries))
        self.assertTrue(all(entry.subject_display_name for entry in entries))
        self.assertTrue(all(entry.competency_label for entry in entries))
        self.assertTrue(all(entry.competency_detail_label for entry in entries))
        self.assertEqual(entries[0].competency_id, self.german_listening_competency_id)
        self.assertEqual(entries[0].subject_id, "deutsch")
        self.assertEqual(entries[-1].competency_id, "CMP-000686")
        self.assertEqual(entries[-1].subject_id, "mathematik")

    def obsolete_curriculum_catalog_refines_only_approved_math_competencies(self) -> None:
        entries = self.curriculum_adapter.list_entries()
        replaced_ids = {
            "CMP-000295", "CMP-000301", "CMP-000306", "CMP-000307",
            "CMP-000309", "CMP-000316", "CMP-000317", "CMP-000318",
            "CMP-000321", "CMP-000330", "CMP-000332", "CMP-000336",
            "CMP-000338",
        }
        by_id = {entry.competency_id: entry for entry in entries}
        current_math = [
            entry
            for entry in entries
            if entry.subject_key == "mathematik"
            and entry.catalog_status == "current"
            and entry.is_active
        ]
        time_expectations = {
            self.math_first_competency_id: (
                "Volle Stunden an Uhrendarstellungen ablesen.", "stage_1_3"
            ),
            "CMP-000669": (
                "Halbe Stunden an Uhrendarstellungen ablesen.", "stage_1_3"
            ),
            "CMP-000670": (
                "Viertelstunden an Uhrendarstellungen ablesen.", "stage_1_3"
            ),
            self.math_time_competency_id: ("Ablesen, Einstellen und Aufschreiben der Uhrzeit", "stage_4"),
            self.math_last_competency_id: ("Uhrzeiten an einer Uhr einstellen.", "cross_stage"),
            "CMP-000673": ("Uhrzeiten notieren.", "cross_stage"),
            "CMP-000674": (
                "Uhrzeiten zwischen gebräuchlichen Schreib- und Sprechweisen übertragen.",
                "cross_stage",
            ),
        }

        self.assertEqual(len(current_math), 81)
        self.assertTrue(all(
            by_id[competency_id].catalog_status == "legacy"
            and not by_id[competency_id].catalog_default_active
            and not by_id[competency_id].is_active
            for competency_id in replaced_ids
        ))
        self.assertEqual(
            {
                competency_id: (
                    by_id[competency_id].competency_text,
                    by_id[competency_id].learning_stage,
                )
                for competency_id in time_expectations
            },
            time_expectations,
        )
        self.assertFalse(any(
            entry.competency_text == "Uhrzeiten ablesen"
            for entry in current_math
        ))
        self.assertEqual(
            {
                competency_id: (
                    by_id[competency_id].competency_text,
                    by_id[competency_id].competency_label,
                )
                for competency_id in (
                    "CMP-000650", "CMP-000661", "CMP-000675", "CMP-000676",
                    "CMP-000682", "CMP-000683", "CMP-000684",
                )
            },
            {
                "CMP-000650": (
                    "Grundaufgaben der Multiplikation und Division sicher wiedergeben oder ableiten.",
                    "Multiplikation und Division",
                ),
                "CMP-000661": (
                    "Zu Sachsituationen sinnvolle Fragen formulieren.",
                    "Fragen zu Sachsituationen",
                ),
                "CMP-000675": (
                    "Einheiten für Geld, Länge, Zeitdauer und Datum sachgerecht gebrauchen und Größen in verschiedenen Schreibweisen angeben.",
                    "Geld, Länge, Zeit und Datum",
                ),
                "CMP-000676": (
                    "Erweiterte Einheiten für Länge und Zeitdauer sowie Einheiten für Masse und Volumen sachgerecht gebrauchen und Größen in verschiedenen Schreibweisen angeben.",
                    "Masse, Volumen und erweiterte Einheiten",
                ),
                "CMP-000682": (
                    "Vierecke, Dreiecke und Kreise in Umwelt, Bildern und Skizzen zeigen und benennen.",
                    "Vierecke, Dreiecke, Kreise",
                ),
                "CMP-000683": (
                    "Erweiterte Vierecks- und Dreiecksarten sowie weitere Vielecke zeigen, benennen und beschreiben.",
                    "Vierecks- und Dreiecksarten",
                ),
                "CMP-000684": (
                    "Vierecke, Dreiecke, Kreise und weitere Vielecke nach ihren Eigenschaften unterscheiden und Beziehungen zwischen Flächen beschreiben.",
                    "Flächen nach Eigenschaften",
                ),
            },
        )

    def obsolete_curriculum_catalog_maps_kunst_to_kunsterziehung(self) -> None:
        kunst_entries = [
            entry
            for entry in self.curriculum_adapter.list_entries()
            if entry.subject_key == "kunst"
        ]

        self.assertTrue(kunst_entries)
        self.assertTrue(all(
            entry.subject_display_name == "Kunst"
            for entry in kunst_entries
        ))
        self.assertTrue(all(
            entry.official_subject_name == "Kunsterziehung"
            for entry in kunst_entries
        ))

    def obsolete_curriculum_catalog_contains_extended_subjects(self) -> None:
        subjects = {
            subject.display_name
            for subject in self.curriculum_adapter.list_active_subjects()
            if not subject.is_core_subject
        }

        self.assertEqual(subjects, {"Ethik", "Religion", "Werken", "Schulgarten"})

    def obsolete_curriculum_catalog_keeps_social_competence_as_own_subject(self) -> None:
        subjects = self.curriculum_adapter.list_active_subjects()
        social_subjects = [
            subject
            for subject in subjects
            if subject.subject_key == "sozialkompetenz"
        ]
        social_competencies = self.curriculum_adapter.list_competencies_for_subject(
            "sozialkompetenz"
        )

        self.assertEqual(len(social_subjects), 1)
        self.assertEqual(social_subjects[0].display_name, "Sozialkompetenz")
        self.assertGreaterEqual(len(social_competencies), 1)
        self.assertTrue(all(
            entry.subject_display_name == "Sozialkompetenz"
            for entry in social_competencies
        ))

    def obsolete_curriculum_catalog_filters_competencies_by_subject(self) -> None:
        epu_competencies = self.curriculum_adapter.list_competencies_for_subject("epu")
        math_competencies = self.curriculum_adapter.list_competencies_for_subject("mathematik")

        self.assertGreaterEqual(len(epu_competencies), 30)
        self.assertTrue(all(entry.subject_key == "epu" for entry in epu_competencies))
        self.assertTrue(any(
            entry.learning_area == "Natur und Technik"
            for entry in epu_competencies
        ))
        self.assertTrue(all(
            entry.subject_key == "mathematik"
            for entry in math_competencies
        ))
        self.assertTrue(any(
            entry.competency_group == "Zeit"
            and entry.competency_text
            == "Ablesen, Einstellen und Aufschreiben der Uhrzeit"
            for entry in math_competencies
        ))

    def obsolete_curriculum_catalog_exposes_subject_area_topic_and_competency_structure(
        self,
    ) -> None:
        entries = self.curriculum_adapter.list_entries()
        by_subject = {
            subject: [entry for entry in entries if entry.subject_key == subject]
            for subject in ("deutsch", "mathematik", "epu", "sozialkompetenz")
        }

        self.assertTrue(all(by_subject.values()))
        self.assertTrue(any(
            entry.learning_area == "Mit Texten und Medien umgehen"
            and entry.competency_group == "Lesefluessigkeit"
            and entry.competency_text == "einen geuebten Text sinngestaltend und verstaendlich vorlesen"
            for entry in by_subject["deutsch"]
        ))
        self.assertTrue(any(
            entry.learning_area
            == "Größenvorstellungen nutzen und mit Größen umgehen"
            and entry.competency_group == "Zeit"
            and entry.competency_text
            == "Ablesen, Einstellen und Aufschreiben der Uhrzeit"
            for entry in by_subject["mathematik"]
        ))
        self.assertTrue(any(
            entry.learning_area == "Natur und Umwelt"
            and entry.competency_group == "Beobachten"
            and entry.competency_text == "ein Naturphaenomen genau beobachten und mit passenden Worten beschreiben"
            for entry in by_subject["epu"]
        ))
        self.assertTrue(any(
            entry.learning_area == "Zusammenarbeit"
            and entry.competency_group == "Absprachen"
            and entry.competency_text == "eine vereinbarte Aufgabe in der Partner- oder Gruppenarbeit übernehmen"
            for entry in by_subject["sozialkompetenz"]
        ))

    def obsolete_curriculum_catalog_uses_specific_labels_for_concrete_competencies(
        self,
    ) -> None:
        math_written_entries = [
            entry
            for entry in self.curriculum_adapter.list_competencies_for_subject(
                "mathematik"
            )
            if entry.learning_area == "Arithmetik - mit Zahlen und Symbolen umgehen"
            and entry.competency_group == "Addition"
        ]

        self.assertEqual(len(math_written_entries), 9)
        self.assertEqual(
            {
                entry.competency_label
                for entry in math_written_entries
            },
            {
                "Addition erklären", "Subtraktion erklären",
                "Multiplikation erklären", "Division erklären",
                "Schriftlich addieren", "Schriftlich subtrahieren",
                "Schriftlich multiplizieren", "Schriftlich dividieren",
                "Schriftlich pruefen",
            },
        )
        self.assertGreater(
            len({entry.competency_label for entry in math_written_entries}),
            1,
        )

    def obsolete_curriculum_catalog_groups_competencies_by_subject(self) -> None:
        groups = self.curriculum_adapter.list_competencies_grouped_by_subject()
        group_by_subject = {group.subject.subject_key: group for group in groups}

        self.assertIn("deutsch", group_by_subject)
        self.assertIn("epu", group_by_subject)
        self.assertIn("sozialkompetenz", group_by_subject)
        self.assertEqual(group_by_subject["epu"].subject.display_name, "EPU")
        self.assertEqual(
            {
                entry.subject_id
                for entry in group_by_subject["epu"].competencies
            },
            {"epu"},
        )
        self.assertTrue(all(
            group.competencies
            for group in groups
        ))

    def obsolete_curriculum_competency_options_have_short_display_labels(self) -> None:
        math_competency = next(
            entry
            for entry in self.curriculum_adapter.list_competencies_for_subject(
                "mathematik"
            )
            if entry.competency_id == self.math_time_competency_id
        )

        self.assertEqual(math_competency.competency_display_name, "Minutengenau ablesen")
        self.assertEqual(math_competency.competency_label, "Minutengenau ablesen")
        self.assertNotEqual(
            math_competency.competency_display_name,
            math_competency.learning_area,
        )
        self.assertNotEqual(
            math_competency.competency_display_name,
            math_competency.competency_text,
        )
        self.assertIn(
            math_competency.competency_text,
            math_competency.competency_detail_label,
        )

    def test_observation_dialog_uses_curriculum_catalog_data(self) -> None:
        source = inspect.getsource(new_observation_dialog)
        view_model_source = inspect.getsource(importlib.import_module(
            "src.desktop_app.view_models.observation_view_model"
        ))

        self.assertIn("competency_subject_groups", source)
        self.assertIn("ObservationCompetencySubjectGroupViewModel", source)
        self.assertIn("currentIndexChanged.connect(self._refresh_competencies)", source)
        self.assertNotIn("_fallback_subject_group", source)
        self.assertNotIn("list_competencies_for_subject", source)
        self.assertNotIn("OBSERVATION_SUBJECT_OPTIONS", source)
        self.assertNotIn("OBSERVATION_COMPETENCY_OPTIONS", source)
        self.assertNotIn("Sachunterricht", view_model_source)

    def test_observation_dialog_projection_uses_fresh_catalog_stage_metadata(self) -> None:
        competencies = {
            competency.competency_id: competency
            for subject in self.adapter.list_observation_competency_subject_groups(
                f"{STUDENT_ID_PREFIX}-000001"
            )
            for area in subject.learning_area_groups
            for topic in area.competency_groups
            for competency in topic.competencies
        }

        self.assertEqual(competencies[self.math_first_competency_id].learning_stage, "cross_stage")
        self.assertEqual(competencies[self.math_time_competency_id].learning_stage, "cross_stage")
        self.assertEqual(competencies[self.math_last_competency_id].learning_stage, "cross_stage")

    def test_observation_dialog_uses_passed_documentation_subject_options(self) -> None:
        app = QApplication.instance() or QApplication([])
        dialog = new_observation_dialog.NewObservationDialog(
            self._sample_student_detail(),
            self.curriculum_adapter,
            self.adapter,
            subject_options=(
                ObservationSubjectOptionViewModel("deutsch", "Deutsch"),
                ObservationSubjectOptionViewModel("mathematik", "Mathematik"),
            ),
        )

        subject_labels = tuple(
            dialog.subject_select.itemText(index)
            for index in range(dialog.subject_select.count())
        )

        self.assertEqual(subject_labels, ("Fächer", "Deutsch", "Mathematik"))
        self.assertNotIn("EPU", subject_labels)
        self.assertTrue(dialog.subject_select.itemIcon(0).isNull())
        self.assertTrue(all(
            not dialog.subject_select.itemIcon(index).isNull()
            for index in range(1, dialog.subject_select.count())
        ))
        dialog.subject_select.setCurrentIndex(1)
        app.processEvents()
        self.assertIsNotNone(app)

    def test_observation_dialog_keeps_initial_additional_subject(self) -> None:
        self._save_custom_documentation_subjects(
            f"{STUDENT_ID_PREFIX}-000001",
            ("deutsch", "mathematik"),
        )
        initial_draft = self._sample_observation_draft(
            subject_id="musik",
            subject_display_name="Musik",
            competency_ratings=(
                self._sample_observation_rating(
                    self.music_listening_competency_id,
                    "musik",
                    "Musik",
                    "Musik hören",
                    "Allgemein",
                    "Musik aufmerksam hören, Eindrücke beschreiben und "
                    "musikalische Merkmale erkennen",
                    "+",
                ),
            ),
        )
        dialog = self._observation_dialog_with_hierarchy(initial_draft)

        draft = dialog.create_draft()

        self.assertEqual(dialog.subject_select.currentData(), "musik")
        self.assertEqual(dialog.subject_select.currentText(), "Musik")
        self.assertEqual(draft.subject_id, "musik")
        self.assertEqual(draft.competency_ratings[0].subject_key, "musik")
        self.assertEqual(draft.competency_ratings[0].subject_display_name, "Musik")
        self.assertIn(self.music_listening_competency_id, dialog.competency_rating_entries)
        self.assertTrue(dialog.competency_catalog_tiles[self.music_listening_competency_id].is_selected())
        markers = dialog.findChildren(components.SubjectAccentMarker)
        self.assertTrue(markers)
        self.assertTrue(all(
            marker.property("subjectId") == "musik"
            for marker in markers
        ))

    def test_observation_dialog_keeps_current_context_selected(self) -> None:
        dialog = self._observation_dialog_with_hierarchy(
            self._sample_observation_draft(context="Partnerarbeit")
        )

        self.assertEqual(dialog.context_select.currentText(), "Partnerarbeit")
        self.assertEqual(dialog.create_draft().context, "Partnerarbeit")

    def test_observation_dialog_keeps_legacy_and_empty_contexts_without_fallback(
        self,
    ) -> None:
        for stored_context, visible_label in (
            ("Freiarbeit", "Freiarbeit · Nicht mehr verfügbar"),
            ("", "Kein Kontext gespeichert · Nicht mehr verfügbar"),
        ):
            with self.subTest(stored_context=stored_context):
                dialog = self._observation_dialog_with_hierarchy(
                    self._sample_observation_draft(context=stored_context)
                )

                self.assertEqual(dialog.context_select.currentText(), visible_label)
                self.assertEqual(dialog.create_draft().context, stored_context)
                self.assertNotEqual(
                    dialog.context_select.currentText(),
                    OBSERVATION_CONTEXT_OPTIONS[0],
                )
                self.assertEqual(
                    dialog.context_select.accessibleName(),
                    "Beobachtungskontext",
                )

    def test_observation_dialog_legacy_context_can_be_changed_by_keyboard(self) -> None:
        dialog = self._observation_dialog_with_hierarchy(
            self._sample_observation_draft(context="Freiarbeit")
        )

        dialog.context_select.setFocus()
        QTest.keyClick(dialog.context_select, Qt.Key.Key_Home)

        self.assertEqual(
            dialog.create_draft().context,
            OBSERVATION_CONTEXT_OPTIONS[0],
        )

    def test_new_observation_dialog_only_lists_registered_contexts(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self.assertEqual(
            tuple(
                dialog.context_select.itemText(index)
                for index in range(dialog.context_select.count())
            ),
            OBSERVATION_CONTEXT_OPTIONS,
        )
        self.assertIn("Partnerarbeit", OBSERVATION_CONTEXT_OPTIONS)

    def test_edit_save_preserves_legacy_context_and_all_other_observation_fields(
        self,
    ) -> None:
        original = self._sample_observation_draft(context="Freiarbeit")
        self.adapter.save_observation(original)
        loaded = self.adapter.observation_draft_for_edit("OBS-000001")
        self.assertIsNotNone(loaded)
        if loaded is None:
            raise AssertionError("Expected persisted observation draft")
        dialog = self._observation_dialog_with_hierarchy(loaded)

        result = self.adapter.update_observation(dialog.create_draft())
        unchanged = self.adapter.observation_draft_for_edit("OBS-000001")

        self.assertIsInstance(result, SuccessResult)
        self.assertIsNotNone(unchanged)
        if unchanged is None:
            raise AssertionError("Expected updated observation draft")
        self.assertEqual(unchanged.context, "Freiarbeit")
        self.assertEqual(unchanged.date_text, original.date_text)
        self.assertEqual(unchanged.subject_id, original.subject_id)
        self.assertEqual(unchanged.note, original.note)
        self.assertEqual(unchanged.competency_ratings, original.competency_ratings)
        self.assertEqual(unchanged.attachments, original.attachments)

        dialog = self._observation_dialog_with_hierarchy(unchanged)
        dialog.context_select.setCurrentText("Präsentation")
        changed_result = self.adapter.update_observation(dialog.create_draft())
        changed = self.adapter.observation_draft_for_edit("OBS-000001")

        self.assertIsInstance(changed_result, SuccessResult)
        self.assertIsNotNone(changed)
        if changed is None:
            raise AssertionError("Expected deliberately updated observation draft")
        self.assertEqual(changed.context, "Präsentation")
        self.assertEqual(changed.date_text, original.date_text)
        self.assertEqual(changed.subject_id, original.subject_id)
        self.assertEqual(changed.note, original.note)
        self.assertEqual(changed.competency_ratings, original.competency_ratings)
        self.assertEqual(changed.attachments, original.attachments)

    def test_observation_dialog_uses_scalable_three_zone_workspace(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        splitter = dialog.findChild(QSplitter, "ObservationThreeZoneWorkspace")

        self.assertIsNotNone(splitter)
        if splitter is not None:
            self.assertEqual(splitter.count(), 3)
            self.assertEqual(splitter.widget(0).maximumWidth(), 330)
            self.assertEqual(splitter.widget(2).maximumWidth(), 338)
        self.assertEqual(dialog.size().width(), 1400)
        self.assertEqual(dialog.size().height(), 900)
        self.assertGreaterEqual(dialog.minimumWidth(), 1180)
        self.assertGreaterEqual(dialog.minimumHeight(), 680)
        self.assertIsInstance(dialog.selected_scroll, QScrollArea)
        self.assertIsInstance(dialog.catalog_scroll, QScrollArea)
        self.assertIsNot(dialog.catalog_scroll, dialog.selected_scroll)
        self.assertIs(dialog.catalog_scroll.widget(), dialog.catalog_content)
        self.assertEqual(
            dialog.catalog_search_input.placeholderText(), "Kompetenzen durchsuchen …"
        )

    def test_observation_dialog_keeps_two_selected_rows_visible_and_more_scrollable(
        self,
    ) -> None:
        app = QApplication.instance() or QApplication([])
        previous_stylesheet = app.styleSheet()
        self.addCleanup(app.setStyleSheet, previous_stylesheet)
        theme.apply_app_theme(app)
        dialog = self._observation_dialog_with_hierarchy()
        self.addCleanup(dialog.close)
        self._select_observation_subject(dialog, "mathematik")
        visible_options = tuple(
            competency
            for subject in dialog.competency_subject_groups
            if subject.subject_key == "mathematik"
            for area in subject.learning_area_groups
            for topic in area.competency_groups
            for competency in topic.competencies
            if competency.competency_id in dialog.competency_catalog_tiles
        )
        competency_ids = tuple(
            competency.competency_id
            for competency in sorted(
                visible_options,
                key=lambda item: len(dialog._competency_display_text(item)),
                reverse=True,
            )[:3]
        )
        for competency_id in competency_ids:
            dialog.competency_catalog_tiles[competency_id]._activate()
        dialog.resize(1180, 760)
        dialog.show()
        app.processEvents()

        rows = tuple(
            sorted(
                dialog.competency_rating_rows.values(),
                key=lambda row: row.geometry().top(),
            )
        )
        self.assertLess(
            rows[1].geometry().bottom(),
            dialog.selected_scroll.viewport().height(),
        )
        self.assertGreater(dialog.selected_scroll.verticalScrollBar().maximum(), 0)
        self.assertGreaterEqual(dialog.catalog_scroll.viewport().height(), 100)
        self.assertIsNotNone(app)

    def test_observation_dialog_shows_fresh_catalog_without_stage_switches(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")

        subject_group = dialog._current_subject_group()
        self.assertIsNotNone(subject_group)
        assert subject_group is not None
        expected_competency_ids = {
            competency.competency_id
            for area_group in subject_group.learning_area_groups
            for topic_group in area_group.competency_groups
            for competency in topic_group.competencies
            if competency.catalog_status == "current" and competency.is_active
        }
        self.assertEqual(
            set(dialog.competency_catalog_tiles),
            expected_competency_ids,
        )
        self.assertIsNone(
            dialog.findChild(QWidget, "ObservationLearningStageFilter")
        )
        visible_texts = {
            label.text() for label in dialog.findChildren(QLabel)
        }
        self.assertNotIn("Passende Kompetenzen", visible_texts)
        self.assertNotIn("Klassenstufe 4", visible_texts)
        self.assertNotIn("Alle Kompetenzen", visible_texts)

    def test_observation_dialog_ui_sprint_four_accessibility_contract(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        actions = dialog.findChild(QDialogButtonBox, "ObservationPersistentActions")
        save_button = actions.button(QDialogButtonBox.StandardButton.Save)

        self.assertEqual(dialog.catalog_search_input.accessibleName(), "Kompetenzkatalog durchsuchen")
        self.assertEqual(dialog.subject_select.accessibleName(), "Fach für den Kompetenzkatalog")
        self.assertEqual(dialog.note_input.accessibleName(), "Beobachtungsnotiz")
        self.assertEqual(save_button.accessibleName(), "Beobachtung speichern")
        self.assertIsNone(
            dialog.findChild(QWidget, "ObservationLearningStageFilter")
        )

    def test_observation_dialog_validation_is_inline_and_near_persistent_actions(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        dialog.save_draft()

        self.assertFalse(dialog.validation_message.isHidden())
        self.assertEqual(
            dialog.validation_message.label.text(),
            OBSERVATION_SAVE_VALIDATION_MESSAGE,
        )
        self.assertEqual(dialog.validation_message.property("messageTone"), "warning")
        self.assertIs(
            dialog.validation_message.parentWidget(),
            dialog.findChild(QDialogButtonBox, "ObservationPersistentActions").parentWidget(),
        )

    def test_observation_dialog_resizes_for_supported_desktop_geometries(self) -> None:
        app = QApplication.instance() or QApplication([])
        dialog = self._observation_dialog_with_hierarchy()
        actions = dialog.findChild(QDialogButtonBox, "ObservationPersistentActions")
        self._select_observation_subject(dialog, "mathematik")
        dialog.competency_catalog_tiles[self.math_time_competency_id]._activate()
        selector = dialog.competency_rating_widgets[self.math_time_competency_id]
        full_labels = tuple(OBSERVATION_RATING_OPTIONS)
        rating_tokens = tuple(selector.buttons)

        for width, height in ((1400, 900), (1280, 800), (1180, 760)):
            dialog.resize(width, height)
            dialog.show()
            app.processEvents()
            with self.subTest(width=width, height=height):
                self.assertGreaterEqual(dialog.width(), 1180)
                self.assertGreaterEqual(dialog.height(), 680)
                self.assertFalse(actions.isHidden())
                self.assertEqual(
                    dialog.catalog_scroll.horizontalScrollBar().maximum(),
                    0,
                )
                self.assertEqual(
                    dialog.selected_scroll.horizontalScrollBar().maximum(),
                    0,
                )
                self.assertEqual(
                    len({button.y() for button in selector.buttons.values()}),
                    1,
                )
                visible_labels = tuple(
                    button.text().removeprefix("✓ ")
                    for button in selector.buttons.values()
                )
                if selector.width() >= selector.FULL_LABEL_MINIMUM_WIDTH:
                    self.assertEqual(visible_labels, full_labels)
                    self.assertTrue(
                        all(
                            not button.property("compact")
                            for button in selector.buttons.values()
                        )
                    )
                    self.assertTrue(
                        all(
                            not button.toolTip()
                            for button in selector.buttons.values()
                        )
                    )
                elif width == 1180:
                    from src.application.competency_development_levels import DEVELOPMENT_LEVEL_COMPACT_LABELS
                    self.assertEqual(visible_labels, tuple(DEVELOPMENT_LEVEL_COMPACT_LABELS[token] for token in rating_tokens))
                    self.assertTrue(
                        all(
                            button.property("compact")
                            for button in selector.buttons.values()
                        )
                    )
                    self.assertEqual(
                        tuple(button.toolTip() for button in selector.buttons.values()),
                        full_labels,
                    )
                    self.assertTrue(
                        all(
                            full_label in button.accessibleName()
                            for button, full_label in zip(
                                selector.buttons.values(),
                                full_labels,
                                strict=True,
                            )
                        )
                    )
        dialog.close()

    def test_observation_dialog_topics_start_collapsed(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        area_button = next(
            button
            for area_key, button in dialog.competency_area_buttons.items()
            if area_key.endswith(
                "|Größenvorstellungen nutzen und mit Größen umgehen"
            )
        )
        topic_button = self._observation_topic_button(dialog, "Zeit")
        topic_container = self._observation_topic_container(dialog, "Zeit")

        self.assertEqual(
            area_button.text(),
            "▸ Kompetenzbereich: Größenvorstellungen nutzen und mit Größen umgehen",
        )
        self.assertEqual(topic_button.text(), "▸ Thema: Zeit")
        self.assertTrue(topic_container.isHidden())

    def test_observation_dialog_catalog_search_matches_all_catalog_text_fields(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")

        for search_text in (
            "ablesen",  # vollständiger Kompetenztext
            "Uhrzeit",  # Kompetenztext
            "Zeit",  # Thema
            "Größenvorstellungen",  # Kompetenzbereich
        ):
            dialog.catalog_search_input.setText(search_text)
            self.assertIn(self.math_time_competency_id, dialog.competency_catalog_tiles)
            self.assertIn("gefunden", dialog.catalog_search_result_label.text())

    def test_observation_dialog_catalog_search_ignores_case_and_outer_whitespace(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")

        dialog.catalog_search_input.setText("  uHrZeIt  ")

        self.assertIn(self.math_time_competency_id, dialog.competency_catalog_tiles)

    def test_observation_dialog_recent_competencies_follow_subject_and_search(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            competency_ratings=(
                self._recent_rating(self.math_time_competency_id),
                self._recent_rating(self.german_listening_competency_id),
            ),
        ))
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        self.assertFalse(dialog.recent_competencies_container.isHidden())
        self.assertEqual(tuple(dialog.recent_competency_chips), (self.math_time_competency_id,))
        recent_title = next(
            label
            for label in dialog.recent_competencies_container.findChildren(QLabel)
            if label.text() == "Zuletzt verwendet"
        )
        recent_text = next(
            label
            for label in dialog.recent_competency_chips[
                self.math_time_competency_id
            ].findChildren(QLabel)
            if label.text() not in {"+", "✓"}
        )
        self.assertEqual(recent_title.text(), "Zuletzt verwendet")
        self.assertFalse(recent_text.wordWrap())

        dialog.catalog_search_input.setText("Uhrzeit")
        self.assertTrue(dialog.recent_competencies_container.isHidden())
        dialog.catalog_search_input.clear()
        self.assertFalse(dialog.recent_competencies_container.isHidden())

        self._select_observation_subject(dialog, "deutsch")
        self.assertEqual(tuple(dialog.recent_competency_chips), (self.german_listening_competency_id,))

    def test_observation_competency_tooltip_only_uses_additional_description(
        self,
    ) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")
        entry = dialog.competency_catalog_tiles[self.math_time_competency_id]
        option = next(
            competency
            for subject in dialog.competency_subject_groups
            for area in subject.learning_area_groups
            for topic in area.competency_groups
            for competency in topic.competencies
            if competency.competency_id == self.math_time_competency_id
        )

        self.assertEqual(entry.toolTip(), "")
        described = replace(
            option,
            competency_label="Uhrzeit ablesen",
            competency_text="Uhrzeiten auf analogen und digitalen Uhren ablesen.",
        )
        self.assertEqual(
            dialog._competency_display_text(described),
            "Uhrzeit ablesen",
        )
        self.assertEqual(
            dialog._competency_detail_text(described),
            "Uhrzeiten auf analogen und digitalen Uhren ablesen.",
        )

    def test_observation_dialog_recent_chip_selects_once_and_disables_afterward(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            competency_ratings=(self._recent_rating(self.math_time_competency_id),),
        ))
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")
        chip = dialog.recent_competency_chips[self.math_time_competency_id]

        QTest.keyClick(chip, Qt.Key.Key_Space)

        self.assertIn(self.math_time_competency_id, dialog.competency_rating_entries)
        self.assertFalse(chip.isEnabled())
        self.assertEqual(chip.selection_signal.text(), "✓")

    def test_observation_dialog_catalog_search_shows_quiet_empty_state(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        dialog.catalog_search_input.setText("nicht vorhandener suchbegriff")

        self.assertEqual(dialog.catalog_search_result_label.text(), "0 Kompetenzen gefunden")
        self.assertIsNotNone(
            dialog.findChild(QLabel, "ObservationCatalogSearchEmptyState")
        )

    def test_observation_dialog_catalog_search_combines_with_subject_filter(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        dialog.catalog_search_input.setText("Uhrzeit")
        self._select_observation_subject(dialog, "mathematik")
        self.assertIn(self.math_time_competency_id, dialog.competency_catalog_tiles)

        self._select_observation_subject(dialog, "deutsch")

        self.assertNotIn(self.math_time_competency_id, dialog.competency_catalog_tiles)
        self.assertEqual(dialog.catalog_search_input.text(), "Uhrzeit")

    def test_observation_dialog_catalog_search_keeps_selection_and_rating(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")
        dialog.competency_catalog_tiles[self.math_time_competency_id]._activate()
        dialog.competency_rating_widgets[self.math_time_competency_id].buttons["++"].click()

        dialog.catalog_search_input.setText("nicht vorhanden")

        self.assertIn(self.math_time_competency_id, dialog.competency_rating_entries)
        self.assertEqual(
            dialog.competency_rating_widgets[self.math_time_competency_id].currentData(), "++"
        )

    def test_observation_dialog_catalog_search_does_not_remove_current_selection(self) -> None:
        initial_draft = self._sample_observation_draft(
            subject_id="musik",
            subject_display_name="Musik",
            competency_ratings=(
                self._sample_observation_rating(
                    self.music_listening_competency_id, "musik", "Musik", "Musik hören",
                    "Allgemein", "Gefühle und Stimmungen in der Musik erkennen und beschreiben", "+",
                ),
            ),
        )
        dialog = self._observation_dialog_with_hierarchy(initial_draft)

        dialog.catalog_search_input.setText("nicht vorhandener Suchtext")

        self.assertNotIn(self.music_listening_competency_id, dialog.competency_catalog_tiles)
        self.assertIn(self.music_listening_competency_id, dialog.competency_rating_entries)
        self.assertEqual(dialog.catalog_search_result_label.text(), "0 Kompetenzen gefunden")

    def test_observation_dialog_clearing_search_restores_manual_expansion_state(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")
        self._observation_topic_button(dialog, "Zeit").click()

        dialog.catalog_search_input.setText("Uhrzeit")
        self.assertFalse(self._observation_topic_container(dialog, "Zeit").isHidden())
        dialog.catalog_search_input.clear()

        self.assertFalse(self._observation_topic_container(dialog, "Zeit").isHidden())

    def test_observation_dialog_clearing_search_keeps_new_catalog_closed(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")

        dialog.catalog_search_input.setText("Uhrzeit")
        dialog.catalog_search_input.clear()

        self.assertTrue(self._observation_topic_container(dialog, "Zeit").isHidden())

    def test_observation_dialog_clearing_search_restores_editing_branches(self) -> None:
        initial_draft = self._sample_observation_draft(
            subject_id="mathematik",
            subject_display_name="Mathematik",
            competency_ratings=(
                self._sample_observation_rating(
                    self.math_time_competency_id, "mathematik", "Mathematik",
                    "Größenvorstellungen nutzen und mit Größen umgehen",
                    "Zeit", "Ablesen, Einstellen und Aufschreiben der Uhrzeit", "+",
                ),
            ),
        )
        dialog = self._observation_dialog_with_hierarchy(initial_draft)

        dialog.catalog_search_input.setText("Uhrzeit")
        dialog.catalog_search_input.clear()

        self.assertFalse(self._observation_topic_container(dialog, "Zeit").isHidden())

    def test_observation_dialog_topic_click_shows_and_hides_competencies(
        self,
    ) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        topic_button = self._observation_topic_button(dialog, "Zeit")
        topic_container = self._observation_topic_container(dialog, "Zeit")

        topic_button.click()
        self.assertFalse(topic_container.isHidden())
        self.assertEqual(topic_button.text(), "▾ Thema: Zeit")
        self.assertIn(
            "Ablesen, Einstellen und Aufschreiben der Uhrzeit",
            [
                label.text()
                for label in topic_container.findChildren(QLabel)
            ],
        )

        topic_button.click()
        self.assertTrue(topic_container.isHidden())
        self.assertEqual(topic_button.text(), "▸ Thema: Zeit")

    def test_observation_dialog_whole_catalog_tile_adds_competency(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        self._observation_area_button(
            dialog,
            "Größenvorstellungen nutzen und mit Größen umgehen",
        ).click()
        self._observation_topic_button(dialog, "Zeit").click()
        tile = dialog.competency_catalog_tiles[self.math_time_competency_id]
        QTest.mouseClick(tile, Qt.MouseButton.LeftButton)
        dialog.competency_rating_widgets[self.math_time_competency_id].buttons["++"].click()
        draft = dialog.create_draft()
        rating = next(
            item for item in draft.competency_ratings
            if item.competency_id == self.math_time_competency_id
        )

        self.assertIn(self.math_time_competency_id, dialog.competency_rating_entries)
        self.assertTrue(tile.is_selected())
        self.assertEqual(tile.selection_signal.text(), "✓")
        self.assertEqual(rating.rating, "++")
        self.assertEqual(
            rating.competency_text,
            "Ablesen, Einstellen und Aufschreiben der Uhrzeit",
        )

    def test_observation_dialog_selection_survives_topic_collapse(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        topic_button = self._observation_topic_button(dialog, "Zeit")
        topic_button.click()
        dialog.competency_catalog_tiles[self.math_time_competency_id]._activate()
        dialog.competency_rating_widgets[self.math_time_competency_id].buttons["++"].click()
        topic_button.click()
        draft = dialog.create_draft()

        self.assertTrue(self._observation_topic_container(dialog, "Zeit").isHidden())
        self.assertIn(self.math_time_competency_id, dialog.competency_rating_entries)
        self.assertIn(self.math_time_competency_id, dialog.competency_rating_widgets)
        self.assertEqual(draft.competency_ratings[0].competency_id, self.math_time_competency_id)
        self.assertEqual(draft.competency_ratings[0].rating, "++")

    def test_observation_dialog_keeps_separate_ratings_per_competency(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        self._observation_topic_button(dialog, "Addition").click()
        self._observation_topic_button(dialog, "Subtraktion").click()
        dialog.competency_catalog_tiles[self.math_addition_competency_id]._activate()
        dialog.competency_catalog_tiles[self.math_subtraction_competency_id]._activate()
        first_rating = dialog.competency_rating_widgets[self.math_addition_competency_id]
        second_rating = dialog.competency_rating_widgets[self.math_subtraction_competency_id]
        first_rating.buttons["++"].click()
        second_rating.buttons["-"].click()
        draft = dialog.create_draft()
        ratings_by_id = {
            rating.competency_id: rating.rating
            for rating in draft.competency_ratings
        }

        self.assertEqual(ratings_by_id[self.math_addition_competency_id], "++")
        self.assertEqual(ratings_by_id[self.math_subtraction_competency_id], "-")

    def test_observation_dialog_edit_keeps_initial_selected_rating(self) -> None:
        initial_draft = self._sample_observation_draft(
            subject_id="mathematik",
            subject_display_name="Mathematik",
            competency_ratings=(
                self._sample_observation_rating(
                    self.math_time_competency_id,
                    "mathematik",
                    "Mathematik",
                    "Größenvorstellungen nutzen und mit Größen umgehen",
                    "Zeit",
                    "Ablesen, Einstellen und Aufschreiben der Uhrzeit",
                    "++",
                ),
            ),
        )
        dialog = self._observation_dialog_with_hierarchy(initial_draft)

        self.assertEqual(dialog.subject_select.currentData(), "mathematik")
        self.assertFalse(self._observation_topic_container(dialog, "Zeit").isHidden())
        self.assertEqual(
            self._observation_topic_button(dialog, "Zeit").text(),
            "▾ Thema: Zeit",
        )
        self.assertTrue(dialog.competency_catalog_tiles[self.math_time_competency_id].is_selected())
        self.assertEqual(
            dialog.competency_rating_widgets[self.math_time_competency_id].currentData(),
            "++",
        )
        selected_button = dialog.competency_rating_widgets[self.math_time_competency_id].buttons["++"]
        self.assertTrue(selected_button.isChecked())
        self.assertTrue(selected_button.property("selected"))
        self.assertTrue(selected_button.text().startswith("✓ "))
        self.assertIn("ausgewählt", selected_button.accessibleName())

    def test_observation_dialog_edit_opens_only_rated_branches(self) -> None:
        initial_draft = self._sample_observation_draft(
            subject_id="mathematik",
            subject_display_name="Mathematik",
            competency_ratings=(
                self._sample_observation_rating(
                    self.math_time_competency_id,
                    "mathematik",
                    "Mathematik",
                    "Größenvorstellungen nutzen und mit Größen umgehen",
                    "Zeit",
                    "Ablesen, Einstellen und Aufschreiben der Uhrzeit",
                    "+",
                ),
            ),
        )
        dialog = self._observation_dialog_with_hierarchy(initial_draft)

        self.assertFalse(self._observation_topic_container(dialog, "Zeit").isHidden())
        self.assertTrue(
            self._observation_topic_container(dialog, "Zählen").isHidden()
        )
        open_areas = [
            key
            for key, container in dialog.competency_area_containers.items()
            if not container.isHidden()
        ]
        self.assertEqual(
            open_areas,
            [
                "mathematik|Größenvorstellungen nutzen und mit Größen umgehen"
            ],
        )

    def test_observation_dialog_only_clicked_topic_opens(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        zeit_container = self._observation_topic_container(dialog, "Zeit")
        counting_container = self._observation_topic_container(dialog, "Zählen")

        self._observation_topic_button(dialog, "Zeit").click()

        self.assertFalse(zeit_container.isHidden())
        self.assertTrue(counting_container.isHidden())

    def test_observation_dialog_prevents_duplicate_selection(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")
        tile = dialog.competency_catalog_tiles[self.math_time_competency_id]

        tile._activate()
        tile._activate()

        self.assertEqual(tuple(dialog.competency_rating_entries), (self.math_time_competency_id,))
        self.assertEqual(
            sum(
                1
                for index in range(dialog.competency_ratings_layout.count())
                if (
                    dialog.competency_ratings_layout.itemAt(index).widget() is not None
                    and dialog.competency_ratings_layout.itemAt(index).widget().property(
                        "competency_key"
                    )
                    == self.math_time_competency_id
                )
            ),
            1,
        )

    def test_quick_observation_activation_keeps_existing_competencies(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")
        dialog.competency_catalog_tiles[self.math_time_competency_id]._activate()

        dialog.quick_observation_checkbox.setChecked(True)

        self.assertFalse(dialog.quick_observation_checkbox.isChecked())
        self.assertIn(self.math_time_competency_id, dialog.competency_rating_entries)
        self.assertIn("Entferne zuerst", dialog.quick_observation_feedback.text())

    def test_existing_quick_observation_can_be_edited_and_converted(self) -> None:
        initial_draft = self._sample_observation_draft(
            observation_id="OBS-000001",
            competency_ratings=(),
            is_quick_observation=True,
        )
        dialog = self._observation_dialog_with_hierarchy(initial_draft)

        self.assertTrue(dialog.quick_observation_checkbox.isChecked())
        self.assertFalse(dialog.competency_zone.isEnabled())
        dialog.quick_observation_checkbox.setChecked(False)
        self._select_observation_subject(dialog, "mathematik")
        dialog.competency_catalog_tiles[self.math_time_competency_id]._activate()

        draft = dialog.create_draft()
        self.assertFalse(draft.is_quick_observation)
        self.assertEqual(draft.competency_ratings[0].rating, "+")

    def test_quick_observation_empty_note_uses_inline_warning(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self.addCleanup(dialog.close)
        dialog.show()
        QApplication.processEvents()
        dialog.quick_observation_checkbox.setChecked(True)
        dialog.note_input.setPlainText("   ")

        dialog.save_draft()

        self.assertTrue(dialog.quick_observation_checkbox.isChecked())
        self.assertEqual(
            dialog.validation_message.label.text(),
            "Bitte eine Notiz für die Schnellbeobachtung eingeben.",
        )
        self.assertEqual(dialog.validation_message.property("messageTone"), "warning")
        self.assertTrue(dialog.note_input.hasFocus())
        self.assertFalse(dialog.competency_zone.isEnabled())
        self.assertIsNone(dialog.competency_zone.graphicsEffect())

    def test_observation_dialog_inserts_new_selection_at_top(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")

        dialog.competency_catalog_tiles[self.math_addition_competency_id]._activate()
        dialog.competency_catalog_tiles[self.math_subtraction_competency_id]._activate()

        first_card = dialog.competency_ratings_layout.itemAt(0).widget()
        self.assertIsNotNone(first_card)
        if first_card is not None:
            self.assertEqual(first_card.property("competency_key"), self.math_subtraction_competency_id)

    def test_observation_dialog_subject_change_keeps_selection_and_rating(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")
        dialog.competency_catalog_tiles[self.math_time_competency_id]._activate()
        dialog.competency_rating_widgets[self.math_time_competency_id].buttons["--"].click()
        self._observation_topic_button(dialog, "Zeit").click()

        self._select_observation_subject(dialog, "deutsch")
        self._select_observation_subject(dialog, "mathematik")
        draft = dialog.create_draft()

        self.assertIn(self.math_time_competency_id, dialog.competency_rating_entries)
        self.assertEqual(draft.competency_ratings[0].rating, "--")
        self.assertTrue(self._observation_topic_container(dialog, "Zeit").isHidden())

    def test_observation_dialog_keeps_cross_subject_selection(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")
        dialog.competency_catalog_tiles[self.math_time_competency_id]._activate()
        dialog.competency_rating_widgets[self.math_time_competency_id].buttons["++"].click()
        self._select_observation_subject(dialog, "deutsch")
        dialog.competency_catalog_tiles[self.german_listening_competency_id]._activate()
        dialog.competency_rating_widgets[self.german_listening_competency_id].buttons["-"].click()

        ratings = {
            item.competency_id: item.rating
            for item in dialog.create_draft().competency_ratings
        }

        self.assertEqual(ratings, {self.math_time_competency_id: "++", self.german_listening_competency_id: "-"})

    def test_observation_dialog_current_competency_is_not_marked_historical(self) -> None:
        initial_draft = self._sample_observation_draft(
            subject_id="musik",
            subject_display_name="Musik",
            competency_ratings=(
                self._sample_observation_rating(
                    self.music_listening_competency_id,
                    "musik",
                    "Musik",
                    "Musik hören und verstehen",
                    "Allgemein",
                    "Gefühle und Stimmungen in der Musik erkennen und beschreiben",
                    "+",
                ),
            ),
        )
        dialog = self._observation_dialog_with_hierarchy(initial_draft)
        current_card = dialog.competency_rating_rows[self.music_listening_competency_id]

        self.assertEqual(current_card.property("historical"), "false")
        self.assertIsNone(current_card.findChild(QLabel, "ObservationHistoricalBadge"))
        self.assertIn(
            "Gefühle und Stimmungen in der Musik erkennen und beschreiben",
            [label.text() for label in current_card.findChildren(QLabel)],
        )

    def test_observation_dialog_honors_documentation_subject_hierarchy(self) -> None:
        self._save_custom_documentation_subjects(
            f"{STUDENT_ID_PREFIX}-000001",
            ("deutsch", "mathematik"),
        )
        dialog = self._observation_dialog_with_hierarchy()
        subject_labels = tuple(
            dialog.subject_select.itemText(index)
            for index in range(dialog.subject_select.count())
        )
        visible_subject_keys: set[str] = set()
        for index in range(dialog.subject_select.count()):
            dialog.subject_select.setCurrentIndex(index)
            visible_subject_keys.update(
                str(tile.property("subject_key"))
                for tile in dialog.competency_catalog_tiles.values()
            )

        self.assertEqual(
            subject_labels[:6],
            (
                "Überfachliche Entwicklung",
                "Selbst- und Sozialkompetenz",
                "Arbeits-/Lernkompetenz",
                "Fächer",
                "Deutsch",
                "Mathematik",
            ),
        )
        self.assertIn("Weitere Fächer", subject_labels)
        self.assertEqual(
            visible_subject_keys,
            {
                "selbst_sozialkompetenz",
                "arbeits_lernkompetenz",
                "epu",
                "deutsch",
                "mathematik",
                "kreatives_gestalten",
                "sport",
                "ethik",
                "religion",
                "musik",
                "englisch",
                "schulgarten",
            },
        )

    def test_additional_subject_recent_competency_requires_explicit_subject_choice(
        self,
    ) -> None:
        student_id = f"{STUDENT_ID_PREFIX}-000001"
        sport_competency = next(
            competency
            for subject in self.adapter.list_observation_competency_subject_groups(
                student_id
            )
            for area in subject.learning_area_groups
            for topic in area.competency_groups
            for competency in topic.competencies
            if competency.subject_key == "sport"
        )
        saved = self.adapter.save_observation(
            self._sample_observation_draft(
                subject_id="sport",
                subject_display_name="Sport",
                competency_ratings=(
                    self._sample_observation_rating(
                        sport_competency.competency_id,
                        sport_competency.subject_key,
                        sport_competency.subject_display_name,
                        sport_competency.learning_area,
                        sport_competency.competency_group,
                        sport_competency.competency_text,
                        "+",
                    ),
                ),
            )
        )
        self.assertIsInstance(saved, SuccessResult)
        self._save_custom_documentation_subjects(student_id, ("deutsch",))

        dialog = self._observation_dialog_with_hierarchy()

        self.assertNotIn(
            sport_competency.competency_id,
            dialog.recent_competency_chips,
        )
        self._select_observation_subject(dialog, "sport")
        self.assertIn(
            sport_competency.competency_id,
            dialog.recent_competency_chips,
        )

    def test_edit_preserves_rating_after_subject_becomes_additional(self) -> None:
        student_id = f"{STUDENT_ID_PREFIX}-000001"
        sport_competency = next(
            competency
            for subject in self.adapter.list_observation_competency_subject_groups(
                student_id
            )
            for area in subject.learning_area_groups
            for topic in area.competency_groups
            for competency in topic.competencies
            if competency.subject_key == "sport"
        )
        saved = self.adapter.save_observation(
            self._sample_observation_draft(
                subject_id="sport",
                subject_display_name="Sport",
                competency_ratings=(
                    self._sample_observation_rating(
                        sport_competency.competency_id,
                        sport_competency.subject_key,
                        sport_competency.subject_display_name,
                        sport_competency.learning_area,
                        sport_competency.competency_group,
                        sport_competency.competency_text,
                        "++",
                    ),
                ),
            )
        )
        self.assertIsInstance(saved, SuccessResult)
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE competencies
                SET active = 0, catalog_status = 'legacy'
                WHERE competency_id = ?
                """,
                (sport_competency.competency_id,),
            )
            connection.commit()
        self._save_custom_documentation_subjects(student_id, ("deutsch",))
        draft = self.adapter.observation_draft_for_edit("OBS-000001")
        self.assertIsNotNone(draft)
        if draft is None:
            raise AssertionError("Expected persisted observation draft")

        groups = self.adapter.list_observation_competency_subject_groups(
            student_id,
            draft,
        )
        preserved = self._find_observation_competency_option(
            groups,
            sport_competency.competency_id,
        )

        self.assertIsNotNone(preserved)
        if preserved is not None:
            self.assertTrue(preserved.selected)
            self.assertEqual(preserved.rating, "++")
            self.assertFalse(preserved.is_active)
            self.assertEqual(preserved.catalog_status, "legacy")
        dialog = self._observation_dialog_with_hierarchy(draft)
        historical_card = dialog.competency_rating_rows[
            sport_competency.competency_id
        ]
        self.assertEqual(historical_card.property("historical"), "true")
        self.assertIsNotNone(
            historical_card.findChild(QLabel, "ObservationHistoricalBadge")
        )
        self.assertEqual(
            dialog.competency_rating_widgets[
                sport_competency.competency_id
            ].currentData(),
            "++",
        )
        self._select_observation_subject(dialog, "sport")
        self.assertIn(
            sport_competency.competency_id,
            dialog.competency_catalog_tiles,
        )
        result = self.adapter.update_observation(
            replace(dialog.create_draft(), note="Legitime spätere Bearbeitung.")
        )
        stored = SQLiteObservationRepository(self.database).get_observation(
            "OBS-000001"
        )
        self.assertIsInstance(result, SuccessResult)
        self.assertIsNotNone(stored)
        if stored is not None:
            self.assertEqual(
                tuple(
                    (rating.competency_id, rating.rating)
                    for rating in stored.competency_ratings
                ),
                ((sport_competency.competency_id, "++"),),
            )

    def test_observation_dialog_uses_four_rating_chips_per_competency(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")
        dialog.competency_catalog_tiles[self.math_time_competency_id]._activate()
        selector = dialog.competency_rating_widgets[self.math_time_competency_id]
        expected_labels = dict(zip(("++", "+", "-", "--"), OBSERVATION_RATING_OPTIONS, strict=True))

        self.assertEqual(tuple(selector.buttons), ("++", "+", "-", "--"))
        for rating, button in selector.buttons.items():
            self.assertIsInstance(button, components.RatingBadgeButton)
            self.assertEqual(button.objectName(), "RatingBadgeButton")
            self.assertTrue(button.property("ratingBadge"))
            self.assertEqual(button.property("ratingToken"), rating)
            self.assertIn(expected_labels[rating], button.accessibleName())

            QTest.mouseClick(button, Qt.MouseButton.LeftButton)

            self.assertEqual(selector.currentData(), rating)
            self.assertTrue(button.isChecked())
            self.assertTrue(button.property("selected"))
            self.assertTrue(button.text().startswith("✓ "))
            self.assertIn("ausgewählt", button.accessibleName())
            self.assertEqual(
                dialog.create_draft().competency_ratings[0].rating,
                rating,
            )

    def test_observation_dialog_competency_selection_and_rating_work_by_keyboard(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(dialog, "mathematik")
        topic_button = self._observation_topic_button(dialog, "Zeit")
        QTest.keyClick(topic_button, Qt.Key.Key_Space)
        tile = dialog.competency_catalog_tiles[self.math_time_competency_id]

        QTest.keyClick(tile, Qt.Key.Key_Space)
        selector = dialog.competency_rating_widgets[self.math_time_competency_id]
        QTest.keyClick(selector.buttons["-"], Qt.Key.Key_Return)

        self.assertEqual(selector.currentData(), "-")

        QTest.keyClick(selector.buttons["--"], Qt.Key.Key_Space)

        self.assertIn(self.math_time_competency_id, dialog.competency_rating_entries)
        self.assertEqual(selector.currentData(), "--")
        self.assertFalse(selector.buttons["-"].isChecked())
        self.assertFalse(selector.buttons["-"].property("selected"))
        self.assertTrue(selector.buttons["--"].isChecked())
        self.assertTrue(selector.buttons["--"].property("selected"))

    def test_observation_dialog_draft_remains_create_update_compatible(self) -> None:
        initial_draft = self._sample_observation_draft(
            observation_id="OBS-000001",
            subject_id="mathematik",
            subject_display_name="Mathematik",
            competency_ratings=(
                self._sample_observation_rating(
                    self.math_time_competency_id,
                    "mathematik",
                    "Mathematik",
                    "Größenvorstellungen nutzen und mit Größen umgehen",
                    "Zeit",
                    "Ablesen, Einstellen und Aufschreiben der Uhrzeit",
                    "+",
                ),
            ),
        )
        update_dialog = self._observation_dialog_with_hierarchy(initial_draft)
        update_draft = update_dialog.create_draft()
        create_dialog = self._observation_dialog_with_hierarchy()
        self._select_observation_subject(create_dialog, "mathematik")
        create_dialog.competency_catalog_tiles[self.math_time_competency_id]._activate()
        create_draft = create_dialog.create_draft()

        create_command = self.adapter.create_observation_command(create_draft)
        update_command = self.adapter.create_update_observation_command(update_draft)

        self.assertIsInstance(create_command, CreateObservationCommand)
        self.assertIsInstance(update_command, UpdateObservationCommand)
        self.assertEqual(
            tuple(fields(create_draft)),
            tuple(fields(update_draft)),
        )
        self.assertEqual(update_command.observation_id, "OBS-000001")

    def test_observation_dialog_save_action_stays_outside_scroll_areas(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        actions = dialog.findChild(QDialogButtonBox, "ObservationPersistentActions")

        self.assertIsNotNone(actions)
        if actions is not None:
            save_button = actions.button(QDialogButtonBox.StandardButton.Save)
            self.assertIsNotNone(save_button)
            if save_button is not None:
                self.assertEqual(save_button.text(), "Speichern")
                self.assertGreaterEqual(save_button.minimumHeight(), 42)
            parent = actions.parentWidget()
            while parent is not None:
                self.assertNotIsInstance(parent, QScrollArea)
                parent = parent.parentWidget()

    def test_observation_dialog_attachment_rows_show_name_type_and_remove_action(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()
        attachments_scroll = dialog.findChild(
            QScrollArea,
            "ObservationAttachmentsScroll",
        )
        self.assertIsNotNone(attachments_scroll)
        if attachments_scroll is not None:
            self.assertEqual(
                attachments_scroll.horizontalScrollBarPolicy(),
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
            )
        self.assertTrue(dialog.attachment_empty_state.wordWrap())
        self.assertTrue(dialog.attachment_feedback_label.wordWrap())
        source = Path(self.temp_dir.name) / "arbeitsprobe.pdf"
        source.write_text("test", encoding="utf-8")
        dialog.attachment_type_select.setCurrentText("Arbeitsprobe")

        dialog.add_attachment_path(source)

        row = dialog.findChild(QFrame, "ObservationFileRow")
        self.assertIsNotNone(row)
        self.assertIn(
            "arbeitsprobe.pdf",
            [label.text() for label in row.findChildren(QLabel)],
        )
        self.assertIn(
            "Arbeitsprobe",
            [label.text() for label in row.findChildren(QLabel)],
        )
        remove = next(
            button
            for button in row.findChildren(QPushButton)
            if button.text() == "Entfernen"
        )
        self.assertTrue(remove.accessibleName())
        remove.click()
        self.assertEqual(dialog.attachment_drafts, [])

    def test_observation_context_options_match_prototype_scope(self) -> None:
        self.assertEqual(
            OBSERVATION_CONTEXT_OPTIONS,
            (
                "Lernzielkontrolle",
                "Präsentation",
                "Einzelgespräch",
                "Partnerarbeit",
                "Gruppenarbeit",
                "Leseübung",
            ),
        )

    def test_observation_draft_view_model_keeps_student_context(self) -> None:
        competency = ObservationCompetencyRatingDraft(
            competency_id=self.german_listening_competency_id,
            subject_key="deutsch",
            subject_display_name="Deutsch",
            learning_area="Mit Texten und Medien umgehen",
            competency_group="Lesen und Verstehen",
            competency_text="Texte lesen und zentrale Informationen entnehmen",
            rating="+",
        )
        draft = ObservationDraftViewModel(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            student_name="Emma Müller",
            date_text="2026-07-01",
            competency_ratings=(competency,),
            context="Leseübung",
            note="Liest einen bekannten Text flüssig.",
            subject_id="deutsch",
            subject_display_name="Deutsch",
        )

        self.assertEqual(draft.student_id, f"{STUDENT_ID_PREFIX}-000001")
        self.assertEqual(draft.student_name, "Emma Müller")
        self.assertEqual(draft.subject_id, "deutsch")
        self.assertEqual(draft.competency_ratings[0].subject_key, "deutsch")
        self.assertEqual(draft.competency_ratings[0].competency_id, self.german_listening_competency_id)
        self.assertEqual(draft.competency_ratings[0].subject_display_name, "Deutsch")
        self.assertEqual(draft.competency_ratings[0].display_label, "Mit Texten und Medien umgehen")
        self.assertEqual(draft.competency_ratings[0].competency_text, "Texte lesen und zentrale Informationen entnehmen")
        self.assertEqual(draft.competency_ratings[0].rating, "+")
        self.assertEqual(draft.attachment_names, ())

    def test_observation_draft_has_no_global_rating(self) -> None:
        field_names = {field.name for field in fields(ObservationDraftViewModel)}

        self.assertNotIn("rating", field_names)
        self.assertNotIn("subject_key", field_names)
        self.assertNotIn("subject", field_names)
        self.assertIn("competency_ratings", field_names)

    def test_observation_competency_ratings_can_span_subjects(self) -> None:
        first = ObservationCompetencyRatingDraft(
            competency_id=self.german_listening_competency_id,
            subject_key="epu",
            subject_display_name="EPU",
            learning_area="Natur und Umwelt",
            competency_group="Erkunden und beschreiben",
            competency_text="Naturphänomene beobachten und beschreiben",
            rating="++",
        )
        second = ObservationCompetencyRatingDraft(
            competency_id=self.german_word_competency_id,
            subject_key="deutsch",
            subject_display_name="Deutsch",
            learning_area="Miteinander sprechen",
            competency_group="Gesprächsbeiträge",
            competency_text="Eigene Beiträge verständlich einbringen",
            rating="-",
        )
        third = ObservationCompetencyRatingDraft(
            competency_id=self.epu_competency_id,
            subject_key="sozialkompetenz",
            subject_display_name="Sozialkompetenz",
            learning_area="Verantwortung",
            competency_group="Auftreten",
            competency_text="Verantwortung in der Gruppe übernehmen",
            rating="+",
        )

        draft = ObservationDraftViewModel(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            student_name="Emma Müller",
            date_text="2026-07-01",
            competency_ratings=(first, second, third),
            context="Präsentation",
            note="Präsentiert Arbeitsergebnisse vor der Gruppe.",
            subject_id="epu",
            subject_display_name="EPU",
        )

        self.assertEqual(draft.competency_ratings[0].rating, "++")
        self.assertEqual(draft.competency_ratings[1].rating, "-")
        self.assertEqual(draft.competency_ratings[2].rating, "+")
        self.assertNotEqual(
            draft.competency_ratings[0].rating,
            draft.competency_ratings[1].rating,
        )
        self.assertEqual(
            [rating.subject_key for rating in draft.competency_ratings],
            ["epu", "deutsch", "sozialkompetenz"],
        )
        self.assertEqual(
            [rating.subject_display_name for rating in draft.competency_ratings],
            ["EPU", "Deutsch", "Sozialkompetenz"],
        )
        self.assertEqual(draft.competency_ratings[0].display_label, "Natur und Umwelt")
        self.assertEqual(draft.competency_ratings[1].display_label, "Miteinander sprechen")

    def test_observation_dialog_messages_match_persistent_scope(self) -> None:
        self.assertEqual(
            OBSERVATION_SAVE_SUCCESS_MESSAGE,
            "Beobachtung wurde gespeichert.",
        )
        self.assertEqual(
            OBSERVATION_ATTACHMENT_EMPTY_STATE,
            "Noch keine Anhänge ausgewählt. Über „Datei hinzufügen“ kannst du einen ergänzen.",
        )
        self.assertIn("Sonstiges", DOCUMENT_TYPE_OPTIONS)

    def test_observation_dialog_has_no_direct_sqlite_write_logic(self) -> None:
        source = inspect.getsource(new_observation_dialog)

        self.assertNotIn("INSERT INTO", source)
        self.assertNotIn("UPDATE ", source)
        self.assertNotIn("DELETE FROM", source)
        self.assertNotIn("sqlite3.connect", source)
        self.assertNotIn("ApplicationCommandDispatcher", source)
        self.assertNotIn("student.create", source)
        self.assertIn("self.observation_adapter.save_observation(draft)", source)

    def test_shell_refreshes_profile_after_observation_save(self) -> None:
        source = inspect.getsource(shell.AppShell.open_new_observation_dialog)
        profile_source = inspect.getsource(shell.AppShell.show_student_profile)

        self.assertIn("self._create_dialog(NewObservationDialog,", source)
        self.assertIn("list_observation_subject_options(", source)
        self.assertIn("list_observation_competency_subject_groups(", source)
        self.assertIn("student.student_id", source)
        self.assertIn("self.show_student_profile(student.student_id)", source)
        self.assertIn('self.status_label.setText("Beobachtung wurde gespeichert.")', source)
        self.assertIn("student_profile_projection_bundle(", profile_source)
        self.assertIn("profile_projection.competency_groups", profile_source)
        self.assertIn("profile_projection.documentation_statuses", profile_source)
        self.assertIn("report_overview_for_student(", profile_source)
        self.assertIn("selected_report_draft_id=", profile_source)
        self.assertIn("selected_learning_conference_draft_id=", profile_source)
        self.assertNotIn("get_report_preview_for_student(student_id)", profile_source)

    def test_shell_opens_quick_observation_from_student_list(self) -> None:
        shell_source = inspect.getsource(shell.AppShell)
        quick_source = inspect.getsource(shell.AppShell.open_quick_observation_dialog)

        self.assertIn("self.students_screen.observation_requested.connect", shell_source)
        self.assertIn("self.open_quick_observation_dialog", shell_source)
        self.assertIn("self.adapter.get_student_profile(student_id)", quick_source)
        self.assertIn("self._create_dialog(NewObservationDialog,", quick_source)
        self.assertIn("list_observation_subject_options(", quick_source)
        self.assertIn("list_observation_competency_subject_groups(", quick_source)
        self.assertIn("student.student_id", quick_source)
        self.assertIn("self.refresh_overview()", quick_source)
        self.assertIn("self.refresh_students()", quick_source)
        self.assertIn('self.status_label.setText("Beobachtung wurde gespeichert.")', quick_source)

    def test_shell_returns_from_filtered_student_list_to_overview(self) -> None:
        shell_source = inspect.getsource(shell.AppShell)
        return_source = inspect.getsource(shell.AppShell.return_to_overview)
        refresh_source = inspect.getsource(shell.AppShell.refresh_students)

        self.assertIn("self.students_screen.back_to_overview_requested.connect", shell_source)
        self.assertIn("self.return_to_overview", shell_source)
        self.assertIn("self.selected_group_id = None", return_source)
        self.assertIn("self.selected_course_group_id = None", return_source)
        self.assertIn("self.selected_course_id = None", return_source)
        self.assertIn("self.students_workspace.show_source_selection()", return_source)
        self.assertIn('self._show_screen("students")', return_source)
        self.assertIn('self._select_navigation("students")', return_source)
        self.assertIn("show_back_button=self._has_active_student_filter()", refresh_source)

    def test_shell_opens_observation_for_edit_and_refreshes_profile(self) -> None:
        source = inspect.getsource(shell.AppShell.open_edit_observation_dialog)

        self.assertIn("observation_draft_for_edit(observation_id)", source)
        self.assertIn("initial_draft=draft", source)
        self.assertIn("list_observation_subject_options(", source)
        self.assertIn("list_observation_competency_subject_groups(", source)
        self.assertIn("student.student_id", source)
        self.assertIn("self.show_student_profile(student.student_id)", source)
        self.assertIn('self.status_label.setText("Beobachtung wurde aktualisiert.")', source)

    def test_shell_soft_deletes_observation_and_refreshes_profile(self) -> None:
        source = inspect.getsource(shell.AppShell.delete_observation)

        self.assertIn("self.adapter.delete_observation(observation_id)", source)
        self.assertIn("self.show_student_profile(draft.student_id)", source)
        self.assertIn(
            "Beobachtung wurde gelöscht. Profil bleibt geöffnet.",
            source,
        )

    def test_shell_soft_deletes_document_and_refreshes_profile(self) -> None:
        shell_source = inspect.getsource(shell.AppShell)
        remove_source = inspect.getsource(shell.AppShell.remove_student_document)

        self.assertIn(
            "self.student_profile_screen.document_remove_requested.connect",
            shell_source,
        )
        self.assertIn("self.remove_student_document", shell_source)
        self.assertIn("create_confirmation_message", remove_source)
        self.assertIn('confirm_text="Datei entfernen"', remove_source)
        self.assertIn("self.adapter.remove_document(document_id)", remove_source)
        self.assertIn("self.show_student_profile(student_id)", remove_source)
        self.assertIn(
            'self.status_label.setText("Datei wurde entfernt.")',
            remove_source,
        )

    def test_observation_dialog_updates_existing_observation(self) -> None:
        source = inspect.getsource(new_observation_dialog.NewObservationDialog.save_draft)

        self.assertIn("draft.observation_id", source)
        self.assertIn("self.observation_adapter.update_observation(draft)", source)
        self.assertIn("self.accept()", source)
        self.assertNotIn("QMessageBox.information", source)

    def test_student_profile_observation_cards_offer_edit_and_delete(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        edited_observation_ids = []
        deleted_observation_ids = []
        screen.observation_edit_requested.connect(edited_observation_ids.append)
        screen.observation_delete_requested.connect(deleted_observation_ids.append)
        screen.set_student(
            self._sample_student_detail(),
            (
                ObservationListItem(
                    "OBS-000001",
                    f"{STUDENT_ID_PREFIX}-000001",
                    "2026-07-03",
                    "Deutsch",
                    "Leseübung",
                    "Liest einen bekannten Text.",
                    (),
                ),
            ),
        )

        button_texts = [button.text() for button in screen.findChildren(QPushButton)]
        details_button = next(
            button
            for button in screen.findChildren(QPushButton)
            if button.text() == "Details anzeigen"
        )
        details_button.click()
        edit_button = next(
            button
            for button in screen.findChildren(QPushButton)
            if button.text() == "Bearbeiten"
        )
        delete_button = next(
            button
            for button in screen.findChildren(QPushButton)
            if button.text() == "Löschen"
        )
        edit_button.click()
        delete_button.click()

        self.assertIn("Details anzeigen", button_texts)
        self.assertIn("Bearbeiten", button_texts)
        self.assertIn("Löschen", button_texts)
        self.assertEqual(edited_observation_ids, ["OBS-000001"])
        self.assertEqual(deleted_observation_ids, ["OBS-000001"])
        self.assertIsNotNone(app)

    def test_student_profile_renders_persisted_observations(self) -> None:
        source = inspect.getsource(importlib.import_module(
            "src.desktop_app.screens.student_profile_screen"
        ))

        self.assertIn("set_observations", source)
        self.assertIn("ObservationListItem", source)
        self.assertIn("_observation_card", source)
        self.assertIn("_observation_summary", source)
        self.assertIn("_toggle_observation_details", source)
        self.assertIn("_empty_observations_card", source)
        self.assertIn('"Notiz"', source)
        self.assertIn('"Kompetenzen"', source)

    def test_student_profile_observation_cards_render_compact_summary(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (
                ObservationListItem(
                    "OBS-000001",
                    f"{STUDENT_ID_PREFIX}-000001",
                    "2026-07-03",
                    "Deutsch",
                    "Leseübung",
                    "Liest einen bekannten Text.",
                    (
                        ObservationRatingViewModel(
                            self.german_listening_competency_id,
                            "Deutsch",
                            "Mit Texten und Medien umgehen",
                            "Lesen und Verstehen",
                            "Texte lesen und zentrale Informationen entnehmen",
                            "+",
                        ),
                    ),
                ),
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]
        button_texts = [button.text() for button in screen.findChildren(QPushButton)]

        self.assertIn("2026-07-03", label_texts)
        self.assertIn("Deutsch", label_texts)
        self.assertIn("Leseübung · Liest einen bekannten Text. · 1 Kompetenz", label_texts)
        self.assertIn("Details anzeigen", button_texts)
        self.assertNotIn("Kontext: Leseübung", label_texts)
        self.assertIn("Kompetenzen", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_observation_details_can_be_expanded(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (
                ObservationListItem(
                    "OBS-000001",
                    f"{STUDENT_ID_PREFIX}-000001",
                    "2026-07-03",
                    "Deutsch",
                    "Leseübung",
                    "Liest einen bekannten Text.",
                    (
                        ObservationRatingViewModel(
                            self.german_listening_competency_id,
                            "Deutsch",
                            "Mit Texten und Medien umgehen",
                            "Lesen und Verstehen",
                            "Texte lesen und zentrale Informationen entnehmen",
                            "+",
                        ),
                    ),
                ),
            ),
        )

        details_button = next(
            button
            for button in screen.findChildren(QPushButton)
            if button.text() == "Details anzeigen"
        )
        details_button.click()
        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertEqual(details_button.text(), "Details ausblenden")
        self.assertIn("Kompetenzen", label_texts)
        self.assertIn("Notiz: Liest einen bekannten Text.", label_texts)
        self.assertTrue(any(
            text.startswith("Kenntnisse meist anwenden  Mit Texten und Medien umgehen")
            for text in label_texts
        ))
        self.assertIsNotNone(app)

    def test_expanded_observation_cards_keep_geometry_during_hover(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        subjects = (
            ("deutsch", "Deutsch", "+"),
            ("mathematik", "Mathematik", "++"),
            ("schulgarten", "Schulgarten", "-"),
            ("epu", "EPU", "--"),
            ("musik", "Musik", "+"),
        )
        observations = tuple(
            ObservationListItem(
                f"OBS-HOVER-{index}",
                f"{STUDENT_ID_PREFIX}-000001",
                f"2026-07-{10 + index:02d}",
                display_name,
                "Langer fachlicher Kontext mit mehreren Arbeitsphasen",
                (
                    "Mehrzeilige Beobachtungsnotiz mit ausreichend Text, damit die "
                    "Detailkarte deutlich wächst und Scrollpositionen belastbar geprüft "
                    "werden können. "
                ) * (index + 1),
                tuple(
                    ObservationRatingViewModel(
                        f"{subject_id}-kompetenz-{rating_index}",
                        display_name,
                        "Lernbereich mit langem Namen",
                        "Kompetenzgruppe",
                        "Ausführlich beschriebene Kompetenz",
                        token,
                        subject_id=subject_id,
                    )
                    for rating_index in range(1 + index % 3)
                ),
                (
                    SimpleNamespace(
                        document_type="Bild",
                        display_title=f"Dokument {index}.jpg",
                        file_path=Path(f"/tmp/Dokument-{index}.jpg"),
                    ),
                ) if index % 2 == 0 else (),
                False,
                subject_id,
            )
            for index, (subject_id, display_name, token) in enumerate(subjects)
        )
        screen.set_student(self._sample_student_detail(), observations)
        screen.profile_tabs.setCurrentIndex(1)
        screen.show()

        show_all_button = next(
            button
            for button in screen.findChildren(QPushButton)
            if button.text() == "Alle Beobachtungen anzeigen (5)"
        )
        show_all_button.click()
        for button in tuple(screen.findChildren(QPushButton)):
            if button.text() == "Details anzeigen":
                button.click()

        cards = tuple(
            card
            for card in screen.findChildren(QFrame, "ProfileObservationCard")
            if card.property("observation_id")
        )
        self.assertEqual(len(cards), 5)
        self.assertTrue(all(card.graphicsEffect() is None for card in cards))

        scroll_area = screen.profile_tabs.widget(1)
        self.assertIsInstance(scroll_area, QScrollArea)
        for width, height in ((1150, 768), (1180, 760), (1280, 800), (1400, 900)):
            screen.resize(width, height)
            app.processEvents()
            bar = scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum() // 2)
            app.processEvents()
            scroll_before = bar.value()
            geometry_before = tuple(card.geometry() for card in cards)
            action_geometry_before = tuple(
                tuple(
                    button.geometry()
                    for button in card.findChildren(QPushButton)
                    if button.text() in {
                        "Details ausblenden",
                        "Bearbeiten",
                        "Löschen",
                        "Öffnen",
                    }
                )
                for card in cards
            )

            for card in cards:
                QApplication.sendEvent(card, QEvent(QEvent.Type.Enter))
                for child in card.findChildren(QPushButton):
                    QApplication.sendEvent(child, QEvent(QEvent.Type.Enter))
                    QApplication.sendEvent(child, QEvent(QEvent.Type.Leave))
                QApplication.sendEvent(card, QEvent(QEvent.Type.Leave))
            app.processEvents()

            self.assertEqual(tuple(card.geometry() for card in cards), geometry_before)
            self.assertEqual(
                tuple(
                    tuple(
                        button.geometry()
                        for button in card.findChildren(QPushButton)
                        if button.text() in {
                            "Details ausblenden",
                            "Bearbeiten",
                            "Löschen",
                            "Öffnen",
                        }
                    )
                    for card in cards
                ),
                action_geometry_before,
            )
            self.assertEqual(bar.value(), scroll_before)
            self.assertTrue(all(
                any(
                    label.text().startswith("Notiz:") and label.isVisible()
                    for label in card.findChildren(QLabel)
                )
                for card in cards
            ))

        screen.close()
        self.assertIsNotNone(app)

    def test_student_profile_subject_filter_limits_observation_cards(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_filter_observations(),
        )

        screen.observation_subject_filter.setCurrentIndex(
            screen.observation_subject_filter.findText("EPU")
        )
        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("EPU", label_texts)
        self.assertIn("Präsentation · Beschreibt Naturphänomene. · 1 Kompetenz", label_texts)
        self.assertNotIn("Leseübung · Liest einen bekannten Text. · 1 Kompetenz", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_limits_unfiltered_observations_to_three_newest(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_many_observations(),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]
        button_texts = [button.text() for button in screen.findChildren(QPushButton)]

        self.assertIn("Projektarbeit · Neueste Beobachtung. · 1 Kompetenz", label_texts)
        self.assertIn("Gruppenarbeit · Verbindet Deutsch und EPU. · 2 Kompetenzen", label_texts)
        self.assertIn("Präsentation · Beschreibt Naturphänomene. · 1 Kompetenz", label_texts)
        self.assertNotIn("Leseübung · Liest einen bekannten Text. · 1 Kompetenz", label_texts)
        self.assertIn("Alle Beobachtungen anzeigen (4)", button_texts)
        self.assertIsNotNone(app)

    def test_student_profile_show_all_and_show_less_toggle_observations(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_many_observations(),
        )

        show_all_button = next(
            button
            for button in screen.findChildren(QPushButton)
            if button.text() == "Alle Beobachtungen anzeigen (4)"
        )
        show_all_button.click()
        expanded_labels = [label.text() for label in screen.findChildren(QLabel)]
        show_all_button.click()
        collapsed_labels = [label.text() for label in screen.findChildren(QLabel)]

        self.assertEqual(show_all_button.text(), "Alle Beobachtungen anzeigen (4)")
        self.assertIn("Leseübung · Liest einen bekannten Text. · 1 Kompetenz", expanded_labels)
        self.assertNotIn("Leseübung · Liest einen bekannten Text. · 1 Kompetenz", collapsed_labels)
        self.assertIsNotNone(app)

    def test_student_profile_show_all_button_switches_to_show_less(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_many_observations(),
        )

        show_all_button = next(
            button
            for button in screen.findChildren(QPushButton)
            if button.text() == "Alle Beobachtungen anzeigen (4)"
        )
        show_all_button.click()

        self.assertEqual(show_all_button.text(), "Weniger anzeigen")
        self.assertIsNotNone(app)

    def test_student_profile_cross_subject_filter_is_available(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_filter_observations(),
        )

        screen.observation_subject_filter.setCurrentIndex(
            screen.observation_subject_filter.findText(OBSERVATION_CROSS_SUBJECT_LABEL)
        )
        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn(OBSERVATION_CROSS_SUBJECT_LABEL, label_texts)
        self.assertIn("Gruppenarbeit · Verbindet Deutsch und EPU. · 2 Kompetenzen", label_texts)
        self.assertNotIn("Präsentation · Beschreibt Naturphänomene. · 1 Kompetenz", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_rating_filter_matches_competency_rating(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_filter_observations(),
        )

        screen.observation_rating_filter.setCurrentIndex(
            screen.observation_rating_filter.findText("--")
        )
        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Leseübung · Liest einen bekannten Text. · 1 Kompetenz", label_texts)
        self.assertNotIn("Präsentation · Beschreibt Naturphänomene. · 1 Kompetenz", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_rating_filter_has_readable_width(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()

        rating_values = [
            screen.observation_rating_filter.itemText(index)
            for index in range(screen.observation_rating_filter.count())
        ]

        self.assertEqual(rating_values, ["Alle", "++", "+", "-", "--"])
        self.assertGreaterEqual(screen.observation_rating_filter.minimumWidth(), 118)
        self.assertLessEqual(screen.observation_search_input.maximumWidth(), 320)
        self.assertIsNotNone(app)

    def test_combobox_dropdown_style_is_global(self) -> None:
        self.assertIn("QComboBox::drop-down", theme.APP_STYLESHEET)
        self.assertIn("QComboBox::down-arrow", theme.APP_STYLESHEET)
        self.assertIn("QComboBox QAbstractItemView", theme.APP_STYLESHEET)
        self.assertNotIn("QComboBox#ObservationFilterInput", theme.APP_STYLESHEET)

    def test_date_time_edit_dropdown_style_is_global(self) -> None:
        self.assertIn("QDateEdit::drop-down", theme.APP_STYLESHEET)
        self.assertIn("QDateTimeEdit::drop-down", theme.APP_STYLESHEET)
        self.assertIn("QTimeEdit::drop-down", theme.APP_STYLESHEET)
        self.assertIn("QDateEdit::down-arrow", theme.APP_STYLESHEET)
        self.assertIn("QDateTimeEdit::down-arrow", theme.APP_STYLESHEET)
        self.assertIn("QTimeEdit::down-arrow", theme.APP_STYLESHEET)

    def test_student_profile_search_filter_matches_context_note_or_competency(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_filter_observations(),
        )

        screen.observation_search_input.setText("gruppenarbeit")
        context_labels = [label.text() for label in screen.findChildren(QLabel)]
        screen.observation_search_input.setText("naturphänomene")
        note_labels = [label.text() for label in screen.findChildren(QLabel)]
        screen.observation_search_input.setText("medien umgehen")
        competency_labels = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Gruppenarbeit · Verbindet Deutsch und EPU. · 2 Kompetenzen", context_labels)
        self.assertIn("Präsentation · Beschreibt Naturphänomene. · 1 Kompetenz", note_labels)
        self.assertIn("Leseübung · Liest einen bekannten Text. · 1 Kompetenz", competency_labels)
        self.assertIsNotNone(app)

    def test_student_profile_active_filter_uses_all_observations(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_many_observations(),
        )

        screen.observation_search_input.setText("bekannten text")
        label_texts = [label.text() for label in screen.findChildren(QLabel)]
        button_texts = [button.text() for button in screen.findChildren(QPushButton)]

        self.assertIn("Leseübung · Liest einen bekannten Text. · 1 Kompetenz", label_texts)
        self.assertNotIn("Alle Beobachtungen anzeigen (4)", button_texts)
        self.assertIsNotNone(app)

    def test_student_profile_observation_filter_reset_shows_all_observations(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_filter_observations(),
        )

        screen.observation_subject_filter.setCurrentIndex(
            screen.observation_subject_filter.findText("EPU")
        )
        screen.observation_rating_filter.setCurrentIndex(
            screen.observation_rating_filter.findText("+")
        )
        screen.observation_search_input.setText("natur")
        screen.observation_reset_button.click()
        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Leseübung · Liest einen bekannten Text. · 1 Kompetenz", label_texts)
        self.assertIn("Präsentation · Beschreibt Naturphänomene. · 1 Kompetenz", label_texts)
        self.assertIn("Gruppenarbeit · Verbindet Deutsch und EPU. · 2 Kompetenzen", label_texts)
        self.assertEqual(screen.observation_subject_filter.currentText(), "Alle")
        self.assertEqual(screen.observation_rating_filter.currentText(), "Alle")
        self.assertEqual(screen.observation_search_input.text(), "")
        self.assertIsNotNone(app)

    def test_student_profile_observation_filters_do_not_affect_competency_overview(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Mit Texten und Medien umgehen",
                documentation_state="observed_unconfirmed",
                observation_count=2,
                last_observation_date="2026-07-03",
                observed_proposal="+",
                subject_id="deutsch",
                subject_name="Deutsch",
            ),
        ))
        screen.set_student(
            self._sample_student_detail(),
            self._sample_filter_observations(),
            competency_cockpit=cockpit,
        )

        screen.observation_search_input.setText("nicht vorhanden")
        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Keine passenden Beobachtungen.", label_texts)
        self.assertTrue(
            any(
                "Mit Texten und Medien umgehen" in button.text()
                for button in screen.findChildren(QPushButton)
            )
        )
        self.assertIsNotNone(app)

    def test_student_profile_cross_subject_card_keeps_rating_subjects(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (
                ObservationListItem(
                    "OBS-000001",
                    f"{STUDENT_ID_PREFIX}-000001",
                    "2026-07-03",
                    OBSERVATION_CROSS_SUBJECT_LABEL,
                    "Präsentation",
                    "Verbindet Inhalte aus EPU und Deutsch.",
                    (
                        ObservationRatingViewModel(
                            self.german_listening_competency_id,
                            "Deutsch",
                            "Mit Texten und Medien umgehen",
                            "Lesen und Verstehen",
                            "Texte lesen und zentrale Informationen entnehmen",
                            "+",
                        ),
                        ObservationRatingViewModel(
                            self.epu_competency_id,
                            "EPU",
                            "Natur und Umwelt",
                            "Erkunden und beschreiben",
                            "Naturphänomene beobachten und beschreiben",
                            "-",
                        ),
                    ),
                ),
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn(OBSERVATION_CROSS_SUBJECT_LABEL, label_texts)
        self.assertTrue(any("Deutsch" in text for text in label_texts))
        self.assertTrue(any("EPU" in text for text in label_texts))
        self.assertIsNotNone(app)

    def test_student_profile_observation_empty_state_is_visible(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(self._sample_student_detail(), ())

        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn(PROFILE_SECTION_PLACEHOLDERS["observations_title"], label_texts)
        self.assertIn(PROFILE_SECTION_PLACEHOLDERS["observations_hint"], label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_renders_competency_overview_by_subject(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Mit Texten und Medien umgehen",
                documentation_state="observed_unconfirmed",
                observation_count=1,
                last_observation_date="2026-07-03",
                observed_proposal="+",
                subject_id="deutsch",
                subject_name="Deutsch",
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)

        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Kompetenz-Cockpit", label_texts)
        self.assertIn("Deutsch", label_texts)
        self.assertTrue(
            any(
                "Mit Texten und Medien umgehen" in button.text()
                for button in screen.findChildren(QPushButton)
            )
        )
        self.assertIsNotNone(app)

    def test_student_profile_renders_confirmed_competency_status(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Mit Texten und Medien umgehen",
                documentation_state="newer_observations",
                observation_count=1,
                last_observation_date="2026-07-04",
                confirmed_rating="+",
                observed_proposal="-",
                subject_id="deutsch",
                subject_name="Deutsch",
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        screen.findChild(QPushButton, "CompetencyCockpitCompetencyButton").click()

        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Bestätigter Stand", label_texts)
        self.assertIn("Bewertung: +", label_texts)
        self.assertIn("Vorschlag aus Beobachtungen", label_texts)
        self.assertIn("Bewertung: -", label_texts)
        self.assertIn(
            "Dokumentationszustand: Neue Beobachtungen seit der Bestätigung",
            label_texts,
        )
        self.assertIsNotNone(app)

    def test_student_profile_replaces_live_preview_with_report_overview(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (),
            (),
            StudentReportPreviewViewModel(
                f"{STUDENT_ID_PREFIX}-000001",
                "Emma Müller",
                (
                    StudentReportSubjectSectionViewModel(
                        "deutsch",
                        "Deutsch",
                        (
                            StudentReportCompetencyViewModel(
                                self.german_listening_competency_id,
                                "Mit Texten und Medien umgehen",
                                "+",
                                "von Laura bestätigt",
                                "Kenntnisse meist anwenden",
                            ),
                        ),
                        (
                            StudentReportCompetencyViewModel(
                                self.german_listening_competency_id,
                                "Mit Texten und Medien umgehen",
                                "+",
                                "von Laura bestätigt",
                                "Kenntnisse meist anwenden",
                            ),
                        ),
                        (
                            StudentReportDevelopmentViewModel(
                                self.german_listening_competency_id,
                                "Mit Texten und Medien umgehen",
                                "Stabil beobachtet: +",
                                ("+", "+"),
                            ),
                        ),
                        (),
                        (
                            StudentReportEvidenceViewModel(
                                "OBS-000001",
                                "2026-07-03",
                                "Leseübung",
                                "Liest einen bekannten Text.",
                                ("+ Mit Texten und Medien umgehen",),
                            ),
                        ),
                    ),
                ),
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Entwicklungsübersicht und Berichtsvorbereitung", label_texts)
        self.assertIn("Bericht", label_texts)
        self.assertIn("Lernentwicklungsgespräch (LEG)", label_texts)
        self.assertIn("Nächste Schritte", label_texts)
        self.assertIn("Dokumentations-Timeline", label_texts)
        self.assertIn("Fachübersicht", label_texts)
        self.assertNotIn("Stärken", label_texts)
        self.assertNotIn("Im Blick behalten", label_texts)
        self.assertIn("Berichte & LEG (Übersicht)", label_texts)
        self.assertNotIn("Aktueller Stand", label_texts)
        self.assertNotIn("Mit Texten und Medien umgehen", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_renders_compact_documentation_status(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        documentation_statuses = (
            StudentDocumentationSubjectStatus(
                "deutsch", "Deutsch", 8, 14, (), 0,
            ),
            StudentDocumentationSubjectStatus(
                "epu", "EPU", 0, 6,
                (StudentMissingCompetencyViewModel(
                    self.epu_competency_id, "Natur und Umwelt", 3,
                ),),
                3,
            ),
        )
        screen.set_student(
            self._sample_student_detail(),
            documentation_statuses=documentation_statuses,
            profile_dashboard=StudentProfileDashboardViewModel(
                documentation_summary_from_subjects(documentation_statuses),
                3,
                5,
                12,
                (
                    StudentProfileUndocumentedSubjectViewModel("Deutsch", 6, 0),
                    StudentProfileUndocumentedSubjectViewModel("EPU", 6, 3),
                ),
                (),
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("8 / 20", label_texts)
        self.assertIn("Bestätigter Stand", label_texts)
        self.assertIn("Beobachtet", label_texts)
        self.assertIn("NOCH NICHT DOKUMENTIERT", label_texts)
        self.assertIn("Deutsch", label_texts)
        self.assertIn("EPU", label_texts)
        self.assertEqual(screen.header_documentation_label.text(), "8 / 20 Lernbereiche")
        self.assertEqual(screen.overview_undocumented_metric.text(), "12")
        self.assertIsNotNone(app)

    def test_student_profile_opens_with_overview_tab(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(self._sample_student_detail())

        tab_widget = screen.findChild(QTabWidget)
        self.assertIsNotNone(tab_widget)
        self.assertEqual(tab_widget.currentIndex(), 0)
        self.assertEqual(
            [tab_widget.tabText(index) for index in range(tab_widget.count())],
            ["Überblick", "Beobachtungen", "Kompetenzen", "Bericht", "Dateien"],
        )
        self.assertIsNotNone(app)

    def test_student_profile_keeps_child_and_current_section_visible(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(self._sample_student_detail())

        screen.profile_navigation.set_current_key("competencies", emit=True)

        self.assertEqual(screen.name_label.text(), "Emma Müller")
        self.assertIn("Grashüpfer", screen.meta_label.text())
        self.assertEqual(screen.course_badge.label.text(), "Kurs 1")
        self.assertEqual(
            screen.course_badge.accessibleName(),
            "Kurszugehörigkeit: Kurs 1",
        )
        self.assertEqual(screen.profile_tabs.currentIndex(), 2)
        self.assertTrue(screen.profile_tabs.tabBar().isHidden())
        self.assertEqual(
            screen.profile_primary_action.property("buttonRole"),
            "primary",
        )
        self.assertIsNotNone(app)

    def test_student_profile_navigation_is_keyboard_reachable_and_complete(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(self._sample_student_detail())

        for expected_index in range(1, 5):
            current_button = screen.profile_navigation.button_group.buttons()[
                expected_index - 1
            ]
            QTest.keyClick(current_button, Qt.Key.Key_Right)
            self.assertEqual(screen.profile_tabs.currentIndex(), expected_index)

        self.assertEqual(
            tuple(screen.profile_tabs.tabText(index) for index in range(5)),
            ("Überblick", "Beobachtungen", "Kompetenzen", "Bericht", "Dateien"),
        )
        self.assertIsNotNone(app)

    def test_student_profile_overview_summarizes_documented_student(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        documentation_statuses = (
            StudentDocumentationSubjectStatus("deutsch", "Deutsch", 2, 3, (), 0),
            StudentDocumentationSubjectStatus("epu", "EPU", 1, 2, (), 1),
        )
        orientation_status = self._cockpit_status(
            self.german_listening_competency_id,
            "Texte sinnentnehmend lesen",
            subject_id="deutsch",
            subject_name="Deutsch",
            learning_area="Mit Texten und Medien umgehen",
            topic="Lesen",
            observation_count=2,
            evidence=(
                StudentCompetencyEvidenceViewModel(
                    "OBS-000001", "2026-03-01", "-", "deutsch", "Deutsch",
                    "Mit Texten und Medien umgehen", "Lesen",
                    "Texte sinnentnehmend lesen", "Leseübung",
                ),
                StudentCompetencyEvidenceViewModel(
                    "OBS-000002", "2026-07-05", "+", "deutsch", "Deutsch",
                    "Mit Texten und Medien umgehen", "Lesen",
                    "Texte sinnentnehmend lesen", "Präsentation",
                ),
            ),
        )
        screen.set_student(
            self._sample_student_detail(),
            self._sample_many_observations(),
            documentation_statuses=documentation_statuses,
            profile_dashboard=build_student_profile_dashboard(
                (orientation_status,),
                documentation_statuses,
                date(2026, 7, 14),
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Arbeitsprofil", label_texts)
        self.assertIn("Lernentwicklung", label_texts)
        self.assertIn("Texte sinnentnehmend lesen", label_texts)
        self.assertIn("Ausgangslage", label_texts)
        self.assertIn("Mit Unterstützung", label_texts)
        self.assertIn("Aktueller dokumentierter Stand", label_texts)
        self.assertIn("Kenntnisse meist anwenden", label_texts)
        self.assertIn("05.07.2026", label_texts)
        self.assertIn("Beobachtung", label_texts)
        self.assertIn("„Präsentation“", label_texts)
        self.assertNotIn("Mit Unterstützung → Kenntnisse meist anwenden", label_texts)
        self.assertNotIn("01.03.2026 – 05.07.2026", label_texts)
        self.assertIn(
            "2026-07-06 · Mathematik · Projektarbeit · Neueste Beobachtung.",
            label_texts,
        )
        self.assertNotIn("Stärken", label_texts)
        self.assertNotIn("Im Blick behalten", label_texts)
        self.assertIsNone(
            screen.findChild(
                QPushButton,
                "StudentProfileOrientationEvidenceOpen",
            )
        )
        development_card = screen.findChild(
            QFrame, "StudentProfileOrientationChange"
        )
        screen.resize(1180, 760)
        screen.show()
        QApplication.processEvents()
        QTest.mouseClick(development_card, Qt.MouseButton.LeftButton)
        self.assertEqual(screen.profile_tabs.currentIndex(), 1)
        self.assertEqual(screen._focused_observation_id, "OBS-000002")
        self.assertIsNotNone(app)

    def test_student_profile_development_badges_render_all_documented_statuses(
        self,
    ) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        changes = (
            StudentProfileOrientationChangeViewModel(
                "CMP-TEST-1", "Kommunikation", "Deutsch", "Gespräche führen",
                "--", "Erste Erfahrungen", "-", "Mit Unterstützung",
                "01.02.2026 – 01.03.2026", date(2026, 3, 1),
                StudentProfileOrientationEventViewModel(
                    date(2026, 3, 1), "-", "Mit Unterstützung", "observation",
                    "Beobachtung", "OBS-TEST-1",
                    "Beobachtung vom 01.03.2026: Mit Unterstützung · Gesprächskreis",
                ),
                1,
            ),
            StudentProfileOrientationChangeViewModel(
                "CMP-TEST-2", "Zeit", "Mathematik", "Uhrzeit",
                "+", "Kenntnisse meist anwenden", "++", "Eigenständig und sicher",
                "01.04.2026 – 01.05.2026", date(2026, 5, 1),
                StudentProfileOrientationEventViewModel(
                    date(2026, 5, 1), "++", "Eigenständig und sicher", "confirmation",
                    "Kompetenz bestätigt", "",
                    "Kompetenz bestätigt am 01.05.2026: Eigenständig und sicher",
                ),
                2,
            ),
        )

        cards = tuple(screen._orientation_change_row(change) for change in changes)
        badges = tuple(
            badge
            for card in cards
            for badge in card.findChildren(QLabel, "StatusBadge")
        )

        self.assertEqual(
            tuple(badge.property("ratingToken") for badge in badges),
            ("--", "-", "+", "++"),
        )
        self.assertTrue(all(badge.property("ratingBadge") for badge in badges))
        self.assertEqual(
            tuple(badge.text() for badge in badges),
            (
                "Erste Erfahrungen",
                "Mit Unterstützung",
                "Kenntnisse meist anwenden",
                "Eigenständig und sicher",
            ),
        )
        self.assertIsNotNone(app)

    def test_student_profile_historical_development_is_quiet_and_read_only(
        self,
    ) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        status = self._cockpit_status(
            "CMP-HIST-1",
            "Zeitspannen bestimmen (alter Katalogstand)",
            subject_id="mathematik",
            subject_name="Mathematik",
            confirmed_rating="+",
            confirmed_at="2026-06-12T09:00:00+00:00",
            historical=True,
            evidence=(StudentCompetencyEvidenceViewModel(
                "OBS-HIST-1", "2026-02-01", "-", "mathematik", "Mathematik",
                "Größen und Messen", "Zeit",
                "Zeitspannen bestimmen (alter Katalogstand)", "Unterricht",
            ),),
        )
        dashboard = build_student_profile_dashboard(
            (status,), (), date(2026, 7, 14)
        )
        screen.set_student(
            self._sample_student_detail(),
            profile_dashboard=dashboard,
        )

        historical_badge = screen.findChild(QLabel, "StudentProfileHistoricalBadge")
        development_card = screen.findChild(
            QFrame, "StudentProfileOrientationChange"
        )

        self.assertEqual(historical_badge.text(), "Historische Referenz")
        self.assertIsNone(
            screen.findChild(QPushButton, "StudentProfileOrientationEvidenceOpen")
        )
        QTest.keyClick(development_card, Qt.Key.Key_Return)
        self.assertEqual(screen.profile_tabs.currentIndex(), 2)
        self.assertIsNotNone(app)

    def test_student_profile_development_cards_fit_supported_profile_sizes(self) -> None:
        app = QApplication.instance() or QApplication([])
        status = self._cockpit_status(
            self.german_listening_competency_id,
            "Texte sinnentnehmend lesen und zentrale Aussagen benennen",
            subject_id="deutsch",
            subject_name="Deutsch",
            topic="Lesen",
            evidence=(
                StudentCompetencyEvidenceViewModel(
                    "OBS-000001", "2026-03-01", "-", "deutsch", "Deutsch",
                    "Mit Texten und Medien umgehen", "Lesen",
                    "Texte sinnentnehmend lesen", "Leseübung",
                ),
                StudentCompetencyEvidenceViewModel(
                    "OBS-000002", "2026-07-05", "+", "deutsch", "Deutsch",
                    "Mit Texten und Medien umgehen", "Lesen",
                    "Texte sinnentnehmend lesen", "Präsentation",
                ),
            ),
        )
        dashboard = build_student_profile_dashboard(
            (status,), (), date(2026, 7, 14)
        )

        for width, height, compact in ((1180, 760, True), (1400, 900, False)):
            with self.subTest(size=(width, height)):
                screen = student_profile_screen.StudentProfileScreen()
                screen.set_student(
                    self._sample_student_detail(),
                    profile_dashboard=dashboard,
                )
                screen.resize(width, height)
                screen.show()
                QApplication.processEvents()
                overview_scroll = screen.profile_tabs.widget(0)
                development_card = screen.findChild(
                    QFrame, "StudentProfileOrientationChange"
                )

                self.assertIsInstance(overview_scroll, QScrollArea)
                self.assertEqual(overview_scroll.horizontalScrollBar().maximum(), 0)
                self.assertEqual(screen._overview_compact, compact)
                self.assertLessEqual(development_card.minimumSizeHint().height(), 180)
                screen.close()
        self.assertIsNotNone(app)

    def test_student_profile_overview_does_not_invent_strengths_without_data(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        documentation_statuses = (
            StudentDocumentationSubjectStatus("deutsch", "Deutsch", 0, 3, (), 0),
        )
        screen.set_student(
            self._sample_student_detail(),
            documentation_statuses=documentation_statuses,
            profile_dashboard=build_student_profile_dashboard(
                (), documentation_statuses, date(2026, 7, 14)
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]
        strength_lines = [text for text in label_texts if text.startswith("✓ ")]

        self.assertIn(
            "Noch keine Entwicklung über mehrere Zeitpunkte sichtbar",
            label_texts,
        )
        self.assertEqual(screen.header_documentation_label.text(), "0 / 3 Lernbereiche")
        self.assertEqual(screen.overview_undocumented_metric.text(), "3")
        self.assertEqual(strength_lines, [])
        self.assertIn("Deutsch", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_overview_resets_when_switching_students(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_many_observations(),
        )
        tab_widget = screen.findChild(QTabWidget)
        tab_widget.setCurrentIndex(2)

        screen.set_student(
            StudentDetailViewModel(
                f"{STUDENT_ID_PREFIX}-000002",
                "Noah Beispiel",
                "Grashüpfer",
                "Kurs 2",
                "",
                True,
            ),
            profile_dashboard=build_student_profile_dashboard(
                (),
                (StudentDocumentationSubjectStatus(
                    "deutsch", "Deutsch", 0, 2, (), 0
                ),),
                date(2026, 7, 14),
            ),
        )
        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertEqual(tab_widget.currentIndex(), 0)
        self.assertIn("Noah Beispiel", label_texts)
        self.assertEqual(screen.header_documentation_label.text(), "0 / 2 Lernbereiche")
        self.assertEqual(screen.overview_undocumented_metric.text(), "2")
        self.assertNotIn("Neueste Beobachtung.", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_overview_view_model_uses_existing_data_only(self) -> None:
        overview = build_student_profile_overview(
            (),
            (),
            (
                StudentDocumentationSubjectStatus("deutsch", "Deutsch", 0, 2, (), 0),
            ),
        )

        self.assertEqual(overview.strengths, ())
        self.assertEqual(
            overview.watch_items,
            (
                "Deutsch weiter beobachten",
            ),
        )
        self.assertEqual(
            overview.reliability_hint,
            "Noch keine Beobachtungen für eine verlässliche Einschätzung.",
        )

    def test_student_profile_overview_watch_items_use_documentation_subjects(self) -> None:
        overview = build_student_profile_overview(
            (),
            (
                StudentCompetencySubjectGroup(
                    "epu",
                    "EPU",
                    (
                        StudentCompetencyStatusViewModel(
                            self.epu_competency_id,
                            "Raum und Zeit",
                            "epu",
                            "EPU",
                            "-",
                            "- teilweise erreicht",
                            "2026-07-03",
                            11,
                            ("-",),
                            1,
                        ),
                    ),
                ),
            ),
            (
                StudentDocumentationSubjectStatus("deutsch", "Deutsch", 0, 2, (), 0),
            ),
        )

        self.assertNotIn("Raum und Zeit weiter beobachten", overview.watch_items)
        self.assertEqual(overview.watch_items, ("Deutsch weiter beobachten",))

    def test_students_screen_shows_compact_documentation_column_and_quick_action(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = students_screen.StudentsScreen()
        observation_student_ids: list[str] = []
        screen.observation_requested.connect(observation_student_ids.append)
        screen.set_students(
            (
                StudentListItem(
                    "STU-000001",
                    "Anna",
                    "Muster",
                    "GRP-1",
                    "Gruppe",
                    "CRS-1",
                    "Kurs 1",
                    documentation_status=documentation_summary_from_subjects(
                        (
                            StudentDocumentationSubjectStatus(
                                "deutsch",
                                "Deutsch",
                                1,
                                2,
                                (),
                                0,
                            ),
                        )
                    ),
                ),
            )
        )

        self.assertEqual(screen.table.columnCount(), 5)
        self.assertEqual(screen.table.horizontalHeaderItem(1).text(), "Stammgruppe")
        self.assertEqual(screen.table.item(0, 1).text(), "Gruppe")
        self.assertEqual(
            screen.table.item(0, 1).data(Qt.ItemDataRole.AccessibleTextRole),
            "Stammgruppe: Gruppe",
        )
        self.assertEqual(screen.table.horizontalHeaderItem(3).text(), "Dokumentation")
        self.assertEqual(screen.table.horizontalHeaderItem(4).text(), "Aktion")
        self.assertEqual(
            screen.table.item(0, 3).text(),
            "1/2 Bereiche · teilweise dokumentiert",
        )
        self.assertNotIn("Deutsch:", screen.table.item(0, 3).text())
        action_widget = screen.table.cellWidget(0, 4)
        self.assertIsNotNone(action_widget)
        action_button = action_widget.findChild(QPushButton)
        self.assertIsNotNone(action_button)
        self.assertEqual(action_button.text(), "Beobachten")
        self.assertEqual(action_button.toolTip(), "Neue Beobachtung für Anna Muster")
        action_button.click()
        self.assertEqual(observation_student_ids, ["STU-000001"])
        self.assertIsNotNone(app)

    def test_students_screen_hides_redundant_group_column_for_one_group(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = students_screen.StudentsScreen()

        screen.set_students((), show_group_column=False)
        self.assertTrue(screen.table.isColumnHidden(1))

        screen.set_students((), show_group_column=True)
        self.assertFalse(screen.table.isColumnHidden(1))
        self.assertIsNotNone(app)

    def test_students_screen_shows_back_button_for_filtered_lists(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = students_screen.StudentsScreen()
        back_requests: list[bool] = []
        screen.back_to_overview_requested.connect(lambda: back_requests.append(True))

        screen.set_students((), group_filter_name="Stammgruppe: Grashüpfer")
        self.assertTrue(screen.back_to_overview_button.isHidden())
        screen.set_students(
            (),
            group_filter_name="Stammgruppe: Grashüpfer",
            show_back_button=True,
        )

        self.assertFalse(screen.back_to_overview_button.isHidden())
        self.assertEqual(screen.back_to_overview_button.text(), "Zurück zur Auswahl")
        screen.back_to_overview_button.click()
        self.assertEqual(back_requests, [True])
        self.assertIsNotNone(app)

    def test_student_profile_undocumented_competencies_only_open_inside_topic(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(self.german_listening_competency_id, "Volle Stunden"),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        topic_button = screen.findChild(QPushButton, "CompetencyCockpitTopicButton")
        topic_details = screen.findChild(QWidget, "CompetencyCockpitTopicDetails")
        competency_button = screen.findChild(
            QPushButton, "CompetencyCockpitCompetencyButton"
        )

        self.assertTrue(topic_details.isHidden())
        self.assertTrue(competency_button.text().startswith("☐ "))
        topic_button.click()
        self.assertFalse(topic_details.isHidden())
        self.assertIsNotNone(app)

    def test_competency_cockpit_disclosures_return_to_stable_height_without_effects(
        self,
    ) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        statuses = tuple(
            self._cockpit_status(
                f"CMP-LAYOUT-{index}",
                f"Kompetenz {index}",
                subject_id="deutsch",
                subject_name="Deutsch",
                topic=f"Thema {index // 2}",
            )
            for index in range(8)
        )
        screen.set_student(
            self._sample_student_detail(),
            competency_cockpit=build_student_competency_cockpit(statuses),
        )
        screen.profile_tabs.setCurrentIndex(2)
        screen.resize(1180, 760)
        screen.show()
        app.processEvents()
        initial_height = screen.competency_cockpit_container.sizeHint().height()
        buttons = (
            *screen.findChildren(QPushButton, "CompetencyCockpitSubjectButton"),
            *screen.findChildren(QPushButton, "CompetencyCockpitLearningAreaButton"),
            *screen.findChildren(QPushButton, "CompetencyCockpitTopicButton"),
        )
        cockpit_cards = (
            *screen.findChildren(QFrame, "CompetencyCockpitSubjectCard"),
            *screen.findChildren(QFrame, "CompetencyCockpitLearningAreaCard"),
            *screen.findChildren(QFrame, "CompetencyCockpitTopicCard"),
            *screen.findChildren(QFrame, "CompetencyCockpitCompetencyRow"),
        )
        self.assertTrue(cockpit_cards)
        self.assertTrue(
            all(card.graphicsEffect() is None for card in cockpit_cards)
        )
        self.assertTrue(
            all(card.focusPolicy() == Qt.FocusPolicy.StrongFocus for card in cockpit_cards)
        )
        opened_heights: list[int] = []
        for button in buttons:
            button.click()
            app.processEvents()
            opened_heights.append(
                screen.competency_cockpit_container.sizeHint().height()
            )
            self.assertIsNone(button.graphicsEffect())
        self.assertEqual(opened_heights, sorted(opened_heights))

        for button in reversed(buttons):
            button.click()
            app.processEvents()
        self.assertEqual(
            screen.competency_cockpit_container.sizeHint().height(),
            initial_height,
        )
        screen.close()
        self.assertIsNotNone(app)

    def test_student_profile_renders_student_documents(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (),
            (),
            None,
            (),
            (
                StudentDocumentViewModel(
                    "MED-000001",
                    f"{STUDENT_ID_PREFIX}-000001",
                    "",
                    "Foerderplan",
                    "Bericht",
                    str(Path(self.temp_dir.name) / "Foerderplan.pdf"),
                    "Foerderplan.pdf",
                    "2026-07-04T12:00:00+00:00",
                ),
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Dokumente & Medien", label_texts)
        self.assertIn("Bericht · Foerderplan", label_texts)
        self.assertIn("2026-07-04", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_emits_document_remove_request(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        removed_documents: list[tuple[str, str]] = []
        screen.document_remove_requested.connect(
            lambda student_id, document_id: removed_documents.append(
                (student_id, document_id)
            )
        )
        screen.set_student(
            self._sample_student_detail(),
            (),
            (),
            None,
            (),
            (
                StudentDocumentViewModel(
                    "MED-000001",
                    f"{STUDENT_ID_PREFIX}-000001",
                    "",
                    "Foerderplan",
                    "Bericht",
                    str(Path(self.temp_dir.name) / "Foerderplan.pdf"),
                    "Foerderplan.pdf",
                    "2026-07-04T12:00:00+00:00",
                ),
            ),
        )

        remove_button = screen.findChild(QPushButton, "DocumentRemoveButton")
        self.assertIsNotNone(remove_button)
        remove_button.click()

        self.assertEqual(
            removed_documents,
            [(f"{STUDENT_ID_PREFIX}-000001", "MED-000001")],
        )
        self.assertIsNotNone(app)

    def test_observation_details_render_linked_attachments(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (
                ObservationListItem(
                    "OBS-000001",
                    f"{STUDENT_ID_PREFIX}-000001",
                    "2026-07-04",
                    "Deutsch",
                    "Leseübung",
                    "Liest.",
                    (),
                    (
                        StudentDocumentViewModel(
                            "MED-000001",
                            f"{STUDENT_ID_PREFIX}-000001",
                            "OBS-000001",
                            "Arbeitsprobe Lesen",
                            "Arbeitsprobe",
                            str(Path(self.temp_dir.name) / "Arbeitsprobe.txt"),
                            "Arbeitsprobe.txt",
                            "2026-07-04T12:00:00+00:00",
                        ),
                    ),
                ),
            ),
        )
        details_button = screen.findChild(QPushButton, "ObservationTextActionButton")

        self.assertIsNotNone(details_button)
        details_button.click()
        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Dokumente & Medien", label_texts)
        self.assertIn("Arbeitsprobe · Arbeitsprobe Lesen", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_copies_report_text_to_clipboard(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (),
            (),
            self._sample_report_preview(),
        )

        screen.copy_report_text_to_clipboard()
        clipboard_text = QApplication.clipboard().text()

        self.assertIn("Schüler: Emma Müller", clipboard_text)
        self.assertIn("Erstellt am:", clipboard_text)
        self.assertIn("## Deutsch", clipboard_text)
        self.assertIn(
            "Mit Texten und Medien umgehen · "
            "Aktueller Stand: Kenntnisse meist anwenden · von Laura bestätigt",
            clipboard_text,
        )
        self.assertEqual(screen.report_feedback_label.text(), "Bericht wurde kopiert.")
        self.assertIsNotNone(app)

    def test_student_profile_exports_report_text_file(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (),
            (),
            self._sample_report_preview(),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "bericht.md"

            screen.export_report_text_to_path(export_path)

            report_text = export_path.read_text(encoding="utf-8")

        self.assertIn("Schüler: Emma Müller", report_text)
        self.assertIn("## Deutsch", report_text)
        self.assertIn("Beispielbeobachtungen", report_text)
        self.assertTrue(report_text.endswith("\n"))
        self.assertIsNotNone(app)

    def test_student_profile_cockpit_has_no_confirmation_mutation_actions(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Volle Stunden",
                documentation_state="observed_unconfirmed",
                observed_proposal="+",
                observation_count=1,
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        buttons = {button.text(): button for button in screen.findChildren(QPushButton)}
        rating_select = screen.findChild(QComboBox, "CompetencyConfirmationRatingSelect")

        self.assertNotIn("Vorschlag aus Beobachtungen übernehmen", buttons)
        self.assertNotIn("Aktuell bestätigen", buttons)
        self.assertIsNone(rating_select)
        self.assertIsNotNone(app)

    def test_student_profile_competency_cockpit_subjects_are_collapsible(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(self.german_listening_competency_id, "Volle Stunden"),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        details_button = screen.findChild(
            QPushButton, "CompetencyCockpitSubjectButton"
        )
        details_container = screen.findChild(
            QWidget, "CompetencyCockpitSubjectDetails"
        )

        self.assertIsNotNone(details_button)
        self.assertIsNotNone(details_container)
        self.assertEqual(details_button.text(), "Öffnen ▾")
        self.assertTrue(details_container.isHidden())
        markers = screen.findChildren(components.SubjectAccentMarker)
        self.assertEqual(
            tuple(marker.property("subjectId") for marker in markers),
            ("mathematik",),
        )

        details_button.click()

        self.assertFalse(details_container.isHidden())
        self.assertEqual(details_button.text(), "Schließen ▴")
        self.assertIsNotNone(app)

    def test_student_profile_cockpit_learning_area_card_opens_without_closing_subject(
        self,
    ) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id,
                "Zahlen darstellen",
                learning_area="Arithmetik - mit Zahlen und Symbolen umgehen",
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        screen.profile_tabs.setCurrentIndex(2)
        screen.resize(1180, 760)
        screen.show()
        QApplication.processEvents()
        subject_button = screen.findChild(
            QPushButton, "CompetencyCockpitSubjectButton"
        )
        subject_details = screen.findChild(QWidget, "CompetencyCockpitSubjectDetails")
        area_card = screen.findChild(QFrame, "CompetencyCockpitLearningAreaCard")
        area_button = screen.findChild(
            QPushButton, "CompetencyCockpitLearningAreaButton"
        )
        area_details = screen.findChild(
            QWidget, "CompetencyCockpitLearningAreaDetails"
        )

        subject_button.click()
        self.assertFalse(subject_details.isHidden())
        self.assertTrue(area_details.isHidden())

        area_title = area_card.findChild(QLabel)
        QTest.mouseClick(
            area_card,
            Qt.MouseButton.LeftButton,
            pos=area_title.geometry().center(),
        )

        self.assertFalse(subject_details.isHidden())
        self.assertFalse(area_details.isHidden())
        self.assertEqual(area_button.text(), "Schließen ▴")

        area_button.click()
        self.assertFalse(subject_details.isHidden())
        self.assertTrue(area_details.isHidden())
        self.assertEqual(area_card.focusPolicy(), Qt.FocusPolicy.StrongFocus)
        QTest.keyClick(area_card, Qt.Key.Key_Return)
        self.assertFalse(subject_details.isHidden())
        self.assertFalse(area_details.isHidden())
        self.assertIsNotNone(app)

    def test_student_profile_cockpit_topic_card_and_button_toggle_same_details(
        self,
    ) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(self.german_listening_competency_id, "Volle Stunden"),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        screen.profile_tabs.setCurrentIndex(2)
        screen.resize(1180, 760)
        screen.show()
        QApplication.processEvents()
        screen.findChild(QPushButton, "CompetencyCockpitSubjectButton").click()
        screen.findChild(QPushButton, "CompetencyCockpitLearningAreaButton").click()
        topic_card = screen.findChild(QFrame, "CompetencyCockpitTopicCard")
        topic_button = screen.findChild(QPushButton, "CompetencyCockpitTopicButton")
        topic_details = screen.findChild(QWidget, "CompetencyCockpitTopicDetails")

        self.assertTrue(topic_details.isHidden())
        topic_title = topic_card.findChild(QLabel)
        QTest.mouseClick(
            topic_card,
            Qt.MouseButton.LeftButton,
            pos=topic_title.geometry().center(),
        )
        self.assertFalse(topic_details.isHidden())
        topic_button.click()
        self.assertTrue(topic_details.isHidden())
        self.assertIsNotNone(app)

    def test_student_profile_cockpit_competency_row_is_pointer_and_keyboard_activatable(
        self,
    ) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(self.german_listening_competency_id, "Volle Stunden"),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        screen.profile_tabs.setCurrentIndex(2)
        screen.resize(1180, 760)
        screen.show()
        QApplication.processEvents()
        screen.findChild(QPushButton, "CompetencyCockpitSubjectButton").click()
        screen.findChild(QPushButton, "CompetencyCockpitLearningAreaButton").click()
        screen.findChild(QPushButton, "CompetencyCockpitTopicButton").click()
        row = screen.findChild(QFrame, "CompetencyCockpitCompetencyRow")
        button = screen.findChild(QPushButton, "CompetencyCockpitCompetencyButton")
        details = screen.findChild(QWidget, "CompetencyCockpitCompetencyDetails")

        self.assertEqual(row.focusPolicy(), Qt.FocusPolicy.StrongFocus)
        self.assertTrue(details.isHidden())
        QTest.mouseClick(row, Qt.MouseButton.LeftButton, pos=QPoint(1, 0))
        self.assertFalse(details.isHidden())
        button.click()
        self.assertTrue(details.isHidden())
        QTest.keyClick(row, Qt.Key.Key_Space)
        self.assertFalse(details.isHidden())
        self.assertIsNotNone(app)

    def test_student_profile_historical_competency_card_stays_read_only(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                "CMP-000099",
                "Historische Zeitkompetenz",
                documentation_state="confirmed",
                confirmed_rating="+",
                historical=True,
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        screen.profile_tabs.setCurrentIndex(2)
        screen.resize(1180, 760)
        screen.show()
        QApplication.processEvents()
        historical = screen.findChild(QWidget, "CompetencyCockpitHistoricalDetails")
        screen.findChild(QPushButton, "CompetencyCockpitHistoricalButton").click()
        historical.findChild(QPushButton, "CompetencyCockpitSubjectButton").click()
        historical.findChild(
            QPushButton, "CompetencyCockpitLearningAreaButton"
        ).click()
        historical.findChild(QPushButton, "CompetencyCockpitTopicButton").click()
        row = historical.findChild(QFrame, "CompetencyCockpitCompetencyRow")
        details = historical.findChild(QWidget, "CompetencyCockpitCompetencyDetails")

        QTest.mouseClick(row, Qt.MouseButton.LeftButton, pos=QPoint(1, 0))

        self.assertFalse(details.isHidden())
        self.assertFalse(
            any(
                button.text().strip() == "+"
                for button in historical.findChildren(QPushButton)
            )
        )
        self.assertIsNone(
            historical.findChild(QComboBox, "CompetencyConfirmationRatingSelect")
        )
        self.assertIsNotNone(app)

    def test_competency_cockpit_projects_subject_area_topic_and_progress(self) -> None:
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Volle Stunden",
                documentation_state="observed_unconfirmed",
                observation_count=1,
                observed_proposal="+",
            ),
            self._cockpit_status(self.german_word_competency_id, "Halbe Stunden"),
        ))

        subject = cockpit.subjects[0]
        area = subject.learning_areas[0]
        topic = area.topics[0]
        self.assertEqual(subject.subject_display_name, "Mathematik")
        self.assertEqual((subject.documented_count, subject.total_count), (1, 2))
        self.assertEqual(subject.progress_percent, 50)
        self.assertEqual((area.documented_count, area.total_count), (1, 2))
        self.assertEqual(topic.competency_group, "Zeit")

    def test_competency_cockpit_handles_empty_and_complete_subjects(self) -> None:
        empty = build_student_competency_cockpit((
            self._cockpit_status(self.german_listening_competency_id, "Volle Stunden"),
        )).subjects[0]
        complete = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_word_competency_id, "Halbe Stunden",
                documentation_state="confirmed",
                confirmed_rating="+",
            ),
        )).subjects[0]

        self.assertEqual((empty.documented_count, empty.progress_percent), (0, 0))
        self.assertEqual((complete.documented_count, complete.progress_percent), (1, 100))

    def test_competency_cockpit_subject_without_observations_is_not_documented(self) -> None:
        subject = build_student_competency_cockpit((
            self._cockpit_status(self.german_listening_competency_id, "Volle Stunden"),
            self._cockpit_status(self.german_word_competency_id, "Halbe Stunden"),
        )).subjects[0]

        self.assertEqual(subject.documented_count, 0)
        self.assertEqual(subject.total_count, 2)

    def test_student_profile_renders_cockpit_cards_and_neutral_progress(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Volle Stunden",
                documentation_state="observed_unconfirmed",
                observation_count=1,
                last_observation_date="2026-07-12",
                observed_proposal="+",
            ),
            self._cockpit_status(self.german_word_competency_id, "Halbe Stunden"),
        ))
        screen.set_student(
            self._sample_student_detail(),
            competency_cockpit=cockpit,
        )

        subject_card = screen.findChild(QFrame, "CompetencyCockpitSubjectCard")
        area_card = screen.findChild(QFrame, "CompetencyCockpitLearningAreaCard")
        progress = screen.findChild(QProgressBar, "CompetencyCockpitProgressBar")
        label_texts = [label.text() for label in screen.findChildren(QLabel)]
        self.assertIsNotNone(subject_card)
        self.assertIsNotNone(area_card)
        self.assertEqual(progress.value(), 50)
        self.assertIn("1 / 2 Kompetenzen dokumentiert", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_cockpit_filters_each_documentation_state(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(self.german_listening_competency_id, "Ohne Dokumentation"),
            self._cockpit_status(
                self.german_word_competency_id, "Beobachtet", documentation_state="observed_unconfirmed",
                observation_count=1,
            ),
            self._cockpit_status(
                self.epu_competency_id, "Nur bestätigt", documentation_state="confirmed",
                confirmed_rating="+",
            ),
            self._cockpit_status(
                self.math_addition_competency_id, "Neuere Beobachtung", documentation_state="newer_observations",
                confirmed_rating="+", observation_count=1,
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        state_filter = screen.findChild(
            QComboBox, "CompetencyCockpitDocumentationFilter"
        )

        expected_labels = {
            "Dokumentiert": {"Beobachtet", "Nur bestätigt", "Neuere Beobachtung"},
            "Noch nicht dokumentiert": {"Ohne Dokumentation"},
            "Beobachtet, noch nicht bestätigt": {"Beobachtet"},
            "Bestätigter Stand": {"Nur bestätigt", "Neuere Beobachtung"},
            "Neuere Beobachtungen nach Bestätigung": {"Neuere Beobachtung"},
        }
        for filter_label, expected in expected_labels.items():
            state_filter.setCurrentIndex(state_filter.findText(filter_label))
            visible_labels = {
                button.text()[2:]
                for button in screen.findChildren(
                    QPushButton, "CompetencyCockpitCompetencyButton"
                )
            }
            with self.subTest(filter_label=filter_label):
                self.assertEqual(visible_labels, expected)

        self.assertIsNotNone(app)

    def test_student_profile_cockpit_search_has_no_meaningless_stage_segments(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id,
                "Volle Stunden ablesen",
                learning_stage="stage_1_3",
            ),
            self._cockpit_status(
                self.german_word_competency_id,
                "Uhrzeiten minutengenau ablesen",
                learning_stage="stage_4",
            ),
            self._cockpit_status(
                self.epu_competency_id,
                "Uhrzeiten notieren",
                learning_stage="cross_stage",
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)

        default_labels = {
            button.text()[2:]
            for button in screen.findChildren(
                QPushButton,
                "CompetencyCockpitCompetencyButton",
            )
        }
        self.assertEqual(
            default_labels,
            {
                "Volle Stunden ablesen",
                "Uhrzeiten minutengenau ablesen",
                "Uhrzeiten notieren",
            },
        )

        screen.competency_search_input.setText("minutengenau")
        self.assertEqual(
            [
                button.text()[2:]
                for button in screen.findChildren(
                    QPushButton,
                    "CompetencyCockpitCompetencyButton",
                )
            ],
            ["Uhrzeiten minutengenau ablesen"],
        )
        self.assertIsNone(
            screen.findChild(QWidget, "CompetencyCockpitStageFilter")
        )
        visible_texts = {
            widget.text()
            for widget in (
                *screen.findChildren(QLabel),
                *screen.findChildren(QPushButton),
            )
            if widget.isVisible()
        }
        self.assertNotIn("Passende Kompetenzen", visible_texts)
        self.assertNotIn("Klassenstufe 4", visible_texts)
        self.assertEqual(
            screen.competency_subject_filter.itemText(0),
            "Alle Kompetenzen",
        )
        self.assertIsNotNone(app)

    def test_work_learning_cockpit_renders_all_13_named_rows_without_effects(
        self,
    ) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = self.adapter.competency_cockpit_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        expected_labels = tuple(
            entry.competency_label
            for entry in self.curriculum_adapter.list_entries()
            if entry.subject_key == "arbeits_lernkompetenz"
        )
        screen.set_student(
            self._sample_student_detail(),
            competency_cockpit=cockpit,
        )
        screen.profile_tabs.setCurrentIndex(2)
        screen.competency_subject_filter.setCurrentIndex(
            screen.competency_subject_filter.findData("arbeits_lernkompetenz")
        )
        screen.resize(1180, 760)
        screen.show()
        app.processEvents()

        for object_name in (
            "CompetencyCockpitSubjectButton",
            "CompetencyCockpitLearningAreaButton",
            "CompetencyCockpitTopicButton",
        ):
            screen.findChild(QPushButton, object_name).click()
        app.processEvents()
        buttons = screen.findChildren(
            QPushButton,
            "CompetencyCockpitCompetencyButton",
        )

        self.assertEqual(len(expected_labels), 13)
        self.assertEqual(
            tuple(button.text()[2:] for button in buttons),
            expected_labels,
        )
        self.assertTrue(all(button.isVisible() for button in buttons))
        self.assertTrue(all(button.width() > 0 and button.height() > 0 for button in buttons))
        for button in buttons:
            QApplication.sendEvent(button, QEvent(QEvent.Type.Enter))
            self.assertIsNone(button.graphicsEffect())
            self.assertFalse(hasattr(button, "_motion_button_controller"))

        screen.competency_search_input.setText("nicht vorhanden")
        screen.competency_search_input.clear()
        app.processEvents()
        self.assertEqual(
            len(
                screen.findChildren(
                    QFrame,
                    "CompetencyCockpitCompetencyRow",
                )
            ),
            13,
        )
        screen.close()
        self.assertIsNotNone(app)

    def test_student_profile_cockpit_combines_subject_filter_and_keeps_progress(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Deutsch dokumentiert", subject_id="deutsch",
                subject_name="Deutsch", documentation_state="observed_unconfirmed",
                observation_count=1,
            ),
            self._cockpit_status(
                self.german_word_competency_id, "Deutsch offen", subject_id="deutsch", subject_name="Deutsch",
            ),
            self._cockpit_status(
                self.epu_competency_id, "EPU offen", subject_id="epu", subject_name="EPU",
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        subject_filter = screen.findChild(QComboBox, "CompetencyCockpitSubjectFilter")
        state_filter = screen.findChild(
            QComboBox, "CompetencyCockpitDocumentationFilter"
        )
        subject_filter.setCurrentIndex(subject_filter.findText("Deutsch"))
        state_filter.setCurrentIndex(state_filter.findText("Dokumentiert"))

        buttons = screen.findChildren(QPushButton, "CompetencyCockpitCompetencyButton")
        counts = [label.text() for label in screen.findChildren(QLabel)]
        progress = screen.findChild(QProgressBar, "CompetencyCockpitProgressBar")
        self.assertEqual([button.text()[2:] for button in buttons], ["Deutsch dokumentiert"])
        self.assertIn("1 / 2 Kompetenzen dokumentiert", counts)
        self.assertEqual(progress.value(), 50)
        self.assertIsNotNone(app)

    def test_student_profile_cockpit_filter_empty_states_and_reset(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(self.german_listening_competency_id, "EPU offen", subject_id="epu", subject_name="EPU"),
            self._cockpit_status(self.german_word_competency_id, "Deutsch offen", subject_id="deutsch", subject_name="Deutsch"),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        subject_filter = screen.findChild(QComboBox, "CompetencyCockpitSubjectFilter")
        state_filter = screen.findChild(
            QComboBox, "CompetencyCockpitDocumentationFilter"
        )
        state_filter.setCurrentIndex(state_filter.findText("Dokumentiert"))

        empty = screen.findChild(QWidget, "CompetencyCockpitEmptyFilterState")
        self.assertEqual(
            empty.text(),
            "Keine Kompetenzen entsprechen den gewählten Filtern. "
            "Ändere die Suche oder setze die Filter zurück.",
        )
        subject_filter.setCurrentIndex(subject_filter.findText("EPU"))

        empty = screen.findChild(QWidget, "CompetencyCockpitEmptyFilterState")
        self.assertEqual(
            empty.text(),
            "Für EPU entsprechen keine Kompetenzen den gewählten Filtern. "
            "Ändere die Suche oder setze die Filter zurück.",
        )
        screen.findChild(QPushButton, "CompetencyCockpitFilterResetButton").click()
        self.assertEqual(subject_filter.currentText(), "Alle Kompetenzen")
        self.assertEqual(state_filter.currentText(), "Alle")
        self.assertEqual(len(screen.findChildren(QFrame, "CompetencyCockpitSubjectCard")), 2)
        self.assertEqual(
            [
                label.text()
                for label in screen.findChildren(QLabel)
                if label.text() == "0 / 1 Kompetenzen dokumentiert"
            ],
            ["0 / 1 Kompetenzen dokumentiert", "0 / 1 Kompetenzen dokumentiert"],
        )
        self.assertIsNotNone(app)

    def test_student_profile_cockpit_filters_preserve_expansion_data_and_history(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Aktiv dokumentiert", documentation_state="confirmed",
                confirmed_rating="+",
            ),
            self._cockpit_status(self.german_word_competency_id, "Aktiv offen"),
            self._cockpit_status(
                "CMP-000099", "Historisch dokumentiert", documentation_state="confirmed",
                confirmed_rating="+", historical=True,
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        screen.findChild(QPushButton, "CompetencyCockpitSubjectButton").click()
        state_filter = screen.findChild(
            QComboBox, "CompetencyCockpitDocumentationFilter"
        )
        original_subject = cockpit.subjects[0]
        original_states = tuple(
            competency.documentation_state
            for area in original_subject.learning_areas
            for topic in area.topics
            for competency in topic.competencies
        )
        state_filter.setCurrentIndex(state_filter.findText("Dokumentiert"))

        details = screen.findChild(QWidget, "CompetencyCockpitSubjectDetails")
        historical = screen.findChild(QPushButton, "CompetencyCockpitHistoricalButton")
        self.assertFalse(details.isHidden())
        self.assertEqual(historical.text(), "Historisch dokumentiert ▾")
        self.assertEqual(
            original_states,
            tuple(
                competency.documentation_state
                for area in cockpit.subjects[0].learning_areas
                for topic in area.topics
                for competency in topic.competencies
            ),
        )
        screen.reset_competency_cockpit_filters()
        self.assertFalse(
            screen.findChild(QWidget, "CompetencyCockpitSubjectDetails").isHidden()
        )
        self.assertIsNotNone(app)

    def test_student_profile_cockpit_opens_levels_and_keeps_local_state(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(self.german_listening_competency_id, "Volle Stunden"),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        subject_button = screen.findChild(QPushButton, "CompetencyCockpitSubjectButton")
        subject_details = screen.findChild(QWidget, "CompetencyCockpitSubjectDetails")

        self.assertTrue(subject_details.isHidden())
        subject_button.click()
        self.assertFalse(subject_details.isHidden())
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        restored_details = screen.findChild(QWidget, "CompetencyCockpitSubjectDetails")
        self.assertFalse(restored_details.isHidden())
        self.assertIsNotNone(app)

    def test_disclosure_reduced_motion_and_fast_switches_end_in_correct_state(self) -> None:
        app = QApplication.instance() or QApplication([])
        motion.set_reduced_motion(True)
        try:
            screen = student_profile_screen.StudentProfileScreen()
            cockpit = build_student_competency_cockpit((
                self._cockpit_status(self.german_listening_competency_id, "Volle Stunden"),
            ))
            screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
            button = screen.findChild(QPushButton, "CompetencyCockpitSubjectButton")
            details = screen.findChild(QWidget, "CompetencyCockpitSubjectDetails")

            for _index in range(3):
                button.click()

            self.assertFalse(details.isHidden())
            self.assertEqual(button.text(), "Schließen ▴")
            self.assertIsNone(button.graphicsEffect())

            dialog = self._observation_dialog_with_hierarchy()
            self._select_observation_subject(dialog, "mathematik")
            topic = self._observation_topic_button(dialog, "Zeit")
            container = self._observation_topic_container(dialog, "Zeit")
            for _index in range(4):
                topic.click()
            self.assertTrue(container.isHidden())
            self.assertEqual(topic.text(), "▸ Thema: Zeit")
        finally:
            motion.set_reduced_motion(False)
        self.assertIsNotNone(app)

    def test_student_profile_cockpit_separates_legacy_section(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(self.german_listening_competency_id, "Volle Stunden"),
            self._cockpit_status(
                "CMP-000099", "Historische Zeitkompetenz",
                documentation_state="confirmed",
                confirmed_rating="+",
                historical=True,
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        historical_button = screen.findChild(
            QPushButton, "CompetencyCockpitHistoricalButton"
        )
        historical_details = screen.findChild(
            QWidget, "CompetencyCockpitHistoricalDetails"
        )

        self.assertEqual(len(cockpit.subjects), 1)
        self.assertEqual(len(cockpit.historical_subjects), 1)
        self.assertTrue(historical_details.isHidden())
        self.assertEqual(historical_button.text(), "Historisch dokumentiert ▾")
        self.assertIsNotNone(app)

    def test_competency_cockpit_observations_button_uses_profile_navigation(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Volle Stunden",
                documentation_state="observed_unconfirmed",
                observation_count=1,
                observed_proposal="+",
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        competency_button = screen.findChild(
            QPushButton, "CompetencyCockpitCompetencyButton"
        )
        competency_button.click()
        observations_button = screen.findChild(
            QPushButton, "CompetencyCockpitObservationOpenButton"
        )
        self.assertIsNone(observations_button)

        screen.set_observations(self._sample_filter_observations())
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Volle Stunden",
                documentation_state="observed_unconfirmed",
                observation_count=1,
                observed_proposal="+",
                evidence=(
                    StudentCompetencyEvidenceViewModel(
                        "OBS-000001", "2026-07-03", "+", "mathematik",
                        "Mathematik", "Größen & Messen", "Zeit",
                        "Volle Stunden", "Lernzielkontrolle",
                    ),
                ),
            ),
        ))
        screen.set_student(
            self._sample_student_detail(),
            self._sample_filter_observations(),
            competency_cockpit=cockpit,
        )
        screen.profile_tabs.setCurrentIndex(2)
        screen.findChild(QPushButton, "CompetencyCockpitCompetencyButton").click()
        observations_button = screen.findChild(
            QPushButton, "CompetencyCockpitObservationOpenButton"
        )
        observations_button.click()

        self.assertEqual(screen.profile_tabs.currentIndex(), 1)
        self.assertIsNotNone(
            screen.findChild(QLabel, "ProfileObservationFocusHint")
        )
        self.assertIsNotNone(app)

    def test_competency_detail_keeps_confirmation_and_proposal_separate(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Volle Stunden",
                documentation_state="newer_observations",
                confirmed_rating="+", confirmed_at="2026-07-01",
                confirmation_note="Sicher im Unterricht.", observed_proposal="-",
                newer_observations=True,
                evidence=(
                    StudentCompetencyEvidenceViewModel(
                        "OBS-000002", "2026-07-04", "-", "mathematik",
                        "Mathematik", "Größen & Messen", "Zeit",
                        "Volle Stunden", "Gruppenarbeit",
                    ),
                ),
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        screen.findChild(QPushButton, "CompetencyCockpitCompetencyButton").click()
        labels = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Bestätigter Stand", labels)
        self.assertIn("Bestätigt am: 2026-07-01", labels)
        self.assertIn("Notiz: Sicher im Unterricht.", labels)
        self.assertIn("Neuere Beobachtungen vorhanden", labels)
        self.assertIn("Vorschlag aus Beobachtungen", labels)
        self.assertIn("Bewertung: -", labels)
        self.assertIsNotNone(app)

    def test_competency_detail_shows_quiet_empty_history_for_confirmation_only(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Volle Stunden", documentation_state="confirmed",
                confirmed_rating="+", confirmed_at="2026-07-01",
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        screen.findChild(QPushButton, "CompetencyCockpitCompetencyButton").click()

        self.assertIsNotNone(
            screen.findChild(QLabel, "CompetencyCockpitEvidenceEmptyState")
        )
        self.assertIsNone(screen.findChild(QLabel, "CompetencyCockpitProposalTitle"))
        self.assertIsNotNone(app)

    def test_competency_detail_evidence_is_newest_first_and_edit_uses_observation_id(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        requested_ids: list[str] = []
        screen.observation_edit_requested.connect(requested_ids.append)
        evidence = (
            StudentCompetencyEvidenceViewModel(
                "OBS-000002", "2026-07-04", "+", "mathematik", "Mathematik",
                "Größen & Messen", "Zeit", "Volle Stunden", "Gruppenarbeit",
            ),
            StudentCompetencyEvidenceViewModel(
                "OBS-000001", "2026-07-03", "-", "mathematik", "Mathematik",
                "Größen & Messen", "Zeit", "Volle Stunden", "Leseübung",
            ),
        )
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(
                self.german_listening_competency_id, "Volle Stunden", observation_count=2,
                documentation_state="observed_unconfirmed", observed_proposal="+",
                evidence=evidence,
            ),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        screen.findChild(QPushButton, "CompetencyCockpitCompetencyButton").click()
        rows = screen.findChildren(QFrame, "CompetencyCockpitEvidenceRow")
        edit_buttons = screen.findChildren(
            QPushButton, "CompetencyCockpitObservationEditButton"
        )

        self.assertEqual(len(rows), 2)
        self.assertIn("2026-07-04", rows[0].findChild(QLabel).text())
        edit_buttons[1].click()
        self.assertEqual(requested_ids, ["OBS-000001"])
        self.assertIsNotNone(app)

    def test_competency_detail_refresh_keeps_tab_and_expansion_state(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        cockpit = build_student_competency_cockpit((
            self._cockpit_status(self.german_listening_competency_id, "Volle Stunden"),
        ))
        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)
        screen.profile_tabs.setCurrentIndex(2)
        screen.findChild(QPushButton, "CompetencyCockpitSubjectButton").click()
        screen.findChild(QPushButton, "CompetencyCockpitLearningAreaButton").click()
        screen.findChild(QPushButton, "CompetencyCockpitTopicButton").click()
        screen.findChild(QPushButton, "CompetencyCockpitCompetencyButton").click()

        screen.set_student(self._sample_student_detail(), competency_cockpit=cockpit)

        self.assertEqual(screen.profile_tabs.currentIndex(), 2)
        self.assertFalse(
            screen.findChild(QWidget, "CompetencyCockpitCompetencyDetails").isHidden()
        )
        self.assertIsNotNone(app)

    def test_profile_refresh_keeps_observation_filters_and_scroll_state(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        observations = self._sample_many_observations()
        screen.set_student(self._sample_student_detail(), observations)
        screen.profile_tabs.setCurrentIndex(1)
        screen.observation_subject_filter.setCurrentIndex(
            screen.observation_subject_filter.findText("EPU")
        )
        screen.observation_rating_filter.setCurrentIndex(
            screen.observation_rating_filter.findText("+")
        )
        screen.observation_search_input.setText("verbindet")
        screen.show_all_observations = True
        observations_scroll = screen.profile_tabs.widget(1)
        self.assertIsInstance(observations_scroll, QScrollArea)
        observations_scroll.verticalScrollBar().setValue(12)

        screen.set_student(self._sample_student_detail(), observations)

        self.assertEqual(screen.profile_tabs.currentIndex(), 1)
        self.assertEqual(screen.observation_subject_filter.currentText(), "EPU")
        self.assertEqual(screen.observation_rating_filter.currentText(), "+")
        self.assertEqual(screen.observation_search_input.text(), "verbindet")
        self.assertTrue(screen.show_all_observations)
        self.assertEqual(
            observations_scroll.verticalScrollBar().value(),
            min(12, observations_scroll.verticalScrollBar().maximum()),
        )
        self.assertIsNotNone(app)

    def test_student_profile_resizes_without_losing_navigation_or_primary_action(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_many_observations(),
            competency_cockpit=build_student_competency_cockpit((
                self._cockpit_status(self.german_listening_competency_id, "Sehr langer Kompetenztext mit Umbruch"),
            )),
        )
        screen.show()

        for width, height in ((1400, 900), (1280, 800), (1180, 760)):
            screen.resize(width, height)
            app.processEvents()
            with self.subTest(width=width, height=height):
                self.assertFalse(screen.profile_primary_action.isHidden())
                self.assertEqual(
                    len(screen.profile_navigation.button_group.buttons()),
                    5,
                )
                self.assertTrue(
                    all(
                        button.width() > 0 and not button.isHidden()
                        for button in screen.profile_navigation.button_group.buttons()
                    )
                )
                current_scroll = screen.profile_tabs.currentWidget()
                self.assertEqual(
                    current_scroll.horizontalScrollBar().maximum(),
                    0,
                )
                self.assertEqual(screen._overview_compact, width < 1200)
        screen.close()
        self.assertIsNotNone(app)

    def test_competency_cockpit_does_not_recalculate_status_in_screen(self) -> None:
        screen_source = inspect.getsource(student_profile_screen.StudentProfileScreen)
        adapter_source = inspect.getsource(
            StudentDesktopAdapter.competency_cockpit_for_student
        )

        self.assertNotIn("calculated_rating_from_history", screen_source)
        self.assertNotIn("SQLite", screen_source)
        self.assertIn("list_competency_status_projection_for_student", adapter_source)
        self.assertNotIn("calculated_rating_from_history", adapter_source)

    def test_profile_dashboard_projection_is_not_calculated_in_screen(self) -> None:
        screen_source = inspect.getsource(student_profile_screen.StudentProfileScreen)
        adapter_source = inspect.getsource(
            StudentDesktopAdapter.student_profile_dashboard_for_student
        )

        self.assertNotIn("build_student_profile_dashboard", screen_source)
        self.assertNotIn("SQLite", screen_source)
        self.assertIn("list_competency_status_projection_for_student", adapter_source)
        self.assertIn("build_student_profile_dashboard", adapter_source)

    def test_sidebar_students_navigation_resets_to_list(self) -> None:
        target = resolve_navigation_target("students")

        self.assertEqual(target.screen_key, "students")
        self.assertTrue(target.reset_group_filter)

    def test_product_shell_navigation_matches_released_information_architecture(self) -> None:
        self.assertEqual(
            tuple((item.key, item.label, item.section) for item in NAVIGATION_ITEMS),
            (
                ("dashboard", "Heute", "ARBEIT"),
                ("students", "Schüler", "ARBEIT"),
                ("master_data", "Stammdaten", "VERWALTUNG"),
                ("settings", "Einstellungen", "VERWALTUNG"),
            ),
        )
        self.assertEqual(
            {item.icon_name for item in NAVIGATION_ITEMS},
            {"today", "students", "master-data", "settings"},
        )

    def test_shell_integrates_group_overview_into_student_workspace(self) -> None:
        app = QApplication.instance() or QApplication([])
        window = shell.AppShell(self.database_path)

        self.assertEqual(
            set(window.screen_index),
            {
                "dashboard",
                "onboarding",
                "students",
                "profile",
                "master_data",
                "settings",
            },
        )
        self.assertNotIn("overview", window.screen_index)
        self.assertNotIn("onboarding", {item.key for item in NAVIGATION_ITEMS})
        self.assertIs(window.overview_screen, window.students_workspace.groups_screen)
        window._show_navigation_item(
            next(
                window.navigation.item(index)
                for index in range(window.navigation.count())
                if window.navigation.item(index).data(Qt.ItemDataRole.UserRole)
                == "students"
            )
        )
        self.assertIs(window.stack.currentWidget(), window.students_workspace)
        self.assertEqual(window.students_workspace.current_content_key(), "groups")

        window.students_workspace.segmented_control.set_current_key("all", emit=True)
        self.assertEqual(window.students_workspace.current_content_key(), "all")
        self.assertFalse(window._has_active_student_filter())
        window.close()
        self.assertIsNotNone(app)

    def test_shell_initial_refresh_reads_synthetic_final_v4_runtime(self) -> None:
        app = QApplication.instance() or QApplication([])
        database_path = Path(self.temp_dir.name) / "synthetic-runtime.sqlite"
        create_synthetic_v4_database(database_path)

        window = shell.AppShell(
            database_path,
            now_provider=lambda: datetime(2026, 8, 3, 9, 0),
        )

        self.assertEqual(len(window.students_screen.students), 3)
        self.assertEqual(len(window.master_data_adapter.groups), 2)
        self.assertEqual(len(window.master_data_adapter.courses), 3)
        self.assertNotEqual(
            window.status_label.text(),
            shell.SCHOOL_YEAR_BLOCK_MESSAGE,
        )
        window.refresh_dashboard()
        self.assertNotEqual(
            window.status_label.text(),
            shell.SCHOOL_YEAR_BLOCK_MESSAGE,
        )
        window.close()
        self.assertIsNotNone(app)

    def test_shell_blocks_student_areas_when_current_school_year_is_missing(
        self,
    ) -> None:
        app = QApplication.instance() or QApplication([])
        database_path = Path(self.temp_dir.name) / "missing-current.sqlite"
        database = _create_empty_final_v4_database(database_path)
        with database.connect() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE school_years
                    SET status = 'closed',
                        closed_at = '2026-08-03T18:00:00+00:00'
                    WHERE status = 'current'
                    """
                )

        window = shell.AppShell(
            database_path,
            now_provider=lambda: datetime(2026, 8, 3, 9, 0),
        )

        self.assertEqual(window.students_screen.students, ())
        self.assertEqual(
            window.status_label.text(),
            shell.SCHOOL_YEAR_BLOCK_MESSAGE,
        )
        window.refresh_dashboard()
        self.assertEqual(
            window.status_label.text(),
            shell.SCHOOL_YEAR_BLOCK_MESSAGE,
        )
        window.close()
        self.assertIsNotNone(app)

    def test_shell_blocks_student_areas_when_current_assignment_is_ambiguous(
        self,
    ) -> None:
        app = QApplication.instance() or QApplication([])
        window = shell.AppShell(
            self.database_path,
            now_provider=lambda: datetime(2026, 8, 3, 9, 0),
        )
        with mock.patch.object(
            window.adapter,
            "list_students",
            side_effect=student_desktop_adapter.SchoolYearAssignmentRepositoryError(
                "assignment_ambiguous"
            ),
        ):
            window.refresh_students()

        self.assertEqual(window.students_screen.students, ())
        self.assertEqual(
            window.status_label.text(),
            shell.ASSIGNMENT_BLOCK_MESSAGE,
        )
        window.close()
        self.assertIsNotNone(app)

    def test_school_year_block_clears_stale_dashboard_actions(self) -> None:
        app = QApplication.instance() or QApplication([])
        database_path = Path(self.temp_dir.name) / "blocked-dashboard.sqlite"
        database = _create_empty_final_v4_database(database_path)
        window = shell.AppShell(
            database_path,
            now_provider=lambda: datetime(2026, 8, 3, 9, 0),
        )
        stale_action = QPushButton("Kinder anzeigen")
        window.dashboard_screen.hero_layout.addWidget(stale_action)
        window.dashboard_screen._hero_occurrence = object()
        window.dashboard_screen.header_observation_button.setVisible(True)
        with database.connect() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE school_years
                    SET status = 'closed',
                        closed_at = '2026-08-03T18:00:00+00:00'
                    WHERE status = 'current'
                    """
                )

        window.refresh_dashboard()
        app.processEvents()

        self.assertIsNone(window.dashboard_screen._hero_occurrence)
        self.assertFalse(
            window.dashboard_screen.header_observation_button.isVisible()
        )
        self.assertIsNone(stale_action.parent())
        self.assertEqual(
            window.status_label.text(),
            shell.SCHOOL_YEAR_BLOCK_MESSAGE,
        )
        window.close()
        self.assertIsNotNone(app)

    def test_student_workspace_keeps_filtered_navigation_origin(self) -> None:
        app = QApplication.instance() or QApplication([])
        workspace = students_workspace.StudentsWorkspace()

        workspace.show_student_list(source_key="course_groups")
        self.assertEqual(workspace.current_content_key(), "filtered_students")
        self.assertEqual(workspace.segmented_control.current_key(), "course_groups")
        self.assertEqual(workspace.show_source_selection(), "course_groups")
        self.assertEqual(workspace.current_content_key(), "course_groups")
        self.assertIsNotNone(app)

    def test_student_row_activation_opens_profile_once_for_each_input_path(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = students_screen.StudentsScreen()
        opened_student_ids: list[str] = []
        observation_student_ids: list[str] = []
        screen.student_selected.connect(opened_student_ids.append)
        screen.observation_requested.connect(observation_student_ids.append)
        screen.set_students(
            (
                StudentListItem(
                    "STU-000001",
                    "Anna",
                    "Muster",
                    "GRP-1",
                    "Gruppe",
                    "CRS-1",
                    "Kurs 1",
                    documentation_status=documentation_summary_from_subjects(()),
                ),
            )
        )

        screen.resize(1000, 560)
        screen.show()
        app.processEvents()
        row_position = screen.table.visualItemRect(screen.table.item(0, 0)).center()
        QTest.mouseClick(
            screen.table.viewport(),
            Qt.MouseButton.LeftButton,
            pos=row_position,
        )
        self.assertEqual(opened_student_ids, ["STU-000001"])

        opened_student_ids.clear()
        screen._last_pointer_activation = None
        QTest.mouseDClick(
            screen.table.viewport(),
            Qt.MouseButton.LeftButton,
            pos=row_position,
        )
        self.assertEqual(opened_student_ids, ["STU-000001"])

        opened_student_ids.clear()
        screen.table.setCurrentCell(0, 0)
        QTest.keyClick(screen.table, Qt.Key.Key_Return)
        self.assertEqual(opened_student_ids, ["STU-000001"])

        opened_student_ids.clear()
        action_widget = screen.table.cellWidget(0, 4)
        profile_button = next(
            button
            for button in action_widget.findChildren(QPushButton)
            if button.text() == "Profil öffnen"
        )
        profile_button.click()
        self.assertEqual(opened_student_ids, ["STU-000001"])

        opened_student_ids.clear()
        observe_button = next(
            button
            for button in action_widget.findChildren(QPushButton)
            if button.text() == "Beobachten"
        )
        observe_button.click()
        self.assertEqual(observation_student_ids, ["STU-000001"])
        self.assertEqual(opened_student_ids, [])
        self.assertIsNotNone(app)

    def test_student_workspace_exposes_courses_in_master_data_order(self) -> None:
        app = QApplication.instance() or QApplication([])
        workspace = students_workspace.StudentsWorkspace()
        selected_course_ids: list[str] = []
        workspace.course_selected.connect(selected_course_ids.append)
        view_model = MasterDataViewModel(
            groups=(),
            courses=(
                MasterDataItemViewModel("CRS-2", "Kurs 2", True, "Grün", "#16A34A"),
                MasterDataItemViewModel("CRS-1", "Kurs 1", True, "Blau", "#2563EB"),
            ),
        )

        workspace.set_master_data(view_model, ())
        workspace.show_section("courses")
        buttons = tuple(
            button
            for button in workspace.courses_screen.findChildren(QPushButton)
            if button.text() == "Schüler anzeigen"
        )

        self.assertEqual(
            students_workspace.STUDENT_WORKSPACE_SEGMENTS,
            (
                ("groups", "Stammgruppen"),
                ("courses", "Kurse"),
                ("course_groups", "Kursverbünde"),
                ("all", "Alle Schüler"),
            ),
        )
        self.assertEqual(workspace.current_content_key(), "courses")
        self.assertEqual(
            tuple(button.accessibleName() for button in buttons),
            (
                "Schüler im Kurs Kurs 2 anzeigen",
                "Schüler im Kurs Kurs 1 anzeigen",
            ),
        )
        buttons[0].click()
        self.assertEqual(selected_course_ids, ["CRS-2"])
        self.assertIsNotNone(app)

    def test_shell_switches_direct_course_filters_without_changing_course_groups(self) -> None:
        app = QApplication.instance() or QApplication([])
        window = shell.AppShell(self.database_path)
        courses = window.adapter.list_courses()
        groups = window.adapter.list_groups()
        course_group_snapshot = window.master_data_adapter.view_model().course_groups

        window.show_students_for_group(groups[0].group_id)
        self.assertTrue(window.students_screen.table.isColumnHidden(1))

        window.show_students_for_course(courses[0].course_id)
        self.assertFalse(window.students_screen.table.isColumnHidden(1))
        first_course_students = window.students_screen.students
        self.assertTrue(first_course_students)
        self.assertTrue(
            all(student.course_id == courses[0].course_id for student in first_course_students)
        )
        self.assertEqual(
            tuple(student.display_name.casefold() for student in first_course_students),
            tuple(sorted(student.display_name.casefold() for student in first_course_students)),
        )
        self.assertEqual(window.students_workspace.list_source_key(), "courses")

        window.show_students_for_course(courses[1].course_id)
        self.assertTrue(window.students_screen.students)
        self.assertTrue(
            all(
                student.course_id == courses[1].course_id
                for student in window.students_screen.students
            )
        )
        self.assertEqual(
            window.master_data_adapter.view_model().course_groups,
            course_group_snapshot,
        )

        window.show_all_students()
        self.assertFalse(window.students_screen.table.isColumnHidden(1))
        self.assertEqual(
            window.students_screen.students,
            window.adapter.list_students(),
        )
        window.close()
        self.assertIsNotNone(app)

    def test_student_list_fits_normal_notebook_width_without_horizontal_scroll(self) -> None:
        app = QApplication.instance() or QApplication([])
        window = shell.AppShell(self.database_path)
        window.show_all_students()
        window.resize(1180, 760)
        window.show()
        app.processEvents()

        self.assertEqual(
            window.students_screen.table.horizontalScrollBar().maximum(),
            0,
        )
        self.assertGreater(window.students_screen.table.viewport().width(), 800)
        window.close()
        self.assertIsNotNone(app)

    def test_interaction_foundations_expose_keyboard_focus_and_feedback(self) -> None:
        app = QApplication.instance() or QApplication([])
        segmented = components.SegmentedControl(
            (("groups", "Stammgruppen"), ("all", "Alle Schüler"))
        )
        selected: list[str] = []
        segmented.selection_changed.connect(selected.append)
        first_button = segmented.button_group.buttons()[0]
        QTest.keyClick(first_button, Qt.Key.Key_Right)
        self.assertEqual(segmented.current_key(), "all")
        self.assertEqual(selected, ["all"])
        self.assertEqual(first_button.focusPolicy(), Qt.FocusPolicy.StrongFocus)

        search = components.SearchField("Schüler suchen …")
        self.assertEqual(
            search.find_shortcut.key().matches(
                QKeySequence(QKeySequence.StandardKey.Find)
            ),
            QKeySequence.SequenceMatch.ExactMatch,
        )
        search.setText("Anna")
        QTest.keyClick(search, Qt.Key.Key_Escape)
        self.assertEqual(search.text(), "")
        self.assertTrue(search.accessibleName())

        button = QPushButton("Speichern")
        components.configure_button(button, "primary", "Änderungen speichern")
        self.assertEqual(button.property("buttonRole"), "primary")
        self.assertEqual(button.accessibleName(), "Änderungen speichern")

        toast = components.Toast()
        toast.show_message("Gespeichert.", tone="success", duration_ms=10_000)
        self.assertFalse(toast.isHidden())
        self.assertEqual(toast.property("toastTone"), "success")
        toast.clear()
        self.assertTrue(toast.isHidden())

        inline = components.InlineMessage()
        inline.set_message("Eingabe prüfen.", tone="warning")
        self.assertFalse(inline.isHidden())
        self.assertEqual(inline.property("messageTone"), "warning")
        empty = components.EmptyState("Noch keine Einträge.")
        self.assertFalse(empty.isHidden())
        self.assertIn("Noch keine Einträge", empty.accessibleName())

        badge = components.StatusBadge("Entwurf", tone="info")
        badge.setText("Entwurf geändert")
        self.assertEqual(badge.accessibleName(), "Entwurf geändert")

        course_badge = components.CourseBadge("Kurs 1", "#2563EB")
        self.assertEqual(course_badge.label.text(), "Kurs 1")
        self.assertEqual(course_badge.accessibleName(), "Kurszugehörigkeit: Kurs 1")
        self.assertEqual(course_badge.property("semanticRole"), "courseContext")
        self.assertFalse(course_badge.property("usesNeutralColor"))
        self.assertNotEqual(course_badge.objectName(), badge.objectName())
        neutral_course_badge = components.CourseBadge("Kurs ohne Farbe", "")
        self.assertEqual(neutral_course_badge.label.text(), "Kurs ohne Farbe")
        self.assertEqual(
            neutral_course_badge.property("courseColorHex"),
            components.CourseBadge.NEUTRAL_COLOR,
        )
        self.assertTrue(neutral_course_badge.property("usesNeutralColor"))

        card = components.AppCard("interactive", interactive=True)
        self.assertEqual(card.property("cardVariant"), "interactive")
        self.assertEqual(card.focusPolicy(), Qt.FocusPolicy.StrongFocus)
        card.set_selected(True)
        self.assertTrue(card.property("selected"))
        card.set_pressed(True)
        self.assertTrue(card.property("pressed"))
        card.setEnabled(False)
        self.assertFalse(card.isEnabled())

        filter_bar = components.FilterBar(search)
        reset_requests: list[bool] = []
        filter_bar.reset_requested.connect(lambda: reset_requests.append(True))
        filter_bar.set_context_filter("Kurs: Kurs 1", True)
        self.assertFalse(filter_bar.context_chip.isHidden())
        self.assertIn("Kurs: Kurs 1", filter_bar.context_chip.accessibleName())
        filter_bar.context_chip.click()
        self.assertEqual(reset_requests, [True])
        filter_bar.set_context_filter("Alle Schüler", False)
        self.assertTrue(filter_bar.context_chip.isHidden())

        icon_button = components.IconButton("info", "Dokumentationshilfe")
        self.assertEqual(icon_button.accessibleName(), "Dokumentationshilfe")
        self.assertTrue(icon_button.toolTip())
        icon_activations: list[bool] = []
        icon_button.clicked.connect(lambda: icon_activations.append(True))
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            QTest.keyClick(icon_button, key)
        self.assertEqual(icon_activations, [True, True, True])
        self.assertEqual(filter_bar.accessibleName(), "Suche und aktive Filter")
        self.assertIsNotNone(app)

    def test_product_tables_replace_empty_grids_with_explanatory_states(self) -> None:
        app = QApplication.instance() or QApplication([])
        students = students_screen.StudentsScreen()
        students.set_students(())
        self.assertTrue(students.table.isHidden())
        self.assertIn("Schüler anlegen", students.empty_state.accessibleName())

        master_data = master_data_screen.MasterDataScreen()
        master_data.set_master_data(MasterDataViewModel((), (), ()))
        self.assertTrue(master_data.group_table.isHidden())
        self.assertTrue(master_data.course_table.isHidden())
        self.assertTrue(master_data.course_group_table.isHidden())
        self.assertIn("+ Stammgruppe", master_data.group_empty_state.accessibleName())
        self.assertTrue(master_data.group_table.accessibleDescription())

        renamed: list[str] = []
        master_data.group_rename_requested.connect(renamed.append)
        master_data.set_master_data(MasterDataViewModel(
            (
                MasterDataItemViewModel(
                    "GRP-000001",
                    "Grashüpfer",
                    True,
                ),
            ),
            (),
            (),
        ))
        master_data.show()
        app.processEvents()
        master_data.group_table.setCurrentCell(0, 0)
        QTest.keyClick(master_data.group_table, Qt.Key.Key_Return)
        self.assertEqual(renamed, ["GRP-000001"])
        self.assertIsNotNone(app)

    def test_master_data_lists_are_compact_accessible_and_responsive(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = master_data_screen.MasterDataScreen()
        screen.set_master_data(
            MasterDataViewModel(
                (
                    MasterDataItemViewModel(
                        "GRP-000001",
                        "Grashüpfer",
                        True,
                    ),
                ),
                (
                    MasterDataItemViewModel(
                        "CRS-000001",
                        "Kurs 1",
                        True,
                        "Blau",
                        "#2563EB",
                        1,
                    ),
                ),
                (
                    CourseGroupViewModel(
                        "CGR-000001",
                        "Mathe/Deutsch Kursverbund A",
                        ("GRP-000001",),
                        ("CRS-000001",),
                    ),
                ),
            )
        )

        self.assertEqual(
            tuple(
                screen.group_table.horizontalHeaderItem(index).text()
                for index in range(screen.group_table.columnCount())
            ),
            ("Stammgruppe", "Status", ""),
        )
        self.assertEqual(
            tuple(
                screen.course_table.horizontalHeaderItem(index).text()
                for index in range(screen.course_table.columnCount())
            ),
            ("Kurs", "Kursstufe", "Kursfarbe", "Status", ""),
        )
        self.assertEqual(
            tuple(
                screen.course_group_table.horizontalHeaderItem(index).text()
                for index in range(screen.course_group_table.columnCount())
            ),
            ("Kursverbund", "Zuordnung", ""),
        )
        self.assertEqual(screen.group_table.rowHeight(0), 46)
        self.assertEqual(screen.course_group_table.rowHeight(0), 62)
        self.assertIn(
            "Status: Vorhanden",
            screen.group_table.cellWidget(0, 1).accessibleName(),
        )

        self.assertEqual(screen.course_table.item(0, 1).text(), "Stufe 1")
        color_cell = screen.course_table.cellWidget(0, 2)
        color_badge = color_cell.findChild(components.CourseBadge)
        self.assertIsNotNone(color_badge)
        self.assertEqual(color_badge.label.text(), "Blau")
        self.assertEqual(color_badge.property("courseColorHex"), "#2563EB")
        self.assertIn("Orientierung", color_cell.accessibleName())

        relation_cell = screen.course_group_table.cellWidget(0, 1)
        self.assertIn("Stammgruppen: Grashüpfer", relation_cell.accessibleName())
        self.assertIn("Kurse: Kurs 1", relation_cell.accessibleName())
        edit_buttons = tuple(
            button
            for button in screen.findChildren(QPushButton)
            if button.text() == "Bearbeiten"
        )
        self.assertEqual(len(edit_buttons), 3)
        self.assertTrue(all(button.minimumWidth() >= 96 for button in edit_buttons))
        self.assertTrue(all(button.accessibleName() for button in edit_buttons))

        screen.show()
        for width, height in ((900, 700), (1120, 840)):
            screen.resize(width, height)
            app.processEvents()
            for table in (
                screen.group_table,
                screen.course_table,
                screen.course_group_table,
            ):
                self.assertEqual(table.horizontalScrollBar().maximum(), 0)
        screen.close()
        self.assertIsNotNone(app)

    def test_component_library_v2_styles_semantic_states_centrally(self) -> None:
        stylesheet = theme.APP_STYLESHEET
        card_surface = stylesheet.split(
            'QFrame#AppCard, QFrame[cardVariant="default"]',
            1,
        )[1].split("}", 1)[0]
        table_surface = stylesheet.split(
            "QTableWidget, QListWidget, QTreeWidget",
            1,
        )[1].split("}", 1)[0]

        self.assertIn('QFrame#AppCard[cardVariant="interactive"]:hover', stylesheet)
        self.assertIn('QFrame#AppCard[selected="true"]', stylesheet)
        self.assertIn('QFrame#AppCard[cardVariant="interactive"][pressed="true"]', stylesheet)
        self.assertIn("QPushButton#FilterChip:focus", stylesheet)
        self.assertIn("QPushButton:disabled", stylesheet)
        self.assertIn("QTableWidget#PremiumTable", stylesheet)
        self.assertIn("QLineEdit#SearchField:focus", stylesheet)
        self.assertIn(f"background-color: {theme.COLOR_SURFACE};", card_surface)
        self.assertNotIn(theme.COLOR_GLASS, card_surface)
        self.assertIn(f"background-color: {theme.COLOR_SURFACE};", table_surface)
        self.assertNotIn(theme.COLOR_GLASS, table_surface)
        self.assertIn(
            "QFrame#FilterBar {\n    background-color: rgba(255, 255, 255, 232);",
            stylesheet,
        )
        self.assertIn(
            'QFrame#CompetencyCockpitLearningAreaCard[interactive="true"]:hover',
            stylesheet,
        )
        self.assertIn(
            'QFrame#CompetencyCockpitCompetencyRow[interactive="true"]:focus',
            stylesheet,
        )
        self.assertIn(
            'QFrame#StudentProfileOrientationChange[interactive="true"]:hover',
            stylesheet,
        )
        for rating in ("--", "-", "+", "++"):
            self.assertIn(
                f'QLabel#StatusBadge[ratingToken="{rating}"]',
                stylesheet,
            )
            self.assertIn(
                f'QPushButton#RatingBadgeButton[ratingToken="{rating}"]',
                stylesheet,
            )
        self.assertIn("QPushButton#RatingBadgeButton:checked", stylesheet)
        self.assertIn("QPushButton#RatingBadgeButton:focus", stylesheet)
        self.assertIn("QPushButton#RatingBadgeButton:checked:pressed", stylesheet)
        self.assertIn("QPushButton#RatingBadgeButton:disabled", stylesheet)

    def test_shell_svg_icons_and_native_font_tokens_are_registered(self) -> None:
        theme_source = inspect.getsource(theme)

        self.assertEqual(icons.ICON_SIZE_SMALL, 16)
        self.assertEqual(icons.ICON_SIZE_MEDIUM, 20)
        self.assertEqual(icons.ICON_SIZE_LARGE, 24)
        for icon_name in icons.ICON_NAMES:
            self.assertTrue(icons.icon_path(icon_name).exists())
            self.assertEqual(icons.icon_path(icon_name).suffix, ".svg")
        self.assertNotIn("font-family:", theme.APP_STYLESHEET)
        self.assertNotIn("Arial", theme_source)
        self.assertEqual(
            (
                theme.SPACING_4,
                theme.SPACING_8,
                theme.SPACING_12,
                theme.SPACING_16,
                theme.SPACING_24,
                theme.SPACING_32,
                theme.SPACING_48,
            ),
            (4, 8, 12, 16, 24, 32, 48),
        )
        self.assertLess(theme.MOTION_FAST_MS, theme.MOTION_STANDARD_MS)
        self.assertLess(theme.MOTION_STANDARD_MS, theme.MOTION_SLOW_MS)

    def test_placeholder_navigation_is_not_part_of_product_shell(self) -> None:
        navigation_keys = {item.key for item in NAVIGATION_ITEMS}

        self.assertTrue(
            {"overview", "observations", "competencies", "reports"}.isdisjoint(
                navigation_keys
            )
        )
        with self.assertRaises(ValueError):
            resolve_navigation_target("reports")

    def test_student_search_finds_first_name(self) -> None:
        students = self.adapter.list_students()
        result = filter_student_list(students, students[0].first_name)

        self.assertIn(students[0].student_id, {student.student_id for student in result})

    def test_student_search_finds_last_name(self) -> None:
        students = self.adapter.list_students()
        result = filter_student_list(students, students[0].last_name)

        self.assertIn(students[0].student_id, {student.student_id for student in result})

    def test_student_search_is_case_insensitive_and_trims_query(self) -> None:
        students = self.adapter.list_students()
        query = f"  {students[0].display_name.upper()}  "
        result = filter_student_list(students, query)

        self.assertIn(students[0].student_id, {student.student_id for student in result})

    def test_empty_student_search_returns_current_group_filter(self) -> None:
        students = self.adapter.list_students(group_id=f"{GROUP_ID_PREFIX}-000001")
        result = filter_student_list(students, "   ")

        self.assertEqual(result, students)

    def test_student_search_combines_with_group_filter(self) -> None:
        students = self.adapter.list_students(group_id=f"{GROUP_ID_PREFIX}-000001")
        result = filter_student_list(students, students[0].course_name)

        self.assertGreater(len(result), 0)
        self.assertTrue(all(student.group_id == f"{GROUP_ID_PREFIX}-000001" for student in result))

    def test_adapter_has_no_direct_sql_write_logic(self) -> None:
        source = inspect.getsource(student_desktop_adapter)

        self.assertNotIn("INSERT INTO", source)
        self.assertNotIn("UPDATE ", source)
        self.assertNotIn("DELETE FROM", source)
        self.assertNotIn("sqlite3.connect", source)

    def test_widgets_have_no_direct_sql_write_logic(self) -> None:
        module_names = (
            "src.desktop_app.adapters.curriculum_desktop_adapter",
            "src.desktop_app.shell",
            "src.desktop_app.dialogs.new_observation_dialog",
            "src.desktop_app.dialogs.new_student_dialog",
            "src.desktop_app.screens.overview_screen",
            "src.desktop_app.screens.settings_screen",
            "src.desktop_app.screens.students_screen",
            "src.desktop_app.screens.students_workspace",
            "src.desktop_app.screens.student_profile_screen",
            "src.desktop_app.screens.placeholder_screen",
        )

        for module_name in module_names:
            module = importlib.import_module(module_name)
            source = inspect.getsource(module)
            with self.subTest(module_name=module_name):
                self.assertNotIn("INSERT INTO", source)
                self.assertNotIn("UPDATE ", source)
                self.assertNotIn("DELETE FROM", source)
                self.assertNotIn("sqlite3.connect", source)

    def test_desktop_app_modules_are_importable(self) -> None:
        for module_name in (
            "src.desktop_app.adapters.curriculum_desktop_adapter",
            "src.desktop_app.adapters.student_desktop_adapter",
            "src.desktop_app.app",
            "src.desktop_app.assets",
            "src.desktop_app.components",
            "src.desktop_app.icons",
            "src.desktop_app.dialogs.new_observation_dialog",
            "src.desktop_app.dialogs.new_student_dialog",
            "src.desktop_app.main",
            "src.desktop_app.new_student_dialog",
            "src.desktop_app.navigation",
            "src.desktop_app.screens.overview_screen",
            "src.desktop_app.screens.placeholder_screen",
            "src.desktop_app.screens.settings_screen",
            "src.desktop_app.screens.student_profile_screen",
            "src.desktop_app.screens.students_screen",
            "src.desktop_app.screens.students_workspace",
            "src.desktop_app.shell",
            "src.desktop_app.student_list_view",
            "src.desktop_app.theme",
            "src.desktop_app.view_models.observation_view_model",
            "src.desktop_app.view_models.settings_view_model",
            "src.desktop_app.view_models.student_view_model",
        ):
            with self.subTest(module_name=module_name):
                importlib.import_module(module_name)

    def _canonical_status(self, competency_id: str) -> StudentCompetencyStatusViewModel:
        return next(
            status
            for status in self.adapter.list_competency_status_projection_for_student(
                f"{STUDENT_ID_PREFIX}-000001"
            )
            if status.competency_id == competency_id
        )

    def _cockpit_status(
        self,
        competency_id: str,
        label: str,
        *,
        documentation_state: str = "undocumented",
        learning_area: str = "Größen & Messen",
        topic: str = "Zeit",
        observation_count: int = 0,
        last_observation_date: str = "",
        confirmed_rating: str = "",
        confirmed_at: str = "",
        confirmation_note: str = "",
        observed_proposal: str = "",
        evidence: tuple[StudentCompetencyEvidenceViewModel, ...] = (),
        newer_observations: bool = False,
        historical: bool = False,
        subject_id: str = "mathematik",
        subject_name: str = "Mathematik",
        sort_order: int = 0,
        learning_stage: str = "cross_stage",
    ) -> StudentCompetencyStatusViewModel:
        return StudentCompetencyStatusViewModel(
            competency_id=competency_id,
            competency_label=label,
            subject_id=subject_id,
            subject_display_name=subject_name,
            rating=observed_proposal,
            rating_label=observed_proposal,
            last_observation_date=last_observation_date,
            sort_order=sort_order,
            observation_count=observation_count,
            confirmed_rating=confirmed_rating,
            confirmed_at=confirmed_at,
            confirmation_note=confirmation_note,
            learning_area=learning_area,
            competency_group=topic,
            competency_text=label,
            documentation_state=documentation_state,
            observed_proposal=observed_proposal,
            evidence=evidence,
            learning_stage=learning_stage,
            catalog_status="legacy" if historical else "current",
            is_active=not historical,
            historical=historical,
            has_observations_newer_than_confirmation=newer_observations,
        )

    def _sample_student_detail(self) -> StudentDetailViewModel:
        return StudentDetailViewModel(
            f"{STUDENT_ID_PREFIX}-000001",
            "Emma Müller",
            "Grashüpfer",
            "Kurs 1",
            "",
            True,
        )

    def _sample_report_preview(self) -> StudentReportPreviewViewModel:
        return StudentReportPreviewViewModel(
            f"{STUDENT_ID_PREFIX}-000001",
            "Emma Müller",
            (
                StudentReportSubjectSectionViewModel(
                    "deutsch",
                    "Deutsch",
                    (
                        StudentReportCompetencyViewModel(
                            self.german_listening_competency_id,
                            "Mit Texten und Medien umgehen",
                            "+",
                            "von Laura bestätigt",
                            "Kenntnisse meist anwenden",
                        ),
                    ),
                    (
                        StudentReportCompetencyViewModel(
                            self.german_listening_competency_id,
                            "Mit Texten und Medien umgehen",
                            "+",
                            "von Laura bestätigt",
                            "Kenntnisse meist anwenden",
                        ),
                    ),
                    (
                        StudentReportDevelopmentViewModel(
                            self.german_word_competency_id,
                            "Wörter und Sätze",
                            "Einzelbeobachtung vorhanden, noch kein Verlauf ableitbar.",
                            ("-",),
                        ),
                    ),
                    (),
                    (
                        StudentReportEvidenceViewModel(
                            "OBS-000001",
                            "2026-07-03",
                            "Leseübung",
                            "Liest einen bekannten Text.",
                            ("+ Mit Texten und Medien umgehen",),
                        ),
                    ),
                ),
            ),
        )

    def _sample_filter_observations(self) -> tuple[ObservationListItem, ...]:
        return (
            ObservationListItem(
                "OBS-000003",
                f"{STUDENT_ID_PREFIX}-000001",
                "2026-07-05",
                OBSERVATION_CROSS_SUBJECT_LABEL,
                "Gruppenarbeit",
                "Verbindet Deutsch und EPU.",
                (
                    ObservationRatingViewModel(
                        self.german_listening_competency_id,
                        "Deutsch",
                        "Mit Texten und Medien umgehen",
                        "Lesen und Verstehen",
                        "Texte lesen und zentrale Informationen entnehmen",
                        "+",
                    ),
                    ObservationRatingViewModel(
                        self.epu_competency_id,
                        "EPU",
                        "Natur und Umwelt",
                        "Erkunden und beschreiben",
                        "Naturphänomene beobachten und beschreiben",
                        "-",
                    ),
                ),
            ),
            ObservationListItem(
                "OBS-000002",
                f"{STUDENT_ID_PREFIX}-000001",
                "2026-07-04",
                "EPU",
                "Präsentation",
                "Beschreibt Naturphänomene.",
                (
                    ObservationRatingViewModel(
                        self.epu_competency_id,
                        "EPU",
                        "Natur und Umwelt",
                        "Erkunden und beschreiben",
                        "Naturphänomene beobachten und beschreiben",
                        "++",
                    ),
                ),
            ),
            ObservationListItem(
                "OBS-000001",
                f"{STUDENT_ID_PREFIX}-000001",
                "2026-07-03",
                "Deutsch",
                "Leseübung",
                "Liest einen bekannten Text.",
                (
                    ObservationRatingViewModel(
                        self.german_listening_competency_id,
                        "Deutsch",
                        "Mit Texten und Medien umgehen",
                        "Lesen und Verstehen",
                        "Texte lesen und zentrale Informationen entnehmen",
                        "--",
                    ),
                ),
            ),
        )

    def _sample_many_observations(self) -> tuple[ObservationListItem, ...]:
        return (
            ObservationListItem(
                "OBS-000004",
                f"{STUDENT_ID_PREFIX}-000001",
                "2026-07-06",
                "Mathematik",
                "Projektarbeit",
                "Neueste Beobachtung.",
                (
                    ObservationRatingViewModel(
                        self.math_addition_competency_id,
                        "Mathematik",
                        "Zahlen und Operationen",
                        "Rechnen",
                        "Rechenwege darstellen und vergleichen",
                        "+",
                    ),
                ),
            ),
            *self._sample_filter_observations(),
        )

    def _sample_observation_draft(
        self,
        *,
        observation_id: str = "",
        date_text: str = "2026-07-03",
        context: str = "Leseübung",
        note: str = "Liest einen bekannten Text.",
        subject_id: str = "deutsch",
        subject_display_name: str = "Deutsch",
        competency_ratings: tuple[ObservationCompetencyRatingDraft, ...] | None = None,
        attachments: tuple[ObservationAttachmentDraft, ...] = (),
        is_quick_observation: bool = False,
    ) -> ObservationDraftViewModel:
        return ObservationDraftViewModel(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            student_name="Emma Müller",
            date_text=date_text,
            subject_id=subject_id,
            subject_display_name=subject_display_name,
            context=context,
            note=note,
            competency_ratings=competency_ratings if competency_ratings is not None else (
                self._sample_observation_rating(
                    self.german_listening_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
                self._sample_observation_rating(
                    self.german_word_competency_id,
                    "deutsch",
                    "Deutsch",
                    "Sprache untersuchen",
                    "Wörter und Sätze",
                    "Wörter nach Merkmalen ordnen",
                    "--",
                ),
            ),
            attachment_names=tuple(attachment.original_filename for attachment in attachments),
            attachments=attachments,
            observation_id=observation_id,
            is_quick_observation=is_quick_observation,
        )

    def _sample_observation_rating(
        self,
        competency_id: str,
        subject_key: str,
        subject_display_name: str,
        learning_area: str,
        competency_group: str,
        competency_text: str,
        rating: str,
    ) -> ObservationCompetencyRatingDraft:
        return ObservationCompetencyRatingDraft(
            competency_id=competency_id,
            subject_key=subject_key,
            subject_display_name=subject_display_name,
            learning_area=learning_area,
            competency_group=competency_group,
            competency_text=competency_text,
            rating=rating,
        )

    def _recent_rating(self, competency_id: str) -> ObservationCompetencyRatingDraft:
        competency = self._find_observation_competency_option(
            self.adapter.list_observation_competency_subject_groups(
                f"{STUDENT_ID_PREFIX}-000001"
            ),
            competency_id,
        )
        self.assertIsNotNone(competency)
        if competency is None:
            raise AssertionError("Expected current competency missing from catalog")
        return self._sample_observation_rating(
            competency.competency_id,
            competency.subject_key,
            competency.subject_display_name,
            competency.learning_area,
            competency.competency_group,
            competency.competency_text,
            "+",
        )

    def _observation_dialog_with_hierarchy(
        self,
        initial_draft: ObservationDraftViewModel | None = None,
    ) -> new_observation_dialog.NewObservationDialog:
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)
        return new_observation_dialog.NewObservationDialog(
            self._sample_student_detail(),
            self.curriculum_adapter,
            self.adapter,
            initial_draft=initial_draft,
            subject_options=self.adapter.list_observation_subject_options(
                self._sample_student_detail().student_id,
                initial_draft
            ),
            competency_subject_groups=(
                self.adapter.list_observation_competency_subject_groups(
                    self._sample_student_detail().student_id,
                    initial_draft
                )
            ),
            recent_competencies=self.adapter.list_recent_observation_competencies(
                self._sample_student_detail().student_id,
                initial_draft,
            ),
        )

    def _save_custom_documentation_subjects(
        self,
        student_id: str,
        subject_ids: tuple[str, ...],
    ) -> None:
        school_year = self.adapter.current_school_year()
        self.assertIsNotNone(school_year)
        if school_year is None:
            raise AssertionError("Expected current school year")
        self.adapter.save_student_documentation_subjects(
            student_id,
            school_year.school_year_id,
            "custom",
            subject_ids,
        )

    def _select_observation_subject(
        self,
        dialog: new_observation_dialog.NewObservationDialog,
        subject_key: str,
    ) -> None:
        subject_index = dialog.subject_select.findData(subject_key)
        self.assertGreaterEqual(subject_index, 0)
        dialog.subject_select.setCurrentIndex(subject_index)
        dialog._refresh_competencies()

    def _observation_topic_button(
        self,
        dialog: new_observation_dialog.NewObservationDialog,
        topic_name: str,
    ) -> QPushButton:
        topic_key = self._observation_topic_key(dialog, topic_name)
        return dialog.competency_topic_buttons[topic_key]

    def _observation_topic_container(
        self,
        dialog: new_observation_dialog.NewObservationDialog,
        topic_name: str,
    ) -> QWidget:
        topic_key = self._observation_topic_key(dialog, topic_name)
        return dialog.competency_topic_containers[topic_key]

    def _observation_area_button(
        self,
        dialog: new_observation_dialog.NewObservationDialog,
        area_name: str,
    ) -> QPushButton:
        matching_buttons = [
            button
            for area_key, button in dialog.competency_area_buttons.items()
            if area_key.endswith(f"|{area_name}")
        ]
        self.assertEqual(len(matching_buttons), 1)
        return matching_buttons[0]

    def _observation_topic_key(
        self,
        dialog: new_observation_dialog.NewObservationDialog,
        topic_name: str,
    ) -> str:
        suffix = f"|{topic_name}"
        matching_keys = [
            topic_key
            for topic_key in dialog.competency_topic_buttons
            if topic_key.endswith(suffix)
        ]
        self.assertEqual(len(matching_keys), 1)
        return matching_keys[0]

    def _observation_subject_group(
        self,
        groups: tuple[ObservationCompetencySubjectGroupViewModel, ...],
        subject_key: str,
    ) -> ObservationCompetencySubjectGroupViewModel | None:
        return next(
            (group for group in groups if group.subject_key == subject_key),
            None,
        )

    def _find_observation_competency_option(
        self,
        groups: tuple[ObservationCompetencySubjectGroupViewModel, ...],
        competency_id: str,
    ) -> ObservationCompetencyOptionViewModel | None:
        for subject_group in groups:
            for learning_area_group in subject_group.learning_area_groups:
                for competency_group in learning_area_group.competency_groups:
                    for competency in competency_group.competencies:
                        if competency.competency_id == competency_id:
                            return competency
        return None


if __name__ == "__main__":
    unittest.main()
