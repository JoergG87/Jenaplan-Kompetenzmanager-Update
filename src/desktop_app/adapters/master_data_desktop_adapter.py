"""Master-data adapter for the PySide6 desktop app."""

from __future__ import annotations

from datetime import date

from src.core.maintenance_gate import product_writer
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
    COURSE_GROUP_DUPLICATE_NAME_MESSAGE,
    CourseGroupViewModel,
    MasterDataItemViewModel,
    MasterDataViewModel,
    course_color_name,
    normalize_master_data_name,
    validate_course_year_level,
)


class MasterDataDesktopAdapter:
    """Load and persist group, course and course-group master data."""

    def __init__(self, student_adapter: StudentDesktopAdapter) -> None:
        self.student_adapter = student_adapter
        self.database = student_adapter.database
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

    @product_writer
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

    @product_writer
    def add_course(
        self,
        name: str,
        color_hex: str = "",
        year_level: int | None = None,
    ) -> MasterDataItemViewModel:
        """Persist a new course."""
        normalized_name = normalize_master_data_name(name)
        validated_year_level = validate_course_year_level(year_level)
        selected_color_hex = color_hex or "#2563EB"
        record = MasterDataCourseRecord(
            self.repository.next_course_id(),
            normalized_name,
            course_color_name(selected_color_hex),
            selected_color_hex,
            True,
            len(self.courses),
            validated_year_level,
        )
        self.repository.upsert_course(record)
        self._append_course_to_default_course_group(record.course_id)
        self._reload()
        return self.courses[record.course_id]

    @product_writer
    def rename_group(
        self,
        group_id: str,
        name: str,
        *,
        active: bool | None = None,
        as_of: date | None = None,
    ) -> MasterDataItemViewModel:
        """Persist a group master-data change without changing membership."""
        item = self.groups[group_id]
        selected_active = item.is_active if active is None else bool(active)
        record = MasterDataGroupRecord(
            group_id,
            normalize_master_data_name(name),
            selected_active,
            self._group_sort_order(group_id),
        )
        self.repository.upsert_student_group(
            record,
            as_of=as_of if not selected_active else None,
        )
        self._reload()
        return self.groups[group_id]

    @product_writer
    def rename_course(
        self,
        course_id: str,
        name: str,
        color_hex: str | None = None,
        *,
        year_level: int | None = None,
        active: bool | None = None,
        as_of: date | None = None,
    ) -> MasterDataItemViewModel:
        """Persist course master data without changing membership."""
        item = self.courses[course_id]
        selected_color_hex = color_hex or item.color_hex
        selected_year_level = validate_course_year_level(
            item.year_level if year_level is None else year_level
        )
        selected_active = item.is_active if active is None else bool(active)
        record = MasterDataCourseRecord(
            course_id,
            normalize_master_data_name(name),
            course_color_name(selected_color_hex),
            selected_color_hex,
            selected_active,
            self._course_sort_order(course_id),
            selected_year_level,
        )
        self.repository.upsert_course(
            record,
            as_of=as_of if not selected_active else None,
        )
        self._reload()
        return self.courses[course_id]

    @product_writer
    def update_course_group(
        self,
        course_group_id: str,
        name: str,
        selected_group_ids: tuple[str, ...],
        selected_course_ids: tuple[str, ...],
    ) -> CourseGroupViewModel:
        """Persist one course-group configuration atomically."""
        normalized_name = normalize_master_data_name(name)
        self._validate_unique_course_group_name(normalized_name, course_group_id)
        updated_course_group = CourseGroupViewModel(
            course_group_id,
            normalized_name,
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

    @product_writer
    def add_course_group(
        self,
        name: str,
        selected_group_ids: tuple[str, ...],
        selected_course_ids: tuple[str, ...],
    ) -> CourseGroupViewModel:
        """Persist a new course group."""
        course_group_id = self.repository.next_course_group_id()
        return self.update_course_group(
            course_group_id,
            name,
            selected_group_ids,
            selected_course_ids,
        )

    def _reload(self) -> None:
        self.groups = {
            group.group_id: MasterDataItemViewModel(
                group.group_id,
                group.group_name,
                True,
                is_active=group.active,
            )
            for group in self.repository.list_student_groups()
        }
        self.courses = {
            course.course_id: MasterDataItemViewModel(
                course.course_id,
                course.course_name,
                True,
                course.color_name,
                course.color_hex,
                course.year_level,
                course.active,
            )
            for course in self.repository.list_courses()
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

    def _validate_unique_course_group_name(
        self,
        name: str,
        current_course_group_id: str,
    ) -> None:
        normalized_name = name.casefold()
        for course_group in self.course_groups.values():
            if course_group.course_group_id == current_course_group_id:
                continue
            if course_group.name.casefold() == normalized_name:
                raise ValueError(COURSE_GROUP_DUPLICATE_NAME_MESSAGE)
