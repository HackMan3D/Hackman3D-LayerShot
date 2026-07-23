$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (-not (Test-Path ".venv-windows")) { py -3.12 -m venv .venv-windows }
& ".venv-windows\Scripts\python.exe" -m pip install -e ".[dev]"
Remove-Item build -Recurse -Force -ErrorAction SilentlyContinue
& ".venv-windows\Scripts\python.exe" -m PyInstaller --noconfirm --clean "Hackman3D LayerShot.spec"
New-Item releases -ItemType Directory -Force | Out-Null
Compress-Archive -Path "dist\Hackman3D LayerShot\*" -DestinationPath "releases\Hackman3D-LayerShot-Windows-x64-0.5.1.zip" -Force
Write-Host "Created releases\Hackman3D-LayerShot-Windows-x64-0.5.1.zip"
