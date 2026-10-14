"""Non-secret package identity contract; no database, Keychain or build writes.

Only a sealed, explicitly selected PyInstaller hook activates this context.
Ordinary product/source executions never select it from environment variables.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import stat
import tempfile
from uuid import UUID

from src.core.runtime_root_protection import inspect_runtime_root, RuntimeRootKind, RuntimeRootProtectionError

PRODUCT_BUNDLE_ID = "de.jenaplan.kompetenzmanager"
PRODUCT_APP_NAME = "Jenaplan-Kompetenzmanager"
SERVICES = ("data-master-key", "device-credential", "monotonic-security-anchor")


def _reject():
    raise ValueError("test_profile_invalid")


def _uuid(value):
    try:
        parsed = UUID(value)
        if parsed.version != 4 or str(parsed) != value:
            _reject()
        return parsed
    except (TypeError, ValueError, AttributeError):
        _reject()


@dataclass(frozen=True)
class MacOSTestPackageProfile:
    test_id: str
    installation_id: str
    bundle_id: str
    app_name: str
    runtime_root: str
    build_root: str
    dist_root: str
    keychain_services: tuple[str, ...]
    account_prefix: str

    def as_dict(self):
        return dict(
            profile="internal-test", test_id=self.test_id,
            installation_id=self.installation_id, bundle_id=self.bundle_id,
            app_name=self.app_name, runtime_root=self.runtime_root,
            build_root=self.build_root, dist_root=self.dist_root,
            keychain_services=list(self.keychain_services), account_prefix=self.account_prefix,
            worker_bundle_id=self.bundle_id, restart_bundle_id=self.bundle_id,
            updates=False, signing="ad-hoc", entitlements=None,
        )


def validate_test_profile(payload, *, before_build=True):
    """Exact identities plus real private synthetic root, without creating files."""
    try:
        test_id = payload["test_id"]
        token = _uuid(test_id).hex
        installation = payload["installation_id"]
        _uuid(installation)
        if installation == test_id:
            _reject()
        bundle = f"{PRODUCT_BUNDLE_ID}.internaltest.t{token}"
        container = Path(payload["runtime_root"]).parent
        if container.parent != Path(tempfile.gettempdir()).resolve():
            _reject()
        if container.name != f"jkm-internal-test-{token}":
            _reject()
        expected = MacOSTestPackageProfile(
            test_id, installation, bundle, f"JKM-Interner-Test-{token}",
            str(container / "data"), str(container / "build"), str(container / "artifacts"),
            tuple(f"{bundle}.{suffix}" for suffix in SERVICES), f"test-v1:{test_id}",
        )
        import json
        if json.dumps(payload, sort_keys=True) != json.dumps(expected.as_dict(), sort_keys=True):
            _reject()
        for path in (container, Path(expected.runtime_root)):
            value = path.lstat()
            if (path.resolve(strict=True) != path or not stat.S_ISDIR(value.st_mode)
                    or value.st_uid != os.getuid() or value.st_mode & 0o077):
                _reject()
        protection = inspect_runtime_root(Path(expected.runtime_root))
        if protection is None or protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
            _reject()
        for name in (expected.build_root, expected.dist_root):
            path = Path(name)
            if path.exists() or path.is_symlink():
                value = path.lstat()
                if (path.resolve(strict=True) != path or not stat.S_ISDIR(value.st_mode)
                        or value.st_uid != os.getuid() or value.st_mode & 0o022):
                    _reject()
        if before_build:
            # The profile is not an authority to adopt existing artifact trees.
            for name in (expected.build_root, expected.dist_root):
                if Path(name).exists() or Path(name).is_symlink():
                    _reject()
            # Before packaging, only the existing synthetic authority is accepted.
            from src.core.runtime_root_protection import RUNTIME_ROOT_PROTECTION_MARKER
            if {p.name for p in Path(expected.runtime_root).iterdir()} != {RUNTIME_ROOT_PROTECTION_MARKER}:
                _reject()
        return expected
    except (OSError, KeyError, TypeError, ValueError, AttributeError, RuntimeRootProtectionError):
        _reject()


_test_identity: MacOSTestPackageProfile | None = None


def test_identity():
    return _test_identity


def activate_test_identity(payload, *, arguments, environment):
    """Hook boundary used anew by normal launch, worker and restart."""
    global _test_identity
    if _test_identity is not None:
        _reject()
    profile = validate_test_profile(payload, before_build=False)
    _validate_arguments(profile, arguments)
    root = Path(profile.runtime_root)
    # Reject foreign links/owners before product code or its lock can run.
    def scan_error(_error):
        _reject()
    for directory, folders, files in os.walk(root, followlinks=False, onerror=scan_error):
        for name in (*folders, *files):
            metadata = (Path(directory) / name).lstat()
            if (not (stat.S_ISDIR(metadata.st_mode) or stat.S_ISREG(metadata.st_mode))
                    or metadata.st_uid != os.getuid() or metadata.st_mode & 0o022
                    or stat.S_ISREG(metadata.st_mode) and metadata.st_nlink != 1):
                _reject()
    override = environment.get("JENAPLAN_APP_DATA_DIR")
    if override is not None and override != profile.runtime_root:
        _reject()
    # Keep OS session and bootloader values; discard app/dev loader overrides.
    for name in tuple(environment):
        if name.startswith(("JENAPLAN_", "JKM_", "DYLD_", "PYTHON", "QT_")):
            environment.pop(name)
    environment["JENAPLAN_APP_DATA_DIR"] = profile.runtime_root
    environment["JENAPLAN_PACKAGED_SMOKE_MARKER"] = "isolated-v1"
    _test_identity = profile
    return profile


def _validate_arguments(profile, arguments):
    import argparse
    if not arguments or arguments == ["--packaged-runtime-audit"]:
        return
    if (len(arguments) == 2 and arguments[0] == "--packaged-smoke-test"
            and arguments[1] in {"initialize", "restart", "cleanup", "restore-worker"}):
        return
    parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    parser.add_argument("--restore-worker", action="store_true")
    parser.add_argument("--final-v4-restore-confirm", action="store_true")
    for name in ("handoff", "nonce", "lock-fd", "ready-fd", "parent-lifetime-fd",
                 "restore-mode", "runtime-root", "restore-id", "restore-token", "restore-lock-fd"):
        parser.add_argument(f"--{name}")
    # Duplicated flags are ambiguous even if argparse would accept the last one.
    flags = [a.split("=", 1)[0] for a in arguments if a.startswith("--")]
    if len(flags) != len(set(flags)):
        _reject()
    try:
        args, unknown = parser.parse_known_args(arguments)
    except (argparse.ArgumentError, SystemExit):
        _reject()
    if unknown or args.restore_worker == args.final_v4_restore_confirm:
        _reject()
    if args.restore_worker:
        if args.restore_mode != "final_v4_encrypted" or not args.handoff:
            _reject()
        handoff = Path(args.handoff)
        if handoff.parent != Path(profile.runtime_root) / "restore-handoffs" or handoff.suffix != ".json":
            _reject()
        if args.runtime_root is not None:
            _reject()
    elif args.runtime_root != profile.runtime_root:
        _reject()


def keychain_service(product_service):
    profile = test_identity()
    if profile is None:
        return product_service.encode("ascii")
    suffix = product_service.removeprefix(PRODUCT_BUNDLE_ID + ".")
    if suffix not in SERVICES:
        _reject()
    return f"{profile.bundle_id}.{suffix}".encode("ascii")


def keychain_account(installation_id, item_id):
    profile = test_identity()
    prefix = "v1"
    if profile is not None:
        if installation_id != profile.installation_id:
            _reject()
        prefix = profile.account_prefix
    return f"{prefix}:{installation_id}:{item_id}".encode("ascii")


def run_test_package_hook(payload):
    """Frozen-only bootstrap; missing/moved/contradictory context has no fallback."""
    import json
    import plistlib
    import sys
    try:
        if not getattr(sys, "frozen", False):
            _reject()
        profile = validate_test_profile(payload, before_build=False)
        executable = Path(sys.executable)
        app = Path(profile.dist_root) / f"{profile.app_name}.app"
        if executable != app / "Contents" / "MacOS" / profile.app_name or executable.resolve(strict=True) != executable:
            _reject()
        info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
        import hashlib
        digest = hashlib.sha256(json.dumps(profile.as_dict(), sort_keys=True).encode()).hexdigest()
        if (info.get("CFBundleIdentifier") != profile.bundle_id
                or info.get("CFBundleExecutable") != profile.app_name
                or info.get("JKMInternalTestProfileSHA256") != digest
                or any(k.startswith("SU") for k in info)):
            _reject()
        config = app / "Contents/Resources/internal_test_profile.json"
        if config.is_symlink() or json.dumps(json.loads(config.read_text()), sort_keys=True) != json.dumps(profile.as_dict(), sort_keys=True):
            _reject()
        arguments = sys.argv[1:]
        if arguments == ["--packaged-test-profile-audit"]:
            activate_test_identity(payload, arguments=[], environment=os.environ)
            print(json.dumps(profile.as_dict(), sort_keys=True), flush=True)
            raise SystemExit(0)
        activate_test_identity(payload, arguments=arguments, environment=os.environ)
    except (OSError, ValueError, TypeError):
        print("Isolierter Teststart gesperrt.", file=sys.stderr)
        raise SystemExit(2)
