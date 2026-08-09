# Stage 6 Contract — Incident Review and Offline Export

## Objective

Provide deterministic incident-review functions around supplied, already-recorded incident data without Docker access or filesystem mutation.

## Accepted incident model

Each incident must contain exactly:

- `incident_id` — lowercase SHA-256 identifier prefixed by `inc-`;
- `container_id` — exact lowercase 64-character Docker ID;
- `configuration_digest` — `sha256:` plus 64 lowercase hexadecimal characters;
- `opened_sequence` and `updated_sequence` — nonnegative integers with updated not earlier than opened;
- `decision` — exactly `NO_ACTION`, `HOLD`, or `RELEASE`;
- `reason_code` — bounded uppercase identifier;
- `action_status` — exactly `NOT_PROJECTED`, `PROJECTED`, `APPROVED`, `DENIED`, `GATEWAY_REJECTED`, `DOCKER_ACCEPTED`, or `DOCKER_REJECTED`;
- `receipts` — a nonempty ordered list of canonical receipt objects.

## Listing

Incident listing is sorted by `updated_sequence` descending and then `incident_id` ascending. Listing output is bounded by an explicit positive limit and contains summaries only.

## Explanation

Explanation must separately report:

1. observed subject and sequence range;
2. bounded decision and reason code;
3. projected-action status;
4. whether native Docker execution is evidenced;
5. receipt-chain verification result.

A projected or approved action is not represented as executed. Only `DOCKER_ACCEPTED` may set `native_execution_evidenced` to true.

## Offline replay

Replay uses only the supplied receipt sequence. Every receipt contains a sequence, event type, payload, previous digest, and receipt digest. Digests are recalculated canonically and chain continuity is verified.

Replay produces the final declared decision, action status, terminal receipt digest, and receipt count. It does not contact Docker.

## Export

Export creation returns canonical bytes in memory only. The package contains:

- incident summary;
- full incident record;
- replay result;
- manifest of member names, byte counts, and SHA-256 values;
- package digest.

No secrets, host environment, usernames, home paths, executable paths, Docker socket locations, or arbitrary files may be included.

## Authority boundary

Stage 6 contains no Docker commands, subprocess execution, socket access, filesystem writes, gateway activation, action approval, or native execution.

## Advancement

Passing Stage 6 authorizes Stage 7 approval and denial interface design. It does not authorize live gateway execution or Docker mutation.
