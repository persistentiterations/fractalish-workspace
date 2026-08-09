# Stage 8 Qualification Gates

Foundation:

```text
6548489 Add Docker continuity product v0.1 Stage 7 pipeline qualification
```

Fixture:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_8_fixture.py
```

Required ending:

```text
STAGE 8 CONTROLLED LIVE PIPELINE FIXTURE: PASS
```

Tests:

```powershell
python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_stage_8_*.py" `
  -v
```

Required ending:

```text
Ran 30 tests
OK
```

Live run:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_8_live.py `
  --container-id $ContainerId `
  --acknowledge-disposable-container
```

Required ending:

```text
STAGE 8 CONTROLLED LIVE END-TO-END QUALIFICATION: PASS
```

After the live run, independently verify:

```powershell
docker inspect `
  --format "running={{.State.Running}} paused={{.State.Paused}}" `
  $ContainerId
```

Required:

```text
running=true paused=false
```
