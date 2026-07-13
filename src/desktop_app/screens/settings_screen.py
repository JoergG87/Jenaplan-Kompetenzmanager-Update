"""Settings screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGraphicsOpacityEffect
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.theme import PRIMARY_BUTTON_STYLESHEET, create_card, set_label_style
from src.desktop_app.view_models.settings_view_model import (
    DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE,
    DocumentationSubjectOptionViewModel,
    SettingsViewModel,
)
from src.desktop_app.view_models.timetable_view_model import (
    TimetableEntryViewModel,
    TimetableWeekViewModel,
)


DOCUMENTATION_SUBJECTS_HELP_TEXT = (
    "Diese Auswahl steuert, welche Fächer im Dokumentationsstand "
    "berücksichtigt werden. Beobachtungen bleiben immer erhalten."
)


class SettingsScreen(QWidget):
    """Show app settings and emit save requests without persistence logic."""

    documentation_subjects_save_requested = Signal(tuple)
    timetable_add_requested = Signal(int)
    timetable_edit_requested = Signal(str)
    timetable_delete_requested = Signal(str)
    timetable_active_requested = Signal(str, bool)

    def __init__(self) -> None:
        super().__init__()
        self.documentation_subject_checkboxes: dict[str, QCheckBox] = {}
        self.documentation_subjects_layout = QVBoxLayout()
        self.status_label = QLabel("")
        self.timetable_week: TimetableWeekViewModel | None = None
        self.selected_timetable_weekday = 1
        self.timetable_tabs = QTabBar()
        self.timetable_tabs.setExpanding(True)
        self.timetable_tabs.setUsesScrollButtons(False)
        self.timetable_tabs.currentChanged.connect(self._select_timetable_day)
        self.timetable_day_layout = QVBoxLayout()
        self.timetable_empty_label = QLabel("")
        self.timetable_add_button = QPushButton("Stunde hinzufügen")
        self.timetable_add_button.setStyleSheet(PRIMARY_BUTTON_STYLESHEET)
        self.timetable_add_button.clicked.connect(self._emit_timetable_add)
        self._build()

    def _build(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName("SettingsScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        title = QLabel("Einstellungen")
        set_label_style(title, "screen_title")
        subtitle = QLabel("Grundlagen für Dokumentation und Auswertung")
        set_label_style(subtitle, "muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._timetable_card())
        layout.addWidget(self._documentation_subjects_card())
        layout.addStretch(1)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def set_settings(self, view_model: SettingsViewModel) -> None:
        """Replace settings content with the current view model."""
        self.set_documentation_subjects(view_model.documentation_subjects)

    def set_timetable(self, week: TimetableWeekViewModel) -> None:
        """Replace the timetable projection while keeping the selected day."""
        self.timetable_week = week
        self.timetable_tabs.blockSignals(True)
        while self.timetable_tabs.count():
            self.timetable_tabs.removeTab(0)
        for day in week.days:
            suffix = f" ({len(day.entries)})" if day.entries else ""
            self.timetable_tabs.addTab(f"{day.label}{suffix}")
            self.timetable_tabs.setTabData(self.timetable_tabs.count() - 1, day.weekday)
        selected_index = next(
            (
                index
                for index in range(self.timetable_tabs.count())
                if self.timetable_tabs.tabData(index) == self.selected_timetable_weekday
            ),
            0,
        )
        self.timetable_tabs.setCurrentIndex(selected_index)
        self.timetable_tabs.blockSignals(False)
        self._render_selected_timetable_day()

    def set_documentation_subjects(
        self,
        subjects: tuple[DocumentationSubjectOptionViewModel, ...],
    ) -> None:
        """Replace the documentation subject checkbox list."""
        self._clear_documentation_subjects()
        self.documentation_subject_checkboxes = {}
        for subject in subjects:
            checkbox = QCheckBox(subject.label)
            checkbox.setObjectName(
                f"DocumentationSubjectCheckbox_{subject.subject_id}"
            )
            checkbox.setChecked(subject.selected)
            self.documentation_subject_checkboxes[subject.subject_id] = checkbox
            self.documentation_subjects_layout.addWidget(checkbox)
        self.documentation_subjects_layout.addStretch(1)

    def show_documentation_subjects_saved(self) -> None:
        """Show the calm save confirmation for documentation subjects."""
        self.status_label.setText(DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE)

    def _documentation_subjects_card(self) -> QFrame:
        card = create_card()
        card.setObjectName("DocumentationSubjectSettingsSection")
        layout = QVBoxLayout(card)
        header = QHBoxLayout()
        title = QLabel("Dokumentationsrelevante Fächer")
        set_label_style(title, "section_title")
        header.addWidget(title)
        header.addStretch(1)
        layout.addLayout(header)

        help_label = QLabel(DOCUMENTATION_SUBJECTS_HELP_TEXT)
        help_label.setWordWrap(True)
        set_label_style(help_label, "muted")
        layout.addWidget(help_label)
        layout.addLayout(self.documentation_subjects_layout)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        save_button = QPushButton("Speichern")
        save_button.setObjectName("DocumentationSubjectSaveButton")
        save_button.clicked.connect(self._emit_documentation_subjects_save)
        action_row.addWidget(save_button)
        layout.addLayout(action_row)

        set_label_style(self.status_label, "muted")
        self.status_label.setObjectName("SettingsStatusLabel")
        layout.addWidget(self.status_label)
        return card

    def _timetable_card(self) -> QFrame:
        card = create_card()
        card.setObjectName("TimetableSettingsSection")
        layout = QVBoxLayout(card)
        title = QLabel("Stundenplan")
        set_label_style(title, "section_title")
        layout.addWidget(title)
        help_label = QLabel(
            "Wochenplan für Montag bis Freitag. Überschneidungen werden beim Speichern geprüft."
        )
        help_label.setWordWrap(True)
        set_label_style(help_label, "muted")
        layout.addWidget(help_label)
        header = QHBoxLayout()
        header.addWidget(self.timetable_tabs, 1)
        header.addWidget(self.timetable_add_button)
        layout.addLayout(header)
        set_label_style(self.timetable_empty_label, "muted")
        self.timetable_empty_label.setObjectName("TimetableEmptyState")
        layout.addWidget(self.timetable_empty_label)
        layout.addLayout(self.timetable_day_layout)
        return card

    def _timetable_entry_card(self, entry: TimetableEntryViewModel) -> QFrame:
        card = create_card()
        card.setObjectName(f"TimetableEntry_{entry.timetable_entry_id}")
        layout = QHBoxLayout(card)
        time = QLabel(entry.time_label)
        time.setMinimumWidth(105)
        set_label_style(time, "card_title")
        layout.addWidget(time, 0)
        details = QVBoxLayout()
        subject = QLabel(entry.subject_label)
        set_label_style(subject, "card_title")
        details.addWidget(subject)
        meta_parts = [entry.target_type_label, entry.target_label]
        if entry.room:
            meta_parts.append(entry.room)
        target = QLabel(" · ".join(meta_parts))
        target.setWordWrap(True)
        set_label_style(target, "muted")
        details.addWidget(target)
        layout.addLayout(details, 1)
        active = QCheckBox("Aktiv")
        active.setChecked(entry.active)
        active.setObjectName(f"TimetableActive_{entry.timetable_entry_id}")
        active.toggled.connect(
            lambda checked, entry_id=entry.timetable_entry_id: self.timetable_active_requested.emit(
                entry_id, checked
            )
        )
        layout.addWidget(active, 0)
        edit_button = QPushButton("Bearbeiten")
        edit_button.clicked.connect(
            lambda checked=False, entry_id=entry.timetable_entry_id: self.timetable_edit_requested.emit(
                entry_id
            )
        )
        delete_button = QPushButton("Löschen")
        delete_button.clicked.connect(
            lambda checked=False, entry_id=entry.timetable_entry_id: self.timetable_delete_requested.emit(
                entry_id
            )
        )
        layout.addWidget(edit_button, 0)
        layout.addWidget(delete_button, 0)
        if not entry.active:
            opacity = QGraphicsOpacityEffect(card)
            opacity.setOpacity(0.58)
            card.setGraphicsEffect(opacity)
        return card

    def _select_timetable_day(self, index: int) -> None:
        if index < 0:
            return
        self.selected_timetable_weekday = int(self.timetable_tabs.tabData(index))
        self._render_selected_timetable_day()

    def _render_selected_timetable_day(self) -> None:
        self._clear_layout(self.timetable_day_layout)
        if self.timetable_week is None:
            return
        day = next(
            day
            for day in self.timetable_week.days
            if day.weekday == self.selected_timetable_weekday
        )
        self.timetable_empty_label.setText(
            f"Für {day.label} sind noch keine Stunden eingetragen."
        )
        self.timetable_empty_label.setVisible(not day.entries)
        self.timetable_add_button.setObjectName(f"TimetableAdd_{day.weekday}")
        day_container = QFrame()
        day_container.setObjectName(f"TimetableDay_{day.weekday}")
        day_layout = QVBoxLayout(day_container)
        day_layout.setContentsMargins(0, 0, 0, 0)
        for entry in day.entries:
            day_layout.addWidget(self._timetable_entry_card(entry))
        self.timetable_day_layout.addWidget(day_container)

    def _emit_timetable_add(self) -> None:
        self.timetable_add_requested.emit(self.selected_timetable_weekday)

    def _emit_documentation_subjects_save(self) -> None:
        selected_subject_ids = tuple(
            subject_id
            for subject_id, checkbox in self.documentation_subject_checkboxes.items()
            if checkbox.isChecked()
        )
        self.documentation_subjects_save_requested.emit(selected_subject_ids)

    def _clear_documentation_subjects(self) -> None:
        while self.documentation_subjects_layout.count():
            item = self.documentation_subjects_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
