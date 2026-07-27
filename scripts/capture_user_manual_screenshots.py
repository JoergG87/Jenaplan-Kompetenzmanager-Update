"""Create current, privacy-neutral screenshots for the 0.3.0 user manual.

The generator never opens an application, pilot, or product data root.  It builds
one deterministic synthetic SQLite fixture in a temporary directory, renders
current PySide views from its projections, and deletes the temporary root after
capture.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QWidget

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
from src.desktop_app.runtime import runtime_paths
from src.desktop_app.screens.master_data_screen import MasterDataScreen
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


CAPTURE_TIME = datetime(2026, 7, 27, 10, 30, tzinfo=UTC)
STUDENT_ID = "STU-000001"


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


def _profile_screen(adapter: StudentDesktopAdapter) -> StudentProfileScreen:
    profile = adapter.get_student_profile(STUDENT_ID)
    if profile is None:
        raise RuntimeError("Synthetisches Schülerprofil fehlt.")
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
    )
    return screen


def _restore_preview() -> RestorePreviewViewModel:
    return RestorePreviewViewModel(
        created_at="27.07.2026, 10:15",
        app_version=APP_VERSION,
        compatibility_status="Kompatibel",
        students_count=24,
        observations_count=186,
        learning_report_revisions_count=3,
        learning_conference_revisions_count=2,
        managed_files_count=8,
        external_references_count=0,
        external_missing_count=0,
        archive_path=Path("/synthetisch/Jenaplan-0.3.0.jkmbackup"),
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
        database = SQLiteDatabase(paths.database)
        adapter = StudentDesktopAdapter(database=database)
        timetable = TimetableDesktopAdapter(database)
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

        dashboard = OverviewScreen()
        projection = timetable.read_projection(CAPTURE_TIME)
        occurrence = projection.current or projection.next
        if occurrence is None:
            heatmap, suggested = adapter.dashboard_documentation_refresh(at=CAPTURE_TIME)
        else:
            heatmap, suggested = adapter.dashboard_documentation_refresh(
                target_type=occurrence.entry.target_type,
                target_id=occurrence.entry.target_id,
                subject_id=occurrence.entry.subject_id,
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
            subject_options=adapter.list_observation_subject_options(),
            competency_subject_groups=adapter.list_observation_competency_subject_groups(),
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
        report_revision.workspace_navigation.set_current_key("revisions", emit=True)
        captured.append(_capture(report_revision, output, "10_report_read_only_revision.png"))

        conference_drafts = _selection_drafts(
            adapter.list_learning_conference_drafts_for_student(STUDENT_ID)
        )
        conference_selection = LearningConferenceDraftSelectionDialog(conference_drafts)
        captured.append(_capture(conference_selection, output, "19_leg_entwurf_auswahl.png", width=900, height=650))

        conference_initial = conference_drafts[0]
        conference_preparation = adapter.learning_conference_preparation_for_student(
            STUDENT_ID,
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
                created_at="27.07.2026, 10:15",
                file_name="Jenaplan-0.3.0-Beispiel.jkmbackup",
                size_bytes=4_500_000,
                verified=True,
            )
        )
        backup.show_page("backup_restore")
        captured.append(_capture(backup, output, "20_backup.png"))

        restore = SettingsScreen()
        restore.set_backup_status(
            BackupSummaryViewModel(
                created_at="27.07.2026, 10:15",
                file_name="Jenaplan-0.3.0-Beispiel.jkmbackup",
                size_bytes=4_500_000,
                verified=True,
            )
        )
        restore.show_page("backup_restore")
        restore.show_restore_preview(_restore_preview())
        captured.append(_capture(restore, output, "21_restore_vorschau.png"))

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

        timetable_screen = SettingsScreen()
        timetable_screen.set_timetable(timetable.week_view_model())
        timetable_screen.show_page("timetable")
        captured.append(_capture(timetable_screen, output, "13_timetable_settings.png"))

        master = MasterDataScreen()
        master.set_master_data(master_data.view_model())
        captured.append(_capture(master, output, "14_master_data.png"))

        about = AppInfoDialog()
        captured.append(_capture(about, output, "23_about_build_302.png", width=760, height=520))

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
        "23_about_build_302.png",
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
    if APP_VERSION != "0.3.0" or APP_BUILD_VERSION != "302":
        raise RuntimeError("Der Screenshotgenerator erwartet Version 0.3.0 / Build 302.")
    for path in capture(args.output):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
