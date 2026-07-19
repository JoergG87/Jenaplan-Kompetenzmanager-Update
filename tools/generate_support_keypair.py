#!/usr/bin/env python3
"""Generate an offline Ed25519 support keypair without registry mutation."""

from __future__ import annotations

import argparse
import base64
from datetime import UTC, datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_strong_passphrase(passphrase: bytes) -> None:
    try:
        text = passphrase.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Passphrase must be valid UTF-8.") from error
    categories = sum(
        (
            any(character.islower() for character in text),
            any(character.isupper() for character in text),
            any(character.isdigit() for character in text),
            any(not character.isalnum() for character in text),
        )
    )
    if len(text) < 20 or len(passphrase) < 24 or categories < 3:
        raise ValueError("Passphrase does not meet the minimum strength contract.")
    if "\x00" in text or "\n" in text or "\r" in text:
        raise ValueError("Passphrase contains a forbidden control character.")


def generate_keypair(
    *,
    private_path: Path,
    public_path: Path,
    key_id: str,
    passphrase: bytes,
    created_at: datetime | None = None,
) -> dict[str, object]:
    if not _KEY_ID_PATTERN.fullmatch(key_id):
        raise ValueError("Invalid key_id.")
    validate_strong_passphrase(passphrase)
    private_path = Path(private_path)
    public_path = Path(public_path)
    if private_path == public_path or private_path.exists() or public_path.exists():
        raise FileExistsError("Key output already exists.")
    if not private_path.parent.is_dir() or not public_path.parent.is_dir():
        raise FileNotFoundError("Key output directory does not exist.")

    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(passphrase),
    )
    public_raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    timestamp = created_at or datetime.now(UTC)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Creation time must be timezone-aware.")
    timestamp = timestamp.astimezone(UTC)
    descriptor: dict[str, object] = {
        "format_version": 1,
        "algorithm": "Ed25519",
        "key_id": key_id,
        "public_key": base64.urlsafe_b64encode(public_raw).decode("ascii").rstrip("="),
        "created_at": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "intended_status": "active",
        "fingerprint_sha256": hashlib.sha256(public_raw).hexdigest(),
    }
    public_bytes = json.dumps(
        descriptor,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    _publish_pair(private_path, private_bytes, public_path, public_bytes)
    return descriptor


def _publish_pair(
    private_path: Path, private_bytes: bytes, public_path: Path, public_bytes: bytes
) -> None:
    temporary: list[Path] = []
    published: list[Path] = []
    try:
        for target, payload in ((private_path, private_bytes), (public_path, public_bytes)):
            descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
            temp = Path(name)
            temporary.append(temp)
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        for temp, target in zip(temporary, (private_path, public_path), strict=True):
            os.link(temp, target)
            os.chmod(target, 0o600)
            published.append(target)
    except Exception:
        for path in published:
            path.unlink(missing_ok=True)
        raise
    finally:
        for path in temporary:
            path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--public-key", required=True, type=Path)
    parser.add_argument("--key-id", required=True)
    args = parser.parse_args()
    first = getpass.getpass("Strong private-key passphrase: ").encode("utf-8")
    second = getpass.getpass("Repeat passphrase: ").encode("utf-8")
    if first != second:
        raise SystemExit("Passphrases do not match.")
    generate_keypair(
        private_path=args.private_key,
        public_path=args.public_key,
        key_id=args.key_id,
        passphrase=first,
    )
    print(f"Created encrypted Ed25519 keypair for key_id={args.key_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
