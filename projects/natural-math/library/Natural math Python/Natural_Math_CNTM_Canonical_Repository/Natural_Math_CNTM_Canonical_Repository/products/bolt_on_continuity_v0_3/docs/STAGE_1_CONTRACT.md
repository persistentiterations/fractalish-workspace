# Stage 1 Contract — Prerequisite and Environment Detection

## Objective

Provide a deterministic, read-only `bolt doctor` command that explains whether the local machine satisfies the prerequisites for later installation and Docker observation stages.

## Permitted behavior

Stage 1 may inspect in-process Python and platform metadata, environment variables used to recommend local data paths, and whether a Docker CLI executable is discoverable through `PATH`.

Stage 1 must not execute Docker, contact a Docker daemon or socket, import a Docker SDK, create configuration or database files, start background work, enroll containers, or mutate Docker.

## Doctor checks

The report contains stable check identifiers for:

- supported Python version;
- supported operating-system family;
- Docker CLI path discovery;
- proposed local data directory;
- observation-only authority.

Docker CLI absence is reported as `WARN`, not treated as proof that Docker is unavailable. Discovering an executable is not proof that the daemon is reachable or supported.

## Output

Human output is deterministic for the supplied environment snapshot. JSON output is canonical, sorted, and contains no timestamps or host secrets.

## Advancement

Stage 1 completion authorizes Stage 2 guided configuration and controlled local persistence. It does not authorize Docker contact or mutation.
