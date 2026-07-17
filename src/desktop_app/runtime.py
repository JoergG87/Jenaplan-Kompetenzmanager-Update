"""Runtime paths and first-start preparation for development and packaged apps."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Mapping


APP_NAME = "Jenaplan-Kompetenzmanager"
APP_BUNDLE_ID = "de.jenaplan.kompetenzmanager"
APP_DATA_DIR_ENV = "JENAPLAN_APP_DATA_DIR"
DATABASE_FILENAME = "kompetenzmanager.sqlite"
SECURITY_DIRECTORY = "security"
SECURITY_DATABASE_FILENAME = "security.sqlite"
ENROLLMENT_MARKER_FILENAME = "enrollment.marker"
BUILD_INFO_FILENAME = "pilot_build_info.json"
INITIAL_DATA_DIRECTORY = "pilot_initial"
INITIAL_PATH_TOKEN = "__PILOT_DATA_ROOT__"
DEVELOPMENT_DATA_ROOT = Path("data")


class RuntimeStorageError(RuntimeError):
    """Raised when the application cannot safely prepare its local storage."""


@dataclass(frozen=True)
class RuntimePaths:
    """All mutable directories owned by one local application installation."""

    root: Path
    database: Path
    documents: Path
    exports: Path
    backups: Path
    logs: Path

    @property
    def security(self) -> Path:
        """Return the isolated security root without creating it."""
        return self.root / SECURITY_DIRECTORY

    @property
    def security_database(self) -> Path:
        """Return the canonical local security-store path."""
        return self.security / SECURITY_DATABASE_FILENAME

    @property
    def enrollment_marker(self) -> Path:
        """Return the canonical non-secret enrollment-marker path."""
        return self.security / ENROLLMENT_MARKER_FILENAME


def is_packaged_app() -> bool:
    """Return whether Python is running from a frozen application bundle."""
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """Return the immutable resource root in source and frozen executions."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str | os.PathLike[str]) -> Path:
    """Resolve one immutable application resource."""
    return resource_root().joinpath(*parts)


def application_data_root(
    *,
    packaged: bool | None = None,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Return the mutable data root without creating it."""
    environment = os.environ if environ is None else environ
    override = environment.get(APP_DATA_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    packaged = is_packaged_app() if packaged is None else packaged
    if not packaged:
        return DEVELOPMENT_DATA_ROOT
    home = Path.home() if home is None else Path(home)
    return home / "Library" / "Application Support" / APP_NAME


def runtime_paths(data_root: Path | None = None) -> RuntimePaths:
    """Build the complete runtime path projection for one data root."""
    root = application_data_root() if data_root is None else Path(data_root)
    return RuntimePaths(
        root=root,
        database=root / DATABASE_FILENAME,
        documents=root / "documents",
        exports=root / "exports",
        backups=root / "backups",
        logs=root / "logs",
    )


def default_database_path() -> Path:
    """Keep the developer database while routing packaged runs to user data."""
    return runtime_paths().database


def prepare_runtime_storage(
    *,
    data_root: Path | None = None,
    resource_root_path: Path | None = None,
) -> RuntimePaths:
    """Create mutable directories and install optional initial data exactly once."""
    paths = runtime_paths(data_root)
    resources = resource_root() if resource_root_path is None else Path(resource_root_path)
    try:
        paths.root.mkdir(parents=True, exist_ok=True)
        _assert_directory(paths.root)
        initial_database = resources / INITIAL_DATA_DIRECTORY / DATABASE_FILENAME
        if not paths.database.exists() and initial_database.is_file():
            _install_initial_data(paths, initial_database)
        for directory in (
            paths.documents,
            paths.exports,
            paths.backups,
            paths.logs,
        ):
            directory.mkdir(parents=True, exist_ok=True)
            _assert_directory(directory)
        _verify_writable(paths.root)
    except RuntimeStorageError:
        raise
    except (OSError, sqlite3.Error) as error:
        raise RuntimeStorageError(
            f"Der lokale Datenordner konnte nicht vorbereitet werden: {paths.root}"
        ) from error
    return paths


def _install_initial_data(paths: RuntimePaths, initial_database: Path) -> None:
    """Copy an explicitly packaged initial database without replacing user data."""
    initial_documents = initial_database.parent / "documents"
    if paths.database.exists():
        return
    if initial_documents.is_dir() and paths.documents.exists() and any(
        paths.documents.iterdir()
    ):
        raise RuntimeStorageError(
            "Die Startdaten wurden nicht eingerichtet, weil bereits lokale "
            f"Dokumente vorhanden sind: {paths.documents}"
        )

    with tempfile.TemporaryDirectory(prefix="pilot-first-start-", dir=paths.root) as temp:
        staged_database = Path(temp) / DATABASE_FILENAME
        shutil.copy2(initial_database, staged_database)
        _rebase_initial_document_paths(staged_database, paths.root)
        if initial_documents.is_dir():
            paths.documents.mkdir(parents=True, exist_ok=True)
            for source in initial_documents.rglob("*"):
                relative = source.relative_to(initial_documents)
                target = paths.documents / relative
                if source.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if target.exists():
                    raise RuntimeStorageError(
                        "Eine vorhandene lokale Datei verhindert die sichere "
                        f"Einrichtung der Startdaten: {target}"
                    )
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        if paths.database.exists():
            raise RuntimeStorageError(
                "Die Benutzerdatenbank wurde während der Ersteinrichtung angelegt "
                "und deshalb nicht ersetzt."
            )
        staged_database.replace(paths.database)


def _rebase_initial_document_paths(database_path: Path, data_root: Path) -> None:
    """Materialize paths in a newly copied, explicitly fictional demo database."""
    with sqlite3.connect(database_path) as connection:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'documents'"
        ).fetchone()
        if table is None:
            return
        rows = connection.execute(
            "SELECT document_id, file_path FROM documents"
        ).fetchall()
        for document_id, file_path in rows:
            prefix = f"{INITIAL_PATH_TOKEN}/"
            if not isinstance(file_path, str) or not file_path.startswith(prefix):
                continue
            relative = Path(file_path[len(prefix) :])
            connection.execute(
                "UPDATE documents SET file_path = ? WHERE document_id = ?",
                (str(data_root / relative), document_id),
            )
        connection.commit()


def _assert_directory(path: Path) -> None:
    if not path.is_dir():
        raise RuntimeStorageError(f"Der benötigte Pfad ist kein Ordner: {path}")


def _verify_writable(path: Path) -> None:
    try:
        descriptor, probe_name = tempfile.mkstemp(prefix=".write-check-", dir=path)
        os.close(descriptor)
        Path(probe_name).unlink()
    except OSError as error:
        raise RuntimeStorageError(
            f"Der lokale Datenordner ist nicht beschreibbar: {path}"
        ) from error


def configure_runtime_logging(paths: RuntimePaths) -> Path:
    """Configure a small rotating technical log outside the app bundle."""
    log_path = paths.logs / "kompetenzmanager.log"
    handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if not any(
        isinstance(existing, RotatingFileHandler)
        and Path(existing.baseFilename) == log_path.resolve()
        for existing in root_logger.handlers
    ):
        root_logger.addHandler(handler)
    logging.getLogger(__name__).info("App-Datenpfad: %s", paths.root)
    return log_path


def load_build_info() -> dict[str, object]:
    """Read non-secret package metadata embedded by the build process."""
    path = resource_path(BUILD_INFO_FILENAME)
    if not path.is_file():
        return {"data_mode": "development", "packaged": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"data_mode": "unknown", "packaged": True}
    return payload if isinstance(payload, dict) else {"data_mode": "unknown"}
