"""Native sealed-package V6 qualification using existing runtime boundaries.

Every migration, login and worker executes in a fresh frozen process. No source
authority, plaintext database, crypto replacement, or human acceptance claim.
"""
from contextlib import closing
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import signal
import select
import subprocess
import sys
import tempfile

from scripts.macos_native_acceptance import _active, _child, _keys, _provider, _parent_handoff, _snapshot

MODES = frozenset({"v6-seed", "v6-migrate", "v6-check", "v6-crash", "v6-matrix",
    "v6-functions", "v6-functions-reopen"})


def _record(profile, name, payload):
    path = Path(profile.runtime_root).parent / name
    path.write_text(json.dumps(payload, sort_keys=True, indent=2))
    path.chmod(0o600)


def _counts(service):
    result = {}
    with closing(service._provider.connect_read_only(service.paths.final_v4.database,
            key_material=service.loaded.database_key.key_material)) as connection:
        for (table,) in connection.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name"):
            quoted = '"' + table.replace('"', '""') + '"'
            result[table] = connection.execute(f"SELECT count(*) FROM {quoted}").fetchone()[0]
    return result


def _finalize(profile, lock):
    from src.desktop_app.runtime import runtime_paths
    from src.security.startup import build_security_runtime, finalize_security_runtime
    paths = runtime_paths(Path(profile.runtime_root))
    finalize_security_runtime(build_security_runtime(paths), paths, lock)


def _v4_service(profile, *, seed=False):
    from src.desktop_app.runtime import runtime_paths
    from src.security.cipher_product_runtime import open_cipher_product_runtime
    from src.security.final_v4_backup_runtime import build_final_v4_encrypted_backup_service
    root = Path(profile.runtime_root)
    account, _loaded = _keys(root)
    opened = open_cipher_product_runtime(paths=runtime_paths(root), account_loader=lambda: account,
        authentication_confirmed=True, first_run_allowed=False)
    if seed:
        from scripts.seed_test_data import seed_cipher_pilot_test_data
        seed_cipher_pilot_test_data(opened, source_root=root)
    return build_final_v4_encrypted_backup_service(opened_runtime=opened.runtime,
        account_loader=lambda: account, environ=os.environ, product_paths=runtime_paths(root))


def _seed(profile):
    from src.core.restore_runtime import RuntimeInstanceLock
    root = Path(profile.runtime_root)
    with RuntimeInstanceLock(root) as lock:
        service = _v4_service(profile, seed=True)
        counts = _counts(service)
        required = ("students", "groups", "courses", "competencies", "observations",
            "observation_competency_ratings", "timetable_entries", "documents", "school_years")
        if any(counts.get(name, 0) <= 0 for name in required):
            raise RuntimeError("native_v6_source_fixture_incomplete")
        service.opened.documents.validate_restart()
        from src.security.startup import build_security_runtime, finalize_security_runtime
        from src.desktop_app.runtime import runtime_paths
        paths = runtime_paths(root)
        finalize_security_runtime(build_security_runtime(paths), paths, lock)
        result = {"status": "ok", "source_schema": 4, "counts": counts,
            "installation_id": service.installation_id,
            "database_context_id": service.loaded.database_context_id,
            "dmk_fingerprint": service.loaded.dmk_fingerprint_sha256,
            "database_key_fingerprint": service.loaded.database_key_fingerprint_sha256}
        _record(profile, "native-v6-source.json", result)
        return result


def _migrate(profile):
    from src.security.transactional_timetable_migration import SyntheticTimetableMigration
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.desktop_app.runtime import runtime_paths
    from src.security.startup import build_security_runtime, finalize_security_runtime
    root = Path(profile.runtime_root)
    with RuntimeInstanceLock(root) as lock:
        service = _v4_service(profile)
        paths = runtime_paths(root)
        finalize_security_runtime(build_security_runtime(paths), paths, lock)
    source = json.loads((Path(profile.runtime_root).parent / "native-v6-source.json").read_text())
    if _counts(service) != source["counts"]:
        raise RuntimeError("native_v6_source_changed")
    boundaries = []
    migration = SyntheticTimetableMigration(service, fault_hook=boundaries.append)
    identity = migration.execute()
    result = {"status": "ok", "target": asdict(identity), "boundaries": boundaries,
        "backup": str(migration.backup), "process_must_exit": True}
    _record(profile, "native-v6-migration.json", result)
    # execute deliberately leaves all old adapters frozen. This mode terminates
    # immediately; no resumed V4 object is used after commit.
    return result


def _check(profile):
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.desktop_app.runtime import runtime_paths
    from src.security.final_v4_backup_runtime import build_final_v4_restore_verifier
    from src.security.transactional_timetable_migration import SyntheticTimetableMigration
    from src.security.internal_test_v6_composition import (
        build_internal_test_v6_backup_service, open_internal_test_v6_runtime,
        InternalTestStartupGuard,
    )
    from src.core.timetable_schema import SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION
    root = Path(profile.runtime_root)
    source = json.loads((root.parent / "native-v6-source.json").read_text())
    account, loaded = _keys(root)
    # Fresh-process independent migration inspection verifies every original
    # typed row, companion, encrypted document and retained source backup.
    verifier = build_final_v4_restore_verifier(runtime_root=root, loaded_keys=loaded,
        installation_id=account.installation_id, product_paths=runtime_paths(root))
    identity = SyntheticTimetableMigration(verifier).inspect_restart()
    if identity != SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity:
        raise RuntimeError("native_v6_target_identity_invalid")
    service = build_internal_test_v6_backup_service(root, authenticated_account=account)
    counts = _counts(service)
    if any(counts.get(table) != count for table, count in source["counts"].items()):
        raise RuntimeError("native_v6_historical_counts_changed")
    if (loaded.dmk_fingerprint_sha256 != source["dmk_fingerprint"]
            or loaded.database_key_fingerprint_sha256 != source["database_key_fingerprint"]
            or loaded.database_context_id != source["database_context_id"]):
        raise RuntimeError("native_v6_keys_changed")
    with RuntimeInstanceLock(root) as lock:
        InternalTestStartupGuard(lock).evaluate()
        with open_internal_test_v6_runtime(service, lock=lock) as opened:
            opened.runtime.lesson_time_templates.set_times(1, "07:45", "08:30")
            suggestion = opened.runtime.lesson_time_templates.suggest(1)
            if (suggestion.start_time, suggestion.end_time) != ("07:45", "08:30"):
                raise RuntimeError("native_v6_template_persistence_failed")
            opened.documents.validate_restart()
            target = service.create(root.parent / "native-v6-qualified.jkmebackup")
            independent = build_internal_test_v6_backup_service(root)
            verified = independent.verify(target.path)
            if verified != target:
                raise RuntimeError("native_v6_backup_independent_verification_failed")
            stage = independent.restore_staging(target.path, root.parent / "native-v6-independent-stage")
            independent.verify_restore_ready(stage.staging_root,
                expected_container_sha256=target.container_sha256)
            # The historic V4 source remains readable through V4 authority but
            # can never be accepted as a V6 target backup.
            historical = root / "schema-upgrade-source/transaction-timetable-v1/source.jkmebackup"
            try:
                independent.verify(historical)
            except Exception:
                pass
            else:
                raise RuntimeError("native_v6_historical_v4_backup_accepted")
        _finalize(profile, lock)
    result = {"status": "ok", "target": asdict(identity), "counts": counts,
        "full_original_row_verification": True, "document_binding": True,
        "keys_preserved": True, "backup_sha256": target.container_sha256,
        "independent_backup_verification": True, "ready_state": stage.state,
        "v4_backup_rejected_as_v6": True, "manual_ui_performed": False}
    _record(profile, "native-v6-check.json", result)
    return result


def _functions(profile, *, reopen=False):
    from datetime import datetime
    from PySide6.QtCore import Qt, QTime, QTimer
    from PySide6.QtWidgets import QApplication, QInputDialog
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
    from src.desktop_app.adapters.lesson_time_templates_desktop_adapter import LessonTimeTemplatesDesktopAdapter
    from src.desktop_app.dialogs.timetable_entry_dialog import TimetableEntryDialog
    from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog
    from src.desktop_app.runtime import runtime_paths
    from src.desktop_app.shell import AppShell
    from src.desktop_app.theme import apply_app_theme
    from src.security.internal_test_v6_composition import (
        build_internal_test_v6_backup_service, open_internal_test_v6_runtime, InternalTestStartupGuard,
    )
    root = Path(profile.runtime_root)
    proof = root.parent / "native-v6-functions.json"
    app = QApplication.instance() or QApplication([])
    apply_app_theme(app)
    captures = root.parent / "native-v6-ui"
    captures.mkdir(mode=0o700, exist_ok=True)
    def require(condition, code):
        if not condition:
            raise RuntimeError("native_v6_functions_" + code)
    with RuntimeInstanceLock(root) as lock:
        InternalTestStartupGuard(lock).evaluate()
        service = build_internal_test_v6_backup_service(root)
        with open_internal_test_v6_runtime(service, lock=lock) as product:
            opened = product.runtime
            def rows(table):
                with closing(opened.database._connection_provider.connect_read_only(opened.database.path)) as connection:
                    return tuple(tuple(row) for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY 1,2'))
            if reopen:
                facts = json.loads(proof.read_text())
                with closing(opened.database.connect()) as connection:
                    for entry_id, kind, start, end, subjects in facts["entries"]:
                        row = connection.execute("SELECT entry_kind,start_time,end_time,active FROM timetable_entries WHERE timetable_entry_id=? AND deleted_at=''", (entry_id,)).fetchone()
                        require(tuple(row) == (kind,start,end,1), "reopened_entry")
                        links = tuple(row[0] for row in connection.execute("SELECT subject_id FROM timetable_entry_subjects WHERE timetable_entry_id=? ORDER BY subject_id", (entry_id,)))
                        require(links == tuple(subjects), "reopened_subjects")
                    found = connection.execute("SELECT subject_id FROM observations WHERE note=?", (facts["observation_note"],)).fetchall()
                    require(len(found) == 1 and found[0][0] == "mathematik", "reopened_single_observation")
                require([list(row) for row in rows("observation_competency_ratings")] == facts["ratings_before"], "reopened_ratings")
                template = opened.lesson_time_templates.suggest(2)
                require((template.start_time,template.end_time) == ("09:05","09:50"), "reopened_template")
                result = dict(status="ok", fresh_process_persistence=True, manual_ui_performed=False)
            else:
                instant = datetime(2026,10,16,8,0)
                student_adapter = StudentDesktopAdapter(database=opened.database, database_create_allowed=False,
                    today_provider=lambda: instant.date(), now_provider=lambda: instant,
                    managed_document_store=opened.documents)
                shell = AppShell(opened.database.path, student_adapter=student_adapter, paths=runtime_paths(root),
                    now_provider=lambda: instant, backup_restore_available=False,
                    lesson_time_templates_adapter=LessonTimeTemplatesDesktopAdapter(opened))
                shell.resize(1180,760); shell.show(); app.processEvents()
                ratings_before = rows("observation_competency_ratings")
                observations_before = len(rows("observations"))
                old_entries = rows("timetable_entries")
                editor = shell.settings_screen.lesson_time_templates_editor
                editor.lesson_number.setValue(2)
                editor.start_time.setTime(QTime(9,0)); editor.end_time.setTime(QTime(8,0))
                editor.save_button.click(); app.processEvents()
                require(not any(v.lesson_number == 2 for v in shell.lesson_time_templates_adapter.view_model().templates), "invalid_times_accepted")
                editor.start_time.setTime(QTime(7,0)); editor.end_time.setTime(QTime(7,45))
                editor.save_button.click(); app.processEvents()
                templates = shell.lesson_time_templates_adapter.view_model().templates
                require(any(v.lesson_number == 2 and v.start_time == "07:00" for v in templates), "template_save")
                created = []
                for weekday, kind in ((4,"subject_lesson"),(5,"homeroom_session")):
                    dialog = TimetableEntryDialog(shell.timetable_adapter.week_view_model(), weekday=weekday, templates=templates)
                    dialog.entry_kind_combo.setCurrentIndex(dialog.entry_kind_combo.findData(kind))
                    if kind == "subject_lesson":
                        selected = []
                        for index in range(dialog.subject_list.count()):
                            item = dialog.subject_list.item(index)
                            wanted = item.data(Qt.ItemDataRole.UserRole) in {"deutsch","mathematik"}
                            item.setCheckState(Qt.CheckState.Checked if wanted else Qt.CheckState.Unchecked)
                            if wanted: selected.append(item.data(Qt.ItemDataRole.UserRole))
                        require(set(selected) == {"deutsch","mathematik"}, "required_subjects_missing")
                    else:
                        require(not dialog.subject_list.isEnabled(), "homeroom_subject_enabled")
                    dialog.lesson_template_combo.setCurrentIndex(next(i+1 for i,v in enumerate(templates) if v.lesson_number == 2))
                    dialog.apply_template_button.click()
                    require(dialog.start_time.time().toString("HH:mm") == "07:00", "time_suggestion")
                    if kind == "subject_lesson":
                        dialog.start_time.setTime(QTime(7,5)); dialog.end_time.setTime(QTime(7,50))
                    room = "Nativer V6-Test " + kind
                    dialog.room_input.setText(room)
                    dialog.show(); app.processEvents(); dialog.grab().save(str(captures / (kind + ".png")))
                    require(shell._save_timetable_dialog(dialog), "entry_save")
                    dialog.close()
                    matches = [entry for day in shell.timetable_adapter.week_view_model().days for entry in day.entries if entry.room == room]
                    require(len(matches) == 1, "duplicate_parent")
                    created.append(matches[0])
                combined, homeroom = created
                for entry in created:
                    dialog = TimetableEntryDialog(shell.timetable_adapter.week_view_model(), weekday=entry.weekday, entry=entry, templates=templates)
                    dialog.room_input.setText(entry.room + " bearbeitet")
                    require(shell._save_timetable_dialog(dialog), "entry_edit")
                    dialog.close()
                require(not shell.timetable_adapter.set_entry_active(homeroom.timetable_entry_id,False).active, "deactivation")
                require(shell.timetable_adapter.set_entry_active(homeroom.timetable_entry_id,True).active, "reactivation")
                disposable = TimetableEntryDialog(shell.timetable_adapter.week_view_model(), weekday=3, templates=templates)
                disposable.entry_kind_combo.setCurrentIndex(disposable.entry_kind_combo.findData("homeroom_session"))
                disposable.start_time.setTime(QTime(7,0)); disposable.end_time.setTime(QTime(7,45))
                disposable.room_input.setText("Nativer V6-Löschtest")
                require(shell._save_timetable_dialog(disposable), "disposable_homeroom_save")
                disposable.close()
                delete_target = next(entry for day in shell.timetable_adapter.week_view_model().days
                    for entry in day.entries if entry.room == "Nativer V6-Löschtest")
                shell.timetable_adapter.delete_entry(delete_target.timetable_entry_id)
                require(shell.timetable_adapter.repository.get_entry(delete_target.timetable_entry_id) is None, "homeroom_delete")
                template = next(v.template for v in templates if v.lesson_number == 2)
                shell.save_lesson_time_template(2,"09:05","09:50",template)
                for old in old_entries:
                    require(old in rows("timetable_entries"), "existing_entries_changed")
                require(shell.timetable_adapter.repository.get_entry(combined.timetable_entry_id).start_time == "07:05", "individual_time_changed")
                require(shell.timetable_adapter.repository.get_entry(homeroom.timetable_entry_id).start_time == "07:00", "copied_time_changed")
                callbacks = []
                def choose_math():
                    chooser = next((w for w in QApplication.topLevelWidgets() if isinstance(w,QInputDialog) and w.isVisible()),None)
                    if chooser is None:
                        callbacks.append("chooser_missing"); return
                    callbacks.append(chooser.textValue())
                    chooser.setTextValue("Mathematik")
                    chooser.grab().save(str(captures / "explicit_subject.png")); chooser.accept()
                QTimer.singleShot(0,choose_math)
                shell.dashboard_screen._emit_observation(combined)
                require(callbacks == ["Bitte Fach wählen"] and shell.pending_observation_subject_id == "mathematik", "explicit_subject_choice")
                student_id = next(student_id for (student_id,) in (
                    (row[0],) for row in rows("students")) if any(option.subject_key == "mathematik"
                    for option in shell.adapter.list_observation_subject_options(student_id)))
                note = "Synthetische native V6-Einzelbeobachtung"
                saved = []
                def save_observation():
                    dialog = next((w for w in QApplication.topLevelWidgets() if isinstance(w,NewObservationDialog) and w.isVisible()),None)
                    if dialog is None:
                        saved.append(False); return
                    group = dialog._current_subject_group()
                    valid = dialog.subject_select.currentData() == "mathematik" and group is not None and group.subject_key == "mathematik"
                    dialog.quick_observation_checkbox.setChecked(True); dialog.note_input.setPlainText(note)
                    dialog.grab().save(str(captures / "single_observation.png"))
                    dialog.save_draft(); saved.append(valid and dialog.has_saved_observation)
                    if not dialog.has_saved_observation: dialog.reject()
                QTimer.singleShot(0,save_observation)
                shell.open_quick_observation_dialog(student_id)
                require(saved == [True], "single_observation_save")
                require(len(rows("observations")) == observations_before+1, "observation_count")
                require(rows("observation_competency_ratings") == ratings_before, "duplicate_rating")
                with closing(opened.database.connect()) as connection:
                    observed = connection.execute("SELECT subject_id FROM observations WHERE note=?", (note,)).fetchall()
                    require(len(observed) == 1 and observed[0][0] == "mathematik", "one_math_observation")
                shell._clear_pending_timetable_observation()
                def cancel_homeroom():
                    chooser = next((w for w in QApplication.topLevelWidgets() if isinstance(w,QInputDialog) and w.isVisible()),None)
                    if chooser is not None: chooser.reject()
                QTimer.singleShot(0,cancel_homeroom)
                shell.dashboard_screen._emit_observation(homeroom)
                require(not shell.pending_observation_subject_id, "homeroom_implicit_subject")
                with closing(opened.database.connect()) as connection:
                    links = connection.execute("SELECT subject_id FROM timetable_entry_subjects WHERE timetable_entry_id=? ORDER BY subject_id", (combined.timetable_entry_id,)).fetchall()
                    require(tuple(row[0] for row in links) == ("deutsch","mathematik"), "combined_links")
                    require(connection.execute("SELECT count(*) FROM timetable_entry_subjects WHERE timetable_entry_id=?", (homeroom.timetable_entry_id,)).fetchone()[0] == 0, "homeroom_links")
                facts = {"status":"ok", "entries":[[e.timetable_entry_id,e.entry_kind,e.start_time,e.end_time,sorted(e.subject_ids)] for e in created],
                    "ratings_before":[list(row) for row in ratings_before], "observation_note":note,
                    "tool_assisted_native_ui":True, "manual_ui_performed":False,
                    "checks":["template_invalid_rejected","template_created_and_changed","suggested_times_copied","individual_times_preserved",
                        "historical_entries_preserved","homeroom_crud_and_reactivation","one_combined_parent_two_links",
                        "explicit_observation_subject","one_observation_no_rating_duplication","existing_ratings_preserved"]}
                _record(profile,"native-v6-functions.json",facts)
                shell.grab().save(str(captures / "appshell.png")); shell.close(); app.processEvents()
                result = facts
        _finalize(profile,lock)
    return result



def _negative_startups(profile):
    """Alter only this newly generated fixture; every rejected start stays inert."""
    root = Path(profile.runtime_root)
    executable = Path(sys.executable)
    report = {}
    journal = next((root / "final-v4-sqlcipher-runtime-v1/.observation-staging").glob("*/journal.json"))
    main = root / "final-v4-sqlcipher-runtime-v1/final-v4.sqlcipher"
    for kind in ("unknown", "damaged_journal", "missing_main"):
        unknown = root / "native-unknown-fixture"
        saved = root.parent / "native-main-fixture-held"
        original = journal.read_bytes()
        try:
            if kind == "unknown":
                unknown.write_bytes(b"unknown synthetic fixture"); unknown.chmod(0o600)
            elif kind == "damaged_journal":
                journal.write_bytes(original + b"invalid")
            else:
                if saved.exists():
                    raise RuntimeError("native_v6_fixture_destination_exists")
                main.rename(saved)
            before = _snapshot(root)
            observed = _child(profile, executable, "restart", timeout=120)
            if observed["returncode"] != 3 or _snapshot(root) != before:
                raise RuntimeError("native_v6_negative_start_failed_" + kind)
            if "data_master_key_store.py:create" in observed.get("payload", {}).get("events", []):
                raise RuntimeError("native_v6_negative_start_created_key")
            report[kind] = observed
        finally:
            if kind == "unknown" and unknown.exists(): unknown.unlink()
            elif kind == "damaged_journal": journal.write_bytes(original)
            elif kind == "missing_main" and saved.exists(): saved.rename(main)
    held = subprocess.Popen([str(executable), "--internal-native-test", "hold-lock"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        ready, _, _ = select.select([held.stdout], [], [], 15)
        if not ready or held.stdout.readline().strip() != b"locked":
            raise RuntimeError("native_v6_lock_fixture_not_ready")
        observed = _child(profile, executable, "restart", timeout=120)
        if observed["returncode"] != 3:
            raise RuntimeError("native_v6_competing_process_accepted")
        report["competing_process"] = observed
    finally:
        held.terminate(); held.communicate(timeout=15)
    report["keychain_and_provider"] = _child(profile, executable, "existing-keys", timeout=120)
    if report["keychain_and_provider"]["returncode"] != 0:
        raise RuntimeError("native_v6_keychain_provider_check_failed")
    return report


def _matrix(profile):
    executable = Path(sys.executable)
    result = {"status": "running", "steps": {}, "manual_ui_performed": False}
    def child(mode):
        observed = _child(profile, executable, mode, timeout=240)
        result["steps"][mode] = observed
        _record(profile, "native-v6-matrix.json", result)
        if observed["returncode"] != 0:
            raise RuntimeError("native_v6_child_failed_" + mode)
        return observed
    root = Path(profile.runtime_root)
    if (root / "security/security.sqlite").exists():
        existing = child("restart")
        if existing["payload"].get("runtime", {}).get("final_v4") != 4:
            raise RuntimeError("native_v6_matrix_requires_fresh_v4_source")
    else:
        child("initialize")
    child("v6-seed")
    seeded = child("restart")["payload"].get("runtime") or {}
    if seeded.get("final_v4") != 4 or seeded.get("first_run") is not False or seeded.get("student_count") != 24:
        raise RuntimeError("native_v6_seeded_v4_normal_restart_failed")
    child("v6-migrate")
    child("v6-check")
    restart = child("restart")
    runtime = restart["payload"].get("runtime") or {}
    if (runtime.get("final_v4") != 6 or runtime.get("first_run") is not False
            or runtime.get("login_authenticated") is not True):
        raise RuntimeError("native_v6_normal_login_not_proven")
    result["negative_startups"] = _negative_startups(profile)
    child("restart")
    # Isolate the destructive crash fixture using the existing synthetic-only
    # matrix pattern: copy the tool-owned baseline, retain the root/marker inode,
    # and restore that exact baseline before the independent successful case.
    from src.security.internal_test_v6_composition import build_internal_test_v6_backup_service
    from src.core.database_content_evidence import database_content_evidence, require_same_content
    def live_content():
        service = build_internal_test_v6_backup_service(root)
        values = []
        for path in (service.paths.final_v4.database, service.paths.database):
            with closing(service._provider.connect_read_only(path,
                    key_material=service.loaded.database_key.key_material)) as connection:
                values.append(database_content_evidence(connection))
        return tuple(values)
    expected_content = live_content()
    with tempfile.TemporaryDirectory(prefix="native-v6-crash-baseline-", dir=root.parent) as temp:
        baseline_root = Path(temp) / "baseline"
        shutil.copytree(root, baseline_root)
        child("restore-ready")
        killed = _child(profile, executable, "v6-crash", timeout=120)
        result["steps"]["v6-crash"] = killed
        _record(profile, "native-v6-matrix.json", result)
        if killed["returncode"] != -signal.SIGKILL:
            raise RuntimeError("native_v6_restore_crash_not_proven")
        child("restart")
        for expected, actual in zip(expected_content, live_content()):
            require_same_content(expected, actual)
        result["packaged_restore_crash_recovery"] = {"boundary": "between_main_and_companion",
            "real_sigkill": True, "full_main_companion_equality": True}
        for entry in root.iterdir():
            if entry.name == ".jkm-runtime-root-v1":
                continue
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        for entry in baseline_root.iterdir():
            if entry.name == ".jkm-runtime-root-v1":
                continue
            if entry.is_dir():
                shutil.copytree(entry, root / entry.name)
            else:
                shutil.copy2(entry, root / entry.name)
    result["parent_worker_restart_handoff"] = _parent_handoff(profile)
    child("restart")
    # A second independent full V6 snapshot must remain verifiable after real
    # worker replacement and the actual restarted app's keyed handshake.
    service = build_internal_test_v6_backup_service(Path(profile.runtime_root))
    baseline = service.verify(Path(profile.runtime_root).parent / "native-v6-qualified.jkmebackup")
    service.verify_live_runtime(Path(profile.runtime_root), manifest=baseline.manifest,
        enforce_artifact_hashes=False)
    with service.verified_snapshot(baseline.path) as snapshot:
        with closing(service._provider.connect_read_only(snapshot.database_path,
                key_material=service.loaded.database_key.key_material)) as before:
            expected_main = database_content_evidence(before)
        with closing(service._provider.connect_read_only(snapshot.companion_path,
                key_material=service.loaded.database_key.key_material)) as before:
            expected_companion = database_content_evidence(before)
    with closing(service._provider.connect_read_only(service.paths.final_v4.database,
            key_material=service.loaded.database_key.key_material)) as after:
        require_same_content(expected_main, database_content_evidence(after))
    with closing(service._provider.connect_read_only(service.paths.database,
            key_material=service.loaded.database_key.key_material)) as after:
        require_same_content(expected_companion, database_content_evidence(after))
    result["native_features"] = child("v6-functions")
    child("restart")
    result["native_feature_persistence"] = child("v6-functions-reopen")
    result.update(status="native_v6_automated_gates_passed",
        full_post_restore_domain_and_documents=True, full_post_restore_typed_row_equality=True,
        open_gates=["human_ui_acceptance", "separate_production_migration_release"])
    _record(profile, "native-v6-matrix.json", result)
    return result


def _crash(profile):
    from src.desktop_app.restore_worker import run, RESTORE_MODE_SYNTHETIC_V6_ENCRYPTED
    root = Path(profile.runtime_root)
    handoff, = (root / "restore-handoffs").glob("*.json")
    nonce = json.loads(handoff.read_text())["nonce"]
    def factory(runtime_root):
        # run() already holds and validates the real process lock. Compose the
        # real V6 service; only the OS process-death boundary is injected.
        from src.security.internal_test_v6_composition import build_internal_test_v6_backup_service
        from src.security.synthetic_v6_live_restore import SyntheticV6EncryptedLiveRestoreService
        service = SyntheticV6EncryptedLiveRestoreService(build_internal_test_v6_backup_service(runtime_root))
        def fault(boundary):
            if boundary == "between_main_and_companion":
                os.kill(os.getpid(), signal.SIGKILL)
        service._fault_hook = fault
        return service
    run(["--handoff", str(handoff), "--nonce=" + nonce,
        "--restore-mode", RESTORE_MODE_SYNTHETIC_V6_ENCRYPTED], encrypted_service_factory=factory)
    raise RuntimeError("native_v6_restore_crash_unexpected_survival")


def run_frozen(mode):
    profile = _active(mode)
    if mode not in MODES:
        raise RuntimeError("native_v6_mode_invalid")
    return {"v6-seed": _seed, "v6-migrate": _migrate,
        "v6-check": _check, "v6-crash": _crash, "v6-matrix": _matrix,
        "v6-functions": _functions,
        "v6-functions-reopen": lambda value: _functions(value,reopen=True)}[mode](profile)
