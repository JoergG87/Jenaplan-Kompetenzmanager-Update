#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT="${1:-$ROOT/build/macos-security/libjkm_macos_security.dylib}"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "Die native Security-Bridge kann nur auf macOS gebaut werden." >&2
    exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
xcrun clang \
    -arch arm64 \
    -mmacosx-version-min=13.0 \
    -fobjc-arc \
    -fblocks \
    -dynamiclib \
    -Wl,-install_name,@rpath/libjkm_macos_security.dylib \
    -framework Foundation \
    -framework Security \
    -framework LocalAuthentication \
    "$ROOT/src/security/infrastructure/macos_security_bridge.m" \
    -o "$OUTPUT"

codesign --force --sign - "$OUTPUT"
