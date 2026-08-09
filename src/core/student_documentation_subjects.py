"""Domain records for school-year-specific documentation subjects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DocumentationSubjectMode(StrEnum):
    """Whether one student/year inherits or owns an exact subject set."""

    INHERIT = "inherit"
    CUSTOM = "custom"


class DocumentationSubjectWriteStatus(StrEnum):
    """Observable result without exposing persistence implementation details."""

    CHANGED = "changed"
    NO_CHANGE = "no_change"


@dataclass(frozen=True, slots=True)
class StudentDocumentationSubjectProfile:
    student_id: str
    school_year_id: str
    mode: DocumentationSubjectMode
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StudentDocumentationSubjectConfiguration:
    """Stored configuration; a missing profile is projected as inherit."""

    student_id: str
    school_year_id: str
    mode: DocumentationSubjectMode
    selected_subject_ids: tuple[str, ...]
    profile: StudentDocumentationSubjectProfile | None


@dataclass(frozen=True, slots=True)
class DocumentationSubjectWriteResult:
    status: DocumentationSubjectWriteStatus
    configuration: StudentDocumentationSubjectConfiguration
