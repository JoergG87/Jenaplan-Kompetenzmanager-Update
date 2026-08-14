"""Isolated real-Keychain checks for an internal frozen macOS build."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Mapping

from src.core.runtime_root_protection import (
    RuntimeRootKind,
    inspect_runtime_root,
)

from src.security.data_keys import (
    DATA_MASTER_KEY_BYTES,
    DataKeyset,
    DataKeysetStatus,
    DataMasterKeyLifecycleError,
    DataMasterKeyService,
    DataMasterKeyStoreStatus,
)
from src.security.infrastructure.data_keyset_repository import (
    SQLiteDataKeysetRepository,
)
from src.security.infrastructure.data_master_key_store import (
    build_platform_data_master_key_store,
)
from src.security.infrastructure.system import (
    PlatformFilePermissionManager,
    SystemRandomSource,
)
from src.security.startup import build_security_runtime


PACKAGED_KEYCHAIN_SMOKE_ARGUMENT = "--packaged-keychain-smoke"
PACKAGED_SMOKE_MARKER_ENV = "JENAPLAN_PACKAGED_SMOKE_MARKER"
PACKAGED_SMOKE_MARKER_VALUE = "isolated-v1"
PACKAGED_KEYCHAIN_TEMP_PREFIX = "jenaplan-keychain-smoke-"
APP_DATA_DIR_ENV = "JENAPLAN_APP_DATA_DIR"


@dataclass(frozen=True)
class _PackagedKeychainPaths:
    root: Path

    @property
    def database(self) -> Path:
        return self.root / "kompetenzmanager.sqlite"

    @property
    def documents(self) -> Path:
        return self.root / "documents"

    @property
    def security(self) -> Path:
        return self.root / "security"

    @property
    def security_database(self) -> Path:
        return self.security / "security.sqlite"

    @property
    def enrollment_marker(self) -> Path:
        return self.security / "enrollment.marker"

    @property
    def app_preferences(self) -> Path:
        return self.root / "app-preferences.json"


def run_packaged_keychain_smoke(
    mode: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    environment = dict(os.environ if environ is None else environ)
    try:
        if not getattr(sys, "frozen", False):
            return _blocked(mode, "packaged_keychain_smoke_requires_frozen_app")
        root = _validated_root(environment)
        if mode == "initialize":
            runtime, service, repository, _store = _new_environment(root)
            runtime.service.enroll_local_account(_password(root, "initial"))
            loaded = service.provision()
            active = repository.active_data_keyset()
            if (
                active is None
                or active.key_id != loaded.key_id
                or len(loaded.key_material) != DATA_MASTER_KEY_BYTES
            ):
                raise RuntimeError("keychain_provision_invalid")
            return _ok(mode, fingerprint=active.fingerprint_sha256)
        if mode == "reload-password-change":
            runtime, service, repository, _store = _existing_environment(root)
            before = service.load()
            active_before = repository.active_data_keyset()
            runtime.service.change_password(
                _password(root, "initial"),
                _password(root, "changed"),
            )
            after = service.load()
            active_after = repository.active_data_keyset()
            if (
                before != after
                or active_before != active_after
                or active_after is None
            ):
                raise RuntimeError("keychain_password_change_rotated_dmk")
            return _ok(
                mode,
                fingerprint=active_after.fingerprint_sha256,
            )
        if mode == "cleanup":
            _runtime, service, repository, store = _existing_environment(root)
            active = repository.active_data_keyset()
            if active is None:
                raise RuntimeError("keychain_cleanup_active_key_missing")
            installation_id = _runtime.repository.load_account().installation_id
            if not service.delete():
                raise RuntimeError("keychain_cleanup_failed")
            result = store.read(
                installation_id=installation_id,
                key_id=active.key_id,
            )
            if (
                repository.active_data_keyset() is not None
                or result.status is not DataMasterKeyStoreStatus.NOT_FOUND
            ):
                raise RuntimeError("keychain_cleanup_incomplete")
            return _ok(mode)
        if mode in {"missing", "corrupt"}:
            runtime, service, repository, store = _new_environment(root)
            runtime.service.enroll_local_account(_password(root, "initial"))
            account = runtime.repository.load_account()
            expected = SystemRandomSource().bytes(DATA_MASTER_KEY_BYTES)
            key_id = SystemRandomSource().uuid4()
            keyset = DataKeyset(
                key_id=key_id,
                generation=1,
                status=DataKeysetStatus.PENDING,
                fingerprint_sha256=hashlib.sha256(expected).hexdigest(),
            )
            repository.prepare_data_keyset(keyset)
            repository.activate_data_keyset(key_id=key_id)
            if mode == "corrupt":
                wrong = SystemRandomSource().bytes(DATA_MASTER_KEY_BYTES)
                while wrong == expected:
                    wrong = SystemRandomSource().bytes(DATA_MASTER_KEY_BYTES)
                store.create(
                    installation_id=account.installation_id,
                    key_id=key_id,
                    key_material=wrong,
                )
            try:
                service.load()
            except DataMasterKeyLifecycleError as error:
                expected_code = (
                    "data_master_key_not_found"
                    if mode == "missing"
                    else "data_master_key_corrupt"
                )
                if error.code != expected_code:
                    raise RuntimeError("keychain_failure_code_invalid") from None
            else:
                raise RuntimeError("keychain_invalid_state_accepted")
            if repository.active_data_keyset() is not None:
                raise RuntimeError("keychain_invalid_state_remained_active")
            if mode == "corrupt":
                service.delete()
            return _ok(mode)
        return _blocked(mode, "packaged_keychain_smoke_mode_invalid")
    except Exception:
        return _blocked(mode, "packaged_keychain_smoke_failed")


def _new_environment(root: Path):
    if root.exists() or root.is_symlink():
        raise RuntimeError("keychain_smoke_root_exists")
    paths = _prepare_paths(root)
    runtime = build_security_runtime(paths)
    repository = SQLiteDataKeysetRepository(
        paths.security / "data-keysets.sqlite",
        PlatformFilePermissionManager(),
    )
    repository.initialize()
    store = build_platform_data_master_key_store()
    if not store.supported:
        raise RuntimeError("keychain_store_unavailable")
    service = DataMasterKeyService(
        repository=repository,
        key_store=store,
        random_source=SystemRandomSource(),
        account_loader=runtime.repository.load_account,
    )
    return runtime, service, repository, store


def _existing_environment(root: Path):
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("keychain_smoke_root_missing")
    paths = _prepare_paths(root)
    runtime = build_security_runtime(paths)
    repository = SQLiteDataKeysetRepository(
        paths.security / "data-keysets.sqlite",
        PlatformFilePermissionManager(),
    )
    repository.initialize()
    store = build_platform_data_master_key_store()
    if not store.supported:
        raise RuntimeError("keychain_store_unavailable")
    service = DataMasterKeyService(
        repository=repository,
        key_store=store,
        random_source=SystemRandomSource(),
        account_loader=runtime.repository.load_account,
    )
    return runtime, service, repository, store


def _prepare_paths(root: Path) -> _PackagedKeychainPaths:
    paths = _PackagedKeychainPaths(root)
    root.mkdir(mode=0o700, exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("keychain_smoke_root_invalid")
    os.chmod(root, 0o700)
    if paths.security.is_symlink():
        raise RuntimeError("keychain_smoke_security_symlink")
    paths.security.mkdir(mode=0o700, exist_ok=True)
    if not paths.security.is_dir():
        raise RuntimeError("keychain_smoke_security_invalid")
    os.chmod(paths.security, 0o700)
    return paths


def _validated_root(environment: Mapping[str, str]) -> Path:
    if (
        environment.get(PACKAGED_SMOKE_MARKER_ENV)
        != PACKAGED_SMOKE_MARKER_VALUE
    ):
        raise RuntimeError("keychain_smoke_marker_invalid")
    raw = environment.get(APP_DATA_DIR_ENV, "")
    root = Path(raw) if raw else Path()
    if not raw or not root.is_absolute():
        raise RuntimeError("keychain_smoke_root_invalid")
    temporary = Path(tempfile.gettempdir()).resolve(strict=True)
    resolved = root.resolve(strict=False)
    relative = resolved.relative_to(temporary)
    if not any(
        part.startswith(PACKAGED_KEYCHAIN_TEMP_PREFIX)
        for part in relative.parts
    ):
        raise RuntimeError("keychain_smoke_root_outside_test_container")
    protection = inspect_runtime_root(resolved)
    if protection is None or protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
        raise RuntimeError("keychain_smoke_test_root_unmarked")
    return resolved


def _password(root: Path, role: str) -> str:
    digest = hashlib.sha256(
        f"packaged-keychain-{role}:{root.name}".encode("ascii")
    ).hexdigest()
    return f"synthetic-only-{digest}"


def _ok(mode: str, *, fingerprint: str | None = None) -> int:
    payload = {"mode": mode, "status": "ok"}
    if fingerprint is not None:
        payload["fingerprint_sha256"] = fingerprint
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True), flush=True)
    return 0


def _blocked(mode: str, code: str) -> int:
    print(
        json.dumps(
            {"error_code": code, "mode": mode, "status": "blocked"},
            ensure_ascii=True,
            sort_keys=True,
        ),
        flush=True,
    )
    return 1
