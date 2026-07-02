"""Master-data light adapter for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import replace

from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.master_data_view_model import (
    MasterDataItemViewModel,
    MasterDataViewModel,
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
        self.courses: dict[str, MasterDataItemViewModel] = {
            course.course_id: MasterDataItemViewModel(
                course.course_id,
                course.course_name,
                True,
            )
            for course in student_adapter.list_courses()
        }
        self._draft_group_counter = 0
        self._draft_course_counter = 0

    def view_model(self) -> MasterDataViewModel:
        """Return the current non-persistent master-data state."""
        return MasterDataViewModel(
            groups=tuple(self.groups.values()),
            courses=tuple(self.courses.values()),
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
        return item

    def add_course(self, name: str) -> MasterDataItemViewModel:
        """Add a non-persistent course draft."""
        self._draft_course_counter += 1
        item = MasterDataItemViewModel(
            f"draft-course-{self._draft_course_counter:03d}",
            normalize_master_data_name(name),
            False,
        )
        self.courses[item.item_id] = item
        return item

    def rename_group(self, group_id: str, name: str) -> MasterDataItemViewModel:
        """Rename a group in the non-persistent master-data draft."""
        return self._rename_item(self.groups, group_id, name)

    def rename_course(self, course_id: str, name: str) -> MasterDataItemViewModel:
        """Rename a course in the non-persistent master-data draft."""
        return self._rename_item(self.courses, course_id, name)

    def _rename_item(
        self,
        items: dict[str, MasterDataItemViewModel],
        item_id: str,
        name: str,
    ) -> MasterDataItemViewModel:
        item = replace(items[item_id], name=normalize_master_data_name(name))
        items[item_id] = item
        return item
