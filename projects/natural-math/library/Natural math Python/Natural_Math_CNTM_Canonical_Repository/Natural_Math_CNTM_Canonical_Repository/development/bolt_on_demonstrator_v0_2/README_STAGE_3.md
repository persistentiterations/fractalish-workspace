# Bolt-On Demonstrator v0.2 — Stage 3

Stage 3 adds controlled RELEASE from the mediated HOLD queue.

The held job can return to the ordinary host only under a new, independent,
one-use RELEASE grant and permit bound to the exact HOLD permit, mediation
digest, immutable job, original ordinal, evidence digest, and integer epoch.

RELEASE does not force execution. It restores the job to the pending batch and
lets the unmodified ordinary host apply its own rules. In the baseline fixture,
J005 is released from mediator custody and then correctly delayed by the host
because dependency J999 remains absent.

No frozen source is modified. HOLD authority cannot be reused as RELEASE
authority. Missing, stale, reused, malformed, tampered, or mismatched RELEASE
evidence fails closed and leaves the job in the HOLD queue.
