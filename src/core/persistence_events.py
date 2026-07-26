"""Monotone persistence events for competency-confirmation freshness."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


LEGACY_UNKNOWN_TIMESTAMP = "0001-01-01T00:00:00Z"


class PersistenceEventKind(str, Enum):
    OBSERVATION_CREATED = "observation_created"
    OBSERVATION_UPDATED = "observation_updated"
    OBSERVATION_COMPETENCY_CHANGED = "observation_competency_changed"
    OBSERVATION_DEACTIVATED = "observation_deactivated"
    CONFIRMATION_UPSERTED = "confirmation_upserted"
    HISTORICAL_OBSERVATION_STATE = "historical_observation_state"
    HISTORICAL_CONFIRMATION_STATE = "historical_confirmation_state"


class PersistenceOrderingState(str, Enum):
    ORDERED = "ordered"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class PersistenceEventRecord:
    event_sequence: int | None
    operation_token: str
    operation_index: int
    operation_payload_hash: str
    event_kind: str
    student_id: str
    competency_id: str | None
    observation_id: str | None
    technical_timestamp: str
    ordering_state: str


@dataclass(frozen=True)
class CompetencyFreshness:
    observation_sequence: int | None = None
    confirmation_sequence: int | None = None
    historical_unknown: bool = False

    @property
    def state(self) -> str:
        if self.historical_unknown:
            return "confirmation_unknown"
        if self.confirmation_sequence is None:
            return "observed_unconfirmed" if self.observation_sequence is not None else ""
        if (
            self.observation_sequence is not None
            and self.observation_sequence > self.confirmation_sequence
        ):
            return "newer_observations"
        return "confirmed"


PERSISTENCE_EVENTS_SCHEMA_SQL = """
CREATE TABLE persistence_events (
    event_sequence INTEGER PRIMARY KEY,
    operation_token TEXT NOT NULL,
    operation_index INTEGER NOT NULL CHECK (operation_index >= 0),
    operation_payload_hash TEXT NOT NULL
        CHECK (length(operation_payload_hash) = 64),
    event_kind TEXT NOT NULL CHECK (
        event_kind IN (
            'observation_created',
            'observation_updated',
            'observation_competency_changed',
            'observation_deactivated',
            'confirmation_upserted',
            'historical_observation_state',
            'historical_confirmation_state'
        )
    ),
    student_id TEXT NOT NULL,
    competency_id TEXT,
    observation_id TEXT,
    technical_timestamp TEXT NOT NULL,
    ordering_state TEXT NOT NULL CHECK (
        ordering_state IN ('ordered', 'unknown', 'not_applicable')
    ),
    UNIQUE (operation_token, operation_index),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (observation_id) REFERENCES observations(observation_id),
    CHECK (
        (
            event_kind IN ('observation_created', 'observation_updated')
            AND competency_id IS NULL
            AND observation_id IS NOT NULL
            AND ordering_state = 'not_applicable'
        )
        OR (
            event_kind IN (
                'observation_competency_changed',
                'observation_deactivated',
                'historical_observation_state'
            )
            AND competency_id IS NOT NULL
            AND observation_id IS NOT NULL
            AND ordering_state IN ('ordered', 'unknown')
        )
        OR (
            event_kind IN (
                'confirmation_upserted',
                'historical_confirmation_state'
            )
            AND competency_id IS NOT NULL
            AND observation_id IS NULL
            AND ordering_state IN ('ordered', 'unknown')
        )
    )
)
"""


def canonical_utc_second(value: str) -> str | None:
    """Normalize an ISO timestamp to a canonical UTC second."""
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def canonical_payload_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def migrate_persistence_events(
    connection: sqlite3.Connection,
    *,
    target_user_version: int,
) -> None:
    """Create and backfill the sole V2 table inside the caller transaction."""
    if _table_exists(connection, "persistence_events"):
        return
    orphaned_student_references = connection.execute(
        """
        SELECT COUNT(*)
        FROM observations AS o
        LEFT JOIN students AS s ON s.student_id = o.student_id
        WHERE s.student_id IS NULL
        """
    ).fetchone()[0]
    if orphaned_student_references:
        # An incomplete pre-registry development schema is not a registered V1
        # migration source. Keep its version and data untouched.
        return
    connection.execute(PERSISTENCE_EVENTS_SCHEMA_SQL)
    observation_rows = connection.execute(
        """
        SELECT
            o.observation_id,
            o.student_id,
            o.updated_at,
            r.competency_id,
            r.rating
        FROM observations AS o
        JOIN observation_competency_ratings AS r
          ON r.observation_id = o.observation_id
        """
    ).fetchall()
    confirmation_rows = connection.execute(
        """
        SELECT student_id, competency_id, confirmed_at, confirmed_rating, note
        FROM student_competency_confirmations
        """
    ).fetchall()

    prepared: list[dict[str, object]] = []
    invalid_pairs: set[tuple[str, str]] = set()
    cross_kind_groups: dict[tuple[str, str, str], set[str]] = {}
    for row in observation_rows:
        source = {
            "kind": PersistenceEventKind.HISTORICAL_OBSERVATION_STATE.value,
            "observation_id": row["observation_id"],
            "student_id": row["student_id"],
            "competency_id": row["competency_id"],
            "updated_at": row["updated_at"],
            "rating": row["rating"],
        }
        normalized = canonical_utc_second(row["updated_at"])
        pair = (row["student_id"], row["competency_id"])
        if normalized is None:
            invalid_pairs.add(pair)
            normalized = LEGACY_UNKNOWN_TIMESTAMP
        prepared.append(
            {
                **source,
                "technical_timestamp": normalized,
                "payload_hash": canonical_payload_hash(source),
                "source_kind": "observation",
            }
        )
        cross_kind_groups.setdefault((*pair, normalized), set()).add("observation")
    for row in confirmation_rows:
        source = {
            "kind": PersistenceEventKind.HISTORICAL_CONFIRMATION_STATE.value,
            "student_id": row["student_id"],
            "competency_id": row["competency_id"],
            "confirmed_at": row["confirmed_at"],
            "confirmed_rating": row["confirmed_rating"],
            "note": row["note"] or "",
        }
        normalized = canonical_utc_second(row["confirmed_at"])
        pair = (row["student_id"], row["competency_id"])
        if normalized is None:
            invalid_pairs.add(pair)
            normalized = LEGACY_UNKNOWN_TIMESTAMP
        prepared.append(
            {
                **source,
                "technical_timestamp": normalized,
                "payload_hash": canonical_payload_hash(source),
                "source_kind": "confirmation",
                "observation_id": None,
            }
        )
        cross_kind_groups.setdefault((*pair, normalized), set()).add("confirmation")

    # Different valid timestamp groups are ordered. No ordering inside a
    # same-resolution group is ever used for fachliche semantics.
    prepared.sort(key=lambda item: str(item["technical_timestamp"]))
    for item in prepared:
        pair = (str(item["student_id"]), str(item["competency_id"]))
        group = (*pair, str(item["technical_timestamp"]))
        unknown = pair in invalid_pairs or cross_kind_groups[group] == {
            "observation",
            "confirmation",
        }
        source_identity = {
            "kind": item["kind"],
            "student_id": item["student_id"],
            "competency_id": item["competency_id"],
            "observation_id": item.get("observation_id"),
        }
        token = "migration-v1-v2:" + canonical_payload_hash(source_identity)
        connection.execute(
            """
            INSERT INTO persistence_events (
                operation_token,
                operation_index,
                operation_payload_hash,
                event_kind,
                student_id,
                competency_id,
                observation_id,
                technical_timestamp,
                ordering_state
            )
            VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                token,
                item["payload_hash"],
                item["kind"],
                item["student_id"],
                item["competency_id"],
                item.get("observation_id"),
                item["technical_timestamp"],
                (
                    PersistenceOrderingState.UNKNOWN.value
                    if unknown
                    else PersistenceOrderingState.ORDERED.value
                ),
            ),
        )
    connection.execute(f"PRAGMA user_version = {int(target_user_version)}")


class SQLitePersistenceEventRepository:
    """Append and read persistence events without deriving fachliche dates."""

    def __init__(self, database: object) -> None:
        self.database = database

    @staticmethod
    def append(
        connection: sqlite3.Connection,
        event: PersistenceEventRecord,
    ) -> int:
        cursor = connection.execute(
            """
            INSERT INTO persistence_events (
                operation_token,
                operation_index,
                operation_payload_hash,
                event_kind,
                student_id,
                competency_id,
                observation_id,
                technical_timestamp,
                ordering_state
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.operation_token,
                event.operation_index,
                event.operation_payload_hash,
                event.event_kind,
                event.student_id,
                event.competency_id,
                event.observation_id,
                event.technical_timestamp,
                event.ordering_state,
            ),
        )
        return int(cursor.lastrowid)

    def list_for_student(
        self,
        student_id: str,
    ) -> tuple[PersistenceEventRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    event_sequence,
                    operation_token,
                    operation_index,
                    operation_payload_hash,
                    event_kind,
                    student_id,
                    competency_id,
                    observation_id,
                    technical_timestamp,
                    ordering_state
                FROM persistence_events
                WHERE student_id = ?
                ORDER BY event_sequence
                """,
                (student_id,),
            ).fetchall()
        return tuple(PersistenceEventRecord(*row) for row in rows)

    def freshness_for_student(
        self,
        student_id: str,
    ) -> dict[str, CompetencyFreshness]:
        events = self.list_for_student(student_id)
        grouped: dict[str, list[PersistenceEventRecord]] = {}
        for event in events:
            if event.competency_id:
                grouped.setdefault(event.competency_id, []).append(event)
        result: dict[str, CompetencyFreshness] = {}
        observation_kinds = {
            PersistenceEventKind.OBSERVATION_COMPETENCY_CHANGED.value,
            PersistenceEventKind.OBSERVATION_DEACTIVATED.value,
            PersistenceEventKind.HISTORICAL_OBSERVATION_STATE.value,
        }
        confirmation_kinds = {
            PersistenceEventKind.CONFIRMATION_UPSERTED.value,
            PersistenceEventKind.HISTORICAL_CONFIRMATION_STATE.value,
        }
        for competency_id, competency_events in grouped.items():
            latest_ordered_new = max(
                (
                    event.event_sequence or 0
                    for event in competency_events
                    if event.ordering_state == PersistenceOrderingState.ORDERED.value
                    and event.event_kind
                    not in {
                        PersistenceEventKind.HISTORICAL_OBSERVATION_STATE.value,
                        PersistenceEventKind.HISTORICAL_CONFIRMATION_STATE.value,
                    }
                ),
                default=0,
            )
            historical_events = tuple(
                event
                for event in competency_events
                if event.event_kind
                in {
                    PersistenceEventKind.HISTORICAL_OBSERVATION_STATE.value,
                    PersistenceEventKind.HISTORICAL_CONFIRMATION_STATE.value,
                }
            )
            latest_historical_timestamp = max(
                (
                    event.technical_timestamp
                    for event in historical_events
                    if event.technical_timestamp != LEGACY_UNKNOWN_TIMESTAMP
                ),
                default="",
            )
            invalid_historical_timestamp = any(
                event.ordering_state == PersistenceOrderingState.UNKNOWN.value
                and event.technical_timestamp == LEGACY_UNKNOWN_TIMESTAMP
                for event in historical_events
            )
            latest_historical_group_unknown = bool(
                latest_historical_timestamp
                and any(
                    event.ordering_state
                    == PersistenceOrderingState.UNKNOWN.value
                    and event.technical_timestamp == latest_historical_timestamp
                    for event in historical_events
                )
            )
            historical_unknown = (
                latest_ordered_new == 0
                and (
                    invalid_historical_timestamp
                    or latest_historical_group_unknown
                )
            )
            observation_sequence = max(
                (
                    event.event_sequence or 0
                    for event in competency_events
                    if event.event_kind in observation_kinds
                ),
                default=0,
            )
            confirmation_sequence = max(
                (
                    event.event_sequence or 0
                    for event in competency_events
                    if event.event_kind in confirmation_kinds
                ),
                default=0,
            )
            result[competency_id] = CompetencyFreshness(
                observation_sequence or None,
                confirmation_sequence or None,
                historical_unknown,
            )
        return result


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        is not None
    )
