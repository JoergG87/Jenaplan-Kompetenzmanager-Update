"""Synthetic V7 strategy for the existing Cipher restore state machine.

No product worker mode or startup fallback is registered by this module.
"""
from pathlib import Path
import hashlib
import hmac

from src.core.restore_runtime import (
    RestoreHandoffError, RestorePreflightError, RestoreJournal,
    restore_transaction_paths,
)
from src.security.final_v4_live_restore import (
    FinalV4EncryptedRestoreHandoffService, FinalV4EncryptedLiveRestoreService,
    FinalV4LiveRestorePreparation, FINAL_V4_LIVE_RESTORE_BACKUP_DIRECTORY,
    _confirm_cipher_restore_startup, _recover_interrupted_cipher_restore,
    _read_canonical_json,
)
from src.security.synthetic_v7_backup_runtime import SyntheticV7EncryptedBackupService

SYNTHETIC_V7_LIVE_RESTORE_KIND = "synthetic_v7_encrypted_same_installation"
SYNTHETIC_V7_LIVE_RESTORE_AUTH_PURPOSE = (
    "jenaplan-kompetenzmanager/synthetic-v7-live-restore-handoff/v1"
)


def _require_service(service, runtime_root=None):
    from src.security.product_v7 import ProductV7BackupService
    if type(service) not in (SyntheticV7EncryptedBackupService, ProductV7BackupService):
        raise RestorePreflightError("Der synthetische V7-Restorevertrag fehlt.")
    service.require_synthetic()
    root = service.paths.final_v4.key_runtime.root.resolve(strict=True)
    if runtime_root is not None and Path(runtime_root).resolve(strict=True) != root:
        raise RestorePreflightError("Der synthetische V7-Restoreroot widerspricht sich.")
    return root


class SyntheticV7EncryptedRestoreHandoffService(FinalV4EncryptedRestoreHandoffService):
    expected_backup_service_type = SyntheticV7EncryptedBackupService
    restore_kind = SYNTHETIC_V7_LIVE_RESTORE_KIND
    authentication_purpose = SYNTHETIC_V7_LIVE_RESTORE_AUTH_PURPOSE

    def __init__(self, backup_service=None, **context):
        if backup_service is not None:
            _require_service(backup_service)
        else:
            # Recovery may need retained key metadata while the live metadata
            # directory is between renames. This loads no keys and grants no
            # runtime admission; the existing bootstrap authenticates the DMK
            # and exact HMAC before using the context.
            self.require_root(Path(context["runtime_root"]))
        super().__init__(backup_service, **context)

    def _runtime_root(self):
        if self.backup_service is not None:
            return _require_service(self.backup_service)
        self.require_root(self.runtime_root)
        return self.runtime_root

    @staticmethod
    def require_root(root):
        from src.core.runtime_root_protection import require_mutable_test_root, RuntimeRootKind
        if root.resolve(strict=True) != root:
            raise RestoreHandoffError("Der V7-Restoreroot ist ungueltig.")
        protection = require_mutable_test_root(root)
        if protection is None or protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
            raise RestoreHandoffError("Der synthetische V7-Restoreroot fehlt.")



class SyntheticV7EncryptedLiveRestoreService(FinalV4EncryptedLiveRestoreService):
    """Same journaled swap/rollback; only an exact synthetic V7 service."""
    def __init__(self, backup_service, *, fault_hook=None, restart_launcher=None):
        _require_service(backup_service)
        super().__init__(backup_service,
            handoff_service=_handoff_type(backup_service)(backup_service),
            fault_hook=fault_hook, restart_launcher=restart_launcher)


def prepare_synthetic_v7_live_restore(*, backup_service, lock, staging_root,
        expected_container_sha256, restore_id, app_version, build_commit,
        source_tree_state=None, before_handoff=None):
    root = _require_service(backup_service)
    if lock.runtime_root != root or lock._file is None:
        raise RestorePreflightError("Der synthetische V7-Livebestand ist nicht gesperrt.")
    # Target READY must be exact V7 before even creating a safety backup.
    backup_service.verify_restore_ready(staging_root,
        expected_container_sha256=expected_container_sha256)
    backup_root = root / FINAL_V4_LIVE_RESTORE_BACKUP_DIRECTORY
    backup_root.mkdir(mode=0o700, exist_ok=True)
    safety = backup_service.create_safety_backup(backup_root / f"safety-{restore_id}.jkmebackup")
    try:
        if before_handoff is not None:
            before_handoff()
        handoff = _handoff_type(backup_service)(backup_service).create(
            staging_root=staging_root, expected_container_sha256=expected_container_sha256,
            safety_backup=safety, restore_id=restore_id, app_version=app_version,
            build_commit=build_commit, source_tree_state=source_tree_state)
    except Exception:
        safety.abort()
        raise
    return FinalV4LiveRestorePreparation(handoff, safety)


def _verify_handoff_history(service, paths):
    """Authenticate persisted context again before any recovery authority."""
    path = paths.consumed_handoff if paths.consumed_handoff.exists() else paths.handoff
    payload = _read_canonical_json(path, RestoreHandoffError)
    observed = payload.pop("authentication_hmac_sha256", None)
    handoff = _handoff_type(service)(service)
    if (payload.get("restore_kind") != _restore_kind(service)
            or payload.get("runtime_root") != str(_require_service(service))
            or payload.get("restore_id") != paths.transaction.name
            or payload.get("installation_id") != service.installation_id
            or payload.get("database_context_id") != service.loaded.database_context_id
            or not isinstance(observed, str)
            or not hmac.compare_digest(observed, handoff._authenticate(payload))):
        raise RestoreHandoffError("Der synthetische V7-Restorebeleg ist nicht authentisiert.")
    return payload


def confirm_synthetic_v7_restore_startup(*, backup_service, runtime_root,
        restore_id, token):
    root = _require_service(backup_service, runtime_root)
    paths = restore_transaction_paths(root, restore_id)
    handoff = _verify_handoff_history(backup_service, paths)
    manifest = backup_service.read_manifest(root / str(handoff["staging_root_relative"]))
    if hashlib.sha256(manifest.to_bytes()).hexdigest() != handoff.get("manifest_sha256"):
        raise RestoreHandoffError("Der synthetische V7-Restartbestand widerspricht dem Manifest.")
    return _confirm_cipher_restore_startup(
        restore_kind=_restore_kind(backup_service),
        manifest_reader=backup_service.read_manifest, backup_service=backup_service,
        runtime_root=root, restore_id=restore_id, token=token)


def recover_interrupted_synthetic_v7_restore(*, backup_service, runtime_root):
    root = _require_service(backup_service, runtime_root)
    transaction_root = root / "restore-transactions"
    if transaction_root.exists():
        for child in sorted(transaction_root.iterdir()):
            if child.is_symlink() or not child.is_dir():
                raise RestoreHandoffError("Der synthetische Restorebereich ist ungueltig.")
            paths = restore_transaction_paths(root, child.name)
            state = RestoreJournal(paths).read()
            if state.get("phase") not in {"completed", "rolled_back", "aborted_before_replacement"}:
                if state.get("restore_kind") != _restore_kind(backup_service):
                    raise RestoreHandoffError("Ein fremder Restorevertrag blockiert V7-Recovery.")
                _verify_handoff_history(backup_service, paths)
    return _recover_interrupted_cipher_restore(
        restore_kind=_restore_kind(backup_service),
        manifest_reader=backup_service.read_manifest,
        live_restore_type=_live_restore_type(backup_service),
        backup_service=backup_service, runtime_root=root)


def classify_terminal_synthetic_v7_restore_artifacts(backup_service):
    """Authorize one terminal synthetic transaction only after full recheck.

    Multiple historical transactions require explicit review; directory names
    or unauthenticated journal phase alone never admit a synthetic runtime.
    """
    root = _require_service(backup_service)
    transaction_root = root / "restore-transactions"
    handoff_root = root / "restore-handoffs"
    if not transaction_root.exists() and not handoff_root.exists():
        return False
    children = tuple(transaction_root.iterdir()) if transaction_root.is_dir() else ()
    if len(children) != 1 or children[0].is_symlink() or not children[0].is_dir():
        raise RestoreHandoffError("Der terminale synthetische Restore ist nicht eindeutig.")
    paths = restore_transaction_paths(root, children[0].name)
    state = RestoreJournal(paths).read()
    phase = state.get("phase")
    if (state.get("restore_kind") != _restore_kind(backup_service)
            or phase not in {"completed", "rolled_back", "aborted_before_replacement"}):
        raise RestoreHandoffError("Der synthetische Restore ist nicht abgeschlossen.")
    handoff = _verify_handoff_history(backup_service, paths)
    if phase == "completed":
        if paths.resume_token.exists() or not paths.consumed_resume_token.is_file():
            raise RestoreHandoffError("Der synthetische Neustart wurde nicht konsumiert.")
        manifest = backup_service.read_manifest(root / str(handoff["staging_root_relative"]))
        if hashlib.sha256(manifest.to_bytes()).hexdigest() != handoff.get("manifest_sha256"):
            raise RestoreHandoffError("Das terminale synthetische Manifest widerspricht dem Handoff.")
    else:
        safety = backup_service.verify(root / str(handoff["safety_backup_relative"]))
        if safety.container_sha256 != handoff.get("safety_backup_sha256"):
            raise RestoreHandoffError("Das terminale synthetische Sicherheitsbackup widerspricht sich.")
        manifest = safety.manifest
    # Terminal restore evidence authenticates history, not immutable live
    # contents. Normal post-restore writes must survive the next startup.
    # Worker/initial handshake still require exact snapshot hashes. Here use
    # current keyed/domain/document checks without comparing old inventories.
    backup_service._validate_context(manifest)
    keys = backup_service.paths.final_v4.key_runtime
    backup_service._validate_key_metadata(keys.keyset_metadata, keys.envelope_registry,
        expected=backup_service.loaded)
    key = backup_service.loaded.database_key.key_material
    backup_service._inspect_main(backup_service.paths.final_v4.database, key)
    backup_service._inspect_companion(backup_service.paths.database, key)
    from src.security.final_v3_document_runtime import FinalV3DocumentRuntime
    FinalV3DocumentRuntime(paths=backup_service.paths,
        factory=backup_service._document_factory, loaded_keys=backup_service.loaded,
        installation_id=backup_service.installation_id, source_root=None,
        random_source=backup_service._random, clock=backup_service._clock).validate_restart()
    backup_service._validate_crossbindings(backup_service.paths.final_v4.database,
        backup_service.paths.database, key)
    allowed_handoffs = {paths.handoff, paths.consumed_handoff}
    if handoff_root.exists() and any(path not in allowed_handoffs for path in handoff_root.iterdir()):
        raise RestoreHandoffError("Fremde synthetische Handoffevidenz ist vorhanden.")
    return True


def _handoff_type(service):
    from src.security.product_v7 import ProductV7BackupService
    if type(service) is ProductV7BackupService:
        from src.security.product_v7_restore import ProductV7RestoreHandoffService
        return ProductV7RestoreHandoffService
    return SyntheticV7EncryptedRestoreHandoffService


def _restore_kind(service):
    return _handoff_type(service).restore_kind


def _live_restore_type(service):
    from src.security.product_v7 import ProductV7BackupService
    if type(service) is ProductV7BackupService:
        from src.security.product_v7_restore import ProductV7LiveRestoreService
        return ProductV7LiveRestoreService
    return SyntheticV7EncryptedLiveRestoreService
