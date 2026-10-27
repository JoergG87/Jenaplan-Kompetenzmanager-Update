"""Focused SQLCipher widget performance and saved-state regression."""
from datetime import datetime, timedelta
from dataclasses import replace
import json
import os
from pathlib import Path
from tests.test_timetable_weeks import migrated, service
from tests.test_timetable_consumers_v6 import _run_process


def _measure_worker(paths, loaded, installation, channel):
    try:
        from PySide6.QtWidgets import QApplication
        from src.security.synthetic_v7_runtime import SyntheticV7Runtime
        from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
        from src.desktop_app.shell import AppShell
        from src.desktop_app.runtime import runtime_paths
        from scripts.timetable_week_timing import measure_week_actions
        from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
        from src.application.commands.timetable import SaveTimetableEntryCommand
        from unittest.mock import patch
        app = QApplication.instance() or QApplication([])
        instant = datetime(2026, 10, 26, 9, 15)
        with SyntheticV7Runtime(service(paths, loaded, installation)).open_existing() as opened:
            timetable = TimetableDesktopAdapter(opened.database)
            timetable.configure_week_cycle(instant.date(), "A")
            first = timetable.repository.list_entries()[0]
            command = SaveTimetableEntryCommand(first.timetable_entry_id, first.weekday, first.start_time,
                first.end_time, first.subject_id, first.target_type, first.target_id, first.room,
                first.active, first.sort_order, entry_kind=first.entry_kind, subject_ids=first.subject_ids,
                week_pattern="A")
            timetable.save_entry(command)
            timetable.save_entry(replace(command, timetable_entry_id="", week_pattern="B"))
            students = StudentDesktopAdapter(database=opened.database, database_create_allowed=False,
                today_provider=lambda: instant.date(), now_provider=lambda: instant, managed_document_store=opened.documents)
            shell = AppShell(student_adapter=students, backup_restore_available=False,
                paths=runtime_paths(paths.final_v4.root), now_provider=lambda: instant)
            shell.resize(1180, 760); shell.show(); app.processEvents()
            measurements = measure_week_actions(shell, app, instant)
            screen = shell.settings_screen
            assert screen.timetable_week.week_assignment.effective_kind == "B"
            assert screen.timetable_week.week_assignment.manual
            assert not timetable.week_assignment(instant.date() + timedelta(weeks=1)).manual
            assert timetable.week_assignment(instant.date() + timedelta(weeks=1)).effective_kind == "B"
            # A second adapter's confirmed change must appear on the next read.
            timetable.set_week_override(instant.date(), "A")
            shell.refresh_timetable_view()
            assert screen.timetable_week.week_assignment.effective_kind == "A"
            # Failed persistence must not claim success or replace saved state.
            with patch.object(shell.timetable_adapter, "set_week_override", side_effect=RuntimeError("Speicherfehler")):
                shell.set_timetable_week_override(instant.date(), "B")
            assert timetable.week_assignment(instant.date()).effective_kind == "A"
            assert "Speicherfehler" in screen.timetable_week_message.label.text()
            # Rapid confirmed commands retain the final write and fresh view.
            for kind in ("B", "A", "B"):
                shell.set_timetable_week_override(instant.date(), kind)
                assert screen.timetable_week.week_assignment.effective_kind == kind
            shell._show_screen("dashboard"); app.processEvents()
            assert shell.dashboard_screen._hero_occurrence.entry.week_pattern == "B"
            output = os.environ.get("JKM_WEEK_TIMING_OUTPUT")
            if output:
                Path(output).write_text(json.dumps(measurements, indent=2))
            shell.close(); app.processEvents()
        channel.send(("ok", measurements))
    except BaseException:
        import traceback
        channel.send(("error", traceback.format_exc()))
    finally:
        channel.close()


def test_week_action_timings(migrated):
    paths, loaded, installation, source = migrated
    result = _run_process(_measure_worker, (paths, loaded, installation))
    assert result[0] == "ok"
    for name, measured in result[1].items():
        for profile in measured["profiles"]:
            opens = next(item["calls"] for item in profile if item["file"] == "sqlite_store.py" and item["function"] == "connect")
            assert opens == (1 if name in ("preview", "navigate") else 2)
            assert not any(item["function"] == "refresh_dashboard" for item in profile)
            assert any(item["function"] == "_write" for item in profile) == (name in ("set_override", "clear_override"))
    _run_process(_reopen_saved_week, (paths, loaded, installation))


def _reopen_saved_week(paths, loaded, installation, channel):
    try:
        from src.security.synthetic_v7_runtime import SyntheticV7Runtime
        from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
        with SyntheticV7Runtime(service(paths, loaded, installation)).open_existing() as opened:
            adapter = TimetableDesktopAdapter(opened.database)
            instant = datetime(2026, 10, 26, 9, 15)
            assert adapter.week_assignment(instant.date()).effective_kind == "B"
            assert adapter.week_assignment(instant.date()).manual
            assert adapter.read_projection(instant).current.entry.week_pattern == "B"
        channel.send(("ok",))
    except BaseException:
        import traceback
        channel.send(("error", traceback.format_exc()))
    finally:
        channel.close()
