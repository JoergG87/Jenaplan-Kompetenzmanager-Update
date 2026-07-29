"""Read-only database startup classification and runtime admission."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import stat

from .database_compatibility import (
    DATABASE_COMPATIBILITY_VERSION,
    REGISTERED_V3_SCHEMA_FINGERPRINT,
    REGISTERED_V3_SCHEMA_VERSION,
    V2_COMPATIBILITY_FINGERPRINT,
    DatabaseCompatibilityError,
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityStatus,
)


_SAFE_RESTORE_STATUSES = frozenset(
    {
        "normal_start",
        "completed",
        "rolled_back",
        "aborted_before_replacement",
    }
)


class DatabaseStartupState(str, Enum):
    """Controlled states before any product database runtime is opened."""

    DATABASE_NOT_FOUND = "DATABASE_NOT_FOUND"
    V2_MIGRATION_REQUIRED = "V2_MIGRATION_REQUIRED"
    V2_BOOTSTRAP_READY = "V2_BOOTSTRAP_READY"
    V3_READY = "V3_READY"
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class DatabaseStartupDetection:
    """Immutable read-only database detection without a runtime disposition."""

    state: DatabaseStartupState
    reason_code: str
    sqlite_user_version: int | None = None
    schema_fingerprint: str | None = None
    schema_object_count: int | None = None


@dataclass(frozen=True, slots=True)
class DatabaseStartupDecision:
    """Immutable coordinator decision kept separate from schema detection."""

    detected_state: DatabaseStartupState
    state: DatabaseStartupState
    reason_code: str
    normal_runtime_allowed: bool
    rescan_after_runtime_storage_preparation: bool
    sqlite_user_version: int | None = None
    schema_fingerprint: str | None = None
    schema_object_count: int | None = None

    def __post_init__(self) -> None:
        if (
            self.normal_runtime_allowed
            and self.rescan_after_runtime_storage_preparation
        ):
            raise ValueError("database_startup_disposition_conflict")


class DatabaseStartupResolver:
    """Classify one database path without creating or changing it."""

    def __init__(
        self,
        inspector: DatabaseCompatibilityInspector | None = None,
    ) -> None:
        self._inspector = inspector or DatabaseCompatibilityInspector()

    def resolve(self, database_path: Path) -> DatabaseStartupDetection:
        """Return the registered database state using read-only inspection."""

        database_path = Path(database_path)
        for sidecar in (
            Path(f"{database_path}-wal"),
            Path(f"{database_path}-shm"),
        ):
            try:
                sidecar.lstat()
            except FileNotFoundError:
                continue
            except OSError:
                return _recovery_detection(
                    "DB-START-SQLITE-SIDECAR-UNREADABLE"
                )
            return _recovery_detection(
                "DB-START-SQLITE-SIDECAR-RECOVERY-REQUIRED"
            )
        try:
            metadata = database_path.lstat()
        except FileNotFoundError:
            return DatabaseStartupDetection(
                DatabaseStartupState.DATABASE_NOT_FOUND,
                "DB-START-DATABASE-NOT-FOUND",
            )
        except OSError:
            return _recovery_detection("DB-START-DATABASE-PATH-UNREADABLE")
        if not stat.S_ISREG(metadata.st_mode):
            return _recovery_detection("DB-START-DATABASE-PATH-UNSAFE")

        try:
            compatibility = self._inspector.inspect(database_path)
        except (DatabaseCompatibilityError, OSError):
            return _recovery_detection("DB-START-DATABASE-UNREADABLE")

        version = compatibility.version.sqlite_user_version
        identity = compatibility.schema_identity
        if (
            compatibility.status is DatabaseCompatibilityStatus.EXACT
            and version == DATABASE_COMPATIBILITY_VERSION
            and identity.fingerprint == V2_COMPATIBILITY_FINGERPRINT
        ):
            return DatabaseStartupDetection(
                DatabaseStartupState.V2_MIGRATION_REQUIRED,
                "DB-START-V2-MIGRATION-REQUIRED",
                version,
                identity.fingerprint,
                identity.object_count,
            )
        if (
            version == REGISTERED_V3_SCHEMA_VERSION
            and identity.fingerprint == REGISTERED_V3_SCHEMA_FINGERPRINT
        ):
            return DatabaseStartupDetection(
                DatabaseStartupState.V3_READY,
                "DB-START-V3-READY",
                version,
                identity.fingerprint,
                identity.object_count,
            )
        if identity.object_count == 0:
            return DatabaseStartupDetection(
                DatabaseStartupState.RECOVERY_REQUIRED,
                "DB-START-EMPTY-DATABASE-FILE",
                version,
                identity.fingerprint,
                identity.object_count,
            )
        return DatabaseStartupDetection(
            DatabaseStartupState.SCHEMA_UNSUPPORTED,
            "DB-START-SCHEMA-UNSUPPORTED",
            version,
            identity.fingerprint,
            identity.object_count,
        )


class DatabaseStartupCoordinator:
    """Apply restore and runtime-admission policy to read-only detection."""

    def __init__(
        self,
        resolver: DatabaseStartupResolver | None = None,
    ) -> None:
        self._resolver = resolver or DatabaseStartupResolver()

    def coordinate(
        self,
        database_path: Path,
        *,
        restore_status: str,
        runtime_storage_prepared: bool = False,
        new_database_initialization_allowed: bool = False,
    ) -> DatabaseStartupDecision:
        """Decide whether product runtime preparation may continue."""

        if restore_status not in _SAFE_RESTORE_STATUSES:
            return _decision_from_detection(
                _recovery_detection("DB-START-RESTORE-RECOVERY-REQUIRED")
            )

        detection = self._resolver.resolve(database_path)
        if (
            detection.state is DatabaseStartupState.DATABASE_NOT_FOUND
            and restore_status != "normal_start"
        ):
            return _decision_from_detection(
                _recovery_detection("DB-START-DATABASE-MISSING-AFTER-RESTORE")
            )
        if detection.state is DatabaseStartupState.DATABASE_NOT_FOUND:
            if not new_database_initialization_allowed:
                return _decision_from_detection(
                    detection,
                    state=DatabaseStartupState.RECOVERY_REQUIRED,
                    reason_code="DB-START-DATABASE-MISSING-RECOVERY-REQUIRED",
                )
            return _decision_from_detection(
                detection,
                normal_runtime_allowed=runtime_storage_prepared,
                rescan_after_runtime_storage_preparation=(
                    not runtime_storage_prepared
                ),
                reason_code=(
                    "DB-START-NEW-V2-RUNTIME-ALLOWED"
                    if runtime_storage_prepared
                    else detection.reason_code
                ),
            )
        if detection.state is DatabaseStartupState.V2_MIGRATION_REQUIRED:
            return _decision_from_detection(
                detection,
                state=DatabaseStartupState.V2_BOOTSTRAP_READY,
                reason_code="DB-START-V2-BOOTSTRAP-READY",
            )
        if detection.state is DatabaseStartupState.V3_READY:
            return _decision_from_detection(
                detection,
                reason_code="DB-START-V3-RUNTIME-NOT-COMPATIBLE",
            )
        return _decision_from_detection(detection)


def _recovery_detection(reason_code: str) -> DatabaseStartupDetection:
    return DatabaseStartupDetection(
        DatabaseStartupState.RECOVERY_REQUIRED,
        reason_code,
    )


def _decision_from_detection(
    detection: DatabaseStartupDetection,
    *,
    state: DatabaseStartupState | None = None,
    reason_code: str | None = None,
    normal_runtime_allowed: bool = False,
    rescan_after_runtime_storage_preparation: bool = False,
) -> DatabaseStartupDecision:
    return DatabaseStartupDecision(
        detected_state=detection.state,
        state=detection.state if state is None else state,
        reason_code=detection.reason_code if reason_code is None else reason_code,
        normal_runtime_allowed=normal_runtime_allowed,
        rescan_after_runtime_storage_preparation=(
            rescan_after_runtime_storage_preparation
        ),
        sqlite_user_version=detection.sqlite_user_version,
        schema_fingerprint=detection.schema_fingerprint,
        schema_object_count=detection.schema_object_count,
    )
