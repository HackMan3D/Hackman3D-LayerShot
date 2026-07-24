# Hackman3D LayerShot

Hackman3D LayerShot turns a small ESP32-C3 into an autonomous Bluetooth camera
shutter for 3D-printing timelapses. It detects layer changes through Moonraker
and triggers an iPhone, an Android phone or a compatible DJI camera.

No iPhone application is required. Once the ESP32 has been configured, the Mac
or PC application can be closed during the entire print.

![LayerShot camera and firmware selection on macOS](docs/images/installation-camera-selection.png)

## Download — version 0.6.0

No compilation or Arduino IDE setup is required:

- [Download for macOS — Apple Silicon](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.6.0/Hackman3D-LayerShot-macOS-0.6.0.zip)
- [Download the Windows installer — 32-bit and 64-bit](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.6.0/Hackman3D-LayerShot-Windows-Setup-0.6.0.exe)
- [Phone firmware for ESP32-C3](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.6.0/Hackman3D-LayerShot-ESP32-C3-Phone.bin)
- [DJI firmware for ESP32-C3](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.6.0/Hackman3D-LayerShot-ESP32-C3-DJI.bin)

> **Security notice:** these downloads are not yet signed with Apple and
> Microsoft developer certificates. macOS Gatekeeper or Windows SmartScreen may
> therefore display a warning even when the files were downloaded from this
> official repository. On macOS, right-click the app and choose **Open**. On
> Windows, choose **More info**, verify the installer file name, then choose
> **Run anyway**.

The desktop application already contains the firmware and installs it from the
**Installation** page. The standalone firmware file is provided only for
recovery and advanced use.

## Three steps. That is all.

LayerShot is designed to be extremely simple:

1. **Install the LayerShot application** on the Mac or PC.
2. **Select the printer and the 2.4 GHz Wi-Fi network** in the guided
   Installation page.
3. **Connect the ESP32-C3 and click Install firmware.**

LayerShot installs the ESP32 program, sends all settings and restarts the board
automatically. There is no source code to edit, no Arduino IDE to install and no
firmware file to select. Choose the camera type, follow its pairing instructions
and LayerShot is ready to photograph every layer.

## Camera compatibility

The Installation page clearly shows these details before installing the
matching firmware:

| Choice in LayerShot | Compatible devices | How the shutter works | Important requirement |
|---|---|---|---|
| iPhone | iPhones supporting Bluetooth keyboard/remote volume keys | Bluetooth HID `Volume +` | Keep Apple's Camera app open |
| Android | Phones whose camera app can assign a volume key to the shutter | Bluetooth HID `Volume +` | Enable “volume button = shutter” when required; support depends on the phone and camera app |
| DJI | DJI Osmo Action 4, Osmo Action 5 Pro, Osmo Action 6 and Osmo 360 | Official DJI BLE camera protocol | Put the camera in Photo mode and approve pairing on its screen |

> **Testing note:** DJI camera support is currently in its public testing phase.
> The compatible models above are based on DJI's official protocol. Please test
> the shutter before starting a print and send feedback if you encounter a problem.

DJI Osmo Action 3 and older models are not listed as compatible by the official
protocol demo used by this project. Smartphone compatibility can vary because
manufacturers are free to change how their Camera app handles volume keys.

## What LayerShot does

- controls supported phone Camera apps through Bluetooth HID (`Volume +`);
- controls compatible DJI cameras through the official DJI BLE protocol;
- detects layer changes autonomously through the printer's Moonraker API;
- supports multiple printers in separate dashboard cards;
- discovers compatible Klipper/Moonraker printers on the local network;
- identifies common Creality models when the printer exposes enough data;
- displays print state, progress, current layer and total layer count;
- embeds the printer camera preview when its local camera page is available;
- installs and configures the ESP32-C3 firmware in one guided operation;
- retrieves a known Wi-Fi password only after operating-system permission;
- provides an ESP status page and a local dashboard served by the ESP32;
- creates a video from imported photos with frame-rate, aspect-ratio, framing,
  rotation, quality and codec controls;
- uses the same Qt interface, features, translations and version number on
  macOS plus 32-bit and 64-bit Windows.

## Supported printers

LayerShot is designed for Creality printers exposing Moonraker/Klipper on the
local network, including:

| Family | Models |
|---|---|
| K2 | K2, K2 Plus |
| K1 | K1, K1C, K1 Max |
| Ender-3 V3 | Ender-3 V3, V3 KE, V3 SE, V3 Plus |
| Creality Hi | Hi, Hi Combo |
| SparkX | SparkX i7 |

Other Moonraker/Klipper printers can be added with the generic profile. Exact
camera and layer-count availability depends on the API exposed by the printer.

## Requirements

- an ESP32-C3 board with 4 MB flash;
- a compatible iPhone, Android phone or DJI camera as listed above;
- a 2.4 GHz Wi-Fi network;
- a printer exposing Moonraker on the same local network;
- macOS 14 or later on Apple Silicon, or Windows 10/11 (32-bit or 64-bit).

## Installation

1. Download and open Hackman3D LayerShot.
2. Open **Installation**.
3. Discover or add the printer, test its connection, then save it.
4. Select the 2.4 GHz Wi-Fi network and enter its password. LayerShot can ask
   macOS or Windows for a password already known by that computer.
5. Choose the camera. LayerShot displays its exact compatibility and pairing
   procedure, then automatically selects the correct firmware.
6. Connect the ESP32-C3 with a USB data cable and select its serial port.
7. Choose **Install and configure**. LayerShot validates all required
   information, installs the selected firmware and sends the Wi-Fi, printer and
   camera settings over USB.
8. Follow the displayed pairing guide and wait for the ESP LED to turn green.

Wi-Fi credentials are never embedded in the application or downloadable
firmware. They are written only to the configured ESP32 and, when explicitly
retrieved or saved, to the current user's protected operating-system keychain.

## Pair the camera

### iPhone

1. On the iPhone, open **Settings > Bluetooth**.
2. In LayerShot, choose **Enable iPhone pairing**, or hold the ESP32 **BOOT**
   button for three seconds.
3. Select **Hackman3D LayerShot** on the iPhone.
4. Open the native Camera app and use **Test camera shutter**.
5. Keep the iPhone Camera app open and start the print.

The **BOOT** button has three actions:

| Action | Result |
|---|---|
| Short press | Take a photo |
| Hold for 3 seconds | Enable Bluetooth pairing for 60 seconds |
| Hold for 10 seconds | Erase saved Bluetooth pairing |

When removing a pairing, also choose **Forget This Device** in the iPhone's
Bluetooth settings before pairing again.

### Android

1. Open **Settings > Connected devices > Pair new device**.
2. Start pairing in LayerShot and select **Hackman3D LayerShot**.
3. Open the Camera app and, if necessary, assign a volume button to **Shutter**.
4. Keep the Camera app open and test the shutter before starting the print.

### DJI

1. Power on a compatible DJI camera and select **Photo** mode.
2. Start the DJI search from LayerShot or hold **BOOT** for three seconds.
3. Keep the camera close to LayerShot and approve the verification prompt on
   the DJI screen.
4. Test the shutter. The ESP32 stores the pairing and reconnects automatically.

## LED colours

| Colour | Meaning |
|---|---|
| Red | Powered, but the selected camera is not connected |
| Flashing blue | Bluetooth pairing mode |
| Green | Camera connected |
| Purple flash | Camera shutter command sent |

## Autonomous operation

The ESP32 directly monitors the configured printer. The desktop application and
computer do not need to remain open while printing. The ESP32 web dashboard is
available at:

`http://hackman-layershot.local`

Some routers publish a numbered `.lan` address instead. The desktop application
automatically searches for the LayerShot device and remembers the working local
address.

## Create a timelapse

1. Import the folder containing the iPhone photos.
2. Choose the output MP4 file.
3. Select frame rate, aspect ratio, framing, crop position, rotation, background,
   quality and H.264/H.265 codec.
4. Start the video export.

Video export currently requires FFmpeg to be installed and should be considered
a beta feature until it has been validated on a wider range of photo sets.

![LayerShot timelapse controls](docs/images/timelapse-controls.png)

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

English and French are currently fully translated. Other languages use English
text where a translation is not yet available.

## Troubleshooting

### macOS blocks the first launch

The current macOS build is signed for integrity but is not yet notarized through
the Apple Developer programme. Control-click **Hackman3D LayerShot**, choose
**Open**, then confirm **Open** once. Later launches work normally.

### The ESP32 cannot connect to Wi-Fi

- use a 2.4 GHz network; ESP32-C3 does not connect to 5 GHz-only networks;
- check the password with the eye button before installation;
- place the ESP32 near the router for the first connection;
- reopen the ESP dashboard or use the ESP status page in LayerShot.

### The iPhone is connected but no photo is taken

- keep the native iPhone Camera app visible;
- test a short **BOOT** press first;
- remove the pairing on both the ESP32 and iPhone, then pair again;
- verify that the ESP LED is green before testing the shutter.

### The printer is not found

- confirm that the computer and printer are on the same local network;
- use network discovery from the Installation page;
- try the Moonraker ports `4408`, `7125` and `80`;
- verify that the printer's local web interface is reachable in a browser.

## Build from source

End users should use the ready-to-run downloads above. Contributors need Python
3.11 or later.

### macOS

```sh
./build_macos.sh
```

### Windows 32-bit and 64-bit

```powershell
.\build_windows.ps1
```

Both scripts package the shared files under `src/hackman_layershot` and produce
application version 0.6.0. The Windows script requires Python 3.12 x64,
Python 3.10 x86 and Inno Setup 7. It produces one installer that automatically
selects the correct architecture; end users do not need Python or Inno Setup.

## Firmware source

The phone firmware source is in `firmware/Hackman3DLayerShot`. The DJI firmware
source is in `firmware/Hackman3DLayerShotDJI` and is built with ESP-IDF. Both
target an ESP32-C3 with 4 MB flash. The desktop app embeds both ready-to-flash
images and chooses the correct one from the camera selection.

## Third-party components

The Windows x64 application uses
[Espressif esptool 5.3.1](https://github.com/espressif/esptool/tree/v5.3.1);
the x86 compatibility application embeds the Python implementation of esptool
4.8.1. The GPL licence is included in
`src/hackman_layershot/assets/esptool-LICENSE.txt`. The Windows x86 interface
uses the last official LGPL PySide2 release supporting 32-bit Windows, while
the other builds use PySide6. The main Python and Qt dependencies are listed in
`pyproject.toml` and `build_windows.ps1`.

DJI camera support is based on DJI's official
[Osmo GPS Controller Demo](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo).
Its compatibility list covers Osmo Action 4, Action 5 Pro, Action 6 and Osmo
360. The upstream licence is preserved in
`firmware/Hackman3DLayerShotDJI/DJI-LICENSE.txt`.

## Support

LayerShot is provided free of charge. Donations, feedback and follows on
HackMan3D social channels are welcome through the permanent application header.

Created, designed and coded by HackMan3D.

This repository is currently private. No redistribution license is granted until
a `LICENSE` file is added.
