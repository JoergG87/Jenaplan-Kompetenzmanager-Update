from pathlib import Path
import sqlite3
import pytest
from prototypes.ipad.main import DemoRepository


def test_reopen_and_invalid_save_preserves_state(tmp_path: Path):
    path = tmp_path / 'demo.sqlite'
    selected = {0: '--', 1: '+', 2: '++'}
    DemoRepository(path).save(selected)
    reopened = DemoRepository(path)
    assert reopened.read() == selected
    with pytest.raises(ValueError):
        reopened.save({0: '+'})
    assert reopened.read() == selected


def test_foreign_database_and_symlink_untouched(tmp_path: Path):
    path = tmp_path / 'foreign.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE sentinel (value TEXT)')
    before = path.read_bytes()
    with pytest.raises(ValueError):
        DemoRepository(path)
    assert path.read_bytes() == before
    link = tmp_path / 'link.sqlite'
    link.symlink_to(path)
    with pytest.raises(ValueError):
        DemoRepository(link)
    assert path.read_bytes() == before


def test_synthetic_window_saves_and_reopens(tmp_path: Path):
    from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
    from prototypes.ipad.main import build_window
    app = QApplication.instance() or QApplication([])
    repository = DemoRepository(tmp_path / 'demo.sqlite')
    window = build_window(repository)
    choices = window.findChildren(QComboBox)
    assert len(choices) == 3
    for choice, token in zip(choices, ('--', '+', '++')):
        choice.setCurrentIndex(choice.findData(token))
    window.findChild(QPushButton).click()
    window.close()
    reopened = build_window(DemoRepository(repository.path))
    assert [choice.currentData() for choice in reopened.findChildren(QComboBox)] == ['--', '+', '++']
    reopened.close()
