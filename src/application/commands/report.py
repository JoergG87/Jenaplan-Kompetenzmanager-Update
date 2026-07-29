"""Read-only application orchestration for transient report preparation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from src.core.learning_report import (
    LearningReportFinalizationPreview,
    LearningReportFinalizationResult,
    LearningReportRevisionReadService,
    LearningReportRevisionHistory,
    LearningReportRevisionRecord,
    LearningReportRevisionState,
    LearningReportRecord,
    ReportFinalizationService,
)
from src.core.learning_report_pdf import (
    LearningReportPdfArtifactRecord,
    LearningReportPdfService,
)
from src.core.report_draft import (
    ReportDraftChartSelectionRecord,
    ReportDraftRecord,
    ReportDraftRepository,
    ReportDraftService,
    ReportDraftSubjectRecord,
)


@dataclass(frozen=True)
class FinalizeLearningReportCommand:
    """Create the next immutable revision for one editable report draft."""

    report_draft_id: str
    finalized_by_display_name: str

    command_name: str = "learning_report.finalize"


class ReportFinalizationApplicationService:
    """Application boundary for explicit learning-report finalization."""

    def __init__(self, domain_service: ReportFinalizationService) -> None:
        self.domain_service = domain_service

    def finalize(
        self,
        command: FinalizeLearningReportCommand,
    ) -> LearningReportFinalizationResult:
        return self.domain_service.finalize(
            report_draft_id=command.report_draft_id,
            finalized_by_display_name=command.finalized_by_display_name,
        )

    def prepare(
        self,
        report_draft_id: str,
    ) -> LearningReportFinalizationPreview:
        return self.domain_service.prepare(report_draft_id=report_draft_id)


class ReportRevisionApplicationService:
    """Application read boundary for immutable report revisions."""

    def __init__(self, read_service: LearningReportRevisionReadService) -> None:
        self.read_service = read_service

    def state_for_draft(self, report_draft_id: str) -> LearningReportRevisionState:
        return self.read_service.state_for_draft(report_draft_id)

    def report_for_draft(self, report_draft_id: str) -> LearningReportRecord | None:
        return self.read_service.report_for_draft(report_draft_id)

    def current_revision_for_draft(
        self,
        report_draft_id: str,
    ) -> LearningReportRevisionRecord | None:
        return self.read_service.current_revision_for_draft(report_draft_id)

    def revision_history_for_draft(
        self,
        report_draft_id: str,
    ) -> tuple[LearningReportRevisionRecord, ...]:
        return self.read_service.revision_history_for_draft(report_draft_id)

    def revision_histories_for_student(
        self,
        student_id: str,
    ) -> tuple[LearningReportRevisionHistory, ...]:
        return self.read_service.revision_histories_for_student(student_id)

    def verify_revision(
        self,
        revision: LearningReportRevisionRecord,
    ) -> dict[str, object]:
        return self.read_service.verify_revision(revision)

    def revision_by_id(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportRevisionRecord | None:
        return self.read_service.revision_by_id(learning_report_revision_id)

    def snapshot_payload(
        self,
        learning_report_revision_id: str,
    ) -> tuple[LearningReportRevisionRecord, dict[str, object]] | None:
        return self.read_service.snapshot_payload(learning_report_revision_id)


@dataclass(frozen=True)
class GenerateLearningReportPdfCommand:
    """Generate or verify the immutable PDF artifact for one final RPV."""

    learning_report_revision_id: str

    command_name: str = "learning_report_pdf.generate"


class LearningReportPdfApplicationService:
    """Application boundary for final report PDF generation and lookup."""

    def __init__(self, domain_service: LearningReportPdfService) -> None:
        self.domain_service = domain_service

    def generate(
        self,
        command: GenerateLearningReportPdfCommand,
    ) -> LearningReportPdfArtifactRecord:
        return self.domain_service.generate(command.learning_report_revision_id)

    def load_for_revision(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportPdfArtifactRecord | None:
        return self.domain_service.load_artifact(learning_report_revision_id)


@dataclass(frozen=True)
class CreateLearningReportDraftCommand:
    """Create one persistent learning-development report draft."""

    student_id: str
    report_type: str
    period_start: str
    period_end: str
    teacher_name: str
    overall_text: str
    subjects: tuple[ReportDraftSubjectRecord, ...]
    competency_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    chart_selections: tuple[ReportDraftChartSelectionRecord, ...]

    command_name: str = "report_draft.create"


@dataclass(frozen=True)
class UpdateLearningReportDraftCommand:
    """Replace the editable contents and references of one report draft."""

    report_draft_id: str
    student_id: str
    report_type: str
    period_start: str
    period_end: str
    teacher_name: str
    overall_text: str
    subjects: tuple[ReportDraftSubjectRecord, ...]
    competency_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    chart_selections: tuple[ReportDraftChartSelectionRecord, ...]

    command_name: str = "report_draft.update"


@dataclass(frozen=True)
class GetLearningReportDraftQuery:
    """Load one persistent report draft by technical identity."""

    report_draft_id: str


@dataclass(frozen=True)
class ListLearningReportDraftsQuery:
    """List editable drafts for one student."""

    student_id: str


class ReportDraftApplicationService:
    """Application boundary for report-draft commands and queries."""

    def __init__(
        self,
        domain_service: ReportDraftService,
        repository: ReportDraftRepository,
    ) -> None:
        self.domain_service = domain_service
        self.repository = repository

    def create(
        self,
        command: CreateLearningReportDraftCommand,
    ) -> ReportDraftRecord:
        return self.domain_service.create_report_draft(
            student_id=command.student_id,
            report_type=command.report_type,
            period_start=command.period_start,
            period_end=command.period_end,
            teacher_name=command.teacher_name,
            overall_text=command.overall_text,
            subjects=command.subjects,
            competency_ids=command.competency_ids,
            observation_ids=command.observation_ids,
            chart_selections=command.chart_selections,
        )

    def update(
        self,
        command: UpdateLearningReportDraftCommand,
    ) -> ReportDraftRecord:
        return self.domain_service.update_report_draft(
            report_draft_id=command.report_draft_id,
            student_id=command.student_id,
            report_type=command.report_type,
            period_start=command.period_start,
            period_end=command.period_end,
            teacher_name=command.teacher_name,
            overall_text=command.overall_text,
            subjects=command.subjects,
            competency_ids=command.competency_ids,
            observation_ids=command.observation_ids,
            chart_selections=command.chart_selections,
        )

    def get(
        self,
        query: GetLearningReportDraftQuery,
    ) -> ReportDraftRecord | None:
        return self.repository.get_report_draft(query.report_draft_id.strip())

    def list_for_student(
        self,
        query: ListLearningReportDraftsQuery,
    ) -> tuple[ReportDraftRecord, ...]:
        return self.repository.list_report_drafts_for_student(query.student_id.strip())


@dataclass(frozen=True)
class PrepareLearningReportQuery:
    """Request the source data needed for one transient report draft."""

    student_id: str
    period_end: date


@dataclass(frozen=True)
class LearningReportSourceData:
    """Application-layer result before the report ViewModel projection."""

    student: object
    competency_statuses: tuple[object, ...]
    observations: tuple[object, ...]


class LearningReportApplicationService:
    """Coordinate existing read paths without deriving a second competency status."""

    def __init__(
        self,
        student_loader: Callable[[str, date], object | None],
        competency_status_loader: Callable[[str], tuple[object, ...]],
        observation_loader: Callable[[str], tuple[object, ...]],
    ) -> None:
        self.student_loader = student_loader
        self.competency_status_loader = competency_status_loader
        self.observation_loader = observation_loader

    def execute(
        self,
        query: PrepareLearningReportQuery,
    ) -> LearningReportSourceData | None:
        student_id = query.student_id.strip()
        if not student_id:
            return None
        student = self.student_loader(student_id, query.period_end)
        if student is None:
            return None
        return LearningReportSourceData(
            student=student,
            competency_statuses=self.competency_status_loader(student_id),
            observations=self.observation_loader(student_id),
        )
