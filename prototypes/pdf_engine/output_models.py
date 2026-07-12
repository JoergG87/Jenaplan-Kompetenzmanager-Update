"""Neutral, immutable output models for the isolated PDF engine prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TypeAlias


@dataclass(frozen=True)
class DocumentMetadata:
    document_title: str
    student_name: str
    group_name: str
    period: str
    teacher_name: str
    school_name: str
    created_on: date
    header_text: str
    footer_text: str
    language: str = "de-DE"


@dataclass(frozen=True)
class HeadingBlock:
    text: str
    level: int = 1


@dataclass(frozen=True)
class ParagraphBlock:
    text: str
    emphasis: str = "body"


@dataclass(frozen=True)
class SpacerBlock:
    height_mm: float


@dataclass(frozen=True)
class KeyValueBlock:
    items: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class TableBlock:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    column_weights: tuple[float, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        column_count = len(self.headers)
        if not column_count:
            raise ValueError("A table needs at least one column.")
        if any(len(row) != column_count for row in self.rows):
            raise ValueError("Every table row must match the header width.")
        if self.column_weights and len(self.column_weights) != column_count:
            raise ValueError("Column weights must match the header width.")


@dataclass(frozen=True)
class ImagePlaceholderBlock:
    label: str
    width_mm: float = 34.0
    height_mm: float = 34.0


@dataclass(frozen=True)
class SignatureBlock:
    labels: tuple[str, ...]


@dataclass(frozen=True)
class DocumentationCoverageItem:
    label: str
    documented: int
    total: int

    def __post_init__(self) -> None:
        if self.total < 0 or self.documented < 0 or self.documented > self.total:
            raise ValueError("Coverage values must satisfy 0 <= documented <= total.")


@dataclass(frozen=True)
class DocumentationCoverageData:
    title: str
    items: tuple[DocumentationCoverageItem, ...]
    note: str


@dataclass(frozen=True)
class CompetencyTimelinePoint:
    recorded_on: date
    state_label: str


@dataclass(frozen=True)
class CompetencyTimelineSeries:
    label: str
    points: tuple[CompetencyTimelinePoint, ...]


@dataclass(frozen=True)
class CompetencyTimelineData:
    title: str
    period_start: date
    period_end: date
    series: tuple[CompetencyTimelineSeries, ...]
    state_colors: tuple[tuple[str, str], ...]
    note: str

    def __post_init__(self) -> None:
        if self.period_end <= self.period_start:
            raise ValueError("Timeline end must be after its start.")


@dataclass(frozen=True)
class ObservationTimelineEvent:
    observed_on: date
    context: str
    note: str


@dataclass(frozen=True)
class ObservationTimelineData:
    title: str
    period_start: date
    period_end: date
    events: tuple[ObservationTimelineEvent, ...]
    note: str

    def __post_init__(self) -> None:
        if self.period_end <= self.period_start:
            raise ValueError("Timeline end must be after its start.")


ChartData: TypeAlias = (
    DocumentationCoverageData | CompetencyTimelineData | ObservationTimelineData
)


@dataclass(frozen=True)
class ChartBlock:
    data: ChartData


OutputBlock: TypeAlias = (
    HeadingBlock
    | ParagraphBlock
    | SpacerBlock
    | KeyValueBlock
    | TableBlock
    | ImagePlaceholderBlock
    | SignatureBlock
    | ChartBlock
)


@dataclass(frozen=True)
class ReportPage:
    label: str
    blocks: tuple[OutputBlock, ...]
    is_cover: bool = False


@dataclass(frozen=True)
class ReportOutputModel:
    metadata: DocumentMetadata
    pages: tuple[ReportPage, ...]

    def __post_init__(self) -> None:
        if not self.pages:
            raise ValueError("A report needs at least one page.")
