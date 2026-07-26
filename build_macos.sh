#!/bin/zsh
set -euo pipefail
ROOT="${0:A:h}"
cd "$ROOT"
PYTHON="${LAYERSHOT_PYTHON:-/Users/eyleck/Documents/Codex/2026-07-19/referenced-chatgpt-conversation-this-is-untrusted/software/.venv-macos/bin/python}"
dot_clean -m "$ROOT/src/hackman_layershot/assets" 2>/dev/null || true
xattr -cr "$ROOT/src/hackman_layershot/assets"
rm -rf build "dist/Hackman3D LayerShot" "dist/Hackman3D LayerShot.app"
PYTHONPATH="$ROOT/src" "$PYTHON" -m PyInstaller --noconfirm --clean "Hackman3D LayerShot.spec"
dot_clean -m "$ROOT/dist/Hackman3D LayerShot.app" 2>/dev/null || true
xattr -cr "$ROOT/dist/Hackman3D LayerShot.app"
mkdir -p releases
SIGN_DIR="$(mktemp -d /tmp/layershot-sign.XXXXXX)"
cp -R -X "$ROOT/dist/Hackman3D LayerShot.app" "$SIGN_DIR/Hackman3D LayerShot.app"
codesign --force --deep --sign - "$SIGN_DIR/Hackman3D LayerShot.app"
codesign --verify --deep --strict "$SIGN_DIR/Hackman3D LayerShot.app"
CLEAN_DIR="$(mktemp -d /tmp/layershot-clean.XXXXXX)"
COPYFILE_DISABLE=1 tar --no-xattrs -cf - -C "$SIGN_DIR" "Hackman3D LayerShot.app" | \
  tar --no-xattrs -xf - -C "$CLEAN_DIR"
codesign --force --deep --sign - "$CLEAN_DIR/Hackman3D LayerShot.app"
codesign --verify --deep --strict "$CLEAN_DIR/Hackman3D LayerShot.app"
rm -rf "$ROOT/releases/Hackman3D LayerShot.app"
rm -f "$ROOT/releases/Hackman3D-LayerShot-macOS-1.2.3.zip"
ditto --norsrc "$CLEAN_DIR/Hackman3D LayerShot.app" "$ROOT/releases/Hackman3D LayerShot.app"
ditto -c -k --norsrc --keepParent \
  "$CLEAN_DIR/Hackman3D LayerShot.app" \
  "$CLEAN_DIR/Hackman3D-LayerShot-macOS-1.2.3.zip"
ditto --norsrc "$CLEAN_DIR/Hackman3D-LayerShot-macOS-1.2.3.zip" \
  "$ROOT/releases/Hackman3D-LayerShot-macOS-1.2.3.zip"
echo "Created releases/Hackman3D LayerShot.app"
echo "Created releases/Hackman3D-LayerShot-macOS-1.2.3.zip"
