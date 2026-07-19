"""ctypes adapter for the small macOS Sparkle bridge."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import sys


class UnsupportedUpdateAdapter:
    @property
    def available(self) -> bool:
        return False

    @property
    def can_check(self) -> bool:
        return False

    def last_check_date(self) -> str | None:
        return None

    def check_for_updates(self) -> None:
        raise RuntimeError("updates_unavailable")


class MacOSSparkleAdapter:
    """Own one process-local Sparkle controller through a stable C ABI."""

    def __init__(self, bridge_path: Path | None = None) -> None:
        path = bridge_path or self._default_bridge_path()
        self._library = ctypes.CDLL(str(path))
        self._library.jkm_sparkle_start.argtypes = []
        self._library.jkm_sparkle_start.restype = ctypes.c_int32
        self._library.jkm_sparkle_can_check.argtypes = []
        self._library.jkm_sparkle_can_check.restype = ctypes.c_int32
        self._library.jkm_sparkle_check_for_updates.argtypes = []
        self._library.jkm_sparkle_check_for_updates.restype = ctypes.c_int32
        self._library.jkm_sparkle_last_check_date.argtypes = []
        self._library.jkm_sparkle_last_check_date.restype = ctypes.c_void_p
        self._library.jkm_sparkle_string_free.argtypes = [ctypes.c_void_p]
        self._library.jkm_sparkle_string_free.restype = None
        if int(self._library.jkm_sparkle_start()) != 0:
            raise RuntimeError("sparkle_start_failed")

    @property
    def available(self) -> bool:
        return True

    @property
    def can_check(self) -> bool:
        return int(self._library.jkm_sparkle_can_check()) == 1

    def last_check_date(self) -> str | None:
        pointer = self._library.jkm_sparkle_last_check_date()
        if not pointer:
            return None
        try:
            value = ctypes.string_at(pointer).decode("utf-8")
            return value or None
        finally:
            self._library.jkm_sparkle_string_free(pointer)

    def check_for_updates(self) -> None:
        if int(self._library.jkm_sparkle_check_for_updates()) != 0:
            raise RuntimeError("sparkle_check_failed")

    @staticmethod
    def _default_bridge_path() -> Path:
        override = os.environ.get("JKM_MACOS_SPARKLE_BRIDGE", "").strip()
        if override:
            return Path(override)
        frozen_root = getattr(sys, "_MEIPASS", None)
        if frozen_root:
            packaged = Path(frozen_root) / "libjkm_macos_sparkle.dylib"
            if packaged.is_file():
                return packaged
        return (
            Path(__file__).resolve().parents[3]
            / "build"
            / "macos-update"
            / "libjkm_macos_sparkle.dylib"
        )


def build_native_update_adapter():
    """Fail closed outside a correctly packaged macOS build."""
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return UnsupportedUpdateAdapter()
    try:
        return MacOSSparkleAdapter()
    except (OSError, RuntimeError):
        return UnsupportedUpdateAdapter()
