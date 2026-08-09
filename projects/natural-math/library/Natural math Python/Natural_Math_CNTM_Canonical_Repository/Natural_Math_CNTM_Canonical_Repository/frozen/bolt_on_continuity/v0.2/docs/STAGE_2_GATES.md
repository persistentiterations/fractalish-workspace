# Stage 2 Gates — Prerequisite Checker

Stage 2 passes only when every gate below is satisfied.

## Gate 1 — Fixed read-only probes

Only fixed `docker version` and `docker info` argument vectors are permitted. Shell execution, user-supplied command text, Docker socket access, and mutation commands are absent.

## Gate 2 — Supported environment decision

Windows and Linux are recognized. CPython 3.11 or newer is required. Linux-container engine mode is required. Unknown or ambiguous values fail closed.

## Gate 3 — Deterministic report

The same normalized inputs produce byte-identical canonical JSON. Reports contain no timestamps, randomness, usernames, home paths, executable paths, secrets, or environment dumps.

## Gate 4 — Safe defaults

Every report states:

```text
observation_only = true
gateway_enabled = false
```

No Stage 2 path can change those values.

## Gate 5 — Bounded failures

Missing Docker, client failure, daemon failure, timeout, malformed JSON, Windows-container mode, unsupported Python, unsupported host, and remote-endpoint evidence produce stable failure reason codes.

## Gate 6 — No engine activation

Stage 2 does not import `bolt_on_continuity`, execute v0.1 code, inspect a container, create an incident, project an action, or invoke the gateway.

## Gate 7 — Tests

Tests cover passing Windows and Linux fixtures, missing Docker, daemon unavailable, malformed output, Windows-container mode, unsupported Python, unsupported platform, remote endpoint rejection, canonical stability, and exact command allowlisting.

## Gate 8 — Structural verifier

The verifier checks required files, forbidden mutation tokens, fixed command vectors, safe defaults, test presence, and Stage 1 boundary validity.

## Gate 9 — Frozen regression

Run:

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

Passing Stage 2 authorizes Stage 3 container discovery and explicit enrollment design. It does not authorize container mutation, installation changes, gateway execution, or action projection.
