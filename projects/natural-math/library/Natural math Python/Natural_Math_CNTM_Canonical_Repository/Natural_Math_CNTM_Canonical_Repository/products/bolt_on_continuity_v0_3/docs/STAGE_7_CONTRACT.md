# Stage 7 Contract — Approval, Denial, and Gateway State

## Objective

Create a deterministic, data-only operator-control layer for one exact projected request.

Stage 7 distinguishes projected request, operator decision, gateway state, and native execution. Native execution remains unavailable.

## Projected request

A request contains exactly schema version, request identifier, full lowercase 64-character container ID, action `HOLD` or `RELEASE`, incident digest, configuration digest, issued sequence, expiry sequence, and request digest. The digest covers every field except itself using canonical JSON.

`NO_ACTION`, shortened IDs, names, aliases, command text, extra fields, malformed digests, expired requests, and non-increasing expiry fail closed.

## Operator decision

A decision is exactly `APPROVE` or `DENY` and binds to the exact request identifier and digest, a bounded reason code, decision sequence, and canonical decision digest.

Approval requires the gateway to be enabled at the decision sequence. Denial is allowed in either gateway state. Approval does not execute or schedule Docker work.

## Gateway state

Initial state is `DISABLED`. Allowed transitions are `DISABLED -> ENABLED` and `ENABLED -> DISABLED`. Repeated transitions fail closed.

## Duplicate and conflict rules

Identical repeated decisions are duplicates. Different decisions for the same request are conflicts. Reuse of a request identifier with a different digest is rejected. Decisions outside the request sequence window are rejected.

## Authority boundary

Stage 7 does not call Docker, build native command vectors, import an operational gateway, pause or unpause containers, write credentials, create autonomous approval, or treat approval as execution evidence. All results state `native_execution_authorized: false`.