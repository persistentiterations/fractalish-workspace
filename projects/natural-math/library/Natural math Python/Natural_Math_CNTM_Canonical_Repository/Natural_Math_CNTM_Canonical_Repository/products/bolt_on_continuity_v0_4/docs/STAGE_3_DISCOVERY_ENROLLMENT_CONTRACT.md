# Bolt-On Continuity v0.4 — Stage 3 Discovery and Enrollment Contract

## Objective

Stage 3 discovers existing containers on the already-qualified local Linux Docker engine and constructs one immutable observation-only enrollment record for an explicitly selected container.

Stage 3 does not create a container. It can enroll only a container that already exists.

## Prerequisite binding

Before Stage 3 discovery or enrollment, the live Stage 2 prerequisite probe must produce `STAGE_2_ELIGIBLE`.

Stage 3 is bound to:

- qualified Stage 2 head `15e29c94d81e5e5eae3ddf384eb8fa6af8ffcdc4`;
- Stage 2 qualification record SHA-256 `97b92c58c6bf342c44dd793bfe0a78401b9c606ecaccd27ca1f9c48cd2d6141e`;
- Stage 2 verifier manifest SHA-256 `6f1c6c119c8114ed20e84c6d28dc1e9de9000e6df861939e5775373e4d957192`.

## Authorized Docker vectors

Stage 3 may execute only:

```text
docker container ls --all --no-trunc --format "{{json .}}"
docker container inspect --format <fixed bounded projection> <exact full container ID>
```

The inspection projection contains only the exact container ID, name, configured image, current state, and platform.

Every command uses a direct argument list, `shell=False`, captured text output, `check=False`, and a five-second timeout.

## Identity and confirmation

A candidate is valid only when discovery returns an exact lowercase 64-character hexadecimal container ID.

Enrollment requires:

1. an ID present exactly once in the current discovery result;
2. the same exact ID supplied as both `--select` and `--confirm`;
3. inspection returning the same exact ID;
4. consistent bounded name and image metadata;
5. explicit Linux platform evidence.

Names, prefixes, shortened IDs, indexes, wildcards, regular expressions, and operator-provided Docker flags are not accepted as identity.

## Output

Discovery produces a deterministic report sorted by full container ID.

Enrollment produces an immutable canonical record containing only:

- the qualified Stage 2 bindings;
- exact container ID;
- bounded display name;
- bounded configured image;
- observed state;
- Linux platform evidence;
- the Stage 3 authority map;
- a SHA-256 digest.

The report and enrollment record are printed or returned as data only. No host file, database, Docker label, container configuration, or other persistent state is created or changed.

## Fail-closed behavior

Malformed JSON, truncated or uppercase IDs, duplicates, unsupported states, excessive output, timeouts, nonzero exits, unknown selections, confirmation mismatch, inspection mismatch, metadata mismatch, and non-Linux platform evidence fail closed.

An empty discovery result is valid but cannot produce an enrollment.

## Authority boundary

Stage 3 authorizes only:

- the previously qualified Stage 2 prerequisite probes;
- local Docker-daemon contact;
- enumeration of existing containers;
- inspection of one exactly selected container;
- construction of an in-memory enrollment record.

Stage 3 does not authorize container creation, start, stop, restart, pause, unpause, kill, removal, exec, logs, events, network or volume changes, image changes, direct socket access, filesystem mutation, installation, background services, recovery, package distribution, publication, production claims, merge, tag, or freeze.

## Advancement boundary

Stage 3 qualification proves only bounded discovery, exact identity confirmation, read-only inspection, and deterministic in-memory enrollment. Stage 4 requires separate authorization.
