# Hackman3D LayerShot

Hackman3D LayerShot turns an ESP32-C3 into an autonomous Bluetooth camera shutter for creating 3D-printing timelapses with the iPhone Camera app.

The desktop application installs and configures the device, monitors one or more Creality/Klipper printers, and assembles the captured photos. Once the settings have been sent to the ESP32, the desktop application does not need to remain open during a print.

## Features

- iPhone camera shutter control through Bluetooth HID (`Volume +`);
- Bluetooth pairing and bond removal with the ESP32 BOOT button;
- autonomous operation with layer-change detection through Moonraker;
- support for Creality K2, K1, Ender, CR, and SPARKX i7 printer families;
- multi-printer dashboard with printer status and camera access when available;
- Wi-Fi, printer, capture interval, stabilization, and layer-limit settings;
- timelapse generation and framing options;
- macOS and Windows desktop applications plus ESP32-C3 firmware;
- multilingual macOS interface.

## Hardware

- compact ESP32-C3 board with 4 MB of flash storage;
- an iPhone compatible with Bluetooth camera remotes;
- a printer available on the same local network and exposing the Moonraker API.

The firmware uses `hackman-layershot.local` as its network name and `Hackman3D LayerShot` as its Bluetooth name.

## Quick start

1. Flash the firmware with the desktop application.
2. Connect the Mac or PC to the temporary `Hackman3D-LayerShot` Wi-Fi network.
3. Send the home Wi-Fi credentials and printer address to the device.
4. Hold BOOT for approximately three seconds, then select `Hackman3D LayerShot` under Settings > Bluetooth on the iPhone.
5. Open the Camera app and start the print.

A short BOOT-button press enables pairing. Holding the button for at least ten seconds removes previously paired Bluetooth devices.

## Building the applications

### macOS

Requirements: macOS and Swift.

```sh
zsh scripts/build-app.sh
open "outputs/Hackman3D LayerShot.app"
```

### Windows

Requirement: .NET 8 SDK.

```powershell
dotnet publish .\windows\Hackman3D.LayerShot.Windows\Hackman3D.LayerShot.Windows.csproj `
  -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
```

See [windows/README.md](windows/README.md) for ARM64 builds and optional tools.

## Building the firmware

Open `firmware/Hackman3DLayerShot/Hackman3DLayerShot.ino` in Arduino IDE with the Espressif ESP32 core installed, then select the board matching the ESP32-C3 hardware.

The firmware does not contain Wi-Fi credentials. Settings entered by the user are stored locally in the ESP32 non-volatile memory.

## Support the project

This software is provided free of charge. Donations, feedback, and follows on Hackman3D social channels are always welcome through the permanent application header.

Created, designed, and coded by Hackman3D.

## Project status

Development release. This repository is currently private, and no redistribution license is granted until a `LICENSE` file is added.
