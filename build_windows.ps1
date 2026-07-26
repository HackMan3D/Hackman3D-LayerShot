$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

# Native x64 application.
if (-not (Test-Path ".venv-windows")) { py -3.12-64 -m venv .venv-windows }
& ".venv-windows\Scripts\python.exe" -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
Remove-Item build -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item dist -Recurse -Force -ErrorAction SilentlyContinue
$env:LAYERSHOT_BUILD_ARCH = "x64"
& ".venv-windows\Scripts\python.exe" -m PyInstaller --noconfirm --clean "Hackman3D LayerShot.spec"
if ($LASTEXITCODE -ne 0) { throw "Windows x64 build failed." }

# Native x86 application for 32-bit Windows. PySide2 is the last official
# LGPL Qt for Python release that supports Windows x86.
if (-not (Test-Path ".venv-windows-x86")) {
    py -3.10-32 -m venv .venv-windows-x86
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.10 32-bit is required for the Windows x86 build."
    }
}
& ".venv-windows-x86\Scripts\python.exe" -m pip install `
    "PySide2==5.15.2.1" "pyserial>=3.5,<4" "esptool==4.8.1" `
    "cryptography==3.4.8" "pyinstaller>=6.8,<7" "imageio-ffmpeg==0.6.0"
if ($LASTEXITCODE -ne 0) { throw "Windows x86 dependency installation failed." }
Remove-Item build -Recurse -Force -ErrorAction SilentlyContinue
$env:LAYERSHOT_BUILD_ARCH = "x86"
& ".venv-windows-x86\Scripts\python.exe" -m PyInstaller --noconfirm --clean "Hackman3D LayerShot.spec"
if ($LASTEXITCODE -ne 0) { throw "Windows x86 build failed." }
Remove-Item Env:LAYERSHOT_BUILD_ARCH

$InnoCompiler = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $InnoCompiler) {
    throw "Inno Setup 7 is required to create the Windows installer. Install it from https://jrsoftware.org/isdl.php"
}

New-Item releases -ItemType Directory -Force | Out-Null
Remove-Item "releases\Hackman3D-LayerShot-Windows-Setup-1.2.4.exe" -Force -ErrorAction SilentlyContinue
& $InnoCompiler "installer\windows\Hackman3D-LayerShot.iss"
if ($LASTEXITCODE -ne 0) { throw "Windows installer creation failed." }
Write-Host "Created releases\Hackman3D-LayerShot-Windows-Setup-1.2.4.exe"
