"""Explicit report-only QWebChannel facade over existing Python contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import json
from typing import Callable

from PySide6.QtCore import QObject, Signal, Slot

from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportChartSelectionViewModel,
    LearningReportDraftViewModel,
    LearningReportFinalizationPreviewViewModel,
    LearningReportPdfArtifactViewModel,
    LearningReportPreparationViewModel,
    LearningReportRevisionStatusViewModel,
    LearningReportRevisionViewModel,
    LearningReportSubjectDraftViewModel,
)


@dataclass
class LearningReportHtmlSession:
    preparation: LearningReportPreparationViewModel
    draft: LearningReportDraftViewModel
    revision_status: LearningReportRevisionStatusViewModel | None = None
    artifacts_by_revision_id: dict[str, LearningReportPdfArtifactViewModel] | None = None
    save_draft: Callable[[LearningReportDraftViewModel], LearningReportDraftViewModel] | None = None
    prepare_finalization: Callable[[str], LearningReportFinalizationPreviewViewModel] | None = None
    finalize_report: Callable[[str, str], LearningReportRevisionStatusViewModel] | None = None
    finalization_error_message: Callable[[Exception], str] | None = None
    refresh_revision_status: Callable[[str], LearningReportRevisionStatusViewModel] | None = None
    load_revision: Callable[[str], LearningReportRevisionViewModel | None] | None = None
    load_final_artifact: Callable[[str], LearningReportPdfArtifactViewModel | None] | None = None
    show_final_pdf: Callable[[str], None] | None = None


class LearningReportHtmlBridge(QObject):
    stateChanged = Signal(str)
    operationFinished = Signal(str)

    _HEADER_FIELDS = frozenset({"teacher_name", "period_start", "period_end"})
    _SUBJECT_FIELDS = {
        "strengths": "strengths_text",
        "development": "development_text",
        "support": "support_needs_text",
        "goals": "next_goals_text",
    }
    _CHART_TYPES = frozenset(
        {"documentation_coverage", "competency_timeline", "observation_timeline"}
    )

    def __init__(self, session: LearningReportHtmlSession, parent: QObject | None = None) -> None:
        super().__init__(parent)
        if not session.draft.report_draft_id:
            raise ValueError("report_html_draft_id_required")
        self.session = session
        self._baseline = session.draft
        self._pending = False
        self._prepared: LearningReportFinalizationPreviewViewModel | None = None
        self._sync_token = 0

    @property
    def is_dirty(self) -> bool:
        return self.session.draft != self._baseline

    @property
    def operation_pending(self) -> bool:
        return self._pending

    @property
    def sync_token(self) -> int:
        return self._sync_token

    @Slot(result=str)
    def initialState(self) -> str:  # noqa: N802
        return _dump(self._state())

    @Slot(result=str)
    def loadEvidenceState(self) -> str:  # noqa: N802
        return _dump(_evidence(self.session.preparation, self.session.draft))

    @Slot(str, str, result=str)
    def updateHeaderField(self, field: str, value: str) -> str:  # noqa: N802
        if field not in self._HEADER_FIELDS:
            return self._error("field_not_allowed")
        if field == "teacher_name":
            parsed: object = value
        else:
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                return self._error("date_invalid", "Bitte gib ein gültiges Datum ein.")
        draft = replace(self.session.draft, **{field: parsed})
        if draft.period_end <= draft.period_start:
            return self._error("period_invalid", "Das Ende muss nach dem Beginn liegen.")
        self.session.draft = draft
        return self._changed("draft_updated")

    @Slot(str, result=str)
    def updateOverallText(self, value: str) -> str:  # noqa: N802
        self.session.draft = replace(self.session.draft, overall_text=value)
        return self._changed("draft_updated")

    @Slot(str, str, str, result=str)
    def updateSubjectText(self, subject_id: str, field: str, value: str) -> str:  # noqa: N802
        attribute = self._SUBJECT_FIELDS.get(field)
        if not self._known_subject(subject_id) or attribute is None:
            return self._error("subject_field_not_allowed")
        subjects = list(self.session.draft.subjects)
        index = next((i for i, item in enumerate(subjects) if item.subject_id == subject_id), -1)
        if index < 0:
            return self._error("subject_not_selected")
        subjects[index] = replace(subjects[index], **{attribute: value})
        self.session.draft = replace(self.session.draft, subjects=tuple(subjects))
        return self._changed("draft_updated")

    @Slot(str, str, bool, result=str)
    def setSelection(self, kind: str, item_id: str, selected: bool) -> str:  # noqa: N802
        if kind == "subject":
            return self._set_subject(item_id, selected)
        if kind == "competency":
            return self._set_id_selection("competency_ids", item_id, selected)
        if kind == "observation":
            return self._set_id_selection("observation_ids", item_id, selected)
        return self._error("selection_not_allowed")

    @Slot(str, str, bool, result=str)
    def setChartSelection(self, subject_id: str, chart_type: str, selected: bool) -> str:  # noqa: N802
        if not self._known_subject(subject_id) or chart_type not in self._CHART_TYPES:
            return self._error("chart_not_allowed")
        if subject_id not in self.session.draft.selected_subject_ids:
            return self._error("subject_not_selected")
        values = list(self.session.draft.chart_selections)
        key = (subject_id, chart_type)
        values = [item for item in values if (item.subject_id, item.chart_type) != key]
        if selected:
            values.append(LearningReportChartSelectionViewModel(*key))
        self.session.draft = replace(
            self.session.draft,
            chart_selections=tuple(sorted(values, key=lambda item: (item.subject_id, item.chart_type))),
        )
        return self._changed("draft_updated")

    @Slot(result=str)
    def saveReportDraft(self) -> str:  # noqa: N802
        callback = self.session.save_draft
        if callback is None or self._pending:
            return self._error("save_unavailable" if callback is None else "operation_in_progress")
        self._pending = True
        try:
            saved = callback(self.session.draft)
        except Exception:
            return self._error("save_failed", "Der Berichtsentwurf konnte nicht gespeichert werden.")
        finally:
            self._pending = False
        self.session.draft = saved
        self._baseline = saved
        self._refresh_status()
        return self._changed("draft_saved")

    @Slot(result=str)
    def prepareFinalization(self) -> str:  # noqa: N802
        if self.is_dirty:
            saved = json.loads(self.saveReportDraft())
            if not saved.get("ok"):
                return _dump(saved)
        callback = self.session.prepare_finalization
        if callback is None or self._pending:
            return self._error("finalization_unavailable")
        self._pending = True
        try:
            self._prepared = callback(self.session.draft.report_draft_id)
        except Exception as error:
            return self._error("finalization_not_ready", self._finalization_error_message(error))
        finally:
            self._pending = False
        result = {"ok": True, "code": "finalization_prepared", "preview": _finalization(self._prepared)}
        self.operationFinished.emit(_dump(result))
        return _dump(result)

    @Slot(str, bool, result=str)
    def confirmFinalization(self, responsible_name: str, acknowledged: bool) -> str:  # noqa: N802
        callback = self.session.finalize_report
        if callback is None or self._prepared is None or self._pending:
            return self._error("finalization_unavailable")
        name = responsible_name.strip()
        if not acknowledged or not name:
            return self._error("confirmation_required", "Bitte bestätige die Finalisierung ausdrücklich.")
        self._pending = True
        try:
            self.session.revision_status = callback(self.session.draft.report_draft_id, name)
        except Exception as error:
            return self._error("finalization_failed", self._finalization_error_message(error))
        finally:
            self._pending = False
        self._prepared = None
        self._refresh_artifacts()
        return self._changed("report_finalized")

    @Slot(str, result=str)
    def openRevision(self, revision_id: str) -> str:  # noqa: N802
        known = {item.learning_report_revision_id for item in self._history()}
        if revision_id not in known or self.session.load_revision is None:
            return self._error("revision_unavailable")
        try:
            revision = self.session.load_revision(revision_id)
        except Exception:
            revision = None
        if revision is None:
            return self._error("revision_unavailable")
        return _dump({"ok": True, "code": "revision_loaded", "revision": _revision(revision)})

    @Slot(str, result=str)
    def showFinalPdf(self, artifact_id: str) -> str:  # noqa: N802
        known = {
            item.learning_report_pdf_artifact_id
            for item in (self.session.artifacts_by_revision_id or {}).values()
        }
        if artifact_id not in known:
            return self._error("final_pdf_unavailable")
        if self.session.show_final_pdf is None:
            return self._error("final_pdf_viewer_blocked", "Die sichere Anzeige des finalen PDFs ist technisch noch nicht freigegeben.")
        self.session.show_final_pdf(artifact_id)
        return self._ok("final_pdf_open_requested")

    def _known_subject(self, subject_id: str) -> bool:
        return any(item.subject_id == subject_id for item in self.session.preparation.subjects)

    def _set_subject(self, subject_id: str, selected: bool) -> str:
        if not self._known_subject(subject_id):
            return self._error("selection_unknown")
        subjects = list(self.session.draft.subjects)
        present = any(item.subject_id == subject_id for item in subjects)
        if selected and not present:
            subjects.append(LearningReportSubjectDraftViewModel(subject_id))
        elif not selected and present:
            subjects = [item for item in subjects if item.subject_id != subject_id]
            subject = next(item for item in self.session.preparation.subjects if item.subject_id == subject_id)
            competency_ids = {item.competency_id for item in subject.competencies}
            observation_ids = {item.observation_id for item in subject.evidence}
            self.session.draft = replace(
                self.session.draft,
                competency_ids=tuple(i for i in self.session.draft.competency_ids if i not in competency_ids),
                observation_ids=tuple(i for i in self.session.draft.observation_ids if i not in observation_ids),
                chart_selections=tuple(i for i in self.session.draft.chart_selections if i.subject_id != subject_id),
            )
        self.session.draft = replace(self.session.draft, subjects=tuple(subjects))
        return self._changed("draft_updated")

    def _set_id_selection(self, attribute: str, item_id: str, selected: bool) -> str:
        known = self._known_ids(attribute)
        if item_id not in known:
            return self._error("selection_unknown")
        selected_subjects = set(self.session.draft.selected_subject_ids)
        if selected and attribute == "competency_ids":
            owner = next(
                (
                    subject.subject_id
                    for subject in self.session.preparation.subjects
                    for item in subject.competencies
                    if item.competency_id == item_id
                ),
                "",
            )
            if owner not in selected_subjects:
                return self._error("subject_not_selected")
        if selected and attribute == "observation_ids" and item_id not in self.session.draft.unavailable_observation_ids:
            candidates = [
                item
                for subject in self.session.preparation.subjects
                if subject.subject_id in selected_subjects
                for item in subject.evidence
                if item.observation_id == item_id
            ]
            if not candidates or not any(
                self.session.draft.period_start <= item.observed_on <= self.session.draft.period_end
                for item in candidates
            ):
                return self._error("observation_not_available")
            selected_competencies = set(self.session.draft.competency_ids)
            if not any(selected_competencies.intersection(item.competency_ids) for item in candidates):
                return self._error("observation_not_available")
        values = list(getattr(self.session.draft, attribute))
        if selected and item_id not in values:
            values.append(item_id)
        elif not selected and item_id in values:
            values.remove(item_id)
        self.session.draft = replace(self.session.draft, **{attribute: tuple(sorted(values))})
        return self._changed("draft_updated")

    def _known_ids(self, attribute: str) -> set[str]:
        if attribute == "competency_ids":
            return {
                item.competency_id
                for subject in self.session.preparation.subjects
                for item in subject.competencies
                if item.selectable or item.competency_id in self.session.draft.competency_ids
            }
        return {
            item.observation_id
            for subject in self.session.preparation.subjects
            for item in subject.evidence
        } | set(self.session.draft.unavailable_observation_ids)

    def _history(self):
        return self.session.revision_status.history if self.session.revision_status else ()

    def _finalization_error_message(self, error: Exception) -> str:
        projector = self.session.finalization_error_message
        if projector is not None:
            try:
                return projector(error)
            except Exception:
                pass
        return "Der Bericht ist noch nicht bereit für die Finalisierung."

    def _refresh_status(self) -> None:
        callback = self.session.refresh_revision_status
        if callback is not None:
            try:
                self.session.revision_status = callback(self.session.draft.report_draft_id)
            except Exception:
                self.session.revision_status = None
        self._refresh_artifacts()

    def _refresh_artifacts(self) -> None:
        loader = self.session.load_final_artifact
        artifacts: dict[str, LearningReportPdfArtifactViewModel] = {}
        if loader is not None:
            for item in self._history():
                try:
                    artifact = loader(item.learning_report_revision_id)
                except Exception:
                    artifact = None
                if artifact is not None:
                    artifacts[item.learning_report_revision_id] = artifact
        self.session.artifacts_by_revision_id = artifacts

    def _state(self) -> dict[str, object]:
        return {
            "surface": "report",
            "preparation": _preparation(self.session.preparation),
            "draft": _draft(self.session.draft),
            "revision_status": _revision_status(self.session.revision_status, self.session.artifacts_by_revision_id or {}),
            "dirty": self.is_dirty,
            "sync_token": self._sync_token,
        }

    def _changed(self, code: str) -> str:
        self._sync_token += 1
        self.stateChanged.emit(_dump(self._state()))
        return self._ok(code)

    def _ok(self, code: str) -> str:
        payload = _dump({"ok": True, "code": code})
        self.operationFinished.emit(payload)
        return payload

    def _error(self, code: str, message: str | None = None) -> str:
        result: dict[str, object] = {"ok": False, "code": code}
        if message:
            result["message"] = message
        payload = _dump(result)
        self.operationFinished.emit(payload)
        return payload


def _preparation(value: LearningReportPreparationViewModel) -> dict[str, object]:
    return {"student_name": value.student_name, "group_name": value.group_name, "course_name": value.course_name, "subjects": [{"subject_id": s.subject_id, "subject_name": s.subject_name} for s in value.subjects]}


def _draft(value: LearningReportDraftViewModel) -> dict[str, object]:
    return {
        "period_start": value.period_start.isoformat(), "period_end": value.period_end.isoformat(),
        "teacher_name": value.teacher_name, "overall_text": value.overall_text,
        "report_type_label": "Lernentwicklungsbericht", "status": value.status,
        "subjects": [{"subject_id": s.subject_id, "strengths": s.strengths_text, "development": s.development_text, "support": s.support_needs_text, "goals": s.next_goals_text} for s in value.subjects],
        "competency_ids": list(value.competency_ids), "observation_ids": list(value.observation_ids),
        "charts": [{"subject_id": c.subject_id, "chart_type": c.chart_type} for c in value.chart_selections],
    }


def _evidence(value: LearningReportPreparationViewModel, draft: LearningReportDraftViewModel) -> dict[str, object]:
    return {"subjects": [{"subject_id": s.subject_id, "subject_name": s.subject_name, "competencies": [{"competency_id": c.competency_id, "area": c.learning_area, "topic": c.competency_group, "text": c.competency_text, "selectable": c.selectable, "historical": c.historical, "sort_order": c.sort_order} for c in s.competencies], "evidence": [{"observation_id": e.observation_id, "date": e.observed_on.isoformat(), "context": e.context, "note": e.note, "competency_ids": list(e.competency_ids)} for e in s.evidence]} for s in value.subjects], "unavailable_observation_ids": list(draft.unavailable_observation_ids)}


def _revision_status(value, artifacts) -> dict[str, object] | None:
    if value is None:
        return None
    return {"state": value.state, "badge_text": value.badge_text, "hint_text": value.hint_text, "history": [{"revision_id": i.learning_report_revision_id, "number": i.revision_number, "status_label": i.status_label, "finalized_at": i.finalized_at, "finalized_by": i.finalized_by_display_name, "period": i.period_label, "artifact_id": artifacts[i.learning_report_revision_id].learning_report_pdf_artifact_id if i.learning_report_revision_id in artifacts else ""} for i in value.history]}


def _finalization(value: LearningReportFinalizationPreviewViewModel) -> dict[str, object]:
    return {"student": value.student_display_name, "report_type": value.report_type_label, "period": value.period_label, "subjects": list(value.subject_names), "competencies": value.competency_count, "observations": value.observation_count, "revision_number": value.revision_number, "responsible": value.suggested_responsible_display_name}


def _revision(value: LearningReportRevisionViewModel) -> dict[str, object]:
    return {"number": value.revision_number, "status_label": value.status_label, "student": value.student_display_name, "group": value.group_name, "course": value.course_name, "report_type": value.report_type_label, "period": value.period_label, "finalized_at": value.finalized_at, "finalized_by": value.finalized_by_display_name, "overall_text": value.overall_text, "subjects": [{"name": s.subject_name, "strengths": s.strengths_text, "development": s.development_text, "support": s.support_needs_text, "goals": s.next_goals_text, "competencies": [{"area": c.learning_area, "topic": c.competency_group, "text": c.competency_text, "historical": c.historical_reference} for c in s.competencies], "observations": [{"date": o.observed_on, "context": o.context, "content": o.content} for o in s.observations], "charts": [{"title": c.title, "summary": c.summary, "details": list(c.details)} for c in s.charts]} for s in value.subjects]}


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
