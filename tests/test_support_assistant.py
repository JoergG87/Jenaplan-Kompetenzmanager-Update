"""Graphical Support-Assistent workflow, audit and package boundaries."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import plistlib
import secrets
import stat
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from scripts.build_support_assistant_package import build_package, verify_package
from src.security.domain import SupportResetRequest
from src.security.infrastructure.product_support_keys import PRODUCT_SUPPORT_KEY_REGISTRY
from src.security.support_reset import SupportResetTokenCodec
from src.support_assistant.application import (
    SupportAssistantApplicationService,
    SupportAssistantError,
    support_request_reference,
)
from src.support_assistant.product_key import SUPPORT_ASSISTANT_PRODUCT_KEY
from tools.generate_support_keypair import generate_keypair
from tools.generate_support_reset import generate_token_from_request_bytes


NOW = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)
PASSPHRASE = secrets.token_urlsafe(32)


def _manifest(path: Path, private_key: Ed25519PrivateKey, key_id: str = "support-test") -> Path:
    public = private_key.public_key().public_bytes_raw()
    value = {
        "format_version": 1,
        "key_id": key_id,
        "algorithm": "Ed25519",
        "public_key": base64.urlsafe_b64encode(public).decode("ascii").rstrip("="),
        "status": "active",
        "not_before": "2026-07-20T00:00:00Z",
        "not_after": "2026-07-21T00:00:00Z",
        "fingerprint_sha256": hashlib.sha256(public).hexdigest(),
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _private_key(path: Path, key_id: str = "support-test") -> tuple[Path, Ed25519PrivateKey]:
    private = Ed25519PrivateKey.generate()
    from cryptography.hazmat.primitives import serialization

    payload = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(PASSPHRASE.encode("utf-8")),
    )
    path.write_bytes(payload)
    path.chmod(0o600)
    return path, private


def _request_bytes(**changes) -> bytes:
    values = {
        "format_version": 1,
        "installation_id": "11111111-1111-4111-8111-111111111111",
        "user_id": "22222222-2222-4222-8222-222222222222",
        "reset_request_id": "33333333-3333-4333-8333-333333333333",
        "action": "reset_local_password_v1",
        "created_at": NOW - timedelta(minutes=5),
        "expires_at": NOW + timedelta(hours=20),
        "nonce": base64.urlsafe_b64encode(b"n" * 32).decode("ascii").rstrip("="),
    }
    values.update(changes)
    return SupportResetTokenCodec.canonical_request_bytes(SupportResetRequest(**values))


def _service(tmp_path: Path) -> tuple[SupportAssistantApplicationService, Path, Path]:
    private_path, private = _private_key(tmp_path / "private.pem")
    manifest = _manifest(tmp_path / "public.json", private)
    audit = tmp_path / "support audit" / "audit.jsonl"
    service = SupportAssistantApplicationService.from_manifest(
        manifest, audit_path=audit, now_fn=lambda: NOW
    )
    return service, private_path, audit


def test_packaged_public_key_matches_the_approved_product_registry() -> None:
    product = PRODUCT_SUPPORT_KEY_REGISTRY["keys"][0]
    expected = {
        "format_version": 1,
        "key_id": product["key_id"],
        "algorithm": product["algorithm"],
        "public_key": product["public_key"],
        "status": product["status"],
        "not_before": product["not_before"],
        "not_after": product["not_after"],
        "fingerprint_sha256": product["fingerprint_sha256"],
    }
    assert SUPPORT_ASSISTANT_PRODUCT_KEY == expected


def test_valid_request_projection_is_minimal_and_reference_is_not_a_binding(
    tmp_path: Path,
) -> None:
    service, _private, _audit = _service(tmp_path)
    loaded = service.inspect_request_bytes(_request_bytes())
    assert loaded.projection.application_name == "Jenaplan-Kompetenzmanager"
    assert loaded.projection.username is None
    assert loaded.projection.installation_id_short == "11111111…1111"
    assert loaded.projection.status == "valid"
    assert support_request_reference("Laura MacBook", loaded.request.reset_request_id).startswith(
        "JKM-LAURA-"
    )
    assert support_request_reference("anderes Gerät", loaded.request.reset_request_id).startswith(
        "JKM-ANDERES-"
    )
    assert loaded.request.installation_id == "11111111-1111-4111-8111-111111111111"


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"not-json", "request_invalid"),
        (_request_bytes(expires_at=NOW), "request_expired"),
        (_request_bytes(created_at=NOW + timedelta(minutes=1)), "request_not_yet_valid"),
    ],
)
def test_invalid_or_inactive_request_is_rejected_before_key_use(
    tmp_path: Path, payload: bytes, code: str
) -> None:
    service, _private, _audit = _service(tmp_path)
    with pytest.raises(SupportAssistantError) as captured:
        service.inspect_request_bytes(payload)
    assert captured.value.code == code


def test_generation_is_protocol_identical_and_audit_contains_only_four_fields(
    tmp_path: Path,
) -> None:
    service, private_path, audit = _service(tmp_path)
    request_bytes = _request_bytes()
    loaded = service.inspect_request_bytes(request_bytes)
    generated = service.generate_reset_code(
        loaded_request=loaded,
        private_key_path=private_path,
        passphrase=PASSPHRASE,
        lifetime_minutes=30,
    )
    expected = generate_token_from_request_bytes(
        request_bytes=request_bytes,
        private_key_path=private_path,
        key_id="support-test",
        passphrase=PASSPHRASE.encode("utf-8"),
        now=NOW,
        lifetime=timedelta(minutes=30),
    )
    assert generated.token == expected
    payload, _canonical, _signature = SupportResetTokenCodec.decode(generated.token)
    assert payload.installation_id == loaded.request.installation_id
    assert payload.reset_request_id == loaded.request.reset_request_id
    assert payload.nonce == loaded.request.nonce
    record = json.loads(audit.read_text(encoding="utf-8"))
    assert record == {
        "timestamp": "2026-07-20T10:00:00Z",
        "request_id": loaded.request.reset_request_id,
        "key_id": "support-test",
        "action": "reset_code_created",
    }
    audit_text = audit.read_text(encoding="utf-8")
    assert generated.token not in audit_text
    assert PASSPHRASE not in audit_text
    assert loaded.request.nonce not in audit_text
    assert stat.S_IMODE(audit.stat().st_mode) == 0o600
    assert stat.S_IMODE(audit.parent.stat().st_mode) == 0o700


def test_wrong_private_key_and_insecure_permissions_fail_without_audit(tmp_path: Path) -> None:
    service, private_path, audit = _service(tmp_path)
    loaded = service.inspect_request_bytes(_request_bytes())
    wrong_path, _wrong = _private_key(tmp_path / "wrong.pem")
    with pytest.raises(SupportAssistantError) as mismatch:
        service.generate_reset_code(
            loaded_request=loaded,
            private_key_path=wrong_path,
            passphrase=PASSPHRASE,
            lifetime_minutes=30,
        )
    assert mismatch.value.code == "private_key_mismatch"
    private_path.chmod(0o644)
    with pytest.raises(SupportAssistantError) as permissions:
        service.generate_reset_code(
            loaded_request=loaded,
            private_key_path=private_path,
            passphrase=PASSPHRASE,
            lifetime_minutes=30,
        )
    assert permissions.value.code == "private_key_permissions"
    assert not audit.exists()


def test_token_file_is_explicit_restrictive_and_never_overwritten(tmp_path: Path) -> None:
    service, private_path, _audit = _service(tmp_path)
    generated = service.generate_reset_code(
        loaded_request=service.inspect_request_bytes(_request_bytes()),
        private_key_path=private_path,
        passphrase=PASSPHRASE,
        lifetime_minutes=15,
    )
    target = tmp_path / "reset-code"
    saved = service.save_reset_code(target, generated.token)
    assert saved.suffix == ".jkmresettoken"
    assert saved.read_text(encoding="ascii").strip() == generated.token
    assert stat.S_IMODE(saved.stat().st_mode) == 0o600
    with pytest.raises(SupportAssistantError) as captured:
        service.save_reset_code(saved, generated.token)
    assert captured.value.code == "token_target_exists"


def test_support_assistant_sources_have_no_product_runtime_or_network_access() -> None:
    source_paths = [
        *Path("src/support_assistant").glob("*.py"),
        Path("support_tools/support_assistant_app.py"),
    ]
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
    assert "sqlite3" not in sources
    assert "kompetenzmanager.sqlite" not in sources
    assert "security.sqlite" not in sources
    assert "jkmbackup" not in sources
    assert "src.desktop_app" not in sources
    assert "src.application" not in sources
    assert "socket" not in sources
    assert "urllib" not in sources
    assert "requests" not in sources


def test_support_assistant_package_is_separate_and_contains_no_runtime_data(
    tmp_path: Path,
) -> None:
    app = tmp_path / "Jenaplan Support-Assistent.app"
    contents = app / "Contents"
    executable = contents / "MacOS" / "Jenaplan Support-Assistent"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"synthetic arm64 executable")
    executable.chmod(0o755)
    (contents / "Info.plist").write_bytes(
        plistlib.dumps(
            {
                "CFBundleIdentifier": "de.jenaplan.support-assistent",
                "CFBundleDisplayName": "Jenaplan Support-Assistent",
            }
        )
    )
    output = build_package(
        app_bundle=app,
        output_root=tmp_path / "dist",
        version="0.2.2",
        build_commit="eb1fdfe",
        source_tree_state="dirty",
    )
    verify_package(output)
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert any("Jenaplan Support-Assistent.app/Contents/MacOS" in name for name in names)
        assert not any(Path(name).suffix.lower() in {
            ".sqlite", ".db", ".jkmbackup", ".jkmresetrequest", ".jkmresettoken", ".pem"
        } for name in names)
        assert not any("Jenaplan-Kompetenzmanager.app" in name for name in names)
    assert "build_macos_support_assistant" not in Path(
        "scripts/build_macos_pilot.sh"
    ).read_text(encoding="utf-8")
    assert "Support-Assistent" not in Path(
        "scripts/build_laura_pilot_package.py"
    ).read_text(encoding="utf-8")
