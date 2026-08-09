$RepoRoot = Split-Path -Parent $PSScriptRoot
$Frozen = Join-Path $RepoRoot "frozen"
Get-ChildItem -Path $Frozen -Recurse -File | ForEach-Object {
    $_.IsReadOnly = $true
    Write-Host "READ-ONLY $($_.FullName)"
}
Write-Host "Frozen files are now marked read-only. Hash verification remains the authoritative protection check."
