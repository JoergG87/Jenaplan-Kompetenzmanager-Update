"""Shared checks for the curriculum catalog quality tools."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


CATALOG_FIELDS = (
    "competency_id",
    "subject_key",
    "subject_display_name",
    "subject_full_name",
    "official_subject_name",
    "school_context_name",
    "grade_band",
    "learning_stage",
    "learning_area",
    "competency_group",
    "competency_text",
    "competency_label",
    "source_reference",
    "catalog_status",
    "catalog_default_active",
    "activation_group_key",
    "is_core_subject",
    "is_active",
)

REQUIRED_FIELDS = tuple(field for field in CATALOG_FIELDS if field != "activation_group_key")
BOOL_FIELDS = ("catalog_default_active", "is_core_subject", "is_active")
LEARNING_STAGE_VALUES = {"stage_1_3", "stage_4", "cross_stage"}
CATALOG_STATUS_VALUES = {"current", "legacy"}
COMPETENCY_ID_PATTERN = re.compile(r"^CMP-\d{6}$")
TECHNICAL_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

TEXT_FIELDS = (
    "subject_display_name",
    "subject_full_name",
    "official_subject_name",
    "school_context_name",
    "grade_band",
    "competency_text",
    "competency_label",
    "source_reference",
)
HIERARCHY_FIELDS = ("subject_key", "learning_area", "competency_group")
METADATA_FIELDS = (
    "catalog_status",
    "catalog_default_active",
    "activation_group_key",
    "is_core_subject",
    "is_active",
)


@dataclass(frozen=True)
class CatalogIssue:
    """One validation or comparison finding."""

    code: str
    message: str
    line_number: int | None = None

    def format(self) -> str:
        prefix = self.code
        if self.line_number is not None:
            prefix = f"{prefix} line {self.line_number}"
        return f"{prefix}: {self.message}"


def read_catalog(path: Path) -> tuple[tuple[str, ...], tuple[dict[str, str], ...]]:
    """Read a semicolon-delimited curriculum catalog."""
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";")
        fieldnames = tuple(reader.fieldnames or ())
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            normalized_row = {
                str(key): value
                for key, value in row.items()
                if key is not None
            }
            normalized_row["_line_number"] = str(line_number)
            rows.append(normalized_row)
    return fieldnames, tuple(rows)


def validate_catalog(path: Path) -> tuple[CatalogIssue, ...]:
    """Validate the current catalog structure and row-level invariants."""
    fieldnames, rows = read_catalog(path)
    issues: list[CatalogIssue] = []
    if fieldnames != CATALOG_FIELDS:
        issues.append(
            CatalogIssue(
                "HEADER_MISMATCH",
                "CSV header must match the approved curriculum catalog v1 structure.",
            )
        )

    seen_ids: dict[str, int] = {}
    text_by_hierarchy: dict[tuple[str, str, str, str, str], str] = {}
    subject_meta: dict[str, tuple[str, str, str, str, str]] = {}
    for row in rows:
        line_number = int(row["_line_number"])
        _validate_required_fields(row, line_number, issues)
        _validate_row_values(row, line_number, issues)

        competency_id = row.get("competency_id", "").strip()
        if competency_id:
            previous_line = seen_ids.get(competency_id)
            if previous_line is not None:
                issues.append(
                    CatalogIssue(
                        "DUPLICATE_ID",
                        f"{competency_id} is already used on line {previous_line}.",
                        line_number,
                    )
                )
            else:
                seen_ids[competency_id] = line_number

        subject_key = row.get("subject_key", "").strip()
        if subject_key:
            meta = (
                row.get("subject_display_name", "").strip(),
                row.get("subject_full_name", "").strip(),
                row.get("official_subject_name", "").strip(),
                row.get("school_context_name", "").strip(),
                row.get("is_core_subject", "").strip().casefold(),
            )
            previous_meta = subject_meta.setdefault(subject_key, meta)
            if previous_meta != meta:
                issues.append(
                    CatalogIssue(
                        "INCONSISTENT_SUBJECT",
                        f"{subject_key} has inconsistent subject metadata.",
                        line_number,
                    )
                )

        hierarchy_key = (
            subject_key,
            row.get("learning_stage", "").strip(),
            row.get("learning_area", "").strip(),
            row.get("competency_group", "").strip(),
            _normalize_text(row.get("competency_text", "")),
        )
        if all(hierarchy_key):
            previous_id = text_by_hierarchy.get(hierarchy_key)
            if previous_id and previous_id != competency_id:
                issues.append(
                    CatalogIssue(
                        "DUPLICATE_COMPETENCY_TEXT",
                        (
                            f"{competency_id} duplicates competency_text in the same "
                            f"subject/stage/hierarchy as {previous_id}."
                        ),
                        line_number,
                    )
                )
            text_by_hierarchy.setdefault(hierarchy_key, competency_id)

    return tuple(issues)


def compare_catalogs(
    old_path: Path,
    new_path: Path,
) -> tuple[CatalogIssue, ...]:
    """Compare two catalog versions and report protected ID changes."""
    old_fields, old_rows = read_catalog(old_path)
    new_fields, new_rows = read_catalog(new_path)
    issues: list[CatalogIssue] = []
    if old_fields != CATALOG_FIELDS:
        issues.append(CatalogIssue("OLD_HEADER_MISMATCH", "Old catalog header is not approved."))
    if new_fields != CATALOG_FIELDS:
        issues.append(CatalogIssue("NEW_HEADER_MISMATCH", "New catalog header is not approved."))

    old_by_id = _rows_by_id(old_rows, "old", issues)
    new_by_id = _rows_by_id(new_rows, "new", issues)
    old_ids = set(old_by_id)
    new_ids = set(new_by_id)

    for competency_id in sorted(new_ids - old_ids):
        issues.append(
            CatalogIssue(
                "NEW_COMPETENCY",
                f"{competency_id} is new.",
                _line_number(new_by_id[competency_id]),
            )
        )
    for competency_id in sorted(old_ids - new_ids):
        issues.append(
            CatalogIssue(
                "DELETED_COMPETENCY",
                f"{competency_id} disappeared from the new catalog.",
                _line_number(old_by_id[competency_id]),
            )
        )

    for competency_id in sorted(old_ids & new_ids):
        old_row = old_by_id[competency_id]
        new_row = new_by_id[competency_id]
        for field_name in TEXT_FIELDS:
            if _value(old_row, field_name) != _value(new_row, field_name):
                issues.append(
                    CatalogIssue(
                        "TEXT_CHANGED",
                        f"{competency_id} changed {field_name}.",
                        _line_number(new_row),
                    )
                )
        for field_name in HIERARCHY_FIELDS:
            if _value(old_row, field_name) != _value(new_row, field_name):
                issues.append(
                    CatalogIssue(
                        "HIERARCHY_CHANGED",
                        f"{competency_id} changed {field_name}.",
                        _line_number(new_row),
                    )
                )
        if _value(old_row, "catalog_status") != _value(new_row, "catalog_status"):
            issues.append(
                CatalogIssue(
                    "STATUS_CHANGED",
                    f"{competency_id} changed catalog_status.",
                    _line_number(new_row),
                )
            )
        if _value(old_row, "learning_stage") != _value(new_row, "learning_stage"):
            issues.append(
                CatalogIssue(
                    "LEARNING_STAGE_CHANGED",
                    f"{competency_id} changed learning_stage.",
                    _line_number(new_row),
                )
            )
        for field_name in METADATA_FIELDS:
            if field_name in {"catalog_status"}:
                continue
            if _value(old_row, field_name) != _value(new_row, field_name):
                issues.append(
                    CatalogIssue(
                        "METADATA_CHANGED",
                        f"{competency_id} changed {field_name}.",
                        _line_number(new_row),
                    )
                )
    return tuple(issues)


def next_competency_ids(path: Path, count: int = 1) -> tuple[str, ...]:
    """Return the next global CMP IDs after the current maximum."""
    _, rows = read_catalog(path)
    max_number = 0
    used_ids = {
        row.get("competency_id", "").strip()
        for row in rows
        if COMPETENCY_ID_PATTERN.fullmatch(row.get("competency_id", "").strip())
    }
    for competency_id in used_ids:
        max_number = max(max_number, int(competency_id.removeprefix("CMP-")))
    return tuple(f"CMP-{number:06d}" for number in range(max_number + 1, max_number + count + 1))


def has_blocking_compare_issue(issues: tuple[CatalogIssue, ...]) -> bool:
    """Return whether comparison findings require explicit catalog review."""
    blocking_codes = {
        "OLD_HEADER_MISMATCH",
        "NEW_HEADER_MISMATCH",
        "DUPLICATE_ID",
        "DELETED_COMPETENCY",
        "TEXT_CHANGED",
        "HIERARCHY_CHANGED",
        "STATUS_CHANGED",
        "LEARNING_STAGE_CHANGED",
        "METADATA_CHANGED",
    }
    return any(issue.code in blocking_codes for issue in issues)


def _validate_required_fields(
    row: dict[str, str],
    line_number: int,
    issues: list[CatalogIssue],
) -> None:
    for field_name in REQUIRED_FIELDS:
        value = row.get(field_name)
        if value is None or not value.strip():
            issues.append(
                CatalogIssue(
                    "MISSING_REQUIRED_FIELD",
                    f"{field_name} is required.",
                    line_number,
                )
            )
        elif value != value.strip():
            issues.append(
                CatalogIssue(
                    "UNTRIMMED_VALUE",
                    f"{field_name} has leading or trailing whitespace.",
                    line_number,
                )
            )
    activation_group_key = row.get("activation_group_key", "")
    if activation_group_key != activation_group_key.strip():
        issues.append(
            CatalogIssue(
                "UNTRIMMED_VALUE",
                "activation_group_key has leading or trailing whitespace.",
                line_number,
            )
        )


def _validate_row_values(
    row: dict[str, str],
    line_number: int,
    issues: list[CatalogIssue],
) -> None:
    competency_id = row.get("competency_id", "").strip()
    if competency_id and not COMPETENCY_ID_PATTERN.fullmatch(competency_id):
        issues.append(
            CatalogIssue(
                "INVALID_COMPETENCY_ID",
                f"{competency_id!r} must use CMP-######.",
                line_number,
            )
        )
    subject_key = row.get("subject_key", "").strip()
    if subject_key and not TECHNICAL_KEY_PATTERN.fullmatch(subject_key):
        issues.append(
            CatalogIssue(
                "INVALID_SUBJECT_KEY",
                f"{subject_key!r} must be a stable lowercase technical key.",
                line_number,
            )
        )
    learning_stage = row.get("learning_stage", "").strip()
    if learning_stage and learning_stage not in LEARNING_STAGE_VALUES:
        issues.append(
            CatalogIssue(
                "INVALID_LEARNING_STAGE",
                f"{learning_stage!r} is not allowed.",
                line_number,
            )
        )
    catalog_status = row.get("catalog_status", "").strip()
    if catalog_status and catalog_status not in CATALOG_STATUS_VALUES:
        issues.append(
            CatalogIssue(
                "INVALID_CATALOG_STATUS",
                f"{catalog_status!r} is not allowed.",
                line_number,
            )
        )
    activation_group_key = row.get("activation_group_key", "").strip()
    if activation_group_key and not TECHNICAL_KEY_PATTERN.fullmatch(activation_group_key):
        issues.append(
            CatalogIssue(
                "INVALID_ACTIVATION_GROUP_KEY",
                f"{activation_group_key!r} must be a generic lowercase technical key.",
                line_number,
            )
        )
    for field_name in BOOL_FIELDS:
        value = row.get(field_name, "").strip().casefold()
        if value and value not in {"true", "false"}:
            issues.append(
                CatalogIssue(
                    "INVALID_BOOL",
                    f"{field_name} must be true or false.",
                    line_number,
                )
            )
    if (
        catalog_status == "legacy"
        and row.get("catalog_default_active", "").strip().casefold() != "false"
    ):
        issues.append(
            CatalogIssue(
                "LEGACY_DEFAULT_ACTIVE",
                "legacy competencies must not be default documentation targets.",
                line_number,
            )
        )
    if (
        activation_group_key
        and row.get("catalog_default_active", "").strip().casefold() != "false"
    ):
        issues.append(
            CatalogIssue(
                "OPTIONAL_GROUP_DEFAULT_ACTIVE",
                "competencies with activation_group_key must default inactive.",
                line_number,
            )
        )


def _rows_by_id(
    rows: tuple[dict[str, str], ...],
    label: str,
    issues: list[CatalogIssue],
) -> dict[str, dict[str, str]]:
    rows_by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        competency_id = row.get("competency_id", "").strip()
        if not competency_id:
            continue
        if competency_id in rows_by_id:
            issues.append(
                CatalogIssue(
                    "DUPLICATE_ID",
                    f"{competency_id} is duplicated in the {label} catalog.",
                    _line_number(row),
                )
            )
            continue
        rows_by_id[competency_id] = row
    return rows_by_id


def _line_number(row: dict[str, str]) -> int | None:
    value = row.get("_line_number")
    if value is None:
        return None
    return int(value)


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _value(row: dict[str, str], field_name: str) -> str:
    return row.get(field_name, "").strip()
