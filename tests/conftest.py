"""Test-only compatibility for explicitly synthetic pre-V3 fixtures."""

from __future__ import annotations

import pytest

import src.application.school_year_assignment as assignment_application
import src.core.sqlite_store as sqlite_store
from tests.helpers.synthetic_legacy_membership import (
    SyntheticLegacyAssignmentReadSession,
    SyntheticLegacyStudentRepository,
)


@pytest.fixture(autouse=True)
def synthetic_legacy_membership_readers(monkeypatch: pytest.MonkeyPatch):
    """Keep old synthetic writer fixtures isolated from product V3 readers."""

    monkeypatch.setattr(
        sqlite_store,
        "SchoolYearAssignmentReadSession",
        SyntheticLegacyAssignmentReadSession,
    )
    monkeypatch.setattr(
        sqlite_store,
        "V3StudentRepository",
        SyntheticLegacyStudentRepository,
    )
    monkeypatch.setattr(
        assignment_application,
        "SchoolYearAssignmentReadSession",
        SyntheticLegacyAssignmentReadSession,
    )
