# Stage 6 Contract — Incident Review and Offline Export

## Objective

Provide deterministic review, explanation, offline replay, and in-memory export for supplied incident records.

## Incident boundary

Each incident contains an `inc-` prefixed lowercase SHA-256 identifier, one exact lowercase 64-character container ID, one `sha256:` configuration digest, nonnegative ordered sequence bounds, a decision from `NO_ACTION`, `HOLD`, or `RELEASE`, a bounded uppercase reason code, an allowed action status, and a nonempty ordered receipt list.

Each receipt contains exactly `sequence`, `event_type`, `payload`, `previous_digest`, and `receipt_digest`. Receipt digests are recomputed over the other four fields using canonical JSON. The first previous digest is sixty-four zeroes and later receipts link to the prior receipt digest.

## Operations

- Listing sorts by updated sequence descending and incident ID ascending and requires a positive bounded limit.
- Explanation separates observation, decision, projected-action status, native-execution evidence, and receipt-chain validity.
- Replay uses supplied receipts only and returns terminal decision, action status, digest, and count.
- Export returns canonical bytes in memory containing summary, full record, replay result, manifest, and package digest.

Only `DOCKER_ACCEPTED` evidences native execution. Projected or approved actions are never represented as executed.

## Non-authority

Stage 6 performs no Docker command, subprocess execution, socket access, filesystem write, gateway activation, approval, denial, or native execution.
