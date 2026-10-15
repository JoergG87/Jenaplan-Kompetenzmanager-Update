"""Global lesson times are defaults copied into a lesson, never live links."""
from dataclasses import dataclass
import re
from typing import Protocol


class LessonTimeTemplateError(ValueError):
    pass


@dataclass(frozen=True)
class LessonTimeTemplate:
    lesson_number: int
    start_time: str
    end_time: str

    def __post_init__(self):
        if type(self.lesson_number) is not int or self.lesson_number < 1:
            raise LessonTimeTemplateError("Die Unterrichtsstunde muss eine positive Zahl sein.")
        for value in (self.start_time, self.end_time):
            if not isinstance(value, str) or re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value) is None:
                raise LessonTimeTemplateError("Uhrzeit muss im Format HH:MM angegeben werden.")
        if self.start_time >= self.end_time:
            raise LessonTimeTemplateError("Beginn muss vor Ende liegen.")


class LessonTimeTemplateRepository(Protocol):
    def list_templates(self) -> tuple[LessonTimeTemplate, ...]: ...
    def save(self, template: LessonTimeTemplate) -> None: ...


class LessonTimeTemplateService:
    def __init__(self, repository: LessonTimeTemplateRepository):
        self.repository = repository

    def set_times(self, lesson_number: int, start_time: str, end_time: str) -> None:
        self.repository.save(LessonTimeTemplate(lesson_number, start_time, end_time))

    def suggest(self, lesson_number: int, *, start_time: str | None = None,
                end_time: str | None = None) -> LessonTimeTemplate:
        if type(lesson_number) is not int or lesson_number < 1:
            raise LessonTimeTemplateError("Die Unterrichtsstunde muss eine positive Zahl sein.")
        if (start_time is None) != (end_time is None):
            raise LessonTimeTemplateError("Individuelle Zeiten benötigen Beginn und Ende.")
        if start_time is not None:
            return LessonTimeTemplate(lesson_number, start_time, end_time)
        for template in self.repository.list_templates():
            if template.lesson_number == lesson_number:
                return template
        raise LessonTimeTemplateError("Für diese Unterrichtsstunde ist keine Zeit hinterlegt.")
