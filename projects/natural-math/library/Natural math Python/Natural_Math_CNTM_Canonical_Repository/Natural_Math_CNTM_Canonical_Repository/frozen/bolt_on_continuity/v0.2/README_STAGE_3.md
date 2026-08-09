# Bolt-On Continuity for Docker v0.2 — Stage 3

## Deterministic Container Discovery and Explicit Enrollment

**Status:** Development stage  
**Prerequisite:** Stage 2 qualified  
**Authority:** Read-only discovery and full-ID inspection only

Stage 3 discovers local Docker containers in deterministic order and creates a data-only enrollment record for exactly one explicitly confirmed subject.

A container name is display information only. It is never action authority. Enrollment requires an exact lowercase 64-character hexadecimal container ID returned by Docker and an exact operator confirmation of that same ID.

Stage 3 does not write product configuration, start monitoring, project an action, enable the gateway, pause, unpause, restart, stop, kill, remove, exec, run, or create a container.

## Fixed read-only Docker probes

```text
docker container ls --all --no-trunc --format {{json .}}
docker inspect <full 64-character container ID>
```

The discovery result is normalized and sorted by full container ID. Enrollment records are canonical JSON with no timestamps or machine-specific paths.

## Verification

```powershell
python .\products\bolt_on_continuity_v0_2\tools\verify_stage_3.py
python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_2\tests `
  -p "test_*.py" `
  -v
python .\tools\verify_all_frozen.py
git diff -- .\frozen
git status --short
```

Required endings:

```text
BOLT-ON CONTINUITY V0.2 STAGE 3 VERIFICATION: PASS
OK
ALL FROZEN RELEASE VERIFICATIONS PASSED
```
