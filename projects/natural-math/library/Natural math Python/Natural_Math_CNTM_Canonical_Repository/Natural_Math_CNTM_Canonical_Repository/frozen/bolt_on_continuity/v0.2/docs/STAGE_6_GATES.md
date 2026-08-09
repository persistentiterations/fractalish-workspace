# Stage 6 Gates — Incident Review and Offline Export

Stage 6 passes only when every gate below is satisfied.

## Gate 1 — Strict incident validation

Malformed identifiers, container IDs, configuration digests, sequence ranges, decisions, reason codes, action statuses, receipts, extra fields, and empty receipt lists are rejected.

## Gate 2 — Deterministic listing

Listing order is stable, summaries are bounded, and invalid limits fail closed.

## Gate 3 — Honest explanation

Decision, projection, approval, gateway result, Docker result, and execution evidence remain distinct. Projection is never reported as execution.

## Gate 4 — Receipt-chain replay

Receipt sequence, previous-digest binding, canonical digest equality, and terminal state are verified without Docker access.

## Gate 5 — Deterministic export

The same incident produces byte-identical members, manifest, and package digest. Export creation remains in memory and performs no file writes.

## Gate 6 — Safe content boundary

Exports contain only the qualified incident model, replay result, hashes, byte counts, and fixed schema metadata. Secrets and host-environment data are absent.

## Gate 7 — No operational authority

Stage 6 has no subprocess, Docker SDK, socket, filesystem-write, gateway, approval, pause, unpause, stop, restart, kill, remove, exec, run, or create path.

## Gate 8 — Tests

Tests cover stable ordering, invalid limits, explanation honesty, valid replay, tampered digest, broken chain, sequence mismatch, deterministic export, manifest verification, tampered export, strict fields, and no execution evidence for projected actions.

## Gate 9 — Frozen regression

```powershell
python .\tools\verify_all_frozen.py
git diff -- .\frozen
```

The required result is `ALL FROZEN RELEASE VERIFICATIONS PASSED`, and the frozen diff must be empty.

## Advancement authorization

Passing Stage 6 authorizes Stage 7 approval and denial interface work only. It does not authorize gateway execution or Docker mutation.
