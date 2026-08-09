# Stage 2 Contract — Bounded Docker Prerequisite Probe

## Objective

Determine whether a local Windows Docker Desktop or native Linux host satisfies the bounded prerequisites for later observation work.

## Permitted probes

Stage 2 may locate the Docker CLI and execute only these shell-free vectors with a bounded timeout:

```text
[docker_path, "version", "--format", "{{json .}}"]
[docker_path, "info", "--format", "{{json .}}"]
```

No operator-provided flags, contexts, hosts, socket paths, templates, or command fragments are accepted.

## Eligibility

Eligibility requires CPython 3.11+, Windows or Linux, a Docker CLI, successful client and server responses, Linux engine mode, local-engine evidence, observation-only authority, and gateway disabled.

Unknown, malformed, remote, timed-out, or nonzero probe results fail closed.

## Prohibitions

Stage 2 does not inspect or enroll containers, read logs or events, access the Docker socket directly, create persistent state, or mutate Docker in any way.
