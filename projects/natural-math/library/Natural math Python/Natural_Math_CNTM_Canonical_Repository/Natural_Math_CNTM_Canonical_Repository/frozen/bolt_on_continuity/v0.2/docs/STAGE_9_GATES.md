# Stage 9 Gates — Installation and Uninstall Qualification

Stage 9 passes only when every gate below is satisfied.

## Gate 1 — Plan-only lifecycle

Installation and uninstall functions return canonical plans only. They perform no filesystem, registry, service, environment, process, or Docker mutation.

## Gate 2 — Clean and repeat installation

`ABSENT` produces `PLAN_INSTALL`. `INSTALLED` produces `ALREADY_INSTALLED` with no duplicate operation list.

## Gate 3 — Interrupted and conflicting state

`PARTIAL`, `CONFLICT`, unknown, malformed, or inconsistent state fails closed and does not produce executable operations.

## Gate 4 — Protected container

The enrolled full container ID is recorded only as a protected subject. No planned operation targets Docker or the monitored container.

## Gate 5 — Explicit data choice

Uninstall defaults to `RETAIN_DATA`. `DELETE_DATA` requires the exact confirmation token `DELETE RECEIPT DATA`; absent or altered confirmation fails closed.

## Gate 6 — Safe uninstall

Uninstall plans remove only declared product-owned artifacts. They do not stop, restart, remove, inspect, pause, unpause, or otherwise modify the enrolled container.

## Gate 7 — Deterministic receipts

Equivalent inputs produce byte-identical canonical plans and identical SHA-256 digests.

## Gate 8 — Safe defaults

Every accepted result states:

```text
observation_only = true
gateway_enabled = false
native_execution_authorized = false
container_mutation_authorized = false
```

## Gate 9 — Tests

Tests cover clean install, repeat install, partial/conflicting state, retain-data uninstall, confirmed deletion plan, missing confirmation, already absent, path safety, protected-container invariants, stable serialization, and no side effects.

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

Passing Stage 9 authorizes Stage 10 end-to-end usability qualification. It does not authorize real installation, real deletion, service registration, gateway execution, or Docker mutation.
