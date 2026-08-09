# Bolt-On Demonstrator v0.4 — Stage 5

## Live Sidecar Installation, Removal, and Failure Recovery

Stage 5 qualifies the lifecycle surrounding the already-qualified Stage 4 command
crossing. It installs three separately identified sidecar packages, activates them,
injects an observation-side failure, recovers to a safe inactive state, reactivates,
then deactivates and removes every package exactly.

The lifecycle registry has no host import, command constructor, authority token,
native host callable, or execution method. Stage 4 is run separately as the live
functional baseline. Lifecycle operations themselves perform zero host actions.

## Added files

```text
README_STAGE_5.md
lifecycle/live_sidecar_lifecycle.py
integration/live_sidecar_failure_recovery.py
tests/test_live_sidecar_failure_recovery.py
```

## Qualified lifecycle

- three package registrations: observation, projection, and gateway binding;
- exact install, activation, deactivation, removal, and recovery receipts;
- one injected active-sidecar failure;
- recovery first lands in safe `INACTIVE` state;
- reactivation requires a separate accepted lifecycle event;
- removal is rejected while a package remains active;
- all packages end in `REMOVED`;
- registry replay and qualification-receipt replay pass;
- 48 malformed lifecycle cases fail closed;
- lifecycle host-state changes remain zero;
- lifecycle host actions remain zero;
- bolt-on executed actions remain zero;
- Stage 4 direct qualification and all frozen releases remain required gates.

## Component self-check

```powershell
python .\development\bolt_on_demonstrator_v0_4\lifecycle\live_sidecar_lifecycle.py
```

Required ending:

```text
Registry digest: da0213433a0ef1e4a32ab3e9bdc2770e7fc74821511c3e92791387ecd61ae214
Replay digest: da0213433a0ef1e4a32ab3e9bdc2770e7fc74821511c3e92791387ecd61ae214
LIVE SIDECAR LIFECYCLE SELF-CHECK: PASS
```

## Direct Stage 5 qualification

```powershell
python .\development\bolt_on_demonstrator_v0_4\integration\live_sidecar_failure_recovery.py
```

Required fixed values include:

```text
Stage: LIVE SIDECAR INSTALLATION, REMOVAL, AND FAILURE RECOVERY 0.4.5
Mode: LIVE_SIDECAR_LIFECYCLE_QUALIFICATION
Bolt-on execution authority: NONE
Host execution boundary: NATIVE_HOST_ONLY
Installation mode: SIDECAR_REGISTRY
Stage 4 commit: e2d86cb4bae89cfb50a4edfb5447d7244cba6bc5
Stage 4 Git blob: ea1b2441384432acac47aec4ac7601a4a628f5ff
Stage 4 qualification: True
Frozen releases: True
Lifecycle structural isolation: True
Packages: 3
Install registrations: 3
Activation registrations: 4
Deactivation registrations: 3
Remove registrations: 3
Failure transitions: 1
Recovery transitions: 1
Active packages after recovery cycle: 0
Installed packages after removal: 0
Failure cases: 48
Failure cases safely rejected: 48
Host state changes during lifecycle: 0
Host actions during lifecycle: 0
Bolt-on executed actions: 0
Deterministic second pass: True
Lifecycle replay: True
Source unchanged: True
Registry digest: da0213433a0ef1e4a32ab3e9bdc2770e7fc74821511c3e92791387ecd61ae214
Lifecycle replay digest: da0213433a0ef1e4a32ab3e9bdc2770e7fc74821511c3e92791387ecd61ae214
Qualification receipt digest: e434756236ccb07963cce92eeed7e7f10b11c991b668ad862fa101a68adae9d6
Qualification replay digest: e434756236ccb07963cce92eeed7e7f10b11c991b668ad862fa101a68adae9d6
STAGE 5 LIVE SIDECAR INSTALLATION, REMOVAL, AND FAILURE RECOVERY: PASS
```

## Tests

Stage 5 adds 95 tests. The complete v0.4 suite therefore contains 440 tests.

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_4\tests `
  -p "test_*.py" `
  -v
```

Required ending:

```text
Ran 440 tests

OK
```

## Claim boundary

A passing Stage 5 proves deterministic sidecar registration, activation, failure
containment, safe recovery, exact deactivation, and exact removal around the
qualified Stage 4 functional path. It does not yet constitute the v0.4 release
candidate or frozen release. Stage 6 remains the external pilot qualification and
release-candidate gate.
