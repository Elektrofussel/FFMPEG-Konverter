Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

& (Join-Path $PSScriptRoot "build_exe.ps1")
& (Join-Path $PSScriptRoot "build_installer.ps1")

$Version = (Get-Content (Join-Path $ProjectRoot "VERSION") -Raw).Trim()
$PortableDir = Join-Path $ProjectRoot "dist\FFmpegConverter"
$PortableZip = Join-Path $ProjectRoot ("dist-installer\FFmpegConverter-Portable-{0}.zip" -f $Version)

if (Test-Path $PortableZip) {
    Remove-Item $PortableZip -Force
}

Compress-Archive -Path (Join-Path $PortableDir "*") -DestinationPath $PortableZip -CompressionLevel Optimal

Write-Host ""
Write-Host "Release artifacts:"
Write-Host "  $(Join-Path $ProjectRoot ("dist-installer\FFmpegConverter-Setup-{0}.exe" -f $Version))"
Write-Host "  $PortableZip"
