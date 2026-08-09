# Stage 2 Contract — Prerequisite and Supported-Environment Checker

## Objective

Provide a deterministic, read-only decision about whether a local host satisfies the bounded prerequisites for future v0.2 installation and one-container enrollment work.

## Supported host families

Stage 2 recognizes only:

- Windows with Docker Desktop using Linux containers;
- native Linux with a local Docker Engine.

macOS, WSL-only ambiguity, remote Docker contexts, Windows-container mode, Kubernetes, Swarm, and unclassified platforms are not qualified by this stage.

## Runtime contract

The checker requires CPython 3.11 or newer. Unsupported implementations or versions produce a failed prerequisite report and no attempted Docker action beyond the fixed read-only probes.

## Docker probe contract

The checker may locate the Docker CLI using the host path and may execute only these fixed argument vectors:

```text
["docker", "version", "--format", "{{json .}}"]
["docker", "info", "--format", "{{json .}}"]
```

The executable path may be resolved by `shutil.which`, but no shell is used. The checker must not accept command fragments, flags, templates, contexts, hosts, socket paths, or environment overrides from the operator.

Each probe has a bounded timeout. Nonzero exit, timeout, missing executable, malformed JSON, missing required fields, or ambiguous engine type fails closed.

## Report contract

The report is a canonical JSON-compatible object with:

- schema version;
- product and stage identifiers;
- host family and machine architecture;
- Python implementation and version;
- Docker CLI presence;
- Docker client version when available;
- Docker server version when available;
- Docker engine operating-system type;
- local-engine status;
- observation-only default;
- gateway-enabled default;
- ordered check records;
- overall eligibility;
- stable reason codes.

No timestamps, random identifiers, absolute Docker executable paths, usernames, home directories, environment variables, secrets, or socket addresses are included in the canonical report.

## Eligibility rule

`eligible` is true only when all mandatory checks pass:

1. supported host family;
2. CPython 3.11 or newer;
3. Docker CLI found;
4. Docker client responds;
5. Docker server responds;
6. engine operating-system type is exactly `linux`;
7. Docker context is local or no remote endpoint evidence is supplied by the fixed probe;
8. observation-only is true;
9. gateway-enabled is false.

Unknown or ambiguous values fail closed.

## Non-goals

Stage 2 does not:

- install or configure software;
- create directories or services;
- enroll or inspect a container;
- read logs or events;
- import the v0.1 engine;
- access the Docker socket directly;
- pause, unpause, stop, restart, kill, remove, exec, create, or run anything;
- modify Docker contexts, networks, volumes, images, or configuration;
- claim that an eligible host is production-ready.
