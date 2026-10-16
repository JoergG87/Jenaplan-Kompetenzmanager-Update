"""Explicit sealed-profile Final-V4 native acceptance; never a product entry.

No crypto/Keychain/guard replacements. Child probes run the real frozen main.
Only the private synthetic root is changed; fixture keys never leave memory.
"""
from __future__ import annotations

import argparse
import ctypes
from contextlib import closing, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import select
import signal
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.core.macos_test_package_profile import (
    NATIVE_TEST_MODES, test_identity, test_build_path_identity,
    validate_internal_test_smoke_context,
)


def run_profile(app, profile_path, mode, *, timeout=180):
    """Reattest the same sealed identity before every child, without overrides."""
    from scripts.macos_package_profile import load_profile
    profile = load_profile(profile_path, before_build=False)
    executable = Path(app) / "Contents/MacOS" / profile.app_name
    if os.environ.get("JENAPLAN_APP_DATA_DIR", profile.runtime_root) != profile.runtime_root:
        raise ValueError("test_profile_invalid")
    return _child(profile, executable, mode, timeout=timeout)


def _child(profile, executable, mode, *, timeout=180):
    if test_identity() is not None:
        _active(mode)  # retain the original frozen parent/root inode authority
    validate_internal_test_smoke_context(
        profile, executable=executable, root=profile.runtime_root,
        arguments=["--internal-native-test", mode],
        expected_identity=test_build_path_identity(profile),
    )
    result = subprocess.run([str(executable), "--internal-native-test", mode],
                            capture_output=True, text=True, timeout=timeout)
    lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
    payload = json.loads(lines[-1]) if lines else {}
    return {"returncode": result.returncode, "payload": payload,
            "stdout": result.stdout, "stderr": result.stderr}


def _active(mode):
    from src.core.macos_test_package_profile import active_internal_test_smoke_root
    profile = test_identity()
    if profile is None or not getattr(sys, "frozen", False) or mode not in NATIVE_TEST_MODES:
        raise ValueError("test_profile_invalid")
    active_internal_test_smoke_root(os.environ, ["--internal-native-test", mode])
    return profile


def _snapshot(root):
    result = {}
    for path in root.rglob("*"):
        if path.name == "instance.lock": continue
        value = path.lstat()
        result[str(path.relative_to(root))] = (
            value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
            value.st_nlink, value.st_size, value.st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
        )
    return result


def _keys(root):
    from src.security.upgrade_startup import ProductStartupInventory, ExistingStartupAccountRepository
    from src.security.existing_installation_keys import ExistingInstallationKeys, ExistingInstallationKeyStatus
    account = ExistingStartupAccountRepository(root / "security/security.sqlite", None).load_bound_active_account()
    result = ExistingInstallationKeys(inventory=ProductStartupInventory()).load_existing(root, authenticated_account=account)
    if result.status is not ExistingInstallationKeyStatus.VALID or result.loaded is None:
        raise RuntimeError("native_existing_keys_" + result.status.value)
    return account, result.loaded


def _provider():
    from src.core.database_engine import SQLCipherConnectionProvider, SQLCIPHER_4_17_BINDING_VERSION, SQLCIPHER_4_17_ENGINE_VERSION
    return SQLCipherConnectionProvider(expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
                                       expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION)


def _existing_keys(profile):
    from importlib.metadata import version
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.security.infrastructure.data_master_key_store import build_platform_data_master_key_store
    from src.security.data_keys import DataMasterKeyStoreStatus
    root = Path(profile.runtime_root)
    with RuntimeInstanceLock(root):
        before = _snapshot(root)
        account, loaded = _keys(root)
        missing = build_platform_data_master_key_store().read(installation_id=account.installation_id, key_id=str(uuid4()))
        if missing.status is not DataMasterKeyStoreStatus.NOT_FOUND:
            raise RuntimeError("native_missing_key_not_rejected")
        checks = []
        for name in ("final-v4.sqlcipher", "documents-v1.sqlcipher"):
            # A fresh keyed read-only open, engine + cipher + SQLite + FK checks.
            with closing(_provider().connect_read_only(root / "final-v4-sqlcipher-runtime-v1" / name,
                                                      key_material=loaded.database_key.key_material)) as db:
                checks.append({"file": name, "cipher": db.execute("PRAGMA cipher_version").fetchone()[0],
                               "provider": db.execute("PRAGMA cipher_provider").fetchone()[0],
                               "sqlite": db.execute("SELECT sqlite_version()").fetchone()[0],
                               "cipher_integrity": db.execute("PRAGMA cipher_integrity_check").fetchall(),
                               "integrity": [tuple(r) for r in db.execute("PRAGMA integrity_check")],
                               "fk": db.execute("PRAGMA foreign_key_check").fetchall()})
                _check_integrity(checks[-1])
        if before != _snapshot(root):
            raise RuntimeError("native_existing_key_probe_mutated_root")
    return {"status": "ok", "binding": version("sqlcipher3"), "checks": checks,
            "missing_key": "not_found", "dmk": loaded.dmk_fingerprint_sha256,
            "database_key": loaded.database_key_fingerprint_sha256}


def _check_integrity(check):
    if (check["cipher"] != "4.17.0 community" or check["provider"] != "commoncrypto"
            or check["sqlite"] != "3.53.3" or check["cipher_integrity"]
            or check["integrity"] != [("ok",)] or check["fk"]):
        raise RuntimeError("native_cipher_integrity_failed")


_OBSERVED = {
    "upgrade_startup.py": {"before_lock", "inspect", "evaluate"},
    "restore_runtime.py": {"acquire"},
    "final_v4_live_restore.py": {"recover_interrupted_final_v4_restore", "confirm_final_v4_restore_startup"},
    "main.py": {"_preflight_desktop_runtime_root", "_new_database_initialization_candidate", "_isolated_packaged_smoke_session"},
    "startup.py": {"build_security_runtime"},
    "cipher_product_runtime.py": {"open_cipher_product_runtime"},
    "data_master_key_store.py": {"create", "read", "delete"},
    "existing_installation_keys.py": {"load_existing"},
}


def _startup(mode):
    # Observe function entry only. No locals, arguments, return values or keys.
    events = []
    def observe(frame, event, _arg):
        name = Path(frame.f_code.co_filename).name
        function = frame.f_code.co_name
        if event == "call" and function in _OBSERVED.get(name, ()):
            events.append(name + ":" + function)
    from src.desktop_app import main
    denied = mode == "restart-denied"
    if denied:
        # OS-level refusal of interactive ACL authorization, in this child only.
        security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        security.SecKeychainSetUserInteractionAllowed.argtypes = [ctypes.c_ubyte]
        security.SecKeychainSetUserInteractionAllowed.restype = ctypes.c_int32
        if security.SecKeychainSetUserInteractionAllowed(False) != 0:
            raise RuntimeError("native_interaction_gate_failed")
    sys.argv[:] = [sys.executable, "--packaged-smoke-test", "restart" if denied else mode]
    sys.setprofile(observe)
    output = io.StringIO()
    try:
        if mode == "restore-parent-exit":
            code = main.main()  # os._exit must publish its result before parent death.
        else:
            with redirect_stdout(output): code = main.main()
    finally:
        sys.setprofile(None)
    lines = [line for line in output.getvalue().splitlines() if line.startswith("{")]
    return code, {"status": "ok" if code == 0 else "blocked", "exit_code": code,
                  "events": events, "pid": os.getpid(), "runtime": json.loads(lines[-1]) if lines else None}


def _check_order(result, *, guard_blocked=False):
    events = result["payload"]["events"]
    restore = "final_v4_live_restore.py:recover_interrupted_final_v4_restore"
    security = "startup.py:build_security_runtime"
    cipher = "cipher_product_runtime.py:open_cipher_product_runtime"
    first = "main.py:_new_database_initialization_candidate"
    if guard_blocked:
        if any(name in events for name in (restore, security, cipher, first,
                                          "data_master_key_store.py:create", "data_master_key_store.py:delete")):
            raise RuntimeError("native_upgrade_veto_order_failed")
        return
    sequence = ["upgrade_startup.py:before_lock", "main.py:_preflight_desktop_runtime_root",
                "restore_runtime.py:acquire", "upgrade_startup.py:evaluate", "upgrade_startup.py:inspect",
                restore, "upgrade_startup.py:evaluate", first, security,
                "main.py:_isolated_packaged_smoke_session", cipher]
    cursor = 0
    try:
        for name in sequence: cursor = events.index(name, cursor) + 1
    except ValueError:
        raise RuntimeError("native_startup_order_failed") from None


def _checkpoint(profile, report):
    path = Path(profile.runtime_root).parent / "native-matrix-progress.json"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as output: json.dump(report, output, indent=2)


def _parent_handoff(profile):
    from src.core.restore_runtime import _process_start_identity, restore_transaction_paths
    result = _child(profile, Path(sys.executable), "restore-parent-exit")
    if result["returncode"] != 0 or "restore" not in result["payload"]:
        raise RuntimeError("native_parent_handoff_failed")
    restore_id = result["payload"]["restore"]["restore_id"]
    root = Path(profile.runtime_root)
    journal_path = restore_transaction_paths(root, restore_id).current_state
    deadline = time.monotonic() + 60
    journal = {}
    while time.monotonic() < deadline:
        if journal_path.exists():
            journal = json.loads(journal_path.read_text())
            if journal.get("phase") in {"completed", "rolled_back", "manual_recovery_required"}: break
        time.sleep(0.1)
    if journal.get("phase") != "completed" or journal.get("restart_handshake", {}).get("status") != "confirmed":
        raise RuntimeError("native_restart_handshake_not_confirmed")
    lock = json.loads((root / "instance.lock").read_text())
    pid = lock["pid"]
    if pid in {os.getpid(), result["payload"]["restore"]["worker_pid"]}:
        raise RuntimeError("native_restart_process_identity_failed")
    library = ctypes.CDLL("/usr/lib/libproc.dylib")
    library.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    buffer = ctypes.create_string_buffer(4096)
    if (library.proc_pidpath(pid, buffer, len(buffer)) <= 0 or buffer.value.decode() != sys.executable
            or lock["process_start_identity"] != _process_start_identity(pid)):
        raise RuntimeError("native_restart_executable_identity_failed")
    # Stop only the just-attested isolated restart; no product process lookup.
    os.kill(pid, signal.SIGTERM)
    for _ in range(100):
        if (library.proc_pidpath(pid, buffer, len(buffer)) <= 0
                or _process_start_identity(pid) != lock["process_start_identity"]): break
        time.sleep(0.1)
    else:
        raise RuntimeError("native_restart_process_did_not_end")
    worker_pid = result["payload"]["restore"]["worker_pid"]
    worker_start = result["payload"]["restore"]["worker_start_identity"]
    if worker_start is None:
        raise RuntimeError("native_worker_start_identity_missing")
    for _ in range(100):
        if (library.proc_pidpath(worker_pid, buffer, len(buffer)) <= 0
                or _process_start_identity(worker_pid) != worker_start): break
        time.sleep(0.1)
    else:
        raise RuntimeError("native_worker_process_did_not_end")
    return {"parent": result, "journal": journal, "restart_pid": pid,
            "restart_executable": sys.executable, "lock": lock, "worker_ended": True,
            "parent_ended": True, "restart_ended": True}


def _restricted_key(profile, loaded):
    """Create ONLY this synthetic DMK item with an ACL trusting /usr/bin/false.

    The real frozen startup must then receive a native Keychain denial. The
    fixture owner retains the original synthetic bytes only in memory and
    restores them in finally. No login-keychain settings or search lists change.
    """
    from src.core.macos_test_package_profile import keychain_account
    _active("matrix")
    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    sec = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
    ptr = ctypes.c_void_p
    cf.CFStringCreateWithCString.argtypes = [ptr, ctypes.c_char_p, ctypes.c_uint32]; cf.CFStringCreateWithCString.restype = ptr
    cf.CFDataCreate.argtypes = [ptr, ptr, ctypes.c_long]; cf.CFDataCreate.restype = ptr
    cf.CFArrayCreateMutable.argtypes = [ptr, ctypes.c_long, ptr]; cf.CFArrayCreateMutable.restype = ptr
    cf.CFArrayAppendValue.argtypes = [ptr, ptr]
    cf.CFDictionaryCreateMutable.argtypes = [ptr, ctypes.c_long, ptr, ptr]; cf.CFDictionaryCreateMutable.restype = ptr
    cf.CFDictionarySetValue.argtypes = [ptr, ptr, ptr]
    cf.CFRelease.argtypes = [ptr]
    sec.SecTrustedApplicationCreateFromPath.argtypes = [ctypes.c_char_p, ctypes.POINTER(ptr)]
    sec.SecAccessCreate.argtypes = [ptr, ptr, ctypes.POINTER(ptr)]
    sec.SecItemAdd.argtypes = [ptr, ptr]; sec.SecItemAdd.restype = ctypes.c_int32
    owned = []
    def own(value):
        if not value: raise RuntimeError("native_acl_allocation_failed")
        owned.append(value); return value
    def string(value): return own(cf.CFStringCreateWithCString(None, value, 0x08000100))
    def callback(name): return ctypes.addressof(ctypes.c_byte.in_dll(cf, name))
    def symbol(name): return ptr.in_dll(sec, name).value
    try:
        trusted = ptr()
        if sec.SecTrustedApplicationCreateFromPath(b"/usr/bin/false", ctypes.byref(trusted)) != 0:
            raise RuntimeError("native_acl_trust_failed")
        own(trusted.value)
        apps = own(cf.CFArrayCreateMutable(None, 0, callback("kCFTypeArrayCallBacks")))
        cf.CFArrayAppendValue(apps, trusted)
        access = ptr()
        if sec.SecAccessCreate(string(b"JKM synthetic A2 denied item"), apps, ctypes.byref(access)) != 0:
            raise RuntimeError("native_acl_create_failed")
        own(access.value)
        query = own(cf.CFDictionaryCreateMutable(None, 0, callback("kCFTypeDictionaryKeyCallBacks"), callback("kCFTypeDictionaryValueCallBacks")))
        raw = ctypes.create_string_buffer(loaded.dmk.key_material)
        data = own(cf.CFDataCreate(None, raw, len(loaded.dmk.key_material)))
        values = {"kSecClass": symbol("kSecClassGenericPassword"),
                  "kSecAttrService": string(profile.keychain_services[0].encode()),
                  "kSecAttrAccount": string(keychain_account(profile.installation_id, loaded.dmk_key_id)),
                  "kSecValueData": data, "kSecAttrAccess": access.value}
        for name, value in values.items(): cf.CFDictionarySetValue(query, symbol(name), value)
        status = sec.SecItemAdd(query, None)
        ctypes.memset(raw, 0, len(raw))
        if status != 0: raise RuntimeError("native_acl_publish_failed:" + str(status))
    finally:
        for value in reversed(owned): cf.CFRelease(value)


def _delete_restricted_key(profile, key_id):
    """Delete exactly one fixture item by native reference, without its secret.

    SecItemDelete rejected the custom fixture ACL with invalid-owner status.
    The item-reference API removes the item without changing its access policy.
    This port is sealed-test-only and never changes the product Keychain port.
    """
    from src.core.macos_test_package_profile import keychain_account
    from src.security.domain import validate_uuid4
    if profile != _active("matrix"):
        raise RuntimeError("native_acl_profile_mismatch")
    key_id = validate_uuid4(key_id)
    service = profile.keychain_services[0].encode()
    account = keychain_account(profile.installation_id, key_id)
    ptr = ctypes.c_void_p
    security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
    security.SecKeychainFindGenericPassword.argtypes = [ptr, ctypes.c_uint32, ctypes.c_char_p,
        ctypes.c_uint32, ctypes.c_char_p, ptr, ptr, ctypes.POINTER(ptr)]
    security.SecKeychainFindGenericPassword.restype = ctypes.c_int32
    security.SecKeychainItemDelete.argtypes = [ptr]
    security.SecKeychainItemDelete.restype = ctypes.c_int32
    item = ptr()
    # NULL length/data: retrieve only the reference, never the secret bytes.
    status = security.SecKeychainFindGenericPassword(None, len(service), service,
        len(account), account, None, None, ctypes.byref(item))
    if status == -25300:
        return False
    if status != 0:
        raise RuntimeError("native_acl_item_reference_failed")
    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    cf.CFRelease.argtypes = [ptr]
    try:
        if security.SecKeychainItemDelete(item) != 0:
            raise RuntimeError("native_acl_item_delete_failed")
        return True
    finally:
        cf.CFRelease(item)


def _acl_preflight(profile):
    """Prove item-local denial and cleanup before touching a matrix DMK."""
    from types import SimpleNamespace
    from src.security.infrastructure.data_master_key_store import build_platform_data_master_key_store
    from src.security.data_keys import DataMasterKeyStoreStatus
    store = build_platform_data_master_key_store()
    key_id, material = str(uuid4()), os.urandom(32)
    record = Path(profile.runtime_root).parent / f"native-acl-fixture-{key_id}.json"
    with record.open("x") as output:
        json.dump({"key_id": key_id, "service": profile.keychain_services[0],
                   "status": "pending"}, output)
    loaded = SimpleNamespace(dmk_key_id=key_id, dmk=SimpleNamespace(key_material=material))
    security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
    security.SecKeychainSetUserInteractionAllowed.argtypes = [ctypes.c_ubyte]
    security.SecKeychainGetUserInteractionAllowed.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]
    previous = ctypes.c_ubyte()
    if security.SecKeychainGetUserInteractionAllowed(ctypes.byref(previous)) != 0:
        raise RuntimeError("native_acl_interaction_state_failed")
    if security.SecKeychainSetUserInteractionAllowed(False) != 0:
        raise RuntimeError("native_acl_interaction_gate_failed")
    try:
        _restricted_key(profile, loaded)
        denied = store.read(installation_id=profile.installation_id, key_id=key_id)
        if denied.status is not DataMasterKeyStoreStatus.ACCESS_DENIED:
            raise RuntimeError("native_acl_denial_not_proven")
        if not _delete_restricted_key(profile, key_id):
            raise RuntimeError("native_acl_cleanup_not_proven")
        store.create(installation_id=profile.installation_id, key_id=key_id, key_material=material)
        restored = store.read(installation_id=profile.installation_id, key_id=key_id)
        if restored.status is not DataMasterKeyStoreStatus.SUCCESS or restored.key_material != material:
            raise RuntimeError("native_acl_same_material_not_restored")
        return {"status": "ok", "read_denied": True, "delete_succeeded": True,
                "same_material_restored": True}
    finally:
        try:
            _delete_restricted_key(profile, key_id)
            if store.read(installation_id=profile.installation_id, key_id=key_id).status is not DataMasterKeyStoreStatus.NOT_FOUND:
                raise RuntimeError("native_acl_cleanup_absence_not_proven")
            record.write_text(json.dumps({"key_id": key_id, "service": profile.keychain_services[0],
                                         "status": "cleaned"}))
        finally:
            if security.SecKeychainSetUserInteractionAllowed(previous.value) != 0:
                raise RuntimeError("native_acl_interaction_restore_failed")


def _evidence(root, account, loaded):
    """Authenticate synthetic unknown-target evidence without executing an upgrade."""
    from src.core.schema_registry import (DatabaseSchemaRegistry, FINAL_V4_SCHEMA_REGISTRATION,
        RegisteredSchemaIdentity, SchemaRegistration, SchemaUpgradeRelation, SCHEMA_FINGERPRINT_ALGORITHM)
    from src.core.schema_upgrade import (UpgradeContext, UpgradePhase, UpgradeArtifact, UpgradeEvidence,
        new_upgrade_state, advance_upgrade)
    from src.security.database_keys import derive_migration_journal_auth_key
    from src.security.infrastructure.upgrade_journal_repository import AuthenticatedUpgradeJournalRepository as Journal
    from src.security.infrastructure.upgrade_replay_anchor import UpgradeReplayAnchorRepository as Anchor
    source = FINAL_V4_SCHEMA_REGISTRATION.identity
    target = RegisteredSchemaIdentity(5, "b" * 64, SCHEMA_FINGERPRINT_ALGORITHM)
    registry = DatabaseSchemaRegistry((FINAL_V4_SCHEMA_REGISTRATION, SchemaRegistration("synthetic_only", target, frozenset())),
                                     (SchemaUpgradeRelation(source, target),))
    ctx = UpgradeContext(str(uuid4()), account.installation_id, loaded.database_context_id,
                         loaded.database_key_id, loaded.database_key_generation, loaded.dmk_key_id,
                         loaded.dmk_generation, source, target, "synthetic_transform_v1")
    state = initial = new_upgrade_state(ctx, registry)
    for phase, role in ((UpgradePhase.EXCLUSIVE, None), (UpgradePhase.SOURCE_VERIFIED, "source"),
                        (UpgradePhase.BACKUP_VERIFIED, "backup"), (UpgradePhase.STAGED, "candidate")):
        artifacts = () if role is None else (UpgradeArtifact(role, str(uuid4()), "a" * 64, 1, 2, 4096, source),)
        state = advance_upgrade(state, UpgradeEvidence(ctx, phase, artifacts), registry)
    key = derive_migration_journal_auth_key(loaded.dmk, migration_id=ctx.operation_id)
    raw = Journal._encode(state, key)
    anchor = Anchor.for_journal(state, hashlib.sha256(raw).hexdigest())
    for name, data in (("schema-upgrade-foundation/journal.json", raw),
                       ("schema-upgrade-replay/anchor.json", Anchor._encode(anchor, key))):
        path = root / name; path.parent.mkdir(mode=0o700, exist_ok=True)
        path.write_bytes(data); path.chmod(0o600)
    return Journal._encode(initial, key)


def _restore_crash(profile, boundary):
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.desktop_app.restore_worker import run
    from src.desktop_app.runtime import runtime_paths
    from src.desktop_app.final_v4_runtime_adapters import DesktopFinalV4RestartLauncher
    from src.security.final_v4_live_restore import build_final_v4_live_restore_worker_service
    root = Path(profile.runtime_root)
    handoff, = (root / "restore-handoffs").glob("*.json")
    nonce = json.loads(handoff.read_text())["nonce"]
    def factory(runtime_root):
        service = build_final_v4_live_restore_worker_service(runtime_root, restore_id=handoff.stem,
            product_paths=runtime_paths(runtime_root), restart_launcher=DesktopFinalV4RestartLauncher())
        def fault(point):
            if point == boundary:
                os.kill(os.getpid(), signal.SIGKILL)
        service._fault_hook = fault
        return service
    return run(["--handoff", str(handoff), "--nonce=" + nonce,
                "--restore-mode", "final_v4_encrypted"], encrypted_service_factory=factory)


def _matrix(profile):
    """Each fixture runs a new frozen process; restore the same root inode."""
    root = Path(profile.runtime_root)
    executable = Path(sys.executable)
    report = {"status": "running", "startup": {}, "crashes": {}, "open_gates": []}
    report["acl_preflight"] = _acl_preflight(profile)
    def child(mode):
        return _child(profile, executable, mode)
    def require(result, code=0):
        if result["returncode"] != code:
            raise RuntimeError("native_child_failed:" + json.dumps(result, ensure_ascii=True))
        return result
    initial = child("initialize")
    report["startup"]["2"] = initial
    _checkpoint(profile, report)
    if initial["returncode"] != 0:
        report.update(status="blocked", blocker="native_first_run_failed")
        return report
    _check_order(initial)
    if initial["payload"]["runtime"]["first_run"] is not True:
        raise RuntimeError("native_first_run_not_proven")
    report["keychain_sqlcipher"] = require(child("existing-keys"))
    account, loaded = _keys(root)
    from src.security.infrastructure.data_master_key_store import build_platform_data_master_key_store
    store = build_platform_data_master_key_store()
    with tempfile.TemporaryDirectory(prefix="native-baseline-", dir=root.parent) as temp:
        baseline = Path(temp) / "baseline"
        shutil.copytree(root, baseline)
        def reset():
            # The root and its marker authority never move or change identity.
            for entry in root.iterdir():
                if entry.name == ".jkm-runtime-root-v1":
                    continue
                if entry.is_dir() and not entry.is_symlink(): shutil.rmtree(entry)
                else: entry.unlink()
            for entry in baseline.iterdir():
                if entry.name == ".jkm-runtime-root-v1": continue
                if entry.is_dir(): shutil.copytree(entry, root / entry.name)
                else: shutil.copy2(entry, root / entry.name)
        for case in (1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20):
            reset()
            key_changed = False
            held = None
            try:
                if case in {4, 5, 6, 7, 8, 9, 16, 19}:
                    old = _evidence(root, account, loaded)
                    journal = root / "schema-upgrade-foundation/journal.json"
                    anchor = root / "schema-upgrade-replay/anchor.json"
                    if case == 4: anchor.unlink()
                    elif case == 5: journal.unlink()
                    elif case == 6: journal.write_bytes(journal.read_bytes() + b"x")
                    elif case == 7: anchor.write_bytes(b"corrupt")
                    elif case == 8: journal.write_bytes(old)
                    elif case == 16:
                        store.delete(installation_id=account.installation_id, key_id=loaded.dmk_key_id)
                        key_changed = True
                        store.create(installation_id=account.installation_id, key_id=loaded.dmk_key_id, key_material=os.urandom(32))
                    elif case == 19:
                        p = root / "encrypted-restore-staging" / str(uuid4()); p.mkdir(parents=True, mode=0o700)
                        p.parent.chmod(0o700)
                        (p / "RESTORE_READY").write_text("synthetic conflict"); (p / "RESTORE_READY").chmod(0o600)
                elif case in {10, 12}:
                    (root / "final-v4-sqlcipher-runtime-v1/final-v4.sqlcipher").unlink()
                    if case == 12:
                        p = root / "schema-upgrade-source/op"; p.mkdir(parents=True, mode=0o700)
                        p.parent.chmod(0o700)
                        (p / "rollback.sqlcipher").write_bytes(b"synthetic"); (p / "rollback.sqlcipher").chmod(0o600)
                elif case == 11:
                    (root / "final-v4-sqlcipher-runtime-v1/documents-v1.sqlcipher").unlink()
                elif case == 13:
                    with closing(_provider().connect(root / "final-v4-sqlcipher-runtime-v1/final-v4.sqlcipher", create=False,
                                                    key_material=loaded.database_key.key_material)) as db:
                        db.execute("PRAGMA user_version=99"); db.commit(); db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                elif case == 14:
                    store.delete(installation_id=account.installation_id, key_id=loaded.dmk_key_id); key_changed = True
                elif case == 15:
                    store.delete(installation_id=account.installation_id, key_id=loaded.dmk_key_id); key_changed = True
                    _restricted_key(profile, loaded)
                elif case == 17:
                    (root / "unsafe").symlink_to(root.parent, target_is_directory=True)
                elif case == 18:
                    held = subprocess.Popen([str(executable), "--internal-native-test", "hold-lock"], stdout=subprocess.PIPE, text=True)
                    if not select.select([held.stdout], [], [], 15)[0] or held.stdout.readline().strip() != "locked":
                        raise RuntimeError("native_lock_not_ready")
                elif case == 20:
                    require(child("restore-ready"))
                before = _snapshot(root) if case != 17 else None
                result = child("restart-denied" if case == 15 else "restart") if case != 17 else _unsafe_child(executable)
                report["startup"][str(case)] = result
                _checkpoint(profile, report)
                allowed = case in {1, 3, 20}
                require(result, 0 if allowed else (4 if case in {13, 14, 15} else (2 if case == 17 else 3)))
                if case == 15 and "data_master_key_access_denied" not in result["stderr"]:
                    raise RuntimeError("native_acl_denial_not_proven")
                if not allowed and case not in {13, 14, 15, 17, 18} and _snapshot(root) != before:
                    raise RuntimeError("native_guard_mutated_blocked_case:" + str(case))
                events = result["payload"].get("events", [])
                if not allowed and "data_master_key_store.py:create" in events:
                    raise RuntimeError("native_replacement_key_created")
                if allowed:
                    _check_order(result)
                    if result["payload"]["runtime"]["first_run"] is not False:
                        raise RuntimeError("native_unexpected_first_run")
                elif case not in {13, 14, 15, 17, 18}:
                    _check_order(result, guard_blocked=True)
            finally:
                if held is not None:
                    held.kill(); held.wait(timeout=10)
                if key_changed:
                    if case == 15:
                        _delete_restricted_key(profile, loaded.dmk_key_id)
                    else:
                        store.delete(installation_id=account.installation_id, key_id=loaded.dmk_key_id)
                    store.create(installation_id=account.installation_id, key_id=loaded.dmk_key_id, key_material=loaded.dmk.key_material)
                if case == 17: (root / "unsafe").unlink(missing_ok=True)
        reset()
        report["restore_worker"] = require(child("restore-worker"))
        reset()
        report["parent_worker_restart_handoff"] = _parent_handoff(profile)
        require(child("restart"))
        _checkpoint(profile, report)
        for boundary in ("before_swap", "between_main_and_companion", "after_databases_before_documents",
                         "during_documents", "after_swap_before_reopen", "after_reopen"):
            reset(); require(child("restore-ready"))
            killed = child("restore-crash-" + boundary)
            require(killed, -signal.SIGKILL)
            recovered = require(child("restart"))
            report["crashes"][boundary] = {"killed": killed, "recovered": recovered}
            _checkpoint(profile, report)
        reset()
        report["post_recovery_keys"] = require(child("existing-keys"))
    # The matrix does not observe UI. Its separate evidence must identify
    # tool-assisted visibility checks and any actual human review honestly.
    report["open_gates"].append("ui_visibility_checks")
    report["manual_ui_performed"] = False
    report["status"] = "automated_gates_passed"
    report["acceptance"] = "native_matrix_passed_ui_separate"
    _checkpoint(profile, report)
    return report


def _unsafe_child(executable):
    # Intentional negative fixture: preflight must reject it, frozen hook too.
    result = subprocess.run([str(executable), "--internal-native-test", "restart"],
                            capture_output=True, text=True, timeout=30)
    return {"returncode": result.returncode, "payload": {}, "stdout": result.stdout, "stderr": result.stderr}


def run_frozen(mode):
    try:
        profile = _active(mode)
        if mode.startswith("v6-"):
            from scripts.macos_native_v6_acceptance import run_frozen as run_v6
            payload = run_v6(mode); code = 0
        elif mode == "matrix":
            payload = _matrix(profile)
            code = 0 if payload["status"] == "automated_gates_passed" else 1
        elif mode == "existing-keys":
            payload = _existing_keys(profile); code = 0
        elif mode == "acl-preflight":
            payload = _acl_preflight(profile); code = 0
        elif mode == "hold-lock":
            from src.core.restore_runtime import RuntimeInstanceLock
            with RuntimeInstanceLock(Path(profile.runtime_root)):
                print("locked", flush=True)
                signal.pause()
            return 1
        elif mode.startswith("restore-crash-"):
            code = _restore_crash(profile, mode.removeprefix("restore-crash-"))
            payload = {"status": "unexpected_survival", "exit_code": code}
            code = 1
        else:
            code, payload = _startup(mode)
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True), flush=True)
        return code
    except Exception as error:
        # Exceptions never interpolate key-bearing objects or arbitrary locals.
        payload = {"status": "blocked", "error_class": type(error).__name__, "mode": mode}
        if str(error) in {"data_master_key_delete_failed", "data_master_key_access_denied", "data_master_key_already_exists"}:
            payload["error_code"] = str(error)
        if isinstance(error, RuntimeError) and str(error).startswith("native_"):
            payload["error_code"] = str(error).split(":", 1)[0]
        if mode in {"matrix", "v6-matrix"} and test_identity() is not None:
            filename = "native-v6-matrix.json" if mode == "v6-matrix" else "native-matrix-progress.json"
            path = Path(test_identity().runtime_root).parent / filename
            if path.is_file() and not path.is_symlink():
                progress = json.loads(path.read_text())
                progress.update(payload)
                if mode == "v6-matrix":
                    path.write_text(json.dumps(progress, indent=2))
                else:
                    _checkpoint(test_identity(), progress)
                payload = progress
        print(json.dumps(payload), flush=True)
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    parser.add_argument("--test-profile", required=True, type=Path)
    parser.add_argument("--mode", choices=sorted(NATIVE_TEST_MODES), default="matrix")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_profile(args.app, args.test_profile, args.mode, timeout=1200 if args.mode in {"matrix", "v6-matrix"} else 240)
    if args.output:
        with args.output.open("x") as stream: json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))
    return result["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())
