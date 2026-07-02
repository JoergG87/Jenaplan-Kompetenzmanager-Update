"""Student adapter for the PySide6 desktop app."""

from __future__ import annotations

from pathlib import Path

from src.application.commands import CreateStudentCommand
from src.application.dispatcher import (
    ApplicationCommandDispatcher,
    student_create_handler,
)
from src.core.sqlite_store import (
    SQLITE_SPIKE_PATH,
    SQLiteCourseRepository,
    SQLiteDatabase,
    SQLiteGroupRepository,
    SQLiteStudentRepository,
    create_sqlite_seed_database,
)
from src.core.student import StudentService, StudentValidator
from src.core.workbook_data import CourseRecord, GroupRecord, StudentRecord
from src.desktop_app.view_models.master_data_view_model import course_color_from_key
from src.desktop_app.view_models.student_view_model import (
    GroupSummaryViewModel,
    StudentDetailViewModel,
    StudentListItem,
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
        courses = {
            course.course_id: course
            for course in self.list_courses()
        }
        students = SQLiteStudentRepository(self.database).list_students()
        return tuple(
            self._student_list_item(student, groups, courses)
            for student in students
            if self._matches_filter(student, group_id, group_ids, course_id)
        )

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

    def _dispatcher(self) -> ApplicationCommandDispatcher:
        student_repository = SQLiteStudentRepository(self.database)
        group_ids = tuple(group.group_id for group in self.list_groups())
        course_ids = tuple(course.course_id for course in self.list_courses())
        service = StudentService(
            student_repository,
            StudentValidator(),
            group_ids,
            course_ids,
        )
        dispatcher = ApplicationCommandDispatcher()
        dispatcher.register("student.create", student_create_handler(service))
        return dispatcher

    def _open_database(self) -> SQLiteDatabase:
        if not self.database_path.exists():
            return create_sqlite_seed_database(self.database_path)
        database = SQLiteDatabase(self.database_path)
        database.initialize_schema()
        database.ensure_master_data_defaults()
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
