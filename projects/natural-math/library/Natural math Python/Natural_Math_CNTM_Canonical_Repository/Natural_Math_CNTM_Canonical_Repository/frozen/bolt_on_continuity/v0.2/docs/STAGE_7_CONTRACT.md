# Stage 7 Contract — Approval, Denial, and Gateway State

## Objective

Create a deterministic, data-only operator-control layer for one exact projected request.

Stage 7 must distinguish:

1. projected request;
2. operator approval or denial;
3. gateway enabled or disabled state;
4. gateway execution, which remains unavailable.

## Projected request input

A request must contain exactly:

- schema version;
- request identifier;
- full lowercase 64-character container ID;
- action `HOLD` or `RELEASE`;
- incident digest;
- configuration digest;
- issued sequence;
- expiry sequence;
- request digest.

The request digest covers every field except itself using canonical JSON.

`NO_ACTION` is not approvable. Shortened IDs, names, aliases, command text, extra fields, malformed digests, expired requests, and non-increasing expiry values fail closed.

## Operator decision

The operator decision is exactly `APPROVE` or `DENY`.

Each decision record binds to:

- the exact request identifier;
- the exact request digest;
- the decision;
- a bounded reason code;
- the decision sequence;
- a canonical decision digest.

Approval requires the gateway state to be enabled at the decision sequence. Denial is allowed whether the gateway is enabled or disabled.

An approval does not execute or schedule Docker work. It only creates a verified approval record for a later qualified stage.

## Gateway state

The initial gateway state is disabled.

Allowed state transitions are:

```text
DISABLED -> ENABLED
ENABLED  -> DISABLED
```

Repeated enable or repeated disable requests are rejected as no-transition errors. State records contain no credentials, command paths, socket locations, or executable requests.

## Duplicate and conflict rules

For one request identifier:

- an identical repeated operator decision is rejected as a duplicate;
- a different decision is rejected as a conflict;
- reuse with a different request digest is rejected;
- an expired request cannot be approved;
- a decision sequence before request issuance or after expiry is rejected.

## Authority boundary

Stage 7 must not:

- import or execute the v0.1 gateway;
- call Docker;
- build native command vectors;
- pause or unpause a container;
- write credentials or authorization secrets;
- create autonomous approval;
- treat gateway enablement as execution authority;
- treat approval as execution evidence.

All Stage 7 results state `native_execution_authorized: false`.
