from __future__ import annotations

import csv
from pathlib import Path

from scripts.curriculum_catalog_tools import (
    CATALOG_FIELDS,
    compare_catalogs,
    has_blocking_compare_issue,
    next_competency_ids,
    validate_catalog,
)


def test_current_curriculum_catalog_passes_quality_gate() -> None:
    issues = validate_catalog(Path("data") / "curriculum_catalog_v1.csv")

    assert issues == ()


def test_validate_curriculum_catalog_reports_structural_errors(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.csv"
    rows = [
        _row("CMP-000001"),
        _row(
            "CMP-000001",
            learning_stage="stage_5",
            catalog_status="draft",
            catalog_default_active="yes",
            activation_group_key="Sport Option",
        ),
    ]
    _write_catalog(catalog, rows)

    issues = validate_catalog(catalog)
    codes = {issue.code for issue in issues}

    assert "DUPLICATE_ID" in codes
    assert "INVALID_LEARNING_STAGE" in codes
    assert "INVALID_CATALOG_STATUS" in codes
    assert "INVALID_BOOL" in codes
    assert "INVALID_ACTIVATION_GROUP_KEY" in codes


def test_validate_curriculum_catalog_reports_duplicate_text_in_hierarchy(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog.csv"
    _write_catalog(
        catalog,
        [
            _row("CMP-000001", competency_text="Text lesen"),
            _row("CMP-000002", competency_text="  text   lesen "),
        ],
    )

    issues = validate_catalog(catalog)

    assert any(issue.code == "DUPLICATE_COMPETENCY_TEXT" for issue in issues)


def test_validate_curriculum_catalog_keeps_legacy_out_of_default_targets(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog.csv"
    _write_catalog(
        catalog,
        [
            _row(
                "CMP-000001",
                catalog_status="legacy",
                catalog_default_active="true",
            ),
        ],
    )

    issues = validate_catalog(catalog)

    assert any(issue.code == "LEGACY_DEFAULT_ACTIVE" for issue in issues)


def test_validate_curriculum_catalog_keeps_optional_groups_default_inactive(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog.csv"
    _write_catalog(
        catalog,
        [
            _row(
                "CMP-000001",
                catalog_default_active="true",
                activation_group_key="optional_project_area",
            ),
        ],
    )

    issues = validate_catalog(catalog)

    assert any(issue.code == "OPTIONAL_GROUP_DEFAULT_ACTIVE" for issue in issues)


def test_compare_curriculum_catalog_reports_protected_id_changes(
    tmp_path: Path,
) -> None:
    old_catalog = tmp_path / "old.csv"
    new_catalog = tmp_path / "new.csv"
    _write_catalog(
        old_catalog,
        [
            _row("CMP-000001", competency_text="Text lesen"),
            _row("CMP-000002", learning_area="Zahlen"),
        ],
    )
    _write_catalog(
        new_catalog,
        [
            _row("CMP-000001", competency_text="Neuer Inhalt"),
            _row("CMP-000002", learning_area="Geometrie", learning_stage="stage_4"),
            _row("CMP-000003"),
        ],
    )

    issues = compare_catalogs(old_catalog, new_catalog)
    codes = [issue.code for issue in issues]

    assert "NEW_COMPETENCY" in codes
    assert "TEXT_CHANGED" in codes
    assert "HIERARCHY_CHANGED" in codes
    assert "LEARNING_STAGE_CHANGED" in codes
    assert has_blocking_compare_issue(issues)


def test_compare_curriculum_catalog_reports_disappeared_ids(tmp_path: Path) -> None:
    old_catalog = tmp_path / "old.csv"
    new_catalog = tmp_path / "new.csv"
    _write_catalog(old_catalog, [_row("CMP-000001"), _row("CMP-000002")])
    _write_catalog(new_catalog, [_row("CMP-000001")])

    issues = compare_catalogs(old_catalog, new_catalog)

    assert any(issue.code == "DELETED_COMPETENCY" for issue in issues)
    assert has_blocking_compare_issue(issues)


def test_next_competency_ids_uses_global_maximum_without_reusing_gaps(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog.csv"
    _write_catalog(
        catalog,
        [
            _row("CMP-000001"),
            _row("CMP-000003"),
        ],
    )

    assert next_competency_ids(catalog, count=3) == (
        "CMP-000004",
        "CMP-000005",
        "CMP-000006",
    )


def _write_catalog(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=CATALOG_FIELDS,
            delimiter=";",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _row(
    competency_id: str,
    *,
    subject_key: str = "deutsch",
    subject_display_name: str = "Deutsch",
    subject_full_name: str = "Deutsch",
    official_subject_name: str = "Deutsch",
    school_context_name: str = "Quelle",
    grade_band: str = "1-4",
    learning_stage: str = "cross_stage",
    learning_area: str = "Lesen",
    competency_group: str = "Grundlage",
    competency_text: str = "Text lesen",
    competency_label: str = "Lesen",
    source_reference: str = "Quelle",
    catalog_status: str = "current",
    catalog_default_active: str = "true",
    activation_group_key: str = "",
    is_core_subject: str = "true",
    is_active: str = "true",
) -> dict[str, str]:
    return {
        "competency_id": competency_id,
        "subject_key": subject_key,
        "subject_display_name": subject_display_name,
        "subject_full_name": subject_full_name,
        "official_subject_name": official_subject_name,
        "school_context_name": school_context_name,
        "grade_band": grade_band,
        "learning_stage": learning_stage,
        "learning_area": learning_area,
        "competency_group": competency_group,
        "competency_text": competency_text,
        "competency_label": competency_label,
        "source_reference": source_reference,
        "catalog_status": catalog_status,
        "catalog_default_active": catalog_default_active,
        "activation_group_key": activation_group_key,
        "is_core_subject": is_core_subject,
        "is_active": is_active,
    }
