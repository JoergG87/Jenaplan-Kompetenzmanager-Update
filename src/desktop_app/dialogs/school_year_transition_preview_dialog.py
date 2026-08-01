"""Editable transition plan with the guarded SJ-3C.6 activation stage."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from src.application.school_year_transition_execution import (
    SchoolYearTransitionExecutionResult,
)
from src.desktop_app.components import AppCard, DialogHeader, InlineMessage
from src.desktop_app.components import configure_button
from src.desktop_app.motion import MotionDialog
from src.desktop_app.school_year_transition_activation import (
    SchoolYearTransitionActivationController,
    SchoolYearTransitionActivationErrorInfo,
)
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
    """Edit one transient plan and project its composed activation workflow."""

    def __init__(
        self,
        plan: SchoolYearTransitionPlan,
        parent: QWidget | None = None,
        *,
        activation_controller: SchoolYearTransitionActivationController
        | None = None,
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
        self.activation_controller = activation_controller
        self._activation_running = False
        self._critical_execution_started = False
        self._terminal_state = False
        self._recovery_required = False
        self._controlled_close_allowed = False
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
                    "Prüfen Sie alle Zuordnungen. Erst die finale "
                    "Bestätigung aktiviert das neue Schuljahr."
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
        layout.addWidget(self._activation_card())

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
            self.close_button.setDefault(False)
            self.close_button.setAutoDefault(False)
            configure_button(
                self.close_button,
                "secondary",
                "Vorschau schließen",
            )
        self.buttons.rejected.connect(self._request_close)
        layout.addWidget(self.buttons)
        if self.activation_controller is not None:
            self.activation_controller.progress.connect(
                self._show_execution_progress
            )
            self.activation_controller.succeeded.connect(
                self._show_execution_success
            )
            self.activation_controller.failed.connect(
                self._show_execution_failure
            )
            self.activation_controller.finished.connect(
                self._activation_finished
            )
        self._refresh_from_plan()

    def _activation_card(self) -> AppCard:
        card = AppCard("soft")
        card.setObjectName("SchoolYearTransitionActivation")
        card.setAccessibleName("Verbindliche Aktivierung des Schuljahres")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        title = QLabel("Verbindliche Aktivierung")
        set_label_style(title, "section_title")
        layout.addWidget(title)
        self.confirmation_checkbox = QCheckBox(
            "Ich habe alle Zuordnungen geprüft"
        )
        self.confirmation_checkbox.setAccessibleName(
            "Bestätigung: Ich habe alle Zuordnungen geprüft"
        )
        self.confirmation_checkbox.toggled.connect(
            self._update_activation_availability
        )
        layout.addWidget(self.confirmation_checkbox)

        password_row = QFormLayout()
        self.password_field = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_field.setAccessibleName(
            "App-Passwort zur Aktivierung erneut eingeben"
        )
        self.password_field.setPlaceholderText("App-Passwort")
        self.password_field.textChanged.connect(
            self._update_activation_availability
        )
        password_row.addRow("App-Passwort erneut eingeben", self.password_field)
        layout.addLayout(password_row)

        self.activate_button = QPushButton()
        self.activate_button.setObjectName("SchoolYearTransitionActivate")
        self.activate_button.setDefault(False)
        self.activate_button.setAutoDefault(False)
        configure_button(
            self.activate_button,
            "primary",
            "Neues Schuljahr verbindlich aktivieren",
        )
        self.activate_button.clicked.connect(self._start_activation)
        layout.addWidget(self.activate_button)

        self.execution_status = InlineMessage()
        self.execution_status.setObjectName(
            "SchoolYearTransitionExecutionStatus"
        )
        self.execution_status.setAccessibleName(
            "Status der verbindlichen Aktivierung"
        )
        layout.addWidget(self.execution_status)

        self.progress_labels: dict[str, QLabel] = {}
        for phase, text in (
            ("writers_draining", "Schreibvorgänge werden beendet"),
            ("backup_creating", "Sicherheitsbackup wird erstellt"),
            ("assignments_checking", "Zuordnungen werden geprüft"),
            ("school_year_activating", "Schuljahr wird aktiviert"),
            ("completion_checking", "Abschluss wird geprüft"),
        ):
            label = QLabel(text)
            label.setAccessibleName(f"Ausstehend: {text}")
            self.progress_labels[phase] = label
            layout.addWidget(label)
        return card

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
            "Stammgruppenänderungen",
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
            "Stammgruppenänderungen": str(
                self.view_model.group_change_count
            ),
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
        self.activate_button.setText(
            "Schuljahr "
            f"{self.view_model.planned_school_year_label} "
            "verbindlich aktivieren"
        )
        self.activate_button.setAccessibleName(self.activate_button.text())
        self._update_activation_availability()

    def _update_activation_availability(self, *_args: object) -> None:
        validation = self.plan.validate()
        executable = (
            self.activation_controller is not None
            and validation.complete
            and validation.counts.unresolved_count == 0
            and all(item.resolved for item in self.plan.items)
            and self.confirmation_checkbox.isChecked()
            and bool(self.password_field.text())
            and not self._activation_running
            and not self._terminal_state
        )
        self.activate_button.setEnabled(executable)

    def _invalidate_confirmation(self) -> None:
        if hasattr(self, "confirmation_checkbox"):
            self.confirmation_checkbox.setChecked(False)
            self.password_field.clear()

    def _start_activation(self) -> None:
        if self._activation_running or self._terminal_state:
            return
        validation = self.plan.validate()
        if (
            self.activation_controller is None
            or not validation.complete
            or validation.counts.unresolved_count != 0
            or any(not item.resolved for item in self.plan.items)
            or not self.confirmation_checkbox.isChecked()
            or not self.password_field.text()
        ):
            self._update_activation_availability()
            return
        self._activation_running = True
        self._set_editing_enabled(False)
        self.execution_status.set_message(
            "Das App-Passwort wird geprüft.",
            tone="info",
        )
        password = self.password_field.text()
        self.password_field.clear()
        if not self.activation_controller.start(
            plan=self.plan,
            password=password,
        ):
            self._activation_running = False
            self._set_editing_enabled(True)
            self._update_activation_availability()

    def _show_execution_progress(self, phase: str) -> None:
        label = self.progress_labels.get(phase)
        if label is None:
            return
        self._critical_execution_started = True
        text = label.text()
        label.setText(f"Aktuell: {text}")
        label.setAccessibleName(f"Aktuell: {text}")
        self.execution_status.set_message(text, tone="info")

    def _show_execution_success(self, result: object) -> None:
        if not isinstance(result, SchoolYearTransitionExecutionResult):
            self._show_execution_failure(
                SchoolYearTransitionActivationErrorInfo(
                    "transition_execution_failed"
                )
            )
            return
        self._terminal_state = True
        self._controlled_close_allowed = True
        counts = result.counts
        self.execution_status.set_message(
            (
                f"Schuljahr {self.view_model.planned_school_year_label} "
                "wurde verbindlich aktiviert. Das Sicherheitsbackup wurde "
                "erfolgreich bestätigt und der Schuljahreswechsel vollständig "
                "abgeschlossen. "
                f"{counts.advance_1_to_2_count} Wechsel 1 → 2, "
                f"{counts.advance_2_to_3_count} Wechsel 2 → 3, "
                f"{counts.repeat_year_level_three_count} Wiederholer, "
                f"{counts.exited_count} ausgeschieden und "
                f"{counts.group_change_count} Stammgruppenänderungen; "
                "0 ungelöst."
            ),
            tone="success",
        )
        self.close_button.setText("Fertig")
        self.close_button.setAccessibleName(
            "Erfolgreiche Aktivierung abschließen"
        )

    def _show_execution_failure(self, error: object) -> None:
        info = (
            error
            if isinstance(error, SchoolYearTransitionActivationErrorInfo)
            else SchoolYearTransitionActivationErrorInfo(
                "transition_execution_failed"
            )
        )
        code = info.code
        if code == "password_invalid":
            text = (
                "Das App-Passwort ist nicht richtig. Es wurden keine "
                "Änderungen begonnen."
            )
            terminal = False
        elif code == "password_throttled":
            wait = max(1, info.retry_after_seconds)
            text = (
                "Die Passwortprüfung ist vorübergehend gesperrt. "
                f"Bitte in {wait} Sekunden erneut versuchen."
            )
            terminal = False
        elif code == "password_check_unavailable":
            text = "Das App-Passwort kann derzeit nicht geprüft werden."
            terminal = True
        elif _requires_new_preview(code):
            text = (
                "Die Zuordnungen haben sich seit der Vorschau geändert. "
                "Bitte schließen Sie den Dialog und erstellen Sie eine neue "
                "Vorschau."
            )
            terminal = True
        elif code == "transition_recovery_required":
            text = (
                "Der Vorgang konnte nicht sicher abgeschlossen werden. "
                "Die App bleibt für weitere Schreibvorgänge gesperrt, bis die "
                "Wiederherstellung geprüft wurde."
            )
            terminal = True
            self._recovery_required = True
        elif _is_backup_failure(code):
            text = (
                "Das Sicherheitsbackup konnte nicht vollständig erstellt und "
                "bestätigt werden. Die Daten wurden nicht geändert."
            )
            terminal = True
        else:
            text = (
                "Das Schuljahr konnte nicht aktiviert werden. Begonnene "
                "Änderungen wurden sicher zurückgenommen."
            )
            terminal = True
        self._terminal_state = terminal
        self._controlled_close_allowed = terminal
        self.execution_status.set_message(text, tone="error")
        if not terminal:
            self.confirmation_checkbox.setChecked(False)
            self.password_field.clear()

    def _activation_finished(self) -> None:
        self._activation_running = False
        if self._terminal_state:
            self.close_button.setEnabled(not self._recovery_required)
            if self._recovery_required:
                self.close_button.setText("App bleibt gesperrt")
                self.close_button.setAccessibleName(
                    "Wiederherstellung muss zuerst geprüft werden"
                )
        else:
            self._set_editing_enabled(True)
            self._update_selection_status()
            self.password_field.setFocus(Qt.FocusReason.OtherFocusReason)
        self._update_activation_availability()

    def _set_editing_enabled(self, enabled: bool) -> None:
        for widget in (
            self.table,
            self.unresolved_filter,
            self.current_course_filter,
            self.target_course_filter,
            self.current_group_filter,
            self.target_group_filter,
            self.reset_filters_button,
            self.select_visible_button,
            self.clear_selection_button,
            *self._bulk_action_widgets,
            self.confirmation_checkbox,
            self.password_field,
        ):
            widget.setEnabled(enabled)
        self.close_button.setEnabled(enabled and not self._activation_running)

    def _request_close(self) -> None:
        if self._activation_running:
            return
        if self._critical_execution_started and not self._controlled_close_allowed:
            return
        super().reject()

    def reject(self) -> None:
        self._request_close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._activation_running:
            event.ignore()
            return
        if self._critical_execution_started and not self._controlled_close_allowed:
            event.ignore()
            return
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            if not self._critical_execution_started and not self._activation_running:
                self._request_close()
            event.accept()
            return
        super().keyPressEvent(event)

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
        self._invalidate_confirmation()
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
        self._invalidate_confirmation()
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
        self._invalidate_confirmation()
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
            self.confirmation_checkbox,
            self.password_field,
            self.activate_button,
        ]
        if self.close_button is not None:
            controls.append(self.close_button)
        for current, following in zip(controls, controls[1:], strict=False):
            QWidget.setTabOrder(current, following)


def _requires_new_preview(code: str) -> bool:
    return code in {
        "transition_sources_changed",
        "transition_current_school_year_changed",
        "transition_target_school_year_changed",
        "transition_plan_sha256_mismatch",
        "transition_step_up_plan_mismatch",
        "transition_backup_source_state_mismatch",
    }


def _is_backup_failure(code: str) -> bool:
    return code.startswith("transition_backup_") or code in {
        "transition_backup_failed",
        "transition_backup_evidence_missing",
    }
