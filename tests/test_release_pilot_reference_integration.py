from __future__ import annotations

import os

import pytest

from scripts.release_pilot import ReleaseConfig, ReleasePilot


@pytest.mark.skipif(
    os.environ.get("JKM_RELEASE_REFERENCE_INTEGRATION") != "1",
    reason="read-only live Build-303 release metadata smoke",
)
def test_published_build_303_reference_is_consistent() -> None:
    result = ReleasePilot(ReleaseConfig.load()).verify_reference_303()
    assert result == {
        "status": "already_published",
        "version": "0.3.0",
        "build": 303,
        "tag": "v0.3.0-build303",
        "release": "published_prerelease",
        "pilot_appcast": "active",
        "lower_build_update_eligible": True,
        "same_build_republish_blocked": True,
        "stable_enabled": False,
    }
