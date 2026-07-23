# Hackman3D LayerShot for Windows

Native Windows application built with .NET 8 WinForms. A self-contained publish produces an executable that does not require a separate .NET installation.

## Build

```powershell
dotnet publish .\Hackman3D.LayerShot.Windows\Hackman3D.LayerShot.Windows.csproj `
  -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
```

Replace `win-x64` with `win-arm64` for Windows on ARM.

## Additional tools

The following files can be placed in a `Resources` directory next to the executable:

- `esptool.exe` and the firmware binaries for USB flashing;
- `ffmpeg.exe` for video export.

Without these files, printer monitoring and network configuration remain available. The application clearly reports which optional component is missing.

## Architectures

- `win-x64`: Windows PCs with Intel or AMD processors;
- `win-arm64`: Windows ARM PCs and Windows 11 ARM virtual machines, including Parallels on Apple Silicon Macs.
