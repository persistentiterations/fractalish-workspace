# RC1 Review Gates — Bolt-On Continuity for Docker v0.2

RC1 passes only when every gate below is satisfied.

A passing review record reports `RC1_READY_FOR_RELEASE_REVIEW`.

## Gate 1 — Qualified source

The review record identifies qualified source commit `31dc5ad0740bf1b262de362f334ed64893a027c2`.

## Gate 2 — Complete deterministic manifest

Every included regular file appears exactly once with a normalized relative path, byte count, and lowercase SHA-256 digest. Entries are sorted by path.

## Gate 3 — Manifest integrity

Missing, extra, changed, duplicated, malformed, absolute, or path-escaping entries fail closed.

## Gate 4 — Qualification evidence

The review record requires `127` passing tests and frozen-regression success.

## Gate 5 — Claims boundary

The candidate is described only as an internal release candidate ready for release review. Production readiness, universal compatibility, zero drift, and zero failure are not claimed.

## Gate 6 — Authority boundary

Every accepted review record preserves observation-only operation and denies gateway, native execution, container mutation, freeze, merge, publication, and production-readiness authority.

## Gate 7 — No side effects

The RC1 qualification module performs no subprocess, socket, Docker, gateway, service-control, network, filesystem-write, freeze, merge, tag, or publication action.

## Gate 8 — Tests

Tests cover stable manifest creation, path ordering, digest correctness, missing and extra entries, tampering, duplicate paths, path escape, qualification evidence, safe authority, and stable review serialization.

## Gate 9 — Frozen regression

```powershell
python .\tools\verify_all_frozen.py
git diff -- .\frozen
```

Required result:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

The frozen diff must be empty.

## Advancement authorization

Passing RC1 authorizes a human release review and preparation of a proposed frozen snapshot. It does not authorize creating that snapshot, merging, tagging, publishing, or expanding execution authority.
