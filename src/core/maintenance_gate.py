"""Qt-free in-process maintenance gate for productive database writers."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import threading
from typing import Any, Iterator


class MaintenanceState(str, Enum):
    NORMAL = "NORMAL"
    MAINTENANCE_PENDING = "MAINTENANCE_PENDING"
    MAINTENANCE_ACTIVE = "MAINTENANCE_ACTIVE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class MaintenancePurpose(str, Enum):
    SCHOOL_YEAR_TRANSITION = "school_year_transition"
    BACKUP_RESTORE = "backup_restore"


class MaintenanceGateError(RuntimeError):
    """Stable fail-closed maintenance error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class MaintenanceWriterBlockedError(MaintenanceGateError):
    pass


class MaintenanceCapabilityError(MaintenanceGateError):
    pass


@dataclass(frozen=True, slots=True)
class MaintenanceCapability:
    """Unforgeable in-process authority for one maintenance owner and purpose."""

    owner_id: str
    purpose: MaintenancePurpose
    _token: object


class WriterLease:
    """Exactly-once lease for one already admitted writer."""

    def __init__(
        self,
        gate: MaintenanceGate,
        *,
        counted: bool = True,
        tracked: bool = True,
    ) -> None:
        self._gate = gate
        self._counted = counted
        self._tracked = tracked
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        if self._tracked:
            self._gate._release_writer(counted=self._counted)

    def __enter__(self) -> WriterLease:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()


class MaintenanceGate:
    """Coordinate writer admission and exclusive in-process maintenance.

    Requesting maintenance and attempting activation are non-blocking, so both
    are safe to call from a Qt event handler.  The gate never waits in, pumps,
    or owns a Qt event loop.
    """

    def __init__(self) -> None:
        self._condition = threading.Condition(threading.RLock())
        self._state = MaintenanceState.NORMAL
        self._active_writers = 0
        self._exclusive_writers = 0
        self._capability: MaintenanceCapability | None = None
        self._local = threading.local()

    @property
    def state(self) -> MaintenanceState:
        with self._condition:
            return self._state

    @property
    def active_writer_count(self) -> int:
        with self._condition:
            return self._active_writers

    def begin_writer(self) -> WriterLease:
        with self._condition:
            if self._exclusive_writer_is_authorized():
                return WriterLease(self, counted=False, tracked=False)
            depth = getattr(self._local, "writer_depth", 0)
            if depth:
                self._local.writer_depth = depth + 1
                return WriterLease(self, counted=False)
            if self._state is not MaintenanceState.NORMAL:
                raise MaintenanceWriterBlockedError(
                    "maintenance_writer_blocked"
                )
            self._active_writers += 1
            self._local.writer_depth = 1
            return WriterLease(self)

    def begin_existing_maintenance_writer(self) -> WriterLease:
        """Prove this thread already owns the active exclusive-writer scope."""

        with self._condition:
            if not self._exclusive_writer_is_authorized():
                raise MaintenanceCapabilityError(
                    "maintenance_exclusive_writer_required"
                )
            return WriterLease(self, counted=False, tracked=False)

    def request_maintenance(
        self,
        *,
        owner_id: str,
        purpose: MaintenancePurpose,
    ) -> MaintenanceCapability:
        owner = _require_owner_id(owner_id)
        if not isinstance(purpose, MaintenancePurpose):
            raise MaintenanceCapabilityError("maintenance_purpose_invalid")
        with self._condition:
            if self._state is not MaintenanceState.NORMAL:
                raise MaintenanceCapabilityError(
                    "maintenance_request_not_available"
                )
            capability = MaintenanceCapability(owner, purpose, object())
            self._capability = capability
            self._state = MaintenanceState.MAINTENANCE_PENDING
            self._condition.notify_all()
            return capability

    def activate(
        self,
        capability: MaintenanceCapability,
        *,
        owner_id: str,
    ) -> bool:
        with self._condition:
            self._require_capability(capability, owner_id=owner_id)
            if self._state is MaintenanceState.MAINTENANCE_ACTIVE:
                return True
            if self._state is not MaintenanceState.MAINTENANCE_PENDING:
                raise MaintenanceCapabilityError(
                    "maintenance_activation_not_pending"
                )
            if self._active_writers:
                return False
            self._state = MaintenanceState.MAINTENANCE_ACTIVE
            self._condition.notify_all()
            return True

    def abort(
        self,
        capability: MaintenanceCapability,
        *,
        owner_id: str,
    ) -> None:
        with self._condition:
            self._require_capability(capability, owner_id=owner_id)
            if self._state is MaintenanceState.RECOVERY_REQUIRED:
                raise MaintenanceCapabilityError(
                    "maintenance_recovery_required"
                )
            if self._state not in (
                MaintenanceState.MAINTENANCE_PENDING,
                MaintenanceState.MAINTENANCE_ACTIVE,
            ):
                self._fail_closed_locked()
                raise MaintenanceCapabilityError("maintenance_state_invalid")
            if self._exclusive_writers:
                raise MaintenanceCapabilityError(
                    "maintenance_exclusive_writer_active"
                )
            self._state = MaintenanceState.NORMAL
            self._capability = None
            self._condition.notify_all()

    def mark_recovery_required(self) -> None:
        with self._condition:
            self._fail_closed_locked()

    @contextmanager
    def exclusive_writer(
        self,
        capability: MaintenanceCapability,
        *,
        owner_id: str,
        purpose: MaintenancePurpose,
    ) -> Iterator[None]:
        """Authorize one ACTIVE maintenance owner to pass the writer block."""

        with self._condition:
            self._require_capability(capability, owner_id=owner_id)
            if capability.purpose is not purpose:
                raise MaintenanceCapabilityError(
                    "maintenance_capability_purpose_mismatch"
                )
            if self._state is not MaintenanceState.MAINTENANCE_ACTIVE:
                raise MaintenanceCapabilityError(
                    "maintenance_not_active"
                )
            previous = getattr(self._local, "exclusive_token", None)
            if previous is not None:
                raise MaintenanceCapabilityError(
                    "maintenance_exclusive_writer_nested"
                )
            self._exclusive_writers += 1
            self._local.exclusive_token = capability._token
        try:
            yield
        finally:
            with self._condition:
                self._local.exclusive_token = None
                if self._exclusive_writers <= 0:
                    self._fail_closed_locked()
                    raise MaintenanceGateError(
                        "maintenance_exclusive_writer_count_invalid"
                    )
                self._exclusive_writers -= 1
                self._condition.notify_all()

    def _exclusive_writer_is_authorized(self) -> bool:
        capability = self._capability
        return (
            self._state is MaintenanceState.MAINTENANCE_ACTIVE
            and capability is not None
            and getattr(self._local, "exclusive_token", None)
            is capability._token
        )

    def _require_capability(
        self,
        capability: MaintenanceCapability,
        *,
        owner_id: str,
    ) -> None:
        owner = _require_owner_id(owner_id)
        registered = self._capability
        if (
            registered is None
            or not isinstance(capability, MaintenanceCapability)
            or capability._token is not registered._token
            or capability.owner_id != owner
            or registered.owner_id != owner
        ):
            raise MaintenanceCapabilityError(
                "maintenance_capability_owner_mismatch"
            )

    def _release_writer(self, *, counted: bool) -> None:
        with self._condition:
            depth = getattr(self._local, "writer_depth", 0)
            if depth <= 0:
                self._fail_closed_locked()
                raise MaintenanceGateError("maintenance_writer_count_invalid")
            self._local.writer_depth = depth - 1
            if counted:
                if depth != 1 or self._active_writers <= 0:
                    self._fail_closed_locked()
                    raise MaintenanceGateError(
                        "maintenance_writer_count_invalid"
                    )
                self._active_writers -= 1
            self._condition.notify_all()

    def _fail_closed_locked(self) -> None:
        self._state = MaintenanceState.RECOVERY_REQUIRED
        self._condition.notify_all()


def _require_owner_id(owner_id: str) -> str:
    if not isinstance(owner_id, str) or not owner_id.strip():
        raise MaintenanceCapabilityError("maintenance_owner_invalid")
    return owner_id.strip()


class MaintenanceGuardedConnection:
    """Connection proxy that admits each database write transaction once."""

    def __init__(self, connection: Any, gate: MaintenanceGate) -> None:
        object.__setattr__(self, "_connection", connection)
        object.__setattr__(self, "_gate", gate)
        object.__setattr__(self, "_writer_lease", None)

    def execute(self, sql: str, parameters: object = ()) -> Any:
        control = _statement_control(sql)
        self._admit_if_write(control)
        try:
            result = self._connection.execute(sql, parameters)
        except Exception:
            self._release_if_transaction_ended()
            raise
        self._release_if_transaction_ended()
        return MaintenanceGuardedCursor(result, self)

    def executemany(self, sql: str, parameters: object) -> Any:
        control = _statement_control(sql)
        self._admit_if_write(control)
        try:
            result = self._connection.executemany(sql, parameters)
        except Exception:
            self._release_if_transaction_ended()
            raise
        self._release_if_transaction_ended()
        return MaintenanceGuardedCursor(result, self)

    def executescript(self, sql_script: str) -> Any:
        control = (
            "write" if _script_contains_write(sql_script) else "read"
        )
        self._admit_if_write(control)
        try:
            result = self._connection.executescript(sql_script)
        except Exception:
            self._release_if_transaction_ended()
            raise
        self._release_if_transaction_ended()
        return MaintenanceGuardedCursor(result, self)

    def commit(self) -> None:
        try:
            self._connection.commit()
        finally:
            self._release_if_transaction_ended()

    def rollback(self) -> None:
        try:
            self._connection.rollback()
        finally:
            self._release_if_transaction_ended()

    def close(self) -> None:
        try:
            if self._connection.in_transaction:
                self._connection.rollback()
        finally:
            self._release_writer()
            self._connection.close()

    def cursor(self, *args, **kwargs) -> MaintenanceGuardedCursor:
        return MaintenanceGuardedCursor(
            self._connection.cursor(*args, **kwargs),
            self,
        )

    def blobopen(self, *args, readonly: bool = False, **kwargs) -> Any:
        if not readonly:
            raise MaintenanceGateError(
                "maintenance_blob_writer_unsupported"
            )
        return self._connection.blobopen(
            *args,
            readonly=True,
            **kwargs,
        )

    def deserialize(self, *args, **kwargs) -> None:
        raise MaintenanceGateError(
            "maintenance_deserialize_writer_unsupported"
        )

    def __enter__(self) -> MaintenanceGuardedConnection:
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool | None:
        try:
            return self._connection.__exit__(exc_type, exc_value, traceback)
        finally:
            self._release_if_transaction_ended()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"_connection", "_gate", "_writer_lease"}:
            object.__setattr__(self, name, value)
            return
        setattr(self._connection, name, value)

    def _admit_if_write(self, control: str) -> None:
        if control != "write" or self._writer_lease is not None:
            return
        object.__setattr__(
            self,
            "_writer_lease",
            self._gate.begin_writer(),
        )

    def _release_if_transaction_ended(self) -> None:
        if not self._connection.in_transaction:
            self._release_writer()

    def _release_writer(self) -> None:
        lease = self._writer_lease
        if lease is None:
            return
        object.__setattr__(self, "_writer_lease", None)
        lease.release()


class MaintenanceGuardedCursor:
    """Cursor proxy that cannot bypass its guarded connection."""

    def __init__(
        self,
        cursor: Any,
        connection: MaintenanceGuardedConnection,
    ) -> None:
        object.__setattr__(self, "_cursor", cursor)
        object.__setattr__(self, "_guarded_connection", connection)

    def execute(self, sql: str, parameters: object = ()) -> Any:
        control = _statement_control(sql)
        self._guarded_connection._admit_if_write(control)
        try:
            self._cursor.execute(sql, parameters)
        except Exception:
            self._guarded_connection._release_if_transaction_ended()
            raise
        self._guarded_connection._release_if_transaction_ended()
        return self

    def executemany(self, sql: str, parameters: object) -> Any:
        control = _statement_control(sql)
        self._guarded_connection._admit_if_write(control)
        try:
            self._cursor.executemany(sql, parameters)
        except Exception:
            self._guarded_connection._release_if_transaction_ended()
            raise
        self._guarded_connection._release_if_transaction_ended()
        return self

    def __iter__(self):
        return iter(self._cursor)

    @property
    def connection(self) -> MaintenanceGuardedConnection:
        return self._guarded_connection

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"_cursor", "_guarded_connection"}:
            object.__setattr__(self, name, value)
            return
        setattr(self._cursor, name, value)


_WRITE_KEYWORDS = frozenset(
    {
        "ALTER",
        "ANALYZE",
        "ATTACH",
        "CREATE",
        "DELETE",
        "DETACH",
        "DROP",
        "INSERT",
        "REINDEX",
        "REPLACE",
        "UPDATE",
        "VACUUM",
    }
)


def _statement_control(sql: str) -> str:
    normalized = _without_leading_sql_comments(sql).lstrip()
    upper = normalized.upper()
    if upper.startswith("COMMIT") or upper.startswith("END"):
        return "commit"
    if upper.startswith("ROLLBACK"):
        return "rollback"
    if upper.startswith("BEGIN IMMEDIATE") or upper.startswith(
        "BEGIN EXCLUSIVE"
    ):
        return "write"
    first = upper.split(None, 1)[0] if upper else ""
    if first in _WRITE_KEYWORDS:
        return "write"
    if first == "PRAGMA" and "=" in upper:
        pragma_name = upper[6:].split("=", 1)[0].strip()
        if pragma_name not in {"FOREIGN_KEYS", "QUERY_ONLY", "BUSY_TIMEOUT"}:
            return "write"
    if first == "WITH":
        padded = f" {upper} "
        if any(f" {keyword} " in padded for keyword in _WRITE_KEYWORDS):
            return "write"
    return "read"


def _script_contains_write(sql_script: str) -> bool:
    return any(
        _statement_control(statement) == "write"
        for statement in sql_script.split(";")
        if statement.strip()
    )


def _without_leading_sql_comments(sql: str) -> str:
    remaining = sql
    while True:
        stripped = remaining.lstrip()
        if stripped.startswith("--"):
            newline = stripped.find("\n")
            return "" if newline < 0 else _without_leading_sql_comments(
                stripped[newline + 1 :]
            )
        if stripped.startswith("/*"):
            end = stripped.find("*/", 2)
            return "" if end < 0 else _without_leading_sql_comments(
                stripped[end + 2 :]
            )
        return stripped


def product_writer(method):
    """Guard one complete product write aggregate through ``self.database``."""

    @wraps(method)
    def guarded(self, *args, **kwargs):
        database = getattr(self, "database", None)
        gate = getattr(database, "maintenance_gate", None)
        if not isinstance(gate, MaintenanceGate):
            raise MaintenanceGateError("maintenance_gate_missing")
        with gate.begin_writer():
            return method(self, *args, **kwargs)

    return guarded
