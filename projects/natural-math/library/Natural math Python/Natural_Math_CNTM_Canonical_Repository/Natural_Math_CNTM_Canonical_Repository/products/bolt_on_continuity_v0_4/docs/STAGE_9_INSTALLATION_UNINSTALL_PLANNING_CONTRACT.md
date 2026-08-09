# Bolt-On Continuity v0.4 — Stage 9 Installation and Uninstall Planning Contract

## Objective

Construct deterministic, data-only lifecycle plans for a separately qualified future installer.

Stage 9 consumes one digest-valid Stage 4 configuration and an operator-supplied installation-state snapshot. It does not inspect the filesystem or Docker environment.

## States and outcomes

Installation states are exactly `ABSENT`, `INSTALLED`, `PARTIAL`, and `CONFLICT`.

Install outcomes are `PLAN_INSTALL`, `ALREADY_INSTALLED`, `FAIL_CLOSED_PARTIAL`, and `FAIL_CLOSED_CONFLICT`.

Uninstall choices are `RETAIN_DATA` and `DELETE_DATA`. Retention is the default. Deletion planning requires the exact token `DELETE RECEIPT DATA`.

Uninstall outcomes are `PLAN_UNINSTALL_RETAIN_DATA`, `PLAN_UNINSTALL_DELETE_DATA`, `ALREADY_ABSENT`, `FAIL_CLOSED_CONFIRMATION`, `FAIL_CLOSED_PARTIAL`, and `FAIL_CLOSED_CONFLICT`.

## Protected boundaries

The enrolled container ID is a protected subject reference and is never an operation target. Product-owned relative targets are derived only from the validated Stage 4 data directory.

Every result states `observation_only: true`, `gateway_enabled: false`, `native_execution_authorized: false`, `container_mutation_authorized: false`, `filesystem_mutation_performed: false`, and `deletion_performed: false`.

Stage 9 performs no filesystem read or write, directory creation, package installation, service registration, environment mutation, Docker contact, container mutation, receipt deletion, subprocess execution, or native execution.
