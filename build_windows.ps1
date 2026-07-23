$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (-not (Test-Path ".venv-windows")) { py -3.12 -m venv .venv-windows }
& ".venv-windows\Scripts\python.exe" -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
Remove-Item build -Recurse -Force -ErrorAction SilentlyContinue
& ".venv-windows\Scripts\python.exe" -m PyInstaller --noconfirm --clean "Hackman3D LayerShot.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
New-Item releases -ItemType Directory -Force | Out-Null
Compress-Archive -Path "dist\Hackman3D LayerShot\*" -DestinationPath "releases\Hackman3D-LayerShot-Windows-x64-0.5.2.zip" -Force
Write-Host "Created releases\Hackman3D-LayerShot-Windows-x64-0.5.2.zip"
