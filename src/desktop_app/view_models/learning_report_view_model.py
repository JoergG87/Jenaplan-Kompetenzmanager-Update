"""Transient preparation and neutral output projection for learning reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from prototypes.pdf_engine.output_models import (
    ChartBlock,
    CompetencyTimelineData,
    CompetencyTimelinePoint,
    CompetencyTimelineSeries,
    DocumentationCoverageData,
    DocumentationCoverageItem,
    DocumentMetadata,
    HeadingBlock,
    KeyValueBlock,
    ObservationTimelineData,
    ObservationTimelineEvent,
    ParagraphBlock,
    ReportOutputModel,
    ReportPage,
    SpacerBlock,
    TableBlock,
)
from src.core.report_draft import (
    LEARNING_DEVELOPMENT_REPORT_TYPE,
    REPORT_DRAFT_STATUS,
    ReportDraftChartSelectionRecord,
    ReportDraftRecord,
    ReportDraftSubjectRecord,
)


RATING_STATE_COLORS = (
    ("++", "#315F7D"),
    ("+", "#2A7774"),
    ("-", "#6C7D8A"),
    ("--", "#9A7048"),
)


@dataclass(frozen=True)
class LearningReportCompetencyViewModel:
    """One canonical competency-status row prepared for conscious selection."""

    competency_id: str
    subject_id: str
    subject_name: str
    learning_area: str
    competency_group: str
    competency_text: str
    documentation_state: str
    historical: bool
    selectable: bool
    evidence_points: tuple[tuple[date, str], ...]


@dataclass(frozen=True)
class LearningReportEvidenceViewModel:
    """One observation that can be deliberately included as report evidence."""

    observation_id: str
    observed_on: date
    subject_name: str
    context: str
    note: str
    competency_ids: tuple[str, ...]

    @property
    def display_label(self) -> str:
        return " · ".join(
            part
            for part in (
                self.observed_on.strftime("%d.%m.%Y"),
                self.context,
                self.note,
            )
            if part
        )


@dataclass(frozen=True)
class LearningReportSubjectViewModel:
    """One subject with its canonical competency rows and evidence candidates."""

    subject_id: str
    subject_name: str
    competencies: tuple[LearningReportCompetencyViewModel, ...]
    evidence: tuple[LearningReportEvidenceViewModel, ...]

    @property
    def documented_count(self) -> int:
        return sum(
            competency.documentation_state != "undocumented"
            for competency in self.competencies
            if competency.selectable
        )

    @property
    def current_count(self) -> int:
        return sum(competency.selectable for competency in self.competencies)


@dataclass(frozen=True)
class LearningReportPreparationViewModel:
    """Read-only productive input projection for one transient report draft."""

    student_id: str
    student_name: str
    group_name: str
    subjects: tuple[LearningReportSubjectViewModel, ...]


@dataclass(frozen=True)
class LearningReportSubjectDraftViewModel:
    """Teacher-authored texts for one deliberately selected report subject."""

    subject_id: str
    strengths_text: str = ""
    development_text: str = ""
    support_needs_text: str = ""
    next_goals_text: str = ""

    def to_record(self) -> ReportDraftSubjectRecord:
        return ReportDraftSubjectRecord(
            self.subject_id,
            self.strengths_text,
            self.development_text,
            self.support_needs_text,
            self.next_goals_text,
        )


@dataclass(frozen=True)
class LearningReportChartSelectionViewModel:
    """One selected neutral diagram for a report subject."""

    subject_id: str
    chart_type: str

    def to_record(self) -> ReportDraftChartSelectionRecord:
        return ReportDraftChartSelectionRecord(self.subject_id, self.chart_type)


@dataclass(frozen=True)
class LearningReportDraftViewModel:
    """Complete editable state for a persistent learning-report draft."""

    student_id: str
    period_start: date
    period_end: date
    teacher_name: str = ""
    overall_text: str = ""
    subjects: tuple[LearningReportSubjectDraftViewModel, ...] = ()
    competency_ids: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()
    chart_selections: tuple[LearningReportChartSelectionViewModel, ...] = ()
    report_draft_id: str = ""
    report_type: str = LEARNING_DEVELOPMENT_REPORT_TYPE
    status: str = REPORT_DRAFT_STATUS
    created_at: str = ""
    updated_at: str = ""
    unavailable_observation_ids: tuple[str, ...] = ()

    @property
    def selected_subject_ids(self) -> tuple[str, ...]:
        return tuple(subject.subject_id for subject in self.subjects)

    @classmethod
    def from_record(
        cls,
        record: ReportDraftRecord,
        *,
        unavailable_observation_ids: tuple[str, ...] = (),
    ) -> "LearningReportDraftViewModel":
        return cls(
            student_id=record.student_id,
            period_start=date.fromisoformat(record.period_start),
            period_end=date.fromisoformat(record.period_end),
            teacher_name=record.teacher_name,
            overall_text=record.overall_text,
            subjects=tuple(
                LearningReportSubjectDraftViewModel(
                    subject.subject_id,
                    subject.strengths_text,
                    subject.development_text,
                    subject.support_needs_text,
                    subject.next_goals_text,
                )
                for subject in record.subjects
            ),
            competency_ids=record.competency_ids,
            observation_ids=record.observation_ids,
            chart_selections=tuple(
                LearningReportChartSelectionViewModel(
                    chart.subject_id,
                    chart.chart_type,
                )
                for chart in record.chart_selections
            ),
            report_draft_id=record.report_draft_id,
            report_type=record.report_type,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            unavailable_observation_ids=unavailable_observation_ids,
        )


@dataclass(frozen=True)
class LearningReportDraft:
    """Renderer-facing user-owned state assembled from the persistent draft."""

    period_start: date
    period_end: date
    teacher_name: str
    overall_view: str
    goals: str
    support: str
    selected_subject_ids: tuple[str, ...]
    selected_competency_ids: tuple[str, ...]
    selected_observation_ids: tuple[str, ...]
    report_type: str = "Lernentwicklungsbericht"
    school_name: str = "Jenaplan-Schule"
    subject_texts: tuple[LearningReportSubjectDraftViewModel, ...] = ()
    chart_selections: tuple[LearningReportChartSelectionViewModel, ...] = ()
    unavailable_observation_ids: tuple[str, ...] = ()


def build_learning_report_preparation(
    student: object,
    statuses: tuple[object, ...],
    observations: tuple[object, ...],
) -> LearningReportPreparationViewModel:
    """Group the canonical status projection without recalculating status."""
    observations_by_id = {
        str(getattr(observation, "observation_id")): observation
        for observation in observations
    }
    competencies_by_subject: dict[str, list[LearningReportCompetencyViewModel]] = {}
    competency_subjects: dict[str, str] = {}
    subject_names: dict[str, str] = {}
    evidence_subjects: dict[str, set[str]] = {}
    evidence_competencies: dict[str, set[str]] = {}

    for status in statuses:
        subject_id = str(getattr(status, "subject_id", "")).strip()
        subject_name = str(
            getattr(status, "subject_display_name", subject_id)
        ).strip() or subject_id
        if not subject_id:
            continue
        subject_names.setdefault(subject_id, subject_name)
        competency_subjects[str(getattr(status, "competency_id", ""))] = subject_id
        historical = bool(getattr(status, "historical", False))
        selectable = bool(getattr(status, "is_active", False)) and not historical
        evidence_points: list[tuple[date, str]] = []
        for evidence in getattr(status, "evidence", ()):
            observed_on = _parse_date(getattr(evidence, "observation_date", ""))
            if observed_on is not None:
                evidence_points.append((observed_on, str(getattr(evidence, "rating", ""))))
            observation_id = str(getattr(evidence, "observation_id", ""))
            if observation_id:
                evidence_subjects.setdefault(observation_id, set()).add(subject_id)
                evidence_competencies.setdefault(observation_id, set()).add(
                    str(getattr(status, "competency_id", ""))
                )
        confirmed_on = _parse_date(str(getattr(status, "confirmed_at", ""))[:10])
        confirmed_rating = str(getattr(status, "confirmed_rating", ""))
        if confirmed_on is not None and confirmed_rating:
            evidence_points.append((confirmed_on, confirmed_rating))
        competencies_by_subject.setdefault(subject_id, []).append(
            LearningReportCompetencyViewModel(
                competency_id=str(getattr(status, "competency_id", "")),
                subject_id=subject_id,
                subject_name=subject_name,
                learning_area=str(getattr(status, "learning_area", "")) or "Ohne Kompetenzbereich",
                competency_group=str(getattr(status, "competency_group", "")) or "Ohne Thema",
                competency_text=(
                    str(getattr(status, "competency_text", ""))
                    or str(getattr(status, "competency_label", ""))
                ),
                documentation_state=str(getattr(status, "documentation_state", "")),
                historical=historical,
                selectable=selectable,
                evidence_points=tuple(sorted(evidence_points)),
            )
        )

    for observation_id, observation in observations_by_id.items():
        for rating in getattr(observation, "competency_ratings", ()):
            competency_id = str(getattr(rating, "competency_id", ""))
            subject_id = competency_subjects.get(competency_id)
            if subject_id:
                evidence_subjects.setdefault(observation_id, set()).add(subject_id)
                evidence_competencies.setdefault(observation_id, set()).add(competency_id)
        if observation_id in evidence_subjects:
            continue
        visible_subject = str(getattr(observation, "subject_display_name", "")).strip()
        subject_id = next(
            (
                key
                for key, name in subject_names.items()
                if name.casefold() == visible_subject.casefold()
            ),
            "",
        )
        if subject_id:
            evidence_subjects.setdefault(observation_id, set()).add(subject_id)

    report_evidence_by_subject: dict[str, list[LearningReportEvidenceViewModel]] = {}
    for observation_id, subject_ids in evidence_subjects.items():
        observation = observations_by_id.get(observation_id)
        if observation is None:
            continue
        observed_on = _parse_date(getattr(observation, "date_text", ""))
        if observed_on is None:
            continue
        evidence = LearningReportEvidenceViewModel(
            observation_id=observation_id,
            observed_on=observed_on,
            subject_name=str(getattr(observation, "subject_display_name", "")),
            context=str(getattr(observation, "context", "")),
            note=str(getattr(observation, "note", "")),
            competency_ids=tuple(sorted(evidence_competencies.get(observation_id, ()))),
        )
        for subject_id in subject_ids:
            report_evidence_by_subject.setdefault(subject_id, []).append(evidence)

    subjects = tuple(
        LearningReportSubjectViewModel(
            subject_id=subject_id,
            subject_name=subject_names[subject_id],
            competencies=tuple(
                sorted(
                    competencies,
                    key=lambda item: (
                        item.historical,
                        item.learning_area.casefold(),
                        item.competency_group.casefold(),
                        item.competency_text.casefold(),
                    ),
                )
            ),
            evidence=tuple(
                sorted(
                    report_evidence_by_subject.get(subject_id, ()),
                    key=lambda item: (item.observed_on, item.observation_id),
                    reverse=True,
                )
            ),
        )
        for subject_id, competencies in sorted(
            competencies_by_subject.items(),
            key=lambda item: subject_names[item[0]].casefold(),
        )
    )
    return LearningReportPreparationViewModel(
        student_id=str(getattr(student, "student_id", "")),
        student_name=str(getattr(student, "display_name", "")),
        group_name=str(getattr(student, "group_name", "")),
        subjects=subjects,
    )


def build_report_output_model(
    preparation: LearningReportPreparationViewModel,
    draft: LearningReportDraft,
) -> ReportOutputModel:
    """Create the complete neutral renderer input from deliberate draft choices."""
    if draft.period_end <= draft.period_start:
        raise ValueError("Das Ende des Berichtszeitraums muss nach dem Beginn liegen.")
    subject_ids = set(draft.selected_subject_ids)
    competency_ids = set(draft.selected_competency_ids)
    observation_ids = set(draft.selected_observation_ids)
    subject_texts = {item.subject_id: item for item in draft.subject_texts}
    chart_types_by_subject: dict[str, set[str]] = {}
    for selection in draft.chart_selections:
        chart_types_by_subject.setdefault(selection.subject_id, set()).add(
            selection.chart_type
        )
    subjects = tuple(
        subject for subject in preparation.subjects if subject.subject_id in subject_ids
    )
    selected_competencies = tuple(
        competency
        for subject in subjects
        for competency in subject.competencies
        if competency.competency_id in competency_ids
    )
    selected_evidence = _unique_evidence(
        evidence
        for subject in subjects
        for evidence in subject.evidence
        if (
            evidence.observation_id in observation_ids
            and draft.period_start <= evidence.observed_on <= draft.period_end
        )
    )

    metadata = DocumentMetadata(
        document_title=draft.report_type,
        student_name=preparation.student_name,
        group_name=preparation.group_name,
        period=(
            f"{draft.period_start.strftime('%d.%m.%Y')} bis "
            f"{draft.period_end.strftime('%d.%m.%Y')}"
        ),
        teacher_name=draft.teacher_name.strip(),
        school_name=draft.school_name.strip(),
        created_on=date.today(),
        header_text=f"{draft.school_name.strip()} | {draft.report_type}",
        footer_text="Vertraulicher Lernentwicklungsbericht",
    )
    subject_pages = tuple(
        _subject_output_page(
            subject=subject,
            subject_text=subject_texts.get(subject.subject_id),
            selected_competencies=tuple(
                competency
                for competency in selected_competencies
                if competency.subject_id == subject.subject_id
            ),
            selected_evidence=tuple(
                evidence
                for evidence in selected_evidence
                if evidence in subject.evidence
            ),
            selected_chart_types=chart_types_by_subject.get(subject.subject_id, set()),
            period_start=draft.period_start,
            period_end=draft.period_end,
        )
        for subject in subjects
    )
    pages = (
        ReportPage(
            label="Dokumentkontext",
            is_cover=True,
            blocks=(
                SpacerBlock(18),
                HeadingBlock(metadata.document_title, level=0),
                HeadingBlock(metadata.student_name, level=1),
                KeyValueBlock(
                    (
                        ("Stammgruppe", metadata.group_name),
                        ("Zeitraum", metadata.period),
                        ("Verantwortliche Lehrkraft", metadata.teacher_name),
                        ("Berichtstyp", draft.report_type),
                    )
                ),
            ),
        ),
        ReportPage(
            label="Pädagogischer Gesamtblick",
            blocks=(
                HeadingBlock("Pädagogischer Gesamtblick"),
                ParagraphBlock(draft.overall_view.strip() or "Noch nicht ausgefüllt."),
            ),
        ),
        *subject_pages,
        ReportPage(
            label="Abschluss",
            blocks=(
                HeadingBlock("Übergreifende Entwicklung und nächste Schritte"),
                *_closing_blocks(subjects, subject_texts, draft),
                *_unavailable_evidence_blocks(draft),
            ),
        ),
    )
    return ReportOutputModel(metadata=metadata, pages=pages)


def _subject_output_page(
    *,
    subject: LearningReportSubjectViewModel,
    subject_text: LearningReportSubjectDraftViewModel | None,
    selected_competencies: tuple[LearningReportCompetencyViewModel, ...],
    selected_evidence: tuple[LearningReportEvidenceViewModel, ...],
    selected_chart_types: set[str],
    period_start: date,
    period_end: date,
) -> ReportPage:
    text = subject_text or LearningReportSubjectDraftViewModel(subject.subject_id)
    blocks: list[object] = [
        HeadingBlock(subject.subject_name),
        HeadingBlock("Lernentwicklung", level=2),
        ParagraphBlock(text.development_text.strip() or "Noch nicht ausgefüllt."),
        HeadingBlock("Stärken", level=2),
        ParagraphBlock(text.strengths_text.strip() or "Noch nicht ausgefüllt."),
        HeadingBlock("Unterstützungsbedarf", level=2),
        ParagraphBlock(text.support_needs_text.strip() or "Noch nicht ausgefüllt."),
        HeadingBlock("Nächste Ziele", level=2),
        ParagraphBlock(text.next_goals_text.strip() or "Noch nicht ausgefüllt."),
        SpacerBlock(8),
        HeadingBlock("Ausgewählte konkrete Kompetenzen", level=2),
        TableBlock(
            headers=("Kompetenzbereich", "Thema", "Ausgewählte Kompetenz"),
            rows=tuple(
                (
                    competency.learning_area,
                    competency.competency_group,
                    (
                        competency.competency_text
                        if competency.selectable
                        else f"{competency.competency_text} · historisch ausgewählt; nicht mehr regulär verfügbar"
                    ),
                )
                for competency in selected_competencies
            ),
            column_weights=(0.24, 0.24, 0.52),
        ),
        SpacerBlock(8),
        HeadingBlock("Bewusst ausgewählte Beobachtungsbelege", level=2),
        TableBlock(
            headers=("Datum", "Kontext", "Notiz"),
            rows=tuple(
                (
                    item.observed_on.strftime("%d.%m.%Y"),
                    item.context,
                    item.note,
                )
                for item in selected_evidence
            ),
            column_weights=(0.18, 0.24, 0.58),
        ),
    ]
    if "documentation_coverage" in selected_chart_types:
        blocks.extend(
            (
                SpacerBlock(8),
                ChartBlock(
                    DocumentationCoverageData(
                        title="Dokumentationsabdeckung",
                        items=(
                            DocumentationCoverageItem(
                                subject.subject_name,
                                subject.documented_count,
                                subject.current_count,
                            ),
                        ),
                        note=(
                            "Die Darstellung zeigt Dokumentationsabdeckung und keine "
                            "Leistung oder Bewertung."
                        ),
                    )
                ),
            )
        )
    if "competency_timeline" in selected_chart_types:
        blocks.extend(
            (
                SpacerBlock(6),
                ChartBlock(
                    CompetencyTimelineData(
                        title="Kompetenzentwicklung mit Einzelständen",
                        period_start=period_start,
                        period_end=period_end,
                        series=tuple(
                            CompetencyTimelineSeries(
                                label=competency.competency_text,
                                points=tuple(
                                    CompetencyTimelinePoint(observed_on, rating)
                                    for observed_on, rating in competency.evidence_points
                                    if period_start <= observed_on <= period_end
                                ),
                            )
                            for competency in selected_competencies
                        ),
                        state_colors=RATING_STATE_COLORS,
                        note=(
                            "Einzelne datierte Stände ohne Score, Durchschnitt, "
                            "Trendlinie oder automatische Bewertung."
                        ),
                    )
                ),
            )
        )
    if "observation_timeline" in selected_chart_types:
        blocks.extend(
            (
                SpacerBlock(6),
                ChartBlock(
                    ObservationTimelineData(
                        title="Zeitachse ausgewählter Beobachtungen",
                        period_start=period_start,
                        period_end=period_end,
                        events=tuple(
                            ObservationTimelineEvent(
                                item.observed_on,
                                item.context,
                                item.note,
                            )
                            for item in selected_evidence
                        ),
                        note="Die Belege wurden bewusst für diesen Bericht ausgewählt.",
                    )
                ),
            )
        )
    return ReportPage(label=subject.subject_name, blocks=tuple(blocks))


def _closing_blocks(
    subjects: tuple[LearningReportSubjectViewModel, ...],
    subject_texts: dict[str, LearningReportSubjectDraftViewModel],
    draft: LearningReportDraft,
) -> tuple[object, ...]:
    blocks: list[object] = []
    for subject in subjects:
        text = subject_texts.get(subject.subject_id)
        if text is None:
            continue
        blocks.extend(
            (
                HeadingBlock(subject.subject_name, level=2),
                ParagraphBlock(
                    text.next_goals_text.strip()
                    or text.support_needs_text.strip()
                    or "Noch nicht ausgefüllt."
                ),
                SpacerBlock(8),
            )
        )
    if not blocks:
        blocks.extend(
            (
                HeadingBlock("Ziele", level=2),
                ParagraphBlock(draft.goals.strip() or "Noch nicht ausgefüllt."),
                SpacerBlock(8),
                HeadingBlock("Unterstützung", level=2),
                ParagraphBlock(draft.support.strip() or "Noch nicht ausgefüllt."),
            )
        )
    return tuple(blocks)


def _unavailable_evidence_blocks(
    draft: LearningReportDraft,
) -> tuple[object, ...]:
    unavailable_ids = tuple(
        observation_id
        for observation_id in draft.unavailable_observation_ids
        if observation_id in set(draft.selected_observation_ids)
    )
    if not unavailable_ids:
        return ()
    return (
        SpacerBlock(8),
        HeadingBlock("Nicht mehr verfügbare Beobachtungsbelege", level=2),
        ParagraphBlock(
            "Die gespeicherten Referenzen bleiben erhalten; Inhalte werden nicht rekonstruiert."
        ),
        TableBlock(
            headers=("Referenz", "Status"),
            rows=tuple(
                (observation_id, "Nicht mehr verfügbar")
                for observation_id in unavailable_ids
            ),
            column_weights=(0.35, 0.65),
        ),
    )


def _parse_date(value: object) -> date | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _unique_evidence(
    evidence: object,
) -> tuple[LearningReportEvidenceViewModel, ...]:
    unique: dict[str, LearningReportEvidenceViewModel] = {}
    for item in evidence:
        unique.setdefault(item.observation_id, item)
    return tuple(sorted(unique.values(), key=lambda item: item.observed_on))
