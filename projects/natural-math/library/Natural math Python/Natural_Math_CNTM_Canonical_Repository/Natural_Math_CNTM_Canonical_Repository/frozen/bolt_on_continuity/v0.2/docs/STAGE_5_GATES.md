# Stage 5 Gates — Observation-Only CLI Lifecycle

Stage 5 passes only when every gate below is satisfied.

## Gate 1 — Exact command surface

Only `version`, `config-check`, `status`, `start`, and `stop` are accepted. Unknown commands fail closed.

## Gate 2 — Stage 4 validation reuse

Configuration-dependent commands use the Stage 4 configuration validator. No weaker parallel validation path exists.

## Gate 3 — Plans are not execution

`start` and `stop` return deterministic plans only. Outputs contain no executable command, process identifier, service mutation, Docker call, or claim of completed execution.

## Gate 4 — Safe state reporting

Stage 5 reports only `NOT_STARTED`, `OBSERVATION_PLAN_READY`, and `STOP_PLAN_READY`.

## Gate 5 — Safety invariants

All accepted outputs preserve:

```text
observation_only = true
gateway_enabled = false
autonomous_actions = false
native_execution_authorized = false
```

## Gate 6 — No side effects

The implementation contains no file writes, directory creation, subprocess use, socket access, process inspection, service installation, threads, background work, or Docker access.

## Gate 7 — Determinism

Identical command and configuration bytes produce byte-identical canonical JSON.

## Gate 8 — Tests

Tests cover all accepted commands, unknown-command rejection, malformed and tampered configuration rejection, deterministic output, safety invariants, and the distinction between plans and execution.

## Gate 9 — Structural verification

The Stage 5 verifier checks required files, exact command and state sets, forbidden operational imports and calls, safety markers, and required tests.

## Gate 10 — Frozen regression

```powershell
python .\tools\verify_all_frozen.py
git diff -- .\frozen
```

Required result:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

The frozen diff must be empty.

## Advancement authorization

Passing Stage 5 authorizes Stage 6 offline incident explanation, replay, and export work only. It does not authorize live monitoring, runtime state, Docker mutation, action projection, or gateway execution.
