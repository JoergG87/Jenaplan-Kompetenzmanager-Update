"""Master-data light screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)

from src.desktop_app.view_models.master_data_view_model import (
    CourseGroupViewModel,
    MasterDataItemViewModel,
    MasterDataViewModel,
)
from src.desktop_app.components import (
    AppCard,
    EmptyState,
    PageHeader,
    SectionHeader,
    configure_button,
)
from src.desktop_app.theme import set_label_style


MASTER_DATA_GROUP_EMPTY_STATE = (
    "Noch keine Stammgruppen angelegt. Über „+ Stammgruppe“ kannst du die erste anlegen."
)
MASTER_DATA_COURSE_EMPTY_STATE = (
    "Noch keine Kurse angelegt. Über „+ Kurs“ kannst du den ersten anlegen."
)
MASTER_DATA_COURSE_GROUP_EMPTY_STATE = (
    "Noch keine Kursverbünde angelegt. Über „+ Kursverbund“ kannst du den ersten anlegen."
)


class MasterDataScreen(QWidget):
    """Show group and course master data without productive persistence."""

    group_add_requested = Signal()
    group_rename_requested = Signal(str)
    course_add_requested = Signal()
    course_rename_requested = Signal(str)
    course_group_add_requested = Signal()
    course_group_edit_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.group_items: tuple[MasterDataItemViewModel, ...] = ()
        self.course_items: tuple[MasterDataItemViewModel, ...] = ()
        self.course_group_items: tuple[CourseGroupViewModel, ...] = ()
        self.group_empty_state = EmptyState(MASTER_DATA_GROUP_EMPTY_STATE)
        self.course_empty_state = EmptyState(MASTER_DATA_COURSE_EMPTY_STATE)
        self.course_group_empty_state = EmptyState(MASTER_DATA_COURSE_GROUP_EMPTY_STATE)
        self.group_empty_state_label = self.group_empty_state.label
        self.course_empty_state_label = self.course_empty_state.label
        self.course_group_empty_state_label = self.course_group_empty_state.label
        self.group_table = QTableWidget(0, 3)
        self.group_table.setAccessibleName("Stammgruppen verwalten")
        self.course_table = QTableWidget(0, 4)
        self.course_table.setAccessibleName("Kurse verwalten")
        self.course_group_table = QTableWidget(0, 4)
        self.course_group_table.setAccessibleName("Kursverbünde verwalten")
        for table in (
            self.group_table,
            self.course_table,
            self.course_group_table,
        ):
            table.installEventFilter(self)
            table.cellDoubleClicked.connect(
                lambda row, _column, source=table: self._activate_table_row(
                    source,
                    row,
                )
            )
        self._build()

    def eventFilter(self, watched: object, event: QEvent) -> bool:  # noqa: N802
        if (
            watched in {
                self.group_table,
                self.course_table,
                self.course_group_table,
            }
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        ):
            self._activate_table_row(watched, watched.currentRow())
            return True
        return super().eventFilter(watched, event)

    def _activate_table_row(self, table: QTableWidget, row: int) -> None:
        if table is self.group_table and 0 <= row < len(self.group_items):
            self.group_rename_requested.emit(self.group_items[row].item_id)
        elif table is self.course_table and 0 <= row < len(self.course_items):
            self.course_rename_requested.emit(self.course_items[row].item_id)
        elif (
            table is self.course_group_table
            and 0 <= row < len(self.course_group_items)
        ):
            self.course_group_edit_requested.emit(
                self.course_group_items[row].course_group_id
            )

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(
            PageHeader(
                "Stammdaten",
                "Strukturen verwalten, die in Schülern, Kursen und Stundenplan verwendet werden",
            )
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 16)
        content_layout.setSpacing(14)
        content_layout.addWidget(
            self._section_card(
                "Stammgruppen",
                "Feste Bezugsgruppen der Kinder",
                "+ Stammgruppe",
                self.group_table,
                self.group_empty_state,
                self.group_add_requested.emit,
            )
        )
        content_layout.addWidget(
            self._section_card(
                "Kurse",
                "Kursstufen mit eigener Farbe",
                "+ Kurs",
                self.course_table,
                self.course_empty_state,
                self.course_add_requested.emit,
            )
        )
        content_layout.addWidget(
            self._section_card(
                "Kursverbünde",
                "Kurse über ausgewählte Stammgruppen hinweg",
                "+ Kursverbund",
                self.course_group_table,
                self.course_group_empty_state,
                self.course_group_add_requested.emit,
            )
        )
        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

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
            self.course_group_edit_requested.emit,
        )

    def _section_card(
        self,
        title: str,
        description: str,
        add_button_label: str,
        table: QTableWidget,
        empty_state: EmptyState,
        add_handler: object,
    ) -> QFrame:
        card = AppCard("default")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        add_button = QPushButton(add_button_label)
        configure_button(add_button, "secondary", add_button_label.lstrip("+ "))
        add_button.clicked.connect(add_handler)
        section_header = SectionHeader(title, description)
        section_header.add_action(add_button)
        layout.addWidget(section_header)

        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setObjectName("PremiumTable")
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(44)
        table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setMinimumHeight(150)
        table.setAccessibleDescription(
            "Mit Enter oder Doppelklick bearbeiten; die sichtbare Aktion ist auch mit Tab erreichbar."
        )
        layout.addWidget(empty_state)
        layout.addWidget(table)
        return card

    def _render_group_table(
        self,
        table: QTableWidget,
        items: tuple[MasterDataItemViewModel, ...],
        rename_handler: object,
    ) -> None:
        table.clearContents()
        table.setHorizontalHeaderLabels(("Name", "Status", "Aktion"))
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(1, 110)
        table.setColumnWidth(2, 125)
        table.setRowCount(len(items))
        self.group_empty_state.setVisible(not items)
        table.setVisible(bool(items))
        for row_index, item in enumerate(items):
            table.setItem(row_index, 0, QTableWidgetItem(item.name))
            table.setItem(row_index, 1, QTableWidgetItem(item.status_label))
            rename_button = QPushButton("Umbenennen")
            configure_button(
                rename_button,
                "quiet",
                f"Stammgruppe {item.name} umbenennen",
            )
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
        table.clearContents()
        table.setHorizontalHeaderLabels(("Farbe", "Name", "Status", "Aktion"))
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 125)
        table.setColumnWidth(2, 110)
        table.setColumnWidth(3, 125)
        table.setRowCount(len(items))
        self.course_empty_state.setVisible(not items)
        table.setVisible(bool(items))
        for row_index, item in enumerate(items):
            table.setCellWidget(row_index, 0, self._course_color_cell(item))
            table.setItem(row_index, 1, QTableWidgetItem(item.name))
            table.setItem(row_index, 2, QTableWidgetItem(item.status_label))
            rename_button = QPushButton("Umbenennen")
            configure_button(
                rename_button,
                "quiet",
                f"Kurs {item.name} umbenennen",
            )
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
        edit_handler: object,
    ) -> None:
        table.clearContents()
        table.setHorizontalHeaderLabels(("Name", "Stammgruppen", "Kurse", "Aktion"))
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(3, 125)
        table.setRowCount(len(items))
        self.course_group_empty_state.setVisible(not items)
        table.setVisible(bool(items))
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
            edit_button = QPushButton("Bearbeiten")
            configure_button(
                edit_button,
                "secondary",
                f"Kursverbund {item.name} bearbeiten",
            )
            edit_button.clicked.connect(
                lambda _checked=False, item_id=item.course_group_id: edit_handler(item_id)
            )
            table.setCellWidget(row_index, 3, edit_button)

    @staticmethod
    def _course_color_cell(item: MasterDataItemViewModel) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(7)
        marker = QFrame()
        marker.setObjectName("CourseColorMarker")
        marker.setFixedSize(10, 10)
        palette = marker.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(item.color_hex))
        marker.setPalette(palette)
        marker.setAutoFillBackground(True)
        label = QLabel(item.color_name)
        layout.addWidget(marker)
        layout.addWidget(label)
        layout.addStretch(1)
        return cell
