from dataclasses import FrozenInstanceError

import pytest

from src.core.lesson_time_templates import LessonTimeTemplate, LessonTimeTemplateError, LessonTimeTemplateService


@pytest.mark.parametrize('number,start,end', [
    (0,'08:00','08:45'), (-1,'08:00','08:45'), (True,'08:00','08:45'),
    (1.5,'08:00','08:45'), (1,'8:00','08:45'), (1,'24:00','24:10'),
    (1,'08:60','09:45'), (1,'08:45','08:45'), (1,'09:00','08:45'),
    (1,'08:00:00','08:45'), (1,None,'08:45')])
def test_invalid_lesson_times_are_rejected(number,start,end):
    with pytest.raises(LessonTimeTemplateError): LessonTimeTemplate(number,start,end)


def test_suggestion_is_immutable_and_individual_times_need_both_values():
    class Repository:
        values = (LessonTimeTemplate(1,'08:00','08:45'),)
        def list_templates(self): return self.values
        def save(self, template): self.values = (template,)
    repo = Repository(); service = LessonTimeTemplateService(repo)
    copied = service.suggest(1)
    service.set_times(1,'08:05','08:50')
    assert copied == LessonTimeTemplate(1,'08:00','08:45')
    assert service.suggest(1) == LessonTimeTemplate(1,'08:05','08:50')
    assert service.suggest(2,start_time='10:00',end_time='10:45').lesson_number == 2
    with pytest.raises(FrozenInstanceError): copied.start_time = '08:30'
    with pytest.raises(LessonTimeTemplateError): service.suggest(2)
    with pytest.raises(LessonTimeTemplateError): service.suggest(1,start_time='08:10')
    with pytest.raises(LessonTimeTemplateError): service.suggest(1,end_time='09:00')
