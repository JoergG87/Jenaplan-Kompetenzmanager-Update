"""Final PDF artifacts generated exclusively from immutable report revisions."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

from .learning_report import (
    FINALIZED_REVISION_STATUS,
    LEARNING_REPORT_SNAPSHOT_SCHEMA_VERSION,
    LearningReportRecord,
    LearningReportRevisionReadService,
    LearningReportRevisionRecord,
    ReportFinalizationError,
)


PDF_MIME_TYPE = "application/pdf"


class LearningReportPdfError(ValueError):
    """Raised when a final report PDF cannot be produced or verified safely."""


@dataclass(frozen=True)
class LearningReportPdfArtifactRecord:
    """Immutable reference to one managed PDF file for one report revision."""

    learning_report_pdf_artifact_id: str
    learning_report_revision_id: str
    relative_file_path: str
    mime_type: str
    file_size_bytes: int
    snapshot_sha256: str
    pdf_sha256: str
    created_at: str


class LearningReportPdfArtifactRepository(Protocol):
    """Persistence and managed-file boundary for final report PDF artifacts."""

    def next_artifact_id(self) -> str: ...

    def get_for_revision(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportPdfArtifactRecord | None: ...

    def save_artifact(
        self,
        artifact: LearningReportPdfArtifactRecord,
    ) -> LearningReportPdfArtifactRecord: ...

    def resolve_file_path(self, relative_file_path: str) -> Path: ...


class LearningReportPdfSnapshotValidator:
    """Validate the complete frozen snapshot contract required by the PDF."""

    def validate(
        self,
        report: LearningReportRecord,
        revision: LearningReportRevisionRecord,
        payload: dict[str, object],
    ) -> None:
        if revision.status != FINALIZED_REVISION_STATUS:
            raise LearningReportPdfError(
                "Nur eine aktuelle finalisierte Berichtrevision kann als PDF erzeugt werden."
            )
        if revision.learning_report_id != report.learning_report_id:
            raise LearningReportPdfError(
                "Die Berichtrevision gehoert nicht zum geladenen Berichtaggregat."
            )
        payload_schema_version = payload.get("snapshot_schema_version")
        if (
            revision.snapshot_schema_version
            != LEARNING_REPORT_SNAPSHOT_SCHEMA_VERSION
            or payload_schema_version != revision.snapshot_schema_version
        ):
            raise LearningReportPdfError(
                "Die Snapshot-Schemaversion der Berichtrevision ist ungueltig."
            )
        if payload.get("source_report_draft_id") != report.source_report_draft_id:
            raise LearningReportPdfError(
                "Die Quellreferenz des Bericht-Snapshots ist ungueltig."
            )
        if payload.get("report_type") != report.report_type:
            raise LearningReportPdfError(
                "Der Berichtstyp des Snapshots stimmt nicht mit dem Bericht ueberein."
            )

        student = self._mapping(payload, "student")
        if student.get("student_id") != report.student_id:
            raise LearningReportPdfError(
                "Die Schuelerreferenz des Bericht-Snapshots ist ungueltig."
            )
        self._required_text(student, "display_name", "Schueleranzeigename")
        group = self._mapping(student, "group")
        course = self._mapping(student, "course")
        self._required_text(group, "group_id", "Stammgruppenreferenz")
        self._required_text(group, "group_name", "Stammgruppenname")
        self._required_text(course, "course_id", "Kursreferenz")
        self._required_text(course, "course_name", "Kursname")

        period = self._mapping(payload, "period")
        period_start = self._iso_date(period, "start")
        period_end = self._iso_date(period, "end")
        if period_start.isoformat() != report.period_start:
            raise LearningReportPdfError(
                "Der Beginn des Snapshot-Zeitraums ist ungueltig."
            )
        if period_end.isoformat() != report.period_end or period_end <= period_start:
            raise LearningReportPdfError(
                "Das Ende des Snapshot-Zeitraums ist ungueltig."
            )
        responsible_display_name = self._required_text(
            payload,
            "responsible_display_name",
            "verantwortlicher Anzeigename",
        )
        if responsible_display_name != revision.finalized_by_display_name:
            raise LearningReportPdfError(
                "Der verantwortliche Anzeigename des Snapshots ist ungueltig."
            )
        snapshot_created_at = self._required_text(
            payload,
            "snapshot_created_at",
            "Snapshot-Zeitpunkt",
        )
        if snapshot_created_at != revision.finalized_at:
            raise LearningReportPdfError(
                "Der Snapshot-Zeitpunkt stimmt nicht mit der Revision ueberein."
            )

        subjects = self._mapping_list(payload, "subjects")
        if not subjects:
            raise LearningReportPdfError("Der Bericht-Snapshot enthaelt keine Faecher.")
        subject_ids = self._unique_ids(subjects, "subject_id", "Fachreferenz")
        for subject in subjects:
            self._required_text(subject, "subject_name", "Fachname")

        manual_texts = self._mapping(payload, "manual_texts")
        if "overall_text" not in manual_texts or not isinstance(
            manual_texts["overall_text"], str
        ):
            raise LearningReportPdfError(
                "Der paedagogische Gesamttext des Snapshots fehlt."
            )
        manual_subjects = self._mapping_list(manual_texts, "subjects")
        manual_subject_ids = self._unique_ids(
            manual_subjects,
            "subject_id",
            "Fachtextreferenz",
        )
        if manual_subject_ids != subject_ids:
            raise LearningReportPdfError(
                "Die Fachtexte des Snapshots sind nicht vollstaendig referenziert."
            )
        for subject_text in manual_subjects:
            for key in (
                "strengths_text",
                "development_text",
                "support_needs_text",
                "next_goals_text",
            ):
                if key not in subject_text or not isinstance(subject_text[key], str):
                    raise LearningReportPdfError(
                        "Ein eingefrorener Fachtext des Snapshots fehlt."
                    )

        competencies = self._mapping_list(payload, "competencies")
        self._unique_ids(competencies, "competency_id", "Kompetenzreferenz")
        for competency in competencies:
            if competency.get("subject_id") not in subject_ids:
                raise LearningReportPdfError(
                    "Eine Kompetenzreferenz des Snapshots verweist auf kein Berichtfach."
                )
            for key, label in (
                ("competency_text", "Kompetenztext"),
                ("learning_area", "Kompetenzbereich"),
                ("competency_group", "Kompetenzthema"),
            ):
                self._required_text(competency, key, label)
            if not isinstance(competency.get("historical_reference"), bool):
                raise LearningReportPdfError(
                    "Die Historienkennzeichnung einer Kompetenzreferenz fehlt."
                )

        observations = self._mapping_list(payload, "observations")
        self._unique_ids(observations, "observation_id", "Beobachtungsreferenz")
        for observation in observations:
            self._iso_date(observation, "observed_on")
            matched = observation.get("matched_subject_ids")
            if not isinstance(matched, list) or not matched:
                raise LearningReportPdfError(
                    "Eine Beobachtungsreferenz ist keinem Berichtfach zugeordnet."
                )
            if any(not isinstance(value, str) or value not in subject_ids for value in matched):
                raise LearningReportPdfError(
                    "Eine Beobachtungsreferenz verweist auf kein Berichtfach."
                )
            if "content" not in observation or not isinstance(
                observation["content"], str
            ):
                raise LearningReportPdfError(
                    "Der eingefrorene Inhalt einer Beobachtungsreferenz fehlt."
                )

        charts = self._mapping_list(payload, "charts")
        for chart in charts:
            if chart.get("subject_id") not in subject_ids:
                raise LearningReportPdfError(
                    "Eine Diagrammreferenz verweist auf kein Berichtfach."
                )
            self._required_text(chart, "chart_type", "Diagrammtyp")
            self._mapping(chart, "values")

    def _mapping(
        self,
        payload: dict[str, object],
        key: str,
    ) -> dict[str, object]:
        value = payload.get(key)
        if not isinstance(value, dict):
            raise LearningReportPdfError(
                f"Der Bericht-Snapshot enthaelt keine gueltige Struktur fuer {key}."
            )
        return value

    def _mapping_list(
        self,
        payload: dict[str, object],
        key: str,
    ) -> tuple[dict[str, object], ...]:
        value = payload.get(key)
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise LearningReportPdfError(
                f"Der Bericht-Snapshot enthaelt keine gueltige Liste fuer {key}."
            )
        return tuple(value)

    def _required_text(
        self,
        payload: dict[str, object],
        key: str,
        label: str,
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LearningReportPdfError(f"{label} fehlt im Bericht-Snapshot.")
        return value

    def _iso_date(self, payload: dict[str, object], key: str) -> date:
        value = self._required_text(payload, key, key)
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise LearningReportPdfError(
                f"Der Datumswert {key} im Bericht-Snapshot ist ungueltig."
            ) from error

    def _unique_ids(
        self,
        items: tuple[dict[str, object], ...],
        key: str,
        label: str,
    ) -> set[str]:
        values = [self._required_text(item, key, label) for item in items]
        if len(values) != len(set(values)):
            raise LearningReportPdfError(f"{label} ist im Bericht-Snapshot doppelt.")
        return set(values)


class LearningReportPdfService:
    """Validate one RPV, render it and persist its immutable artifact reference."""

    def __init__(
        self,
        revision_service: LearningReportRevisionReadService,
        artifact_repository: LearningReportPdfArtifactRepository,
        report_loader: Callable[[str], LearningReportRecord | None],
        output_model_builder: Callable[
            [LearningReportRevisionRecord, dict[str, object]], object
        ],
        renderer: Callable[[object, Path], Path],
        *,
        validator: LearningReportPdfSnapshotValidator | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.revision_service = revision_service
        self.artifact_repository = artifact_repository
        self.report_loader = report_loader
        self.output_model_builder = output_model_builder
        self.renderer = renderer
        self.validator = validator or LearningReportPdfSnapshotValidator()
        self.now = now or (lambda: datetime.now(UTC))

    def generate(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportPdfArtifactRecord:
        revision_id = learning_report_revision_id.strip()
        if not revision_id:
            raise LearningReportPdfError(
                "learning_report_revision_id darf nicht leer sein."
            )
        try:
            loaded = self.revision_service.snapshot_payload(revision_id)
        except ReportFinalizationError as error:
            raise LearningReportPdfError(str(error)) from error
        if loaded is None:
            raise LearningReportPdfError(
                f"Berichtrevision nicht gefunden: {revision_id}"
            )
        revision, payload = loaded
        report = self.report_loader(revision.learning_report_id)
        if report is None:
            raise LearningReportPdfError(
                "Das Berichtaggregat der ausgewaehlten Revision fehlt."
            )
        self.validator.validate(report, revision, payload)

        existing = self.artifact_repository.get_for_revision(revision_id)
        if existing is not None:
            self._verify_existing(existing, revision)
            return existing

        artifact_id = self.artifact_repository.next_artifact_id()
        relative_path = self._relative_path(report, revision, payload)
        target_path = self.artifact_repository.resolve_file_path(relative_path)
        temporary_path = target_path.with_suffix(".pdf.tmp")
        if target_path.exists() or temporary_path.exists():
            raise LearningReportPdfError(
                "Am verwalteten PDF-Pfad existiert bereits eine nicht registrierte Datei."
            )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        moved_to_target = False
        persisted = False
        try:
            output_model = self.output_model_builder(revision, payload)
            rendered_path = Path(self.renderer(output_model, temporary_path))
            if rendered_path.resolve() != temporary_path.resolve():
                raise LearningReportPdfError(
                    "Der PDF-Renderer hat nicht in den verwalteten Zielpfad geschrieben."
                )
            pdf_bytes = temporary_path.read_bytes()
            if not pdf_bytes.startswith(b"%PDF-"):
                raise LearningReportPdfError(
                    "Der PDF-Renderer hat keine gueltige PDF-Datei erzeugt."
                )
            file_size = len(pdf_bytes)
            if file_size <= 0:
                raise LearningReportPdfError("Die erzeugte PDF-Datei ist leer.")
            pdf_digest = hashlib.sha256(pdf_bytes).hexdigest()
            temporary_path.replace(target_path)
            moved_to_target = True
            artifact = LearningReportPdfArtifactRecord(
                artifact_id,
                revision.learning_report_revision_id,
                relative_path,
                PDF_MIME_TYPE,
                file_size,
                revision.snapshot_sha256,
                pdf_digest,
                self._timestamp(),
            )
            saved = self.artifact_repository.save_artifact(artifact)
            persisted = True
            return saved
        except LearningReportPdfError:
            raise
        except Exception as error:
            raise LearningReportPdfError(
                f"Das finale PDF konnte nicht erzeugt werden: {error}"
            ) from error
        finally:
            temporary_path.unlink(missing_ok=True)
            if moved_to_target and not persisted:
                target_path.unlink(missing_ok=True)

    def load_artifact(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportPdfArtifactRecord | None:
        revision_id = learning_report_revision_id.strip()
        artifact = self.artifact_repository.get_for_revision(revision_id)
        if artifact is None:
            return None
        revision = self.revision_service.revision_by_id(revision_id)
        if revision is None:
            raise LearningReportPdfError(
                "Die Quellrevision des PDF-Artefakts fehlt."
            )
        self._verify_existing(artifact, revision)
        return artifact

    def _relative_path(
        self,
        report: LearningReportRecord,
        revision: LearningReportRevisionRecord,
        payload: dict[str, object],
    ) -> str:
        student = payload["student"]
        if not isinstance(student, dict):
            raise LearningReportPdfError("Schuelerdaten fehlen im Bericht-Snapshot.")
        student_id = str(student["student_id"])
        filename = (
            f"Lernentwicklungsbericht_{student_id}_{report.period_end}_"
            f"v{revision.revision_number}_{revision.learning_report_revision_id}.pdf"
        )
        return str(
            Path("documents")
            / student_id
            / "reports"
            / report.learning_report_id
            / revision.learning_report_revision_id
            / filename
        )

    def _verify_existing(
        self,
        artifact: LearningReportPdfArtifactRecord,
        revision: LearningReportRevisionRecord,
    ) -> None:
        if artifact.snapshot_sha256 != revision.snapshot_sha256:
            raise LearningReportPdfError(
                "Der Snapshot-Hash des PDF-Artefakts stimmt nicht mit der Revision ueberein."
            )
        path = self.artifact_repository.resolve_file_path(
            artifact.relative_file_path
        )
        if not path.is_file():
            raise LearningReportPdfError(
                "Die Datei des registrierten PDF-Artefakts fehlt."
            )
        pdf_bytes = path.read_bytes()
        if len(pdf_bytes) != artifact.file_size_bytes:
            raise LearningReportPdfError(
                "Die Dateigroesse des PDF-Artefakts ist ungueltig."
            )
        if hashlib.sha256(pdf_bytes).hexdigest() != artifact.pdf_sha256:
            raise LearningReportPdfError(
                "Der SHA-256 des PDF-Artefakts ist ungueltig."
            )

    def _timestamp(self) -> str:
        value = self.now()
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).replace(microsecond=0).isoformat()
