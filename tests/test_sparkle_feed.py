"""Pure validation tests for the signed Sparkle publishing boundary."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from scripts.build_sparkle_pilot_feed import (
    _https_prefix,
    validate_app_bundle,
    validate_generated_appcast,
)


def test_update_urls_require_fixed_https_without_credentials_or_local_paths() -> None:
    assert _https_prefix(
        "https://example.github.io/jenaplan-updates/pilot",
        name="Pilot",
    ) == "https://example.github.io/jenaplan-updates/pilot/"
    for value in (
        "http://example.test/pilot",
        "https://user:secret@example.test/pilot",
        "https://localhost/pilot",
        "https://example.test/Users/name/pilot",
    ):
        with pytest.raises(ValueError):
            _https_prefix(value, name="Pilot")


def test_appcast_validation_requires_archive_and_feed_signatures(tmp_path: Path) -> None:
    archive_url = "https://github.com/example/updates/releases/download/v0.2.2/Jenaplan-Kompetenzmanager-0.2.2-macOS-arm64.zip"
    appcast = tmp_path / "appcast.xml"
    appcast.write_text(
        f'''<?xml version="1.0" encoding="utf-8"?>
<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle" version="2.0">
  <channel><item><sparkle:version>202</sparkle:version><sparkle:shortVersionString>0.2.2</sparkle:shortVersionString><enclosure url="{archive_url}" length="42" type="application/octet-stream" sparkle:edSignature="archive-signature" /></item></channel>
</rss>
<!-- sparkle-signatures:
edSignature: feed-signature
length: 42
-->''',
        encoding="utf-8",
    )
    validate_generated_appcast(
        appcast,
        archive_url=archive_url,
        short_version="0.2.2",
        build_version="202",
    )
    appcast.write_text(
        appcast.read_text(encoding="utf-8").replace("<!-- sparkle-signatures:", "<!-- removed-signatures:"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="nicht signiert"):
        validate_generated_appcast(
            appcast,
            archive_url=archive_url,
            short_version="0.2.2",
            build_version="202",
        )


def test_signed_feed_requires_archive_verification_before_extraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = tmp_path / "Jenaplan-Kompetenzmanager.app"
    plist = app / "Contents" / "Info.plist"
    plist.parent.mkdir(parents=True)
    import plistlib

    info = {
        "CFBundleIdentifier": "de.jenaplan.kompetenzmanager",
        "CFBundleShortVersionString": "0.2.2",
        "CFBundleVersion": "202",
        "CFBundleExecutable": "Jenaplan-Kompetenzmanager",
        "LSMinimumSystemVersion": "13.0",
        "SUPublicEDKey": "public-test-key",
        "SURequireSignedFeed": True,
        "SUVerifyUpdateBeforeExtraction": False,
    }
    executable = app / "Contents" / "MacOS" / info["CFBundleExecutable"]
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"synthetic-test-executable")
    executable.chmod(0o755)

    def successful_bundle_check(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="arm64\n", stderr="")

    monkeypatch.setattr(subprocess, "run", successful_bundle_check)
    with plist.open("wb") as handle:
        plistlib.dump(info, handle)
    with pytest.raises(ValueError, match="Vorabprüfung"):
        validate_app_bundle(app, short_version="0.2.2", build_version="202")
    info["SUVerifyUpdateBeforeExtraction"] = True
    with plist.open("wb") as handle:
        plistlib.dump(info, handle)
    validate_app_bundle(app, short_version="0.2.2", build_version="202")


def test_update_bundle_rejects_wrong_identity_and_architecture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import plistlib

    app = tmp_path / "Jenaplan-Kompetenzmanager.app"
    plist = app / "Contents" / "Info.plist"
    executable = app / "Contents" / "MacOS" / "Jenaplan-Kompetenzmanager"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"synthetic-test-executable")
    executable.chmod(0o755)
    info = {
        "CFBundleIdentifier": "de.jenaplan.kompetenzmanager",
        "CFBundleShortVersionString": "0.2.2",
        "CFBundleVersion": "202",
        "CFBundleExecutable": executable.name,
        "LSMinimumSystemVersion": "13.0",
        "SUPublicEDKey": "public-test-key",
        "SURequireSignedFeed": True,
        "SUVerifyUpdateBeforeExtraction": True,
    }
    with plist.open("wb") as handle:
        plistlib.dump(info, handle)

    def wrong_architecture(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="x86_64\n", stderr="")

    monkeypatch.setattr(subprocess, "run", wrong_architecture)
    with pytest.raises(ValueError, match="arm64"):
        validate_app_bundle(app, short_version="0.2.2", build_version="202")

    info["CFBundleIdentifier"] = "example.invalid.bundle"
    with plist.open("wb") as handle:
        plistlib.dump(info, handle)
    with pytest.raises(ValueError, match="CFBundleIdentifier"):
        validate_app_bundle(app, short_version="0.2.2", build_version="202")
