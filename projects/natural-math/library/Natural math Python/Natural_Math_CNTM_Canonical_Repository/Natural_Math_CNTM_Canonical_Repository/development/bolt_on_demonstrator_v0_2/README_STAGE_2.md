# Bolt-On Demonstrator v0.2 — Stage 2

## Mediated Host with Bounded `HOLD`

Stage 2 introduces the first active intervention, but only inside a disposable
mediator. The qualified v0.1 host and frozen v0.1 release are not edited.

The mediator may execute exactly one action:

```text
HOLD
```

A valid HOLD removes one governance-`DEFER` job from the current dispatched
batch and places the unchanged job object in a bounded hold queue. It does not
delete, rewrite, replace, reorder, or execute that job.

## Required authority chain

The HOLD executes only when all of these exact bindings agree:

1. Current v0.1 governance replay passes.
2. Stage 1 authority receipts replay to the declared authority digest.
3. The Stage 1 grant is scoped only to `HOLD`.
4. The Stage 1 grant has a one-action budget.
5. The active permit hash validates.
6. The permit is bound to the same governance session.
7. The permit is bound to the same Stage 1 authority digest and grant hash.
8. The request ID, job ordinal, job ID, and evidence digest match.
9. The source governance decision is `DEFER`.
10. The Stage 1 outcome is `WOULD_HOLD`.
11. The integer epoch matches exactly.
12. The permit has not already been consumed.

Any failure causes an exact ordinary-host passthrough with zero intervention.

## Files

```text
mediation/mediated_hold_host.py
tests/test_mediated_hold_host.py
README_STAGE_2.md
STAGE_2_VERIFICATION.txt
```

## Run Stage 2

From the canonical repository root:

```powershell
python .\development\bolt_on_demonstrator_v0_2\mediation\mediated_hold_host.py
```

Expected final line:

```text
STAGE 2 MEDIATED HOLD QUALIFICATION: PASS
```

## Run all v0.2 tests

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_2\tests `
  -p "test_*.py" `
  -v
```

Expected ending:

```text
Ran 54 tests

OK
```

## Verify frozen releases

```powershell
python .\tools\verify_all_frozen.py
```

Expected ending:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

## Save Stage 2

```powershell
git add .\development\bolt_on_demonstrator_v0_2
git commit -m "Add v0.2 Stage 2 mediated HOLD execution"
git push origin main
git status
```

## Claim boundary

A passing Stage 2 proves that a disposable mediator can execute one exact,
one-use, evidence-bound HOLD while all missing, invalid, stale, tampered,
out-of-scope, non-DEFER, UNKNOWN, expired, or reused authority paths produce no
intervention and preserve ordinary host behavior.

It does not yet authorize release, deny, rewrite, mutation, arbitrary policy,
multiple simultaneous interventions, external identity claims, or production
use.
