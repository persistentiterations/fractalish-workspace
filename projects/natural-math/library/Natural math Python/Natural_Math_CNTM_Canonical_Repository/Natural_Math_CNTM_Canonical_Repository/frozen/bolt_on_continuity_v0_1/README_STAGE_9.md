# Bolt-On Continuity for Docker v0.1 — Stage 9

## Adversarial Rejection and Bounded Recovery Qualification

**Foundation commit:** `f892511`

Stage 9 does not add any Docker authority. It qualifies rejection behavior and
one bounded recovery path using only:

```text
docker inspect <full-container-id>
docker pause <full-container-id>
docker unpause <full-container-id>
```

The fixture suite verifies deterministic rejection of malformed subjects,
commands, states, sequence values, altered receipt chains, and failed
postconditions.

The live recovery qualification deliberately rejects the first RELEASE request
inside a transport wrapper. The container remains paused, after which exactly
one recovery RELEASE is permitted. Qualification passes only when the final
independent state is:

```text
running=true paused=false
```
