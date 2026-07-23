# Hackman3D LayerShot

Hackman3D LayerShot turns an ESP32-C3 into an autonomous Bluetooth camera shutter for 3D-printing timelapses with the iPhone Camera app.

The macOS and Windows applications are built from the same Python/PySide6 source. They have the same interface, features, translations and version number. Once configuration has been sent to the ESP32, the desktop application does not need to remain open during a print.

## Download — version 0.5.1

No compilation or Arduino IDE setup is required:

- [Download for macOS — Apple Silicon](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.5.1/Hackman3D-LayerShot-macOS-0.5.1.zip)
- [Download for Windows — Intel/AMD x64](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.5.1/Hackman3D-LayerShot-Windows-x64-0.5.1.zip)
- [Standalone ESP32-C3 firmware 1.2.0](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.5.1/Hackman3D-LayerShot-ESP32-C3-Firmware-1.2.0.bin)

The application contains the firmware and installs it from the **Installation** page. The standalone image is intended for recovery and advanced use.

The Windows package is a native 64-bit Intel/AMD build.

## Features

- strictly identical Qt interface on macOS and Windows;
- iPhone camera shutter control through Bluetooth HID (`Volume +`);
- Bluetooth pairing mode controlled from the app or the ESP32 BOOT button;
- autonomous layer-change detection through Moonraker;
- support for K2, K1, Ender-3 V3, Creality Hi and SparkX i7 families;
- multi-printer dashboard with independent printer cards;
- camera access for printers exposing a camera page;
- Wi-Fi detection and retrieval of a known network password when permitted by the operating system;
- firmware installation and ESP32 configuration from the desktop app;
- timelapse import, frame-rate, aspect-ratio and framing controls;
- permanent HackMan3D support and social header.

## Supported languages

The same language selector is included on macOS and Windows:

| | | |
|---|---|---|
| English | Français | Italiano |
| Español | Português | 中文 |
| Deutsch | हिन्दी | العربية |
| বাংলা | Bahasa Indonesia | Русский |
| 日本語 | 한국어 | Türkçe |
| Tiếng Việt | ไทย | |

English and French are currently fully translated. Other languages use the English text where a translation is not yet available.

## Hardware and setup

- ESP32-C3 board with 4 MB flash;
- iPhone compatible with Bluetooth camera remotes;
- printer on the same local network with a Moonraker API.

1. Open Hackman3D LayerShot.
2. Connect the ESP32-C3 with a USB data cable.
3. Open **Installation**, select its USB port, then choose **Install firmware**.
4. Add the printer and enter Wi-Fi details.
5. Send the configuration to the ESP32.
6. Enable pairing and select `Hackman3D LayerShot` in iPhone **Settings > Bluetooth**.
7. Open the iPhone Camera app and start the print.

The ESP32 is available as `hackmanlayershot.local`. A short BOOT-button press enables pairing; holding BOOT for at least ten seconds removes saved Bluetooth bonds.

## Build from source

End users should use the ready-to-run downloads above. Contributors need Python 3.11 or later.

### macOS

```sh
./build_macos.sh
```

### Windows

```powershell
.\build_windows.ps1
```

Both scripts package the same files under `src/hackman_layershot` and produce version 0.5.1.

## Firmware source

The Arduino source is in `firmware/Hackman3DLayerShot`. It targets an ESP32-C3 with the **Huge APP** partition scheme. Wi-Fi credentials are never included in the firmware image; they are stored locally in the ESP32 non-volatile memory during setup.

## Support

LayerShot is provided free of charge. Donations, feedback and follows on HackMan3D social channels are welcome through the permanent application header.

Created, designed and coded by HackMan3D.

This repository is currently private. No redistribution license is granted until a `LICENSE` file is added.
