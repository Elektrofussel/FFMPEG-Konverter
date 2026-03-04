Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$AppDist = Join-Path $ProjectRoot "dist\FFmpegConverter\FFmpegConverter.exe"
if (!(Test-Path $AppDist)) {
    throw "Portable build missing. Run scripts/build_exe.ps1 first."
}

$Version = (Get-Content (Join-Path $ProjectRoot "VERSION") -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "VERSION file is empty."
}

$IsccCandidates = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)

$Iscc = $null
foreach ($candidate in $IsccCandidates) {
    if (Test-Path $candidate) {
        $Iscc = $candidate
        break
    }
}

if (-not $Iscc) {
    $Cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($Cmd) { $Iscc = $Cmd.Source }
}

if (-not $Iscc) {
    throw "Inno Setup (ISCC.exe) not found. Install Inno Setup 6 first."
}

Write-Host "Using ISCC: $Iscc"
Write-Host "Building installer version: $Version"

if (!(Test-Path "dist-installer")) {
    New-Item -ItemType Directory -Path "dist-installer" | Out-Null
}

& $Iscc "/DMyAppVersion=$Version" "installer\FFmpegConverter.iss"

$Expected = Join-Path $ProjectRoot ("dist-installer\FFmpegConverter-Setup-{0}.exe" -f $Version)
if (!(Test-Path $Expected)) {
    throw "Installer build finished, but expected output was not found: $Expected"
}

Write-Host ""
Write-Host "Installer successful:"
Write-Host "  $Expected"
