param(
    [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") {
    throw "Guardian.exe must be built on Windows. Current OS is not Windows."
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $ProjectRoot ".build-venv"
$Release = Join-Path $ProjectRoot "release\Guardian-v0.7-Windows"
$ExeSource = Join-Path $ProjectRoot "dist\Guardian.exe"
$ExeTarget = Join-Path $Release "Guardian.exe"

Write-Host "Guardian v0.7 Windows build" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "The Windows Python launcher 'py' is required on the BUILD machine. It is not required on the TEST or END-USER machine."
}

if (Test-Path $Venv) {
    Remove-Item -Recurse -Force $Venv
}

& py -3 -m venv $Venv
$Python = Join-Path $Venv "Scripts\python.exe"

& $Python -m pip install --upgrade "pip==24.2" "setuptools==75.1.0" "wheel==0.44.0"
& $Python -m pip install .
& $Python -m pip install "pyinstaller==6.10.0"
& $Python -m PyInstaller --clean --noconfirm guardian.spec

if (-not (Test-Path $ExeSource)) {
    throw "PyInstaller did not create dist\Guardian.exe"
}

Copy-Item -Force $ExeSource $ExeTarget

Write-Host "Built: $ExeTarget" -ForegroundColor Green
& $ExeTarget version
if ($LASTEXITCODE -ne 0) {
    throw "Guardian.exe version check failed with exit code $LASTEXITCODE"
}

# Produce release checksums after the executable exists.
$ChecksumFile = Join-Path $Release "RELEASE_CHECKSUMS.txt"
$Files = @(
    "Guardian.exe",
    "guardian_policy.json",
    "Guardian_Visual_Demo.html",
    "LICENSE.txt",
    "samples\clean.py",
    "samples\hold_file_write.py",
    "samples\reject_unsafe.py",
    "samples\missing_manifest.py"
)

$Lines = foreach ($Relative in $Files) {
    $Path = Join-Path $Release $Relative
    if (-not (Test-Path $Path)) {
        throw "Missing release file: $Relative"
    }
    $Hash = (Get-FileHash -Algorithm SHA256 $Path).Hash.ToLowerInvariant()
    "$Hash  $Relative"
}
$Lines | Set-Content -Encoding UTF8 $ChecksumFile

if (-not $SkipValidation) {
    & (Join-Path $Release "scripts\VALIDATE_WINDOWS_RELEASE.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Windows release validation failed with exit code $LASTEXITCODE"
    }
}

Write-Host ""
Write-Host "Guardian v0.7 build completed." -ForegroundColor Green
Write-Host "Release folder: $Release"
