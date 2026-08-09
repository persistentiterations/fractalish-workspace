# Product Contract — Stage 0

## Contract identifier

```text
BONACQUI_BOLT_ON_CONTINUITY_DOCKER_PRODUCT_CONTRACT_0_1_STAGE_0
```

## Product objective

Build a removable local sidecar for one configured Linux Docker container that:

1. observes bounded Docker evidence through a read-only surface;
2. normalizes evidence deterministically;
3. preserves append-only, tamper-detectable incident receipts;
4. detects only explicitly configured bounded divergence conditions;
5. projects only `HOLD` or `RELEASE`;
6. submits a bounded request only through a separate host-owned gateway;
7. leaves Docker and the host operator in control of execution;
8. can be disabled and uninstalled without impairing the monitored container.

## First user problem

The product addresses recurring local service incidents whose reconstruction
would otherwise require manually combining container state, event timing, bounded
logs, configuration, and remembered operator actions.

## Product subject

Exactly one configured container is in scope. The subject must be bound to an
immutable Docker container identifier. A human-readable container name may be
recorded but must not be sufficient authority for an action.

If a container is replaced under the same name, the replacement is a different
subject and requires explicit reconfiguration.

## Observation contract

A future observer may read only the configured evidence classes:

- Docker container identity;
- container lifecycle state;
- health state when exposed by the container;
- selected Docker events;
- bounded log evidence;
- observation timestamp and collection sequence;
- observer and schema versions.

Observation must be bounded by configured byte, record, and time limits.
Truncation must be explicit and receipt-backed.

The observer must not expose command, exec, shell, stop, restart, kill, remove,
network, volume, image, or configuration-mutation methods.

## Decision contract

The decision component accepts canonical normalized evidence only.

A decision must be:

- deterministic;
- bound to a product-contract version;
- bound to one exact subject;
- bound to one configuration digest;
- bound to the evidence receipt or incident digest;
- replayable without Docker access;
- either `NO_ACTION`, `HOLD`, or `RELEASE`.

Ambiguous, stale, incomplete, malformed, unauthorized, unsupported, or
tampered evidence must yield `NO_ACTION` or a fail-closed rejection receipt.

## Action-request contract

A projected request is not an executed action.

A request must include:

- exact schema and contract versions;
- exact container identifier;
- one action from `HOLD` or `RELEASE`;
- triggering incident digest;
- configuration digest;
- unique request identifier;
- issuance and expiry values;
- expected observed state;
- canonical request digest.

It must not include:

- shell text;
- arbitrary Docker arguments;
- a command path;
- a Docker socket reference;
- executable code;
- user-selected native commands;
- wildcard targets.

## Host-owned gateway contract

The future gateway is a separate package and process boundary.

It must independently validate:

- request schema;
- request digest;
- contract version;
- exact configured subject;
- action allowlist;
- request freshness;
- duplicate and replay status;
- triggering receipt binding;
- expected current state;
- local authorization configuration.

Only after validation may it map:

```text
HOLD    -> pause the exact configured container
RELEASE -> unpause the exact configured container
```

The gateway must reject every other operation.

## Receipt contract

Every material transition must create a canonical receipt:

- evidence accepted or rejected;
- normalization result;
- incident opened or updated;
- divergence decision;
- action projected or suppressed;
- gateway accepted or rejected;
- Docker accepted or rejected;
- resulting observed state;
- replay result;
- disable, recovery, or uninstall event.

Receipts must be hash-chained within an incident and exportable without secrets.

## Lifecycle contract

Later stages must provide:

- explicit installation;
- explicit configuration;
- observation-only mode;
- action projection enable/disable;
- gateway enable/disable;
- safe component restart;
- no duplicate action after restart;
- deterministic recovery;
- uninstall;
- explicit evidence retention or deletion choice.

Sidecar, viewer, or gateway failure must not corrupt or terminate the monitored
container.

## Non-goals for v0.1

- autonomous root-cause diagnosis;
- arbitrary remediation;
- production security certification;
- remote Docker daemons;
- internet-facing operation;
- multi-container coordination;
- Kubernetes or Docker Swarm;
- enterprise identity or authentication;
- generalized policy language;
- support for every Docker version or platform;
- universal compatibility;
- zero-drift claims.
