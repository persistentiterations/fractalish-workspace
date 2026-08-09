# Bolt-On Continuity for Docker v0.1 — Stage 3

## Bounded Action Projection

**Stage foundation commit:** `a46405b`  
**Host actions:** None  
**Gateway:** None  
**Docker write authority:** None

Stage 3 deterministically projects exactly one of:

```text
HOLD
RELEASE
NO_ACTION
```

from qualified incident evidence.

A projection is a data record only. It is not an executed action and cannot call
Docker.

Direct qualification:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_3.py
```

Required ending:

```text
STAGE 3 BOUNDED ACTION PROJECTION: PASS
```

Tests:

```powershell
python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_stage_3_*.py" `
  -v
```

Required ending:

```text
Ran 44 tests

OK
```
