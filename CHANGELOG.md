# Changelog

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
