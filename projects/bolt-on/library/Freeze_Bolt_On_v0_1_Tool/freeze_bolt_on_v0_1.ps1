param()

$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Text
    )
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $encoding)
}

Write-Host ""
Write-Host "============================================================"
Write-Host "FREEZE BOLT-ON DEMONSTRATOR v0.1"
Write-Host "============================================================"

$RepoRoot = (git rev-parse --show-toplevel 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($RepoRoot)) {
    throw "Run this script from inside the canonical Git repository."
}

$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
$DevRoot = Join-Path $RepoRoot "development\bolt_on_demonstrator_v0_1"
$FrozenParent = Join-Path $RepoRoot "frozen\bolt_on"
$FrozenRoot = Join-Path $FrozenParent "v0.1"
$TempRoot = Join-Path $FrozenParent "v0.1.__building__"
$ToolsRoot = Join-Path $RepoRoot "tools"
$V02Root = Join-Path $RepoRoot "development\bolt_on_demonstrator_v0_2"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$Required = @(
    (Join-Path $DevRoot "host\ordinary_host.py"),
    (Join-Path $DevRoot "adapter\bolt_on_adapter.py"),
    (Join-Path $DevRoot "governance\natural_math_shadow_governance.py"),
    (Join-Path $DevRoot "memory\cntm_shadow_memory.py"),
    (Join-Path $DevRoot "qualification\integrated_adversarial_qualification.py"),
    (Join-Path $RepoRoot "tools\verify_frozen.py")
)

foreach ($Path in $Required) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required file not found: $Path"
    }
}

$Status = git -C $RepoRoot status --porcelain
if ($LASTEXITCODE -ne 0) {
    throw "Git status failed."
}
if (-not [string]::IsNullOrWhiteSpace(($Status -join "`n"))) {
    throw "The Git working tree is not clean. Commit or remove pending changes before freezing v0.1."
}

if (Test-Path -LiteralPath $FrozenRoot) {
    throw "The frozen release already exists: $FrozenRoot`nNothing was overwritten."
}

if (Test-Path -LiteralPath $TempRoot) {
    Remove-Item -LiteralPath $TempRoot -Recurse -Force
}

Write-Host ""
Write-Host "[1/7] Running the complete Stage 1-5 test suite..."
& python -m unittest discover `
    -s (Join-Path $DevRoot "tests") `
    -p "test_*.py" `
    -v
if ($LASTEXITCODE -ne 0) {
    throw "The Stage 1-5 tests failed. Release was not created."
}

Write-Host ""
Write-Host "[2/7] Running the integrated Stage 5 qualification..."
$QualificationOutput = & python (Join-Path $DevRoot "qualification\integrated_adversarial_qualification.py")
$QualificationOutput | Write-Host
if ($LASTEXITCODE -ne 0 -or
    ($QualificationOutput -join "`n") -notmatch "STAGE 5 INTEGRATED QUALIFICATION:\s+PASS") {
    throw "Stage 5 qualification did not pass. Release was not created."
}

Write-Host ""
Write-Host "[3/7] Verifying the existing frozen foundations..."
& python (Join-Path $RepoRoot "tools\verify_frozen.py")
if ($LASTEXITCODE -ne 0) {
    throw "Existing frozen verification failed. Release was not created."
}

Write-Host ""
Write-Host "[4/7] Copying the qualified demonstrator into the frozen release..."
New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null

$SourceFiles = Get-ChildItem -LiteralPath $DevRoot -Recurse -File | Where-Object {
    $_.FullName -notmatch "[\\/]__pycache__[\\/]" -and
    $_.Extension -ne ".pyc"
}

foreach ($File in $SourceFiles) {
    $Relative = $File.FullName.Substring($DevRoot.Length).TrimStart("\", "/")
    $Destination = Join-Path $TempRoot $Relative
    $DestinationDirectory = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null
    Copy-Item -LiteralPath $File.FullName -Destination $Destination -Force
}

$Commit = (git -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Could not identify the current Git commit."
}

$ReleaseRecord = @"
BOLT-ON DEMONSTRATOR v0.1 — FROZEN RELEASE RECORD
================================================

Release: bolt-on-demonstrator-v0.1
Source commit: $Commit
Release mode: SHADOW
Intervention authority: NONE
Qualified test count: 76
Integrated campaigns: 6
Fault injections: 6
Attach-detach cycles: 5
Unauthorized interventions: 0

Campaign digest:
9ff12f5a0776c93c11fe4d020bcaf8b756caff82c5f3a1076c23c6ed152f6eab

Shared memory digest:
6ba2c70e929777e37feeb6798aba39fc5f2e95b574e8872867f5e53017d66a73

QUALIFIED CLAIM
---------------
A deterministic shadow-only bolt-on can attach to an ordinary host, observe
it, produce replayable governance recommendations, preserve bounded evidence
memory, contain the tested evidence faults, and detach without modifying the
host or its frozen foundations.

CLAIM BOUNDARY
--------------
This release does not claim active control, production readiness,
compatibility with every external system, autonomous intervention, or zero
drift. Active bounded intervention belongs in v0.2 development.
"@

Write-Utf8NoBom -Path (Join-Path $TempRoot "RELEASE_RECORD.txt") -Text $ReleaseRecord

$ManifestPath = Join-Path $TempRoot "RELEASE_MANIFEST_SHA256.txt"
$ManifestLines = @()

$ReleaseFiles = Get-ChildItem -LiteralPath $TempRoot -Recurse -File |
    Where-Object { $_.FullName -ne $ManifestPath } |
    Sort-Object FullName

foreach ($File in $ReleaseFiles) {
    $Relative = $File.FullName.Substring($TempRoot.Length).TrimStart("\", "/")
    $Relative = $Relative.Replace("\", "/")
    $Hash = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $ManifestLines += "$Hash  $Relative"
}

Write-Utf8NoBom -Path $ManifestPath -Text (($ManifestLines -join "`n") + "`n")

Move-Item -LiteralPath $TempRoot -Destination $FrozenRoot

Write-Host ""
Write-Host "[5/7] Installing frozen-release verification tools..."
New-Item -ItemType Directory -Path $ToolsRoot -Force | Out-Null
Copy-Item `
    -LiteralPath (Join-Path $ScriptRoot "verify_bolt_on_v0_1.py") `
    -Destination (Join-Path $ToolsRoot "verify_bolt_on_v0_1.py") `
    -Force
Copy-Item `
    -LiteralPath (Join-Path $ScriptRoot "verify_all_frozen.py") `
    -Destination (Join-Path $ToolsRoot "verify_all_frozen.py") `
    -Force

Write-Host ""
Write-Host "[6/7] Marking the frozen release read-only..."
Get-ChildItem -LiteralPath $FrozenRoot -Recurse -File | ForEach-Object {
    $_.IsReadOnly = $true
}

Write-Host ""
Write-Host "[7/7] Opening the separate v0.2 development folder..."
if (-not (Test-Path -LiteralPath $V02Root)) {
    New-Item -ItemType Directory -Path $V02Root -Force | Out-Null
    $V02Readme = @"
# Bolt-On Demonstrator v0.2 — Development

This folder is reserved for bounded active-intervention development.

Do not edit the frozen v0.1 release. Begin v0.2 by importing or adapting only
the components explicitly needed for the next qualification campaign.
"@
    Write-Utf8NoBom -Path (Join-Path $V02Root "README.md") -Text $V02Readme
}

Write-Host ""
Write-Host "Running the new combined frozen verification..."
& python (Join-Path $ToolsRoot "verify_all_frozen.py")
if ($LASTEXITCODE -ne 0) {
    throw "Combined frozen verification failed."
}

Write-Host ""
Write-Host "============================================================"
Write-Host "BOLT-ON DEMONSTRATOR v0.1 FREEZE CREATED SUCCESSFULLY"
Write-Host "============================================================"
Write-Host "Frozen release: $FrozenRoot"
Write-Host "Source commit:  $Commit"
Write-Host ""
Write-Host "The files are created but not committed or tagged yet."
Write-Host "Run the Git commands shown in README_FREEZE.md."
