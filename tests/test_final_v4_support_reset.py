from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import os
from pathlib import Path
import sqlite3
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from src.core.runtime_root_protection import (
    activate_pilot_product_root,
    publish_pilot_product_root,
)
from src.core.maintenance_gate import MaintenanceState
from src.desktop_app.runtime import prepare_cipher_runtime_storage, runtime_paths
from src.security.cipher_product_runtime import open_cipher_product_runtime
from src.desktop_app.main import _build_cipher_product_student_adapter
from src.security.domain import (
    AuthenticationStatus,
    RecoveryStatus,
    SecurityStoreState,
    SupportPublicKey,
    SupportPublicKeyStatus,
    SupportResetFailureCode,
    SupportResetRejected,
)
from src.security.final_v4_backup_runtime import build_final_v4_encrypted_backup_service
from src.security.data_keys import DataMasterKeyReadResult, DataMasterKeyStoreStatus
from src.security.final_v4_support_recovery import (
    FinalV4PreAuthRecoveryFactory,
    FinalV4SupportResetBackupFactory,
)
from src.security.infrastructure import (
    Ed25519SignatureVerifier,
    PlatformFilePermissionManager,
    PublicKeyRegistry,
    SQLiteSecurityRepository,
)
from src.security.startup import build_security_runtime
from src.security.startup import SecurityStartState, SecurityStartupResolver
from src.security.support_reset import SupportResetService
from tests.test_cipher_product_composition import MemoryDataMasterKeyStore
from tests.test_final_v3_document_runtime import _Consumer
from tests.test_final_v4_encrypted_backup import (
    REPORT_DOCUMENT_ID,
    _add_all_document_classes,
)
from tests.test_final_v4_sqlcipher_runtime import requires_exact_417
from tests.test_support_reset import (
    DeterministicRandom,
    MutableClock,
    ToggleFailure,
    signed_token,
)


PASSWORD = "eine ausreichend lange Final V4 Support Reset Passphrase"
NEW_PASSWORD = "eine neue ausreichend lange Final V4 Reset Passphrase"
NOW = datetime(2026, 8, 14, 10, 0, tzinfo=UTC)


def _support_service(runtime, *, random_source=None, repository=None):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    clock = MutableClock(NOW)
    service = SupportResetService(
        repository=repository or runtime.repository,
        marker=runtime.service._marker,
        random_source=random_source or DeterministicRandom(b"final-v4-support"),
        utc_clock=clock,
        key_registry=PublicKeyRegistry(
            (
                SupportPublicKey(
                    "support-final-v4-test",
                    public,
                    SupportPublicKeyStatus.ACTIVE,
                    NOW - timedelta(days=1),
                    NOW + timedelta(days=1),
                ),
            )
        ),
        signature_verifier=Ed25519SignatureVerifier(),
    )
    return service, private, clock


def _case(tmp_path: Path):
    root = (tmp_path / "pilot-product").resolve()
    root.mkdir(mode=0o700)
    publish_pilot_product_root(root)
    paths = runtime_paths(root)
    security = build_security_runtime(paths)
    enrollment = security.service.enroll_local_account(PASSWORD)
    store = MemoryDataMasterKeyStore()
    opened = open_cipher_product_runtime(
        paths=paths,
        account_loader=security.repository.load_account,
        authentication_confirmed=True,
        first_run_allowed=True,
        key_store=store,
    )
    _build_cipher_product_student_adapter(opened)
    prepare_cipher_runtime_storage(data_root=root)
    activate_pilot_product_root(root)
    payloads = _add_all_document_classes(opened.runtime)
    with opened.database.connect() as connection:
        competency = connection.execute(
            "SELECT competency_id, subject_id, subject_name, learning_area, "
            "competency_group, label FROM competencies ORDER BY competency_id LIMIT 1"
        ).fetchone()
        assert competency is not None
        connection.execute(
            """
            INSERT INTO observation_competency_ratings (
                observation_id, competency_id, subject_id,
                subject_display_name, learning_area, competency_group,
                competency_text, rating
            ) VALUES ('OBS-000001', ?, ?, ?, ?, ?, ?, '+')
            """,
            tuple(competency),
        )
        connection.commit()
    return root, paths, security, enrollment, store, opened, payloads


def _technical_snapshot(paths) -> dict[str, str]:
    files = (
        Path(paths.root) / ".jkm-runtime-root-v1",
        paths.keyset_metadata,
        paths.database_key_envelope_registry,
        paths.final_v4_database,
        paths.document_companion_database,
        *sorted(paths.encrypted_document_storage.rglob("*.jkmedoc")),
    )
    return {
        str(path.relative_to(paths.root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }


def _domain_snapshot(opened) -> tuple[tuple[object, ...], ...]:
    queries = (
        "SELECT student_id, first_name, last_name FROM students ORDER BY student_id",
        "SELECT observation_id, student_id, note FROM observations ORDER BY observation_id",
        "SELECT observation_id, competency_id, rating FROM observation_competency_ratings ORDER BY observation_id, competency_id",
        "SELECT report_draft_id, student_id, status FROM report_drafts ORDER BY report_draft_id",
        "SELECT learning_conference_draft_id, student_id, status FROM learning_conference_drafts ORDER BY learning_conference_draft_id",
        "SELECT * FROM learning_report_pdf_artifacts ORDER BY rowid",
        "SELECT * FROM learning_conference_pdf_artifacts ORDER BY rowid",
    )
    with opened.database.connect() as connection:
        return tuple(
            tuple(tuple(row) for row in connection.execute(query).fetchall())
            for query in queries
        )


@requires_exact_417
def test_final_v4_support_reset_preserves_keys_data_and_documents(tmp_path: Path) -> None:
    root, paths, security, enrollment, store, opened, payloads = _case(tmp_path)
    before_keys = (
        opened.dmk_key_id,
        opened.dmk_generation,
        opened.dmk_fingerprint_sha256,
        opened.database_key_id,
        opened.database_key_generation,
        opened.database_context_id,
    )
    before_files = _technical_snapshot(paths)
    before_domain = _domain_snapshot(opened)
    reset, private, clock = _support_service(security)
    request = reset.create_request()
    token = signed_token(
        request,
        private,
        key_id="support-final-v4-test",
    )
    factory = FinalV4PreAuthRecoveryFactory(
        paths=paths,
        account_loader=security.repository.load_account,
        security_store_validator=security.repository.require_current_read_only,
        key_store=store,
        random_source=DeterministicRandom(b"final-v4-backup"),
        clock=clock,
    )

    result = reset.execute(token, backup=factory.create())

    assert Path(result.backup.path).suffix == ".jkmebackup"
    assert Path(result.backup.path).is_file()
    assert security.service.security_store_state().state is SecurityStoreState.PASSWORD_RESET_PENDING
    assert security.service.authenticate_password(PASSWORD).status is AuthenticationStatus.PASSWORD_RESET_REQUIRED
    assert (
        security.service.verify_and_consume_recovery_code(enrollment.recovery_codes[0]).status
        is not RecoveryStatus.ACCEPTED
    )
    restarted_security = build_security_runtime(paths)
    decision = SecurityStartupResolver().resolve(
        restarted_security.service.security_store_state(),
        legacy_installation_present=False,
    )
    assert decision.state is SecurityStartState.PASSWORD_RESET_PENDING
    prepared = restarted_security.service.prepare_recovery_password_reset(NEW_PASSWORD)
    assert prepared.recovery_codes
    assert not set(prepared.recovery_codes).intersection(enrollment.recovery_codes)
    assert restarted_security.service.confirm_recovery_password_reset(
        prepared.recovery_set_id
    )
    assert (
        restarted_security.service.authenticate_password(NEW_PASSWORD).status
        is AuthenticationStatus.AUTHENTICATED
    )

    reopened = open_cipher_product_runtime(
        paths=paths,
        account_loader=restarted_security.repository.load_account,
        authentication_confirmed=True,
        first_run_allowed=False,
        key_store=store,
    )
    after_keys = (
        reopened.dmk_key_id,
        reopened.dmk_generation,
        reopened.dmk_fingerprint_sha256,
        reopened.database_key_id,
        reopened.database_key_generation,
        reopened.database_context_id,
    )
    assert after_keys == before_keys
    assert _technical_snapshot(paths) == before_files
    assert _domain_snapshot(reopened) == before_domain
    consumer = _Consumer()
    reopened.documents.read(document_id=REPORT_DOCUMENT_ID, consumer=consumer)
    assert bytes(consumer.payload) == payloads[REPORT_DOCUMENT_ID]
    assert (root / ".jkm-runtime-root-v1").is_file()

    child = os.fork()
    if child == 0:  # pragma: no cover - asserted through the child exit status
        try:
            child_security = build_security_runtime(paths)
            assert (
                child_security.service.authenticate_password(NEW_PASSWORD).status
                is AuthenticationStatus.AUTHENTICATED
            )
            child_runtime = open_cipher_product_runtime(
                paths=paths,
                account_loader=child_security.repository.load_account,
                authentication_confirmed=True,
                first_run_allowed=False,
                key_store=store,
            )
            assert _domain_snapshot(child_runtime) == before_domain
            child_consumer = _Consumer()
            child_runtime.documents.read(
                document_id=REPORT_DOCUMENT_ID,
                consumer=child_consumer,
            )
            assert bytes(child_consumer.payload) == payloads[REPORT_DOCUMENT_ID]
        except BaseException:
            os._exit(81)
        os._exit(0)
    waited, child_status = os.waitpid(child, 0)
    assert waited == child
    assert os.waitstatus_to_exitcode(child_status) == 0


@requires_exact_417
def test_final_v4_support_reset_backup_conflict_keeps_old_auth_valid(tmp_path: Path) -> None:
    _root, paths, security, enrollment, store, _opened, _payloads = _case(tmp_path)
    reset, private, clock = _support_service(security)
    request = reset.create_request()
    token = signed_token(
        request,
        private,
        key_id="support-final-v4-test",
    )
    random_source = DeterministicRandom(b"conflicting-final-v4-backup")
    expected_random = DeterministicRandom(b"conflicting-final-v4-backup")
    conflict = paths.backups / (
        f"support-reset-safety-{NOW.strftime('%Y%m%dT%H%M%SZ')}-"
        f"{expected_random.uuid4()}.jkmebackup"
    )
    conflict.write_bytes(b"existing no-clobber target")
    factory = FinalV4PreAuthRecoveryFactory(
        paths=paths,
        account_loader=security.repository.load_account,
        security_store_validator=security.repository.require_current_read_only,
        key_store=store,
        random_source=random_source,
        clock=clock,
    )
    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(token, backup=factory.create())

    assert caught.value.code is SupportResetFailureCode.BACKUP_FAILED
    assert security.service.security_store_state().state is SecurityStoreState.READY
    assert security.repository.security_epoch() == 1
    assert security.service.authenticate_password(PASSWORD).status is AuthenticationStatus.AUTHENTICATED
    assert (
        security.service.verify_and_consume_recovery_code(enrollment.recovery_codes[0]).status
        is RecoveryStatus.ACCEPTED
    )
    assert store.create_calls == 1


@requires_exact_417
def test_authenticated_final_v4_support_reset_releases_maintenance_after_commit(
    tmp_path: Path,
) -> None:
    _root, paths, security, _enrollment, store, opened, _payloads = _case(tmp_path)
    reset, private, clock = _support_service(security)
    request = reset.create_request()
    backup_service = build_final_v4_encrypted_backup_service(
        opened_runtime=opened.runtime,
        account_loader=security.repository.load_account,
        environ={},
        key_store=store,
        product_paths=paths,
        random_source=DeterministicRandom(b"authenticated-final-v4-backup"),
        clock=clock,
    )
    backup_factory = FinalV4SupportResetBackupFactory(
        service=backup_service,
        backup_root=paths.backups,
        random_source=DeterministicRandom(b"authenticated-final-v4-target"),
        clock=clock,
    )

    result = reset.execute(
        signed_token(request, private, key_id="support-final-v4-test"),
        backup=backup_factory.create(),
    )

    assert Path(result.backup.path).suffix == ".jkmebackup"
    assert backup_service._gate.state is MaintenanceState.NORMAL
    assert security.service.security_store_state().state is SecurityStoreState.PASSWORD_RESET_PENDING


@requires_exact_417
def test_authenticated_backup_revalidation_failure_releases_maintenance(
    tmp_path: Path,
) -> None:
    _root, paths, security, enrollment, store, opened, _payloads = _case(tmp_path)
    reset, private, clock = _support_service(security)
    request = reset.create_request()
    backup_service = build_final_v4_encrypted_backup_service(
        opened_runtime=opened.runtime,
        account_loader=security.repository.load_account,
        environ={},
        key_store=store,
        product_paths=paths,
        random_source=DeterministicRandom(b"expiring-final-v4-backup"),
        clock=clock,
    )
    port = FinalV4SupportResetBackupFactory(
        service=backup_service,
        backup_root=paths.backups,
        random_source=DeterministicRandom(b"expiring-final-v4-target"),
        clock=clock,
    ).create()

    class ExpiringPort:
        def create_and_verify(self):
            proof = port.create_and_verify()
            clock.now += timedelta(hours=1)
            return proof

        def finish(self, *, reset_committed: bool) -> None:
            port.finish(reset_committed=reset_committed)

    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(
            signed_token(request, private, key_id="support-final-v4-test"),
            backup=ExpiringPort(),
        )

    assert caught.value.code is SupportResetFailureCode.TOKEN_EXPIRED
    assert backup_service._gate.state is MaintenanceState.NORMAL
    assert security.repository.security_epoch() == 1
    assert security.service.authenticate_password(PASSWORD).status is AuthenticationStatus.AUTHENTICATED
    assert (
        security.service.verify_and_consume_recovery_code(enrollment.recovery_codes[0]).status
        is RecoveryStatus.ACCEPTED
    )


@requires_exact_417
def test_authenticated_precommit_failure_releases_maintenance(
    tmp_path: Path,
) -> None:
    _root, paths, security, enrollment, store, opened, _payloads = _case(tmp_path)
    failure = ToggleFailure()
    repository = SQLiteSecurityRepository(
        paths.security_database,
        PlatformFilePermissionManager(),
        failure_injector=failure,
    )
    reset, private, clock = _support_service(security, repository=repository)
    request = reset.create_request()
    backup_service = build_final_v4_encrypted_backup_service(
        opened_runtime=opened.runtime,
        account_loader=repository.load_account,
        environ={},
        key_store=store,
        product_paths=paths,
        random_source=DeterministicRandom(b"precommit-final-v4-backup"),
        clock=clock,
    )
    port = FinalV4SupportResetBackupFactory(
        service=backup_service,
        backup_root=paths.backups,
        random_source=DeterministicRandom(b"precommit-final-v4-target"),
        clock=clock,
    ).create()
    failure.point = "before_write_commit"

    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(
            signed_token(request, private, key_id="support-final-v4-test"),
            backup=port,
        )

    failure.point = None
    assert caught.value.code is SupportResetFailureCode.RUNTIME_RECOVERY_REQUIRED
    assert backup_service._gate.state is MaintenanceState.NORMAL
    assert repository.security_epoch() == 1
    assert security.service.authenticate_password(PASSWORD).status is AuthenticationStatus.AUTHENTICATED
    assert (
        security.service.verify_and_consume_recovery_code(enrollment.recovery_codes[0]).status
        is RecoveryStatus.ACCEPTED
    )


@requires_exact_417
@pytest.mark.parametrize(
    "damage",
    (
        "dmk_missing",
        "dmk_access_denied",
        "dmk_wrong_key_id",
        "dmk_wrong_generation",
        "dmk_corrupt",
        "database_missing",
        "envelope_tampered",
        "companion_missing",
        "document_trailing_bytes",
        "root_marker_tampered",
    ),
)
def test_final_v4_support_reset_preflight_damage_is_fail_closed(
    tmp_path: Path, damage: str
) -> None:
    root, paths, security, _enrollment, store, _opened, _payloads = _case(tmp_path)
    if damage == "dmk_missing":
        store.values.clear()
    elif damage == "dmk_access_denied":
        store.read = lambda **_kwargs: DataMasterKeyReadResult(
            DataMasterKeyStoreStatus.ACCESS_DENIED
        )
    elif damage == "dmk_wrong_key_id":
        with sqlite3.connect(paths.keyset_metadata) as connection:
            connection.execute(
                "UPDATE data_keysets SET key_id = ? WHERE status = 'active'",
                (str(uuid.uuid4()),),
            )
    elif damage == "dmk_wrong_generation":
        with sqlite3.connect(paths.keyset_metadata) as connection:
            connection.execute(
                "UPDATE data_keysets SET generation = 2 WHERE status = 'active'"
            )
    elif damage == "dmk_corrupt":
        identity = next(iter(store.values))
        store.values[identity] = b"x" * 32
    elif damage == "database_missing":
        paths.final_v4_database.rename(root / "missing-final-v4.sqlcipher")
    elif damage == "envelope_tampered":
        paths.database_key_envelope_registry.write_bytes(b"{}")
    elif damage == "companion_missing":
        paths.document_companion_database.rename(root / "missing-companion.sqlcipher")
    elif damage == "document_trailing_bytes":
        container = next(paths.encrypted_document_storage.rglob("*.jkmedoc"))
        with container.open("ab") as stream:
            stream.write(b"trailing")
    elif damage == "root_marker_tampered":
        (root / ".jkm-runtime-root-v1").write_bytes(b"tampered")
    else:  # pragma: no cover - enum-like parametrization guard
        raise AssertionError(damage)
    reset, private, clock = _support_service(security)
    request = reset.create_request()
    token = signed_token(
        request,
        private,
        key_id="support-final-v4-test",
    )
    factory = FinalV4PreAuthRecoveryFactory(
        paths=paths,
        account_loader=security.repository.load_account,
        security_store_validator=security.repository.require_current_read_only,
        key_store=store,
        random_source=DeterministicRandom(b"damaged-final-v4"),
        clock=clock,
    )
    keyset_before = paths.keyset_metadata.read_bytes()
    envelope_before = paths.database_key_envelope_registry.read_bytes()
    keychain_before = dict(store.values)

    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(token, backup=factory.create())

    assert caught.value.code is SupportResetFailureCode.PRODUCT_VALIDATION_FAILED
    assert security.service.security_store_state().state is SecurityStoreState.READY
    assert security.repository.security_epoch() == 1
    assert security.service.authenticate_password(PASSWORD).status is AuthenticationStatus.AUTHENTICATED
    assert store.create_calls == 1
    assert paths.keyset_metadata.read_bytes() == keyset_before
    assert paths.database_key_envelope_registry.read_bytes() == envelope_before
    assert store.values == keychain_before
    assert not tuple(paths.backups.glob("support-reset-safety-*.jkmebackup"))
