# Stage 4 Contract — Canonical Configuration and Validation

## Objective

Build and validate one deterministic configuration for one explicitly enrolled Docker container without writing to the filesystem.

## Input boundary

The builder accepts only a validated Stage 3 enrollment record with schema version 1, the Stage 3 contract identifier, an exact lowercase 64-character hexadecimal container ID, observation-only true, gateway-enabled false, and a valid enrollment digest.

## Canonical configuration

The configuration contains exactly: `schema_version`, `product`, `product_version`, `subject`, `mode`, `storage`, `retention`, `authority`, and `configuration_digest`.

Canonical JSON uses UTF-8, sorted keys, compact separators, no NaN, and exactly one trailing newline when emitted as storage-ready bytes. The digest is SHA-256 over canonical JSON with `configuration_digest` omitted.

## Safe defaults

The mode is exactly:

```text
observation_only = true
gateway_enabled = false
approval_required = true
autonomous_actions = false
```

The authority vocabulary is exactly `NO_ACTION`, `HOLD`, `RELEASE`. These values do not grant Docker execution authority.

## Storage and retention

The data directory must be a relative local path with no parent traversal, environment expansion, network prefix, drive prefix, or executable suffix. Bounds must be true integers: maximum incidents 1–100000 and maximum receipt bytes per incident 1024–16777216.

Retention mode is `retain_until_operator_deletes` or `bounded_count`.

## Failure behavior

Validation rejects missing or extra fields, unknown versions, malformed or substituted subjects, digest mismatch, altered defaults, expanded authority, unsafe paths, booleans encoded as integers or strings, invalid bounds, unsupported retention, and command or secret fields.

## Non-authority

Stage 4 performs no Docker call, probing, inspection, persistence, installation, service control, monitoring, incident creation, gateway call, projection, or action execution.
