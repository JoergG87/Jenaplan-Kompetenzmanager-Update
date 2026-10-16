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
import sys
import tempfile

from scripts.macos_native_acceptance import _active, _child, _keys, _provider, _parent_handoff

MODES = frozenset({"v6-seed", "v6-migrate", "v6-check", "v6-crash", "v6-matrix"})


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
        account_loader=lambda: account, product_paths=runtime_paths(root))


def _seed(profile):
    from src.core.restore_runtime import RuntimeInstanceLock
    root = Path(profile.runtime_root)
    with RuntimeInstanceLock(root):
        service = _v4_service(profile, seed=True)
        counts = _counts(service)
        required = ("students", "groups", "courses", "competencies", "observations",
            "observation_competency_ratings", "timetable_entries", "documents", "school_years")
        if any(counts.get(name, 0) <= 0 for name in required):
            raise RuntimeError("native_v6_source_fixture_incomplete")
        service.opened.documents.validate_restart()
        result = {"status": "ok", "source_schema": 4, "counts": counts,
            "installation_id": service.installation_id,
            "database_context_id": service.loaded.database_context_id,
            "dmk_fingerprint": service.loaded.dmk_fingerprint_sha256,
            "database_key_fingerprint": service.loaded.database_key_fingerprint_sha256}
        _record(profile, "native-v6-source.json", result)
        return result


def _migrate(profile):
    from src.security.transactional_timetable_migration import SyntheticTimetableMigration
    service = _v4_service(profile)
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
    result = {"status": "ok", "target": asdict(identity), "counts": counts,
        "full_original_row_verification": True, "document_binding": True,
        "keys_preserved": True, "backup_sha256": target.container_sha256,
        "independent_backup_verification": True, "ready_state": stage.state,
        "v4_backup_rejected_as_v6": True, "manual_ui_performed": False}
    _record(profile, "native-v6-check.json", result)
    return result


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
    child("v6-migrate")
    child("v6-check")
    restart = child("restart")
    runtime = restart["payload"].get("runtime") or {}
    if (runtime.get("final_v4") != 6 or runtime.get("first_run") is not False
            or runtime.get("login_authenticated") is not True):
        raise RuntimeError("native_v6_normal_login_not_proven")
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
        "v6-check": _check, "v6-crash": _crash, "v6-matrix": _matrix}[mode](profile)
