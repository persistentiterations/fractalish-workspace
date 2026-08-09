# Stage 2 Contract

An incident ledger belongs to exactly one immutable container ID and one
configuration digest.

Each entry contains an incident ID, zero-based sequence, event type, integer
recorded time, evidence digest, exact payload, previous entry digest, and entry
digest.

Allowed event types are:

```text
INCIDENT_OPENED
OBSERVATION_RECORDED
STATE_CHANGED
INCIDENT_NOTE
INCIDENT_CLOSED
```

The first entry must be `INCIDENT_OPENED`. An incident may close once, and no
entry may follow closure. Sequence numbers must be contiguous. Times must be
non-decreasing. Evidence digests and payloads are immutable once appended.

Exports contain the exact ledger, an export digest, and no secret or execution
field. Replay verifies every entry, chain link, subject binding, sequence,
timestamp order, closure rule, and export digest.

Malformed, reordered, removed, duplicated, inserted, rehashed, cross-subject,
cross-configuration, or post-closure records fail closed.

Stage 2 has no Docker transport, no action request, no gateway, and no host
execution authority.
