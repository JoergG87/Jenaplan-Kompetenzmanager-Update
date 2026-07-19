"""Download and verify the pinned official Sparkle distribution."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request


SPARKLE_VERSION = "2.9.4"
SPARKLE_ARCHIVE_NAME = f"Sparkle-{SPARKLE_VERSION}.tar.xz"
SPARKLE_DOWNLOAD_URL = (
    "https://github.com/sparkle-project/Sparkle/releases/download/"
    f"{SPARKLE_VERSION}/{SPARKLE_ARCHIVE_NAME}"
)
SPARKLE_SHA256 = "ce89daf967db1e1893ed3ebd67575ed82d3902563e3191ca92aaec9164fbdef9"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_sparkle(output_dir: Path, *, archive: Path | None = None) -> Path:
    output_dir = Path(output_dir)
    archive_path = Path(archive) if archive is not None else output_dir / SPARKLE_ARCHIVE_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    if not archive_path.is_file():
        with tempfile.NamedTemporaryFile(
            prefix="sparkle-download-", suffix=".tar.xz", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            with urllib.request.urlopen(SPARKLE_DOWNLOAD_URL, timeout=60) as response:
                with temporary_path.open("wb") as target:
                    shutil.copyfileobj(response, target)
            temporary_path.replace(archive_path)
        finally:
            temporary_path.unlink(missing_ok=True)
    if sha256(archive_path) != SPARKLE_SHA256:
        raise RuntimeError("Sparkle-Archiv hat nicht den freigegebenen SHA-256-Wert.")
    extraction = output_dir / f"Sparkle-{SPARKLE_VERSION}"
    if extraction.exists():
        shutil.rmtree(extraction)
    extraction.mkdir(parents=True)
    with tarfile.open(archive_path, mode="r:xz") as bundle:
        bundle.extractall(extraction, filter="data")
    framework = extraction / "Sparkle.framework"
    if not framework.is_dir():
        raise RuntimeError("Sparkle.framework fehlt in der verifizierten Distribution.")
    return extraction


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    print(fetch_sparkle(args.output, archive=args.archive))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
