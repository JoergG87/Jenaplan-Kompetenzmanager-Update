from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(mode: str, phase: str, root: Path) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    repository_root = Path(__file__).resolve().parents[1]
    environment["PYTHONPATH"] = str(repository_root)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.helpers.sprint9_backup_crash_worker",
            mode,
            phase,
            str(root),
        ],
        cwd=repository_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _assert_sources_unchanged(root: Path) -> None:
    expected = json.loads(
        (root / "source-hashes.json").read_text(encoding="ascii")
    )
    assert _hash(root / "source.sqlcipher") == expected["database"]
    assert _hash(root / "document.bin") == expected["document"]
    assert _hash(root / "foreign.bin") == expected["foreign"]
    assert (root / "foreign.bin").read_bytes() == (
        b"foreign-file-must-never-change"
    )


@pytest.mark.parametrize(
    "phase",
    [
        "writer_after_header",
        "writer_after_manifest",
        "writer_after_chunk:sqlcipher_database",
        "writer_after_chunk:managed_document",
        "writer_before_final",
        "writer_after_final",
        "writer_after_file_fsync",
        "writer_after_retained_fsync",
        "writer_after_preverify",
    ],
)
def test_real_process_abort_during_write_never_publishes_target(
    tmp_path: Path, phase: str
) -> None:
    root = (tmp_path / phase.replace(":", "-")).resolve()
    result = _run("write", phase, root)

    assert result.returncode == 73
    assert result.stdout == ""
    assert result.stderr == ""
    assert not (root / "container.jkmebackup").exists()
    _assert_sources_unchanged(root)
    assert not list(root.glob("*.jkmebackup"))


def test_real_process_abort_after_publication_leaves_valid_target(
    tmp_path: Path,
) -> None:
    root = (tmp_path / "writer-after-publication").resolve()
    result = _run("write", "writer_after_publish", root)

    assert result.returncode == 73
    assert result.stdout == ""
    assert result.stderr == ""
    assert (root / "container.jkmebackup").is_file()
    retained = list(root.glob(".*.retained"))
    assert len(retained) == 1
    assert os.stat(retained[0]).st_ino == os.stat(
        root / "container.jkmebackup"
    ).st_ino
    _assert_sources_unchanged(root)
    verified = _run("verify", "unused", root)
    assert verified.returncode == 0, verified.stderr
    assert verified.stdout == ""
    assert verified.stderr == ""


@pytest.mark.parametrize(
    "phase",
    [
        "restore_after_root_created",
        "restore_write:sqlcipher_database",
        "restore_write:managed_document",
        "restore_before_fsync:sqlcipher_database",
        "restore_after_entry:sqlcipher_database",
        "restore_after_entry:managed_document",
        "restore_before_completion",
        "restore_after_completion_file_fsync",
    ],
)
def test_real_process_abort_during_restore_never_publishes_completion(
    tmp_path: Path, phase: str
) -> None:
    root = (tmp_path / phase.replace(":", "-")).resolve()
    result = _run("restore", phase, root)

    assert result.returncode == 73
    assert result.stdout == ""
    assert result.stderr == ""
    assert (root / "container.jkmebackup").is_file()
    assert not (root / "restore" / ".restore-complete.json").exists()
    _assert_sources_unchanged(root)
    verified = _run("verify", "unused", root)
    assert verified.returncode == 0, verified.stderr
    assert verified.stdout == ""
    assert verified.stderr == ""


@pytest.mark.parametrize(
    "phase", ["restore_after_completion_publish", "restore_after_completion"]
)
def test_real_process_abort_after_restore_publication_leaves_valid_marker(
    tmp_path: Path, phase: str
) -> None:
    root = (tmp_path / phase.replace(":", "-")).resolve()
    result = _run("restore", phase, root)

    assert result.returncode == 73
    assert result.stdout == ""
    assert result.stderr == ""
    assert (root / "restore" / ".restore-complete.json").is_file()
    _assert_sources_unchanged(root)
    verified = _run("verify", "unused", root)
    assert verified.returncode == 0, verified.stderr
