"""Student entity reference implementation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from .constants import (
    ACTIVE,
    ARCHIVED_AT,
    COURSE_ID,
    CREATED_AT,
    FIRST_NAME,
    GROUP_ID,
    ID_SEQUENCE_WIDTH,
    LAST_NAME,
    STUDENT_ID,
    STUDENT_ID_PREFIX,
    STUDENT_NOTES,
    UPDATED_AT,
)
from .workbook_data import StudentRecord


class StudentValidationError(ValueError):
    """Raised when student data violates the registered student schema."""


class StudentRepositoryError(RuntimeError):
    """Raised when student storage cannot be updated consistently."""


class StudentValidator:
    """Validate student data against service-provided reference data."""

    def validate(
        self,
        student_data: dict[str, object],
        valid_group_ids: Iterable[str],
        valid_course_ids: Iterable[str],
    ) -> None:
        group_ids = set(valid_group_ids)
        course_ids = set(valid_course_ids)

        self._require_text(student_data, FIRST_NAME)
        self._require_text(student_data, LAST_NAME)
        group_id = self._require_text(student_data, GROUP_ID)
        course_id = self._require_text(student_data, COURSE_ID)

        if group_id not in group_ids:
            raise StudentValidationError(f"Unbekannte group_id: {group_id}")
        if course_id not in course_ids:
            raise StudentValidationError(f"Unbekannte course_id: {course_id}")

        if STUDENT_NOTES in student_data and student_data[STUDENT_NOTES] is not None:
            if not isinstance(student_data[STUDENT_NOTES], str):
                raise StudentValidationError("student_notes muss Text sein.")

        if ACTIVE in student_data and not isinstance(student_data[ACTIVE], bool):
            raise StudentValidationError("active muss ein boolescher Wert sein.")

        active = student_data.get(ACTIVE, True)
        archived_at = student_data.get(ARCHIVED_AT)
        if active is True and archived_at not in (None, ""):
            raise StudentValidationError("archived_at darf nur gesetzt sein, wenn active = FALSE ist.")

    def _require_text(self, student_data: dict[str, object], field_name: str) -> str:
        value = student_data.get(field_name)
        if value is None:
            raise StudentValidationError(f"Pflichtfeld fehlt: {field_name}")
        if not isinstance(value, str):
            raise StudentValidationError(f"{field_name} muss Text sein.")
        cleaned_value = value.strip()
        if not cleaned_value:
            raise StudentValidationError(f"{field_name} darf nicht leer sein.")
        return cleaned_value


class StudentRepository:
    """Read and write student records only."""

    def __init__(self, students: Iterable[StudentRecord] = ()) -> None:
        self._students = tuple(students)

    def create_student(self, student: StudentRecord) -> StudentRecord:
        if self.get_student_by_id(student.student_id) is not None:
            raise StudentRepositoryError(f"student_id existiert bereits: {student.student_id}")
        self._students = (*self._students, student)
        return student

    def update_student(self, student: StudentRecord) -> StudentRecord:
        return self._replace_student(student)

    def archive_student(self, student: StudentRecord) -> StudentRecord:
        return self._replace_student(student)

    def get_student(self, student_id: str) -> StudentRecord | None:
        return self.get_student_by_id(student_id)

    def get_student_by_id(self, student_id: str) -> StudentRecord | None:
        for student in self._students:
            if student.student_id == student_id:
                return student
        return None

    def list_students(self) -> tuple[StudentRecord, ...]:
        return self._students

    def _replace_student(self, student: StudentRecord) -> StudentRecord:
        updated_students = []
        found_student = False
        for existing_student in self._students:
            if existing_student.student_id == student.student_id:
                updated_students.append(student)
                found_student = True
            else:
                updated_students.append(existing_student)

        if not found_student:
            raise StudentRepositoryError(f"student_id nicht gefunden: {student.student_id}")

        self._students = tuple(updated_students)
        return student


class StudentService:
    """Coordinate student write processes."""

    def __init__(
        self,
        repository: StudentRepository,
        validator: StudentValidator,
        valid_group_ids: Iterable[str],
        valid_course_ids: Iterable[str],
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.validator = validator
        self.valid_group_ids = tuple(valid_group_ids)
        self.valid_course_ids = tuple(valid_course_ids)
        self.now_provider = now_provider or (lambda: datetime.now(UTC))

    def create_student(
        self,
        first_name: str,
        last_name: str,
        group_id: str,
        course_id: str,
        student_notes: str = "",
    ) -> StudentRecord:
        student_data = {
            FIRST_NAME: first_name,
            LAST_NAME: last_name,
            GROUP_ID: group_id,
            COURSE_ID: course_id,
            STUDENT_NOTES: student_notes,
            ACTIVE: True,
            ARCHIVED_AT: None,
        }
        self.validator.validate(student_data, self.valid_group_ids, self.valid_course_ids)

        timestamp = self._timestamp()
        student = StudentRecord(
            self._generate_student_id(),
            first_name.strip(),
            last_name.strip(),
            group_id.strip(),
            course_id.strip(),
            student_notes,
            True,
            timestamp,
            timestamp,
            None,
        )
        return self.repository.create_student(student)

    def update_student(
        self,
        student_id: str,
        first_name: str,
        last_name: str,
        group_id: str,
        course_id: str,
        student_notes: str = "",
    ) -> StudentRecord:
        existing_student = self._require_existing_student(student_id)
        student_data = {
            STUDENT_ID: existing_student.student_id,
            FIRST_NAME: first_name,
            LAST_NAME: last_name,
            GROUP_ID: group_id,
            COURSE_ID: course_id,
            STUDENT_NOTES: student_notes,
            ACTIVE: existing_student.active,
            ARCHIVED_AT: existing_student.archived_at,
        }
        self.validator.validate(student_data, self.valid_group_ids, self.valid_course_ids)

        updated_student = StudentRecord(
            existing_student.student_id,
            first_name.strip(),
            last_name.strip(),
            group_id.strip(),
            course_id.strip(),
            student_notes,
            existing_student.active,
            existing_student.created_at,
            self._timestamp(),
            existing_student.archived_at,
        )
        return self.repository.update_student(updated_student)

    def archive_student(self, student_id: str) -> StudentRecord:
        existing_student = self._require_existing_student(student_id)
        timestamp = self._timestamp()
        archived_student = StudentRecord(
            existing_student.student_id,
            existing_student.first_name,
            existing_student.last_name,
            existing_student.group_id,
            existing_student.course_id,
            existing_student.student_notes,
            False,
            existing_student.created_at,
            timestamp,
            timestamp,
        )
        self.validator.validate(
            {
                STUDENT_ID: archived_student.student_id,
                FIRST_NAME: archived_student.first_name,
                LAST_NAME: archived_student.last_name,
                GROUP_ID: archived_student.group_id,
                COURSE_ID: archived_student.course_id,
                STUDENT_NOTES: archived_student.student_notes,
                ACTIVE: archived_student.active,
                ARCHIVED_AT: archived_student.archived_at,
            },
            self.valid_group_ids,
            self.valid_course_ids,
        )
        return self.repository.archive_student(archived_student)

    def _generate_student_id(self) -> str:
        used_ids = {student.student_id for student in self.repository.list_students()}
        next_number = 1
        while True:
            student_id = f"{STUDENT_ID_PREFIX}-{next_number:0{ID_SEQUENCE_WIDTH}}"
            if student_id not in used_ids:
                return student_id
            next_number += 1

    def _require_existing_student(self, student_id: str) -> StudentRecord:
        student = self.repository.get_student_by_id(student_id)
        if student is None:
            raise StudentRepositoryError(f"student_id nicht gefunden: {student_id}")
        return student

    def _timestamp(self) -> str:
        return self.now_provider().replace(microsecond=0).isoformat()
