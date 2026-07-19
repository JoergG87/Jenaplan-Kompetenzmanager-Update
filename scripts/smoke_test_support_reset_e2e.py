"""Run the real packaged .command through a complete synthetic reset lifecycle."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import pty
import select
import sqlite3
import stat
import tempfile
import time
import uuid
import zipfile
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives import serialization

from src.application.commands.backup import BackupApplicationService, CreateBackupCommand
from src.application.commands.security_backup import VerifiedSecurityBackupAdapter
from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.runtime import prepare_runtime_storage, prepare_security_runtime_storage
from src.security.domain import (
    AuthenticationStatus,
    DeviceCredential,
    DeviceCredentialStatus,
    RecoveryStatus,
    SecurityStoreState,
    SupportPublicKey,
    SupportPublicKeyStatus,
    SupportResetRejected,
)
from src.security.infrastructure import (
    Argon2idPasswordHasher,
    Ed25519SignatureVerifier,
    EnrollmentMarkerFile,
    PlatformFilePermissionManager,
    PublicKeyRegistry,
    SQLiteSecurityRepository,
    SystemClock,
    SystemRandomSource,
)
from src.security.application import SecurityApplicationService
from src.security.support_reset import SupportResetService, SupportResetTokenCodec
from scripts.build_support_reset_package import verify_package
from tools.generate_support_keypair import generate_keypair


OLD_PASSWORD = "synthetisches altes Passwort für den E2E Test"
NEW_PASSWORD = "synthetisches neues Passwort für den E2E Test"
KEY_PASSPHRASE = "Sehr-Starke synthetische Support Passphrase 2026!"
KEY_ID = "support-e2e-test"


def run(package_path: Path) -> dict[str, object]:
    package_path = Path(package_path).resolve(strict=True)
    verify_package(package_path)
    with tempfile.TemporaryDirectory(prefix="jenaplan-support-e2e-") as temporary:
        root = Path(temporary)
        runtime_root = root / "synthetic runtime"
        package_root = root / "Support Paket mit Leerzeichen"
        package_root.mkdir()
        with zipfile.ZipFile(package_path) as archive:
            archive.extractall(package_root)
            for info in archive.infolist():
                mode = (info.external_attr >> 16) & 0o777
                if mode:
                    os.chmod(package_root / info.filename, mode)
        extracted = tuple(package_root.iterdir())
        if len(extracted) != 1:
            raise RuntimeError("support_e2e_package_root_invalid")
        handoff = extracted[0]

        paths = prepare_runtime_storage(data_root=runtime_root)
        prepare_security_runtime_storage(data_root=runtime_root)
        SQLiteDatabase(paths.database).initialize_schema()
        _seed_synthetic_business_data(paths.database)
        business_before = _business_snapshot(paths.database)

        permissions = PlatformFilePermissionManager()
        repository = SQLiteSecurityRepository(paths.security_database, permissions)
        marker = EnrollmentMarkerFile(paths.enrollment_marker, permissions)
        clock = SystemClock()
        random_source = SystemRandomSource()
        security = SecurityApplicationService(
            repository=repository,
            marker=marker,
            password_hasher=Argon2idPasswordHasher(),
            random_source=random_source,
            utc_clock=clock,
            monotonic_clock=clock,
            permissions=permissions,
        )
        enrollment = security.enroll_local_account(OLD_PASSWORD)
        old_recovery_code = enrollment.recovery_codes[0]

        key_directory = root / "external keys"
        key_directory.mkdir(mode=0o700)
        private_path = key_directory / "support-private.pem"
        public_path = key_directory / "support-public.json"
        descriptor = generate_keypair(
            private_path=private_path,
            public_path=public_path,
            key_id=KEY_ID,
            passphrase=KEY_PASSPHRASE.encode("utf-8"),
            created_at=datetime.now(UTC),
        )
        private_key = serialization.load_pem_private_key(
            private_path.read_bytes(), password=KEY_PASSPHRASE.encode("utf-8")
        )
        public_raw = private_key.public_key().public_bytes_raw()
        reset = SupportResetService(
            repository=repository,
            marker=marker,
            random_source=random_source,
            utc_clock=clock,
            key_registry=PublicKeyRegistry(
                (
                    SupportPublicKey(
                        KEY_ID,
                        public_raw,
                        SupportPublicKeyStatus.ACTIVE,
                        datetime.now(UTC) - timedelta(minutes=5),
                        datetime.now(UTC) + timedelta(days=1),
                    ),
                )
            ),
            signature_verifier=Ed25519SignatureVerifier(),
        )
        _create_synthetic_device_credential(repository)
        request = reset.create_request()
        request_path = root / "request.jkmresetrequest"
        request_path.write_bytes(SupportResetTokenCodec.canonical_request_bytes(request))
        os.chmod(request_path, 0o600)
        token_path = root / "signed-reset.jkmresettoken"

        transcript, exit_code = _drive_command(
            handoff / "Jenaplan-Support-Reset.command",
            request_path=request_path,
            private_path=private_path,
            public_path=public_path,
            token_path=token_path,
        )
        if exit_code != 0:
            raise RuntimeError(f"support_e2e_command_failed:{exit_code}")
        token = token_path.read_text(encoding="ascii").strip()
        if KEY_PASSPHRASE in transcript or token in transcript:
            raise RuntimeError("support_e2e_secret_in_transcript")
        if stat.S_IMODE(token_path.stat().st_mode) != 0o600:
            raise RuntimeError("support_e2e_token_permissions_invalid")

        backup = VerifiedSecurityBackupAdapter(
            BackupApplicationService(),
            CreateBackupCommand(
                database_path=paths.database,
                runtime_paths=paths,
                target_path=paths.backups,
                app_version="0.2.0",
                build_commit="35511bf6c73d23b8cb1bb6e3a14f61a1861fc7fe",
                source_tree_state="dirty",
            ),
        )
        result = reset.execute(token, backup=backup)
        if security.security_store_state().state is not SecurityStoreState.PASSWORD_RESET_PENDING:
            raise RuntimeError("support_e2e_pending_state_missing")
        if security.authenticate_password(OLD_PASSWORD).status is not AuthenticationStatus.PASSWORD_RESET_REQUIRED:
            raise RuntimeError("support_e2e_old_password_not_blocked")
        if repository.active_device_credential() is not None:
            raise RuntimeError("support_e2e_device_credential_not_revoked")

        prepared = security.prepare_recovery_password_reset(NEW_PASSWORD)
        if not security.confirm_recovery_password_reset(prepared.recovery_set_id):
            raise RuntimeError("support_e2e_new_recovery_not_confirmed")
        if security.authenticate_password(OLD_PASSWORD).status is AuthenticationStatus.AUTHENTICATED:
            raise RuntimeError("support_e2e_old_password_reaccepted")
        if security.authenticate_password(NEW_PASSWORD).status is not AuthenticationStatus.AUTHENTICATED:
            raise RuntimeError("support_e2e_new_password_rejected")
        if security.verify_and_consume_recovery_code(old_recovery_code).status is RecoveryStatus.ACCEPTED:
            raise RuntimeError("support_e2e_old_recovery_reaccepted")
        if _business_snapshot(paths.database) != business_before:
            raise RuntimeError("support_e2e_business_data_changed")
        try:
            reset.execute(token, backup=backup)
        except SupportResetRejected:
            reused_rejected = True
        else:
            reused_rejected = False
        if not reused_rejected:
            raise RuntimeError("support_e2e_token_reuse_accepted")

        return {
            "command_exit": exit_code,
            "request_id": request.reset_request_id,
            "key_id": descriptor["key_id"],
            "fingerprint_sha256": descriptor["fingerprint_sha256"],
            "backup": str(Path(result.backup.path).name),
            "security_epoch": result.security_epoch,
            "new_recovery_codes": len(prepared.recovery_codes),
            "business_rows": len(business_before),
            "token_reuse_rejected": reused_rejected,
        }


def _drive_command(
    command: Path,
    *,
    request_path: Path,
    private_path: Path,
    public_path: Path,
    token_path: Path,
) -> tuple[str, int]:
    pid, descriptor = pty.fork()
    if pid == 0:
        os.chdir("/")
        os.execve(
            "/bin/zsh",
            ["/bin/zsh", str(command)],
            {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "de_DE.UTF-8"},
        )
    transcript = bytearray()
    cursor = 0

    def expect(text: str, answer: str, timeout: float = 30.0) -> None:
        nonlocal cursor
        needle = text.encode("utf-8")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            position = bytes(transcript).find(needle, cursor)
            if position >= 0:
                cursor = position + len(needle)
                os.write(descriptor, answer.encode("utf-8") + b"\n")
                return
            readable, _writable, _errors = select.select([descriptor], [], [], 0.2)
            if readable:
                try:
                    transcript.extend(os.read(descriptor, 8192))
                except OSError:
                    break
        tail = transcript.decode("utf-8", errors="replace")[-1000:]
        raise RuntimeError(f"support_e2e_prompt_missing:{text}:{tail}")

    expect("Auswahl [1]:", "1")
    expect("Pfad zur .jkmresetrequest-Datei:", str(request_path))
    expect("vom betroffenen Gerät stammt:", "JA")
    expect("verschlüsselten privaten PKCS#8-Schlüssel:", str(private_path))
    expect("zugehörigen öffentlichen Schlüsselbeschreibung:", str(public_path))
    expect("Passphrase für den privaten Schlüssel (Versuch 1/3):", KEY_PASSPHRASE)
    expect("Gültigkeitsdauer 15, 30, 60 oder 120 Minuten [30]:", "30")
    expect("Zielpfad für die Reset-Code-Datei (.jkmresettoken):", str(token_path))
    expect("Reset-Code zusätzlich im Terminal anzeigen? [nein/JA]:", "nein")
    expect("Zum Schließen des Fensters die Eingabetaste drücken", "")

    while True:
        readable, _writable, _errors = select.select([descriptor], [], [], 0.2)
        if readable:
            try:
                transcript.extend(os.read(descriptor, 8192))
            except OSError:
                pass
        finished, status = os.waitpid(pid, os.WNOHANG)
        if finished == pid:
            os.close(descriptor)
            return transcript.decode("utf-8", errors="replace"), os.waitstatus_to_exitcode(status)


def _seed_synthetic_business_data(database: Path) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("INSERT INTO groups VALUES ('group-e2e', 'Testgruppe', 1, 1)")
        connection.execute(
            "INSERT INTO courses VALUES ('course-e2e', 'Testkurs', NULL, '', '', 1, 1)"
        )
        connection.execute(
            "INSERT INTO students VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, NULL)",
            (
                "student-e2e",
                "Synthetisch",
                "Testkind",
                "group-e2e",
                "course-e2e",
                "Nur künstliche E2E-Daten",
                "2026-07-19T12:00:00Z",
                "2026-07-19T12:00:00Z",
            ),
        )
        connection.commit()


def _business_snapshot(database: Path) -> tuple[tuple[object, ...], ...]:
    with sqlite3.connect(database) as connection:
        return tuple(
            connection.execute(
                "SELECT student_id, first_name, last_name, group_id, course_id, student_notes, active "
                "FROM students ORDER BY student_id"
            ).fetchall()
        )


def _create_synthetic_device_credential(
    repository: SQLiteSecurityRepository,
) -> DeviceCredential:
    account = repository.load_account()
    credential = DeviceCredential(
        credential_id=str(uuid.uuid4()),
        installation_id=account.installation_id,
        user_id=account.user_id,
        device_label="Synthetischer Mac",
        salt=b"s" * 16,
        secret_hash=b"h" * 32,
        hash_format_version=1,
        security_epoch_at_issue=repository.security_epoch(),
        created_at=datetime.now(UTC),
        last_used_at=None,
        revoked_at=None,
        status=DeviceCredentialStatus.PENDING,
    )
    repository.prepare_device_credential(credential)
    repository.activate_device_credential(
        credential_id=credential.credential_id, now=datetime.now(UTC)
    )
    return credential


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    result = run(args.package)
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
