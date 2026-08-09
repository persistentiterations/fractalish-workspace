# Bolt-On Demonstrator v0.3 — Stage 3

## Equivalent-Event Cross-Host Replay

Stage 3 proves that materially different host evidence can be translated into
one exact portable semantic event stream and replayed independently without
executing a host action.

The qualified sources are:

- Stage 1 portable adapter contract;
- Stage 2 independent workflow host and attachment;
- the deterministic queue evidence stream established in Stage 1;
- the independent versioned workflow-host event stream established in Stage 2.

Stage 3 does not modify either host. It does not execute `HOLD`, `RELEASE`,
`PAUSE`, `RESUME`, or any other host operation.

## Separation of portable meaning and host provenance

Stage 3 maintains two different receipt layers.

### Portable replay ledger

The portable ledger contains only the qualified host-neutral meaning:

1. `ACTIVATED`: `READY -> ACTIVE`, carrying portable action `HOLD`;
2. `CONTROL_POINT`: `ACTIVE -> AT_CONTROL_POINT`, carrying portable action
   `RELEASE`.

The queue and workflow hosts must independently produce the same portable event
objects, semantic stream digest, complete receipt stream, replay result, final
portable state, action sequence, and final ledger digest.

### Host-evidence ledger

Each host also receives a separate evidence ledger that binds:

- host identity;
- host family;
- exact host-run digest;
- host-specific raw event digest;
- source event sequence;
- corresponding portable semantic-event digest.

These evidence ledgers must be valid and replayable, but they must not be equal.
That preserves provenance while proving portable equivalence.

## Qualified properties

- deterministic portable-event construction;
- byte-for-byte identical portable ledgers across hosts;
- independent portable receipt replay;
- exact portable transition validation;
- exact final state reconstruction;
- exact `HOLD`, `RELEASE` action reconstruction;
- distinct host-specific evidence bindings;
- independent evidence-ledger replay;
- payload-tamper detection;
- receipt-reordering detection;
- rejection of rehashed illegal transitions;
- rejection of rehashed subject changes;
- rejection of nonzero execution claims;
- missing-adapter fail-closed behavior;
- Stage 1 and Stage 2 source-hash binding;
- frozen v0.2 verification before and after qualification;
- zero executed actions.

## Files

```text
README_STAGE_3.md
portability/cross_host_replay.py
tests/test_cross_host_replay.py
```

## Install

From the canonical repository PowerShell window:

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Bolt_On_Demonstrator_v0_3_Stage_3.zip" `
  -DestinationPath "." `
  -Force
```

The archive adds only Stage 3 files. It does not contain or replace Stage 1,
Stage 2, frozen v0.1, or frozen v0.2 files.

## Run Stage 3

```powershell
python .\development\bolt_on_demonstrator_v0_3\portability\cross_host_replay.py
```

Expected output:

```text
Stage: EQUIVALENT-EVENT CROSS-HOST REPLAY 0.3.3
Mode: CROSS_HOST_REPLAY_ONLY
Execution authority: NONE
Frozen v0.2 manifest: e020199f5327866bfcbe34877466ea06558eb6650c578ce841c37b4c9abd159c
Portable events: 2
Portable semantic stream digest: 93956b1ff0ed5083368885f33bc600d38e281684e9f6c990f7efad0b624184cd
Portable ledger digest: 8bb846f97fbea27271a6f25e4a084dbf694e583c703c602fc90db3aca48fc479
Queue evidence ledger: 83fb78a3659409eb99a94a12c53f0369e9a4f6f80f2992a7b9a8782e11527dda
Workflow evidence ledger: 7902b0b511f91b2dbc3b08794e869f7053359faee898a5ce37c625e3778ea58d
Cross-host replay digest: 8bb846f97fbea27271a6f25e4a084dbf694e583c703c602fc90db3aca48fc479
Executed actions: 0
STAGE 3 EQUIVALENT-EVENT CROSS-HOST REPLAY: PASS
```

The portable ledger and cross-host replay digests are intentionally equal. The
two host-evidence ledger digests are intentionally different.

## Run the complete v0.3 suite

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_3\tests `
  -p "test_*.py" `
  -v
```

Expected ending:

```text
Ran 120 tests

OK
```

Stage 3 contributes 44 tests to the 76 tests already qualified in Stages 1 and
2.

## Verify all frozen releases

```powershell
python .\tools\verify_all_frozen.py
```

Expected final line:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

## Save Stage 3

Do not commit until the direct qualification, complete 120-test suite, frozen
verification, and repository status have all been reviewed.

```powershell
git add `
  .\development\bolt_on_demonstrator_v0_3\README_STAGE_3.md `
  .\development\bolt_on_demonstrator_v0_3\portability\cross_host_replay.py `
  .\development\bolt_on_demonstrator_v0_3\tests\test_cross_host_replay.py

git commit -m "Add v0.3 Stage 3 equivalent-event cross-host replay"
git push origin main
git status
```

## Claim boundary

A passing Stage 3 proves that two materially different evidence streams can be
normalized into one exact portable event stream whose complete replay ledger is
identical and independently verifiable, while retaining distinct host-specific
provenance ledgers.

It does not yet prove live host replacement, active execution after host
substitution, production adapter safety, arbitrary-host compatibility,
distributed replay, or production-grade cryptographic identity. Those claims
remain outside Stage 3.

Stage 4 will introduce live host substitution under the already-qualified
portable contract and replay boundaries.
