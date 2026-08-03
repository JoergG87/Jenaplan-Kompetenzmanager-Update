#!/usr/bin/env python3
"""Build the pinned SQLCipher 4.17.0/sqlcipher3 wheel in a fresh temp root."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "packaging/sqlcipher_4_17_macos_arm64_sources.json"
REQUIREMENTS_PATH = REPO_ROOT / "requirements-sqlcipher-4.17-build.txt"
NOTICE_PATH = REPO_ROOT / "packaging/THIRD_PARTY_NOTICES_SQLCIPHER_4_17_MACOS.md"
REPORT_NAME = "sqlcipher-4.17-macos-arm64-build-report.json"
SQLCIPHER_4_17_LOCAL_BINDING_VERSION = "0.6.2+jkm.sqlcipher4170.1"
SQLCIPHER_4_17_SOURCE_DATE_EPOCH = 1783468800


class BuildError(RuntimeError):
    pass


def sanitized_environment(base: dict[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if base is None else base)
    for key in tuple(environment):
        if key.startswith("PIP_") or key in {
            "PYTHONHOME",
            "PYTHONINSPECT",
            "PYTHONPATH",
            "PYTHONSTARTUP",
            "PYTHONUSERBASE",
        }:
            environment.pop(key, None)
    environment.update(
        {
            "PIP_CONFIG_FILE": "/dev/null",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INPUT": "1",
            "PYTHONNOUSERSITE": "1",
        }
    )
    return environment


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> str:
    print("$", " ".join(command), flush=True)
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env if env is not None else sanitized_environment(),
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    if result.returncode != 0:
        if capture and result.stdout:
            print(result.stdout, file=sys.stderr)
        raise BuildError(f"command_failed:{command[0]}:{result.returncode}")
    return (result.stdout or "").strip()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def create_build_root(requested: Path | None) -> Path:
    allowed = {
        Path(tempfile.gettempdir()).resolve(),
        Path("/private/tmp").resolve(),
        Path("/tmp").resolve(),
    }
    if requested is None:
        root = Path(tempfile.mkdtemp(prefix="jkm-sqlcipher-417-")).resolve()
    else:
        if not requested.is_absolute():
            raise BuildError("build_root_must_be_absolute")
        root = requested.resolve(strict=False)
        if requested.exists() or requested.is_symlink():
            raise BuildError("build_root_must_not_exist")
        if not any(_is_within(root, candidate) for candidate in allowed):
            raise BuildError("build_root_must_be_under_system_temp")
        root.mkdir(mode=0o700, parents=False)
    if root.is_symlink() or not root.is_dir():
        raise BuildError("build_root_invalid")
    root.chmod(0o700)
    return root


def load_manifest() -> dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("format") != 1:
        raise BuildError("source_manifest_format_unsupported")
    if (
        manifest["sources"]["binding"]["local_version"]
        != SQLCIPHER_4_17_LOCAL_BINDING_VERSION
        or manifest["build"]["source_date_epoch"]
        != SQLCIPHER_4_17_SOURCE_DATE_EPOCH
    ):
        raise BuildError("source_manifest_local_contract_mismatch")
    return manifest


def verify_toolchain(manifest: dict[str, object]) -> dict[str, str]:
    target = manifest["target"]
    assert isinstance(target, dict)
    actual = {
        "platform": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "macos_sdk": _run(["xcrun", "--show-sdk-version"], capture=True),
        "clang_identity": _run(["xcrun", "clang", "--version"], capture=True).splitlines()[0],
        "macos": platform.mac_ver()[0],
    }
    for key in ("platform", "machine", "python", "macos_sdk", "clang_identity"):
        if actual[key] != target[key]:
            raise BuildError(f"toolchain_mismatch:{key}:{actual[key]}")
    return actual


def _download(url: str, target: Path) -> None:
    temporary = target.with_suffix(target.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "jkm-sqlcipher-build/1"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            with temporary.open("xb") as output:
                shutil.copyfileobj(response, output)
                output.flush()
                os.fsync(output.fileno())
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def obtain_source(
    source: dict[str, str], *, downloads: Path, offline_cache: Path | None
) -> Path:
    target = downloads / source["archive"]
    if offline_cache is not None:
        cached = offline_cache / source["archive"]
        if cached.is_symlink() or not cached.is_file():
            raise BuildError(f"offline_source_missing:{source['archive']}")
        shutil.copyfile(cached, target)
    else:
        _download(source["url"], target)
    actual = sha256(target)
    if actual != source["sha256"]:
        raise BuildError(f"source_hash_mismatch:{source['archive']}:{actual}")
    return target


def safe_extract_tar(archive: Path, destination: Path, expected_root: str) -> Path:
    destination.mkdir(mode=0o700)
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        if not members:
            raise BuildError("source_archive_empty")
        for member in members:
            member_path = Path(member.name)
            if (
                member_path.is_absolute()
                or ".." in member_path.parts
                or not member_path.parts
                or member_path.parts[0] != expected_root
                or member.issym()
                or member.islnk()
                or member.isdev()
            ):
                raise BuildError(f"source_archive_member_rejected:{member.name}")
        bundle.extractall(destination, members=members, filter="data")
    root = destination / expected_root
    if root.is_symlink() or not root.is_dir():
        raise BuildError("source_archive_root_missing")
    return root


def create_build_venv(root: Path, *, offline_cache: Path | None) -> Path:
    venv_root = root / "build-venv"
    _run([sys.executable, "-m", "venv", "--copies", str(venv_root)])
    python = venv_root / "bin/python"
    command = [
        str(python),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--require-hashes",
        "-r",
        str(REQUIREMENTS_PATH),
    ]
    if offline_cache is not None:
        command[5:5] = ["--no-index", "--find-links", str(offline_cache)]
    pip_env = sanitized_environment()
    pip_env["PIP_CACHE_DIR"] = str(root / "pip-cache")
    _run(command, env=pip_env)
    versions = json.loads(
        _run(
            [
                str(python),
                "-c",
                (
                    "import json; from importlib import metadata; "
                    "print(json.dumps({n: metadata.version(n) for n in "
                    "('pip','setuptools','wheel','packaging')}))"
                ),
            ],
            capture=True,
        )
    )
    expected = {"pip": "26.1.2", "setuptools": "83.0.0", "wheel": "0.46.3", "packaging": "26.2"}
    if versions != expected:
        raise BuildError(f"build_tool_version_mismatch:{versions}")
    return python


def deterministic_environment(root: Path, manifest: dict[str, object]) -> dict[str, str]:
    target = manifest["target"]
    build = manifest["build"]
    assert isinstance(target, dict) and isinstance(build, dict)
    cflags = [str(item) for item in build["cflags"]]
    cflags.append(f"-ffile-prefix-map={root}=/usr/src/jkm-sqlcipher417")
    environment = sanitized_environment()
    environment.update(
        {
            "ARCHFLAGS": "-arch arm64",
            "CC": "/usr/bin/clang",
            "CFLAGS": " ".join(cflags),
            "LDFLAGS": " ".join(str(item) for item in build["ldflags"]),
            "LC_ALL": "C",
            "MACOSX_DEPLOYMENT_TARGET": str(target["macos_deployment_target"]),
            "PYTHONHASHSEED": "0",
            "SOURCE_DATE_EPOCH": str(build["source_date_epoch"]),
            "TZ": "UTC",
            "ZERO_AR_DATE": "1",
            "_PYTHON_HOST_PLATFORM": "macosx-11.0-arm64",
        }
    )
    return environment


def generate_amalgamation(
    sqlcipher_root: Path,
    build_root: Path,
    manifest: dict[str, object],
    environment: dict[str, str],
) -> tuple[Path, Path]:
    generated_root = build_root / "sqlcipher-amalgamation"
    generated_root.mkdir()
    build = manifest["build"]
    assert isinstance(build, dict)
    _run(
        [str(sqlcipher_root / "configure"), *[str(item) for item in build["configure_args"]]],
        cwd=generated_root,
        env=environment,
    )
    _run(["make", "sqlite3.c"], cwd=generated_root, env=environment)
    sqlite3_c = generated_root / "sqlite3.c"
    sqlite3_h = generated_root / "sqlite3.h"
    generated = manifest["generated"]
    assert isinstance(generated, dict)
    for path, key in ((sqlite3_c, "sqlite3_c_sha256"), (sqlite3_h, "sqlite3_h_sha256")):
        actual = sha256(path)
        if actual != generated[key]:
            raise BuildError(f"amalgamation_hash_mismatch:{path.name}:{actual}")
    return sqlite3_c, sqlite3_h


def _replace_exact(content: str, old: str, new: str, *, label: str) -> str:
    if content.count(old) != 1:
        raise BuildError(f"binding_patch_context_mismatch:{label}")
    return content.replace(old, new)


def patch_binding(
    binding_root: Path,
    sqlcipher_root: Path,
    sqlite3_c: Path,
    sqlite3_h: Path,
    manifest: dict[str, object],
) -> dict[str, str]:
    binding = manifest["sources"]["binding"]
    assert isinstance(binding, dict)
    setup_path = binding_root / "setup.py"
    pyproject_path = binding_root / "pyproject.toml"
    if sha256(setup_path) != binding["upstream_setup_sha256"]:
        raise BuildError("binding_setup_source_hash_mismatch")
    if sha256(pyproject_path) != binding["upstream_pyproject_sha256"]:
        raise BuildError("binding_pyproject_source_hash_mismatch")
    if sha256(binding_root / "LICENSE") != binding["license_sha256"]:
        raise BuildError("binding_license_hash_mismatch")

    setup = setup_path.read_text(encoding="ISO-8859-1")
    setup = _replace_exact(
        setup,
        "VERSION = '0.6.2'",
        f"VERSION = '{binding['local_version']}'",
        label="local-version",
    )
    setup = _replace_exact(
        setup,
        "        ('SQLITE_EXTRA_SHUTDOWN', 'sqlcipher_extra_shutdown'),\n",
        "        ('SQLITE_EXTRA_SHUTDOWN', 'sqlcipher_extra_shutdown'),\n"
        "        ('SQLCIPHER_CRYPTO_CC', '1'),\n",
        label="commoncrypto-macro",
    )
    conan_block = '''    try:
        import conan
    except ImportError:
        library_dirs = include_dirs = []
    else:
        # Configure the compiler
        arch = get_arch()
        if arch == "universal2":
            # https://docs.conan.io/2/reference/tools/cmake/cmaketoolchain.html#conan-tools-cmaketoolchain-universal-binaries
            conan_info = install_openssl("armv8|x86_64")
        else:
            conan_info = install_openssl(arch)
        library_dirs, include_dirs = add_deps(conan_info)
'''
    setup = _replace_exact(
        setup,
        conan_block,
        "    # JKM local build: CommonCrypto is selected explicitly; Conan is disabled.\n"
        "    library_dirs = include_dirs = []\n",
        label="disable-conan",
    )
    setup = _replace_exact(
        setup,
        "    extra_compile_args = ['-Qunused-arguments'] if sys.platform == 'darwin' else []",
        "    extra_compile_args = [\n"
        "        '-Qunused-arguments', '-O2', '-g0', '-arch', 'arm64',\n"
        "        '-mmacosx-version-min=11.0',\n"
        "    ] if sys.platform == 'darwin' else []",
        label="compile-flags",
    )
    setup = _replace_exact(
        setup,
        "    else:\n        # Include math library, required for fts5, and crypto.\n"
        "        extra_link_args.extend(['-lm', '-lcrypto'])",
        "    elif sys.platform == 'darwin':\n"
        "        extra_link_args.extend([\n"
        "            '-lm', '-arch', 'arm64', '-mmacosx-version-min=11.0',\n"
        "            '-framework', 'Security', '-framework', 'CoreFoundation',\n"
        "        ])\n"
        "    else:\n"
        "        # Non-macOS upstream behavior is not used by this build basis.\n"
        "        extra_link_args.extend(['-lm', '-lcrypto'])",
        label="commoncrypto-linkage",
    )
    setup_path.write_text(setup, encoding="ISO-8859-1")

    pyproject = pyproject_path.read_text(encoding="utf-8")
    pyproject = _replace_exact(
        pyproject,
        '    "setuptools>=69",\n    "conan>=2.0",\n    "wheel"',
        '    "setuptools==83.0.0",\n    "wheel==0.46.3"',
        label="build-requirements",
    )
    pyproject = _replace_exact(
        pyproject,
        'version = "0.6.2"',
        f'version = "{binding["local_version"]}"',
        label="project-version",
    )
    pyproject = _replace_exact(
        pyproject,
        'license = "MIT"',
        'license = "LicenseRef-zlib"\nlicense-files = [\n'
        '    "LICENSE",\n    "SQLCIPHER_LICENSE.md",\n'
        '    "SQLITE_LICENSE.md",\n    "THIRD_PARTY_NOTICE.md",\n]',
        label="license-metadata",
    )
    pyproject_path.write_text(pyproject, encoding="utf-8")

    shutil.copyfile(sqlite3_c, binding_root / "vendor/sqlite3.c")
    shutil.copyfile(sqlite3_h, binding_root / "vendor/sqlite3.h")
    sqlcipher_source = manifest["sources"]["sqlcipher"]
    assert isinstance(sqlcipher_source, dict)
    source_license = sqlcipher_root / "LICENSE.md"
    source_sqlite_license = sqlcipher_root / "SQLITE_LICENSE.md"
    if sha256(source_license) != sqlcipher_source["license_sha256"]:
        raise BuildError("sqlcipher_license_source_hash_mismatch")
    if sha256(source_sqlite_license) != sqlcipher_source["sqlite_license_source_sha256"]:
        raise BuildError("sqlite_license_source_hash_mismatch")
    shutil.copyfile(source_license, binding_root / "SQLCIPHER_LICENSE.md")
    normalized_sqlite_license = "\n".join(
        line.rstrip() for line in source_sqlite_license.read_text(encoding="utf-8").splitlines()
    ) + "\n"
    repository_sqlite_license = (
        REPO_ROOT / "packaging/licenses/sqlcipher-4.17.0/SQLITE_LICENSE.md"
    )
    if repository_sqlite_license.read_text(encoding="utf-8") != normalized_sqlite_license:
        raise BuildError("sqlite_license_repository_copy_mismatch")
    (binding_root / "SQLITE_LICENSE.md").write_text(
        normalized_sqlite_license, encoding="utf-8"
    )
    shutil.copyfile(NOTICE_PATH, binding_root / "THIRD_PARTY_NOTICE.md")

    hashes = {
        "setup_py": sha256(setup_path),
        "pyproject_toml": sha256(pyproject_path),
        "binding_license": sha256(binding_root / "LICENSE"),
        "sqlcipher_license": sha256(binding_root / "SQLCIPHER_LICENSE.md"),
        "sqlite_license": sha256(binding_root / "SQLITE_LICENSE.md"),
        "third_party_notice": sha256(binding_root / "THIRD_PARTY_NOTICE.md"),
    }
    generated = manifest["generated"]
    assert isinstance(generated, dict)
    for report_key, manifest_key in (
        ("setup_py", "patched_setup_sha256"),
        ("pyproject_toml", "patched_pyproject_sha256"),
        ("sqlcipher_license", "sqlcipher_license_sha256"),
        ("sqlite_license", "sqlite_license_sha256"),
        ("third_party_notice", "third_party_notice_sha256"),
    ):
        expected = generated.get(manifest_key)
        if expected and hashes[report_key] != expected:
            raise BuildError(f"binding_patch_hash_mismatch:{report_key}")
    return hashes


def build_wheel(
    binding_root: Path,
    output_root: Path,
    build_python: Path,
    environment: dict[str, str],
    manifest: dict[str, object],
) -> Path:
    wheel_root = output_root / "wheel"
    wheel_root.mkdir()
    _run(
        [
            str(build_python),
            "-m",
            "pip",
            "wheel",
            "--disable-pip-version-check",
            "--no-build-isolation",
            "--no-deps",
            "--no-cache-dir",
            "--wheel-dir",
            str(wheel_root),
            ".",
        ],
        cwd=binding_root,
        env=environment,
    )
    wheels = list(wheel_root.glob("*.whl"))
    if len(wheels) != 1:
        raise BuildError("wheel_output_count_invalid")
    wheel = wheels[0]
    binding = manifest["sources"]["binding"]
    assert isinstance(binding, dict)
    expected_name = (
        f"sqlcipher3-{binding['local_version']}-cp314-cp314-"
        "macosx_11_0_arm64.whl"
    )
    if wheel.name != expected_name:
        raise BuildError(f"wheel_name_mismatch:{wheel.name}")
    expected_hash = manifest["generated"].get("expected_wheel_sha256")
    actual_hash = sha256(wheel)
    if expected_hash and actual_hash != expected_hash:
        raise BuildError(f"wheel_hash_mismatch:{actual_hash}")
    return wheel


def build(*, requested_root: Path | None, offline_cache: Path | None) -> Path:
    manifest = load_manifest()
    toolchain = verify_toolchain(manifest)
    root = create_build_root(requested_root)
    print(f"build_root={root}", flush=True)
    downloads = root / "downloads"
    downloads.mkdir()

    sources = manifest["sources"]
    assert isinstance(sources, dict)
    source_archives: dict[str, Path] = {}
    for name in ("sqlcipher", "binding"):
        source = sources[name]
        assert isinstance(source, dict)
        source_archives[name] = obtain_source(
            source, downloads=downloads, offline_cache=offline_cache
        )

    extracted = root / "sources"
    extracted.mkdir()
    sqlcipher_source = sources["sqlcipher"]
    binding_source = sources["binding"]
    assert isinstance(sqlcipher_source, dict) and isinstance(binding_source, dict)
    sqlcipher_root = safe_extract_tar(
        source_archives["sqlcipher"], extracted / "sqlcipher", str(sqlcipher_source["root"])
    )
    binding_root = safe_extract_tar(
        source_archives["binding"], extracted / "binding", str(binding_source["root"])
    )

    build_python = create_build_venv(root, offline_cache=offline_cache)
    environment = deterministic_environment(root, manifest)
    sqlite3_c, sqlite3_h = generate_amalgamation(
        sqlcipher_root, root, manifest, environment
    )
    patch_hashes = patch_binding(
        binding_root, sqlcipher_root, sqlite3_c, sqlite3_h, manifest
    )
    wheel = build_wheel(binding_root, root, build_python, environment, manifest)

    report = {
        "format": 1,
        "root": str(root),
        "toolchain": toolchain,
        "sources": {
            name: {
                "archive": path.name,
                "sha256": sha256(path),
                "commit": sources[name]["commit"],
            }
            for name, path in source_archives.items()
        },
        "generated": {
            "sqlite3_c_sha256": sha256(sqlite3_c),
            "sqlite3_h_sha256": sha256(sqlite3_h),
        },
        "binding_patch": patch_hashes,
        "build": {
            "source_date_epoch": manifest["build"]["source_date_epoch"],
            "cflags": environment["CFLAGS"],
            "ldflags": environment["LDFLAGS"],
            "crypto_provider": manifest["target"]["crypto_provider"],
        },
        "wheel": {
            "path": str(wheel),
            "name": wheel.name,
            "size": wheel.stat().st_size,
            "sha256": sha256(wheel),
        },
    }
    report_path = root / REPORT_NAME
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"report={report_path}")
    print(f"wheel={wheel}")
    print(f"wheel_sha256={report['wheel']['sha256']}")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        help="new absolute build root below the macOS system temp directory",
    )
    parser.add_argument(
        "--offline-cache",
        type=Path,
        help="directory containing both source archives and pinned build-tool wheels",
    )
    args = parser.parse_args()
    offline_cache = args.offline_cache.resolve() if args.offline_cache else None
    if offline_cache is not None and (
        offline_cache.is_symlink() or not offline_cache.is_dir()
    ):
        raise BuildError("offline_cache_invalid")
    build(requested_root=args.root, offline_cache=offline_cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
