"""Tests for the experimental PySide6 desktop adapter."""

from __future__ import annotations

import inspect
import importlib
import os
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QLabel,
    QPushButton,
    QTabWidget,
    QWidget,
)

from src.application.commands import (
    CreateObservationCommand,
    CreateStudentCommand,
    UpdateObservationCommand,
)
from src.application.dispatcher import SuccessResult
from src.core.constants import COURSE_ID_PREFIX, GROUP_ID_PREFIX, STUDENT_ID_PREFIX
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
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
from src.desktop_app.navigation import NAVIGATION_ITEMS, resolve_navigation_target
from src.desktop_app.screens import master_data_screen
from src.desktop_app.screens import overview_screen
from src.desktop_app.screens import settings_screen
from src.desktop_app.screens import student_profile_screen
from src.desktop_app.screens import students_screen
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
    ObservationCompetencyOptionViewModel,
    ObservationCompetencyRatingDraft,
    ObservationCompetencySubjectGroupViewModel,
    ObservationDraftViewModel,
    ObservationListItem,
    ObservationRatingViewModel,
    ObservationSubjectOptionViewModel,
    StudentDocumentationSubjectStatus,
    StudentCompetencyStatusViewModel,
    StudentCompetencySubjectGroup,
    StudentMissingCompetencyViewModel,
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
    StudentDocumentViewModel,
    StudentReportDevelopmentViewModel,
    StudentListItem,
    StudentReportCompetencyViewModel,
    StudentReportEvidenceViewModel,
    StudentReportPreviewViewModel,
    StudentReportSubjectSectionViewModel,
    build_student_profile_overview,
    documentation_summary_from_subjects,
    filter_student_list,
    format_student_report_preview_text,
    sort_student_list,
)


class DesktopAppAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "kompetenzmanager.sqlite"
        self.database = create_sqlite_seed_database(self.database_path)
        self.adapter = StudentDesktopAdapter(self.database_path)
        self.master_data_adapter = MasterDataDesktopAdapter(self.adapter)
        self.curriculum_adapter = CurriculumDesktopAdapter()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_adapter_creates_create_student_command(self) -> None:
        command = self.adapter.create_student_command(
            first_name="Jule",
            last_name="Schneider",
            group_id=f"{GROUP_ID_PREFIX}-000001",
            course_id=f"{COURSE_ID_PREFIX}-000001",
            student_notes="Liest gern.",
        )

        self.assertIsInstance(command, CreateStudentCommand)
        self.assertEqual(command.command_name, "student.create")
        self.assertEqual(command.first_name, "Jule")
        self.assertEqual(command.last_name, "Schneider")
        self.assertEqual(command.group_id, f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(command.course_id, f"{COURSE_ID_PREFIX}-000001")
        self.assertEqual(command.student_notes, "Liest gern.")

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
        self.assertEqual(student.student_id, f"{STUDENT_ID_PREFIX}-000029")

        stored_student = SQLiteStudentRepository(self.database).get_student_by_id(student.student_id)
        self.assertIsNotNone(stored_student)
        self.assertEqual(stored_student.first_name, "Jule")
        self.assertEqual(len(SQLiteStudentRepository(self.database).list_students()), 29)

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
        self.assertEqual(command.competency_ratings[0].competency_id, "CMP-000001")
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
                    "CMP-000003",
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
            ("CMP-000003",),
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
                    "CMP-000001",
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
                self._sample_observation_rating(
                    "CMP-000003",
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
            ("Deutsch", "EPU"),
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
                    "CMP-000001",
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
                self._sample_observation_rating(
                    "CMP-000003",
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
            ("Deutsch", "EPU"),
        )
        self.assertEqual(
            tuple(rating.rating for rating in observations[0].competency_ratings),
            ("+", "-"),
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
        self.assertEqual(competencies[0].competency_id, "CMP-000001")
        self.assertEqual(competencies[0].subject_id, "deutsch")
        self.assertEqual(competencies[0].subject_name, "Deutsch")
        self.assertTrue(competencies[0].label)

    def test_documentation_subject_options_default_to_active_catalog_subjects(self) -> None:
        options = self.adapter.list_documentation_subject_options()

        self.assertGreater(len(options), 0)
        self.assertEqual(
            tuple(option.subject_id for option in options[:4]),
            ("deutsch", "mathematik", "epu", "musik"),
        )
        self.assertIn("Sozialkompetenz", tuple(option.label for option in options))
        self.assertTrue(all(option.selected for option in options))

    def test_save_active_documentation_subjects_updates_selected_options_only(
        self,
    ) -> None:
        competency_repository = SQLiteCompetencyRepository(self.database)
        active_by_competency = {
            competency.competency_id: competency.active
            for competency in competency_repository.list_competencies()
        }

        self.adapter.save_active_documentation_subjects(("deutsch", "epu"))
        options = self.adapter.list_documentation_subject_options()
        selected_subject_ids = tuple(
            option.subject_id for option in options if option.selected
        )
        active_after_save = {
            competency.competency_id: competency.active
            for competency in competency_repository.list_competencies()
        }

        self.assertEqual(selected_subject_ids, ("deutsch", "epu"))
        self.assertEqual(active_after_save, active_by_competency)

    def test_documentation_subject_selection_survives_adapter_reinitialization(
        self,
    ) -> None:
        self.adapter.save_active_documentation_subjects(("sozialkompetenz",))

        reloaded_adapter = StudentDesktopAdapter(self.database_path)
        options = reloaded_adapter.list_documentation_subject_options()

        self.assertEqual(
            tuple(option.subject_id for option in options if option.selected),
            ("sozialkompetenz",),
        )

    def test_observation_subject_options_use_documentation_subject_selection(
        self,
    ) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))

        options = self.adapter.list_observation_subject_options()

        self.assertEqual(
            tuple(option.subject_key for option in options),
            ("deutsch", "mathematik"),
        )
        self.assertNotIn("epu", {option.subject_key for option in options})

    def test_observation_subject_options_default_to_active_catalog_subjects(
        self,
    ) -> None:
        options = self.adapter.list_observation_subject_options()
        expected_subject_ids = tuple(
            option.subject_id
            for option in self.adapter.list_documentation_subject_options()
        )

        self.assertEqual(
            tuple(option.subject_key for option in options),
            expected_subject_ids,
        )
        self.assertIn("sozialkompetenz", {option.subject_key for option in options})

    def test_observation_subject_options_keep_initial_non_documentation_subject(
        self,
    ) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))
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

        options = self.adapter.list_observation_subject_options(initial_draft)

        self.assertEqual(options[-1].subject_key, "musik")
        self.assertEqual(
            options[-1].display_name,
            "Musik (nicht dokumentationsrelevant)",
        )

    def test_observation_competency_hierarchy_defaults_to_active_catalog_subjects(
        self,
    ) -> None:
        groups = self.adapter.list_observation_competency_subject_groups()
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
            self._find_observation_competency_option(groups, "CMP-000020")
        )

    def test_observation_competency_hierarchy_uses_documentation_subjects(
        self,
    ) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))

        groups = self.adapter.list_observation_competency_subject_groups()

        self.assertEqual(
            tuple(group.subject_key for group in groups),
            ("deutsch", "mathematik"),
        )
        self.assertNotIn("epu", {group.subject_key for group in groups})

    def test_observation_competency_hierarchy_contains_concrete_math_time_competency(
        self,
    ) -> None:
        groups = self.adapter.list_observation_competency_subject_groups()
        competency = self._find_observation_competency_option(groups, "CMP-000318")
        subject_group = self._observation_subject_group(groups, "mathematik")

        self.assertIsNotNone(subject_group)
        self.assertIsNotNone(competency)
        self.assertEqual(subject_group.subject_display_name, "Mathematik")
        if competency is not None:
            self.assertEqual(competency.subject_key, "mathematik")
            self.assertEqual(
                competency.learning_area,
                "Groessen - Groessenvorstellungen nutzen und mit Groessen umgehen",
            )
            self.assertEqual(competency.competency_group, "Zeit")
            self.assertEqual(
                competency.competency_text,
                "Uhrzeiten ablesen, einstellen, notieren und auf verschiedene Weise benennen.",
            )
            self.assertEqual(competency.competency_label, "Uhrzeiten nutzen")

    def test_observation_competency_hierarchy_keeps_current_deutsch_competency(
        self,
    ) -> None:
        groups = self.adapter.list_observation_competency_subject_groups()
        competency = self._find_observation_competency_option(groups, "CMP-000241")

        self.assertIsNotNone(competency)
        if competency is not None:
            self.assertEqual(competency.subject_key, "deutsch")
            self.assertEqual(competency.subject_display_name, "Deutsch")
            self.assertEqual(
                competency.competency_text,
                "Wörter, Sätze sowie literarische und nicht literarische "
                "altersgemäße Texte sinnverstehend lesen",
            )

    def test_observation_competency_hierarchy_marks_initial_draft_rating(
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
                    "Groessen - Groessenvorstellungen nutzen und mit Groessen umgehen",
                    "Zeit",
                    "Uhrzeiten ablesen, einstellen, notieren und auf verschiedene Weise benennen.",
                    "++",
                ),
            ),
        )

        groups = self.adapter.list_observation_competency_subject_groups(
            initial_draft
        )
        selected = self._find_observation_competency_option(groups, "CMP-000318")
        unselected = self._find_observation_competency_option(groups, "CMP-000319")

        self.assertIsNotNone(selected)
        if selected is not None:
            self.assertTrue(selected.selected)
            self.assertEqual(selected.rating, "++")
        self.assertIsNotNone(unselected)
        if unselected is not None:
            self.assertFalse(unselected.selected)
            self.assertEqual(unselected.rating, "")

    def test_observation_competency_hierarchy_keeps_initial_non_documentation_subject(
        self,
    ) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))
        legacy_competency = next(
            competency
            for competency in CurriculumDesktopAdapter(
                database=self.database
            ).list_entries()
            if competency.competency_id == "CMP-000020"
        )
        self.assertEqual(legacy_competency.catalog_status, "legacy")
        self.assertFalse(legacy_competency.is_active)
        initial_draft = self._sample_observation_draft(
            subject_id="musik",
            subject_display_name="Musik",
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000020",
                    "musik",
                    "Musik",
                    "Musik hören",
                    "Hören und Beschreiben",
                    "Musik aufmerksam hören, Eindrücke beschreiben und "
                    "musikalische Merkmale erkennen",
                    "+",
                ),
            ),
        )

        groups = self.adapter.list_observation_competency_subject_groups(
            initial_draft
        )
        music_group = self._observation_subject_group(groups, "musik")
        selected = self._find_observation_competency_option(groups, "CMP-000020")

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

    def test_student_adapter_upserts_catalog_without_removing_local_competencies(self) -> None:
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
                    ("SQLite-Lesekompetenz", "CMP-000241"),
                )
        self.adapter.save_observation(self._sample_observation_draft(
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000241",
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
                    "CMP-000001",
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
                    "CMP-000001",
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
                self._sample_observation_rating(
                    "CMP-000012",
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
        self.assertEqual(deutsch_status.rating_label, "+ erreicht")
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

    def test_deleted_observation_is_excluded_from_calculated_competency_status(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-01",
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000001",
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
                    "CMP-000001",
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
                    "CMP-000001",
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
        self.assertEqual(confirmation.competency_id, "CMP-000001")
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
                    "CMP-000001",
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
            competency_id="CMP-000001",
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
                    "CMP-000001",
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
            competency_id="CMP-000001",
            confirmed_rating="+",
        )
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-04",
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000001",
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
            competency_id="CMP-000241",
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
            if competency.competency_id == "CMP-000241"
        )

        self.assertEqual(status.rating, "+")
        self.assertEqual(status.confirmed_rating, "+")
        self.assertEqual(status.rating_history, ())
        self.assertEqual(status.observation_count, 0)
        self.assertEqual(status.confirmation_note, "im Lerngespraech bestaetigt")
        self.assertEqual(status.confirmation_status_label, "von Laura bestätigt: +")
        self.assertNotIn(
            "CMP-000241",
            {competency.competency_id for competency in deutsch_group.missing_competencies},
        )

    def test_report_preview_uses_confirmation_without_active_observation(self) -> None:
        self.adapter.save_competency_confirmation(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            competency_id="CMP-000241",
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
            "Sinnverstehend lesen · "
            "Aktueller Stand: + erreicht · von Laura bestätigt",
        )
        self.assertEqual(deutsch_section.development, ())
        self.assertEqual(deutsch_section.example_observations, ())

    def test_confirmed_status_stays_visible_after_observation_soft_delete(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000241",
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
            competency_id="CMP-000241",
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
            if competency.competency_id == "CMP-000241"
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
            "Sinnverstehend lesen · "
            "Aktueller Stand: + erreicht · von Laura bestätigt",
        )
        self.assertEqual(deutsch_section.development, ())
        self.assertEqual(deutsch_section.example_observations, ())

    def test_report_preview_uses_confirmed_competency_status_when_available(self) -> None:
        self.adapter.save_observation(self._sample_observation_draft(
            date_text="2026-07-03",
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000001",
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
            competency_id="CMP-000001",
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
            "Mit Texten und Medien umgehen · "
            "Aktueller Stand: + erreicht · von Laura bestätigt",
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
                    "CMP-000001",
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
            competency_id="CMP-000001",
            confirmed_rating="+",
        )

        preview = self.adapter.get_report_preview_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        deutsch_section = preview.subject_sections[0]

        self.assertEqual(
            deutsch_section.current_statuses[0].display_label,
            "Mit Texten und Medien umgehen · "
            "Aktueller Stand: + erreicht · von Laura bestätigt",
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
                    "CMP-000001",
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
            "Mit Texten und Medien umgehen · "
            "Aktueller Stand: + erreicht · aus Beobachtungen abgeleitet",
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
                    "CMP-000001",
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
            "Mit Texten und Medien umgehen · "
            "Aktueller Stand: - in Entwicklung · aus Beobachtungen abgeleitet",
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
                        "CMP-000001",
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
                        "CMP-000001",
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
                        "CMP-000001",
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
                    "CMP-000001",
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
                    "CMP-000001",
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
                    "CMP-000001",
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
                    "CMP-000001",
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
            "Aktueller Stand: + erreicht · von Laura bestätigt",
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
                    "CMP-000001",
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

    def test_documentation_status_starts_with_zero_documented_learning_areas(self) -> None:
        statuses = self.adapter.list_documentation_status_for_student(
            f"{STUDENT_ID_PREFIX}-000001"
        )
        expected_subject_ids = tuple(
            dict.fromkeys(
                competency.subject_id
                for competency in SQLiteCompetencyRepository(
                    self.database
                ).list_competencies()
                if competency.active
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
                competency.learning_area
                for competency in SQLiteCompetencyRepository(
                    self.database
                ).list_competencies()
                if competency.active and competency.subject_id == subject_id
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
                    "CMP-000241",
                    "deutsch",
                    "Deutsch",
                    "Leseverstehen",
                    "Sinnverstehendes Lesen",
                    "Wörter, Sätze sowie literarische und nicht literarische "
                    "altersgemäße Texte sinnverstehend lesen",
                    "+",
                ),
                self._sample_observation_rating(
                    "CMP-000278",
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
                    "CMP-000001",
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
            competency_id="CMP-000241",
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
            "CMP-000241",
            {competency.competency_id for competency in deutsch_status.missing_competencies},
        )

    def test_missing_competencies_ignore_non_documentation_subjects(self) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))
        self.adapter.save_observation(self._sample_observation_draft(
            subject_id="epu",
            subject_display_name="EPU",
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000012",
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
                    "CMP-000012",
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
            competency_id="CMP-000012",
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

        self.assertEqual(result.value.student_id, f"{STUDENT_ID_PREFIX}-000001")
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
        course = self.master_data_adapter.add_course("Kurs 4", "#9333EA")
        reloaded_adapter = MasterDataDesktopAdapter(StudentDesktopAdapter(self.database_path))
        view_model = reloaded_adapter.view_model()

        self.assertIsInstance(group, MasterDataItemViewModel)
        self.assertEqual(group.name, "Eulen")
        self.assertTrue(group.is_persistent)
        self.assertEqual(group.status_label, "Vorhanden")
        self.assertEqual(course.name, "Kurs 4")
        self.assertEqual(course.color_name, "Lila")
        self.assertEqual(course.color_hex, "#9333EA")
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
        course = self.master_data_adapter.add_course("Kurs Gelb", "#EAB308")
        reloaded_adapter = MasterDataDesktopAdapter(StudentDesktopAdapter(self.database_path))
        reloaded_course = reloaded_adapter.courses[course.item_id]

        self.assertEqual(reloaded_course.color_name, "Gelb")
        self.assertEqual(reloaded_course.color_hex, "#EAB308")

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
        self.assertIn("DIALOG_PRIMARY_BUTTON_STYLE", button_source)
        self.assertIn("PRIMARY_BUTTON_STYLESHEET", button_source)
        self.assertIn("background-color: #2563EB", theme.PRIMARY_BUTTON_STYLESHEET)
        self.assertIn("color: #FFFFFF", theme.PRIMARY_BUTTON_STYLESHEET)
        self.assertIn("save_button.setStyleSheet(DIALOG_PRIMARY_BUTTON_STYLE)", button_source)
        self.assertIn("save_button.setDefault(True)", button_source)
        self.assertIn('cancel_button.setShortcut("Esc")', button_source)

    def test_pyside_app_uses_icon_based_visual_theme(self) -> None:
        theme_source = inspect.getsource(theme)
        main_source = inspect.getsource(main)
        shell_source = inspect.getsource(shell)
        screen_source = inspect.getsource(students_screen)

        self.assertIn('COLOR_NAVY = "#0B3A63"', theme_source)
        self.assertIn('COLOR_BLUE = "#2563EB"', theme_source)
        self.assertIn('COLOR_TURQUOISE = "#0EA5A7"', theme_source)
        self.assertIn('COLOR_GREEN = "#16A34A"', theme_source)
        self.assertIn('COLOR_ORANGE = "#F97316"', theme_source)
        self.assertIn("APP_STYLESHEET", theme_source)
        self.assertIn("QWidget#AppSidebar", theme.APP_STYLESHEET)
        self.assertIn("QListWidget#AppNavigation", theme.APP_STYLESHEET)
        self.assertIn("QFrame#AppCard", theme.APP_STYLESHEET)
        self.assertIn("rgba(255, 255, 255, 246)", theme.APP_STYLESHEET)
        self.assertIn("COLOR_GLASS", theme_source)
        self.assertIn("def apply_app_theme(", theme_source)
        self.assertIn("def create_card(", theme_source)
        self.assertIn("def set_label_style(", theme_source)
        self.assertIn("apply_app_theme(app)", main_source)
        self.assertIn('root.setObjectName("AppRoot")', shell_source)
        self.assertIn('sidebar_container.setObjectName("AppSidebar")', shell_source)
        self.assertIn('self.navigation.setObjectName("AppNavigation")', shell_source)
        self.assertIn('set_label_style(title, "screen_title")', screen_source)

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

        self.assertIn('APP_INFO_APP_NAME = "Jenaplan Kompetenzmanager"', source)
        self.assertIn('APP_INFO_MODE = "PySide6 Prototyp"', source)
        self.assertIn(
            'APP_INFO_STORAGE_HINT = "Einige Funktionen sind noch nicht dauerhaft gespeichert."',
            source,
        )
        self.assertIn("AppInfoDialog", shell_source)
        self.assertIn('self.info_button = QPushButton("Info")', shell_source)
        self.assertIn("create_app_icon_label(112)", source)
        self.assertIn("open_app_info_dialog", shell_source)

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

        self.assertIn('("Farbe", "Name", "Status", "Aktion")', source)
        self.assertIn('QTableWidgetItem(f"● {item.color_name}")', source)
        self.assertIn("setForeground(QColor(item.color_hex))", source)
        self.assertIn("COURSE_COLOR_OPTIONS", dialog_source)
        self.assertIn('form.addRow("Farbe", self.color_select)', dialog_source)
        self.assertIn("include_color=True", shell_source)
        self.assertIn("dialog.color_hex()", shell_source)

    def test_student_list_items_include_course_color(self) -> None:
        students = self.adapter.list_students()

        self.assertEqual(students[0].group_name, "Grashüpfer")
        self.assertIn(students[0].course_name, {"Kurs 1", "Kurs 2", "Kurs 3"})
        self.assertIn(students[0].course_color_name, {"Blau", "Grün", "Orange"})
        self.assertIn(
            students[0].course_color_hex,
            {"#2563EB", "#16A34A", "#F97316"},
        )

    def test_students_screen_shows_course_color_marker(self) -> None:
        source = inspect.getsource(importlib.import_module(
            "src.desktop_app.screens.students_screen"
        ))

        self.assertIn('"Name", "Kurs", "Dokumentation", "Aktion"', source)
        self.assertIn(
            "self.table.setCellWidget(row_index, 1, self._course_cell(student))",
            source,
        )
        self.assertIn('marker = QLabel("●")', source)
        self.assertIn("student.course_color_hex or '#6B7280'", source)
        self.assertIn('set_label_style(course_label, "body")', source)
        self.assertIn("QHeaderView.ResizeMode.ResizeToContents", source)
        self.assertNotIn('"Stammgruppe", "Kurs"', source)
        self.assertNotIn("self.table.setItem(row_index, 1", source)

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
        self.assertIn('QLabel("●")', source)
        self.assertIn("course.color_hex or '#6B7280'", source)
        self.assertIn("self.master_data_adapter.view_model()", shell_source)
        self.assertIn("self.adapter.list_group_summaries()", shell_source)

    def test_master_data_screen_shows_course_groups(self) -> None:
        source = inspect.getsource(master_data_screen)
        dialog_source = inspect.getsource(master_data_dialog)
        shell_source = inspect.getsource(shell.AppShell.open_edit_course_group_dialog)

        self.assertIn('MASTER_DATA_COURSE_GROUP_EMPTY_STATE = "Noch keine Kursverbünde vorhanden."', source)
        self.assertIn('"Kursverbünde"', source)
        self.assertIn('"+ Kursverbund"', source)
        self.assertIn("course_group_add_requested = Signal()", source)
        self.assertIn("course_group_edit_requested = Signal(str)", source)
        self.assertIn("self.course_group_table = QTableWidget(0, 4)", source)
        self.assertIn(
            'table.setHorizontalHeaderLabels(("Name", "Stammgruppen", "Kurse", "Aktion"))',
            source,
        )
        self.assertIn("item.selected_group_ids", source)
        self.assertIn("item.selected_course_ids", source)
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
                        group_id,
                        course_id,
                        student_notes,
                        active,
                        created_at,
                        updated_at,
                        archived_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"{STUDENT_ID_PREFIX}-999999",
                        "Test",
                        "Fuchs",
                        f"{GROUP_ID_PREFIX}-000002",
                        f"{COURSE_ID_PREFIX}-000001",
                        "",
                        1,
                        "2026-07-02",
                        "2026-07-02",
                        None,
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
        self.assertIn("Lege über „+ Schüler“ den ersten Schüler an.", source)
        self.assertIn('STUDENT_SEARCH_EMPTY_STATE = "Keine Schüler gefunden."', source)
        self.assertIn('clear_search_button = QPushButton("Zurücksetzen")', source)
        self.assertIn("self.search_input.text().strip()", source)

    def test_master_data_empty_states_are_registered(self) -> None:
        source = inspect.getsource(master_data_screen)

        self.assertIn(
            'MASTER_DATA_GROUP_EMPTY_STATE = "Noch keine Stammgruppen vorhanden."',
            source,
        )
        self.assertIn(
            'MASTER_DATA_COURSE_EMPTY_STATE = "Noch keine Kurse vorhanden."',
            source,
        )
        self.assertIn("self.group_empty_state_label.setVisible(not items)", source)
        self.assertIn("self.course_empty_state_label.setVisible(not items)", source)

    def test_new_student_dialog_uses_master_data_for_group_and_course_options(self) -> None:
        source = inspect.getsource(new_student_dialog)
        shell_source = inspect.getsource(shell.AppShell.open_new_student_dialog)

        self.assertIn("MasterDataDesktopAdapter", source)
        self.assertIn("self.master_data_adapter.view_model()", source)
        self.assertIn("self.group_items = {group.item_id: group", source)
        self.assertIn("self.course_items = {course.item_id: course", source)
        self.assertIn("self._populate_master_data_select(", source)
        self.assertIn("select.addItem(item.name, item.item_id)", source)
        self.assertIn("NewStudentDialog(self.adapter, self.master_data_adapter)", shell_source)

    def test_new_student_dialog_uses_required_dropdown_placeholders(self) -> None:
        source = inspect.getsource(new_student_dialog)

        self.assertIn('STUDENT_DIALOG_SELECT_PLACEHOLDER = "Bitte auswählen"', source)
        self.assertIn('"Keine Stammgruppen vorhanden"', source)
        self.assertIn('"Keine Kurse vorhanden"', source)
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
                "++ sicher erreicht",
                "+ erreicht",
                "- in Entwicklung",
                "-- Unterstützungsbedarf",
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

    def test_curriculum_catalog_loads_active_subjects(self) -> None:
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

    def test_curriculum_catalog_uses_epu_instead_of_sachunterricht(self) -> None:
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

    def test_curriculum_catalog_entries_have_stable_id_subject_and_label(self) -> None:
        entries = self.curriculum_adapter.list_entries()
        competency_ids = [entry.competency_id for entry in entries]

        self.assertEqual(len(competency_ids), len(set(competency_ids)))
        self.assertTrue(all(entry.competency_id.startswith("CMP-") for entry in entries))
        self.assertTrue(all(entry.subject_id for entry in entries))
        self.assertTrue(all(entry.subject_display_name for entry in entries))
        self.assertTrue(all(entry.competency_label for entry in entries))
        self.assertTrue(all(entry.competency_detail_label for entry in entries))
        self.assertEqual(entries[0].competency_id, "CMP-000001")
        self.assertEqual(entries[0].subject_id, "deutsch")
        self.assertEqual(entries[-1].competency_id, "CMP-000646")
        self.assertEqual(entries[-1].subject_id, "ethik")

    def test_curriculum_catalog_maps_kunst_to_kunsterziehung(self) -> None:
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

    def test_curriculum_catalog_contains_extended_subjects(self) -> None:
        subjects = {
            subject.display_name
            for subject in self.curriculum_adapter.list_active_subjects()
            if not subject.is_core_subject
        }

        self.assertEqual(subjects, {"Ethik", "Religion", "Werken", "Schulgarten"})

    def test_curriculum_catalog_keeps_social_competence_as_own_subject(self) -> None:
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

    def test_curriculum_catalog_filters_competencies_by_subject(self) -> None:
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
            == "Uhrzeiten ablesen, einstellen, notieren und auf verschiedene Weise benennen."
            for entry in math_competencies
        ))

    def test_curriculum_catalog_exposes_subject_area_topic_and_competency_structure(
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
            == "Groessen - Groessenvorstellungen nutzen und mit Groessen umgehen"
            and entry.competency_group == "Zeit"
            and entry.competency_text
            == "Uhrzeiten ablesen, einstellen, notieren und auf verschiedene Weise benennen."
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

    def test_curriculum_catalog_uses_specific_labels_for_concrete_competencies(
        self,
    ) -> None:
        math_written_entries = [
            entry
            for entry in self.curriculum_adapter.list_competencies_for_subject(
                "mathematik"
            )
            if entry.learning_area == "Arithmetik - mit Zahlen und Symbolen umgehen"
            and entry.competency_group == "Schriftliches Rechnen"
        ]

        self.assertGreaterEqual(len(math_written_entries), 3)
        self.assertEqual(
            {
                entry.competency_label
                for entry in math_written_entries
            },
            {"Schriftlich erklaeren", "Schriftlich rechnen", "Schriftlich pruefen"},
        )
        self.assertGreater(
            len({entry.competency_label for entry in math_written_entries}),
            1,
        )

    def test_curriculum_catalog_groups_competencies_by_subject(self) -> None:
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

    def test_curriculum_competency_options_have_short_display_labels(self) -> None:
        math_competency = next(
            entry
            for entry in self.curriculum_adapter.list_competencies_for_subject(
                "mathematik"
            )
            if entry.competency_id == "CMP-000318"
        )

        self.assertEqual(math_competency.competency_display_name, "Uhrzeiten nutzen")
        self.assertEqual(math_competency.competency_label, "Uhrzeiten nutzen")
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

        self.assertIn("CurriculumDesktopAdapter", source)
        self.assertIn("competency_subject_groups", source)
        self.assertIn("ObservationCompetencySubjectGroupViewModel", source)
        self.assertIn("list_active_subjects", source)
        self.assertIn("list_competencies_for_subject", source)
        self.assertIn("currentIndexChanged.connect(self._refresh_competencies)", source)
        self.assertNotIn("OBSERVATION_SUBJECT_OPTIONS", source)
        self.assertNotIn("OBSERVATION_COMPETENCY_OPTIONS", source)
        self.assertNotIn("Sachunterricht", view_model_source)

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

        self.assertEqual(subject_labels, ("Deutsch", "Mathematik"))
        self.assertNotIn("EPU", subject_labels)
        self.assertIsNotNone(app)

    def test_observation_dialog_keeps_initial_non_documentation_subject(self) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))
        initial_draft = self._sample_observation_draft(
            subject_id="musik",
            subject_display_name="Musik",
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000020",
                    "musik",
                    "Musik",
                    "Musik hören",
                    "Hören und Beschreiben",
                    "Musik aufmerksam hören, Eindrücke beschreiben und "
                    "musikalische Merkmale erkennen",
                    "+",
                ),
            ),
        )
        dialog = self._observation_dialog_with_hierarchy(initial_draft)

        draft = dialog.create_draft()

        self.assertEqual(dialog.subject_select.currentData(), "musik")
        self.assertEqual(
            dialog.subject_select.currentText(),
            "Musik (nicht dokumentationsrelevant)",
        )
        self.assertEqual(draft.subject_id, "musik")
        self.assertEqual(draft.competency_ratings[0].subject_key, "musik")
        self.assertEqual(draft.competency_ratings[0].subject_display_name, "Musik")
        self.assertTrue(dialog.competency_checkboxes["CMP-000020"].isChecked())

    def test_observation_dialog_topics_start_collapsed(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        area_button = next(
            button
            for area_key, button in dialog.competency_area_buttons.items()
            if area_key.endswith(
                "|Groessen - Groessenvorstellungen nutzen und mit Groessen umgehen"
            )
        )
        topic_button = self._observation_topic_button(dialog, "Zeit")
        topic_container = self._observation_topic_container(dialog, "Zeit")

        self.assertEqual(
            area_button.text(),
            "▸ Kompetenzbereich: Groessen - Groessenvorstellungen nutzen und "
            "mit Groessen umgehen",
        )
        self.assertEqual(topic_button.text(), "▸ Thema: Zeit")
        self.assertTrue(topic_container.isHidden())

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
            "Uhrzeiten ablesen, einstellen, notieren und auf verschiedene Weise benennen.",
            [
                checkbox.text()
                for checkbox in topic_container.findChildren(QCheckBox)
            ],
        )

        topic_button.click()
        self.assertTrue(topic_container.isHidden())
        self.assertEqual(topic_button.text(), "▸ Thema: Zeit")

    def test_observation_dialog_checkbox_creates_rating_row_and_draft(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        self._observation_topic_button(dialog, "Zeit").click()
        dialog.competency_checkboxes["CMP-000318"].setChecked(True)
        rating_select = dialog.competency_rating_widgets["CMP-000318"]
        rating_select.setCurrentIndex(rating_select.findData("++"))
        draft = dialog.create_draft()
        rating = next(
            item for item in draft.competency_ratings
            if item.competency_id == "CMP-000318"
        )

        self.assertIn("CMP-000318", dialog.competency_rating_entries)
        self.assertEqual(rating.rating, "++")
        self.assertEqual(
            rating.competency_text,
            "Uhrzeiten ablesen, einstellen, notieren und auf verschiedene Weise benennen.",
        )

    def test_observation_dialog_selection_survives_topic_collapse(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        topic_button = self._observation_topic_button(dialog, "Zeit")
        topic_button.click()
        dialog.competency_checkboxes["CMP-000318"].setChecked(True)
        rating_select = dialog.competency_rating_widgets["CMP-000318"]
        rating_select.setCurrentIndex(rating_select.findData("+"))
        topic_button.click()
        draft = dialog.create_draft()

        self.assertTrue(self._observation_topic_container(dialog, "Zeit").isHidden())
        self.assertIn("CMP-000318", dialog.competency_rating_entries)
        self.assertIn("CMP-000318", dialog.competency_rating_widgets)
        self.assertEqual(draft.competency_ratings[0].competency_id, "CMP-000318")
        self.assertEqual(draft.competency_ratings[0].rating, "+")

    def test_observation_dialog_keeps_separate_ratings_per_competency(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        self._observation_topic_button(dialog, "Schriftliches Rechnen").click()
        dialog.competency_checkboxes["CMP-000306"].setChecked(True)
        dialog.competency_checkboxes["CMP-000307"].setChecked(True)
        first_rating = dialog.competency_rating_widgets["CMP-000306"]
        second_rating = dialog.competency_rating_widgets["CMP-000307"]
        first_rating.setCurrentIndex(first_rating.findData("++"))
        second_rating.setCurrentIndex(second_rating.findData("-"))
        draft = dialog.create_draft()
        ratings_by_id = {
            rating.competency_id: rating.rating
            for rating in draft.competency_ratings
        }

        self.assertEqual(ratings_by_id["CMP-000306"], "++")
        self.assertEqual(ratings_by_id["CMP-000307"], "-")

    def test_observation_dialog_edit_keeps_initial_selected_rating(self) -> None:
        initial_draft = self._sample_observation_draft(
            subject_id="mathematik",
            subject_display_name="Mathematik",
            competency_ratings=(
                self._sample_observation_rating(
                    "CMP-000318",
                    "mathematik",
                    "Mathematik",
                    "Groessen - Groessenvorstellungen nutzen und mit Groessen umgehen",
                    "Zeit",
                    "Uhrzeiten ablesen, einstellen, notieren und auf verschiedene Weise benennen.",
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
        self.assertTrue(dialog.competency_checkboxes["CMP-000318"].isChecked())
        self.assertEqual(
            dialog.competency_rating_widgets["CMP-000318"].currentData(),
            "++",
        )

    def test_observation_dialog_only_clicked_topic_opens(self) -> None:
        dialog = self._observation_dialog_with_hierarchy()

        self._select_observation_subject(dialog, "mathematik")
        zeit_container = self._observation_topic_container(dialog, "Zeit")
        geld_container = self._observation_topic_container(dialog, "Geld")

        self._observation_topic_button(dialog, "Zeit").click()

        self.assertFalse(zeit_container.isHidden())
        self.assertTrue(geld_container.isHidden())

    def test_observation_dialog_honors_documentation_subject_hierarchy(self) -> None:
        self.adapter.save_active_documentation_subjects(("deutsch", "mathematik"))
        dialog = self._observation_dialog_with_hierarchy()
        subject_labels = tuple(
            dialog.subject_select.itemText(index)
            for index in range(dialog.subject_select.count())
        )
        visible_subject_keys: set[str] = set()
        for index in range(dialog.subject_select.count()):
            dialog.subject_select.setCurrentIndex(index)
            visible_subject_keys.update(
                str(checkbox.property("subject_key"))
                for checkbox in dialog.findChildren(QCheckBox)
            )

        self.assertEqual(subject_labels, ("Deutsch", "Mathematik"))
        self.assertEqual(visible_subject_keys, {"deutsch", "mathematik"})

    def test_observation_dialog_uses_rating_dropdown_per_competency(self) -> None:
        source = inspect.getsource(new_observation_dialog)

        self.assertNotIn("self.rating_select", source)
        self.assertNotIn('form_layout.addLayout(self._field_row("Bewertung"', source)
        self.assertIn("Ausgewählte Kompetenzen bewerten", source)
        self.assertIn("Jede ausgewählte Kompetenz erhält eine eigene Bewertung.", source)
        self.assertIn("rating_select.addItem(\"Bewertung auswählen\", \"\")", source)
        self.assertIn("for rating_option in OBSERVATION_RATING_OPTIONS", source)
        self.assertIn('rating_option.split(" ", 1)[0]', source)

    def test_observation_dialog_keeps_buttons_outside_scroll_area(self) -> None:
        source = inspect.getsource(new_observation_dialog)

        self.assertIn("QScrollArea", source)
        self.assertIn("scroll_area.setWidgetResizable(True)", source)
        self.assertIn("layout.addWidget(scroll_area, 1)", source)
        self.assertIn("layout.addWidget(buttons)", source)

    def test_observation_dialog_uses_compact_competency_layout(self) -> None:
        source = inspect.getsource(new_observation_dialog)

        self.assertIn("self.competency_tree_layout.setSpacing(6)", source)
        self.assertIn("Kompetenzbereich:", source)
        self.assertIn("Thema:", source)
        self.assertIn("self.competency_ratings_layout.setSpacing(4)", source)
        self.assertIn("rating_select.setMinimumWidth(190)", source)
        self.assertIn("row.addWidget(label, 1)", source)

    def test_observation_dialog_keeps_cross_subject_competency_ratings(self) -> None:
        source = inspect.getsource(new_observation_dialog)
        refresh_source = inspect.getsource(
            new_observation_dialog.NewObservationDialog._refresh_competencies
        )
        sync_source = inspect.getsource(
            new_observation_dialog.NewObservationDialog._sync_competency_ratings
        )

        self.assertIn("_remove_competency_rating_row", source)
        self.assertIn("_remove_competency_rating", source)
        self.assertIn('QPushButton("Entfernen")', source)
        self.assertIn("self.competency_rating_entries.pop", source)
        self.assertIn("self.competency_rating_widgets.pop", source)
        self.assertIn("self.competency_checkboxes.clear()", source)
        self.assertNotIn("_clear_competency_ratings", refresh_source)
        self.assertIn("competency_key in self.competency_rating_entries", source)
        self.assertIn("checkbox.setChecked", source)
        self.assertIn(
            "if competency_key not in self.competency_rating_widgets",
            sync_source,
        )
        self.assertIn(
            "elif competency_key in self.competency_rating_widgets",
            sync_source,
        )

    def test_observation_context_options_match_prototype_scope(self) -> None:
        self.assertEqual(
            OBSERVATION_CONTEXT_OPTIONS,
            (
                "Lernzielkontrolle",
                "Präsentation",
                "Einzelgespräch",
                "Gruppenarbeit",
                "Leseübung",
            ),
        )

    def test_observation_draft_view_model_keeps_student_context(self) -> None:
        competency = ObservationCompetencyRatingDraft(
            competency_id="CMP-000001",
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
        self.assertEqual(draft.competency_ratings[0].competency_id, "CMP-000001")
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
            competency_id="CMP-000001",
            subject_key="epu",
            subject_display_name="EPU",
            learning_area="Natur und Umwelt",
            competency_group="Erkunden und beschreiben",
            competency_text="Naturphänomene beobachten und beschreiben",
            rating="++",
        )
        second = ObservationCompetencyRatingDraft(
            competency_id="CMP-000002",
            subject_key="deutsch",
            subject_display_name="Deutsch",
            learning_area="Miteinander sprechen",
            competency_group="Gesprächsbeiträge",
            competency_text="Eigene Beiträge verständlich einbringen",
            rating="-",
        )
        third = ObservationCompetencyRatingDraft(
            competency_id="CMP-000003",
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
            "Noch keine Anhänge ausgewählt.",
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

        self.assertIn("NewObservationDialog(", source)
        self.assertIn(
            "subject_options=self.adapter.list_observation_subject_options()",
            source,
        )
        self.assertIn(
            "self.adapter.list_observation_competency_subject_groups()",
            source,
        )
        self.assertIn("self.show_student_profile(student.student_id)", source)
        self.assertIn('self.status_label.setText("Beobachtung wurde gespeichert.")', source)
        self.assertIn("list_competency_overview_for_student(student_id)", profile_source)
        self.assertIn("get_report_preview_for_student(student_id)", profile_source)
        self.assertIn("list_documentation_status_for_student(student_id)", profile_source)
        self.assertIn("report_preview", profile_source)

    def test_shell_opens_quick_observation_from_student_list(self) -> None:
        shell_source = inspect.getsource(shell.AppShell)
        quick_source = inspect.getsource(shell.AppShell.open_quick_observation_dialog)

        self.assertIn("self.students_screen.observation_requested.connect", shell_source)
        self.assertIn("self.open_quick_observation_dialog", shell_source)
        self.assertIn("self.adapter.get_student_profile(student_id)", quick_source)
        self.assertIn("NewObservationDialog(", quick_source)
        self.assertIn(
            "subject_options=self.adapter.list_observation_subject_options()",
            quick_source,
        )
        self.assertIn(
            "self.adapter.list_observation_competency_subject_groups()",
            quick_source,
        )
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
        self.assertIn('self._show_screen("overview")', return_source)
        self.assertIn('self._select_navigation("overview")', return_source)
        self.assertIn("show_back_button=self._has_active_student_filter()", refresh_source)

    def test_shell_opens_observation_for_edit_and_refreshes_profile(self) -> None:
        source = inspect.getsource(shell.AppShell.open_edit_observation_dialog)

        self.assertIn("observation_draft_for_edit(observation_id)", source)
        self.assertIn("initial_draft=draft", source)
        self.assertIn(
            "subject_options=self.adapter.list_observation_subject_options(draft)",
            source,
        )
        self.assertIn(
            "self.adapter.list_observation_competency_subject_groups(draft)",
            source,
        )
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
        self.assertIn("QMessageBox.question", remove_source)
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
                            "CMP-000001",
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
                            "CMP-000001",
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
            text.startswith("+  Mit Texten und Medien umgehen")
            for text in label_texts
        ))
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
        screen.set_student(
            self._sample_student_detail(),
            self._sample_filter_observations(),
            (
                StudentCompetencySubjectGroup(
                    "deutsch",
                    "Deutsch",
                    (
                        StudentCompetencyStatusViewModel(
                            "CMP-000001",
                            "Mit Texten und Medien umgehen",
                            "deutsch",
                            "Deutsch",
                            "+",
                            "+ erreicht",
                            "2026-07-03",
                            0,
                            ("-", "+"),
                            2,
                            1.6,
                        ),
                    ),
                ),
            ),
        )

        screen.observation_search_input.setText("nicht vorhanden")
        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Keine passenden Beobachtungen.", label_texts)
        self.assertIn("Mit Texten und Medien umgehen", label_texts)
        self.assertIn(
            "Vorschlag aus Beobachtungen: + · noch nicht bestätigt",
            label_texts,
        )
        self.assertIn("Verlauf: - → +", label_texts)
        self.assertIn("2 Beobachtungen · zuletzt beobachtet: 2026-07-03", label_texts)
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
                            "CMP-000001",
                            "Deutsch",
                            "Mit Texten und Medien umgehen",
                            "Lesen und Verstehen",
                            "Texte lesen und zentrale Informationen entnehmen",
                            "+",
                        ),
                        ObservationRatingViewModel(
                            "CMP-000003",
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
        screen.set_student(
            self._sample_student_detail(),
            (),
            (
                StudentCompetencySubjectGroup(
                    "deutsch",
                    "Deutsch",
                    (
                        StudentCompetencyStatusViewModel(
                            "CMP-000001",
                            "Mit Texten und Medien umgehen",
                            "deutsch",
                            "Deutsch",
                            "+",
                            "+ erreicht",
                            "2026-07-03",
                            0,
                            ("+",),
                            1,
                            2.0,
                        ),
                    ),
                ),
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Kompetenzübersicht", label_texts)
        self.assertIn("Deutsch", label_texts)
        self.assertIn("Mit Texten und Medien umgehen", label_texts)
        self.assertIn(
            "Vorschlag aus Beobachtungen: + · noch nicht bestätigt",
            label_texts,
        )
        self.assertIn("Verlauf: +", label_texts)
        self.assertIn("1 Beobachtung · zuletzt beobachtet: 2026-07-03", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_renders_confirmed_competency_status(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (),
            (
                StudentCompetencySubjectGroup(
                    "deutsch",
                    "Deutsch",
                    (
                        StudentCompetencyStatusViewModel(
                            "CMP-000001",
                            "Mit Texten und Medien umgehen",
                            "deutsch",
                            "Deutsch",
                            "-",
                            "- in Entwicklung",
                            "2026-07-04",
                            0,
                            ("-",),
                            1,
                            1.0,
                            "+",
                            "2026-07-03T12:00:00+00:00",
                            "pädagogisch bestätigt",
                        ),
                    ),
                ),
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn(
            "aus Beobachtungen abgeleitet: - · von Laura bestätigt: +",
            label_texts,
        )
        self.assertIn(
            "von Laura bestätigt am 2026-07-03 · "
            "neuer Vorschlag aus Beobachtungen vorhanden",
            label_texts,
        )
        self.assertIsNotNone(app)

    def test_student_profile_renders_report_preview(self) -> None:
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
                                "CMP-000001",
                                "Mit Texten und Medien umgehen",
                                "+",
                                "von Laura bestätigt",
                                "+ erreicht",
                            ),
                        ),
                        (
                            StudentReportCompetencyViewModel(
                                "CMP-000001",
                                "Mit Texten und Medien umgehen",
                                "+",
                                "von Laura bestätigt",
                                "+ erreicht",
                            ),
                        ),
                        (
                            StudentReportDevelopmentViewModel(
                                "CMP-000001",
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

        self.assertIn("Berichtsvorschau", label_texts)
        self.assertIn("Deutsch", label_texts)
        self.assertIn("Aktueller Stand", label_texts)
        self.assertIn("Stärken", label_texts)
        self.assertIn("Entwicklung", label_texts)
        self.assertIn("Unterstützungsbedarf", label_texts)
        self.assertIn("Beispielbeobachtungen", label_texts)
        self.assertIn(
            "Mit Texten und Medien umgehen · "
            "Aktueller Stand: + erreicht · von Laura bestätigt",
            label_texts,
        )
        self.assertIn("Mit Texten und Medien umgehen · Stabil beobachtet: +", label_texts)
        self.assertIn("2026-07-03 · Leseübung · Liest einen bekannten Text.", label_texts)
        self.assertIn("+ Mit Texten und Medien umgehen", label_texts)
        self.assertIsNotNone(app)

    def test_student_profile_renders_compact_documentation_status(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (),
            (),
            None,
            (
                StudentDocumentationSubjectStatus(
                    "deutsch",
                    "Deutsch",
                    8,
                    14,
                    (),
                    0,
                ),
                StudentDocumentationSubjectStatus(
                    "epu",
                    "EPU",
                    0,
                    6,
                    (
                        StudentMissingCompetencyViewModel(
                            "CMP-000003",
                            "Natur und Umwelt",
                            3,
                        ),
                    ),
                    3,
                ),
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]
        overview_details_container = screen.findChild(
            QWidget,
            "OverviewDocumentationDetails",
        )
        overview_details_button = screen.findChild(
            QPushButton,
            "OverviewDocumentationDetailsButton",
        )
        competency_details_container = screen.findChild(QWidget, "DocumentationStatusDetails")
        competency_details_button = screen.findChild(
            QPushButton,
            "DocumentationStatusDetailsButton",
        )

        self.assertIn("Dokumentationsstand", label_texts)
        self.assertIn("8/20 Lernbereiche dokumentiert", label_texts)
        self.assertIn("teilweise dokumentiert", label_texts)
        self.assertIn("Noch wenig belegt: EPU, Deutsch", label_texts)
        self.assertIsNotNone(overview_details_container)
        self.assertTrue(overview_details_container.isHidden())
        self.assertIsNotNone(overview_details_button)
        self.assertFalse(overview_details_button.isHidden())
        self.assertEqual(overview_details_button.text(), "Details anzeigen")
        overview_details_button.click()
        self.assertFalse(overview_details_container.isHidden())
        self.assertEqual(overview_details_button.text(), "Details ausblenden")
        expanded_label_texts = [label.text() for label in screen.findChildren(QLabel)]
        self.assertIn("Deutsch", expanded_label_texts)
        self.assertIn("8/14 Lernbereiche", expanded_label_texts)
        self.assertIn("Deutsch: 8 / 14 dokumentiert", expanded_label_texts)
        self.assertIn("EPU", expanded_label_texts)
        self.assertIn("0/6 Lernbereiche", expanded_label_texts)
        self.assertIn("EPU: 0 / 6 dokumentiert", expanded_label_texts)
        self.assertIn(
            "Für nächste Beobachtungen geeignet: Natur und Umwelt",
            expanded_label_texts,
        )
        detail_text = " ".join(
            label.text().casefold()
            for label in overview_details_container.findChildren(QLabel)
        )
        for avoided_word in ("fehlend", "kritisch", "problem"):
            self.assertNotIn(avoided_word, detail_text)
        self.assertIsNotNone(competency_details_container)
        self.assertTrue(competency_details_container.isHidden())
        self.assertIsNotNone(competency_details_button)
        self.assertEqual(competency_details_button.text(), "Details anzeigen")
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

    def test_student_profile_overview_summarizes_documented_student(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            self._sample_many_observations(),
            (
                StudentCompetencySubjectGroup(
                    "deutsch",
                    "Deutsch",
                    (
                        StudentCompetencyStatusViewModel(
                            "CMP-000001",
                            "Texte sinnentnehmend lesen",
                            "deutsch",
                            "Deutsch",
                            "+",
                            "+ erreicht",
                            "2026-07-05",
                            0,
                            ("-", "+", "+"),
                            3,
                            2.1,
                        ),
                    ),
                ),
                StudentCompetencySubjectGroup(
                    "epu",
                    "EPU",
                    (
                        StudentCompetencyStatusViewModel(
                            "CMP-000003",
                            "Naturphänomene beschreiben",
                            "epu",
                            "EPU",
                            "++",
                            "++ sicher erreicht",
                            "2026-07-04",
                            1,
                            ("+", "++"),
                            2,
                            2.8,
                        ),
                    ),
                ),
            ),
            documentation_statuses=(
                StudentDocumentationSubjectStatus("deutsch", "Deutsch", 2, 3, (), 0),
                StudentDocumentationSubjectStatus("epu", "EPU", 1, 2, (), 1),
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Halbjahresblick", label_texts)
        self.assertIn("4 Beobachtungen · 3/5 Lernbereiche dokumentiert", label_texts)
        self.assertIn(
            f"Letzte Beobachtung: 2026-07-06 · Mathematik · Projektarbeit",
            label_texts,
        )
        self.assertIn("Stärken", label_texts)
        self.assertIn("✓ Texte sinnentnehmend lesen", label_texts)
        self.assertIn("✓ Naturphänomene beschreiben", label_texts)
        self.assertIn("Im Blick behalten", label_texts)
        self.assertIn("Entwicklung", label_texts)
        self.assertNotIn("Texte sinnentnehmend lesen: - → + → +", label_texts)
        self.assertIn(
            "Sichtbare Entwicklung erscheint hier nach mehreren Beobachtungen.",
            label_texts,
        )
        self.assertIsNotNone(app)

    def test_student_profile_overview_does_not_invent_strengths_without_data(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (),
            (),
            documentation_statuses=(
                StudentDocumentationSubjectStatus("deutsch", "Deutsch", 0, 3, (), 0),
            ),
        )

        label_texts = [label.text() for label in screen.findChildren(QLabel)]
        strength_lines = [text for text in label_texts if text.startswith("✓ ")]

        self.assertIn("0 Beobachtungen · 0/3 Lernbereiche dokumentiert", label_texts)
        self.assertIn(
            "Letzte Beobachtung: noch keine Beobachtung dokumentiert",
            label_texts,
        )
        self.assertIn(
            "Noch keine Beobachtungen für eine verlässliche Einschätzung.",
            label_texts,
        )
        self.assertEqual(strength_lines, [])
        self.assertIn("! Deutsch weiter beobachten", label_texts)
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
            (),
            (),
            documentation_statuses=(
                StudentDocumentationSubjectStatus("deutsch", "Deutsch", 0, 2, (), 0),
            ),
        )
        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertEqual(tab_widget.currentIndex(), 0)
        self.assertIn("Noah Beispiel", label_texts)
        self.assertIn("0 Beobachtungen · 0/2 Lernbereiche dokumentiert", label_texts)
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
                            "CMP-000012",
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

        self.assertEqual(screen.table.columnCount(), 4)
        self.assertEqual(screen.table.horizontalHeaderItem(2).text(), "Dokumentation")
        self.assertEqual(screen.table.horizontalHeaderItem(3).text(), "Aktion")
        self.assertEqual(
            screen.table.item(0, 2).text(),
            "1/2 Bereiche · teilweise dokumentiert",
        )
        self.assertNotIn("Deutsch:", screen.table.item(0, 2).text())
        action_widget = screen.table.cellWidget(0, 3)
        self.assertIsNotNone(action_widget)
        action_button = action_widget.findChild(QPushButton)
        self.assertIsNotNone(action_button)
        self.assertEqual(action_button.text(), "Beobachten")
        self.assertEqual(action_button.toolTip(), "Neue Beobachtung für Anna Muster")
        action_button.click()
        self.assertEqual(observation_student_ids, ["STU-000001"])
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
        self.assertEqual(screen.back_to_overview_button.text(), "← Zur Übersicht")
        screen.back_to_overview_button.click()
        self.assertEqual(back_requests, [True])
        self.assertIsNotNone(app)

    def test_student_profile_missing_competencies_can_be_expanded(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (),
            (
                StudentCompetencySubjectGroup(
                    "deutsch",
                    "Deutsch",
                    (
                        StudentCompetencyStatusViewModel(
                            "CMP-000001",
                            "Mit Texten und Medien umgehen",
                            "deutsch",
                            "Deutsch",
                            "+",
                            "+ erreicht",
                            "2026-07-03",
                            0,
                            ("+",),
                            1,
                            2.0,
                        ),
                    ),
                    (
                        StudentMissingCompetencyViewModel(
                            "CMP-000002",
                            "Wörter und Sätze",
                            1,
                        ),
                    ),
                ),
            ),
        )
        details_button = screen.findChild(QPushButton, "CompetencyGroupDetailsButton")
        missing_button = screen.findChild(QPushButton, "MissingCompetenciesDetailsButton")
        missing_container = screen.findChild(QWidget, "MissingCompetenciesDetails")

        self.assertIsNotNone(details_button)
        self.assertIsNotNone(missing_button)
        self.assertIsNotNone(missing_container)
        self.assertTrue(missing_container.isHidden())
        self.assertEqual(
            missing_button.text(),
            "Noch nicht dokumentierte Kompetenzen (1) ▾",
        )

        details_button.click()
        missing_button.click()

        label_texts = [label.text() for label in screen.findChildren(QLabel)]
        self.assertFalse(missing_container.isHidden())
        self.assertEqual(
            missing_button.text(),
            "Noch nicht dokumentierte Kompetenzen (1) ▴",
        )
        self.assertIn("Wörter und Sätze", label_texts)
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
        label_texts = [label.text() for label in screen.findChildren(QLabel)]

        self.assertIn("Schüler: Emma Müller", clipboard_text)
        self.assertIn("Erstellt am:", clipboard_text)
        self.assertIn("## Deutsch", clipboard_text)
        self.assertIn(
            "Mit Texten und Medien umgehen · "
            "Aktueller Stand: + erreicht · von Laura bestätigt",
            clipboard_text,
        )
        self.assertIn("Bericht wurde kopiert.", label_texts)
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

    def test_student_profile_emits_competency_confirmation_actions(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        emitted: list[tuple[str, str, str, str]] = []
        screen.competency_confirmation_requested.connect(
            lambda student_id, competency_id, rating, note: emitted.append(
                (student_id, competency_id, rating, note)
            )
        )
        screen.set_student(
            self._sample_student_detail(),
            (),
            (
                StudentCompetencySubjectGroup(
                    "deutsch",
                    "Deutsch",
                    (
                        StudentCompetencyStatusViewModel(
                            "CMP-000001",
                            "Mit Texten und Medien umgehen",
                            "deutsch",
                            "Deutsch",
                            "+",
                            "+ erreicht",
                            "2026-07-03",
                            0,
                            ("+",),
                            1,
                            2.0,
                        ),
                    ),
                ),
            ),
        )
        buttons = {button.text(): button for button in screen.findChildren(QPushButton)}
        rating_select = screen.findChild(QComboBox, "CompetencyConfirmationRatingSelect")

        buttons["Vorschlag aus Beobachtungen übernehmen"].click()
        rating_select.setCurrentText("++")
        buttons["Aktuell bestätigen"].click()

        self.assertEqual(
            emitted,
            [
                (f"{STUDENT_ID_PREFIX}-000001", "CMP-000001", "+", ""),
                (f"{STUDENT_ID_PREFIX}-000001", "CMP-000001", "++", ""),
            ],
        )
        self.assertIsNotNone(app)

    def test_student_profile_competency_groups_are_collapsible(self) -> None:
        app = QApplication.instance() or QApplication([])
        screen = student_profile_screen.StudentProfileScreen()
        screen.set_student(
            self._sample_student_detail(),
            (),
            (
                StudentCompetencySubjectGroup(
                    "deutsch",
                    "Deutsch",
                    (
                        StudentCompetencyStatusViewModel(
                            "CMP-000001",
                            "Mit Texten und Medien umgehen",
                            "deutsch",
                            "Deutsch",
                            "+",
                            "+ erreicht",
                            "2026-07-03",
                            0,
                            ("-", "+"),
                            2,
                            1.6,
                        ),
                    ),
                ),
            ),
        )
        details_button = screen.findChild(QPushButton, "CompetencyGroupDetailsButton")
        details_container = screen.findChild(QWidget, "CompetencyGroupDetails")

        self.assertIsNotNone(details_button)
        self.assertIsNotNone(details_container)
        self.assertEqual(details_button.text(), "Details ▾")
        self.assertTrue(details_container.isHidden())

        details_button.click()

        self.assertFalse(details_container.isHidden())
        self.assertEqual(details_button.text(), "Details ▴")
        self.assertIsNotNone(app)

    def test_sidebar_students_navigation_resets_to_list(self) -> None:
        target = resolve_navigation_target("students")

        self.assertEqual(target.screen_key, "students")
        self.assertTrue(target.reset_group_filter)

    def test_placeholder_navigation_keeps_target_key(self) -> None:
        target = resolve_navigation_target("reports")

        self.assertEqual(target.screen_key, "reports")
        self.assertFalse(target.reset_group_filter)

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
            "src.desktop_app.shell",
            "src.desktop_app.student_list_view",
            "src.desktop_app.theme",
            "src.desktop_app.view_models.observation_view_model",
            "src.desktop_app.view_models.settings_view_model",
            "src.desktop_app.view_models.student_view_model",
        ):
            with self.subTest(module_name=module_name):
                importlib.import_module(module_name)

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
                            "CMP-000001",
                            "Mit Texten und Medien umgehen",
                            "+",
                            "von Laura bestätigt",
                            "+ erreicht",
                        ),
                    ),
                    (
                        StudentReportCompetencyViewModel(
                            "CMP-000001",
                            "Mit Texten und Medien umgehen",
                            "+",
                            "von Laura bestätigt",
                            "+ erreicht",
                        ),
                    ),
                    (
                        StudentReportDevelopmentViewModel(
                            "CMP-000002",
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
                        "CMP-000001",
                        "Deutsch",
                        "Mit Texten und Medien umgehen",
                        "Lesen und Verstehen",
                        "Texte lesen und zentrale Informationen entnehmen",
                        "+",
                    ),
                    ObservationRatingViewModel(
                        "CMP-000003",
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
                        "CMP-000003",
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
                        "CMP-000001",
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
                        "CMP-000004",
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
    ) -> ObservationDraftViewModel:
        return ObservationDraftViewModel(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            student_name="Emma Müller",
            date_text=date_text,
            subject_id=subject_id,
            subject_display_name=subject_display_name,
            context=context,
            note=note,
            competency_ratings=competency_ratings or (
                self._sample_observation_rating(
                    "CMP-000001",
                    "deutsch",
                    "Deutsch",
                    "Mit Texten und Medien umgehen",
                    "Lesen und Verstehen",
                    "Texte lesen und zentrale Informationen entnehmen",
                    "+",
                ),
                self._sample_observation_rating(
                    "CMP-000002",
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
                initial_draft
            ),
            competency_subject_groups=(
                self.adapter.list_observation_competency_subject_groups(
                    initial_draft
                )
            ),
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
