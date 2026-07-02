"""Master-data adapter for the PySide6 desktop app."""

from __future__ import annotations

from src.core.sqlite_store import (
    DEFAULT_COURSE_GROUP_ID,
    MasterDataCourseGroupRecord,
    MasterDataCourseRecord,
    MasterDataGroupRecord,
    SQLiteMasterDataRepository,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.master_data_view_model import (
    COURSE_GROUP_EMPTY_COURSES_MESSAGE,
    COURSE_GROUP_EMPTY_GROUPS_MESSAGE,
    CourseGroupViewModel,
    MasterDataItemViewModel,
    MasterDataViewModel,
    course_color_name,
    normalize_master_data_name,
)


class MasterDataDesktopAdapter:
    """Load and persist group, course and course-group master data."""

    def __init__(self, student_adapter: StudentDesktopAdapter) -> None:
        self.student_adapter = student_adapter
        self.repository = SQLiteMasterDataRepository(student_adapter.database)
        self.groups: dict[str, MasterDataItemViewModel] = {}
        self.courses: dict[str, MasterDataItemViewModel] = {}
        self.course_groups: dict[str, CourseGroupViewModel] = {}
        self._reload()

    def view_model(self) -> MasterDataViewModel:
        """Return the current persistent master-data state."""
        self._reload()
        return MasterDataViewModel(
            groups=tuple(self.groups.values()),
            courses=tuple(self.courses.values()),
            course_groups=tuple(self.course_groups.values()),
        )

    def add_group(self, name: str) -> MasterDataItemViewModel:
        """Persist a new group."""
        normalized_name = normalize_master_data_name(name)
        record = MasterDataGroupRecord(
            self.repository.next_student_group_id(),
            normalized_name,
            True,
            len(self.groups),
        )
        self.repository.upsert_student_group(record)
        self._append_group_to_default_course_group(record.group_id)
        self._reload()
        return self.groups[record.group_id]

    def add_course(
        self,
        name: str,
        color_hex: str = "",
    ) -> MasterDataItemViewModel:
        """Persist a new course."""
        normalized_name = normalize_master_data_name(name)
        selected_color_hex = color_hex or "#2563EB"
        record = MasterDataCourseRecord(
            self.repository.next_course_id(),
            normalized_name,
            course_color_name(selected_color_hex),
            selected_color_hex,
            True,
            len(self.courses),
        )
        self.repository.upsert_course(record)
        self._append_course_to_default_course_group(record.course_id)
        self._reload()
        return self.courses[record.course_id]

    def rename_group(self, group_id: str, name: str) -> MasterDataItemViewModel:
        """Persist a group rename."""
        item = self.groups[group_id]
        record = MasterDataGroupRecord(
            group_id,
            normalize_master_data_name(name),
            item.is_persistent,
            self._group_sort_order(group_id),
        )
        self.repository.upsert_student_group(record)
        self._reload()
        return self.groups[group_id]

    def rename_course(
        self,
        course_id: str,
        name: str,
        color_hex: str | None = None,
    ) -> MasterDataItemViewModel:
        """Persist a course rename and color change."""
        item = self.courses[course_id]
        selected_color_hex = color_hex or item.color_hex
        record = MasterDataCourseRecord(
            course_id,
            normalize_master_data_name(name),
            course_color_name(selected_color_hex),
            selected_color_hex,
            item.is_persistent,
            self._course_sort_order(course_id),
        )
        self.repository.upsert_course(record)
        self._reload()
        return self.courses[course_id]

    def update_course_group(
        self,
        course_group_id: str,
        name: str,
        selected_group_ids: tuple[str, ...],
        selected_course_ids: tuple[str, ...],
    ) -> CourseGroupViewModel:
        """Persist one course-group configuration atomically."""
        updated_course_group = CourseGroupViewModel(
            course_group_id,
            normalize_master_data_name(name),
            tuple(group_id for group_id in selected_group_ids if group_id in self.groups),
            tuple(course_id for course_id in selected_course_ids if course_id in self.courses),
        )
        if not updated_course_group.selected_group_ids:
            raise ValueError(COURSE_GROUP_EMPTY_GROUPS_MESSAGE)
        if not updated_course_group.selected_course_ids:
            raise ValueError(COURSE_GROUP_EMPTY_COURSES_MESSAGE)
        self.repository.update_course_group(
            MasterDataCourseGroupRecord(
                updated_course_group.course_group_id,
                updated_course_group.name,
                updated_course_group.selected_group_ids,
                updated_course_group.selected_course_ids,
                True,
                self._course_group_sort_order(course_group_id),
            )
        )
        self._reload()
        return self.course_groups[course_group_id]

    def _reload(self) -> None:
        self.groups = {
            group.group_id: MasterDataItemViewModel(
                group.group_id,
                group.group_name,
                True,
            )
            for group in self.repository.list_student_groups()
            if group.active
        }
        self.courses = {
            course.course_id: MasterDataItemViewModel(
                course.course_id,
                course.course_name,
                True,
                course.color_name,
                course.color_hex,
            )
            for course in self.repository.list_courses()
            if course.active
        }
        self.course_groups = {
            course_group.course_group_id: CourseGroupViewModel(
                course_group.course_group_id,
                course_group.name,
                tuple(
                    group_id
                    for group_id in course_group.selected_group_ids
                    if group_id in self.groups
                ),
                tuple(
                    course_id
                    for course_id in course_group.selected_course_ids
                    if course_id in self.courses
                ),
            )
            for course_group in self.repository.list_course_groups()
            if course_group.active
        }

    def _append_group_to_default_course_group(self, group_id: str) -> None:
        course_group = self.course_groups.get(DEFAULT_COURSE_GROUP_ID)
        if course_group is None or group_id in course_group.selected_group_ids:
            return
        self.repository.update_course_group(
            MasterDataCourseGroupRecord(
                course_group.course_group_id,
                course_group.name,
                (*course_group.selected_group_ids, group_id),
                course_group.selected_course_ids,
                True,
                self._course_group_sort_order(course_group.course_group_id),
            )
        )

    def _append_course_to_default_course_group(self, course_id: str) -> None:
        course_group = self.course_groups.get(DEFAULT_COURSE_GROUP_ID)
        if course_group is None or course_id in course_group.selected_course_ids:
            return
        self.repository.update_course_group(
            MasterDataCourseGroupRecord(
                course_group.course_group_id,
                course_group.name,
                course_group.selected_group_ids,
                (*course_group.selected_course_ids, course_id),
                True,
                self._course_group_sort_order(course_group.course_group_id),
            )
        )

    def _group_sort_order(self, group_id: str) -> int:
        return tuple(self.groups).index(group_id) if group_id in self.groups else len(self.groups)

    def _course_sort_order(self, course_id: str) -> int:
        return (
            tuple(self.courses).index(course_id)
            if course_id in self.courses
            else len(self.courses)
        )

    def _course_group_sort_order(self, course_group_id: str) -> int:
        return (
            tuple(self.course_groups).index(course_group_id)
            if course_group_id in self.course_groups
            else len(self.course_groups)
        )
