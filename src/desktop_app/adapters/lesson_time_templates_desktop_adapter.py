"""Explicit exact synthetic V5/V6 capability adapter; never composed by product startup."""
from src.core.maintenance_gate import product_writer
from src.core.lesson_time_templates import LessonTimeTemplate
from src.desktop_app.view_models.lesson_time_templates_view_model import (
    LessonTimeTemplateOptionViewModel, LessonTimeTemplatesViewModel,
)


class LessonTimeTemplatesDesktopAdapter:
    def __init__(self, runtime) -> None:
        from src.security.synthetic_v5_runtime import OpenedSyntheticV5Runtime
        from src.security.synthetic_v6_runtime import OpenedSyntheticV6Runtime
        if type(runtime) not in (OpenedSyntheticV5Runtime, OpenedSyntheticV6Runtime):
            raise ValueError("synthetic_v5_runtime_required")
        self.database = runtime.database
        self.service = runtime.lesson_time_templates

    def view_model(self) -> LessonTimeTemplatesViewModel:
        return LessonTimeTemplatesViewModel(tuple(
            LessonTimeTemplateOptionViewModel(value)
            for value in self.service.repository.list_templates()))

    @product_writer
    def save_template(self, lesson_number: int, start_time: str, end_time: str,
                      expected: LessonTimeTemplate | None) -> None:
        self.service.set_times_if_unchanged(lesson_number, start_time, end_time,
                                          expected=expected)
