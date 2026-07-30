"""Read-only Qt dialog for the SJ-3B.1 school-year transition preview."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.core.school_year_transition import SchoolYearTransitionPreview
from src.desktop_app.components import AppCard, DialogHeader, InlineMessage
from src.desktop_app.components import configure_button
from src.desktop_app.motion import MotionDialog
from src.desktop_app.theme import set_label_style
from src.desktop_app.view_models.school_year_transition_preview_view_model import (
    SchoolYearTransitionPreviewRowViewModel,
    SchoolYearTransitionPreviewViewModel,
)


TABLE_HEADERS = (
    "Kind",
    "Bisherige Stammgruppe",
    "Bisheriger Kurs",
    "Bisherige Kursstufe",
    "Vorgeschlagene Stammgruppe",
    "Vorgeschlagener Kurs",
    "Zielstatus",
    "Warnungen",
)


class SchoolYearTransitionPreviewDialog(MotionDialog):
    """Display one existing preview without editing or execution capability."""

    def __init__(self, preview: SchoolYearTransitionPreview) -> None:
        super().__init__()
        self.view_model = SchoolYearTransitionPreviewViewModel.from_preview(preview)
        self.setWindowTitle("Schuljahreswechsel-Vorschau")
        self.setAccessibleName("Schuljahreswechsel-Vorschau")
        self.setModal(True)
        self.setMinimumSize(520, 360)
        self.resize(1180, 700)
        self.table = QTableWidget(0, len(TABLE_HEADERS))
        self.table.setObjectName("SchoolYearTransitionPreviewTable")
        self.table.setAccessibleName("Vorschau je Kind")
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
                "Rein lesende Vorschau. Es werden keine Änderungen ausgeführt.",
                icon_name="info",
            )
        )
        layout.addWidget(self._summary_card())

        self.status_message = InlineMessage()
        self.status_message.setObjectName("SchoolYearTransitionPreviewStatus")
        self.status_message.setAccessibleName("Status der Vorschau")
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
                if self.view_model.status_label == "Vorschau vollständig"
                else "warning"
            ),
        )
        layout.addWidget(self.status_message)

        self._configure_table()
        self._populate_table()
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.setObjectName("DialogActionBar")
        buttons.setAccessibleName("Dialogaktionen")
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.setText("Schließen")
            close_button.setDefault(True)
            close_button.setAutoDefault(True)
            close_button.setShortcut("Esc")
            configure_button(close_button, "secondary", "Vorschau schließen")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _summary_card(self) -> AppCard:
        card = AppCard("soft")
        card.setObjectName("SchoolYearTransitionPreviewSummary")
        card.setAccessibleName("Zusammenfassung der Vorschau")
        form = QFormLayout(card)
        form.setContentsMargins(18, 14, 18, 14)
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(6)
        fields = (
            ("Aktuelles Schuljahr", self.view_model.current_school_year_label),
            ("Geplantes neues Schuljahr", self.view_model.planned_school_year_label),
            ("Zeitraum", self.view_model.period_label),
            ("Kinder gesamt", str(self.view_model.student_count)),
            ("Wechsel 1 → 2", str(self.view_model.advance_1_to_2_count)),
            ("Wechsel 2 → 3", str(self.view_model.advance_2_to_3_count)),
            ("Ungelöst", str(self.view_model.unresolved_count)),
        )
        self.summary_labels: dict[str, QLabel] = {}
        for field_name, value in fields:
            value_label = QLabel(value)
            value_label.setAccessibleName(f"{field_name}: {value}")
            set_label_style(value_label, "body")
            self.summary_labels[field_name] = value_label
            form.addRow(field_name, value_label)
        return card

    def _configure_table(self) -> None:
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        for column, header in enumerate(TABLE_HEADERS):
            header_item = self.table.horizontalHeaderItem(column)
            if header_item is not None:
                header_item.setData(Qt.ItemDataRole.AccessibleTextRole, header)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
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
        widths = (150, 175, 150, 145, 195, 175, 150, 330)
        for column, width in enumerate(widths):
            self.table.setColumnWidth(column, width)

    def _populate_table(self) -> None:
        self.table.setRowCount(len(self.view_model.rows))
        for row_index, row in enumerate(self.view_model.rows):
            self._populate_row(row_index, row)
        if self.view_model.rows:
            self.table.setCurrentCell(0, 0)

    def _populate_row(
        self,
        row_index: int,
        row: SchoolYearTransitionPreviewRowViewModel,
    ) -> None:
        values = (
            row.child_label,
            row.current_group_label,
            row.current_course_label,
            row.current_year_level_label,
            row.proposed_group_label,
            row.proposed_course_label,
            row.target_status_label,
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
