"""Focused A/B rules and real SQLCipher migration/runtime/backup integration."""
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import os
import uuid

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest

from src.core.timetable_weeks import TimetableWeekCycle, iso_week_monday
from src.core.timetable import TimetableEntry, TimetableValidator, TimetableValidationError, build_timetable_projection
from src.core.timetable_weeks_schema import SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION as TARGET
from tests.test_timetable_consumers_v6 import _run_process, _seed_appshell_case


def entry(pattern="all", **kwargs):
    values = dict(timetable_entry_id="TTE-1", weekday=1, start_time="08:00", end_time="08:45",
        subject_id="de", target_type="group", target_id="g", room="", active=True,
        sort_order=0, created_at="", updated_at="", week_pattern=pattern)
    values.update(kwargs)
    return TimetableEntry(**values)


@pytest.mark.parametrize("kind", ["A", "B"])
def test_cycle_reference_both_directions_kw53_and_holidays(kind):
    cycle = TimetableWeekCycle(date(2020, 12, 30), kind)
    assert cycle.reference_monday == date(2020, 12, 28)
    opposite = "B" if kind == "A" else "A"
    # KW 53 -> KW 1 changes despite both having odd week numbers.
    for offset in range(-60, 61):
        day = cycle.reference_monday + timedelta(weeks=offset, days=3)
        assert cycle.assignment(day).effective_kind == (kind if offset % 2 == 0 else opposite)
    assert cycle.assignment(date(2021, 1, 4)).effective_kind == opposite
    assert cycle.assignment(date(2020, 12, 21)).effective_kind == opposite
    # No holiday input exists: Christmas and summer weeks count normally.
    assert cycle.assignment(date(2021, 8, 2)).effective_kind == opposite


def test_single_override_never_rephases_following_week():
    cycle = TimetableWeekCycle(date(2026, 10, 26), "A")
    overrides = ((date(2026, 11, 9), "B"),)
    assert cycle.assignment(date(2026, 11, 9), overrides).manual
    assert cycle.assignment(date(2026, 11, 9), overrides).effective_kind == "B"
    assert cycle.assignment(date(2026, 11, 16), overrides).effective_kind == "B"
    assert cycle.assignment(date(2026, 11, 9)).effective_kind == "A"


@pytest.mark.parametrize("left,right,conflict", [("all","A",True),("all","B",True),("A","A",True),("B","B",True),("A","B",False)])
def test_overlap_respects_shared_validity(left, right, conflict):
    args = dict(valid_subject_ids=("de",), valid_target_ids={"group": ("g",)},
                existing_entries=(entry(right, timetable_entry_id="TTE-2"),))
    if conflict:
        with pytest.raises(TimetableValidationError): TimetableValidator().validate(entry(left), **args)
    else:
        TimetableValidator().validate(entry(left), **args)


def test_projection_searches_next_week_and_all_lessons():
    cycle = TimetableWeekCycle(date(2020, 12, 28), "A")
    lessons = (entry("A"), entry("B", timetable_entry_id="TTE-2"),
               entry("all", timetable_entry_id="TTE-3", start_time="09:00", end_time="09:45"))
    kinds = lambda value: cycle.assignment(value).effective_kind
    result = build_timetable_projection(lessons, datetime(2020, 12, 28, 8, 5), kinds)
    assert result.current.entry.week_pattern == "A"
    assert [o.entry.week_pattern for o in result.today] == ["A", "all"]
    result = build_timetable_projection(lessons, datetime(2021, 1, 1, 12), kinds)
    assert result.next.occurrence_date == date(2021, 1, 4)
    assert result.next.entry.week_pattern == "B"


def service(paths, loaded, installation, version=7):
    from tests.test_transactional_schema_migration import _inspection_service
    from src.security.final_v3_document_runtime import FinalV3DocumentRuntime
    from src.security.synthetic_v7_backup_runtime import SyntheticV7EncryptedBackupService
    from src.security.synthetic_v6_backup_runtime import SyntheticV6EncryptedBackupService
    from src.security.synthetic_v7_runtime import KeyedSyntheticV7CompatibilityInspector
    from src.security.synthetic_v6_runtime import KeyedSyntheticV6CompatibilityInspector
    from src.security.internal_test_v6_composition import _ExistingV6MainFactory
    old = _inspection_service(paths, loaded, installation)
    inspector = KeyedSyntheticV7CompatibilityInspector if version == 7 else KeyedSyntheticV6CompatibilityInspector
    documents = FinalV3DocumentRuntime(paths=paths, factory=old._document_factory,
        loaded_keys=loaded, installation_id=installation, source_root=None,
        random_source=old._random, clock=old._clock)
    opened = SimpleNamespace(documents=documents, installation_id=installation,
        database_context_id=loaded.database_context_id, final_v4=SimpleNamespace(compatibility=None))
    cls = SyntheticV7EncryptedBackupService if version == 7 else SyntheticV6EncryptedBackupService
    return cls(opened_runtime=opened, paths=paths, loaded_keys=loaded,
        main_factory=_ExistingV6MainFactory(old._provider, paths.final_v4.database, loaded.database_key.key_material, inspector),
        document_factory=old._document_factory, provider=old._provider, maintenance_gate=old._gate,
        random_source=old._random, clock=old._clock)


def _migration_worker(directory, source, paths, loaded, installation, fail, channel):
    try:
        from tests.test_transactional_schema_migration import _seed_case, _protected
        from src.security.transactional_timetable_weeks_migration import SyntheticTimetableWeeksMigration
        if source == 4:
            _, current = _seed_case(Path(directory))
        else:
            current = service(paths, loaded, installation, 6)
            with closing(current._main_factory.connect(paths.final_v4.database)) as c:
                c.execute("INSERT INTO timetable_entry_subjects SELECT 'TTE-SYNTHETIC',subject_id FROM competencies WHERE subject_id='SUB-SYN-MATH'")
                c.commit()
        protected = _protected(current)
        migration = SyntheticTimetableWeeksMigration(current)
        if fail:
            def fault(boundary):
                if boundary == "before_commit": raise RuntimeError("injected SQLCipher transaction failure")
            migration._fault_hook = fault
            with pytest.raises(RuntimeError, match="injected"): migration.execute()
        else:
            assert migration.execute() == TARGET.identity
        assert _protected(current) == protected
        assert not current.paths.final_v4.database.read_bytes().startswith(b"SQLite format 3")
        channel.send(("ok", current.paths, current.loaded, current.installation_id))
    except BaseException:
        import traceback
        channel.send(("error", traceback.format_exc()))
    finally:
        channel.close()


@pytest.fixture(params=[4, 6])
def migrated(tmp_path, request):
    source = request.param
    paths = loaded = installation = None
    if source == 6:
        _, paths, loaded, installation = _run_process(_seed_appshell_case, (tmp_path,))
    _, paths, loaded, installation = _run_process(_migration_worker,
        (str(tmp_path), source, paths, loaded, installation, False))
    return paths, loaded, installation, source


def _runtime_worker(paths, loaded, installation, source, channel):
    try:
        from src.security.transactional_timetable_weeks_migration import SyntheticTimetableWeeksMigration
        from src.security.synthetic_v7_runtime import SyntheticV7Runtime
        from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
        from src.desktop_app.dialogs.timetable_entry_dialog import TimetableEntryDialog
        from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
        from src.desktop_app.adapters.lesson_time_templates_desktop_adapter import LessonTimeTemplatesDesktopAdapter
        from src.desktop_app.shell import AppShell
        from src.desktop_app.runtime import runtime_paths
        from src.core.schema_registry import PRODUCT_SCHEMA_REGISTRY, FINAL_V4_SCHEMA_REGISTRATION
        from src.core.database_content_evidence import database_content_evidence
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QDate
        from src.desktop_app.theme import apply_app_theme
        current = service(paths, loaded, installation)
        from tests.test_transactional_schema_migration import _inspection_service
        source_service = _inspection_service(paths, loaded, installation) if source == 4 else service(paths, loaded, installation, 6)
        assert SyntheticTimetableWeeksMigration(source_service).inspect_restart() == TARGET.identity
        assert PRODUCT_SCHEMA_REGISTRY.schemas == (FINAL_V4_SCHEMA_REGISTRATION,)
        app = QApplication.instance() or QApplication([]); apply_app_theme(app)
        instant = datetime(2026,10,26,9,15)
        with SyntheticV7Runtime(current).open_existing() as opened:
            adapter = TimetableDesktopAdapter(opened.database)
            entries = adapter.repository.list_entries()
            assert entries and all(e.week_pattern == "all" for e in entries)
            with closing(opened.database.connect()) as c:
                before = database_content_evidence(c)
            adapter.configure_week_cycle(date(2026,10,28), "A")
            original = entries[0]
            if source == 6: assert len(original.subject_ids) == 2
            from src.application.commands.timetable import SaveTimetableEntryCommand
            def command(e, pattern):
                return SaveTimetableEntryCommand(e.timetable_entry_id, e.weekday, e.start_time, e.end_time,
                    e.subject_id, e.target_type, e.target_id, e.room, e.active, e.sort_order,
                    entry_kind=e.entry_kind, subject_ids=e.subject_ids, week_pattern=pattern)
            adapter.save_entry(command(original, "A"))
            alternate = replace(original, timetable_entry_id="", week_pattern="B", room="B-Raum")
            saved_b = adapter.save_entry(command(alternate, "B"))
            home = SaveTimetableEntryCommand("",2,"08:00","08:45","","group", original.target_id,"",True,
                    entry_kind="homeroom_session",week_pattern="A")
            adapter.save_entry(home)
            adapter.save_entry(replace(home, weekday=1, start_time="10:00",end_time="11:00",week_pattern="all"))
            assert adapter.read_projection(instant).current.entry.week_pattern == "A"
            next_week = adapter.read_projection(datetime(2026,10,30,16)).next
            assert next_week.occurrence_date == date(2026,11,2) and next_week.entry.week_pattern == "B"
            adapter.set_week_override(date(2026,10,30), "B")
            adapter.set_week_override(date(2026,10,28), "B")
            assert adapter.week_assignment(instant.date()).manual
            assert adapter.read_projection(instant).current.entry.week_pattern == "B"
            assert adapter.week_assignment(date(2026,11,2)).effective_kind == "B"
            adapter.clear_week_override(date(2026,10,27))
            assert not adapter.week_assignment(instant.date()).manual
            adapter.set_week_override(date(2026,11,9), "B")
            # Actual shell signals and editor values, no persistence on preview.
            students = StudentDesktopAdapter(database=opened.database, database_create_allowed=False,
                today_provider=lambda: instant.date(), now_provider=lambda: instant, managed_document_store=opened.documents)
            shell = AppShell(student_adapter=students, backup_restore_available=False,
                paths=runtime_paths(paths.final_v4.root), now_provider=lambda: instant,
                lesson_time_templates_adapter=LessonTimeTemplatesDesktopAdapter(opened))
            shell.resize(1180,760);shell.show();app.processEvents()
            screen=shell.settings_screen
            assert not screen.timetable_week_rules.isVisible()
            screen.timetable_week_rules_toggle.click()
            assert not screen.timetable_week_rules.isHidden()
            screen.timetable_week_rules_toggle.click()
            assert screen.timetable_week_rules.isHidden()
            screen.timetable_week_date.setDate(QDate(instant.date()))
            shell.refresh_timetable_view()
            assert "A-Woche" in screen.timetable_week_status.text()
            screen.timetable_week_preview.setCurrentIndex(2); app.processEvents()
            assert {e.week_pattern for day in screen.timetable_week.days for e in day.entries} <= {"all","B"}
            assert not adapter.week_assignment(instant.date()).manual
            screen.timetable_override_requested.emit(instant.date(), "B")
            assert adapter.week_assignment(instant.date()).manual
            assert shell.dashboard_screen._hero_occurrence.entry.week_pattern == "B"
            screen.timetable_override_clear_requested.emit(instant.date())
            assert not adapter.week_assignment(instant.date()).manual
            shell.refresh_dashboard(instant)
            assert shell.dashboard_screen._hero_occurrence.entry.week_pattern == "A"
            dialog=TimetableEntryDialog(adapter.week_view_model(),weekday=1,entry=saved_b)
            assert dialog.week_pattern_combo.currentData() == "B"
            assert dialog.command().week_pattern == "B"
            shell.show_timetable_settings();app.processEvents()
            capture=paths.final_v4.root.parent / "ab-week-ui.png";shell.grab().save(str(capture))
            dialog.show();app.processEvents();dialog.grab().save(str(paths.final_v4.root.parent / "ab-editor-ui.png"));dialog.close()
            # Historical ratings, observations, report revisions and every other
            # non-timetable table remain byte-value identical.
            with closing(opened.database.connect()) as c:
                after = database_content_evidence(c)
                assert c.execute("SELECT count(*) FROM timetable_week_overrides").fetchone()[0] == 1
            ignored={"timetable_entries","timetable_entry_subjects","timetable_week_cycle","timetable_week_overrides"}
            assert tuple(t for t in before.tables if t[0] not in ignored)==tuple(t for t in after.tables if t[0] not in ignored)
            shell.close();app.processEvents()
        channel.send(("ok",))
    except BaseException:
        import traceback
        channel.send(("error", traceback.format_exc()))
    finally: channel.close()


def _reopen_worker(paths, loaded, installation, channel):
    try:
        from src.security.synthetic_v7_runtime import SyntheticV7Runtime
        from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
        with SyntheticV7Runtime(service(paths, loaded, installation)).open_existing() as opened:
            adapter = TimetableDesktopAdapter(opened.database)
            assert adapter.week_assignment(date(2026,11,9)).manual
            assert adapter.week_assignment(date(2026,11,9)).effective_kind == "B"
            assert adapter.week_assignment(date(2026,11,16)).effective_kind == "B"
            assert adapter.read_projection(datetime(2026,10,26,9,15)).current.entry.week_pattern == "A"
            assert {e.week_pattern for e in adapter.repository.list_entries()} == {"A","B","all"}
        channel.send(("ok",))
    except BaseException:
        import traceback
        channel.send(("error",traceback.format_exc()))
    finally:channel.close()


def test_migration_editor_dashboard_and_real_process_restart(migrated):
    paths,loaded,installation,source=migrated
    _run_process(_runtime_worker,(paths,loaded,installation,source))
    _run_process(_reopen_worker,(paths,loaded,installation))


@pytest.mark.parametrize("source", [4,6])
def test_transaction_rollback_retains_exact_source(tmp_path, source):
    paths=loaded=installation=None
    if source==6:
        _,paths,loaded,installation=_run_process(_seed_appshell_case,(tmp_path,))
    _,paths,loaded,installation=_run_process(_migration_worker,(str(tmp_path),source,paths,loaded,installation,True))
    from src.core.database_compatibility import DatabaseCompatibilityInspector
    current=service(paths,loaded,installation)
    with closing(current._provider.connect_read_only(paths.final_v4.database,key_material=loaded.database_key.key_material)) as c:
        assert DatabaseCompatibilityInspector().inspect_connection(c).version.sqlite_user_version == source


def _confirm_restore(paths, loaded, installation, restore_id, token, channel):
    try:
        from src.security.synthetic_v7_live_restore import confirm_synthetic_v7_restore_startup
        confirm_synthetic_v7_restore_startup(backup_service=service(paths,loaded,installation),
            runtime_root=paths.final_v4.root, restore_id=restore_id, token=token)
        channel.send(("ok",))
    except BaseException:
        import traceback
        traceback.print_exc();channel.send(("error",traceback.format_exc()))
    finally:channel.close()


def _restore_process(paths, loaded, installation, handoff, nonce, channel):
    try:
        from src.security.synthetic_v7_live_restore import SyntheticV7EncryptedLiveRestoreService
        from src.core.restore_runtime import RuntimeInstanceLock
        current=service(paths,loaded,installation)
        def restart(transaction, token, lock):
            _run_process(_confirm_restore,(paths,loaded,installation,transaction.transaction.name,token))
            return True
        with RuntimeInstanceLock(paths.final_v4.root) as lock:
            SyntheticV7EncryptedLiveRestoreService(current).execute(handoff_path=handoff,
                nonce=nonce,lock=lock,restart=restart,handshake_timeout_seconds=1)
        channel.send(("ok",))
    except BaseException:
        import traceback
        traceback.print_exc();channel.send(("error",traceback.format_exc()))
    finally:channel.close()


def test_encrypted_backup_restore_retains_week_rules_and_history(migrated, tmp_path):
    from src.security.synthetic_v7_runtime import SyntheticV7Runtime
    from src.security.synthetic_v7_backup_runtime import SyntheticV7EncryptedBackupManifestV1
    from src.security.synthetic_v6_backup_runtime import SyntheticV6EncryptedBackupManifestV1
    from src.security.final_v4_backup_runtime import FinalV4EncryptedBackupManifestV1
    from src.security.synthetic_v7_live_restore import prepare_synthetic_v7_live_restore, classify_terminal_synthetic_v7_restore_artifacts
    from src.security.final_v4_live_restore import FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.core.database_content_evidence import database_content_evidence
    from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
    paths,loaded,installation,_=migrated
    current=service(paths,loaded,installation)
    with SyntheticV7Runtime(current).open_existing() as opened:
        adapter=TimetableDesktopAdapter(opened.database)
        adapter.configure_week_cycle(date(2020,12,28),"B")
        adapter.set_week_override(date(2021,1,4),"B")
    with closing(current._main_factory.connect(paths.final_v4.database)) as c:
        before=database_content_evidence(c)
    backup=current.create(tmp_path/'ab-v7.jkmebackup')
    assert type(backup.manifest) is SyntheticV7EncryptedBackupManifestV1
    assert current.verify(backup.path)==backup
    raw=backup.path.read_bytes()
    assert b'SQLite format 3' not in raw and loaded.database_key.key_material not in raw
    for manifest in (SyntheticV6EncryptedBackupManifestV1,FinalV4EncryptedBackupManifestV1):
        with pytest.raises(Exception): manifest.from_bytes(backup.manifest.to_bytes())
    with SyntheticV7Runtime(service(paths,loaded,installation)).open_existing() as opened:
        TimetableDesktopAdapter(opened.database).clear_week_override(date(2021,1,4))
    restore_id=str(uuid.uuid4())
    parent=paths.final_v4.root/FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY
    parent.mkdir(mode=0o700)
    stage=current.restore_staging(backup.path,parent/restore_id)
    import json
    ready=json.loads(stage.ready_path.read_text())
    assert ready['ready_version']==4 and ready['database_schema_version']==7
    with RuntimeInstanceLock(paths.final_v4.root) as lock:
        prepared=prepare_synthetic_v7_live_restore(backup_service=current,lock=lock,
            staging_root=stage.staging_root,expected_container_sha256=backup.container_sha256,
            restore_id=restore_id,app_version='0.4.4',build_commit='a'*40)
    prepared.safety_backup.transfer_to_worker()
    _run_process(_restore_process,(paths,loaded,installation,prepared.handoff.path,prepared.handoff.nonce))
    restored=service(paths,loaded,installation)
    assert classify_terminal_synthetic_v7_restore_artifacts(restored)
    with closing(restored._main_factory.connect(paths.final_v4.database)) as c:
        assert database_content_evidence(c)==before
    with SyntheticV7Runtime(restored).open_existing() as opened:
        adapter=TimetableDesktopAdapter(opened.database)
        assert adapter.week_assignment(date(2021,1,4)).manual
        assert adapter.week_assignment(date(2021,1,4)).effective_kind=='B'


def test_next_lesson_past_multiple_suppressed_occurrences():
    from src.application.commands.timetable import TimetableApplicationService
    cycle=TimetableWeekCycle(date(2021,1,4),"A")
    overrides=((date(2021,1,18),"B"),(date(2021,2,1),"B"))
    repo=SimpleNamespace(list_entries=lambda:(entry("A"),))
    weeks=SimpleNamespace(snapshot=lambda:(cycle,overrides))
    application=TimetableApplicationService(None,repo,weeks)
    projection=application.projection(datetime(2021,1,4,12))
    assert projection.next.occurrence_date==date(2021,2,15)
