"""Immutable PDF artifacts generated exclusively from verified LEG revisions."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import BytesIO
from pathlib import Path
from typing import Protocol

from src.core.managed_document_store import (
    ManagedPdfArtifactError,
    ManagedPdfArtifactLifecyclePort,
)

from prototypes.pdf_engine.output_models import (
    DocumentMetadata,
    HeadingBlock,
    KeyValueBlock,
    ParagraphBlock,
    ReportOutputModel,
    ReportPage,
    SpacerBlock,
    TableBlock,
)

from .learning_conference import (
    COMPLETED_REVISION_STATUS,
    LEARNING_CONFERENCE_SNAPSHOT_SCHEMA_VERSION,
    LearningConferenceCompletionError,
    LearningConferenceRevisionReadService,
    LearningConferenceRevisionRecord,
)


PDF_MIME_TYPE = "application/pdf"


class LearningConferencePdfError(ValueError):
    """Raised when a final LEG PDF cannot be produced or verified safely."""


@dataclass(frozen=True)
class LearningConferencePdfArtifactRecord:
    """Immutable reference to one managed PDF file for one LEG revision."""

    learning_conference_pdf_artifact_id: str
    learning_conference_revision_id: str
    relative_file_path: str
    mime_type: str
    file_size_bytes: int
    snapshot_sha256: str
    pdf_sha256: str
    created_at: str


class LearningConferencePdfArtifactRepository(Protocol):
    """Persistence and managed-file boundary for final LEG PDF artifacts."""

    def next_artifact_id(self) -> str: ...

    def get_for_revision(
        self,
        learning_conference_revision_id: str,
    ) -> LearningConferencePdfArtifactRecord | None: ...

    def save_artifact(
        self,
        artifact: LearningConferencePdfArtifactRecord,
    ) -> LearningConferencePdfArtifactRecord: ...

    def resolve_file_path(self, relative_file_path: str) -> Path: ...


class LearningConferencePdfSnapshotValidator:
    """Validate the complete frozen LEG snapshot needed for final output."""

    def validate(
        self,
        revision: LearningConferenceRevisionRecord,
        payload: dict[str, object],
    ) -> None:
        if revision.status != COMPLETED_REVISION_STATUS:
            raise LearningConferencePdfError(
                "Nur eine aktuelle abgeschlossene LEG-Revision kann als PDF erzeugt werden."
            )
        if (
            revision.snapshot_schema_version
            != LEARNING_CONFERENCE_SNAPSHOT_SCHEMA_VERSION
            or payload.get("snapshot_schema_version")
            != revision.snapshot_schema_version
        ):
            raise LearningConferencePdfError(
                "Die Snapshot-Schemaversion der LEG-Revision ist ungueltig."
            )
        self._required_text(
            payload,
            "source_learning_conference_draft_id",
            "Quell-LCD-Referenz",
        )

        student = self._mapping(payload, "student")
        self._required_text(student, "student_id", "Schuelerreferenz")
        self._required_text(student, "display_name", "Schueleranzeigename")
        group = self._mapping(student, "group")
        course = self._mapping(student, "course")
        self._required_text(group, "group_id", "Stammgruppenreferenz")
        self._required_text(group, "group_name", "Stammgruppenname")
        self._required_text(course, "course_id", "Kursreferenz")
        self._required_text(course, "course_name", "Kursname")

        self._iso_date(payload, "conference_date")
        responsible = self._required_text(
            payload,
            "responsible_teacher",
            "verantwortliche Lehrkraft",
        )
        if responsible != revision.completed_by_display_name:
            raise LearningConferencePdfError(
                "Die verantwortliche Lehrkraft des LEG-Snapshots ist ungueltig."
            )
        period = self._mapping(payload, "period")
        period_start = self._optional_iso_date(period, "start")
        period_end = self._optional_iso_date(period, "end")
        if (period_start is None) != (period_end is None):
            raise LearningConferencePdfError(
                "Der Zeitraum des LEG-Snapshots ist unvollstaendig."
            )
        if period_start is not None and period_end is not None and period_end < period_start:
            raise LearningConferencePdfError(
                "Der Zeitraum des LEG-Snapshots ist ungueltig."
            )

        shared = self._mapping(payload, "shared_results")
        for key, label in (
            ("goals", "gemeinsame Ziele"),
            ("support", "Unterstuetzungen"),
            ("agreements", "Vereinbarungen"),
            ("responsibilities", "Zustaendigkeiten"),
        ):
            self._text(shared, key, label)
        if not any(
            str(shared[key]).strip()
            for key in ("goals", "support", "agreements")
        ):
            raise LearningConferencePdfError(
                "Der LEG-Snapshot enthaelt kein abgeschlossenes gemeinsames Ergebnis."
            )
        self._optional_iso_date(shared, "next_review_date")

        subjects = self._mapping_list(payload, "subjects")
        subject_ids = self._unique_ids(subjects, "subject_id", "Fachreferenz")
        for subject in subjects:
            self._required_text(subject, "subject_name", "Fachname")

        cross_topics = self._mapping_list(payload, "cross_topics")
        self._unique_ids(cross_topics, "key", "Themenreferenz")
        for topic in cross_topics:
            self._required_text(topic, "label", "Themenname")

        competencies = self._mapping_list(payload, "competencies")
        self._unique_ids(competencies, "competency_id", "Kompetenzreferenz")
        for competency in competencies:
            subject_id = self._required_text(
                competency,
                "subject_id",
                "Kompetenz-Fachreferenz",
            )
            if subject_id not in subject_ids:
                raise LearningConferencePdfError(
                    "Eine Kompetenzreferenz verweist auf kein ausgewaehltes LEG-Fach."
                )
            for key, label in (
                ("subject_name", "Kompetenz-Fachname"),
                ("learning_area", "Kompetenzbereich"),
                ("competency_group", "Kompetenzthema"),
                ("competency_text", "Kompetenztext"),
                ("catalog_status_at_completion", "Katalogstatus"),
            ):
                self._required_text(competency, key, label)
            for key in ("historical_reference", "active_at_completion"):
                if not isinstance(competency.get(key), bool):
                    raise LearningConferencePdfError(
                        "Die Historienkennzeichnung einer LEG-Kompetenz fehlt."
                    )

        observations = self._mapping_list(payload, "observations")
        self._unique_ids(observations, "observation_id", "Beobachtungsreferenz")
        for observation in observations:
            self._iso_date(observation, "observed_on")
            self._required_text(observation, "subject_id", "Beobachtungs-Fachreferenz")
            self._required_text(observation, "subject_name", "Beobachtungs-Fachname")
            self._text(observation, "context", "Beobachtungskontext")
            self._text(observation, "content", "Beobachtungsinhalt")
            ratings = self._mapping_list(observation, "ratings")
            for rating in ratings:
                self._required_text(rating, "competency_id", "Bewertungskompetenz")
                self._required_text(rating, "rating", "Beobachtungsbewertung")

    def _mapping(
        self,
        payload: dict[str, object],
        key: str,
    ) -> dict[str, object]:
        value = payload.get(key)
        if not isinstance(value, dict):
            raise LearningConferencePdfError(
                f"Der LEG-Snapshot enthaelt keine gueltige Struktur fuer {key}."
            )
        return value

    def _mapping_list(
        self,
        payload: dict[str, object],
        key: str,
    ) -> tuple[dict[str, object], ...]:
        value = payload.get(key)
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise LearningConferencePdfError(
                f"Der LEG-Snapshot enthaelt keine gueltige Liste fuer {key}."
            )
        return tuple(value)

    def _required_text(
        self,
        payload: dict[str, object],
        key: str,
        label: str,
    ) -> str:
        value = self._text(payload, key, label)
        if not value.strip():
            raise LearningConferencePdfError(f"{label} fehlt im LEG-Snapshot.")
        return value

    def _text(
        self,
        payload: dict[str, object],
        key: str,
        label: str,
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str):
            raise LearningConferencePdfError(f"{label} fehlt im LEG-Snapshot.")
        return value

    def _iso_date(self, payload: dict[str, object], key: str) -> date:
        value = self._required_text(payload, key, key)
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise LearningConferencePdfError(
                f"Der Datumswert {key} im LEG-Snapshot ist ungueltig."
            ) from error

    def _optional_iso_date(
        self,
        payload: dict[str, object],
        key: str,
    ) -> date | None:
        value = self._text(payload, key, key)
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise LearningConferencePdfError(
                f"Der Datumswert {key} im LEG-Snapshot ist ungueltig."
            ) from error

    def _unique_ids(
        self,
        items: tuple[dict[str, object], ...],
        key: str,
        label: str,
    ) -> set[str]:
        values = [self._required_text(item, key, label) for item in items]
        if len(values) != len(set(values)):
            raise LearningConferencePdfError(f"{label} ist im LEG-Snapshot doppelt.")
        return set(values)


class LearningConferencePdfOutputModelBuilder:
    """Adapt only one verified LEG snapshot to the neutral renderer contract."""

    def build(
        self,
        revision: LearningConferenceRevisionRecord,
        payload: dict[str, object],
    ) -> ReportOutputModel:
        student = self._mapping(payload["student"])
        group = self._mapping(student["group"])
        course = self._mapping(student["course"])
        period = self._mapping(payload["period"])
        shared = self._mapping(payload["shared_results"])
        competencies = self._mapping_items(payload["competencies"])
        observations = self._mapping_items(payload["observations"])
        conference_date = str(payload["conference_date"])
        metadata = DocumentMetadata(
            document_title="Lernentwicklungsgespräch",
            student_name=str(student["display_name"]),
            group_name=str(group["group_name"]),
            period=self._period_label(period),
            teacher_name=str(payload["responsible_teacher"]),
            school_name="Jenaplan-Schule",
            created_on=date.fromisoformat(revision.completed_at[:10]),
            header_text="Jenaplan-Schule | Lernentwicklungsgespräch",
            footer_text=f"Abgeschlossene Revision {revision.revision_number}",
        )
        next_review = str(shared.get("next_review_date", ""))
        return ReportOutputModel(
            metadata=metadata,
            pages=(
                ReportPage(
                    label="Gesprächskontext",
                    is_cover=True,
                    blocks=(
                        SpacerBlock(18),
                        HeadingBlock(metadata.document_title, level=0),
                        HeadingBlock(metadata.student_name, level=1),
                        KeyValueBlock(
                            (
                                ("Stammgruppe", metadata.group_name),
                                ("Kurs", str(course["course_name"])),
                                ("Gesprächsdatum", self._date_label(conference_date)),
                                ("Zeitraum", metadata.period),
                                ("Verantwortliche Lehrkraft", metadata.teacher_name),
                                ("Revision", str(revision.revision_number)),
                                ("Revisions-ID", revision.learning_conference_revision_id),
                                ("Abgeschlossen am", self._timestamp_label(revision.completed_at)),
                            )
                        ),
                    ),
                ),
                ReportPage(
                    label="Gemeinsame Ergebnisse",
                    blocks=(
                        HeadingBlock("Gemeinsame Ergebnisse"),
                        HeadingBlock("Gemeinsame Ziele", level=2),
                        ParagraphBlock(self._content(shared, "goals")),
                        HeadingBlock("Unterstützungen", level=2),
                        ParagraphBlock(self._content(shared, "support")),
                        HeadingBlock("Vereinbarungen", level=2),
                        ParagraphBlock(self._content(shared, "agreements")),
                        HeadingBlock("Zuständigkeiten", level=2),
                        ParagraphBlock(self._content(shared, "responsibilities")),
                        HeadingBlock("Nächste Überprüfung", level=2),
                        ParagraphBlock(
                            self._date_label(next_review) if next_review else "Nicht festgelegt."
                        ),
                    ),
                ),
                ReportPage(
                    label="Ausgewählte Kompetenzen",
                    blocks=(
                        HeadingBlock("Ausgewählte Kompetenzen"),
                        TableBlock(
                            headers=("Fach", "Bereich · Thema", "Kompetenz"),
                            rows=tuple(
                                (
                                    str(item["subject_name"]),
                                    " · ".join(
                                        value
                                        for value in (
                                            str(item["learning_area"]),
                                            str(item["competency_group"]),
                                        )
                                        if value
                                    ),
                                    str(item["competency_text"])
                                    + (" · historischer Bezug" if item["historical_reference"] else ""),
                                )
                                for item in competencies
                            ),
                            column_weights=(0.2, 0.3, 0.5),
                        ),
                    ),
                ),
                ReportPage(
                    label="Ausgewählte Beobachtungsbelege",
                    blocks=(
                        HeadingBlock("Ausgewählte Beobachtungsbelege"),
                        TableBlock(
                            headers=("Datum", "Fach · Kontext", "Beleg"),
                            rows=tuple(
                                (
                                    self._date_label(str(item["observed_on"])),
                                    " · ".join(
                                        value
                                        for value in (
                                            str(item["subject_name"]),
                                            str(item["context"]),
                                        )
                                        if value
                                    ),
                                    str(item["content"]) or "Kein Text festgehalten.",
                                )
                                for item in observations
                            ),
                            column_weights=(0.18, 0.28, 0.54),
                        ),
                    ),
                ),
            ),
        )

    @staticmethod
    def _mapping(value: object) -> dict[str, object]:
        if not isinstance(value, dict):
            raise LearningConferencePdfError("Der LEG-Snapshot ist ungueltig.")
        return value

    @staticmethod
    def _mapping_items(value: object) -> tuple[dict[str, object], ...]:
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise LearningConferencePdfError("Der LEG-Snapshot ist ungueltig.")
        return tuple(value)

    @staticmethod
    def _content(payload: dict[str, object], key: str) -> str:
        return str(payload[key]).strip() or "Nicht festgehalten."

    @classmethod
    def _period_label(cls, period: dict[str, object]) -> str:
        start = str(period.get("start", ""))
        end = str(period.get("end", ""))
        if not start and not end:
            return "Kein Zeitraum festgelegt"
        return f"{cls._date_label(start)} bis {cls._date_label(end)}"

    @staticmethod
    def _date_label(value: str) -> str:
        return date.fromisoformat(value).strftime("%d.%m.%Y")

    @staticmethod
    def _timestamp_label(value: str) -> str:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime(
            "%d.%m.%Y, %H:%M"
        )


class LearningConferencePdfService:
    """Validate one LCV, render it and persist its immutable artifact reference."""

    def __init__(
        self,
        revision_service: LearningConferenceRevisionReadService,
        artifact_repository: LearningConferencePdfArtifactRepository,
        output_model_builder: LearningConferencePdfOutputModelBuilder,
        renderer: Callable[[ReportOutputModel, object], object],
        *,
        managed_lifecycle: (
            ManagedPdfArtifactLifecyclePort[LearningConferencePdfArtifactRecord] | None
        ) = None,
        validator: LearningConferencePdfSnapshotValidator | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.revision_service = revision_service
        self.artifact_repository = artifact_repository
        self.output_model_builder = output_model_builder
        self.renderer = renderer
        self.managed_lifecycle = managed_lifecycle
        self.validator = validator or LearningConferencePdfSnapshotValidator()
        self.now = now or (lambda: datetime.now(UTC))

    def generate(
        self,
        learning_conference_revision_id: str,
    ) -> LearningConferencePdfArtifactRecord:
        revision_id = learning_conference_revision_id.strip()
        if not revision_id:
            raise LearningConferencePdfError(
                "learning_conference_revision_id darf nicht leer sein."
            )
        revision, payload = self._load_verified(revision_id)
        self.validator.validate(revision, payload)

        if self.managed_lifecycle is not None:
            try:
                return self.managed_lifecycle.generate(
                    revision_id=revision.learning_conference_revision_id,
                    snapshot_sha256=revision.snapshot_sha256,
                    created_at=self._timestamp(),
                    render_pdf=lambda: self._render_bytes(revision, payload),
                )
            except ManagedPdfArtifactError as error:
                raise LearningConferencePdfError(error.code) from error

        existing = self.artifact_repository.get_for_revision(revision_id)
        if existing is not None:
            self._verify_existing(existing, revision)
            return existing

        artifact_id = self.artifact_repository.next_artifact_id()
        relative_path = self._relative_path(revision, payload)
        target_path = self.artifact_repository.resolve_file_path(relative_path)
        temporary_path = target_path.with_suffix(".pdf.tmp")
        if target_path.exists() or temporary_path.exists():
            raise LearningConferencePdfError(
                "Am verwalteten LEG-PDF-Pfad existiert bereits eine nicht registrierte Datei."
            )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        moved_to_target = False
        persisted = False
        try:
            output_model = self.output_model_builder.build(revision, payload)
            rendered_path = Path(self.renderer(output_model, temporary_path))
            if rendered_path.resolve() != temporary_path.resolve():
                raise LearningConferencePdfError(
                    "Der PDF-Renderer hat nicht in den verwalteten Zielpfad geschrieben."
                )
            pdf_bytes = temporary_path.read_bytes()
            if not pdf_bytes.startswith(b"%PDF-"):
                raise LearningConferencePdfError(
                    "Der PDF-Renderer hat keine gueltige PDF-Datei erzeugt."
                )
            file_size = len(pdf_bytes)
            if file_size <= 0:
                raise LearningConferencePdfError("Die erzeugte LEG-PDF-Datei ist leer.")
            pdf_digest = hashlib.sha256(pdf_bytes).hexdigest()
            temporary_path.replace(target_path)
            moved_to_target = True
            artifact = LearningConferencePdfArtifactRecord(
                artifact_id,
                revision.learning_conference_revision_id,
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
        except LearningConferencePdfError:
            raise
        except Exception as error:
            raise LearningConferencePdfError(
                f"Das finale LEG-PDF konnte nicht erzeugt werden: {error}"
            ) from error
        finally:
            temporary_path.unlink(missing_ok=True)
            if moved_to_target and not persisted:
                target_path.unlink(missing_ok=True)

    def load_artifact(
        self,
        learning_conference_revision_id: str,
    ) -> LearningConferencePdfArtifactRecord | None:
        revision_id = learning_conference_revision_id.strip()
        artifact = self.artifact_repository.get_for_revision(revision_id)
        if artifact is None:
            return None
        revision, _payload = self._load_verified(revision_id)
        self._verify_existing(artifact, revision)
        return artifact

    def _load_verified(
        self,
        revision_id: str,
    ) -> tuple[LearningConferenceRevisionRecord, dict[str, object]]:
        try:
            verified = self.revision_service.load_verified_revision(revision_id)
        except LearningConferenceCompletionError as error:
            raise LearningConferencePdfError(str(error)) from error
        return verified.revision, verified.snapshot

    def _relative_path(
        self,
        revision: LearningConferenceRevisionRecord,
        payload: dict[str, object],
    ) -> str:
        student = payload.get("student")
        if not isinstance(student, dict):
            raise LearningConferencePdfError("Schuelerdaten fehlen im LEG-Snapshot.")
        student_id = str(student["student_id"])
        filename = (
            f"Lernentwicklungsgespraech_{student_id}_v{revision.revision_number}_"
            f"{revision.learning_conference_revision_id}.pdf"
        )
        return str(
            Path("documents")
            / student_id
            / "learning_conferences"
            / revision.learning_conference_id
            / revision.learning_conference_revision_id
            / filename
        )

    def _verify_existing(
        self,
        artifact: LearningConferencePdfArtifactRecord,
        revision: LearningConferenceRevisionRecord,
    ) -> None:
        if artifact.snapshot_sha256 != revision.snapshot_sha256:
            raise LearningConferencePdfError(
                "Der Snapshot-Hash des LEG-PDF-Artefakts stimmt nicht mit der Revision ueberein."
            )
        if artifact.relative_file_path.startswith("managed-document:"):
            if self.managed_lifecycle is None:
                raise LearningConferencePdfError(
                    "Ein verschluesseltes LEG-PDF kann ohne Security-Runtime nicht gelesen werden."
                )
            try:
                self.managed_lifecycle.verify_existing(artifact)
            except ManagedPdfArtifactError as error:
                raise LearningConferencePdfError(error.code) from error
            return
        path = self.artifact_repository.resolve_file_path(artifact.relative_file_path)
        if not path.is_file():
            raise LearningConferencePdfError(
                "Die Datei des registrierten LEG-PDF-Artefakts fehlt."
            )
        pdf_bytes = path.read_bytes()
        if not pdf_bytes.startswith(b"%PDF-"):
            raise LearningConferencePdfError(
                "Die Datei des registrierten LEG-PDF-Artefakts ist keine PDF-Datei."
            )
        if len(pdf_bytes) != artifact.file_size_bytes:
            raise LearningConferencePdfError(
                "Die Dateigroesse des LEG-PDF-Artefakts ist ungueltig."
            )
        if hashlib.sha256(pdf_bytes).hexdigest() != artifact.pdf_sha256:
            raise LearningConferencePdfError(
                "Der SHA-256 des LEG-PDF-Artefakts ist ungueltig."
            )

    def _render_bytes(
        self,
        revision: LearningConferenceRevisionRecord,
        payload: dict[str, object],
    ) -> bytes:
        output_model = self.output_model_builder.build(revision, payload)
        sink = BytesIO()
        rendered = self.renderer(output_model, sink)
        if rendered is not sink:
            raise LearningConferencePdfError(
                "Der PDF-Renderer hat nicht in den kontrollierten Speicher geschrieben."
            )
        pdf_bytes = sink.getvalue()
        if not pdf_bytes.startswith(b"%PDF-"):
            raise LearningConferencePdfError(
                "Der PDF-Renderer hat keine gueltige PDF-Datei erzeugt."
            )
        return pdf_bytes

    def _timestamp(self) -> str:
        value = self.now()
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).replace(microsecond=0).isoformat()
