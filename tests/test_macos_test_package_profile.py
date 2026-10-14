"""Synthetic profile/process gates; no native App, signing or Keychain accesses."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock
import uuid

import pytest

import src.core.macos_test_package_profile as identity
from src.desktop_app.runtime import application_data_root
from src.core.runtime_root_protection import prepare_synthetic_test_root, publish_pilot_product_root
from scripts.macos_package_profile import validate_build_selection, prepare_hook, profile_digest
from scripts.macos_package_profile import verify_prepared_hook


@pytest.fixture
def profile(monkeypatch):
    test_id, installation_id = str(uuid.uuid4()), str(uuid.uuid4())
    token = uuid.UUID(test_id).hex
    container = Path(tempfile.gettempdir()).resolve() / f"jkm-internal-test-{token}"
    container.mkdir(mode=0o700)
    prepare_synthetic_test_root(container / "data")
    bundle = f"{identity.PRODUCT_BUNDLE_ID}.internaltest.t{token}"
    payload = identity.MacOSTestPackageProfile(
        test_id, installation_id, bundle, f"JKM-Interner-Test-{token}",
        str(container / "data"), str(container / "build"), str(container / "artifacts"),
        tuple(f"{bundle}.{suffix}" for suffix in identity.SERVICES), f"test-v1:{test_id}",
    ).as_dict()
    monkeypatch.setattr(identity, "_test_identity", None)
    yield payload
    import shutil
    shutil.rmtree(container)


def config(tmp_path, profile):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile))
    return path


def test_product_default_is_unchanged_and_environment_cannot_activate_test(profile):
    assert validate_build_selection("product", None, environment={"JENAPLAN_INTERNAL_TEST_PROFILE": "foreign"}) is None
    assert identity.test_identity() is None
    assert identity.keychain_service(identity.PRODUCT_BUNDLE_ID + ".data-master-key") == b"de.jenaplan.kompetenzmanager.data-master-key"
    assert identity.keychain_account(profile["installation_id"], "item") == f'v1:{profile["installation_id"]}:item'.encode()


def test_explicit_complete_profile_is_read_only(tmp_path, profile):
    before = {p: p.stat() for p in Path(profile["runtime_root"]).rglob("*")}
    validated = validate_build_selection("internal-test", config(tmp_path, profile), environment={})
    assert validated.as_dict() == profile
    assert {p: p.stat() for p in Path(profile["runtime_root"]).rglob("*")} == before
    assert not Path(profile["build_root"]).exists()
    assert not Path(profile["dist_root"]).exists()


@pytest.mark.parametrize("field", [
    "test_id", "installation_id", "bundle_id", "app_name", "runtime_root", "build_root",
    "dist_root", "keychain_services", "account_prefix", "worker_bundle_id", "restart_bundle_id",
    "updates", "signing", "entitlements", "profile",
])
def test_every_missing_identity_rejected_before_writes(profile, field):
    profile.pop(field)
    with pytest.raises(ValueError, match="test_profile_invalid"):
        identity.validate_test_profile(profile)


@pytest.mark.parametrize("field,value", [
    ("bundle_id", identity.PRODUCT_BUNDLE_ID), ("app_name", identity.PRODUCT_APP_NAME),
    ("runtime_root", "/foreign/product"), ("build_root", "/foreign/build"),
    ("dist_root", "/foreign/release"), ("account_prefix", "v1"),
    ("worker_bundle_id", identity.PRODUCT_BUNDLE_ID), ("restart_bundle_id", identity.PRODUCT_BUNDLE_ID),
    ("updates", True), ("signing", "Developer ID Application: product"), ("entitlements", {}),
    ("keychain_services", [identity.PRODUCT_BUNDLE_ID + ".data-master-key"]), ("extra", "unknown"),
])
def test_conflicting_or_product_identities_rejected(profile, field, value):
    profile[field] = value
    with pytest.raises(ValueError, match="test_profile_invalid"):
        identity.validate_test_profile(profile)


def test_duplicate_ids_and_existing_artifact_targets_rejected(profile):
    duplicate = dict(profile, installation_id=profile["test_id"])
    with pytest.raises(ValueError):
        identity.validate_test_profile(duplicate)
    for field in ("build_root", "dist_root"):
        path = Path(profile[field]); path.mkdir()
        with pytest.raises(ValueError):
            identity.validate_test_profile(profile)
        path.rmdir()
        path.symlink_to(Path(profile["runtime_root"]), target_is_directory=True)
        with pytest.raises(ValueError):
            identity.validate_test_profile(profile, before_build=False)
        path.unlink()


def test_product_marker_and_bad_permissions_are_not_test_authority(profile):
    root = Path(profile["runtime_root"])
    root.chmod(0o755)
    with pytest.raises(ValueError):
        identity.validate_test_profile(profile)
    root.chmod(0o700)
    (root / ".jkm-runtime-root-v1").unlink()
    publish_pilot_product_root(root)
    with pytest.raises(ValueError):
        identity.validate_test_profile(profile)


def test_corrupted_authority_is_sanitized(profile):
    (Path(profile["runtime_root"]) / ".jkm-runtime-root-v1").write_text("broken")
    with pytest.raises(ValueError, match="^test_profile_invalid$"):
        identity.validate_test_profile(profile)


@pytest.mark.parametrize("name", ["MACOS_SIGN_IDENTITY", "MACOS_NOTARY_PROFILE", "JENAPLAN_PILOT_APPCAST_URL",
                                  "JENAPLAN_MACOS_BUILD_ROOT", "JENAPLAN_MACOS_DIST_ROOT"])
def test_signing_feed_and_output_overrides_rejected(tmp_path, profile, name):
    with pytest.raises(ValueError):
        validate_build_selection("internal-test", config(tmp_path, profile), environment={name: "foreign"})


def test_profile_file_and_selection_fail_closed(tmp_path, profile):
    for mode, path in [("internal-test", None), ("unknown", None), ("product", config(tmp_path, profile))]:
        with pytest.raises(ValueError):
            validate_build_selection(mode, path, environment={})
    link = tmp_path / "link.json"; link.symlink_to(config(tmp_path, profile))
    with pytest.raises(ValueError):
        validate_build_selection("internal-test", link, environment={})


def test_services_accounts_installation_and_update_adapter_are_bound(profile, monkeypatch):
    env = {"JKM_MACOS_SECURITY_BRIDGE": "/foreign", "JENAPLAN_RESTART_ROOT": "/foreign", "HOME": "/session"}
    identity.activate_test_identity(profile, arguments=[], environment=env)
    assert env["JENAPLAN_APP_DATA_DIR"] == profile["runtime_root"]
    assert "JKM_MACOS_SECURITY_BRIDGE" not in env and "JENAPLAN_RESTART_ROOT" not in env
    from src.security.infrastructure.data_master_key_store import _data_master_key_account
    from src.security.infrastructure.platform_auth import _account
    for suffix in identity.SERVICES:
        assert identity.keychain_service(identity.PRODUCT_BUNDLE_ID + "." + suffix).decode() in profile["keychain_services"]
    key_id = str(uuid.uuid4())
    for port in (_account, _data_master_key_account):
        assert port(profile["installation_id"], key_id).decode().startswith(profile["account_prefix"] + ":")
        with pytest.raises(ValueError):
            port(str(uuid.uuid4()), key_id)
    from src.security.infrastructure.monotonic_anchor_store import MacOSMonotonicSecurityAnchorStore
    store = object.__new__(MacOSMonotonicSecurityAnchorStore)
    store._installation_id = profile["installation_id"]; store._database_context_id = key_id
    assert store._service.decode() == profile["keychain_services"][2]
    assert store._account.decode().startswith(profile["account_prefix"] + ":")
    store._installation_id = str(uuid.uuid4())
    with pytest.raises(ValueError):
        _ = store._account
    from src.updater.infrastructure.sparkle import build_native_update_adapter, MacOSSparkleAdapter
    monkeypatch.setattr("ctypes.CDLL", Mock(side_effect=AssertionError("no native loading")))
    assert build_native_update_adapter().available is False
    with pytest.raises(RuntimeError):
        MacOSSparkleAdapter(Path("/foreign"))
    from src.desktop_app.runtime import application_data_root
    assert application_data_root(environ={"JENAPLAN_APP_DATA_DIR": "/foreign"}) == Path(profile["runtime_root"])


@pytest.mark.parametrize("arguments", [
    ["--runtime-root", "/foreign"], ["--packaged-cipher-seed", "/foreign"],
    ["--packaged-keychain-smoke", "initialize"], ["--packaged-smoke-test", "unknown"],
    ["--final-v4-restore-confirm", "--runtime-root", "/foreign"],
    ["--restore-worker", "--handoff", "/foreign/restore-handoffs/id.json", "--restore-mode", "final_v4_encrypted"],
    ["--final-v4-restore-confirm", "--runtime-root", "x", "--runtime-root", "y"],
])
def test_foreign_worker_restart_and_tool_arguments_rejected(profile, arguments):
    with pytest.raises(ValueError):
        identity.activate_test_identity(profile, arguments=arguments, environment={})
    assert identity.test_identity() is None


@pytest.mark.parametrize("entry", ["worker", "restart", "smoke"])
def test_same_profile_reentered_by_each_process(profile, entry):
    arguments = {
        "worker": ["--restore-worker", "--handoff", profile["runtime_root"] + "/restore-handoffs/id.json",
                   "--nonce=-nonce", "--restore-mode", "final_v4_encrypted"],
        "restart": ["--final-v4-restore-confirm", "--runtime-root", profile["runtime_root"]],
        "smoke": ["--packaged-smoke-test", "restart"],
    }[entry]
    identity.activate_test_identity(profile, arguments=arguments, environment={})
    assert identity.test_identity().installation_id == profile["installation_id"]
    with pytest.raises(ValueError):
        identity.activate_test_identity(profile, arguments=arguments, environment={})


def test_foreign_env_and_descendant_links_stop_before_context_activation(profile):
    with pytest.raises(ValueError):
        identity.activate_test_identity(profile, arguments=[], environment={"JENAPLAN_APP_DATA_DIR": "/foreign"})
    (Path(profile["runtime_root"]) / "instance.lock").symlink_to("/foreign")
    with pytest.raises(ValueError):
        identity.activate_test_identity(profile, arguments=[], environment={})
    assert identity.test_identity() is None


def test_real_builder_preflight_has_no_build_side_effects(tmp_path, profile):
    path = config(tmp_path, profile)
    command = ["bash", "scripts/build_macos_pilot.sh", "--package-profile", "internal-test", "--test-profile", str(path)]
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("JENAPLAN_", "MACOS_SIGN", "MACOS_NOTAR"))}
    result = subprocess.run(command + ["--validate-profile-only"], env=environment, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["bundle_id"] == profile["bundle_id"]
    bad = dict(profile, bundle_id=identity.PRODUCT_BUNDLE_ID); path.write_text(json.dumps(bad))
    result = subprocess.run(command, env=environment, text=True, capture_output=True)
    assert result.returncode == 2 and "test_profile_invalid" in result.stderr
    assert not Path(profile["build_root"]).exists() and not Path(profile["dist_root"]).exists()
    result = subprocess.run(["bash", "scripts/build_macos_pilot.sh", "--validate-profile-only"],
                            env=environment, text=True, capture_output=True)
    assert result.returncode == 0
    assert json.loads(result.stdout)["bundle_id"] == identity.PRODUCT_BUNDLE_ID


def test_sealed_hook_contains_complete_literal_and_no_product_fallback(profile):
    validated = identity.validate_test_profile(profile)
    Path(profile["build_root"]).mkdir()
    prepare_hook(validated)
    hook = Path(profile["build_root"]) / "internal_test_hook.py"
    code = hook.read_text()
    assert "run_test_package_hook" in code and profile["installation_id"] in code
    with pytest.raises(FileExistsError):
        prepare_hook(validated)
    with pytest.raises(SystemExit) as error:
        identity.run_test_package_hook(profile)
    assert error.value.code == 2


def test_duplicate_json_and_boolean_alias_are_rejected(tmp_path, profile):
    path = config(tmp_path, profile)
    path.write_text(path.read_text().replace('{', '{"updates": false,', 1))
    with pytest.raises(ValueError):
        validate_build_selection("internal-test", path, environment={})
    profile["updates"] = 0
    with pytest.raises(ValueError):
        identity.validate_test_profile(profile)


def test_snapshot_digest_and_missing_or_tampered_hook_fail_closed(tmp_path, profile):
    path = config(tmp_path, profile)
    with pytest.raises(ValueError):
        validate_build_selection("internal-test", path, environment={"JENAPLAN_INTERNAL_TEST_PROFILE_DIGEST": "wrong"})
    validated = identity.validate_test_profile(profile)
    Path(profile["build_root"]).mkdir()
    with pytest.raises(FileNotFoundError):
        verify_prepared_hook(validated)
    prepare_hook(validated)
    verify_prepared_hook(validated)
    (Path(profile["build_root"]) / "internal_test_hook.py").write_text("# missing guard\n")
    with pytest.raises(ValueError):
        verify_prepared_hook(validated)


def test_payload_rejects_profile_before_first_write(tmp_path, profile):
    from scripts.prepare_macos_pilot_payload import prepare_payload
    path = config(tmp_path, dict(profile, bundle_id=identity.PRODUCT_BUNDLE_ID))
    output = tmp_path / "never-created"
    with pytest.raises(ValueError):
        prepare_payload(output, data_mode="empty", version="0.4.4", git_commit="synthetic",
                        source_tree_state="clean", architecture="arm64", test_profile=path)
    assert not output.exists()


@pytest.mark.parametrize("damage", ["none", "bundle", "digest", "feed", "config", "moved"])
def test_frozen_hook_attests_metadata_without_creating_app(profile, monkeypatch, damage):
    """Mock immutable bundle reads only; this is not a native package proof."""
    import plistlib
    executable = Path(profile["dist_root"]) / (profile["app_name"] + ".app") / "Contents/MacOS" / profile["app_name"]
    info = dict(CFBundleIdentifier=profile["bundle_id"], CFBundleExecutable=profile["app_name"],
                JKMInternalTestProfileSHA256=profile_digest(identity.validate_test_profile(profile)))
    if damage == "bundle": info["CFBundleIdentifier"] = identity.PRODUCT_BUNDLE_ID
    if damage == "digest": info["JKMInternalTestProfileSHA256"] = "wrong"
    if damage == "feed": info["SUFeedURL"] = "https://foreign.example"
    read_bytes, read_text, resolve = Path.read_bytes, Path.read_text, Path.resolve
    monkeypatch.setattr(Path, "read_bytes", lambda p: plistlib.dumps(info) if p.name == "Info.plist" else read_bytes(p))
    monkeypatch.setattr(Path, "read_text", lambda p, *a, **kw: json.dumps(dict(profile, updates=0) if damage == "config" else profile)
                        if p.name == "internal_test_profile.json" else read_text(p, *a, **kw))
    monkeypatch.setattr(Path, "resolve", lambda p, *a, **kw: p if p == executable else resolve(p, *a, **kw))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable) if damage != "moved" else "/foreign/executable")
    monkeypatch.setattr(sys, "argv", [str(executable)])
    monkeypatch.setattr(os, "environ", {})
    if damage == "none":
        identity.run_test_package_hook(profile)
        assert identity.test_identity().bundle_id == profile["bundle_id"]
    else:
        with pytest.raises(SystemExit) as error:
            identity.run_test_package_hook(profile)
        assert error.value.code == 2
        assert identity.test_identity() is None
    assert not Path(profile["dist_root"]).exists()


@pytest.mark.parametrize("enrollment", ["enroll_local_account", "prepare_local_account_enrollment"])
def test_enrollment_factory_only_changes_installation_id(profile, monkeypatch, enrollment):
    from src.security import startup
    from src.security.infrastructure.platform_auth import UnsupportedDeviceSecretStore, UnsupportedLocalDeviceAuthenticator
    from src.desktop_app.runtime import runtime_paths
    monkeypatch.setattr(startup, "build_platform_authentication_adapters", lambda: (
        UnsupportedDeviceSecretStore(), UnsupportedLocalDeviceAuthenticator(),
    ))
    identity.activate_test_identity(profile, arguments=[], environment={})
    runtime = startup.build_security_runtime(runtime_paths(Path(profile["runtime_root"])))
    enrolled = getattr(runtime.service, enrollment)("Synthetische lange Passphrase 2026!")
    assert enrolled.installation_id == profile["installation_id"]
    assert len({enrolled.installation_id, enrolled.user_id, enrolled.recovery_set_id}) == 3
    assert runtime.repository.load_account().installation_id == profile["installation_id"]


def test_spec_product_and_test_profile_use_same_security_basis(tmp_path, profile, monkeypatch):
    """Execute actual spec with inert PyInstaller constructors; create no App."""
    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, "distribution", lambda _: SimpleNamespace(
        files=["licenses/LICENSE", "licenses/licenses/LICENSE.libsodium.txt"],
        locate_file=lambda _: Path(__file__),
    ))
    for name in ("JENAPLAN_PILOT_PAYLOAD_DIR", "JENAPLAN_MACOS_ICON", "JENAPLAN_MACOS_SECURITY_BRIDGE",
                 "JENAPLAN_MACOS_SPARKLE_BRIDGE", "JENAPLAN_SPARKLE_FRAMEWORK", "JENAPLAN_SPARKLE_LICENSE",
                 "JENAPLAN_PILOT_FIRST_STEPS_PDF"):
        monkeypatch.setenv(name, str(tmp_path / name))
    monkeypatch.setenv("JENAPLAN_PILOT_APPCAST_URL", "https://synthetic.example/appcast")
    monkeypatch.delenv("JENAPLAN_INTERNAL_TEST_PROFILE", raising=False)
    constructors = {name: Mock(return_value=SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[]))
                    for name in ("Analysis", "PYZ", "EXE", "COLLECT", "BUNDLE")}
    def run():
        return runpy.run_path("packaging/macos_pilot.spec", init_globals={"SPECPATH": str(Path("packaging").resolve()), **constructors})
    monkeypatch.setenv("JENAPLAN_PACKAGE_PROFILE", "product")
    product = run()
    assert constructors["BUNDLE"].call_args.kwargs["bundle_identifier"] == identity.PRODUCT_BUNDLE_ID
    assert constructors["Analysis"].call_args.kwargs["runtime_hooks"] == []
    assert constructors["BUNDLE"].call_args.kwargs["info_plist"]["SUFeedURL"].startswith("https:")
    monkeypatch.delenv("JENAPLAN_PILOT_APPCAST_URL")
    monkeypatch.setenv("JENAPLAN_PACKAGE_PROFILE", "internal-test")
    monkeypatch.setenv("JENAPLAN_INTERNAL_TEST_PROFILE", str(config(tmp_path, profile)))
    validated = identity.validate_test_profile(profile)
    Path(profile["build_root"]).mkdir()
    prepare_hook(validated)
    monkeypatch.setenv("JENAPLAN_INTERNAL_TEST_PROFILE_DIGEST", profile_digest(validated))
    run()
    bundle = constructors["BUNDLE"].call_args.kwargs
    analysis = constructors["Analysis"].call_args.kwargs
    assert bundle["bundle_identifier"] == profile["bundle_id"]
    assert bundle["name"] == profile["app_name"] + ".app"
    assert not any(k.startswith("SU") for k in bundle["info_plist"])
    assert bundle["info_plist"]["JKMInternalTestProfileSHA256"] == profile_digest(validated)
    assert analysis["runtime_hooks"] == [profile["build_root"] + "/internal_test_hook.py"]
    assert analysis["binaries"] == [(str(tmp_path / "JENAPLAN_MACOS_SECURITY_BRIDGE"), ".")]
    assert bundle["info_plist"]["CFBundleVersion"] == "404"
    assert bundle["info_plist"]["CFBundleShortVersionString"] == "0.4.4"
    assert "sqlcipher3._sqlite3" in analysis["hiddenimports"]
    assert product["TEST_PROFILE"] is None


# Path acceptance tests use real filesystem identities, never a packaged app.
def checked_paths(profile, snapshot=None, digest=None):
    from scripts.macos_package_profile import validate_test_build_paths
    validated = identity.validate_test_profile(profile)
    validate_test_build_paths(
        validated,
        expected_identity=identity.test_build_path_identity(validated) if snapshot is None else snapshot,
        expected_digest=profile_digest(validated) if digest is None else digest,
    )


def test_system_temp_alias_is_same_directory_and_preserves_sealed_digest(profile, monkeypatch):
    canonical = Path(tempfile.gettempdir()).resolve()
    raw = Path(tempfile.gettempdir())
    assert raw.samefile(canonical)
    assert (raw.stat().st_dev, raw.stat().st_ino) == (canonical.stat().st_dev, canonical.stat().st_ino)
    validated = identity.validate_test_profile(profile)
    digest = profile_digest(validated)
    snapshot = identity.test_build_path_identity(validated)
    for spelling in (str(raw), str(canonical)):
        monkeypatch.setattr(identity.tempfile, "gettempdir", lambda: spelling)
        checked_paths(profile, snapshot, digest)
        assert profile_digest(identity.validate_test_profile(profile)) == digest
    assert not Path(profile["build_root"]).exists()


@pytest.mark.parametrize("damage", ["different", "missing", "file", "relative", "symlink", "permissions"])
def test_temp_authority_and_existing_directory_identity_fail_closed(tmp_path, profile, monkeypatch, damage):
    target = tmp_path / "authority"
    if damage in {"different", "permissions"}:
        target.mkdir(mode=0o700)
        if damage == "permissions": target.chmod(0o777)
    elif damage == "file":
        target.write_text("file")
    elif damage == "relative":
        target = Path("relative")
    elif damage == "symlink":
        target.symlink_to(Path(tempfile.gettempdir()).resolve(), target_is_directory=True)
    monkeypatch.setattr(identity.tempfile, "gettempdir", lambda: str(target))
    with pytest.raises((ValueError, OSError)):
        checked_paths(profile)
    assert not Path(profile["build_root"]).exists()


@pytest.mark.parametrize("target", ["container", "data"])
def test_replaced_real_directory_identity_is_detected(profile, target):
    validated = identity.validate_test_profile(profile)
    snapshot = identity.test_build_path_identity(validated)
    path = Path(profile["runtime_root"])
    if target == "container": path = path.parent
    old = path.with_name(path.name + "-retained")
    path.rename(old)
    import shutil
    try:
        shutil.copytree(old, path)
        path.chmod(0o700)
        # Identical contents and strings are insufficient; real inode changed.
        assert not path.samefile(old)
        with pytest.raises(ValueError, match="test_profile_invalid"):
            checked_paths(profile, snapshot)
    finally:
        shutil.rmtree(path)
        old.rename(path)


def test_parent_symlink_cannot_replace_private_container(profile):
    container = Path(profile["runtime_root"]).parent
    old = container.with_name(container.name + "-retained")
    container.rename(old)
    container.symlink_to(old, target_is_directory=True)
    try:
        with pytest.raises(ValueError): checked_paths(profile)
    finally:
        container.unlink()
        old.rename(container)


@pytest.mark.parametrize("entry", ["directory", "file", "symlink"])
def test_existing_build_target_never_adopted(profile, entry):
    path = Path(profile["build_root"])
    if entry == "directory": path.mkdir(mode=0o700)
    elif entry == "file": path.write_text("file")
    else: path.symlink_to(Path(profile["runtime_root"]), target_is_directory=True)
    with pytest.raises(ValueError): checked_paths(profile)
    assert not Path(profile["dist_root"]).exists()


@pytest.mark.parametrize("field,value", [
    ("runtime_root", "/Applications/Jenaplan-Kompetenzmanager.app"),
    ("build_root", str(Path("build/macos-pilot").resolve())),
    ("dist_root", str(Path("dist/macos").resolve())),
    ("runtime_root", "relative/data"),
])
def test_product_or_foreign_paths_cannot_enter_shared_gate(profile, field, value):
    profile[field] = value
    with pytest.raises(ValueError): checked_paths(profile)


def test_shared_gate_rejects_digest_and_missing_snapshot(profile):
    with pytest.raises(ValueError): checked_paths(profile, digest="tampered")
    with pytest.raises(ValueError): checked_paths(profile, snapshot=[])


def test_real_builder_negative_preflight_never_reaches_buildwrite(tmp_path, profile):
    path = config(tmp_path, profile)
    command = ["bash", "scripts/build_macos_pilot.sh", "--package-profile", "internal-test",
               "--test-profile", str(path), "--validate-profile-only"]
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("JENAPLAN_", "MACOS_SIGN", "MACOS_NOTAR"))}
    for changes in ({"dist_root": str(Path("dist/macos").resolve())}, {"runtime_root": "relative"}, {}):
        path.write_text(json.dumps(dict(profile, **changes)))
        env = dict(environment)
        if not changes: env["JENAPLAN_INTERNAL_TEST_PROFILE_DIGEST"] = "tampered"
        result = subprocess.run(command, env=env, text=True, capture_output=True)
        assert result.returncode == 2 and "test_profile_invalid" in result.stderr
    assert not Path(profile["build_root"]).exists()
    assert not Path(profile["dist_root"]).exists()
    assert sorted(p.name for p in Path(profile["runtime_root"]).iterdir()) == [".jkm-runtime-root-v1"]


@pytest.fixture
def smoke_bundle(profile):
    # Inert files only: no executable code, PyInstaller, signing or native App.
    import plistlib
    app = Path(profile["dist_root"]) / (profile["app_name"] + ".app")
    exe = app / "Contents/MacOS" / profile["app_name"]
    exe.parent.mkdir(parents=True, mode=0o700)
    exe.write_text("inert")
    resources = app / "Contents/Resources"
    resources.mkdir(mode=0o700)
    validated = identity.validate_test_profile(profile, before_build=False)
    (resources / "internal_test_profile.json").write_text(json.dumps(profile))
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps(dict(
        CFBundleIdentifier=profile["bundle_id"], CFBundleExecutable=profile["app_name"],
        JKMInternalTestProfileSHA256=profile_digest(validated),
    )))
    return app, exe, validated


def test_smoke_uses_activated_sealed_root_without_legacy_prefix(profile, smoke_bundle, monkeypatch):
    from src.desktop_app import main as desktop
    app, exe, validated = smoke_bundle
    environment = {}
    identity.activate_test_identity(profile, arguments=["--packaged-smoke-test", "initialize"], environment=environment)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    monkeypatch.setattr(sys, "argv", [str(exe), "--packaged-smoke-test", "initialize"])
    assert desktop._validated_packaged_smoke_data_root(environment) == Path(profile["runtime_root"])
    assert identity.keychain_service(identity.PRODUCT_BUNDLE_ID + ".data-master-key").decode() == profile["keychain_services"][0]
    assert profile["worker_bundle_id"] == profile["restart_bundle_id"] == profile["bundle_id"]


@pytest.mark.parametrize("damage", ["missing", "tamper", "digest", "installation", "bundle", "service", "old_snapshot", "worker", "restart"])
def test_smoke_preflight_snapshot_damage_stops_before_any_app_access(tmp_path, profile, smoke_bundle, monkeypatch, damage):
    import plistlib
    from scripts import smoke_test_macos_app as runner
    app, exe, validated = smoke_bundle
    path = config(tmp_path, profile)
    config_path = app / "Contents/Resources/internal_test_profile.json"
    if damage == "missing": config_path.unlink()
    elif damage == "digest":
        f = app / "Contents/Info.plist"
        data = plistlib.loads(f.read_bytes()); data["JKMInternalTestProfileSHA256"] = "invalid"
        f.write_bytes(plistlib.dumps(data))
    else:
        data = dict(profile)
        field, value = {
            "tamper": ("updates", True), "installation": ("installation_id", str(uuid.uuid4())),
            "bundle": ("bundle_id", identity.PRODUCT_BUNDLE_ID),
            "service": ("keychain_services", [identity.PRODUCT_BUNDLE_ID + ".data-master-key"]),
            "old_snapshot": ("test_id", str(uuid.uuid4())),
            "worker": ("worker_bundle_id", identity.PRODUCT_BUNDLE_ID),
            "restart": ("restart_bundle_id", identity.PRODUCT_BUNDLE_ID),
        }[damage]
        data[field] = value; config_path.write_text(json.dumps(data))
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **kw: pytest.fail("preflight must not launch any process"))
    with pytest.raises((ValueError, OSError)):
        runner.smoke_test(app, test_profile=path, preflight_only=True)
    assert sorted(x.name for x in Path(profile["runtime_root"]).iterdir()) == [".jkm-runtime-root-v1"]


@pytest.mark.parametrize("root", ["/Applications/Jenaplan-Kompetenzmanager.app", "/tmp/arbitrary", "relative", "/tmp/jenaplan-packaged-smoke-unbound", None])
def test_active_smoke_never_falls_back_to_foreign_or_legacy_root(profile, smoke_bundle, monkeypatch, root):
    from src.desktop_app import main as desktop
    app, exe, validated = smoke_bundle
    env = {}; identity.activate_test_identity(profile, arguments=[], environment=env)
    env["JENAPLAN_APP_DATA_DIR"] = root
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    monkeypatch.setattr(sys, "argv", [str(exe), "--packaged-smoke-test", "initialize"])
    with pytest.raises(desktop.RuntimeStorageError): desktop._validated_packaged_smoke_data_root(env)


@pytest.mark.parametrize("arguments", [
    ["--packaged-smoke-test"], ["--packaged-smoke-test", "unknown"],
    ["--restore-worker", "--handoff", "/foreign/id.json", "--restore-mode", "final_v4_encrypted"],
    ["--final-v4-restore-confirm", "--runtime-root", "/foreign"],
])
def test_smoke_preflight_rejects_ambiguous_worker_restart_arguments(profile, smoke_bundle, arguments):
    app, exe, validated = smoke_bundle
    with pytest.raises(ValueError):
        identity.validate_internal_test_smoke_context(validated, executable=exe,
            root=profile["runtime_root"], arguments=arguments)


def test_read_only_preflight_rechecks_process_context_and_directory_identity(tmp_path, profile, smoke_bundle, monkeypatch):
    from scripts import smoke_test_macos_app as runner
    app, exe, validated = smoke_bundle
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **kw: pytest.fail("unexpected process launch"))
    report = runner.smoke_test(app, test_profile=config(tmp_path, profile), preflight_only=True)
    assert report["status"] == "preflight_ok" and report["app_started"] is False
    snapshot = identity.test_build_path_identity(validated)
    root = Path(profile["runtime_root"]); old = root.with_name("data-retained")
    root.rename(old)
    from src.core.runtime_root_protection import prepare_synthetic_test_root
    try:
        prepare_synthetic_test_root(root)
        with pytest.raises(ValueError):
            identity.validate_internal_test_smoke_context(validated, executable=exe,
                root=str(root), arguments=["--packaged-smoke-test", "restart"], expected_identity=snapshot)
    finally:
        import shutil
        shutil.rmtree(root); old.rename(root)


@pytest.mark.parametrize("damage", ["unfrozen", "moved_executable", "link", "unsafe_parent", "missing_marker"])
def test_runtime_smoke_revalidates_frozen_package_and_root(profile, smoke_bundle, monkeypatch, damage):
    from src.desktop_app import main as desktop
    app, exe, validated = smoke_bundle
    env = {}; identity.activate_test_identity(profile, arguments=[], environment=env)
    monkeypatch.setattr(sys, "frozen", damage != "unfrozen", raising=False)
    monkeypatch.setattr(sys, "executable", "/Applications/Jenaplan-Kompetenzmanager.app/Contents/MacOS/Jenaplan-Kompetenzmanager" if damage == "moved_executable" else str(exe))
    monkeypatch.setattr(sys, "argv", [str(exe), "--packaged-smoke-test", "initialize"])
    root = Path(profile["runtime_root"])
    if damage == "link": (root / "link").symlink_to("/foreign")
    elif damage == "unsafe_parent": root.parent.chmod(0o777)
    elif damage == "missing_marker": (root / ".jkm-runtime-root-v1").unlink()
    with pytest.raises(desktop.RuntimeStorageError): desktop._validated_packaged_smoke_data_root(env)


def test_preflight_requires_explicit_profile_and_cannot_activate_from_environment(profile, smoke_bundle, monkeypatch):
    from scripts import smoke_test_macos_app as runner
    from src.desktop_app import main as desktop
    app, exe, validated = smoke_bundle
    monkeypatch.setenv("JENAPLAN_INTERNAL_TEST_PROFILE", "ignored")
    with pytest.raises(ValueError): runner.smoke_test(app, preflight_only=True)
    assert identity.test_identity() is None
    with pytest.raises(desktop.RuntimeStorageError):
        desktop._validated_packaged_smoke_data_root({"JENAPLAN_APP_DATA_DIR": profile["runtime_root"], "JENAPLAN_PACKAGED_SMOKE_MARKER": "isolated-v1"})



def test_external_preflight_rejects_inherited_foreign_root_before_bundle_or_launch(tmp_path, profile, smoke_bundle, monkeypatch):
    from scripts import smoke_test_macos_app as runner
    app, exe, validated = smoke_bundle
    monkeypatch.setenv("JENAPLAN_APP_DATA_DIR", "/foreign")
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **kw: pytest.fail("unauthorized process"))
    with pytest.raises(ValueError):
        runner.smoke_test(app, test_profile=config(tmp_path, profile), preflight_only=True)


def test_context_rejects_foreign_parameters_before_package_reads(profile, smoke_bundle, monkeypatch):
    app, exe, validated = smoke_bundle
    monkeypatch.setattr(identity, "verify_test_package", lambda *a: pytest.fail("foreign parameters must stop before package read"))
    with pytest.raises(ValueError):
        identity.validate_internal_test_smoke_context(validated, executable=exe, root="/foreign", arguments=[])
    with pytest.raises(ValueError):
        identity.validate_internal_test_smoke_context(validated, executable=exe, root=profile["runtime_root"], arguments=["--foreign"])
