# Stage 5 Contract — Observation-Only CLI Lifecycle

## Objective

Provide a deterministic, local, standard-library command surface that lets an operator validate configuration and understand intended lifecycle state without starting services or contacting Docker.

## Command contract

The accepted commands are exactly:

```text
version
config-check
status
start
stop
```

Unknown commands fail closed with a stable reason code.

## Input contract

`config-check`, `status`, `start`, and `stop` accept canonical configuration bytes produced under Stage 4. The command layer must call the Stage 4 validator and must not weaken or duplicate its validation rules.

## Output contract

Each command returns a canonical JSON object with:

- schema version;
- product version;
- command;
- accepted boolean;
- stable reason code;
- configuration digest when validation succeeds;
- exact subject container ID when validation succeeds;
- lifecycle state or requested lifecycle plan;
- safety fields.

Every output must state:

```text
observation_only = true
gateway_enabled = false
autonomous_actions = false
native_execution_authorized = false
```

## Lifecycle states

Stage 5 recognizes only:

```text
NOT_STARTED
OBSERVATION_PLAN_READY
STOP_PLAN_READY
```

These values describe product planning state only. They do not claim that a process or Docker operation occurred.

## Start contract

`start` validates configuration and returns an `OBSERVATION_PLAN_READY` plan. The plan may name future components but must contain no executable command, PID, service name, socket, shell text, or Docker operation.

## Stop contract

`stop` validates configuration and returns a `STOP_PLAN_READY` plan. It must explicitly state that the monitored container remains independently operable and is not stopped or mutated.

## Status contract

`status` returns `NOT_STARTED` in Stage 5 because no runtime-state store exists. It must not infer process state from the host.

## Config-check contract

`config-check` reports whether Stage 4 configuration validation passed. It must never repair malformed configuration silently.

## Version contract

`version` requires no configuration and reports product version `0.2` and CLI contract version `5`.

## Prohibited behavior

Stage 5 must not:

- call Docker;
- import the v0.1 operational package;
- invoke subprocesses;
- create or modify files;
- create directories;
- inspect processes;
- install services;
- open sockets or listeners;
- start threads or background workers;
- project `HOLD` or `RELEASE`;
- activate or enable the gateway;
- represent a plan as completed execution.

## Advancement

Passing Stage 5 authorizes Stage 6 incident explanation, offline replay, and deterministic export design. It does not authorize a daemon, live monitoring, gateway execution, or Docker mutation.
