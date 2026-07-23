# Hackman3D LayerShot pour Windows

Application Windows native basée sur .NET 8 WinForms. La publication autonome génère un exécutable qui ne demande pas d’installation séparée de .NET.

## Compilation

```powershell
dotnet publish .\Hackman3D.LayerShot.Windows\Hackman3D.LayerShot.Windows.csproj `
  -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
```

Pour Windows ARM64, remplacez `win-x64` par `win-arm64`.

## Outils annexes

Les fichiers suivants peuvent être placés dans un dossier `Resources` à côté de l’exécutable :

- `esptool.exe` et les binaires du firmware pour le flash USB ;
- `ffmpeg.exe` pour l’export vidéo.

Sans ces fichiers, la surveillance des imprimantes et la configuration réseau restent disponibles ; l’application indique clairement quelle fonction facultative manque.

## Architectures

- `win-x64` : PC Windows Intel et AMD ;
- `win-arm64` : PC Windows ARM et machines virtuelles Windows 11 ARM, notamment sous Parallels sur Mac Apple Silicon.
