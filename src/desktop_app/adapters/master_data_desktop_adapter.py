"""Master-data light adapter for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import replace

from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.master_data_view_model import (
    COURSE_GROUP_EMPTY_COURSES_MESSAGE,
    COURSE_GROUP_EMPTY_GROUPS_MESSAGE,
    CourseGroupViewModel,
    MasterDataItemViewModel,
    MasterDataViewModel,
    course_color_from_key,
    course_color_name,
    normalize_master_data_name,
)


class MasterDataDesktopAdapter:
    """Keep a non-persistent master-data draft for groups and courses."""

    def __init__(self, student_adapter: StudentDesktopAdapter) -> None:
        self.student_adapter = student_adapter
        self.groups: dict[str, MasterDataItemViewModel] = {
            group.group_id: MasterDataItemViewModel(
                group.group_id,
                group.group_name,
                True,
            )
            for group in student_adapter.list_groups()
        }
        self.courses: dict[str, MasterDataItemViewModel] = {}
        for index, course in enumerate(student_adapter.list_courses()):
            color_name, color_hex = course_color_from_key(course.color_key, index)
            self.courses[course.course_id] = MasterDataItemViewModel(
                course.course_id,
                course.course_name,
                True,
                color_name,
                color_hex,
            )
        self.course_groups: dict[str, CourseGroupViewModel] = {
            "course-group-default": CourseGroupViewModel(
                "course-group-default",
                "Mathe/Deutsch Kursverbund A",
                tuple(self.groups),
                tuple(self.courses),
            )
        }
        self._draft_group_counter = 0
        self._draft_course_counter = 0

    def view_model(self) -> MasterDataViewModel:
        """Return the current non-persistent master-data state."""
        return MasterDataViewModel(
            groups=tuple(self.groups.values()),
            courses=tuple(self.courses.values()),
            course_groups=tuple(self.course_groups.values()),
        )

    def add_group(self, name: str) -> MasterDataItemViewModel:
        """Add a non-persistent group draft."""
        self._draft_group_counter += 1
        item = MasterDataItemViewModel(
            f"draft-group-{self._draft_group_counter:03d}",
            normalize_master_data_name(name),
            False,
        )
        self.groups[item.item_id] = item
        self._append_group_to_default_course_group(item.item_id)
        return item

    def add_course(
        self,
        name: str,
        color_hex: str = "",
    ) -> MasterDataItemViewModel:
        """Add a non-persistent course draft."""
        self._draft_course_counter += 1
        selected_color_hex = color_hex or course_color_from_key(
            "",
            len(self.courses),
        )[1]
        item = MasterDataItemViewModel(
            f"draft-course-{self._draft_course_counter:03d}",
            normalize_master_data_name(name),
            False,
            course_color_name(selected_color_hex),
            selected_color_hex,
        )
        self.courses[item.item_id] = item
        self._append_course_to_default_course_group(item.item_id)
        return item

    def rename_group(self, group_id: str, name: str) -> MasterDataItemViewModel:
        """Rename a group in the non-persistent master-data draft."""
        return self._rename_item(self.groups, group_id, name)

    def rename_course(
        self,
        course_id: str,
        name: str,
        color_hex: str | None = None,
    ) -> MasterDataItemViewModel:
        """Rename a course in the non-persistent master-data draft."""
        item = self.courses[course_id]
        selected_color_hex = color_hex or item.color_hex
        renamed_item = replace(
            item,
            name=normalize_master_data_name(name),
            color_name=course_color_name(selected_color_hex),
            color_hex=selected_color_hex,
        )
        self.courses[course_id] = renamed_item
        return renamed_item

    def update_course_group(
        self,
        course_group_id: str,
        name: str,
        selected_group_ids: tuple[str, ...],
        selected_course_ids: tuple[str, ...],
    ) -> CourseGroupViewModel:
        """Update a session-local course-group configuration."""
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
        self.course_groups[course_group_id] = updated_course_group
        return updated_course_group

    def _rename_item(
        self,
        items: dict[str, MasterDataItemViewModel],
        item_id: str,
        name: str,
    ) -> MasterDataItemViewModel:
        item = replace(items[item_id], name=normalize_master_data_name(name))
        items[item_id] = item
        return item

    def _append_group_to_default_course_group(self, group_id: str) -> None:
        course_group = self.course_groups.get("course-group-default")
        if course_group is None or group_id in course_group.selected_group_ids:
            return
        self.course_groups[course_group.course_group_id] = replace(
            course_group,
            selected_group_ids=(*course_group.selected_group_ids, group_id),
        )

    def _append_course_to_default_course_group(self, course_id: str) -> None:
        course_group = self.course_groups.get("course-group-default")
        if course_group is None or course_id in course_group.selected_course_ids:
            return
        self.course_groups[course_group.course_group_id] = replace(
            course_group,
            selected_course_ids=(*course_group.selected_course_ids, course_id),
        )
