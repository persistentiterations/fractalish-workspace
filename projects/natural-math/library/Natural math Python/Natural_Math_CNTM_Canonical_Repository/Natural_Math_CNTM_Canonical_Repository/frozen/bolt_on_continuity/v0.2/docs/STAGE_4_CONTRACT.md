# Stage 4 Contract — Canonical Configuration and Validation

## Objective

Create and validate one deterministic local configuration for one explicitly enrolled Docker container.

## Input boundary

The builder accepts only a validated Stage 3 enrollment record containing:

- schema version;
- exact lowercase 64-character container ID;
- display name;
- image reference;
- observation-only true;
- gateway-enabled false.

## Canonical configuration

The configuration contains exactly:

- `schema_version`;
- `product`;
- `product_version`;
- `subject`;
- `mode`;
- `storage`;
- `retention`;
- `authority`;
- `configuration_digest`.

Canonical JSON uses UTF-8, sorted keys, compact separators, no NaN, and one trailing newline when serialized for storage.

The digest is SHA-256 over the canonical configuration with `configuration_digest` omitted.

## Safe defaults

The only Stage 4 mode is:

```text
observation_only = true
gateway_enabled = false
approval_required = true
autonomous_actions = false
```

The authority list is exactly:

```text
NO_ACTION
HOLD
RELEASE
```

These values describe bounded decision vocabulary only. They do not grant Docker execution authority.

## Storage and retention bounds

Stage 4 records a relative local data directory, maximum incident count, maximum receipt bytes per incident, and retention mode. Absolute paths, parent traversal, environment expansion, network locations, and executable paths are rejected.

Supported retention modes are `retain_until_operator_deletes` and `bounded_count`.

## Validation

The validator rejects:

- missing or extra fields;
- unknown schema or product versions;
- shortened, uppercase, malformed, or substituted container IDs;
- name-only subjects;
- digest mismatch;
- altered safe defaults;
- expanded action values;
- absolute, network, or escaping paths;
- booleans encoded as integers or strings;
- non-integer, zero, negative, or excessive bounds;
- unsupported retention modes;
- secrets or command text fields.

## No write side effect

Stage 4 returns canonical bytes but does not choose a host destination or write a configuration file. Filesystem installation and atomic persistence require later qualification.

## Non-authority

Stage 4 performs no Docker probe, inspect, pause, unpause, installation, service control, monitoring, gateway call, incident creation, or action projection.
