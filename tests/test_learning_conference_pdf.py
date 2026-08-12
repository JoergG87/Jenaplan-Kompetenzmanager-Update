"""Sprint 10B checks for PDFs generated exclusively from completed LCV snapshots."""

from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from pypdf import PdfReader

from prototypes.pdf_engine.renderer import PdfRenderer
from src.core.learning_conference import (
    LearningConferenceRevisionReadService,
    canonical_learning_conference_snapshot_json,
    learning_conference_snapshot_sha256,
)
from src.core.learning_conference_pdf import (
    LearningConferencePdfError,
    LearningConferencePdfOutputModelBuilder,
    LearningConferencePdfSnapshotValidator,
)
from src.core.observation import (
    ObservationCompetencyRatingRecord,
    ObservationRecord,
)
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteLearningConferenceRepository,
    SQLiteObservationRepository,
    create_sqlite_seed_database,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.dialogs import learning_conference_dialog
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceDraftViewModel,
)


class LearningConferencePdfTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "leg-pdf.sqlite"
        create_sqlite_seed_database(self.database_path)
        self.adapter = StudentDesktopAdapter(self.database_path)
        self.student = self.adapter.list_students()[0]
        self.competency = next(
            item
            for item in SQLiteCompetencyRepository(
                self.adapter.database
            ).list_competencies()
            if item.active and item.catalog_status == "current"
        )
        rating = ObservationCompetencyRatingRecord(
            self.competency.competency_id,
            self.competency.subject_id,
            self.competency.subject_name,
            self.competency.learning_area,
            self.competency.competency_group,
            self.competency.description,
            "+",
        )
        self.observation = ObservationRecord(
            "OBS-LEG-PDF",
            self.student.student_id,
            "2026-07-10",
            self.competency.subject_id,
            "Lernzeit",
            "Unveränderlicher gemeinsamer Beobachtungsbeleg.",
            True,
            "2026-07-10T10:00:00+00:00",
            "2026-07-10T10:00:00+00:00",
            (rating,),
        )
        SQLiteObservationRepository(self.adapter.database).create_observation(
            self.observation
        )
        self.saved = self.adapter.save_learning_conference_draft(self._draft())
        self.repository = SQLiteLearningConferenceRepository(self.adapter.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_pdf_is_generated_from_completed_lcv_and_registered(self) -> None:
        revision_id = self._complete()

        artifact = self.adapter.generate_learning_conference_pdf(revision_id)
        path = Path(artifact.file_path)

        self.assertTrue(path.is_file())
        self.assertEqual(artifact.learning_conference_revision_id, revision_id)
        self.assertTrue(
            artifact.learning_conference_pdf_artifact_id.startswith("LCA-")
        )
        self.assertEqual(path.stat().st_size, artifact.file_size_bytes)
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            artifact.pdf_sha256,
        )
        self.assertEqual(
            path.parts[-6:-1],
            (
                "documents",
                self.student.student_id,
                "learning_conferences",
                "LCF-000001",
                revision_id,
            ),
        )
        self.assertNotIn(self.student.display_name, path.name)
        with self.adapter.database.connect() as connection:
            row = connection.execute(
                """
                SELECT learning_conference_revision_id, pdf_sha256
                FROM learning_conference_pdf_artifacts
                """
            ).fetchone()
        self.assertEqual(row["learning_conference_revision_id"], revision_id)
        self.assertEqual(row["pdf_sha256"], artifact.pdf_sha256)

    def test_pdf_contains_only_completed_snapshot_content(self) -> None:
        revision_id = self._complete()

        artifact = self.adapter.generate_learning_conference_pdf(revision_id)
        text = "\n".join(
            page.extract_text() or "" for page in PdfReader(artifact.file_path).pages
        )
        normalized_text = " ".join(text.split())

        self.assertIn("Lernentwicklungsgespräch", text)
        self.assertIn(revision_id, text)
        self.assertIn(self.student.display_name, text)
        self.assertIn("Gemeinsam vereinbartes Ziel", text)
        self.assertIn("Gemeinsam vereinbarte Unterstützung", text)
        self.assertIn("Gemeinsame Vereinbarung", text)
        self.assertIn("Kind: üben; Lehrkraft: begleiten", text)
        self.assertIn(self.competency.description, normalized_text)
        self.assertIn(self.observation.note, text)
        self.assertNotIn("Interner Gesprächseinstieg", text)
        self.assertNotIn("Interne Lehrkraftsicht", text)
        self.assertNotIn("Vorbereitetes Ziel", text)

    def test_lcd_change_does_not_change_existing_pdf(self) -> None:
        revision_id = self._complete()
        first = self.adapter.generate_learning_conference_pdf(revision_id)
        first_bytes = Path(first.file_path).read_bytes()

        self.saved = self.adapter.save_learning_conference_draft(
            replace(
                self.saved,
                agreed_goals_text="Spätere nicht abgeschlossene Draftänderung",
                teacher_perspective_text="Neue interne Vorbereitung",
            )
        )
        second = self.adapter.generate_learning_conference_pdf(revision_id)

        self.assertEqual(second, first)
        self.assertEqual(Path(second.file_path).read_bytes(), first_bytes)

    def test_pdf_sha256_is_stable_and_generation_is_idempotent(self) -> None:
        revision_id = self._complete()
        verified = LearningConferenceRevisionReadService(
            self.repository
        ).load_verified_revision(revision_id)
        first_path = Path(self.temp_dir.name) / "first.pdf"
        second_path = Path(self.temp_dir.name) / "second.pdf"
        model = LearningConferencePdfOutputModelBuilder().build(
            verified.revision,
            verified.snapshot,
        )

        PdfRenderer().render(model, first_path)
        PdfRenderer().render(model, second_path)
        first_hash = hashlib.sha256(first_path.read_bytes()).hexdigest()
        second_hash = hashlib.sha256(second_path.read_bytes()).hexdigest()
        first_artifact = self.adapter.generate_learning_conference_pdf(revision_id)
        second_artifact = self.adapter.generate_learning_conference_pdf(revision_id)

        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_artifact, second_artifact)
        self.assertEqual(first_artifact.pdf_sha256, first_hash)
        with self.adapter.database.connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM learning_conference_pdf_artifacts"
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_subject_column_preserves_long_names_across_multiple_pages(self) -> None:
        revision_id = self._complete()
        verified = LearningConferenceRevisionReadService(
            self.repository
        ).load_verified_revision(revision_id)
        payload = json.loads(json.dumps(verified.snapshot, ensure_ascii=False))
        subject_names = (
            "Mathematik",
            "Kreatives Gestalten",
            "Arbeits-/Lernkompetenz",
            "Selbst- und Sozialkompetenz",
            "Naturwissenschaftliche Bildung und gesellschaftliche Orientierung",
        )
        payload["subjects"] = [
            {
                "subject_id": f"SUB-LAYOUT-{index:03d}",
                "subject_name": subject_name,
            }
            for index, subject_name in enumerate(subject_names)
        ]
        base_competency = dict(payload["competencies"][0])
        payload["competencies"] = [
            {
                **base_competency,
                "competency_id": f"CMP-LAYOUT-{index:03d}",
                "subject_id": (
                    f"SUB-LAYOUT-{index % len(subject_names):03d}"
                ),
                "subject_name": subject_names[index % len(subject_names)],
                "competency_text": (
                    "Eine längere Kompetenzbeschreibung für die stabile "
                    "Mehrseiten-Tabelle."
                ),
            }
            for index in range(50)
        ]
        LearningConferencePdfSnapshotValidator().validate(
            verified.revision,
            payload,
        )
        model = LearningConferencePdfOutputModelBuilder().build(
            verified.revision,
            payload,
        )
        competency_table = next(
            block
            for page in model.pages
            for block in page.blocks
            if getattr(block, "headers", ())
            == ("Fach", "Bereich · Thema", "Kompetenz")
        )
        self.assertEqual(competency_table.column_weights, (0.24, 0.28, 0.48))

        target = Path(self.temp_dir.name) / "long-subjects.pdf"
        PdfRenderer().render(model, target)
        reader = PdfReader(target)
        page_texts = tuple(page.extract_text() or "" for page in reader.pages)
        normalized_text = " ".join(
            "\n".join(page_texts).split()
        )
        competency_pages = tuple(
            page_text
            for page_text in page_texts
            if "Eine längere Kompetenzbeschreibung" in page_text
        )

        self.assertGreater(len(reader.pages), len(model.pages))
        self.assertGreater(len(competency_pages), 1)
        self.assertTrue(all("Fach" in page_text for page_text in competency_pages))
        for subject_name in subject_names:
            self.assertIn(subject_name, normalized_text)

    def test_superseded_revision_cannot_generate_pdf(self) -> None:
        first_revision_id = self._complete()
        self.saved = self.adapter.save_learning_conference_draft(
            replace(self.saved, agreed_goals_text="Korrigiertes gemeinsames Ziel")
        )
        self._complete()

        with self.assertRaisesRegex(LearningConferencePdfError, "abgeschlossene"):
            self.adapter.generate_learning_conference_pdf(first_revision_id)

    def test_corrupted_existing_artifact_is_detected(self) -> None:
        revision_id = self._complete()
        artifact = self.adapter.generate_learning_conference_pdf(revision_id)
        Path(artifact.file_path).write_bytes(b"%PDF-beschaedigt")

        with self.assertRaises(LearningConferencePdfError):
            self.adapter.load_learning_conference_pdf_artifact(revision_id)

    def test_invalid_snapshot_prevents_pdf_even_with_matching_hash(self) -> None:
        revision_id = self._complete()
        revision = self.repository.get_revision(revision_id)
        payload = json.loads(revision.snapshot_json)
        del payload["shared_results"]["responsibilities"]
        canonical = canonical_learning_conference_snapshot_json(payload)
        with self.adapter.database.connect() as connection:
            connection.execute(
                "DROP TRIGGER trg_learning_conference_revisions_immutable_update"
            )
            connection.execute(
                """
                UPDATE learning_conference_revisions
                SET snapshot_json = ?, snapshot_sha256 = ?
                WHERE learning_conference_revision_id = ?
                """,
                (
                    canonical,
                    learning_conference_snapshot_sha256(canonical),
                    revision_id,
                ),
            )
            connection.commit()

        with self.assertRaises(LearningConferencePdfError):
            self.adapter.generate_learning_conference_pdf(revision_id)
        with self.adapter.database.connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM learning_conference_pdf_artifacts"
            ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_leg_ui_contains_no_renderer_hash_or_sqlite_logic(self) -> None:
        source = inspect.getsource(learning_conference_dialog)

        self.assertNotIn("PdfRenderer", source)
        self.assertNotIn("hashlib", source)
        self.assertNotIn("sqlite3", source)
        self.assertNotIn("snapshot_json", source)

    def _complete(self) -> str:
        status = self.adapter.complete_learning_conference(
            self.saved.learning_conference_draft_id
        )
        current = next(item for item in status.revisions if item.status == "completed")
        return current.learning_conference_revision_id

    def _draft(self) -> LearningConferenceDraftViewModel:
        return LearningConferenceDraftViewModel(
            student_id=self.student.student_id,
            period_start=date(2026, 2, 1),
            period_end=date(2026, 7, 31),
            conference_date=date(2026, 7, 10),
            responsible_teacher="Laura Lernbegleiterin",
            conversation_entry_text="Interner Gesprächseinstieg",
            child_retrospective_text="Rückblick des Kindes",
            teacher_perspective_text="Interne Lehrkraftsicht",
            strengths_text="Interne Vorbereitung zu Stärken",
            development_fields_text="Gemeinsam betrachtete Entwicklung",
            prepared_goals_text="Vorbereitetes Ziel",
            prepared_support_text="Vorbereitete Unterstützung",
            prepared_agreements_text="Vorbereitete Vereinbarung",
            agreed_goals_text="Gemeinsam vereinbartes Ziel",
            agreed_support_text="Gemeinsam vereinbarte Unterstützung",
            agreed_agreements_text="Gemeinsame Vereinbarung",
            responsibilities_text="Kind: üben; Lehrkraft: begleiten",
            next_review_date=date(2026, 9, 15),
            subject_ids=(self.competency.subject_id,),
            cross_topic_keys=("social_behavior",),
            competency_ids=(self.competency.competency_id,),
            observation_ids=(self.observation.observation_id,),
            chart_types=("documentation_coverage",),
        )


if __name__ == "__main__":
    unittest.main()
