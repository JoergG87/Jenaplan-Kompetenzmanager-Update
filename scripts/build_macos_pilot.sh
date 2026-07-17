#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DATA_MODE="empty"
if [ "${1:-}" = "--data-mode" ]; then
    DATA_MODE="${2:-}"
    shift 2
fi
if [ "$#" -ne 0 ] || { [ "$DATA_MODE" != "empty" ] && [ "$DATA_MODE" != "laura" ]; }; then
    echo "Aufruf: scripts/build_macos_pilot.sh [--data-mode empty|laura]" >&2
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
for tool in python3 hdiutil codesign ditto sips iconutil security osascript xcrun; do
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
GIT_COMMIT="$(git rev-parse HEAD)"
if [ -n "$(git status --porcelain)" ]; then
    SOURCE_TREE_STATE="dirty"
else
    SOURCE_TREE_STATE="clean"
fi
APP_NAME="Jenaplan-Kompetenzmanager"
BUILD_ROOT="$ROOT/build/macos-pilot"
VENV="$BUILD_ROOT/venv"
PAYLOAD="$BUILD_ROOT/payload"
ICONSET="$BUILD_ROOT/AppIcon.iconset"
ICON="$BUILD_ROOT/AppIcon.icns"
SECURITY_BRIDGE="$BUILD_ROOT/libjkm_macos_security.dylib"
PYI_DIST="$BUILD_ROOT/pyinstaller-dist"
PYI_WORK="$BUILD_ROOT/pyinstaller-work"
DIST_ROOT="$ROOT/dist/macos"
APP_PATH="$DIST_ROOT/$APP_NAME.app"
if [ "$DATA_MODE" = "laura" ]; then
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
LAURA_ZIP="$ROOT/dist/${APP_NAME}_Pilot_${VERSION}_Laura.zip"
MOUNT_DIR=""

cleanup_mount() {
    if [ -n "$MOUNT_DIR" ] && [ -d "$MOUNT_DIR" ]; then
        hdiutil detach "$MOUNT_DIR" -quiet >/dev/null 2>&1 || true
    fi
}
trap cleanup_mount EXIT

rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT" "$DIST_ROOT"
rm -rf "$APP_PATH" "$DMG_PATH" "$DMG_PATH.sha256"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --disable-pip-version-check -r requirements-macos-build.txt

"$VENV/bin/python" scripts/prepare_macos_pilot_payload.py \
    --output "$PAYLOAD" \
    --data-mode "$DATA_MODE" \
    --version "$VERSION" \
    --git-commit "$GIT_COMMIT" \
    --source-tree-state "$SOURCE_TREE_STATE" \
    --architecture "$ARCHITECTURE"

"$VENV/bin/python" scripts/build_pilot_documents.py \
    --version "$VERSION" \
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

export JENAPLAN_PILOT_PAYLOAD_DIR="$PAYLOAD"
export JENAPLAN_MACOS_ICON="$ICON"
export JENAPLAN_MACOS_SECURITY_BRIDGE="$SECURITY_BRIDGE"
export MACOSX_DEPLOYMENT_TARGET="13.0"
"$VENV/bin/python" -m PyInstaller \
    --noconfirm \
    --clean \
    --distpath "$PYI_DIST" \
    --workpath "$PYI_WORK" \
    packaging/macos_pilot.spec

ditto "$PYI_DIST/$APP_NAME.app" "$APP_PATH"
if [ "$DATA_MODE" = "empty" ] && find "$APP_PATH" -type f \( -name '*.sqlite' -o -name '*.db' \) -print -quit | grep -q .; then
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
shasum -a 256 "$DMG_PATH" > "$DMG_PATH.sha256"
shasum -a 256 "$INSTALLATION_PDF" > "$INSTALLATION_PDF.sha256"
shasum -a 256 "$MANUAL_PDF" > "$MANUAL_PDF.sha256"
shasum -a 256 "$FIRST_STEPS_PDF" > "$FIRST_STEPS_PDF.sha256"
shasum -a 256 "$QUICKSTART_PDF" > "$QUICKSTART_PDF.sha256"
shasum -a 256 "$BACKUP_GUIDE_PDF" > "$BACKUP_GUIDE_PDF.sha256"
shasum -a 256 "$BACKUP_SCRIPT" > "$BACKUP_SCRIPT.sha256"

if [ "$DATA_MODE" = "laura" ]; then
    "$VENV/bin/python" scripts/build_laura_pilot_package.py \
        --output-root "$ROOT/dist" \
        --version "$VERSION" \
        --dmg "$DMG_PATH" \
        --installation-pdf "$INSTALLATION_PDF" \
        --first-steps-pdf "$FIRST_STEPS_PDF" \
        --manual-pdf "$MANUAL_PDF" \
        --quickstart-pdf "$QUICKSTART_PDF" \
        --pilot-workbook docs/Pilottest_Laura_Schuelerprofil_Variante_A.xlsx \
        --backup-pdf "$BACKUP_GUIDE_PDF" \
        --backup-script "$BACKUP_SCRIPT"
    shasum -a 256 "$LAURA_ZIP" > "$LAURA_ZIP.sha256"
fi

echo "App: $APP_PATH"
echo "DMG: $DMG_PATH"
echo "Installationsanleitung: $INSTALLATION_PDF"
echo "Benutzerhandbuch: $MANUAL_PDF"
echo "Erste Schritte: $FIRST_STEPS_PDF"
echo "Schnellstart: $QUICKSTART_PDF"
echo "Backup-Anleitung: $BACKUP_GUIDE_PDF"
echo "Backup-Skript: $BACKUP_SCRIPT"
if [ "$DATA_MODE" = "laura" ]; then
    echo "Laura-ZIP: $LAURA_ZIP"
fi
echo "Pilotdaten: $DATA_MODE"
echo "Quellbaum: $SOURCE_TREE_STATE bei $GIT_COMMIT"
echo "Signierung: $SIGNING_STATUS"
