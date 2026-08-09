# Bolt-On Demonstrator v0.1 — Stage 1

## Purpose

Stage 1 establishes an ordinary host program before any Natural Math governance,
CNTM memory, or adapter code is attached.

The host is deliberately plain:

- standard-library-only;
- exact integer state;
- deterministic processing order;
- accepted, rejected, completed, and delayed job events;
- immutable result records;
- SHA-256 run digest;
- no file writing;
- no Natural Math or CNTM imports.

Later stages must demonstrate that attaching the bolt-on does not silently
replace or alter this host contract.

## Files

```text
host/ordinary_host.py
tests/test_host_baseline.py
README.md
STAGE_1_VERIFICATION.txt
```

## Install into the canonical repository

Extract these files into:

```text
development/bolt_on_demonstrator_v0_1/
```

Do not copy anything into `frozen/`.

## Run the host

From the canonical repository root:

```powershell
python .\development\bolt_on_demonstrator_v0_1\host\ordinary_host.py
```

Expected final value:

```text
43
```

## Run the qualification tests

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_1\tests `
  -p "test_*.py" `
  -v
```

Expected result:

```text
Ran 8 tests
OK
```

## Recheck frozen releases

```powershell
python .\tools\verify_frozen.py
```

Expected result:

```text
FROZEN VERIFICATION PASSED: 11 files
```

## Save Stage 1 in Git

After the host and all tests pass:

```powershell
git add .\development\bolt_on_demonstrator_v0_1
git commit -m "Add bolt-on demonstrator Stage 1 ordinary host baseline"
git status
```

Expected final Git status:

```text
nothing to commit, working tree clean
```

## Stage 1 claim boundary

A successful Stage 1 proves only that the independent host has a fixed,
deterministic behavior contract. It does not yet prove observation equivalence,
governance, CNTM memory, intervention, or safe detachment.
