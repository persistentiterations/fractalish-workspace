# Stage 1 Contract — Clean Scaffold and Frozen Engine Boundary

## Objective

Create a separate v0.2 product package and record the exact frozen v0.1 components that may later be evaluated for reuse.

## Package isolation

The v0.2 package namespace is:

```text
bolt_on_continuity_v0_2
```

It must not shadow or replace the v0.1 namespace `bolt_on_continuity`.

## Allowed Stage 1 behavior

Stage 1 may:

- expose product identity and version constants;
- load and validate a static JSON engine-boundary manifest;
- calculate SHA-256 digests for repository files during verification;
- report whether the declared frozen sources still match their recorded digests.

Stage 1 must not:

- import a v0.1 operational module;
- copy a v0.1 operational module into v0.2;
- invoke Docker;
- import a Docker SDK;
- use `subprocess`, `os.system`, shell execution, or command text;
- open the Docker socket;
- perform observation, projection, approval, gateway, or execution operations;
- add new action values;
- modify any frozen or v0.1 development file.

## Engine-boundary manifest

The manifest records named reuse candidates. Each entry must include:

- stable component identifier;
- frozen relative source path;
- expected SHA-256 digest;
- disposition `candidate_only`;
- intended future proof type;
- whether native Docker authority is present in the source.

A manifest entry is not reuse approval. Stage 2 or later must create an explicit adapter or vendored boundary and prove equivalence before operational use.

## Initial candidate set

Stage 1 records only the components necessary to define the future boundary:

- incident ledger;
- bounded action projector;
- host-owned gateway;
- dry-run native action adapter;
- controlled native executor;
- read-only Docker observer;
- deterministic continuity pipeline.

The executor, observer, gateway, and native adapter remain particularly restricted because their source participates in Docker-facing behavior. Their presence in the manifest grants no import or execution authority.

## Dependency rule

The Stage 1 package uses only the Python standard library and has no runtime dependency on Docker or the v0.1 Python package.

## Fail-closed rule

Boundary loading must reject:

- malformed JSON;
- unknown schema version;
- missing or extra top-level fields;
- duplicate component identifiers;
- absolute paths;
- paths outside `frozen/bolt_on_continuity_v0_1`;
- non-SHA-256 digest formats;
- dispositions other than `candidate_only`;
- unknown proof types;
- unexpected action values.

## Advancement

Stage 1 completion authorizes Stage 2 prerequisite and environment detection work. It does not authorize live Docker mutation or reuse of an operational v0.1 module.
