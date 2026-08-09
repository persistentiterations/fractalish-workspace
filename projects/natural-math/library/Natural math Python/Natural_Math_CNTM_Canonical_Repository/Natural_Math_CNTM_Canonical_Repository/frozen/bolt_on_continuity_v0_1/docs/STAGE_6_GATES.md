# Stage 6 Gates

Foundation: `6d31f03`.

Run fixture qualification and tests first:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_6_fixture.py
python -m unittest discover -s .\products\bolt_on_continuity_v0_1\tests -p "test_stage_6_*.py" -v
```

Required:

```text
STAGE 6 CONTROLLED NATIVE EXECUTION FIXTURE: PASS
Ran 36 tests
OK
```

Re-run Stages 5 through 0 and all frozen verification before the live run.
Follow `STAGE_6_LIVE_RUNBOOK.md` exactly. After the live run, confirm the
disposable container is running and unpaused before removing it.
