# Release Review Contract — Bolt-On Continuity v0.4

## Candidate identity

- candidate: `v0.4-rc1`
- qualified RC1 head: `caede7dcec30c4e30a79f1d1721dae5402e1f95b`
- proposed frozen destination: `frozen/bolt_on_continuity/v0.4`

## Required evidence

The review requires an RC1 verification pass, exactly 234 passing product tests, a complete frozen regression pass, an empty pre-freeze diff under `frozen/`, a clean working tree, a deterministic proposed-snapshot manifest, and explicit claims- and authority-boundary approval.

## Outcomes

- `PROPOSED_FREEZE_READY_FOR_APPROVAL`
- `FAIL_CLOSED_RELEASE_REVIEW`

## Authority boundary

A passing review authorizes only a later explicit freeze decision. It does not create or authorize a frozen snapshot, merge, tag, publication, installation, distribution, native execution, container mutation, or production-readiness claim.