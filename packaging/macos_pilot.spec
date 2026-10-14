# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller configuration for the macOS arm64 pilot application."""

from __future__ import annotations

import os
import runpy
from importlib import metadata
from pathlib import Path


PROJECT_ROOT = Path(SPECPATH).parent
VERSION_DATA = runpy.run_path(PROJECT_ROOT / "src" / "version.py")
VERSION = VERSION_DATA["APP_VERSION"]
BUILD_VERSION = VERSION_DATA["APP_BUILD_VERSION"]
APP_NAME = "Jenaplan-Kompetenzmanager"
BUNDLE_ID = "de.jenaplan.kompetenzmanager"
import sys
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.macos_package_profile import validate_build_selection, profile_digest, verify_prepared_hook
PACKAGE_PROFILE = os.environ.get("JENAPLAN_PACKAGE_PROFILE", "product")
TEST_PROFILE = validate_build_selection(
    PACKAGE_PROFILE, os.environ.get("JENAPLAN_INTERNAL_TEST_PROFILE"), before_build=False,
)
if TEST_PROFILE is not None:
    if os.environ.get("JENAPLAN_INTERNAL_TEST_PROFILE_DIGEST") != profile_digest(TEST_PROFILE):
        raise RuntimeError("test_profile_invalid")
    verify_prepared_hook(TEST_PROFILE)
    APP_NAME = TEST_PROFILE.app_name
    BUNDLE_ID = TEST_PROFILE.bundle_id
PAYLOAD_ROOT = Path(os.environ["JENAPLAN_PILOT_PAYLOAD_DIR"])
ICON_PATH = Path(os.environ["JENAPLAN_MACOS_ICON"])
SECURITY_BRIDGE = Path(os.environ["JENAPLAN_MACOS_SECURITY_BRIDGE"])
PILOT_FIRST_STEPS_PDF = Path(os.environ["JENAPLAN_PILOT_FIRST_STEPS_PDF"])
if TEST_PROFILE is None:
    SPARKLE_BRIDGE = Path(os.environ["JENAPLAN_MACOS_SPARKLE_BRIDGE"])
    SPARKLE_FRAMEWORK = Path(os.environ["JENAPLAN_SPARKLE_FRAMEWORK"])
    SPARKLE_LICENSE = Path(os.environ["JENAPLAN_SPARKLE_LICENSE"])
    SPARKLE_PUBLIC_KEY = (PROJECT_ROOT / "packaging" / "sparkle_pilot_public_key.txt").read_text().strip()
    PILOT_APPCAST_URL = os.environ["JENAPLAN_PILOT_APPCAST_URL"].strip()
    if not PILOT_APPCAST_URL.startswith("https://"):
        raise RuntimeError("Der Pilot-Appcast muss eine feste HTTPS-URL verwenden.")


def distribution_file(distribution_name, suffix):
    distribution = metadata.distribution(distribution_name)
    matches = tuple(
        distribution.locate_file(item)
        for item in distribution.files or ()
        if str(item).endswith(suffix)
    )
    if len(matches) != 1 or not matches[0].is_file():
        raise RuntimeError(
            f"Lizenzdatei für {distribution_name} fehlt: {suffix}"
        )
    return matches[0]


datas = [
    (str(PROJECT_ROOT / "assets"), "assets"),
    (str(PROJECT_ROOT / "data" / "curriculum_catalog_v1.csv"), "data"),
    (str(PAYLOAD_ROOT / "pilot_build_info.json"), "."),
    (
        str(distribution_file("PyNaCl", "licenses/LICENSE")),
        "third_party_licenses/PyNaCl",
    ),
    (
        str(
            distribution_file(
                "PyNaCl",
                "licenses/licenses/LICENSE.libsodium.txt",
            )
        ),
        "third_party_licenses/libsodium",
    ),
    (
        str(distribution_file("sqlcipher3", "licenses/LICENSE")),
        "third_party_licenses/sqlcipher3",
    ),
    (
        str(distribution_file("cryptography", "licenses/LICENSE")),
        "third_party_licenses/cryptography",
    ),
    (
        str(distribution_file("cffi", "licenses/LICENSE")),
        "third_party_licenses/cffi",
    ),
    (
        str(
            PROJECT_ROOT
            / "packaging"
            / "THIRD_PARTY_NOTICES_SECURITY_0.3.0.md"
        ),
        "third_party_licenses",
    ),
    (
        str(
            PROJECT_ROOT
            / "packaging"
            / "THIRD_PARTY_NOTICES_SQLCIPHER_4_17_MACOS.md"
        ),
        "third_party_licenses",
    ),
]
if TEST_PROFILE is None:
    datas.append((str(PILOT_FIRST_STEPS_PDF), "pilot_guides"))
    datas.append((str(SPARKLE_LICENSE), "third_party_licenses"))
else:
    datas.append((str(Path(TEST_PROFILE.build_root) / "internal_test_profile.json"), "."))
initial_data = PAYLOAD_ROOT / "pilot_initial"
if initial_data.is_dir():
    datas.append((str(initial_data), "pilot_initial"))


a = Analysis(
    [str(PROJECT_ROOT / "src" / "desktop_app" / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[(str(SECURITY_BRIDGE), ".")] + ([
        (str(SPARKLE_BRIDGE), "."),
        (str(SPARKLE_FRAMEWORK / "Versions" / "B" / "Sparkle"), "Sparkle.framework/Versions/B"),
    ] if TEST_PROFILE is None else []),
    datas=datas,
    hiddenimports=[
        "PySide6.QtSvg",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "src.desktop_app.leg_html.bridge",
        "src.desktop_app.leg_html.host",
        "src.desktop_app.leg_html.resources_rc",
        "src.desktop_app.web_ui.security",
        "src.desktop_app.report_html.bridge",
        "src.desktop_app.report_html.host",
        "src.desktop_app.report_html.resources_rc",
        "prototypes.pdf_engine.output_models",
        "prototypes.pdf_engine.renderer",
        "src.core.restore_runtime",
        "src.core.macos_test_package_profile",
        "src.desktop_app.restore_worker",
        "src.security.application",
        "src.security.device_credentials",
        "src.security.support_reset",
        "src.security.infrastructure.argon2_hasher",
        "src.security.infrastructure.ed25519",
        "src.security.infrastructure.key_registry",
        "src.security.infrastructure.sqlite_repository",
        "src.security.infrastructure.system",
        "src.security.infrastructure.platform_auth",
        "src.security.packaged_keychain_smoke",
        "scripts.seed_test_data",
        "src.security.document_container",
        "src.security.backup_container",
        "src.security.cipher_product_runtime",
        "src.security.database_key_runtime",
        "src.security.final_v3_document_runtime",
        "src.security.final_v4_sqlcipher_runtime",
        "src.security.final_v4_backup_runtime",
        "src.security.final_v4_live_restore",
        "src.application.managed_documents",
        "src.application.managed_pdf_artifacts",
        "src.application.commands.final_v4_backup_restore",
        "src.core.managed_document_store",
        "src.updater.application",
        "src.updater.domain",
        "src.updater.infrastructure.sparkle",
        "argon2",
        "argon2.low_level",
        "cryptography",
        "cryptography.hazmat.primitives.asymmetric.ed25519",
        "_cffi_backend",
        "cffi",
        "nacl",
        "nacl._sodium",
        "nacl.bindings",
        "sqlcipher3",
        "sqlcipher3._sqlite3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=([str(Path(TEST_PROFILE.build_root) / "internal_test_hook.py")]
                   if TEST_PROFILE is not None else []),
    excludes=[
        "numpy",
        "pandas",
        "PySide6.QtMultimedia",
        "src.security.integration_backup",
        "src.security.integration_database",
        "src.security.integration_gate",
        "src.security.integration_orchestrator",
        "src.security.packaged_integration_smoke",
    ],
    noarchive=False,
    optimize=1,
)

# PyInstaller hooks can add dependency metadata during Analysis.
# CycloneDX SBOMs may contain absolute build paths and are not shipped.
a.datas = [
    item
    for item in a.datas
    if not str(item[0]).endswith(".cyclonedx.json")
]


pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon=str(ICON_PATH),
    bundle_identifier=BUNDLE_ID,
    version=VERSION,
    info_plist={
        "CFBundleDisplayName": APP_NAME,
        "CFBundleName": APP_NAME,
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": BUILD_VERSION,
        "LSMinimumSystemVersion": "13.0",
        "LSApplicationCategoryType": "public.app-category.education",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        **({
            "SUFeedURL": PILOT_APPCAST_URL,
            "SUPublicEDKey": SPARKLE_PUBLIC_KEY,
            "SURequireSignedFeed": True,
            "SUVerifyUpdateBeforeExtraction": True,
            "SUEnableAutomaticChecks": False,
            "SUAllowsAutomaticUpdates": False,
            "SUAutomaticallyUpdate": False,
        } if TEST_PROFILE is None else {
            "JKMInternalTestProfileSHA256": profile_digest(TEST_PROFILE),
        }),
    },
)
