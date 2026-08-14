#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DATA_MODE="empty"
BUILD_LAURA_PACKAGE="0"
DEFER_PACKAGE_TESTS="0"
while [ "$#" -gt 0 ]; do
    case "$1" in
        --data-mode)
            DATA_MODE="${2:-}"
            shift 2
            ;;
        --with-laura-package)
            BUILD_LAURA_PACKAGE="1"
            shift
            ;;
        --defer-package-tests)
            DEFER_PACKAGE_TESTS="1"
            shift
            ;;
        *)
            echo "Unbekannte Option: $1" >&2
            exit 2
            ;;
    esac
done
if { [ "$DATA_MODE" != "empty" ] && [ "$DATA_MODE" != "release" ]; } \
    || [ "$BUILD_LAURA_PACKAGE" = "1" ]; then
    echo "Aufruf: scripts/build_macos_pilot.sh [--data-mode empty|release] [--defer-package-tests]" >&2
    echo "Portable Laura-Testdatenpakete sind im installationsgebundenen Final-V4-Cipher-Modus gesperrt." >&2
    exit 2
fi

if [ "$(uname -s)" != "Darwin" ]; then
    echo "Der macOS-Pilotbuild muss auf macOS ausgeführt werden." >&2
    exit 1
fi
ARCHITECTURE="$(uname -m)"
if [ "$ARCHITECTURE" != "arm64" ]; then
    echo "Dieser Pilotbuild ist für arm64 konfiguriert; gefunden: $ARCHITECTURE" >&2
    exit 1
fi
for tool in python3 hdiutil codesign ditto sips iconutil security osascript xcrun file lipo; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Benötigtes Build-Werkzeug fehlt: $tool" >&2
        exit 1
    fi
done
PYTHON_VERSION="$(python3 -c 'import platform; print(platform.python_version())')"
if [ "$PYTHON_VERSION" != "3.14.6" ]; then
    echo "Für diesen reproduzierbaren Pilotbuild wird Python 3.14.6 benötigt; gefunden: $PYTHON_VERSION" >&2
    exit 1
fi

VERSION="$(python3 -c 'from src.version import APP_VERSION; print(APP_VERSION)')"
BUILD_VERSION="$(python3 -c 'from src.version import APP_BUILD_VERSION; print(APP_BUILD_VERSION)')"
GIT_COMMIT="$(git rev-parse HEAD)"
if [ -n "$(git status --porcelain)" ]; then
    SOURCE_TREE_STATE="dirty"
else
    SOURCE_TREE_STATE="clean"
fi
APP_NAME="Jenaplan-Kompetenzmanager"
BUILD_ROOT="${JENAPLAN_MACOS_BUILD_ROOT:-$ROOT/build/macos-pilot}"
VENV="$BUILD_ROOT/venv"
PAYLOAD="$BUILD_ROOT/payload"
ICONSET="$BUILD_ROOT/AppIcon.iconset"
ICON="$BUILD_ROOT/AppIcon.icns"
SECURITY_BRIDGE="$BUILD_ROOT/libjkm_macos_security.dylib"
SPARKLE_BRIDGE="$BUILD_ROOT/libjkm_macos_sparkle.dylib"
SPARKLE_VENDOR="$BUILD_ROOT/sparkle"
PYI_DIST="$BUILD_ROOT/pyinstaller-dist"
PYI_WORK="$BUILD_ROOT/pyinstaller-work"
DIST_ROOT="${JENAPLAN_MACOS_DIST_ROOT:-$ROOT/dist/macos}"
APP_PATH="$DIST_ROOT/$APP_NAME.app"
if [ "$DATA_MODE" = "release" ]; then
    DMG_NAME="$APP_NAME-$VERSION-macOS-$ARCHITECTURE.dmg"
    VOLUME_NAME="Jenaplan $VERSION"
elif [ "$DATA_MODE" = "laura" ]; then
    DMG_NAME="$APP_NAME-Pilot-$VERSION-macOS-$ARCHITECTURE.dmg"
    VOLUME_NAME="Jenaplan Pilot $VERSION"
else
    DMG_NAME="$APP_NAME-SmokeTest-$VERSION-macOS-$ARCHITECTURE.dmg"
    VOLUME_NAME="Jenaplan Smoke $VERSION"
fi
DMG_PATH="$DIST_ROOT/$DMG_NAME"
DMG_STAGE="$BUILD_ROOT/dmg-root"
DMG_BACKGROUND="$BUILD_ROOT/dmg-background.png"
DMG_RW="$BUILD_ROOT/pilot-layout-rw.dmg"
INSTALLATION_PDF="$DIST_ROOT/$APP_NAME-Pilot-$VERSION-Installationsanleitung.pdf"
MANUAL_PDF="$DIST_ROOT/$APP_NAME-Pilot-$VERSION-Benutzerhandbuch.pdf"
FIRST_STEPS_PDF="$DIST_ROOT/$APP_NAME-Pilot-$VERSION-Erste-Schritte.pdf"
QUICKSTART_PDF="$DIST_ROOT/$APP_NAME-Pilot-$VERSION-Schnellstart-Lehrkraefte.pdf"
BACKUP_GUIDE_PDF="$DIST_ROOT/$APP_NAME-Pilot-$VERSION-Backup-Anleitung.pdf"
BACKUP_SCRIPT="$DIST_ROOT/$APP_NAME-Pilot-$VERSION-Backup.sh"
RELEASE_NOTES="$DIST_ROOT/$APP_NAME-$VERSION-Release-Notes.md"
RELEASE_CHECKSUMS="$DIST_ROOT/SHA256SUMS-$VERSION.txt"
RELEASE_INVENTORY="$DIST_ROOT/RELEASE_INVENTORY-$VERSION.txt"
EMPTY_ZIP="$ROOT/dist/$APP_NAME-$VERSION-Pilotpaket-Leer-macOS-$ARCHITECTURE.zip"
LAURA_ZIP="$ROOT/dist/$APP_NAME-$VERSION-Pilotpaket-Laura-Testdaten-macOS-$ARCHITECTURE.zip"
LAURA_TESTDATA_BACKUP="$DIST_ROOT/Laura-Testdaten-$VERSION.jkmbackup"
LAURA_TEST_WORKBOOK="${LAURA_TEST_WORKBOOK:-$ROOT/docs/Pilottest_Laura_Schuelerprofil_Variante_A.xlsx}"
MOUNT_DIR=""

validate_output_root() {
    local candidate="$1"
    local label="$2"
    if [[ "$candidate" != /* ]] \
        || [ "$candidate" = "/" ] \
        || [ "$candidate" = "$ROOT" ] \
        || [ -L "$candidate" ]; then
        echo "Abbruch: Unsicheres $label: $candidate" >&2
        exit 2
    fi
    case "$candidate" in
        "$ROOT/build/"*|"$ROOT/dist/"*|/private/tmp/*|"${TMPDIR%/}/"*)
            ;;
        *)
            echo "Abbruch: $label liegt nicht in einer freigegebenen Build- oder Temporärwurzel." >&2
            exit 2
            ;;
    esac
}
validate_output_root "$BUILD_ROOT" "Build-Ziel"
validate_output_root "$DIST_ROOT" "Distributions-Ziel"
if ! python3 -c 'import sys; from pathlib import Path; from src.core.runtime_root_protection import require_unprotected_output_path; [require_unprotected_output_path(Path(value)) for value in sys.argv[1:]]' "$BUILD_ROOT" "$DIST_ROOT"; then
    echo "Abbruch: Build- oder Distributionsziel liegt in einem geschützten Produktroot." >&2
    exit 2
fi
if [ "$BUILD_ROOT" = "$DIST_ROOT" ]; then
    echo "Abbruch: Build- und Distributions-Ziel müssen getrennt sein." >&2
    exit 2
fi

cleanup_mount() {
    if [ -n "$MOUNT_DIR" ] && [ -d "$MOUNT_DIR" ]; then
        hdiutil detach "$MOUNT_DIR" -quiet >/dev/null 2>&1 || true
    fi
}
trap cleanup_mount EXIT

if [ -e "$BUILD_ROOT" ] || [ -L "$BUILD_ROOT" ] \
    || [ -e "$DIST_ROOT" ] || [ -L "$DIST_ROOT" ]; then
    echo "Abbruch: Build- und Distributionsziele müssen vollständig neu sein." >&2
    exit 2
fi
mkdir -p "$BUILD_ROOT" "$DIST_ROOT"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --disable-pip-version-check -r requirements-macos-build.txt
SQLCIPHER_417_WHEEL="${JENAPLAN_SQLCIPHER_417_WHEEL:-}"
if [ -z "$SQLCIPHER_417_WHEEL" ] || [ ! -f "$SQLCIPHER_417_WHEEL" ] || [ -L "$SQLCIPHER_417_WHEEL" ]; then
    echo "JENAPLAN_SQLCIPHER_417_WHEEL muss auf das auditierte lokale SQLCipher-4.17-Wheel zeigen." >&2
    exit 2
fi
EXPECTED_SQLCIPHER_WHEEL_SHA="$(python3 -c 'import json; print(json.load(open("packaging/sqlcipher_4_17_macos_arm64_sources.json"))["generated"]["expected_wheel_sha256"])')"
OBSERVED_SQLCIPHER_WHEEL_SHA="$(shasum -a 256 "$SQLCIPHER_417_WHEEL" | awk '{print $1}')"
if [ "$OBSERVED_SQLCIPHER_WHEEL_SHA" != "$EXPECTED_SQLCIPHER_WHEEL_SHA" ]; then
    echo "Das SQLCipher-4.17-Wheel stimmt nicht mit dem Buildmanifest überein." >&2
    exit 2
fi
"$VENV/bin/python" -m pip install --disable-pip-version-check --no-index --no-deps "$SQLCIPHER_417_WHEEL"
"$VENV/bin/python" scripts/audit_macos_security_runtime.py

"$VENV/bin/python" scripts/prepare_macos_pilot_payload.py \
    --output "$PAYLOAD" \
    --data-mode "$DATA_MODE" \
    --version "$VERSION" \
    --git-commit "$GIT_COMMIT" \
    --source-tree-state "$SOURCE_TREE_STATE" \
    --architecture "$ARCHITECTURE"

"$VENV/bin/python" scripts/build_pilot_documents.py \
    --version "$VERSION" \
    --build-version "$BUILD_VERSION" \
    --pilot-commit "$GIT_COMMIT" \
    --output-dir "$DIST_ROOT" \
    --installation-source docs/PILOT_INSTALLATION_LEHRKRAFT.md \
    --manual-source docs/user_manual/USER_MANUAL_SOURCE.md \
    --first-steps-source docs/PILOT_FIRST_STEPS.md \
    --quickstart-source docs/PILOT_QUICKSTART_LEHRKRAEFTE.md \
    --backup-source docs/PILOT_BACKUP.md \
    --icon assets/app_icon.png
cp scripts/backup_macos_pilot.sh "$BACKUP_SCRIPT"
chmod +x "$BACKUP_SCRIPT"

mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" assets/app_icon.png \
        --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    doubled=$((size * 2))
    sips -z "$doubled" "$doubled" assets/app_icon.png \
        --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$ICON"

scripts/build_macos_security_bridge.sh "$SECURITY_BRIDGE"

SPARKLE_FETCH_ARGS=(--output "$SPARKLE_VENDOR")
if [ -n "${JENAPLAN_SPARKLE_ARCHIVE:-}" ]; then
    SPARKLE_FETCH_ARGS+=(--archive "$JENAPLAN_SPARKLE_ARCHIVE")
fi
SPARKLE_SOURCE="$("$VENV/bin/python" scripts/fetch_sparkle.py "${SPARKLE_FETCH_ARGS[@]}")"
scripts/build_macos_sparkle_bridge.sh "$SPARKLE_SOURCE" "$SPARKLE_BRIDGE"
SPARKLE_LICENSE="$BUILD_ROOT/Sparkle-LICENSE.txt"
cp "$SPARKLE_SOURCE/LICENSE" "$SPARKLE_LICENSE"

PILOT_APPCAST_URL="${JENAPLAN_PILOT_APPCAST_URL:-$(cat packaging/pilot_appcast_url.txt)}"
if [[ "$PILOT_APPCAST_URL" != https://* ]]; then
    echo "JENAPLAN_PILOT_APPCAST_URL muss auf den festen HTTPS-Pilot-Appcast zeigen." >&2
    exit 2
fi

export JENAPLAN_PILOT_PAYLOAD_DIR="$PAYLOAD"
export JENAPLAN_MACOS_ICON="$ICON"
export JENAPLAN_MACOS_SECURITY_BRIDGE="$SECURITY_BRIDGE"
export JENAPLAN_MACOS_SPARKLE_BRIDGE="$SPARKLE_BRIDGE"
export JENAPLAN_SPARKLE_FRAMEWORK="$SPARKLE_SOURCE/Sparkle.framework"
export JENAPLAN_SPARKLE_LICENSE="$SPARKLE_LICENSE"
export JENAPLAN_PILOT_APPCAST_URL="$PILOT_APPCAST_URL"
export JENAPLAN_PILOT_FIRST_STEPS_PDF="$FIRST_STEPS_PDF"
export MACOSX_DEPLOYMENT_TARGET="13.0"
export DYLD_FRAMEWORK_PATH="$SPARKLE_SOURCE"
"$VENV/bin/python" -m PyInstaller \
    --noconfirm \
    --clean \
    --distpath "$PYI_DIST" \
    --workpath "$PYI_WORK" \
    packaging/macos_pilot.spec

ditto "$PYI_DIST/$APP_NAME.app" "$APP_PATH"
rm -rf "$APP_PATH/Contents/Frameworks/Sparkle.framework"
ditto "$SPARKLE_SOURCE/Sparkle.framework" "$APP_PATH/Contents/Frameworks/Sparkle.framework"
SQLCIPHER_DIRECT_URL="$APP_PATH/Contents/Resources/sqlcipher3-0.6.2+jkm.sqlcipher4170.1.dist-info/direct_url.json"
if [ ! -f "$SQLCIPHER_DIRECT_URL" ]; then
    echo "Abbruch: SQLCipher-Buildquellennachweis ist vor der Bundle-Bereinigung nicht eindeutig." >&2
    exit 1
fi
rm -f "$SQLCIPHER_DIRECT_URL"
"$VENV/bin/python" scripts/thin_macos_bundle_arm64.py "$APP_PATH"
if { [ "$DATA_MODE" = "empty" ] || [ "$DATA_MODE" = "release" ]; } && find "$APP_PATH" -type f \( -name '*.sqlite' -o -name '*.db' \) -print -quit | grep -q .; then
    echo "Abbruch: Das App-Bundle enthält unerwartet eine Datenbank." >&2
    exit 1
fi
if [ "$DATA_MODE" = "laura" ]; then
    DATABASE_COUNT="$(find "$APP_PATH" -type f \( -name '*.sqlite' -o -name '*.db' \) | wc -l | tr -d ' ')"
    if [ "$DATABASE_COUNT" != "1" ] || ! find "$APP_PATH" -name FIKTIVE_PILOTDATEN.txt -print -quit | grep -q .; then
        echo "Abbruch: Die Laura-Variante ist nicht eindeutig als fiktiv gekennzeichnet." >&2
        exit 1
    fi
fi

SIGNING_IDENTITY="${MACOS_SIGN_IDENTITY:-}"
if [ -z "$SIGNING_IDENTITY" ]; then
    SIGNING_IDENTITY="$(security find-identity -v -p codesigning 2>/dev/null \
        | sed -n 's/.*"\(Developer ID Application:.*\)"/\1/p' \
        | head -n 1)"
fi
if [ -n "$SIGNING_IDENTITY" ]; then
    codesign --force --deep --options runtime --timestamp \
        --sign "$SIGNING_IDENTITY" "$APP_PATH"
    SIGNING_STATUS="Developer-ID-signiert: $SIGNING_IDENTITY"
else
    codesign --force --deep --sign - "$APP_PATH"
    SIGNING_STATUS="ad-hoc signiert; nicht notarisiert"
fi
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

PLIST_VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP_PATH/Contents/Info.plist")"
PLIST_BUILD="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$APP_PATH/Contents/Info.plist")"
PLIST_FEED="$(/usr/libexec/PlistBuddy -c 'Print :SUFeedURL' "$APP_PATH/Contents/Info.plist")"
PLIST_SIGNED_FEED="$(/usr/libexec/PlistBuddy -c 'Print :SURequireSignedFeed' "$APP_PATH/Contents/Info.plist")"
PLIST_VERIFY_BEFORE_EXTRACTION="$(/usr/libexec/PlistBuddy -c 'Print :SUVerifyUpdateBeforeExtraction' "$APP_PATH/Contents/Info.plist")"
if [ "$PLIST_VERSION" != "$VERSION" ] || [ "$PLIST_BUILD" != "$BUILD_VERSION" ] || [ "$PLIST_FEED" != "$PILOT_APPCAST_URL" ] || [ "$PLIST_SIGNED_FEED" != "true" ] || [ "$PLIST_VERIFY_BEFORE_EXTRACTION" != "true" ]; then
    echo "Abbruch: Version, Buildnummer oder Pilot-Appcast im Bundle ist inkonsistent." >&2
    exit 1
fi
if [ ! -f "$APP_PATH/Contents/Resources/third_party_licenses/Sparkle-LICENSE.txt" ]; then
    echo "Abbruch: Der Sparkle-Lizenzhinweis fehlt im App-Bundle." >&2
    exit 1
fi
if [ "$DEFER_PACKAGE_TESTS" = "0" ]; then
    "$VENV/bin/python" scripts/audit_macos_app_bundle.py \
        "$APP_PATH" \
        --expected-version "$VERSION" \
        --expected-build "$BUILD_VERSION"
    "$VENV/bin/python" scripts/smoke_test_macos_app.py \
        "$APP_PATH" \
        --expected-data-mode "$DATA_MODE"
    "$VENV/bin/python" scripts/smoke_test_packaged_restore_worker.py \
        "$APP_PATH"
    "$VENV/bin/python" scripts/smoke_test_macos_keychain.py \
        "$APP_PATH"
fi

mkdir -p "$DMG_STAGE"
ditto "$APP_PATH" "$DMG_STAGE/$APP_NAME.app"
ln -s /Applications "$DMG_STAGE/Programme"
cp "$INSTALLATION_PDF" "$DMG_STAGE/Installationsanleitung.pdf"
mkdir -p "$DMG_STAGE/.background"
"$VENV/bin/python" scripts/create_macos_dmg_background.py \
    --output "$DMG_BACKGROUND" \
    --version "$VERSION"
cp "$DMG_BACKGROUND" "$DMG_STAGE/.background/dmg-background.png"

hdiutil create \
    -volname "$VOLUME_NAME" \
    -srcfolder "$DMG_STAGE" \
    -ov \
    -format UDRW \
    "$DMG_RW" >/dev/null
MOUNT_DIR="$(hdiutil attach "$DMG_RW" -readwrite -noverify -noautoopen | tail -n 1 | cut -f 3-)"
if [ -z "$MOUNT_DIR" ] || [ ! -d "$MOUNT_DIR" ]; then
    echo "DMG-Arbeitsvolume konnte nicht eingebunden werden." >&2
    exit 1
fi
osascript <<OSA
tell application "Finder"
    repeat with attempt from 1 to 100
        if exists disk "$VOLUME_NAME" then exit repeat
        delay 0.1
    end repeat
    if not (exists disk "$VOLUME_NAME") then
        error "DMG-Arbeitsvolume ist in Finder nicht sichtbar."
    end if
    tell disk "$VOLUME_NAME"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set pathbar visible of container window to false
        set bounds of container window to {120, 120, 820, 648}
        set theViewOptions to the icon view options of container window
        set arrangement of theViewOptions to not arranged
        set icon size of theViewOptions to 96
        set text size of theViewOptions to 13
        set background picture of theViewOptions to file ".background:dmg-background.png"
        set position of item "$APP_NAME.app" of container window to {175, 235}
        set position of item "Programme" of container window to {525, 235}
        set position of item "Installationsanleitung.pdf" of container window to {350, 385}
        update without registering applications
        delay 2
        close
    end tell
end tell
OSA
sync
rm -rf "$MOUNT_DIR/.fseventsd" "$MOUNT_DIR/.Trashes"
hdiutil detach "$MOUNT_DIR" -quiet
MOUNT_DIR=""
hdiutil convert "$DMG_RW" -format UDZO -imagekey zlib-level=9 -ov -o "$DMG_PATH" >/dev/null
if [ -n "$SIGNING_IDENTITY" ]; then
    codesign --force --timestamp --sign "$SIGNING_IDENTITY" "$DMG_PATH"
fi
write_checksum() {
    local artifact="$1"
    (
        cd "$(dirname "$artifact")"
        shasum -a 256 "$(basename "$artifact")"
    ) > "$artifact.sha256"
}

write_checksum "$DMG_PATH"
write_checksum "$INSTALLATION_PDF"
write_checksum "$MANUAL_PDF"
write_checksum "$FIRST_STEPS_PDF"
write_checksum "$QUICKSTART_PDF"
write_checksum "$BACKUP_GUIDE_PDF"
write_checksum "$BACKUP_SCRIPT"
cp docs/RELEASE_NOTES.md "$RELEASE_NOTES"

(
    cd "$DIST_ROOT"
    shasum -a 256 \
        "$(basename "$DMG_PATH")" \
        "$(basename "$INSTALLATION_PDF")" \
        "$(basename "$MANUAL_PDF")" \
        "$(basename "$FIRST_STEPS_PDF")" \
        "$(basename "$QUICKSTART_PDF")" \
        "$(basename "$BACKUP_GUIDE_PDF")" \
        "$(basename "$BACKUP_SCRIPT")" \
        "$(basename "$RELEASE_NOTES")"
) > "$RELEASE_CHECKSUMS"

BUILD_TIME="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
{
    echo "Jenaplan-Kompetenzmanager - Release-Inventar"
    echo
    echo "Version: $VERSION"
    echo "Build: $BUILD_VERSION"
    echo "Git-Commit: $GIT_COMMIT"
    echo "Quellbaum: $SOURCE_TREE_STATE"
    echo "Buildzeit: $BUILD_TIME"
    echo "Architektur: $ARCHITECTURE"
    echo "Bundle-ID: de.jenaplan.kompetenzmanager"
    echo "Mindest-macOS: 13.0"
    echo "Signierung: $SIGNING_STATUS"
    echo "Notarisierung: nicht durchgeführt"
    echo "Datenmodus: $DATA_MODE (Release-Kandidat ohne Pilot- oder Echtdaten)"
    echo "Produktiver Support-Reset: installationsgebundene Auth-Recovery mit Final-V4-Preflight und verifiziertem Safety-.jkmebackup"
    echo "Updatekanal: pilot (manuelle Prüfung; keine automatische Installation)"
    echo "Pilot-Appcast: $PILOT_APPCAST_URL"
    echo "Stable-Kanal: deaktiviert"
    echo "Produktdaten: frischer Final-V4-Cipher-Bestand; keine Klartext- oder Altbestandsmigration"
    echo "Gebündelte Datenbankruntime: sqlcipher3 0.6.2+jkm.sqlcipher4170.1 / SQLCipher 4.17.0 community / SQLite 3.53.3 / CommonCrypto"
    echo "Backup/Restore: installationsgebundene .jkmebackup-Runtime; kein ZIP-v1 im Cipher-Modus"
    echo "Windows-Freigabe: nicht erteilt"
    echo
    echo "Automatisierter Teststand: siehe Abschlussbericht zum Release-Kandidaten"
    echo "Offene reale Prüfungen: echter Sleep/Wake; physische Touch-ID-Systemaufforderung und Fingerabdruck; App-Switcher; reale Keychain-/Touch-ID-Prüfung nach Update auf Lauras Mac; Developer-ID-Signierung; Apple-Notarisierung."
    echo
    echo "Artefakte (Bytes, SHA-256, Datei):"
    for artifact in "$DMG_PATH" "$MANUAL_PDF" "$FIRST_STEPS_PDF" "$QUICKSTART_PDF" "$INSTALLATION_PDF" "$BACKUP_GUIDE_PDF" "$RELEASE_NOTES"; do
        echo "$(stat -f '%z' "$artifact")  $(shasum -a 256 "$artifact" | awk '{print $1}')  $(basename "$artifact")"
    done
} > "$RELEASE_INVENTORY"

if [ "$DATA_MODE" = "release" ] && [ "$BUILD_LAURA_PACKAGE" = "1" ]; then
    "$VENV/bin/python" scripts/build_laura_testdata_backup.py \
        --output-directory "$DIST_ROOT" \
        --version "$VERSION" \
        --build-commit "$GIT_COMMIT" \
        --source-tree-state "$SOURCE_TREE_STATE"
    "$VENV/bin/python" scripts/build_laura_pilot_package.py \
        --output-root "$ROOT/dist" \
        --version "$VERSION" \
        --pilot-commit "$GIT_COMMIT" \
        --architecture "$ARCHITECTURE" \
        --variant empty \
        --dmg "$DMG_PATH" \
        --first-steps-pdf "$FIRST_STEPS_PDF" \
        --manual-pdf "$MANUAL_PDF" \
        --quickstart-pdf "$QUICKSTART_PDF" \
        --installation-pdf "$INSTALLATION_PDF" \
        --backup-guide-pdf "$BACKUP_GUIDE_PDF" \
        --pilot-workbook "$LAURA_TEST_WORKBOOK" \
        --release-notes "$RELEASE_NOTES" \
        --release-inventory "$RELEASE_INVENTORY"
    "$VENV/bin/python" scripts/build_laura_pilot_package.py \
        --output-root "$ROOT/dist" \
        --version "$VERSION" \
        --pilot-commit "$GIT_COMMIT" \
        --architecture "$ARCHITECTURE" \
        --variant laura_testdata \
        --pilot-backup "$LAURA_TESTDATA_BACKUP" \
        --dmg "$DMG_PATH" \
        --first-steps-pdf "$FIRST_STEPS_PDF" \
        --manual-pdf "$MANUAL_PDF" \
        --quickstart-pdf "$QUICKSTART_PDF" \
        --installation-pdf "$INSTALLATION_PDF" \
        --backup-guide-pdf "$BACKUP_GUIDE_PDF" \
        --pilot-workbook "$LAURA_TEST_WORKBOOK" \
        --release-notes "$RELEASE_NOTES" \
        --release-inventory "$RELEASE_INVENTORY"
    EMPTY_ZIP_SHA="$(shasum -a 256 "$EMPTY_ZIP" | awk '{print $1}')"
    LAURA_ZIP_SHA="$(shasum -a 256 "$LAURA_ZIP" | awk '{print $1}')"
    LAURA_TESTDATA_BACKUP_SHA="$(shasum -a 256 "$LAURA_TESTDATA_BACKUP" | awk '{print $1}')"
    echo "$EMPTY_ZIP_SHA  $(basename "$EMPTY_ZIP")" > "$EMPTY_ZIP.sha256"
    echo "$LAURA_ZIP_SHA  $(basename "$LAURA_ZIP")" > "$LAURA_ZIP.sha256"
    echo "$LAURA_TESTDATA_BACKUP_SHA  $(basename "$LAURA_TESTDATA_BACKUP")" > "$LAURA_TESTDATA_BACKUP.sha256"
    echo "$LAURA_TESTDATA_BACKUP_SHA  $(basename "$LAURA_TESTDATA_BACKUP")" >> "$RELEASE_CHECKSUMS"
    echo "$EMPTY_ZIP_SHA  $(basename "$EMPTY_ZIP")" >> "$RELEASE_CHECKSUMS"
    echo "$LAURA_ZIP_SHA  $(basename "$LAURA_ZIP")" >> "$RELEASE_CHECKSUMS"
    echo "$(stat -f '%z' "$LAURA_TESTDATA_BACKUP")  $LAURA_TESTDATA_BACKUP_SHA  $(basename "$LAURA_TESTDATA_BACKUP")" >> "$RELEASE_INVENTORY"
    echo "$(stat -f '%z' "$EMPTY_ZIP")  $EMPTY_ZIP_SHA  $(basename "$EMPTY_ZIP")" >> "$RELEASE_INVENTORY"
    echo "$(stat -f '%z' "$LAURA_ZIP")  $LAURA_ZIP_SHA  $(basename "$LAURA_ZIP")" >> "$RELEASE_INVENTORY"
fi

echo "App: $APP_PATH"
echo "DMG: $DMG_PATH"
echo "Installationsanleitung: $INSTALLATION_PDF"
echo "Benutzerhandbuch: $MANUAL_PDF"
echo "Erste Schritte: $FIRST_STEPS_PDF"
echo "Schnellstart: $QUICKSTART_PDF"
echo "Backup-Anleitung: $BACKUP_GUIDE_PDF"
echo "Backup-Skript: $BACKUP_SCRIPT"
if [ "$DATA_MODE" = "release" ] && [ "$BUILD_LAURA_PACKAGE" = "1" ]; then
    echo "Leere Pilotvariante: $EMPTY_ZIP"
    echo "Laura-Testdaten-Backup: $LAURA_TESTDATA_BACKUP"
    echo "Laura-Testdatenvariante: $LAURA_ZIP"
fi
echo "Release-Prüfsummen: $RELEASE_CHECKSUMS"
echo "Release-Inventar: $RELEASE_INVENTORY"
echo "Pilotdaten: $DATA_MODE"
echo "Quellbaum: $SOURCE_TREE_STATE bei $GIT_COMMIT"
echo "Signierung: $SIGNING_STATUS"
