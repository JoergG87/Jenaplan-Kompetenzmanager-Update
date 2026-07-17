"""Platform secret-store and local-authentication adapters."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import sys

from ..domain import (
    DEVICE_CREDENTIAL_SECRET_BYTES,
    LocalAuthenticationAvailability,
    LocalAuthenticationResult,
    SecretStoreReadResult,
    SecretStoreStatus,
    SecurityStoreError,
    validate_uuid4,
)


_SERVICE = "de.jenaplan.kompetenzmanager.device-credential"
_ERR_SEC_SUCCESS = 0
_ERR_SEC_DUPLICATE_ITEM = -25299
_ERR_SEC_ITEM_NOT_FOUND = -25300
_ERR_SEC_AUTH_FAILED = -25293
_ERR_SEC_INTERACTION_NOT_ALLOWED = -25308
_ERR_SEC_USER_CANCELED = -128


def _account(installation_id: str, credential_id: str) -> bytes:
    return f"v1:{validate_uuid4(installation_id)}:{validate_uuid4(credential_id)}".encode(
        "ascii"
    )


class UnsupportedDeviceSecretStore:
    @property
    def supported(self) -> bool:
        return False

    def create(self, *, installation_id: str, credential_id: str, secret: bytes) -> None:
        raise SecurityStoreError("device_secret_store_unsupported")

    def read(self, *, installation_id: str, credential_id: str) -> SecretStoreReadResult:
        return SecretStoreReadResult(SecretStoreStatus.UNSUPPORTED)

    def delete(self, *, installation_id: str, credential_id: str) -> bool:
        return False


class UnsupportedLocalDeviceAuthenticator:
    def availability(self) -> LocalAuthenticationAvailability:
        return LocalAuthenticationAvailability.UNSUPPORTED

    def authenticate(self, reason: str) -> LocalAuthenticationResult:
        return LocalAuthenticationResult.NOT_AVAILABLE


class _MacOSSecurityBridge:
    def __init__(self, path: Path | None = None) -> None:
        bridge_path = path or self._default_path()
        try:
            self.library = ctypes.CDLL(str(bridge_path))
        except OSError as error:
            raise SecurityStoreError("macos_security_bridge_unavailable") from error
        self.library.jkm_keychain_create.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t,
        ]
        self.library.jkm_keychain_create.restype = ctypes.c_int32
        self.library.jkm_keychain_read.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8)),
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self.library.jkm_keychain_read.restype = ctypes.c_int32
        self.library.jkm_keychain_delete.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.library.jkm_keychain_delete.restype = ctypes.c_int32
        self.library.jkm_secret_free.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t,
        ]
        self.library.jkm_secret_free.restype = None
        self.library.jkm_local_auth_availability.argtypes = []
        self.library.jkm_local_auth_availability.restype = ctypes.c_int32
        self.library.jkm_local_authenticate.argtypes = [ctypes.c_char_p]
        self.library.jkm_local_authenticate.restype = ctypes.c_int32

    @staticmethod
    def _default_path() -> Path:
        override = os.environ.get("JKM_MACOS_SECURITY_BRIDGE", "").strip()
        if override:
            return Path(override)
        frozen_root = getattr(sys, "_MEIPASS", None)
        packaged = (
            Path(frozen_root) / "libjkm_macos_security.dylib"
            if frozen_root
            else Path("__missing_packaged_bridge__")
        )
        if packaged.is_file():
            return packaged
        return Path(__file__).resolve().parents[3] / "build" / "macos-security" / "libjkm_macos_security.dylib"


class MacOSKeychainSecretStore:
    def __init__(self, bridge: _MacOSSecurityBridge | None = None) -> None:
        self._bridge = bridge or _MacOSSecurityBridge()

    @property
    def supported(self) -> bool:
        return True

    def create(self, *, installation_id: str, credential_id: str, secret: bytes) -> None:
        if len(secret) != DEVICE_CREDENTIAL_SECRET_BYTES:
            raise SecurityStoreError("device_secret_length_invalid")
        buffer = (ctypes.c_uint8 * len(secret)).from_buffer_copy(secret)
        status = int(
            self._bridge.library.jkm_keychain_create(
                _SERVICE.encode("ascii"),
                _account(installation_id, credential_id),
                buffer,
                len(secret),
            )
        )
        ctypes.memset(buffer, 0, len(secret))
        if status == _ERR_SEC_DUPLICATE_ITEM:
            raise SecurityStoreError("device_secret_already_exists")
        if status != _ERR_SEC_SUCCESS:
            raise SecurityStoreError("device_secret_create_failed")

    def read(self, *, installation_id: str, credential_id: str) -> SecretStoreReadResult:
        pointer = ctypes.POINTER(ctypes.c_uint8)()
        length = ctypes.c_size_t()
        status = int(
            self._bridge.library.jkm_keychain_read(
                _SERVICE.encode("ascii"),
                _account(installation_id, credential_id),
                ctypes.byref(pointer),
                ctypes.byref(length),
            )
        )
        if status == _ERR_SEC_ITEM_NOT_FOUND:
            return SecretStoreReadResult(SecretStoreStatus.NOT_FOUND)
        if status in {
            _ERR_SEC_AUTH_FAILED,
            _ERR_SEC_INTERACTION_NOT_ALLOWED,
            _ERR_SEC_USER_CANCELED,
        }:
            return SecretStoreReadResult(SecretStoreStatus.ACCESS_DENIED)
        if status != _ERR_SEC_SUCCESS:
            return SecretStoreReadResult(SecretStoreStatus.ERROR)
        try:
            if length.value != DEVICE_CREDENTIAL_SECRET_BYTES:
                return SecretStoreReadResult(SecretStoreStatus.ERROR)
            secret = ctypes.string_at(pointer, length.value)
            return SecretStoreReadResult(SecretStoreStatus.SUCCESS, secret)
        finally:
            self._bridge.library.jkm_secret_free(pointer, length)

    def delete(self, *, installation_id: str, credential_id: str) -> bool:
        status = int(
            self._bridge.library.jkm_keychain_delete(
                _SERVICE.encode("ascii"), _account(installation_id, credential_id)
            )
        )
        if status == _ERR_SEC_ITEM_NOT_FOUND:
            return False
        if status != _ERR_SEC_SUCCESS:
            raise SecurityStoreError("device_secret_delete_failed")
        return True


class MacOSLocalDeviceAuthenticator:
    def __init__(self, bridge: _MacOSSecurityBridge | None = None) -> None:
        self._bridge = bridge or _MacOSSecurityBridge()

    def availability(self) -> LocalAuthenticationAvailability:
        code = int(self._bridge.library.jkm_local_auth_availability())
        return {
            0: LocalAuthenticationAvailability.AVAILABLE,
            3: LocalAuthenticationAvailability.NOT_AVAILABLE,
            4: LocalAuthenticationAvailability.NOT_ENROLLED,
            5: LocalAuthenticationAvailability.LOCKED_OUT,
        }.get(code, LocalAuthenticationAvailability.ERROR)

    def authenticate(self, reason: str) -> LocalAuthenticationResult:
        encoded = reason.encode("utf-8")
        code = int(self._bridge.library.jkm_local_authenticate(encoded))
        return {
            0: LocalAuthenticationResult.SUCCESS,
            1: LocalAuthenticationResult.USER_CANCEL,
            2: LocalAuthenticationResult.FALLBACK_REQUESTED,
            3: LocalAuthenticationResult.NOT_AVAILABLE,
            4: LocalAuthenticationResult.NOT_ENROLLED,
            5: LocalAuthenticationResult.LOCKED_OUT,
            6: LocalAuthenticationResult.SYSTEM_CANCEL,
            7: LocalAuthenticationResult.FAILED,
        }.get(code, LocalAuthenticationResult.ERROR)


def build_platform_authentication_adapters():
    if sys.platform != "darwin":
        return UnsupportedDeviceSecretStore(), UnsupportedLocalDeviceAuthenticator()
    try:
        bridge = _MacOSSecurityBridge()
    except SecurityStoreError:
        return UnsupportedDeviceSecretStore(), UnsupportedLocalDeviceAuthenticator()
    return MacOSKeychainSecretStore(bridge), MacOSLocalDeviceAuthenticator(bridge)
