# Stage 8 Contract — Recovery Classification

## Objective

Produce deterministic, data-only recovery decisions from validated persisted state and current bounded subject/store evidence.

## Inputs

- exact enrolled 64-character container ID;
- prior request and operator-control records;
- prior terminal action evidence when present;
- current discovered container IDs and states;
- receipt-store health evidence.

## Subject classifications

- `SUBJECT_MATCHED` — exact enrolled ID is present;
- `SUBJECT_MISSING` — exact enrolled ID is absent and no same-name replacement is asserted;
- `SUBJECT_REPLACED` — the enrolled ID is absent while the same display name is bound to a different full ID;
- `SUBJECT_STOPPED` — exact enrolled ID is present with stopped/exited state;
- `SUBJECT_AMBIGUOUS` — malformed, conflicting, duplicated, or incomplete evidence.

Names are descriptive only. A replacement under the same name is a new subject and requires enrollment.

## Store classifications

- `STORE_HEALTHY`;
- `STORE_MISSING`;
- `STORE_PERMISSION_DENIED`;
- `STORE_PARTIAL_WRITE`;
- `STORE_CORRUPT`;
- `STORE_DISK_FULL`;
- `STORE_AMBIGUOUS`.

Only `STORE_HEALTHY` permits a normal recovery disposition.

## Recovery dispositions

- `RESUME_OBSERVATION_ONLY` — subject matched, store healthy, and no unresolved action uncertainty exists;
- `SUPPRESS_DUPLICATE` — an identical request already has terminal execution evidence or an accepted terminal gateway result;
- `REQUIRE_REENROLLMENT` — subject replacement is detected;
- `REPORT_SUBJECT_UNAVAILABLE` — subject is missing or stopped;
- `FAIL_CLOSED_STORE` — store health is not proven;
- `FAIL_CLOSED_UNCERTAIN` — evidence is malformed, contradictory, incomplete, or action outcome is uncertain.

## Duplicate rule

No restart may recreate or re-authorize a request whose request ID and digest are already terminal. Conflicting reuse of a request ID fails closed.

## Safety result

Every report states:

```text
observation_only = true
gateway_enabled = false
native_execution_authorized = false
```

Stage 8 performs no filesystem writes, Docker calls, gateway calls, or process control.
