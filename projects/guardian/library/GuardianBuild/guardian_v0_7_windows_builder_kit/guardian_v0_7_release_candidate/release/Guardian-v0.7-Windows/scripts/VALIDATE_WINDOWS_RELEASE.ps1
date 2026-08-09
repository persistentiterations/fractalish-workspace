$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Release = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Guardian = Join-Path $Release "Guardian.exe"
$Policy = Join-Path $Release "guardian_policy.json"
$Samples = Join-Path $Release "samples"
$Output = Join-Path $Release "validation-output"
$Ledger = Join-Path $Output "guardian_validation_ledger.jsonl"
$ResultsPath = Join-Path $Output "WINDOWS_VALIDATION_RESULTS.json"

if (-not (Test-Path $Guardian)) {
    Write-Error "Guardian.exe is missing. Build or copy it into $Release first."
    exit 10
}

if (Test-Path $Output) {
    Remove-Item -Recurse -Force $Output
}
New-Item -ItemType Directory -Path $Output | Out-Null

# Record whether Python commands exist. Python is not used for validation.
$PythonChecks = [ordered]@{}
foreach ($Command in @("python", "py", "python3")) {
    $Resolved = Get-Command $Command -ErrorAction SilentlyContinue
    $PythonChecks[$Command] = if ($Resolved) { $Resolved.Source } else { $null }
}

# Generate a temporary validation key in memory.
$KeyBytes = New-Object byte[] 32
$RandomGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()

try {
    $RandomGenerator.GetBytes($KeyBytes)
}
finally {
    $RandomGenerator.Dispose()
}

$env:GUARDIAN_HMAC_KEY = ([System.BitConverter]::ToString($KeyBytes)).Replace("-", "")

$Checks = New-Object System.Collections.Generic.List[object]

function Add-Check {
    param(
        [string]$Name,
        [bool]$Passed,
        [object]$Detail
    )
    $Checks.Add([ordered]@{
        name = $Name
        passed = $Passed
        detail = $Detail
    })
}

function Run-GuardianJson {
    param(
        [string]$Name,
        [string[]]$Arguments,
        [int]$ExpectedExit,
        [string]$ExpectedOutcome
    )

    $OutFile = Join-Path $Output ($Name + ".json")
    $ErrFile = Join-Path $Output ($Name + ".stderr.txt")

    & $Guardian @Arguments 1> $OutFile 2> $ErrFile
    $Exit = $LASTEXITCODE

    $Payload = $null
    try {
        $Payload = Get-Content -Raw $OutFile | ConvertFrom-Json
    } catch {
        Add-Check $Name $false "Output was not valid JSON. Exit=$Exit"
        return
    }

    $Passed = ($Exit -eq $ExpectedExit) -and ($Payload.intake_outcome -eq $ExpectedOutcome)
    Add-Check $Name $Passed ([ordered]@{
        expected_exit = $ExpectedExit
        actual_exit = $Exit
        expected_outcome = $ExpectedOutcome
        actual_outcome = $Payload.intake_outcome
        slip_id = $Payload.slip_id
        file_fingerprint = $Payload.file_fingerprint
        policy_fingerprint = $Payload.policy_fingerprint
        signature_present = -not [string]::IsNullOrWhiteSpace($Payload.slip_signature)
    })
}

# Version.
$VersionOut = Join-Path $Output "version.json"
& $Guardian version 1> $VersionOut
$VersionExit = $LASTEXITCODE
$VersionPayload = Get-Content -Raw $VersionOut | ConvertFrom-Json
Add-Check "version" ($VersionExit -eq 0) $VersionPayload

# Embedded package integrity.
$IntegrityOut = Join-Path $Output "verify_installation.json"
& $Guardian verify-installation 1> $IntegrityOut
$IntegrityExit = $LASTEXITCODE
$IntegrityPayload = Get-Content -Raw $IntegrityOut | ConvertFrom-Json
Add-Check "verify-installation" (($IntegrityExit -eq 0) -and $IntegrityPayload.valid) $IntegrityPayload

# Policy.
$PolicyOut = Join-Path $Output "validate_policy.json"
& $Guardian validate-policy $Policy 1> $PolicyOut
$PolicyExit = $LASTEXITCODE
$PolicyPayload = Get-Content -Raw $PolicyOut | ConvertFrom-Json
Add-Check "validate-policy" (($PolicyExit -eq 0) -and $PolicyPayload.valid) $PolicyPayload

Run-GuardianJson "clean" @("--ledger", $Ledger, "scan", (Join-Path $Samples "clean.py"), "--json") 0 "Let In"
Run-GuardianJson "hold_file_write" @("--ledger", $Ledger, "scan", (Join-Path $Samples "hold_file_write.py"), "--json") 2 "Hold"
Run-GuardianJson "reject_unsafe" @("--ledger", $Ledger, "scan", (Join-Path $Samples "reject_unsafe.py"), "--json") 3 "Reject"
Run-GuardianJson "missing_manifest" @("--ledger", $Ledger, "scan", (Join-Path $Samples "missing_manifest.py"), "--json") 2 "Hold"

# Signed replay.
$ReplayOut = Join-Path $Output "ledger_replay.txt"
& $Guardian --ledger $Ledger replay 1> $ReplayOut 2>&1
$ReplayExit = $LASTEXITCODE
Add-Check "signed-ledger-replay" ($ReplayExit -eq 0) (Get-Content -Raw $ReplayOut)

# External release checksum.
$ExeHash = (Get-FileHash -Algorithm SHA256 $Guardian).Hash.ToLowerInvariant()
Add-Check "Guardian.exe-sha256" $true $ExeHash

$AllPassed = -not ($Checks | Where-Object { -not $_.passed })

$Result = [ordered]@{
    schema_version = "1.0"
    guardian_release = "0.7.0"
    tested_at_utc = [DateTime]::UtcNow.ToString("o")
    windows = [ordered]@{
        edition = [Environment]::OSVersion.VersionString
        architecture = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
        machine_name = $env:COMPUTERNAME
    }
    python_commands_observed = $PythonChecks
    python_was_used_for_validation = $false
    guardian_exe_sha256 = $ExeHash
    checks = $Checks
    all_passed = $AllPassed
}

$Result | ConvertTo-Json -Depth 12 | Set-Content -Encoding UTF8 $ResultsPath

Remove-Item Env:\GUARDIAN_HMAC_KEY -ErrorAction SilentlyContinue

Write-Host ""
if ($AllPassed) {
    Write-Host "Guardian v0.7 Windows validation PASSED." -ForegroundColor Green
    Write-Host "Results: $ResultsPath"
    exit 0
}

Write-Host "Guardian v0.7 Windows validation FAILED." -ForegroundColor Red
$Checks | Where-Object { -not $_.passed } | Format-Table
exit 1


