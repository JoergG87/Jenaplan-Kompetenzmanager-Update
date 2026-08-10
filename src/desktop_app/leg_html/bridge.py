"""Explicit LEG-only QWebChannel bridge over existing Python contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import json
from typing import Callable

from PySide6.QtCore import QObject, Signal, Slot

from src.core.learning_conference import LearningConferenceCompletionError
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceDraftViewModel,
    LearningConferencePdfArtifactViewModel,
    LearningConferencePreparationViewModel,
    LearningConferenceRevisionStatusViewModel,
    LearningConferenceSubjectViewModel,
    build_learning_conference_completion_error,
)


JsonObject = dict[str, object]


@dataclass
class LearningConferenceHtmlSession:
    """One process-local binding to the existing LEG aggregate and callbacks."""

    preparation: LearningConferencePreparationViewModel
    draft: LearningConferenceDraftViewModel
    revision_status: LearningConferenceRevisionStatusViewModel | None = None
    artifacts_by_revision_id: dict[str, LearningConferencePdfArtifactViewModel] | None = None
    save_draft: Callable[
        [LearningConferenceDraftViewModel], LearningConferenceDraftViewModel
    ] | None = None
    complete_conference: Callable[[str], LearningConferenceRevisionStatusViewModel] | None = None
    refresh_revision_status: Callable[[str], LearningConferenceRevisionStatusViewModel] | None = None
    load_final_artifact: Callable[[str], LearningConferencePdfArtifactViewModel | None] | None = None
    open_revision: Callable[[str], None] | None = None
    show_final_pdf: Callable[[str], None] | None = None


class LearningConferenceHtmlBridge(QObject):
    """Allowlisted UI projection; owns no persistence or completion rules."""

    stateChanged = Signal(str)
    operationFinished = Signal(str)

    _TEXT_FIELDS = frozenset(
        {
            "responsible_teacher",
            "conversation_entry_text",
            "child_retrospective_text",
            "teacher_perspective_text",
            "strengths_text",
            "development_fields_text",
            "prepared_goals_text",
            "prepared_support_text",
            "prepared_agreements_text",
            "agreed_goals_text",
            "agreed_support_text",
            "agreed_agreements_text",
            "responsibilities_text",
        }
    )
    _DATE_FIELDS = frozenset(
        {"period_start", "period_end", "conference_date", "next_review_date"}
    )
    _SELECTION_FIELDS = {
        "subject": "subject_ids",
        "cross_topic": "cross_topic_keys",
        "competency": "competency_ids",
        "observation": "observation_ids",
        "chart": "chart_types",
    }
    _VISIBLE_COMPLETION_ERRORS = {
        "student_missing": "Das Kind ist für diesen Abschluss nicht verfügbar.",
        "assignment_missing": "Für das Gesprächsdatum fehlt eine eindeutige Zuordnung.",
        "assignment_ambiguous": "Für das Gesprächsdatum ist die Zuordnung nicht eindeutig.",
        "assignment_exited": "Für das Gesprächsdatum besteht keine aktive Zuordnung.",
        "conference_date_missing": "Bitte lege das Gesprächsdatum fest.",
        "conference_date_invalid": "Das Gesprächsdatum ist ungültig.",
        "responsible_teacher_missing": "Bitte trage die verantwortliche Lehrkraft ein.",
        "period_invalid": "Bitte prüfe den Gesprächszeitraum.",
        "shared_result_missing": "Bitte halte mindestens ein gemeinsames Ergebnis fest.",
        "subject_reference_missing": "Bitte wähle mindestens einen Fachbereich.",
        "competency_reference_missing": "Eine ausgewählte Kompetenz ist nicht mehr verfügbar.",
        "competency_reference_invalid": "Eine ausgewählte Kompetenz kann nicht abgeschlossen werden.",
        "observation_unavailable": "Ein ausgewählter Beleg ist nicht mehr verfügbar.",
        "observation_invalid": "Ein ausgewählter Beleg kann nicht abgeschlossen werden.",
    }

    def __init__(
        self,
        session: LearningConferenceHtmlSession,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self._baseline = session.draft
        self._save_pending = False
        self._completion_pending = False

    @property
    def is_dirty(self) -> bool:
        return self.session.draft != self._baseline

    @Slot(result=str)
    def initialState(self) -> str:  # noqa: N802
        return _dump(self._state())

    @Slot(result=str)
    def loadEvidenceState(self) -> str:  # noqa: N802
        """Project the large hierarchy only on the first explicit DOM request."""
        return _dump(_evidence_preparation(self.session.preparation, self.session.draft))

    @Slot(str, str, result=str)
    def updateText(self, field: str, value: str) -> str:  # noqa: N802
        if field not in self._TEXT_FIELDS:
            return self._error("field_not_allowed")
        self.session.draft = replace(self.session.draft, **{field: value})
        return self._changed("draft_updated")

    @Slot(str, str, result=str)
    def updateDate(self, field: str, value: str) -> str:  # noqa: N802
        if field not in self._DATE_FIELDS:
            return self._error("date_field_not_allowed")
        try:
            parsed = date.fromisoformat(value) if value else None
        except ValueError:
            return self._error("date_invalid", "Bitte gib ein gültiges Datum ein.")
        self.session.draft = replace(self.session.draft, **{field: parsed})
        return self._changed("draft_updated")

    @Slot(str, str, bool, result=str)
    def setSelection(self, kind: str, item_id: str, selected: bool) -> str:  # noqa: N802
        attribute = self._SELECTION_FIELDS.get(kind)
        if attribute is None:
            return self._error("selection_not_allowed")
        if not self._known_selection(kind, item_id):
            return self._error("selection_unknown")
        values = list(getattr(self.session.draft, attribute))
        if selected and item_id not in values:
            values.append(item_id)
        elif not selected and item_id in values:
            values.remove(item_id)
        self.session.draft = replace(
            self.session.draft,
            **{attribute: tuple(sorted(values))},
        )
        return self._changed("draft_updated")

    @Slot(result=str)
    def saveConferenceDraft(self) -> str:  # noqa: N802
        callback = self.session.save_draft
        if callback is None:
            return self._error("save_unavailable")
        if self._save_pending:
            return self._error("save_in_progress")
        self._save_pending = True
        try:
            saved = callback(self.session.draft)
        except Exception:
            return self._error(
                "save_failed",
                "Der LEG-Entwurf konnte nicht gespeichert werden.",
            )
        finally:
            self._save_pending = False
        self.session.draft = saved
        self._baseline = saved
        self._refresh_revision_context()
        return self._changed("draft_saved")

    @Slot(result=str)
    def completeConference(self) -> str:  # noqa: N802
        callback = self.session.complete_conference
        draft_id = self.session.draft.learning_conference_draft_id
        if callback is None:
            return self._error("completion_unavailable")
        if self._completion_pending:
            return self._error("completion_in_progress")
        if self.is_dirty or not draft_id:
            return self._error(
                "completion_requires_saved_draft",
                "Bitte speichere den Entwurf vor dem Abschluss.",
            )
        self._completion_pending = True
        try:
            self.session.revision_status = callback(draft_id)
        except LearningConferenceCompletionError as error:
            visible = build_learning_conference_completion_error(error)
            message = self._VISIBLE_COMPLETION_ERRORS.get(
                visible.code,
                "Das LEG ist noch nicht bereit für den Abschluss.",
            )
            return self._error(
                "completion_not_ready",
                message,
                phase_key=visible.phase_key,
            )
        except Exception:
            return self._error(
                "completion_failed",
                "Das LEG konnte wegen eines technischen Fehlers nicht abgeschlossen werden.",
            )
        finally:
            self._completion_pending = False
        self._refresh_artifacts()
        return self._changed("conference_completed")

    @Slot(str, result=str)
    def openRevision(self, revision_id: str) -> str:  # noqa: N802
        known = {
            item.learning_conference_revision_id
            for item in (
                self.session.revision_status.revisions
                if self.session.revision_status is not None
                else ()
            )
        }
        if revision_id not in known or self.session.open_revision is None:
            return self._error("revision_unavailable")
        self.session.open_revision(revision_id)
        return self._ok("revision_open_requested")

    @Slot(str, result=str)
    def showFinalPdf(self, artifact_id: str) -> str:  # noqa: N802
        known = {
            artifact.learning_conference_pdf_artifact_id
            for artifact in (self.session.artifacts_by_revision_id or {}).values()
        }
        if artifact_id not in known:
            return self._error("final_pdf_unavailable")
        if self.session.show_final_pdf is None:
            return self._error(
                "final_pdf_viewer_blocked",
                "Die sichere Anzeige des finalen PDFs ist technisch noch nicht freigegeben.",
            )
        self.session.show_final_pdf(artifact_id)
        return self._ok("final_pdf_open_requested")

    def _refresh_revision_context(self) -> None:
        draft_id = self.session.draft.learning_conference_draft_id
        callback = self.session.refresh_revision_status
        if draft_id and callback is not None:
            try:
                self.session.revision_status = callback(draft_id)
            except Exception:
                self.session.revision_status = None
        self._refresh_artifacts()

    def _refresh_artifacts(self) -> None:
        loader = self.session.load_final_artifact
        status = self.session.revision_status
        artifacts: dict[str, LearningConferencePdfArtifactViewModel] = {}
        if loader is not None and status is not None:
            for revision in status.revisions:
                try:
                    artifact = loader(revision.learning_conference_revision_id)
                except Exception:
                    artifact = None
                if artifact is not None:
                    artifacts[revision.learning_conference_revision_id] = artifact
        self.session.artifacts_by_revision_id = artifacts

    def _known_selection(self, kind: str, item_id: str) -> bool:
        preparation = self.session.preparation
        if kind == "subject":
            return any(item.subject_id == item_id for item in preparation.subjects)
        if kind == "cross_topic":
            return any(item.cross_topic_key == item_id for item in preparation.cross_topics)
        if kind == "competency":
            return any(
                competency.competency_id == item_id
                and (
                    competency.selectable
                    or item_id in self.session.draft.competency_ids
                )
                for subject in preparation.subjects
                for competency in subject.competencies
            )
        if kind == "observation":
            return (
                any(item.observation_id == item_id for item in preparation.evidence)
                or item_id in self.session.draft.unavailable_observation_ids
            )
        return item_id in {
            "documentation_coverage",
            "competency_timeline",
            "observation_timeline",
        }

    def _state(self) -> JsonObject:
        return {
            "surface": "conference",
            "preparation": _preparation_summary(self.session.preparation),
            "draft": _draft(self.session.draft),
            "revision_status": _revision_status(
                self.session.revision_status,
                self.session.artifacts_by_revision_id or {},
            ),
            "dirty": self.is_dirty,
            "capabilities": {
                "save": self.session.save_draft is not None,
                "complete": self.session.complete_conference is not None,
                "show_final_pdf": self.session.show_final_pdf is not None,
            },
        }

    def _changed(self, code: str) -> str:
        self.stateChanged.emit(_dump(self._state()))
        return self._ok(code)

    def _ok(self, code: str) -> str:
        result = {"ok": True, "code": code}
        payload = _dump(result)
        self.operationFinished.emit(payload)
        return payload

    def _error(
        self,
        code: str,
        message: str | None = None,
        *,
        phase_key: str | None = None,
    ) -> str:
        result: JsonObject = {"ok": False, "code": code}
        if message:
            result["message"] = message
        if phase_key:
            result["phase_key"] = phase_key
        payload = _dump(result)
        self.operationFinished.emit(payload)
        return payload


def _ordered_subjects(
    value: LearningConferencePreparationViewModel,
) -> list[LearningConferenceSubjectViewModel]:
    return list(value.subjects)


def _preparation_summary(value: LearningConferencePreparationViewModel) -> JsonObject:
    return {
        "student_name": value.student_name,
        "group_name": value.group_name,
        "course_name": value.course_name,
        "membership_status_label": value.membership_status_label,
        "subjects": [
            {"subject_id": subject.subject_id, "subject_name": subject.subject_name}
            for subject in _ordered_subjects(value)
        ],
        "cross_topics": [
            {"cross_topic_key": item.cross_topic_key, "label": item.label}
            for item in value.cross_topics
        ],
    }


def _evidence_preparation(
    value: LearningConferencePreparationViewModel,
    draft: LearningConferenceDraftViewModel,
) -> JsonObject:
    subjects = _ordered_subjects(value)
    return {
        "subjects": [
            {
                "subject_id": subject.subject_id,
                "subject_name": subject.subject_name,
                "competencies": [
                    {
                        "competency_id": item.competency_id,
                        "learning_area": item.learning_area,
                        "competency_group": item.competency_group,
                        "competency_text": item.competency_text,
                        "documentation_state": item.documentation_state,
                        "observed_proposal": item.observed_proposal,
                        "confirmed_rating": item.confirmed_rating,
                        "historical": item.historical,
                        "selectable": item.selectable,
                        "observation_dates": list(item.observation_dates),
                        "has_current_confirmation": item.has_current_confirmation,
                    }
                    for item in sorted(
                        subject.competencies,
                        key=lambda item: (item.sort_order, item.competency_id),
                    )
                ],
            }
            for subject in subjects
        ],
        "evidence": [
            {
                "observation_id": item.observation_id,
                "date_text": item.date_text,
                "subject_name": item.subject_name,
                "context": item.context,
                "note": item.note,
                "competency_ids": list(item.competency_ids),
                "is_quick_observation": item.is_quick_observation,
            }
            for item in value.evidence
        ],
        "unavailable_observation_ids": list(draft.unavailable_observation_ids),
    }


def _draft(value: LearningConferenceDraftViewModel) -> JsonObject:
    result: JsonObject = {
        field: getattr(value, field)
        for field in LearningConferenceHtmlBridge._TEXT_FIELDS
    }
    result.update(
        {
            field: _date_value(getattr(value, field))
            for field in LearningConferenceHtmlBridge._DATE_FIELDS
        }
    )
    result.update(
        {
            "subject_ids": list(value.subject_ids),
            "cross_topic_keys": list(value.cross_topic_keys),
            "competency_ids": list(value.competency_ids),
            "observation_ids": list(value.observation_ids),
            "chart_types": list(value.chart_types),
            "has_persistent_id": bool(value.learning_conference_draft_id),
        }
    )
    return result


def _revision_status(
    value: LearningConferenceRevisionStatusViewModel | None,
    artifacts: dict[str, LearningConferencePdfArtifactViewModel],
) -> JsonObject | None:
    if value is None:
        return None
    return {
        "has_completion": value.has_completion,
        "status_label": value.status_label,
        "draft_changed": value.draft_changed,
        "hash_valid": value.hash_valid,
        "revisions": [
            {
                "revision_id": item.learning_conference_revision_id,
                "revision_number": item.revision_number,
                "status_label": item.status_label,
                "completed_at_text": item.completed_at_text,
                "completed_by_display_name": item.completed_by_display_name,
                "artifact": _artifact(
                    artifacts.get(item.learning_conference_revision_id)
                ),
            }
            for item in value.revisions
        ],
    }


def _artifact(value: LearningConferencePdfArtifactViewModel | None) -> JsonObject | None:
    if value is None:
        return None
    return {
        "artifact_id": value.learning_conference_pdf_artifact_id,
        "file_name": value.file_name,
        "created_at": value.created_at,
    }


def _date_value(value: date | None) -> str:
    return "" if value is None else value.isoformat()


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
