# Bolt-On Continuity for Docker v0.1 — Stage 5

## Dry-Run Native Action Adapter

**Stage foundation commit:** `c4f3e8f`  
**Execution mode:** Dry-run only  
**Docker write calls:** None

Stage 5 converts an approved Stage 4 gateway decision into one exact bounded
native operation plan:

```text
HOLD    -> docker pause <immutable-container-id>
RELEASE -> docker unpause <immutable-container-id>
```

No subprocess is started. No Docker socket is opened. No host action occurs.

Direct qualification:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_5.py
```

Required ending:

```text
STAGE 5 DRY-RUN NATIVE ACTION ADAPTER: PASS
```

Tests:

```powershell
python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_stage_5_*.py" `
  -v
```

Required ending:

```text
Ran 52 tests

OK
```
