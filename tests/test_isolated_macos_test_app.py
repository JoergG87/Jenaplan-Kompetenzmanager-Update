from pathlib import Path
import os
import tempfile
from unittest.mock import patch

import pytest

from scripts.create_isolated_macos_test_app import launch_test_runtime, test_environment as environment_for_test
from src.core.runtime_root_protection import prepare_synthetic_test_root, publish_pilot_product_root


@pytest.fixture
def isolated_root():
    with tempfile.TemporaryDirectory(prefix="jenaplan-packaged-smoke-isolated-") as parent:
        root = Path(parent).resolve() / "data"
        prepare_synthetic_test_root(root)
        yield root


def test_normal_relaunch_uses_bound_root_despite_missing_or_foreign_environment(isolated_root):
    with patch.dict(os.environ, {"JENAPLAN_APP_DATA_DIR": "/foreign/product"}, clear=True):
        result = environment_for_test(isolated_root, [])
    assert result["JENAPLAN_APP_DATA_DIR"] == str(isolated_root)
    assert result["JENAPLAN_PACKAGED_SMOKE_MARKER"] == "isolated-v1"


@pytest.mark.parametrize("arguments", [
    ["--runtime-root", "/foreign"], ["--packaged-cipher-seed", "/foreign"],
    ["--restore-worker"], ["--packaged-smoke-test", "unknown"],
    ["--packaged-smoke-test", "initialize", "--runtime-root", "/foreign"],
])
def test_path_and_unrecognized_arguments_never_reach_product_runtime(isolated_root, arguments):
    with patch("os.execve") as execute:
        with pytest.raises(ValueError):
            launch_test_runtime(isolated_root, Path(__file__), arguments)
        execute.assert_not_called()


@pytest.mark.parametrize("damage", ["missing", "marker_missing", "marker_corrupt", "product", "symlink", "permissions"])
def test_damaged_root_never_reaches_product_runtime(isolated_root, damage):
    marker = isolated_root / ".jkm-runtime-root-v1"
    root = isolated_root
    if damage == "missing":
        root = isolated_root.parent / "absent"
    elif damage == "marker_missing":
        marker.unlink()
    elif damage == "marker_corrupt":
        marker.write_text("{}")
    elif damage == "product":
        marker.unlink()
        publish_pilot_product_root(root)
    elif damage == "symlink":
        root = isolated_root.parent / "link"
        root.symlink_to(isolated_root, target_is_directory=True)
    elif damage == "permissions":
        root.chmod(0o755)
    with patch("os.execve") as execute:
        with pytest.raises((ValueError, RuntimeError)):
            launch_test_runtime(root, Path(__file__), [])
        execute.assert_not_called()


@pytest.mark.parametrize("mode", ["initialize", "restart", "cleanup", "restore-worker"])
def test_supported_smoke_modes_keep_the_bound_root(isolated_root, mode):
    result = environment_for_test(isolated_root, ["--packaged-smoke-test", mode])
    assert result["JENAPLAN_APP_DATA_DIR"] == str(isolated_root)


@pytest.mark.parametrize("entry", ["instance.lock", "logs", "security", "nested/item"])
def test_internal_symlinks_never_reach_runtime(isolated_root, entry):
    path=isolated_root/entry
    path.parent.mkdir(exist_ok=True)
    path.symlink_to(isolated_root.parent/'foreign')
    with patch('os.execve') as execute:
        with pytest.raises(ValueError):launch_test_runtime(isolated_root,Path(__file__),[])
        execute.assert_not_called()


def test_hardlinked_data_file_is_rejected(isolated_root):
    other=isolated_root.parent/'other';other.write_text('untouched')
    os.link(other,isolated_root/'instance.lock')
    with pytest.raises(ValueError):environment_for_test(isolated_root,[])
    assert other.read_text()=='untouched'


def test_external_runtime_loader_and_plugin_overrides_are_not_inherited(isolated_root):
    overrides={'JKM_MACOS_SECURITY_BRIDGE':'/foreign/bridge','DYLD_INSERT_LIBRARIES':'/foreign/lib',
               'PYTHONPATH':'/foreign','QT_PLUGIN_PATH':'/foreign','JENAPLAN_RESTART_ROOT':'/foreign'}
    with patch.dict(os.environ,overrides):env=environment_for_test(isolated_root,[])
    for key in overrides:assert key not in env


def test_launcher_disables_bytecode_in_sealed_bundle():
    source=Path('scripts/create_isolated_macos_test_app.py').read_text()
    assert 'args[2] = "-B"' in source
