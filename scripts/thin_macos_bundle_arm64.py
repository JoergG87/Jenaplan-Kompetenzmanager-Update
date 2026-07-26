"""Remove non-arm64 slices from Mach-O files in an internal macOS bundle."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def thin_bundle(root: Path) -> tuple[Path, ...]:
    root = Path(root)
    if not root.is_dir():
        raise RuntimeError("Bundle-Verzeichnis fehlt.")
    changed: list[Path] = []
    for path in sorted(
        item
        for item in root.rglob("*")
        if item.is_file() and not item.is_symlink()
    ):
        architectures = _architectures(path)
        if not architectures or architectures == ("arm64",):
            continue
        if "arm64" not in architectures:
            raise RuntimeError(
                f"Mach-O ohne arm64-Slice im Bundle: {path.name}"
            )
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.arm64-",
            dir=path.parent,
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            result = subprocess.run(
                [
                    "lipo",
                    str(path),
                    "-thin",
                    "arm64",
                    "-output",
                    str(temporary),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"arm64-Thinning fehlgeschlagen: {path.name}"
                )
            os.chmod(temporary, path.stat().st_mode & 0o777)
            temporary.replace(path)
            changed.append(path)
        finally:
            temporary.unlink(missing_ok=True)
    return tuple(changed)


def _architectures(path: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["file", "-b", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 or "Mach-O" not in result.stdout:
        return ()
    lipo = subprocess.run(
        ["lipo", "-archs", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if lipo.returncode != 0:
        raise RuntimeError(
            f"Mach-O-Architektur unlesbar: {path.name}"
        )
    return tuple(lipo.stdout.strip().split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    changed = thin_bundle(args.bundle)
    print(f"arm64-Slices vorbereitet: {len(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
