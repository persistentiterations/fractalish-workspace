# Stage 9 Contract — Installation and Uninstall Qualification

## Objective

Define deterministic lifecycle plans that a later installer may execute only after separate qualification.

## Inputs

Stage 9 accepts a Stage 4 validated configuration, an installation-state snapshot, an operator retention choice, and an exact deletion-confirmation token when deletion is requested.

## States and outcomes

Installation states are exactly `ABSENT`, `INSTALLED`, `PARTIAL`, and `CONFLICT`.

Install outcomes are exactly `PLAN_INSTALL`, `ALREADY_INSTALLED`, `FAIL_CLOSED_PARTIAL`, and `FAIL_CLOSED_CONFLICT`.

Uninstall choices are exactly `RETAIN_DATA` and `DELETE_DATA`. Retention is the default. Deletion requires the exact token `DELETE RECEIPT DATA` and remains a plan only.

Uninstall outcomes are exactly `PLAN_UNINSTALL_RETAIN_DATA`, `PLAN_UNINSTALL_DELETE_DATA`, `ALREADY_ABSENT`, `FAIL_CLOSED_CONFIRMATION`, `FAIL_CLOSED_PARTIAL`, and `FAIL_CLOSED_CONFLICT`.

## Invariants

Every plan states `observation_only: true`, `gateway_enabled: false`, `native_execution_authorized: false`, and `container_mutation_authorized: false`.

The monitored container ID is a protected subject reference only and never an operation target. Product-owned relative paths are derived only from the validated Stage 4 data directory.

## Non-authority

Stage 9 performs no filesystem write, directory creation, package installation, service registration, environment change, Docker call, container mutation, receipt deletion, or native execution.
