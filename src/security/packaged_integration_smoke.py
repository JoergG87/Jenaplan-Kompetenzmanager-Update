"""Marker-bound Security Sprint 12 checks inside a frozen application.

This module is imported only for the explicit internal packaged-test command.
It never resolves product RuntimePaths and accepts only the existing Sprint-11
temporary-root gate.
"""

from __future__ import annotations

import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import sys
import uuid
from typing import Mapping

from src.core.database_engine import SQLCipherConnectionProvider
from src.core.sqlite_store import SQLiteDatabase
from src.core.final_v4_schema import FinalV4SchemaInitializer
from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import DatabaseKey
from src.security.infrastructure.system import SystemClock, SystemRandomSource
from src.security.integration_gate import (
    SecurityIntegrationError,
    SecurityIntegrationGate,
    SecurityIntegrationGateState,
)
from src.security.integration_orchestrator import (
    SecurityIntegrationOrchestrator,
    SecurityIntegrationPhase,
    prepare_security_integration_test_layout,
)
from src.version import APP_VERSION


PACKAGED_SECURITY_INTEGRATION_ARGUMENT = (
    "--packaged-security-integration-test"
)
PACKAGED_SMOKE_MARKER_ENV = "JENAPLAN_PACKAGED_SMOKE_MARKER"
PACKAGED_SMOKE_MARKER_VALUE = "isolated-v1"
SYNTHETIC_DOCUMENT_PAYLOAD = (
    b"jenaplan-packaged-security-synthetic-document-v1\n" * 257
)
_ALLOWED_CRASH_POINTS = {
    "initial_after_journal_publish",
    "safety_copy_after_publish",
    "documents_after_prepared_generation",
    "phase_encrypted_backup_verified_committed",
}


def run_packaged_security_integration_smoke(
    mode: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Run one sanitized packaged integration step."""
    environment = dict(os.environ if environ is None else environ)
    try:
        if not getattr(sys, "frozen", False):
            raise SecurityIntegrationError(
                "packaged_security_smoke_requires_frozen_app"
            )
        if (
            environment.get(PACKAGED_SMOKE_MARKER_ENV)
            != PACKAGED_SMOKE_MARKER_VALUE
        ):
            raise SecurityIntegrationError(
                "packaged_security_smoke_marker_invalid"
            )
        if mode == "disabled":
            decision = SecurityIntegrationGate().resolve(environment)
            if decision.state is not SecurityIntegrationGateState.DISABLED:
                raise SecurityIntegrationError(
                    "packaged_security_smoke_gate_not_disabled"
                )
            return _emit(
                {
                    "gate": "disabled",
                    "mode": mode,
                    "status": "ok",
                }
            )
        if mode == "initialize":
            root = _raw_root(environment)
            paths = prepare_security_integration_test_layout(
                root=root,
                environ=environment,
            )
            _create_plaintext_installation(paths.root)
            return _emit(
                {
                    "gate": "active",
                    "mode": mode,
                    "status": "ok",
                    "versions": _runtime_versions(),
                }
            )

        paths = SecurityIntegrationGate().require_active(environment)
        if mode == "run":
            report = _orchestrator(paths.root, environment).run()
            _verify_completed(paths.root, environment, restore=False)
            return _emit(
                {
                    "document_count": report.document_count,
                    "gate": "active",
                    "mode": mode,
                    "phase": report.phase,
                    "source_retained": report.source_retained,
                    "status": "ok",
                    "versions": _runtime_versions(),
                }
            )
        if mode == "verify":
            result = _verify_completed(
                paths.root,
                environment,
                restore=True,
            )
            return _emit(
                {
                    "gate": "active",
                    "mode": mode,
                    "phase": SecurityIntegrationPhase.COMPLETED,
                    "restore_document_count": result,
                    "status": "ok",
                    "versions": _runtime_versions(),
                }
            )
        if mode == "wrong-key":
            preflight = _orchestrator(
                paths.root,
                environment,
                wrong_database_key=True,
            ).preflight()
            if preflight.phase is not SecurityIntegrationPhase.BLOCKED:
                raise SecurityIntegrationError(
                    "packaged_security_smoke_wrong_key_not_blocked"
                )
            return _emit(
                {
                    "gate": "active",
                    "mode": mode,
                    "phase": preflight.phase,
                    "status": "ok",
                }
            )
        if mode in {"tamper-backup", "tamper-document"}:
            target = (
                paths.encrypted_backup
                if mode == "tamper-backup"
                else next(
                    item
                    for item in paths.document_storage.iterdir()
                    if item.suffix == ".jkmedoc"
                )
            )
            payload = bytearray(target.read_bytes())
            if not payload:
                raise SecurityIntegrationError(
                    "packaged_security_smoke_tamper_target_empty"
                )
            payload[-1] ^= 0x01
            target.write_bytes(payload)
            preflight = _orchestrator(paths.root, environment).preflight()
            if preflight.phase is not SecurityIntegrationPhase.BLOCKED:
                raise SecurityIntegrationError(
                    "packaged_security_smoke_tamper_not_blocked"
                )
            return _emit(
                {
                    "gate": "active",
                    "mode": mode,
                    "phase": preflight.phase,
                    "status": "ok",
                }
            )
        if mode == "recover":
            report = _orchestrator(paths.root, environment).recover()
            _verify_completed(paths.root, environment, restore=False)
            return _emit(
                {
                    "gate": "active",
                    "mode": mode,
                    "phase": report.phase,
                    "status": "ok",
                }
            )
        if mode.startswith("crash:"):
            crash_point = mode.partition(":")[2]
            if crash_point not in _ALLOWED_CRASH_POINTS:
                raise SecurityIntegrationError(
                    "packaged_security_smoke_crash_point_invalid"
                )

            def crash(point: str) -> None:
                if point == crash_point:
                    os._exit(91)

            _orchestrator(
                paths.root,
                environment,
                fault=crash,
            ).run()
            raise SecurityIntegrationError(
                "packaged_security_smoke_crash_not_reached"
            )
        raise SecurityIntegrationError(
            "packaged_security_smoke_mode_invalid"
        )
    except SecurityIntegrationError as error:
        return _emit_error(mode, error.code)
    except Exception:
        return _emit_error(mode, "packaged_security_smoke_failed")


def _raw_root(environment: Mapping[str, str]) -> Path:
    raw = environment.get("JKM_SECURITY_INTEGRATION_ROOT", "")
    root = Path(raw) if raw else Path()
    if not raw or not root.is_absolute():
        raise SecurityIntegrationError(
            "packaged_security_smoke_root_invalid"
        )
    return root


def _create_plaintext_installation(root: Path) -> None:
    paths = SecurityIntegrationGate().require_active(
        {
            "JKM_SECURITY_INTEGRATION_TEST": "1",
            "JKM_SECURITY_INTEGRATION_ROOT": str(root),
        }
    )
    document_path = paths.source_documents / "synthetic-report.pdf"
    document_path.write_bytes(SYNTHETIC_DOCUMENT_PAYLOAD)
    os.chmod(document_path, 0o600)
    FinalV4SchemaInitializer().initialize(paths.source_database)
    database = SQLiteDatabase(
        paths.source_database,
        create=False,
        initialize_schema=False,
    )
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO groups (group_id, group_name, sort_order, active)
            VALUES ('G-SYNTHETIC', 'Synthetische Testgruppe', 1, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO courses (
                course_id, course_name, color_key, color_name, color_hex,
                sort_order, active, year_level
            )
            VALUES (
                'C-SYNTHETIC', 'Synthetischer Testkurs', '', '', '', 1, 1, 1
            )
            """
        )
        connection.execute(
            """
            INSERT INTO school_years(
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES (
                'SY-SYNTHETIC', '2025/26', '2025-08-01', '2026-07-31',
                'current', '2025-07-01T10:00:00+00:00', NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO students (
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            )
            VALUES (
                'S-SYNTHETIC', 'Fiktiv', 'Pakettest',
                '', 1,
                '2026-07-26T10:00:00+00:00',
                '2026-07-26T10:00:00+00:00',
                NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO student_school_year_assignments(
                assignment_id, student_id, school_year_id, group_id,
                course_id, assignment_status, valid_from, valid_to,
                created_at, updated_at
            ) VALUES (
                'ASG-SYNTHETIC', 'S-SYNTHETIC', 'SY-SYNTHETIC',
                'G-SYNTHETIC', 'C-SYNTHETIC', 'enrolled',
                '2025-08-01', '2026-07-31',
                '2025-07-01T10:00:00+00:00',
                '2025-07-01T10:00:00+00:00'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO documents (
                document_id, student_id, observation_id, title,
                document_type, file_path, original_filename, created_at,
                note, active
            )
            VALUES (
                'DOC-SYNTHETIC', 'S-SYNTHETIC', NULL,
                'Synthetischer Bericht', 'Bericht', ?,
                'Synthetischer Bericht.pdf',
                '2026-07-26T10:00:00+00:00', '', 1
            )
            """,
            (str(document_path),),
        )
        connection.commit()
    os.chmod(paths.source_database, 0o600)


def _orchestrator(
    root: Path,
    environment: Mapping[str, str],
    *,
    wrong_database_key: bool = False,
    fault=None,
) -> SecurityIntegrationOrchestrator:
    dmk, database_key = _keys(root)
    if wrong_database_key:
        database_key = DatabaseKey(
            database_key.key_id,
            database_key.generation,
            hashlib.sha256(
                f"wrong-packaged-database-key:{root.name}".encode("ascii")
            ).digest(),
        )
    return SecurityIntegrationOrchestrator.from_environment(
        environ=environment,
        installation_id=_uuid(root, "installation"),
        database_context_id=_uuid(root, "database"),
        migration_id=_uuid(root, "migration"),
        migration_generation=1,
        dmk_loader=lambda: dmk,
        database_key_loader=lambda _dmk: database_key,
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=SQLCipherConnectionProvider(),
        app_instance_available=lambda: True,
        source_closed_probe=lambda _path: True,
        app_version=APP_VERSION,
        fault_injector=fault,
    )


def _keys(root: Path) -> tuple[LoadedDataMasterKey, DatabaseKey]:
    return (
        LoadedDataMasterKey(
            _uuid(root, "dmk"),
            1,
            hashlib.sha256(
                f"packaged-synthetic-dmk:{root.name}".encode("ascii")
            ).digest(),
        ),
        DatabaseKey(
            _uuid(root, "database-key"),
            1,
            hashlib.sha256(
                f"packaged-synthetic-database-key:{root.name}".encode(
                    "ascii"
                )
            ).digest(),
        ),
    )


def _uuid(root: Path, role: str) -> str:
    raw = bytearray(
        hashlib.sha256(f"{role}:{root.name}".encode("ascii")).digest()[:16]
    )
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))


def _verify_completed(
    root: Path,
    environment: Mapping[str, str],
    *,
    restore: bool,
) -> int:
    paths = SecurityIntegrationGate().require_active(environment)
    if paths.root != root:
        raise SecurityIntegrationError(
            "packaged_security_smoke_root_binding_invalid"
        )
    orchestrator = _orchestrator(root, environment)
    preflight = orchestrator.preflight()
    if preflight.phase is not SecurityIntegrationPhase.COMPLETED:
        raise SecurityIntegrationError(
            "packaged_security_smoke_not_completed"
        )
    runtime = orchestrator.open_runtime()
    if runtime.student_count() != 1:
        raise SecurityIntegrationError(
            "packaged_security_smoke_student_projection_invalid"
        )
    if paths.source_database.read_bytes() != paths.safety_copy.read_bytes():
        raise SecurityIntegrationError(
            "packaged_security_smoke_safety_copy_mismatch"
        )
    encrypted_targets = [
        paths.encrypted_database,
        paths.encrypted_backup,
        *(
            item
            for item in paths.document_storage.iterdir()
            if item.suffix == ".jkmedoc"
        ),
    ]
    if len(encrypted_targets) != 3:
        raise SecurityIntegrationError(
            "packaged_security_smoke_encrypted_inventory_invalid"
        )
    for target in encrypted_targets:
        payload = target.read_bytes()
        if (
            SYNTHETIC_DOCUMENT_PAYLOAD in payload
            or (
                target == paths.encrypted_database
                and payload.startswith(b"SQLite format 3\x00")
            )
        ):
            raise SecurityIntegrationError(
                "packaged_security_smoke_plaintext_leak"
            )
    if not restore:
        return 0
    restored = orchestrator.restore_verified_backup(
        "restore-packaged-security"
    )
    if not restored.database_verified or restored.document_count != 1:
        raise SecurityIntegrationError(
            "packaged_security_smoke_restore_invalid"
        )
    return restored.document_count


def _runtime_versions() -> dict[str, str]:
    import _cffi_backend  # noqa: F401
    import nacl
    from nacl import bindings
    import sqlcipher3

    if bindings.crypto_secretstream_xchacha20poly1305_KEYBYTES != 32:
        raise SecurityIntegrationError(
            "packaged_security_smoke_libsodium_invalid"
        )
    connection = sqlcipher3.connect(":memory:")
    try:
        cipher_version = str(
            connection.execute("PRAGMA cipher_version").fetchone()[0]
        )
    finally:
        connection.close()
    return {
        "cffi": metadata.version("cffi"),
        "cryptography": metadata.version("cryptography"),
        "pynacl": nacl.__version__,
        "pyside6": metadata.version("PySide" + "6"),
        "shiboken6": metadata.version("shiboken6"),
        "sqlcipher": cipher_version,
        "sqlcipher3": metadata.version("sqlcipher3"),
    }


def _emit(payload: dict[str, object]) -> int:
    print(
        json.dumps(payload, ensure_ascii=True, sort_keys=True),
        flush=True,
    )
    return 0


def _emit_error(mode: str, code: str) -> int:
    print(
        json.dumps(
            {
                "error_code": code,
                "mode": mode,
                "status": "blocked",
            },
            ensure_ascii=True,
            sort_keys=True,
        ),
        flush=True,
    )
    return 1
