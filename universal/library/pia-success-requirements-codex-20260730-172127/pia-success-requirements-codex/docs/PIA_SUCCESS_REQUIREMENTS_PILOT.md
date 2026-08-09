# PIA Success Requirements Pilot

Status: **pilot harness, not production capability**

This repository now contains a bounded PIA pilot surface under
`python/cognitive_basin/pia/`. It is designed to satisfy the current PIA
checklist as executable local evidence while preserving conservative claim
boundaries.

## What the pilot demonstrates

- Governed formation of contradiction history through a declared formation
  service.
- A non-directive formed-history object: provenance, contradiction, confidence,
  eligibility, and scope are retained; route hints, expected outcomes, action
  instructions, and fixture answers are rejected.
- A condition-blind state-access controller that selects state only from
  validity, eligibility, scope, policy, and provenance metadata.
- Cryptographic formation authenticity using canonical serialization, digests,
  lineage binding, and a pilot HMAC authority.
- Blinded fixture commitments that keep expected analyses in a private steward
  record, outside the runtime fixture, with a signed public verification receipt
  binding the private record to the public commitments.
- Typed route distributions over the complete declared route vocabulary.
- Host A export and Host B import of a signed continuity bundle into Host B's
  own state namespace, with a signed Host B import receipt.
- A Host A state receipt showing the formed object existed in Host A's own
  namespace before export.
- A single guarded success surface that emits a signed run receipt; lower-level
  component outputs cannot validate as successful PIA evidence.

## Claim boundary

The deterministic test host is harness evidence. A receipt with
`pilot_claim_status: DETERMINISTIC_HARNESS_VERIFIED` is not a live-provider
model-host portability result.

The optional `GrokCliModelHost` adapter can be used for manual live-host input
runs when the Grok CLI is authenticated and available. Because the guarded
scorer still creates the route distribution from host output, live runs must be
reported as `LIVE_HOST_INPUT_HARNESS_VERIFIED` unless a later implementation
requires the host itself to emit the complete typed distribution.

Do not claim:

- production-grade key custody, key rotation, or compromise recovery;
- protection from all administrator-level or repository-level bypasses;
- general portability across arbitrary models or providers;
- long-duration identity, understanding, consciousness, or semantic correctness;
- calibrated route probabilities beyond the tested fixture distribution.

The strongest defensible success statement after the included tests pass is:

> In the tested deterministic pilot configuration, a governed and authenticated
> continuity object was formed, exported from Host A, verified and imported by
> an independently initialized Host B, exposed through a condition-blind access
> controller, and used by the sole guarded execution route to produce a complete
> typed route distribution and signed run receipt over blinded fixture
> commitments.

## Verification

Run the targeted pilot tests from the repository root:

```powershell
python -m pytest tests/test_pia_success_requirements.py -q
```

Generate retained pilot artifacts with:

```powershell
python -m python.cognitive_basin.pia.acceptance --all --artifact-dir artifacts/pia-pilot
```

That command writes:

- `formed-history.json`
- `host-a-state-receipt.json`
- `continuity-bundle.json`
- `host-b-import-receipt.json`
- `blinded-fixture-runtime.json`
- `private/fixture-steward-record-private.json`
- `fixture-steward-verification.json`
- `typed-route-distribution.json`
- `guarded-run-receipt.json`
- `pia-pilot-acceptance-summary.json`

The tests include positive and negative coverage for:

- valid formation;
- rejected missing evidence;
- rejected directive fields;
- tamper detection;
- condition-blind controller leakage rejection;
- Host B import into a clean namespace;
- fixture steward seal verification without exposing the expected analysis;
- typed route-distribution completeness;
- guarded receipt validation;
- forged authorization rejection;
- lower-layer bypass rejection.
