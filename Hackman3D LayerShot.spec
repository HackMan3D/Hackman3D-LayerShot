# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

root = Path(SPECPATH)
assets = root / "src" / "hackman_layershot" / "assets"
a = Analysis(
    ["run_layershot.py"],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(assets), "assets")],
    hiddenimports=["serial.tools.list_ports"],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Hackman3D LayerShot",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
          console=False, icon=str(assets / ("Hackman3DLayerShot.icns" if sys.platform == "darwin" else "Hackman3DLayerShot.ico")))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="Hackman3D LayerShot")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="Hackman3D LayerShot.app",
                 icon=str(assets / "Hackman3DLayerShot.icns"),
                 bundle_identifier="com.hackman3d.layershot",
                 info_plist={"CFBundleShortVersionString":"0.5.1","CFBundleVersion":"0.5.1",
                             "NSLocalNetworkUsageDescription":"LayerShot connects to your printers and ESP32 on the local network.",
                             "NSBluetoothAlwaysUsageDescription":"LayerShot configures the ESP32 Bluetooth camera shutter."})
