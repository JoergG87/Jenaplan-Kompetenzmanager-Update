"""Qt-free lifecycle for one local, revocable device credential."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .domain import (
    AccountStatus,
    DEVICE_CREDENTIAL_HASH_FORMAT_VERSION,
    DEVICE_CREDENTIAL_SALT_BYTES,
    DEVICE_CREDENTIAL_SECRET_BYTES,
    DeviceCredential,
    DeviceCredentialAuthenticationResult,
    DeviceCredentialAuthenticationStatus,
    DeviceCredentialRegistrationResult,
    DeviceCredentialStatus,
    LocalAuthenticationAvailability,
    LocalAuthenticationResult,
    SecretStoreStatus,
    SecurityStateError,
    SecurityStoreError,
    hash_device_secret,
    verify_device_secret,
)
from .ports import (
    DeviceCredentialRepository,
    DeviceSecretStore,
    LocalDeviceAuthenticator,
    RandomSource,
    UtcClock,
)


@dataclass(frozen=True)
class DeviceCredentialStatusResult:
    enabled: bool
    secret_available: bool
    local_authentication: LocalAuthenticationAvailability


class DeviceCredentialService:
    """Coordinate store metadata, platform secret and local authentication."""

    def __init__(
        self,
        *,
        repository: DeviceCredentialRepository,
        secret_store: DeviceSecretStore,
        local_authenticator: LocalDeviceAuthenticator,
        random_source: RandomSource,
        utc_clock: UtcClock,
        security_epoch,
        account_loader,
    ) -> None:
        self._repository = repository
        self._secret_store = secret_store
        self._local_authenticator = local_authenticator
        self._random = random_source
        self._clock = utc_clock
        self._security_epoch = security_epoch
        self._account_loader = account_loader

    @property
    def supported(self) -> bool:
        return self._secret_store.supported

    def status(self) -> DeviceCredentialStatusResult:
        availability = self._local_authenticator.availability()
        if not self.supported:
            return DeviceCredentialStatusResult(False, False, availability)
        try:
            self._cleanup_incomplete()
            credential = self._repository.active_device_credential()
            if credential is None:
                return DeviceCredentialStatusResult(False, False, availability)
            if credential.security_epoch_at_issue != self._security_epoch():
                self._reject(credential)
                return DeviceCredentialStatusResult(False, False, availability)
            secret = self._secret_store.read(
                installation_id=credential.installation_id,
                credential_id=credential.credential_id,
            )
            available = secret.status is SecretStoreStatus.SUCCESS
            if not available and secret.status is not SecretStoreStatus.ACCESS_DENIED:
                self._reject(credential)
                return DeviceCredentialStatusResult(False, False, availability)
            return DeviceCredentialStatusResult(True, available, availability)
        except SecurityStoreError:
            return DeviceCredentialStatusResult(False, False, availability)

    def register(self, *, device_label: str = "Dieser Mac") -> DeviceCredentialRegistrationResult:
        if not self.supported:
            raise SecurityStateError("device_secret_store_unsupported")
        label = device_label.strip()
        if not 1 <= len(label) <= 80:
            raise SecurityStateError("device_label_invalid")
        self._cleanup_incomplete()
        account = self._account_loader()
        if account.status is not AccountStatus.ACTIVE:
            raise SecurityStateError("device_credential_account_not_active")
        now = self._now()
        secret = self._random.bytes(DEVICE_CREDENTIAL_SECRET_BYTES)
        salt = self._random.bytes(DEVICE_CREDENTIAL_SALT_BYTES)
        if len(secret) != DEVICE_CREDENTIAL_SECRET_BYTES or len(salt) != DEVICE_CREDENTIAL_SALT_BYTES:
            raise SecurityStateError("device_credential_random_invalid")
        credential = DeviceCredential(
            credential_id=self._random.uuid4(),
            installation_id=account.installation_id,
            user_id=account.user_id,
            device_label=label,
            salt=salt,
            secret_hash=hash_device_secret(salt, secret),
            hash_format_version=DEVICE_CREDENTIAL_HASH_FORMAT_VERSION,
            security_epoch_at_issue=self._security_epoch(),
            created_at=now,
            last_used_at=None,
            revoked_at=None,
            status=DeviceCredentialStatus.PENDING,
        )
        self._repository.prepare_device_credential(credential)
        created = False
        try:
            self._secret_store.create(
                installation_id=credential.installation_id,
                credential_id=credential.credential_id,
                secret=secret,
            )
            created = True
            replaced = self._repository.activate_device_credential(
                credential_id=credential.credential_id, now=now
            )
        except Exception:
            try:
                self._repository.revoke_device_credential(
                    credential_id=credential.credential_id, now=self._now()
                )
            except Exception:
                pass
            if created:
                try:
                    self._secret_store.delete(
                        installation_id=credential.installation_id,
                        credential_id=credential.credential_id,
                    )
                except Exception:
                    pass
            raise
        finally:
            secret = b""
        if replaced is not None:
            try:
                self._secret_store.delete(
                    installation_id=credential.installation_id,
                    credential_id=replaced,
                )
            except Exception:
                pass
        active_credential = replace(credential, status=DeviceCredentialStatus.ACTIVE)
        return DeviceCredentialRegistrationResult(active_credential, replaced)

    def authenticate(self, *, require_local_authentication: bool = False) -> DeviceCredentialAuthenticationResult:
        if not self.supported:
            return DeviceCredentialAuthenticationResult(
                DeviceCredentialAuthenticationStatus.UNSUPPORTED
            )
        try:
            self._cleanup_incomplete()
            account = self._account_loader()
            if account.status is not AccountStatus.ACTIVE:
                return DeviceCredentialAuthenticationResult(
                    DeviceCredentialAuthenticationStatus.REJECTED
                )
            credential = self._repository.active_device_credential()
            if credential is None:
                return DeviceCredentialAuthenticationResult(
                    DeviceCredentialAuthenticationStatus.NOT_CONFIGURED
                )
            if credential.security_epoch_at_issue != self._security_epoch():
                self._reject(credential)
                return DeviceCredentialAuthenticationResult(
                    DeviceCredentialAuthenticationStatus.REJECTED
                )
            if require_local_authentication:
                result = self._local_authenticator.authenticate(
                    "Jenaplan-Kompetenzmanager entsperren"
                )
                if result is not LocalAuthenticationResult.SUCCESS:
                    if result in {
                        LocalAuthenticationResult.NOT_AVAILABLE,
                        LocalAuthenticationResult.NOT_ENROLLED,
                        LocalAuthenticationResult.LOCKED_OUT,
                        LocalAuthenticationResult.ERROR,
                    }:
                        status = DeviceCredentialAuthenticationStatus.UNSUPPORTED
                    else:
                        status = DeviceCredentialAuthenticationStatus.REJECTED
                    return DeviceCredentialAuthenticationResult(
                        status, local_authentication_result=result
                    )
            stored = self._secret_store.read(
                installation_id=credential.installation_id,
                credential_id=credential.credential_id,
            )
            if stored.status is not SecretStoreStatus.SUCCESS or stored.secret is None:
                self._reject(credential)
                return DeviceCredentialAuthenticationResult(
                    DeviceCredentialAuthenticationStatus.REJECTED
                )
            secret = stored.secret
            verified = verify_device_secret(credential, secret)
            secret = b""
            if not verified:
                self._reject(credential)
                return DeviceCredentialAuthenticationResult(
                    DeviceCredentialAuthenticationStatus.REJECTED
                )
            if not self._repository.touch_device_credential(
                credential_id=credential.credential_id, now=self._now()
            ):
                return DeviceCredentialAuthenticationResult(
                    DeviceCredentialAuthenticationStatus.REJECTED
                )
            return DeviceCredentialAuthenticationResult(
                DeviceCredentialAuthenticationStatus.AUTHENTICATED, credential
            )
        except SecurityStoreError:
            return DeviceCredentialAuthenticationResult(
                DeviceCredentialAuthenticationStatus.STORE_UNAVAILABLE
            )

    def disable(self) -> bool:
        credential = self._repository.active_device_credential()
        if credential is None:
            return False
        revoked = self._repository.revoke_device_credential(
            credential_id=credential.credential_id, now=self._now()
        )
        try:
            self._secret_store.delete(
                installation_id=credential.installation_id,
                credential_id=credential.credential_id,
            )
        except Exception:
            pass
        return revoked

    def _reject(self, credential: DeviceCredential) -> None:
        try:
            self._repository.revoke_device_credential(
                credential_id=credential.credential_id, now=self._now()
            )
        finally:
            try:
                self._secret_store.delete(
                    installation_id=credential.installation_id,
                    credential_id=credential.credential_id,
                )
            except Exception:
                pass

    def _cleanup_incomplete(self) -> None:
        now = self._now()
        for credential in self._repository.pending_device_credentials():
            try:
                self._repository.revoke_device_credential(
                    credential_id=credential.credential_id, now=now
                )
            except Exception:
                continue
            try:
                self._secret_store.delete(
                    installation_id=credential.installation_id,
                    credential_id=credential.credential_id,
                )
            except Exception:
                pass
        for credential in self._repository.revoked_device_credentials():
            try:
                self._secret_store.delete(
                    installation_id=credential.installation_id,
                    credential_id=credential.credential_id,
                )
            except Exception:
                pass

    def _now(self) -> datetime:
        return self._clock.utc_now()
