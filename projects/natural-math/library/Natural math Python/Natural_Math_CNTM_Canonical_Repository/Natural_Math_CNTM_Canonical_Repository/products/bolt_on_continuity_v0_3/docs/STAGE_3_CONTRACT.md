# Stage 3 Contract — Discovery and Enrollment

## Objective

Discover local Docker containers and construct one immutable observation-only enrollment record without granting mutation authority.

## Fixed probes

Stage 3 may execute only these shell-free argument vectors:

```text
docker container ls --all --no-trunc --format {{json .}}
docker inspect <exact full 64-character lowercase container ID>
```

Each probe has a bounded timeout. Operator-supplied Docker flags, contexts, hosts, socket paths, command fragments, names, prefixes, indexes, wildcards, and shell text are rejected.

## Identity and confirmation

A subject is identified only by an exact lowercase 64-character hexadecimal container ID returned by discovery. Enrollment requires the same exact ID as both selection and confirmation.

## Output

A successful enrollment record contains the exact ID, bounded display metadata, observed state, `observation_only: true`, `gateway_enabled: false`, and a canonical SHA-256 digest. It is returned as data only and is not persisted.

## Failure behavior

Malformed output, duplicate IDs, truncated IDs, unknown IDs, confirmation mismatch, inspection mismatch, unsupported platform evidence, timeouts, and nonzero probe exits fail closed.

## Non-authority

Stage 3 contains no pause, unpause, stop, restart, kill, remove, exec, run, create, network, volume, image, gateway, projection, decision, or incident authority.
