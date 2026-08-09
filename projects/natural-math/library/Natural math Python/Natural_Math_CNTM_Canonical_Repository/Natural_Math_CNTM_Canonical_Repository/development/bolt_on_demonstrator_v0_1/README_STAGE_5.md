# Bolt-On Demonstrator v0.1 — Stage 5

## Purpose

Stage 5 qualifies the complete shadow-only bolt-on as one integrated system:

```text
ordinary host
    ↓
observation-only adapter
    ↓
Natural Math shadow governance
    ↓
CNTM bounded shadow memory
```

The system still has no intervention authority.

## Integrated campaigns

The qualification runs six deterministic host scenarios:

```text
NORMAL
REORDERED
DUPLICATE
MISSING_DEPENDENCY
DEPENDENCY_CYCLE
MIXED_INVALID
```

It also injects six faults into immutable evidence copies:

```text
OBSERVATION_TAMPER
OBSERVATION_MISSING_RECEIPT
GOVERNANCE_TAMPER
GOVERNANCE_MISSING_RECEIPT
MEMORY_TAMPER
MEMORY_MISSING_RECORD
```

Additional gates cover:

- seven distinct sessions in one bounded CNTM memory image;
- exact multi-session memory replay;
- atomic duplicate-session rejection;
- atomic capacity-exhaustion rejection;
- contradiction preservation;
- UNKNOWN preservation;
- five repeated attach/detach cycles;
- unchanged host, adapter, governance, memory, and 11 frozen Python sources;
- deterministic repeated full-campaign digest;
- zero unauthorized interventions.

## Install

Extract this ZIP into:

```text
development/bolt_on_demonstrator_v0_1/
```

from the canonical repository root.

## Run Stage 5

```powershell
python .\development\bolt_on_demonstrator_v0_1\qualification\integrated_adversarial_qualification.py
```

Expected final line:

```text
STAGE 5 INTEGRATED QUALIFICATION: PASS
```

Expected release digests:

```text
Campaign digest:
9ff12f5a0776c93c11fe4d020bcaf8b756caff82c5f3a1076c23c6ed152f6eab

Shared memory digest:
6ba2c70e929777e37feeb6798aba39fc5f2e95b574e8872867f5e53017d66a73
```

## Run all Stage 1–5 tests

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_1\tests `
  -p "test_*.py" `
  -v
```

Expected ending:

```text
Ran 76 tests

OK
```

## Verify frozen files

```powershell
python .\tools\verify_frozen.py
```

Expected:

```text
FROZEN VERIFICATION PASSED: 11 files
```

## Commit Stage 5

```powershell
git add .\development\bolt_on_demonstrator_v0_1
git commit -m "Add Stage 5 integrated adversarial qualification"
git status
```

Expected final status:

```text
nothing to commit, working tree clean
```

## Claim boundary

A passing Stage 5 establishes a qualified shadow-only bolt-on demonstrator. It
shows deterministic observation, governance recommendations, bounded evidence
memory, fault detection, full-stack replay, and safe attachment/detachment
without modifying the host or frozen foundations.

It does not yet authorize the bolt-on to alter host execution. Active bounded
intervention belongs in a separate v0.2 development branch.
