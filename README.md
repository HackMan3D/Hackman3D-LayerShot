# Hackman3D LayerShot

[![Latest release](https://img.shields.io/github/v/release/HackMan3D/Hackman3D-LayerShot?style=flat-square&label=Release&color=0A84FF)](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/latest)
![Platforms](https://img.shields.io/badge/Platforms-macOS%20%7C%20Windows-0A84FF?style=flat-square)
![Hardware](https://img.shields.io/badge/Hardware-ESP32--C3-00A6A6?style=flat-square)
![Firmware](https://img.shields.io/badge/Firmware-Arduino%20%7C%20ESP--IDF-00979D?style=flat-square)
![Cameras](https://img.shields.io/badge/Cameras-iPhone%20%7C%20Android%20%7C%20DJI%20%7C%20GoPro-7B61FF?style=flat-square)
![Source](https://img.shields.io/badge/Source-Available-39A845?style=flat-square)
[![GitHub stars](https://img.shields.io/github/stars/HackMan3D/Hackman3D-LayerShot?style=flat-square&logo=github&label=Stars)](https://github.com/HackMan3D/Hackman3D-LayerShot/stargazers)
[![Downloads](https://img.shields.io/github/downloads/HackMan3D/Hackman3D-LayerShot/total?style=flat-square&logo=github&label=Downloads)](https://github.com/HackMan3D/Hackman3D-LayerShot/releases)
[![Views](https://hits.sh/github.com/HackMan3D/Hackman3D-LayerShot.svg?style=flat-square&label=Views&color=0A84FF)](https://github.com/HackMan3D/Hackman3D-LayerShot)

Hackman3D LayerShot turns a small ESP32-C3 into an autonomous Bluetooth camera
shutter for 3D-printing timelapses. It detects layer changes through Moonraker
and triggers an iPhone, Android phone, DJI camera, GoPro or selected
experimental Insta360 camera.

No iPhone application is required. Once the ESP32 has been configured, the Mac
or PC application can be closed during the entire print.

![LayerShot printer dashboard](docs/images/printer-dashboard.png)

## Download — version 1.2.8

No compilation or Arduino IDE setup is required:

- [Download for macOS — Apple Silicon](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v1.2.8/Hackman3D-LayerShot-macOS-1.2.8.zip)
- [Download the Windows installer — 32-bit and 64-bit](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v1.2.8/Hackman3D-LayerShot-Windows-Setup-1.2.8.exe)
- [Phone firmware for ESP32-C3](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v1.2.8/Hackman3D-LayerShot-ESP32-C3-Phone.bin)
- [DJI firmware for ESP32-C3](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v1.2.8/Hackman3D-LayerShot-ESP32-C3-DJI.bin)
- [GoPro firmware for ESP32-C3](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v1.2.8/Hackman3D-LayerShot-ESP32-C3-GoPro.bin)
- [Experimental Insta360 firmware for ESP32-C3](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v1.2.8/Hackman3D-LayerShot-ESP32-C3-Insta360-Experimental.bin)

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

![Guided printer installation](docs/images/guided-installation.png)

## What is new in 1.2.8

- adds an always-available **Activate / repair camera in Klipper** action;
- restores Moonraker camera registration after a Creality factory reset;
- supports K2 printers whose WebRTC service remains active but no longer serves
  its built-in viewer page;
- preserves the native Creality viewer on printers such as SparkX and uses the
  LayerShot fallback player only when required;
- reads each printer's webcam configuration directly from Moonraker;
- activates the built-in Creality K2 or SparkX camera in Klipper with one
  button when the stream exists but is not registered;
- never displays the Fluidd dashboard as if it were a camera;
- automatically reconnects every ESP firmware to Wi-Fi after an interruption;
- offers an optional fixed ESP address with an availability check;
- correctly reconstructs tiled iPhone HEIC and HEIF photos before rendering;
- macOS and Windows use the same interface, features and visible version.

## Camera compatibility

The Installation page clearly shows these details before installing the
matching firmware:

| Choice in LayerShot | Compatible devices | How the shutter works | Important requirement |
|---|---|---|---|
| iPhone | iPhones supporting Bluetooth keyboard/remote volume keys | Bluetooth HID `Volume +` | Keep Apple's Camera app open |
| Android | Phones whose camera app can assign a volume key to the shutter | Bluetooth HID `Volume +` | Enable “volume button = shutter” when required; support depends on the phone and camera app |
| Generic HID — Volume + | Camera and tethering applications accepting Bluetooth Volume + | Bluetooth HID `Volume +` | Assign Volume + to Capture/Shutter and test |
| Generic HID — Volume − | Camera and tethering applications accepting Bluetooth Volume − | Bluetooth HID `Volume −` | Assign Volume − to Capture/Shutter and test |
| Generic HID — Enter | Camera, webcam, kiosk and tethering software accepting Enter | Bluetooth keyboard `Enter` | Map Enter to Capture/Shutter |
| Generic HID — Space | Camera, webcam, stop-motion and tethering software accepting Space | Bluetooth keyboard `Space` | Map Space to Capture/Shutter |
| DJI | DJI Osmo Action 4, Osmo Action 5 Pro, Osmo Action 6 and Osmo 360 | Official DJI BLE camera protocol | Put the camera in Photo mode and approve pairing on its screen |
| GoPro | HERO9 Black, HERO10 Black/Bones, HERO11 Black/Mini and HERO12 Black; newer Open GoPro models require LayerShot validation | Official Open GoPro BLE API | Put the camera in Photo mode and open its Connect Device screen |
| Insta360 — experimental | X3, X4, X5, Ace, Ace Pro and Ace Pro 2 families | Experimental emulation of an Insta360 GPS Bluetooth remote | Compatibility depends on the exact camera firmware; test before printing |

> **DJI validation:** DJI camera support has been successfully validated by a
> LayerShot user on compatible hardware. Testing the shutter before a long
> print is still recommended.

![Camera compatibility and shutter delay](docs/images/camera-selection.png)

DJI Osmo Action 3 and older models are not listed as compatible by the official
protocol demo used by this project. Smartphone compatibility can vary because
manufacturers are free to change how their Camera app handles volume keys.

### Extended phone, tablet and application coverage

The four generic HID profiles make LayerShot usable with many camera
applications on Samsung Galaxy, Google Pixel, Xiaomi, Redmi, Poco, OnePlus,
Oppo, Realme, Huawei, Honor, Sony Xperia, Motorola, Nokia and ASUS devices.
They also cover iPad camera applications plus desktop webcam, stop-motion,
kiosk and tethering software when that software lets the user map Volume +,
Volume −, Enter or Space to the shutter.

This is genuine Bluetooth HID compatibility, not a model-name promise: always
use **Test camera shutter** before a print.

### Interchangeable-lens cameras

Canon BR-E1, Nikon ML-L7, Sony RMT-P1BT, Fujifilm TG-BT1, Panasonic
DMW-BTR1 and OM System/Olympus RM-WR1 remotes do not share a universal
Bluetooth shutter protocol. Their manufacturers' desktop SDKs also cannot run
inside an ESP32-C3. These camera families are therefore not labelled compatible
until a lawful embedded protocol and physical-camera validation are available.
For the broadest future DSLR/mirrorless coverage, an isolated wired-shutter
accessory is the reliable route and can be added without changing autonomous
layer detection.

## What LayerShot does

- controls supported phone Camera apps through Bluetooth HID (`Volume +`);
- controls compatible DJI cameras through the official DJI BLE protocol;
- controls compatible GoPro cameras through the official Open GoPro BLE API;
- offers experimental Insta360 Bluetooth-remote support for popular models;
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

## Printer dashboard

Every configured printer has its own card. LayerShot shows the detected model,
network endpoint, G-code file, current state, layer count and progress. A printer
that is homing, heating or calibrating is reported as **Preparing / calibration**
instead of standby. Multiple printers are monitored independently, and camera
previews remain local when the printer exposes a compatible stream.

The documentation screenshots intentionally use the reserved example networks
`192.0.2.0/24`. They contain no real printer address, Wi-Fi name or password.

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

The next installation section stays locked until the current section has been
completed. When several printers are saved, the printer selected in step 1 is
the one provisioned into the ESP. Its display name also creates a unique local
address: `Studio SparkX` becomes
`http://hackman-layershot-studiosparkx.local`.

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

### GoPro

1. Select **Photo** mode and open the GoPro's **Connections > Connect Device**
   screen.
2. Start the GoPro search in LayerShot or hold **BOOT** for three seconds.
3. Keep the camera nearby and approve pairing if requested.
4. Test the shutter. LayerShot stores the Bluetooth bond and reconnects
   automatically.

### Insta360 — experimental

1. Open **Settings > Bluetooth Remote** on the camera.
2. Select **Insta360 GPS Remote**, then start pairing in LayerShot.
3. Keep the camera in Photo mode and test the shutter before printing.
4. Report the exact camera model and firmware version when providing feedback.

## LED colours

| Colour | Meaning |
|---|---|
| Red | Powered, but the selected camera is not connected |
| Flashing blue | Bluetooth pairing mode |
| Green | Camera connected |
| Purple flash | Camera shutter command sent |

## Autonomous operation

The ESP32 directly monitors the configured printer. The desktop application and
computer do not need to remain open while printing. The ESP32 web dashboard
uses the selected printer name. For example, a printer named `SparkX i7` is
available at:

`http://hackman-layershot-sparkxi7.local`

Each ESP therefore has a distinct, readable address. Some routers publish a
numbered `.lan` address instead. The desktop application
automatically searches for the LayerShot device and remembers the working local
address.

## ESP32 status and multiple devices

The ESP32 page discovers LayerShot boards on the local network and lists each
one with its IP address, assigned printer and camera type. Selecting a device
updates its firmware, Wi-Fi, Bluetooth, printer, layer and shutter-delay
information. Pairing, shutter, LED and forget-camera controls target only the
selected board.

![Multiple LayerShot ESP32 devices](docs/images/multi-esp-controls.png)

## Create a timelapse

1. Import the folder containing the camera photos.
2. Keep the proposed output name in the source folder or edit it.
3. Select frame rate, output format, aspect ratio, framing, crop position,
   rotation, background, quality and codec.
4. Use the first-frame preview to check how the selected social-media format
   will be filled.
5. Start the video export.

LayerShot uses its bundled FFmpeg when available and can also use a system
installation. Landscape, square, portrait, Story/Reel and other common social
formats can be created without modifying the source photos.

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

## Privacy and local operation

- printer and ESP communication stays on the local network;
- the desktop application does not upload camera previews or Wi-Fi credentials;
- a Wi-Fi password requested from macOS or Windows is sent only to the ESP being
  configured;
- autonomous layer detection continues after the desktop application is closed;
- all screenshots in this repository use fictitious names, reserved
  documentation IP addresses and masked example credentials.

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

### Windows cannot open the ESP32 serial port

- close Arduino IDE, serial monitors and any other LayerShot instance;
- reconnect the ESP32 with a USB data cable and press **Refresh ports**;
- select the COM port shown by Windows Device Manager;
- if access is still denied, restart Windows and run the official installer
  build instead of a copied development folder;
- hold **BOOT**, briefly press **RESET**, then release **BOOT** to enter the
  ESP32-C3 download mode when automatic reset is unavailable.

### The shutter fires before the print head reaches its photo position

Select a delay from 1 to 5 seconds in the camera step. The default is 3 seconds,
which gives the slicer's smooth-timelapse movement time to finish before the
Bluetooth command is sent. The saved value is visible on the ESP32 page.

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
application version 1.2.3. The Windows script requires Python 3.12 x64,
Python 3.10 x86 and Inno Setup 7. It produces one installer that automatically
selects the correct architecture; end users do not need Python or Inno Setup.

## Firmware source

The phone firmware source is in `firmware/Hackman3DLayerShot`. The DJI firmware
source is in `firmware/Hackman3DLayerShotDJI` and is built with ESP-IDF. GoPro
and Insta360 sources are in `firmware/Hackman3DLayerShotGoPro` and
`firmware/Hackman3DLayerShotInsta360`. They target an ESP32-C3 with 4 MB flash.
The desktop app embeds the ready-to-flash images and chooses the correct one
from the camera selection.

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

GoPro support follows GoPro's official
[Open GoPro BLE API](https://gopro.github.io/OpenGoPro/docs/ble/). Experimental
Insta360 remote emulation is derived from Patrick Chwalek's MIT-licensed
`insta360_ble_esp32` research; its licence is preserved alongside the firmware.

## Support

LayerShot is provided free of charge. Donations, feedback and follows on
HackMan3D social channels are welcome through the permanent application header.

Created, designed and coded by HackMan3D.

Third-party licences are preserved next to the components they cover. See the
repository licence files before redistributing modified builds.
