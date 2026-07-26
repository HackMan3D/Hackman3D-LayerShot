# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import sys
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)
assets = root / "src" / "hackman_layershot" / "assets"
asset_datas = [
    (str(path), "assets")
    for path in assets.iterdir()
    if path.is_file() and " 2" not in path.name
]
ffmpeg_datas, ffmpeg_binaries, ffmpeg_hiddenimports = collect_all("imageio_ffmpeg")
build_arch = os.environ.get("LAYERSHOT_BUILD_ARCH", "x64")
windows_x86 = sys.platform == "win32" and build_arch == "x86"
if windows_x86:
    esptool_datas, esptool_binaries, esptool_hiddenimports = collect_all("esptool")
    platform_hiddenimports = ["PySide2.QtWebEngineWidgets"]
elif sys.platform == "win32":
    esptool_datas, esptool_binaries, esptool_hiddenimports = [], [], []
    platform_hiddenimports = ["PySide6.QtWebEngineWidgets"]
else:
    esptool_datas, esptool_binaries, esptool_hiddenimports = collect_all("esptool")
    platform_hiddenimports = []
a = Analysis(
    ["run_layershot.py"],
    pathex=[str(root / "src")],
    binaries=esptool_binaries + ffmpeg_binaries,
    datas=asset_datas + esptool_datas + ffmpeg_datas,
    hiddenimports=["serial.tools.list_ports"] + esptool_hiddenimports
                  + ffmpeg_hiddenimports + platform_hiddenimports,
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Hackman3D LayerShot",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
          console=False, icon=str(assets / ("Hackman3DLayerShot.icns" if sys.platform == "darwin" else "Hackman3DLayerShot.ico")))
distribution_name = ("Hackman3D LayerShot" if sys.platform == "darwin"
                     else f"Hackman3D LayerShot {build_arch}")
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name=distribution_name)
if sys.platform == "darwin":
    app = BUNDLE(coll, name="Hackman3D LayerShot.app",
                 icon=str(assets / "Hackman3DLayerShot.icns"),
                 bundle_identifier="com.hackman3d.layershot.desktop",
                 info_plist={"CFBundleDisplayName":"Hackman3D LayerShot",
                             "CFBundleName":"Hackman3D LayerShot",
                             "CFBundleShortVersionString":"1.2.2","CFBundleVersion":"1.2.2",
                             "NSAppTransportSecurity":{"NSAllowsLocalNetworking":True,
                                                       "NSAllowsArbitraryLoadsInWebContent":True},
                             "NSLocalNetworkUsageDescription":"Hackman3D LayerShot connects to your 3D printers and ESP32 on your local network.",
                             "NSBonjourServices":["_http._tcp."],
                             "NSBluetoothAlwaysUsageDescription":"LayerShot configures the ESP32 Bluetooth camera shutter."})
