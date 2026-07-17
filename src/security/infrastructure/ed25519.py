"""Ed25519 verification adapter with no algorithm fallback."""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class Ed25519SignatureVerifier:
    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        if (
            not isinstance(public_key, bytes)
            or len(public_key) != 32
            or not isinstance(message, bytes)
            or not isinstance(signature, bytes)
            or len(signature) != 64
        ):
            return False
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
        except (InvalidSignature, ValueError, TypeError):
            return False
        return True
