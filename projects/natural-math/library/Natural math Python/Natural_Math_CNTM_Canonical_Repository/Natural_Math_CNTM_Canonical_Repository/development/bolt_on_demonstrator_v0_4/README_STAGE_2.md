# Bolt-On Demonstrator v0.4 — Stage 2

## Independent Ordinary Host Fixture and Native Baseline

Stage 2 creates the first v0.4 host that is not designed as a bolt-on test host.
The host is a standalone deterministic job service using only Python standard
library modules and native job-service terms. It imports no Natural Math, CNTM,
frozen release, portable-action, adapter, sidecar, or governance module.

The Stage 2 qualification harness is separate from the host. The harness binds
the native baseline to the qualified Stage 1 external-host contract and verifies
that frozen v0.3 remains unchanged.

## Native host

The ordinary host exposes seven native operations:

```text
REGISTER_JOB
START_JOB
CHECKPOINT_JOB
PAUSE_JOB
RESUME_JOB
COMPLETE_JOB
CANCEL_JOB
```

Its canonical baseline is:

```text
REGISTER_JOB -> START_JOB -> CHECKPOINT_JOB -> PAUSE_JOB -> RESUME_JOB -> COMPLETE_JOB
```

The baseline applies six commands, rejects none, records one checkpoint, and
ends in native state `DONE` at version 6.

Every command binds:

- an exact native operation;
- an exact job identifier;
- an expected native version;
- an idempotency key;
- a host authority token;
- an exact canonical payload;
- a derived command identifier and SHA-256 digest.

Every outcome receives an append-only hash-chained native receipt. Replaying the
command journal reconstructs the same receipts, job record, snapshot, and run
digest.

## Rejection campaign

The deterministic native rejection campaign contains 19 submitted commands:
4 valid native actions and 15 rejected commands. It covers:

- unknown operations;
- missing jobs;
- stale and future expected versions;
- wrong authority tokens;
- invalid state transitions;
- missing checkpoint payloads;
- duplicate registration;
- exact idempotency replay;
- conflicting idempotency reuse;
- commands after terminal state.

All 15 rejected commands preserve the exact before-state and before-version.
The rejection journal also replays independently.

## Independence boundary

The standalone host source must:

- import only the Python standard library;
- contain no import or source dependency on v0.3 or v0.4 integration code;
- expose only native job-service operations and records;
- remain runnable after all integration files are removed;
- perform no sidecar installation and no portable action;
- retain host-owned execution authority only inside the native service.

The qualification harness may inspect the host and prior qualification evidence,
but the host may not import or call the harness.

## Qualified invariants

- Stage 1 direct qualification passes from its committed source;
- Stage 1 source SHA-256 is
  `8035b10d0e68ec0365f48340366ec3bdd903a4dcc2e7b9b2574b2269c04b4806`;
- frozen v0.3 verifies before and after qualification;
- frozen v0.3 contains exactly 20 sealed entries;
- the native host source SHA-256 is
  `14a3b86d4cabee409d84904f3db4feb416be905c3c54edb3ca5ef4d50e41a797`;
- the native host has no prohibited coupling;
- two baseline runs are byte-for-byte equal;
- two rejection campaigns are byte-for-byte equal;
- baseline command and receipt replay passes;
- rejection command and receipt replay passes;
- raw receipt tampering is detected;
- receipt reordering is detected;
- self-consistently rehashed semantic forgery is detected;
- all 15 rejected commands are state-neutral;
- the qualification receipt chain replays independently;
- source files remain unchanged during qualification;
- bolt-on executed actions remain exactly zero.

## Files

```text
README_STAGE_2.md
hosts/ordinary_job_service.py
integration/independent_host_baseline.py
tests/test_independent_host_baseline.py
```

The archive adds only these four Stage 2 files.

## Install

From the canonical repository PowerShell window:

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Bolt_On_Demonstrator_v0_4_Stage_2.zip" `
  -DestinationPath "." `
  -Force
```

## Run the standalone host

```powershell
python .\development\bolt_on_demonstrator_v0_4\hosts\ordinary_job_service.py
```

Required final line:

```text
ORDINARY JOB SERVICE SELF-QUALIFICATION: PASS
```

## Run Stage 2

```powershell
python .\development\bolt_on_demonstrator_v0_4\integration\independent_host_baseline.py
```

Expected output:

```text
Stage: INDEPENDENT ORDINARY HOST FIXTURE AND NATIVE BASELINE 0.4.2
Mode: NATIVE_HOST_BASELINE_QUALIFICATION
Bolt-on execution authority: NONE
Host execution boundary: NATIVE_HOST_ONLY
Stage 1 source: 8035b10d0e68ec0365f48340366ec3bdd903a4dcc2e7b9b2574b2269c04b4806
Frozen v0.3 manifest: 57f7026ff9dcc69d6dcacb51fda89a40700828e110e74145a0edfaf266c5f6fa
Frozen v0.3 entries: 20
Host: ORDINARY VERSIONED JOB SERVICE 1.0
Host source: 14a3b86d4cabee409d84904f3db4feb416be905c3c54edb3ca5ef4d50e41a797
Integration API: JOB-SERVICE-READ-COMMAND-1
Native operations: REGISTER_JOB, START_JOB, CHECKPOINT_JOB, PAUSE_JOB, RESUME_JOB, COMPLETE_JOB, CANCEL_JOB
Baseline commands: 6
Baseline applied: 6
Baseline rejected: 0
Final state: DONE
Final version: 6
Checkpoint count: 1
Rejection commands: 19
Rejection applied: 4
Rejection rejected: 15
Rejection cases safely rejected: 15
Deterministic second pass: True
Restart replay: True
Independent host source: True
Native host actions: 6
Bolt-on executed actions: 0
Baseline digest: df74c38b6bc7c377bb0fbc175035e03cea46d22c4f48e0109c7ce8ad75508129
Baseline replay digest: df74c38b6bc7c377bb0fbc175035e03cea46d22c4f48e0109c7ce8ad75508129
Rejection digest: b0acc3703f85f697b04c1fc41ce6e7e6e466b21b0662a3fc8d87e2c9b476015d
Qualification receipt digest: 480193cc70bf336405735cbbb86e7f9d3886953592197a2a5d208177f14d2f9d
Qualification replay digest: 480193cc70bf336405735cbbb86e7f9d3886953592197a2a5d208177f14d2f9d
STAGE 2 INDEPENDENT ORDINARY HOST BASELINE: PASS
```

## Run the complete v0.4 suite

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_4\tests `
  -p "test_*.py" `
  -v
```

Required ending:

```text
Ran 145 tests

OK
```

## Verify frozen releases

```powershell
python .\tools\verify_all_frozen.py
```

Required final line:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

Do not commit until the standalone host, direct Stage 2 qualification, complete
145-test suite, frozen verification, and repository status have all been
reviewed.

## Claim boundary

A passing Stage 2 proves that an independently implemented deterministic native
job service can satisfy the Stage 1 external-host surfaces while remaining
fully functional and replayable without any bolt-on code installed.

It does not yet prove that a read-only adapter has observed this host, that a
host-owned command gateway has accepted a projected action, or that a live
third-party production system has been integrated. Those remain later v0.4
stages.
