"""Read-only SQLite schema identity and database compatibility policy."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


DATABASE_COMPATIBILITY_VERSION = 1

# Registered after calculating the complete canonical schema identity of the
# c029aff V1 schema. The versioned V1 schema and its known unversioned direct
# predecessor intentionally have the same schema identity; user_version is the
# differentiating version metadata.
V1_COMPATIBILITY_FINGERPRINT = (
    "cc24b317186c65a47d4e06662115847154ba4772a582b206c099031676597057"
)
KNOWN_UNVERSIONED_V1_PREDECESSOR_FINGERPRINT = (
    "cc24b317186c65a47d4e06662115847154ba4772a582b206c099031676597057"
)


class DatabaseCompatibilityStatus(str, Enum):
    """Compatibility classification for one inspected database."""

    EXACT = "exact"
    MIGRATION_REQUIRED = "migration_required"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True)
class DatabaseSchemaIdentity:
    """Stable identity of all compatibility-relevant SQLite schema objects."""

    fingerprint: str
    object_count: int


@dataclass(frozen=True)
class DatabaseVersionInfo:
    """Version metadata derived from the inspected database and policy."""

    sqlite_user_version: int
    compatibility_version: int | None


@dataclass(frozen=True)
class DatabaseCompatibilityResult:
    """Complete read-only compatibility decision for one database."""

    status: DatabaseCompatibilityStatus
    schema_identity: DatabaseSchemaIdentity
    version: DatabaseVersionInfo
    reason: str


class DatabaseCompatibilityError(RuntimeError):
    """Base class for controlled database compatibility failures."""


class UnsupportedDatabaseVersionError(DatabaseCompatibilityError):
    """Raised when a database declares a newer unsupported version."""


class UnknownDatabaseSchemaError(DatabaseCompatibilityError):
    """Raised when no registered schema identity matches."""


class DatabaseVersionMismatchError(DatabaseCompatibilityError):
    """Raised when declared and actual compatibility metadata disagree."""


class DatabaseCompatibilityPolicy:
    """Classify version metadata together with a complete schema identity."""

    def evaluate(
        self,
        *,
        sqlite_user_version: int,
        schema_identity: DatabaseSchemaIdentity,
    ) -> DatabaseCompatibilityResult:
        fingerprint = schema_identity.fingerprint
        if (
            sqlite_user_version == DATABASE_COMPATIBILITY_VERSION
            and fingerprint == V1_COMPATIBILITY_FINGERPRINT
        ):
            return DatabaseCompatibilityResult(
                status=DatabaseCompatibilityStatus.EXACT,
                schema_identity=schema_identity,
                version=DatabaseVersionInfo(
                    sqlite_user_version=sqlite_user_version,
                    compatibility_version=DATABASE_COMPATIBILITY_VERSION,
                ),
                reason="Die Datenbank entspricht exakt dem registrierten V1-Schema.",
            )
        if (
            sqlite_user_version == 0
            and fingerprint == KNOWN_UNVERSIONED_V1_PREDECESSOR_FINGERPRINT
        ):
            return DatabaseCompatibilityResult(
                status=DatabaseCompatibilityStatus.MIGRATION_REQUIRED,
                schema_identity=schema_identity,
                version=DatabaseVersionInfo(
                    sqlite_user_version=sqlite_user_version,
                    compatibility_version=DATABASE_COMPATIBILITY_VERSION,
                ),
                reason=(
                    "Die bekannte unversionierte V1-Vorgaengerstruktur benoetigt "
                    "eine spaetere kontrollierte Migration."
                ),
            )
        if sqlite_user_version > DATABASE_COMPATIBILITY_VERSION:
            reason = "Die Datenbankversion ist neuer als diese Anwendung unterstuetzt."
        elif sqlite_user_version == 0:
            reason = "Die unversionierte Datenbankstruktur ist nicht registriert."
        elif sqlite_user_version == DATABASE_COMPATIBILITY_VERSION:
            reason = "Die deklarierte V1-Datenbank besitzt ein unbekanntes Schema."
        else:
            reason = "Die Datenbankversion wird nicht unterstuetzt."
        return DatabaseCompatibilityResult(
            status=DatabaseCompatibilityStatus.INCOMPATIBLE,
            schema_identity=schema_identity,
            version=DatabaseVersionInfo(
                sqlite_user_version=sqlite_user_version,
                compatibility_version=None,
            ),
            reason=reason,
        )

    @staticmethod
    def require_backup_compatible(
        result: DatabaseCompatibilityResult,
    ) -> DatabaseCompatibilityResult:
        """Accept exact V1 and its registered unversioned predecessor only."""
        if result.status is not DatabaseCompatibilityStatus.INCOMPATIBLE:
            return result
        if result.version.sqlite_user_version > DATABASE_COMPATIBILITY_VERSION:
            raise UnsupportedDatabaseVersionError(result.reason)
        if result.version.sqlite_user_version == DATABASE_COMPATIBILITY_VERSION:
            raise DatabaseVersionMismatchError(result.reason)
        raise UnknownDatabaseSchemaError(result.reason)


class DatabaseCompatibilityInspector:
    """Inspect SQLite compatibility without changing the database."""

    def __init__(self, policy: DatabaseCompatibilityPolicy | None = None) -> None:
        self.policy = policy or DatabaseCompatibilityPolicy()

    def inspect(self, database_path: Path) -> DatabaseCompatibilityResult:
        database_path = Path(database_path)
        try:
            with closing(_open_read_only_database(database_path)) as connection:
                sqlite_user_version = int(
                    connection.execute("PRAGMA user_version").fetchone()[0]
                )
                schema = _compatibility_schema(connection)
        except (OSError, sqlite3.Error) as error:
            raise DatabaseCompatibilityError(
                f"Die Datenbank-Kompatibilitaet konnte nicht gelesen werden: {error}"
            ) from error
        identity = _schema_identity(schema)
        return self.policy.evaluate(
            sqlite_user_version=sqlite_user_version,
            schema_identity=identity,
        )

    @staticmethod
    def schema_identity(database_path: Path) -> DatabaseSchemaIdentity:
        """Return only the complete canonical schema identity, read-only."""
        try:
            with closing(_open_read_only_database(Path(database_path))) as connection:
                return _schema_identity(_compatibility_schema(connection))
        except (OSError, sqlite3.Error) as error:
            raise DatabaseCompatibilityError(
                f"Der Datenbank-Fingerprint konnte nicht gelesen werden: {error}"
            ) from error


def _schema_identity(schema: dict[str, object]) -> DatabaseSchemaIdentity:
    canonical = _canonical_json_bytes(schema)
    objects = schema["objects"]
    return DatabaseSchemaIdentity(
        fingerprint=hashlib.sha256(canonical).hexdigest(),
        object_count=len(objects) if isinstance(objects, list) else 0,
    )


def _compatibility_schema(connection: sqlite3.Connection) -> dict[str, object]:
    tables: list[dict[str, object]] = []
    for table_name, table_sql in connection.execute(
        "SELECT name, sql FROM sqlite_schema "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall():
        quoted_table = _quote_identifier(str(table_name))
        columns = [
            {
                "cid": int(row[0]),
                "name": str(row[1]),
                "type": str(row[2]),
                "not_null": bool(row[3]),
                "default": row[4],
                "primary_key_position": int(row[5]),
                "hidden": int(row[6]) if len(row) > 6 else 0,
            }
            for row in connection.execute(
                f"PRAGMA table_xinfo({quoted_table})"
            ).fetchall()
        ]
        foreign_keys = sorted(
            (
                {
                    "id": int(row[0]),
                    "sequence": int(row[1]),
                    "table": str(row[2]),
                    "from": str(row[3]),
                    "to": None if row[4] is None else str(row[4]),
                    "on_update": str(row[5]),
                    "on_delete": str(row[6]),
                    "match": str(row[7]),
                }
                for row in connection.execute(
                    f"PRAGMA foreign_key_list({quoted_table})"
                ).fetchall()
            ),
            key=lambda item: (item["id"], item["sequence"]),
        )
        tables.append(
            {
                "type": "table",
                "name": str(table_name),
                "sql": _normalize_schema_sql(str(table_sql)),
                "columns": columns,
                "foreign_keys": foreign_keys,
            }
        )

    indexes: list[dict[str, object]] = []
    for index_name, table_name, index_sql in connection.execute(
        "SELECT name, tbl_name, sql FROM sqlite_schema "
        "WHERE type = 'index' AND sql IS NOT NULL "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall():
        quoted_index = _quote_identifier(str(index_name))
        columns = [
            {
                "sequence": int(row[0]),
                "column_id": int(row[1]),
                "name": None if row[2] is None else str(row[2]),
                "descending": bool(row[3]),
                "collation": None if row[4] is None else str(row[4]),
                "key": bool(row[5]),
            }
            for row in connection.execute(
                f"PRAGMA index_xinfo({quoted_index})"
            ).fetchall()
        ]
        indexes.append(
            {
                "type": "index",
                "name": str(index_name),
                "table": str(table_name),
                "sql": _normalize_schema_sql(str(index_sql)),
                "columns": columns,
            }
        )

    other_objects = [
        {
            "type": str(object_type),
            "name": str(name),
            "table": str(table_name),
            "sql": _normalize_schema_sql(str(sql)),
        }
        for object_type, name, table_name, sql in connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_schema "
            "WHERE type IN ('trigger', 'view') AND name NOT LIKE 'sqlite_%' "
            "ORDER BY type, name"
        ).fetchall()
    ]
    objects = [*tables, *indexes, *other_objects]
    objects.sort(key=lambda item: (str(item["type"]), str(item["name"])))
    return {"objects": objects}


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _open_read_only_database(path: Path) -> sqlite3.Connection:
    uri = f"{path.resolve().as_uri()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _normalize_schema_sql(sql: str) -> str:
    """Normalize stored schema SQL while preserving quoted token contents."""
    tokens: list[str] = []
    index = 0
    length = len(sql)
    while index < length:
        character = sql[index]
        if character.isspace():
            index += 1
            continue
        if sql.startswith("--", index):
            newline = sql.find("\n", index + 2)
            index = length if newline < 0 else newline + 1
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            index = length if end < 0 else end + 2
            continue
        if character in {"'", '"', "`", "["}:
            closing = "]" if character == "[" else character
            start = index
            index += 1
            while index < length:
                if sql[index] == closing:
                    if (
                        closing != "]"
                        and index + 1 < length
                        and sql[index + 1] == closing
                    ):
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            tokens.append(sql[start:index])
            continue
        if character.isalnum() or character in {"_", "$"}:
            start = index
            index += 1
            while index < length and (
                sql[index].isalnum() or sql[index] in {"_", "$"}
            ):
                index += 1
            tokens.append(sql[start:index].lower())
            continue
        tokens.append(character)
        index += 1
    if tokens and tokens[-1] == ";":
        tokens.pop()
    return " ".join(tokens)
