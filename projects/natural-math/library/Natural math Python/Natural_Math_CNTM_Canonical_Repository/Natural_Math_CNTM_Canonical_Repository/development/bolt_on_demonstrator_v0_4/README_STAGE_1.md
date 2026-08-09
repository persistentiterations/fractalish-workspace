# Bolt-On Demonstrator v0.4 — Stage 1

## External Host Integration Contract

Stage 1 defines what an independently existing host must expose before the
frozen v0.3 portability architecture may be attached in a later live pilot.
It performs no host action.

The stage binds directly to the frozen v0.3 release and imports its portable
`HOLD` and `RELEASE` action definitions. It does not copy, alter, or replace the
frozen contract.

## Required external-host surfaces

A compatible host must provide four separated surfaces:

1. **Read-only observation export**
   - deterministic serialization;
   - stable subject, state, sequence, and version fields;
   - append-only ordered events;
   - a point-in-time snapshot for baseline comparison.

2. **Host-owned command boundary**
   - exact finite native operations;
   - exact subject and expected-version binding;
   - idempotency and authorization binding;
   - no command callable or executor supplied to the adapter.

3. **Sidecar lifecycle**
   - no host-source modification;
   - no monkeypatching or environment mutation;
   - no host restart for this pilot lane;
   - complete uninstall and exact rollback.

4. **Read/project-only adapter package**
   - methods limited to `identity`, `normalise_record`, and `project_action`;
   - portable action set fixed to `HOLD` and `RELEASE`;
   - exact mapping to host-native operations;
   - no executor, host mutator, shell dependency, or host-source write.

## Stage 1 reference profile

The qualification uses an ordinary versioned job-service profile with:

- append-only job-event export;
- host-owned versioned request-file boundary;
- `HOLD -> PAUSE_JOB`;
- `RELEASE -> RESUME_JOB`;
- sidecar registry installation;
- four-operation ordinary baseline ending in `DONE`.

Installation and removal change only the external sidecar registry. The ordinary
host baseline digest remains identical before installation, during registration,
and after removal.

## Adversarial contract matrix

The stage includes 28 deterministic rejection cases covering:

- writable, reorderable, or nondeterministic observation exports;
- command callables, wildcards, missing version/authority bindings;
- source modification, restart, monkeypatch, missing uninstall, and missing
  rollback;
- package hash or target-host substitution;
- incomplete, ambiguous, or unauthorized operation maps;
- permission escalation and execution-method exposure;
- embedded executors, mutators, shell requirements, and source writes.

Every rejected case must cause zero host actions, zero bolt-on executed actions,
and no baseline change.

## Qualified invariants

- frozen v0.3 verifies before and after the run;
- the frozen v0.3 manifest contains exactly 20 entries;
- all 37 core contract gates pass for the valid profile;
- all 28 invalid profiles/packages fail closed;
- one sidecar installation and one removal are recorded;
- the registry is empty after removal;
- the ordinary host baseline is unchanged;
- host actions remain zero;
- bolt-on executed actions remain zero;
- receipts replay independently;
- receipt tampering, reordering, and rehashed summary forgery are detected;
- the Stage 1 source remains unchanged during qualification;
- the adapter interface exposes no hidden execution method.

## Files

```text
README.md
README_STAGE_1.md
integration/external_host_contract.py
tests/test_external_host_contract.py
```

The archive adds only these four v0.4 Stage 1 files.

## Install

From the canonical repository PowerShell window:

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Bolt_On_Demonstrator_v0_4_Stage_1.zip" `
  -DestinationPath "." `
  -Force
```

## Run Stage 1

```powershell
python .\development\bolt_on_demonstrator_v0_4\integration\external_host_contract.py
```

Expected output:

```text
Stage: EXTERNAL HOST INTEGRATION CONTRACT 0.4.1
Mode: EXTERNAL_HOST_CONTRACT_DRY_RUN
Execution authority: NONE
Frozen v0.3 manifest: 57f7026ff9dcc69d6dcacb51fda89a40700828e110e74145a0edfaf266c5f6fa
Frozen v0.3 entries: 20
Reference host: ORDINARY VERSIONED JOB SERVICE 1.0
Installation mode: SIDECAR_REGISTRY
Portable actions: HOLD, RELEASE
Native operations: PAUSE_JOB, RESUME_JOB
Contract requirements: 37
Rejection cases: 28
Rejection cases safely rejected: 28
Install registrations: 1
Remove registrations: 1
Host state changes during install/remove: 0
Host actions: 0
Bolt-on executed actions: 0
Baseline digest: 6de3af3a1cb152c8bca6104c93c33747447ef37042ed3f4b31ca382867f0a840
Compatibility digest: b1c02be15cfe993edd45761917f1b6f89ddcdb6b1e079e0925712d8d01b7ab16
Receipt digest: 609ada21eeed17dd34bf507d0788f8a71919d38da63be0d8d9d44d5a2cb76e29
Replay digest: 609ada21eeed17dd34bf507d0788f8a71919d38da63be0d8d9d44d5a2cb76e29
STAGE 1 EXTERNAL HOST INTEGRATION CONTRACT: PASS
```

## Run the complete v0.4 suite

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_4\tests `
  -p "test_*.py" `
  -v
```

Expected ending:

```text
Ran 73 tests

OK
```

## Verify frozen releases

```powershell
python .\tools\verify_all_frozen.py
```

Expected final line:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

Do not commit until the direct qualification, 73-test suite, frozen verification,
and repository status have all been reviewed.

## Claim boundary

A passing Stage 1 proves that the frozen v0.3 portable actions can be bound to a
strict external-host integration contract and that the reference sidecar package
can be registered and removed without changing the ordinary host baseline or
acquiring execution authority.

It does not yet prove integration with a production or third-party host, network
security, production authentication, distributed operation, or live command
execution. Those are later v0.4 stages.
