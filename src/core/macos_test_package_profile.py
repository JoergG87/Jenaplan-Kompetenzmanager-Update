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
NATIVE_TEST_MODES = frozenset({
    "v7-prepare", "v7-weeks", "v7-weeks-reopen",
    "v6-seed", "v6-migrate", "v6-check", "v6-crash", "v6-matrix",
    "v6-subject-plants", "v6-functions", "v6-functions-reopen", "v6-negatives", "v6-migration-fault", "v6-migration-inspect",
    "initialize", "restart", "restart-denied", "cleanup", "existing-keys", "matrix", "hold-lock", "acl-preflight",
    "restore-worker", "restore-ready", "restore-parent-exit",
    "restore-crash-before_swap", "restore-crash-between_main_and_companion",
    "restore-crash-after_databases_before_documents", "restore-crash-during_documents",
    "restore-crash-after_swap_before_reopen", "restore-crash-after_reopen",
})


def _reject():
    raise ValueError("test_profile_invalid")


def _directory_identity(path):
    """Walk canonical absolute directories without following any path links."""
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        _reject()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    identities = []
    try:
        for component in path.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            value = os.fstat(fd)
            identities.append((value.st_dev, value.st_ino))
        value = os.fstat(fd)
        if (not stat.S_ISDIR(value.st_mode) or value.st_uid != os.getuid()
                or value.st_mode & 0o077):
            _reject()
        return identities
    finally:
        os.close(fd)


def canonical_test_temp_root():
    """Resolve only the OS temp authority, never an untrusted profile path.

    The OS /var alias is verified by file identity. Canonical descendants are
    still opened with NOFOLLOW; this grants no authority to arbitrary links.
    """
    raw = Path(tempfile.gettempdir())
    if not raw.is_absolute() or ".." in raw.parts:
        _reject()
    canonical = raw.resolve(strict=True)
    if raw != canonical:
        # Only root-owned macOS system aliases may spell the OS temp authority
        # differently. Do not authorize a user-created temp/parent symlink.
        aliases = {"/var": "/private/var", "/tmp": "/private/tmp"}
        alias = Path("/" + raw.parts[1])
        target = aliases.get(str(alias))
        metadata = alias.lstat()
        if (target is None or not stat.S_ISLNK(metadata.st_mode)
                or metadata.st_uid != 0 or str(alias.parent / os.readlink(alias)) != target
                or Path(target).joinpath(*raw.parts[2:]) != canonical):
            _reject()
    if not raw.samefile(canonical):
        _reject()
    _directory_identity(canonical)
    return canonical


def test_build_path_identity(profile):
    """Ephemeral ancestor identities, separate from the sealed profile format.

    Rechecks detect observed replacement, not arbitrary same-user ABA or a
    race after the last check; they are not an OS sandbox or a write lease.
    """
    temp = canonical_test_temp_root()
    container = Path(profile.runtime_root).parent
    if container.parent != temp:
        _reject()
    return [_directory_identity(path) for path in
            (temp, container, Path(profile.runtime_root))]


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
        if container.parent != canonical_test_temp_root():
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
        test_build_path_identity(expected)
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
_test_path_identity = None


def test_identity():
    return _test_identity


def activate_test_identity(payload, *, arguments, environment):
    """Hook boundary used anew by normal launch, worker and restart."""
    global _test_identity, _test_path_identity
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
    path_identity = test_build_path_identity(profile)
    # Keep OS session and bootloader values; discard app/dev loader overrides.
    for name in tuple(environment):
        if name.startswith(("JENAPLAN_", "JKM_", "DYLD_", "PYTHON", "QT_")):
            environment.pop(name)
    environment["JENAPLAN_APP_DATA_DIR"] = profile.runtime_root
    environment["JENAPLAN_PACKAGED_SMOKE_MARKER"] = "isolated-v1"
    _test_identity = profile
    _test_path_identity = path_identity
    return profile


def _validate_arguments(profile, arguments):
    import argparse
    if (len(arguments) == 2 and arguments[0] == "--internal-native-test"
            and arguments[1] in NATIVE_TEST_MODES):
        return
    if not arguments or arguments == ["--packaged-runtime-audit"]:
        return
    if (len(arguments) == 2 and arguments[0] == "--packaged-smoke-test"
            and arguments[1] in {"initialize", "restart", "cleanup", "restore-worker",
                                 "restore-ready", "restore-parent-exit"}):
        return
    parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    parser.add_argument("--restore-worker", action="store_true")
    parser.add_argument("--final-v4-restore-confirm", action="store_true")
    parser.add_argument("--synthetic-v6-restore-confirm", action="store_true")
    parser.add_argument("--synthetic-v7-restore-confirm", action="store_true")
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
    if unknown or sum((args.restore_worker, args.final_v4_restore_confirm,
                       args.synthetic_v6_restore_confirm, args.synthetic_v7_restore_confirm)) != 1:
        _reject()
    if args.restore_worker:
        if args.restore_mode not in {"final_v4_encrypted", "synthetic_v6_encrypted", "synthetic_v7_encrypted"} or not args.handoff:
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


def verify_test_package(profile, executable):
    """Read-only attestation shared by hook, smoke and external preflight."""
    import json
    import plistlib
    import hashlib
    profile = validate_test_profile(profile.as_dict(), before_build=False)
    executable = Path(executable)
    app = Path(profile.dist_root) / f"{profile.app_name}.app"
    if executable != app / "Contents" / "MacOS" / profile.app_name or executable.resolve(strict=True) != executable:
        _reject()
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    digest = hashlib.sha256(json.dumps(profile.as_dict(), sort_keys=True).encode()).hexdigest()
    if (info.get("CFBundleIdentifier") != profile.bundle_id
            or info.get("CFBundleExecutable") != profile.app_name
            or info.get("JKMInternalTestProfileSHA256") != digest
            or any(k.startswith("SU") for k in info)):
        _reject()
    config = app / "Contents/Resources/internal_test_profile.json"
    if config.is_symlink() or json.dumps(json.loads(config.read_text()), sort_keys=True) != json.dumps(profile.as_dict(), sort_keys=True):
        _reject()


def validate_internal_test_smoke_context(profile, *, executable, root, arguments,
                                         expected_identity=None):
    """Authorize only the sealed root, never a temporary-name prefix.

    The external read-only runner can inspect this contract without activating
    runtime identity; the app must already have entered through its frozen hook.
    """
    profile = validate_test_profile(profile.as_dict(), before_build=False)
    if root != profile.runtime_root:
        _reject()
    _validate_arguments(profile, arguments)
    snapshot = test_build_path_identity(profile)
    if expected_identity is not None and snapshot != expected_identity:
        _reject()
    verify_test_package(profile, executable)
    for directory, folders, files in os.walk(root, followlinks=False, onerror=lambda _: _reject()):
        for name in (*folders, *files):
            value = (Path(directory) / name).lstat()
            if (not (stat.S_ISDIR(value.st_mode) or stat.S_ISREG(value.st_mode))
                    or value.st_uid != os.getuid() or value.st_mode & 0o022
                    or stat.S_ISREG(value.st_mode) and value.st_nlink != 1):
                _reject()
    if snapshot != test_build_path_identity(profile):
        _reject()
    return Path(root)


def active_internal_test_smoke_root(environment, arguments):
    """Frozen app entry; absence or contradiction never selects legacy mode."""
    import sys
    profile = test_identity()
    if (profile is None or not getattr(sys, "frozen", False)
            or _test_path_identity is None
            or environment.get("JENAPLAN_PACKAGED_SMOKE_MARKER") != "isolated-v1"):
        _reject()
    return validate_internal_test_smoke_context(
        profile, executable=sys.executable, root=environment.get("JENAPLAN_APP_DATA_DIR"),
        arguments=arguments, expected_identity=_test_path_identity,
    )


def run_test_package_hook(payload):
    """Frozen-only bootstrap; missing/moved/contradictory context has no fallback."""
    import json
    import sys
    try:
        if not getattr(sys, "frozen", False):
            _reject()
        profile = validate_test_profile(payload, before_build=False)
        verify_test_package(profile, sys.executable)
        arguments = sys.argv[1:]
        if arguments == ["--packaged-test-profile-audit"]:
            activate_test_identity(payload, arguments=[], environment=os.environ)
            print(json.dumps(profile.as_dict(), sort_keys=True), flush=True)
            raise SystemExit(0)
        activate_test_identity(payload, arguments=arguments, environment=os.environ)
    except (OSError, ValueError, TypeError):
        print("Isolierter Teststart gesperrt.", file=sys.stderr)
        raise SystemExit(2)
