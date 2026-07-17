#!/usr/bin/env python3
"""Sign one technical support-reset request with an offline private key."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import getpass
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.security.domain import (
    SUPPORT_RESET_ALGORITHM,
    SUPPORT_RESET_TOKEN_DEFAULT_AGE,
    SUPPORT_RESET_TOKEN_MAX_AGE,
    SupportResetPayload,
)
from src.security.support_reset import SupportResetTokenCodec


def generate_token(
    *,
    request_path: Path,
    private_key_path: Path,
    key_id: str,
    passphrase: bytes,
    now: datetime,
    lifetime: timedelta = SUPPORT_RESET_TOKEN_DEFAULT_AGE,
    output_path: Path | None = None,
) -> str:
    if lifetime <= timedelta(0) or lifetime > SUPPORT_RESET_TOKEN_MAX_AGE:
        raise ValueError("Token lifetime must be between one second and two hours.")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Signing time must be timezone-aware.")
    now = now.astimezone(UTC)
    request = SupportResetTokenCodec.decode_request(Path(request_path).read_bytes())
    if now < request.created_at or now >= request.expires_at:
        raise ValueError("Reset request is not active at the signing time.")
    expires_at = min(now + lifetime, request.expires_at)
    private_bytes = Path(private_key_path).read_bytes()
    try:
        private_key = serialization.load_pem_private_key(
            private_bytes, password=passphrase
        )
    except (TypeError, ValueError) as error:
        raise ValueError("Encrypted private key could not be opened.") from error
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Private key is not Ed25519.")
    payload = SupportResetPayload(
        format_version=request.format_version,
        algorithm=SUPPORT_RESET_ALGORITHM,
        key_id=key_id,
        installation_id=request.installation_id,
        user_id=request.user_id,
        reset_request_id=request.reset_request_id,
        action=request.action,
        created_at=now,
        expires_at=expires_at,
        nonce=request.nonce,
    )
    canonical = SupportResetTokenCodec.canonical_payload_bytes(payload)
    token = SupportResetTokenCodec.encode(payload, private_key.sign(canonical))
    if output_path is not None:
        _write_exclusive(Path(output_path), token.encode("ascii") + b"\n")
    return token


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    os.chmod(path, 0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    passphrase = getpass.getpass("Private-key passphrase: ").encode("utf-8")
    token = generate_token(
        request_path=args.request,
        private_key_path=args.private_key,
        key_id=args.key_id,
        passphrase=passphrase,
        now=datetime.now(UTC),
        lifetime=timedelta(minutes=args.minutes),
        output_path=args.output,
    )
    print(
        f"Signed request with key_id={args.key_id}; lifetime={args.minutes} minutes."
    )
    if args.output is None:
        print(token)
    else:
        print(f"Token written with restrictive permissions to {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
