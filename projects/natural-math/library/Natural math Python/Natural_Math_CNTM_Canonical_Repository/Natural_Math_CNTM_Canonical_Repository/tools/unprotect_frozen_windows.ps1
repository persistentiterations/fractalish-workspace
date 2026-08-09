$RepoRoot = Split-Path -Parent $PSScriptRoot
$Frozen = Join-Path $RepoRoot "frozen"
Get-ChildItem -Path $Frozen -Recurse -File | ForEach-Object {
    $_.IsReadOnly = $false
    Write-Host "WRITABLE $($_.FullName)"
}
Write-Host "Use only to restore verified files. Do not develop directly in frozen/."
