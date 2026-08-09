# Bolt-On Demonstrator v0.1 — Stage 3

## Natural Math shadow-governance interface

Stage 3 adds a deterministic governance interface above the unchanged Stage 1
host and unchanged Stage 2 observer.

The interface is deliberately restricted to **SHADOW / AUTHORITY NONE**. It can
recommend:

```text
PROCEED  (+1)
DEFER     (0)
RESTRICT (-1)
UNKNOWN   (0; insufficient or contradictory evidence)
```

It cannot change, filter, reorder, replace, or suppress host jobs. It reads the
frozen Natural Math RC21 source only to verify its exact SHA-256 identity. It
does not import or execute RC21 and does not modify any frozen file.

## Files added

```text
governance/natural_math_shadow_governance.py
tests/test_shadow_governance.py
README_STAGE_3.md
STAGE_3_VERIFICATION.txt
```

## Install

From the canonical repository root:

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Bolt_On_Demonstrator_v0_1_Stage_3.zip" `
  -DestinationPath ".\development\bolt_on_demonstrator_v0_1" `
  -Force

Remove-Item .\development\bolt_on_demonstrator_v0_1\governance\.gitkeep `
  -ErrorAction SilentlyContinue
```

## Run Stage 3

```powershell
python .\development\bolt_on_demonstrator_v0_1\governance\natural_math_shadow_governance.py
```

Expected final line:

```text
STAGE 3 SHADOW QUALIFICATION: PASS
```

## Run all tests

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_1\tests `
  -p "test_*.py" `
  -v
```

Expected:

```text
Ran 37 tests
OK
```

## Verify frozen releases

```powershell
python .\tools\verify_frozen.py
```

Expected:

```text
FROZEN VERIFICATION PASSED: 11 files
```

## Commit

```powershell
git add .\development\bolt_on_demonstrator_v0_1
git commit -m "Add Stage 3 Natural Math shadow governance"
git status
```

## Claim boundary

Stage 3 proves that a deterministic, receipt-governed shadow layer can evaluate
an ordinary host through an observation adapter without changing the host. It
does not yet prove authorized intervention, active enforcement, CNTM memory, or
production integration. The new interface follows the RC21 authority and replay
boundary but does not claim to embed the full frozen RC21 program into the host.
