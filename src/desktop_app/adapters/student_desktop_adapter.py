"""Student adapter for the PySide6 desktop app."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.application.commands import (
    CreateObservationCommand,
    CreateStudentCommand,
    DeleteObservationCommand,
    UpdateObservationCommand,
)
from src.application.dispatcher import (
    ApplicationCommandDispatcher,
    observation_create_handler,
    observation_delete_handler,
    observation_update_handler,
    student_create_handler,
)
from src.core.observation import (
    ObservationCompetencyRatingRecord,
    ObservationService,
    ObservationValidator,
)
from src.core.sqlite_store import (
    SQLITE_SPIKE_PATH,
    SQLiteCourseRepository,
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteGroupRepository,
    SQLiteObservationRepository,
    SQLiteStudentCompetencyConfirmationRepository,
    SQLiteStudentRepository,
    StudentCompetencyConfirmationRecord,
)
from src.core.student import StudentService, StudentValidator
from src.core.workbook_data import CourseRecord, GroupRecord, StudentRecord
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from src.desktop_app.view_models.master_data_view_model import course_color_from_key
from src.desktop_app.view_models.observation_view_model import (
    OBSERVATION_CROSS_SUBJECT_LABEL,
    ObservationDraftViewModel,
    ObservationCompetencyRatingDraft,
    ObservationListItem,
    ObservationRatingViewModel,
    StudentCompetencyStatusViewModel,
    StudentCompetencySubjectGroup,
    calculated_rating_from_history,
    observation_rating_label,
)
from src.desktop_app.view_models.student_view_model import (
    GroupSummaryViewModel,
    StudentDetailViewModel,
    StudentListItem,
    StudentReportCompetencyViewModel,
    StudentReportEvidenceViewModel,
    StudentReportPreviewViewModel,
    StudentReportSubjectSectionViewModel,
    sort_student_list,
)


class StudentDesktopAdapter:
    """Thin adapter between Qt widgets and the application command layer."""

    def __init__(self, database_path: Path = SQLITE_SPIKE_PATH) -> None:
        self.database_path = Path(database_path)
        self.database = self._open_database()

    def list_students(
        self,
        *,
        group_id: str | None = None,
        group_ids: tuple[str, ...] = (),
        course_id: str | None = None,
    ) -> tuple[StudentListItem, ...]:
        """Return students with readable group and course names."""
        groups = {group.group_id: group.group_name for group in self.list_groups()}
        course_records = self.list_courses()
        courses = {course.course_id: course for course in course_records}
        course_order_by_id = {
            course.course_id: index
            for index, course in enumerate(course_records)
        }
        students = SQLiteStudentRepository(self.database).list_students()
        loaded_students = tuple(
            self._student_list_item(student, groups, courses)
            for student in students
            if self._matches_filter(student, group_id, group_ids, course_id)
        )
        return sort_student_list(loaded_students, course_order_by_id)

    def get_student_profile(self, student_id: str) -> StudentDetailViewModel | None:
        """Return a light profile view model for one student."""
        student = SQLiteStudentRepository(self.database).get_student_by_id(student_id)
        if student is None:
            return None
        groups = {group.group_id: group.group_name for group in self.list_groups()}
        courses = {course.course_id: course.course_name for course in self.list_courses()}
        return StudentDetailViewModel(
            student.student_id,
            f"{student.first_name} {student.last_name}",
            groups.get(student.group_id, student.group_id),
            courses.get(student.course_id, student.course_id),
            student.student_notes,
            student.active,
        )

    def list_group_summaries(self) -> tuple[GroupSummaryViewModel, ...]:
        """Return group cards for the app overview."""
        students = SQLiteStudentRepository(self.database).list_students()
        active_counts = {
            group.group_id: sum(
                1
                for student in students
                if student.group_id == group.group_id and student.active
            )
            for group in self.list_groups()
        }
        return tuple(
            GroupSummaryViewModel(
                group.group_id,
                group.group_name,
                active_counts.get(group.group_id, 0),
            )
            for group in self.list_groups()
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

    def group_id_by_name(self) -> dict[str, str]:
        """Map visible group names to stable group IDs."""
        return {group.group_name: group.group_id for group in self.list_groups()}

    def course_id_by_name(self) -> dict[str, str]:
        """Map visible course names to stable course IDs."""
        return {course.course_name: course.course_id for course in self.list_courses()}

    def create_student_command(
        self,
        *,
        first_name: str,
        last_name: str,
        group_id: str,
        course_id: str,
        student_notes: str = "",
    ) -> CreateStudentCommand:
        """Create a student command from GUI input state."""
        return CreateStudentCommand(
            first_name=first_name,
            last_name=last_name,
            group_id=group_id,
            course_id=course_id,
            student_notes=student_notes,
        )

    def save_new_student(
        self,
        *,
        first_name: str,
        last_name: str,
        group_id: str,
        course_id: str,
        student_notes: str = "",
    ) -> object:
        """Persist a new student through the existing application stack."""
        command = self.create_student_command(
            first_name=first_name,
            last_name=last_name,
            group_id=group_id,
            course_id=course_id,
            student_notes=student_notes,
        )
        return self._dispatcher().dispatch(command)

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
        )

    def save_observation(self, draft: ObservationDraftViewModel) -> object:
        """Persist an observation through the application stack."""
        command = self.create_observation_command(draft)
        return self._dispatcher().dispatch(command)

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
        )

    def update_observation(self, draft: ObservationDraftViewModel) -> object:
        """Update an existing observation through the application stack."""
        command = self.create_update_observation_command(draft)
        return self._dispatcher().dispatch(command)

    def delete_observation(self, observation_id: str) -> object:
        """Soft-delete an observation through the application stack."""
        command = DeleteObservationCommand(observation_id=observation_id)
        return self._dispatcher().dispatch(command)

    def observation_draft_for_edit(
        self,
        observation_id: str,
    ) -> ObservationDraftViewModel | None:
        """Return an editable draft for one persisted observation."""
        observation = SQLiteObservationRepository(self.database).get_observation(
            observation_id
        )
        if observation is None or not observation.active:
            return None
        student = self.get_student_profile(observation.student_id)
        return ObservationDraftViewModel(
            student_id=observation.student_id,
            student_name=student.display_name if student else observation.student_id,
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
            observation_id=observation.observation_id,
        )

    def list_observations_for_student(
        self,
        student_id: str,
    ) -> tuple[ObservationListItem, ...]:
        """Return persisted observations for the profile view."""
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
                    )
                    for rating in observation.competency_ratings
                ),
            )
            for observation in observations
        )

    def list_competency_overview_for_student(
        self,
        student_id: str,
    ) -> tuple[StudentCompetencySubjectGroup, ...]:
        """Return calculated competency statuses grouped by subject."""
        observations = SQLiteObservationRepository(
            self.database
        ).list_observations_for_student(student_id)
        competencies = {
            competency.competency_id: competency
            for competency in SQLiteCompetencyRepository(
                self.database
            ).list_competencies()
        }
        confirmations = {
            confirmation.competency_id: confirmation
            for confirmation in SQLiteStudentCompetencyConfirmationRepository(
                self.database
            ).list_confirmations_for_student(student_id)
        }
        histories_by_competency: dict[str, list[tuple[object, str]]] = {}
        for observation in observations:
            for rating in observation.competency_ratings:
                histories_by_competency.setdefault(rating.competency_id, []).append(
                    (rating, observation.date)
                )
        statuses = tuple(
            self._competency_status_view_model(
                tuple(entries),
                competencies.get(competency_id),
                confirmations.get(competency_id),
            )
            for competency_id, entries in histories_by_competency.items()
        )
        return self._group_competency_statuses(statuses)

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

    def save_competency_confirmation(
        self,
        *,
        student_id: str,
        competency_id: str,
        confirmed_rating: str,
        note: str = "",
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
        ).upsert_confirmation(confirmation)

    def _dispatcher(self) -> ApplicationCommandDispatcher:
        student_repository = SQLiteStudentRepository(self.database)
        observation_repository = SQLiteObservationRepository(self.database)
        group_ids = tuple(group.group_id for group in self.list_groups())
        course_ids = tuple(course.course_id for course in self.list_courses())
        student_service = StudentService(
            student_repository,
            StudentValidator(),
            group_ids,
            course_ids,
        )
        observation_service = ObservationService(
            observation_repository,
            ObservationValidator(),
            tuple(student.student_id for student in student_repository.list_students()),
        )
        dispatcher = ApplicationCommandDispatcher()
        dispatcher.register("student.create", student_create_handler(student_service))
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

    def _open_database(self) -> SQLiteDatabase:
        database = SQLiteDatabase(self.database_path)
        database.initialize_schema()
        database.ensure_master_data_defaults()
        SQLiteCompetencyRepository(database).ensure_catalog_defaults(
            CurriculumDesktopAdapter().list_entries()
        )
        return database

    def _student_list_item(
        self,
        student: StudentRecord,
        groups: dict[str, str],
        courses: dict[str, CourseRecord],
    ) -> StudentListItem:
        course = courses.get(student.course_id)
        course_name = student.course_id
        course_color_name = ""
        course_color_hex = ""
        if course is not None:
            course_name = course.course_name
            course_index = tuple(courses).index(course.course_id)
            course_color_name, course_color_hex = course_color_from_key(
                course.color_key,
                course_index,
            )
        return StudentListItem(
            student.student_id,
            student.first_name,
            student.last_name,
            student.group_id,
            groups.get(student.group_id, student.group_id),
            student.course_id,
            course_name,
            course_color_name,
            course_color_hex,
        )

    def _matches_filter(
        self,
        student: StudentRecord,
        group_id: str | None,
        group_ids: tuple[str, ...],
        course_id: str | None,
    ) -> bool:
        if group_id and student.group_id != group_id:
            return False
        if group_ids and student.group_id not in group_ids:
            return False
        if course_id and student.course_id != course_id:
            return False
        return True

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
        entries_newest_first: tuple[tuple[object, str], ...],
        competency: object | None,
        confirmation: StudentCompetencyConfirmationRecord | None,
    ) -> StudentCompetencyStatusViewModel:
        newest_rating, newest_date = entries_newest_first[0]
        ratings_newest_first = tuple(
            getattr(rating, "rating")
            for rating, _date in entries_newest_first
        )
        current_rating, weighted_score = calculated_rating_from_history(
            ratings_newest_first
        )
        subject_id = getattr(
            competency,
            "subject_id",
            getattr(newest_rating, "subject_id"),
        )
        subject_display_name = getattr(
            competency,
            "subject_name",
            getattr(newest_rating, "subject_display_name"),
        )
        competency_label = getattr(
            competency,
            "label",
            getattr(newest_rating, "learning_area"),
        )
        sort_order = int(getattr(competency, "sort_order", 0))
        return StudentCompetencyStatusViewModel(
            getattr(newest_rating, "competency_id"),
            competency_label,
            subject_id,
            subject_display_name,
            current_rating,
            observation_rating_label(current_rating),
            newest_date,
            sort_order,
            tuple(reversed(ratings_newest_first)),
            len(entries_newest_first),
            weighted_score,
            confirmation.confirmed_rating if confirmation else "",
            confirmation.confirmed_at if confirmation else "",
            confirmation.note if confirmation else "",
        )

    def _group_competency_statuses(
        self,
        statuses: tuple[StudentCompetencyStatusViewModel, ...],
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
            )
            for subject_id in groups
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
        return StudentReportSubjectSectionViewModel(
            group.subject_id,
            group.subject_display_name,
            tuple(
                competency
                for competency in competency_lines
                if competency.rating in ("++", "+")
            ),
            tuple(
                competency
                for competency in competency_lines
                if competency.rating == "-"
            ),
            tuple(
                competency
                for competency in competency_lines
                if competency.rating == "--"
            ),
            self._report_evidence_for_subject(group, observations),
        )

    def _report_competency_line(
        self,
        competency: StudentCompetencyStatusViewModel,
    ) -> StudentReportCompetencyViewModel:
        rating = competency.confirmed_rating or competency.rating
        source = "Bestätigt" if competency.confirmed_rating else "Vorschlag"
        return StudentReportCompetencyViewModel(
            competency.competency_id,
            competency.competency_label,
            rating,
            source,
            observation_rating_label(rating),
        )

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
