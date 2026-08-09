# RC1 Contract — Bolt-On Continuity for Docker v0.2

## Candidate identity

- Candidate: `v0.2-rc1`
- Qualified source commit: `31dc5ad0740bf1b262de362f334ed64893a027c2`
- Required test count: `127`
- Required test result: `OK`
- Required frozen result: `ALL FROZEN RELEASE VERIFICATIONS PASSED`

## Package scope

The candidate package is the complete `products/bolt_on_continuity_v0_2` tree, excluding transient cache files and generated local artifacts.

The manifest must contain one normalized relative path, byte count, and lowercase SHA-256 digest for every included regular file. Entries must be sorted by path and must be unique.

## Review outcome

A valid candidate may report `RC1_READY_FOR_RELEASE_REVIEW`.

Any missing, extra, changed, duplicated, malformed, path-escaping, or unsupported entry must report `FAIL_CLOSED_RC1_NOT_READY`.

## Authority boundary

RC1 packaging authorizes no runtime or repository mutation beyond files in the RC1 development directory. It does not authorize:

- edits under `frozen`;
- release freeze;
- merge to `main`;
- tag creation;
- artifact publication;
- real installation;
- daemon or service execution;
- gateway execution;
- Docker mutation;
- production-readiness claims.

Every accepted RC1 review record states:

```text
observation_only = true
gateway_enabled = false
native_execution_authorized = false
container_mutation_authorized = false
release_freeze_authorized = false
merge_authorized = false
publication_authorized = false
production_readiness_claim_authorized = false
```
