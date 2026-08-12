from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.application.commands.backup import CreateBackupCommand
from src.application.commands.final_v4_backup_restore import (
    FinalV4BackupRestoreApplicationError,
    FinalV4EncryptedBackupApplicationService,
    FinalV4EncryptedRestoreApplicationService,
)
from src.application.commands.restore import (
    CreateRestoreHandoffCommand,
    VerifyPreparedRestoreQuery,
    VerifyRestoreBackupQuery,
)
from src.core.restore_runtime import RestoreHandoffResult
from src.desktop_app.adapters.backup_restore_desktop_adapter import (
    BackupRestoreDesktopAdapter,
)
from src.desktop_app.runtime import runtime_paths


class _EncryptedService:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.paths = SimpleNamespace(
            final_v4=SimpleNamespace(
                key_runtime=SimpleNamespace(root=root),
            )
        )
        self.created: list[Path] = []
        self.staged: list[tuple[Path, Path]] = []
        self.result = SimpleNamespace(
            path=root / "source.jkmebackup",
            container_size=2048,
            container_sha256="a" * 64,
            manifest=SimpleNamespace(
                created_at="2026-08-09T12:00:00Z",
                app_version="0.4.0",
                format_version=1,
            ),
        )

    def create(self, target: Path):
        assert target.suffix == ".jkmebackup"
        self.created.append(target)
        return SimpleNamespace(**{**self.result.__dict__, "path": target})

    def verify(self, path: Path):
        assert Path(path).suffix == ".jkmebackup"
        return SimpleNamespace(**{**self.result.__dict__, "path": Path(path)})

    def restore_staging(self, source: Path, target: Path):
        self.staged.append((Path(source), Path(target)))
        target.mkdir(mode=0o700)
        return SimpleNamespace(staging_root=target)

    def verify_restore_ready(self, staging_root: Path, *, expected_container_sha256: str):
        assert expected_container_sha256 == "a" * 64
        return SimpleNamespace(
            staging_root=Path(staging_root),
            container_sha256=expected_container_sha256,
        )

    def restore_preview_counts(self, staging_root: Path, *, expected_container_sha256: str):
        self.verify_restore_ready(
            staging_root,
            expected_container_sha256=expected_container_sha256,
        )
        return SimpleNamespace(
            students=3,
            observations=4,
            learning_report_revisions=5,
            learning_conference_revisions=6,
            managed_documents=7,
        )


def test_product_backup_command_publishes_only_jkmebackup(tmp_path: Path) -> None:
    service = _EncryptedService(tmp_path)
    application = FinalV4EncryptedBackupApplicationService(
        service,
        now_provider=lambda: datetime(2026, 8, 9, 12, tzinfo=UTC),
    )
    paths = SimpleNamespace(database=tmp_path / "forbidden.sqlite")
    result = application.create(
        CreateBackupCommand(
            database_path=paths.database,
            runtime_paths=paths,
            target_path=tmp_path,
            app_version="0.4.0",
            build_commit="commit",
        )
    )
    assert result.path.name == (
        "Jenaplan-Kompetenzmanager-Backup-20260809T120000Z.jkmebackup"
    )
    assert not list(tmp_path.glob("*.jkmbackup"))


def test_cipher_desktop_discovery_never_enqueues_zip_v1(tmp_path: Path) -> None:
    paths = runtime_paths(tmp_path)
    paths.backups.mkdir(parents=True)
    encrypted = paths.backups / "current.jkmebackup"
    encrypted.write_bytes(b"encrypted")
    (paths.backups / "historical.jkmbackup").write_bytes(b"zip-v1")
    adapter = BackupRestoreDesktopAdapter(
        paths,
        app_version="0.4.0",
        backup_service=object(),
        restore_service=object(),
        enabled=True,
        backup_extension=".jkmebackup",
    )
    operation = adapter.discover_verified_backups_operation()
    assert operation.payload.paths == (encrypted,)
    assert operation.payload.allowed_suffix == ".jkmebackup"


def test_product_restore_creates_and_reverifies_restore_ready_before_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _EncryptedService(tmp_path)
    application = FinalV4EncryptedRestoreApplicationService(
        service,
        lock=object(),
        worker_launcher=object(),
        restore_id_provider=lambda: "restore-1",
    )
    source = tmp_path / "pilot.jkmebackup"
    result = application.verify(VerifyRestoreBackupQuery(source))
    assert result.restore_id == "restore-1"
    assert result.staging_root.parent.name == "encrypted-restore-staging"
    assert result.preview.students_count == 3
    assert service.staged == [(source, result.staging_root)]
    assert application.verify_prepared(
        VerifyPreparedRestoreQuery("restore-1", SimpleNamespace())
    ) is result

    handoff = RestoreHandoffResult(
        "restore-1",
        "nonce",
        tmp_path / "handoff.json",
        "a" * 64,
        "b" * 64,
    )
    preparation = SimpleNamespace(handoff=handoff)
    prepared: list[dict[str, object]] = []
    launched: list[object] = []

    def prepare(**kwargs):
        prepared.append(kwargs)
        return preparation

    monkeypatch.setattr(
        "src.application.commands.final_v4_backup_restore.prepare_final_v4_live_restore",
        prepare,
    )
    monkeypatch.setattr(
        "src.application.commands.final_v4_backup_restore.launch_prepared_final_v4_restore",
        lambda **kwargs: launched.append(kwargs) or "worker",
    )
    observed = application.create_handoff(
        CreateRestoreHandoffCommand(
            source,
            "restore-1",
            SimpleNamespace(),
            "0.4.0",
            "commit",
        )
    )
    assert observed is handoff
    assert prepared[0]["staging_root"] == result.staging_root
    assert application.launch_prepared_restore(handoff) == "worker"
    assert launched[0]["preparation"] is preparation
    assert launched[0]["launcher"] is application.worker_launcher


def test_historical_zip_v1_is_not_a_cipher_restore_candidate(tmp_path: Path) -> None:
    service = _EncryptedService(tmp_path)
    application = FinalV4EncryptedRestoreApplicationService(
        service,
        lock=object(),
        worker_launcher=object(),
    )
    with pytest.raises(FinalV4BackupRestoreApplicationError) as caught:
        application.verify(
            VerifyRestoreBackupQuery(tmp_path / "historical.jkmbackup")
        )
    assert caught.value.code == "backup_invalid"
    assert service.staged == []
