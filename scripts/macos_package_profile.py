"""Read-only pre-package gate and sealed test-hook preparation for one builder."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import stat

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.macos_test_package_profile import (
    PRODUCT_APP_NAME, PRODUCT_BUNDLE_ID, validate_test_profile,
    test_build_path_identity,
)


def load_profile(path, *, before_build=True):
    path = Path(path)
    value = path.lstat()
    if (path.is_symlink() or not stat.S_ISREG(value.st_mode) or value.st_uid != os.getuid()
            or value.st_mode & 0o022 or value.st_nlink != 1):
        raise ValueError("test_profile_invalid")
    return validate_test_profile(json.loads(path.read_text(), object_pairs_hook=_unique_keys), before_build=before_build)


def _unique_keys(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("test_profile_invalid")
        result[name] = value
    return result


def validate_build_selection(mode, path, *, environment=None, before_build=True):
    env = os.environ if environment is None else environment
    if mode == "product":
        if path:
            raise ValueError("test_profile_invalid")
        return None
    if mode != "internal-test" or not path:
        raise ValueError("test_profile_invalid")
    profile = load_profile(path, before_build=before_build)
    expected_digest = env.get("JENAPLAN_INTERNAL_TEST_PROFILE_DIGEST")
    if expected_digest is not None and expected_digest != profile_digest(profile):
        raise ValueError("test_profile_invalid")
    for name, value in env.items():
        if value and (name.startswith(("MACOS_SIGN", "MACOS_NOTAR", "JENAPLAN_NOTAR"))
                      or name in {"JENAPLAN_PILOT_APPCAST_URL", "JENAPLAN_MACOS_BUILD_ROOT", "JENAPLAN_MACOS_DIST_ROOT"}):
            raise ValueError("test_profile_invalid")
    return profile


def profile_digest(profile):
    return hashlib.sha256(json.dumps(profile.as_dict(), sort_keys=True).encode()).hexdigest()


def validate_test_build_paths(profile, *, expected_identity, expected_digest):
    """Same identity contract as profile validation, immediately before writes."""
    from src.core.runtime_root_protection import require_unprotected_output_path
    current = validate_test_profile(profile.as_dict())
    if expected_digest != profile_digest(current):
        raise ValueError("test_profile_invalid")
    observed = json.dumps(test_build_path_identity(current), sort_keys=True)
    if observed != json.dumps(expected_identity, sort_keys=True):
        raise ValueError("test_profile_invalid")
    for name in (current.build_root, current.dist_root):
        require_unprotected_output_path(Path(name))
    # Check again after protected-parent inspection, without creating targets.
    if observed != json.dumps(test_build_path_identity(current), sort_keys=True):
        raise ValueError("test_profile_invalid")


def prepare_hook(profile):
    """Only called after the pure gate, inside this profile's new buildroot."""
    root = Path(profile.build_root)
    hook = root / "internal_test_hook.py"
    config = root / "internal_test_profile.json"
    # Exclusive writes, never replace another profile or artifact.
    with hook.open("x") as output:
        output.write(hook_source(profile))
    with config.open("x") as output:
        json.dump(profile.as_dict(), output, sort_keys=True)


def hook_source(profile):
    return ("from src.core.macos_test_package_profile import run_test_package_hook\n"
            f"run_test_package_hook({profile.as_dict()!r})\n")


def verify_prepared_hook(profile):
    for filename in ("internal_test_hook.py", "internal_test_profile.json"):
        path = Path(profile.build_root) / filename
        metadata = path.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or metadata.st_mode & 0o022 or metadata.st_nlink != 1):
            raise ValueError("test_profile_invalid")
    if (Path(profile.build_root) / "internal_test_hook.py").read_text() != hook_source(profile):
        raise ValueError("test_profile_invalid")
    if load_profile(Path(profile.build_root) / "internal_test_profile.json", before_build=False) != profile:
        raise ValueError("test_profile_invalid")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-profile", choices=("product", "internal-test"), default="product")
    parser.add_argument("--test-profile")
    parser.add_argument("--field", choices=("app_name", "build_root", "dist_root", "digest", "path_identity"))
    parser.add_argument("--check-build-paths", action="store_true")
    parser.add_argument("--expected-path-identity")
    parser.add_argument("--expected-digest")
    parser.add_argument("--prepare-hook", action="store_true")
    args = parser.parse_args()
    try:
        profile = validate_build_selection(args.package_profile, args.test_profile,
                                          before_build=not args.prepare_hook)
        if args.expected_digest is not None and (profile is None or args.expected_digest != profile_digest(profile)):
            raise ValueError("test_profile_invalid")
        if args.check_build_paths:
            if profile is None:
                raise ValueError("test_profile_invalid")
            validate_test_build_paths(profile, expected_identity=json.loads(args.expected_path_identity),
                                      expected_digest=args.expected_digest)
        elif args.prepare_hook:
            if profile is None:
                raise ValueError("test_profile_invalid")
            prepare_hook(profile)
        elif args.field:
            if profile is None:
                raise ValueError("test_profile_invalid")
            if args.field == "path_identity":
                print(json.dumps(test_build_path_identity(profile), sort_keys=True))
            else:
                print(profile_digest(profile) if args.field == "digest" else getattr(profile, args.field))
        else:
            print(json.dumps(profile.as_dict() if profile else {
                "profile": "product", "bundle_id": PRODUCT_BUNDLE_ID, "app_name": PRODUCT_APP_NAME,
            }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError):
        print("test_profile_invalid", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
