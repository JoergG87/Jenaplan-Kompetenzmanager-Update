# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller configuration for the macOS arm64 pilot application."""

from __future__ import annotations

import os
import runpy
from pathlib import Path


PROJECT_ROOT = Path(SPECPATH).parent
VERSION_DATA = runpy.run_path(PROJECT_ROOT / "src" / "version.py")
VERSION = VERSION_DATA["APP_VERSION"]
BUILD_VERSION = VERSION_DATA["APP_BUILD_VERSION"]
APP_NAME = "Jenaplan-Kompetenzmanager"
BUNDLE_ID = "de.jenaplan.kompetenzmanager"
PAYLOAD_ROOT = Path(os.environ["JENAPLAN_PILOT_PAYLOAD_DIR"])
ICON_PATH = Path(os.environ["JENAPLAN_MACOS_ICON"])
SECURITY_BRIDGE = Path(os.environ["JENAPLAN_MACOS_SECURITY_BRIDGE"])
SPARKLE_BRIDGE = Path(os.environ["JENAPLAN_MACOS_SPARKLE_BRIDGE"])
SPARKLE_FRAMEWORK = Path(os.environ["JENAPLAN_SPARKLE_FRAMEWORK"])
SPARKLE_LICENSE = Path(os.environ["JENAPLAN_SPARKLE_LICENSE"])
SPARKLE_PUBLIC_KEY = (
    PROJECT_ROOT / "packaging" / "sparkle_pilot_public_key.txt"
).read_text(encoding="utf-8").strip()
PILOT_APPCAST_URL = os.environ["JENAPLAN_PILOT_APPCAST_URL"].strip()
PILOT_FIRST_STEPS_PDF = Path(os.environ["JENAPLAN_PILOT_FIRST_STEPS_PDF"])
if not PILOT_APPCAST_URL.startswith("https://"):
    raise RuntimeError("Der Pilot-Appcast muss eine feste HTTPS-URL verwenden.")

datas = [
    (str(PROJECT_ROOT / "assets"), "assets"),
    (str(PROJECT_ROOT / "data" / "curriculum_catalog_v1.csv"), "data"),
    (str(PAYLOAD_ROOT / "pilot_build_info.json"), "."),
    (str(PILOT_FIRST_STEPS_PDF), "pilot_guides"),
    (str(SPARKLE_LICENSE), "third_party_licenses"),
]
initial_data = PAYLOAD_ROOT / "pilot_initial"
if initial_data.is_dir():
    datas.append((str(initial_data), "pilot_initial"))

a = Analysis(
    [str(PROJECT_ROOT / "src" / "desktop_app" / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[
        (str(SECURITY_BRIDGE), "."),
        (str(SPARKLE_BRIDGE), "."),
        (
            str(SPARKLE_FRAMEWORK / "Versions" / "B" / "Sparkle"),
            "Sparkle.framework/Versions/B",
        ),
    ],
    datas=datas,
    hiddenimports=[
        "PySide6.QtSvg",
        "prototypes.pdf_engine.output_models",
        "prototypes.pdf_engine.renderer",
        "src.core.restore_runtime",
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
        "src.updater.application",
        "src.updater.domain",
        "src.updater.infrastructure.sparkle",
        "argon2",
        "argon2.low_level",
        "cryptography",
        "cryptography.hazmat.primitives.asymmetric.ed25519",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "numpy",
        "pandas",
        "PySide6.QtMultimedia",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
    ],
    noarchive=False,
    optimize=1,
)
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
        "SUFeedURL": PILOT_APPCAST_URL,
        "SUPublicEDKey": SPARKLE_PUBLIC_KEY,
        "SURequireSignedFeed": True,
        "SUVerifyUpdateBeforeExtraction": True,
        "SUEnableAutomaticChecks": False,
        "SUAllowsAutomaticUpdates": False,
        "SUAutomaticallyUpdate": False,
    },
)
