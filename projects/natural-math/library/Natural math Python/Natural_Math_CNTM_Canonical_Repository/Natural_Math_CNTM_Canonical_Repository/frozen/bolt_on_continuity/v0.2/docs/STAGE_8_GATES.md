# Stage 8 Gates — Recovery and Failure Handling

Stage 8 passes only when every gate below is satisfied.

## Gate 1 — Exact subject authority

Recovery decisions bind only to the enrolled full 64-character ID. Name-only, shortened-ID, and wildcard evidence are rejected.

## Gate 2 — Replacement detection

A same-name container with a different full ID yields `REQUIRE_REENROLLMENT`; it is never treated as the enrolled subject.

## Gate 3 — Missing and stopped behavior

Missing or stopped subjects produce deterministic reports and no broadened action.

## Gate 4 — Store failure

Missing, permission-denied, partial-write, corrupt, disk-full, or ambiguous store evidence yields `FAIL_CLOSED_STORE`.

## Gate 5 — Duplicate suppression

Terminal request ID and digest pairs yield `SUPPRESS_DUPLICATE`. Conflicting reuse, incomplete terminal evidence, and uncertain outcomes fail closed.

## Gate 6 — Safe restart

Only exact subject match, healthy store, and resolved prior records may yield `RESUME_OBSERVATION_ONLY`.

## Gate 7 — No execution

Stage 8 contains no Docker commands, subprocess execution, socket access, filesystem mutation, gateway import, or native executor import.

## Gate 8 — Determinism

Equivalent normalized evidence produces byte-identical canonical reports and digests.

## Gate 9 — Tests

Tests cover healthy restart, duplicate suppression, conflicting reuse, uncertain outcome, replacement, missing subject, stopped subject, ambiguous evidence, each store failure class, canonical stability, and safe flags.

## Gate 10 — Frozen regression

```powershell
python .\tools\verify_all_frozen.py
git diff -- .\frozen
```

The required ending is `ALL FROZEN RELEASE VERIFICATIONS PASSED`, and the frozen diff must be empty.

## Advancement authorization

Passing Stage 8 authorizes Stage 9 installation and uninstall qualification design. It does not authorize native Docker execution or production use.
