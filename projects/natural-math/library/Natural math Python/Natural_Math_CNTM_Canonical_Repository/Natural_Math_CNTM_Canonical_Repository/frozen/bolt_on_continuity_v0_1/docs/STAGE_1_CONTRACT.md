# Stage 1 Contract — Read-Only Docker Observer

Stage 1 accepts one immutable configured container ID, one configuration digest,
one integer collection sequence, one integer observation time, raw inspect JSON,
bounded event records, and bounded log bytes.

Accepted output contains canonical normalized evidence, an evidence digest, a
deterministic receipt, the retained raw capture, and replay verification.

Fail-closed reasons include malformed inspect data, malformed events, wrong or
ambiguous subject, stale or future evidence, unsupported state, exceeded bounds,
tampering, and transport failure.

Default qualification bounds are 100 events, 65,536 log bytes, 30 seconds maximum
evidence age, five seconds future skew, exactly one inspect object, and exactly
one configured container ID.

Canonical JSON uses UTF-8, sorted keys, no insignificant whitespace, no floats,
integer times and sequences, and SHA-256 digests.

The observer must not expose a generic command runner, invoke a shell, accept a
user-provided Docker subcommand, project HOLD or RELEASE, contain gateway code,
connect to a listener, or select multiple subjects.
