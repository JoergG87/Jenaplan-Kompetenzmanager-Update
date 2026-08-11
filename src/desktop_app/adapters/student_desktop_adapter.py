"""Student adapter for the PySide6 desktop app."""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from pathlib import Path

from src.application.commands import (
    CreateObservationCommand,
    DeleteObservationCommand,
    UpdateObservationCommand,
)
from src.application.dispatcher import (
    ApplicationCommandDispatcher,
    ErrorResult,
    SuccessResult,
    observation_create_handler,
    observation_delete_handler,
    observation_update_handler,
)
from src.application.managed_documents import ManagedStudentDocumentService
from src.application.student_documentation_subjects import (
    StudentDocumentationSubjectService,
    effective_documentation_subjects,
)
from src.application.managed_pdf_artifacts import ManagedPdfArtifactLifecycle
from src.application.school_year_assignment import (
    ArchiveStudent,
    AssignmentApplicationError,
    ChangeStudentMembership,
    CreateStudentWithInitialEnrollment,
    ExitStudentFromSchoolYear,
    UpdateStudentMasterData,
)
from src.application.commands.report import (
    CreateLearningReportDraftCommand,
    FinalizeLearningReportCommand,
    GenerateLearningReportPdfCommand,
    GetLearningReportDraftQuery,
    LearningReportApplicationService,
    LearningReportPdfApplicationService,
    ListLearningReportDraftsQuery,
    PrepareLearningReportQuery,
    ReportDraftApplicationService,
    ReportFinalizationApplicationService,
    ReportRevisionApplicationService,
    UpdateLearningReportDraftCommand,
)
from src.application.commands.learning_conference import (
    CompleteLearningConferenceCommand,
    CreateLearningConferenceDraftCommand,
    GenerateLearningConferencePdfCommand,
    GetLearningConferenceDraftQuery,
    GetLearningConferenceRevisionQuery,
    GetLearningConferenceRevisionStateQuery,
    LearningConferenceApplicationService,
    LearningConferenceCompletionApplicationService,
    LearningConferenceDraftApplicationService,
    LearningConferenceDraftInput,
    LearningConferenceRevisionApplicationService,
    LearningConferencePdfApplicationService,
    ListLearningConferenceDraftsQuery,
    PrepareLearningConferenceQuery,
    UpdateLearningConferenceDraftCommand,
)
from src.core.observation import (
    ObservationCompetencyRatingRecord,
    ObservationRecord,
    ObservationService,
    ObservationValidator,
)
from src.core.observation_uow import (
    EncryptedObservationAttachmentRuntime,
    ensure_durable_directory,
    ObservationPersistenceUnitOfWork,
    ObservationWriterLock,
)
from src.core.managed_document_store import (
    ManagedDocumentStore,
    ManagedPdfArtifactError,
)
from src.core.maintenance_gate import product_writer
from src.core.sqlite_store import (
    SQLITE_SPIKE_PATH,
    SQLiteCourseRepository,
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteDocumentationSubjectSettingsRepository,
    SQLiteDocumentRepository,
    SQLiteGroupRepository,
    SQLiteLearningConferenceDraftRepository,
    SQLiteLearningConferencePdfArtifactRepository,
    SQLiteLearningConferenceRepository,
    SQLiteLearningReportRepository,
    SQLiteLearningReportPdfArtifactRepository,
    SQLiteObservationRepository,
    SQLitePersistenceEventRepository,
    SQLiteReportDraftRepository,
    SQLiteStudentCompetencyConfirmationRepository,
    SQLiteStudentDocumentationProjectionRepository,
    DocumentRecord,
    StudentCompetencyConfirmationRecord,
    StudentDocumentationProjectionBatch,
)
from src.core.report_draft import ReportDraftRecord, ReportDraftService
from src.core.learning_report import (
    LearningReportRevisionReadService,
    ReportFinalizationError,
    ReportFinalizationService,
)
from src.core.learning_report_pdf import (
    LearningReportPdfArtifactRecord,
    LearningReportPdfError,
    LearningReportPdfService,
)
from src.core.learning_conference_draft import (
    LearningConferenceDraftRecord,
    LearningConferenceDraftService,
)
from src.core.learning_conference import (
    LearningConferenceCompletionService,
    LearningConferenceRevisionReadService,
)
from src.core.learning_conference_pdf import (
    LearningConferencePdfArtifactRecord,
    LearningConferencePdfError,
    LearningConferencePdfOutputModelBuilder,
    LearningConferencePdfService,
)
from src.core.school_year import (
    AssignmentAtDateProjection,
    AssignmentResolutionStatus,
    CurrentStudentMembershipProjection,
    V3Student,
)
from src.core.student_documentation_subjects import DocumentationSubjectMode
from src.core.sqlite_school_year_assignment import (
    SchoolYearAssignmentReadSession,
    SchoolYearAssignmentRepositoryError,
    SchoolYearRepository,
    V3StudentRepository,
)
from src.core.records import CourseRecord, GroupRecord
from src.desktop_app.adapters.curriculum_desktop_adapter import (
    CurriculumDesktopAdapter,
    DOCUMENTATION_SUBJECT_PREFERRED_ORDER,
)
from src.desktop_app.view_models.master_data_view_model import course_color_from_key
from src.desktop_app.view_models.observation_view_model import (
    COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS,
    OBSERVATION_CROSS_SUBJECT_LABEL,
    OBSERVATION_RATING_SCORES,
    DOCUMENT_TYPE_OPTIONS,
    ObservationDraftViewModel,
    ObservationAttachmentDraft,
    ObservationCompetencyGroupViewModel,
    ObservationCompetencyOptionViewModel,
    ObservationCompetencyRatingDraft,
    ObservationCompetencySubjectGroupViewModel,
    ObservationLearningAreaGroupViewModel,
    ObservationListItem,
    ObservationRatingViewModel,
    ObservationSubjectOptionViewModel,
    StudentCompetencyEvidenceViewModel,
    StudentCompetencyCockpitViewModel,
    StudentDocumentationSubjectStatus,
    StudentDocumentationLearningAreaStatus,
    StudentCompetencyStatusViewModel,
    StudentCompetencySubjectGroup,
    StudentMissingCompetencyViewModel,
    build_student_competency_cockpit,
    calculated_rating_from_history,
    observation_rating_label,
)
from src.desktop_app.view_models.settings_view_model import (
    DocumentationSubjectOptionViewModel,
    SettingsViewModel,
)
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportDraftViewModel,
    LearningReportFinalizationPreviewViewModel,
    LearningReportPreparationViewModel,
    LearningReportRevisionStatusViewModel,
    LearningReportRevisionViewModel,
    LearningReportPdfArtifactViewModel,
    build_learning_report_finalization_preview,
    build_learning_report_preparation,
    build_learning_report_revision_status,
    build_learning_report_revision_view_model,
    build_learning_report_pdf_artifact_view_model,
)
from prototypes.pdf_engine.renderer import PdfRenderer
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceDraftViewModel,
    LearningConferencePreparationViewModel,
    LearningConferenceRevisionStatusViewModel,
    LearningConferenceRevisionViewModel,
    LearningConferencePdfArtifactViewModel,
    build_learning_conference_pdf_artifact_view_model,
    build_learning_conference_preparation,
    build_learning_conference_revision_status,
    build_learning_conference_revision_view_model,
)
from src.desktop_app.view_models.report_overview_view_model import (
    ReportOverviewViewModel,
    build_report_overview,
)
from src.desktop_app.view_models.student_view_model import (
    DashboardDocumentationCellViewModel,
    DashboardDocumentationGroupViewModel,
    DashboardDocumentationHeatmapViewModel,
    DashboardSuggestedStudentViewModel,
    GroupSummaryViewModel,
    StudentDetailViewModel,
    StudentProfileDashboardViewModel,
    StudentProfileProjectionBundle,
    StudentDocumentationSubjectOptionViewModel,
    StudentDocumentationSubjectProjectionViewModel,
    StudentDocumentationSummaryViewModel,
    StudentDocumentViewModel,
    StudentReportDevelopmentViewModel,
    StudentListItem,
    StudentReportCompetencyViewModel,
    StudentReportEvidenceViewModel,
    StudentReportPreviewViewModel,
    StudentReportSubjectSectionViewModel,
    build_student_profile_dashboard,
    documentation_summary_from_subjects,
    sort_student_list,
)

class StudentDesktopAdapter:
    """Thin adapter between Qt widgets and the application command layer."""

    def __init__(
        self,
        database_path: Path = SQLITE_SPIKE_PATH,
        *,
        database: SQLiteDatabase | None = None,
        database_create_allowed: bool = True,
        today_provider: Callable[[], date] | None = None,
        now_provider: Callable[[], datetime] | None = None,
        encrypted_observation_attachments: (
            EncryptedObservationAttachmentRuntime | None
        ) = None,
        managed_document_store: ManagedDocumentStore | None = None,
        managed_pdf_fault_hook: Callable[[str], None] | None = None,
    ) -> None:
        self.database_path = (
            Path(database.path) if database is not None else Path(database_path)
        )
        self.database = database or self._open_database(
            create=database_create_allowed
        )
        self._today_provider = today_provider or date.today
        self._now_provider = now_provider or (
            lambda: datetime.now().astimezone()
        )
        if (
            managed_document_store is not None
            and encrypted_observation_attachments is not None
            and managed_document_store is not encrypted_observation_attachments
        ):
            raise ValueError("All managed documents must use the same store.")
        self._managed_document_store = managed_document_store
        self._managed_pdf_fault_hook = managed_pdf_fault_hook
        self._encrypted_observation_attachments = (
            managed_document_store or encrypted_observation_attachments
        )
        self._managed_documents = (
            None
            if managed_document_store is None
            else ManagedStudentDocumentService(
                database=self.database,
                store=managed_document_store,
                now_provider=self._now_provider,
            )
        )
        self._observation_recovery_suspended = 0
        if self._managed_documents is not None:
            self._managed_documents.recover_pending()
            self._learning_report_managed_pdf_lifecycle().recover_pending()
            self._learning_conference_managed_pdf_lifecycle().recover_pending()
        self._observation_uow().recover_pending()

    def list_students(
        self,
        *,
        group_id: str | None = None,
        group_ids: tuple[str, ...] = (),
        course_id: str | None = None,
        course_ids: tuple[str, ...] = (),
        course_group_id: str | None = None,
    ) -> tuple[StudentListItem, ...]:
        """Return students with readable group and course names."""
        self._recover_observation_uow()
        as_of = self._today()
        batch = SQLiteStudentDocumentationProjectionRepository(
            self.database
        ).read_batch(
            as_of=as_of,
            group_id=group_id,
            group_ids=group_ids,
            course_id=course_id,
            course_ids=course_ids,
            course_group_id=course_group_id,
        )
        course_records = batch.courses
        courses = {course.course_id: course for course in course_records}
        course_order_by_id = {
            course.course_id: index
            for index, course in enumerate(course_records)
        }
        documentation_statuses_by_student = (
            self._documentation_statuses_by_student(batch)
        )
        loaded_students = tuple(
            self._student_list_item(
                student,
                batch.memberships_by_student[student.student_id],
                courses,
                documentation_summary_from_subjects(
                    documentation_statuses_by_student.get(
                        student.student_id,
                        (),
                    )
                ),
            )
            for student in batch.students
        )
        return sort_student_list(loaded_students, course_order_by_id)

    def get_student_profile(
        self,
        student_id: str,
        *,
        reference_date: date | None = None,
    ) -> StudentDetailViewModel | None:
        """Return a light profile view model for one student."""
        self._recover_observation_uow()
        as_of = reference_date if reference_date is not None else self._today()
        batch = SQLiteStudentDocumentationProjectionRepository(
            self.database
        ).read_batch(
            as_of=as_of,
            student_id=student_id,
            historical_membership=reference_date is not None,
        )
        return self._student_profile_from_batch(
            batch,
            student_id,
            historical=reference_date is not None,
        )

    def student_profile_projection_bundle(
        self,
        student_id: str,
    ) -> StudentProfileProjectionBundle:
        """Compose one profile navigation from a single read snapshot."""
        self._recover_observation_uow()
        as_of = self._today()
        batch = SQLiteStudentDocumentationProjectionRepository(
            self.database
        ).read_batch(
            as_of=as_of,
            student_id=student_id,
            include_documents=True,
        )
        student = self._student_profile_from_batch(
            batch,
            student_id,
            historical=False,
        )
        source_documents = batch.documents_by_student.get(student_id, ())
        documents = tuple(
            self._document_view_model(document)
            for document in source_documents
        )
        observations = self._observation_list_items_from_batch(
            batch,
            student_id,
            documents=source_documents,
        )
        statuses = self._competency_status_projection_from_batch(
            batch,
            student_id,
        )
        documented_ids = {
            status.competency_id
            for status in statuses
            if status.documentation_state != "undocumented"
        }
        active_current_competencies = tuple(
            competency
            for competency in batch.competencies
            if competency.active and competency.catalog_status == "current"
        )
        documentation_subjects = self._student_documentation_subject_projection_from_batch(
            batch,
            student_id,
            student_is_read_only=(student is None or not student.active),
        )
        active_documentation_subject_ids = set(
            documentation_subjects.selected_subject_ids
        )
        documentation_competencies = tuple(
            competency
            for competency in active_current_competencies
            if competency.subject_id in active_documentation_subject_ids
        )
        documentation_statuses = self._documentation_statuses(
            documentation_competencies,
            documented_ids,
        )
        competency_groups = self._group_competency_statuses(
            tuple(
                status
                for status in statuses
                if status.documentation_state != "undocumented"
            ),
            active_current_competencies,
            documented_ids,
            active_documentation_subject_ids,
        )
        return StudentProfileProjectionBundle(
            student=student,
            observations=observations,
            competency_groups=competency_groups,
            documentation_statuses=documentation_statuses,
            documents=documents,
            competency_cockpit=build_student_competency_cockpit(
                statuses,
                tuple(active_documentation_subject_ids),
            ),
            profile_dashboard=build_student_profile_dashboard(
                statuses,
                documentation_statuses,
                as_of,
            ),
            documentation_subjects=documentation_subjects,
        )

    def _student_profile_from_batch(
        self,
        batch: StudentDocumentationProjectionBatch,
        student_id: str,
        *,
        historical: bool,
        neutral_without_membership: bool = False,
    ) -> StudentDetailViewModel | None:
        student = next(
            (
                candidate
                for candidate in batch.students
                if candidate.student_id == student_id
            ),
            None,
        )
        membership = batch.memberships_by_student.get(student_id)
        if student is None:
            return None
        if neutral_without_membership:
            return StudentDetailViewModel(
                student_id=student.student_id,
                display_name=f"{student.first_name} {student.last_name}",
                group_name="",
                course_name="",
                student_notes=student.notes,
                active=student.active,
                resolution_status=(
                    AssignmentResolutionStatus.NO_ASSIGNMENT.value
                ),
                status_label="Zuordnung noch nicht aufgelöst",
                membership_blocking=False,
            )
        if membership is None:
            return None
        courses = {course.course_id: course for course in batch.courses}
        course_name, course_color_name, course_color_hex = (
            self._course_context(
                membership.course_id,
                courses,
                membership.course_name or "",
            )
            if membership.course_id is not None
            else ("", "", "")
        )
        resolution_status = membership.resolution_status
        if (
            not historical
            and membership.student_archived
        ):
            resolution_status = AssignmentResolutionStatus.STUDENT_ARCHIVED
        status_label, membership_blocking = self._membership_status(
            resolution_status,
            historical=historical,
        )
        return StudentDetailViewModel(
            student.student_id,
            f"{student.first_name} {student.last_name}",
            self._membership_group_name(
                membership,
                status_label=status_label,
                historical=historical,
            ),
            course_name,
            student.notes,
            student.active,
            course_color_name,
            course_color_hex,
            resolution_status.value,
            status_label,
            membership_blocking,
        )

    def student_record_for_edit(self, student_id: str) -> V3Student | None:
        """Return only V3 master data for the edit dialog."""
        with self.database.connect() as connection:
            return V3StudentRepository(connection).get_by_id(student_id)

    def list_group_summaries(self) -> tuple[GroupSummaryViewModel, ...]:
        """Return group cards for the app overview."""
        batch = SQLiteStudentDocumentationProjectionRepository(
            self.database
        ).read_batch(as_of=self._today())
        return tuple(
            GroupSummaryViewModel(
                group.group_id,
                group.group_name,
                batch.group_counts.get(group.group_id, 0),
            )
            for group in batch.groups
        )

    def dashboard_documentation_heatmap(
        self,
    ) -> DashboardDocumentationHeatmapViewModel:
        """Aggregate canonical documentation coverage by group and subject."""
        batch = SQLiteStudentDocumentationProjectionRepository(
            self.database
        ).read_batch(as_of=self._today())
        return self._dashboard_documentation_heatmap_from_batch(batch)

    def dashboard_documentation_refresh(
        self,
        *,
        target_type: str = "",
        target_id: str = "",
        subject_id: str = "",
        subject_label: str = "",
        at: datetime,
        limit: int = 5,
    ) -> tuple[
        DashboardDocumentationHeatmapViewModel,
        tuple[DashboardSuggestedStudentViewModel, ...],
    ]:
        """Return heatmap and lesson suggestions from one refresh-local batch."""
        as_of = at.date()
        batch = SQLiteStudentDocumentationProjectionRepository(
            self.database
        ).read_batch(
            as_of=as_of,
            target_group_id=target_id if target_type == "group" else None,
            target_course_id=target_id if target_type == "course" else None,
            target_course_group_id=(
                target_id if target_type == "course_group" else None
            ),
        )
        heatmap = self._dashboard_documentation_heatmap_from_batch(batch)
        if limit <= 0 or not subject_id:
            return heatmap, ()
        if target_type not in {"group", "course", "course_group"}:
            return heatmap, ()
        return (
            heatmap,
            self._dashboard_suggestions_from_batch(
                batch,
                target_student_ids=batch.target_student_ids,
                subject_id=subject_id,
                subject_label=subject_label,
                at_date=as_of,
                limit=limit,
            ),
        )

    def _dashboard_documentation_heatmap_from_batch(
        self,
        batch: StudentDocumentationProjectionBatch,
    ) -> DashboardDocumentationHeatmapViewModel:
        statuses_by_student = self._documentation_statuses_by_student(batch)
        groups: list[DashboardDocumentationGroupViewModel] = []
        for group in batch.groups:
            group_students = tuple(
                student
                for student in batch.students
                if (
                    batch.memberships_by_student[student.student_id].group_id
                    == group.group_id
                )
            )
            subject_totals: dict[str, list[object]] = {}
            for student in group_students:
                for status in statuses_by_student[student.student_id]:
                    values = subject_totals.setdefault(
                        status.subject_id,
                        [status.subject_display_name, 0, 0, status.sort_order],
                    )
                    values[1] = int(values[1]) + int(status.documented_count > 0)
                    values[2] = int(values[2]) + 1
                    values[3] = min(int(values[3]), status.sort_order)
            cells = tuple(
                DashboardDocumentationCellViewModel(
                    subject_id,
                    str(values[0]),
                    int(values[1]),
                    int(values[2]),
                )
                for subject_id, values in sorted(
                    subject_totals.items(),
                    key=lambda item: (int(item[1][3]), str(item[1][0]).casefold()),
                )
            )
            groups.append(
                DashboardDocumentationGroupViewModel(
                    group.group_id,
                    group.group_name,
                    cells,
                )
            )
        return DashboardDocumentationHeatmapViewModel(tuple(groups))

    def list_dashboard_suggested_students(
        self,
        *,
        target_type: str,
        target_id: str,
        subject_id: str,
        subject_label: str,
        at: datetime,
        limit: int = 5,
    ) -> tuple[DashboardSuggestedStudentViewModel, ...]:
        """Return neutral, date-based documentation suggestions for one lesson."""
        if limit <= 0 or not subject_id:
            return ()
        as_of = at.date()
        batch = SQLiteStudentDocumentationProjectionRepository(
            self.database
        ).read_batch(
            as_of=as_of,
            target_group_id=target_id if target_type == "group" else None,
            target_course_id=target_id if target_type == "course" else None,
            target_course_group_id=(
                target_id if target_type == "course_group" else None
            ),
        )
        if target_type not in {"group", "course", "course_group"}:
            return ()
        return self._dashboard_suggestions_from_batch(
            batch,
            target_student_ids=batch.target_student_ids,
            subject_id=subject_id,
            subject_label=subject_label,
            at_date=as_of,
            limit=limit,
        )

    def _dashboard_suggestions_from_batch(
        self,
        batch: StudentDocumentationProjectionBatch,
        *,
        target_student_ids: tuple[str, ...],
        subject_id: str,
        subject_label: str,
        at_date: date,
        limit: int,
    ) -> tuple[DashboardSuggestedStudentViewModel, ...]:
        courses = {course.course_id: course for course in batch.courses}
        target_student_id_set = frozenset(target_student_ids)
        students = tuple(
            student
            for student in batch.students
            if student.student_id in target_student_id_set
        )
        suggestions = tuple(
            self._dashboard_suggestion_for_student(
                student,
                batch.memberships_by_student[student.student_id],
                subject_id,
                subject_label,
                at_date,
                courses,
                batch.observations_by_student.get(student.student_id, ()),
            )
            for student in students
        )
        return tuple(
            sorted(
                suggestions,
                key=lambda item: (
                    self._dashboard_suggestion_priority(item, at_date),
                    item.last_documentation_date or date.min,
                    item.display_name.casefold(),
                    item.student_id,
                ),
            )[:limit]
        )

    def _dashboard_suggestion_for_student(
        self,
        student: V3Student,
        membership: CurrentStudentMembershipProjection,
        subject_id: str,
        subject_label: str,
        at_date: date,
        courses: dict[str, CourseRecord],
        observations: tuple[object, ...],
    ) -> DashboardSuggestedStudentViewModel:
        observation_dates = tuple(
            observation_date
            for observation in observations
            if self._observation_has_dashboard_subject(observation, subject_id)
            for observation_date in (date.fromisoformat(observation.date),)
            if observation_date <= at_date
        )
        display_name = f"{student.first_name} {student.last_name}"
        course_name, course_color_name, course_color_hex = self._course_context(
            membership.course_id or "",
            courses,
            membership.course_name or "",
        )
        if not observation_dates:
            return DashboardSuggestedStudentViewModel(
                student_id=student.student_id,
                display_name=display_name,
                documentation_hint=f"Noch keine Dokumentation in {subject_label}",
                course_name=course_name,
                course_color_name=course_color_name,
                course_color_hex=course_color_hex,
            )
        last_date = max(observation_dates)
        days_since = (at_date - last_date).days
        if days_since == 0:
            hint = "Heute bereits dokumentiert"
        elif days_since == 1:
            hint = "Letzte Beobachtung vor 1 Tag"
        else:
            hint = f"Letzte Beobachtung vor {days_since} Tagen"
        return DashboardSuggestedStudentViewModel(
            student_id=student.student_id,
            display_name=display_name,
            documentation_hint=hint,
            last_documentation_date=last_date,
            documented_today=days_since == 0,
            course_name=course_name,
            course_color_name=course_color_name,
            course_color_hex=course_color_hex,
        )

    @staticmethod
    def _dashboard_suggestion_priority(
        suggestion: DashboardSuggestedStudentViewModel,
        at_date: date,
    ) -> int:
        if suggestion.last_documentation_date is None:
            return 0
        if suggestion.last_documentation_date == at_date:
            return 2
        return 1

    @staticmethod
    def _observation_has_dashboard_subject(
        observation: object,
        subject_id: str,
    ) -> bool:
        ratings = tuple(getattr(observation, "competency_ratings", ()))
        if ratings:
            return subject_id in {
                getattr(rating, "subject_id", "") for rating in ratings
            }
        quick_subject_id = str(getattr(observation, "subject_id", "")).strip()
        return bool(
            quick_subject_id
            and quick_subject_id != "cross_subject"
            and quick_subject_id == subject_id
        )

    def list_groups(self) -> tuple[GroupRecord, ...]:
        """Return active groups for app navigation and dropdowns."""
        return tuple(
            group
            for group in SQLiteGroupRepository(self.database).list_groups()
            if group.active
        )

    def list_courses(self) -> tuple[CourseRecord, ...]:
        """Return active courses for app navigation and dropdowns."""
        return tuple(
            course
            for course in SQLiteCourseRepository(self.database).list_courses()
            if course.active
        )

    def settings_view_model(self) -> SettingsViewModel:
        """Return app settings display data."""
        return SettingsViewModel(self.list_documentation_subject_options())

    def list_documentation_subject_options(
        self,
    ) -> tuple[DocumentationSubjectOptionViewModel, ...]:
        """Return selectable documentation subjects from the active catalog."""
        competencies = tuple(
            competency
            for competency in SQLiteCompetencyRepository(self.database).list_competencies()
            if competency.active
        )
        selected_subject_ids = set(
            SQLiteDocumentationSubjectSettingsRepository(
                self.database
            ).list_active_documentation_subject_ids()
        )
        subject_labels: dict[str, str] = {}
        subject_sort_order: dict[str, int] = {}
        for competency in competencies:
            subject_labels.setdefault(competency.subject_id, competency.subject_name)
            current_sort_order = subject_sort_order.get(competency.subject_id)
            if current_sort_order is None or competency.sort_order < current_sort_order:
                subject_sort_order[competency.subject_id] = competency.sort_order

        return tuple(
            DocumentationSubjectOptionViewModel(
                subject_id=subject_id,
                label=subject_labels[subject_id],
                selected=subject_id in selected_subject_ids,
            )
            for subject_id in sorted(
                subject_labels,
                key=lambda value: self._documentation_subject_sort_key(
                    value,
                    subject_labels,
                    subject_sort_order,
                ),
            )
        )

    def _student_documentation_subject_projection_from_batch(
        self,
        batch: StudentDocumentationProjectionBatch,
        student_id: str,
        *,
        student_is_read_only: bool,
    ) -> StudentDocumentationSubjectProjectionViewModel:
        subject_labels: dict[str, str] = {}
        subject_sort_orders: dict[str, int] = {}
        known_subject_ids: set[str] = set()
        catalog_subject_labels: dict[str, str] = {}
        for competency in batch.competencies:
            known_subject_ids.add(competency.subject_id)
            catalog_subject_labels.setdefault(
                competency.subject_id,
                competency.subject_name,
            )
            if not competency.active:
                continue
            subject_labels.setdefault(competency.subject_id, competency.subject_name)
            subject_sort_orders[competency.subject_id] = min(
                subject_sort_orders.get(competency.subject_id, competency.sort_order),
                competency.sort_order,
            )
        ordered_subject_ids = tuple(
            sorted(
                subject_labels,
                key=lambda value: self._documentation_subject_sort_key(
                    value,
                    subject_labels,
                    subject_sort_orders,
                ),
            )
        )
        available = tuple(
            StudentDocumentationSubjectOptionViewModel(
                subject_id,
                subject_labels[subject_id],
            )
            for subject_id in ordered_subject_ids
            if subject_id not in COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS
        )
        configuration = batch.student_documentation_subject_configurations.get(
            student_id
        )
        if (
            configuration is None
            or batch.current_school_year_id is None
            or batch.current_school_year_label is None
        ):
            return StudentDocumentationSubjectProjectionViewModel(
                "",
                "Kein aktuelles Schuljahr",
                DocumentationSubjectMode.INHERIT.value,
                available,
                (),
                True,
            )
        selected = tuple(
            subject_id
            for subject_id in effective_documentation_subjects(
            configuration,
            batch.active_documentation_subject_ids,
            known_subject_ids=known_subject_ids,
            )
            if subject_id not in COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS
        )
        retained_inactive = tuple(
            StudentDocumentationSubjectOptionViewModel(
                subject_id,
                catalog_subject_labels[subject_id],
            )
            for subject_id in selected
            if subject_id not in subject_labels
            and subject_id not in COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS
        )
        return StudentDocumentationSubjectProjectionViewModel(
            batch.current_school_year_id,
            batch.current_school_year_label,
            configuration.mode.value,
            available,
            selected,
            student_is_read_only,
            retained_inactive,
        )

    @product_writer
    def save_student_documentation_subjects(
        self,
        student_id: str,
        school_year_id: str,
        mode: str,
        subject_ids: tuple[str, ...],
    ) -> None:
        """Persist one complete student/year selection through the application service."""
        service = self._student_documentation_subject_service()
        if DocumentationSubjectMode(mode) is DocumentationSubjectMode.INHERIT:
            service.set_mode(
                student_id,
                school_year_id,
                DocumentationSubjectMode.INHERIT,
            )
            return
        service.replace_custom_subjects(student_id, school_year_id, subject_ids)

    @product_writer
    def save_active_documentation_subjects(
        self,
        subject_ids: tuple[str, ...],
    ) -> None:
        """Persist the complete documentation-subject selection."""
        SQLiteDocumentationSubjectSettingsRepository(
            self.database
        ).save_active_documentation_subject_ids(subject_ids)

    def list_observation_subject_options(
        self,
        initial_draft: ObservationDraftViewModel | None = None,
    ) -> tuple[ObservationSubjectOptionViewModel, ...]:
        """Return subject options for the observation dialog."""
        options = [
            ObservationSubjectOptionViewModel(option.subject_id, option.label)
            for option in self.list_documentation_subject_options()
            if option.selected
        ]
        existing_subject_keys = {option.subject_key for option in options}
        initial_subjects = (
            tuple(
                (rating.subject_key, rating.subject_display_name)
                for rating in initial_draft.competency_ratings
                if rating.subject_key
            )
            if initial_draft is not None and initial_draft.competency_ratings
            else (
                (
                    self._initial_observation_subject_key(initial_draft),
                    self._initial_observation_subject_label(initial_draft),
                ),
            )
        )
        for subject_key, subject_label in initial_subjects:
            if not subject_key or subject_key in existing_subject_keys:
                continue
            options.append(
                ObservationSubjectOptionViewModel(
                    subject_key,
                    f"{subject_label or subject_key} (nicht dokumentationsrelevant)",
                )
            )
            existing_subject_keys.add(subject_key)
        return tuple(options)

    def list_observation_competency_subject_groups(
        self,
        initial_draft: ObservationDraftViewModel | None = None,
    ) -> tuple[ObservationCompetencySubjectGroupViewModel, ...]:
        """Return active and persisted observation competencies for dialog rendering."""
        selected_ratings = {
            rating.competency_id: rating.rating
            for rating in (initial_draft.competency_ratings if initial_draft else ())
            if rating.competency_id
        }
        curriculum_adapter = CurriculumDesktopAdapter(database=self.database)
        catalog_entries = curriculum_adapter.list_entries()
        subject_groups: list[ObservationCompetencySubjectGroupViewModel] = []
        for subject_option in self.list_observation_subject_options(initial_draft):
            learning_area_groups: dict[
                str,
                dict[str, list[ObservationCompetencyOptionViewModel]],
            ] = {}
            for competency in catalog_entries:
                is_selected = competency.competency_id in selected_ratings
                is_current_catalog_option = (
                    competency.is_active and competency.catalog_status == "current"
                )
                if competency.subject_key != subject_option.subject_key or (
                    not is_current_catalog_option and not is_selected
                ):
                    continue
                option = ObservationCompetencyOptionViewModel(
                    competency_id=competency.competency_id,
                    subject_key=competency.subject_key,
                    subject_display_name=competency.subject_display_name,
                    learning_area=competency.learning_area,
                    competency_group=competency.competency_group,
                    competency_text=competency.competency_text,
                    competency_label=competency.competency_label,
                    selected=is_selected,
                    rating=selected_ratings.get(competency.competency_id, ""),
                    learning_stage=competency.learning_stage,
                    catalog_status=competency.catalog_status,
                    is_active=competency.is_active,
                    sort_order=competency.sort_order,
                )
                learning_area_groups.setdefault(
                    competency.learning_area,
                    {},
                ).setdefault(competency.competency_group, []).append(option)
            subject_groups.append(
                ObservationCompetencySubjectGroupViewModel(
                    subject_key=subject_option.subject_key,
                    subject_display_name=subject_option.display_name,
                    learning_area_groups=tuple(
                        ObservationLearningAreaGroupViewModel(
                            learning_area,
                            tuple(
                                ObservationCompetencyGroupViewModel(
                                    competency_group,
                                    tuple(sorted(
                                        competencies,
                                        key=lambda item: (
                                            item.sort_order,
                                            item.competency_id,
                                        ),
                                    )),
                                )
                                for competency_group, competencies in sorted(
                                    competency_groups.items(),
                                    key=lambda item: min(
                                        competency.sort_order
                                        for competency in item[1]
                                    ),
                                )
                            ),
                        )
                        for learning_area, competency_groups in sorted(
                            learning_area_groups.items(),
                            key=lambda item: min(
                                competency.sort_order
                                for competencies in item[1].values()
                                for competency in competencies
                            ),
                        )
                    ),
                )
            )
        return tuple(subject_groups)

    def list_recent_observation_competencies(
        self,
        student_id: str,
        initial_draft: ObservationDraftViewModel | None = None,
    ) -> tuple[ObservationCompetencyOptionViewModel, ...]:
        """Return up to four newest distinct active current competencies."""
        current_competencies = {
            competency.competency_id: competency
            for subject_group in self.list_observation_competency_subject_groups(
                initial_draft
            )
            for learning_area_group in subject_group.learning_area_groups
            for competency_group in learning_area_group.competency_groups
            for competency in competency_group.competencies
            if competency.is_active and competency.catalog_status == "current"
        }
        recent_competencies: list[ObservationCompetencyOptionViewModel] = []
        seen_competency_ids: set[str] = set()
        for observation in SQLiteObservationRepository(
            self.database
        ).list_observations_for_student(student_id):
            for rating in observation.competency_ratings:
                competency_id = rating.competency_id
                if competency_id in seen_competency_ids:
                    continue
                seen_competency_ids.add(competency_id)
                competency = current_competencies.get(competency_id)
                if competency is not None:
                    recent_competencies.append(competency)
                    if len(recent_competencies) == 4:
                        return tuple(recent_competencies)
        return tuple(recent_competencies)

    def group_id_by_name(self) -> dict[str, str]:
        """Map visible group names to stable group IDs."""
        return {group.group_name: group.group_id for group in self.list_groups()}

    def course_id_by_name(self) -> dict[str, str]:
        """Map visible course names to stable course IDs."""
        return {course.course_name: course.course_id for course in self.list_courses()}

    def current_school_year(self):
        """Return the single centrally registered current school year."""
        with self.database.connect() as connection:
            try:
                return SchoolYearRepository(connection).require_current()
            except SchoolYearAssignmentRepositoryError:
                return None

    def operation_date(self) -> date:
        """Return the adapter-owned explicit date for one UI operation."""
        return self._today()

    def current_membership_for_student(
        self,
        student_id: str,
        *,
        as_of: date | None = None,
    ) -> CurrentStudentMembershipProjection:
        """Resolve one membership at the explicit or adapter-owned reference day."""
        reference = self._today() if as_of is None else as_of
        with self.database.connect() as connection:
            connection.execute("BEGIN")
            try:
                return SchoolYearAssignmentReadSession(
                    connection
                ).current_membership(student_id, as_of=reference)
            finally:
                connection.rollback()

    @product_writer
    def save_new_student(
        self,
        *,
        first_name: str,
        last_name: str,
        group_id: str,
        course_id: str,
        student_notes: str = "",
    ) -> object:
        """Create V3 master data and its initial assignment atomically."""
        current = self.current_school_year()
        if current is None:
            return ErrorResult(
                "student.create",
                "Es ist kein aktuelles Schuljahr festgelegt.",
                AssignmentApplicationError.__name__,
            )
        effective = self._today()
        if not current.start_date <= effective <= current.end_date:
            return ErrorResult(
                "student.create",
                "Das aktuelle Schuljahr umfasst den heutigen Tag nicht.",
                AssignmentApplicationError.__name__,
            )
        try:
            created = CreateStudentWithInitialEnrollment(
                self.database.connect,
                now_provider=self._now,
            ).execute(
                first_name=first_name,
                last_name=last_name,
                notes=student_notes,
                school_year_id=current.school_year_id,
                valid_from=effective,
                valid_to=current.end_date,
                group_id=group_id,
                course_id=course_id,
            )
            return SuccessResult("student.create", created.student)
        except Exception as error:
            return self._student_lifecycle_error("student.create", error)

    @product_writer
    def save_existing_student(
        self,
        *,
        student_id: str,
        first_name: str,
        last_name: str,
        student_notes: str = "",
    ) -> object:
        """Persist only V3 student master data; never change membership."""
        try:
            updated = UpdateStudentMasterData(
                self.database.connect,
                now_provider=self._now,
            ).execute(
                student_id,
                first_name=first_name,
                last_name=last_name,
                notes=student_notes,
            )
            return SuccessResult("student.update_master_data", updated)
        except Exception as error:
            return self._student_lifecycle_error(
                "student.update_master_data",
                error,
            )

    @product_writer
    def change_student_membership(
        self,
        student_id: str,
        *,
        effective_on: date,
        group_id: str | None,
        course_id: str,
    ) -> object:
        """Apply one explicit dated V3 membership change atomically."""
        try:
            changed = ChangeStudentMembership(
                self.database.connect,
                now_provider=self._now,
            ).execute(
                student_id,
                effective_on=effective_on,
                group_id=group_id,
                course_id=course_id,
            )
            return SuccessResult("student.membership.change", changed)
        except Exception as error:
            return self._student_lifecycle_error(
                "student.membership.change",
                error,
            )

    @product_writer
    def exit_student_from_school_year(
        self,
        student_id: str,
        *,
        effective_on: date,
    ) -> object:
        """End enrollment without archiving the student."""
        try:
            exited = ExitStudentFromSchoolYear(
                self.database.connect,
                now_provider=self._now,
            ).execute(student_id, effective_on=effective_on)
            return SuccessResult("student.membership.exit", exited)
        except Exception as error:
            return self._student_lifecycle_error(
                "student.membership.exit",
                error,
            )

    @product_writer
    def archive_student_master_data(self, student_id: str) -> object:
        """Archive master data without changing an assignment."""
        reference = self._today()
        try:
            archived = ArchiveStudent(
                self.database.connect,
                now_provider=self._now,
            ).execute(
                student_id,
                as_of=reference,
            )
            return SuccessResult("student.archive", archived)
        except Exception as error:
            return self._student_lifecycle_error("student.archive", error)

    @staticmethod
    def _student_lifecycle_error(
        command_name: str,
        error: Exception,
    ) -> ErrorResult:
        code = str(getattr(error, "code", ""))
        messages = {
            "student_first_name_invalid": "Bitte einen Vornamen eingeben.",
            "student_last_name_invalid": "Bitte einen Nachnamen eingeben.",
            "current_school_year_missing": (
                "Es ist kein aktuelles Schuljahr festgelegt."
            ),
            "current_school_year_ambiguous": (
                "Das aktuelle Schuljahr ist nicht eindeutig."
            ),
            "group_invalid": "Die gewählte Stammgruppe ist nicht verfügbar.",
            "group_inactive": "Die gewählte Stammgruppe ist nicht aktiv.",
            "course_invalid": "Der gewählte Kurs ist nicht verfügbar.",
            "course_inactive": "Der gewählte Kurs ist nicht aktiv.",
            "course_year_level_invalid": (
                "Für den gewählten Kurs fehlt eine gültige Kursstufe."
            ),
            "assignment_missing": "Für dieses Kind fehlt die aktuelle Zuordnung.",
            "assignment_ambiguous": (
                "Die aktuelle Zuordnung dieses Kindes ist nicht eindeutig."
            ),
            "membership_change_on_first_interval_day": (
                "Am ersten Tag der bestehenden Zuordnung ist kein Wechsel möglich."
            ),
            "membership_exit_on_first_interval_day": (
                "Am ersten Tag der bestehenden Zuordnung ist kein Austritt möglich."
            ),
            "active_enrollment_blocks_archive": (
                "Vor der Archivierung muss die Einschreibung bewusst beendet werden."
            ),
            "archive_timestamp_precedes_student_update": (
                "Die Archivierung wurde zum Schutz neuerer Stammdaten blockiert."
            ),
            "student_missing_or_archived": (
                "Das Kind ist nicht verfügbar oder bereits archiviert."
            ),
        }
        return ErrorResult(
            command_name,
            messages.get(
                code,
                "Die Änderung konnte nicht vollständig gespeichert werden.",
            ),
            type(error).__name__,
        )

    def create_observation_command(
        self,
        draft: ObservationDraftViewModel,
    ) -> CreateObservationCommand:
        """Create an observation command from GUI draft state."""
        return CreateObservationCommand(
            student_id=draft.student_id,
            date=draft.date_text,
            subject_id=self._subject_id_for_draft(draft),
            context=draft.context,
            note=draft.note,
            competency_ratings=self._rating_records_from_draft(draft),
            is_quick_observation=draft.is_quick_observation,
        )

    @product_writer
    def save_observation(self, draft: ObservationDraftViewModel) -> object:
        """Persist observation and attachments through one recoverable unit."""
        command = self.create_observation_command(draft)
        try:
            self._validate_observation_command(command)
            timestamp = datetime.now(UTC).replace(microsecond=0).isoformat()
            observation = ObservationRecord(
                "",
                command.student_id.strip(),
                command.date.strip(),
                command.subject_id.strip(),
                command.context.strip(),
                command.note,
                True,
                timestamp,
                timestamp,
                command.competency_ratings,
            )
            saved = self._observation_uow().save(
                observation=observation,
                attachments=draft.attachments,
                operation_token=draft.operation_token,
                create=True,
            )
            return SuccessResult(command.command_name, saved)
        except Exception as error:
            return ErrorResult(
                command.command_name,
                str(error),
                type(error).__name__,
            )

    def create_update_observation_command(
        self,
        draft: ObservationDraftViewModel,
    ) -> UpdateObservationCommand:
        """Create an update command from GUI draft state."""
        return UpdateObservationCommand(
            observation_id=draft.observation_id,
            student_id=draft.student_id,
            date=draft.date_text,
            subject_id=self._subject_id_for_draft(draft),
            context=draft.context,
            note=draft.note,
            competency_ratings=self._rating_records_from_draft(draft),
            is_quick_observation=draft.is_quick_observation,
        )

    @product_writer
    def update_observation(self, draft: ObservationDraftViewModel) -> object:
        """Update observation and attachments through one recoverable unit."""
        command = self.create_update_observation_command(draft)
        try:
            self._validate_observation_command(command)
            existing = SQLiteObservationRepository(self.database).get_observation(
                command.observation_id
            )
            if existing is None:
                raise ValueError(
                    f"observation_id nicht gefunden: {command.observation_id}"
                )
            candidate = ObservationRecord(
                command.observation_id,
                command.student_id.strip(),
                command.date.strip(),
                command.subject_id.strip(),
                command.context.strip(),
                command.note,
                True,
                existing.created_at,
                existing.updated_at,
                command.competency_ratings,
            )
            observation = ObservationRecord(
                candidate.observation_id,
                candidate.student_id,
                candidate.date,
                candidate.subject_id,
                candidate.context,
                candidate.note,
                candidate.active,
                candidate.created_at,
                datetime.now(UTC).replace(microsecond=0).isoformat(),
                candidate.competency_ratings,
            )
            saved = self._observation_uow().save(
                observation=observation,
                attachments=draft.attachments,
                operation_token=draft.operation_token,
                create=False,
            )
            return SuccessResult(command.command_name, saved)
        except Exception as error:
            return ErrorResult(
                command.command_name,
                str(error),
                type(error).__name__,
            )

    @product_writer
    def delete_observation(self, observation_id: str) -> object:
        """Soft-delete an observation through the application stack."""
        command = DeleteObservationCommand(observation_id=observation_id)
        return self._dispatcher().dispatch(command)

    def read_encrypted_observation_attachment(
        self,
        *,
        document_id: str,
        consumer: object,
    ) -> object:
        """Stream an active encrypted observation attachment by its MED-ID."""
        return self._observation_uow().read_encrypted_attachment(
            document_id=document_id,
            consumer=consumer,
        )

    def _validate_observation_command(self, command: object) -> None:
        self._observation_recovery_suspended += 1
        try:
            students = tuple(student.student_id for student in self.list_students())
        finally:
            self._observation_recovery_suspended -= 1
        ObservationValidator().validate(
            {
                "student_id": getattr(command, "student_id"),
                "date": getattr(command, "date"),
                "subject_id": getattr(command, "subject_id"),
                "context": getattr(command, "context"),
                "note": getattr(command, "note"),
                "competency_ratings": getattr(command, "competency_ratings"),
                "is_quick_observation": getattr(
                    command,
                    "is_quick_observation",
                    False,
                ),
            },
            students,
        )

    def observation_draft_for_edit(
        self,
        observation_id: str,
    ) -> ObservationDraftViewModel | None:
        """Return an editable draft for one persisted observation."""
        self._recover_observation_uow()
        observation = SQLiteObservationRepository(self.database).get_observation(
            observation_id
        )
        if observation is None or not observation.active:
            return None
        try:
            reference_date = date.fromisoformat(observation.date)
        except ValueError:
            reference_date = None
        student = (
            self.get_student_profile(
                observation.student_id,
                reference_date=reference_date,
            )
            if reference_date is not None
            else None
        )
        return ObservationDraftViewModel(
            student_id=observation.student_id,
            student_name=(
                student.display_name if student else "Kind nicht verfügbar"
            ),
            date_text=observation.date,
            subject_id=observation.subject_id,
            subject_display_name=self._subject_display_name(observation),
            context=observation.context,
            note=observation.note,
            competency_ratings=tuple(
                ObservationCompetencyRatingDraft(
                    rating.subject_id,
                    rating.subject_display_name,
                    rating.learning_area,
                    rating.competency_group,
                    rating.competency_text,
                    rating.rating,
                    rating.competency_id,
                )
                for rating in observation.competency_ratings
            ),
            attachment_names=tuple(
                document.original_filename
                for document in self._document_repository().list_documents_for_observation(
                    observation.observation_id
                )
            ),
            attachments=tuple(
                self._attachment_draft_from_record(document)
                for document in self._document_repository().list_documents_for_observation(
                    observation.observation_id
                )
            ),
            observation_id=observation.observation_id,
            is_quick_observation=(
                not observation.competency_ratings and bool(observation.note.strip())
            ),
        )

    def list_observations_for_student(
        self,
        student_id: str,
    ) -> tuple[ObservationListItem, ...]:
        """Return persisted observations for the profile view."""
        self._recover_observation_uow()
        observations = SQLiteObservationRepository(
            self.database
        ).list_observations_for_student(student_id)
        return tuple(
            ObservationListItem(
                observation.observation_id,
                observation.student_id,
                observation.date,
                self._subject_display_name(observation),
                observation.context,
                observation.note,
                tuple(
                    ObservationRatingViewModel(
                        rating.competency_id,
                        rating.subject_display_name,
                        rating.learning_area,
                        rating.competency_group,
                        rating.competency_text,
                        rating.rating,
                        subject_id=rating.subject_id,
                    )
                    for rating in observation.competency_ratings
                ),
                tuple(
                    self._document_view_model(document)
                    for document in self._document_repository().list_documents_for_observation(
                        observation.observation_id
                    )
                ),
                not observation.competency_ratings and bool(observation.note.strip()),
            )
            for observation in observations
        )

    def list_documents_for_student(
        self,
        student_id: str,
    ) -> tuple[StudentDocumentViewModel, ...]:
        """Return active document and media metadata for one student."""
        self._recover_observation_uow()
        return tuple(
            self._document_view_model(document)
            for document in self._document_repository().list_documents_for_student(
                student_id
            )
        )

    @product_writer
    def add_student_document(
        self,
        *,
        student_id: str,
        source_path: Path,
        document_type: str = "Sonstiges",
        title: str = "",
        note: str = "",
        observation_id: str = "",
        operation_token: str = "",
    ) -> StudentDocumentViewModel:
        """Persist one general document through the configured managed path."""
        if self._managed_documents is not None:
            if observation_id:
                raise ValueError(
                    "Observation attachments use the observation unit of work."
                )
            normalized_type = (
                document_type
                if document_type in DOCUMENT_TYPE_OPTIONS
                else "Sonstiges"
            )
            document = self._managed_documents.create(
                student_id=student_id,
                source_path=source_path,
                document_type=normalized_type,
                title=title,
                note=note,
                operation_token=operation_token,
            )
            return self._document_view_model(document)
        document = self._create_document_record(
            student_id=student_id,
            source_path=source_path,
            document_type=document_type,
            title=title,
            note=note,
            observation_id=observation_id,
        )
        return self._document_view_model(document)

    @product_writer
    def replace_student_document(
        self,
        *,
        document_id: str,
        source_path: Path,
        operation_token: str = "",
    ) -> StudentDocumentViewModel:
        """Replace one encrypted general document without changing its MED-ID."""
        if self._managed_documents is None:
            raise RuntimeError("Encrypted managed documents are not active.")
        return self._document_view_model(
            self._managed_documents.replace(
                document_id=document_id,
                source_path=source_path,
                operation_token=operation_token,
            )
        )

    @product_writer
    def remove_document(
        self, document_id: str, operation_token: str = ""
    ) -> None:
        """Soft-delete one document or media metadata row."""
        if self._managed_documents is not None:
            self._managed_documents.remove(
                document_id=document_id,
                operation_token=operation_token,
            )
            return
        self._document_repository().deactivate_document(document_id)

    def read_managed_student_document(
        self,
        *,
        document_id: str,
        consumer: object,
    ) -> object:
        """Stream one active general document to an injected consumer."""
        if self._managed_documents is None:
            raise RuntimeError("Encrypted managed documents are not active.")
        return self._managed_documents.read(
            document_id=document_id,
            consumer=consumer,
        )

    def list_competency_overview_for_student(
        self,
        student_id: str,
    ) -> tuple[StudentCompetencySubjectGroup, ...]:
        """Return documented canonical competency statuses grouped by subject."""
        statuses = self.list_competency_status_projection_for_student(student_id)
        documented_ids = {
            status.competency_id
            for status in statuses
            if status.documentation_state != "undocumented"
        }
        return self._group_competency_statuses(
            tuple(status for status in statuses if status.documentation_state != "undocumented"),
            self._active_current_competencies(),
            documented_ids,
            self._active_documentation_subject_ids(),
        )

    def list_competency_status_projection_for_student(
        self,
        student_id: str,
        *,
        retained_competency_ids: tuple[str, ...] = (),
    ) -> tuple[StudentCompetencyStatusViewModel, ...]:
        """Return the single canonical read projection for competency status."""
        observations = SQLiteObservationRepository(
            self.database
        ).list_observations_for_student(student_id)
        confirmations = SQLiteStudentCompetencyConfirmationRepository(
            self.database
        ).list_confirmations_for_student(student_id)
        freshness_by_competency = SQLitePersistenceEventRepository(
            self.database
        ).freshness_for_student(student_id)
        competencies = SQLiteCompetencyRepository(
            self.database
        ).list_competencies()
        return self._competency_status_projection_from_sources(
            observations=observations,
            confirmations=confirmations,
            freshness_by_competency=freshness_by_competency,
            competencies=competencies,
            retained_competency_ids=retained_competency_ids,
        )

    def _competency_status_projection_from_sources(
        self,
        *,
        observations: tuple[object, ...],
        confirmations: tuple[StudentCompetencyConfirmationRecord, ...],
        freshness_by_competency: Mapping[str, object],
        competencies: tuple[object, ...],
        retained_competency_ids: tuple[str, ...] = (),
    ) -> tuple[StudentCompetencyStatusViewModel, ...]:
        confirmations_by_competency = {
            confirmation.competency_id: confirmation
            for confirmation in confirmations
        }
        histories_by_competency: dict[str, list[tuple[object, str, str, str]]] = {}
        for observation in observations:
            for rating in observation.competency_ratings:
                history = histories_by_competency.setdefault(rating.competency_id, [])
                if not any(
                    existing_observation_id == observation.observation_id
                    for _rating, _date, existing_observation_id, _context in history
                ):
                    history.append(
                        (
                            rating,
                            observation.date,
                            observation.observation_id,
                            observation.context,
                        )
                    )
        referenced_competency_ids = (
            set(histories_by_competency)
            | set(confirmations_by_competency)
            | {
                competency_id.strip()
                for competency_id in retained_competency_ids
                if competency_id.strip()
            }
        )
        competencies_by_id = {
            competency.competency_id: competency
            for competency in competencies
            if (
                competency.active and competency.catalog_status == "current"
            ) or competency.competency_id in referenced_competency_ids
        }
        competency_ids = set(competencies_by_id) | referenced_competency_ids
        statuses = tuple(
            self._competency_status_view_model(
                tuple(histories_by_competency.get(competency_id, ())),
                competencies_by_id.get(competency_id),
                confirmations_by_competency.get(competency_id),
                freshness_by_competency.get(competency_id),
            )
            for competency_id in competency_ids
        )
        return tuple(
            sorted(
                statuses,
                key=lambda status: (
                    status.subject_display_name.casefold(),
                    status.sort_order,
                    status.competency_id,
                ),
            )
        )

    def competency_cockpit_for_student(
        self,
        student_id: str,
    ) -> StudentCompetencyCockpitViewModel:
        """Group the canonical Sprint-6B status projection for cockpit display."""
        statuses = self.list_competency_status_projection_for_student(student_id)
        subject_ids = self._effective_documentation_subject_ids(student_id)
        return build_student_competency_cockpit(
            statuses,
            tuple(subject_ids),
        )

    def list_documentation_status_for_student(
        self,
        student_id: str,
    ) -> tuple[StudentDocumentationSubjectStatus, ...]:
        """Return catalog coverage by subject for one student."""
        statuses = self.list_competency_status_projection_for_student(student_id)
        documented_ids = {
            status.competency_id
            for status in statuses
            if status.documentation_state != "undocumented"
        }
        return self._documentation_statuses(
            self._documentation_relevant_competencies(
                self._effective_documentation_subject_ids(student_id)
            ),
            documented_ids,
        )

    def student_profile_dashboard_for_student(
        self,
        student_id: str,
        *,
        as_of: date | None = None,
    ) -> StudentProfileDashboardViewModel:
        """Compose the Variant-A profile from existing canonical projections."""
        statuses = self.list_competency_status_projection_for_student(student_id)
        documented_ids = {
            status.competency_id
            for status in statuses
            if status.documentation_state != "undocumented"
        }
        documentation_statuses = self._documentation_statuses(
            self._documentation_relevant_competencies(
                self._effective_documentation_subject_ids(student_id)
            ),
            documented_ids,
        )
        return build_student_profile_dashboard(
            statuses,
            documentation_statuses,
            as_of or date.today(),
        )

    def get_report_preview_for_student(
        self,
        student_id: str,
    ) -> StudentReportPreviewViewModel | None:
        """Return a derived report preparation grouped by subject."""
        profile = self.get_student_profile(student_id)
        if profile is None:
            return None
        competency_groups = self.list_competency_overview_for_student(student_id)
        observations = self.list_observations_for_student(student_id)
        return StudentReportPreviewViewModel(
            profile.student_id,
            profile.display_name,
            self._report_subject_sections(competency_groups, observations),
        )

    def learning_report_preparation_for_student(
        self,
        student_id: str,
        *,
        period_end: date,
        retained_competency_ids: tuple[str, ...] = (),
    ) -> LearningReportPreparationViewModel | None:
        """Prepare a transient report selection from the canonical status projection."""
        batch = SQLiteStudentDocumentationProjectionRepository(
            self.database
        ).read_batch(
            as_of=period_end,
            student_id=student_id,
            historical_membership=True,
        )
        student = self._student_profile_from_batch(
            batch,
            student_id,
            historical=True,
        )
        statuses = self._competency_status_projection_from_batch(
            batch,
            student_id,
            retained_competency_ids=retained_competency_ids,
        )
        observations = self._observation_list_items_from_batch(
            batch,
            student_id,
        )
        source = LearningReportApplicationService(
            lambda _student_id, _reference_date: student,
            lambda _student_id: statuses,
            lambda _student_id: observations,
        ).execute(PrepareLearningReportQuery(student_id, period_end))
        if source is None:
            return None
        return build_learning_report_preparation(
            source.student,
            source.competency_statuses,
            source.observations,
        )

    def report_overview_for_student(
        self,
        student_id: str,
        *,
        selected_report_draft_id: str = "",
        selected_learning_conference_draft_id: str = "",
    ) -> ReportOverviewViewModel:
        """Compose Paket-1 display state from separate report and LEG reads."""
        report_list_error = None
        try:
            report_drafts = self.list_learning_report_drafts_for_student(
                student_id
            )
        except Exception as error:
            report_drafts = ()
            report_list_error = error
        learning_conference_list_error = None
        try:
            learning_conference_drafts = (
                self.list_learning_conference_drafts_for_student(student_id)
            )
        except Exception as error:
            learning_conference_drafts = ()
            learning_conference_list_error = error
        selected_report = next(
            (
                draft
                for draft in report_drafts
                if (
                    selected_report_draft_id
                    and draft.report_draft_id == selected_report_draft_id
                )
            ),
            None,
        )
        report_revision_service = self._report_revision_application_service()
        report_states = {}
        report_revision_errors: set[str] = set()
        for draft in report_drafts:
            try:
                state = report_revision_service.state_for_draft(
                    draft.report_draft_id
                )
                report_states[draft.report_draft_id] = state
            except Exception as error:
                report_states[draft.report_draft_id] = error
        _completion, learning_conference_revision_service = (
            self._learning_conference_revision_services()
        )
        learning_conference_states = {}
        learning_conference_revision_periods: dict[
            str,
            tuple[str, str, str],
        ] = {}
        learning_conference_revision_errors: set[str] = set()
        for draft in learning_conference_drafts:
            try:
                state = learning_conference_revision_service.state_for_draft(
                    GetLearningConferenceRevisionStateQuery(
                        draft.learning_conference_draft_id
                    )
                )
                learning_conference_states[
                    draft.learning_conference_draft_id
                ] = state
            except Exception as error:
                learning_conference_states[
                    draft.learning_conference_draft_id
                ] = error
        phase2_observations: tuple[Mapping[str, object], ...] = ()
        phase2_report_revisions: tuple[Mapping[str, object], ...] = ()
        phase2_learning_conference_revisions: tuple[
            Mapping[str, object],
            ...,
        ] = ()
        phase2_confirmations: tuple[Mapping[str, object], ...] = ()
        phase2_subjects: tuple[Mapping[str, object], ...] = ()
        phase2_preparation: LearningReportPreparationViewModel | None = None
        phase2_source_errors: list[str] = []
        current_school_year = self.current_school_year()
        if selected_report is not None:
            try:
                phase2_preparation = self.learning_report_preparation_for_student(
                    student_id,
                    period_end=selected_report.period_end,
                    retained_competency_ids=selected_report.competency_ids,
                )
            except Exception:
                phase2_preparation = None
        if current_school_year is not None:
            try:
                effective_subject_ids = (
                    self._student_documentation_subject_service()
                    .effective_documentation_subjects(
                        student_id,
                        current_school_year.school_year_id,
                    )
                )
                phase2_subject_ids = tuple(dict.fromkeys((
                    *COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS,
                    *(
                        subject_id
                        for subject_id in effective_subject_ids
                        if subject_id
                        not in COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS
                    ),
                )))
                batch = SQLiteStudentDocumentationProjectionRepository(
                    self.database
                ).read_batch(
                    as_of=current_school_year.end_date,
                    student_id=student_id,
                    historical_membership=True,
                )
                (
                    phase2_observations,
                    phase2_confirmations,
                    phase2_subjects,
                ) = self._phase2_live_evidence_sources(
                    batch,
                    student_id,
                    phase2_subject_ids,
                )
            except Exception:
                phase2_source_errors.append("live_documentation")
            try:
                report_histories = (
                    report_revision_service.revision_histories_for_student(
                        student_id
                    )
                )
                report_rows: list[Mapping[str, object]] = []
                for history in report_histories:
                    for revision in history.revisions:
                        try:
                            report_revision_service.verify_revision(revision)
                            hash_valid = True
                        except Exception:
                            hash_valid = False
                            report_revision_errors.add(
                                revision.learning_report_revision_id
                            )
                        report_rows.append({
                            "report_draft_id": (
                                history.report.source_report_draft_id
                            ),
                            "learning_report_revision_id": (
                                revision.learning_report_revision_id
                            ),
                            "revision_number": revision.revision_number,
                            "status": revision.status,
                            "finalized_at": revision.finalized_at,
                            "hash_valid": hash_valid,
                        })
                phase2_report_revisions = tuple(report_rows)
            except Exception:
                phase2_source_errors.append("report_revisions")
            try:
                learning_conference_histories = (
                    learning_conference_revision_service
                    .revision_histories_for_student(student_id)
                )
                learning_conference_rows: list[Mapping[str, object]] = []
                for history in learning_conference_histories:
                    for revision in history.revisions:
                        snapshot: Mapping[str, object] = {}
                        try:
                            snapshot = (
                                learning_conference_revision_service
                                .verify_revision(revision)
                            )
                            hash_valid = True
                        except Exception:
                            hash_valid = False
                            learning_conference_revision_errors.add(
                                revision.learning_conference_revision_id
                            )
                        period = snapshot.get("period")
                        start = ""
                        end = ""
                        if isinstance(period, Mapping):
                            start = str(period.get("start", ""))
                            end = str(period.get("end", ""))
                        conference_date = str(
                            snapshot.get("conference_date", "")
                        )
                        if hash_valid:
                            learning_conference_revision_periods[
                                revision.learning_conference_revision_id
                            ] = (start, end, conference_date)
                        learning_conference_rows.append({
                            "learning_conference_draft_id": (
                                history.conference
                                .source_learning_conference_draft_id
                            ),
                            "learning_conference_revision_id": (
                                revision.learning_conference_revision_id
                            ),
                            "revision_number": revision.revision_number,
                            "status": revision.status,
                            "conference_date": conference_date,
                            "hash_valid": hash_valid,
                        })
                phase2_learning_conference_revisions = tuple(
                    learning_conference_rows
                )
            except Exception:
                phase2_source_errors.append("learning_conference_revisions")
        return build_report_overview(
            report_drafts,
            report_states,
            learning_conference_drafts,
            learning_conference_states,
            phase2_preparation,
            report_list_error=report_list_error,
            learning_conference_list_error=learning_conference_list_error,
            report_revision_errors=frozenset(report_revision_errors),
            learning_conference_revision_periods=(
                learning_conference_revision_periods
            ),
            learning_conference_revision_errors=frozenset(
                learning_conference_revision_errors
            ),
            selected_report_draft_id=selected_report_draft_id,
            selected_learning_conference_draft_id=(
                selected_learning_conference_draft_id
            ),
            phase2_period_start=(
                current_school_year.start_date
                if current_school_year is not None
                else None
            ),
            phase2_period_end=(
                current_school_year.end_date
                if current_school_year is not None
                else None
            ),
            phase2_observations=phase2_observations,
            phase2_report_revisions=phase2_report_revisions,
            phase2_learning_conference_revisions=(
                phase2_learning_conference_revisions
            ),
            phase2_confirmations=phase2_confirmations,
            phase2_subjects=phase2_subjects,
            phase2_source_errors=tuple(phase2_source_errors),
        )

    def _phase2_live_evidence_sources(
        self,
        batch: StudentDocumentationProjectionBatch,
        student_id: str,
        effective_subject_ids: tuple[str, ...],
    ) -> tuple[
        tuple[Mapping[str, object], ...],
        tuple[Mapping[str, object], ...],
        tuple[Mapping[str, object], ...],
    ]:
        """Translate one consistent live snapshot into pure projection rows."""
        competencies_by_id = {
            competency.competency_id: competency
            for competency in batch.competencies
        }
        observations = tuple(
            {
                "observation_id": observation.observation_id,
                "observed_on": observation.date,
                "subject_id": observation.subject_id,
                "context": observation.context,
                "active": observation.active,
                "assignments": tuple(
                    {
                        "competency_id": rating.competency_id,
                        "subject_id": rating.subject_id,
                        "active": bool(
                            competencies_by_id.get(rating.competency_id)
                            and competencies_by_id[rating.competency_id].active
                        ),
                        "catalog_status": getattr(
                            competencies_by_id.get(rating.competency_id),
                            "catalog_status",
                            "missing",
                        ),
                        "historical": not bool(
                            competencies_by_id.get(rating.competency_id)
                            and competencies_by_id[rating.competency_id].active
                            and competencies_by_id[
                                rating.competency_id
                            ].catalog_status == "current"
                        ),
                    }
                    for rating in observation.competency_ratings
                ),
                "competency_area": ", ".join(dict.fromkeys(
                    rating.learning_area.strip()
                    for rating in observation.competency_ratings
                    if rating.learning_area.strip()
                )),
                "topic": ", ".join(dict.fromkeys(
                    rating.competency_group.strip()
                    for rating in observation.competency_ratings
                    if rating.competency_group.strip()
                )),
            }
            for observation in batch.observations_by_student.get(
                student_id,
                (),
            )
        )
        statuses = self._competency_status_projection_from_sources(
            observations=batch.observations_by_student.get(student_id, ()),
            confirmations=batch.confirmations_by_student.get(student_id, ()),
            freshness_by_competency=batch.freshness_by_student.get(
                student_id,
                {},
            ),
            competencies=batch.competencies,
        )
        confirmations = tuple(
            {
                "student_id": student_id,
                "competency_id": status.competency_id,
                "subject_id": status.subject_id,
                "competency_text": status.competency_text,
                "confirmed_at": status.confirmed_at,
                "documentation_state": status.documentation_state,
                "confirmation_safe": (
                    bool(status.confirmed_at)
                    and status.documentation_state != "confirmation_unknown"
                ),
                "active": status.is_active,
                "catalog_status": status.catalog_status,
                "historical": status.historical,
            }
            for status in statuses
            if status.confirmed_at
        )
        subjects_by_id: dict[str, str] = {}
        for competency in batch.competencies:
            if (
                competency.subject_id in effective_subject_ids
            ):
                subjects_by_id.setdefault(
                    competency.subject_id,
                    competency.subject_name,
                )
        subjects = tuple(
            {
                "subject_id": subject_id,
                "subject_name": subjects_by_id[subject_id],
                "active": True,
            }
            for subject_id in effective_subject_ids
            if subject_id in subjects_by_id
        )
        return observations, confirmations, subjects

    @product_writer
    def save_learning_report_draft(
        self,
        draft: LearningReportDraftViewModel,
    ) -> LearningReportDraftViewModel:
        """Create or update one persistent report draft through the application layer."""
        service = self._report_draft_application_service()
        common = dict(
            student_id=draft.student_id,
            report_type=draft.report_type,
            period_start=draft.period_start.isoformat(),
            period_end=draft.period_end.isoformat(),
            teacher_name=draft.teacher_name,
            overall_text=draft.overall_text,
            subjects=tuple(subject.to_record() for subject in draft.subjects),
            competency_ids=draft.competency_ids,
            observation_ids=draft.observation_ids,
            chart_selections=tuple(
                chart.to_record() for chart in draft.chart_selections
            ),
        )
        if draft.report_draft_id:
            record = service.update(
                UpdateLearningReportDraftCommand(
                    report_draft_id=draft.report_draft_id,
                    **common,
                )
            )
        else:
            record = service.create(CreateLearningReportDraftCommand(**common))
        return self._learning_report_draft_view_model(record)

    def load_learning_report_draft(
        self,
        report_draft_id: str,
    ) -> LearningReportDraftViewModel | None:
        """Load one persistent report draft through the application query boundary."""
        record = self._report_draft_application_service().get(
            GetLearningReportDraftQuery(report_draft_id)
        )
        if record is None:
            return None
        return self._learning_report_draft_view_model(record)

    def list_learning_report_drafts_for_student(
        self,
        student_id: str,
    ) -> tuple[LearningReportDraftViewModel, ...]:
        """List persistent report drafts for future profile/UX selection."""
        records = self._report_draft_application_service().list_for_student(
            ListLearningReportDraftsQuery(student_id)
        )
        return tuple(self._learning_report_draft_view_model(record) for record in records)

    def learning_report_revision_status(
        self,
        report_draft_id: str,
    ) -> LearningReportRevisionStatusViewModel:
        """Return the current revision and newest-first history for one draft."""
        state = self._report_revision_application_service().state_for_draft(
            report_draft_id
        )
        return build_learning_report_revision_status(state)

    def prepare_learning_report_finalization(
        self,
        report_draft_id: str,
    ) -> LearningReportFinalizationPreviewViewModel:
        """Validate a saved draft and project its confirmation summary."""
        preview = self._report_finalization_application_service().prepare(
            report_draft_id
        )
        return build_learning_report_finalization_preview(preview)

    @product_writer
    def finalize_learning_report(
        self,
        report_draft_id: str,
        finalized_by_display_name: str,
    ) -> LearningReportRevisionStatusViewModel:
        """Create the next immutable revision and return refreshed UI status."""
        self._report_finalization_application_service().finalize(
            FinalizeLearningReportCommand(
                report_draft_id,
                finalized_by_display_name,
            )
        )
        return self.learning_report_revision_status(report_draft_id)

    def load_learning_report_revision(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportRevisionViewModel | None:
        """Build a final read projection exclusively from stored RPV data."""
        loaded = self._report_revision_application_service().snapshot_payload(
            learning_report_revision_id
        )
        if loaded is None:
            return None
        revision, payload = loaded
        return build_learning_report_revision_view_model(revision, payload)

    @product_writer
    def generate_learning_report_pdf(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportPdfArtifactViewModel:
        """Generate or verify the immutable managed PDF for one final RPV."""
        artifact = self._learning_report_pdf_application_service().generate(
            GenerateLearningReportPdfCommand(learning_report_revision_id)
        )
        repository = SQLiteLearningReportPdfArtifactRepository(self.database)
        file_path = (
            None
            if artifact.relative_file_path.startswith("managed-document:")
            else repository.resolve_file_path(artifact.relative_file_path)
        )
        return build_learning_report_pdf_artifact_view_model(
            artifact,
            file_path,
        )

    def load_learning_report_pdf_artifact(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportPdfArtifactViewModel | None:
        """Load and verify an existing final PDF artifact for one RPV."""
        artifact = self._learning_report_pdf_application_service().load_for_revision(
            learning_report_revision_id
        )
        if artifact is None:
            return None
        repository = SQLiteLearningReportPdfArtifactRepository(self.database)
        file_path = (
            None
            if artifact.relative_file_path.startswith("managed-document:")
            else repository.resolve_file_path(artifact.relative_file_path)
        )
        return build_learning_report_pdf_artifact_view_model(
            artifact,
            file_path,
        )

    def read_learning_report_pdf_artifact(
        self,
        *,
        artifact_id: str,
        consumer: object,
    ) -> None:
        """Resolve one RPA identity and deliver verified PDF bytes in memory."""
        if self._managed_document_store is None:
            raise LearningReportPdfError(
                "Verschluesselte PDF-Artefakte sind im Gate-Off-Pfad nicht aktiv."
            )
        repository = SQLiteLearningReportPdfArtifactRepository(self.database)
        artifact = repository.get_by_artifact_id(artifact_id)
        if artifact is None:
            raise LearningReportPdfError("PDF-Artefakt nicht gefunden.")
        loaded = self._learning_report_pdf_application_service().load_for_revision(
            artifact.learning_report_revision_id
        )
        if loaded != artifact:
            raise LearningReportPdfError("PDF-Artefaktreferenz ist ungueltig.")
        pdf_bytes = self._learning_report_managed_pdf_lifecycle(
            repository
        ).verify_existing(artifact)
        self._deliver_pdf_bytes(consumer, artifact, pdf_bytes)

    def read_final_pdf_artifact(
        self,
        *,
        artifact_id: str,
        consumer: object,
    ) -> None:
        """Resolve one opaque RPA/LCA identity through the shared safe reader."""
        if artifact_id.startswith("RPA-"):
            self.read_learning_report_pdf_artifact(
                artifact_id=artifact_id,
                consumer=consumer,
            )
            return
        if artifact_id.startswith("LCA-"):
            self.read_learning_conference_pdf_artifact(
                artifact_id=artifact_id,
                consumer=consumer,
            )
            return
        raise ManagedPdfArtifactError("managed_pdf_artifact_id_unknown")

    @staticmethod
    def final_pdf_artifact_error_message(_error: Exception) -> str:
        """Return one non-technical message for every viewer read failure."""
        return (
            "Das finale PDF konnte nicht sicher gelesen werden. "
            "Bitte schließe die Ansicht und versuche es erneut."
        )

    def learning_report_pdf_error_message(self, error: Exception) -> str:
        """Translate expected final-PDF failures into calm UI language."""
        message = str(error)
        if "finalisierte Berichtrevision" in message:
            return "Nur die aktuelle finale Berichtrevision kann als PDF erstellt werden."
        if "Snapshot" in message or "snapshot" in message:
            return (
                "Der gespeicherte Berichtstand konnte nicht sicher verifiziert werden. "
                "Es wurde kein finales PDF erstellt."
            )
        if "Referenz" in message or "referenz" in message:
            return (
                "Im gespeicherten Berichtstand fehlt eine erforderliche Referenz. "
                "Es wurde kein finales PDF erstellt."
            )
        if "registrierten PDF-Artefakts fehlt" in message:
            return "Die registrierte PDF-Datei wurde nicht gefunden."
        if "SHA-256" in message or "Dateigroesse" in message:
            return "Die Integritaet der vorhandenen PDF-Datei konnte nicht bestaetigt werden."
        if isinstance(error, LearningReportPdfError):
            return "Das finale PDF konnte nicht sicher erstellt werden."
        return "Das finale PDF konnte wegen eines technischen Fehlers nicht erstellt werden."

    def learning_report_finalization_error_message(self, error: Exception) -> str:
        """Translate expected domain failures into calm, actionable UI language."""
        message = str(error)
        if "Aggregateidentitaet" in message or "anderen Berichtstyp" in message:
            return (
                "Berichtstyp oder Zeitraum weicht von der letzten finalen Fassung ab. "
                "Für einen anderen Berichtstyp oder Zeitraum muss ein neuer "
                "Berichtsentwurf angelegt werden."
            )
        translations = (
            (("finalized_by_display_name",), "Bitte den Anzeigenamen der verantwortlichen Lehrkraft eingeben."),
            (("Berichtszeitraum", "period_end"), "Bitte einen gültigen Berichtszeitraum auswählen. Das Ende muss nach dem Beginn liegen."),
            (("Mindestens ein Fach", "Fachreferenzen", "Faecher"), "Bitte mindestens ein verfügbares Fach auswählen."),
            (("Berichtstext",), "Bitte mindestens einen bewusst verfassten Berichtstext ergänzen."),
            (("Kompetenzreferenzen", "Kompetenzen"), "Eine ausgewählte Kompetenz ist nicht mehr zulässig oder passt nicht zum Fach. Bitte die Auswahl prüfen."),
            (("Nicht verfuegbare Beobachtungsreferenzen",), "Ein ausgewählter Beobachtungsbeleg ist nicht mehr verfügbar. Bitte den Bezug im Entwurf abwählen."),
            (("Beobachtungsreferenzen", "Beobachtungen"), "Ein ausgewählter Beobachtungsbeleg gehört nicht zu diesem Kind oder Fach. Bitte die Auswahl prüfen."),
            (("Diagrammreferenzen",), "Eine Diagrammauswahl passt nicht zu den ausgewählten Fächern. Bitte die Auswahl prüfen."),
        )
        for needles, visible in translations:
            if any(needle in message for needle in needles):
                return visible
        if isinstance(error, ReportFinalizationError):
            return "Der Bericht kann noch nicht finalisiert werden. Bitte den Entwurf und seine Auswahl prüfen."
        return "Die Finalisierung konnte wegen eines technischen Fehlers nicht abgeschlossen werden."

    def _report_draft_application_service(self) -> ReportDraftApplicationService:
        repository = SQLiteReportDraftRepository(self.database)
        return ReportDraftApplicationService(
            ReportDraftService(repository),
            repository,
        )

    def _report_finalization_application_service(
        self,
    ) -> ReportFinalizationApplicationService:
        repository = SQLiteLearningReportRepository(self.database)
        return ReportFinalizationApplicationService(
            ReportFinalizationService(repository)
        )

    def _report_revision_application_service(
        self,
    ) -> ReportRevisionApplicationService:
        repository = SQLiteLearningReportRepository(self.database)
        return ReportRevisionApplicationService(
            LearningReportRevisionReadService(repository)
        )

    def _learning_report_pdf_application_service(
        self,
    ) -> LearningReportPdfApplicationService:
        report_repository = SQLiteLearningReportRepository(self.database)
        artifact_repository = SQLiteLearningReportPdfArtifactRepository(self.database)
        renderer = PdfRenderer()
        domain_service = LearningReportPdfService(
            LearningReportRevisionReadService(report_repository),
            artifact_repository,
            report_repository.get_report,
            lambda revision, payload: build_learning_report_revision_view_model(
                revision,
                payload,
            ).output_model,
            renderer.render,
            managed_lifecycle=(
                None
                if self._managed_document_store is None
                else self._learning_report_managed_pdf_lifecycle(
                    artifact_repository
                )
            ),
        )
        return LearningReportPdfApplicationService(domain_service)

    def _learning_report_managed_pdf_lifecycle(
        self,
        repository: SQLiteLearningReportPdfArtifactRepository | None = None,
    ) -> ManagedPdfArtifactLifecycle[LearningReportPdfArtifactRecord]:
        if self._managed_document_store is None:
            raise ValueError("managed_document_store_required")
        repository = repository or SQLiteLearningReportPdfArtifactRepository(
            self.database
        )
        return ManagedPdfArtifactLifecycle(
            database_path=self.database_path,
            store=self._managed_document_store,
            artifact_kind="report",
            next_artifact_id=repository.next_artifact_id,
            get_for_revision=repository.get_for_revision,
            save_artifact=repository.save_artifact,
            build_artifact=lambda value: LearningReportPdfArtifactRecord(
                value.artifact_id,
                value.revision_id,
                value.managed_reference,
                "application/pdf",
                value.pdf_size,
                value.snapshot_sha256,
                value.pdf_sha256,
                value.created_at,
            ),
            artifact_reference=lambda value: value.relative_file_path,
            artifact_mime_type=lambda value: value.mime_type,
            artifact_size=lambda value: value.file_size_bytes,
            artifact_pdf_sha256=lambda value: value.pdf_sha256,
            fault_hook=self._managed_pdf_fault_hook,
        )

    def _learning_report_draft_view_model(
        self,
        record: ReportDraftRecord,
    ) -> LearningReportDraftViewModel:
        repository = SQLiteReportDraftRepository(self.database)
        return LearningReportDraftViewModel.from_record(
            record,
            unavailable_observation_ids=repository.unavailable_observation_ids(record),
        )

    def learning_conference_preparation_for_student(
        self,
        student_id: str,
        *,
        conference_date: date | None = None,
        retained_competency_ids: tuple[str, ...] = (),
    ) -> LearningConferencePreparationViewModel | None:
        """Prepare LEG selection from existing canonical Live projections."""
        as_of = conference_date if conference_date is not None else self._today()
        batch = SQLiteStudentDocumentationProjectionRepository(
            self.database
        ).read_batch(
            as_of=as_of,
            student_id=student_id,
            historical_membership=conference_date is not None,
            include_membership=conference_date is not None,
        )
        student = self._student_profile_from_batch(
            batch,
            student_id,
            historical=conference_date is not None,
            neutral_without_membership=conference_date is None,
        )
        statuses = self._competency_status_projection_from_batch(
            batch,
            student_id,
            retained_competency_ids=retained_competency_ids,
        )
        observations = self._observation_list_items_from_batch(
            batch,
            student_id,
        )
        source = LearningConferenceApplicationService(
            lambda _student_id, _reference_date: student,
            lambda _student_id: statuses,
            lambda _student_id: observations,
        ).execute(PrepareLearningConferenceQuery(student_id, conference_date))
        if source is None:
            return None
        return build_learning_conference_preparation(
            source.student,
            source.competency_statuses,
            source.observations,
        )

    @product_writer
    def save_learning_conference_draft(
        self,
        draft: LearningConferenceDraftViewModel,
    ) -> LearningConferenceDraftViewModel:
        """Create or update one LEG draft through the application boundary."""
        draft_input = LearningConferenceDraftInput(
            student_id=draft.student_id,
            period_start=(draft.period_start.isoformat() if draft.period_start else ""),
            period_end=draft.period_end.isoformat() if draft.period_end else "",
            conference_date=(
                draft.conference_date.isoformat() if draft.conference_date else ""
            ),
            responsible_teacher=draft.responsible_teacher,
            conversation_entry_text=draft.conversation_entry_text,
            child_retrospective_text=draft.child_retrospective_text,
            teacher_perspective_text=draft.teacher_perspective_text,
            strengths_text=draft.strengths_text,
            development_fields_text=draft.development_fields_text,
            prepared_goals_text=draft.prepared_goals_text,
            prepared_support_text=draft.prepared_support_text,
            prepared_agreements_text=draft.prepared_agreements_text,
            agreed_goals_text=draft.agreed_goals_text,
            agreed_support_text=draft.agreed_support_text,
            agreed_agreements_text=draft.agreed_agreements_text,
            responsibilities_text=draft.responsibilities_text,
            next_review_date=(
                draft.next_review_date.isoformat() if draft.next_review_date else ""
            ),
            subject_ids=draft.subject_ids,
            cross_topic_keys=draft.cross_topic_keys,
            competency_ids=draft.competency_ids,
            observation_ids=draft.observation_ids,
            chart_types=draft.chart_types,
        )
        service = self._learning_conference_draft_application_service()
        if draft.learning_conference_draft_id:
            record = service.update(
                UpdateLearningConferenceDraftCommand(
                    draft.learning_conference_draft_id,
                    draft_input,
                )
            )
        else:
            record = service.create(
                CreateLearningConferenceDraftCommand(draft_input)
            )
        return self._learning_conference_draft_view_model(record)

    def load_learning_conference_draft(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceDraftViewModel | None:
        """Load one persistent LEG draft without replacing unavailable evidence."""
        record = self._learning_conference_draft_application_service().get(
            GetLearningConferenceDraftQuery(learning_conference_draft_id)
        )
        if record is None:
            return None
        return self._learning_conference_draft_view_model(record)

    def list_learning_conference_drafts_for_student(
        self,
        student_id: str,
    ) -> tuple[LearningConferenceDraftViewModel, ...]:
        """List persistent LEG drafts for later reopening."""
        records = self._learning_conference_draft_application_service().list_for_student(
            ListLearningConferenceDraftsQuery(student_id)
        )
        return tuple(
            self._learning_conference_draft_view_model(record)
            for record in records
        )

    def _learning_conference_draft_application_service(
        self,
    ) -> LearningConferenceDraftApplicationService:
        repository = SQLiteLearningConferenceDraftRepository(self.database)
        return LearningConferenceDraftApplicationService(
            LearningConferenceDraftService(repository),
            repository,
        )

    def _learning_conference_draft_view_model(
        self,
        record: LearningConferenceDraftRecord,
    ) -> LearningConferenceDraftViewModel:
        repository = SQLiteLearningConferenceDraftRepository(self.database)
        return LearningConferenceDraftViewModel.from_record(
            record,
            unavailable_observation_ids=repository.unavailable_observation_ids(record),
        )

    @product_writer
    def complete_learning_conference(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceRevisionStatusViewModel:
        """Execute an explicit LCD-only completion command outside the UI."""
        completion, revisions = self._learning_conference_revision_services()
        completion.complete(
            CompleteLearningConferenceCommand(learning_conference_draft_id)
        )
        state = revisions.state_for_draft(
            GetLearningConferenceRevisionStateQuery(
                learning_conference_draft_id
            )
        )
        return build_learning_conference_revision_status(state)

    def learning_conference_revision_status(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceRevisionStatusViewModel:
        """Project the current LCF/LCV state for one editable LCD."""
        _completion, revisions = self._learning_conference_revision_services()
        return build_learning_conference_revision_status(
            revisions.state_for_draft(
                GetLearningConferenceRevisionStateQuery(
                    learning_conference_draft_id
                )
            )
        )

    def load_learning_conference_revision(
        self,
        learning_conference_revision_id: str,
    ) -> LearningConferenceRevisionViewModel:
        """Load a hash-verified snapshot-only historical LEG projection."""
        _completion, revisions = self._learning_conference_revision_services()
        verified = revisions.get_revision(
            GetLearningConferenceRevisionQuery(
                learning_conference_revision_id
            )
        )
        return build_learning_conference_revision_view_model(verified)

    @product_writer
    def generate_learning_conference_pdf(
        self,
        learning_conference_revision_id: str,
    ) -> LearningConferencePdfArtifactViewModel:
        """Generate or verify the immutable managed PDF for one completed LCV."""
        artifact = self._learning_conference_pdf_application_service().generate(
            GenerateLearningConferencePdfCommand(learning_conference_revision_id)
        )
        repository = SQLiteLearningConferencePdfArtifactRepository(self.database)
        file_path = (
            None
            if artifact.relative_file_path.startswith("managed-document:")
            else repository.resolve_file_path(artifact.relative_file_path)
        )
        return build_learning_conference_pdf_artifact_view_model(
            artifact,
            file_path,
        )

    def load_learning_conference_pdf_artifact(
        self,
        learning_conference_revision_id: str,
    ) -> LearningConferencePdfArtifactViewModel | None:
        """Load and verify an existing final LEG PDF artifact for one LCV."""
        artifact = self._learning_conference_pdf_application_service().load_for_revision(
            learning_conference_revision_id
        )
        if artifact is None:
            return None
        repository = SQLiteLearningConferencePdfArtifactRepository(self.database)
        file_path = (
            None
            if artifact.relative_file_path.startswith("managed-document:")
            else repository.resolve_file_path(artifact.relative_file_path)
        )
        return build_learning_conference_pdf_artifact_view_model(
            artifact,
            file_path,
        )

    def read_learning_conference_pdf_artifact(
        self,
        *,
        artifact_id: str,
        consumer: object,
    ) -> None:
        """Resolve one LCA identity and deliver verified PDF bytes in memory."""
        if self._managed_document_store is None:
            raise LearningConferencePdfError(
                "Verschluesselte LEG-PDF-Artefakte sind im Gate-Off-Pfad nicht aktiv."
            )
        repository = SQLiteLearningConferencePdfArtifactRepository(self.database)
        artifact = repository.get_by_artifact_id(artifact_id)
        if artifact is None:
            raise LearningConferencePdfError("LEG-PDF-Artefakt nicht gefunden.")
        loaded = self._learning_conference_pdf_application_service().load_for_revision(
            artifact.learning_conference_revision_id
        )
        if loaded != artifact:
            raise LearningConferencePdfError("LEG-PDF-Artefaktreferenz ist ungueltig.")
        pdf_bytes = self._learning_conference_managed_pdf_lifecycle(
            repository
        ).verify_existing(artifact)
        self._deliver_pdf_bytes(consumer, artifact, pdf_bytes)

    @staticmethod
    def _deliver_pdf_bytes(consumer: object, artifact: object, pdf_bytes: bytes) -> None:
        try:
            consumer.start(artifact)
            for offset in range(0, len(pdf_bytes), 64 * 1024):
                consumer.write(pdf_bytes[offset : offset + 64 * 1024])
            consumer.finish(artifact)
        except Exception:
            try:
                consumer.abort("managed_pdf_consumer_failed")
            finally:
                raise

    def learning_conference_pdf_error_message(self, error: Exception) -> str:
        """Translate expected LEG-PDF failures into calm UI language."""
        message = str(error)
        if "aktuelle abgeschlossene LEG-Revision" in message:
            return "Nur die aktuelle abgeschlossene LEG-Revision kann als PDF erstellt werden."
        if "Snapshot" in message or "snapshot" in message:
            return (
                "Der gespeicherte LEG-Abschluss konnte nicht sicher verifiziert werden. "
                "Es wurde kein finales PDF erstellt."
            )
        if "registrierten LEG-PDF-Artefakts fehlt" in message:
            return "Die registrierte LEG-PDF-Datei wurde nicht gefunden."
        if "SHA-256" in message or "Dateigroesse" in message or "keine PDF-Datei" in message:
            return "Die Integritaet der vorhandenen LEG-PDF-Datei konnte nicht bestaetigt werden."
        if isinstance(error, LearningConferencePdfError):
            return "Das finale LEG-PDF konnte nicht sicher erstellt werden."
        return "Das finale LEG-PDF konnte wegen eines technischen Fehlers nicht erstellt werden."

    def _learning_conference_pdf_application_service(
        self,
    ) -> LearningConferencePdfApplicationService:
        revision_repository = SQLiteLearningConferenceRepository(self.database)
        artifact_repository = SQLiteLearningConferencePdfArtifactRepository(
            self.database
        )
        domain_service = LearningConferencePdfService(
            LearningConferenceRevisionReadService(revision_repository),
            artifact_repository,
            LearningConferencePdfOutputModelBuilder(),
            PdfRenderer().render,
            managed_lifecycle=(
                None
                if self._managed_document_store is None
                else self._learning_conference_managed_pdf_lifecycle(
                    artifact_repository
                )
            ),
        )
        return LearningConferencePdfApplicationService(domain_service)

    def _learning_conference_managed_pdf_lifecycle(
        self,
        repository: SQLiteLearningConferencePdfArtifactRepository | None = None,
    ) -> ManagedPdfArtifactLifecycle[LearningConferencePdfArtifactRecord]:
        if self._managed_document_store is None:
            raise ValueError("managed_document_store_required")
        repository = repository or SQLiteLearningConferencePdfArtifactRepository(
            self.database
        )
        return ManagedPdfArtifactLifecycle(
            database_path=self.database_path,
            store=self._managed_document_store,
            artifact_kind="learning_conference",
            next_artifact_id=repository.next_artifact_id,
            get_for_revision=repository.get_for_revision,
            save_artifact=repository.save_artifact,
            build_artifact=lambda value: LearningConferencePdfArtifactRecord(
                value.artifact_id,
                value.revision_id,
                value.managed_reference,
                "application/pdf",
                value.pdf_size,
                value.snapshot_sha256,
                value.pdf_sha256,
                value.created_at,
            ),
            artifact_reference=lambda value: value.relative_file_path,
            artifact_mime_type=lambda value: value.mime_type,
            artifact_size=lambda value: value.file_size_bytes,
            artifact_pdf_sha256=lambda value: value.pdf_sha256,
            fault_hook=self._managed_pdf_fault_hook,
        )

    def _learning_conference_revision_services(
        self,
    ) -> tuple[
        LearningConferenceCompletionApplicationService,
        LearningConferenceRevisionApplicationService,
    ]:
        repository = SQLiteLearningConferenceRepository(self.database)
        domain_service = LearningConferenceCompletionService(repository)
        return (
            LearningConferenceCompletionApplicationService(domain_service),
            LearningConferenceRevisionApplicationService(
                LearningConferenceRevisionReadService(
                    repository,
                    domain_service,
                )
            ),
        )

    @product_writer
    def save_competency_confirmation(
        self,
        *,
        student_id: str,
        competency_id: str,
        confirmed_rating: str,
        note: str = "",
        operation_token: str = "",
    ) -> StudentCompetencyConfirmationRecord:
        """Persist a teacher-confirmed competency status."""
        confirmation = StudentCompetencyConfirmationRecord(
            student_id.strip(),
            competency_id.strip(),
            confirmed_rating.strip(),
            datetime.now(UTC).replace(microsecond=0).isoformat(),
            note.strip(),
        )
        return SQLiteStudentCompetencyConfirmationRepository(
            self.database
        ).upsert_confirmation(
            confirmation,
            operation_token=operation_token,
        )

    def _create_document_record(
        self,
        *,
        student_id: str,
        source_path: Path,
        document_type: str,
        title: str,
        note: str,
        observation_id: str = "",
    ) -> DocumentRecord:
        source_path = Path(source_path).expanduser()
        if not source_path.is_file():
            raise FileNotFoundError(f"Datei nicht gefunden: {source_path}")
        document_type = (
            document_type if document_type in DOCUMENT_TYPE_OPTIONS else "Sonstiges"
        )
        repository = self._document_repository()
        observation_uow = ObservationPersistenceUnitOfWork(self.database)
        with ObservationWriterLock(observation_uow.staging_root):
            observation_uow.recover_pending_while_writer_locked()
            document_id = observation_uow.reserve_id_while_writer_locked("MED")
            original_filename = source_path.name
            target_path = self._document_target_path(
                student_id,
                document_id,
                original_filename,
            )
            ensure_durable_directory(target_path.parent)
            published = False
            try:
                if source_path.resolve() != target_path.resolve():
                    with source_path.open("rb") as source, target_path.open("xb") as target:
                        shutil.copyfileobj(source, target, length=1024 * 1024)
                        target.flush()
                        os.fsync(target.fileno())
                    published = True
                    directory_fd = os.open(target_path.parent, os.O_RDONLY)
                    try:
                        os.fsync(directory_fd)
                    finally:
                        os.close(directory_fd)
                timestamp = datetime.now(UTC).replace(microsecond=0).isoformat()
                document = DocumentRecord(
                    document_id=document_id,
                    student_id=student_id,
                    observation_id=observation_id,
                    title=title.strip() or source_path.stem,
                    document_type=document_type,
                    file_path=str(target_path),
                    original_filename=original_filename,
                    created_at=timestamp,
                    note=note.strip(),
                    active=True,
                )
                return repository.create_document(document)
            except Exception:
                if published and target_path.is_file() and not target_path.is_symlink():
                    target_path.unlink()
                    directory_fd = os.open(target_path.parent, os.O_RDONLY)
                    try:
                        os.fsync(directory_fd)
                    finally:
                        os.close(directory_fd)
                raise

    def _document_target_path(
        self,
        student_id: str,
        document_id: str,
        original_filename: str,
    ) -> Path:
        safe_filename = self._safe_filename(original_filename)
        return (
            self.database_path.parent
            / "documents"
            / student_id
            / f"{document_id}_{safe_filename}"
        )

    def _safe_filename(self, filename: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename.strip())
        return cleaned or "datei"

    def _document_repository(self) -> SQLiteDocumentRepository:
        return SQLiteDocumentRepository(self.database)

    def _observation_uow(self) -> ObservationPersistenceUnitOfWork:
        return ObservationPersistenceUnitOfWork(
            self.database,
            encrypted_attachments=self._encrypted_observation_attachments,
        )

    def _recover_observation_uow(self) -> None:
        if self._observation_recovery_suspended:
            return
        if self._managed_documents is not None:
            self._managed_documents.recover_pending()
        self._observation_uow().recover_pending()

    def _document_view_model(self, document: DocumentRecord) -> StudentDocumentViewModel:
        return StudentDocumentViewModel(
            document.document_id,
            document.student_id,
            document.observation_id,
            document.title,
            document.document_type,
            document.file_path,
            document.original_filename,
            document.created_at,
            document.note,
            self._managed_documents is not None and not document.observation_id,
        )

    def _attachment_draft_from_record(
        self,
        document: DocumentRecord,
    ) -> ObservationAttachmentDraft:
        return ObservationAttachmentDraft(
            source_path="",
            title=document.title,
            document_type=document.document_type,
            note=document.note,
            document_id=document.document_id,
            file_path=document.file_path,
            original_filename=document.original_filename,
        )

    def _dispatcher(self) -> ApplicationCommandDispatcher:
        observation_repository = SQLiteObservationRepository(self.database)
        observation_service = ObservationService(
            observation_repository,
            ObservationValidator(),
            tuple(
                student.student_id
                for student in self.list_students()
            ),
        )
        dispatcher = ApplicationCommandDispatcher()
        dispatcher.register(
            "observation.create",
            observation_create_handler(observation_service),
        )
        dispatcher.register(
            "observation.update",
            observation_update_handler(observation_service),
        )
        dispatcher.register(
            "observation.delete",
            observation_delete_handler(observation_service),
        )
        return dispatcher

    def _open_database(self, *, create: bool) -> SQLiteDatabase:
        database = SQLiteDatabase(self.database_path, create=create)
        database.initialize_schema()
        database.ensure_master_data_defaults()
        SQLiteCompetencyRepository(database).ensure_catalog_defaults(
            CurriculumDesktopAdapter().list_entries()
        )
        return database

    def _today(self) -> date:
        value = self._today_provider()
        if type(value) is not date:
            raise TypeError("today_provider muss ein Datum liefern.")
        return value

    def _now(self) -> datetime:
        value = self._now_provider()
        if not isinstance(value, datetime):
            raise TypeError("now_provider muss einen Zeitpunkt liefern.")
        if value.tzinfo is None or value.utcoffset() is None:
            value = value.astimezone()
        return value

    def _documentation_subject_sort_key(
        self,
        subject_id: str,
        subject_labels: dict[str, str],
        subject_sort_order: dict[str, int],
    ) -> tuple[int, int, str, str]:
        preferred_order = {
            value: index
            for index, value in enumerate(DOCUMENTATION_SUBJECT_PREFERRED_ORDER)
        }
        return (
            preferred_order.get(subject_id, len(preferred_order)),
            subject_sort_order.get(subject_id, len(subject_sort_order)),
            subject_labels.get(subject_id, subject_id).casefold(),
            subject_id,
        )

    def _student_list_item(
        self,
        student: V3Student,
        membership: CurrentStudentMembershipProjection,
        courses: dict[str, CourseRecord],
        documentation_status: StudentDocumentationSummaryViewModel,
    ) -> StudentListItem:
        course_name, course_color_name, course_color_hex = self._course_context(
            membership.course_id or "",
            courses,
            membership.course_name or "",
        )
        return StudentListItem(
            student.student_id,
            student.first_name,
            student.last_name,
            membership.group_id or "",
            membership.group_name or "Stammgruppe nicht verfügbar",
            membership.course_id or "",
            course_name,
            course_color_name,
            course_color_hex,
            documentation_status,
        )

    @staticmethod
    def _course_context(
        course_id: str,
        courses: dict[str, CourseRecord],
        course_name: str = "",
    ) -> tuple[str, str, str]:
        """Resolve one existing course to the shared display context."""
        course = courses.get(course_id)
        if course is None:
            return course_name or "Kurs nicht verfügbar", "", ""
        course_index = tuple(courses).index(course.course_id)
        color_name, color_hex = course_color_from_key(
            course.color_key,
            course_index,
        )
        return course_name or course.course_name, color_name, color_hex

    @staticmethod
    def _membership_group_name(
        membership: CurrentStudentMembershipProjection | AssignmentAtDateProjection,
        *,
        status_label: str,
        historical: bool,
    ) -> str:
        if membership.group_name:
            return membership.group_name
        if historical and status_label:
            return status_label
        if membership.resolution_status in {
            AssignmentResolutionStatus.ENROLLED,
            AssignmentResolutionStatus.EXITED,
        }:
            return "Stammgruppe nicht verfügbar"
        return ""

    @staticmethod
    def _membership_status(
        status: AssignmentResolutionStatus,
        *,
        historical: bool = False,
    ) -> tuple[str, bool]:
        if historical:
            labels = {
                AssignmentResolutionStatus.ENROLLED: "",
                AssignmentResolutionStatus.EXITED: (
                    "Am Beobachtungsdatum ausgeschieden"
                ),
                AssignmentResolutionStatus.NO_ASSIGNMENT: (
                    "Keine Zuordnung am Beobachtungsdatum"
                ),
                AssignmentResolutionStatus.CURRENT_SCHOOL_YEAR_MISSING: (
                    "Kein aktuelles Schuljahr festgelegt"
                ),
                AssignmentResolutionStatus.AMBIGUOUS: (
                    "Zuordnung am Beobachtungsdatum nicht eindeutig"
                ),
                AssignmentResolutionStatus.STUDENT_ARCHIVED: "Kind ist archiviert",
            }
        else:
            labels = {
                AssignmentResolutionStatus.ENROLLED: "",
                AssignmentResolutionStatus.EXITED: (
                    "Im aktuellen Schuljahr ausgeschieden"
                ),
                AssignmentResolutionStatus.NO_ASSIGNMENT: (
                    "Keine aktuelle Zuordnung"
                ),
                AssignmentResolutionStatus.CURRENT_SCHOOL_YEAR_MISSING: (
                    "Kein aktuelles Schuljahr festgelegt"
                ),
                AssignmentResolutionStatus.AMBIGUOUS: (
                    "Aktuelle Zuordnung nicht eindeutig"
                ),
                AssignmentResolutionStatus.STUDENT_ARCHIVED: "Kind ist archiviert",
            }
        return (
            labels[status],
            status
            in {
                AssignmentResolutionStatus.AMBIGUOUS,
                AssignmentResolutionStatus.CURRENT_SCHOOL_YEAR_MISSING,
            },
        )

    def _subject_display_name(self, observation: object) -> str:
        subjects = self._subjects_from_ratings(
            getattr(observation, "competency_ratings", ())
        )
        if len(subjects) > 1:
            return OBSERVATION_CROSS_SUBJECT_LABEL
        if len(subjects) == 1:
            return next(iter(subjects.values()))
        return getattr(observation, "subject_id", "")

    def _subject_id_for_draft(self, draft: ObservationDraftViewModel) -> str:
        subjects = self._subjects_from_draft(draft.competency_ratings)
        if len(subjects) > 1:
            return "cross_subject"
        if len(subjects) == 1:
            return next(iter(subjects))
        return draft.subject_id

    def _rating_records_from_draft(
        self,
        draft: ObservationDraftViewModel,
    ) -> tuple[ObservationCompetencyRatingRecord, ...]:
        return tuple(
            ObservationCompetencyRatingRecord(
                rating.competency_id,
                rating.subject_key,
                rating.subject_display_name,
                rating.learning_area,
                rating.competency_group,
                rating.competency_text,
                rating.rating,
            )
            for rating in draft.competency_ratings
        )

    def _subjects_from_draft(
        self,
        ratings: tuple[object, ...],
    ) -> dict[str, str]:
        subjects: dict[str, str] = {}
        for rating in ratings:
            subject_key = str(getattr(rating, "subject_key", "")).strip()
            if not subject_key:
                continue
            subjects.setdefault(
                subject_key,
                str(getattr(rating, "subject_display_name", subject_key)).strip()
                or subject_key,
            )
        return subjects

    def _subjects_from_ratings(
        self,
        ratings: tuple[object, ...],
    ) -> dict[str, str]:
        subjects: dict[str, str] = {}
        for rating in ratings:
            subject_id = str(getattr(rating, "subject_id", "")).strip()
            subject_label = str(
                getattr(rating, "subject_display_name", subject_id)
            ).strip()
            subject_key = subject_id or subject_label
            if not subject_key:
                continue
            subjects.setdefault(subject_key, subject_label or subject_key)
        return subjects

    def _competency_status_view_model(
        self,
        entries_newest_first: tuple[tuple[object, str, str, str], ...],
        competency: object | None,
        confirmation: StudentCompetencyConfirmationRecord | None,
        freshness: object | None = None,
    ) -> StudentCompetencyStatusViewModel:
        snapshot = entries_newest_first[0][0] if entries_newest_first else None
        evidence = tuple(
            StudentCompetencyEvidenceViewModel(
                observation_id,
                observation_date,
                getattr(rating, "rating"),
                getattr(rating, "subject_id"),
                getattr(rating, "subject_display_name"),
                getattr(rating, "learning_area"),
                getattr(rating, "competency_group"),
                getattr(rating, "competency_text"),
                context,
            )
            for rating, observation_date, observation_id, context in entries_newest_first
        )
        if entries_newest_first:
            newest_rating, newest_date, _observation_id, _context = entries_newest_first[0]
            ratings_newest_first = tuple(
                getattr(rating, "rating")
                for rating, _date, _id, _context in entries_newest_first
            )
            current_rating, weighted_score = calculated_rating_from_history(
                ratings_newest_first
            )
            use_current_catalog = bool(
                competency is not None
                and getattr(competency, "active", False)
                and getattr(competency, "catalog_status", "current") == "current"
            )
            subject_id = (
                getattr(competency, "subject_id")
                if use_current_catalog else getattr(newest_rating, "subject_id")
            )
            subject_display_name = (
                getattr(competency, "subject_name")
                if use_current_catalog else getattr(newest_rating, "subject_display_name")
            )
            # An inactive/legacy catalog row is retained only to make the
            # historic reference resolvable.  Its current presentation must
            # not overwrite the text captured with the observation.
            competency_label = (
                getattr(competency, "label")
                if competency is not None else getattr(newest_rating, "competency_text")
            )
            competency_id = getattr(newest_rating, "competency_id")
            rating_history = tuple(reversed(ratings_newest_first))
            observation_count = len(entries_newest_first)
        elif competency is not None:
            current_rating = confirmation.confirmed_rating if confirmation else ""
            weighted_score = 0.0
            subject_id = getattr(competency, "subject_id")
            subject_display_name = getattr(competency, "subject_name")
            competency_label = getattr(competency, "label")
            competency_id = getattr(competency, "competency_id")
            newest_date = ""
            rating_history = ()
            observation_count = 0
        else:
            # A historical observation snapshot remains displayable even if its
            # catalog row no longer exists.
            newest_rating, newest_date, _observation_id, _context = entries_newest_first[0]
            current_rating, weighted_score = calculated_rating_from_history(
                tuple(
                    getattr(rating, "rating")
                    for rating, _date, _id, _context in entries_newest_first
                )
            )
            subject_id = getattr(newest_rating, "subject_id")
            subject_display_name = getattr(newest_rating, "subject_display_name")
            competency_label = getattr(newest_rating, "competency_text")
            competency_id = getattr(newest_rating, "competency_id")
            rating_history = tuple(
                getattr(item, "rating")
                for item, _date, _id, _context in reversed(entries_newest_first)
            )
            observation_count = len(entries_newest_first)
        sort_order = int(getattr(competency, "sort_order", 0))
        observed_proposal = current_rating if entries_newest_first else ""
        freshness_state = str(getattr(freshness, "state", "") or "")
        if confirmation is not None and freshness_state == "confirmation_unknown":
            documentation_state = "confirmation_unknown"
        elif confirmation is not None:
            documentation_state = (
                freshness_state
                if freshness_state in {"confirmed", "newer_observations"}
                else "confirmed"
            )
        elif entries_newest_first:
            documentation_state = "observed_unconfirmed"
        else:
            documentation_state = "undocumented"
        historical = bool(
            competency is None
            or not getattr(competency, "active", False)
            or getattr(competency, "catalog_status", "current") != "current"
        )
        return StudentCompetencyStatusViewModel(
            competency_id,
            competency_label,
            subject_id,
            subject_display_name,
            current_rating,
            observation_rating_label(current_rating, competency or newest_rating),
            newest_date,
            sort_order,
            rating_history,
            observation_count,
            weighted_score,
            (
                confirmation.confirmed_rating
                if confirmation and documentation_state != "confirmation_unknown"
                else ""
            ),
            confirmation.confirmed_at if confirmation else "",
            confirmation.note if confirmation else "",
            (
                getattr(competency, "learning_area")
                if competency is not None and (not historical or snapshot is None)
                else getattr(snapshot, "learning_area", "")
            ),
            (
                getattr(competency, "competency_group")
                if competency is not None and (not historical or snapshot is None)
                else getattr(snapshot, "competency_group", "")
            ),
            (
                getattr(competency, "description")
                if competency is not None and (not historical or snapshot is None)
                else getattr(snapshot, "competency_text", "")
            ),
            documentation_state,
            observed_proposal,
            evidence,
            getattr(competency, "learning_stage", ""),
            getattr(competency, "catalog_status", ""),
            bool(getattr(competency, "active", False)),
            historical,
            competency is None,
            bool(
                documentation_state == "newer_observations"
            ),
        )

    def _group_competency_statuses(
        self,
        statuses: tuple[StudentCompetencyStatusViewModel, ...],
        active_competencies: tuple[object, ...],
        documented_ids: set[str],
        documentation_subject_ids: set[str],
    ) -> tuple[StudentCompetencySubjectGroup, ...]:
        groups: dict[str, list[StudentCompetencyStatusViewModel]] = {}
        subject_names: dict[str, str] = {}
        for status in sorted(statuses, key=lambda item: (item.sort_order, item.competency_id)):
            groups.setdefault(status.subject_id, []).append(status)
            subject_names.setdefault(status.subject_id, status.subject_display_name)
        return tuple(
            StudentCompetencySubjectGroup(
                subject_id,
                subject_names[subject_id],
                tuple(groups[subject_id]),
                self._missing_competencies_for_subject(
                    active_competencies,
                    documented_ids,
                    subject_id,
                )
                if subject_id in documentation_subject_ids
                else (),
            )
            for subject_id in groups
        )

    def _active_competencies(self) -> tuple[object, ...]:
        return tuple(
            competency
            for competency in SQLiteCompetencyRepository(
                self.database
            ).list_competencies()
            if getattr(competency, "active", False)
        )

    def _active_current_competencies(self) -> tuple[object, ...]:
        return tuple(
            competency
            for competency in self._active_competencies()
            if getattr(competency, "catalog_status", "current") == "current"
        )

    def _active_documentation_subject_ids(self) -> set[str]:
        return set(
            SQLiteDocumentationSubjectSettingsRepository(
                self.database
            ).list_active_documentation_subject_ids()
        )

    def _initial_observation_subject_key(
        self,
        initial_draft: ObservationDraftViewModel | None,
    ) -> str:
        if initial_draft is None:
            return ""
        if initial_draft.competency_ratings:
            return initial_draft.competency_ratings[0].subject_key
        return initial_draft.subject_id

    def _initial_observation_subject_label(
        self,
        initial_draft: ObservationDraftViewModel | None,
    ) -> str:
        if initial_draft is None:
            return ""
        if initial_draft.competency_ratings:
            return initial_draft.competency_ratings[0].subject_display_name
        return initial_draft.subject_display_name or initial_draft.subject_id

    def _documentation_relevant_competencies(
        self,
        documentation_subject_ids: set[str] | None = None,
    ) -> tuple[object, ...]:
        subject_ids = (
            self._active_documentation_subject_ids()
            if documentation_subject_ids is None
            else documentation_subject_ids
        )
        return tuple(
            competency
            for competency in self._active_current_competencies()
            if getattr(competency, "subject_id") in subject_ids
        )

    def _student_documentation_subject_service(
        self,
    ) -> StudentDocumentationSubjectService:
        return StudentDocumentationSubjectService(
            self.database.connect,
            now_provider=self._now_provider,
        )

    def _effective_documentation_subject_ids(self, student_id: str) -> set[str]:
        school_year = self.current_school_year()
        if school_year is None:
            return set()
        return set(
            self._student_documentation_subject_service().effective_documentation_subjects(
                student_id,
                school_year.school_year_id,
            )
        )

    def _competency_status_projection_from_batch(
        self,
        batch: StudentDocumentationProjectionBatch,
        student_id: str,
        *,
        retained_competency_ids: tuple[str, ...] = (),
    ) -> tuple[StudentCompetencyStatusViewModel, ...]:
        return self._competency_status_projection_from_sources(
            observations=batch.observations_by_student.get(student_id, ()),
            confirmations=batch.confirmations_by_student.get(student_id, ()),
            freshness_by_competency=batch.freshness_by_student.get(
                student_id,
                {},
            ),
            competencies=batch.competencies,
            retained_competency_ids=retained_competency_ids,
        )

    def _observation_list_items_from_batch(
        self,
        batch: StudentDocumentationProjectionBatch,
        student_id: str,
        *,
        documents: tuple[DocumentRecord, ...] = (),
    ) -> tuple[ObservationListItem, ...]:
        documents_by_observation: dict[str, list[DocumentRecord]] = {}
        for document in documents:
            if document.observation_id:
                documents_by_observation.setdefault(
                    document.observation_id,
                    [],
                ).append(document)
        return tuple(
            ObservationListItem(
                observation.observation_id,
                observation.student_id,
                observation.date,
                self._subject_display_name(observation),
                observation.context,
                observation.note,
                tuple(
                    ObservationRatingViewModel(
                        rating.competency_id,
                        rating.subject_display_name,
                        rating.learning_area,
                        rating.competency_group,
                        rating.competency_text,
                        rating.rating,
                        subject_id=rating.subject_id,
                    )
                    for rating in observation.competency_ratings
                ),
                tuple(
                    self._document_view_model(document)
                    for document in documents_by_observation.get(
                        observation.observation_id,
                        (),
                    )
                ),
                (
                    not observation.competency_ratings
                    and bool(observation.note.strip())
                ),
            )
            for observation in batch.observations_by_student.get(
                student_id,
                (),
            )
        )

    def _documentation_statuses_by_student(
        self,
        batch: StudentDocumentationProjectionBatch,
    ) -> dict[str, tuple[StudentDocumentationSubjectStatus, ...]]:
        documentation_subject_ids = set(
            batch.active_documentation_subject_ids
        )
        documentation_competencies = tuple(
            competency
            for competency in batch.competencies
            if competency.active
            and competency.catalog_status == "current"
            and competency.subject_id in documentation_subject_ids
        )
        statuses_by_student: dict[
            str,
            tuple[StudentDocumentationSubjectStatus, ...],
        ] = {}
        for student in batch.students:
            documented_ids = {
                rating.competency_id
                for observation in batch.observations_by_student.get(
                    student.student_id,
                    (),
                )
                for rating in observation.competency_ratings
            } | {
                confirmation.competency_id
                for confirmation in batch.confirmations_by_student.get(
                    student.student_id,
                    (),
                )
            }
            statuses_by_student[student.student_id] = (
                self._documentation_statuses(
                    documentation_competencies,
                    documented_ids,
                )
            )
        return statuses_by_student

    def _documentation_summary_for_student(
        self,
        student_id: str,
    ) -> StudentDocumentationSummaryViewModel:
        return documentation_summary_from_subjects(
            self.list_documentation_status_for_student(student_id)
        )

    def _documentation_statuses(
        self,
        active_competencies: tuple[object, ...],
        documented_ids: set[str],
    ) -> tuple[StudentDocumentationSubjectStatus, ...]:
        grouped: dict[str, list[object]] = {}
        subject_names: dict[str, str] = {}
        subject_sort_orders: dict[str, int] = {}
        for competency in active_competencies:
            subject_id = getattr(competency, "subject_id")
            grouped.setdefault(subject_id, []).append(competency)
            subject_names.setdefault(
                subject_id,
                getattr(competency, "subject_name", subject_id),
            )
            subject_sort_orders[subject_id] = min(
                subject_sort_orders.get(subject_id, getattr(competency, "sort_order", 0)),
                getattr(competency, "sort_order", 0),
            )
        return tuple(
            StudentDocumentationSubjectStatus(
                subject_id,
                subject_names[subject_id],
                len({getattr(item, "competency_id") for item in grouped[subject_id] if getattr(item, "competency_id") in documented_ids}),
                len({getattr(item, "competency_id") for item in grouped[subject_id]}),
                self._missing_competencies_for_subject(
                    active_competencies,
                    documented_ids,
                    subject_id,
                ),
                subject_sort_orders[subject_id],
                self._documentation_learning_area_statuses(
                    grouped[subject_id], documented_ids
                ),
            )
            for subject_id in sorted(
                grouped,
                key=lambda key: (subject_sort_orders[key], key),
            )
        )

    def _documentation_learning_area_statuses(
        self,
        competencies: list[object],
        documented_ids: set[str],
    ) -> tuple[StudentDocumentationLearningAreaStatus, ...]:
        grouped: dict[str, set[str]] = {}
        for competency in competencies:
            learning_area = getattr(competency, "learning_area", "")
            if learning_area:
                grouped.setdefault(learning_area, set()).add(
                    getattr(competency, "competency_id")
                )
        return tuple(
            StudentDocumentationLearningAreaStatus(
                learning_area,
                len(competency_ids & documented_ids),
                len(competency_ids),
            )
            for learning_area, competency_ids in sorted(grouped.items())
        )

    def _missing_competencies_for_subject(
        self,
        active_competencies: tuple[object, ...],
        documented_ids: set[str],
        subject_id: str,
    ) -> tuple[StudentMissingCompetencyViewModel, ...]:
        return tuple(
            StudentMissingCompetencyViewModel(
                getattr(competency, "competency_id"),
                getattr(competency, "label"),
                getattr(competency, "sort_order", 0),
            )
            for competency in active_competencies
            if getattr(competency, "subject_id") == subject_id
            and getattr(competency, "competency_id") not in documented_ids
        )

    def _report_subject_sections(
        self,
        competency_groups: tuple[StudentCompetencySubjectGroup, ...],
        observations: tuple[ObservationListItem, ...],
    ) -> tuple[StudentReportSubjectSectionViewModel, ...]:
        sections = tuple(
            self._report_subject_section(group, observations)
            for group in competency_groups
        )
        return tuple(section for section in sections if section.has_content)

    def _report_subject_section(
        self,
        group: StudentCompetencySubjectGroup,
        observations: tuple[ObservationListItem, ...],
    ) -> StudentReportSubjectSectionViewModel:
        competency_lines = tuple(
            self._report_competency_line(competency)
            for competency in group.competencies
        )
        strengths = tuple(
            competency
            for competency in competency_lines
            if competency.rating in ("++", "+")
        )
        support_needs = tuple(
            competency
            for competency in competency_lines
            if competency.rating == "--"
        )
        return StudentReportSubjectSectionViewModel(
            group.subject_id,
            group.subject_display_name,
            competency_lines,
            strengths,
            tuple(
                self._report_development_line(competency)
                for competency in group.competencies
                if competency.rating_history
            ),
            support_needs,
            self._report_evidence_for_subject(group, observations),
        )

    def _report_competency_line(
        self,
        competency: StudentCompetencyStatusViewModel,
    ) -> StudentReportCompetencyViewModel:
        if competency.documentation_state == "confirmation_unknown":
            rating = ""
            source = "Bestätigungsstand unklar – bitte erneut bestätigen"
        else:
            rating = competency.confirmed_rating or competency.rating
            source = (
                "von Laura bestätigt"
                if competency.confirmed_rating
                else "aus Beobachtungen abgeleitet"
            )
        return StudentReportCompetencyViewModel(
            competency.competency_id,
            competency.competency_label,
            rating,
            source,
            observation_rating_label(rating, competency),
        )

    def _report_development_line(
        self,
        competency: StudentCompetencyStatusViewModel,
    ) -> StudentReportDevelopmentViewModel:
        history = competency.rating_history
        return StudentReportDevelopmentViewModel(
            competency.competency_id,
            competency.competency_label,
            self._report_development_label(history),
            history,
        )

    def _report_development_label(self, rating_history: tuple[str, ...]) -> str:
        if not rating_history:
            return "Noch keine Beobachtungen dokumentiert."
        if len(rating_history) == 1:
            return "Einzelbeobachtung vorhanden, noch kein Verlauf ableitbar."
        if len(set(rating_history)) == 1:
            return f"Stabil beobachtet: {rating_history[-1]}"
        scores = tuple(OBSERVATION_RATING_SCORES[rating] for rating in rating_history)
        if self._is_monotonic(scores, increasing=True) and scores[-1] > scores[0]:
            return (
                f"Entwicklung: {rating_history[0]} → {rating_history[-1]} · "
                "positive Entwicklung erkennbar"
            )
        if self._is_monotonic(scores, increasing=False) and scores[-1] < scores[0]:
            return (
                f"Entwicklung: {rating_history[0]} → {rating_history[-1]} · "
                "erneute Beobachtung sinnvoll"
            )
        return (
            "Wechselnde Beobachtungslage, weitere Beobachtungen sinnvoll. "
            f"Verlauf: {' → '.join(rating_history)}"
        )

    def _is_monotonic(self, scores: tuple[int, ...], *, increasing: bool) -> bool:
        if increasing:
            return all(left <= right for left, right in zip(scores, scores[1:]))
        return all(left >= right for left, right in zip(scores, scores[1:]))

    def _report_evidence_for_subject(
        self,
        group: StudentCompetencySubjectGroup,
        observations: tuple[ObservationListItem, ...],
    ) -> tuple[StudentReportEvidenceViewModel, ...]:
        evidence: list[StudentReportEvidenceViewModel] = []
        for observation in observations:
            matching_ratings = tuple(
                rating
                for rating in observation.competency_ratings
                if rating.subject_display_name == group.subject_display_name
            )
            if not matching_ratings:
                continue
            evidence.append(
                StudentReportEvidenceViewModel(
                    observation.observation_id,
                    observation.date_text,
                    observation.context,
                    self._report_note_preview(observation.note),
                    tuple(
                        f"{rating.rating} {rating.learning_area}"
                        for rating in matching_ratings
                    ),
                )
            )
        return tuple(evidence[:3])

    def _report_note_preview(self, note: str, max_length: int = 96) -> str:
        cleaned_note = " ".join(note.split())
        if len(cleaned_note) <= max_length:
            return cleaned_note
        return f"{cleaned_note[:max_length].rstrip()}..."
