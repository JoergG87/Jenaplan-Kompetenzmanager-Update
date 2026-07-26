"""Database and encrypted-document adapters for Security Sprint 11."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import hashlib
import mimetypes
import os
from pathlib import Path
from typing import Any, Callable

from prototypes.encrypted_document_container.sprint10_container import (
    DocumentChunkConsumer,
    DocumentSource,
    EncryptedDocumentExportResult,
    EncryptedDocumentVerificationResult,
    SyntheticEncryptedDocumentServiceV1,
)
from src.core.database_engine import (
    DatabaseConnectionProvider,
    DatabaseEngine,
    SQLCipherConnectionProvider,
    SQLiteReadOnlyConnectionProvider,
)
from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import DatabaseKey
from src.security.document_container import (
    ALLOWED_DOCUMENT_MIME_TYPES,
    DocumentContainerContextV1,
)

from .integration_gate import (
    SecurityIntegrationError,
    SecurityIntegrationPaths,
)
from .integration_state import SecurityIntegrationDocumentPlan


SECURITY_INTEGRATION_USER_VERSION = 1101
SECURITY_INTEGRATION_SCHEMA_VERSION = 1
SECURITY_INTEGRATION_APPLICATION_ID = 0x4A4B4D31
SECURITY_INTEGRATION_APP_FORMAT_VERSION = "security-integration-v1"
SECURITY_DOCUMENT_URI_PREFIX = "jkm-secure://"
_DOCUMENT_LIFECYCLE = frozenset(
    {"ACTIVE", "PREPARED", "RETAINED", "QUARANTINED"}
)


class SecurityIntegrationConnectionFactory:
    """Only database-open boundary used by the gated integration path."""

    def __init__(
        self,
        *,
        provider: DatabaseConnectionProvider,
        allowed_path: Path,
        key_loader: Callable[[], DatabaseKey] | None = None,
        expected_key_id: str | None = None,
        expected_key_generation: int | None = None,
        validator: Callable[[Any], None] | None = None,
        read_only: bool = False,
    ) -> None:
        self.engine = provider.engine
        self._provider = provider
        self._allowed_path = Path(allowed_path)
        self._key_loader = key_loader
        self._expected_key_id = expected_key_id
        self._expected_key_generation = expected_key_generation
        self._validator = validator
        self._read_only = bool(read_only)

    @classmethod
    def plaintext_source(
        cls,
        path: Path,
    ) -> "SecurityIntegrationConnectionFactory":
        return cls(
            provider=SQLiteReadOnlyConnectionProvider(),
            allowed_path=path,
        )

    @classmethod
    def sqlcipher(
        cls,
        *,
        path: Path,
        provider: SQLCipherConnectionProvider,
        key_loader: Callable[[], DatabaseKey],
        expected_key_id: str,
        expected_key_generation: int,
        validator: Callable[[Any], None] | None = None,
        read_only: bool = False,
    ) -> "SecurityIntegrationConnectionFactory":
        return cls(
            provider=provider,
            allowed_path=path,
            key_loader=key_loader,
            expected_key_id=expected_key_id,
            expected_key_generation=expected_key_generation,
            validator=validator,
            read_only=read_only,
        )

    def connect(
        self,
        path: Path,
        *,
        create: bool,
        key_material=None,
    ) -> Any:
        if key_material is not None or Path(path) != self._allowed_path:
            raise SecurityIntegrationError(
                "security_integration_connection_scope_invalid"
            )
        loaded_key: DatabaseKey | None = None
        material: bytes | None = None
        if self.engine is DatabaseEngine.SQLCIPHER:
            if self._key_loader is None:
                raise SecurityIntegrationError(
                    "security_integration_database_key_missing"
                )
            loaded_key = self._key_loader()
            if (
                loaded_key.key_id != self._expected_key_id
                or loaded_key.generation != self._expected_key_generation
                or len(loaded_key.key_material) != 32
            ):
                raise SecurityIntegrationError(
                    "security_integration_database_key_invalid"
                )
            material = loaded_key.key_material
        elif self._key_loader is not None:
            raise SecurityIntegrationError(
                "security_integration_connection_factory_invalid"
            )
        if create and self._read_only:
            raise SecurityIntegrationError(
                "security_integration_read_only_create_blocked"
            )
        if (
            self.engine is DatabaseEngine.SQLCIPHER
            and self._read_only
        ):
            if not isinstance(
                self._provider,
                SQLCipherConnectionProvider,
            ):
                raise SecurityIntegrationError(
                    "security_integration_read_only_provider_invalid"
                )
            connection = self._provider.connect_read_only(
                self._allowed_path,
                key_material=material,
            )
        else:
            connection = self._provider.connect(
                self._allowed_path,
                create=create,
                key_material=material,
            )
        try:
            if not create and self._validator is not None:
                self._validator(connection)
            return connection
        except Exception:
            try:
                connection.close()
            except Exception:
                pass
            raise

    def open_existing(self) -> Any:
        return self.connect(self._allowed_path, create=False)

    def create_new(self) -> Any:
        return self.connect(self._allowed_path, create=True)

    def load_database_key(self) -> DatabaseKey:
        if self._key_loader is None:
            raise SecurityIntegrationError(
                "security_integration_database_key_missing"
            )
        key = self._key_loader()
        if (
            key.key_id != self._expected_key_id
            or key.generation != self._expected_key_generation
            or len(key.key_material) != 32
        ):
            raise SecurityIntegrationError(
                "security_integration_database_key_invalid"
            )
        return key

    def scoped_to(
        self,
        path: Path,
        *,
        validator: Callable[[Any], None] | None = None,
    ) -> "SecurityIntegrationConnectionFactory":
        """Create another explicit path scope with the same engine/key policy."""
        return SecurityIntegrationConnectionFactory(
            provider=self._provider,
            allowed_path=path,
            key_loader=self._key_loader,
            expected_key_id=self._expected_key_id,
            expected_key_generation=self._expected_key_generation,
            validator=validator,
            read_only=self._read_only,
        )


@dataclass(frozen=True)
class EncryptedDocumentGenerationRecord:
    source_document_id: str
    document_id: str
    document_generation: int
    storage_id: str
    key_id: str
    key_generation: int
    envelope_revision: int
    container_format_version: int
    plaintext_size: int
    plaintext_sha256: str
    mime_type: str
    lifecycle_status: str
    container_name: str
    retained_reason: str
    quarantine_reason: str
    created_at: str


@dataclass(frozen=True)
class PlaintextDocumentSource:
    source_document_id: str
    source_path: Path
    original_filename: str
    mime_type: str
    plaintext_size: int
    plaintext_sha256: str
    source_path_sha256: str


def inspect_plaintext_documents(
    *,
    factory: SecurityIntegrationConnectionFactory,
    paths: SecurityIntegrationPaths,
) -> tuple[PlaintextDocumentSource, ...]:
    with closing(factory.open_existing()) as connection:
        try:
            rows = connection.execute(
                """
                SELECT document_id, file_path, original_filename
                FROM documents
                WHERE active = 1
                ORDER BY document_id
                """
            ).fetchall()
        except Exception:
            raise SecurityIntegrationError(
                "security_integration_document_inventory_invalid"
            ) from None
    if not rows:
        raise SecurityIntegrationError(
            "security_integration_document_inventory_empty"
        )
    results: list[PlaintextDocumentSource] = []
    for row in rows:
        source_path = _validated_source_path(
            paths.source_documents,
            row["file_path"],
        )
        size, digest = _hash_regular(source_path)
        original_filename = str(row["original_filename"] or source_path.name)
        mime_type = _mime_type(original_filename)
        results.append(
            PlaintextDocumentSource(
                source_document_id=str(row["document_id"]),
                source_path=source_path,
                original_filename=original_filename,
                mime_type=mime_type,
                plaintext_size=size,
                plaintext_sha256=digest,
                source_path_sha256=hashlib.sha256(
                    source_path.relative_to(paths.root)
                    .as_posix()
                    .encode("utf-8")
                ).hexdigest(),
            )
        )
    return tuple(results)


def transfer_plaintext_to_sqlcipher(
    *,
    source_factory: SecurityIntegrationConnectionFactory,
    target_factory: SecurityIntegrationConnectionFactory,
    installation_id: str,
    database_context_id: str,
    migration_id: str,
    created_at: str,
) -> tuple[str, str]:
    with closing(source_factory.open_existing()) as source:
        _verify_sqlite_integrity(source)
        source_snapshot = _database_snapshot_sha256(source)
        dump = "\n".join(source.iterdump())
        source_application_id = int(
            source.execute("PRAGMA application_id").fetchone()[0]
        )
        source_user_version = int(
            source.execute("PRAGMA user_version").fetchone()[0]
        )
    with closing(target_factory.create_new()) as target:
        try:
            target.execute("PRAGMA foreign_keys = OFF")
            target.executescript(dump)
            target.execute(
                f"PRAGMA application_id = {source_application_id}"
            )
            target.execute(f"PRAGMA user_version = {source_user_version}")
            target.commit()
            target.execute("PRAGMA foreign_keys = ON")
            _verify_sqlite_integrity(target)
            target_snapshot = _database_snapshot_sha256(target)
            if target_snapshot != source_snapshot:
                raise SecurityIntegrationError(
                    "security_integration_database_transfer_mismatch"
                )
            install_security_integration_schema(
                target,
                installation_id=installation_id,
                database_context_id=database_context_id,
                migration_id=migration_id,
                created_at=created_at,
            )
        except SecurityIntegrationError:
            raise
        except Exception:
            raise SecurityIntegrationError(
                "security_integration_database_transfer_failed"
            ) from None
    with closing(target_factory.open_existing()) as reopened:
        validate_security_integration_schema(
            reopened,
            installation_id=installation_id,
            database_context_id=database_context_id,
            migration_id=migration_id,
        )
        final_snapshot = _database_snapshot_sha256(
            reopened,
            excluded_tables={
                "security_integration_metadata",
                "security_document_generations",
            },
        )
    if final_snapshot != source_snapshot:
        raise SecurityIntegrationError(
            "security_integration_database_reopen_mismatch"
        )
    return source_snapshot, final_snapshot


def install_security_integration_schema(
    connection: Any,
    *,
    installation_id: str,
    database_context_id: str,
    migration_id: str,
    created_at: str,
) -> None:
    try:
        with connection:
            connection.executescript(
                """
                CREATE TABLE security_integration_metadata (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    schema_version INTEGER NOT NULL CHECK (schema_version = 1),
                    installation_id TEXT NOT NULL,
                    database_context_id TEXT NOT NULL,
                    migration_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE security_document_generations (
                    source_document_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    document_generation INTEGER NOT NULL
                        CHECK (document_generation > 0),
                    storage_id TEXT NOT NULL UNIQUE,
                    key_id TEXT NOT NULL,
                    key_generation INTEGER NOT NULL CHECK (key_generation > 0),
                    envelope_revision INTEGER NOT NULL
                        CHECK (envelope_revision > 0),
                    container_format_version INTEGER NOT NULL
                        CHECK (container_format_version > 0),
                    plaintext_size INTEGER NOT NULL CHECK (plaintext_size >= 0),
                    plaintext_sha256 TEXT NOT NULL
                        CHECK (length(plaintext_sha256) = 64),
                    mime_type TEXT NOT NULL,
                    lifecycle_status TEXT NOT NULL CHECK (
                        lifecycle_status IN (
                            'ACTIVE', 'PREPARED', 'RETAINED', 'QUARANTINED'
                        )
                    ),
                    container_name TEXT NOT NULL UNIQUE,
                    retained_reason TEXT NOT NULL DEFAULT '',
                    quarantine_reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (document_id, document_generation),
                    UNIQUE (source_document_id, document_generation),
                    FOREIGN KEY (source_document_id)
                        REFERENCES documents(document_id)
                );

                CREATE UNIQUE INDEX
                    idx_security_document_one_active_generation
                    ON security_document_generations(source_document_id)
                    WHERE lifecycle_status = 'ACTIVE';

                CREATE INDEX idx_security_document_storage_state
                    ON security_document_generations(
                        lifecycle_status, storage_id
                    );
                """
            )
            connection.execute(
                """
                INSERT INTO security_integration_metadata (
                    singleton,
                    schema_version,
                    installation_id,
                    database_context_id,
                    migration_id,
                    created_at
                )
                VALUES (1, ?, ?, ?, ?, ?)
                """,
                (
                    SECURITY_INTEGRATION_SCHEMA_VERSION,
                    installation_id,
                    database_context_id,
                    migration_id,
                    created_at,
                ),
            )
            connection.execute(
                f"PRAGMA application_id = {SECURITY_INTEGRATION_APPLICATION_ID}"
            )
            connection.execute(
                f"PRAGMA user_version = {SECURITY_INTEGRATION_USER_VERSION}"
            )
    except Exception:
        raise SecurityIntegrationError(
            "security_integration_schema_install_failed"
        ) from None


def validate_security_integration_schema(
    connection: Any,
    *,
    installation_id: str,
    database_context_id: str,
    migration_id: str,
) -> None:
    try:
        application_id = int(
            connection.execute("PRAGMA application_id").fetchone()[0]
        )
        user_version = int(
            connection.execute("PRAGMA user_version").fetchone()[0]
        )
        row = connection.execute(
            """
            SELECT schema_version, installation_id, database_context_id,
                   migration_id
            FROM security_integration_metadata
            WHERE singleton = 1
            """
        ).fetchone()
        columns = tuple(
            item[1]
            for item in connection.execute(
                "PRAGMA table_info(security_document_generations)"
            ).fetchall()
        )
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
    except Exception:
        raise SecurityIntegrationError(
            "security_integration_schema_invalid"
        ) from None
    expected_columns = (
        "source_document_id",
        "document_id",
        "document_generation",
        "storage_id",
        "key_id",
        "key_generation",
        "envelope_revision",
        "container_format_version",
        "plaintext_size",
        "plaintext_sha256",
        "mime_type",
        "lifecycle_status",
        "container_name",
        "retained_reason",
        "quarantine_reason",
        "created_at",
    )
    if (
        application_id != SECURITY_INTEGRATION_APPLICATION_ID
        or user_version != SECURITY_INTEGRATION_USER_VERSION
        or row is None
        or tuple(row)
        != (
            SECURITY_INTEGRATION_SCHEMA_VERSION,
            installation_id,
            database_context_id,
            migration_id,
        )
        or columns != expected_columns
        or foreign_keys
    ):
        raise SecurityIntegrationError(
            "security_integration_schema_invalid"
        )


class SecurityDocumentApplicationAdapter:
    """Persist only fully verified encrypted document generations."""

    def __init__(
        self,
        *,
        paths: SecurityIntegrationPaths,
        factory: SecurityIntegrationConnectionFactory,
        service: SyntheticEncryptedDocumentServiceV1,
        dmk_loader: Callable[[], LoadedDataMasterKey],
        installation_id: str,
        database_context_id: str,
    ) -> None:
        self.paths = paths
        self.factory = factory
        self.service = service
        self._dmk_loader = dmk_loader
        self.installation_id = installation_id
        self.database_context_id = database_context_id

    def prepare_existing(
        self,
        plan: SecurityIntegrationDocumentPlan,
    ) -> EncryptedDocumentGenerationRecord:
        source = self._source_for_plan(plan)
        context = self._context(plan.document_id, 1)
        dmk = self._dmk_loader()
        container = self.paths.document_storage / (
            f"{plan.storage_id}.w1.jkmedoc"
        )
        if container.exists():
            verification = self.service.verify(
                test_root=self.paths.root,
                container=container,
                dmk=dmk,
                context=context,
                expected_storage_id=plan.storage_id,
            )
        else:
            verification = self.service.create(
                test_root=self.paths.root,
                source=DocumentSource(
                    source_name=source.source_path.name,
                    original_filename=source.original_filename,
                    mime_type=source.mime_type,
                ),
                storage_id=plan.storage_id,
                dmk=dmk,
                context=context,
            )
        record = _record_from_verification(
            source_document_id=plan.source_document_id,
            verification=verification,
            lifecycle_status="PREPARED",
        )
        self._insert_or_verify_prepared(record)
        return record

    def prepare_replacement(
        self,
        *,
        source_document_id: str,
        source_name: str,
        original_filename: str,
        mime_type: str,
        storage_id: str,
    ) -> EncryptedDocumentGenerationRecord:
        current = self._active_record(source_document_id)
        generation = current.document_generation + 1
        context = self._context(current.document_id, generation)
        source_path = _validated_source_path(
            self.paths.source_documents,
            str(self.paths.source_documents / source_name),
        )
        source_size, source_hash = _hash_regular(source_path)
        container = self.paths.document_storage / (
            f"{storage_id}.w1.jkmedoc"
        )
        if container.exists():
            verification = self.service.verify(
                test_root=self.paths.root,
                container=container,
                dmk=self._dmk_loader(),
                context=context,
                expected_storage_id=storage_id,
            )
        else:
            verification = self.service.create(
                test_root=self.paths.root,
                source=DocumentSource(
                    source_name=source_name,
                    original_filename=original_filename,
                    mime_type=mime_type,
                ),
                storage_id=storage_id,
                dmk=self._dmk_loader(),
                context=context,
            )
        manifest = verification.manifest
        if (
            manifest.original_filename != original_filename
            or manifest.mime_type != mime_type
            or manifest.plaintext_size != source_size
            or manifest.plaintext_sha256 != source_hash
        ):
            raise SecurityIntegrationError(
                "security_integration_document_replacement_mismatch"
            )
        record = _record_from_verification(
            source_document_id=source_document_id,
            verification=verification,
            lifecycle_status="PREPARED",
        )
        self._insert_or_verify_prepared(record)
        return record

    def activate_replacement(
        self,
        prepared: EncryptedDocumentGenerationRecord,
    ) -> EncryptedDocumentGenerationRecord:
        if prepared.lifecycle_status != "PREPARED":
            raise SecurityIntegrationError(
                "security_integration_document_prepared_invalid"
            )
        verification = self.service.verify(
            test_root=self.paths.root,
            container=self.paths.document_storage / prepared.container_name,
            dmk=self._dmk_loader(),
            context=self._context(
                prepared.document_id,
                prepared.document_generation,
            ),
            expected_storage_id=prepared.storage_id,
        )
        if (
            verification.manifest.plaintext_size
            != prepared.plaintext_size
            or verification.manifest.plaintext_sha256
            != prepared.plaintext_sha256
        ):
            raise SecurityIntegrationError(
                "security_integration_document_container_mismatch"
            )
        with closing(self.factory.open_existing()) as connection:
            try:
                with connection:
                    active = connection.execute(
                        """
                        SELECT document_id, document_generation
                        FROM security_document_generations
                        WHERE source_document_id = ?
                          AND lifecycle_status = 'ACTIVE'
                        """,
                        (prepared.source_document_id,),
                    ).fetchone()
                    staged = connection.execute(
                        """
                        SELECT source_document_id, document_id,
                               document_generation, storage_id, key_id,
                               key_generation, envelope_revision,
                               container_format_version, plaintext_size,
                               plaintext_sha256, mime_type, lifecycle_status,
                               container_name, retained_reason,
                               quarantine_reason, created_at
                        FROM security_document_generations
                        WHERE document_id = ?
                          AND document_generation = ?
                          AND source_document_id = ?
                          AND storage_id = ?
                        """,
                        (
                            prepared.document_id,
                            prepared.document_generation,
                            prepared.source_document_id,
                            prepared.storage_id,
                        ),
                    ).fetchone()
                    if (
                        active is None
                        or str(active["document_id"]) != prepared.document_id
                        or int(active["document_generation"])
                        != prepared.document_generation - 1
                        or staged is None
                        or _record_from_row(staged) != prepared
                    ):
                        raise SecurityIntegrationError(
                            "security_integration_document_replacement_state_invalid"
                        )
                    connection.execute(
                        """
                        UPDATE security_document_generations
                        SET lifecycle_status = 'RETAINED',
                            retained_reason = 'generation_replaced'
                        WHERE source_document_id = ?
                          AND lifecycle_status = 'ACTIVE'
                        """,
                        (prepared.source_document_id,),
                    )
                    connection.execute(
                        """
                        UPDATE security_document_generations
                        SET lifecycle_status = 'ACTIVE'
                        WHERE document_id = ?
                          AND document_generation = ?
                        """,
                        (
                            prepared.document_id,
                            prepared.document_generation,
                        ),
                    )
                    reference = (
                        f"{SECURITY_DOCUMENT_URI_PREFIX}"
                        f"{prepared.storage_id}/"
                        f"{prepared.document_generation}"
                    )
                    updated = connection.execute(
                        """
                        UPDATE documents
                        SET file_path = ?, original_filename = ?
                        WHERE document_id = ?
                        """,
                        (
                            reference,
                            verification.manifest.original_filename,
                            prepared.source_document_id,
                        ),
                    ).rowcount
                    if updated != 1:
                        raise SecurityIntegrationError(
                            "security_integration_document_pointer_failed"
                        )
            except SecurityIntegrationError:
                raise
            except Exception:
                raise SecurityIntegrationError(
                    "security_integration_document_replacement_failed"
                ) from None
        active_record = self._active_record(prepared.source_document_id)
        if active_record != _replace_lifecycle(prepared, "ACTIVE"):
            raise SecurityIntegrationError(
                "security_integration_document_replacement_verify_failed"
            )
        return active_record

    def delete_active(self, source_document_id: str) -> None:
        self._active_record(source_document_id)
        raise SecurityIntegrationError(
            "security_integration_document_delete_deferred"
        )

    def activate_prepared(
        self,
        plans: tuple[SecurityIntegrationDocumentPlan, ...],
    ) -> tuple[EncryptedDocumentGenerationRecord, ...]:
        if not plans:
            raise SecurityIntegrationError(
                "security_integration_document_plan_empty"
            )
        with closing(self.factory.open_existing()) as connection:
            try:
                with connection:
                    for plan in plans:
                        row = connection.execute(
                            """
                            SELECT lifecycle_status
                            FROM security_document_generations
                            WHERE document_id = ?
                              AND document_generation = 1
                              AND storage_id = ?
                              AND source_document_id = ?
                            """,
                            (
                                plan.document_id,
                                plan.storage_id,
                                plan.source_document_id,
                            ),
                        ).fetchone()
                        if row is None:
                            raise SecurityIntegrationError(
                                "security_integration_document_prepared_missing"
                            )
                        if row["lifecycle_status"] == "ACTIVE":
                            continue
                        if row["lifecycle_status"] != "PREPARED":
                            raise SecurityIntegrationError(
                                "security_integration_document_state_invalid"
                            )
                        connection.execute(
                            """
                            UPDATE security_document_generations
                            SET lifecycle_status = 'RETAINED',
                                retained_reason = 'generation_replaced'
                            WHERE source_document_id = ?
                              AND lifecycle_status = 'ACTIVE'
                            """,
                            (plan.source_document_id,),
                        )
                        connection.execute(
                            """
                            UPDATE security_document_generations
                            SET lifecycle_status = 'ACTIVE'
                            WHERE document_id = ?
                              AND document_generation = 1
                            """,
                            (plan.document_id,),
                        )
                        reference = (
                            f"{SECURITY_DOCUMENT_URI_PREFIX}"
                            f"{plan.storage_id}/1"
                        )
                        updated = connection.execute(
                            """
                            UPDATE documents
                            SET file_path = ?
                            WHERE document_id = ?
                            """,
                            (reference, plan.source_document_id),
                        ).rowcount
                        if updated != 1:
                            raise SecurityIntegrationError(
                                "security_integration_document_pointer_failed"
                            )
            except SecurityIntegrationError:
                raise
            except Exception:
                raise SecurityIntegrationError(
                    "security_integration_document_activation_failed"
                ) from None
        return self.verify_active(plans)

    def verify_active(
        self,
        plans: tuple[SecurityIntegrationDocumentPlan, ...],
    ) -> tuple[EncryptedDocumentGenerationRecord, ...]:
        records: list[EncryptedDocumentGenerationRecord] = []
        with closing(self.factory.open_existing()) as connection:
            for plan in plans:
                row = connection.execute(
                    """
                    SELECT source_document_id, document_id,
                           document_generation, storage_id, key_id,
                           key_generation, envelope_revision,
                           container_format_version, plaintext_size,
                           plaintext_sha256, mime_type, lifecycle_status,
                           container_name, retained_reason,
                           quarantine_reason, created_at
                    FROM security_document_generations
                    WHERE document_id = ? AND document_generation = 1
                    """,
                    (plan.document_id,),
                ).fetchone()
                pointer = connection.execute(
                    "SELECT file_path FROM documents WHERE document_id = ?",
                    (plan.source_document_id,),
                ).fetchone()
                if row is None or pointer is None:
                    raise SecurityIntegrationError(
                        "security_integration_document_active_missing"
                    )
                record = _record_from_row(row)
                expected_reference = (
                    f"{SECURITY_DOCUMENT_URI_PREFIX}{plan.storage_id}/1"
                )
                if (
                    record.lifecycle_status != "ACTIVE"
                    or pointer["file_path"] != expected_reference
                    or record.storage_id != plan.storage_id
                    or record.plaintext_size != plan.plaintext_size
                    or record.plaintext_sha256 != plan.plaintext_sha256
                ):
                    raise SecurityIntegrationError(
                        "security_integration_document_pointer_invalid"
                    )
                verification = self.service.verify(
                    test_root=self.paths.root,
                    container=self.paths.document_storage
                    / record.container_name,
                    dmk=self._dmk_loader(),
                    context=self._context(record.document_id, 1),
                    expected_storage_id=record.storage_id,
                )
                if (
                    verification.manifest.plaintext_size
                    != record.plaintext_size
                    or verification.manifest.plaintext_sha256
                    != record.plaintext_sha256
                ):
                    raise SecurityIntegrationError(
                        "security_integration_document_container_mismatch"
                    )
                records.append(record)
        return tuple(records)

    def stream_active(
        self,
        source_document_id: str,
        consumer: DocumentChunkConsumer,
    ) -> EncryptedDocumentVerificationResult:
        record = self._active_record(source_document_id)
        return self.service.stream_verified(
            test_root=self.paths.root,
            container=self.paths.document_storage / record.container_name,
            dmk=self._dmk_loader(),
            context=self._context(
                record.document_id,
                record.document_generation,
            ),
            expected_storage_id=record.storage_id,
            consumer=consumer,
        )

    def export_active(
        self,
        source_document_id: str,
        export_name: str,
    ) -> EncryptedDocumentExportResult:
        record = self._active_record(source_document_id)
        return self.service.export(
            test_root=self.paths.root,
            container=self.paths.document_storage / record.container_name,
            export_name=export_name,
            dmk=self._dmk_loader(),
            context=self._context(
                record.document_id,
                record.document_generation,
            ),
            expected_storage_id=record.storage_id,
        )

    def _source_for_plan(
        self,
        plan: SecurityIntegrationDocumentPlan,
    ) -> PlaintextDocumentSource:
        sources = inspect_plaintext_documents(
            factory=SecurityIntegrationConnectionFactory.plaintext_source(
                self.paths.source_database
            ),
            paths=self.paths,
        )
        source = next(
            (
                item
                for item in sources
                if item.source_document_id == plan.source_document_id
            ),
            None,
        )
        if (
            source is None
            or source.plaintext_size != plan.plaintext_size
            or source.plaintext_sha256 != plan.plaintext_sha256
            or source.source_path_sha256 != plan.source_path_sha256
        ):
            raise SecurityIntegrationError(
                "security_integration_document_source_changed"
            )
        return source

    def _insert_or_verify_prepared(
        self,
        record: EncryptedDocumentGenerationRecord,
    ) -> None:
        with closing(self.factory.open_existing()) as connection:
            existing = connection.execute(
                """
                SELECT source_document_id, document_id,
                       document_generation, storage_id, key_id,
                       key_generation, envelope_revision,
                       container_format_version, plaintext_size,
                       plaintext_sha256, mime_type, lifecycle_status,
                       container_name, retained_reason,
                       quarantine_reason, created_at
                FROM security_document_generations
                WHERE document_id = ? AND document_generation = ?
                """,
                (record.document_id, record.document_generation),
            ).fetchone()
            if existing is not None:
                observed = _record_from_row(existing)
                if observed != record and not (
                    observed.lifecycle_status == "ACTIVE"
                    and observed == _replace_lifecycle(record, "ACTIVE")
                ):
                    raise SecurityIntegrationError(
                        "security_integration_document_prepared_changed"
                    )
                return
            try:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO security_document_generations (
                            source_document_id, document_id,
                            document_generation, storage_id, key_id,
                            key_generation, envelope_revision,
                            container_format_version, plaintext_size,
                            plaintext_sha256, mime_type, lifecycle_status,
                            container_name, retained_reason,
                            quarantine_reason, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        tuple(record.__dict__.values()),
                    )
            except Exception:
                raise SecurityIntegrationError(
                    "security_integration_document_persist_failed"
                ) from None

    def _active_record(
        self,
        source_document_id: str,
    ) -> EncryptedDocumentGenerationRecord:
        with closing(self.factory.open_existing()) as connection:
            row = connection.execute(
                """
                SELECT source_document_id, document_id,
                       document_generation, storage_id, key_id,
                       key_generation, envelope_revision,
                       container_format_version, plaintext_size,
                       plaintext_sha256, mime_type, lifecycle_status,
                       container_name, retained_reason,
                       quarantine_reason, created_at
                FROM security_document_generations
                WHERE source_document_id = ?
                  AND lifecycle_status = 'ACTIVE'
                """,
                (source_document_id,),
            ).fetchone()
        if row is None:
            raise SecurityIntegrationError(
                "security_integration_document_active_missing"
            )
        return _record_from_row(row)

    def _context(
        self,
        document_id: str,
        generation: int,
    ) -> DocumentContainerContextV1:
        return DocumentContainerContextV1(
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
            document_id=document_id,
            document_generation=generation,
            app_format_version=SECURITY_INTEGRATION_APP_FORMAT_VERSION,
        )


def security_integration_database_validator(
    *,
    installation_id: str,
    database_context_id: str,
    migration_id: str,
) -> Callable[[Any], None]:
    return lambda connection: validate_security_integration_schema(
        connection,
        installation_id=installation_id,
        database_context_id=database_context_id,
        migration_id=migration_id,
    )


def _record_from_verification(
    *,
    source_document_id: str,
    verification: EncryptedDocumentVerificationResult,
    lifecycle_status: str,
) -> EncryptedDocumentGenerationRecord:
    manifest = verification.manifest
    header = verification.header
    return EncryptedDocumentGenerationRecord(
        source_document_id=source_document_id,
        document_id=manifest.context.document_id,
        document_generation=manifest.context.document_generation,
        storage_id=manifest.storage_id,
        key_id=header.document_key_id,
        key_generation=header.document_key_generation,
        envelope_revision=header.envelope.rewrap_revision,
        container_format_version=header.container_version,
        plaintext_size=manifest.plaintext_size,
        plaintext_sha256=manifest.plaintext_sha256,
        mime_type=manifest.mime_type,
        lifecycle_status=lifecycle_status,
        container_name=verification.container_path.name,
        retained_reason="",
        quarantine_reason="",
        created_at=manifest.created_at,
    )


def _record_from_row(row: Any) -> EncryptedDocumentGenerationRecord:
    record = EncryptedDocumentGenerationRecord(
        source_document_id=str(row["source_document_id"]),
        document_id=str(row["document_id"]),
        document_generation=int(row["document_generation"]),
        storage_id=str(row["storage_id"]),
        key_id=str(row["key_id"]),
        key_generation=int(row["key_generation"]),
        envelope_revision=int(row["envelope_revision"]),
        container_format_version=int(row["container_format_version"]),
        plaintext_size=int(row["plaintext_size"]),
        plaintext_sha256=str(row["plaintext_sha256"]),
        mime_type=str(row["mime_type"]),
        lifecycle_status=str(row["lifecycle_status"]),
        container_name=str(row["container_name"]),
        retained_reason=str(row["retained_reason"]),
        quarantine_reason=str(row["quarantine_reason"]),
        created_at=str(row["created_at"]),
    )
    if record.lifecycle_status not in _DOCUMENT_LIFECYCLE:
        raise SecurityIntegrationError(
            "security_integration_document_state_invalid"
        )
    return record


def _replace_lifecycle(
    record: EncryptedDocumentGenerationRecord,
    lifecycle: str,
) -> EncryptedDocumentGenerationRecord:
    return EncryptedDocumentGenerationRecord(
        **{
            **record.__dict__,
            "lifecycle_status": lifecycle,
        }
    )


def _validated_source_path(root: Path, raw_path: object) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise SecurityIntegrationError(
            "security_integration_document_source_invalid"
        )
    path = Path(raw_path)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
        status = os.lstat(path)
    except (OSError, RuntimeError, ValueError):
        raise SecurityIntegrationError(
            "security_integration_document_source_invalid"
        ) from None
    if (
        path.parent != root
        or resolved != path
        or path.is_symlink()
        or not os.path.isfile(path)
        or not stat_is_regular(status.st_mode)
    ):
        raise SecurityIntegrationError(
            "security_integration_document_source_invalid"
        )
    return path


def stat_is_regular(mode: int) -> bool:
    import stat

    return stat.S_ISREG(mode)


def _hash_regular(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)
    except OSError:
        raise SecurityIntegrationError(
            "security_integration_document_source_read_failed"
        ) from None
    return size, digest.hexdigest()


def _mime_type(filename: str) -> str:
    guessed = mimetypes.guess_type(filename, strict=False)[0]
    return (
        guessed
        if guessed in ALLOWED_DOCUMENT_MIME_TYPES
        else "application/octet-stream"
    )


def _verify_sqlite_integrity(connection: Any) -> None:
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
    except Exception:
        raise SecurityIntegrationError(
            "security_integration_database_integrity_failed"
        ) from None
    if len(integrity) != 1 or str(integrity[0][0]) != "ok" or foreign_keys:
        raise SecurityIntegrationError(
            "security_integration_database_integrity_failed"
        )


def _database_snapshot_sha256(
    connection: Any,
    *,
    excluded_tables: set[str] | None = None,
) -> str:
    excluded = excluded_tables or set()
    digest = hashlib.sha256()
    try:
        schema_rows = connection.execute(
            """
            SELECT type, name, tbl_name, sql
            FROM sqlite_schema
            WHERE name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        ).fetchall()
        for row in schema_rows:
            if str(row[2]) in excluded or str(row[1]) in excluded:
                continue
            digest.update(repr(tuple(row)).encode("utf-8"))
            digest.update(b"\n")
        table_names = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT name FROM sqlite_schema
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
            if str(row[0]) not in excluded
        ]
        for table in table_names:
            quoted = table.replace('"', '""')
            rows = connection.execute(
                f'SELECT * FROM "{quoted}"'
            ).fetchall()
            for value in sorted(repr(tuple(row)) for row in rows):
                digest.update(table.encode("utf-8"))
                digest.update(b"\0")
                digest.update(value.encode("utf-8"))
                digest.update(b"\n")
    except Exception:
        raise SecurityIntegrationError(
            "security_integration_database_snapshot_failed"
        ) from None
    return digest.hexdigest()
