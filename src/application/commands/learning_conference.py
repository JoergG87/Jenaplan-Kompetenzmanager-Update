"""Application commands and queries for learning-conference drafts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass

from src.core.learning_conference_draft import (
    LearningConferenceDraftRecord,
    LearningConferenceDraftRepository,
    LearningConferenceDraftService,
)
from src.core.learning_conference import (
    LearningConferenceCompletionResult,
    LearningConferenceCompletionService,
    LearningConferenceRevisionReadService,
    LearningConferenceRevisionState,
    LearningConferenceVerifiedRevision,
)
from src.core.learning_conference_pdf import (
    LearningConferencePdfArtifactRecord,
    LearningConferencePdfService,
)


@dataclass(frozen=True)
class LearningConferenceDraftInput:
    """Application input shared by create and update commands."""

    student_id: str
    period_start: str
    period_end: str
    conference_date: str
    responsible_teacher: str
    conversation_entry_text: str
    child_retrospective_text: str
    teacher_perspective_text: str
    strengths_text: str
    development_fields_text: str
    prepared_goals_text: str
    prepared_support_text: str
    prepared_agreements_text: str
    agreed_goals_text: str
    agreed_support_text: str
    agreed_agreements_text: str
    responsibilities_text: str
    next_review_date: str
    subject_ids: tuple[str, ...]
    cross_topic_keys: tuple[str, ...]
    competency_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    chart_types: tuple[str, ...]


@dataclass(frozen=True)
class CreateLearningConferenceDraftCommand:
    """Create one persistent LEG draft."""

    draft: LearningConferenceDraftInput
    command_name: str = "learning_conference_draft.create"


@dataclass(frozen=True)
class UpdateLearningConferenceDraftCommand:
    """Replace the editable contents and references of one LEG draft."""

    learning_conference_draft_id: str
    draft: LearningConferenceDraftInput
    command_name: str = "learning_conference_draft.update"


@dataclass(frozen=True)
class GetLearningConferenceDraftQuery:
    """Load one LEG draft by technical identity."""

    learning_conference_draft_id: str


@dataclass(frozen=True)
class ListLearningConferenceDraftsQuery:
    """List the editable LEG drafts for one student."""

    student_id: str


class LearningConferenceDraftApplicationService:
    """Application boundary for LEG-draft commands and queries."""

    def __init__(
        self,
        domain_service: LearningConferenceDraftService,
        repository: LearningConferenceDraftRepository,
    ) -> None:
        self.domain_service = domain_service
        self.repository = repository

    def create(
        self,
        command: CreateLearningConferenceDraftCommand,
    ) -> LearningConferenceDraftRecord:
        return self.domain_service.create_learning_conference_draft(
            **asdict(command.draft)
        )

    def update(
        self,
        command: UpdateLearningConferenceDraftCommand,
    ) -> LearningConferenceDraftRecord:
        return self.domain_service.update_learning_conference_draft(
            learning_conference_draft_id=command.learning_conference_draft_id,
            **asdict(command.draft),
        )

    def get(
        self,
        query: GetLearningConferenceDraftQuery,
    ) -> LearningConferenceDraftRecord | None:
        return self.repository.get_learning_conference_draft(
            query.learning_conference_draft_id.strip()
        )

    def list_for_student(
        self,
        query: ListLearningConferenceDraftsQuery,
    ) -> tuple[LearningConferenceDraftRecord, ...]:
        return self.repository.list_learning_conference_drafts_for_student(
            query.student_id.strip()
        )


@dataclass(frozen=True)
class PrepareLearningConferenceQuery:
    """Request the existing Live data needed for one LEG preparation."""

    student_id: str


@dataclass(frozen=True)
class LearningConferenceSourceData:
    """Application result before the LEG preparation ViewModel projection."""

    student: object
    competency_statuses: tuple[object, ...]
    observations: tuple[object, ...]


class LearningConferenceApplicationService:
    """Coordinate existing read paths without deriving a second status."""

    def __init__(
        self,
        student_loader: Callable[[str], object | None],
        competency_status_loader: Callable[[str], tuple[object, ...]],
        observation_loader: Callable[[str], tuple[object, ...]],
    ) -> None:
        self.student_loader = student_loader
        self.competency_status_loader = competency_status_loader
        self.observation_loader = observation_loader

    def execute(
        self,
        query: PrepareLearningConferenceQuery,
    ) -> LearningConferenceSourceData | None:
        student_id = query.student_id.strip()
        if not student_id:
            return None
        student = self.student_loader(student_id)
        if student is None:
            return None
        return LearningConferenceSourceData(
            student=student,
            competency_statuses=self.competency_status_loader(student_id),
            observations=self.observation_loader(student_id),
        )


@dataclass(frozen=True)
class CompleteLearningConferenceCommand:
    """Explicitly complete exactly one persisted LCD."""

    learning_conference_draft_id: str
    command_name: str = "learning_conference.complete"


@dataclass(frozen=True)
class GetLearningConferenceRevisionStateQuery:
    """Load completion state and history for one editable LCD."""

    learning_conference_draft_id: str


@dataclass(frozen=True)
class GetLearningConferenceRevisionQuery:
    """Load one immutable LCV after snapshot verification."""

    learning_conference_revision_id: str


class LearningConferenceCompletionApplicationService:
    """Application command boundary for the explicit LEG completion."""

    def __init__(self, domain_service: LearningConferenceCompletionService) -> None:
        self.domain_service = domain_service

    def complete(
        self,
        command: CompleteLearningConferenceCommand,
    ) -> LearningConferenceCompletionResult:
        return self.domain_service.complete(
            learning_conference_draft_id=command.learning_conference_draft_id
        )


class LearningConferenceRevisionApplicationService:
    """Application query boundary for snapshot-only LEG revision reads."""

    def __init__(self, read_service: LearningConferenceRevisionReadService) -> None:
        self.read_service = read_service

    def state_for_draft(
        self,
        query: GetLearningConferenceRevisionStateQuery,
    ) -> LearningConferenceRevisionState:
        return self.read_service.state_for_draft(
            query.learning_conference_draft_id
        )

    def get_revision(
        self,
        query: GetLearningConferenceRevisionQuery,
    ) -> LearningConferenceVerifiedRevision:
        return self.read_service.load_verified_revision(
            query.learning_conference_revision_id
        )


@dataclass(frozen=True)
class GenerateLearningConferencePdfCommand:
    """Generate or verify the immutable PDF artifact for one completed LCV."""

    learning_conference_revision_id: str
    command_name: str = "learning_conference_pdf.generate"


class LearningConferencePdfApplicationService:
    """Application boundary for final LEG PDF generation and lookup."""

    def __init__(self, domain_service: LearningConferencePdfService) -> None:
        self.domain_service = domain_service

    def generate(
        self,
        command: GenerateLearningConferencePdfCommand,
    ) -> LearningConferencePdfArtifactRecord:
        return self.domain_service.generate(command.learning_conference_revision_id)

    def load_for_revision(
        self,
        learning_conference_revision_id: str,
    ) -> LearningConferencePdfArtifactRecord | None:
        return self.domain_service.load_artifact(learning_conference_revision_id)
