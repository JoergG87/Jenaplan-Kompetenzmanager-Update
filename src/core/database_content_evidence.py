"""Deterministic typed full-row evidence. Values never leave working memory."""
from dataclasses import dataclass
import hashlib
import struct

from .schema_upgrade import UpgradeError, UpgradeArtifact


@dataclass(frozen=True)
class DatabaseContentEvidence:
    tables: tuple[tuple[str, int, str], ...]


def _frame(value: bytes) -> bytes:
    return len(value).to_bytes(8, "big") + value


def _typed(value) -> bytes:
    if value is None:
        return b"n"
    if type(value) is int:
        return b"i" + str(value).encode("ascii")
    if type(value) is float:
        return b"r" + struct.pack("!d", value)
    if isinstance(value, str):
        return b"s" + value.encode("utf-8")
    if isinstance(value, bytes):
        return b"b" + value
    raise UpgradeError("upgrade_value_type_unsupported")


def database_content_evidence(connection) -> DatabaseContentEvidence:
    tables = connection.execute(
        "SELECT name FROM sqlite_schema WHERE type='table' "
        "AND (name NOT LIKE 'sqlite_%' OR name='sqlite_sequence') ORDER BY name"
    ).fetchall()
    result = []
    for (name,) in tables:
        quoted = '"' + str(name).replace('"', '""') + '"'
        cursor = connection.execute(f"SELECT * FROM {quoted}")
        columns = tuple(item[0] for item in cursor.description)
        rows = sorted(b"".join(_frame(_typed(value)) for value in row) for row in cursor)
        digest = hashlib.sha256()
        digest.update(_frame(str(name).encode("utf-8")))
        for column in columns:
            digest.update(_frame(column.encode("utf-8")))
        digest.update(len(rows).to_bytes(8, "big"))
        for row in rows:
            digest.update(_frame(row))
        result.append((str(name), len(rows), digest.hexdigest()))
    return DatabaseContentEvidence(tuple(result))


def require_same_content(left: DatabaseContentEvidence, right: DatabaseContentEvidence) -> None:
    if left != right:
        raise UpgradeError("upgrade_data_changed")


@dataclass(frozen=True)
class UpgradeSourceVerification:
    artifact: UpgradeArtifact
    main_content: DatabaseContentEvidence
    companion_content: DatabaseContentEvidence
