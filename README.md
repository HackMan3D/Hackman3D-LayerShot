# Hackman3D LayerShot

Hackman3D LayerShot turns an ESP32-C3 into an autonomous Bluetooth camera shutter for creating 3D-printing timelapses with the iPhone Camera app.

The desktop application installs and configures the device, monitors one or more Creality/Klipper printers, and assembles the captured photos. Once the settings have been sent to the ESP32, the desktop application does not need to remain open during a print.

## Download

No compilation or Arduino IDE setup is required. Download the application for your computer:

- [Download for macOS — Apple Silicon](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.4.0/Hackman3D-LayerShot-macOS-0.4.0.zip)
- [Download for Windows — Intel/AMD x64](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.4.0/Hackman3D-LayerShot-Windows-x64-0.4.0.zip)
- [Download for Windows — ARM64](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.4.0/Hackman3D-LayerShot-Windows-ARM64-0.4.0.zip)

The desktop packages include the ESP32 flashing tool and the correct firmware files. Connect the ESP32-C3 by USB and use the installation section inside Hackman3D LayerShot. The application detects the serial port, flashes the firmware, and guides the user through Wi-Fi and printer setup.

The [standalone ESP32-C3 firmware image](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.4.0/Hackman3D-LayerShot-ESP32-C3-Firmware-1.1.0.bin) is also available for recovery and advanced use, but normal users should install and update the firmware through the desktop application.

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

## Installation

Everything required for normal setup is handled by the desktop application:

1. Download and open Hackman3D LayerShot for macOS or Windows.
2. Connect the ESP32-C3 to the computer by USB.
3. In the application, detect the USB port and select **Install firmware**.
4. Follow the application instructions to configure Wi-Fi and the printer.
5. Hold BOOT for approximately three seconds, then select `Hackman3D LayerShot` under Settings > Bluetooth on the iPhone.
6. Open the Camera app and start the print.

A short BOOT-button press enables pairing. Holding the button for at least ten seconds removes previously paired Bluetooth devices.

## Building from source

The following instructions are for contributors only. End users should download the ready-to-run applications above.

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
