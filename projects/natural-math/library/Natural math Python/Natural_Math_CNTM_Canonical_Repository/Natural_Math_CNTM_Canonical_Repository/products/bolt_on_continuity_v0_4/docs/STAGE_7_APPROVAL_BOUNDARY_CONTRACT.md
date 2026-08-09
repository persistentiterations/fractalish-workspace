# Bolt-On Continuity v0.4 — Stage 7 Approval Boundary Contract

## Objective

Provide deterministic, data-only operator control for one exact projected HOLD or RELEASE request.

## Boundary

A projected request binds an exact request ID, full container ID, action, incident digest, configuration digest, issued sequence, expiry sequence, and canonical digest. Operator decisions are exactly APPROVE or DENY and bind to the exact request and sequence window.

Gateway state begins DISABLED. Approval requires an ENABLED gateway at or before the decision sequence. Denial is permitted while disabled. Approval records authorization data only; it never executes, schedules, or constructs a Docker command.

Identical repeated decisions fail as duplicates. Different decisions for the same request fail as conflicts. Reusing a request ID with a different request digest fails closed.

## Non-authority

Stage 7 performs no Docker contact or mutation, native command construction or execution, container operation, filesystem access or mutation, subprocess execution, socket or network access, credential write, autonomous approval, background service, thread creation, recovery, publication, installation, or distribution.
