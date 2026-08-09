# Stage 9 Gates

Foundation:

```text
f892511 Add Docker continuity product v0.1 Stage 8 live qualification
```

Fixture:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_9_fixture.py
```

Required ending:

```text
STAGE 9 ADVERSARIAL AND RECOVERY FIXTURE: PASS
```

Tests:

```powershell
python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_stage_9_*.py" `
  -v
```

Required ending:

```text
Ran 36 tests
OK
```

Live bounded recovery:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_9_live_recovery.py `
  --container-id $ContainerId `
  --acknowledge-disposable-container
```

Required ending:

```text
STAGE 9 CONTROLLED LIVE RECOVERY QUALIFICATION: PASS
```
