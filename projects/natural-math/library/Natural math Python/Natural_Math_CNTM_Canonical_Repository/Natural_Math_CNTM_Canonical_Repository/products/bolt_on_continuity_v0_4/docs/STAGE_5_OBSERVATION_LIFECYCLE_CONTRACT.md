# Bolt-On Continuity v0.4 — Stage 5 Observation-Only Lifecycle Contract

## Objective

Consume one exact, digest-valid Stage 4 canonical configuration and return deterministic lifecycle validation or planning data without starting a runtime or contacting Docker.

## Commands

Stage 5 supports exactly `config-check`, `status`, `start`, and `stop`.

- `config-check` validates the supplied Stage 4 configuration without repair.
- `status` reports `NOT_STARTED`; Stage 5 has no runtime state store.
- `start` returns an `OBSERVATION_PLAN_READY` plan only.
- `stop` returns a `STOP_PLAN_READY` plan only and states that the enrolled container remains independently operable.

Every command reads canonical Stage 4 JSON from standard input and delegates configuration validation to Stage 4.

## Fixed safety state

Every accepted or rejected result contains:

```text
observation_only = true
gateway_enabled = false
autonomous_actions = false
native_execution_authorized = false
execution_performed = false
container_mutated = false
```

## Canonical result

Results contain the command, acceptance status, reason code, lifecycle state, configuration digest and subject ID when valid, plan data, Stage 4 qualification bindings, authority map, and a canonical SHA-256 result digest.

## Non-authority

Stage 5 performs no Docker call, subprocess execution, filesystem read or write, process inspection, service installation, socket or network operation, thread or background task, container operation, persistence, automatic recovery, gateway action, HOLD or RELEASE projection, publication, production claim, merge, tag, or freeze.

A lifecycle plan is data only and must never be represented as executed work.
