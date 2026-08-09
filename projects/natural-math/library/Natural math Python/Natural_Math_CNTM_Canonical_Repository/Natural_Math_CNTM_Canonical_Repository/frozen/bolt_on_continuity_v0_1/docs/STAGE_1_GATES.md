# Stage 1 Verification Gates

Run from the repository root.

## Confirm Stage 0 foundation

```powershell
git status --short
git log -1 --oneline
```

Required starting commit:

```text
3ba6ca0 Add Docker continuity product v0.1 Stage 0 contract
```

The working tree must be clean.

## Verify frozen releases before extraction

```powershell
python .\tools\verify_all_frozen.py
```

Required ending:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

## Extract Stage 1

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Bolt_On_Continuity_for_Docker_v0_1_Stage_1.zip" `
  -DestinationPath "." `
  -Force
```

## Direct qualification

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_1.py
```

Required ending:

```text
STAGE 1 READ-ONLY DOCKER OBSERVER: PASS
```

## Stage 1 tests

```powershell
python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_stage_1_*.py" `
  -v
```

Required ending:

```text
Ran 36 tests

OK
```

## Re-run Stage 0 gates

```powershell
python .\products\bolt_on_continuity_v0_1\tools\verify_stage_0.py

python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_stage_0_*.py" `
  -v
```

Required endings:

```text
STAGE 0 PRODUCT CONTRACT VERIFICATION: PASS
```

```text
Ran 12 tests

OK
```

## Verify frozen releases again

```powershell
python .\tools\verify_all_frozen.py
```

Required ending:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

## Inspect repository changes

```powershell
git diff -- .\frozen
git status --short --untracked-files=all
```

The frozen diff must be empty. All new or changed paths must remain under
`products/bolt_on_continuity_v0_1`.

Do not commit until every output is confirmed. A passing Stage 1 proves
fixture-backed deterministic read-only observation under the qualified contract.
It does not yet prove a live Docker installation, machine-level permission
isolation, action projection, or execution.
