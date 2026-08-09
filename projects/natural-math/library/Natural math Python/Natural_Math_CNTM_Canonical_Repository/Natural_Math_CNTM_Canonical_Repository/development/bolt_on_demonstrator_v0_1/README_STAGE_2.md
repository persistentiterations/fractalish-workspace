# Bolt-On Demonstrator v0.1 — Stage 2

## Observation-only adapter

Stage 2 attaches an independent observer to the unchanged Stage 1 host.
The adapter has no authority to approve, reject, delay, reorder, or alter work.

It performs four bounded actions:

1. Copies host inputs into immutable observation records.
2. Runs the unchanged host using fresh copies of those inputs.
3. Records every host event in an independent SHA-256 hash chain.
4. Replays the observation chain and reports tampering or missing receipts.

## Stage 2 claim boundary

A passing Stage 2 establishes:

- direct and observed host results are exactly equal;
- the host digest remains unchanged;
- the host source remains unchanged;
- caller-owned input objects remain unchanged;
- observation receipts are deterministic;
- altered or removed receipts are detected;
- removing the observer requires no host repair.

It does **not** yet establish Natural Math governance, CNTM memory, intervention,
authority, contradiction resolution, or persistent application memory.

## Added files

```text
adapter/bolt_on_adapter.py
tests/test_observation_adapter.py
README_STAGE_2.md
STAGE_2_VERIFICATION.txt
```

## Install

Extract the Stage 2 ZIP into:

```text
development/bolt_on_demonstrator_v0_1/
```

Use `-Force` so the new adapter file replaces the adapter `.gitkeep` placeholder.
No frozen file is included in this package.

## Run the adapter demonstration

From the canonical repository root:

```powershell
python .\development\bolt_on_demonstrator_v0_1\adapter\bolt_on_adapter.py
```

Expected final line:

```text
STAGE 2 EQUIVALENCE:          PASS
```

## Run all Stage 1 and Stage 2 tests

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_1\tests `
  -p "test_*.py" `
  -v
```

Expected result:

```text
Ran 20 tests
OK
```

## Verify frozen releases

```powershell
python .\tools\verify_frozen.py
```

Expected result:

```text
FROZEN VERIFICATION PASSED: 11 files
```

## Commit Stage 2

```powershell
git add .\development\bolt_on_demonstrator_v0_1
git commit -m "Add Stage 2 observation-only adapter"
git status
```

Expected final status:

```text
nothing to commit, working tree clean
```
