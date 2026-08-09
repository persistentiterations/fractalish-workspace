# Stage 9 Contract — Installation and Uninstall Qualification

## Objective

Define deterministic lifecycle plans that a later installer may execute only after separate qualification.

## Inputs

Stage 9 accepts:

- a Stage 4 validated configuration;
- an installation-state snapshot;
- an operator retention choice;
- an exact deletion-confirmation token when deletion is requested.

## Installation states

```text
ABSENT
INSTALLED
PARTIAL
CONFLICT
```

Unknown states are rejected.

## Installation outcomes

```text
PLAN_INSTALL
ALREADY_INSTALLED
FAIL_CLOSED_PARTIAL
FAIL_CLOSED_CONFLICT
```

A clean install plan may name only product-owned paths derived from the validated relative data directory. It must not name Docker sockets, container filesystems, system-wide service registries, arbitrary executable paths, or the monitored container as a mutation target.

## Uninstall choices

```text
RETAIN_DATA
DELETE_DATA
```

`RETAIN_DATA` is the default. `DELETE_DATA` requires the exact token:

```text
DELETE RECEIPT DATA
```

Deletion remains a plan only. Stage 9 performs no deletion.

## Uninstall outcomes

```text
PLAN_UNINSTALL_RETAIN_DATA
PLAN_UNINSTALL_DELETE_DATA
ALREADY_ABSENT
FAIL_CLOSED_CONFIRMATION
FAIL_CLOSED_PARTIAL
FAIL_CLOSED_CONFLICT
```

## Required invariants

Every accepted plan states:

```text
observation_only = true
gateway_enabled = false
native_execution_authorized = false
container_mutation_authorized = false
```

The monitored container ID may be included only as a protected subject reference. It must never appear in an operation target.

## Determinism

Equivalent normalized inputs must produce byte-identical canonical JSON and identical SHA-256 plan digests.

## Non-goals

Stage 9 does not:

- write files or directories;
- install packages;
- register or remove services;
- change PATH or environment variables;
- invoke Docker;
- pause, unpause, stop, restart, remove, or alter a container;
- delete receipt data;
- activate native execution.

## Advancement

Passing Stage 9 authorizes Stage 10 end-to-end usability qualification using deterministic fixtures and non-author workflow evidence. It does not authorize production installation or Docker mutation.
