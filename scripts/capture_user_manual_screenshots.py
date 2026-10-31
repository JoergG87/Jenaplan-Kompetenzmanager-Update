"""Create current, privacy-neutral screenshots for the pilot user manual.

The generator never opens an application, pilot, or product data root.  It builds
one deterministic synthetic SQLite fixture in a temporary directory, renders
current PySide views from its projections, and deletes the temporary root after
capture.
"""

from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QScrollArea, QWidget

from scripts.seed_test_data import seed_test_data
from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from src.desktop_app.adapters.master_data_desktop_adapter import MasterDataDesktopAdapter
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
from src.desktop_app.components import create_confirmation_message
from src.desktop_app.dialogs.app_info_dialog import AppInfoDialog
from src.desktop_app.dialogs.learning_conference_dialog import (
    LearningConferenceDialog,
    LearningConferenceDraftSelectionDialog,
)
from src.desktop_app.dialogs.learning_report_dialog import (
    LearningReportDialog,
    LearningReportDraftSelectionDialog,
)
from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog
from src.desktop_app.dialogs.timetable_entry_dialog import TimetableEntryDialog
from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.lesson_times_schema import LESSON_TIME_TEMPLATE_STATEMENT
from src.core.lesson_time_templates import LessonTimeTemplate
from src.core.timetable_schema import (
    TIMETABLE_INDEX_STATEMENT, TIMETABLE_SUBJECTS_STATEMENT, TIMETABLE_TARGET_STATEMENT,
)
from src.core.timetable_weeks_schema import (
    SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION, TIMETABLE_WEEKS_STATEMENTS,
)
from src.application.commands.timetable import SaveTimetableEntryCommand
from src.desktop_app.view_models.lesson_time_templates_view_model import (
    LessonTimeTemplateOptionViewModel, LessonTimeTemplatesViewModel,
)
from src.desktop_app.runtime import runtime_paths
from src.desktop_app.screens.master_data_screen import MasterDataScreen
from src.desktop_app.screens.onboarding_screen import (
    OnboardingScreen,
    OnboardingStatusProjection,
)
from src.desktop_app.screens.overview_screen import OverviewScreen
from src.desktop_app.screens.settings_screen import SettingsScreen
from src.desktop_app.screens.student_profile_screen import StudentProfileScreen
from src.desktop_app.security_ui import AuthenticationDialog
from src.desktop_app.theme import apply_app_theme
from src.desktop_app.view_models.backup_restore_view_model import (
    BackupSummaryViewModel,
    RestorePreviewViewModel,
)
from src.security.startup import SecurityStartState, SecurityStartupDecision
from src.version import APP_BUILD_VERSION, APP_VERSION


CAPTURE_TIME = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)
STUDENT_ID = "STU-000001"


def _prepare_v7_documentation_fixture(database: SQLiteDatabase) -> None:
    """Use the exact V7 DDL only in the disposable screenshot fixture.

    This is an unencrypted rendering fixture, never an installation migration
    or evidence for SQLCipher, backup, restore, or Keychain behavior.
    """
    with closing(database.connect()) as connection, connection:
        links = tuple(tuple(row) for row in connection.execute(
            "SELECT timetable_entry_id, subject_id FROM timetable_entries"))
        connection.execute(LESSON_TIME_TEMPLATE_STATEMENT)
        connection.execute(TIMETABLE_TARGET_STATEMENT)
        connection.execute("""INSERT INTO timetable_entries_v5_target SELECT
            timetable_entry_id, weekday, start_time, end_time, 'subject_lesson',
            target_type, target_id, room, active, sort_order, created_at, updated_at,
            deleted_at FROM timetable_entries""")
        connection.execute("DROP TABLE timetable_entries")
        connection.execute("ALTER TABLE timetable_entries_v5_target RENAME TO timetable_entries")
        connection.execute(TIMETABLE_INDEX_STATEMENT)
        connection.execute(TIMETABLE_SUBJECTS_STATEMENT)
        connection.executemany("INSERT INTO timetable_entry_subjects VALUES (?, ?)", links)
        for statement in TIMETABLE_WEEKS_STATEMENTS:
            connection.execute(statement)
        connection.execute("PRAGMA user_version=7")
        identity = DatabaseCompatibilityInspector.schema_identity_for_connection(connection)
        if identity.fingerprint != SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity.fingerprint:
            raise RuntimeError("Screenshot-Fixture hat nicht die exakte V7-Identität.")


def _capture(widget: QWidget, destination: Path, file_name: str, *, width: int = 1400, height: int = 900) -> Path:
    widget.resize(width, height)
    widget.show()
    QApplication.processEvents()
    # QMessageBox adjusts itself when shown; apply the requested documentation
    # viewport once more so its full warning and both choices are visible.
    widget.resize(width, height)
    QApplication.processEvents()
    path = destination / file_name
    if not widget.grab().save(str(path), "PNG"):
        raise RuntimeError(f"Screenshot konnte nicht gespeichert werden: {path}")
    widget.close()
    widget.deleteLater()
    QApplication.processEvents()
    return path


def _replace_real_example_name(widget: QWidget) -> None:
    """Keep the documentation fixture fictional without changing product UI code."""
    for field in widget.findChildren(QLineEdit):
        if field.placeholderText() == "Zum Beispiel Laura":
            field.setPlaceholderText("Zum Beispiel Mara")


def _capture_restore_preview(widget: SettingsScreen, destination: Path) -> Path:
    """Capture the real backup/restore card at a readable documentation width."""
    widget.resize(840, 700)
    widget.show()
    QApplication.processEvents()
    card = widget.findChild(QWidget, "BackupRestoreSettingsSection")
    if card is None:
        raise RuntimeError("Datensicherungskarte für Restore-Vorschau fehlt.")
    path = destination / "21_restore_vorschau.png"
    if not card.grab().save(str(path), "PNG"):
        raise RuntimeError("Restore-Vorschau konnte nicht gespeichert werden.")
    widget.close()
    widget.deleteLater()
    QApplication.processEvents()
    return path


def _profile_screen(adapter: StudentDesktopAdapter) -> StudentProfileScreen:
    profile = adapter.get_student_profile(STUDENT_ID)
    if profile is None:
        raise RuntimeError("Synthetisches Schülerprofil fehlt.")
    bundle = adapter.student_profile_projection_bundle(STUDENT_ID)
    screen = StudentProfileScreen()
    screen.set_student(
        profile,
        adapter.list_observations_for_student(STUDENT_ID),
        adapter.list_competency_overview_for_student(STUDENT_ID),
        adapter.get_report_preview_for_student(STUDENT_ID),
        adapter.list_documentation_status_for_student(STUDENT_ID),
        adapter.list_documents_for_student(STUDENT_ID),
        adapter.competency_cockpit_for_student(STUDENT_ID),
        adapter.student_profile_dashboard_for_student(STUDENT_ID),
        report_overview=adapter.report_overview_for_student(STUDENT_ID),
        documentation_subjects=bundle.documentation_subjects,
    )
    return screen


def _restore_preview() -> RestorePreviewViewModel:
    return RestorePreviewViewModel(
        created_at="31.10.2026, 10:15",
        app_version=APP_VERSION,
        compatibility_status="Kompatibel",
        students_count=24,
        observations_count=186,
        learning_report_revisions_count=3,
        learning_conference_revisions_count=2,
        managed_files_count=8,
        external_references_count=0,
        external_missing_count=0,
        archive_path=Path("/synthetisch/Jenaplan-Review.jkmebackup"),
        restore_id="synthetische-dokumentation",
    )


def _selection_drafts(drafts: tuple[object, ...]) -> tuple[object, ...]:
    if len(drafts) > 1:
        return drafts
    if not drafts:
        raise RuntimeError("Synthetische Entwürfe fehlen.")
    first = drafts[0]
    if not hasattr(first, "period_start") or not hasattr(first, "period_end"):
        return drafts
    changes = {
        "period_start": first.period_start.replace(year=first.period_start.year - 1),
        "period_end": first.period_end.replace(year=first.period_end.year - 1),
    }
    if getattr(first, "conference_date", None) is not None:
        changes["conference_date"] = first.conference_date.replace(
            year=first.conference_date.year - 1
        )
    return first, replace(first, **changes)


def capture(output: Path) -> tuple[Path, ...]:
    """Render each documented screen from a disposable synthetic SQLite root."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    application = QApplication.instance() or QApplication([])
    application.setApplicationName("Jenaplan-Kompetenzmanager")
    application.setApplicationVersion(APP_VERSION)
    application.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, True)
    apply_app_theme(application)
    captured: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="jenaplan-user-manual-screenshots-") as temporary:
        paths = runtime_paths(Path(temporary) / "synthetic-runtime")
        seed = seed_test_data(
            paths.database,
            reset=True,
            teacher_name="Mara Lernbegleiterin",
        )
        if seed.student_count <= 0 or seed.observation_count <= 0:
            raise RuntimeError("Synthetische Screenshotdaten sind unvollständig.")
        database = SQLiteDatabase(paths.database, initialize_schema=False)
        _prepare_v7_documentation_fixture(database)
        adapter = StudentDesktopAdapter(database=database,
            today_provider=lambda: CAPTURE_TIME.date(), now_provider=lambda: CAPTURE_TIME)
        timetable = TimetableDesktopAdapter(database)
        timetable.configure_week_cycle(CAPTURE_TIME.date(), "A")
        # Replace only disposable synthetic lessons so the new product features
        # can be understood together in a compact Monday view.
        for entry in timetable.repository.list_entries():
            timetable.delete_entry(entry.timetable_entry_id)
        group_id = timetable.week_view_model().targets_by_type["group"][0].item_id
        home = timetable.save_entry(SaveTimetableEntryCommand(
            "", 1, "08:00", "08:30", "", "group", group_id, "Stammgruppenraum", True,
            entry_kind="homeroom_session"))
        combined = timetable.save_entry(SaveTimetableEntryCommand(
            "", 1, "08:45", "09:30", "", "group", group_id, "Lernatelier", True,
            entry_kind="subject_lesson", subject_ids=("deutsch", "mathematik"), week_pattern="A"))
        timetable.save_entry(SaveTimetableEntryCommand(
            "", 1, "08:45", "09:30", "", "group", group_id, "Musikraum", True,
            entry_kind="subject_lesson", subject_ids=("musik",), week_pattern="B"))
        templates = tuple(LessonTimeTemplateOptionViewModel(LessonTimeTemplate(*values))
                          for values in ((1, "08:00", "08:30"), (2, "08:45", "09:30")))
        curriculum = CurriculumDesktopAdapter(database=database)
        master_data = MasterDataDesktopAdapter(adapter)

        login = AuthenticationDialog(
            service=None,
            repository=None,
            decision=SecurityStartupDecision(SecurityStartState.LOGIN_REQUIRED, "DOC-SYNTHETIC"),
        )
        captured.append(_capture(login, output, "15_anmeldung.png", width=1180, height=760))

        enrollment = AuthenticationDialog(
            service=None,
            repository=None,
            decision=SecurityStartupDecision(SecurityStartState.FIRST_RUN, "DOC-SYNTHETIC"),
        )
        _replace_real_example_name(enrollment)
        captured.append(_capture(enrollment, output, "16_passwortanlage.png", width=1180, height=760))

        security = SettingsScreen()
        security.set_security_status(15)
        security.set_device_credential_status(
            supported=True,
            enabled=True,
            local_authentication="not_enrolled",
            touch_id_preferred=False,
            secret_available=True,
        )
        _replace_real_example_name(security)
        security.show_page("security")
        captured.append(_capture(security, output, "17_sicherheit_touch_id.png"))

        onboarding = OnboardingScreen()
        onboarding.set_context(
            step=1,
            display_name="Mara",
            status_projection=OnboardingStatusProjection(),
        )
        captured.append(_capture(onboarding, output, "24_first_steps.png", width=1180, height=760))

        dashboard = OverviewScreen()
        projection = timetable.read_projection(CAPTURE_TIME)
        occurrence = projection.current or projection.next
        if occurrence is None:
            heatmap, suggested = adapter.dashboard_documentation_refresh(at=CAPTURE_TIME)
        else:
            heatmap, suggested = adapter.dashboard_documentation_refresh(
                target_type=occurrence.entry.target_type,
                target_id=occurrence.entry.target_id,
                subject_id=occurrence.entry.subject_ids[0] if occurrence.entry.subject_ids else "",
                subject_label=occurrence.entry.subject_label,
                at=CAPTURE_TIME,
            )
        dashboard.set_dashboard(
            projection,
            heatmap,
            CAPTURE_TIME,
            not timetable.week_view_model().is_empty,
            suggested,
            "Mara",
        )
        captured.append(_capture(dashboard, output, "01_dashboard.png"))

        student = adapter.get_student_profile(STUDENT_ID)
        if student is None:
            raise RuntimeError("Synthetischer Schüler fehlt.")
        observation = NewObservationDialog(
            student,
            curriculum,
            adapter,
            subject_options=adapter.list_observation_subject_options(STUDENT_ID),
            competency_subject_groups=(
                adapter.list_observation_competency_subject_groups(STUDENT_ID)
            ),
            recent_competencies=adapter.list_recent_observation_competencies(STUDENT_ID),
        )
        captured.append(_capture(observation, output, "02_observation_dialog.png"))

        profile = _profile_screen(adapter)
        captured.append(_capture(profile, output, "04_student_profile_overview.png"))

        cockpit = _profile_screen(adapter)
        cockpit.profile_tabs.setCurrentIndex(2)
        captured.append(_capture(cockpit, output, "05_student_profile_competency_development.png"))

        report_drafts = _selection_drafts(adapter.list_learning_report_drafts_for_student(STUDENT_ID))
        report_selection = LearningReportDraftSelectionDialog(report_drafts)
        captured.append(_capture(report_selection, output, "18_bericht_entwurf_auswahl.png", width=900, height=650))

        report_initial = report_drafts[0]
        report_preparation = adapter.learning_report_preparation_for_student(
            STUDENT_ID,
            period_end=report_initial.period_end,
            retained_competency_ids=report_initial.competency_ids,
        )
        if report_preparation is None:
            raise RuntimeError("Synthetische Berichtsvorbereitung fehlt.")
        report_status = adapter.learning_report_revision_status(report_initial.report_draft_id)
        report_workspace = LearningReportDialog(
            report_preparation,
            initial_draft=report_initial,
            revision_status=report_status,
        )
        captured.append(_capture(report_workspace, output, "06_learning_report_workspace.png"))

        report_revision = LearningReportDialog(
            report_preparation,
            initial_draft=report_initial,
            revision_status=report_status,
        )
        report_revision.show_workspace("revisions")
        captured.append(_capture(report_revision, output, "10_report_read_only_revision.png"))

        conference_drafts = _selection_drafts(
            adapter.list_learning_conference_drafts_for_student(STUDENT_ID)
        )
        conference_selection = LearningConferenceDraftSelectionDialog(conference_drafts)
        captured.append(_capture(conference_selection, output, "19_leg_entwurf_auswahl.png", width=900, height=650))

        conference_initial = conference_drafts[0]
        conference_preparation = adapter.learning_conference_preparation_for_student(
            STUDENT_ID,
            conference_date=conference_initial.conference_date,
            retained_competency_ids=conference_initial.competency_ids,
        )
        if conference_preparation is None:
            raise RuntimeError("Synthetische LEG-Vorbereitung fehlt.")
        conference = LearningConferenceDialog(
            conference_preparation,
            initial_draft=conference_initial,
        )
        conference.set_active_phase("agreements", focus=False)
        captured.append(_capture(conference, output, "11_learning_conference_preparation.png"))

        backup = SettingsScreen()
        backup.set_backup_status(
            BackupSummaryViewModel(
                created_at="31.10.2026, 10:15",
                file_name="Jenaplan-Review.jkmebackup",
                size_bytes=4_500_000,
                verified=True,
            )
        )
        backup.show_page("backup_restore")
        captured.append(_capture(backup, output, "20_backup.png"))

        restore = SettingsScreen()
        restore.set_backup_status(
            BackupSummaryViewModel(
                created_at="31.10.2026, 10:15",
                file_name="Jenaplan-Review.jkmebackup",
                size_bytes=4_500_000,
                verified=True,
            )
        )
        restore.show_page("backup_restore")
        restore.show_restore_preview(_restore_preview())
        captured.append(_capture_restore_preview(restore, output))

        restart_notice, _confirm = create_confirmation_message(
            None,
            "Wiederherstellung starten",
            "Der aktuelle lokale Datenbestand wird ersetzt. Vorher wird automatisch ein Sicherheitsbackup erstellt. Die App wird anschließend neu gestartet.\n\nWiederherstellung jetzt starten?",
            confirm_text="Wiederherstellen",
        )
        message_label = restart_notice.findChild(QLabel, "qt_msgbox_label")
        if message_label is not None:
            message_label.setMinimumWidth(620)
            message_label.setWordWrap(True)
        restart_notice.adjustSize()
        captured.append(_capture(restart_notice, output, "22_restore_neustart.png", width=760, height=420))

        timetable_screen = SettingsScreen(now_provider=lambda: CAPTURE_TIME,
                                           lesson_time_templates_available=True)
        timetable_screen.set_timetable(timetable.week_view_model(CAPTURE_TIME.date()))
        timetable_screen.show_page("timetable")
        captured.append(_capture(timetable_screen, output, "13_timetable_settings.png"))

        time_settings = SettingsScreen(lesson_time_templates_available=True)
        time_settings.lesson_time_templates_editor.set_view_model(LessonTimeTemplatesViewModel(templates))
        time_settings.lesson_time_templates_editor.template_combo.setCurrentIndex(2)
        time_settings.show_page("lesson_time_templates")
        captured.append(_capture(time_settings, output, "26_lesson_time_templates.png", width=1180, height=760))

        combined_editor = TimetableEntryDialog(timetable.week_view_model(CAPTURE_TIME.date()),
            weekday=1, entry=combined, templates=templates)
        combined_editor.lesson_template_combo.setCurrentIndex(2)
        captured.append(_capture(combined_editor, output, "27_combined_subjects.png", width=820, height=1320))

        home_editor = TimetableEntryDialog(timetable.week_view_model(CAPTURE_TIME.date()),
            weekday=1, entry=home, templates=templates)
        captured.append(_capture(home_editor, output, "28_homeroom_session.png", width=820, height=1320))

        timetable.set_week_override(CAPTURE_TIME.date(), "B")
        week_rules = SettingsScreen(now_provider=lambda: CAPTURE_TIME, lesson_time_templates_available=True)
        week_rules.set_timetable(timetable.week_view_model(CAPTURE_TIME.date()))
        week_rules.show_page("timetable")
        week_rules.timetable_week_rules_toggle.setChecked(True)
        captured.append(_capture(week_rules, output, "29_week_rules.png", height=1000))

        current_year = adapter.current_school_year()
        if current_year is None:
            raise RuntimeError("Synthetisches aktuelles Schuljahr fehlt.")
        adapter.save_student_documentation_subjects(
            STUDENT_ID, current_year.school_year_id, "custom", ("deutsch", "mathematik", "englisch"))
        plants = _profile_screen(adapter)
        plants.profile_tabs.setCurrentIndex(3)
        plants.resize(1400, 1000)
        plants.show()
        QApplication.processEvents()
        plants._report_subjects_expanded = True
        plants._render_report_subjects(plants.current_report_overview)
        QApplication.processEvents()
        plants.profile_tabs.widget(3).ensureWidgetVisible(plants.subjects_card, 12, 12)
        QApplication.processEvents()
        # Capture the actual Fachübersicht widget rather than an arbitrary crop
        # through the adjacent timeline. No text or product controls are edited.
        card_path = output / "30_subject_plants.png"
        if not plants.subjects_card.grab().save(str(card_path), "PNG"):
            raise RuntimeError("Fachübersicht konnte nicht gespeichert werden.")
        captured.append(card_path)
        plants.close()
        plants.deleteLater()
        QApplication.processEvents()

        master = MasterDataScreen()
        master.set_master_data(master_data.view_model())
        captured.append(_capture(master, output, "14_master_data.png"))

        about = AppInfoDialog()
        captured.append(_capture(about, output, "23_about_version.png", width=760, height=520))

        current_year = adapter.current_school_year()
        if current_year is None:
            raise RuntimeError("Synthetisches aktuelles Schuljahr fehlt.")
        adapter.save_student_documentation_subjects(
            STUDENT_ID,
            current_year.school_year_id,
            "custom",
            ("deutsch", "mathematik", "englisch"),
        )
        subject_selection = _profile_screen(adapter)
        subject_selection.resize(1400, 900)
        subject_selection.show()
        QApplication.processEvents()
        subject_selection._set_documentation_subjects_expanded(True)
        QApplication.processEvents()
        overview_scroll = subject_selection.profile_tabs.widget(0)
        if not isinstance(overview_scroll, QScrollArea):
            raise RuntimeError("Synthetischer Profilbereich ist nicht scrollbar.")
        subject_card = subject_selection.findChild(
            QWidget,
            "StudentProfileDocumentationSubjectsCard",
        )
        if subject_card is None:
            raise RuntimeError("Karte für Dokumentationsfächer fehlt.")
        overview_scroll.ensureWidgetVisible(subject_card, 24, 24)
        QApplication.processEvents()
        captured.append(
            _capture(
                subject_selection,
                output,
                "25_student_subject_selection.png",
            )
        )

    expected = {
        "01_dashboard.png",
        "02_observation_dialog.png",
        "04_student_profile_overview.png",
        "05_student_profile_competency_development.png",
        "06_learning_report_workspace.png",
        "10_report_read_only_revision.png",
        "11_learning_conference_preparation.png",
        "13_timetable_settings.png",
        "14_master_data.png",
        "15_anmeldung.png",
        "16_passwortanlage.png",
        "17_sicherheit_touch_id.png",
        "18_bericht_entwurf_auswahl.png",
        "19_leg_entwurf_auswahl.png",
        "20_backup.png",
        "21_restore_vorschau.png",
        "22_restore_neustart.png",
        "23_about_version.png",
        "24_first_steps.png",
        "25_student_subject_selection.png",
        "26_lesson_time_templates.png",
        "27_combined_subjects.png",
        "28_homeroom_session.png",
        "29_week_rules.png",
        "30_subject_plants.png",
    }
    actual = {path.name for path in captured}
    if actual != expected:
        raise RuntimeError(f"Screenshot-Inventar ist unvollständig: {sorted(expected - actual)}")
    return tuple(captured)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "user_manual" / "screenshots",
    )
    args = parser.parse_args()
    for path in capture(args.output):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
