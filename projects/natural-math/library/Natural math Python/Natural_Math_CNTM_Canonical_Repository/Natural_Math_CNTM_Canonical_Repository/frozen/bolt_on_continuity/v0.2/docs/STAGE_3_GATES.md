# Stage 3 Gates — Discovery and Enrollment

Stage 3 passes only when every gate below is satisfied.

## Gate 1 — Fixed read-only commands

Only the exact discovery command and `docker inspect` with one validated full ID are permitted. Shell execution and user-supplied command text are absent.

## Gate 2 — Full-ID authority

Every accepted container ID is exactly 64 lowercase hexadecimal characters. Names, prefixes, indexes, and wildcards are rejected.

## Gate 3 — Deterministic discovery

Discovery JSON lines are strictly parsed, normalized, deduplicated, and sorted by full ID. Identical evidence produces byte-identical canonical output.

## Gate 4 — Explicit confirmation

Selection and confirmation must both equal the exact discovered full ID. Confirmation mismatch fails closed before inspection.

## Gate 5 — Independent inspection binding

The inspected object must contain the exact selected ID. Same-name or prefix matches do not pass.

## Gate 6 — Safe enrollment record

The record states `observation_only = true` and `gateway_enabled = false`, includes a canonical digest, and contains no timestamp, path, username, secret, socket, or executable command.

## Gate 7 — Replacement safety

Tests prove that a same-name container with a different ID cannot inherit enrollment.

## Gate 8 — No configuration write or engine activation

Stage 3 returns data only. It does not write installation state, import v0.1 operational modules, create incidents, project actions, or activate the gateway.

## Gate 9 — Tests and verifier

Tests cover deterministic ordering, malformed evidence, duplicate IDs, short IDs, name-only selection, prefix rejection, confirmation mismatch, inspection mismatch, same-name replacement, canonical digest stability, and exact command allowlisting.

## Gate 10 — Frozen regression

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

Passing Stage 3 authorizes Stage 4 canonical configuration creation and validation around the enrolled subject. It does not authorize monitoring, action projection, gateway execution, or Docker mutation.
