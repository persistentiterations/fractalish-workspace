# Stage 8 Contract — Recovery Classification

## Objective

Produce deterministic, data-only recovery decisions from validated prior state and bounded current subject/store evidence.

## Inputs

- exact enrolled lowercase 64-character container ID and display name;
- prior request and operator-control records;
- prior terminal action evidence when present;
- current discovered container IDs, names, and states;
- receipt-store health evidence.

## Subject classifications

- `SUBJECT_MATCHED` — exact enrolled ID is present and running;
- `SUBJECT_MISSING` — exact enrolled ID is absent and no same-name replacement is present;
- `SUBJECT_REPLACED` — enrolled ID is absent while the same display name is attached to a different full ID;
- `SUBJECT_STOPPED` — exact enrolled ID is present with a stopped or exited state;
- `SUBJECT_AMBIGUOUS` — malformed, duplicated, conflicting, or incomplete evidence.

Names are descriptive only. A replacement under the same name is a different subject and requires enrollment.

## Store classifications

`STORE_HEALTHY`, `STORE_MISSING`, `STORE_PERMISSION_DENIED`, `STORE_PARTIAL_WRITE`, `STORE_CORRUPT`, `STORE_DISK_FULL`, and `STORE_AMBIGUOUS`.

Only `STORE_HEALTHY` permits normal recovery.

## Recovery dispositions

- `RESUME_OBSERVATION_ONLY` — exact subject matched, store healthy, and no unresolved action uncertainty exists;
- `SUPPRESS_DUPLICATE` — an identical request already has terminal execution evidence or a terminal gateway result;
- `REQUIRE_REENROLLMENT` — subject replacement is detected;
- `REPORT_SUBJECT_UNAVAILABLE` — subject is missing or stopped;
- `FAIL_CLOSED_STORE` — store health is not proven;
- `FAIL_CLOSED_UNCERTAIN` — evidence is malformed, contradictory, incomplete, or action outcome is uncertain.

## Duplicate rule

No recovery may recreate or re-authorize a request whose request ID and digest are already terminal. Conflicting reuse of one request ID fails closed.

## Safety result

Every report states `observation_only: true`, `gateway_enabled: false`, and `native_execution_authorized: false`.

Stage 8 performs no filesystem writes, Docker calls, gateway calls, subprocess execution, or process control.
