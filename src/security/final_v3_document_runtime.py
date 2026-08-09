"""Internally gated encrypted-document runtime beside Final-V3 SQLCipher.

The runtime is deliberately Qt-free and absent from product startup.  It uses
the already marker-bound DMK/Database-Key and Final-V3 SQLCipher runtime, an
exact companion SQLCipher schema, and the existing secretstream container
engine.  It exposes no plaintext export or operating-system preview.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field
from datetime import timezone
from enum import StrEnum
import hashlib
import os
from pathlib import Path
import re
import stat
import uuid
from typing import Any, Mapping

from prototypes.encrypted_document_container.sprint10_container import (
    DOCUMENT_CONTAINER_EXTENSION,
    SOURCES_DIRECTORY,
    STORAGE_DIRECTORY,
    SYNTHETIC_DOCUMENT_STORAGE_MARKER,
    SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES,
    SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER,
    SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES,
    DocumentChunkConsumer,
    DocumentSource,
    EncryptedDocumentVerificationResult,
    SyntheticEncryptedDocumentServiceV1,
)
from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCipherConnectionProvider,
)

from .database_key_runtime import (
    DMK_DATABASE_KEY_RUNTIME_ROOT_ENV,
    DatabaseKeyRuntimeError,
    LoadedDatabaseKeyRuntime,
    build_database_key_runtime,
)
from .document_container import (
    ENCRYPTED_DOCUMENT_FORMAT,
    ENCRYPTED_DOCUMENT_VERSION,
    DocumentContainerContextV1,
    EncryptedDocumentError,
)
from .domain import validate_uuid4
from .final_v3_sqlcipher_runtime import (
    FinalV3SQLCipherRuntimeCoordinator,
    FinalV3SQLCipherRuntimeDecisionState,
    FinalV3SQLCipherRuntimeError,
    FinalV3SQLCipherRuntimeGate,
    FinalV3SQLCipherRuntimePaths,
    FinalV3SQLCipherRuntimeScope,
    MarkerGatedFinalV3SQLCipherRuntimeScope,
    OpenedFinalV3SQLCipherRuntime,
)
from .infrastructure.system import (
    PlatformFilePermissionManager,
    SystemClock,
    SystemRandomSource,
)


FINAL_V3_DOCUMENT_SCHEMA_VERSION = 1
FINAL_V3_DOCUMENT_USER_VERSION = 1
FINAL_V3_DOCUMENT_APPLICATION_ID = 0x4A4B4D44
FINAL_V3_DOCUMENT_SCHEMA_FINGERPRINT = (
    "7f218993b6664e5e80e82c7dbc67cf7a73f1915486836fc703177ec6e04d81b3"
)
FINAL_V3_DOCUMENT_APP_FORMAT_VERSION = "final-v3-document-runtime-v1"
FINAL_V3_DOCUMENT_DATABASE_FILENAME = "documents-v1.sqlcipher"
FINAL_V3_DOCUMENT_CONTAINER_DIRECTORY = "document-containers-v1"
FINAL_V3_DOCUMENT_SCHEMA_ID = "final-v3-document-schema-v1"
_LIFECYCLES = frozenset({"PREPARED", "ACTIVE", "RETAINED", "QUARANTINED"})
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_CONTAINER_NAME = re.compile(
    r"\A[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\.jkmedoc\Z"
)
_MED_DOCUMENT_ID = re.compile(r"\AMED-[0-9]{6}\Z")


_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE final_v3_document_runtime_metadata (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        schema_id TEXT NOT NULL CHECK (schema_id = 'final-v3-document-schema-v1'),
        schema_version INTEGER NOT NULL CHECK (schema_version = 1),
        installation_id TEXT NOT NULL,
        database_context_id TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE final_v3_documents (
        document_id TEXT PRIMARY KEY NOT NULL,
        active_generation INTEGER,
        created_at TEXT NOT NULL,
        CHECK (active_generation IS NULL OR active_generation > 0),
        FOREIGN KEY (document_id, active_generation)
            REFERENCES final_v3_document_generations(
                document_id, document_generation
            ) DEFERRABLE INITIALLY DEFERRED
    )
    """,
    """
    CREATE TABLE final_v3_document_generations (
        document_id TEXT NOT NULL,
        document_generation INTEGER NOT NULL CHECK (document_generation > 0),
        storage_id TEXT NOT NULL UNIQUE,
        document_key_id TEXT NOT NULL,
        document_key_generation INTEGER NOT NULL
            CHECK (document_key_generation > 0),
        envelope_revision INTEGER NOT NULL CHECK (envelope_revision > 0),
        container_format TEXT NOT NULL
            CHECK (container_format = 'jenaplan-encrypted-document'),
        container_format_version INTEGER NOT NULL
            CHECK (container_format_version = 1),
        plaintext_size INTEGER NOT NULL CHECK (plaintext_size >= 0),
        plaintext_sha256 TEXT NOT NULL CHECK (
            length(plaintext_sha256) = 64
            AND plaintext_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
        container_size INTEGER NOT NULL CHECK (container_size > 0),
        container_sha256 TEXT NOT NULL CHECK (
            length(container_sha256) = 64
            AND container_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
        mime_type TEXT NOT NULL CHECK (length(trim(mime_type)) > 0),
        lifecycle_status TEXT NOT NULL CHECK (
            lifecycle_status IN (
                'PREPARED', 'ACTIVE', 'RETAINED', 'QUARANTINED'
            )
        ),
        created_at TEXT NOT NULL,
        PRIMARY KEY (document_id, document_generation),
        FOREIGN KEY (document_id) REFERENCES final_v3_documents(document_id)
            ON UPDATE RESTRICT ON DELETE RESTRICT
    )
    """,
    """
    CREATE UNIQUE INDEX idx_final_v3_document_one_active_generation
    ON final_v3_document_generations(document_id)
    WHERE lifecycle_status = 'ACTIVE'
    """,
    """
    CREATE INDEX idx_final_v3_document_generation_lifecycle
    ON final_v3_document_generations(lifecycle_status, storage_id)
    """,
)


class FinalV3DocumentRuntimeDecisionState(StrEnum):
    DISABLED = "DISABLED"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class FinalV3DocumentRuntimeOperation(StrEnum):
    CLASSIFY = "classify"
    OPEN_FINAL_V3 = "open_final_v3"
    LOAD_KEYS = "load_keys"
    INITIALIZE_SCHEMA = "initialize_schema"
    INSPECT_SCHEMA = "inspect_schema"
    PREPARE = "prepare"
    ACTIVATE = "activate"
    READ = "read"
    REPLACE = "replace"
    DEACTIVATE = "deactivate"


class FinalV3DocumentRuntimeError(RuntimeError):
    """Sanitized failure without paths, SQL, metadata text, or key material."""

    def __init__(
        self,
        code: str,
        *,
        operation: FinalV3DocumentRuntimeOperation,
    ) -> None:
        self.code = code
        self.operation = operation
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class FinalV3DocumentRuntimePaths:
    final_v3: FinalV3SQLCipherRuntimePaths
    database: Path
    container_root: Path
    layout_source_root: Path
    storage_root: Path

    @classmethod
    def for_final_v3(
        cls, final_v3: FinalV3SQLCipherRuntimePaths
    ) -> "FinalV3DocumentRuntimePaths":
        container_root = (
            final_v3.runtime_root / FINAL_V3_DOCUMENT_CONTAINER_DIRECTORY
        )
        return cls(
            final_v3=final_v3,
            database=final_v3.runtime_root / FINAL_V3_DOCUMENT_DATABASE_FILENAME,
            container_root=container_root,
            layout_source_root=container_root / SOURCES_DIRECTORY,
            storage_root=container_root / STORAGE_DIRECTORY,
        )


@dataclass(frozen=True, slots=True)
class FinalV3DocumentGeneration:
    document_id: str
    document_generation: int
    storage_id: str
    document_key_id: str
    document_key_generation: int
    envelope_revision: int
    container_format: str
    container_format_version: int
    plaintext_size: int
    plaintext_sha256: str
    container_size: int
    container_sha256: str
    mime_type: str
    lifecycle_status: str
    created_at: str


@dataclass(frozen=True, slots=True)
class FinalV3DocumentPreparePlan:
    document_id: str
    document_generation: int
    storage_id: str
    previous_active_generation: int | None


@dataclass(frozen=True)
class OpenedFinalV3DocumentRuntime:
    final_v3: OpenedFinalV3SQLCipherRuntime
    documents: "FinalV3DocumentRuntime" = field(repr=False)
    database_context_id: str
    installation_id: str


@dataclass(frozen=True)
class FinalV3DocumentRuntimeDecision:
    state: FinalV3DocumentRuntimeDecisionState
    runtime: OpenedFinalV3DocumentRuntime | None = field(
        default=None, repr=False
    )
    error_code: str | None = None
    error_operation: FinalV3DocumentRuntimeOperation | None = None


class FinalV3DocumentConnectionFactory:
    """Exact path/key scope for the document companion SQLCipher database."""

    def __init__(
        self,
        *,
        provider: SQLCipherConnectionProvider,
        paths: FinalV3DocumentRuntimePaths,
        loaded_keys: LoadedDatabaseKeyRuntime,
        environ: Mapping[str, str],
        scope: FinalV3SQLCipherRuntimeScope | None = None,
    ) -> None:
        if (
            provider.expected_binding_version != SQLCIPHER_4_17_BINDING_VERSION
            or provider.expected_engine_version != SQLCIPHER_4_17_ENGINE_VERSION
        ):
            raise _error("document_sqlcipher_provider_invalid")
        self._scope = scope or MarkerGatedFinalV3SQLCipherRuntimeScope(environ)
        expected = FinalV3DocumentRuntimePaths.for_final_v3(
            self._scope.require_paths()
        )
        if paths != expected:
            raise _error("document_runtime_scope_invalid")
        self._provider = provider
        self._paths = paths
        self._loaded = loaded_keys

    def connect(self, *, create: bool) -> Any:
        self._require_scope()
        if not create:
            _require_no_document_database_sidecars(self._paths.database)
        return self._provider.connect(
            self._paths.database,
            create=create,
            key_material=self._loaded.database_key.key_material,
        )

    def connect_read_only(self) -> Any:
        self._require_scope()
        _require_no_document_database_sidecars(self._paths.database)
        return self._provider.connect_read_only(
            self._paths.database,
            key_material=self._loaded.database_key.key_material,
        )

    def _require_scope(self) -> None:
        expected = FinalV3DocumentRuntimePaths.for_final_v3(
            self._scope.require_paths()
        )
        if self._paths.database.parent != self._paths.final_v3.runtime_root:
            raise _error("document_runtime_scope_invalid")
        if self._paths != expected:
            raise _error("document_runtime_scope_invalid")
        _require_private_directory(self._paths.final_v3.runtime_root)


class FinalV3DocumentSchemaV1:
    """Exact companion schema, context binding, and pointer invariants."""

    @classmethod
    def initialize(
        cls,
        connection: Any,
        *,
        installation_id: str,
        database_context_id: str,
        created_at: str,
    ) -> None:
        _uuid(installation_id, "document_installation_context_invalid")
        _uuid(database_context_id, "document_database_context_invalid")
        try:
            connection.execute("BEGIN IMMEDIATE")
            for statement in _SCHEMA_STATEMENTS:
                connection.execute(statement)
            connection.execute(
                """
                INSERT INTO final_v3_document_runtime_metadata (
                    singleton, schema_id, schema_version, installation_id,
                    database_context_id, created_at
                ) VALUES (1, ?, ?, ?, ?, ?)
                """,
                (
                    FINAL_V3_DOCUMENT_SCHEMA_ID,
                    FINAL_V3_DOCUMENT_SCHEMA_VERSION,
                    installation_id,
                    database_context_id,
                    created_at,
                ),
            )
            connection.execute(
                f"PRAGMA application_id = {FINAL_V3_DOCUMENT_APPLICATION_ID}"
            )
            connection.execute(
                f"PRAGMA user_version = {FINAL_V3_DOCUMENT_USER_VERSION}"
            )
            cls.validate(
                connection,
                installation_id=installation_id,
                database_context_id=database_context_id,
            )
            connection.commit()
        except FinalV3DocumentRuntimeError:
            connection.rollback()
            raise
        except Exception:
            connection.rollback()
            raise _error("document_schema_initialization_failed") from None

    @classmethod
    def validate(
        cls,
        connection: Any,
        *,
        installation_id: str,
        database_context_id: str,
    ) -> None:
        try:
            application_id = int(
                connection.execute("PRAGMA application_id").fetchone()[0]
            )
            user_version = int(
                connection.execute("PRAGMA user_version").fetchone()[0]
            )
            identity = DatabaseCompatibilityInspector.schema_identity_for_connection(
                connection
            )
            metadata = connection.execute(
                """
                SELECT schema_id, schema_version, installation_id,
                       database_context_id
                FROM final_v3_document_runtime_metadata
                WHERE singleton = 1
                """
            ).fetchall()
            integrity = connection.execute("PRAGMA integrity_check").fetchall()
            foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        except Exception:
            raise _error("document_schema_inspection_failed") from None
        if (
            application_id != FINAL_V3_DOCUMENT_APPLICATION_ID
            or user_version != FINAL_V3_DOCUMENT_USER_VERSION
            or identity.fingerprint != FINAL_V3_DOCUMENT_SCHEMA_FINGERPRINT
            or len(metadata) != 1
            or tuple(metadata[0])
            != (
                FINAL_V3_DOCUMENT_SCHEMA_ID,
                FINAL_V3_DOCUMENT_SCHEMA_VERSION,
                installation_id,
                database_context_id,
            )
            or len(integrity) != 1
            or str(integrity[0][0]).lower() != "ok"
            or foreign_keys
        ):
            raise _error("document_schema_incompatible")
        cls.validate_pointers(connection)

    @staticmethod
    def validate_pointers(connection: Any) -> None:
        try:
            invalid_state = connection.execute(
                """
                SELECT d.document_id
                FROM final_v3_documents AS d
                WHERE (
                    d.active_generation IS NULL
                    AND (
                        (SELECT COUNT(*) FROM final_v3_document_generations AS p
                         WHERE p.document_id = d.document_id
                           AND p.lifecycle_status = 'PREPARED') > 1
                        OR EXISTS (
                            SELECT 1 FROM final_v3_document_generations AS a
                            WHERE a.document_id = d.document_id
                              AND a.lifecycle_status = 'ACTIVE'
                        )
                    )
                ) OR (
                    d.active_generation IS NOT NULL
                    AND (
                        (SELECT COUNT(*) FROM final_v3_document_generations AS a
                         WHERE a.document_id = d.document_id
                           AND a.lifecycle_status = 'ACTIVE') <> 1
                        OR NOT EXISTS (
                            SELECT 1 FROM final_v3_document_generations AS a
                            WHERE a.document_id = d.document_id
                              AND a.document_generation = d.active_generation
                              AND a.lifecycle_status = 'ACTIVE'
                        )
                        OR (SELECT COUNT(*)
                            FROM final_v3_document_generations AS p
                            WHERE p.document_id = d.document_id
                              AND p.lifecycle_status = 'PREPARED') > 1
                    )
                )
                """
            ).fetchall()
        except Exception:
            raise _error("document_pointer_inspection_failed") from None
        if invalid_state:
            raise _error("document_pointer_invariant_failed")


class FinalV3DocumentRuntime:
    """Prepare, activate, read and replace immutable document generations."""

    def __init__(
        self,
        *,
        paths: FinalV3DocumentRuntimePaths,
        factory: FinalV3DocumentConnectionFactory,
        loaded_keys: LoadedDatabaseKeyRuntime,
        installation_id: str,
        source_root: Path | None,
        random_source: Any,
        clock: Any,
        fault_hook=None,
    ) -> None:
        self.paths = paths
        self._factory = factory
        self._loaded = loaded_keys
        self._installation_id = installation_id
        self.source_root = None if source_root is None else Path(source_root)
        if self.source_root is not None:
            _require_external_source_root(self.source_root, paths)
        self._random = random_source
        self._clock = clock
        self._fault_hook = fault_hook
        self._operation = FinalV3DocumentRuntimeOperation.CLASSIFY
        self._service = SyntheticEncryptedDocumentServiceV1(
            random_source=random_source,
            clock=clock,
            fault_injector=self._container_fault,
            required_source_prefix=None,
            plain_storage_names=True,
            retain_published_hardlink_evidence=False,
            source_root_override=self.source_root,
            direct_visible_write=True,
            require_export_layout=False,
        )

    def validate_restart(self) -> None:
        previous_operation = self._operation
        self._operation = FinalV3DocumentRuntimeOperation.INSPECT_SCHEMA
        try:
            with closing(self._factory.connect_read_only()) as connection:
                FinalV3DocumentSchemaV1.validate(
                    connection,
                    installation_id=self._installation_id,
                    database_context_id=self._loaded.database_context_id,
                )
                records = tuple(
                    _record_from_row(row)
                    for row in connection.execute(
                        _GENERATION_SELECT
                        + " ORDER BY document_id, document_generation"
                    ).fetchall()
                )
            self._validate_storage_inventory(records)
        finally:
            self._operation = previous_operation

    def prepare(
        self,
        *,
        document_id: str,
        source_name: str | None = None,
        source_path: Path | None = None,
        original_filename: str,
        mime_type: str,
        plan: FinalV3DocumentPreparePlan | Mapping[str, object] | None = None,
    ) -> FinalV3DocumentGeneration:
        self._operation = FinalV3DocumentRuntimeOperation.PREPARE
        _document_id(document_id)
        self.validate_restart()
        if plan is None:
            plan = self.plan_prepare(document_id=document_id)
        plan = self._require_prepare_plan(plan, document_id=document_id)
        existing = self._prepared_for(document_id)
        if existing is not None:
            self._verify_record(existing)
            if (
                existing.document_generation == plan.document_generation
                and existing.storage_id == plan.storage_id
            ):
                return existing
            raise _error("document_prepared_activation_required", self._operation)

        with closing(self._factory.connect_read_only()) as connection:
            rows = connection.execute(
                _GENERATION_SELECT
                + " WHERE document_id = ? ORDER BY document_generation",
                (document_id,),
            ).fetchall()
        records = tuple(_record_from_row(row) for row in rows)
        active = tuple(r for r in records if r.lifecycle_status == "ACTIVE")
        if records and len(active) != 1:
            raise _error("document_generation_state_invalid", self._operation)
        previous_active_generation = (
            active[0].document_generation if active else None
        )
        if plan.previous_active_generation != previous_active_generation:
            raise _error("document_prepare_plan_conflict", self._operation)
        generation = records[-1].document_generation + 1 if records else 1
        if generation != plan.document_generation:
            raise _error("document_prepare_plan_conflict", self._operation)
        storage_id = plan.storage_id
        context = self._context(document_id, generation)
        if source_path is not None:
            if source_name is not None:
                raise _error("document_source_ambiguous", self._operation)
            candidate = Path(source_path)
            if not candidate.is_absolute():
                raise _error("document_source_path_invalid", self._operation)
            source_root = candidate.parent
            source_name = candidate.name
        else:
            source_root = self.source_root
        if source_root is None or source_name is None:
            raise _error("document_source_root_required", self._operation)
        _require_external_source_root(source_root, self.paths)
        service = self._service_for_source_root(source_root)
        self._emit("before_container_creation")
        try:
            verification = service.create(
                test_root=self.paths.container_root,
                source=DocumentSource(
                    source_name=source_name,
                    original_filename=original_filename,
                    mime_type=mime_type,
                ),
                storage_id=storage_id,
                dmk=self._loaded.dmk,
                context=context,
                document_key_generation=generation,
            )
        except EncryptedDocumentError as error:
            raise _error(error.code, self._operation) from None
        self._emit("after_verification_before_prepared")
        record = _record_from_verification(verification, "PREPARED")
        try:
            with closing(self._factory.connect(create=False)) as connection:
                connection.execute("BEGIN IMMEDIATE")
                observed = connection.execute(
                    _GENERATION_SELECT
                    + " WHERE document_id = ? ORDER BY document_generation",
                    (document_id,),
                ).fetchall()
                if len(observed) != len(records):
                    raise _error("document_generation_conflict", self._operation)
                if not records:
                    connection.execute(
                        """
                        INSERT INTO final_v3_documents (
                            document_id, active_generation, created_at
                        ) VALUES (?, NULL, ?)
                        """,
                        (document_id, record.created_at),
                    )
                connection.execute(
                    """
                    INSERT INTO final_v3_document_generations (
                        document_id, document_generation, storage_id,
                        document_key_id, document_key_generation,
                        envelope_revision, container_format,
                        container_format_version, plaintext_size,
                        plaintext_sha256, container_size, container_sha256,
                        mime_type, lifecycle_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _record_values(record),
                )
                FinalV3DocumentSchemaV1.validate_pointers(connection)
                connection.commit()
        except FinalV3DocumentRuntimeError:
            raise
        except Exception:
            raise _error("document_prepared_persist_failed", self._operation) from None
        self._emit("after_prepared_before_activation")
        return self._require_generation(document_id, generation, "PREPARED")

    def prepare_bytes(
        self,
        *,
        document_id: str,
        source_bytes: bytes,
        original_filename: str,
        mime_type: str,
        plan: FinalV3DocumentPreparePlan | Mapping[str, object] | None = None,
    ) -> FinalV3DocumentGeneration:
        """Prepare one generation directly from memory without a plaintext file."""
        self._operation = FinalV3DocumentRuntimeOperation.PREPARE
        _document_id(document_id)
        if not isinstance(source_bytes, bytes) or not source_bytes:
            raise _error("document_source_bytes_invalid", self._operation)
        self.validate_restart()
        if plan is None:
            plan = self.plan_prepare(document_id=document_id)
        plan = self._require_prepare_plan(plan, document_id=document_id)
        existing = self._prepared_for(document_id)
        if existing is not None:
            self._verify_record(existing)
            if (
                existing.document_generation == plan.document_generation
                and existing.storage_id == plan.storage_id
                and existing.plaintext_size == len(source_bytes)
                and existing.plaintext_sha256
                == hashlib.sha256(source_bytes).hexdigest()
            ):
                return existing
            raise _error("document_prepared_activation_required", self._operation)

        with closing(self._factory.connect_read_only()) as connection:
            rows = connection.execute(
                _GENERATION_SELECT
                + " WHERE document_id = ? ORDER BY document_generation",
                (document_id,),
            ).fetchall()
        records = tuple(_record_from_row(row) for row in rows)
        active = tuple(r for r in records if r.lifecycle_status == "ACTIVE")
        if records and len(active) != 1:
            raise _error("document_generation_state_invalid", self._operation)
        previous_active_generation = active[0].document_generation if active else None
        if plan.previous_active_generation != previous_active_generation:
            raise _error("document_prepare_plan_conflict", self._operation)
        generation = records[-1].document_generation + 1 if records else 1
        if generation != plan.document_generation:
            raise _error("document_prepare_plan_conflict", self._operation)
        context = self._context(document_id, generation)
        self._emit("before_container_creation")
        try:
            verification = self._service.create(
                test_root=self.paths.container_root,
                source=DocumentSource(
                    source_name="memory-source.bin",
                    original_filename=original_filename,
                    mime_type=mime_type,
                ),
                storage_id=plan.storage_id,
                dmk=self._loaded.dmk,
                context=context,
                document_key_generation=generation,
                source_bytes=source_bytes,
            )
        except EncryptedDocumentError as error:
            raise _error(error.code, self._operation) from None
        self._emit("after_verification_before_prepared")
        record = _record_from_verification(verification, "PREPARED")
        try:
            with closing(self._factory.connect(create=False)) as connection:
                connection.execute("BEGIN IMMEDIATE")
                observed = connection.execute(
                    _GENERATION_SELECT
                    + " WHERE document_id = ? ORDER BY document_generation",
                    (document_id,),
                ).fetchall()
                if len(observed) != len(records):
                    raise _error("document_generation_conflict", self._operation)
                if not records:
                    connection.execute(
                        """
                        INSERT INTO final_v3_documents (
                            document_id, active_generation, created_at
                        ) VALUES (?, NULL, ?)
                        """,
                        (document_id, record.created_at),
                    )
                connection.execute(
                    """
                    INSERT INTO final_v3_document_generations (
                        document_id, document_generation, storage_id,
                        document_key_id, document_key_generation,
                        envelope_revision, container_format,
                        container_format_version, plaintext_size,
                        plaintext_sha256, container_size, container_sha256,
                        mime_type, lifecycle_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _record_values(record),
                )
                FinalV3DocumentSchemaV1.validate_pointers(connection)
                connection.commit()
        except FinalV3DocumentRuntimeError:
            raise
        except Exception:
            raise _error("document_prepared_persist_failed", self._operation) from None
        self._emit("after_prepared_before_activation")
        return self._require_generation(document_id, generation, "PREPARED")

    def plan_prepare(self, *, document_id: str) -> FinalV3DocumentPreparePlan:
        self._operation = FinalV3DocumentRuntimeOperation.PREPARE
        _document_id(document_id)
        self.validate_restart()
        existing = self._prepared_for(document_id)
        if existing is not None:
            raise _error("document_prepared_activation_required", self._operation)
        with closing(self._factory.connect_read_only()) as connection:
            rows = connection.execute(
                _GENERATION_SELECT
                + " WHERE document_id = ? ORDER BY document_generation",
                (document_id,),
            ).fetchall()
        records = tuple(_record_from_row(row) for row in rows)
        active = tuple(r for r in records if r.lifecycle_status == "ACTIVE")
        if records and len(active) != 1:
            raise _error("document_generation_state_invalid", self._operation)
        generation = records[-1].document_generation + 1 if records else 1
        return FinalV3DocumentPreparePlan(
            document_id=document_id,
            document_generation=generation,
            storage_id=self._new_uuid("document_storage_id_invalid"),
            previous_active_generation=(
                active[0].document_generation if active else None
            ),
        )

    def verify_prepared(
        self, *, plan: FinalV3DocumentPreparePlan | Mapping[str, object]
    ) -> FinalV3DocumentGeneration:
        self._operation = FinalV3DocumentRuntimeOperation.PREPARE
        raw_document_id = (
            plan.document_id
            if isinstance(plan, FinalV3DocumentPreparePlan)
            else plan.get("document_id")
        )
        plan = self._require_prepare_plan(
            plan, document_id=str(raw_document_id)
        )
        self.validate_restart()
        record = self._require_generation(
            plan.document_id, plan.document_generation, "PREPARED"
        )
        if record.storage_id != plan.storage_id:
            raise _error("document_prepare_plan_conflict", self._operation)
        self._verify_record(record)
        return record

    def activate(
        self, *, document_id: str, document_generation: int | None = None
    ) -> FinalV3DocumentGeneration:
        self._operation = FinalV3DocumentRuntimeOperation.ACTIVATE
        _document_id(document_id)
        self.validate_restart()
        if document_generation is None:
            pending = self._prepared_for(document_id)
            if pending is None:
                raise _error("document_prepared_missing", self._operation)
            document_generation = pending.document_generation
        if not isinstance(document_generation, int) or isinstance(
            document_generation, bool
        ) or document_generation < 1:
            raise _error("document_generation_invalid", self._operation)
        active = self._active_for_optional(document_id)
        if (
            active is not None
            and active.document_generation == document_generation
        ):
            self._verify_record(active)
            return active
        prepared = self._require_generation(document_id, document_generation, "PREPARED")
        self._verify_record(prepared)
        try:
            with closing(self._factory.connect(create=False)) as connection:
                connection.execute("BEGIN IMMEDIATE")
                current = connection.execute(
                    """
                    SELECT active_generation FROM final_v3_documents
                    WHERE document_id = ?
                    """,
                    (document_id,),
                ).fetchone()
                staged = connection.execute(
                    _GENERATION_SELECT
                    + " WHERE document_id = ? AND document_generation = ?",
                    (document_id, document_generation),
                ).fetchone()
                if current is None or staged is None:
                    raise _error("document_prepared_missing", self._operation)
                if _record_from_row(staged) != prepared:
                    raise _error("document_prepared_changed", self._operation)
                previous_generation = current[0]
                if previous_generation is not None:
                    connection.execute(
                        """
                        UPDATE final_v3_document_generations
                        SET lifecycle_status = 'PREPARED'
                        WHERE document_id = ? AND document_generation = ?
                          AND lifecycle_status = 'ACTIVE'
                        """,
                        (document_id, int(previous_generation)),
                    )
                self._emit("during_pointer_switch")
                updated = connection.execute(
                    """
                    UPDATE final_v3_document_generations
                    SET lifecycle_status = 'ACTIVE'
                    WHERE document_id = ? AND document_generation = ?
                      AND lifecycle_status = 'PREPARED'
                    """,
                    (document_id, document_generation),
                ).rowcount
                pointer = connection.execute(
                    """
                    UPDATE final_v3_documents SET active_generation = ?
                    WHERE document_id = ?
                    """,
                    (document_generation, document_id),
                ).rowcount
                if updated != 1 or pointer != 1:
                    raise _error("document_pointer_switch_failed", self._operation)
                self._emit("after_activation_before_retained")
                if previous_generation is not None:
                    retained = connection.execute(
                        """
                        UPDATE final_v3_document_generations
                        SET lifecycle_status = 'RETAINED'
                        WHERE document_id = ? AND document_generation = ?
                          AND lifecycle_status = 'PREPARED'
                        """,
                        (document_id, int(previous_generation)),
                    ).rowcount
                    if retained != 1:
                        raise _error(
                            "document_retained_mark_failed", self._operation
                        )
                self._verify_record(prepared)
                FinalV3DocumentSchemaV1.validate_pointers(connection)
                connection.commit()
        except FinalV3DocumentRuntimeError:
            raise
        except Exception:
            raise _error("document_activation_failed", self._operation) from None
        return self._require_generation(
            document_id, document_generation, "ACTIVE"
        )

    def apply_journaled_changes(
        self,
        *,
        prepared_plans: tuple[FinalV3DocumentPreparePlan | Mapping[str, object], ...],
        deactivated_document_ids: tuple[str, ...],
    ) -> tuple[FinalV3DocumentGeneration, ...]:
        """Atomically apply every pointer change of one Observation journal."""
        self._operation = FinalV3DocumentRuntimeOperation.ACTIVATE
        plans = tuple(
            self._require_prepare_plan(
                plan,
                document_id=str(
                    plan.document_id
                    if isinstance(plan, FinalV3DocumentPreparePlan)
                    else plan.get("document_id")
                ),
            )
            for plan in prepared_plans
        )
        activation_ids = tuple(plan.document_id for plan in plans)
        deactivation_ids = tuple(str(value) for value in deactivated_document_ids)
        for document_id in deactivation_ids:
            _document_id(document_id)
        if (
            len(set(activation_ids)) != len(activation_ids)
            or len(set(deactivation_ids)) != len(deactivation_ids)
            or set(activation_ids) & set(deactivation_ids)
        ):
            raise _error("document_activation_plan_invalid", self._operation)
        self.validate_restart()

        targets: dict[str, FinalV3DocumentGeneration] = {}
        for plan in plans:
            active = self._active_for_optional(plan.document_id)
            if active is not None and active.document_generation == plan.document_generation:
                self._verify_record(active)
                if active.storage_id != plan.storage_id:
                    raise _error("document_prepare_plan_conflict", self._operation)
                targets[plan.document_id] = active
                continue
            prepared = self._require_generation(
                plan.document_id, plan.document_generation, "PREPARED"
            )
            self._verify_record(prepared)
            if prepared.storage_id != plan.storage_id:
                raise _error("document_prepare_plan_conflict", self._operation)
            targets[plan.document_id] = prepared
        for document_id in deactivation_ids:
            active = self._active_for_optional(document_id)
            if active is not None:
                self._verify_record(active)

        try:
            with closing(self._factory.connect(create=False)) as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    for plan in plans:
                        current = connection.execute(
                            """
                            SELECT active_generation FROM final_v3_documents
                            WHERE document_id = ?
                            """,
                            (plan.document_id,),
                        ).fetchone()
                        target_row = connection.execute(
                            _GENERATION_SELECT
                            + " WHERE document_id = ? AND document_generation = ?",
                            (plan.document_id, plan.document_generation),
                        ).fetchone()
                        if current is None or target_row is None:
                            raise _error("document_prepared_missing", self._operation)
                        target = _record_from_row(target_row)
                        if current[0] == plan.document_generation:
                            if target.lifecycle_status != "ACTIVE":
                                raise _error("document_pointer_switch_failed", self._operation)
                            continue
                        if current[0] != plan.previous_active_generation:
                            raise _error("document_prepare_plan_conflict", self._operation)
                        if target.lifecycle_status != "PREPARED":
                            raise _error("document_prepared_changed", self._operation)
                        if plan.previous_active_generation is not None:
                            changed = connection.execute(
                                """
                                UPDATE final_v3_document_generations
                                SET lifecycle_status = 'PREPARED'
                                WHERE document_id = ? AND document_generation = ?
                                  AND lifecycle_status = 'ACTIVE'
                                """,
                                (plan.document_id, plan.previous_active_generation),
                            ).rowcount
                            if changed != 1:
                                raise _error("document_pointer_switch_failed", self._operation)
                        self._emit("during_pointer_switch")
                        activated = connection.execute(
                            """
                            UPDATE final_v3_document_generations
                            SET lifecycle_status = 'ACTIVE'
                            WHERE document_id = ? AND document_generation = ?
                              AND lifecycle_status = 'PREPARED'
                            """,
                            (plan.document_id, plan.document_generation),
                        ).rowcount
                        pointed = connection.execute(
                            """
                            UPDATE final_v3_documents SET active_generation = ?
                            WHERE document_id = ?
                            """,
                            (plan.document_generation, plan.document_id),
                        ).rowcount
                        if activated != 1 or pointed != 1:
                            raise _error("document_pointer_switch_failed", self._operation)
                        if plan.previous_active_generation is not None:
                            retained = connection.execute(
                                """
                                UPDATE final_v3_document_generations
                                SET lifecycle_status = 'RETAINED'
                                WHERE document_id = ? AND document_generation = ?
                                  AND lifecycle_status = 'PREPARED'
                                """,
                                (plan.document_id, plan.previous_active_generation),
                            ).rowcount
                            if retained != 1:
                                raise _error("document_retained_mark_failed", self._operation)
                    for document_id in deactivation_ids:
                        current = connection.execute(
                            """
                            SELECT active_generation FROM final_v3_documents
                            WHERE document_id = ?
                            """,
                            (document_id,),
                        ).fetchone()
                        if current is None:
                            raise _error("document_active_missing", self._operation)
                        if current[0] is None:
                            continue
                        retained = connection.execute(
                            """
                            UPDATE final_v3_document_generations
                            SET lifecycle_status = 'RETAINED'
                            WHERE document_id = ? AND document_generation = ?
                              AND lifecycle_status = 'ACTIVE'
                            """,
                            (document_id, int(current[0])),
                        ).rowcount
                        pointed = connection.execute(
                            """
                            UPDATE final_v3_documents SET active_generation = NULL
                            WHERE document_id = ? AND active_generation = ?
                            """,
                            (document_id, int(current[0])),
                        ).rowcount
                        if retained != 1 or pointed != 1:
                            raise _error("document_deactivation_failed", self._operation)
                    FinalV3DocumentSchemaV1.validate_pointers(connection)
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
        except FinalV3DocumentRuntimeError:
            raise
        except Exception:
            raise _error("document_activation_failed", self._operation) from None
        return tuple(
            self._require_generation(
                plan.document_id, plan.document_generation, "ACTIVE"
            )
            for plan in plans
        )

    def read(
        self,
        *,
        document_id: str,
        consumer: DocumentChunkConsumer,
        document_generation: int | None = None,
    ) -> EncryptedDocumentVerificationResult:
        self._operation = FinalV3DocumentRuntimeOperation.READ
        _document_id(document_id)
        if document_generation is not None and (
            not isinstance(document_generation, int)
            or isinstance(document_generation, bool)
            or document_generation < 1
        ):
            raise _error("document_generation_invalid", self._operation)
        with closing(self._factory.connect_read_only()) as connection:
            FinalV3DocumentSchemaV1.validate(
                connection,
                installation_id=self._installation_id,
                database_context_id=self._loaded.database_context_id,
            )
        active = self._active_for(document_id)
        if (
            document_generation is not None
            and active.document_generation != document_generation
        ):
            raise _error("document_active_generation_mismatch", self._operation)
        try:
            result = self._service.stream_verified(
                test_root=self.paths.container_root,
                container=self._container_path(active.storage_id),
                dmk=self._loaded.dmk,
                context=self._context(
                    active.document_id, active.document_generation
                ),
                expected_storage_id=active.storage_id,
                consumer=consumer,
            )
        except EncryptedDocumentError as error:
            raise _error(error.code, self._operation) from None
        self._require_verification_matches(active, result)
        return result

    def replace(
        self,
        *,
        document_id: str,
        source_name: str,
        original_filename: str,
        mime_type: str,
    ) -> FinalV3DocumentGeneration:
        self._operation = FinalV3DocumentRuntimeOperation.REPLACE
        prepared = self.prepare(
            document_id=document_id,
            source_name=source_name,
            original_filename=original_filename,
            mime_type=mime_type,
        )
        return self.activate(
            document_id=document_id,
            document_generation=prepared.document_generation,
        )

    def deactivate(self, *, document_id: str) -> FinalV3DocumentGeneration | None:
        self._operation = FinalV3DocumentRuntimeOperation.DEACTIVATE
        _document_id(document_id)
        self.validate_restart()
        active = self._active_for_optional(document_id)
        if active is None:
            return None
        self._verify_record(active)
        try:
            with closing(self._factory.connect(create=False)) as connection:
                connection.execute("BEGIN IMMEDIATE")
                retained = connection.execute(
                    """
                    UPDATE final_v3_document_generations
                    SET lifecycle_status = 'RETAINED'
                    WHERE document_id = ? AND document_generation = ?
                      AND lifecycle_status = 'ACTIVE'
                    """,
                    (document_id, active.document_generation),
                ).rowcount
                pointer = connection.execute(
                    """
                    UPDATE final_v3_documents SET active_generation = NULL
                    WHERE document_id = ? AND active_generation = ?
                    """,
                    (document_id, active.document_generation),
                ).rowcount
                if retained != 1 or pointer != 1:
                    raise _error("document_deactivation_failed", self._operation)
                FinalV3DocumentSchemaV1.validate_pointers(connection)
                connection.commit()
        except FinalV3DocumentRuntimeError:
            raise
        except Exception:
            raise _error("document_deactivation_failed", self._operation) from None
        return self._require_generation(
            document_id, active.document_generation, "RETAINED"
        )

    def _prepared_for(
        self, document_id: str
    ) -> FinalV3DocumentGeneration | None:
        with closing(self._factory.connect_read_only()) as connection:
            rows = connection.execute(
                _GENERATION_SELECT
                + " WHERE document_id = ? AND lifecycle_status = 'PREPARED'",
                (document_id,),
            ).fetchall()
        if len(rows) > 1:
            raise _error("document_prepared_cardinality_invalid", self._operation)
        return None if not rows else _record_from_row(rows[0])

    def _active_for(self, document_id: str) -> FinalV3DocumentGeneration:
        record = self._active_for_optional(document_id)
        if record is None:
            raise _error("document_active_missing", self._operation)
        return record

    def _active_for_optional(
        self, document_id: str
    ) -> FinalV3DocumentGeneration | None:
        with closing(self._factory.connect_read_only()) as connection:
            row = connection.execute(
                _GENERATION_SELECT
                + " WHERE document_id = ? AND lifecycle_status = 'ACTIVE'",
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        return _record_from_row(row)

    def _service_for_source_root(
        self, source_root: Path
    ) -> SyntheticEncryptedDocumentServiceV1:
        return SyntheticEncryptedDocumentServiceV1(
            random_source=self._random,
            clock=self._clock,
            fault_injector=self._container_fault,
            required_source_prefix=None,
            plain_storage_names=True,
            retain_published_hardlink_evidence=False,
            source_root_override=source_root,
            direct_visible_write=True,
            require_export_layout=False,
        )

    def _require_prepare_plan(
        self,
        plan: FinalV3DocumentPreparePlan | Mapping[str, object],
        *,
        document_id: str,
    ) -> FinalV3DocumentPreparePlan:
        if isinstance(plan, Mapping):
            try:
                if set(plan) != {
                    "document_id",
                    "document_generation",
                    "storage_id",
                    "previous_active_generation",
                }:
                    raise ValueError("fields")
                document_generation = plan["document_generation"]
                if (
                    not isinstance(document_generation, int)
                    or isinstance(document_generation, bool)
                    or document_generation < 1
                ):
                    raise ValueError("document_generation")
                previous_active_generation = plan["previous_active_generation"]
                if previous_active_generation is not None and (
                    not isinstance(previous_active_generation, int)
                    or isinstance(previous_active_generation, bool)
                    or previous_active_generation < 1
                ):
                    raise ValueError("previous_active_generation")
                plan = FinalV3DocumentPreparePlan(
                    document_id=str(plan["document_id"]),
                    document_generation=document_generation,
                    storage_id=str(plan["storage_id"]),
                    previous_active_generation=previous_active_generation,
                )
            except Exception:
                raise _error("document_prepare_plan_invalid", self._operation) from None
        if not isinstance(plan, FinalV3DocumentPreparePlan):
            raise _error("document_prepare_plan_invalid", self._operation)
        _document_id(plan.document_id)
        if plan.document_id != document_id:
            raise _error("document_prepare_plan_conflict", self._operation)
        if (
            not isinstance(plan.document_generation, int)
            or isinstance(plan.document_generation, bool)
            or plan.document_generation < 1
        ):
            raise _error("document_prepare_plan_invalid", self._operation)
        if plan.previous_active_generation is not None and (
            not isinstance(plan.previous_active_generation, int)
            or isinstance(plan.previous_active_generation, bool)
            or plan.previous_active_generation < 1
        ):
            raise _error("document_prepare_plan_invalid", self._operation)
        _uuid(plan.storage_id, "document_storage_id_invalid")
        return plan

    def _require_generation(
        self, document_id: str, generation: int, lifecycle: str
    ) -> FinalV3DocumentGeneration:
        with closing(self._factory.connect_read_only()) as connection:
            row = connection.execute(
                _GENERATION_SELECT
                + " WHERE document_id = ? AND document_generation = ?",
                (document_id, generation),
            ).fetchone()
        if row is None:
            raise _error("document_generation_missing", self._operation)
        record = _record_from_row(row)
        if record.lifecycle_status != lifecycle:
            raise _error("document_generation_lifecycle_invalid", self._operation)
        return record

    def _verify_record(
        self, record: FinalV3DocumentGeneration
    ) -> EncryptedDocumentVerificationResult:
        try:
            verification = self._service.verify(
                test_root=self.paths.container_root,
                container=self._container_path(record.storage_id),
                dmk=self._loaded.dmk,
                context=self._context(
                    record.document_id, record.document_generation
                ),
                expected_storage_id=record.storage_id,
            )
        except EncryptedDocumentError as error:
            raise _error(error.code, self._operation) from None
        self._require_verification_matches(record, verification)
        return verification

    def _require_verification_matches(
        self,
        record: FinalV3DocumentGeneration,
        verification: EncryptedDocumentVerificationResult,
    ) -> None:
        observed = _record_from_verification(
            verification, record.lifecycle_status
        )
        if observed != record:
            raise _error("document_container_metadata_mismatch", self._operation)

    def _validate_storage_inventory(
        self, records: tuple[FinalV3DocumentGeneration, ...]
    ) -> None:
        expected = {
            f"{record.storage_id}{DOCUMENT_CONTAINER_EXTENSION}": record
            for record in records
        }
        try:
            entries = tuple(os.scandir(self.paths.storage_root))
        except OSError:
            raise _error("document_storage_unavailable", self._operation) from None
        observed: dict[str, Any] = {}
        for entry in entries:
            if entry.name == SYNTHETIC_DOCUMENT_STORAGE_MARKER:
                continue
            if not _CONTAINER_NAME.fullmatch(entry.name):
                raise _error("document_storage_inventory_invalid", self._operation)
            try:
                status = entry.stat(follow_symlinks=False)
            except OSError:
                raise _error("document_storage_inventory_invalid", self._operation) from None
            if (
                not stat.S_ISREG(status.st_mode)
                or status.st_nlink != 1
                or entry.name in observed
            ):
                raise _error("document_storage_inventory_invalid", self._operation)
            observed[entry.name] = status
        if set(observed) != set(expected):
            raise _error("document_storage_inventory_invalid", self._operation)
        for name, record in expected.items():
            status = observed[name]
            if status.st_size != record.container_size:
                raise _error("document_container_size_mismatch", self._operation)
            self._verify_record(record)

    def _context(
        self, document_id: str, generation: int
    ) -> DocumentContainerContextV1:
        return DocumentContainerContextV1(
            installation_id=self._installation_id,
            database_context_id=self._loaded.database_context_id,
            document_id=document_id,
            document_generation=generation,
            app_format_version=FINAL_V3_DOCUMENT_APP_FORMAT_VERSION,
        )

    def _container_path(self, storage_id: str) -> Path:
        _uuid(storage_id, "document_storage_id_invalid")
        return self.paths.storage_root / (
            f"{storage_id}{DOCUMENT_CONTAINER_EXTENSION}"
        )

    def _new_uuid(self, code: str) -> str:
        value = self._random.bytes(16)
        if not isinstance(value, bytes) or len(value) != 16:
            raise _error(code, self._operation)
        return str(uuid.UUID(bytes=value, version=4))

    def _container_fault(self, boundary: str) -> None:
        mapped = {
            "writer_after_header_prefix": "during_container_write",
            "writer_after_envelope": "during_container_write",
            "writer_after_manifest": "during_container_write",
            "writer_after_first_chunk": "during_container_write",
            "writer_after_middle_chunk": "during_container_write",
            "writer_before_final": "during_container_write",
            "writer_after_final": "during_container_write",
            "writer_after_file_fsync": "after_write_before_verification",
            "writer_after_retained_directory_fsync": (
                "after_write_before_verification"
            ),
        }.get(boundary)
        if mapped is not None:
            self._emit(mapped)

    def _emit(self, boundary: str) -> None:
        if self._fault_hook is not None:
            self._fault_hook(boundary)


class FinalV3DocumentRuntimeCoordinator:
    """Compose one already-keyed Final-V3 runtime with its document runtime."""

    def __init__(
        self,
        *,
        final_v3: OpenedFinalV3SQLCipherRuntime,
        paths: FinalV3DocumentRuntimePaths,
        loaded_keys: LoadedDatabaseKeyRuntime,
        installation_id: str,
        document_database_create_allowed: bool,
        provider: SQLCipherConnectionProvider,
        scope: FinalV3SQLCipherRuntimeScope,
        environ: Mapping[str, str],
        source_root: Path | None,
        random_source: Any,
        clock: Any,
        fault_hook=None,
    ) -> None:
        self.final_v3 = final_v3
        self.paths = paths
        self.loaded_keys = loaded_keys
        self.installation_id = installation_id
        self.document_database_create_allowed = bool(
            document_database_create_allowed
        )
        self.provider = provider
        self.scope = scope
        self.environment = dict(environ)
        self.source_root = None if source_root is None else Path(source_root)
        self.random_source = random_source
        self.clock = clock
        self.fault_hook = fault_hook

    def open(self) -> OpenedFinalV3DocumentRuntime:
        _uuid(self.installation_id, "document_installation_context_invalid")
        if self.source_root is not None:
            _require_external_source_root(self.source_root, self.paths)
        if (
            self.loaded_keys is not self.final_v3.loaded_keys
            or self.loaded_keys.database_context_id
            != self.final_v3.database_context_id
            or self.loaded_keys.database_key_id != self.final_v3.database_key_id
            or self.loaded_keys.database_key_generation
            != self.final_v3.database_key_generation
        ):
            raise _error(
                "document_key_runtime_binding_mismatch",
                FinalV3DocumentRuntimeOperation.LOAD_KEYS,
            )
        factory = FinalV3DocumentConnectionFactory(
            provider=self.provider,
            paths=self.paths,
            loaded_keys=self.loaded_keys,
            environ=self.environment,
            scope=self.scope,
        )
        database_exists = _path_exists_or_symlink(self.paths.database)
        _require_no_document_database_sidecars(self.paths.database)
        if not database_exists:
            if not self.document_database_create_allowed:
                raise _error(
                    "document_database_initialization_required",
                    FinalV3DocumentRuntimeOperation.LOAD_KEYS,
                )
            if _path_exists_or_symlink(self.paths.container_root):
                raise _error(
                    "document_storage_without_database",
                    FinalV3DocumentRuntimeOperation.LOAD_KEYS,
                )
            with closing(factory.connect(create=True)) as connection:
                FinalV3DocumentSchemaV1.initialize(
                    connection,
                    installation_id=self.installation_id,
                    database_context_id=self.loaded_keys.database_context_id,
                    created_at=_format_utc(self.clock.utc_now()),
                )
            PlatformFilePermissionManager().secure_sqlite_files(self.paths.database)
            _initialize_container_layout(self.paths)
        else:
            if self.document_database_create_allowed:
                raise _error(
                    "document_database_already_exists",
                    FinalV3DocumentRuntimeOperation.LOAD_KEYS,
                )
            if not _path_exists_or_symlink(self.paths.container_root):
                raise _error(
                    "document_storage_missing",
                    FinalV3DocumentRuntimeOperation.LOAD_KEYS,
                )
            _validate_container_layout(self.paths)
        with closing(factory.connect_read_only()) as connection:
            FinalV3DocumentSchemaV1.validate(
                connection,
                installation_id=self.installation_id,
                database_context_id=self.loaded_keys.database_context_id,
            )
        documents = FinalV3DocumentRuntime(
            paths=self.paths,
            factory=factory,
            loaded_keys=self.loaded_keys,
            installation_id=self.installation_id,
            source_root=self.source_root,
            random_source=self.random_source,
            clock=self.clock,
            fault_hook=self.fault_hook,
        )
        documents.validate_restart()
        return OpenedFinalV3DocumentRuntime(
            final_v3=self.final_v3,
            documents=documents,
            database_context_id=self.loaded_keys.database_context_id,
            installation_id=self.installation_id,
        )


def run_gated_final_v3_document_runtime(
    *,
    account_loader,
    authentication_confirmed: bool,
    technical_first_run_confirmed: bool = False,
    document_database_create_allowed: bool = False,
    environ: Mapping[str, str] | None = None,
    key_store=None,
    random_source=None,
    clock=None,
    sqlcipher_provider: SQLCipherConnectionProvider | None = None,
    source_root: Path | None = None,
    fault_hook=None,
) -> FinalV3DocumentRuntimeDecision:
    """Open only under the existing double marker gate; never fall back."""

    environment = dict(os.environ if environ is None else environ)
    gate = FinalV3SQLCipherRuntimeGate()
    gate_decision = gate.resolve(environment)
    if gate_decision.state is not FinalV3SQLCipherRuntimeDecisionState.ACTIVE:
        return FinalV3DocumentRuntimeDecision(
            FinalV3DocumentRuntimeDecisionState.DISABLED
            if gate_decision.state
            is FinalV3SQLCipherRuntimeDecisionState.DISABLED
            else FinalV3DocumentRuntimeDecisionState.BLOCKED,
            error_code=gate_decision.error_code,
            error_operation=(
                None
                if gate_decision.error_code is None
                else FinalV3DocumentRuntimeOperation.CLASSIFY
            ),
        )
    operation = FinalV3DocumentRuntimeOperation.CLASSIFY
    try:
        scope = MarkerGatedFinalV3SQLCipherRuntimeScope(environment)
        paths = FinalV3DocumentRuntimePaths.for_final_v3(scope.require_paths())
        external_source_root = None if source_root is None else Path(source_root)
        if external_source_root is not None:
            _require_external_source_root(external_source_root, paths)
        account = account_loader()
        installation_id = getattr(account, "installation_id", None)
        _uuid(installation_id, "document_installation_context_invalid")
        stable_account_loader = lambda: account
        random = random_source or SystemRandomSource()
        runtime_clock = clock or SystemClock()
        provider = sqlcipher_provider or SQLCipherConnectionProvider(
            expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
            expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
        )
        operation = FinalV3DocumentRuntimeOperation.OPEN_FINAL_V3
        final_v3 = FinalV3SQLCipherRuntimeCoordinator(
            paths=paths.final_v3,
            account_loader=stable_account_loader,
            authentication_confirmed=authentication_confirmed,
            technical_first_run_confirmed=technical_first_run_confirmed,
            key_store=key_store,
            random_source=random,
            clock=runtime_clock,
            sqlcipher_provider=provider,
            fault_hook=fault_hook,
            environ=environment,
            scope=scope,
        ).open()
        operation = FinalV3DocumentRuntimeOperation.LOAD_KEYS
        opened = FinalV3DocumentRuntimeCoordinator(
            final_v3=final_v3,
            paths=paths,
            installation_id=installation_id,
            loaded_keys=final_v3.loaded_keys,
            document_database_create_allowed=document_database_create_allowed,
            provider=provider,
            scope=scope,
            environ=environment,
            source_root=external_source_root,
            random_source=random,
            clock=runtime_clock,
            fault_hook=fault_hook,
        ).open()
        return FinalV3DocumentRuntimeDecision(
            FinalV3DocumentRuntimeDecisionState.ACTIVE,
            runtime=opened,
        )
    except FinalV3DocumentRuntimeError as error:
        return FinalV3DocumentRuntimeDecision(
            FinalV3DocumentRuntimeDecisionState.BLOCKED,
            error_code=error.code,
            error_operation=error.operation,
        )
    except (FinalV3SQLCipherRuntimeError, DatabaseKeyRuntimeError) as error:
        return FinalV3DocumentRuntimeDecision(
            FinalV3DocumentRuntimeDecisionState.BLOCKED,
            error_code=str(getattr(error, "code", "document_runtime_failed")),
            error_operation=operation,
        )
    except Exception:
        return FinalV3DocumentRuntimeDecision(
            FinalV3DocumentRuntimeDecisionState.BLOCKED,
            error_code="document_runtime_failed",
            error_operation=operation,
        )


_GENERATION_SELECT = """
SELECT document_id, document_generation, storage_id, document_key_id,
       document_key_generation, envelope_revision, container_format,
       container_format_version, plaintext_size, plaintext_sha256,
       container_size, container_sha256, mime_type, lifecycle_status,
       created_at
FROM final_v3_document_generations
"""


def _record_from_row(row: Any) -> FinalV3DocumentGeneration:
    record = FinalV3DocumentGeneration(
        document_id=str(row[0]),
        document_generation=int(row[1]),
        storage_id=str(row[2]),
        document_key_id=str(row[3]),
        document_key_generation=int(row[4]),
        envelope_revision=int(row[5]),
        container_format=str(row[6]),
        container_format_version=int(row[7]),
        plaintext_size=int(row[8]),
        plaintext_sha256=str(row[9]),
        container_size=int(row[10]),
        container_sha256=str(row[11]),
        mime_type=str(row[12]),
        lifecycle_status=str(row[13]),
        created_at=str(row[14]),
    )
    if (
        record.lifecycle_status not in _LIFECYCLES
        or not _SHA256.fullmatch(record.plaintext_sha256)
        or not _SHA256.fullmatch(record.container_sha256)
    ):
        raise _error("document_generation_record_invalid")
    _document_id(record.document_id)
    for value, code in (
        (record.storage_id, "document_storage_id_invalid"),
        (record.document_key_id, "document_key_id_invalid"),
    ):
        _uuid(value, code)
    return record


def _record_from_verification(
    result: EncryptedDocumentVerificationResult, lifecycle: str
) -> FinalV3DocumentGeneration:
    manifest = result.manifest
    header = result.header
    return FinalV3DocumentGeneration(
        document_id=manifest.context.document_id,
        document_generation=manifest.context.document_generation,
        storage_id=manifest.storage_id,
        document_key_id=header.document_key_id,
        document_key_generation=header.document_key_generation,
        envelope_revision=header.envelope.rewrap_revision,
        container_format=header.container_format,
        container_format_version=header.container_version,
        plaintext_size=manifest.plaintext_size,
        plaintext_sha256=manifest.plaintext_sha256,
        container_size=result.container_size,
        container_sha256=result.container_sha256,
        mime_type=manifest.mime_type,
        lifecycle_status=lifecycle,
        created_at=manifest.created_at,
    )


def _record_values(record: FinalV3DocumentGeneration) -> tuple[object, ...]:
    return (
        record.document_id,
        record.document_generation,
        record.storage_id,
        record.document_key_id,
        record.document_key_generation,
        record.envelope_revision,
        record.container_format,
        record.container_format_version,
        record.plaintext_size,
        record.plaintext_sha256,
        record.container_size,
        record.container_sha256,
        record.mime_type,
        record.lifecycle_status,
        record.created_at,
    )


def _initialize_container_layout(paths: FinalV3DocumentRuntimePaths) -> None:
    for directory in (
        paths.container_root,
        paths.layout_source_root,
        paths.storage_root,
    ):
        try:
            directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        except OSError:
            raise _error("document_storage_initialization_failed") from None
    _write_marker(
        paths.container_root / SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER,
        SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES,
    )
    _write_marker(
        paths.storage_root / SYNTHETIC_DOCUMENT_STORAGE_MARKER,
        SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES,
    )
    _validate_container_layout(paths)


def _validate_container_layout(paths: FinalV3DocumentRuntimePaths) -> None:
    for directory in (
        paths.container_root,
        paths.layout_source_root,
        paths.storage_root,
    ):
        _require_private_directory(directory)
    _require_marker(
        paths.container_root / SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER,
        SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES,
    )
    _require_marker(
        paths.storage_root / SYNTHETIC_DOCUMENT_STORAGE_MARKER,
        SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES,
    )


def _write_marker(path: Path, payload: bytes) -> None:
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            written = os.write(fd, payload)
            if written != len(payload):
                raise OSError("short marker write")
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        raise _error("document_storage_marker_create_failed") from None


def _require_marker(path: Path, expected: bytes) -> None:
    try:
        status = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(status.st_mode) or status.st_nlink != 1:
            raise OSError("marker type")
        with path.open("rb") as handle:
            payload = handle.read(len(expected) + 1)
    except OSError:
        raise _error("document_storage_marker_invalid") from None
    if payload != expected:
        raise _error("document_storage_marker_invalid")


def _require_private_directory(path: Path) -> None:
    try:
        status = os.stat(path, follow_symlinks=False)
    except OSError:
        raise _error("document_runtime_scope_invalid") from None
    if (
        not stat.S_ISDIR(status.st_mode)
        or stat.S_IMODE(status.st_mode) & 0o077
        or (hasattr(os, "getuid") and status.st_uid != os.getuid())
    ):
        raise _error("document_runtime_scope_invalid")


def _path_exists_or_symlink(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _require_no_document_database_sidecars(path: Path) -> None:
    if any(
        _path_exists_or_symlink(Path(f"{path}{suffix}"))
        for suffix in ("-journal", "-wal", "-shm")
    ):
        raise _error("document_database_sidecar_present")


def _require_external_source_root(
    source_root: Path, paths: FinalV3DocumentRuntimePaths
) -> None:
    if not source_root.is_absolute():
        raise _error("document_source_root_invalid")
    _require_private_directory(source_root)
    source = source_root.resolve()
    managed = paths.final_v3.root.resolve()
    for child, parent in ((source, managed), (managed, source)):
        try:
            child.relative_to(parent)
        except ValueError:
            continue
        raise _error("document_source_root_managed")


def _uuid(value: object, code: str) -> None:
    try:
        validate_uuid4(value)
    except Exception:
        raise _error(code) from None


def _document_id(value: object) -> None:
    if isinstance(value, str) and _MED_DOCUMENT_ID.fullmatch(value):
        return
    _uuid(value, "document_id_invalid")


def _format_utc(value: Any) -> str:
    try:
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        raise _error("document_clock_invalid") from None


def _error(
    code: str,
    operation: FinalV3DocumentRuntimeOperation = (
        FinalV3DocumentRuntimeOperation.CLASSIFY
    ),
) -> FinalV3DocumentRuntimeError:
    return FinalV3DocumentRuntimeError(code, operation=operation)
