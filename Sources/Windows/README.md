# Hackman3D LayerShot for Windows

Native Windows application built with .NET 8 WinForms. A self-contained publish produces an executable that does not require a separate .NET installation.

## Ready-to-run downloads

End users do not need the .NET SDK or Arduino IDE:

- [Windows x64 release](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.4.1/Hackman3D-LayerShot-Windows-x64-0.4.1.zip)
- [Windows ARM64 release](https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/v0.4.1/Hackman3D-LayerShot-Windows-ARM64-0.4.1.zip)

The release packages include `esptool.exe` and the matching firmware binaries. Keep the executable and its `Resources` directory together. Firmware installation is performed from inside Hackman3D LayerShot.

## Build

```powershell
dotnet publish .\Hackman3D.LayerShot.Windows\Hackman3D.LayerShot.Windows.csproj `
  -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
```

Replace `win-x64` with `win-arm64` for Windows on ARM.

## Additional development tools

Custom development builds expect the following files in a `Resources` directory next to the executable:

- `esptool.exe` and the firmware binaries for USB flashing;
- `ffmpeg.exe` for video export.

Official release packages already include the firmware flashing components. Video export requires `ffmpeg.exe`; without it, printer monitoring, firmware installation, and network configuration remain available.

## Architectures

- `win-x64`: Windows PCs with Intel or AMD processors;
- `win-arm64`: Windows ARM PCs and Windows 11 ARM virtual machines, including Parallels on Apple Silicon Macs.
