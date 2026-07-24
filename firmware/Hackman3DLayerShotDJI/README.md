# Hackman3D LayerShot — DJI firmware

This ESP-IDF firmware adds shutter-only support for DJI Osmo Action 4,
Osmo Action 5 Pro, Osmo Action 6 and Osmo 360 cameras. It uses DJI's
published R SDK Bluetooth protocol and keeps the same autonomous Moonraker
layer monitoring, local dashboard, USB provisioning and BOOT-button controls
as the smartphone firmware.

The DJI protocol and reference implementation are derived from DJI's official
`Osmo-GPS-Controller-Demo`. See `DJI-LICENSE.txt` and the upstream repository:

https://github.com/dji-sdk/Osmo-GPS-Controller-Demo

Build with ESP-IDF 5.5:

```sh
idf.py set-target esp32c3
idf.py build
esptool.py --chip esp32c3 merge-bin -o Hackman3DLayerShotDJI.bin \
  --flash-mode dio --flash-size 4MB \
  0x0 build/bootloader/bootloader.bin \
  0x8000 build/partition_table/partition-table.bin \
  0x10000 build/hackman3d_layershot_dji.bin
```
