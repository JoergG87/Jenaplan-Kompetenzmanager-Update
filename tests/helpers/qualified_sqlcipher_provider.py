"""Load the real audited 4.17 extension without replacing the stock test driver.

No fake driver/version and no skip: hash or native-loader failures are errors.
The existing provider ports receive the actual extension and wheel metadata.
"""
from __future__ import annotations
import atexit
from email.parser import BytesParser
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import zipfile

from src.core.database_engine import (SQLCipherConnectionProvider,
    SQLCIPHER_4_17_BINDING_VERSION, SQLCIPHER_4_17_ENGINE_VERSION)

_CACHE = None
_WHEEL_ROOT = Path(__file__).resolve().parents[2] / "build/macos-inputs/sqlcipher-4.17-sdk27"
_WHEEL_NAME = "sqlcipher3-0.6.2+jkm.sqlcipher4170.1-cp314-cp314-macosx_11_0_arm64.whl"


def _verified_wheel():
    wheel = _WHEEL_ROOT / _WHEEL_NAME
    audit = json.loads((_WHEEL_ROOT / "audit-report.json").read_text())
    raw = wheel.read_bytes()
    if (audit.get("status") != "GO" or audit["wheel"]["name"] != wheel.name
            or hashlib.sha256(raw).hexdigest() != audit["wheel"]["sha256"]):
        raise RuntimeError("qualified_sqlcipher_wheel_not_verified")
    return wheel


def _actual_binding_version():
    with zipfile.ZipFile(_verified_wheel()) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith('.dist-info/METADATA'))
        metadata = BytesParser().parsebytes(archive.read(metadata_name))
        if metadata['Name'] != 'sqlcipher3':
            raise RuntimeError('qualified_sqlcipher_metadata_invalid')
        return metadata['Version']


def _actual_native_extension():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    with zipfile.ZipFile(_verified_wheel()) as archive:
        name = next(name for name in archive.namelist() if name.startswith('sqlcipher3/') and name.endswith('.so'))
        raw = archive.read(name)
    temporary = tempfile.TemporaryDirectory(prefix='jkm-qualified-sqlcipher-tests-')
    atexit.register(temporary.cleanup)
    path = Path(temporary.name) / Path(name).name
    path.write_bytes(raw); path.chmod(0o600)
    if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(raw).digest():
        raise RuntimeError('qualified_sqlcipher_extension_changed')
    module_name = '_jkm_qualified_sqlcipher_test._sqlite3'
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError('qualified_sqlcipher_loader_missing')
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    _CACHE = module
    return module


def qualified_sqlcipher_test_provider():
    if _actual_binding_version() != SQLCIPHER_4_17_BINDING_VERSION:
        raise RuntimeError('qualified_sqlcipher_binding_incompatible')
    return SQLCipherConnectionProvider(
        expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
        expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
        driver_loader=_actual_native_extension,
        binding_version_loader=_actual_binding_version,
    )
