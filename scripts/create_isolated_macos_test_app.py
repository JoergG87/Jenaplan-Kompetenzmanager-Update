"""Create a local test copy whose normal LaunchServices entry cannot use product data."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.runtime_root_protection import (
    RuntimeRootKind,
    inspect_runtime_root,
    prepare_synthetic_test_root,
)

APP_ID = "de.jenaplan.kompetenzmanager"
TEST_APP_NAME = "Jenaplan-Isolierter-Test.app"
LAUNCHER_NAME = "jkm-isolated-launcher"
SMOKE_MODES = frozenset({"initialize", "restart", "cleanup", "restore-worker"})


def test_environment(root: Path, arguments: list[str]) -> dict[str, str]:
    """Validate the fixed root and an argument allowlist before product code runs."""
    if arguments and not (
        len(arguments) == 2
        and arguments[0] == "--packaged-smoke-test"
        and arguments[1] in SMOKE_MODES
    ):
        raise ValueError("isolated_test_arguments_rejected")
    temporary = Path(tempfile.gettempdir()).resolve()
    root = Path(root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValueError("isolated_test_root_missing")
    resolved = root.resolve(strict=True)
    if root != resolved:
        raise ValueError("isolated_test_root_moved")
    relative = resolved.relative_to(temporary)
    if len(relative.parts) != 2 or not relative.parts[0].startswith(
        "jenaplan-packaged-smoke-isolated-"
    ) or relative.parts[1] != "data":
        raise ValueError("isolated_test_root_outside_container")
    for path in (root.parent, root):
        metadata = path.stat()
        if metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            raise ValueError("isolated_test_root_permissions")
    protection = inspect_runtime_root(root)
    if protection is None or protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
        raise ValueError("isolated_test_root_authority_rejected")
    # Never follow data-root links, including lock/log/security files created
    # after first start. Reject hardlinks and special files before product code.
    def reject_scan_error(error: OSError) -> None:
        raise ValueError("isolated_test_root_scan_failed") from error

    for directory, folders, files in os.walk(root, followlinks=False, onerror=reject_scan_error):
        for name in (*folders, *files):
            path = Path(directory) / name
            metadata = path.lstat()
            if (stat.S_ISLNK(metadata.st_mode)
                or not (stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode))
                or metadata.st_uid != os.getuid()
                or (stat.S_ISREG(metadata.st_mode) and metadata.st_nlink != 1)):
                raise ValueError("isolated_test_root_entry_rejected")
    # Only OS session values are inherited. In particular no bridge, dynamic
    # loader, Python, Qt-plugin, alternate runtime or developer overrides.
    environment = {
        name: value for name, value in os.environ.items()
        if name in {"HOME", "USER", "LOGNAME", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE"}
    }
    environment["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    environment.update(
        JENAPLAN_APP_DATA_DIR=str(root),
        JENAPLAN_PACKAGED_SMOKE_MARKER="isolated-v1",
        QT_QPA_PLATFORM="cocoa",
    )
    return environment


def launch_test_runtime(root: Path, executable: Path, arguments: list[str]) -> None:
    environment = test_environment(root, arguments)
    if executable.is_symlink() or not executable.is_file():
        raise ValueError("isolated_test_executable_missing")
    os.execve(str(executable), [str(executable), *arguments], environment)


def create_test_app(source_app: Path) -> dict[str, str]:
    if sys.platform != "darwin":
        raise ValueError("isolated_test_requires_macos")
    source_app = Path(source_app).resolve(strict=True)
    if source_app.suffix != ".app":
        raise ValueError("isolated_test_source_not_app")
    info = plistlib.loads((source_app / "Contents/Info.plist").read_bytes())
    executable_name = info.get("CFBundleExecutable", "")
    if info.get("CFBundleIdentifier") != APP_ID or (
        not executable_name or Path(executable_name).name != executable_name
    ):
        raise ValueError("isolated_test_source_identity_rejected")
    source_executable = source_app / "Contents/MacOS" / executable_name
    if source_executable.is_symlink() or not source_executable.is_file():
        raise ValueError("isolated_test_source_executable_missing")
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(source_app)], check=True)
    container = Path(tempfile.mkdtemp(prefix="jenaplan-packaged-smoke-isolated-")).resolve()
    root = container / "data"
    prepare_synthetic_test_root(root)
    test_environment(root, [])
    app = container / TEST_APP_NAME
    subprocess.run(["ditto", str(source_app), str(app)], check=True)
    executable = app / "Contents/MacOS" / executable_name
    bootstrap = app / "Contents/Resources/isolated-test-bootstrap.py"
    # Keep the guard in the sealed test copy; later checkout changes must not
    # change the launch boundary of an existing test artifact.
    support_root = bootstrap.parent
    shutil.copy2(__file__, support_root / "isolated_test_support.py")
    core = support_root / "src/core"
    core.mkdir(parents=True, exist_ok=True)
    (core.parent / "__init__.py").write_text("")
    (core / "__init__.py").write_text("")
    shutil.copy2(ROOT / "src/core/runtime_root_protection.py", core / "runtime_root_protection.py")
    bootstrap.write_text(
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parent))\n"
        "from isolated_test_support import launch_test_runtime\n"
        "try:\n"
        f"    launch_test_runtime(Path({str(root)!r}), Path({str(executable)!r}), sys.argv[1:])\n"
        "except Exception:\n"
        "    print('Isolierter Teststart gesperrt.', file=sys.stderr)\n"
        "    raise SystemExit(2)\n",
        encoding="utf-8",
    )
    # A native main executable preserves a distinct, signable LaunchServices entry.
    launcher_source = container / "launcher.c"
    launcher_source.write_text(
        "#include <stdlib.h>\n#include <unistd.h>\n"
        "int main(int argc, char **argv) {\n"
        " char **args = calloc((size_t)argc + 4, sizeof(char *));\n"
        " if (!args) return 2;\n"
        f" args[0] = {json.dumps(sys.executable)};\n"
        ' args[1] = "-I";\n'
        ' args[2] = "-B";\n'
        f" args[3] = {json.dumps(str(bootstrap))};\n"
        " for (int i=1; i<argc; ++i) args[i+3] = argv[i];\n"
        " execv(args[0], args);\n free(args);\n return 2;\n}\n",
        encoding="utf-8",
    )
    launcher = app / "Contents/MacOS" / LAUNCHER_NAME
    subprocess.run(
        ["xcrun", "clang", "-arch", "arm64", "-mmacosx-version-min=13.0",
         str(launcher_source), "-o", str(launcher)], check=True,
    )
    info.update(
        CFBundleExecutable=LAUNCHER_NAME,
        CFBundleIdentifier=f"{APP_ID}.isolatedtest.{uuid.uuid4().hex}",
        CFBundleName="Jenaplan-Isolierter-Test",
        CFBundleDisplayName="Jenaplan – Isolierter Test",
    )
    # A copied bundle must not register product document handlers or updater actions.
    for name in tuple(info):
        if name.startswith("SU") or name in {"CFBundleDocumentTypes", "CFBundleURLTypes", "LSEnvironment"}:
            info.pop(name)
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    return {"app": str(app), "root": str(root), "launcher": str(launcher),
            "bundle_id": info["CFBundleIdentifier"], "release_qualification": "not_applicable"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_app", type=Path)
    print(json.dumps(create_test_app(parser.parse_args().source_app), indent=2))
