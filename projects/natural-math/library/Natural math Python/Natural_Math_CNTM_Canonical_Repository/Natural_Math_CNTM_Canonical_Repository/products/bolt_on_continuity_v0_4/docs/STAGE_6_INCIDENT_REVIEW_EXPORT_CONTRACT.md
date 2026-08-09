# Bolt-On Continuity v0.4 — Stage 6 Incident Review and Offline Export Contract

## Objective
Provide deterministic review, explanation, offline replay, and in-memory export for operator-supplied incident records.

## Incident boundary
An incident contains exactly an `inc-` prefixed lowercase SHA-256 identifier, one exact lowercase 64-character container ID, one `sha256:` configuration digest, nonnegative sequence bounds, a decision from `NO_ACTION`, `HOLD`, or `RELEASE`, a bounded uppercase reason code, an allowed action status, and a nonempty ordered receipt list.

Each receipt contains exactly `sequence`, `event_type`, `payload`, `previous_digest`, and `receipt_digest`. Digests are recomputed from canonical JSON. The first previous digest is sixty-four zeroes and every later receipt links to the prior digest.

## Operations
- `list` validates all supplied incidents, sorts by updated sequence descending and incident ID ascending, and applies a bounded positive limit.
- `explain` separates observation, decision, projected-action status, receipt-chain validity, and native-execution evidence.
- `replay` uses supplied receipts only and returns terminal sequence, receipt digest, decision, action status, and receipt count.
- `export` constructs canonical export data in memory with the incident, explanation, replay result, manifest, and package digest.

Only `DOCKER_ACCEPTED` is evidence of native execution. `PROJECTED`, `APPROVED`, and `DENIED` never imply execution.

## Authority boundary
Stage 6 validates, lists, explains, replays, and exports supplied data only. It performs no Docker contact, container operation, subprocess execution, process inspection, socket or network access, filesystem read or write, gateway action, approval, denial, native execution, background service, thread creation, recovery, publication, or production claim.

Stage 7 requires separate authorization.
