"""Argon2id implementation with the version-1 password contract."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

from ..domain import SecurityStoreError


ARGON2_MEMORY_COST_KIB = 64 * 1024
ARGON2_TIME_COST = 6
ARGON2_PARALLELISM = 1
ARGON2_SALT_LENGTH = 16
ARGON2_HASH_LENGTH = 32


class Argon2idPasswordHasher:
    """Hash and verify without fallback, logging or credential retention."""

    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST_KIB,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LENGTH,
            salt_len=ARGON2_SALT_LENGTH,
            type=Type.ID,
        )

    def hash(self, password: str, salt: bytes) -> str:
        if len(salt) != ARGON2_SALT_LENGTH:
            raise ValueError("Argon2 salt must contain exactly 16 bytes.")
        try:
            return self._hasher.hash(password, salt=salt)
        except Exception as error:
            raise SecurityStoreError("password_hashing_failed") from error

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except VerifyMismatchError:
            return False
        except (InvalidHashError, VerificationError) as error:
            raise SecurityStoreError("stored_password_hash_invalid") from error

    def needs_rehash(self, password_hash: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(password_hash)
        except InvalidHashError as error:
            raise SecurityStoreError("stored_password_hash_invalid") from error
