# Bolt-On Demonstrator v0.3 — Stage 5

## Adversarial Adapter Qualification

Stage 5 attacks the adapter and live-substitution boundaries qualified in
Stages 1–4. It adds no host action and does not modify any prior stage or frozen
release.

The baseline remains the qualified Stage 4 campaign:

1. attach to the deterministic lease-queue host;
2. project portable `HOLD` to native `SUSPEND`;
3. execute through a one-use host-owned permit;
4. detach with an exact portable checkpoint;
5. substitute the independent workflow host;
6. project portable `RELEASE` to native `RESUME`;
7. execute through a second one-use host-owned permit;
8. detach and allow ordinary host completion.

Stage 5 preserves that valid path while proving that malformed, forged, stale,
replayed, cross-boundary, reordered, and semantically rehashed evidence fails
closed before an attack can cause a host action.

## Stage 5 hardening

Adversarial testing identified two bindings that must be independently checked
at the integrated boundary even when an object has a valid self-consistent
hash:

- permit and substitution-ticket identifiers must be re-derived from their
  complete bound fields rather than accepted as arbitrary rehashed identifiers;
- permit issuer and governance-session bindings must be explicitly pinned before
  a host-owned executor may run.

Stage 5 adds strict preflight validation for those bindings without changing the
Stage 4 host-owned execution functions. A valid Stage 4 permit, checkpoint, and
ticket still pass. Invalid evidence is rejected without calling a host executor.

## Qualified attack campaign

The deterministic campaign contains 48 attack vectors in four categories.

### Adapter attacks — 18

- missing adapter;
- forged adapter identity;
- identity drift and identity exceptions;
- event-normalization failure;
- foreign adapter event binding;
- sequence and duplicate-event manipulation;
- stale source-event and state evidence;
- subject and action-scope substitution;
- projection exceptions;
- hidden execution claims;
- projection subject, adapter, event, and state substitution.

### Execution-permit attacks — 14

- permit hash tampering;
- rehashed permit-ID substitution;
- issuer and governance-session substitution;
- cross-host, cross-adapter, request, and projection replay;
- action, native operation, subject, and epoch substitution;
- permit reuse;
- native-state drift.

### Checkpoint, substitution, and attachment attacks — 10

- checkpoint semantic rewriting;
- rehashed checkpoint-ID substitution;
- checkpoint outcome rebinding;
- ticket hash tampering;
- rehashed ticket-ID substitution;
- ticket issuer and session substitution;
- ticket reuse;
- attaching a second host before detachment;
- attachment-event reordering.

### Receipt attacks — 6

- receipt payload tampering;
- receipt reordering;
- rehashed direct-authority claims;
- rehashed adapter-execution claims;
- rehashed illegal host transitions;
- rehashed campaign-summary action reversal.

## Required invariants

- all 48 attacks are safely rejected;
- host state is unchanged by every rejected attack;
- host actions caused during attacks remain exactly zero;
- bolt-on executed actions remain exactly zero;
- the valid Stage 4 control path remains accepted;
- the baseline control campaign still has exactly two host-owned actions;
- all attack outcomes receive deterministic hash-chained receipts;
- adversarial receipts replay independently;
- raw tampering, reordering, and self-consistently rehashed semantic tampering are
  detected;
- Stage 1–4 and both host source hashes are bound;
- frozen v0.2 is verified before and after qualification.

## Files

```text
README_STAGE_5.md
portability/adversarial_adapter_qualification.py
tests/test_adversarial_adapter_qualification.py
```

The archive adds only these Stage 5 files.

## Install

From the canonical repository PowerShell window:

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Bolt_On_Demonstrator_v0_3_Stage_5.zip" `
  -DestinationPath "." `
  -Force
```

## Run Stage 5

```powershell
python .\development\bolt_on_demonstrator_v0_3\portability\adversarial_adapter_qualification.py
```

Expected output:

```text
Stage: ADVERSARIAL ADAPTER QUALIFICATION 0.3.5
Mode: INTEGRATED_ADVERSARIAL_ADAPTER_TESTING
Bolt-on execution authority: NONE
Execution boundary: HOST_BOUNDARY_ONLY
Frozen v0.2 manifest: e020199f5327866bfcbe34877466ea06558eb6650c578ce841c37b4c9abd159c
Attack categories: 4
Attacks executed: 48
Attacks safely rejected: 48
Baseline host actions: 2
Host actions during attacks: 0
Bolt-on executed actions: 0
Adversarial campaign digest: e6693c8aed808238241f09923e9952302ddab4477aaf56703fdeb29804f05363
Replay digest: e6693c8aed808238241f09923e9952302ddab4477aaf56703fdeb29804f05363
STAGE 5 ADVERSARIAL ADAPTER QUALIFICATION: PASS
```

The adversarial campaign and replay digests must match exactly.

## Run the complete v0.3 suite

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_3\tests `
  -p "test_*.py" `
  -v
```

Expected ending:

```text
Ran 256 tests

OK
```

Stage 5 contributes 60 tests to the 196 tests already qualified in Stages 1–4.

## Verify all frozen releases

```powershell
python .\tools\verify_all_frozen.py
```

Expected final line:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

## Save Stage 5

Do not commit until the direct Stage 5 qualification, complete 256-test suite,
frozen verification, and repository status have all been reviewed.

```powershell
git add `
  .\development\bolt_on_demonstrator_v0_3\README_STAGE_5.md `
  .\development\bolt_on_demonstrator_v0_3\portability\adversarial_adapter_qualification.py `
  .\development\bolt_on_demonstrator_v0_3\tests\test_adversarial_adapter_qualification.py

git commit -m "Add v0.3 Stage 5 adversarial adapter qualification"
git push origin main
git status
```

## Claim boundary

A passing Stage 5 proves that the qualified two-host adapter and substitution
architecture rejects the enumerated forged, stale, replayed, reordered, and
semantically rehashed attack classes without giving the bolt-on execution
authority or causing an attack-time host action.

It does not prove arbitrary-host compatibility, production network security,
production identity authentication, distributed consensus, resistance to every
possible attack, or safe operation in an uncontrolled production environment.

Stage 6 will package portability qualification, deterministic second-pass
verification, release-candidate approval, and the separate v0.3 freeze
procedure.
