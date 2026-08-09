"""Settings overview and its deliberately separated local pages."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QKeySequence, QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QComboBox, QDateEdit, QFormLayout, QLineEdit, QProgressBar, QStackedWidget,
    QTabBar, QVBoxLayout, QWidget,
)

from src.core.app_preferences import DISPLAY_NAME_MAX_LENGTH
from src.desktop_app.components import AppCard, InlineMessage, PageHeader, configure_button
from src.desktop_app.theme import create_card, set_label_style
from src.desktop_app.view_models.backup_restore_view_model import (
    BackupSummaryViewModel, RestorePreviewViewModel,
)
from src.desktop_app.view_models.settings_view_model import (
    DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE, DocumentationSubjectOptionViewModel,
    SettingsViewModel,
)
from src.desktop_app.view_models.timetable_view_model import (
    TimetableEntryViewModel, TimetableWeekViewModel,
)
from src.updater.domain import UpdateProjection, UpdateState


DOCUMENTATION_SUBJECTS_HELP_TEXT = (
    "Diese Auswahl steuert, welche Fächer im Dokumentationsstand "
    "berücksichtigt werden. Beobachtungen bleiben immer erhalten."
)


class SettingsNavigationCard(AppCard):
    """One large keyboard-operable local settings destination."""

    activated = Signal(str)

    def __init__(self, key: str, title: str, description: str) -> None:
        super().__init__("interactive")
        self.key = key
        self.setObjectName(f"SettingsNavigationCard_{key}")
        self.setAccessibleName(f"{title}. {description}")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 18, 16)
        copy = QVBoxLayout()
        title_label = QLabel(title)
        set_label_style(title_label, "section_title")
        copy.addWidget(title_label)
        description_label = QLabel(description)
        set_label_style(description_label, "muted")
        copy.addWidget(description_label)
        self.status = QLabel("")
        set_label_style(self.status, "small")
        copy.addWidget(self.status)
        layout.addLayout(copy, 1)
        chevron = QLabel("›")
        chevron.setAccessibleName("Öffnen")
        chevron.setStyleSheet("font-size: 28px; color: #556372;")
        layout.addWidget(chevron, 0, Qt.AlignmentFlag.AlignVCenter)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.activated.emit(self.key)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit(self.key)
            event.accept()
            return
        super().keyPressEvent(event)


class SettingsScreen(QWidget):
    """Render settings state and emit UI commands without service access."""

    documentation_subjects_save_requested = Signal(tuple)
    timetable_add_requested = Signal(int)
    timetable_edit_requested = Signal(str)
    timetable_delete_requested = Signal(str)
    timetable_active_requested = Signal(str, bool)
    backup_create_requested = Signal()
    backup_verify_requested = Signal()
    restore_prepare_requested = Signal()
    restore_start_requested = Signal()
    backup_restore_page_opened = Signal()
    inactivity_minutes_changed = Signal(int)
    password_change_requested = Signal()
    recovery_codes_requested = Signal()
    support_reset_requested = Signal()
    lock_requested = Signal()
    display_name_changed = Signal(str)
    onboarding_requested = Signal()
    device_credential_enable_requested = Signal()
    device_credential_disable_requested = Signal()
    touch_id_preference_changed = Signal(bool)
    update_check_requested = Signal()
    updates_page_opened = Signal()
    school_year_transition_preview_requested = Signal(str, object, object)

    def __init__(self) -> None:
        super().__init__()
        self.documentation_subject_checkboxes: dict[str, QCheckBox] = {}
        self.documentation_subjects_layout = QVBoxLayout()
        self.documentation_status_label = QLabel("")
        self.timetable_week: TimetableWeekViewModel | None = None
        self.selected_timetable_weekday = 1
        self.timetable_tabs = QTabBar()
        self.timetable_tabs.setAccessibleName("Wochentag im Stundenplan")
        self.timetable_tabs.setUsesScrollButtons(False)
        self.timetable_tabs.currentChanged.connect(self._select_timetable_day)
        self.timetable_day_layout = QVBoxLayout()
        self.timetable_empty_label = QLabel("")
        self.timetable_add_button = QPushButton("Stunde hinzufügen")
        configure_button(self.timetable_add_button, "secondary", "Stunde zum ausgewählten Wochentag hinzufügen")
        self.timetable_add_button.clicked.connect(self._emit_timetable_add)
        self.current_page = "overview"
        self.operation_active = False
        self.backup_restore_available = True
        self.restore_preview: RestorePreviewViewModel | None = None
        self.detail_back_buttons: dict[str, QPushButton] = {}
        self._school_year_signature: tuple[str, date, date] | None = None
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._overview_page())
        self.pages.addWidget(self._detail_page("timetable", "Stundenplan", self._timetable_card()))
        self.pages.addWidget(self._detail_page("documentation_subjects", "Fächer für die Dokumentation", self._documentation_subjects_card()))
        self.pages.addWidget(self._detail_page("backup_restore", "Datensicherung", self._backup_restore_card()))
        self.pages.addWidget(self._detail_page("security", "Sicherheit", self._security_card()))
        self.pages.addWidget(self._detail_page("updates", "Updates", self._updates_card()))
        self.pages.addWidget(
            self._detail_page(
                "school_years",
                "Schuljahre",
                self._school_years_card(),
            )
        )
        outer.addWidget(self.pages)

    def _scroll_page(self, content: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("SettingsScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        return scroll

    def _initialize_current_page_cursor(self) -> None:
        scroll = self.pages.currentWidget()
        if not isinstance(scroll, QScrollArea):
            return
        scroll.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        content = scroll.widget()
        if content is not None:
            content.setCursor(Qt.CursorShape.ArrowCursor)

    def _overview_page(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(PageHeader("Einstellungen", "Grundlagen für Dokumentation und Auswertung"))
        self.settings_cards = {
            "timetable": SettingsNavigationCard("timetable", "Stundenplan", "Unterrichtszeiten und Zuordnungen verwalten"),
            "documentation_subjects": SettingsNavigationCard("documentation_subjects", "Fächer für die Dokumentation", "Sichtbare Fächer auswählen"),
            "backup_restore": SettingsNavigationCard("backup_restore", "Datensicherung", "Backup erstellen und wiederherstellen"),
            "security": SettingsNavigationCard("security", "Sicherheit", "Passwortschutz und automatische Sperre"),
            "updates": SettingsNavigationCard("updates", "Updates", "Pilotversion bewusst aktualisieren"),
            "school_years": SettingsNavigationCard(
                "school_years",
                "Schuljahre",
                "Aktuelles Schuljahr und Wechselvorschau",
            ),
        }
        for card in self.settings_cards.values():
            card.activated.connect(self.show_page)
            layout.addWidget(card)
        general = create_card()
        general_layout = QHBoxLayout(general)
        general_layout.setContentsMargins(20, 14, 18, 14)
        text = QVBoxLayout()
        title = QLabel("Allgemein")
        set_label_style(title, "section_title")
        text.addWidget(title)
        hint = QLabel("Kurze Orientierung zur Einrichtung erneut öffnen.")
        hint.setWordWrap(True)
        set_label_style(hint, "muted")
        text.addWidget(hint)
        general_layout.addLayout(text, 1)
        self.onboarding_button = QPushButton("Erste Schritte erneut öffnen")
        configure_button(
            self.onboarding_button,
            "secondary",
            "Erste Schritte erneut öffnen",
        )
        self.onboarding_button.clicked.connect(self.onboarding_requested)
        general_layout.addWidget(
            self.onboarding_button,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addWidget(general)
        layout.addStretch(1)
        return self._scroll_page(content)

    def _detail_page(self, key: str, title: str, body: QWidget) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        back = QPushButton("‹ Einstellungen")
        back.setObjectName(f"SettingsBack_{key}")
        configure_button(back, "quiet", "Zur Einstellungsübersicht zurück")
        back.clicked.connect(self.show_overview)
        self.detail_back_buttons[key] = back
        layout.addWidget(back, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(PageHeader(title))
        layout.addWidget(body)
        layout.addStretch(1)
        return self._scroll_page(content)

    def show_page(self, key: str) -> None:
        page_indexes = {
            "timetable": 1,
            "documentation_subjects": 2,
            "backup_restore": 3,
            "security": 4,
            "updates": 5,
            "school_years": 6,
        }
        if self.operation_active or key not in page_indexes:
            return
        self.current_page = key
        self.pages.setCurrentIndex(page_indexes[key])
        self._initialize_current_page_cursor()
        if key == "backup_restore":
            self.backup_restore_page_opened.emit()
        elif key == "updates":
            self.updates_page_opened.emit()

    def show_overview(self) -> None:
        if self.operation_active:
            return
        self.current_page = "overview"
        self.pages.setCurrentIndex(0)
        self._initialize_current_page_cursor()

    def reset_navigation(self) -> None:
        """Open settings predictably at its orientation-only overview."""
        if not self.operation_active:
            self.show_overview()

    def set_operation_active(self, active: bool, message: str = "") -> None:
        self.operation_active = active
        self.operation_status_label.setText(message if active else "")
        self.operation_progress.setAccessibleName(message if active else "")
        self.operation_progress.setVisible(active)
        for button in self.detail_back_buttons.values():
            button.setDisabled(active)
        self._update_backup_restore_actions()

    def set_backup_restore_available(self, available: bool) -> None:
        """Disable the existing ZIP-v1 controls in Cipher product mode."""
        self.backup_restore_available = bool(available)
        if not self.backup_restore_available:
            message = (
                "Datensicherung und Wiederherstellung sind in diesem "
                "Pilotstand noch nicht verfügbar."
            )
            self.backup_message.set_message(message, tone="info")
            self.restore_message.set_message(message, tone="info")
            self.settings_cards["backup_restore"].status.setText(
                "Noch nicht verfügbar"
            )
        self._update_backup_restore_actions()

    def show_close_blocked(self) -> None:
        self.operation_status_label.setText(
            "Die laufende Datensicherung wird sicher abgeschlossen. "
            "Danach kann die App geschlossen werden."
        )

    def set_settings(self, view_model: SettingsViewModel) -> None:
        self.set_documentation_subjects(view_model.documentation_subjects)
        selected = sum(item.selected for item in view_model.documentation_subjects)
        self.settings_cards["documentation_subjects"].status.setText(f"{selected} von {len(view_model.documentation_subjects)} Fächern aktiv")

    def set_current_school_year(
        self,
        label: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> None:
        """Show the current persisted year and initialize only transient input."""
        if (
            label is None
            or start_date is None
            or end_date is None
        ):
            text = "Nicht eindeutig verfügbar"
            self.current_school_year_label.setText(text)
            self.current_school_year_label.setAccessibleName(
                f"Aktuelles Schuljahr: {text}"
            )
            self.settings_cards["school_years"].status.setText(text)
            self.school_year_transition_button.setEnabled(False)
            return

        period = (
            f"{label} · {start_date.strftime('%d.%m.%Y')} bis "
            f"{end_date.strftime('%d.%m.%Y')}"
        )
        self.current_school_year_label.setText(period)
        self.current_school_year_label.setAccessibleName(
            f"Aktuelles Schuljahr: {period}"
        )
        self.settings_cards["school_years"].status.setText(label)
        self.school_year_transition_button.setEnabled(True)
        signature = (label, start_date, end_date)
        if signature == self._school_year_signature:
            return
        self._school_year_signature = signature
        target_start = end_date + timedelta(days=1)
        try:
            following_start = target_start.replace(
                year=target_start.year + 1
            )
        except ValueError:
            following_start = target_start.replace(
                year=target_start.year + 1,
                month=3,
                day=1,
            )
        target_end = following_start - timedelta(days=1)
        self.new_school_year_start.setDate(
            QDate(target_start.year, target_start.month, target_start.day)
        )
        self.new_school_year_end.setDate(
            QDate(target_end.year, target_end.month, target_end.day)
        )

    def show_school_year_transition_error(self, text: str) -> None:
        self.school_year_transition_message.set_message(text, tone="error")
        self.school_year_transition_message.setFocus()

    def clear_school_year_transition_error(self) -> None:
        self.school_year_transition_message.set_message("")

    def set_timetable(self, week: TimetableWeekViewModel) -> None:
        self.timetable_week = week
        count = sum(len(day.entries) for day in week.days)
        self.settings_cards["timetable"].status.setText("Nicht eingerichtet" if not count else f"{count} Unterrichtsblöcke eingerichtet")
        self.timetable_tabs.blockSignals(True)
        while self.timetable_tabs.count(): self.timetable_tabs.removeTab(0)
        for day in week.days:
            suffix = f" ({len(day.entries)})" if day.entries else ""
            self.timetable_tabs.addTab(f"{day.label}{suffix}")
            self.timetable_tabs.setTabData(self.timetable_tabs.count() - 1, day.weekday)
        self.timetable_tabs.setCurrentIndex(next((i for i in range(self.timetable_tabs.count()) if self.timetable_tabs.tabData(i) == self.selected_timetable_weekday), 0))
        self.timetable_tabs.blockSignals(False)
        self._render_selected_timetable_day()

    def set_backup_status(self, backup: BackupSummaryViewModel | None) -> None:
        if backup is None:
            self.settings_cards["backup_restore"].status.setText("Noch keine geprüfte Sicherung")
            self.latest_backup_label.setText("Noch keine geprüfte Sicherung")
        else:
            self.settings_cards["backup_restore"].status.setText(f"Letzte geprüfte Sicherung: {backup.created_at}")
            self.latest_backup_label.setText(f"{backup.created_at} · {backup.file_name} · {backup.size_label} · Geprüft")

    def set_security_status(self, inactivity_minutes: int) -> None:
        self.settings_cards["security"].status.setText(
            f"Passwortschutz aktiv · Sperre nach {inactivity_minutes} Minuten"
        )
        self.inactivity_combo.blockSignals(True)
        self.inactivity_combo.setCurrentIndex(
            max(0, self.inactivity_combo.findData(inactivity_minutes))
        )
        self.inactivity_combo.blockSignals(False)

    def show_security_message(self, text: str, *, tone: str = "success") -> None:
        self.security_message.set_message(text, tone=tone)

    def set_device_credential_status(
        self,
        *,
        supported: bool,
        enabled: bool,
        local_authentication: str,
        touch_id_preferred: bool = False,
        secret_available: bool = False,
    ) -> None:
        self.remember_device.blockSignals(True)
        self.remember_device.setChecked(enabled)
        self.remember_device.blockSignals(False)
        self.remember_device.setVisible(supported)
        self.remember_device_hint.setVisible(supported)
        self.revoke_device_button.setVisible(supported and enabled)
        touch_available = enabled and secret_available and local_authentication == "available"
        self.touch_id_checkbox.blockSignals(True)
        self.touch_id_checkbox.setChecked(touch_available and touch_id_preferred)
        self.touch_id_checkbox.blockSignals(False)
        self.touch_id_checkbox.setVisible(supported)
        self.touch_id_checkbox.setEnabled(touch_available)
        if not enabled:
            status_text = "zuerst gespeicherte Anmeldung aktivieren"
        elif not secret_available:
            status_text = "gespeicherte Anmeldung nicht verfügbar"
        else:
            status_text = {
                "available": "verfügbar",
                "not_enrolled": "nicht eingerichtet",
                "not_available": "auf diesem Mac nicht verfügbar",
                "locked_out": "vorübergehend gesperrt",
                "unsupported": "auf diesem Mac nicht verfügbar",
                "error": "gerade nicht verfügbar",
            }.get(local_authentication, "gerade nicht verfügbar")
        if touch_available and touch_id_preferred:
            status_text = "aktiviert"
        self.touch_id_status.setText(f"Touch ID: {status_text}")
        self.touch_id_status.setVisible(supported)

    def set_display_name(self, display_name: str | None) -> None:
        self.display_name_input.setText(display_name or "")

    def set_update_status(self, projection: UpdateProjection) -> None:
        self.settings_cards["updates"].status.setText(
            f"Version {projection.current_version} · Kanal Pilot"
        )
        self.update_version_label.setText(
            f"Installiert: {projection.current_version} · Build {projection.build_version}"
        )
        self.update_channel_label.setText("Updatekanal: Pilot")
        checked = projection.last_checked_at or "Noch nicht geprüft"
        self.update_last_check_label.setText(f"Letzte Prüfung: {checked}")
        self.update_status_message.set_message(
            projection.message,
            tone="error" if projection.state is UpdateState.ERROR else "info",
        )
        self.update_check_button.setEnabled(projection.can_check)

    def show_profile_message(self, text: str, *, tone: str = "success") -> None:
        self.profile_message.set_message(text, tone=tone)

    def show_backup_success(self, summary: BackupSummaryViewModel, *, verified: bool = False) -> None:
        self.set_backup_status(summary)
        action = "Die Sicherung wurde geprüft." if verified else "Die Sicherung wurde erstellt und geprüft."
        self.backup_message.set_message(f"{action} {summary.created_at} · {summary.size_label}", tone="success")

    def show_backup_error(self, text: str) -> None:
        self.backup_message.set_message(text, tone="error")

    def show_restore_preview(self, preview: RestorePreviewViewModel) -> None:
        self.restore_preview = preview
        status = {"exact": "Kompatibel", "migration_required": "Migration wird vorbereitet", "incompatible": "Nicht kompatibel"}.get(preview.compatibility_status.lower(), preview.compatibility_status)
        self.restore_preview_label.setText(
            f"Erstellt: {preview.created_at}\nApp-Version: {preview.app_version}\nDatenbank: {status}\n"
            f"Kinder: {preview.students_count} · Beobachtungen: {preview.observations_count}\n"
            f"Berichtrevisionen: {preview.learning_report_revisions_count} · LEG-Revisionen: {preview.learning_conference_revisions_count}\n"
            f"Verwaltete Dateien: {preview.managed_files_count} · Externe Referenzen: {preview.external_references_count} · Fehlend: {preview.external_missing_count}"
        )
        compatible = preview.compatibility_status.lower() != "incompatible"
        self._update_backup_restore_actions()
        self.restore_message.set_message(
            "Die Wiederherstellung ersetzt den aktuellen lokalen Datenbestand. Vorher wird automatisch ein Sicherheitsbackup erstellt. Externe Dateien werden nicht wiederhergestellt. Der Vorgang darf nicht unterbrochen werden.",
            tone="warning" if compatible else "error",
        )

    def show_restore_error(self, text: str) -> None:
        self.restore_message.set_message(text, tone="error")

    def clear_restore_preview(self) -> None:
        self.restore_preview = None
        self.restore_preview_label.setText("")
        self._update_backup_restore_actions()

    def set_documentation_subjects(self, subjects: tuple[DocumentationSubjectOptionViewModel, ...]) -> None:
        self._clear_layout(self.documentation_subjects_layout)
        self.documentation_subject_checkboxes = {}
        for subject in subjects:
            checkbox = QCheckBox(subject.label)
            checkbox.setObjectName(f"DocumentationSubjectCheckbox_{subject.subject_id}")
            checkbox.setChecked(subject.selected)
            checkbox.setAccessibleName(f"{subject.label} als dokumentationsrelevantes Fach verwenden")
            self.documentation_subject_checkboxes[subject.subject_id] = checkbox
            self.documentation_subjects_layout.addWidget(checkbox)
        self.documentation_subjects_layout.addStretch(1)

    def show_documentation_subjects_saved(self) -> None:
        self.documentation_status_label.setText(DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE)

    def _documentation_subjects_card(self) -> QFrame:
        card = create_card(); card.setObjectName("DocumentationSubjectSettingsSection")
        layout = QVBoxLayout(card)
        help_label = QLabel(DOCUMENTATION_SUBJECTS_HELP_TEXT); help_label.setWordWrap(True); set_label_style(help_label, "muted")
        layout.addWidget(help_label); layout.addLayout(self.documentation_subjects_layout)
        save = QPushButton("Speichern"); save.setObjectName("DocumentationSubjectSaveButton"); configure_button(save, "primary", "Dokumentationsfächer speichern")
        save.setShortcut(QKeySequence.StandardKey.Save); save.clicked.connect(self._emit_documentation_subjects_save)
        layout.addWidget(save, 0, Qt.AlignmentFlag.AlignRight)
        set_label_style(self.documentation_status_label, "muted"); self.documentation_status_label.setObjectName("SettingsStatusLabel"); layout.addWidget(self.documentation_status_label)
        return card

    def _timetable_card(self) -> QFrame:
        card = create_card(); card.setObjectName("TimetableSettingsSection"); layout = QVBoxLayout(card)
        help_label = QLabel("Wochenplan für Montag bis Freitag. Überschneidungen werden beim Speichern geprüft."); help_label.setWordWrap(True); set_label_style(help_label, "muted")
        layout.addWidget(help_label); header = QHBoxLayout(); header.addWidget(self.timetable_tabs, 1); header.addWidget(self.timetable_add_button); layout.addLayout(header)
        set_label_style(self.timetable_empty_label, "muted"); self.timetable_empty_label.setObjectName("TimetableEmptyState"); layout.addWidget(self.timetable_empty_label); layout.addLayout(self.timetable_day_layout)
        return card

    def _school_years_card(self) -> QFrame:
        card = create_card()
        card.setObjectName("SchoolYearSettingsSection")
        layout = QVBoxLayout(card)

        current_title = QLabel("Aktuelles Schuljahr")
        set_label_style(current_title, "section_title")
        layout.addWidget(current_title)
        self.current_school_year_label = QLabel("Nicht eindeutig verfügbar")
        self.current_school_year_label.setObjectName("CurrentSchoolYear")
        self.current_school_year_label.setAccessibleName(
            "Aktuelles Schuljahr: Nicht eindeutig verfügbar"
        )
        layout.addWidget(self.current_school_year_label)

        prepare_title = QLabel("Neues Schuljahr")
        set_label_style(prepare_title, "section_title")
        layout.addWidget(prepare_title)
        help_label = QLabel(
            "Die Angaben werden nur für eine Vorschau verwendet. "
            "Beim Schließen wird nichts gespeichert oder ausgeführt."
        )
        help_label.setWordWrap(True)
        set_label_style(help_label, "muted")
        layout.addWidget(help_label)

        form = QFormLayout()
        self.new_school_year_label = QLineEdit()
        self.new_school_year_label.setObjectName("NewSchoolYearLabel")
        self.new_school_year_label.setAccessibleName(
            "Bezeichnung des neuen Schuljahres"
        )
        self.new_school_year_label.setPlaceholderText("Zum Beispiel 2026/27")
        form.addRow("Bezeichnung", self.new_school_year_label)

        self.new_school_year_start = QDateEdit()
        self.new_school_year_start.setObjectName("NewSchoolYearStart")
        self.new_school_year_start.setAccessibleName(
            "Beginn des neuen Schuljahres"
        )
        self.new_school_year_start.setCalendarPopup(True)
        self.new_school_year_start.setDisplayFormat("dd.MM.yyyy")
        form.addRow("Beginn", self.new_school_year_start)

        self.new_school_year_end = QDateEdit()
        self.new_school_year_end.setObjectName("NewSchoolYearEnd")
        self.new_school_year_end.setAccessibleName(
            "Ende des neuen Schuljahres"
        )
        self.new_school_year_end.setCalendarPopup(True)
        self.new_school_year_end.setDisplayFormat("dd.MM.yyyy")
        form.addRow("Ende", self.new_school_year_end)
        layout.addLayout(form)

        self.school_year_transition_message = InlineMessage()
        self.school_year_transition_message.setObjectName(
            "SchoolYearTransitionMessage"
        )
        self.school_year_transition_message.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus
        )
        layout.addWidget(self.school_year_transition_message)

        self.school_year_transition_button = QPushButton(
            "Schuljahreswechsel vorbereiten"
        )
        self.school_year_transition_button.setObjectName(
            "PrepareSchoolYearTransition"
        )
        configure_button(
            self.school_year_transition_button,
            "primary",
            "Schuljahreswechsel als flüchtige Vorschau vorbereiten",
        )
        self.school_year_transition_button.setEnabled(False)
        self.school_year_transition_button.clicked.connect(
            self._emit_school_year_transition_preview
        )
        layout.addWidget(
            self.school_year_transition_button,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )
        return card

    def _emit_school_year_transition_preview(self) -> None:
        self.clear_school_year_transition_error()
        self.school_year_transition_preview_requested.emit(
            self.new_school_year_label.text(),
            self.new_school_year_start.date().toPython(),
            self.new_school_year_end.date().toPython(),
        )

    def _backup_restore_card(self) -> QFrame:
        card = create_card(); card.setObjectName("BackupRestoreSettingsSection"); layout = QVBoxLayout(card)
        title = QLabel("Letzte geprüfte lokale Sicherung"); set_label_style(title, "section_title"); layout.addWidget(title)
        self.latest_backup_label = QLabel("Noch keine geprüfte Sicherung"); self.latest_backup_label.setWordWrap(True); set_label_style(self.latest_backup_label, "muted"); layout.addWidget(self.latest_backup_label)
        note = QLabel("Freie Exporte und externe Dateireferenzen sind nicht Bestandteil der Sicherung."); note.setWordWrap(True); set_label_style(note, "small"); layout.addWidget(note)
        self.operation_status_label = QLabel(""); self.operation_status_label.setWordWrap(True); self.operation_status_label.setObjectName("BackupRestoreOperationStatus"); self.operation_status_label.setAccessibleName("Status der Datensicherung"); set_label_style(self.operation_status_label, "muted"); layout.addWidget(self.operation_status_label)
        self.operation_progress = QProgressBar(); self.operation_progress.setObjectName("BackupRestoreOperationProgress"); self.operation_progress.setRange(0, 0); self.operation_progress.setTextVisible(False); self.operation_progress.setVisible(False); layout.addWidget(self.operation_progress)
        self.backup_message = InlineMessage(); layout.addWidget(self.backup_message)
        self.backup_create_button = QPushButton("Backup erstellen"); configure_button(self.backup_create_button, "primary", "Backup in einen ausgewählten Ordner erstellen"); self.backup_create_button.clicked.connect(self.backup_create_requested); layout.addWidget(self.backup_create_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.backup_verify_button = QPushButton("Backup prüfen …"); configure_button(self.backup_verify_button, "secondary", "Bestehende Sicherung technisch prüfen"); self.backup_verify_button.clicked.connect(self.backup_verify_requested); layout.addWidget(self.backup_verify_button, 0, Qt.AlignmentFlag.AlignLeft)
        restore_title = QLabel("Wiederherstellung"); set_label_style(restore_title, "section_title"); layout.addWidget(restore_title)
        self.restore_prepare_button = QPushButton("Wiederherstellen …"); configure_button(self.restore_prepare_button, "secondary", "Sicherung prüfen und Wiederherstellung vorbereiten"); self.restore_prepare_button.clicked.connect(self.restore_prepare_requested); layout.addWidget(self.restore_prepare_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.restore_preview_label = QLabel(""); self.restore_preview_label.setWordWrap(True); self.restore_preview_label.setObjectName("RestorePreview"); set_label_style(self.restore_preview_label, "muted"); layout.addWidget(self.restore_preview_label)
        self.restore_message = InlineMessage(); layout.addWidget(self.restore_message)
        self.restore_start_button = QPushButton("Wiederherstellung starten"); configure_button(self.restore_start_button, "primary", "Vorbereitete Wiederherstellung verbindlich starten"); self.restore_start_button.setEnabled(False); self.restore_start_button.clicked.connect(self.restore_start_requested); layout.addWidget(self.restore_start_button, 0, Qt.AlignmentFlag.AlignLeft)
        return card

    def _security_card(self) -> QFrame:
        card = create_card()
        card.setObjectName("SecuritySettingsSection")
        layout = QVBoxLayout(card)
        profile_title = QLabel("Persönliche Begrüßung")
        set_label_style(profile_title, "section_title")
        layout.addWidget(profile_title)
        layout.addWidget(QLabel("Wie dürfen wir dich begrüßen?"))
        self.display_name_input = QLineEdit()
        self.display_name_input.setPlaceholderText("Zum Beispiel Laura")
        self.display_name_input.setAccessibleName(
            "Optionaler Anzeigename für die persönliche Begrüßung"
        )
        self.display_name_input.setMaxLength(DISPLAY_NAME_MAX_LENGTH)
        self.display_name_input.returnPressed.connect(
            lambda: self.display_name_changed.emit(self.display_name_input.text())
        )
        layout.addWidget(self.display_name_input)
        profile_hint = QLabel("Optional · Wird nur lokal als Klartext angezeigt.")
        set_label_style(profile_hint, "small")
        layout.addWidget(profile_hint)
        save_profile = QPushButton("Begrüßung speichern")
        configure_button(save_profile, "secondary", "Persönliche Begrüßung speichern")
        save_profile.clicked.connect(
            lambda: self.display_name_changed.emit(self.display_name_input.text())
        )
        layout.addWidget(save_profile, 0, Qt.AlignmentFlag.AlignLeft)
        self.profile_message = InlineMessage()
        layout.addWidget(self.profile_message)
        security_title = QLabel("App-Sperre")
        set_label_style(security_title, "section_title")
        layout.addWidget(security_title)
        active = QLabel("Passwortschutz aktiv")
        layout.addWidget(active)
        interval_label = QLabel("Automatisch sperren nach")
        layout.addWidget(interval_label)
        self.inactivity_combo = QComboBox()
        self.inactivity_combo.setAccessibleName("Automatische Sperrzeit")
        for minutes in (5, 10, 15, 30, 60):
            self.inactivity_combo.addItem(f"{minutes} Minuten", minutes)
        self.inactivity_combo.currentIndexChanged.connect(
            lambda _index: self.inactivity_minutes_changed.emit(
                int(self.inactivity_combo.currentData())
            )
        )
        layout.addWidget(self.inactivity_combo, 0, Qt.AlignmentFlag.AlignLeft)
        comfort_title = QLabel("Komfort beim Entsperren")
        set_label_style(comfort_title, "section_title")
        layout.addWidget(comfort_title)
        self.remember_device = QCheckBox("Auf diesem Gerät angemeldet bleiben")
        self.remember_device.setAccessibleName("Auf diesem Gerät angemeldet bleiben")
        self.remember_device.setVisible(False)
        self.remember_device.clicked.connect(
            lambda checked: (
                self.device_credential_enable_requested.emit()
                if checked
                else self.device_credential_disable_requested.emit()
            )
        )
        layout.addWidget(self.remember_device)
        self.remember_device_hint = QLabel(
            "Die App wird weiterhin nach Inaktivität oder Ruhezustand gesperrt."
        )
        self.remember_device_hint.setWordWrap(True)
        set_label_style(self.remember_device_hint, "small")
        self.remember_device_hint.setVisible(False)
        layout.addWidget(self.remember_device_hint)
        self.touch_id_checkbox = QCheckBox("Touch ID zum Entsperren verwenden")
        self.touch_id_checkbox.setAccessibleName("Touch ID zum Entsperren verwenden")
        self.touch_id_checkbox.setVisible(False)
        self.touch_id_checkbox.toggled.connect(self.touch_id_preference_changed)
        layout.addWidget(self.touch_id_checkbox)
        self.touch_id_status = QLabel("Touch ID: nicht verfügbar")
        set_label_style(self.touch_id_status, "small")
        self.touch_id_status.setVisible(False)
        layout.addWidget(self.touch_id_status)
        self.revoke_device_button = QPushButton("Gespeicherte Anmeldung widerrufen")
        configure_button(
            self.revoke_device_button,
            "secondary",
            "Gespeicherte Anmeldung widerrufen",
        )
        self.revoke_device_button.clicked.connect(
            self.device_credential_disable_requested
        )
        self.revoke_device_button.setVisible(False)
        layout.addWidget(self.revoke_device_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.security_message = InlineMessage()
        layout.addWidget(self.security_message)
        change = QPushButton("Passwort ändern")
        configure_button(change, "secondary", "Lokales Passwort ändern")
        change.clicked.connect(self.password_change_requested)
        layout.addWidget(change, 0, Qt.AlignmentFlag.AlignLeft)
        recovery_title = QLabel("Wiederherstellung")
        set_label_style(recovery_title, "section_title")
        layout.addWidget(recovery_title)
        recovery_note = QLabel(
            "Wenn Passwort und Recovery-Codes nicht mehr verfügbar sind, kann eine "
            "technisch gebundene Support-Anfrage erstellt werden."
        )
        recovery_note.setWordWrap(True)
        set_label_style(recovery_note, "small")
        layout.addWidget(recovery_note)
        recovery = QPushButton("Recovery-Codes neu erzeugen")
        configure_button(recovery, "secondary", "Neue Recovery-Codes erzeugen")
        recovery.clicked.connect(self.recovery_codes_requested)
        layout.addWidget(recovery, 0, Qt.AlignmentFlag.AlignLeft)
        support_reset = QPushButton("Technische Support-Reset-Anfrage erstellen")
        support_reset.setObjectName("SupportResetSettingsButton")
        configure_button(
            support_reset,
            "secondary",
            "Technische Support-Reset-Anfrage erstellen",
        )
        support_reset.clicked.connect(self.support_reset_requested)
        layout.addWidget(support_reset, 0, Qt.AlignmentFlag.AlignLeft)
        lock = QPushButton("Jetzt sperren")
        configure_button(lock, "primary", "App jetzt sperren")
        lock.clicked.connect(self.lock_requested)
        layout.addWidget(lock, 0, Qt.AlignmentFlag.AlignLeft)
        notice = QLabel(
            "Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups."
        )
        notice.setWordWrap(True)
        set_label_style(notice, "muted")
        layout.addWidget(notice)
        filevault = QLabel(
            "Für den Schutz der Dateien auf dem Mac empfehlen wir FileVault und ein geschütztes Benutzerkonto."
        )
        filevault.setWordWrap(True)
        set_label_style(filevault, "small")
        layout.addWidget(filevault)
        return card

    def _updates_card(self) -> QFrame:
        card = create_card()
        card.setObjectName("UpdateSettingsSection")
        layout = QVBoxLayout(card)
        title = QLabel("Beaufsichtigte Pilotupdates")
        set_label_style(title, "section_title")
        layout.addWidget(title)
        note = QLabel(
            "Updates werden nur nach deiner ausdrücklichen Auswahl gesucht und "
            "installiert. Es gibt keine automatische Hintergrundinstallation."
        )
        note.setWordWrap(True)
        set_label_style(note, "muted")
        layout.addWidget(note)
        self.update_version_label = QLabel("Installiert: –")
        self.update_version_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.update_version_label)
        self.update_channel_label = QLabel("Updatekanal: Pilot")
        self.update_channel_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.update_channel_label)
        self.update_last_check_label = QLabel("Letzte Prüfung: Noch nicht geprüft")
        self.update_last_check_label.setTextFormat(Qt.TextFormat.PlainText)
        set_label_style(self.update_last_check_label, "small")
        layout.addWidget(self.update_last_check_label)
        self.update_status_message = InlineMessage()
        layout.addWidget(self.update_status_message)
        self.update_check_button = QPushButton("Nach Updates suchen")
        self.update_check_button.setObjectName("CheckForUpdatesButton")
        configure_button(
            self.update_check_button,
            "primary",
            "Im Pilotkanal nach einer neuen Version suchen",
        )
        self.update_check_button.clicked.connect(self.update_check_requested)
        layout.addWidget(self.update_check_button, 0, Qt.AlignmentFlag.AlignLeft)
        fallback = QLabel(
            "Falls die Updateprüfung nicht möglich ist, kann weiterhin ein neues "
            "DMG manuell installiert werden. Die lokalen Daten bleiben außerhalb der App."
        )
        fallback.setWordWrap(True)
        set_label_style(fallback, "small")
        layout.addWidget(fallback)
        return card

    def _update_backup_restore_actions(self) -> None:
        disabled = self.operation_active or not self.backup_restore_available
        self.backup_create_button.setDisabled(disabled)
        self.backup_verify_button.setDisabled(disabled)
        self.restore_prepare_button.setDisabled(disabled)
        restore_is_compatible = (
            self.restore_preview is not None
            and self.restore_preview.compatibility_status.lower() != "incompatible"
        )
        self.restore_start_button.setEnabled(
            self.backup_restore_available
            and not self.operation_active
            and restore_is_compatible
        )

    def _timetable_entry_card(self, entry: TimetableEntryViewModel) -> QFrame:
        card = create_card(); card.setObjectName(f"TimetableEntry_{entry.timetable_entry_id}"); layout = QHBoxLayout(card)
        time = QLabel(entry.time_label); time.setMinimumWidth(105); set_label_style(time, "card_title"); layout.addWidget(time)
        details = QVBoxLayout(); subject = QLabel(entry.subject_label); set_label_style(subject, "card_title"); details.addWidget(subject)
        target = QLabel(" · ".join(part for part in [entry.target_type_label, entry.target_label, entry.room] if part)); target.setWordWrap(True); set_label_style(target, "muted"); details.addWidget(target); layout.addLayout(details, 1)
        active = QCheckBox("Aktiv"); active.setChecked(entry.active); active.setObjectName(f"TimetableActive_{entry.timetable_entry_id}"); active.toggled.connect(lambda checked, entry_id=entry.timetable_entry_id: self.timetable_active_requested.emit(entry_id, checked)); layout.addWidget(active)
        edit = QPushButton("Bearbeiten"); configure_button(edit, "secondary", "Stunde bearbeiten"); edit.clicked.connect(lambda checked=False, entry_id=entry.timetable_entry_id: self.timetable_edit_requested.emit(entry_id)); layout.addWidget(edit)
        delete = QPushButton("Löschen"); configure_button(delete, "destructive", "Stunde löschen"); delete.clicked.connect(lambda checked=False, entry_id=entry.timetable_entry_id: self.timetable_delete_requested.emit(entry_id)); layout.addWidget(delete)
        if not entry.active:
            opacity = QGraphicsOpacityEffect(card)
            opacity.setOpacity(0.58)
            card.setGraphicsEffect(opacity)
        return card

    def _select_timetable_day(self, index: int) -> None:
        if index >= 0:
            self.selected_timetable_weekday = int(self.timetable_tabs.tabData(index)); self._render_selected_timetable_day()

    def _render_selected_timetable_day(self) -> None:
        self._clear_layout(self.timetable_day_layout)
        if self.timetable_week is None: return
        day = next(day for day in self.timetable_week.days if day.weekday == self.selected_timetable_weekday)
        self.timetable_empty_label.setText(f"Für {day.label} sind noch keine Stunden eingetragen. Über „Stunde hinzufügen“ kannst du den Tagesplan beginnen.")
        self.timetable_empty_label.setVisible(not day.entries); self.timetable_add_button.setObjectName(f"TimetableAdd_{day.weekday}")
        container = QFrame(); container.setObjectName(f"TimetableDay_{day.weekday}"); rows = QVBoxLayout(container); rows.setContentsMargins(0, 0, 0, 0)
        for entry in day.entries: rows.addWidget(self._timetable_entry_card(entry))
        self.timetable_day_layout.addWidget(container)

    def _emit_timetable_add(self) -> None: self.timetable_add_requested.emit(self.selected_timetable_weekday)
    def _emit_documentation_subjects_save(self) -> None: self.documentation_subjects_save_requested.emit(tuple(key for key, value in self.documentation_subject_checkboxes.items() if value.isChecked()))
    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0); widget = item.widget()
            if widget is not None: widget.setParent(None); widget.deleteLater()
