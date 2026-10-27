"""V6 worker boundaries and real SQLCipher/authenticated recovery evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from src.core.macos_test_package_profile import _validate_arguments, validate_test_profile
from src.core.restore_runtime import RestoreJournal, RestoreManualRecoveryRequired, restore_transaction_paths
from src.desktop_app.restore_worker import RESTORE_MODE_SYNTHETIC_V6_ENCRYPTED
from src.security.data_keys import DataMasterKeyReadResult, DataMasterKeyStoreStatus
from src.security.final_v4_live_restore import _bootstrap_handoff_context
from src.security.synthetic_v6_live_restore import (
    SYNTHETIC_V6_LIVE_RESTORE_KIND, SyntheticV6EncryptedRestoreHandoffService,
)
from tests.test_macos_test_package_profile import profile
from tests.test_synthetic_v6_backup_restore import case, _prepare, _run_restore, _hash


@pytest.mark.parametrize("status", ["normal_start", "resume_required", "aborted_before_replacement", "rolled_back", "failed"])
def test_only_successful_verified_rollback_exports_its_existing_context(monkeypatch, tmp_path, status):
    from unittest.mock import Mock
    from src.desktop_app import synthetic_v6_runtime_adapters as adapters
    from src.security import internal_test_v6_composition as composition
    from src.security import synthetic_v6_live_restore as recovery
    service = object()
    monkeypatch.setattr(composition, "require_internal_test_v6_context", lambda root: None)
    monkeypatch.setattr(adapters, "build_internal_test_v6_restore_verifier", lambda root: service)
    def recover(**kwargs):
        assert kwargs == {"backup_service": service, "runtime_root": tmp_path}
        if status == "failed":
            raise RestoreManualRecoveryRequired("synthetic verification failure")
        return SimpleNamespace(status=status)
    monkeypatch.setattr(recovery, "recover_interrupted_synthetic_v6_restore", recover)
    callback = Mock()
    if status == "failed":
        with pytest.raises(RestoreManualRecoveryRequired):
            adapters.recover_internal_test_v6_restore(tmp_path, on_verified_rollback=callback)
    else:
        assert adapters.recover_internal_test_v6_restore(tmp_path,
            on_verified_rollback=callback).status == status
    if status == "rolled_back":
        callback.assert_called_once_with(service)
    else:
        callback.assert_not_called()


@pytest.mark.parametrize("version", [6,7])
def test_v6_profile_worker_and_restart_are_bound_to_exact_profile(profile, version):
    validated = validate_test_profile(profile)
    root = Path(profile["runtime_root"])
    worker = ["--restore-worker", "--restore-mode", f"synthetic_v{version}_encrypted",
        "--handoff", str(root / "restore-handoffs" / "test.json"), "--nonce", "nonce"]
    restart = [f"--synthetic-v{version}-restore-confirm", "--runtime-root", str(root),
        "--restore-id", "id", "--restore-token", "token", "--restore-lock-fd", "5"]
    _validate_arguments(validated, worker)
    _validate_arguments(validated, restart)
    for arguments in (worker + ["--final-v4-restore-confirm"],
                      restart + ["--final-v4-restore-confirm"],
                      restart + ["--restore-worker"],
                      [value.replace(str(root), "/foreign") for value in worker],
                      [value.replace(str(root), "/foreign") for value in restart]):
        with pytest.raises(ValueError):
            _validate_arguments(validated, arguments)


@pytest.mark.parametrize("version", [6,7])
def test_real_source_worker_cannot_activate_v6_from_environment(tmp_path, version):
    root = tmp_path.resolve() / "synthetic"
    handoffs = root / "restore-handoffs"
    handoffs.mkdir(parents=True)
    handoff = handoffs / "test.json"
    handoff.write_text("{}")
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-m", "src.desktop_app.restore_worker",
        "--restore-mode", f"synthetic_v{version}_encrypted",
        "--handoff", str(handoff), "--nonce", "unused"],
        cwd=Path(__file__).resolve().parents[1], capture_output=True,
        env=dict(os.environ, JENAPLAN_APP_DATA_DIR=str(root),
            JENAPLAN_PACKAGED_SMOKE_MARKER="isolated-v1"), timeout=15)
    assert result.returncode != 0
    assert not (root / "instance.lock").exists()
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_native_v6_runner_has_no_source_authority():
    from scripts.macos_native_v6_acceptance import run_frozen
    with pytest.raises(ValueError, match="test_profile_invalid"):
        run_frozen("v6-migrate")


class _ExistingSyntheticDMK:
    """Existing synthetic key port; native AES/HMAC/SQLCipher remain real."""
    def __init__(self, service):
        self.service = service

    def read(self, *, installation_id, key_id):
        assert installation_id == self.service.installation_id
        assert key_id == self.service.loaded.dmk_key_id
        return DataMasterKeyReadResult(DataMasterKeyStoreStatus.SUCCESS,
            self.service.loaded.dmk.key_material)


@pytest.mark.parametrize("tamper", [False, True])
def test_real_crash_retained_metadata_authenticates_exact_v6_handoff(case, tmp_path, tamper):
    service, _, _ = case
    prep, _, _ = _prepare(service, tmp_path)
    _run_restore(service, prep, crash="between_main_and_companion")
    paths = restore_transaction_paths(service.paths.final_v4.root, prep.handoff.restore_id)
    key_paths = service.paths.final_v4.key_runtime
    assert not key_paths.metadata_root.exists()
    retained = paths.rollback / key_paths.metadata_root.name
    before = {p: _hash(p) for p in retained.rglob("*") if p.is_file()}
    if tamper:
        payload = json.loads(paths.consumed_handoff.read_text())
        payload["database_context_id"] = "00000000-0000-4000-8000-000000000001"
        paths.consumed_handoff.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    arguments = dict(account_loader=lambda: SimpleNamespace(installation_id=service.installation_id),
        key_store=_ExistingSyntheticDMK(service), restore_kind=SYNTHETIC_V6_LIVE_RESTORE_KIND,
        handoff_service_type=SyntheticV6EncryptedRestoreHandoffService)
    if tamper:
        with pytest.raises(RestoreManualRecoveryRequired):
            _bootstrap_handoff_context(paths, RestoreJournal(paths).read(), **arguments)
    else:
        handoff, loaded = _bootstrap_handoff_context(paths, RestoreJournal(paths).read(), **arguments)
        assert loaded == service.loaded
        assert handoff["restore_kind"] == SYNTHETIC_V6_LIVE_RESTORE_KIND
    assert not key_paths.metadata_root.exists()
    assert {p: _hash(p) for p in retained.rglob("*") if p.is_file()} == before
