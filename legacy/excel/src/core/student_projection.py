"""Student projection builder for workbook data."""

from __future__ import annotations

from .workbook_data import CourseRecord, GroupRecord, StudentRecord, WorkbookData


class StudentProjectionBuilder:
    """Create workbook data projections from student records."""

    def __init__(
        self,
        groups: tuple[GroupRecord, ...],
        courses: tuple[CourseRecord, ...],
        default_group_id: str,
        default_student_id: str,
        school_year: str,
    ) -> None:
        self.groups = groups
        self.courses = courses
        self.default_group_id = default_group_id
        self.default_student_id = default_student_id
        self.school_year = school_year

    def build(self, students: tuple[StudentRecord, ...]) -> WorkbookData:
        return WorkbookData(
            students=students,
            groups=self.groups,
            courses=self.courses,
            student_card_projection=self._sort_student_card_projection(students),
            default_group_id=self.default_group_id,
            default_student_id=self.default_student_id,
            school_year=self.school_year,
        )

    def _sort_student_card_projection(
        self,
        students: tuple[StudentRecord, ...],
    ) -> tuple[StudentRecord, ...]:
        return tuple(
            sorted(
                students,
                key=lambda student: (
                    student.course_id.casefold(),
                    student.last_name.casefold(),
                    student.first_name.casefold(),
                ),
            )
        )
