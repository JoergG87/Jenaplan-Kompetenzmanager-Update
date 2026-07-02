"""Master-data light screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.view_models.master_data_view_model import (
    CourseGroupViewModel,
    MasterDataItemViewModel,
    MasterDataViewModel,
)


MASTER_DATA_GROUP_EMPTY_STATE = "Noch keine Stammgruppen vorhanden."
MASTER_DATA_COURSE_EMPTY_STATE = "Noch keine Kurse vorhanden."
MASTER_DATA_COURSE_GROUP_EMPTY_STATE = "Noch keine Kursverbünde vorhanden."


class MasterDataScreen(QWidget):
    """Show group and course master data without productive persistence."""

    group_add_requested = Signal()
    group_rename_requested = Signal(str)
    course_add_requested = Signal()
    course_rename_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.group_items: tuple[MasterDataItemViewModel, ...] = ()
        self.course_items: tuple[MasterDataItemViewModel, ...] = ()
        self.course_group_items: tuple[CourseGroupViewModel, ...] = ()
        self.group_empty_state_label = QLabel(MASTER_DATA_GROUP_EMPTY_STATE)
        self.course_empty_state_label = QLabel(MASTER_DATA_COURSE_EMPTY_STATE)
        self.course_group_empty_state_label = QLabel(MASTER_DATA_COURSE_GROUP_EMPTY_STATE)
        self.group_table = QTableWidget(0, 3)
        self.course_table = QTableWidget(0, 4)
        self.course_group_table = QTableWidget(0, 3)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Stammdaten")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        subtitle = QLabel("Stammgruppen und Kurse verwalten")
        subtitle.setStyleSheet("color: #555;")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(
            self._section_card(
                "Stammgruppen",
                "+ Stammgruppe",
                self.group_table,
                self.group_empty_state_label,
                self.group_add_requested.emit,
            )
        )
        layout.addWidget(
            self._section_card(
                "Kurse",
                "+ Kurs",
                self.course_table,
                self.course_empty_state_label,
                self.course_add_requested.emit,
            )
        )
        layout.addWidget(
            self._readonly_section_card(
                "Kursverbünde",
                self.course_group_table,
                self.course_group_empty_state_label,
            )
        )
        layout.addStretch(1)

    def set_master_data(self, view_model: MasterDataViewModel) -> None:
        """Replace all displayed master-data rows."""
        self.group_items = view_model.groups
        self.course_items = view_model.courses
        self.course_group_items = view_model.course_groups
        self._render_group_table(
            self.group_table,
            self.group_items,
            self.group_rename_requested.emit,
        )
        self._render_course_table(
            self.course_table,
            self.course_items,
            self.course_rename_requested.emit,
        )
        self._render_course_group_table(
            self.course_group_table,
            self.course_group_items,
            self.group_items,
            self.course_items,
        )

    def _section_card(
        self,
        title: str,
        add_button_label: str,
        table: QTableWidget,
        empty_state_label: QLabel,
        add_handler: object,
    ) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet("QFrame { background: #ffffff; border-radius: 6px; }")
        layout = QVBoxLayout(card)
        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        add_button = QPushButton(add_button_label)
        add_button.clicked.connect(add_handler)
        header.addWidget(title_label)
        header.addStretch(1)
        header.addWidget(add_button)
        layout.addLayout(header)

        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(150)
        empty_state_label.setStyleSheet("color: #666;")
        layout.addWidget(empty_state_label)
        layout.addWidget(table)
        return card

    def _readonly_section_card(
        self,
        title: str,
        table: QTableWidget,
        empty_state_label: QLabel,
    ) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet("QFrame { background: #ffffff; border-radius: 6px; }")
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title_label)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(120)
        empty_state_label.setStyleSheet("color: #666;")
        layout.addWidget(empty_state_label)
        layout.addWidget(table)
        return card

    def _render_group_table(
        self,
        table: QTableWidget,
        items: tuple[MasterDataItemViewModel, ...],
        rename_handler: object,
    ) -> None:
        table.setHorizontalHeaderLabels(("Name", "Status", "Aktion"))
        table.setRowCount(len(items))
        self.group_empty_state_label.setVisible(not items)
        for row_index, item in enumerate(items):
            table.setItem(row_index, 0, QTableWidgetItem(item.name))
            table.setItem(row_index, 1, QTableWidgetItem(item.status_label))
            rename_button = QPushButton("Umbenennen")
            rename_button.clicked.connect(
                lambda _checked=False, item_id=item.item_id: rename_handler(item_id)
            )
            table.setCellWidget(row_index, 2, rename_button)

    def _render_course_table(
        self,
        table: QTableWidget,
        items: tuple[MasterDataItemViewModel, ...],
        rename_handler: object,
    ) -> None:
        table.setHorizontalHeaderLabels(("Farbe", "Name", "Status", "Aktion"))
        table.setRowCount(len(items))
        self.course_empty_state_label.setVisible(not items)
        for row_index, item in enumerate(items):
            color_item = QTableWidgetItem(f"● {item.color_name}")
            color_item.setForeground(QColor(item.color_hex))
            table.setItem(row_index, 0, color_item)
            table.setItem(row_index, 1, QTableWidgetItem(item.name))
            table.setItem(row_index, 2, QTableWidgetItem(item.status_label))
            rename_button = QPushButton("Umbenennen")
            rename_button.clicked.connect(
                lambda _checked=False, item_id=item.item_id: rename_handler(item_id)
            )
            table.setCellWidget(row_index, 3, rename_button)

    def _render_course_group_table(
        self,
        table: QTableWidget,
        items: tuple[CourseGroupViewModel, ...],
        groups: tuple[MasterDataItemViewModel, ...],
        courses: tuple[MasterDataItemViewModel, ...],
    ) -> None:
        table.setHorizontalHeaderLabels(("Name", "Stammgruppen", "Kurse"))
        table.setRowCount(len(items))
        self.course_group_empty_state_label.setVisible(not items)
        groups_by_id = {group.item_id: group.name for group in groups}
        courses_by_id = {course.item_id: course.name for course in courses}
        for row_index, item in enumerate(items):
            group_names = ", ".join(
                groups_by_id[group_id]
                for group_id in item.selected_group_ids
                if group_id in groups_by_id
            )
            course_names = ", ".join(
                courses_by_id[course_id]
                for course_id in item.selected_course_ids
                if course_id in courses_by_id
            )
            table.setItem(row_index, 0, QTableWidgetItem(item.name))
            table.setItem(row_index, 1, QTableWidgetItem(group_names))
            table.setItem(row_index, 2, QTableWidgetItem(course_names))
