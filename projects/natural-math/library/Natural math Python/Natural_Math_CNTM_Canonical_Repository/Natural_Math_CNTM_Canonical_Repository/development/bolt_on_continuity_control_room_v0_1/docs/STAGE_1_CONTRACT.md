# Bolt-On Continuity Control Room v0.1 — Stage 1 Contract

## Claim

Stage 1 proves one local, observation-only path from a real Docker `inspect`
result to a canonical record, deterministic receipt, and minimal local web page.
It observes exactly one operator-selected container per request.

## Fixture boundary

`ContainerObserver.inspect_one(subject)` is the only observation boundary. Unit
tests use `FixtureObserver`, which returns a captured Docker inspection object.
The live path uses `DockerCliObserver`, whose only Docker operation is:

```text
docker inspect --type container <subject>
```

The subject is passed as one subprocess argument. The adapter exposes no generic
command method and no mutation method.

## Canonical observation

Only `Id`, `Name`, `Config.Image`, `Image`, `State.Status`, `State.Running`,
`Created`, and `State.StartedAt` cross the canonicalization boundary. Missing or
empty values become `null` and display as unavailable. No fallback is invented.

## Evidence and receipt

The retained record contains the selected subject, source interface, source
command, canonical source fields, result, and observation time. The receipt is
SHA-256 over UTF-8 canonical JSON containing schema
`bolt-on-continuity-control-room-receipt/v1`, subject, source interface,
canonical fields, and result. Keys are sorted and separators fixed. Observation
time is external event metadata and excluded, so identical facts produce the
same receipt.

## Display provenance

Container facts are **observed**. Observer connection is **derived**.
Observation time and receipt ID are **retained**. Missing values are
**unavailable**. Operator input is never presented as an observed fact.

## Demonstration fixture

The operator may explicitly launch a harmless container outside the application:

```powershell
docker run --detach --name bolt-on-control-room-demo --publish 127.0.0.1:8088:80 nginx:alpine
```

The application never runs this command. It receives exactly one container name
or ID and performs inspection only.

## Explicit exclusions

Stage 1 contains no stop, start, restart, pause, unpause, kill, rename, remove,
create, exec, copy, update, or network-management call. It contains no incident
controls, history comparison, recovery logic, operator decisions, background
service, installation, publication, or production-readiness claim.

## Qualification

Qualification requires unit tests, the explicit live-Docker integration test
against one operator-selected harmless container, the Stage 1 verifier with
`--require-docker`, all frozen-release verification, an unchanged `frozen/`
tree, and a clean committed worktree.
