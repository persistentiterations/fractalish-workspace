# Bolt-On Continuity for Docker v0.1 — Stage 6

## Controlled Native Execution Qualification

**Stage foundation commit:** `6d31f03`

Stage 6 is the first live-action stage. It is restricted to one deliberately
created disposable Linux Docker container identified by its full immutable
64-character hexadecimal container ID.

The live qualification performs:

1. read-only preflight inspection;
2. one exact `docker pause <id>`;
3. read-only verification that the container is paused;
4. one exact `docker unpause <id>`;
5. read-only verification that the container is running and unpaused;
6. deterministic execution and recovery receipts.

It contains no generic command runner, no container-name targeting, no wildcard
targeting, no `exec`, no stop, restart, remove, or kill operation.

Fixture qualification:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_6_fixture.py
```

Live qualification is performed only after all fixture and regression gates
pass. See `docs/STAGE_6_LIVE_RUNBOOK.md`.
