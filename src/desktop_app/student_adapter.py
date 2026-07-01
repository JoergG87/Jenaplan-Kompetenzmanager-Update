"""Application adapter for the experimental PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass
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
from src.core.workbook_data import CourseRecord, GroupRecord


@dataclass(frozen=True)
class StudentListItem:
    """Display-ready student row for desktop lists."""

    student_id: str
    first_name: str
    last_name: str
    group_name: str
    course_name: str

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class StudentDesktopAdapter:
    """Thin adapter between Qt widgets and the application command layer."""

    def __init__(self, database_path: Path = SQLITE_SPIKE_PATH) -> None:
        self.database_path = Path(database_path)
        self.database = self._open_database()

    def list_students(self) -> tuple[StudentListItem, ...]:
        """Return students with readable group and course names."""
        groups = {group.group_id: group.group_name for group in self.list_groups()}
        courses = {course.course_id: course.course_name for course in self.list_courses()}
        return tuple(
            StudentListItem(
                student.student_id,
                student.first_name,
                student.last_name,
                groups.get(student.group_id, student.group_id),
                courses.get(student.course_id, student.course_id),
            )
            for student in SQLiteStudentRepository(self.database).list_students()
        )

    def list_groups(self) -> tuple[GroupRecord, ...]:
        """Return active groups for the new-student dropdown."""
        return tuple(
            group
            for group in SQLiteGroupRepository(self.database).list_groups()
            if group.active
        )

    def list_courses(self) -> tuple[CourseRecord, ...]:
        """Return active courses for the new-student dropdown."""
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
        return database
