"""Overview screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.view_models.master_data_view_model import (
    CourseGroupViewModel,
    MasterDataItemViewModel,
    MasterDataViewModel,
)
from src.desktop_app.view_models.student_view_model import GroupSummaryViewModel
from src.desktop_app.theme import create_card, set_label_style


OVERVIEW_GROUP_EMPTY_STATE = "Noch keine Stammgruppen vorhanden."
OVERVIEW_COURSE_EMPTY_STATE = "Noch keine Kurse vorhanden."


class OverviewScreen(QWidget):
    """Start screen with lightweight group overview."""

    group_selected = Signal(str)
    course_selected = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.groups_layout = QGridLayout()
        self.course_groups_layout = QVBoxLayout()
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Übersicht")
        set_label_style(title, "screen_title")
        subtitle = QLabel("Stammgruppen und Schülerbestand")
        set_label_style(subtitle, "muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._section_card("Stammgruppen", self.groups_layout))
        layout.addWidget(self._section_card("Kursverbünde", self.course_groups_layout))
        layout.addStretch()

    def set_groups(self, groups: tuple[GroupSummaryViewModel, ...]) -> None:
        """Replace group cards."""
        view_model = MasterDataViewModel(
            groups=tuple(
                MasterDataItemViewModel(group.group_id, group.group_name, True)
                for group in groups
            ),
            courses=(),
        )
        self.set_master_data(view_model, groups)

    def set_master_data(
        self,
        view_model: MasterDataViewModel,
        group_summaries: tuple[GroupSummaryViewModel, ...] = (),
    ) -> None:
        """Replace overview lists with current master-data scope."""
        self._clear_layout(self.groups_layout)
        self._clear_layout(self.course_groups_layout)
        group_counts = {
            group.group_id: group.active_student_count
            for group in group_summaries
        }
        groups_by_id = {group.item_id: group for group in view_model.groups}
        courses_by_id = {course.item_id: course for course in view_model.courses}
        if not view_model.groups:
            self.groups_layout.addWidget(QLabel(OVERVIEW_GROUP_EMPTY_STATE), 0, 0)
        for index, group in enumerate(view_model.groups):
            count = group_counts.get(group.item_id)
            self.groups_layout.addWidget(
                self._group_card(group, count),
                index // 2,
                index % 2,
            )
        if not view_model.course_groups:
            self.course_groups_layout.addWidget(QLabel(OVERVIEW_COURSE_EMPTY_STATE))
        for course_group in view_model.course_groups:
            self.course_groups_layout.addWidget(
                self._course_group_card(course_group, groups_by_id, courses_by_id)
            )

    def _section_card(self, title: str, content_layout: object) -> QFrame:
        card = create_card()
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        set_label_style(title_label, "section_title")
        layout.addWidget(title_label)
        layout.addLayout(content_layout)
        return card

    def _group_card(
        self,
        group: MasterDataItemViewModel,
        active_student_count: int | None = None,
    ) -> QFrame:
        card = create_card()
        layout = QVBoxLayout(card)
        name = QLabel(group.name)
        set_label_style(name, "section_title")
        count_text = (
            f"{active_student_count} Schüler"
            if active_student_count is not None
            else group.status_label
        )
        count = QLabel(count_text)
        open_button = QPushButton("Schüler anzeigen")
        open_button.setEnabled(group.is_persistent)
        open_button.clicked.connect(lambda: self.group_selected.emit(group.item_id))
        layout.addWidget(name)
        layout.addWidget(count)
        layout.addWidget(open_button)
        return card

    def _course_group_card(
        self,
        course_group: CourseGroupViewModel,
        groups_by_id: dict[str, MasterDataItemViewModel],
        courses_by_id: dict[str, MasterDataItemViewModel],
    ) -> QFrame:
        card = create_card()
        layout = QVBoxLayout(card)
        title = QLabel(course_group.name)
        set_label_style(title, "section_title")
        group_names = tuple(
            groups_by_id[group_id].name
            for group_id in course_group.selected_group_ids
            if group_id in groups_by_id
        )
        groups_label = QLabel(f"Stammgruppen: {', '.join(group_names)}")
        set_label_style(groups_label, "muted")
        layout.addWidget(title)
        layout.addWidget(groups_label)
        for course_id in course_group.selected_course_ids:
            course = courses_by_id.get(course_id)
            if course is not None:
                layout.addWidget(self._course_row(course_group, course))
        return card

    def _course_row(
        self,
        course_group: CourseGroupViewModel,
        course: MasterDataItemViewModel,
    ) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        marker = QLabel("●")
        marker.setStyleSheet(f"color: {course.color_hex or '#6B7280'};")
        open_button = QPushButton(course.name)
        open_button.clicked.connect(
            lambda: self.course_selected.emit(
                course_group.course_group_id,
                course.item_id,
            )
        )
        status = QLabel(course.status_label)
        set_label_style(status, "subtle")
        layout.addWidget(marker)
        layout.addWidget(open_button)
        layout.addStretch(1)
        layout.addWidget(status)
        return row

    def _clear_layout(self, layout: object) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
