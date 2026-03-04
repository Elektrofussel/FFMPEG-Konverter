param(
    [string]$Version = "",
    [switch]$SkipBuild,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = (Get-Content (Join-Path $ProjectRoot "VERSION") -Raw).Trim()
}
if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "Version is empty. Set VERSION file or pass -Version."
}

$SetupPath = Join-Path $ProjectRoot ("dist-installer\FFmpegConverter-Setup-{0}.exe" -f $Version)
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\FFmpeg Converter"
$AppDataDir = Join-Path $env:APPDATA "FFmpeg-Konverter"
$Uninstaller = Join-Path $InstallDir "unins000.exe"
$MarkerFile = Join-Path $AppDataDir "config.json"

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Get-UninstallEntry {
    $keys = Get-ChildItem "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall" -ErrorAction SilentlyContinue
    foreach ($k in $keys) {
        $p = Get-ItemProperty $k.PSPath -ErrorAction SilentlyContinue
        if ($p -and $p.DisplayName -like "FFmpeg Converter*") { return $p }
    }
    return $null
}

function Remove-PathIfExists([string]$PathValue) {
    if (Test-Path $PathValue) { Remove-Item $PathValue -Recurse -Force }
}

function Ensure-Marker([string]$Text) {
    New-Item -ItemType Directory -Path $AppDataDir -Force | Out-Null
    $obj = @{ test = $Text; timestamp = (Get-Date).ToString("s") } | ConvertTo-Json -Compress
    Set-Content -Path $MarkerFile -Value $obj -Encoding UTF8
}

function Run-Step([string]$Name, [scriptblock]$Action) {
    Write-Host "==> $Name"
    if ($DryRun) {
        Write-Host "    (dry-run)"
        return
    }
    & $Action
}

if (-not $SkipBuild) {
    Run-Step "Build installer" {
        & (Join-Path $PSScriptRoot "build_installer.ps1")
    }
}

Assert-True (Test-Path $SetupPath) "Setup not found: $SetupPath"

Run-Step "Cleanup previous install/appdata" {
    if (Test-Path $Uninstaller) {
        Start-Process -FilePath $Uninstaller -ArgumentList "/VERYSILENT","/NORESTART","/DELETEUSERDATA" -Wait
    }
    Remove-PathIfExists $InstallDir
    Remove-PathIfExists $AppDataDir
}

Run-Step "Install app (silent)" {
    Start-Process -FilePath $SetupPath -ArgumentList "/VERYSILENT","/NORESTART" -Wait
}

Run-Step "Validate install state" {
    Assert-True (Test-Path (Join-Path $InstallDir "FFmpegConverter.exe")) "Missing installed EXE."
    Assert-True (Test-Path (Join-Path $InstallDir "unins000.exe")) "Missing uninstaller."
    Assert-True (Test-Path $AppDataDir) "Missing appdata folder."
    $entry = Get-UninstallEntry
    Assert-True ($null -ne $entry) "Missing uninstall registry entry."
}

Run-Step "Prepare appdata marker for KEEP test" {
    Ensure-Marker "keep"
}

Run-Step "Uninstall with /KEEPUSERDATA" {
    Start-Process -FilePath $Uninstaller -ArgumentList "/VERYSILENT","/NORESTART","/KEEPUSERDATA" -Wait
}

Run-Step "Validate KEEP result" {
    Assert-True (Test-Path $AppDataDir) "AppData directory was removed but should be kept."
    Assert-True (Test-Path $MarkerFile) "Marker file was removed but should be kept."
    Assert-True (-not (Test-Path $InstallDir)) "Install directory still exists after uninstall."
}

Run-Step "Reinstall for DELETE test" {
    Start-Process -FilePath $SetupPath -ArgumentList "/VERYSILENT","/NORESTART" -Wait
    Ensure-Marker "delete"
}

Run-Step "Uninstall with /DELETEUSERDATA" {
    $u = Join-Path $InstallDir "unins000.exe"
    Assert-True (Test-Path $u) "Uninstaller missing before DELETE test."
    Start-Process -FilePath $u -ArgumentList "/VERYSILENT","/NORESTART","/DELETEUSERDATA" -Wait
}

Run-Step "Validate DELETE result" {
    Assert-True (-not (Test-Path $InstallDir)) "Install directory still exists after DELETE uninstall."
    Assert-True (-not (Test-Path $AppDataDir)) "AppData directory still exists after DELETE uninstall."
    $entry = Get-UninstallEntry
    Assert-True ($null -eq $entry) "Uninstall registry entry still exists."
}

Write-Host ""
Write-Host "Installer test passed for version $Version."
