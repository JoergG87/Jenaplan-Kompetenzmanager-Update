"""Display-ready report overview projections without UI or persistence logic."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import TypeVar

from src.core.learning_conference import (
    COMPLETED_REVISION_STATUS,
    LearningConferenceRevisionState,
)
from src.core.learning_report import (
    FINALIZED_REVISION_STATUS,
    LearningReportRevisionState,
)
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceDraftViewModel,
)
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportDraftViewModel,
    LearningReportPreparationViewModel,
)
from src.desktop_app.view_models.observation_view_model import (
    COMPETENCY_PRESENTATION_GROUP_CROSS_CURRICULAR,
    competency_presentation_group,
)

DraftViewModel = TypeVar("DraftViewModel")
_UNSET = object()
_CURRENTLY_UNAVAILABLE_CATALOG_STATUSES = frozenset(
    {"historical", "inactive", "deactivated", "retired", "deleted", "archived"}
)


@dataclass(frozen=True)
class ReportOverviewActionViewModel:
    """One existing navigation action exposed without process inference."""

    action_key: str
    label: str
    target_id: str = ""
    subject_id: str = ""


@dataclass(frozen=True)
class ReportStatusCardViewModel:
    """Display contract for the report status card."""

    state: str
    status_label: str
    period_label: str
    revision_label: str
    last_changed_label: str
    hint_text: str
    primary_action: ReportOverviewActionViewModel


@dataclass(frozen=True)
class LearningConferenceStatusCardViewModel:
    """Display contract built only from existing LEG projections."""

    state: str
    status_label: str
    period_label: str
    revision_label: str
    last_changed_label: str
    hint_text: str
    primary_action: ReportOverviewActionViewModel | None


@dataclass(frozen=True)
class ReportNextStepViewModel:
    """One concrete existing action, never a pedagogical recommendation."""

    title: str
    detail: str
    action: ReportOverviewActionViewModel


@dataclass(frozen=True)
class ReportHistoryItemViewModel:
    """Common display row for one separately sourced report or LEG item."""

    document_type: str
    period_label: str
    version_label: str
    status_label: str
    activity_label: str
    action: ReportOverviewActionViewModel
    activity_sort_key: str


@dataclass(frozen=True)
class ReportSubjectEntryViewModel:
    """Safe subject navigation without Paket-2 counting semantics."""

    subject_id: str
    subject_name: str
    action: ReportOverviewActionViewModel
    documented_count: int = 0
    current_count: int = 0
    observation_count: int = 0


@dataclass(frozen=True)
class ReportOverviewTimelineEventViewModel:
    """One neutral, display-ready Phase-2 documentation event."""

    event_type: str
    source_identity: tuple[str, ...]
    occurred_on: date
    date_label: str
    title: str
    detail_text: str
    accessible_name: str
    action: ReportOverviewActionViewModel | None = None


@dataclass(frozen=True)
class ReportOverviewSubjectDocumentationViewModel:
    """Absolute current documentation identities for one canonical subject."""

    subject_id: str
    subject_name: str
    competency_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    competency_count_text: str
    observation_count_text: str
    accessible_name: str
    evidence_action: ReportOverviewActionViewModel
    prepare_action: ReportOverviewActionViewModel
    confirmation_count_text: str = ""

    @property
    def is_cross_curricular(self) -> bool:
        """Keep the section decision at the presentation boundary."""
        return (
            competency_presentation_group(self.subject_id)
            == COMPETENCY_PRESENTATION_GROUP_CROSS_CURRICULAR
        )


@dataclass(frozen=True)
class ReportOverviewProjectionWarningViewModel:
    """Neutral display state for one incomplete Phase-2 source projection."""

    warning_key: str
    text: str = "Dokumentationsdaten konnten nicht vollständig gelesen werden."
    accessible_name: str = (
        "Hinweis: Dokumentationsdaten konnten nicht vollständig gelesen werden."
    )


@dataclass(frozen=True)
class ReportOverviewViewModel:
    """Complete display projection for the report overview."""

    report_status: ReportStatusCardViewModel
    learning_conference_status: LearningConferenceStatusCardViewModel
    next_steps: tuple[ReportNextStepViewModel, ...]
    history: tuple[ReportHistoryItemViewModel, ...]
    subjects: tuple[ReportSubjectEntryViewModel, ...]
    selected_report_draft_id: str
    report_period_label: str
    report_period_start_label: str
    report_period_end_label: str
    report_content_available: bool
    workspace_action: ReportOverviewActionViewModel
    timeline_events: tuple[ReportOverviewTimelineEventViewModel, ...] = ()
    subject_documentation: tuple[
        ReportOverviewSubjectDocumentationViewModel,
        ...,
    ] = ()
    projection_warnings: tuple[
        ReportOverviewProjectionWarningViewModel,
        ...,
    ] = ()


def empty_report_overview() -> ReportOverviewViewModel:
    """Return the safe profile state before adapter data is available."""
    create = ReportOverviewActionViewModel("create_report", "Bericht erstellen")
    begin_learning_conference = ReportOverviewActionViewModel(
        "select_learning_conference",
        "LEG beginnen",
    )
    return ReportOverviewViewModel(
        report_status=ReportStatusCardViewModel(
            "no_draft",
            "Kein Entwurf vorhanden",
            "Kein Berichtszeitraum gewählt",
            "Keine Revision",
            "Noch keine Änderung",
            "Erstelle einen Berichtsentwurf, um einen Zeitraum festzulegen.",
            create,
        ),
        learning_conference_status=LearningConferenceStatusCardViewModel(
            "no_draft",
            "Kein LEG vorhanden",
            "Kein LEG-Zeitraum",
            "Keine Revision",
            "Noch keine Änderung",
            "Für dieses Kind ist noch kein LEG-Arbeitsstand vorhanden.",
            begin_learning_conference,
        ),
        next_steps=(
            ReportNextStepViewModel(
                "Bericht erstellen",
                "Öffnet den bestehenden Erstellungsweg.",
                create,
            ),
            ReportNextStepViewModel(
                "LEG beginnen",
                "Öffnet den bestehenden, getrennten LEG-Arbeitsraum.",
                begin_learning_conference,
            ),
        ),
        history=(),
        subjects=(),
        selected_report_draft_id="",
        report_period_label="Kein Berichtszeitraum gewählt",
        report_period_start_label="",
        report_period_end_label="",
        report_content_available=False,
        workspace_action=create,
    )


def build_report_overview(
    report_drafts: Sequence[LearningReportDraftViewModel],
    report_states: Mapping[str, LearningReportRevisionState | Exception],
    learning_conference_drafts: Sequence[LearningConferenceDraftViewModel],
    learning_conference_states: Mapping[
        str,
        LearningConferenceRevisionState | Exception,
    ],
    preparation: LearningReportPreparationViewModel | None,
    *,
    report_list_error: Exception | None = None,
    learning_conference_list_error: Exception | None = None,
    report_revision_errors: frozenset[str] = frozenset(),
    learning_conference_revision_periods: Mapping[
        str,
        tuple[str, str, str],
    ] | None = None,
    learning_conference_revision_errors: frozenset[str] = frozenset(),
    selected_report_draft_id: str = "",
    selected_learning_conference_draft_id: str = "",
    phase2_period_start: object = _UNSET,
    phase2_period_end: object = _UNSET,
    phase2_observations: Sequence[Mapping[str, object]] = (),
    phase2_report_revisions: Sequence[Mapping[str, object]] = (),
    phase2_learning_conference_revisions: Sequence[Mapping[str, object]] = (),
    phase2_confirmations: Sequence[Mapping[str, object]] = (),
    phase2_subjects: Sequence[Mapping[str, object]] = (),
    phase2_source_errors: Sequence[str] = (),
) -> ReportOverviewViewModel:
    """Compose existing report and LEG reads only at the display boundary."""
    report_drafts = tuple(report_drafts)
    learning_conference_drafts = tuple(learning_conference_drafts)
    selected_report = _strict_selected_draft(
        report_drafts,
        selected_report_draft_id,
        "report_draft_id",
    )
    selected_learning_conference = _selected_draft(
        learning_conference_drafts,
        selected_learning_conference_draft_id,
        "learning_conference_draft_id",
    )
    report_status = (
        _unreadable_report_status()
        if report_list_error is not None
        else _report_status_card(
            report_drafts,
            report_states,
            selected_report,
            report_revision_errors,
        )
    )
    learning_conference_status = (
        _unreadable_learning_conference_status()
        if learning_conference_list_error is not None
        else _learning_conference_status_card(
            learning_conference_drafts,
            learning_conference_states,
            selected_learning_conference,
            learning_conference_revision_errors,
        )
    )
    subjects = tuple(
        ReportSubjectEntryViewModel(
            subject.subject_id,
            subject.subject_name,
            ReportOverviewActionViewModel(
                "prepare_subject",
                "Bericht vorbereiten",
                selected_report.report_draft_id if selected_report else "",
                subject.subject_id,
            ),
            subject.documented_count,
            subject.current_count,
            len(subject.evidence),
        )
        for subject in (preparation.subjects if preparation is not None else ())
    )
    history = _history(
        report_drafts,
        report_states,
        learning_conference_drafts,
        learning_conference_states,
        report_revision_errors,
        learning_conference_revision_periods or {},
        learning_conference_revision_errors,
    )
    next_steps = _next_steps(
        report_drafts,
        report_states,
        learning_conference_drafts,
        selected_report,
        selected_learning_conference,
        report_list_error=report_list_error,
        learning_conference_list_error=learning_conference_list_error,
    )
    if selected_report is None:
        period_label = "Kein Berichtszeitraum gewählt"
        period_start_label = ""
        period_end_label = ""
        workspace_action = report_status.primary_action
    else:
        period_label = _period_label(
            selected_report.period_start,
            selected_report.period_end,
        )
        period_start_label = _date_label(selected_report.period_start)
        period_end_label = _date_label(selected_report.period_end)
        workspace_action = ReportOverviewActionViewModel(
            "open_report",
            "Bericht öffnen",
            selected_report.report_draft_id,
        )
    phase2_timeline: tuple[ReportOverviewTimelineEventViewModel, ...] = ()
    phase2_subject_documentation: tuple[
        ReportOverviewSubjectDocumentationViewModel,
        ...,
    ] = ()
    phase2_warnings: tuple[ReportOverviewProjectionWarningViewModel, ...] = ()
    if phase2_period_start is not _UNSET or phase2_period_end is not _UNSET:
        resolved_phase2_start = (
            None if phase2_period_start is _UNSET else phase2_period_start
        )
        resolved_phase2_end = (
            None if phase2_period_end is _UNSET else phase2_period_end
        )
        (
            phase2_timeline,
            phase2_subject_documentation,
            phase2_warnings,
        ) = _phase2_evidence_projection(
            resolved_phase2_start,
            resolved_phase2_end,
            observations=phase2_observations,
            report_revisions=phase2_report_revisions,
            learning_conference_revisions=(
                phase2_learning_conference_revisions
            ),
            confirmations=phase2_confirmations,
            subjects=phase2_subjects,
            source_errors=phase2_source_errors,
            selected_report_draft_id=(
                selected_report.report_draft_id if selected_report else ""
            ),
        )
    return ReportOverviewViewModel(
        report_status=report_status,
        learning_conference_status=learning_conference_status,
        next_steps=next_steps,
        history=history,
        subjects=subjects,
        selected_report_draft_id=(
            selected_report.report_draft_id if selected_report else ""
        ),
        report_period_label=period_label,
        report_period_start_label=period_start_label,
        report_period_end_label=period_end_label,
        report_content_available=selected_report is not None,
        workspace_action=workspace_action,
        timeline_events=phase2_timeline,
        subject_documentation=phase2_subject_documentation,
        projection_warnings=phase2_warnings,
    )


def _report_status_card(
    drafts: tuple[LearningReportDraftViewModel, ...],
    states: Mapping[str, LearningReportRevisionState | Exception],
    selected: LearningReportDraftViewModel | None,
    revision_errors: frozenset[str],
) -> ReportStatusCardViewModel:
    if not drafts:
        return empty_report_overview().report_status
    if selected is None:
        return ReportStatusCardViewModel(
            "multiple_drafts",
            (
                f"{len(drafts)} Entwürfe vorhanden"
                if len(drafts) > 1
                else "Entwurf vorhanden"
            ),
            "Berichtszeitraum erst nach Auswahl",
            "Keine Revision gewählt",
            _latest_update_label(item.updated_at for item in drafts),
            "Wähle einen Berichtsentwurf bewusst aus. Zuletzt bearbeitet sortiert nur die Auswahl.",
            ReportOverviewActionViewModel("select_report", "Bericht auswählen"),
        )
    assert selected is not None
    state = states.get(selected.report_draft_id)
    period = _period_label(selected.period_start, selected.period_end)
    last_changed = _timestamp_label(selected.updated_at)
    open_action = ReportOverviewActionViewModel(
        "open_report",
        "Bericht öffnen",
        selected.report_draft_id,
    )
    if isinstance(state, Exception) or state is None:
        card = ReportStatusCardViewModel(
            "integrity_error",
            "Berichtstand nicht lesbar",
            period,
            "Revision nicht sicher ermittelt",
            last_changed,
            "Der Berichtstand konnte nicht vollständig geprüft werden.",
            open_action,
        )
    else:
        current = state.current_revision
        if current is None:
            card = ReportStatusCardViewModel(
                "draft_without_revision",
                "Entwurf ohne Revision",
                period,
                "Keine Revision",
                last_changed,
                "Der gewählte Bericht ist bearbeitbar und noch nicht finalisiert.",
                open_action,
            )
        elif (
            not state.current_snapshot_hash_valid
            or current.learning_report_revision_id in revision_errors
        ):
            card = ReportStatusCardViewModel(
                "integrity_error",
                "Integritätsprüfung fehlgeschlagen",
                period,
                f"Revision {current.revision_number}",
                last_changed,
                "Die aktuelle Berichtrevision konnte nicht sicher verifiziert werden.",
                open_action,
            )
        elif state.comparison_error:
            card = ReportStatusCardViewModel(
                "draft_check_required",
                "Entwurf prüfen",
                period,
                f"Aktuelle Revision {current.revision_number}",
                last_changed,
                "Der Entwurf kann erst nach Prüfung seiner Inhalte wieder "
                "finalisiert werden. Die vorhandene Revision bleibt unverändert.",
                open_action,
            )
        elif state.draft_changed:
            card = ReportStatusCardViewModel(
                "draft_changed",
                "Entwurf seit Revision verändert",
                period,
                f"Aktuelle Revision {current.revision_number}",
                last_changed,
                (
                    "Die unveränderliche Revision bleibt erhalten; der Entwurf "
                    "enthält neuere Änderungen."
                ),
                open_action,
            )
        else:
            card = ReportStatusCardViewModel(
                "finalized",
                f"Finalisiert · Revision {current.revision_number}",
                period,
                f"Aktuelle Revision {current.revision_number}",
                last_changed,
                "Der gespeicherte Entwurf entspricht der aktuellen finalen Revision.",
                open_action,
            )
    if len(drafts) > 1:
        return replace(
            card,
            state="multiple_drafts_selected",
            status_label=f"{card.status_label} · bewusst gewählt",
            hint_text=f"{len(drafts)} Berichtsentwürfe vorhanden. {card.hint_text}",
            primary_action=ReportOverviewActionViewModel(
                "select_report",
                "Bericht auswählen",
            ),
        )
    return card


def _unreadable_report_status() -> ReportStatusCardViewModel:
    return ReportStatusCardViewModel(
        "integrity_error",
        "Berichtstände nicht lesbar",
        "Berichtszeitraum nicht sicher ermittelt",
        "Revision nicht sicher ermittelt",
        "Letzte Änderung nicht lesbar",
        "Die vorhandenen Berichtstände konnten nicht vollständig geprüft werden.",
        ReportOverviewActionViewModel("select_report", "Bericht auswählen"),
    )


def _learning_conference_status_card(
    drafts: tuple[LearningConferenceDraftViewModel, ...],
    states: Mapping[str, LearningConferenceRevisionState | Exception],
    selected: LearningConferenceDraftViewModel | None,
    revision_errors: frozenset[str],
) -> LearningConferenceStatusCardViewModel:
    if not drafts:
        return empty_report_overview().learning_conference_status
    if len(drafts) > 1 and selected is None:
        periods = {
            (draft.period_start, draft.period_end)
            for draft in drafts
        }
        label = (
            "Mehrere LEG-Zeiträume"
            if len(periods) > 1
            else f"{len(drafts)} LEG-Entwürfe"
        )
        return LearningConferenceStatusCardViewModel(
            "multiple_drafts",
            label,
            "LEG-Zeitraum erst nach Auswahl",
            "Keine Revision gewählt",
            _latest_update_label(item.updated_at for item in drafts),
            "Wähle den LEG-Arbeitsstand bewusst aus.",
            ReportOverviewActionViewModel(
                "select_learning_conference",
                "LEG auswählen",
            ),
        )
    assert selected is not None
    draft = selected
    state = states.get(draft.learning_conference_draft_id)
    action = ReportOverviewActionViewModel(
        "open_learning_conference",
        "LEG öffnen",
        draft.learning_conference_draft_id,
    )
    period = _optional_period_label(
        draft.period_start,
        draft.period_end,
        draft.conference_date,
    )
    last_changed = _timestamp_label(draft.updated_at)
    if isinstance(state, Exception) or state is None:
        card = LearningConferenceStatusCardViewModel(
            "integrity_error",
            "LEG-Stand nicht lesbar",
            period,
            "Revision nicht sicher ermittelt",
            last_changed,
            "Der LEG-Stand konnte nicht vollständig geprüft werden.",
            action,
        )
    else:
        current = state.current_revision
        if current is None:
            card = LearningConferenceStatusCardViewModel(
                "draft",
                "LEG-Entwurf vorhanden",
                period,
                "Keine Revision",
                last_changed,
                "Der gewählte LEG-Arbeitsstand ist noch nicht abgeschlossen.",
                action,
            )
        elif (
            not state.current_snapshot_hash_valid
            or current.learning_conference_revision_id in revision_errors
        ):
            card = LearningConferenceStatusCardViewModel(
                "integrity_error",
                "Integritätsprüfung fehlgeschlagen",
                period,
                f"Revision {current.revision_number}",
                last_changed,
                "Die aktuelle LEG-Revision konnte nicht sicher verifiziert werden.",
                action,
            )
        elif state.comparison_error is not None:
            card = LearningConferenceStatusCardViewModel(
                "draft_check_required",
                "LEG-Entwurf prüfen",
                period,
                f"Aktuelle Revision {current.revision_number}",
                last_changed,
                "Der LEG-Entwurf kann erst nach Prüfung seiner Inhalte erneut "
                "abgeschlossen werden. Die vorhandene Revision bleibt unverändert.",
                action,
            )
        elif state.draft_changed:
            card = LearningConferenceStatusCardViewModel(
                "draft_changed",
                "Entwurf seit Abschluss geändert",
                period,
                f"Aktuelle Revision {current.revision_number}",
                last_changed,
                "Der abgeschlossene Stand bleibt unverändert erhalten.",
                action,
            )
        else:
            card = LearningConferenceStatusCardViewModel(
                "completed",
                f"Abgeschlossen · Revision {current.revision_number}",
                period,
                f"Aktuelle Revision {current.revision_number}",
                last_changed,
                "Der LEG-Arbeitsstand entspricht der aktuellen Abschlussrevision.",
                action,
            )
    if len(drafts) > 1:
        return replace(
            card,
            state="multiple_drafts_selected",
            status_label=f"{card.status_label} · bewusst gewählt",
            hint_text=f"{len(drafts)} LEG-Arbeitsstände vorhanden. {card.hint_text}",
            primary_action=ReportOverviewActionViewModel(
                "select_learning_conference",
                "LEG auswählen",
            ),
        )
    return card


def _unreadable_learning_conference_status() -> LearningConferenceStatusCardViewModel:
    return LearningConferenceStatusCardViewModel(
        "integrity_error",
        "LEG-Stände nicht lesbar",
        "LEG-Zeitraum nicht sicher ermittelt",
        "Revision nicht sicher ermittelt",
        "Letzte Änderung nicht lesbar",
        "Die vorhandenen LEG-Stände konnten nicht vollständig geprüft werden.",
        ReportOverviewActionViewModel(
            "select_learning_conference",
            "LEG auswählen",
        ),
    )


def _next_steps(
    report_drafts: tuple[LearningReportDraftViewModel, ...],
    report_states: Mapping[str, LearningReportRevisionState | Exception],
    learning_conference_drafts: tuple[LearningConferenceDraftViewModel, ...],
    selected_report: LearningReportDraftViewModel | None,
    selected_learning_conference: LearningConferenceDraftViewModel | None,
    *,
    report_list_error: Exception | None,
    learning_conference_list_error: Exception | None,
) -> tuple[ReportNextStepViewModel, ...]:
    result: list[ReportNextStepViewModel] = []
    if report_list_error is not None:
        action = ReportOverviewActionViewModel("select_report", "Bericht auswählen")
        result.append(ReportNextStepViewModel(
            "Berichtstände prüfen",
            "Öffnet die bestehende Auswahl; es wird kein Stand automatisch aktiviert.",
            action,
        ))
    elif not report_drafts:
        action = ReportOverviewActionViewModel("create_report", "Bericht erstellen")
        result.append(ReportNextStepViewModel(
            action.label,
            "Öffnet den bestehenden Zeitraum- und Erstellungsweg.",
            action,
        ))
    elif selected_report is None:
        action = ReportOverviewActionViewModel("select_report", "Bericht auswählen")
        result.append(ReportNextStepViewModel(
            action.label,
            "Vor jeder weiteren Berichtaktion zuerst einen Entwurf wählen.",
            action,
        ))
    else:
        assert selected_report is not None
        draft = selected_report
        state = report_states.get(draft.report_draft_id)
        continue_action = ReportOverviewActionViewModel(
            "open_report",
            "Vorhandenen Entwurf fortsetzen",
            draft.report_draft_id,
        )
        result.append(ReportNextStepViewModel(
            continue_action.label,
            "Öffnet den bestehenden Berichtarbeitsraum.",
            continue_action,
        ))
        if not isinstance(state, Exception) and state is not None:
            current = state.current_revision
            if current is None:
                final_action = ReportOverviewActionViewModel(
                    "finalize_report",
                    "Bericht finalisieren",
                    draft.report_draft_id,
                )
                result.append(ReportNextStepViewModel(
                    final_action.label,
                    "Öffnet den vorhandenen Finalisierungsbereich mit seinen Prüfungen.",
                    final_action,
                ))
            elif (
                state.draft_changed
                and state.current_snapshot_hash_valid
                and not state.comparison_error
            ):
                final_action = ReportOverviewActionViewModel(
                    "finalize_report",
                    "Neue Revision finalisieren",
                    draft.report_draft_id,
                )
                result.append(ReportNextStepViewModel(
                    final_action.label,
                    "Öffnet den vorhandenen Finalisierungsbereich mit seinen Prüfungen.",
                    final_action,
                ))
    if learning_conference_list_error is not None:
        action = ReportOverviewActionViewModel(
            "select_learning_conference",
            "LEG auswählen",
        )
        result.append(ReportNextStepViewModel(
            "LEG-Stände prüfen",
            "Öffnet die bestehende Auswahl ohne Berichtsdaten zu verwenden.",
            action,
        ))
    elif not learning_conference_drafts:
        action = ReportOverviewActionViewModel(
            "select_learning_conference",
            "LEG beginnen",
        )
        result.append(ReportNextStepViewModel(
            action.label,
            "Öffnet den bestehenden, getrennten LEG-Arbeitsraum.",
            action,
        ))
    else:
        if (
            len(learning_conference_drafts) > 1
            and selected_learning_conference is None
        ):
            action = ReportOverviewActionViewModel(
                "select_learning_conference",
                "LEG auswählen",
            )
        else:
            assert selected_learning_conference is not None
            action = ReportOverviewActionViewModel(
                "open_learning_conference",
                "LEG öffnen",
                selected_learning_conference.learning_conference_draft_id,
            )
        result.append(ReportNextStepViewModel(
            action.label,
            "Öffnet den bestehenden, getrennten LEG-Arbeitsraum.",
            action,
        ))
    return tuple(result)


def _history(
    report_drafts: tuple[LearningReportDraftViewModel, ...],
    report_states: Mapping[str, LearningReportRevisionState | Exception],
    learning_conference_drafts: tuple[LearningConferenceDraftViewModel, ...],
    learning_conference_states: Mapping[
        str,
        LearningConferenceRevisionState | Exception,
    ],
    report_revision_errors: frozenset[str],
    learning_conference_revision_periods: Mapping[str, tuple[str, str, str]],
    learning_conference_revision_errors: frozenset[str],
) -> tuple[ReportHistoryItemViewModel, ...]:
    items: list[ReportHistoryItemViewModel] = []
    for draft in report_drafts:
        period = _period_label(draft.period_start, draft.period_end)
        items.append(ReportHistoryItemViewModel(
            "Bericht",
            period,
            "Entwurf",
            "Bearbeitbar",
            _timestamp_label(draft.updated_at),
            ReportOverviewActionViewModel(
                "open_report",
                "Öffnen",
                draft.report_draft_id,
            ),
            draft.updated_at,
        ))
        state = report_states.get(draft.report_draft_id)
        if isinstance(state, LearningReportRevisionState):
            revision_period = (
                _iso_period_label(
                    state.report.period_start,
                    state.report.period_end,
                )
                if state.report is not None
                else period
            )
            for revision in state.revisions:
                status = (
                    "Aktuell"
                    if revision.status == FINALIZED_REVISION_STATUS
                    else "Ersetzt"
                )
                if revision.learning_report_revision_id in report_revision_errors:
                    status = "Integrität nicht bestätigt"
                elif (
                    revision.status == FINALIZED_REVISION_STATUS
                    and not state.current_snapshot_hash_valid
                ):
                    status = "Integrität nicht bestätigt"
                items.append(ReportHistoryItemViewModel(
                    "Bericht",
                    revision_period,
                    f"Revision {revision.revision_number}",
                    status,
                    _timestamp_label(revision.finalized_at),
                    ReportOverviewActionViewModel(
                        "open_report_revision",
                        "Öffnen",
                        revision.learning_report_revision_id,
                    ),
                    revision.finalized_at,
                ))
    for draft in learning_conference_drafts:
        period = _optional_period_label(
            draft.period_start,
            draft.period_end,
            draft.conference_date,
        )
        items.append(ReportHistoryItemViewModel(
            "LEG",
            period,
            "Entwurf",
            "Bearbeitbar",
            _timestamp_label(draft.updated_at),
            ReportOverviewActionViewModel(
                "open_learning_conference",
                "Öffnen",
                draft.learning_conference_draft_id,
            ),
            draft.updated_at,
        ))
        state = learning_conference_states.get(draft.learning_conference_draft_id)
        if isinstance(state, LearningConferenceRevisionState):
            for revision in state.revisions:
                revision_period_values = learning_conference_revision_periods.get(
                    revision.learning_conference_revision_id
                )
                revision_period = (
                    _iso_optional_leg_period_label(*revision_period_values)
                    if revision_period_values is not None
                    else "Zeitraum nicht sicher lesbar"
                )
                status = (
                    "Aktuell"
                    if revision.status == COMPLETED_REVISION_STATUS
                    else "Ersetzt"
                )
                if (
                    revision.learning_conference_revision_id
                    in learning_conference_revision_errors
                ):
                    status = "Integrität nicht bestätigt"
                elif (
                    revision.status == COMPLETED_REVISION_STATUS
                    and not state.current_snapshot_hash_valid
                ):
                    status = "Integrität nicht bestätigt"
                items.append(ReportHistoryItemViewModel(
                    "LEG",
                    revision_period,
                    f"Revision {revision.revision_number}",
                    status,
                    _timestamp_label(revision.completed_at),
                    ReportOverviewActionViewModel(
                        "open_learning_conference_revision",
                        "Öffnen",
                        revision.learning_conference_revision_id,
                    ),
                    revision.completed_at,
                ))
    return tuple(
        sorted(
            items,
            key=lambda item: (
                item.activity_sort_key,
                item.document_type,
                item.version_label,
            ),
            reverse=True,
        )
    )


def _phase2_evidence_projection(
    period_start_value: object,
    period_end_value: object,
    *,
    observations: Sequence[Mapping[str, object]],
    report_revisions: Sequence[Mapping[str, object]],
    learning_conference_revisions: Sequence[Mapping[str, object]],
    confirmations: Sequence[Mapping[str, object]],
    subjects: Sequence[Mapping[str, object]],
    source_errors: Sequence[str],
    selected_report_draft_id: str,
) -> tuple[
    tuple[ReportOverviewTimelineEventViewModel, ...],
    tuple[ReportOverviewSubjectDocumentationViewModel, ...],
    tuple[ReportOverviewProjectionWarningViewModel, ...],
]:
    """Build the deterministic Phase-2 display projection from read-only rows."""
    warning_keys = {
        f"source:{value.strip()}"
        for value in source_errors
        if isinstance(value, str) and value.strip()
    }
    period_start = _phase2_local_date(period_start_value)
    period_end = _phase2_local_date(period_end_value)
    if period_start is None:
        warning_keys.add("period_start_invalid")
    if period_end is None:
        warning_keys.add("period_end_invalid")
    if (
        period_start is not None
        and period_end is not None
        and period_end < period_start
    ):
        warning_keys.add("period_end_before_start")
    if (
        period_start is None
        or period_end is None
        or period_end < period_start
    ):
        return (), (), _phase2_warnings(warning_keys)

    canonical_subjects = _phase2_canonical_subjects(subjects)
    subject_names = {
        subject_id: subject_name
        for subject_id, subject_name in canonical_subjects
    }
    subject_order = {
        subject_id: index
        for index, (subject_id, _subject_name) in enumerate(canonical_subjects)
    }
    competency_ids_by_subject: dict[str, set[str]] = {
        subject_id: set()
        for subject_id, _subject_name in canonical_subjects
    }
    observation_ids_by_subject: dict[str, set[str]] = {
        subject_id: set()
        for subject_id, _subject_name in canonical_subjects
    }
    confirmed_competency_ids_by_subject: dict[str, set[str]] = {
        subject_id: set()
        for subject_id, _subject_name in canonical_subjects
    }
    observation_events: list[ReportOverviewTimelineEventViewModel] = []

    for observation in observations:
        observation_id = _phase2_text(observation.get("observation_id"))
        if not observation_id or observation.get("active", True) is False:
            continue
        observed_on = _phase2_local_date(
            observation.get("observed_on", observation.get("date"))
        )
        if observed_on is None:
            warning_keys.add(f"observation_date_invalid:{observation_id}")
            continue
        if not _phase2_in_period(observed_on, period_start, period_end):
            continue

        assignments = _phase2_mapping_rows(observation.get("assignments", ()))
        assigned_subject_ids = {
            _phase2_text(assignment.get("subject_id"))
            for assignment in assignments
        }
        assigned_subject_ids.discard("")
        assigned_subject_ids.discard("cross_subject")
        if assignments:
            observation_subject_ids = assigned_subject_ids
        else:
            fallback_subject_id = _phase2_text(observation.get("subject_id"))
            observation_subject_ids = (
                {fallback_subject_id}
                if fallback_subject_id and fallback_subject_id != "cross_subject"
                else set()
            )

        for subject_id in observation_subject_ids:
            if subject_id in observation_ids_by_subject:
                observation_ids_by_subject[subject_id].add(observation_id)

        assigned_competency_ids = {
            _phase2_text(assignment.get("competency_id"))
            for assignment in assignments
            if _phase2_text(assignment.get("competency_id"))
        }
        for assignment in assignments:
            competency_id = _phase2_text(assignment.get("competency_id"))
            subject_id = _phase2_text(assignment.get("subject_id"))
            if (
                competency_id
                and subject_id in competency_ids_by_subject
                and _phase2_is_current_competency(assignment)
            ):
                competency_ids_by_subject[subject_id].add(competency_id)

        event_subject_names = tuple(
            subject_names[subject_id]
            for subject_id in sorted(
                observation_subject_ids,
                key=lambda item: (subject_order.get(item, len(subject_order)), item),
            )
            if subject_id in subject_names
        )
        detail_parts: list[str] = []
        if event_subject_names:
            detail_parts.append(", ".join(event_subject_names))
        assignment_count = len(assigned_competency_ids)
        detail_parts.append(
            (
                "1 Kompetenz zugeordnet"
                if assignment_count == 1
                else f"{assignment_count} Kompetenzen zugeordnet"
            )
        )
        for field in ("competency_area", "topic", "context"):
            value = _phase2_short_existing_text(observation.get(field))
            if value:
                detail_parts.append(value)
        observation_events.append(
            _phase2_event(
                event_type="observation",
                source_identity=("observation", observation_id),
                occurred_on=observed_on,
                title="Beobachtung dokumentiert",
                detail_text=" · ".join(detail_parts),
                action=ReportOverviewActionViewModel(
                    "show_observation",
                    "Beobachtung öffnen",
                    observation_id,
                ),
            )
        )

    report_events = _phase2_report_events(
        report_revisions,
        period_start,
        period_end,
        warning_keys,
    )
    learning_conference_events = _phase2_learning_conference_events(
        learning_conference_revisions,
        period_start,
        period_end,
        warning_keys,
    )
    confirmation_events = _phase2_confirmation_events(
        confirmations,
        period_start,
        period_end,
        warning_keys,
    )
    for confirmation in confirmations:
        subject_id = _phase2_text(confirmation.get("subject_id"))
        competency_id = _phase2_text(confirmation.get("competency_id"))
        confirmed_on = _phase2_local_date(confirmation.get("confirmed_at"))
        if (
            subject_id in confirmed_competency_ids_by_subject
            and competency_id
            and _phase2_is_current_competency(confirmation)
            and _phase2_is_safe_confirmation(confirmation)
            and confirmed_on is not None
            and _phase2_in_period(confirmed_on, period_start, period_end)
        ):
            confirmed_competency_ids_by_subject[subject_id].add(competency_id)

    document_events = _phase2_deduplicate_events(
        (*report_events, *learning_conference_events)
    )
    supplementary_events = _phase2_deduplicate_events(
        (*observation_events, *confirmation_events)
    )
    if len(document_events) >= 15:
        selected_events = document_events
    else:
        remaining_capacity = 15 - len(document_events)
        newest_supplementary = tuple(
            sorted(
                supplementary_events,
                key=lambda event: (
                    -event.occurred_on.toordinal(),
                    event.source_identity,
                ),
            )[:remaining_capacity]
        )
        selected_events = (*document_events, *newest_supplementary)
    timeline_events = tuple(
        sorted(
            selected_events,
            key=lambda event: (
                event.occurred_on,
                event.source_identity,
            ),
        )
    )

    subject_documentation = tuple(
        _phase2_subject_documentation(
            subject_id,
            subject_name,
            competency_ids_by_subject[subject_id],
            observation_ids_by_subject[subject_id],
            confirmed_competency_ids_by_subject[subject_id],
            selected_report_draft_id,
        )
        for subject_id, subject_name in canonical_subjects
    )
    return (
        timeline_events,
        subject_documentation,
        _phase2_warnings(warning_keys),
    )


def _phase2_report_events(
    revisions: Sequence[Mapping[str, object]],
    period_start: date,
    period_end: date,
    warning_keys: set[str],
) -> tuple[ReportOverviewTimelineEventViewModel, ...]:
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for revision in revisions:
        report_draft_id = _phase2_text(revision.get("report_draft_id"))
        if not report_draft_id or not _phase2_is_completed_revision(
            revision,
            completion_key="is_finalized",
            completed_statuses={"finalized", "superseded"},
        ):
            continue
        if revision.get("hash_valid") is not True:
            warning_keys.add(f"report_revision_invalid:{report_draft_id}")
            continue
        grouped.setdefault(report_draft_id, []).append(revision)

    result: list[ReportOverviewTimelineEventViewModel] = []
    for report_draft_id, candidates in grouped.items():
        revision = max(
            candidates,
            key=lambda item: _phase2_revision_key(
                item,
                "learning_report_revision_id",
            ),
        )
        revision_id = _phase2_text(
            revision.get("learning_report_revision_id")
        )
        finalized_on = _phase2_local_date(revision.get("finalized_at"))
        if finalized_on is None:
            warning_keys.add(f"report_date_invalid:{report_draft_id}")
            continue
        if not _phase2_in_period(finalized_on, period_start, period_end):
            continue
        result.append(
            _phase2_event(
                event_type="report",
                source_identity=("report", report_draft_id),
                occurred_on=finalized_on,
                title="Bericht abgeschlossen",
                detail_text="Finalisierter Bericht",
                action=(
                    ReportOverviewActionViewModel(
                        "open_report_revision",
                        "Bericht öffnen",
                        revision_id,
                    )
                    if revision_id
                    else None
                ),
            )
        )
    return tuple(result)


def _phase2_learning_conference_events(
    revisions: Sequence[Mapping[str, object]],
    period_start: date,
    period_end: date,
    warning_keys: set[str],
) -> tuple[ReportOverviewTimelineEventViewModel, ...]:
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for revision in revisions:
        draft_id = _phase2_text(
            revision.get("learning_conference_draft_id")
        )
        if not draft_id or not _phase2_is_completed_revision(
            revision,
            completion_key="is_completed",
            completed_statuses={"completed", "superseded"},
        ):
            continue
        if revision.get("hash_valid") is not True:
            warning_keys.add(f"learning_conference_revision_invalid:{draft_id}")
            continue
        grouped.setdefault(draft_id, []).append(revision)

    result: list[ReportOverviewTimelineEventViewModel] = []
    for draft_id, candidates in grouped.items():
        revision = max(
            candidates,
            key=lambda item: _phase2_revision_key(
                item,
                "learning_conference_revision_id",
            ),
        )
        revision_id = _phase2_text(
            revision.get("learning_conference_revision_id")
        )
        conference_on = _phase2_local_date(revision.get("conference_date"))
        if conference_on is None:
            warning_keys.add(f"learning_conference_date_invalid:{draft_id}")
            continue
        if not _phase2_in_period(conference_on, period_start, period_end):
            continue
        result.append(
            _phase2_event(
                event_type="learning_conference",
                source_identity=("learning_conference", draft_id),
                occurred_on=conference_on,
                title="LEG durchgeführt",
                detail_text="Lernentwicklungsgespräch",
                action=(
                    ReportOverviewActionViewModel(
                        "open_learning_conference_revision",
                        "LEG öffnen",
                        revision_id,
                    )
                    if revision_id
                    else None
                ),
            )
        )
    return tuple(result)


def _phase2_confirmation_events(
    confirmations: Sequence[Mapping[str, object]],
    period_start: date,
    period_end: date,
    warning_keys: set[str],
) -> tuple[ReportOverviewTimelineEventViewModel, ...]:
    result: list[ReportOverviewTimelineEventViewModel] = []
    for confirmation in confirmations:
        student_id = _phase2_text(confirmation.get("student_id"))
        competency_id = _phase2_text(confirmation.get("competency_id"))
        if (
            not student_id
            or not competency_id
            or not _phase2_is_current_competency(confirmation)
            or not _phase2_is_safe_confirmation(confirmation)
        ):
            continue
        confirmed_on = _phase2_local_date(confirmation.get("confirmed_at"))
        if confirmed_on is None:
            warning_keys.add(
                f"confirmation_date_invalid:{student_id}:{competency_id}"
            )
            continue
        if not _phase2_in_period(confirmed_on, period_start, period_end):
            continue
        competency_text = _phase2_short_existing_text(
            confirmation.get("competency_text")
        )
        result.append(
            _phase2_event(
                event_type="confirmation",
                source_identity=(
                    "confirmation",
                    student_id,
                    competency_id,
                ),
                occurred_on=confirmed_on,
                title="Kompetenz bestätigt",
                detail_text=(
                    competency_text
                    or "Aktueller sicherer Bestätigungsstand"
                ),
                action=ReportOverviewActionViewModel(
                    "show_competency",
                    "Kompetenzbereich öffnen",
                    competency_id,
                ),
            )
        )
    return tuple(result)


def _phase2_subject_documentation(
    subject_id: str,
    subject_name: str,
    competency_ids: set[str],
    observation_ids: set[str],
    confirmed_competency_ids: set[str],
    selected_report_draft_id: str,
) -> ReportOverviewSubjectDocumentationViewModel:
    sorted_competency_ids = tuple(sorted(competency_ids))
    sorted_observation_ids = tuple(sorted(observation_ids))
    competency_count = len(sorted_competency_ids)
    observation_count = len(sorted_observation_ids)
    confirmation_count = len(confirmed_competency_ids)
    return ReportOverviewSubjectDocumentationViewModel(
        subject_id=subject_id,
        subject_name=subject_name,
        competency_ids=sorted_competency_ids,
        observation_ids=sorted_observation_ids,
        competency_count_text=(
            f"{competency_count} "
            f"{'Kompetenz' if competency_count == 1 else 'Kompetenzen'} "
            "dokumentiert"
        ),
        observation_count_text=(
            f"{observation_count} "
            f"{'Beobachtung' if observation_count == 1 else 'Beobachtungen'} "
            "im aktuellen Schuljahr"
        ),
        accessible_name=(
            f"{subject_name}: {competency_count} "
            f"{'Kompetenz' if competency_count == 1 else 'Kompetenzen'} "
            "dokumentiert"
        ),
        evidence_action=ReportOverviewActionViewModel(
            "show_subject_evidence",
            "Belege ansehen",
            subject_id,
            subject_id,
        ),
        prepare_action=ReportOverviewActionViewModel(
            "prepare_subject",
            "Bericht vorbereiten",
            selected_report_draft_id,
            subject_id,
        ),
        confirmation_count_text=(
            "Aktuell bestätigter Stand für "
            f"{confirmation_count} "
            f"{'Kompetenz' if confirmation_count == 1 else 'Kompetenzen'} "
            "vorhanden"
            if confirmation_count
            else ""
        ),
    )


def _phase2_event(
    *,
    event_type: str,
    source_identity: tuple[str, ...],
    occurred_on: date,
    title: str,
    detail_text: str,
    action: ReportOverviewActionViewModel | None,
) -> ReportOverviewTimelineEventViewModel:
    date_label = _date_label(occurred_on)
    accessible_name = " · ".join(
        value
        for value in (date_label, title, detail_text)
        if value
    )
    return ReportOverviewTimelineEventViewModel(
        event_type=event_type,
        source_identity=source_identity,
        occurred_on=occurred_on,
        date_label=date_label,
        title=title,
        detail_text=detail_text,
        accessible_name=accessible_name,
        action=action,
    )


def _phase2_deduplicate_events(
    events: Sequence[ReportOverviewTimelineEventViewModel],
) -> tuple[ReportOverviewTimelineEventViewModel, ...]:
    by_identity: dict[
        tuple[str, ...],
        ReportOverviewTimelineEventViewModel,
    ] = {}
    for event in events:
        existing = by_identity.get(event.source_identity)
        if existing is None or (
            event.occurred_on,
            event.detail_text,
            event.title,
        ) > (
            existing.occurred_on,
            existing.detail_text,
            existing.title,
        ):
            by_identity[event.source_identity] = event
    return tuple(by_identity.values())


def _phase2_canonical_subjects(
    subjects: Sequence[Mapping[str, object]],
) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for subject in subjects:
        subject_id = _phase2_text(subject.get("subject_id"))
        subject_name = _phase2_text(subject.get("subject_name"))
        if (
            not subject_id
            or not subject_name
            or subject_id == "cross_subject"
            or subject.get("active", True) is False
            or subject_id in seen
        ):
            continue
        seen.add(subject_id)
        result.append((subject_id, subject_name))
    return tuple(result)


def _phase2_mapping_rows(value: object) -> tuple[Mapping[str, object], ...]:
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _phase2_is_current_competency(row: Mapping[str, object]) -> bool:
    if row.get("active", True) is False or row.get("historical") is True:
        return False
    catalog_status = _phase2_text(row.get("catalog_status")).lower()
    return catalog_status not in _CURRENTLY_UNAVAILABLE_CATALOG_STATUSES


def _phase2_is_safe_confirmation(row: Mapping[str, object]) -> bool:
    explicit = row.get("confirmation_safe")
    if explicit is not None:
        return explicit is True
    state = _phase2_text(row.get("documentation_state")).lower()
    return state not in {
        "",
        "undocumented",
        "unknown",
        "confirmation_unknown",
    }


def _phase2_is_completed_revision(
    row: Mapping[str, object],
    *,
    completion_key: str,
    completed_statuses: set[str],
) -> bool:
    if completion_key in row:
        return row.get(completion_key) is True
    return _phase2_text(row.get("status")).lower() in completed_statuses


def _phase2_revision_key(
    row: Mapping[str, object],
    revision_id_key: str,
) -> tuple[int, str]:
    value = row.get("revision_number", 0)
    try:
        revision_number = int(value)
    except (TypeError, ValueError):
        revision_number = 0
    return revision_number, _phase2_text(row.get(revision_id_key))


def _phase2_local_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.astimezone().date() if value.tzinfo is not None else value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone().date() if parsed.tzinfo is not None else parsed.date()


def _phase2_in_period(value: date, period_start: date, period_end: date) -> bool:
    return period_start <= value <= period_end


def _phase2_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _phase2_short_existing_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.split())
    if len(normalized) <= 120:
        return normalized
    return f"{normalized[:117].rstrip()}…"


def _phase2_warnings(
    warning_keys: set[str],
) -> tuple[ReportOverviewProjectionWarningViewModel, ...]:
    return tuple(
        ReportOverviewProjectionWarningViewModel(warning_key)
        for warning_key in sorted(warning_keys)
    )


def _period_label(start: date, end: date) -> str:
    return f"{_date_label(start)} bis {_date_label(end)}"


def _optional_period_label(
    start: date | None,
    end: date | None,
    conference_date: date | None = None,
) -> str:
    if start is not None and end is not None:
        return _period_label(start, end)
    if conference_date is not None:
        return f"Gespräch am {_date_label(conference_date)} · Zeitraum noch offen"
    return "LEG-Zeitraum noch offen"


def _iso_period_label(start: str, end: str) -> str:
    try:
        return _period_label(date.fromisoformat(start), date.fromisoformat(end))
    except ValueError:
        return "Zeitraum nicht lesbar"


def _iso_optional_leg_period_label(
    start: str,
    end: str,
    conference_date: str,
) -> str:
    if start and end:
        return _iso_period_label(start, end)
    if conference_date:
        try:
            return (
                f"Gespräch am {_date_label(date.fromisoformat(conference_date))} "
                "· Zeitraum noch offen"
            )
        except ValueError:
            return "Gesprächsdatum nicht lesbar"
    return "LEG-Zeitraum noch offen"


def _date_label(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _timestamp_label(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return "Datum nicht verfügbar"
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return "Datum nicht lesbar"
    return parsed.strftime("%d.%m.%Y · %H:%M")


def _latest_update_label(values: Iterable[str]) -> str:
    candidates = tuple(value for value in values if value)
    if not candidates:
        return "Noch keine Änderung"
    return _timestamp_label(max(candidates))


def _selected_draft(
    drafts: Sequence[DraftViewModel],
    selected_id: str,
    id_attribute: str,
) -> DraftViewModel | None:
    if len(drafts) == 1:
        return drafts[0]
    if selected_id:
        return next(
            (
                draft
                for draft in drafts
                if str(getattr(draft, id_attribute, "")) == selected_id
            ),
            None,
        )
    return drafts[0] if len(drafts) == 1 else None


def _strict_selected_draft(
    drafts: Sequence[DraftViewModel],
    selected_id: str,
    id_attribute: str,
) -> DraftViewModel | None:
    if not selected_id:
        return None
    return next(
        (
            draft
            for draft in drafts
            if str(getattr(draft, id_attribute, "")) == selected_id
        ),
        None,
    )
