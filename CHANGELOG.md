# Changelog

## 1.2.7 — 2026-07-27

- Reads each printer's webcam configuration directly from Moonraker.
- Prevents the Fluidd interface from being mistaken for a camera stream.
- Adds an **Activate camera in Klipper** button when no webcam is registered.
- Detects the built-in Creality WebRTC service used by K2 and SparkX printers
  and registers it through Moonraker's official webcam API.
- Keeps printer configuration files untouched and reports when no active
  camera service is available.

## 1.2.6 — 2026-07-27

- Added automatic Wi-Fi recovery to every ESP32-C3 firmware profile.
- Added an optional fixed ESP address with automatic gateway, netmask and DNS
  detection on macOS and Windows.
- Added a local availability scan and a final conflict check immediately
  before flashing the ESP32.
- The setup access point remains available while LayerShot retries the saved
  2.4 GHz network every ten seconds.

## 1.2.5 — 2026-07-27

- Correctly reconstructs tiled iPhone HEIC/HEIF photos before rendering.
- Prevents FFmpeg from using a single 512×512 HEIC tile as the full frame.
- Uses the same full-resolution HEIC conversion for the preview and video.
- Leaves all original photos untouched by using temporary converted frames.

## 1.2.4 — 2026-07-26

- Detects obsolete firmware on each connected LayerShot ESP32.
- Displays the installed and available firmware versions.
- Provides a direct action to open Installation and update the ESP32.
- Keeps quick installation on the latest bundled firmware by default.
- Adds an optional advanced selector for firmware from older official releases.
- Reads the latest firmware catalogue directly from GitHub, allowing firmware
  updates without requiring a new desktop application release.
- Shows both the saved printer name and its network address in the ESP32 panel.
- Refreshes ESP32 status silently without flashing between Connected and
  Connecting.

## 1.2.3 — 2026-07-26

- Fixed the timelapse preview for iPhone photos with embedded orientation
  metadata.
- The preview and generated video now apply the same phone orientation before
  the selected rotation, crop and aspect-ratio settings.

## 1.2.2 — 2026-07-26

### Stable multi-ESP addressing

- The application now keeps each ESP's Bonjour `.local` hostname as its
  permanent identity instead of replacing it with a temporary DHCP address.
- ESP selectors display both the stable hostname and the current numeric IP.
- Hostname checks prevent a missing ESP from being silently replaced by a
  different LayerShot device found on the same network.

## 1.2.1 — 2026-07-26

### Phone shutter timer hotfix

- Updated the autonomous phone firmware to 2.2.1.
- Made a short press on the physical ESP32 BOOT button respect the configured
  1–5 second shutter delay, matching layer changes and software shutter tests.

## 1.2.0 — 2026-07-26

### Extended Bluetooth camera compatibility

- Added generic Bluetooth HID shutter profiles for Volume +, Volume −, Enter
  and Space.
- Added guidance for Samsung Galaxy, Google Pixel, Xiaomi/Redmi/Poco,
  OnePlus/Oppo/Realme, Huawei/Honor, Sony Xperia, Motorola, Nokia and ASUS
  camera applications.
- Added support for compatible iPad, webcam, kiosk, stop-motion and tethering
  applications with configurable capture shortcuts.
- Updated the autonomous phone firmware to 2.2.0 and stored the selected HID
  command in the ESP32.
- Added clear documentation about proprietary Canon, Nikon, Sony, Fujifilm,
  Panasonic and OM System Bluetooth remote protocols.
- Fixed ESP discovery on macOS with Bonjour-based detection, stale-IP recovery
  and an editable manual address fallback.
- Made the phone firmware's test-shutter command use the configured 1–5 second
  delay, so the timer can be verified before starting a print.
- Timer changes are now sent immediately to an already configured phone
  firmware; reflashing is no longer required just to change the delay.

## 1.1.0 — 2026-07-26

### Desktop application

- Added one guided installation flow shared by macOS and 32/64-bit Windows.
- Installation sections now unlock only after the preceding step is complete.
- Added visible application version information and GitHub update checks.
- Added independent discovery and control of multiple LayerShot ESP32 devices.
- Made the ESP dashboard open immediately using the selected device address.
- Corrected printer selection during provisioning when several printers exist.
- Added printer-derived ESP hostnames such as
  `hackman-layershot-studiosparkx.local`.
- Added an explicit **Preparing / calibration** printer state.

### Cameras and firmware

- Added GoPro support through the official Open GoPro Bluetooth API.
- Added experimental Insta360 GPS Remote emulation.
- Retained phone Bluetooth HID and validated DJI Osmo Action support.
- Added a 1–5 second shutter delay, with 3 seconds selected by default.
- Displayed the stored delay in the ESP status panel.
- Added matching pairing, shutter, LED and forget-camera controls.

### Timelapse

- Added more output formats and codecs.
- Added landscape, square, portrait and social-media crop presets.
- Added a live first-frame framing preview.
- Proposed a generic output name directly in the selected photo folder.
- Bundled FFmpeg in packaged applications.

### Documentation and distribution

- Added ready-to-install macOS and combined 32/64-bit Windows downloads.
- Added standalone recovery firmware for phone, DJI, GoPro and Insta360.
- Added documented security-warning workarounds for unsigned builds.
- Added sanitized screenshots using fictitious names and reserved IP addresses.
- Expanded compatibility, installation, pairing, autonomous operation, privacy
  and troubleshooting documentation.
