# Bolt-On Demonstrator v0.2 — Stage 5

## Integrated adversarial active-control qualification

Stage 5 composes the qualified Stage 1–4 paths and attacks the active-control boundary without adding any new host action.

Qualified attack classes:

- forged HOLD permit
- forged RELEASE permit
- reordered cycle receipts
- reordered campaign receipts
- duplicate HOLD use
- duplicate RELEASE use
- stale checkpoint recovery
- cross-session RELEASE replay
- partial detach during an active hold
- conflicting HOLD/RELEASE evidence
- expired RELEASE authority
- tampered HOLD evidence

The permitted action vocabulary remains exactly `HOLD` and `RELEASE`. The ordinary host remains unchanged. A successful RELEASE restores the immutable held job to its original ordinal and returns control to ordinary host rules.

Stage 5 runs 30 new tests. In the canonical repository, the complete v0.2 suite should increase from 120 to 150 tests.

A Stage 5 pass is a pre-freeze qualification result, not the freeze itself. Freeze creation should remain a separate, explicit operation after the canonical repository passes all 150 tests and all frozen-release verifiers.
