"""Offline support tools, backup adapter and packaging exclusion contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import base64
import json
import os
from pathlib import Path
from types import SimpleNamespace

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
import pytest

from src.application.commands.security_backup import VerifiedSecurityBackupAdapter
from src.security.domain import SupportResetRequest
from src.security.support_reset import SupportResetTokenCodec
from tools.generate_support_keypair import generate_keypair
from tools.generate_support_reset import generate_token


PASSPHRASE = "Sehr-Starke Support Passphrase 2026!".encode("utf-8")
NOW = datetime(2026, 7, 17, 15, 0, tzinfo=UTC)


def request_file(path: Path) -> SupportResetRequest:
    request = SupportResetRequest(
        format_version=1,
        installation_id="11111111-1111-4111-8111-111111111111",
        user_id="22222222-2222-4222-8222-222222222222",
        reset_request_id="33333333-3333-4333-8333-333333333333",
        action="reset_local_password_v1",
        created_at=NOW,
        expires_at=NOW + timedelta(hours=24),
        nonce=base64.urlsafe_b64encode(b"n" * 32).decode("ascii").rstrip("="),
    )
    path.write_bytes(SupportResetTokenCodec.canonical_request_bytes(request))
    return request


def test_keypair_tool_writes_only_encrypted_pkcs8_with_restrictive_permissions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    private_path = tmp_path / "support-private.pem"
    public_path = tmp_path / "support-public.json"
    generate_keypair(
        private_path=private_path,
        public_path=public_path,
        key_id="support-2026-a",
        passphrase=PASSPHRASE,
    )
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
    private_bytes = private_path.read_bytes()
    assert b"BEGIN ENCRYPTED PRIVATE KEY" in private_bytes
    assert b"BEGIN PRIVATE KEY" not in private_bytes
    assert PASSPHRASE not in private_bytes
    assert os.stat(private_path).st_mode & 0o777 == 0o600
    assert os.stat(public_path).st_mode & 0o777 == 0o600
    public = json.loads(public_path.read_text(encoding="utf-8"))
    assert public["algorithm"] == "Ed25519"
    assert public["key_id"] == "support-2026-a"
    assert len(base64.urlsafe_b64decode(public["public_key"] + "=")) == 32
    with pytest.raises(ValueError):
        serialization.load_pem_private_key(private_bytes, password=b"wrong passphrase")


def test_keypair_tool_rejects_weak_passphrase_and_existing_outputs(tmp_path: Path) -> None:
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.json"
    with pytest.raises(ValueError):
        generate_keypair(
            private_path=private_path,
            public_path=public_path,
            key_id="support-2026-a",
            passphrase=b"too short",
        )
    private_path.write_text("occupied", encoding="utf-8")
    with pytest.raises(FileExistsError):
        generate_keypair(
            private_path=private_path,
            public_path=public_path,
            key_id="support-2026-a",
            passphrase=PASSPHRASE,
        )


def test_reset_tool_signs_canonical_request_and_optional_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.json"
    generate_keypair(
        private_path=private_path,
        public_path=public_path,
        key_id="support-2026-a",
        passphrase=PASSPHRASE,
    )
    request_path = tmp_path / "request.json"
    request = request_file(request_path)
    token = generate_token(
        request_path=request_path,
        private_key_path=private_path,
        key_id="support-2026-a",
        passphrase=PASSPHRASE,
        now=NOW + timedelta(minutes=1),
    )
    assert capsys.readouterr().out == ""
    payload, canonical, signature = SupportResetTokenCodec.decode(token)
    assert payload.reset_request_id == request.reset_request_id
    assert payload.expires_at - payload.created_at == timedelta(minutes=30)
    public = json.loads(public_path.read_text(encoding="utf-8"))
    raw = base64.urlsafe_b64decode(public["public_key"] + "=")
    Ed25519PublicKey.from_public_bytes(raw).verify(signature, canonical)

    output = tmp_path / "reset.token"
    same_contract = generate_token(
        request_path=request_path,
        private_key_path=private_path,
        key_id="support-2026-a",
        passphrase=PASSPHRASE,
        now=NOW + timedelta(minutes=2),
        output_path=output,
    )
    assert output.read_text(encoding="ascii").strip() == same_contract
    assert os.stat(output).st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        generate_token(
            request_path=request_path,
            private_key_path=private_path,
            key_id="support-2026-a",
            passphrase=PASSPHRASE,
            now=NOW + timedelta(minutes=3),
            output_path=output,
        )


def test_reset_tool_rejects_wrong_passphrase_and_overlong_token(tmp_path: Path) -> None:
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.json"
    generate_keypair(
        private_path=private_path,
        public_path=public_path,
        key_id="support-2026-a",
        passphrase=PASSPHRASE,
    )
    request_path = tmp_path / "request.json"
    request_file(request_path)
    with pytest.raises(ValueError, match="could not be opened"):
        generate_token(
            request_path=request_path,
            private_key_path=private_path,
            key_id="support-2026-a",
            passphrase=b"wrong",
            now=NOW,
        )
    with pytest.raises(ValueError, match="two hours"):
        generate_token(
            request_path=request_path,
            private_key_path=private_path,
            key_id="support-2026-a",
            passphrase=PASSPHRASE,
            now=NOW,
            lifetime=timedelta(hours=2, seconds=1),
        )


def test_backup_adapter_requires_reverified_published_archive() -> None:
    verification = SimpleNamespace(
        path=Path("/tmp/backup.jkmbackup"), archive_sha256="b" * 64
    )
    created = SimpleNamespace(
        path=verification.path,
        verification=SimpleNamespace(archive_sha256="b" * 64),
    )

    class Service:
        def create(self, _command):
            return created

        def verify(self, query):
            assert query.path == created.path
            return verification

    proof = VerifiedSecurityBackupAdapter(Service(), object()).create_and_verify()
    assert proof.path.endswith("backup.jkmbackup")
    assert proof.sha256 == "b" * 64

    verification.archive_sha256 = "c" * 64
    with pytest.raises(RuntimeError, match="mismatch"):
        VerifiedSecurityBackupAdapter(Service(), object()).create_and_verify()


def test_packaging_includes_core_but_excludes_tools_and_private_key_material() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = (root / "packaging" / "macos_pilot.spec").read_text(encoding="utf-8")
    assert "src.security.support_reset" in spec
    assert "src.security.infrastructure.ed25519" in spec
    assert "cryptography.hazmat.primitives.asymmetric.ed25519" in spec
    assert "tools/generate_support" not in spec
    assert "tests/" not in spec
    tool_source = (root / "tools" / "generate_support_reset.py").read_text(encoding="utf-8")
    assert "kompetenzmanager.sqlite" not in tool_source
    tracked_sources = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (root / "src").rglob("*.py")
    )
    assert "BEGIN PRIVATE KEY" not in tracked_sources
    assert "BEGIN ENCRYPTED PRIVATE KEY" not in tracked_sources
