from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import uuid

import pytest

from src.desktop_app.runtime import prepare_security_runtime_storage
from src.core.app_preferences import AppPreferences
from src.security.device_credentials import DeviceCredentialService
from src.security.domain import (
    DeviceCredentialAuthenticationStatus,
    DeviceCredentialStatus,
    LocalAuthenticationAvailability,
    LocalAuthenticationResult,
    SecretStoreReadResult,
    SecretStoreStatus,
    hash_device_secret,
)
from src.security.infrastructure.system import SystemClock, SystemRandomSource
from src.security.startup import build_security_runtime


class MemorySecretStore:
    supported = True

    def __init__(self) -> None:
        self.values: dict[tuple[str, str], bytes] = {}
        self.fail_create = False
        self.fail_delete = False

    def create(self, *, installation_id: str, credential_id: str, secret: bytes) -> None:
        if self.fail_create:
            raise RuntimeError("create_failed")
        key = (installation_id, credential_id)
        if key in self.values:
            raise RuntimeError("duplicate")
        self.values[key] = bytes(secret)

    def read(self, *, installation_id: str, credential_id: str) -> SecretStoreReadResult:
        secret = self.values.get((installation_id, credential_id))
        if secret is None:
            return SecretStoreReadResult(SecretStoreStatus.NOT_FOUND)
        return SecretStoreReadResult(SecretStoreStatus.SUCCESS, secret)

    def delete(self, *, installation_id: str, credential_id: str) -> bool:
        if self.fail_delete:
            raise RuntimeError("delete_failed")
        return self.values.pop((installation_id, credential_id), None) is not None


@dataclass
class FakeLocalAuthenticator:
    available: LocalAuthenticationAvailability = LocalAuthenticationAvailability.AVAILABLE
    result: LocalAuthenticationResult = LocalAuthenticationResult.SUCCESS
    calls: int = 0

    def availability(self) -> LocalAuthenticationAvailability:
        return self.available

    def authenticate(self, reason: str) -> LocalAuthenticationResult:
        assert reason == "Jenaplan-Kompetenzmanager entsperren"
        self.calls += 1
        return self.result


def credential_service(tmp_path: Path):
    paths = prepare_security_runtime_storage(data_root=tmp_path / "runtime")
    runtime = build_security_runtime(paths)
    password = "eine lange sichere Geräte-Testpassphrase"
    runtime.service.enroll_local_account(password)
    secret_store = MemorySecretStore()
    local_auth = FakeLocalAuthenticator()
    service = DeviceCredentialService(
        repository=runtime.repository,
        secret_store=secret_store,
        local_authenticator=local_auth,
        random_source=SystemRandomSource(),
        utc_clock=SystemClock(),
        security_epoch=runtime.repository.security_epoch,
        account_loader=runtime.repository.load_account,
    )
    return runtime, service, secret_store, local_auth, password


def test_registration_uses_256_bit_random_secret_and_only_hash_in_store(tmp_path: Path) -> None:
    runtime, service, secrets, _local_auth, _password = credential_service(tmp_path)
    first = service.register().credential
    first_secret = next(iter(secrets.values.values()))
    assert len(first_secret) == 32
    assert len(first.salt) == 16
    assert len(first.secret_hash) == 32
    assert first_secret != first.secret_hash
    second = service.register().credential
    second_secret = secrets.values[(second.installation_id, second.credential_id)]
    assert second_secret != first_secret
    assert runtime.repository.active_device_credential() == second
    assert first.credential_id not in {key[1] for key in secrets.values}
    with sqlite3.connect(runtime.repository.database_path) as connection:
        row = connection.execute(
            "SELECT salt, secret_hash, hash_format_version, status FROM device_credentials "
            "WHERE credential_id = ?",
            (second.credential_id,),
        ).fetchone()
    assert bytes(row[0]) == second.salt
    assert bytes(row[1]) == second.secret_hash
    assert row[2:] == (1, "active")


def test_valid_secret_authenticates_and_wrong_secret_revokes(tmp_path: Path) -> None:
    runtime, service, secrets, _local_auth, _password = credential_service(tmp_path)
    credential = service.register().credential
    assert service.authenticate().status is DeviceCredentialAuthenticationStatus.AUTHENTICATED
    secrets.values[(credential.installation_id, credential.credential_id)] = b"x" * 32
    assert service.authenticate().status is DeviceCredentialAuthenticationStatus.REJECTED
    assert runtime.repository.active_device_credential() is None


def test_missing_secret_and_delete_failure_are_fail_safe(tmp_path: Path) -> None:
    runtime, service, secrets, _local_auth, _password = credential_service(tmp_path)
    credential = service.register().credential
    secrets.values.clear()
    assert service.authenticate().status is DeviceCredentialAuthenticationStatus.REJECTED
    assert runtime.repository.active_device_credential() is None

    replacement = service.register().credential
    secrets.fail_delete = True
    assert service.disable() is True
    assert runtime.repository.active_device_credential() is None
    assert (replacement.installation_id, replacement.credential_id) in secrets.values


def test_registration_compensates_secret_when_repository_commit_fails(tmp_path: Path) -> None:
    runtime, _service, secrets, local_auth, _password = credential_service(tmp_path)

    class FailingRepository:
        def __getattr__(self, name):
            return getattr(runtime.repository, name)

        def activate_device_credential(self, *, credential_id, now):
            raise RuntimeError("commit_failed")

    service = DeviceCredentialService(
        repository=FailingRepository(),
        secret_store=secrets,
        local_authenticator=local_auth,
        random_source=SystemRandomSource(),
        utc_clock=SystemClock(),
        security_epoch=runtime.repository.security_epoch,
        account_loader=runtime.repository.load_account,
    )
    with pytest.raises(RuntimeError, match="commit_failed"):
        service.register()
    assert secrets.values == {}
    assert runtime.repository.active_device_credential() is None


@pytest.mark.parametrize("secret_created", [False, True])
def test_restart_cleanup_recovers_pending_registration(
    tmp_path: Path, secret_created: bool
) -> None:
    runtime, service, secrets, _local_auth, _password = credential_service(tmp_path)
    original = service.register().credential
    original_secret = secrets.values[
        (original.installation_id, original.credential_id)
    ]
    assert service.disable()
    pending = replace(
        original,
        credential_id=str(uuid.uuid4()),
        secret_hash=hash_device_secret(original.salt, original_secret),
        status=DeviceCredentialStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        revoked_at=None,
    )
    runtime.repository.prepare_device_credential(pending)
    if secret_created:
        secrets.create(
            installation_id=pending.installation_id,
            credential_id=pending.credential_id,
            secret=original_secret,
        )
    status = service.status()
    assert status.enabled is False
    assert runtime.repository.pending_device_credentials() == ()
    assert runtime.repository.active_device_credential() is None
    assert (pending.installation_id, pending.credential_id) not in secrets.values


@pytest.mark.parametrize(
    "local_result",
    [
        LocalAuthenticationResult.USER_CANCEL,
        LocalAuthenticationResult.FALLBACK_REQUESTED,
        LocalAuthenticationResult.NOT_AVAILABLE,
        LocalAuthenticationResult.NOT_ENROLLED,
        LocalAuthenticationResult.LOCKED_OUT,
        LocalAuthenticationResult.SYSTEM_CANCEL,
        LocalAuthenticationResult.FAILED,
        LocalAuthenticationResult.ERROR,
    ],
)
def test_local_auth_failure_never_authenticates(
    tmp_path: Path, local_result: LocalAuthenticationResult
) -> None:
    _runtime, service, _secrets, local_auth, _password = credential_service(tmp_path)
    service.register()
    local_auth.result = local_result
    result = service.authenticate(require_local_authentication=True)
    assert result.status is not DeviceCredentialAuthenticationStatus.AUTHENTICATED
    assert result.local_authentication_result is local_result
    assert local_auth.calls == 1


def test_touch_id_success_plus_secret_verification_authenticates(tmp_path: Path) -> None:
    _runtime, service, _secrets, local_auth, _password = credential_service(tmp_path)
    service.register()
    result = service.authenticate(require_local_authentication=True)
    assert result.status is DeviceCredentialAuthenticationStatus.AUTHENTICATED
    assert local_auth.calls == 1


def test_password_change_epoch_revokes_active_device_credential(tmp_path: Path) -> None:
    runtime, service, secrets, _local_auth, password = credential_service(tmp_path)
    credential = service.register().credential
    result = runtime.service.change_password(
        password, "eine andere lange sichere Geräte-Testpassphrase"
    )
    assert result.status.value == "authenticated"
    assert runtime.repository.active_device_credential() is None
    assert service.authenticate().status is DeviceCredentialAuthenticationStatus.NOT_CONFIGURED
    assert (credential.installation_id, credential.credential_id) not in secrets.values


def test_store_has_exactly_one_active_credential_after_rotation(tmp_path: Path) -> None:
    runtime, service, _secrets, _local_auth, _password = credential_service(tmp_path)
    first = service.register().credential
    second = service.register().credential
    with sqlite3.connect(runtime.repository.database_path) as connection:
        rows = connection.execute(
            "SELECT credential_id, status FROM device_credentials ORDER BY created_at_utc"
        ).fetchall()
    assert rows == [(first.credential_id, "revoked"), (second.credential_id, "active")]
    assert sum(status == "active" for _identifier, status in rows) == 1


def test_preferences_may_store_touch_id_choice_but_no_credential_material(tmp_path: Path) -> None:
    runtime, service, _secrets, _local_auth, _password = credential_service(tmp_path)
    credential = service.register().credential
    runtime.preferences.save(AppPreferences(touch_id_preferred=True))
    raw = runtime.preferences.path.read_text(encoding="utf-8")
    assert runtime.preferences.load().touch_id_preferred is True
    assert "touch_id_preferred" in raw
    for forbidden in (
        credential.credential_id,
        credential.secret_hash.hex(),
        credential.salt.hex(),
        "security_epoch",
        "credential_id",
    ):
        assert forbidden not in raw
