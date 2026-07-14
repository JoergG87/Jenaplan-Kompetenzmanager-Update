"""Sprint 9A checks for final PDFs generated exclusively from report revisions."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader

from prototypes.pdf_engine.renderer import PdfRenderer
from src.core.learning_report import canonical_snapshot_json, snapshot_sha256
from src.core.learning_report_pdf import LearningReportPdfError
from src.core.observation import ObservationCompetencyRatingRecord, ObservationRecord
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteLearningReportRepository,
    SQLiteObservationRepository,
    create_sqlite_seed_database,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportChartSelectionViewModel,
    LearningReportDraftViewModel,
    LearningReportSubjectDraftViewModel,
)


class LearningReportPdfTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "kompetenzmanager.sqlite"
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
        self.observation = ObservationRecord(
            "OBS-PDF-000001",
            self.student.student_id,
            "2026-03-12",
            self.competency.subject_id,
            "Lernzeit",
            "Unveränderlicher Beobachtungsbeleg für das finale PDF.",
            True,
            "2026-03-12T10:00:00+00:00",
            "2026-03-12T10:00:00+00:00",
            (
                ObservationCompetencyRatingRecord(
                    self.competency.competency_id,
                    self.competency.subject_id,
                    self.competency.subject_name,
                    self.competency.learning_area,
                    self.competency.competency_group,
                    self.competency.description,
                    "+",
                ),
            ),
        )
        SQLiteObservationRepository(self.adapter.database).create_observation(
            self.observation
        )
        self.saved = self.adapter.save_learning_report_draft(self._draft())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_pdf_is_generated_from_final_revision_and_registered(self) -> None:
        revision_id = self._finalize()

        artifact = self.adapter.generate_learning_report_pdf(revision_id)
        path = Path(artifact.file_path)

        self.assertTrue(path.is_file())
        self.assertEqual(artifact.learning_report_revision_id, revision_id)
        self.assertTrue(artifact.learning_report_pdf_artifact_id.startswith("RPA-"))
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
                "reports",
                "RPT-000001",
                revision_id,
            ),
        )
        self.assertNotIn(self.student.display_name, path.name)
        with self.adapter.database.connect() as connection:
            row = connection.execute(
                """
                SELECT learning_report_revision_id, pdf_sha256
                FROM learning_report_pdf_artifacts
                """
            ).fetchone()
        self.assertEqual(row["learning_report_revision_id"], revision_id)
        self.assertEqual(row["pdf_sha256"], artifact.pdf_sha256)

    def test_pdf_content_matches_only_the_revision_snapshot(self) -> None:
        revision_id = self._finalize()

        artifact = self.adapter.generate_learning_report_pdf(revision_id)
        reader = PdfReader(artifact.file_path)
        page_texts = tuple(page.extract_text() or "" for page in reader.pages)
        text = "\n".join(page_texts)

        self.assertIn(revision_id, text)
        self.assertIn(self.student.display_name, text)
        self.assertIn("Manuell verfasster pädagogischer Gesamtblick.", text)
        self.assertIn(self.competency.description, text)
        self.assertIn(self.observation.note, text)
        self.assertIn("Finalisiert am", text)
        for page_number, page_text in enumerate(page_texts, 1):
            self.assertIn(
                f"Seite {page_number} von {len(page_texts)}",
                page_text,
            )

    def test_draft_change_does_not_change_existing_pdf(self) -> None:
        revision_id = self._finalize()
        first = self.adapter.generate_learning_report_pdf(revision_id)
        first_bytes = Path(first.file_path).read_bytes()

        self.saved = self.adapter.save_learning_report_draft(
            replace(
                self.saved,
                overall_text="Nachträglich geänderter Drafttext, nicht Teil des PDFs.",
            )
        )
        second = self.adapter.generate_learning_report_pdf(revision_id)

        self.assertEqual(second, first)
        self.assertEqual(Path(second.file_path).read_bytes(), first_bytes)
        self.assertNotIn(
            "Nachträglich geänderter Drafttext".encode("utf-8"),
            first_bytes,
        )

    def test_pdf_sha256_is_stable_and_generation_is_idempotent(self) -> None:
        revision_id = self._finalize()
        revision = self.adapter.load_learning_report_revision(revision_id)
        first_path = Path(self.temp_dir.name) / "first.pdf"
        second_path = Path(self.temp_dir.name) / "second.pdf"

        PdfRenderer().render(revision.output_model, first_path)
        PdfRenderer().render(revision.output_model, second_path)
        first_hash = hashlib.sha256(first_path.read_bytes()).hexdigest()
        second_hash = hashlib.sha256(second_path.read_bytes()).hexdigest()
        first_artifact = self.adapter.generate_learning_report_pdf(revision_id)
        second_artifact = self.adapter.generate_learning_report_pdf(revision_id)

        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_artifact, second_artifact)
        self.assertEqual(first_artifact.pdf_sha256, first_hash)

    def test_missing_revision_and_superseded_revision_are_rejected(self) -> None:
        with self.assertRaises(LearningReportPdfError):
            self.adapter.generate_learning_report_pdf("RPV-999999")

        first_revision_id = self._finalize()
        self.saved = self.adapter.save_learning_report_draft(
            replace(self.saved, overall_text="Manueller Inhalt für Revision zwei.")
        )
        self._finalize()

        with self.assertRaisesRegex(LearningReportPdfError, "finalisierte"):
            self.adapter.generate_learning_report_pdf(first_revision_id)

    def test_invalid_snapshot_hash_is_rejected_without_artifact(self) -> None:
        revision_id = self._finalize()
        with self.adapter.database.connect() as connection:
            connection.execute(
                "DROP TRIGGER trg_learning_report_revisions_immutable_update"
            )
            connection.execute(
                """
                UPDATE learning_report_revisions
                SET snapshot_sha256 = ?
                WHERE learning_report_revision_id = ?
                """,
                ("0" * 64, revision_id),
            )
            connection.commit()

        with self.assertRaises(LearningReportPdfError):
            self.adapter.generate_learning_report_pdf(revision_id)

        self._assert_no_artifact()

    def test_missing_snapshot_reference_is_rejected_even_with_matching_hash(self) -> None:
        revision_id = self._finalize()
        repository = SQLiteLearningReportRepository(self.adapter.database)
        revision = repository.get_revision(revision_id)
        payload = json.loads(revision.snapshot_json)
        payload["competencies"][0]["subject_id"] = "missing-subject"
        canonical = canonical_snapshot_json(payload)
        with self.adapter.database.connect() as connection:
            connection.execute(
                "DROP TRIGGER trg_learning_report_revisions_immutable_update"
            )
            connection.execute(
                """
                UPDATE learning_report_revisions
                SET snapshot_json = ?, snapshot_sha256 = ?
                WHERE learning_report_revision_id = ?
                """,
                (canonical, snapshot_sha256(canonical), revision_id),
            )
            connection.commit()

        with self.assertRaisesRegex(LearningReportPdfError, "Kompetenzreferenz"):
            self.adapter.generate_learning_report_pdf(revision_id)

        self._assert_no_artifact()

    def test_renderer_failure_leaves_no_file_or_artifact_reference(self) -> None:
        revision_id = self._finalize()

        with patch.object(PdfRenderer, "render", side_effect=RuntimeError("kaputt")):
            with self.assertRaises(LearningReportPdfError):
                self.adapter.generate_learning_report_pdf(revision_id)

        self._assert_no_artifact()
        pdf_files = tuple((self.database_path.parent / "documents").rglob("*.pdf"))
        self.assertEqual(pdf_files, ())

    def test_artifact_reference_is_immutable_in_sqlite(self) -> None:
        revision_id = self._finalize()
        artifact = self.adapter.generate_learning_report_pdf(revision_id)

        with self.adapter.database.connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    UPDATE learning_report_pdf_artifacts
                    SET pdf_sha256 = ?
                    WHERE learning_report_pdf_artifact_id = ?
                    """,
                    ("0" * 64, artifact.learning_report_pdf_artifact_id),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    DELETE FROM learning_report_pdf_artifacts
                    WHERE learning_report_pdf_artifact_id = ?
                    """,
                    (artifact.learning_report_pdf_artifact_id,),
                )

    def test_corrupted_existing_pdf_is_rejected(self) -> None:
        revision_id = self._finalize()
        artifact = self.adapter.generate_learning_report_pdf(revision_id)
        Path(artifact.file_path).write_bytes(b"%PDF-beschaedigt")

        with self.assertRaises(LearningReportPdfError):
            self.adapter.load_learning_report_pdf_artifact(revision_id)

    def _finalize(self) -> str:
        status = self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )
        return status.current_revision_id

    def _assert_no_artifact(self) -> None:
        with self.adapter.database.connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM learning_report_pdf_artifacts"
            ).fetchone()[0]
        self.assertEqual(count, 0)

    def _draft(self) -> LearningReportDraftViewModel:
        return LearningReportDraftViewModel(
            student_id=self.student.student_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            teacher_name="Laura Lernbegleiterin",
            overall_text="Manuell verfasster pädagogischer Gesamtblick.",
            subjects=(
                LearningReportSubjectDraftViewModel(
                    self.competency.subject_id,
                    "Sorgfältiges Arbeiten.",
                    "Zunehmend selbstständig.",
                    "Ruhige Zwischenschritte.",
                    "Lösungswege festhalten.",
                ),
            ),
            competency_ids=(self.competency.competency_id,),
            observation_ids=(self.observation.observation_id,),
            chart_selections=tuple(
                LearningReportChartSelectionViewModel(
                    self.competency.subject_id,
                    chart_type,
                )
                for chart_type in (
                    "documentation_coverage",
                    "competency_timeline",
                    "observation_timeline",
                )
            ),
        )


if __name__ == "__main__":
    unittest.main()
