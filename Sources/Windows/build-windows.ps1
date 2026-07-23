$ErrorActionPreference = "Stop"

$project = Join-Path $PSScriptRoot "Hackman3D.LayerShot.Windows\Hackman3D.LayerShot.Windows.csproj"
$output = Join-Path $PSScriptRoot "Build\Windows-x64"

Write-Host "Building Hackman3D LayerShot for Windows x64..." -ForegroundColor Cyan

dotnet publish $project `
  --configuration Release `
  --runtime win-x64 `
  --self-contained true `
  -p:PublishSingleFile=true `
  -p:IncludeNativeLibrariesForSelfExtract=true `
  --output $output

$resources = Join-Path $PSScriptRoot "Resources"
if (Test-Path $resources) {
  Copy-Item $resources -Destination $output -Recurse -Force
}

Write-Host ""
Write-Host "Build complete:" -ForegroundColor Green
Write-Host $output
