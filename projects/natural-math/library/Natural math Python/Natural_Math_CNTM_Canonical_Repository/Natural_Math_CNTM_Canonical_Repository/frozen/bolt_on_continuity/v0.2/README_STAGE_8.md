# Bolt-On Continuity for Docker v0.2 — Stage 8

## Restart, Replacement, and Storage-Failure Recovery

Stage 8 defines deterministic recovery decisions after restart and bounded failure handling for subject replacement, missing or stopped containers, and receipt-store uncertainty.

Stage 8 remains observation-only. It does not execute Docker commands, invoke the gateway, approve actions, or write recovery state.

## Outputs

- restart snapshot validation;
- duplicate-action suppression decisions;
- same-name replacement detection;
- missing and stopped subject classifications;
- receipt-store health classifications;
- fail-closed recovery reports;
- tests and structural verifier.

## Verification

```powershell
python .\products\bolt_on_continuity_v0_2\tools\verify_stage_8.py
python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_2\tests `
  -p "test_*.py" `
  -v
python .\tools\verify_all_frozen.py
git diff -- .\frozen
git status --short
```

Required endings:

```text
BOLT-ON CONTINUITY V0.2 STAGE 8 VERIFICATION: PASS
OK
ALL FROZEN RELEASE VERIFICATIONS PASSED
```
