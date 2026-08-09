# Bolt-On Continuity v0.4 — Stage 2 Docker Prerequisite Probe Contract

## Objective

Stage 2 determines whether the local machine has a reachable, local, Linux-mode Docker engine suitable for later bounded demonstration work.

Stage 2 does not inspect any container or change Docker state.

## Newly authorized contact

The authorization to begin Stage 2 permits only these three fixed Docker CLI vectors:

```text
[docker_path, "context", "inspect", "--format", "{{json .}}"]
[docker_path, "version", "--format", "{{json .}}"]
[docker_path, "info", "--format", "{{json .}}"]
```

The current-context inspection runs first. The version and information probes may run only when:

- no `DOCKER_HOST`, `DOCKER_CONTEXT`, `DOCKER_TLS_VERIFY`, or `DOCKER_CERT_PATH` override is active; and
- the inspected Docker endpoint uses a local `npipe://` or `unix://` transport.

Each vector is executed as a direct argument list with `shell=False`, a five-second timeout, and no operator-provided command fragments, contexts, hosts, socket paths, templates, or additional flags.

## Eligibility requirements

Stage 2 eligibility requires:

1. The qualified Stage 1 head and qualification hashes remain unchanged.
2. CPython 3.11 or newer.
3. A Windows or Linux host.
4. A Docker CLI discoverable through `PATH`.
5. No active remote-Docker environment override.
6. A successfully parsed local Docker context.
7. Successful Docker client and server version responses.
8. A successful Docker information response.
9. A Linux-mode Docker engine.
10. The exact bounded Stage 2 authority map.

Missing, timed-out, malformed, nonzero, remote, ambiguous, or non-Linux evidence fails closed.

## Receipt requirements

Human and JSON reports are deterministic and timestamp-free. Reports may include version strings and eligibility states, but must not disclose:

- the Docker executable path;
- usernames or home directories;
- environment values;
- Docker socket or endpoint addresses;
- Docker root directories;
- command stderr;
- container, image, volume, network, log, or event data.

## Explicit exclusions

Stage 2 does not authorize:

- `docker ps`, container listing, container inspection, logs, or events;
- image, volume, network, compose, build, pull, push, run, start, stop, restart, exec, or removal commands;
- direct Docker socket or SDK access;
- filesystem creation or mutation;
- installation or activation;
- background services;
- recovery action;
- publication, packaging, distribution, merge, tag, or freeze;
- production-readiness, compatibility, or security-certification claims.

## Advancement boundary

Stage 2 qualification proves only that the bounded local prerequisite probes are deterministic, fail closed, and can identify an eligible local Linux Docker engine. Stage 3 requires separate authorization.
