"""Exclusive synthetic Tablet runtime, independent of desktop startup and keys."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

from src.core.database_compatibility import DatabaseCompatibilityInspector, DatabaseCompatibilityStatus
from src.core.sqlite_store import SQLiteDatabase

BUNDLE_ID = 'de.jenaplan.kompetenzmanager.ipad-app-test'
MARKER = 'tablet-test.json'


def _inspect(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Tablet-Testdaten fehlen oder sind unsicher.')
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
        result = DatabaseCompatibilityInspector().inspect_connection(connection)
        if result.status is not DatabaseCompatibilityStatus.EXACT:
            raise ValueError('Tablet-Testdaten haben ein unbekanntes Schema.')
        if connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Tablet-Testdaten sind beschädigt.')
        if connection.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Tablet-Testdaten sind unvollständig.')


class TabletRuntime:
    """Owns only a separate, explicitly synthetic app-container database."""
    def __init__(self, root: Path, template: Path, template_sha256: str):
        root, template = Path(root), Path(template)
        if not root.is_absolute() or any(p.is_symlink() for p in (root, *root.parents)):
            raise ValueError('Unsicherer Tablet-Datenordner.')
        self.root = root
        self.database_path = root / 'kompetenzmanager.sqlite'
        identity = {'format': 2, 'bundle_id': BUNDLE_ID, 'synthetic_only': True,
                    'root_role': 'synthetic-tablet-app'}
        if root.exists() and any(root.iterdir()):
            marker = root / MARKER
            if marker.is_symlink() or not marker.is_file() or json.loads(marker.read_text()) != identity:
                raise ValueError('Fremder oder unvollständiger Tablet-Testbestand.')
            _inspect(self.database_path)
        else:
            if template.is_symlink() or not template.is_file():
                raise ValueError('Tablet-Startvorlage fehlt.')
            if hashlib.sha256(template.read_bytes()).hexdigest() != template_sha256:
                raise ValueError('Tablet-Startvorlage wurde verändert.')
            _inspect(template)
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            stage = root / 'initializing.sqlite'
            with template.open('rb') as source, stage.open('xb') as target:
                shutil.copyfileobj(source, target)
                target.flush(); os.fsync(target.fileno())
            stage.chmod(0o600)
            _inspect(stage)
            documents = template.parent / 'documents'
            if documents.is_dir() and not documents.is_symlink():
                if any(p.is_symlink() for p in documents.rglob('*')):
                    raise ValueError('Unsichere synthetische Beispieldateien.')
                shutil.copytree(documents, root / 'documents')
            os.replace(stage, self.database_path)
            with (root / MARKER).open('x') as marker:
                json.dump(identity, marker, sort_keys=True)
                marker.flush(); os.fsync(marker.fileno())
        self.database = SQLiteDatabase(self.database_path, create=False)
        self.database.initialize_schema()


def tablet_data_root():
    from PySide6.QtCore import QStandardPaths
    value = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    if not value:
        raise ValueError('Kein eigener iPad-App-Container verfügbar.')
    return Path(value).resolve() / 'synthetic-tablet-app'
