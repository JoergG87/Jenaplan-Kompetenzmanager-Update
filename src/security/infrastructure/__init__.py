"""Infrastructure adapters for the isolated local security core."""

from .argon2_hasher import Argon2idPasswordHasher
from .ed25519 import Ed25519SignatureVerifier
from .key_registry import DEFAULT_SUPPORT_KEY_REGISTRY, PublicKeyRegistry
from .sqlite_repository import SQLiteSecurityRepository
from .system import (
    EnrollmentMarkerFile,
    PlatformFilePermissionManager,
    SystemClock,
    SystemRandomSource,
)
from .platform_auth import (
    MacOSKeychainSecretStore,
    MacOSLocalDeviceAuthenticator,
    UnsupportedDeviceSecretStore,
    UnsupportedLocalDeviceAuthenticator,
    build_platform_authentication_adapters,
)

__all__ = [
    "Argon2idPasswordHasher",
    "Ed25519SignatureVerifier",
    "PublicKeyRegistry",
    "DEFAULT_SUPPORT_KEY_REGISTRY",
    "EnrollmentMarkerFile",
    "PlatformFilePermissionManager",
    "SQLiteSecurityRepository",
    "SystemClock",
    "SystemRandomSource",
]
