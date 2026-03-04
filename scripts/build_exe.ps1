Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

Write-Host "Project root: $ProjectRoot"

if (!(Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment (.venv)..."
    py -3 -m venv .venv
}

$Py = (Resolve-Path ".venv\Scripts\python.exe").Path

Write-Host "Installing runtime dependencies..."
& $Py -m pip install --upgrade pip
& $Py -m pip install -r requirements.txt

Write-Host "Installing build dependencies..."
& $Py -m pip install -r requirements-build.txt

Write-Host "Cleaning previous build outputs..."
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist\FFmpegConverter") { Remove-Item "dist\FFmpegConverter" -Recurse -Force }

Write-Host "Building EXE with PyInstaller..."
& $Py -m PyInstaller --noconfirm --clean "ffmpeg_konverter.spec"

$OutDir = Join-Path $ProjectRoot "dist\FFmpegConverter"
if (!(Test-Path $OutDir)) {
    throw "Build failed: output directory missing: $OutDir"
}

Write-Host ""
Write-Host "Build successful:"
Write-Host "  $OutDir"
