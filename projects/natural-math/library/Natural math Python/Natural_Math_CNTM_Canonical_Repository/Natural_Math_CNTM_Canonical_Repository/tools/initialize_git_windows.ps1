$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

git init
git add .
git commit -m "Create canonical frozen Natural Math and CNTM repository"
git branch -M main

git tag -a natural-math-v10.3.2 -m "Frozen Natural Math v10.3.2 baseline"
git tag -a natural-math-v12.0 -m "Frozen Natural Math v12.0 RC21-qualified release"
git tag -a cntm-v1.3F -m "Frozen CNTM finite ternary substrate v1.3F"
git tag -a cntm-v2.4 -m "Frozen CNTM application layer v2.4"
git tag -a cntm-v3.0F -m "Frozen CNTM deterministic local-memory infrastructure v3.0F"

Write-Host "Git repository and annotated release tags created. Add a private remote only after reviewing the files."
