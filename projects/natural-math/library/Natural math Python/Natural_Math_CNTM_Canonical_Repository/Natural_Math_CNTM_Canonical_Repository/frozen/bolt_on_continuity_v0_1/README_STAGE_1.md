# Bolt-On Continuity for Docker v0.1 — Stage 1

## Read-Only Docker Observer

**Stage foundation commit:** `3ba6ca0`  
**Execution authority:** None  
**Action projection:** Not implemented  
**Docker write operations:** Not implemented

Stage 1 adds a bounded observer for exactly one configured Linux Docker container.
It accepts fixed inspect, events, and logs evidence; validates immutable container
identity; normalizes accepted evidence deterministically; creates an evidence
receipt; and independently replays the captured evidence.

The optional CLI transport allows only:

```text
docker inspect
docker events
docker logs
docker version
```

It uses argument arrays with `shell=False`, exposes no generic command method,
and contains no action projection or gateway.

## Direct qualification

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_1.py
```

Required ending:

```text
STAGE 1 READ-ONLY DOCKER OBSERVER: PASS
```

## Test suite

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

Fixture qualification proves the observer contract and implemented transport
allowlist. It does not yet prove live Docker compatibility or machine-level
permission isolation.
