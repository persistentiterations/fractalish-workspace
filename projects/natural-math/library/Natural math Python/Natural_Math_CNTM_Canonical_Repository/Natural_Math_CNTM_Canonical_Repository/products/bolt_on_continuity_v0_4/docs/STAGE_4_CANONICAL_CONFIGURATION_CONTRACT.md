# Bolt-On Continuity v0.4 — Stage 4 Canonical Configuration Contract

## Objective

Stage 4 consumes one validated Stage 3 enrollment receipt and constructs one deterministic, observation-only configuration entirely in memory.

## Input boundary

The input must be the exact Stage 3 enrollment schema with:

- `product: Bolt-On Continuity v0.4`;
- `stage: 3` and `schema_version: 1`;
- status `STAGE_3_ENROLLED`;
- an exact lowercase 64-character container ID;
- bounded non-empty display name and image;
- Linux platform and a recognized observed state;
- the exact qualified Stage 3 authority map;
- a valid canonical Stage 3 record digest.

Missing, extra, substituted, malformed, or digest-invalid enrollment data fails closed.

## Canonical output

The configuration binds to the qualified Stage 3 head, qualification record, and verifier manifest. It includes only:

- product and stage bindings;
- enrolled subject metadata;
- observation-only safe mode;
- bounded relative storage recommendations;
- bounded retention values;
- the symbolic vocabulary `NO_ACTION`, `HOLD`, `RELEASE`;
- the Stage 4 authority map;
- one SHA-256 configuration digest.

Canonical JSON is UTF-8, sorted, compact, NaN-free, and ends with exactly one newline.

## Safe defaults

- observation only: true;
- gateway enabled: false;
- operator approval required: true;
- autonomous actions: false;
- persistence authorized: false;
- Docker contact: false;
- Docker mutation: false.

The action vocabulary is descriptive configuration data and grants no execution authority.

## Storage and retention bounds

The data directory must be a relative local POSIX-style path. Parent traversal, absolute paths, Windows drive or backslash paths, environment expansion, home expansion, NUL characters, network paths, and executable suffixes are rejected.

Maximum incidents must be a true integer from 1 through 100000. Maximum receipt bytes per incident must be a true integer from 1024 through 16777216. Retention mode is either `retain_until_operator_deletes` or `bounded_count`.

## Non-authority

Stage 4 performs no Docker command, daemon contact, container inspection, container mutation, filesystem write, installation, service control, monitoring, incident creation, recovery, publication, merge, tag, or freeze.

A disposable Docker qualification fixture may be created and removed by an operator outside the product solely to obtain a real Stage 3 enrollment receipt. That operator fixture does not expand Stage 4 authority.
