#!/bin/bash
set -e

LAUNCHER_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$LAUNCHER_DIR/.." && pwd)"

cd "$PROJECT_DIR"

if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

"$PYTHON" -m src.desktop_app.main
