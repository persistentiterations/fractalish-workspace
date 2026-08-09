# Bolt-On Demonstrator v0.4 — Stage 6

## External Pilot Qualification and Release Candidate

Stage 6 is the final qualification gate for v0.4. It reruns the five prior stage
qualifications, verifies all frozen predecessor releases, performs one complete
external-pilot evidence chain, generates a deterministic in-memory release
manifest for the full v0.4 development tree, replays the pilot receipts, and
rejects a 64-case receipt/manifest tamper campaign.

This stage declares a release candidate only. It does not create, modify, or
populate `frozen/bolt_on/v0.4`. The freeze remains a separate commit and gate.

## Added files

```text
README_STAGE_6.md
release_candidate/release_candidate_manifest.py
integration/external_pilot_qualification.py
tests/test_external_pilot_qualification.py
```

## Component self-check

```powershell
python .\development\bolt_on_demonstrator_v0_4\release_candidate\release_candidate_manifest.py
```

Required ending:

```text
RELEASE CANDIDATE MANIFEST SELF-CHECK: PASS
```

## Direct Stage 6 qualification

```powershell
python .\development\bolt_on_demonstrator_v0_4\integration\external_pilot_qualification.py
```

Required fixed values include:

```text
Stage: EXTERNAL PILOT QUALIFICATION AND RELEASE CANDIDATE 0.4.6
Mode: EXTERNAL_PILOT_RELEASE_CANDIDATE
Release status: RELEASE_CANDIDATE
Bolt-on execution authority: NONE
Host execution boundary: NATIVE_HOST_ONLY
Stage 5 commit: afa1435f5ed1c5136895b7c8e3fba0dfbc6f064d
Prior stages qualified: 5
Frozen releases: True
External pilot subjects: 1
External pilot observation events: 6
External pilot projected requests: 2
External pilot host-owned actions: 2
External pilot bolt-on actions: 0
Lifecycle packages installed: 3
Lifecycle packages removed: 3
Lifecycle packages active after removal: 0
Release manifest entries: 25
Tamper cases: 64
Tamper cases safely rejected: 64
Deterministic second pass: True
Pilot receipt replay: True
Freeze performed: False
STAGE 6 EXTERNAL PILOT QUALIFICATION AND RELEASE CANDIDATE: PASS
```

The three printed digests are repository-bound outputs and must match their
corresponding replay values where applicable.

## Complete suite

Stage 6 adds 120 tests. The complete v0.4 suite therefore contains 560 tests.

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_4\tests `
  -p "test_*.py" `
  -v
```

Required ending:

```text
Ran 560 tests

OK
```

## Claim boundary

A passing Stage 6 qualifies v0.4 as a deterministic external-system integration
release candidate with read-only observation, bounded host-owned command
crossing, exact lifecycle recovery/removal, replayable pilot evidence, and
release-wide tamper detection. It is not frozen until a separate final-freeze
stage copies the candidate into `frozen/bolt_on/v0.4`, generates the frozen
manifest, independently verifies it, and commits that frozen tree separately.
