#!/bin/zsh
set -euo pipefail
ROOT="${0:A:h:h}"
cd "$ROOT"
swift build -c release
APP="$ROOT/outputs/Hackman3D LayerShot.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp ".build/release/LayerShot" "$APP/Contents/MacOS/LayerShot"
cp "$ROOT/Resources/Info.plist" "$APP/Contents/Info.plist"
cp "$ROOT/Resources/Hackman3DLayerShot.png" "$APP/Contents/Resources/Hackman3DLayerShot.png"
cp "$ROOT/Resources/Hackman3DLayerShot.icns" "$APP/Contents/Resources/Hackman3DLayerShot.icns"
cp "$ROOT"/Resources/social_*.svg "$APP/Contents/Resources/"
cp "$ROOT"/work/firmware-build/Hackman3DLayerShot.ino.bin "$APP/Contents/Resources/"
cp "$ROOT"/work/firmware-build/Hackman3DLayerShot.ino.bootloader.bin "$APP/Contents/Resources/"
cp "$ROOT"/work/firmware-build/Hackman3DLayerShot.ino.partitions.bin "$APP/Contents/Resources/"
ESPTOOL="$HOME/Library/Arduino15/packages/esp32/tools/esptool_py/5.3.0/esptool"
if [[ -x "$ESPTOOL" ]]; then
  cp "$ESPTOOL" "$APP/Contents/Resources/esptool"
  chmod +x "$APP/Contents/Resources/esptool"
fi
xattr -cr "$APP"
xattr -d com.apple.FinderInfo "$APP" 2>/dev/null || true
xattr -d com.apple.fileprovider.fpfs#P "$APP" 2>/dev/null || true
codesign --force --deep --sign - "$APP"
echo "$APP"
