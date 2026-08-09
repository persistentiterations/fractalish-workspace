# Stage 5 Contract — Observation-Only CLI Lifecycle

## Objective
Provide deterministic local configuration validation and lifecycle planning without starting services or contacting Docker.

## Commands
Stage 5 adds `config-check`, `status`, `start`, and `stop`. Each accepts canonical Stage 4 configuration bytes and delegates validation to the Stage 4 validator.

## Output
Every result is canonical JSON-compatible data containing schema version, product version, command, accepted, reason code, configuration digest and exact subject ID when valid, lifecycle state, and safety fields.

Safety fields are always:

```text
observation_only = true
gateway_enabled = false
autonomous_actions = false
native_execution_authorized = false
```

Lifecycle states are limited to `NOT_STARTED`, `OBSERVATION_PLAN_READY`, and `STOP_PLAN_READY`. They describe plans only.

`config-check` validates without repair. `status` reports `NOT_STARTED` because no runtime store exists. `start` returns an observation plan. `stop` returns a stop plan and explicitly states that the enrolled container remains independently operable and is not stopped or mutated.

## Prohibited behavior
Stage 5 does not call Docker, invoke subprocesses, create or modify files, inspect processes, install services, open sockets, start threads, project HOLD or RELEASE, enable a gateway, or claim that a plan was executed.
