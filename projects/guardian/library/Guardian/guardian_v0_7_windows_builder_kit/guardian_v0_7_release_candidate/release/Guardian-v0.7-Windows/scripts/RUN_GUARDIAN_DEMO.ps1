$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Release = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Guardian = Join-Path $Release "Guardian.exe"
$Demo = Join-Path $Release "Guardian_Visual_Demo.html"
$Validator = Join-Path $Release "scripts\VALIDATE_WINDOWS_RELEASE.ps1"

if (-not (Test-Path $Guardian)) {
    Write-Host "Guardian.exe is missing from this release folder." -ForegroundColor Red
    Write-Host "Build it with BUILD_WINDOWS.ps1 or download the completed Windows release."
    Read-Host "Press Enter to close"
    exit 10
}

if (Test-Path $Demo) {
    Start-Process $Demo
}

Write-Host "Running the real Guardian executable against the four sample artifacts..." -ForegroundColor Cyan
& $Validator
$Exit = $LASTEXITCODE

Write-Host ""
if ($Exit -eq 0) {
    Write-Host "The real executable passed all sample and ledger checks." -ForegroundColor Green
    Write-Host "The browser window explains the same workflow visually."
} else {
    Write-Host "Validation failed. Review validation-output before using the release." -ForegroundColor Red
}

Read-Host "Press Enter to close"
exit $Exit
