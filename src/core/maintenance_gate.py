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
    SCHEMA_UPGRADE = "schema_upgrade"


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


# All provider instances share physical-handle admission, including backups.
_connection_condition = threading.Condition(threading.RLock())
_connection_counts: dict[str, int] = {}
_connection_freezes: dict[str, object] = {}
_connection_identities: dict[str, set[tuple[int, int]]] = {}
_connection_inode_freezes: dict[tuple[int, int], object] = {}
_connection_local = threading.local()


def checkpoint_connection_active() -> bool:
    return bool(getattr(_connection_local, "checkpoint", False))


def _connection_path(path) -> str:
    from pathlib import Path
    return str(Path(path).absolute().resolve())


def _connection_identity(path):
    import os
    try:
        info = os.stat(path, follow_symlinks=False)
        return info.st_dev, info.st_ino
    except FileNotFoundError:
        return None


class RegisteredConnection:
    def __init__(self, connection, path: str):
        object.__setattr__(self, "_raw", connection)
        object.__setattr__(self, "_registered_path", path)
        object.__setattr__(self, "_closed", False)

    def close(self):
        if self._closed:
            return
        self._raw.close()
        object.__setattr__(self, "_closed", True)
        with _connection_condition:
            _connection_counts[self._registered_path] -= 1
            _connection_condition.notify_all()

    def __del__(self):
        try:
            self.close()
        except BaseException:
            # Failed physical closes remain registered, including thread errors.
            pass

    def backup(self, target, *args, **kwargs):
        return self._raw.backup(getattr(target, "_raw", target), *args, **kwargs)

    def execute(self, *args, **kwargs):
        return RegisteredCursor(self._raw.execute(*args, **kwargs), self)

    def executemany(self, *args, **kwargs):
        return RegisteredCursor(self._raw.executemany(*args, **kwargs), self)

    def executescript(self, *args, **kwargs):
        return RegisteredCursor(self._raw.executescript(*args, **kwargs), self)

    def cursor(self, *args, **kwargs):
        return RegisteredCursor(self._raw.cursor(*args, **kwargs), self)

    def __enter__(self):
        self._raw.__enter__()
        return self

    def __exit__(self, *args):
        return self._raw.__exit__(*args)

    def __getattr__(self, name):
        return getattr(self._raw, name)

    def __setattr__(self, name, value):
        setattr(self._raw, name, value)


class RegisteredCursor:
    def __init__(self, cursor, connection):
        object.__setattr__(self, "_cursor", cursor)
        object.__setattr__(self, "connection", connection)

    def execute(self, *args, **kwargs):
        self._cursor.execute(*args, **kwargs)
        return self

    def executemany(self, *args, **kwargs):
        self._cursor.executemany(*args, **kwargs)
        return self

    def executescript(self, *args, **kwargs):
        self._cursor.executescript(*args, **kwargs)
        return self

    def __iter__(self):
        return iter(self._cursor)

    def __next__(self):
        return next(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def __setattr__(self, name, value):
        setattr(self._cursor, name, value)


def registered_connection_open(method):
    @wraps(method)
    def opened(self, path, *args, **kwargs):
        key = _connection_path(path)
        with _connection_condition:
            identity = _connection_identity(key)
            frozen = _connection_freezes.get(key) or _connection_inode_freezes.get(identity)
            if frozen is not None and getattr(_connection_local, "token", None) is not frozen:
                raise MaintenanceGateError("upgrade_connection_open_frozen")
            _connection_counts[key] = _connection_counts.get(key, 0) + 1
            if identity is not None:
                _connection_identities.setdefault(key, set()).add(identity)
        try:
            connection = method(self, path, *args, **kwargs)
            with _connection_condition:
                identity = _connection_identity(key)
                if identity is not None:
                    _connection_identities.setdefault(key, set()).add(identity)
            if getattr(_connection_local, "token", None) is not None and not checkpoint_connection_active():
                connection.execute("PRAGMA query_only = ON")
        except BaseException:
            if "connection" in locals():
                try:
                    connection.close()
                except BaseException:
                    # Do not claim an unsuccessfully closed handle disappeared.
                    raise
            with _connection_condition:
                _connection_counts[key] -= 1
                _connection_condition.notify_all()
            raise
        return RegisteredConnection(connection, key)
    return opened


class ConnectionDrain:
    """Physical-handle freeze. Exit retains admission until explicit safe abort.

    Transactions and readers must finish and close themselves. No force-close
    or implicit commit is permitted. Privileged verification opens are tracked.
    """
    def __init__(self, paths, *, gate, capability, owner_id,
                 require_authority, timeout=0, runtime_paths=None):
        from pathlib import Path
        self._paths = tuple(Path(path).absolute() for path in paths)
        self._keys = tuple(_connection_path(path) for path in self.paths)
        if not self.paths or len(set(self._keys)) != len(self._keys):
            raise MaintenanceGateError("upgrade_drain_paths_invalid")
        self._runtime_keys = set(self._keys if runtime_paths is None else
                                 (_connection_path(path) for path in runtime_paths))
        if not self._runtime_keys or not self._runtime_keys.issubset(self._keys):
            raise MaintenanceGateError("upgrade_drain_runtime_paths_invalid")
        self._runtime_paths = tuple(Path(key) for key in sorted(self._runtime_keys))
        self.gate, self.capability, self.owner_id = gate, capability, owner_id
        self._authority = require_authority
        self.timeout = timeout
        self._token = object()
        self._active = False
        self._parents = ()
        self._checkpointed = set()
        self._identities = set()

    @property
    def paths(self):
        return self._paths

    @property
    def runtime_paths(self):
        return self._runtime_paths

    def _require_authority(self):
        self._authority()
        with self.gate._condition:
            self.gate._require_capability(self.capability, owner_id=self.owner_id)
            if (self.gate._state is not MaintenanceState.MAINTENANCE_ACTIVE
                    or self.capability.purpose is not MaintenancePurpose.SCHEMA_UPGRADE
                    or self.gate._active_writers):
                raise MaintenanceGateError("upgrade_drain_maintenance_required")

    def __enter__(self):
        import time
        import os
        import stat
        self._require_authority()
        parents = []
        for path in self.paths:
            for parent in (path.parent, *path.parent.parents):
                info = parent.lstat()
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                    raise MaintenanceGateError("upgrade_drain_parent_invalid")
            info = path.parent.lstat()
            if info.st_uid != os.getuid() or info.st_mode & 0o022:
                raise MaintenanceGateError("upgrade_drain_parent_invalid")
            parents.append((info.st_dev, info.st_ino))
        with _connection_condition:
            if self._active or any(key in _connection_freezes for key in self._keys):
                raise MaintenanceGateError("upgrade_drain_already_frozen")
            identities = {_connection_identity(key) for key in self._keys} - {None}
            if any(identity in _connection_inode_freezes for identity in identities):
                raise MaintenanceGateError("upgrade_drain_inode_already_frozen")
            for key in self._keys:
                _connection_freezes[key] = self._token
            self._identities = identities
            for identity in identities:
                _connection_inode_freezes[identity] = self._token
            self._active = True
            self._parents = tuple(parents)
            deadline = time.monotonic() + self.timeout
            while self._has_connections():
                self._require_authority()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise MaintenanceGateError("upgrade_connections_active")
                _connection_condition.wait(min(remaining, 0.05))
        self._require_authority()
        return self

    def _has_connections(self):
        return any(count and (key in self._keys or
                   bool(_connection_identities.get(key, set()) & self._identities))
                   for key, count in _connection_counts.items())

    def require_frozen(self):
        self._require_authority()
        if (tuple(_connection_path(path) for path in self.paths) != self._keys
                or set(_connection_path(path) for path in self.runtime_paths) != self._runtime_keys):
            raise MaintenanceGateError("upgrade_drain_paths_changed")
        with _connection_condition:
            if not self._active or any(_connection_freezes.get(key) is not self._token for key in self._keys):
                raise MaintenanceGateError("upgrade_drain_authority_lost")
            current_identities = {_connection_identity(key) for key in self._keys} - {None}
            if any(_connection_inode_freezes.get(identity) not in (None, self._token)
                   for identity in current_identities):
                raise MaintenanceGateError("upgrade_drain_inode_authority_conflict")
            for identity in current_identities:
                self._identities.add(identity)
                _connection_inode_freezes[identity] = self._token
            if self._has_connections():
                raise MaintenanceGateError("upgrade_connections_active")
        for path, expected in zip(self.paths, self._parents):
            info = path.parent.lstat()
            if (info.st_dev, info.st_ino) != expected or path.parent.is_symlink():
                raise MaintenanceGateError("upgrade_drain_parent_changed")

    @contextmanager
    def maintenance_connections(self):
        self.require_frozen()
        if getattr(_connection_local, "token", None) is not None:
            raise MaintenanceGateError("upgrade_maintenance_connections_nested")
        _connection_local.token = self._token
        try:
            yield
        finally:
            _connection_local.token = None
            self.require_frozen()

    def checkpoint(self, path, opener):
        from contextlib import closing
        key = _connection_path(path)
        if key not in self._keys:
            raise MaintenanceGateError("upgrade_checkpoint_path_invalid")
        with self.maintenance_connections():
            _connection_local.checkpoint = True
            try:
                with closing(opener()) as connection:
                    registered = connection
                    if isinstance(connection, MaintenanceGuardedConnection):
                        registered = connection._connection
                    if (not isinstance(registered, RegisteredConnection)
                            or registered._registered_path != key
                            or registered._closed):
                        raise MaintenanceGateError("upgrade_checkpoint_connection_mismatch")
                    if connection.in_transaction:
                        raise MaintenanceGateError("upgrade_checkpoint_transaction_active")
                    row = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                    if row is None or len(row) != 3 or int(row[0]) != 0 or int(row[1]) != int(row[2]):
                        raise MaintenanceGateError("upgrade_checkpoint_busy")
            finally:
                _connection_local.checkpoint = False
        self._checkpointed.add(key)
        self._require_no_sidecars()

    @contextmanager
    def synthetic_transaction_connection(self, path, opener):
        """One explicitly writable main connection for the synthetic SQL spike.

        Ordinary maintenance opens remain query-only. Never grants a product
        root, companion, inherited lease or file-exchange write capability.
        """
        from contextlib import closing
        from pathlib import Path
        from .runtime_root_protection import require_mutable_test_root, RuntimeRootKind
        path = Path(path)
        expected = path.parent.parent / "final-v4-sqlcipher-runtime-v1" / "final-v4.sqlcipher"
        protection = require_mutable_test_root(path.parent.parent)
        if (path != expected or _connection_path(path) not in self._runtime_keys
                or protection is None or protection.kind is not RuntimeRootKind.SYNTHETIC_TEST):
            raise MaintenanceGateError("transaction_synthetic_main_required")
        with self._transaction_connection(path, opener) as connection:
            yield connection

    @contextmanager
    def product_transaction_connection(self, path, opener):
        """Explicit product main transaction, under the same frozen drain."""
        from pathlib import Path
        from .runtime_root_protection import require_product_runtime_root
        path = Path(path)
        root = path.parent.parent
        require_product_runtime_root(root, first_run=False)
        if (path != root / "final-v4-sqlcipher-runtime-v1/final-v4.sqlcipher"
                or _connection_path(path) not in self._runtime_keys):
            raise MaintenanceGateError("transaction_product_main_required")
        with self._transaction_connection(path, opener) as connection:
            yield connection

    @contextmanager
    def _transaction_connection(self, path, opener):
        from contextlib import closing
        with self.maintenance_connections():
            with closing(opener()) as connection:
                if (not isinstance(connection, RegisteredConnection)
                        or connection._registered_path != _connection_path(path)
                        or connection.in_transaction):
                    raise MaintenanceGateError("transaction_connection_mismatch")
                connection.execute("PRAGMA query_only=OFF")
                if connection.execute("PRAGMA query_only").fetchone()[0] != 0:
                    raise MaintenanceGateError("transaction_connection_read_only")
                yield connection

    def _require_no_sidecars(self):
        from pathlib import Path
        for path in self.paths:
            for suffix in ("-wal", "-shm", "-journal"):
                sidecar = Path(str(path) + suffix)
                try:
                    sidecar.lstat()
                except FileNotFoundError:
                    continue
                raise MaintenanceGateError("upgrade_drain_sidecar_present")

    def require_drained(self):
        self.require_frozen()
        if not self._runtime_keys.issubset(self._checkpointed):
            raise MaintenanceGateError("upgrade_checkpoint_required")
        self._require_no_sidecars()

    def release(self):
        self.require_frozen()
        with _connection_condition:
            for key in self._keys:
                del _connection_freezes[key]
            for identity in self._identities:
                if _connection_inode_freezes.get(identity) is self._token:
                    del _connection_inode_freezes[identity]
            self._active = False
            _connection_condition.notify_all()

    def __exit__(self, *args):
        return False
