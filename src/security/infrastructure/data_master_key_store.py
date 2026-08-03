"""Explicit platform DMK store adapters outside the product startup path."""

from __future__ import annotations

import ctypes
import sys

from ..data_keys import (
    DATA_MASTER_KEY_BYTES,
    DataMasterKeyReadResult,
    DataMasterKeyStoreStatus,
)
from ..domain import SecurityStoreError, validate_uuid4
from .platform_auth import _MacOSSecurityBridge


_DATA_MASTER_KEY_SERVICE = "de.jenaplan.kompetenzmanager.data-master-key"
_ERR_SEC_SUCCESS = 0
_ERR_SEC_DUPLICATE_ITEM = -25299
_ERR_SEC_ITEM_NOT_FOUND = -25300
_ERR_SEC_AUTH_FAILED = -25293
_ERR_SEC_INTERACTION_NOT_ALLOWED = -25308
_ERR_SEC_USER_CANCELED = -128
_ERR_SEC_DECODE = -26275


def _data_master_key_account(installation_id: str, key_id: str) -> bytes:
    return f"v1:{validate_uuid4(installation_id)}:{validate_uuid4(key_id)}".encode(
        "ascii"
    )


class UnsupportedDataMasterKeyStore:
    """Fail-closed placeholder used until a Windows DPAPI adapter is supplied."""

    @property
    def supported(self) -> bool:
        return False

    def create(
        self, *, installation_id: str, key_id: str, key_material: bytes
    ) -> None:
        raise SecurityStoreError("data_master_key_store_unsupported")

    def read(
        self, *, installation_id: str, key_id: str
    ) -> DataMasterKeyReadResult:
        return DataMasterKeyReadResult(DataMasterKeyStoreStatus.UNSUPPORTED)

    def delete(self, *, installation_id: str, key_id: str) -> bool:
        return False


class MacOSDataMasterKeyStore:
    """Store DMKs only in a separately namespaced macOS Keychain item."""

    def __init__(self, bridge: _MacOSSecurityBridge | None = None) -> None:
        self._bridge = bridge or _MacOSSecurityBridge()

    @property
    def supported(self) -> bool:
        return True

    def create(
        self, *, installation_id: str, key_id: str, key_material: bytes
    ) -> None:
        if len(key_material) != DATA_MASTER_KEY_BYTES:
            raise SecurityStoreError("data_master_key_length_invalid")
        buffer = (ctypes.c_uint8 * len(key_material)).from_buffer_copy(key_material)
        try:
            status = int(
                self._bridge.library.jkm_keychain_create(
                    _DATA_MASTER_KEY_SERVICE.encode("ascii"),
                    _data_master_key_account(installation_id, key_id),
                    buffer,
                    len(key_material),
                )
            )
        finally:
            ctypes.memset(buffer, 0, len(key_material))
        if status == _ERR_SEC_DUPLICATE_ITEM:
            raise SecurityStoreError("data_master_key_already_exists")
        if status in {
            _ERR_SEC_AUTH_FAILED,
            _ERR_SEC_INTERACTION_NOT_ALLOWED,
            _ERR_SEC_USER_CANCELED,
        }:
            raise SecurityStoreError("data_master_key_access_denied")
        if status != _ERR_SEC_SUCCESS:
            raise SecurityStoreError("data_master_key_create_failed")

    def read(
        self, *, installation_id: str, key_id: str
    ) -> DataMasterKeyReadResult:
        pointer = ctypes.POINTER(ctypes.c_uint8)()
        length = ctypes.c_size_t()
        status = int(
            self._bridge.library.jkm_keychain_read(
                _DATA_MASTER_KEY_SERVICE.encode("ascii"),
                _data_master_key_account(installation_id, key_id),
                ctypes.byref(pointer),
                ctypes.byref(length),
            )
        )
        if status == _ERR_SEC_ITEM_NOT_FOUND:
            return DataMasterKeyReadResult(DataMasterKeyStoreStatus.NOT_FOUND)
        if status in {
            _ERR_SEC_AUTH_FAILED,
            _ERR_SEC_INTERACTION_NOT_ALLOWED,
            _ERR_SEC_USER_CANCELED,
        }:
            return DataMasterKeyReadResult(DataMasterKeyStoreStatus.ACCESS_DENIED)
        if status == _ERR_SEC_DECODE:
            return DataMasterKeyReadResult(DataMasterKeyStoreStatus.CORRUPT)
        if status != _ERR_SEC_SUCCESS:
            return DataMasterKeyReadResult(DataMasterKeyStoreStatus.ERROR)
        try:
            if length.value != DATA_MASTER_KEY_BYTES:
                return DataMasterKeyReadResult(DataMasterKeyStoreStatus.CORRUPT)
            key_material = ctypes.string_at(pointer, length.value)
            return DataMasterKeyReadResult(
                DataMasterKeyStoreStatus.SUCCESS, key_material
            )
        finally:
            self._bridge.library.jkm_secret_free(pointer, length)

    def delete(self, *, installation_id: str, key_id: str) -> bool:
        status = int(
            self._bridge.library.jkm_keychain_delete(
                _DATA_MASTER_KEY_SERVICE.encode("ascii"),
                _data_master_key_account(installation_id, key_id),
            )
        )
        if status == _ERR_SEC_ITEM_NOT_FOUND:
            return False
        if status != _ERR_SEC_SUCCESS:
            raise SecurityStoreError("data_master_key_delete_failed")
        return True


def build_platform_data_master_key_store():
    if sys.platform != "darwin":
        return UnsupportedDataMasterKeyStore()
    try:
        bridge = _MacOSSecurityBridge()
    except SecurityStoreError:
        return UnsupportedDataMasterKeyStore()
    return MacOSDataMasterKeyStore(bridge)
