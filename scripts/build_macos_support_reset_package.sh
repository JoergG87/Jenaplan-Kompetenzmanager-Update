#!/bin/zsh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    print -u2 "Das Supportpaket muss auf macOS arm64 gebaut werden."
    exit 2
fi
for TOOL in python3 file; do
    if ! command -v "$TOOL" >/dev/null 2>&1; then
        print -u2 "Erforderliches Build-Werkzeug fehlt: $TOOL"
        exit 2
    fi
done
python3 -c 'import PyInstaller, cryptography' >/dev/null

VERSION="$(python3 -c 'from src.version import APP_VERSION; print(APP_VERSION)')"
BUILD_COMMIT="$(git rev-parse HEAD)"
if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
    SOURCE_TREE_STATE="dirty"
else
    SOURCE_TREE_STATE="clean"
fi
BUILD_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/jenaplan-support-build.XXXXXX")"
cleanup() {
    rm -rf "$BUILD_ROOT"
}
trap cleanup EXIT

PYI_DIST="$BUILD_ROOT/dist"
PYI_WORK="$BUILD_ROOT/work"
PYI_SPEC="$BUILD_ROOT/spec"
mkdir -p "$PYI_DIST" "$PYI_WORK" "$PYI_SPEC"

python3 -m PyInstaller \
    --noconfirm \
    --clean \
    --onefile \
    --console \
    --target-arch arm64 \
    --name Jenaplan-Support-Reset \
    --distpath "$PYI_DIST" \
    --workpath "$PYI_WORK/reset" \
    --specpath "$PYI_SPEC" \
    support_tools/support_reset_cli.py

python3 -m PyInstaller \
    --noconfirm \
    --clean \
    --onefile \
    --console \
    --target-arch arm64 \
    --name Jenaplan-Support-Schluessel-einrichten \
    --distpath "$PYI_DIST" \
    --workpath "$PYI_WORK/keypair" \
    --specpath "$PYI_SPEC" \
    support_tools/keypair_cli.py

if ! file "$PYI_DIST/Jenaplan-Support-Reset" | grep -q "arm64"; then
    print -u2 "Der Reset-Executable ist nicht macOS arm64."
    exit 1
fi
if ! file "$PYI_DIST/Jenaplan-Support-Schluessel-einrichten" | grep -q "arm64"; then
    print -u2 "Der Keypair-Executable ist nicht macOS arm64."
    exit 1
fi

python3 scripts/build_support_reset_package.py \
    --reset-executable "$PYI_DIST/Jenaplan-Support-Reset" \
    --keypair-executable "$PYI_DIST/Jenaplan-Support-Schluessel-einrichten" \
    --output-root "$ROOT/dist" \
    --version "$VERSION" \
    --build-commit "$BUILD_COMMIT" \
    --source-tree-state "$SOURCE_TREE_STATE"
