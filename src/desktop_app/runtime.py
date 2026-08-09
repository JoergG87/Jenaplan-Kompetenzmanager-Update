"""Runtime paths and first-start preparation for development and packaged apps."""

from __future__ import annotations

import json
import logging
import os
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
APP_PREFERENCES_FILENAME = "app-preferences.json"
BUILD_INFO_FILENAME = "pilot_build_info.json"
# Retained only as historical packaging metadata. Runtime startup no longer
# installs a packaged predecessor database.
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

    @property
    def app_preferences(self) -> Path:
        """Return the general local app-preferences path outside Security."""
        return self.root / APP_PREFERENCES_FILENAME

    @property
    def key_runtime_metadata(self) -> Path:
        """Return the non-secret DMK/Database-Key metadata directory."""
        from src.security.database_key_runtime import (
            DMK_DATABASE_KEY_RUNTIME_METADATA_DIRECTORY,
        )

        return self.root / DMK_DATABASE_KEY_RUNTIME_METADATA_DIRECTORY

    @property
    def keyset_metadata(self) -> Path:
        """Return the non-secret keyset metadata database path."""
        from src.security.database_key_runtime import (
            DMK_DATABASE_KEY_RUNTIME_KEYSET_FILENAME,
        )

        return self.key_runtime_metadata / DMK_DATABASE_KEY_RUNTIME_KEYSET_FILENAME

    @property
    def database_key_envelope_registry(self) -> Path:
        """Return the authenticated Database-Key envelope registry path."""
        from src.security.infrastructure.database_key_envelope_repository import (
            DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME,
        )

        return self.key_runtime_metadata / DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME

    @property
    def final_v4_runtime(self) -> Path:
        """Return the productive encrypted Final-V4 runtime directory."""
        from src.security.final_v4_sqlcipher_runtime import (
            FINAL_V4_SQLCIPHER_RUNTIME_DIRECTORY,
        )

        return self.root / FINAL_V4_SQLCIPHER_RUNTIME_DIRECTORY

    @property
    def final_v4_database(self) -> Path:
        """Return the productive Final-V4 SQLCipher database path."""
        from src.security.final_v4_sqlcipher_runtime import (
            FINAL_V4_SQLCIPHER_DATABASE_FILENAME,
        )

        return self.final_v4_runtime / FINAL_V4_SQLCIPHER_DATABASE_FILENAME

    @property
    def document_companion_database(self) -> Path:
        """Return the keyed managed-document companion database path."""
        from src.security.final_v3_document_runtime import (
            FINAL_V3_DOCUMENT_DATABASE_FILENAME,
        )

        return self.final_v4_runtime / FINAL_V3_DOCUMENT_DATABASE_FILENAME

    @property
    def encrypted_document_storage(self) -> Path:
        """Return the managed encrypted document-container storage path."""
        from src.security.final_v3_document_runtime import (
            FINAL_V3_DOCUMENT_CONTAINER_DIRECTORY,
        )

        return self.final_v4_runtime / FINAL_V3_DOCUMENT_CONTAINER_DIRECTORY


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
    """Create mutable directories without installing a predecessor database."""
    paths = runtime_paths(data_root)
    del resource_root_path
    try:
        paths.root.mkdir(parents=True, exist_ok=True)
        _assert_directory(paths.root)
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
    except OSError as error:
        raise RuntimeStorageError(
            f"Der lokale Datenordner konnte nicht vorbereitet werden: {paths.root}"
        ) from error
    return paths


def prepare_cipher_runtime_storage(*, data_root: Path | None = None) -> RuntimePaths:
    """Prepare only non-secret product directories beside the Cipher runtime."""
    paths = runtime_paths(data_root)
    try:
        paths.root.mkdir(parents=True, exist_ok=True)
        _assert_directory(paths.root)
        for directory in (paths.exports, paths.backups, paths.logs):
            directory.mkdir(parents=True, exist_ok=True)
            _assert_directory(directory)
        _verify_writable(paths.root)
    except RuntimeStorageError:
        raise
    except OSError as error:
        raise RuntimeStorageError(
            f"Der lokale Datenordner konnte nicht vorbereitet werden: {paths.root}"
        ) from error
    return paths


def prepare_security_runtime_storage(*, data_root: Path | None = None) -> RuntimePaths:
    """Prepare only the technical root and isolated security directory."""
    paths = runtime_paths(data_root)
    try:
        paths.root.mkdir(parents=True, exist_ok=True)
        _assert_directory(paths.root)
        if paths.security.is_symlink():
            raise RuntimeStorageError("Der Security-Pfad darf kein Link sein.")
        paths.security.mkdir(parents=True, exist_ok=True, mode=0o700)
        _assert_directory(paths.security)
        if os.name == "posix":
            os.chmod(paths.security, 0o700)
        _verify_writable(paths.root)
    except RuntimeStorageError:
        raise
    except OSError as error:
        raise RuntimeStorageError(
            "Die technische Sicherheitsablage konnte nicht vorbereitet werden."
        ) from error
    return paths


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


class PreAuthSecurityLogBuffer(logging.Handler):
    """Keep data-minimized security event codes in memory until auth succeeds."""

    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.name == "jenaplan.security":
            self.records.append(record)


def begin_pre_auth_security_logging() -> PreAuthSecurityLogBuffer:
    handler = PreAuthSecurityLogBuffer()
    logger = logging.getLogger("jenaplan.security")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)
    return handler


def flush_pre_auth_security_logging(handler: PreAuthSecurityLogBuffer) -> None:
    logger = logging.getLogger("jenaplan.security")
    logger.removeHandler(handler)
    logger.propagate = True
    for record in handler.records:
        logger.log(record.levelno, record.getMessage())
    handler.records.clear()


def discard_pre_auth_security_logging(handler: PreAuthSecurityLogBuffer) -> None:
    logger = logging.getLogger("jenaplan.security")
    logger.removeHandler(handler)
    logger.propagate = True
    handler.records.clear()


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
