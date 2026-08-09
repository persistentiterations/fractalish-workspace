# Stage 4 Gates — Canonical Configuration and Validation

Stage 4 passes only when every gate below is satisfied.

## Gate 1 — Exact subject binding

The configuration is bound to one lowercase full 64-character container ID from a validated enrollment record. A name, prefix, index, or replacement container cannot substitute for that ID.

## Gate 2 — Canonical representation

The same accepted enrollment and bounded options produce byte-identical canonical JSON and the same SHA-256 configuration digest.

## Gate 3 — Safe defaults

Every accepted configuration requires:

```text
observation_only = true
gateway_enabled = false
approval_required = true
autonomous_actions = false
```

## Gate 4 — Fixed vocabulary

The declared decision vocabulary is exactly `NO_ACTION`, `HOLD`, and `RELEASE`. It grants no execution authority.

## Gate 5 — Strict schema

Missing fields, extra fields, unknown versions, wrong scalar types, unsupported retention modes, invalid bounds, and digest mismatch fail closed.

## Gate 6 — Safe storage description

Only bounded relative local paths are accepted. Absolute paths, UNC/network paths, drive-qualified paths, parent traversal, home expansion, and environment expansion are rejected.

## Gate 7 — No persistence or operation

Stage 4 returns canonical bytes only. It does not write files, create directories, install services, call Docker, import v0.1 operational code, monitor containers, project actions, or invoke the gateway.

## Gate 8 — Tests

Tests cover deterministic construction, digest verification, tampering, extra and missing fields, malformed subject IDs, authority expansion, unsafe paths, invalid bounds, and safe-default enforcement.

## Gate 9 — Structural verifier

The verifier checks required files, exact constants, forbidden operational imports and calls, test presence, and Stage 3 availability.

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

Passing Stage 4 authorizes Stage 5 development of a bounded local CLI and observation-only lifecycle around validated configuration data. It does not authorize native Docker mutation or gateway execution.
