"""Master-data light screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.components import (
    AppCard,
    CourseBadge,
    EmptyState,
    PageHeader,
    SectionHeader,
    StatusBadge,
    configure_button,
)
from src.desktop_app.theme import set_label_style
from src.desktop_app.view_models.master_data_view_model import (
    CourseGroupViewModel,
    MasterDataItemViewModel,
    MasterDataViewModel,
)


MASTER_DATA_GROUP_EMPTY_STATE = (
    "Noch keine Stammgruppen angelegt. Mit „+ Stammgruppe“ kannst du die erste anlegen."
)
MASTER_DATA_COURSE_EMPTY_STATE = (
    "Noch keine Kurse angelegt. Mit „+ Kurs“ kannst du den ersten anlegen."
)
MASTER_DATA_COURSE_GROUP_EMPTY_STATE = (
    "Noch keine Kursverbünde angelegt. Mit „+ Kursverbund“ kannst du den ersten anlegen."
)


class MasterDataScreen(QWidget):
    """Show the existing group, course, and course-group projections."""

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
        self.course_table = QTableWidget(0, 5)
        self.course_table.setAccessibleName("Kurse verwalten")
        self.course_group_table = QTableWidget(0, 3)
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
                "Stammgruppen, Kurse und Kursverbünde zentral verwalten",
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
                "Feste Bezugsgruppen der Kinder und ihr Datenstatus",
                "+ Stammgruppe",
                self.group_table,
                self.group_empty_state,
                self.group_add_requested.emit,
            )
        )
        content_layout.addWidget(
            self._section_card(
                "Kurse",
                "Kursstufen mit dezenter Farborientierung",
                "+ Kurs",
                self.course_table,
                self.course_empty_state,
                self.course_add_requested.emit,
            )
        )
        content_layout.addWidget(
            self._section_card(
                "Kursverbünde",
                "Zusammengehörige Stammgruppen und Kurse auf einen Blick",
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
        table.setAlternatingRowColors(False)
        table.setObjectName("PremiumTable")
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.TextElideMode.ElideRight)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(46)
        table.horizontalHeader().setFixedHeight(36)
        table.horizontalHeader().setSectionsClickable(False)
        table.horizontalHeader().setHighlightSections(False)
        table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        table.setAccessibleDescription(
            "Eine Zeile mit Enter oder Doppelklick bearbeiten; die sichtbare Aktion ist auch mit Tab erreichbar."
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
        table.setHorizontalHeaderLabels(("Stammgruppe", "Status", ""))
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(1, 126)
        table.setColumnWidth(2, 116)
        action_header = table.horizontalHeaderItem(2)
        action_header.setData(Qt.ItemDataRole.AccessibleTextRole, "Bearbeiten")
        action_header.setToolTip("Bearbeiten")
        table.setRowCount(len(items))
        table.setFixedHeight(38 + (min(max(len(items), 1), 6) * 46))
        self.group_empty_state.setVisible(not items)
        table.setVisible(bool(items))
        for row_index, item in enumerate(items):
            name_item = QTableWidgetItem(item.name)
            name_item.setToolTip(item.name)
            name_item.setData(Qt.ItemDataRole.AccessibleTextRole, item.name)
            table.setItem(row_index, 0, name_item)

            status_cell = QWidget()
            status_cell.setAccessibleName(
                f"Status: {item.status_label} · {item.activity_label}"
            )
            status_layout = QHBoxLayout(status_cell)
            status_layout.setContentsMargins(10, 0, 6, 0)
            status_badge = StatusBadge(
                item.activity_label,
                tone="info" if item.is_active else "neutral",
            )
            status_layout.addWidget(status_badge, 0, Qt.AlignmentFlag.AlignLeft)
            status_layout.addStretch(1)
            table.setCellWidget(row_index, 1, status_cell)

            rename_button = QPushButton("Bearbeiten")
            configure_button(
                rename_button,
                "quiet",
                f"Stammgruppe {item.name} bearbeiten",
            )
            rename_button.setToolTip(f"Stammgruppe {item.name} bearbeiten")
            rename_button.setMinimumWidth(96)
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
        table.setHorizontalHeaderLabels(
            ("Kurs", "Kursstufe", "Kursfarbe", "Status", "")
        )
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(1, 112)
        table.setColumnWidth(2, 154)
        table.setColumnWidth(3, 126)
        table.setColumnWidth(4, 116)
        action_header = table.horizontalHeaderItem(4)
        action_header.setData(Qt.ItemDataRole.AccessibleTextRole, "Bearbeiten")
        action_header.setToolTip("Bearbeiten")
        table.setRowCount(len(items))
        table.setFixedHeight(38 + (min(max(len(items), 1), 6) * 46))
        self.course_empty_state.setVisible(not items)
        table.setVisible(bool(items))
        for row_index, item in enumerate(items):
            name_item = QTableWidgetItem(item.name)
            name_item.setToolTip(item.name)
            name_item.setData(Qt.ItemDataRole.AccessibleTextRole, item.name)
            table.setItem(row_index, 0, name_item)
            year_level_item = QTableWidgetItem(item.year_level_label)
            year_level_item.setData(
                Qt.ItemDataRole.AccessibleTextRole,
                item.year_level_label,
            )
            table.setItem(row_index, 1, year_level_item)
            table.setCellWidget(row_index, 2, self._course_color_cell(item))

            status_cell = QWidget()
            status_cell.setAccessibleName(
                f"Status: {item.status_label} · {item.activity_label}"
            )
            status_layout = QHBoxLayout(status_cell)
            status_layout.setContentsMargins(10, 0, 6, 0)
            status_badge = StatusBadge(
                item.activity_label,
                tone="info" if item.is_active else "neutral",
            )
            status_layout.addWidget(status_badge, 0, Qt.AlignmentFlag.AlignLeft)
            status_layout.addStretch(1)
            table.setCellWidget(row_index, 3, status_cell)

            rename_button = QPushButton("Bearbeiten")
            configure_button(
                rename_button,
                "quiet",
                f"Kurs {item.name} bearbeiten",
            )
            rename_button.setToolTip(f"Kurs {item.name} bearbeiten")
            rename_button.setMinimumWidth(96)
            rename_button.clicked.connect(
                lambda _checked=False, item_id=item.item_id: rename_handler(item_id)
            )
            table.setCellWidget(row_index, 4, rename_button)

    def _render_course_group_table(
        self,
        table: QTableWidget,
        items: tuple[CourseGroupViewModel, ...],
        groups: tuple[MasterDataItemViewModel, ...],
        courses: tuple[MasterDataItemViewModel, ...],
        edit_handler: object,
    ) -> None:
        table.clearContents()
        table.setHorizontalHeaderLabels(("Kursverbund", "Zuordnung", ""))
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 268)
        table.setColumnWidth(2, 116)
        action_header = table.horizontalHeaderItem(2)
        action_header.setData(Qt.ItemDataRole.AccessibleTextRole, "Bearbeiten")
        action_header.setToolTip("Bearbeiten")
        table.setRowCount(len(items))
        table.verticalHeader().setDefaultSectionSize(62)
        table.setFixedHeight(38 + (min(max(len(items), 1), 5) * 62))
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
            name_item = QTableWidgetItem(item.name)
            name_item.setToolTip(item.name)
            name_item.setData(Qt.ItemDataRole.AccessibleTextRole, item.name)
            table.setItem(row_index, 0, name_item)

            relation_cell = QWidget()
            relation_cell.setAccessibleName(
                f"Stammgruppen: {group_names or 'Keine'}; Kurse: {course_names or 'Keine'}"
            )
            relation_layout = QVBoxLayout(relation_cell)
            relation_layout.setContentsMargins(10, 6, 8, 6)
            relation_layout.setSpacing(2)
            group_label = QLabel(f"Stammgruppen · {group_names or 'Keine'}")
            group_label.setToolTip(group_names)
            group_label.setAccessibleName("")
            course_label = QLabel(f"Kurse · {course_names or 'Keine'}")
            course_label.setToolTip(course_names)
            course_label.setAccessibleName("")
            set_label_style(course_label, "muted")
            relation_layout.addWidget(group_label)
            relation_layout.addWidget(course_label)
            table.setCellWidget(row_index, 1, relation_cell)

            edit_button = QPushButton("Bearbeiten")
            configure_button(
                edit_button,
                "quiet",
                f"Kursverbund {item.name} bearbeiten",
            )
            edit_button.setToolTip(f"Kursverbund {item.name} bearbeiten")
            edit_button.setMinimumWidth(96)
            edit_button.clicked.connect(
                lambda _checked=False, item_id=item.course_group_id: edit_handler(item_id)
            )
            table.setCellWidget(row_index, 2, edit_button)

    @staticmethod
    def _course_color_cell(item: MasterDataItemViewModel) -> QWidget:
        cell = QWidget()
        cell.setAccessibleName(
            f"Kursfarbe {item.color_name}; dient zur Orientierung und Zugehörigkeit"
        )
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(10, 0, 6, 0)
        badge = CourseBadge(item.color_name, item.color_hex)
        badge.setAccessibleName("")
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return cell
