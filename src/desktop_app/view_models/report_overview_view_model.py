"""Display-ready Paket-1 projection for the student report overview."""

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

DraftViewModel = TypeVar("DraftViewModel")


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
class ReportOverviewViewModel:
    """Complete display projection for package 1 of the report overview."""

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
) -> ReportOverviewViewModel:
    """Compose existing report and LEG reads only at the display boundary."""
    report_drafts = tuple(report_drafts)
    learning_conference_drafts = tuple(learning_conference_drafts)
    selected_report = _selected_draft(
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
    )


def _report_status_card(
    drafts: tuple[LearningReportDraftViewModel, ...],
    states: Mapping[str, LearningReportRevisionState | Exception],
    selected: LearningReportDraftViewModel | None,
    revision_errors: frozenset[str],
) -> ReportStatusCardViewModel:
    if not drafts:
        return empty_report_overview().report_status
    if len(drafts) > 1 and selected is None:
        return ReportStatusCardViewModel(
            "multiple_drafts",
            f"{len(drafts)} Entwürfe vorhanden",
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
    elif len(report_drafts) > 1 and selected_report is None:
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
