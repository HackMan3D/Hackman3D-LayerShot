#!/bin/zsh
set -euo pipefail
ROOT="${0:A:h}"
cd "$ROOT"
PYTHON="${LAYERSHOT_PYTHON:-/Users/eyleck/Documents/Codex/2026-07-19/referenced-chatgpt-conversation-this-is-untrusted/software/.venv-macos/bin/python}"
rm -rf build "dist/Hackman3D LayerShot" "dist/Hackman3D LayerShot.app"
PYTHONPATH="$ROOT/src" "$PYTHON" -m PyInstaller --noconfirm --clean "Hackman3D LayerShot.spec"
mkdir -p releases
ditto -c -k --sequesterRsrc --keepParent "dist/Hackman3D LayerShot.app" "releases/Hackman3D-LayerShot-macOS-0.5.0.zip"
echo "Created releases/Hackman3D-LayerShot-macOS-0.5.0.zip"
