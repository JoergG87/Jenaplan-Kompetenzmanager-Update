#!/bin/zsh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    print -u2 "Der Support-Assistent muss auf macOS arm64 gebaut werden."
    exit 2
fi
for TOOL in python3 file plutil; do
    if ! command -v "$TOOL" >/dev/null 2>&1; then
        print -u2 "Erforderliches Build-Werkzeug fehlt: $TOOL"
        exit 2
    fi
done
python3 -c 'import PyInstaller, PySide6, cryptography' >/dev/null

VERSION="$(python3 -c 'from src.version import APP_VERSION; print(APP_VERSION)')"
BUILD_VERSION="$(python3 -c 'from src.version import APP_BUILD_VERSION; print(APP_BUILD_VERSION)')"
MINIMUM_MACOS_VERSION="13.0"
BUILD_COMMIT="$(git rev-parse HEAD)"
if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
    SOURCE_TREE_STATE="dirty"
else
    SOURCE_TREE_STATE="clean"
fi
BUILD_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/jenaplan-support-assistant-build.XXXXXX")"
cleanup() {
    rm -rf "$BUILD_ROOT"
}
trap cleanup EXIT

python3 -m PyInstaller \
    --noconfirm \
    --clean \
    --onedir \
    --windowed \
    --target-arch arm64 \
    --name "Jenaplan Support-Assistent" \
    --osx-bundle-identifier de.jenaplan.support-assistent \
    --icon "$ROOT/assets/app_icon.png" \
    --exclude-module src.application \
    --exclude-module src.core \
    --exclude-module src.desktop_app \
    --exclude-module src.security.infrastructure \
    --exclude-module src.updater \
    --exclude-module prototypes \
    --exclude-module sqlite3 \
    --exclude-module pandas \
    --exclude-module numpy \
    --distpath "$BUILD_ROOT/dist" \
    --workpath "$BUILD_ROOT/work" \
    --specpath "$BUILD_ROOT/spec" \
    support_tools/support_assistant_app.py

APP="$BUILD_ROOT/dist/Jenaplan Support-Assistent.app"
EXECUTABLE="$APP/Contents/MacOS/Jenaplan Support-Assistent"
INFO_PLIST="$APP/Contents/Info.plist"
if ! file "$EXECUTABLE" | grep -q "arm64"; then
    print -u2 "Der Support-Assistent ist nicht macOS arm64."
    exit 1
fi
if [[ "$(plutil -extract CFBundleIdentifier raw "$INFO_PLIST")" != "de.jenaplan.support-assistent" ]]; then
    print -u2 "Die Bundle-ID des Support-Assistenten ist ungültig."
    exit 1
fi

/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$INFO_PLIST"
/usr/libexec/PlistBuddy -c "Delete :CFBundleVersion" "$INFO_PLIST" >/dev/null 2>&1 || true
/usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $BUILD_VERSION" "$INFO_PLIST"
/usr/libexec/PlistBuddy -c "Delete :LSMinimumSystemVersion" "$INFO_PLIST" >/dev/null 2>&1 || true
/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string $MINIMUM_MACOS_VERSION" "$INFO_PLIST"

if [[ -x /usr/bin/codesign ]]; then
    /usr/bin/codesign --force --deep --sign - "$APP"
    /usr/bin/codesign --verify --deep --strict "$APP"
fi
if [[ "$(plutil -extract CFBundleShortVersionString raw "$INFO_PLIST")" != "$VERSION" \
    || "$(plutil -extract CFBundleVersion raw "$INFO_PLIST")" != "$BUILD_VERSION" \
    || "$(plutil -extract LSMinimumSystemVersion raw "$INFO_PLIST")" != "$MINIMUM_MACOS_VERSION" ]]; then
    print -u2 "Die Release-Metadaten des Support-Assistenten sind inkonsistent."
    exit 1
fi
if ! "$EXECUTABLE" --packaged-smoke-test; then
    print -u2 "Der paketierte Support-Assistent hat den isolierten Smoke-Test nicht bestanden."
    exit 1
fi

python3 scripts/build_support_assistant_package.py \
    --app-bundle "$APP" \
    --output-root "$ROOT/dist" \
    --version "$VERSION" \
    --build-version "$BUILD_VERSION" \
    --minimum-macos-version "$MINIMUM_MACOS_VERSION" \
    --build-commit "$BUILD_COMMIT" \
    --source-tree-state "$SOURCE_TREE_STATE"
