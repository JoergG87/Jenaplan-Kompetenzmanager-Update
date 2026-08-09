from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from src.security.final_v3_document_runtime import FinalV3DocumentRuntimeError
from tests.helpers.final_v3_document_runtime_worker import (
    DOCUMENT_ID,
    NEW_PAYLOAD,
    OLD_PAYLOAD,
    open_exact_runtime,
    open_runtime,
    paths_for,
)
from tests.test_final_v4_sqlcipher_runtime import requires_exact_417


class _Consumer:
    def __init__(self) -> None:
        self.payload = bytearray()
        self.finished = False
        self.aborted: str | None = None

    def start(self, _manifest) -> None:
        return None

    def write(self, chunk: bytes) -> None:
        self.payload.extend(chunk)

    def finish(self, _result) -> None:
        self.finished = True

    def abort(self, code: str) -> None:
        self.aborted = code


def _worker(base: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            "tests/helpers/final_v3_document_runtime_worker.py",
            arguments[0],
            str(base),
            *arguments[1:],
        ],
        cwd=Path.cwd(),
        env={**os.environ, "PYTHONPATH": str(Path.cwd())},
        capture_output=True,
        check=False,
        timeout=20,
    )


def _read(base: Path) -> bytes:
    consumer = _Consumer()
    open_runtime(base).read(document_id=DOCUMENT_ID, consumer=consumer)
    assert consumer.finished and consumer.aborted is None
    return bytes(consumer.payload)


@pytest.mark.parametrize(
    ("boundary", "restart_state"),
    [
        ("before_container_creation", "clean"),
        ("during_container_write", "blocked"),
        ("after_write_before_verification", "blocked"),
        ("after_verification_before_prepared", "blocked"),
        ("after_prepared_before_activation", "resumable"),
        ("during_pointer_switch", "resumable"),
        ("after_activation_before_retained", "resumable"),
    ],
)
def test_real_process_abort_is_exactly_resumable_or_fail_closed(
    tmp_path: Path, boundary: str, restart_state: str
) -> None:
    setup = subprocess.run(
        [
            sys.executable,
            "tests/helpers/final_v3_document_runtime_worker.py",
            "setup",
            str(tmp_path),
        ],
        cwd=Path.cwd(),
        env={**os.environ, "PYTHONPATH": str(Path.cwd())},
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert setup.returncode == 0, setup.stderr
    crashed = subprocess.run(
        [
            sys.executable,
            "tests/helpers/final_v3_document_runtime_worker.py",
            "crash",
            str(tmp_path),
            boundary,
        ],
        cwd=Path.cwd(),
        env={**os.environ, "PYTHONPATH": str(Path.cwd())},
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert crashed.returncode == 73
    assert crashed.stdout == b"" and crashed.stderr == b""
    paths = paths_for(tmp_path)
    for path in paths.storage_root.iterdir():
        if path.is_file() and path.name.endswith(".jkmedoc"):
            assert OLD_PAYLOAD not in path.read_bytes()
            assert NEW_PAYLOAD not in path.read_bytes()

    if restart_state == "blocked":
        with pytest.raises(FinalV3DocumentRuntimeError) as captured:
            open_runtime(tmp_path).validate_restart()
        assert captured.value.code == "document_storage_inventory_invalid"
        with sqlite3.connect(paths.database) as connection:
            assert connection.execute(
                """
                SELECT document_generation, lifecycle_status
                FROM final_v3_document_generations
                ORDER BY document_generation
                """
            ).fetchall() == [(1, "ACTIVE")]
        return

    restarted = open_runtime(tmp_path)
    restarted.validate_restart()
    old_consumer = _Consumer()
    restarted.read(document_id=DOCUMENT_ID, consumer=old_consumer)
    assert old_consumer.finished and old_consumer.aborted is None
    assert bytes(old_consumer.payload) == OLD_PAYLOAD
    with sqlite3.connect(paths.database) as connection:
        rows = connection.execute(
            """
            SELECT document_generation, lifecycle_status
            FROM final_v3_document_generations
            ORDER BY document_generation
            """
        ).fetchall()
    if restart_state == "clean":
        assert rows == [(1, "ACTIVE")]
        return

    assert rows == [(1, "ACTIVE"), (2, "PREPARED")]
    active = restarted.activate(document_id=DOCUMENT_ID, document_generation=2)
    assert active.lifecycle_status == "ACTIVE"
    assert _read(tmp_path) == NEW_PAYLOAD
    with sqlite3.connect(paths.database) as connection:
        assert connection.execute(
            """
            SELECT document_generation, lifecycle_status
            FROM final_v3_document_generations
            ORDER BY document_generation
            """
        ).fetchall() == [(1, "RETAINED"), (2, "ACTIVE")]


@requires_exact_417
@pytest.mark.parametrize(
    "boundary",
    [
        "before_container_creation",
        "during_container_write",
        "after_write_before_verification",
        "after_verification_before_prepared",
        "after_prepared_before_activation",
        "during_pointer_switch",
        "after_activation_before_retained",
    ],
)
def test_exact_sqlcipher_process_abort_is_resumable_or_fail_closed(
    tmp_path: Path, boundary: str
) -> None:
    setup = _worker(tmp_path, "exact-setup")
    assert setup.returncode == 0, setup.stderr
    crashed = _worker(tmp_path, "exact-crash", boundary)
    assert crashed.returncode == 73
    assert crashed.stdout == b"" and crashed.stderr == b""

    sidecars = tuple(
        Path(f"{paths_for(tmp_path).database}{suffix}")
        for suffix in ("-journal", "-wal", "-shm")
        if Path(f"{paths_for(tmp_path).database}{suffix}").exists()
    )
    if sidecars:
        with pytest.raises(FinalV3DocumentRuntimeError) as captured:
            open_exact_runtime(tmp_path).validate_restart()
        assert captured.value.code == "document_database_sidecar_present"
        return

    restarted = open_exact_runtime(tmp_path)
    if boundary in {
        "during_container_write",
        "after_write_before_verification",
        "after_verification_before_prepared",
    }:
        with pytest.raises(FinalV3DocumentRuntimeError) as captured:
            restarted.validate_restart()
        assert captured.value.code == "document_storage_inventory_invalid"
        return

    restarted.validate_restart()
    old_consumer = _Consumer()
    restarted.read(document_id=DOCUMENT_ID, consumer=old_consumer)
    assert old_consumer.finished and old_consumer.aborted is None
    assert bytes(old_consumer.payload) == OLD_PAYLOAD
    if boundary in {
        "after_prepared_before_activation",
        "during_pointer_switch",
        "after_activation_before_retained",
    }:
        restarted.activate(document_id=DOCUMENT_ID, document_generation=2)
        consumer = _Consumer()
        open_exact_runtime(tmp_path).read(
            document_id=DOCUMENT_ID, consumer=consumer
        )
        assert consumer.finished and consumer.aborted is None
        assert bytes(consumer.payload) == NEW_PAYLOAD
