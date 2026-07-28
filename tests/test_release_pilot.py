from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

import scripts.release_pilot as release


@pytest.fixture
def config() -> release.ReleaseConfig:
    return release.ReleaseConfig.load()


@pytest.fixture
def isolated_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    pointer = tmp_path / "release_state.json"
    monkeypatch.setattr(release, "STATE_POINTER", pointer)
    return pointer


def create_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
) -> release.Manifest:
    monkeypatch.setattr(
        release.ReleaseConfig,
        "output_root",
        property(lambda self: tmp_path / "output"),
    )
    return release.Manifest.create(
        config=config,
        version="0.3.1",
        build=304,
        source_commit="a" * 40,
        branch="spike/python-gui",
    )


def appcast_payload(*, build: int = 303, version: str = "0.3.0") -> bytes:
    return f"""<?xml version="1.0"?>
<rss xmlns:sparkle="{release.SPARKLE_NAMESPACE}" version="2.0">
  <channel>
    <title>Jenaplan-Kompetenzmanager</title>
    <item>
      <title>{version}</title>
      <sparkle:version>{build}</sparkle:version>
      <sparkle:shortVersionString>{version}</sparkle:shortVersionString>
      <sparkle:minimumSystemVersion>13.0</sparkle:minimumSystemVersion>
      <sparkle:hardwareRequirements>arm64</sparkle:hardwareRequirements>
      <sparkle:releaseNotesLink sparkle:edSignature="notes" sparkle:length="12">https://example.test/notes.html</sparkle:releaseNotesLink>
      <enclosure url="https://example.test/app.dmg" length="42" type="application/octet-stream" sparkle:edSignature="archive"/>
    </item>
  </channel>
</rss>
<!-- sparkle-signatures:
edSignature: feed
length: 1
-->
""".encode()


def test_configuration_is_canonical_and_stable_is_disabled(
    config: release.ReleaseConfig,
) -> None:
    assert config["schema_version"] == 1
    assert config["stable_enabled"] is False
    assert config["architecture"] == "arm64"
    assert config["reference_release"]["build"] == 303
    assert len(config["asset_patterns"]) == 4


def test_build_script_can_defer_package_only_smokes() -> None:
    payload = Path("scripts/build_macos_pilot.sh").read_text(encoding="utf-8")
    assert "--defer-package-tests" in payload
    assert 'if [ "$DEFER_PACKAGE_TESTS" = "0" ]; then' in payload
    assert "scripts/smoke_test_macos_app.py" in payload
    assert "scripts/smoke_test_packaged_restore_worker.py" in payload


def test_configuration_rejects_stable_activation(
    tmp_path: Path,
    config: release.ReleaseConfig,
) -> None:
    payload = config.path.read_text(encoding="utf-8").replace(
        "stable_enabled = false", "stable_enabled = true"
    )
    path = tmp_path / "release.toml"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(release.ReleaseError, match="Stable"):
        release.ReleaseConfig.load(path)


def test_manifest_is_resumable_and_public_variant_has_no_private_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
    isolated_state: Path,
) -> None:
    manifest = create_manifest(tmp_path, monkeypatch, config)
    manifest.complete("inspected")
    manifest.complete("prepared", worktree_path="/Users/private/worktree")
    reloaded = release.Manifest.load(manifest.local_path)
    assert reloaded.is_complete("prepared")
    public = json.loads(manifest.public_path.read_text(encoding="utf-8"))
    assert "worktree_path" not in public
    assert "/Users/" not in manifest.public_path.read_text(encoding="utf-8")
    assert isolated_state.is_file()


def test_state_machine_rejects_out_of_order_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
    isolated_state: Path,
) -> None:
    manifest = create_manifest(tmp_path, monkeypatch, config)
    with pytest.raises(release.ReleaseError, match="Vorgängerphase"):
        manifest.complete("built")


def test_failed_phase_can_resume_without_losing_completed_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
    isolated_state: Path,
) -> None:
    manifest = create_manifest(tmp_path, monkeypatch, config)
    manifest.complete("inspected")
    manifest.complete("prepared")
    manifest.complete("built")
    manifest.fail("package_verified", release.ReleaseError("temporary"))
    assert manifest.is_complete("built")
    manifest.complete("package_verified")
    assert manifest.data["error"] is None


@pytest.mark.parametrize(
    "value",
    (
        "Authorization: Bearer ghp_abcdefghijklmnopqrstuvwxyz",
        "password=very-secret",
        "https://user:secret@example.test/file",
        "token: ghp_abcdefghijklmnopqrstuvwxyz",
    ),
)
def test_secret_redaction(value: str) -> None:
    sanitized = release.redact(value)
    assert "very-secret" not in sanitized
    assert "ghp_" not in sanitized
    assert "user:secret" not in sanitized


def test_runner_redacts_subprocess_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def failed(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0], 1, "", "Authorization: Bearer ghp_abcdefghijklmnopqrstuvwxyz"
        )

    monkeypatch.setattr(subprocess, "run", failed)
    with pytest.raises(release.ReleaseError) as caught:
        release.Runner().run(["gh", "auth", "status"])
    assert "ghp_" not in str(caught.value)


def test_optional_github_lookup_distinguishes_404_from_outage(
    config: release.ReleaseConfig,
) -> None:
    automation = release.ReleasePilot(config)

    def missing(command):
        raise release.ReleaseError("HTTP 404: release not found")

    automation._gh_json = missing  # type: ignore[method-assign]
    assert automation._gh_optional_json(["release", "view", "missing"]) is None

    def outage(command):
        raise release.ReleaseError("connection timed out")

    automation._gh_json = outage  # type: ignore[method-assign]
    with pytest.raises(release.ReleaseError, match="timed out"):
        automation._gh_optional_json(["release", "view", "missing"])


def test_appcast_parser_and_build_order() -> None:
    items = release.parse_appcast(appcast_payload())
    assert release.latest_pilot_build(items) == 303
    assert items[0]["architecture"] == "arm64"


def test_appcast_rejects_invalid_xml() -> None:
    with pytest.raises(release.ReleaseError, match="wohlgeformt"):
        release.parse_appcast(b"<not-xml")


def test_new_appcast_item_is_newest_and_preserves_old_build(
    config: release.ReleaseConfig,
) -> None:
    automation = release.ReleasePilot(config)
    payload = automation._build_appcast(
        existing_payload=appcast_payload(),
        version="0.3.1",
        build=304,
        dmg_url="https://example.test/app-304.dmg",
        dmg_length=84,
        dmg_signature="new-signature",
        notes_url="https://example.test/notes-304.html",
        notes_length=24,
        notes_signature="new-notes",
    )
    items = release.parse_appcast(payload)
    assert [item["build"] for item in items] == [304, 303]


def test_appcast_blocks_same_or_lower_build(config: release.ReleaseConfig) -> None:
    automation = release.ReleasePilot(config)
    with pytest.raises(release.ReleaseError, match="gleichen oder höheren"):
        automation._build_appcast(
            existing_payload=appcast_payload(),
            version="0.3.0",
            build=303,
            dmg_url="https://example.test/app.dmg",
            dmg_length=42,
            dmg_signature="signature",
            notes_url="https://example.test/notes.html",
            notes_length=12,
            notes_signature="notes",
        )


def test_phase_plan_requires_explicit_appcast_gate() -> None:
    assert release.phase_plan(
        include_build=True, publish_github=False, publish_appcast=False
    ) == ["inspect", "prepare", "build", "package-test"]
    with pytest.raises(release.ReleaseError, match="GitHub"):
        release.phase_plan(
            include_build=True, publish_github=False, publish_appcast=True
        )


def test_run_dry_run_plans_without_state_or_publication(
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
) -> None:
    monkeypatch.setattr(release.ReleaseConfig, "load", lambda path: config)
    monkeypatch.setattr(
        release.ReleasePilot,
        "inspect",
        lambda self, **kwargs: {
            "status": "ok",
            "version": "0.3.0",
            "build": 303,
            "already_published": True,
        },
    )
    rendered: list[dict[str, object]] = []
    monkeypatch.setattr(release, "render", rendered.append)
    assert release.main(["run", "--dry-run", "--build-artifacts"]) == 0
    assert rendered[0]["publishing"] == "disabled"
    assert rendered[0]["sparkle_private_material"] == "not_accessed"
    assert "build" in rendered[0]["planned_phases"]


def test_dry_run_runner_never_executes_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*args, **kwargs):
        raise AssertionError("subprocess must not run")

    monkeypatch.setattr(subprocess, "run", unexpected)
    completed = release.Runner(dry_run=True).run(
        ["git", "tag", "unsafe"], mutating=True
    )
    assert completed.returncode == 0


def test_inspect_aborts_for_dirty_worktree(
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
) -> None:
    values = {
        ("rev-parse", "--is-inside-work-tree"): "true",
        ("branch", "--show-current"): "spike/python-gui",
        ("rev-parse", "HEAD"): "a" * 40,
        ("status", "--porcelain=v1", "--untracked-files=all"): "?? secret.txt",
    }

    def fake_git(runner, *args, **kwargs):
        return values[args]

    monkeypatch.setattr(release, "git", fake_git)
    with pytest.raises(release.ReleaseError, match="nicht sauber"):
        release.ReleasePilot(config).inspect(check_network=False)


def test_inspect_aborts_for_wrong_commit_branch(
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
) -> None:
    values = {
        ("rev-parse", "--is-inside-work-tree"): "true",
        ("branch", "--show-current"): "main",
        ("rev-parse", "HEAD"): "a" * 40,
        ("status", "--porcelain=v1", "--untracked-files=all"): "",
    }

    monkeypatch.setattr(
        release, "git", lambda runner, *args, **kwargs: values[args]
    )
    with pytest.raises(release.ReleaseError, match="Unerwarteter Branch"):
        release.ReleasePilot(config).inspect(check_network=False)


def test_prepare_requires_version_committed_first(
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
) -> None:
    automation = release.ReleasePilot(config)
    monkeypatch.setattr(
        automation,
        "inspect",
        lambda **kwargs: {
            "head": "a" * 40,
            "branch": "spike/python-gui",
        },
    )
    monkeypatch.setattr(release, "current_version", lambda: ("0.3.0", 303))
    with pytest.raises(release.ReleaseError, match="separat"):
        automation.prepare(version="0.3.1", build=304, check_network=False)


def test_manifest_commit_version_mismatch_blocks_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
    isolated_state: Path,
) -> None:
    manifest = create_manifest(tmp_path, monkeypatch, config)

    def fake_git(runner, *args, **kwargs):
        if args[:2] == ("cat-file", "-t"):
            return "commit"
        if args[0] == "show":
            return 'APP_VERSION = "0.3.2"\nAPP_BUILD_VERSION = "305"\n'
        raise AssertionError(args)

    monkeypatch.setattr(release, "git", fake_git)
    with pytest.raises(release.ReleaseError, match="Versionsquelle"):
        release.ReleasePilot(config)._ensure_manifest_source(manifest)


def test_asset_hash_mismatch_blocks_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
    isolated_state: Path,
) -> None:
    manifest = create_manifest(tmp_path, monkeypatch, config)
    asset = tmp_path / "asset.dmg"
    asset.write_bytes(b"original")
    manifest.data["assets"] = [
        {
            "name": asset.name,
            "size": asset.stat().st_size,
            "sha256": release.sha256_file(asset),
            "local_path": str(asset),
        }
    ]
    manifest.save()
    asset.write_bytes(b"changed!")
    with pytest.raises(release.ReleaseError, match="verändert"):
        release.ReleasePilot(config)._asset_path(manifest, asset.name)


def test_existing_reference_release_blocks_republication(
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
) -> None:
    automation = release.ReleasePilot(config)
    monkeypatch.setattr(
        automation,
        "_remote_release",
        lambda tag: {
            "isDraft": False,
            "isPrerelease": True,
            "assets": [
                {
                    "name": asset["name"],
                    "size": asset["size"],
                    "digest": f"sha256:{asset['sha256']}",
                }
                for asset in config["reference_release"]["assets"]
            ],
        },
    )
    monkeypatch.setattr(
        automation,
        "_resolve_remote_tag_commit",
        lambda tag: config["reference_release"]["source_commit"],
    )
    monkeypatch.setattr(
        automation,
        "_remote_appcast",
        lambda: [
            {
                "build": 303,
                "length": next(
                    asset["size"]
                    for asset in config["reference_release"]["assets"]
                    if asset["name"].endswith(".dmg")
                ),
            },
            {"build": 202, "length": 1},
        ],
    )
    result = automation.verify_reference_303()
    assert result["same_build_republish_blocked"] is True
    assert result["lower_build_update_eligible"] is True
    assert result["stable_enabled"] is False


def test_github_failure_does_not_invalidate_built_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
    isolated_state: Path,
) -> None:
    manifest = create_manifest(tmp_path, monkeypatch, config)
    for phase in ("inspected", "prepared", "built", "package_verified"):
        manifest.complete(phase)
    monkeypatch.setattr(
        release.ReleasePilot,
        "_manifest_assets_by_name",
        lambda self, current: {},
    )

    class OfflineRunner(release.Runner):
        def run(self, command, **kwargs):
            raise release.ReleaseError("GitHub unavailable")

    with pytest.raises(release.ReleaseError, match="unavailable"):
        release.ReleasePilot(config, OfflineRunner()).publish_github(manifest)
    assert manifest.is_complete("built")
    assert manifest.is_complete("package_verified")


def test_colliding_github_release_commit_is_no_go(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
    isolated_state: Path,
) -> None:
    manifest = create_manifest(tmp_path, monkeypatch, config)
    for phase in ("inspected", "prepared", "built", "package_verified"):
        manifest.complete(phase)
    automation = release.ReleasePilot(config)
    monkeypatch.setattr(automation, "_manifest_assets_by_name", lambda current: {})
    monkeypatch.setattr(
        automation,
        "_remote_release",
        lambda tag: {
            "isDraft": True,
            "isPrerelease": True,
            "assets": [],
            "databaseId": 1,
            "url": "https://example.test/release",
        },
    )
    monkeypatch.setattr(
        automation, "_resolve_remote_tag_commit", lambda tag: "b" * 40
    )
    monkeypatch.setattr(
        automation.runner,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", ""),
    )
    with pytest.raises(release.ReleaseError, match="anderen Commit"):
        automation.publish_github(manifest)


def test_appcast_outage_preserves_completed_github_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: release.ReleaseConfig,
    isolated_state: Path,
) -> None:
    manifest = create_manifest(tmp_path, monkeypatch, config)
    for phase in (
        "inspected",
        "prepared",
        "built",
        "package_verified",
        "github_draft_created",
        "github_assets_verified",
        "github_published",
    ):
        manifest.complete(phase)
    dmg_name = release.expected_asset_names(config, "0.3.1", 304)[0]
    dmg = tmp_path / dmg_name
    dmg.write_bytes(b"synthetic-dmg")
    manifest.data["assets"] = [
        {
            "name": dmg_name,
            "size": dmg.stat().st_size,
            "sha256": release.sha256_file(dmg),
            "local_path": str(dmg),
        }
    ]
    manifest.save()
    monkeypatch.setattr(
        release,
        "fetch_bytes",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            release.ReleaseError("GitHub download unavailable")
        ),
    )
    with pytest.raises(release.ReleaseError, match="unavailable"):
        release.ReleasePilot(config).publish_appcast(manifest)
    assert manifest.is_complete("github_published")
    assert manifest.data["phase_status"]["appcast_prepared"] == "failed"


def test_forbidden_runtime_artifact_is_blocked(
    tmp_path: Path, config: release.ReleaseConfig
) -> None:
    (tmp_path / "student.sqlite").write_bytes(b"synthetic")
    with pytest.raises(release.ReleaseError, match="Verbotenes"):
        release.ReleasePilot(config)._scan_forbidden(tmp_path)


def test_public_manifest_removes_local_asset_paths() -> None:
    payload = release.sanitize_public(
        {
            "assets": [
                {
                    "name": "a.dmg",
                    "local_path": "/Users/private/a.dmg",
                    "sha256": "a" * 64,
                }
            ]
        }
    )
    assert payload["assets"][0]["local_path"] == "<local-path-redacted>"
