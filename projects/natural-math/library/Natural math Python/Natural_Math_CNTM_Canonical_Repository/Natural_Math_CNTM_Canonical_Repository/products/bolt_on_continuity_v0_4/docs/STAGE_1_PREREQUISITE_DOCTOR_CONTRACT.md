# Bolt-On Continuity v0.4 — Stage 1 Prerequisite Doctor Contract

## Objective

Stage 1 adds one bounded, read-only prerequisite doctor that explains whether a supplied machine snapshot is suitable for later product demonstration work.

## Permitted inspection

Stage 1 may inspect:

- the running Python version;
- the operating-system family;
- selected environment values used only to recommend a local data path;
- whether a Docker CLI executable is discoverable through `PATH`.

Discovering a Docker CLI path is not proof that Docker is running, reachable, correctly configured, or supported.

## Required checks

The deterministic report contains stable checks for:

1. Python 3.11 or newer.
2. Windows or Linux platform recognition.
3. Docker CLI path discovery.
4. A recommended future local data directory.
5. The Stage 0 qualification binding.
6. The all-false operational and release authority boundary.

A missing Docker CLI is a warning, not a failure. An unsupported operating-system family is a warning pending later qualification.

## Output requirements

For the same supplied snapshot, human and JSON output must be byte-for-byte repeatable. JSON is canonical, sorted, timestamp-free, and excludes the full environment.

## Explicit exclusions

Stage 1 must not:

- execute Docker or any other external process;
- contact a Docker daemon, API, socket, or network service;
- import a Docker SDK;
- create, edit, or delete host files or directories;
- install or activate software;
- start background work or services;
- enroll or inspect containers;
- publish, distribute, merge, tag, or freeze a release;
- claim production readiness, compatibility, security certification, or successful Docker operation.

## Advancement boundary

Stage 1 qualification proves only that the doctor is deterministic, read-only, and correctly bounded. Stage 2 requires separate authorization.
