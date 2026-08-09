# Stage 7 Gates — Approval, Denial, and Gateway State

Stage 7 passes only when every gate below is satisfied.

## Gate 1 — Strict request binding

Projected requests require the exact full container ID, `HOLD` or `RELEASE`, bounded sequence values, canonical digests, and no extra fields.

## Gate 2 — Explicit human decision

Only `APPROVE` and `DENY` are accepted. There is no implicit, default, inferred, timed, or autonomous approval.

## Gate 3 — Expiry and sequence checks

Approval or denial must bind to a decision sequence from issuance through expiry, inclusive. Expired, pre-issued, or malformed requests fail closed.

## Gate 4 — Gateway state separation

Gateway state begins disabled. Enable and disable are explicit deterministic state transitions. Gateway enablement does not authorize native execution.

## Gate 5 — Duplicate and conflict rejection

Repeated decisions, conflicting decisions, and request-identifier reuse with a different digest are rejected.

## Gate 6 — Canonical records

Request, gateway-state, and operator-decision records have deterministic canonical JSON and SHA-256 digests.

## Gate 7 — No execution surface

Stage 7 contains no Docker import, subprocess execution, socket access, native command vector, v0.1 gateway import, pause, unpause, or other mutation command.

Every accepted record contains:

```text
native_execution_authorized = false
```

## Gate 8 — Tests

Tests cover valid approval, valid denial, disabled-gateway approval rejection, expiry, sequence bounds, digest tampering, wrong action, shortened ID, extra fields, duplicate decision, conflicting decision, request-ID reuse, gateway transitions, and deterministic serialization.

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

Passing Stage 7 authorizes Stage 8 restart, recovery, persistence-boundary, and subject-replacement qualification. It does not authorize Docker execution or gateway activation against a live container.
