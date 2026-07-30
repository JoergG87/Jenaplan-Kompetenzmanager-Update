"""Editable Qt dialog for the transient SJ-3B.2b transition plan."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.application.school_year_transition_plan import (
    SchoolYearTransitionPlan,
    SchoolYearTransitionPlanError,
)
from src.desktop_app.components import AppCard, DialogHeader, InlineMessage
from src.desktop_app.components import configure_button
from src.desktop_app.motion import MotionDialog
from src.desktop_app.theme import set_label_style
from src.desktop_app.view_models.school_year_transition_preview_view_model import (
    SchoolYearTransitionDecisionOptionViewModel,
    SchoolYearTransitionPreviewRowViewModel,
    SchoolYearTransitionPreviewViewModel,
    apply_course_choice,
    apply_group_choice,
)


TABLE_HEADERS = (
    "Auswahl",
    "Kind",
    "Bisherige Stammgruppe",
    "Bisheriger Kurs",
    "Bisherige Kursstufe",
    "Zielstatus",
    "Zielstammgruppe",
    "Zielkurs",
    "Warnungen / Blocker",
)


class SchoolYearTransitionPreviewDialog(MotionDialog):
    """Edit one transient plan without repositories, writes, or execution."""

    def __init__(
        self,
        plan: SchoolYearTransitionPlan,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.plan = plan
        self.view_model = SchoolYearTransitionPreviewViewModel.from_plan(plan)
        self.setWindowTitle("Schuljahreswechsel-Vorschau")
        self.setAccessibleName("Schuljahreswechsel-Vorschau bearbeiten")
        self.setModal(True)
        self.setMinimumSize(520, 360)
        self.resize(1320, 720)
        self.table = QTableWidget(0, len(TABLE_HEADERS))
        self.table.setObjectName("SchoolYearTransitionPreviewTable")
        self.table.setAccessibleName("Flüchtiger Plan je Kind")
        self._decision_controls: list[QComboBox] = []
        self._selected_student_ids: set[str] = set()
        self._visible_student_ids: tuple[str, ...] = ()
        self._populating_table = False
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(
            DialogHeader(
                "Schuljahreswechsel-Vorschau",
                (
                    f"{self.view_model.current_school_year_label} → "
                    f"{self.view_model.planned_school_year_label}"
                ),
                (
                    "Individuelle Änderungen bleiben flüchtig. "
                    "Es werden keine Daten gespeichert oder ausgeführt."
                ),
                icon_name="info",
            )
        )
        layout.addWidget(self._summary_card())
        layout.addWidget(self._filter_card())
        layout.addWidget(self._bulk_card())

        self.status_message = InlineMessage()
        self.status_message.setObjectName("SchoolYearTransitionPreviewStatus")
        self.status_message.setAccessibleName("Status des flüchtigen Plans")
        layout.addWidget(self.status_message)

        self._configure_table()
        self.table.itemChanged.connect(self._selection_item_changed)
        layout.addWidget(self.table, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        self.buttons.setObjectName("DialogActionBar")
        self.buttons.setAccessibleName("Dialogaktionen")
        self.close_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Close
        )
        if self.close_button is not None:
            self.close_button.setText("Schließen")
            self.close_button.setDefault(True)
            self.close_button.setAutoDefault(True)
            self.close_button.setShortcut("Esc")
            configure_button(
                self.close_button,
                "secondary",
                "Vorschau schließen",
            )
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._refresh_from_plan()

    def _summary_card(self) -> AppCard:
        card = AppCard("soft")
        card.setObjectName("SchoolYearTransitionPreviewSummary")
        card.setAccessibleName("Zusammenfassung des flüchtigen Plans")
        form = QFormLayout(card)
        form.setContentsMargins(18, 14, 18, 14)
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(6)
        field_names = (
            "Aktuelles Schuljahr",
            "Geplantes neues Schuljahr",
            "Zeitraum",
            "Kinder gesamt",
            "Gelöst",
            "Wechsel 1 → 2",
            "Wechsel 2 → 3",
            "Anderer Kurs",
            "Kurs 3 wiederholen",
            "Ausgeschieden",
            "Ungelöst",
            "Individuell bearbeitet",
        )
        self.summary_labels: dict[str, QLabel] = {}
        for field_name in field_names:
            value_label = QLabel()
            set_label_style(value_label, "body")
            self.summary_labels[field_name] = value_label
            form.addRow(field_name, value_label)
        return card

    def _filter_card(self) -> AppCard:
        card = AppCard("soft")
        card.setObjectName("SchoolYearTransitionFilters")
        card.setAccessibleName("Filter für Kinder im flüchtigen Plan")
        grid = QGridLayout(card)
        grid.setContentsMargins(18, 14, 18, 14)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        self.unresolved_filter = self._filter_combo(
            "Statusfilter",
            (("Alle Kinder", False), ("Nur ungelöst", True)),
        )
        self.current_course_filter = self._filter_combo(
            "Filter bisheriger Kurs",
            (
                ("Alle bisherigen Kurse", None),
                *self._current_course_filter_options(),
            ),
        )
        self.target_course_filter = self._filter_combo(
            "Filter Zielkurs",
            (
                ("Alle Zielkurse", None),
                *((course.course_name, course.course_id)
                  for course in self.plan.available_courses),
            ),
        )
        self.current_group_filter = self._filter_combo(
            "Filter bisherige Stammgruppe",
            (
                ("Alle bisherigen Stammgruppen", None),
                *self._current_group_filter_options(),
            ),
        )
        self.target_group_filter = self._filter_combo(
            "Filter Zielstammgruppe",
            (
                ("Alle Zielstammgruppen", None),
                *((group.group_name, group.group_id)
                  for group in self.plan.available_groups),
            ),
        )
        filters = (
            ("Status", self.unresolved_filter),
            ("Bisheriger Kurs", self.current_course_filter),
            ("Zielkurs", self.target_course_filter),
            ("Bisherige Stammgruppe", self.current_group_filter),
            ("Zielstammgruppe", self.target_group_filter),
        )
        for column, (label, combo) in enumerate(filters):
            grid.addWidget(QLabel(label), 0, column)
            grid.addWidget(combo, 1, column)

        self.reset_filters_button = QPushButton("Alle Filter zurücksetzen")
        self.reset_filters_button.setObjectName(
            "SchoolYearTransitionResetFilters"
        )
        configure_button(
            self.reset_filters_button,
            "secondary",
            "Alle Filter zurücksetzen",
        )
        self.reset_filters_button.clicked.connect(self._reset_filters)
        grid.addWidget(self.reset_filters_button, 1, len(filters))
        for combo in (
            self.unresolved_filter,
            self.current_course_filter,
            self.target_course_filter,
            self.current_group_filter,
            self.target_group_filter,
        ):
            combo.currentIndexChanged.connect(self._filter_changed)
        return card

    def _bulk_card(self) -> AppCard:
        card = AppCard("soft")
        card.setObjectName("SchoolYearTransitionBulkActions")
        card.setAccessibleName("Auswahl und Sammelbearbeitung")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        selection_row = QHBoxLayout()
        self.selected_count_label = QLabel("0 Kinder ausgewählt")
        self.selected_count_label.setObjectName(
            "SchoolYearTransitionSelectedCount"
        )
        self.selected_count_label.setAccessibleName(
            "0 Kinder ausgewählt"
        )
        selection_row.addWidget(self.selected_count_label)
        selection_row.addStretch(1)
        self.select_visible_button = QPushButton("Alle sichtbaren auswählen")
        configure_button(
            self.select_visible_button,
            "secondary",
            "Alle sichtbaren Kinder auswählen",
        )
        self.select_visible_button.clicked.connect(self._select_all_visible)
        selection_row.addWidget(self.select_visible_button)
        self.clear_selection_button = QPushButton("Auswahl aufheben")
        configure_button(
            self.clear_selection_button,
            "secondary",
            "Auswahl aller Kinder aufheben",
        )
        self.clear_selection_button.clicked.connect(self._clear_selection)
        selection_row.addWidget(self.clear_selection_button)
        layout.addLayout(selection_row)

        actions = QHBoxLayout()
        self.bulk_course_combo = self._filter_combo(
            "Zielkurs für ausgewählte sichtbare Kinder",
            (
                ("Zielkurs wählen", None),
                *((course.course_name, course.course_id)
                  for course in self.plan.available_courses),
            ),
        )
        actions.addWidget(self.bulk_course_combo)
        self.bulk_course_button = QPushButton("Zielkurs setzen")
        configure_button(
            self.bulk_course_button,
            "primary",
            "Zielkurs für ausgewählte sichtbare Kinder setzen",
        )
        self.bulk_course_button.clicked.connect(self._bulk_set_course)
        actions.addWidget(self.bulk_course_button)

        self.bulk_group_combo = self._filter_combo(
            "Zielstammgruppe für ausgewählte sichtbare Kinder",
            (
                ("Zielstammgruppe wählen", None),
                *((group.group_name, group.group_id)
                  for group in self.plan.available_groups),
            ),
        )
        actions.addWidget(self.bulk_group_combo)
        self.bulk_group_button = QPushButton("Zielstammgruppe setzen")
        configure_button(
            self.bulk_group_button,
            "primary",
            "Zielstammgruppe für ausgewählte sichtbare Kinder setzen",
        )
        self.bulk_group_button.clicked.connect(self._bulk_set_group)
        actions.addWidget(self.bulk_group_button)

        self.bulk_exited_button = QPushButton("Als ausgeschieden markieren")
        configure_button(
            self.bulk_exited_button,
            "secondary",
            "Ausgewählte sichtbare Kinder als ausgeschieden markieren",
        )
        self.bulk_exited_button.clicked.connect(self._bulk_mark_exited)
        actions.addWidget(self.bulk_exited_button)
        self.bulk_unresolved_button = QPushButton("Bewusst ungelöst setzen")
        configure_button(
            self.bulk_unresolved_button,
            "secondary",
            "Ausgewählte sichtbare Kinder bewusst ungelöst setzen",
        )
        self.bulk_unresolved_button.clicked.connect(
            self._bulk_leave_unresolved
        )
        actions.addWidget(self.bulk_unresolved_button)
        layout.addLayout(actions)
        self._bulk_action_widgets = (
            self.bulk_course_combo,
            self.bulk_course_button,
            self.bulk_group_combo,
            self.bulk_group_button,
            self.bulk_exited_button,
            self.bulk_unresolved_button,
        )
        self._update_selection_status()
        return card

    @staticmethod
    def _filter_combo(
        accessible_name: str,
        options: tuple[tuple[str, object], ...],
    ) -> QComboBox:
        combo = QComboBox()
        combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        combo.setAccessibleName(accessible_name)
        for label, value in options:
            combo.addItem(label, value)
        return combo

    def _current_course_filter_options(
        self,
    ) -> tuple[tuple[str, str], ...]:
        options = {
            (item.current_course_name, item.current_course_id)
            for item in self.plan.items
            if item.current_course_id is not None
            and item.current_course_name is not None
        }
        return tuple(sorted(options, key=lambda option: (option[0], option[1])))

    def _current_group_filter_options(
        self,
    ) -> tuple[tuple[str, str], ...]:
        options = {
            (item.current_group_name, item.current_group_id)
            for item in self.plan.items
            if item.current_group_id is not None
            and item.current_group_name is not None
        }
        return tuple(sorted(options, key=lambda option: (option[0], option[1])))

    def _configure_table(self) -> None:
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        for column, header in enumerate(TABLE_HEADERS):
            header_item = self.table.horizontalHeaderItem(column)
            if header_item is not None:
                header_item.setData(
                    Qt.ItemDataRole.AccessibleTextRole,
                    header,
                )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionsClickable(False)
        self.table.horizontalHeader().setHighlightSections(False)
        for column in range(len(TABLE_HEADERS)):
            self.table.horizontalHeader().setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.Interactive,
            )
        widths = (145, 180, 180, 155, 145, 215, 245, 180, 390)
        for column, width in enumerate(widths):
            self.table.setColumnWidth(column, width)

    def _refresh_from_plan(
        self,
        *,
        focus_student_id: str | None = None,
        focus_kind: str = "course",
    ) -> None:
        self.view_model = SchoolYearTransitionPreviewViewModel.from_plan(
            self.plan
        )
        values = {
            "Aktuelles Schuljahr": self.view_model.current_school_year_label,
            "Geplantes neues Schuljahr": (
                self.view_model.planned_school_year_label
            ),
            "Zeitraum": self.view_model.period_label,
            "Kinder gesamt": str(self.view_model.student_count),
            "Gelöst": str(self.view_model.resolved_count),
            "Wechsel 1 → 2": str(self.view_model.advance_1_to_2_count),
            "Wechsel 2 → 3": str(self.view_model.advance_2_to_3_count),
            "Anderer Kurs": str(self.view_model.other_course_count),
            "Kurs 3 wiederholen": str(
                self.view_model.repeat_year_level_three_count
            ),
            "Ausgeschieden": str(self.view_model.exited_count),
            "Ungelöst": str(self.view_model.unresolved_count),
            "Individuell bearbeitet": str(self.view_model.edited_count),
        }
        for field_name, value in values.items():
            label = self.summary_labels[field_name]
            label.setText(value)
            label.setAccessibleName(f"{field_name}: {value}")
        self._update_status_message()
        self._populate_table(
            focus_student_id=focus_student_id,
            focus_kind=focus_kind,
        )
        self._update_selection_status()

    def _update_status_message(self) -> None:
        status_text = (
            f"{self.view_model.status_label}. "
            f"{self.view_model.status_description}"
        )
        if self.view_model.global_issues_label:
            status_text = f"{status_text} {self.view_model.global_issues_label}"
        self.status_message.set_message(
            status_text,
            tone=(
                "success"
                if self.view_model.status_label == "Plan vollständig"
                else "warning"
            ),
        )

    def _populate_table(
        self,
        *,
        focus_student_id: str | None,
        focus_kind: str,
    ) -> None:
        visible_rows = self.view_model.filtered_rows(
            unresolved_only=bool(self.unresolved_filter.currentData()),
            current_course_id=self.current_course_filter.currentData(),
            target_course_id=self.target_course_filter.currentData(),
            current_group_id=self.current_group_filter.currentData(),
            target_group_id=self.target_group_filter.currentData(),
        )
        self._visible_student_ids = tuple(
            row.student_id for row in visible_rows
        )
        self._populating_table = True
        self.table.clearContents()
        self.table.setRowCount(len(visible_rows))
        self._decision_controls = []
        focus_target: QComboBox | None = None
        for row_index, row in enumerate(visible_rows):
            course_combo, group_combo = self._populate_row(row_index, row)
            if row.student_id == focus_student_id:
                focus_target = (
                    group_combo if focus_kind == "group" else course_combo
                )
        self._populating_table = False
        if visible_rows:
            self.table.setCurrentCell(0, 0)
        self._configure_tab_order()
        if focus_target is not None:
            focus_target.setFocus(Qt.FocusReason.OtherFocusReason)

    def _populate_row(
        self,
        row_index: int,
        row: SchoolYearTransitionPreviewRowViewModel,
    ) -> tuple[QComboBox, QComboBox | None]:
        selection_item = QTableWidgetItem()
        selection_item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
        )
        is_selected = row.student_id in self._selected_student_ids
        selection_item.setCheckState(
            Qt.CheckState.Checked
            if is_selected
            else Qt.CheckState.Unchecked
        )
        selection_item.setText(
            "Ausgewählt" if is_selected else "Nicht ausgewählt"
        )
        selection_item.setData(Qt.ItemDataRole.UserRole, row.student_id)
        selection_item.setData(
            Qt.ItemDataRole.AccessibleTextRole,
            (
                f"{row.child_label}: "
                f"{'ausgewählt' if is_selected else 'nicht ausgewählt'}"
            ),
        )
        selection_item.setData(
            Qt.ItemDataRole.AccessibleDescriptionRole,
            row.accessible_description,
        )
        self.table.setItem(row_index, 0, selection_item)
        values = (
            row.child_label,
            row.current_group_label,
            row.current_course_label,
            row.current_year_level_label,
            row.target_status_label,
            row.target_group_label,
            row.target_course_label,
            row.warnings_label,
        )
        for column, value in enumerate(values, start=1):
            item = QTableWidgetItem(value)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, value)
            item.setData(
                Qt.ItemDataRole.AccessibleDescriptionRole,
                row.accessible_description,
            )
            if not row.resolved:
                item.setData(Qt.ItemDataRole.UserRole, "unresolved")
            self.table.setItem(row_index, column, item)

        course_combo = self._decision_combo(
            current_label=row.target_status_label,
            choices=row.course_choices,
            accessible_name=(
                f"Zielentscheidung für {row.child_label}"
            ),
            accessible_description=row.accessible_description,
        )
        course_combo.activated.connect(
            partial(
                self._course_choice_activated,
                row.student_id,
                course_combo,
            )
        )
        self.table.setCellWidget(row_index, 5, course_combo)
        self._decision_controls.append(course_combo)

        group_combo: QComboBox | None = None
        if not row.exited:
            group_combo = self._decision_combo(
                current_label=row.target_group_label,
                choices=row.group_choices,
                accessible_name=(
                    f"Zielstammgruppe für {row.child_label}"
                ),
                accessible_description=row.accessible_description,
            )
            group_combo.activated.connect(
                partial(
                    self._group_choice_activated,
                    row.student_id,
                    group_combo,
                )
            )
            self.table.setCellWidget(row_index, 6, group_combo)
            self._decision_controls.append(group_combo)
        return course_combo, group_combo

    @staticmethod
    def _decision_combo(
        *,
        current_label: str,
        choices: tuple[SchoolYearTransitionDecisionOptionViewModel, ...],
        accessible_name: str,
        accessible_description: str,
    ) -> QComboBox:
        combo = QComboBox()
        combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        combo.setAccessibleName(accessible_name)
        combo.setAccessibleDescription(accessible_description)
        combo.addItem(current_label, None)
        for choice in choices:
            combo.addItem(
                choice.label,
                (choice.action, choice.option_id),
            )
        combo.setCurrentIndex(0)
        return combo

    def _filter_changed(self, _index: int) -> None:
        self._populate_table(focus_student_id=None, focus_kind="course")
        self._update_selection_status()

    def _reset_filters(self) -> None:
        filters = (
            self.unresolved_filter,
            self.current_course_filter,
            self.target_course_filter,
            self.current_group_filter,
            self.target_group_filter,
        )
        for combo in filters:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self._populate_table(focus_student_id=None, focus_kind="course")
        self._update_selection_status()

    def _selection_item_changed(self, item: QTableWidgetItem) -> None:
        if self._populating_table or item.column() != 0:
            return
        student_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(student_id, str):
            return
        is_selected = item.checkState() == Qt.CheckState.Checked
        if is_selected:
            self._selected_student_ids.add(student_id)
        else:
            self._selected_student_ids.discard(student_id)
        item.setText("Ausgewählt" if is_selected else "Nicht ausgewählt")
        item.setData(
            Qt.ItemDataRole.AccessibleTextRole,
            (
                f"{self._student_label(student_id)}: "
                f"{'ausgewählt' if is_selected else 'nicht ausgewählt'}"
            ),
        )
        self._update_selection_status()

    def _student_label(self, student_id: str) -> str:
        return next(
            row.child_label
            for row in self.view_model.rows
            if row.student_id == student_id
        )

    def _select_all_visible(self) -> None:
        self._selected_student_ids.update(self._visible_student_ids)
        self._populate_table(focus_student_id=None, focus_kind="course")
        self._update_selection_status()

    def _clear_selection(self) -> None:
        self._selected_student_ids.clear()
        self._populate_table(focus_student_id=None, focus_kind="course")
        self._update_selection_status()

    def _visible_selected_student_ids(self) -> tuple[str, ...]:
        return tuple(
            student_id
            for student_id in self._visible_student_ids
            if student_id in self._selected_student_ids
        )

    def _update_selection_status(self) -> None:
        total_count = len(self._selected_student_ids)
        visible_count = len(self._visible_selected_student_ids())
        text = (
            "1 Kind ausgewählt"
            if total_count == 1
            else f"{total_count} Kinder ausgewählt"
        )
        if visible_count != total_count:
            text = f"{text}, davon {visible_count} im aktuellen Filter sichtbar"
        self.selected_count_label.setText(text)
        self.selected_count_label.setAccessibleName(text)
        has_visible_selection = visible_count > 0
        for widget in self._bulk_action_widgets:
            widget.setEnabled(has_visible_selection)
        self.clear_selection_button.setEnabled(total_count > 0)
        self.select_visible_button.setEnabled(
            bool(self._visible_student_ids)
            and visible_count < len(self._visible_student_ids)
        )

    def _bulk_set_course(self) -> None:
        course_id = self.bulk_course_combo.currentData()
        if not isinstance(course_id, str):
            self._show_choice_error()
            return
        self._apply_bulk_change(
            "den Zielkurs setzen",
            lambda student_ids: self.plan.set_target_course_for_students(
                student_ids,
                course_id,
            ),
            focus_kind="course",
        )

    def _bulk_set_group(self) -> None:
        group_id = self.bulk_group_combo.currentData()
        if not isinstance(group_id, str):
            self._show_choice_error()
            return
        self._apply_bulk_change(
            "die Zielstammgruppe setzen",
            lambda student_ids: self.plan.set_target_group_for_students(
                student_ids,
                group_id,
            ),
            focus_kind="group",
        )

    def _bulk_mark_exited(self) -> None:
        self._apply_bulk_change(
            "als ausgeschieden markieren",
            self.plan.mark_students_exited,
            focus_kind="course",
        )

    def _bulk_leave_unresolved(self) -> None:
        self._apply_bulk_change(
            "bewusst ungelöst setzen",
            self.plan.leave_students_unresolved,
            focus_kind="course",
        )

    def _apply_bulk_change(
        self,
        description: str,
        change: Callable[[tuple[str, ...]], SchoolYearTransitionPlan],
        *,
        focus_kind: str,
    ) -> None:
        student_ids = self._visible_selected_student_ids()
        if not student_ids:
            return
        if len(student_ids) > 1 and not self._confirm_bulk_change(
            len(student_ids),
            description,
        ):
            return
        try:
            self.plan = change(student_ids)
        except (SchoolYearTransitionPlanError, ValueError):
            self._show_choice_error()
            return
        self._refresh_from_plan(
            focus_student_id=student_ids[0],
            focus_kind=focus_kind,
        )

    def _confirm_bulk_change(
        self,
        count: int,
        description: str,
    ) -> bool:
        result = QMessageBox.question(
            self,
            "Sammeländerung bestätigen",
            (
                f"Möchten Sie {count} ausgewählte, im aktuellen Filter "
                f"sichtbare Kinder {description}? "
                "Die Änderung bleibt flüchtig."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def _course_choice_activated(
        self,
        student_id: str,
        combo: QComboBox,
        index: int,
    ) -> None:
        selection = combo.itemData(index)
        if selection is None:
            return
        action, option_id = selection
        try:
            self.plan = apply_course_choice(
                self.plan,
                student_id=student_id,
                action=action,
                option_id=option_id,
            )
        except (SchoolYearTransitionPlanError, ValueError):
            self._show_choice_error()
            return
        self._refresh_from_plan(
            focus_student_id=student_id,
            focus_kind="course",
        )

    def _group_choice_activated(
        self,
        student_id: str,
        combo: QComboBox,
        index: int,
    ) -> None:
        selection = combo.itemData(index)
        if selection is None:
            return
        action, option_id = selection
        try:
            self.plan = apply_group_choice(
                self.plan,
                student_id=student_id,
                action=action,
                option_id=option_id,
            )
        except (SchoolYearTransitionPlanError, ValueError):
            self._show_choice_error()
            return
        self._refresh_from_plan(
            focus_student_id=student_id,
            focus_kind="group",
        )

    def _show_choice_error(self) -> None:
        self.status_message.set_message(
            (
                "Die Auswahl konnte nicht übernommen werden. "
                "Der flüchtige Plan blieb unverändert."
            ),
            tone="warning",
        )

    def _configure_tab_order(self) -> None:
        controls: list[QWidget] = [
            self.unresolved_filter,
            self.current_course_filter,
            self.target_course_filter,
            self.current_group_filter,
            self.target_group_filter,
            self.reset_filters_button,
            self.select_visible_button,
            self.clear_selection_button,
            self.bulk_course_combo,
            self.bulk_course_button,
            self.bulk_group_combo,
            self.bulk_group_button,
            self.bulk_exited_button,
            self.bulk_unresolved_button,
            self.table,
            *self._decision_controls,
        ]
        if self.close_button is not None:
            controls.append(self.close_button)
        for current, following in zip(controls, controls[1:], strict=False):
            QWidget.setTabOrder(current, following)
