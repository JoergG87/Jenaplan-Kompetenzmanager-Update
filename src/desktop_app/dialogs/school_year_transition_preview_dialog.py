"""Editable Qt dialog for the transient SJ-3B.2b transition plan."""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QLabel,
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

    def __init__(self, plan: SchoolYearTransitionPlan) -> None:
        super().__init__()
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

        self.status_message = InlineMessage()
        self.status_message.setObjectName("SchoolYearTransitionPreviewStatus")
        self.status_message.setAccessibleName("Status des flüchtigen Plans")
        layout.addWidget(self.status_message)

        self._configure_table()
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
        widths = (180, 180, 155, 145, 215, 245, 180, 390)
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
        self.table.clearContents()
        self.table.setRowCount(len(self.view_model.rows))
        self._decision_controls = []
        focus_target: QComboBox | None = None
        for row_index, row in enumerate(self.view_model.rows):
            course_combo, group_combo = self._populate_row(row_index, row)
            if row.student_id == focus_student_id:
                focus_target = (
                    group_combo if focus_kind == "group" else course_combo
                )
        if self.view_model.rows:
            self.table.setCurrentCell(0, 0)
        self._configure_tab_order()
        if focus_target is not None:
            focus_target.setFocus(Qt.FocusReason.OtherFocusReason)

    def _populate_row(
        self,
        row_index: int,
        row: SchoolYearTransitionPreviewRowViewModel,
    ) -> tuple[QComboBox, QComboBox | None]:
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
        for column, value in enumerate(values):
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
        self.table.setCellWidget(row_index, 4, course_combo)
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
            self.table.setCellWidget(row_index, 5, group_combo)
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
        controls: list[QWidget] = [self.table, *self._decision_controls]
        if self.close_button is not None:
            controls.append(self.close_button)
        for current, following in zip(controls, controls[1:], strict=False):
            QWidget.setTabOrder(current, following)
