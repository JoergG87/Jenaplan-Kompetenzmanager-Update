"""Operational macOS support flow, versioned registry and package boundaries."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
import hashlib
from io import StringIO
import json
from pathlib import Path
import shutil
import stat
import subprocess
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from scripts.build_support_reset_package import build_package, verify_package
from src.security.domain import SupportPublicKeyStatus, SupportResetRequest
from src.security.infrastructure.key_registry import PublicKeyRegistry
from src.security.infrastructure.product_support_keys import PRODUCT_SUPPORT_KEY_REGISTRY
from src.security.support_reset import SupportResetTokenCodec
from support_tools.keypair_cli import run_interactive as run_keypair
from support_tools.support_reset_cli import OperatorInputError, run_interactive
from tools.generate_support_keypair import generate_keypair


NOW = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)
PASSPHRASE = "Sehr-Starke Support Passphrase 2026!"


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


def _keypair(directory: Path, key_id: str = "support-2026-a") -> tuple[Path, Path]:
    private = directory / f"{key_id}-private.pem"
    public = directory / f"{key_id}-public.json"
    generate_keypair(
        private_path=private,
        public_path=public,
        key_id=key_id,
        passphrase=PASSPHRASE.encode(),
        created_at=NOW,
    )
    return private, public


def _inputs(values: list[str]):
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def test_versioned_product_registry_contains_only_approved_public_key() -> None:
    assert PRODUCT_SUPPORT_KEY_REGISTRY == {
        "format_version": 1,
        "keys": (
            {
                "key_id": "support-2026-b",
                "algorithm": "Ed25519",
                "public_key": "qjrZixhRuZd7dGXIvpchvWAdGwGhtlFm2mVTHB0XVUU",
                "status": "active",
                "not_before": "2026-07-19T22:12:15Z",
                "not_after": "9999-12-31T23:59:59Z",
                "revoked_at": None,
                "fingerprint_sha256": (
                    "76e619df93483de9313d5bf592fc852c"
                    "88f1ba7ac5261018801c0fcd5e96be77"
                ),
            },
        ),
    }
    registry = PublicKeyRegistry.from_manifest(PRODUCT_SUPPORT_KEY_REGISTRY)
    assert registry.key_ids() == ("support-2026-b",)
    assert registry.get("support-2026-b").status is SupportPublicKeyStatus.ACTIVE


def test_versioned_registry_validates_active_rotation() -> None:
    private = Ed25519PrivateKey.generate()
    raw = private.public_key().public_bytes_raw()
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    base = {
        "key_id": "support-2026-a",
        "algorithm": "Ed25519",
        "public_key": encoded,
        "status": "active",
        "not_before": "2026-07-19T00:00:00Z",
        "not_after": "2027-07-19T00:00:00Z",
        "revoked_at": None,
        "fingerprint_sha256": hashlib.sha256(raw).hexdigest(),
    }
    registry = PublicKeyRegistry.from_manifest({"format_version": 1, "keys": [base]})
    assert registry.key_ids() == ("support-2026-a",)
    assert registry.get("support-2026-a").status is SupportPublicKeyStatus.ACTIVE

    retired = PublicKeyRegistry.from_manifest(
        {"format_version": 1, "keys": [{**base, "status": "retired"}]}
    )
    assert retired.key_ids() == ()
    assert retired.get("support-2026-a").status is SupportPublicKeyStatus.RETIRED


@pytest.mark.parametrize(
    "change",
    [
        {"algorithm": "Ed448"},
        {"public_key": "not-base64url"},
        {"fingerprint_sha256": "0" * 64},
        {"status": "unknown"},
        {"not_before": "2026-07-19"},
    ],
)
def test_registry_rejects_malformed_or_unknown_records(change: dict) -> None:
    raw = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    record = {
        "key_id": "support-2026-a",
        "algorithm": "Ed25519",
        "public_key": base64.urlsafe_b64encode(raw).decode("ascii").rstrip("="),
        "status": "active",
        "not_before": "2026-07-19T00:00:00Z",
        "not_after": "2027-07-19T00:00:00Z",
        "revoked_at": None,
        "fingerprint_sha256": hashlib.sha256(raw).hexdigest(),
    }
    with pytest.raises(ValueError):
        PublicKeyRegistry.from_manifest(
            {"format_version": 1, "keys": [{**record, **change}]}
        )


def test_interactive_support_flow_writes_bound_token_without_secret_output(tmp_path: Path) -> None:
    private, public = _keypair(tmp_path)
    target = tmp_path / "reset-code.jkmresettoken"
    request_text = _request_bytes().decode("utf-8")
    stdout = StringIO()
    result = run_interactive(
        input_fn=_inputs(
            ["2", request_text, "JA", str(private), str(public), "30", str(target), "nein"]
        ),
        getpass_fn=lambda _prompt: PASSPHRASE,
        output=stdout,
        now_fn=lambda: NOW,
    )
    assert result == 0
    token = target.read_text(encoding="ascii").strip()
    payload, _canonical, _signature = SupportResetTokenCodec.decode(token)
    assert payload.installation_id == "11111111-1111-4111-8111-111111111111"
    assert payload.reset_request_id == "33333333-3333-4333-8333-333333333333"
    assert payload.expires_at - payload.created_at == timedelta(minutes=30)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    visible = stdout.getvalue()
    assert token not in visible
    assert PASSPHRASE not in visible
    assert "11111111-1111-4111-8111-111111111111" not in visible
    assert "nnnn" not in visible


def test_interactive_support_flow_accepts_file_and_optional_explicit_display(tmp_path: Path) -> None:
    private, public = _keypair(tmp_path)
    request = tmp_path / "request.jkmresetrequest"
    request.write_bytes(_request_bytes())
    target = tmp_path / "shown.jkmresettoken"
    stdout = StringIO()
    assert run_interactive(
        input_fn=_inputs(
            ["1", str(request), "JA", str(private), str(public), "15", str(target), "JA"]
        ),
        getpass_fn=lambda _prompt: PASSPHRASE,
        output=stdout,
        now_fn=lambda: NOW,
    ) == 0
    assert target.read_text(encoding="ascii").strip() in stdout.getvalue()
    assert "vertraulich" in stdout.getvalue()


def test_interactive_support_flow_limits_passphrase_attempts_and_never_writes(tmp_path: Path) -> None:
    private, public = _keypair(tmp_path)
    target = tmp_path / "must-not-exist.jkmresettoken"
    attempts = iter(("wrong-1", "wrong-2", "wrong-3"))
    stdout = StringIO()
    with pytest.raises(OperatorInputError, match="drei Versuchen"):
        run_interactive(
            input_fn=_inputs(
                ["2", _request_bytes().decode(), "JA", str(private), str(public)]
            ),
            getpass_fn=lambda _prompt: next(attempts),
            output=stdout,
            now_fn=lambda: NOW,
        )
    assert not target.exists()
    assert "wrong" not in stdout.getvalue()


@pytest.mark.parametrize("minutes", ["0", "14", "121", "abc"])
def test_interactive_support_flow_rejects_invalid_lifetime(tmp_path: Path, minutes: str) -> None:
    private, public = _keypair(tmp_path)
    with pytest.raises(OperatorInputError, match="Gültigkeitsdauer|Zulässig"):
        run_interactive(
            input_fn=_inputs(
                ["2", _request_bytes().decode(), "JA", str(private), str(public), minutes]
            ),
            getpass_fn=lambda _prompt: PASSPHRASE,
            output=StringIO(),
            now_fn=lambda: NOW,
        )


def test_interactive_support_flow_rejects_existing_output_and_wrong_keypair(tmp_path: Path) -> None:
    private, public = _keypair(tmp_path, "support-a")
    _other_private, other_public = _keypair(tmp_path, "support-b")
    base = ["2", _request_bytes().decode(), "JA", str(private)]
    with pytest.raises(OperatorInputError, match="passen nicht"):
        run_interactive(
            input_fn=_inputs([*base, str(other_public)]),
            getpass_fn=lambda _prompt: PASSPHRASE,
            output=StringIO(),
            now_fn=lambda: NOW,
        )
    target = tmp_path / "occupied.jkmresettoken"
    target.write_text("occupied", encoding="ascii")
    with pytest.raises(OperatorInputError, match="existiert bereits"):
        run_interactive(
            input_fn=_inputs([*base, str(public), "30", str(target)]),
            getpass_fn=lambda _prompt: PASSPHRASE,
            output=StringIO(),
            now_fn=lambda: NOW,
        )
    assert target.read_text(encoding="ascii") == "occupied"


def test_keypair_starter_creates_only_external_encrypted_material(tmp_path: Path) -> None:
    directory = tmp_path / "external keys"
    stdout = StringIO()
    assert run_keypair(
        input_fn=_inputs([str(directory), "JA", "support-2026-a"]),
        getpass_fn=_inputs([PASSPHRASE, PASSPHRASE]),
        output=stdout,
        now_fn=lambda: NOW,
    ) == 0
    private = directory / "jenaplan-support-support-2026-a-private.pem"
    public = directory / "jenaplan-support-support-2026-a-public.json"
    assert b"BEGIN ENCRYPTED PRIVATE KEY" in private.read_bytes()
    assert b"BEGIN PRIVATE KEY" not in private.read_bytes()
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(private.stat().st_mode) == 0o600
    descriptor = json.loads(public.read_text())
    assert descriptor["created_at"] == "2026-07-19T12:00:00Z"
    assert descriptor["intended_status"] == "active"
    assert "Registry wurde nicht verändert" in stdout.getvalue()


@pytest.mark.parametrize("exit_code", [0, 37])
def test_command_starts_from_own_spaced_directory_and_propagates_exit(
    tmp_path: Path, exit_code: int
) -> None:
    root = tmp_path / "Support Paket mit Leerzeichen"
    binary = root / "bin" / "Jenaplan-Support-Reset"
    binary.parent.mkdir(parents=True)
    binary.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="ascii")
    binary.chmod(0o755)
    command = root / "Jenaplan-Support-Reset.command"
    shutil.copyfile(
        Path("support_tools/Jenaplan-Support-Reset.command"), command
    )
    command.chmod(0o755)
    completed = subprocess.run(
        ["/bin/zsh", str(command)],
        cwd="/",
        env={"PATH": "/usr/bin:/bin"},
        input="",
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == exit_code
    assert f"Exitcode {exit_code}" in completed.stdout if exit_code else "erfolgreich" in completed.stdout


def test_command_reports_missing_runtime_without_reading_secrets(tmp_path: Path) -> None:
    command = tmp_path / "Jenaplan-Support-Reset.command"
    shutil.copyfile(Path("support_tools/Jenaplan-Support-Reset.command"), command)
    command.chmod(0o755)
    completed = subprocess.run(
        ["/bin/zsh", str(command)],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin"},
        input="",
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 127
    source = command.read_text(encoding="utf-8")
    assert "getpass" not in source
    assert "PASSPHRASE" not in source
    assert "--private" not in source


def test_support_package_is_allowlisted_secret_free_and_separate(tmp_path: Path) -> None:
    reset = tmp_path / "reset-bin"
    keypair = tmp_path / "keypair-bin"
    reset.write_bytes(b"synthetic arm64 executable")
    keypair.write_bytes(b"synthetic arm64 executable")
    reset.chmod(0o755)
    keypair.chmod(0o755)
    package = build_package(
        reset_executable=reset,
        keypair_executable=keypair,
        output_root=tmp_path / "dist",
        version="0.2.0",
        build_commit="35511bf6c73d23b8cb1bb6e3a14f61a1861fc7fe",
        source_tree_state="dirty",
    )
    verify_package(package)
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        assert any(name.endswith("Jenaplan-Support-Reset.command") for name in names)
        assert not any(Path(name).suffix in {".sqlite", ".db", ".pem", ".jkmbackup"} for name in names)
        combined = b"".join(archive.read(name) for name in names)
        assert b"/Users/" not in combined
        assert b"BEGIN ENCRYPTED PRIVATE KEY-----\n" not in combined
    pilot_build = Path("scripts/build_macos_pilot.sh").read_text(encoding="utf-8")
    laura_build = Path("scripts/build_laura_pilot_package.py").read_text(encoding="utf-8")
    assert "build_macos_support_reset_package" not in pilot_build
    assert "Support-Reset-macOS.zip" not in laura_build


def test_support_operator_sources_have_no_network_or_business_database_access() -> None:
    sources = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "support_tools/support_reset_cli.py",
            "tools/generate_support_reset.py",
        )
    )
    assert "kompetenzmanager.sqlite" not in sources
    assert "sqlite3" not in sources
    assert "socket" not in sources
    assert "urllib" not in sources
    assert "requests" not in sources
    assert "subprocess" not in sources
    assert "os.environ" not in sources
