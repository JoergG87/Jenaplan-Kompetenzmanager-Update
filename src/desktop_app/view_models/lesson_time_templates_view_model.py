"""Immutable projections of encrypted global teaching times."""
from dataclasses import dataclass
from src.core.lesson_time_templates import LessonTimeTemplate


@dataclass(frozen=True)
class LessonTimeTemplateOptionViewModel:
    template: LessonTimeTemplate

    @property
    def lesson_number(self) -> int:
        return self.template.lesson_number

    @property
    def start_time(self) -> str:
        return self.template.start_time

    @property
    def end_time(self) -> str:
        return self.template.end_time

    @property
    def label(self) -> str:
        return f"{self.lesson_number}. Stunde: {self.start_time}–{self.end_time}"


@dataclass(frozen=True)
class LessonTimeTemplatesViewModel:
    templates: tuple[LessonTimeTemplateOptionViewModel, ...]
