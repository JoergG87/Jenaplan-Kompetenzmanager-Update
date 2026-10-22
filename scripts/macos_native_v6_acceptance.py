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
    "v6-subject-plants", "v6-functions", "v6-functions-reopen", "v6-negatives", "v6-migration-fault", "v6-migration-inspect"})


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
    # Reject a damaged source before the mutable normal V4 runtime can read
    # WAL-mode metadata. execute() independently repeats full source validation.
    from src.security.final_v4_sqlcipher_runtime import KeyedFinalV4CompatibilityInspector
    with closing(_provider().connect_read_only(runtime_paths(root).final_v4_database,
            key_material=_loaded.database_key.key_material)) as connection:
        KeyedFinalV4CompatibilityInspector().inspect_connection(connection)
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
    with RuntimeInstanceLock(root) as lock:
        _finalize(profile, lock)
    result = {"status": "ok", "target": asdict(identity), "boundaries": boundaries,
        "backup": str(migration.backup), "process_must_exit": True}
    _record(profile, "native-v6-migration.json", result)
    # execute deliberately leaves all old adapters frozen. This mode terminates
    # immediately; no resumed V4 object is used after commit.
    return result


def _check(profile):
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.desktop_app.runtime import runtime_paths
    from src.security.final_v4_backup_runtime import (
        build_final_v4_restore_verifier, FinalV4EncryptedBackupError,
    )
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
            _finalize(profile, lock)
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
            except FinalV4EncryptedBackupError as error:
                if error.code != "backup_manifest_entry_missing":
                    raise
            else:
                raise RuntimeError("native_v6_historical_v4_backup_accepted")
            historical_backup = verifier.verify(historical)
            historical_ready = verifier.restore_staging(historical,
                root.parent / "native-v4-historical-ready")
            try:
                independent.verify_restore_ready(historical_ready.staging_root,
                    expected_container_sha256=historical_backup.container_sha256)
            except FinalV4EncryptedBackupError as error:
                if error.code != "restore_ready_invalid":
                    raise
            else:
                raise RuntimeError("native_v6_historical_v4_ready_accepted")
        _finalize(profile, lock)
    result = {"status": "ok", "target": asdict(identity), "counts": counts,
        "full_original_row_verification": True, "document_binding": True,
        "keys_preserved": True, "backup_sha256": target.container_sha256,
        "independent_backup_verification": True, "ready_state": stage.state,
        "v4_backup_rejected_as_v6": True, "v4_ready_rejected_as_v6": True,
        "v4_backup_rejection_code": "backup_manifest_entry_missing",
        "v4_ready_rejection_code": "restore_ready_invalid",
        "manual_ui_performed": False}
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
                feature_backup = service.create(root.parent / "native-v6-features-qualified.jkmebackup")
                facts["feature_backup_sha256"] = feature_backup.container_sha256
                _record(profile,"native-v6-functions.json",facts)
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
    shutil.copytree(Path(profile.runtime_root), Path(profile.runtime_root).parent / "native-v4-baseline")
    child("v6-migrate")
    child("v6-check")
    restart = child("restart")
    runtime = restart["payload"].get("runtime") or {}
    if (runtime.get("final_v4") != 6 or runtime.get("first_run") is not False
            or runtime.get("login_authenticated") is not True):
        raise RuntimeError("native_v6_normal_login_not_proven")
    result["negative_startups"] = _negative_startups(profile)
    child("restart")
    result["native_features"] = child("v6-functions")
    child("restart")
    result["native_feature_persistence"] = child("v6-functions-reopen")
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
    baseline = service.verify(Path(profile.runtime_root).parent / "native-v6-features-qualified.jkmebackup")
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
    result["native_feature_post_restore_persistence"] = child("v6-functions-reopen")
    result.update(status="native_v6_automated_gates_passed",
        full_post_restore_domain_and_documents=True, full_post_restore_typed_row_equality=True,
        open_gates=["human_ui_acceptance", "remaining_startup_matrix_cases",
            "packaged_migration_failure_matrix", "separate_production_migration_release",
            "production_signing_notarization_update"])
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


def _migration_fault(profile):
    """Closed fault-injection cases in a real frozen maintenance process."""
    import errno
    control = json.loads((Path(profile.runtime_root).parent / "native-migration-fault.json").read_text())
    boundary, kind = control["boundary"], control["kind"]
    if boundary not in {"source_verified", "backup_verified", "parent_copied", "before_commit", "after_commit"} or kind not in {"sigkill", "sql_error", "enospc"}:
        raise RuntimeError("native_migration_fault_invalid")
    from src.security.transactional_timetable_migration import SyntheticTimetableMigration
    root = Path(profile.runtime_root)
    service = _v4_service(profile)
    from src.core.restore_runtime import RuntimeInstanceLock
    with RuntimeInstanceLock(root) as lock:
        _finalize(profile, lock)
    migration = SyntheticTimetableMigration(service)
    reached = False
    def fault(point):
        nonlocal reached
        if point != boundary: return
        reached = True
        _record(profile, "native-migration-fault-reached.json", {"boundary": point, "kind": kind, "pid": os.getpid()})
        if kind == "sigkill": os.kill(os.getpid(), signal.SIGKILL)
        if kind == "enospc": raise OSError(errno.ENOSPC, "injected native maintenance write failure")
        # Inject invalid SQL into the actual active main transaction, without
        # replacing any provider/connection/guard. No frame values are logged.
        frame = sys._getframe(1)
        while frame is not None:
            if (frame.f_code.co_name == "execute"
                    and frame.f_code.co_filename.endswith("transactional_schema_migration.py")
                    and "connection" in frame.f_locals):
                frame.f_locals["connection"].execute("SELECT * FROM deliberately_absent_native_fault_table")
            frame = frame.f_back
        raise RuntimeError("native_migration_sql_connection_not_found")
    migration._fault_hook = fault
    try:
        migration.execute()
    except Exception as error:
        if not reached:
            raise RuntimeError("native_migration_fault_not_reached") from None
        return {"status": "injected_failure", "boundary": boundary, "kind": kind,
            "error_class": type(error).__name__, "errno": getattr(error, "errno", None)}
    raise RuntimeError("native_migration_fault_not_reached")


def _migration_inspect(profile):
    from src.desktop_app.runtime import runtime_paths
    from src.security.final_v4_backup_runtime import build_final_v4_restore_verifier
    from src.security.transactional_timetable_migration import SyntheticTimetableMigration
    root = Path(profile.runtime_root)
    account, loaded = _keys(root)
    service = build_final_v4_restore_verifier(runtime_root=root, loaded_keys=loaded,
        installation_id=account.installation_id, product_paths=runtime_paths(root))
    identity = SyntheticTimetableMigration(service).inspect_restart()
    return {"status": "ok", "identity": asdict(identity), "fresh_process": True}


def _migration_failures(profile, account, loaded):
    """Forensic test oracle retains pre-fault keys in memory, never app authority.

    The ordinary cold startup must stay blocked. Only the existing explicit
    synthetic transaction inspector may prove full old/new content, using the
    already authenticated test context, its independently verified backup and
    SQLite's own hot-journal recovery under the existing real instance lock.
    """
    import hashlib
    from src.desktop_app.runtime import runtime_paths
    from src.security.final_v4_backup_runtime import build_final_v4_restore_verifier
    from src.security.transactional_timetable_migration import SyntheticTimetableMigration
    root = Path(profile.runtime_root)
    executable = Path(sys.executable)
    archive = root.parent / "native-migration-campaign-states"
    archive.mkdir(mode=0o700)
    source = root.parent / "native-v4-baseline"
    def preserve(name):
        destination = archive / name; destination.mkdir(mode=0o700)
        for path in root.iterdir():
            if path.name != ".jkm-runtime-root-v1": path.rename(destination / path.name)
        return destination
    def populate():
        for path in source.iterdir():
            if path.name == ".jkm-runtime-root-v1": continue
            if path.is_dir(): shutil.copytree(path, root / path.name)
            else: shutil.copy2(path, root / path.name)
    def protected():
        return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file() and (
                str(path.relative_to(root)).startswith(("security/", "security-key-runtime-v1/"))
                and not path.name.endswith(("-wal", "-shm"))
                or path.name == "documents-v1.sqlcipher" or path.suffix == ".jkmedoc")}
    original = preserve("original-v6")
    result = {"cases": {}, "enospc_is_injected": True, "diagnostic_grants_no_app_admission": True}
    try:
        for boundary, kind, version in (("parent_copied", "sql_error", 4),
                ("before_commit", "enospc", 4), ("before_commit", "sigkill", 4),
                ("after_commit", "sigkill", 6)):
            populate(); name = kind + "-" + boundary
            before = protected()
            control = root.parent / "native-migration-fault.json"
            control.write_text(json.dumps({"kind": kind, "boundary": boundary}))
            failed = _child(profile, executable, "v6-migration-fault")
            point = json.loads((root.parent / "native-migration-fault-reached.json").read_text())
            snapshot = _snapshot(root)
            stopped = _child(profile, executable, "restart")
            held = stopped["returncode"] == 3 and snapshot == _snapshot(root)
            service = build_final_v4_restore_verifier(runtime_root=root, loaded_keys=loaded,
                installation_id=account.installation_id, product_paths=runtime_paths(root))
            identity = SyntheticTimetableMigration(service).inspect_restart()
            injected = (failed["returncode"] == -signal.SIGKILL if kind == "sigkill" else
                failed["payload"].get("status") == "injected_failure")
            if kind == "sql_error": injected &= failed["payload"].get("error_class") == "OperationalError"
            if kind == "enospc": injected &= failed["payload"].get("errno") == 28
            metadata_wals = [path for path in root.rglob("*-wal") if path.parent.name in {"security", "security-key-runtime-v1"}]
            wal_empty = all(path.stat().st_size == 0 for path in metadata_wals)
            passed = (injected and held and point["kind"] == kind and point["boundary"] == boundary
                and identity.schema_version == version and before == protected() and wal_empty)
            result["cases"][name] = {"passed": bool(passed), "fault": failed,
                "reached": point, "cold_start": stopped, "cold_start_unchanged": held,
                "full_independent_typed_content_inspection": asdict(identity),
                "protected_bytes_equal": before == protected(), "metadata_wals_empty": wal_empty,
                "metadata_wal_sizes": {str(path.relative_to(root)): path.stat().st_size for path in metadata_wals}}
            if version == 6:
                backup = root / "schema-upgrade-source/transaction-timetable-v1/source.jkmebackup"
                saved = archive / "missing-source.jkmebackup"; backup.rename(saved)
                snapshot = _snapshot(root)
                try:
                    SyntheticTimetableMigration(service).inspect_restart()
                except Exception as error:
                    result["cases"]["missing_backup"] = {"passed": snapshot == _snapshot(root),
                        "error_class": type(error).__name__, "unchanged": snapshot == _snapshot(root)}
                else: result["cases"]["missing_backup"] = {"passed": False}
                saved.rename(backup)
                main = service.paths.final_v4.database; raw = main.read_bytes()
                main.write_bytes(b"corrupt!" + raw[8:]); snapshot = _snapshot(root)
                try:
                    SyntheticTimetableMigration(service).inspect_restart()
                except Exception as error:
                    result["cases"]["target_integrity"] = {"passed": snapshot == _snapshot(root),
                        "error_class": type(error).__name__, "unchanged": snapshot == _snapshot(root)}
                else: result["cases"]["target_integrity"] = {"passed": False}
                main.write_bytes(raw)
            preserve(name)
            _record(profile, "native-migration-negatives.json", result)
        populate()
        main = root / "final-v4-sqlcipher-runtime-v1/final-v4.sqlcipher"
        main.write_bytes(b"corrupt!" + main.read_bytes()[8:])
        before = _snapshot(root)
        rejected = _child(profile, executable, "v6-migrate")
        result["cases"]["corrupt_v4_source"] = {"result": rejected,
            "passed": rejected["returncode"] != 0 and before == _snapshot(root),
            "unchanged": before == _snapshot(root)}
        preserve("corrupt-v4-source")
    finally:
        if any(path.name != ".jkm-runtime-root-v1" for path in root.iterdir()):
            preserve("preserved-on-exception")
        for path in original.iterdir(): path.rename(root / path.name)
    result["status"] = "passed" if all(case["passed"] for case in result["cases"].values()) else "failed"
    _record(profile, "native-migration-negatives.json", result)
    return result


def _negatives(profile):
    """Real frozen app starts; only this sealed synthetic installation is a fixture."""
    import hashlib
    import sqlite3
    from uuid import uuid4
    from scripts.macos_native_acceptance import _restricted_key, _delete_restricted_key
    from src.security.infrastructure.data_master_key_store import build_platform_data_master_key_store
    from src.security.internal_test_v6_composition import build_internal_test_v6_backup_service
    from src.core.restore_runtime import RuntimeInstanceLock
    root = Path(profile.runtime_root)
    executable = Path(sys.executable)
    account, loaded = _keys(root)
    service = build_internal_test_v6_backup_service(root)
    store = build_platform_data_master_key_store()
    result = {"status": "running", "cases": {}, "manual_ui_performed": False}
    key_changed = False
    with tempfile.TemporaryDirectory(prefix="native-v6-negative-", dir=root.parent) as temporary:
        baseline = Path(temporary) / "baseline"
        shutil.copytree(root, baseline)
        known = set(_snapshot(root))
        generated = {"schema-upgrade-foundation", "schema-upgrade-foundation/journal.json",
            "security/security.sqlite-wal", "security/security.sqlite-shm"}
        def reset():
            if set(_snapshot(root)) - known - generated:
                raise RuntimeError("native_negative_unknown_artifacts_preserved")
            for entry in root.iterdir():
                if entry.name == ".jkm-runtime-root-v1": continue
                if entry.is_dir(): shutil.rmtree(entry)
                else: entry.unlink()
            for entry in baseline.iterdir():
                if entry.name == ".jkm-runtime-root-v1": continue
                if entry.is_dir(): shutil.copytree(entry, root / entry.name)
                else: shutil.copy2(entry, root / entry.name)
        def evidence(): return _snapshot(root)
        def startup(name, mutate, *, denied=False):
            reset()
            nonlocal key_changed
            key_changed = False
            held = None
            try:
                _, held = mutate()
                before = evidence()
                value = _child(profile, executable, "restart-denied" if denied else "restart")
                after = evidence()
                events = value["payload"].get("events", [])
                passed = (value["returncode"] == 3 and value["payload"].get("status") == "blocked"
                    and value["payload"].get("exit_code") == 3 and isinstance(value["payload"].get("pid"), int)
                    and "upgrade_startup.py:before_lock" in events and before == after
                    and not any(e in events for e in ("startup.py:build_security_runtime",
                        "data_master_key_store.py:create", "data_master_key_store.py:delete")))
                result["cases"][name] = dict(value, passed=passed, installation_unchanged=before == after,
                    stopped_before_authentication="startup.py:build_security_runtime" not in events)
                _record(profile, "native-v6-negatives.json", result)
            finally:
                if held is not None:
                    held.terminate(); held.wait(timeout=15)
                if key_changed:
                    if denied: _delete_restricted_key(profile, loaded.dmk_key_id)
                    else: store.delete(installation_id=account.installation_id, key_id=loaded.dmk_key_id)
                    store.create(installation_id=account.installation_id, key_id=loaded.dmk_key_id,
                        key_material=loaded.dmk.key_material)
                    restored = store.read(installation_id=account.installation_id, key_id=loaded.dmk_key_id)
                    if restored.key_material != loaded.dmk.key_material:
                        raise RuntimeError("native_negative_key_restore_failed")
                reset()
        def damage(path):
            def apply():
                path.write_bytes(b"corrupt encrypted fixture")
                return False, None
            return apply
        startup("corrupt_main", damage(service.paths.final_v4.database))
        startup("corrupt_companion", damage(service.paths.database))
        startup("corrupt_document", damage(next((root / "final-v4-sqlcipher-runtime-v1/document-containers-v1/storage").glob("*.jkmedoc"))))
        startup("corrupt_historical_source", damage(root / "schema-upgrade-source/transaction-timetable-v1/source.jkmebackup"))
        def schema():
            with closing(_provider().connect(service.paths.final_v4.database, create=False,
                    key_material=loaded.database_key.key_material)) as connection:
                connection.execute("PRAGMA user_version=99"); connection.commit()
            return False, None
        startup("unknown_schema_identity", schema)
        def key(kind):
            def apply():
                nonlocal key_changed
                key_changed = True
                store.delete(installation_id=account.installation_id, key_id=loaded.dmk_key_id)
                if kind == "wrong":
                    store.create(installation_id=account.installation_id, key_id=loaded.dmk_key_id, key_material=os.urandom(32))
                elif kind == "denied":
                    import ctypes
                    from src.security.data_keys import DataMasterKeyStoreStatus
                    _restricted_key(profile, loaded)
                    security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
                    security.SecKeychainSetUserInteractionAllowed.argtypes = [ctypes.c_ubyte]
                    if security.SecKeychainSetUserInteractionAllowed(False) != 0:
                        raise RuntimeError("native_negative_interaction_gate_failed")
                    try:
                        denied_read = store.read(installation_id=account.installation_id, key_id=loaded.dmk_key_id)
                        if denied_read.status is not DataMasterKeyStoreStatus.ACCESS_DENIED:
                            raise RuntimeError("native_negative_denial_not_proven")
                        result["active_item_denial"] = denied_read.status.value
                    finally:
                        security.SecKeychainSetUserInteractionAllowed(True)
                return True, None
            return apply
        startup("missing_active_dmk", key("missing"))
        startup("wrong_active_dmk", key("wrong"))
        startup("denied_active_dmk", key("denied"), denied=True)
        def partial_upgrade():
            path = root / "schema-upgrade-foundation"; path.mkdir(mode=0o700)
            (path / "journal.json").write_text("{}"); (path / "journal.json").chmod(0o600)
            return False, None
        startup("incomplete_upgrade", partial_upgrade)
        state = next(root.glob("restore-transactions/*/current-state.json"))
        startup("incomplete_restore", damage(state))
        def hold():
            process = subprocess.Popen([str(executable), "--internal-native-test", "hold-lock"], stdout=subprocess.PIPE, text=True)
            if not select.select([process.stdout], [], [], 20)[0] or process.stdout.readline().strip() != "locked":
                process.terminate(); process.wait(timeout=15)
                raise RuntimeError("native_negative_lock_not_ready")
            return False, process
        startup("concurrent_app", hold)
        reset()
        _, held = hold()
        try:
            before = evidence()
            worker = subprocess.run([str(executable), "--restore-worker", "--handoff",
                str(next(root.glob("restore-handoffs/*.consumed.json"))),
                "--nonce=" + str(uuid4()), "--restore-mode", "synthetic_v6_encrypted"],
                capture_output=True, text=True, timeout=30)
            result["cases"]["concurrent_worker"] = {"returncode": worker.returncode,
                "stderr": worker.stderr, "installation_unchanged": before == evidence(),
                "passed": worker.returncode == 20 and before == evidence()}
        finally:
            held.terminate(); held.wait(timeout=15)
            reset()
        def installation():
            database = root / "security/security.sqlite"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("PRAGMA foreign_keys=OFF")
                foreign = str(uuid4())
                for (table,) in connection.execute("SELECT name FROM sqlite_schema WHERE type='table'").fetchall():
                    if any(row[1] == "installation_id" for row in connection.execute('PRAGMA table_info("'+table+'")')):
                        connection.execute('UPDATE "'+table+'" SET installation_id=?', (foreign,))
                connection.commit(); connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            # Close the fixture connection before startup; empty SQLite sidecars
            # belong only to this explicit fixture, never to runtime repair.
            for suffix in ("-wal", "-shm"):
                path = Path(str(database) + suffix)
                if path.exists(): path.unlink()
            return False, None
        startup("foreign_installation", installation)
        reset()
        from src.desktop_app.runtime import runtime_paths
        from src.security.cipher_product_runtime import CipherProductRuntimeScope
        from src.security.final_v4_sqlcipher_runtime import FinalV4SQLCipherRuntimeCoordinator, FinalV4SQLCipherRuntimeError
        before = evidence()
        with RuntimeInstanceLock(root):
            try:
                FinalV4SQLCipherRuntimeCoordinator(paths=service.paths.final_v4,
                    account_loader=lambda: account, authentication_confirmed=True,
                    technical_first_run_confirmed=False, loaded_keys=loaded,
                    sqlcipher_provider=_provider(), scope=CipherProductRuntimeScope(runtime_paths(root))).open()
            except FinalV4SQLCipherRuntimeError as error:
                result["cases"]["v4_runtime_against_v6"] = {"passed": before == evidence()
                    and error.operation.value == "inspect_database", "error_code": error.code,
                    "operation": error.operation.value, "installation_unchanged": before == evidence()}
            else:
                result["cases"]["v4_runtime_against_v6"] = {"passed": False}
        reset()
        backup = root.parent / "native-v6-features-qualified.jkmebackup"
        verified = service.verify(backup)
        stage = service.restore_staging(backup, Path(temporary) / "fresh-ready").staging_root
        expected_hash = verified.container_sha256
        service.verify_restore_ready(stage, expected_container_sha256=expected_hash)
        result["ready_positive_control"] = True
        ready = stage / "RESTORE_READY"
        original_ready = ready.read_bytes()
        from src.security.final_v4_backup_runtime import canonical_json
        foreign = json.loads(original_ready); foreign["installation_id"] = str(uuid4())
        historical = json.loads(original_ready); historical["ready_version"] = 1
        manifest = stage / "synthetic-v6-backup-manifest-v1.json"
        for name, path, payload in (
                ("tampered_ready", ready, b"{}"),
                ("foreign_ready", ready, canonical_json(foreign)),
                ("historical_ready", ready, canonical_json(historical)),
                ("tampered_manifest", manifest, b"{}")):
            original = path.read_bytes(); path.write_bytes(payload); before = evidence()
            try:
                service.verify_restore_ready(stage, expected_container_sha256=expected_hash)
            except Exception as error:
                from src.security.final_v4_backup_runtime import FinalV4EncryptedBackupError
                result["cases"][name] = {"passed": before == evidence() and isinstance(error, FinalV4EncryptedBackupError),
                    "error_code": getattr(error, "code", None), "installation_unchanged": before == evidence(), "frozen_verifier": True}
            else:
                result["cases"][name] = {"passed": False, "unexpected_acceptance": True}
            finally:
                path.write_bytes(original)
        reset()
        result["migration_failures"] = _migration_failures(profile, account, loaded)
        control = _child(profile, executable, "restart")
        result["positive_control"] = control
        result["status"] = ("passed" if all(v["passed"] for v in result["cases"].values())
            and result["migration_failures"]["status"] == "passed"
            and control["returncode"] == 0 and control["payload"].get("runtime", {}).get("first_run") is False else "failed")
        _record(profile, "native-v6-negatives.json", result)
    return result


def _subject_plants(profile):
    """Read the actual synthetic V6 profile and render only the requested chips."""
    from datetime import date
    from PySide6.QtWidgets import QApplication, QLabel
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
    from src.desktop_app.screens.student_profile_screen import StudentProfileScreen
    from src.desktop_app.theme import apply_app_theme
    from src.desktop_app.view_models.observation_view_model import subject_development_stage
    from src.security.internal_test_v6_composition import (
        build_internal_test_v6_backup_service, open_internal_test_v6_runtime,
    )
    app = QApplication.instance() or QApplication([])
    apply_app_theme(app)
    root = Path(profile.runtime_root)
    result = {"status": "ok", "students": [], "manual_ui_performed": False}
    with RuntimeInstanceLock(root) as lock:
        service = build_internal_test_v6_backup_service(root)
        with open_internal_test_v6_runtime(service, lock=lock) as product:
            adapter = StudentDesktopAdapter(database=product.runtime.database,
                database_create_allowed=False, today_provider=lambda: date(2026,10,22),
                managed_document_store=product.runtime.documents)
            students = adapter.list_students()[:3]
            if len(students) != 3:
                raise RuntimeError("native_subject_plant_fixture_missing")
            for student in students:
                bundle = adapter.student_profile_projection_bundle(student.student_id)
                overview = adapter.report_overview_for_student(student.student_id)
                screen = StudentProfileScreen()
                screen.set_student(bundle.student, observations=bundle.observations,
                    competency_cockpit=bundle.competency_cockpit, report_overview=overview)
                screen.profile_tabs.setCurrentIndex(3)
                screen.resize(1680,1050); screen.show(); app.processEvents()
                screen._report_subjects_expanded = True
                screen._render_report_subjects(overview); app.processEvents()
                if screen.subjects_card.geometry().intersects(screen.history_card.geometry()):
                    raise RuntimeError("native_subject_plant_history_overlap")
                plants = screen.findChildren(QLabel, "ReportOverviewSubjectPlant")
                expected = {item.subject_id: subject_development_stage(item)
                            for item in bundle.competency_cockpit.subjects}
                if len(plants) != len(overview.subject_documentation):
                    raise RuntimeError("native_subject_plant_missing_chip")
                for plant in plants:
                    stage = expected.get(plant.property("subject_id"))
                    if plant.property("development_stage") != stage:
                        raise RuntimeError("native_subject_plant_wrong_stage")
                    if stage is not None and plant.pixmap().isNull():
                        raise RuntimeError("native_subject_plant_missing_asset")
                screenshot = root.parent / ("subject-plants-" + student.student_id + ".png")
                if not screen.subjects_card.grab().save(str(screenshot)):
                    raise RuntimeError("native_subject_plant_screenshot_failed")
                result["students"].append({"student_id": student.student_id,
                    "screen_width": screen.width(), "columns": screen._report_overview_columns,
                    "subjects_rect": screen.subjects_card.geometry().getRect(),
                    "history_rect": screen.history_card.geometry().getRect(),
                    "chips": len(plants), "stages": {p.property("subject_id"): p.property("development_stage") for p in plants},
                    "screenshot": str(screenshot)})
                screen.close(); app.processEvents()
        _finalize(profile, lock)
    _record(profile, "native-subject-plants.json", result)
    return result


def run_frozen(mode):
    profile = _active(mode)
    if mode not in MODES:
        raise RuntimeError("native_v6_mode_invalid")
    return {"v6-subject-plants": _subject_plants, "v6-seed": _seed, "v6-migrate": _migrate,
        "v6-check": _check, "v6-crash": _crash, "v6-matrix": _matrix,
        "v6-migration-fault": _migration_fault, "v6-migration-inspect": _migration_inspect,
        "v6-negatives": _negatives, "v6-functions": _functions,
        "v6-functions-reopen": lambda value: _functions(value,reopen=True)}[mode](profile)
