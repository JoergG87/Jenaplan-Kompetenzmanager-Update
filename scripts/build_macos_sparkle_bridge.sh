#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SPARKLE_ROOT="${1:?Pfad zur verifizierten Sparkle-Distribution fehlt}"
OUTPUT="${2:-$ROOT/build/macos-update/libjkm_macos_sparkle.dylib}"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "Die native Sparkle-Bridge kann nur auf macOS gebaut werden." >&2
    exit 1
fi
if [ ! -d "$SPARKLE_ROOT/Sparkle.framework" ]; then
    echo "Sparkle.framework fehlt: $SPARKLE_ROOT" >&2
    exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
xcrun clang \
    -arch arm64 \
    -mmacosx-version-min=13.0 \
    -fobjc-arc \
    -dynamiclib \
    -Wl,-install_name,@rpath/libjkm_macos_sparkle.dylib \
    -F"$SPARKLE_ROOT" \
    -framework Foundation \
    -framework Sparkle \
    -Wl,-rpath,@loader_path \
    "$ROOT/src/updater/infrastructure/macos_sparkle_bridge.m" \
    -o "$OUTPUT"

codesign --force --sign - "$OUTPUT"
